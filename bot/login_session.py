# SPDX-License-Identifier: Apache-2.0
"""pexpect-driven paste-login flow for the optimai CLI.

Drives `optimai-cli auth login --no-open --paste` (verified v0.1.63: the
flags exist; the CLI prints a login URL pointing at node.optimai.network,
then reads the pasted redirect URL/code from stdin). pexpect calls are
blocking, so they run in worker threads via `asyncio.to_thread`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re

import pexpect

from .optimai import OptimaiCLI

log = logging.getLogger(__name__)

# Primary: the real dashboard login URL shape.
URL_RE = re.compile(r"https://\S*node\.optimai\.network/login\?\S+", re.IGNORECASE)
# Fallback: any generic https URL line mentioning "login".
URL_FALLBACK_RE = re.compile(r"https://\S+", re.IGNORECASE)

SUCCESS_WORDS = ("success", "logged in", "authenticated", "signed in")
FAILURE_WORDS = ("error", "failed", "invalid", "incorrect", "unauthorized", "denied")

GONE_MESSAGE = "The login process is gone — start a new session with /login."
URL_CAPTURE_TIMEOUT = 60  # seconds to wait for the CLI to print the URL
SUBMIT_TIMEOUT = 90       # seconds to wait for paste-result confirmation


class LoginSession:
    """One in-flight `auth login --no-open --paste` process."""

    def __init__(self, cli: OptimaiCLI) -> None:
        env = os.environ.copy()
        env["HOME"] = cli.home

        self.child: pexpect.spawn | None = pexpect.spawn(
            cli.binary,
            ["auth", "login", "--no-open", "--paste"],
            env=env,
            encoding="utf-8",
            timeout=URL_CAPTURE_TIMEOUT,
        )
        self.url: str | None = None

    # ------------------------------------------------------------------
    # URL capture
    # ------------------------------------------------------------------

    async def wait_for_url(self) -> str | None:
        """Read CLI output until the login URL appears (or timeout/EOF)."""

        def _find() -> str | None:
            child = self.child
            if child is None:
                return None
            try:
                index = child.expect([URL_RE, pexpect.EOF, pexpect.TIMEOUT])
                if index == 0:
                    return child.match.group(0).strip().rstrip(".,)")
                # Fallback: scan captured output for a generic login URL.
                blob = (child.before or "") + (getattr(child, "buffer", "") or "")
                match = URL_FALLBACK_RE.search(blob)
                if match and "login" in match.group(0).lower():
                    return match.group(0).strip().rstrip(".,)")
                return None
            except pexpect.ExceptionPexpect as exc:
                log.warning("Login URL capture failed: %s", exc)
                return None

        url = await asyncio.to_thread(_find)
        self.url = url
        return url

    # ------------------------------------------------------------------
    # Paste submission
    # ------------------------------------------------------------------

    async def submit(self, text: str) -> tuple[bool, str]:
        """`sendline` the pasted redirect URL/code; watch the output for
        success/failure words; return (ok, summary_text). Never raises."""

        def _submit() -> tuple[bool, str]:
            child = self.child
            if child is None or child.closed:
                return (False, GONE_MESSAGE)
            try:
                child.sendline(text.replace("\n", " ").replace("\r", " "))
                return self._interpret(child)
            except pexpect.ExceptionPexpect as exc:
                return (False, f"Login flow error: {exc}")

        return await asyncio.to_thread(_submit)

    def _interpret(self, child: pexpect.spawn) -> tuple[bool, str]:
        """Scan CLI lines after the paste for success/failure words."""
        ok = False
        lines: list[str] = []
        while True:
            index = child.expect([pexpect.EOF, pexpect.TIMEOUT, r"[^\r\n]+"], timeout=SUBMIT_TIMEOUT)
            if index == 0:  # EOF: append whatever preceded the EOF, finish
                if child.before:
                    lines.append(child.before)
                break
            if index == 1:  # TIMEOUT
                lines.append("(timed out waiting for the login result)")
                break
            line = child.match.group(0).rstrip()
            lines.append(line)
            low = line.lower()
            if any(word in low for word in SUCCESS_WORDS):
                ok = True
                break
            if any(word in low for word in FAILURE_WORDS):
                ok = False
                break
        text = " | ".join(part.strip() for part in lines if part.strip()) or "(no output)"
        return (ok, text)

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    async def cancel(self) -> None:
        """Close the child WITHOUT raising.

        KNOWN BUG (avoided): cancel must pass the actual child HANDLE into the
        closer — a closer invoked without the `child` argument raises.
        """
        child = self.child
        self.child = None
        if child is not None and not child.closed:
            try:
                child.close(force=True)
            except Exception:
                log.debug("Closing login child failed (ignored)", exc_info=True)

    def is_child_closed(self) -> bool:
        return self.child is None or self.child.closed


class LoginManager:
    """One pending login session at a time, with TTL auto-cancel."""

    def __init__(self, cli: OptimaiCLI, ttl_minutes: int = 3, alert_fn=None) -> None:
        self.cli = cli
        self.ttl_seconds = max(60, int(ttl_minutes) * 60)
        self._alert_fn = alert_fn
        self._session: LoginSession | None = None
        self._ttl_task: asyncio.Task | None = None

    @property
    def has_pending(self) -> bool:
        return (
            self._session is not None
            and self._session.child is not None
            and not self._session.child.closed
        )

    async def start(self) -> str | None:
        """Start a session and return the login URL. When a session is
        already pending, return the SAME url (no duplicate CLI processes)."""
        if self.has_pending:
            session = self._session
            assert session is not None
            if session.url:
                return session.url

        await self.cancel(silent=True)
        session = LoginSession(self.cli)
        url = await session.wait_for_url()
        if url is None:
            await session.cancel()
            return None
        self._session = session
        self._schedule_ttl()
        return url

    # ------------------------------------------------------------------

    def _schedule_ttl(self) -> None:
        if self._ttl_task is not None:
            self._ttl_task.cancel()
        self._ttl_task = asyncio.create_task(self._expire())

    async def _expire(self) -> None:
        try:
            await asyncio.sleep(self.ttl_seconds)
        except asyncio.CancelledError:
            return
        self._ttl_task = None
        session = self._session
        self._session = None
        if session is not None:
            await session.cancel()
            if self._alert_fn is not None:
                try:
                    await self._alert_fn("⏳ The /login session expired. Send /login again.")
                except Exception:
                    log.exception("Login expiry alert failed")

    async def submit(self, text: str) -> tuple[bool, str]:
        if not self.has_pending:
            return (False, "No pending login session — send /login first.")
        session = self._session
        assert session is not None
        result = await session.submit(text)
        await self.cancel(silent=True)
        return result

    async def login_legacy(self, email: str, password: str) -> tuple[bool, str]:
        """Direct email/password login using `optimai-cli auth login --legacy`."""
        await self.cancel(silent=True)

        def _legacy() -> tuple[bool, str]:
            env = os.environ.copy()
            env["HOME"] = self.cli.home
            try:
                child = pexpect.spawn(
                    self.cli.binary,
                    ["auth", "login", "--legacy"],
                    env=env,
                    encoding="utf-8",
                    timeout=20,
                )
                child.expect(r"Email.*:", timeout=15)
                child.sendline(email.strip())
                child.expect(r"Password.*:", timeout=15)
                child.sendline(password.strip())

                lines: list[str] = []
                ok = False
                while True:
                    index = child.expect([pexpect.EOF, pexpect.TIMEOUT, r"[^\r\n]+"], timeout=20)
                    if index == 0:
                        if child.before:
                            lines.append(child.before)
                        break
                    if index == 1:
                        lines.append("(timed out waiting for response)")
                        break
                    line = child.match.group(0).rstrip()
                    lines.append(line)
                    low = line.lower()
                    if any(word in low for word in SUCCESS_WORDS):
                        ok = True
                        break
                    if any(word in low for word in FAILURE_WORDS):
                        ok = False
                        break
                child.close(force=True)
                msg = " | ".join(l.strip() for l in lines if l.strip()) or ("Logged in successfully." if ok else "Login failed.")
                return (ok, msg)
            except pexpect.ExceptionPexpect as exc:
                return (False, f"Legacy login error: {exc}")

        return await asyncio.to_thread(_legacy)

    async def cancel(self, silent: bool = False) -> bool:
        """Cancel the pending session (closes the pexpect child)."""
        session = self._session
        if self._ttl_task is not None:
            self._ttl_task.cancel()
            self._ttl_task = None
        self._session = None
        if session is not None:
            await session.cancel()
            return True
        return not silent and False

    async def shutdown(self) -> None:
        """Close any leftover login process (used in post_shutdown)."""
        if self._ttl_task is not None:
            self._ttl_task.cancel()
            self._ttl_task = None
        session = self._session
        self._session = None
        if session is not None:
            await session.cancel()
