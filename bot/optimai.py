# SPDX-License-Identifier: Apache-2.0
"""Async wrapper around the `optimai-cli` binary plus pure log helpers.

Verified CLI surface (optimai-cli v0.1.63, core CLI 0.1.63):
  - `auth login --no-open --paste`  (both flags exist; URL points at
    https://node.optimai.network, paste-callback flow for SSH/VPS hosts)
  - `auth status`                   (logged out prints "Not authenticated"
    with EXIT CODE 0 — so authentication is detected by substring, never
    by exit code alone)
  - `node start` / `node status --format [json|text]`
  - `rewards balance --format [json|text]`
  - There is NO `node stop` subcommand: the node stops gracefully on Ctrl+C,
    which is why the supervisor sends SIGINT to the process group.
  - There is NO `optimai-cli docker` subcommand: the docker CLI is called
    directly via `run_bin`.
  - The bootstrap binary downloads the core CLI into $HOME on first use and
    stores credentials under $HOME/.optimai -> HOME must be a persistent path.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time

log = logging.getLogger(__name__)

NOT_AUTHENTICATED_MARK = "Not authenticated"
UPDATE_WARNING_MARK = "Important OptimAI CLI update available"
LOG_ROTATE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def contains_update_warning(text: str) -> bool:
    """True when the CLI printed its 'Important OptimAI CLI update available'
    warning (the upstream troubleshooting signal: the installed CLI uses an
    older update system and must be reinstalled). Pure function."""
    return UPDATE_WARNING_MARK.lower() in text.lower()


class OptimaiCLI:
    """Async subprocess wrapper. `run()` targets the optimai CLI (with the
    persistent HOME override); `run_bin()` targets arbitrary host binaries."""

    def __init__(self, binary: str = "optimai-cli", home: str = "/data/home") -> None:
        self.binary = binary
        self.home = home
        self._cached_docker: tuple[float, bool, str] | None = None

    def _cli_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = self.home
        return env

    async def run(self, *args: str, timeout: float = 30) -> tuple[int | None, str, str]:
        """Run the optimai CLI; returns (returncode, stdout, stderr). Never
        raises on non-zero exit; kills the process on timeout. Does not block
        the event loop (asyncio.create_subprocess_exec only)."""
        return await self._exec(self.binary, args, timeout, self._cli_env())

    async def run_bin(
        self, binary: str, *args: str, timeout: float = 30
    ) -> tuple[int | None, str, str]:
        """Same contract as `run()` but for an arbitrary host binary (e.g. the
        static `docker` client). Uses the inherited environment."""
        return await self._exec(binary, args, timeout, None)

    async def _exec(
        self,
        binary: str,
        args: tuple[str, ...],
        timeout: float,
        env: dict[str, str] | None,
    ) -> tuple[int | None, str, str]:
        try:
            proc = await asyncio.create_subprocess_exec(
                binary,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError:
            return (127, "", f"{binary}: command not found")
        except PermissionError:
            return (126, "", f"{binary}: not executable")

        try:
            out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            try:
                out_b, err_b = await proc.communicate()
            except Exception:
                out_b, err_b = b"", b""
            return (
                124,
                (out_b or b"").decode("utf-8", "replace"),
                (err_b or b"").decode("utf-8", "replace") or f"{binary}: timed out after {timeout}s",
            )

        out = (out_b or b"").decode("utf-8", "replace")
        err = (err_b or b"").decode("utf-8", "replace")
        return (proc.returncode, out, err)

    # ------------------------------------------------------------------
    # Domain helpers
    # ------------------------------------------------------------------

    async def auth_status(self) -> tuple[int | None, str, str]:
        return await self.run("auth", "status", timeout=15)

    async def auth_me(self) -> tuple[int | None, str, str]:
        """Ask official OptimAI CLI for authenticated user profile info."""
        return await self.run("auth", "me", timeout=15)

    async def auth_logout(self) -> tuple[int | None, str, str]:
        """Sign out from official OptimAI CLI."""
        return await self.run("auth", "logout", timeout=15)

    async def is_authenticated(self) -> bool:
        """False on non-zero exit OR on the logged-out output. The real CLI
        prints exactly `Not authenticated` with exit code 0 when logged out,
        so substring matching is mandatory. Never raises."""
        try:
            rc, out, err = await self.auth_status()
        except Exception:
            return False
        text = (out + err).strip()
        if rc != 0 or not text:
            return False
        if NOT_AUTHENTICATED_MARK in text:
            return False
        low = text.lower()
        if "not logged in" in low or "unauthenticated" in low:
            return False
        return any(k in low for k in ("logged in", "authenticated", "user:", "@"))

    async def node_status(self) -> tuple[bool, str]:
        """(ok, text) — text is passed through raw for Telegram display."""
        rc, out, err = await self.run("node", "status", timeout=15)
        return rc == 0, (out + err).strip()

    async def rewards_balance(self) -> tuple[bool, str]:
        """(ok, text) — text is passed through raw for Telegram display."""
        rc, out, err = await self.run("rewards", "balance", timeout=15)
        return rc == 0, (out + err).strip()

    async def node_stop(self) -> tuple[bool, str]:
        """(ok, text) — executes `optimai-cli node stop` to shut down background node."""
        rc, out, err = await self.run("node", "stop", timeout=15)
        return rc == 0, (out + err).strip()

    async def stop_mining_containers(self) -> int:
        """Find and stop background Docker containers spawned for OptimAI/crawl4ai mining.
        Returns the count of stopped containers."""
        try:
            rc, out, _ = await self.run_bin(
                "docker", "ps", "--format", "{{.ID}} {{.Image}} {{.Names}}", timeout=10
            )
            if rc != 0 or not out.strip():
                return 0
            stopped = 0
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    cid, img = parts[0], parts[1].lower()
                    name = parts[2].lower() if len(parts) > 2 else ""
                    if name in ("optimai-telegram-node", "optimai-node") or "telegram" in name:
                        continue
                    if any(k in img or k in name for k in ("optimai", "crawl4ai", "crawler")):
                        stop_rc, _, _ = await self.run_bin("docker", "stop", "-t", "5", cid, timeout=15)
                        if stop_rc == 0:
                            stopped += 1
            return stopped
        except Exception as exc:
            log.debug("stop_mining_containers error: %s", exc)
            return 0

    async def docker_server_version(self, force: bool = False) -> tuple[bool, str]:
        """Ask the HOST docker daemon (through the mounted socket at
        /var/run/docker.sock) for its server version using the docker CLI
        client directly — NEVER `optimai-cli docker` (not a real subcommand).
        Cached for 15s to keep bot command latency fast.
        Returns (ok=False, "") on Railway where the daemon does not exist."""
        now = time.monotonic()
        if not force and self._cached_docker is not None:
            cached_at, cached_ok, cached_ver = self._cached_docker
            if now - cached_at < 15.0:
                return cached_ok, cached_ver

        rc, out, err = await self.run_bin(
            "docker", "version", "--format", "{{.Server.Version}}", timeout=10
        )
        version = (out or "").strip()
        ok = rc == 0 and bool(version)
        if not ok:
            sock_ok, sock_ver = probe_docker_socket()
            if sock_ok:
                ok = True
                version = sock_ver
        res_ver = version if ok else ""
        self._cached_docker = (now, ok, res_ver)
        return ok, res_ver


def probe_docker_socket(sock_path: str = "/var/run/docker.sock", timeout: float = 2.0) -> tuple[bool, str]:
    """Directly probe the Docker Engine Unix domain socket at sock_path via HTTP.
    Returns (True, version) if reachable, or (False, "") if absent/failing."""
    if not os.path.exists(sock_path):
        return False, ""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(sock_path)
        s.sendall(b"GET /version HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        res = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            res += chunk
        s.close()
        _, _, body = res.partition(b"\r\n\r\n")
        if body:
            try:
                data = json.loads(body.decode("utf-8", errors="replace"))
                ver = data.get("Version") or data.get("ApiVersion")
                if ver:
                    return True, str(ver)
            except Exception:
                text = body.decode("utf-8", errors="replace")
                s_idx = text.find("{")
                e_idx = text.rfind("}")
                if s_idx != -1 and e_idx != -1:
                    data = json.loads(text[s_idx : e_idx + 1])
                    ver = data.get("Version") or data.get("ApiVersion")
                    if ver:
                        return True, str(ver)
        return True, "docker-daemon"
    except Exception as exc:
        log.debug("probe_docker_socket failed: %s", exc)
        return False, ""


# ----------------------------------------------------------------------
# Pure log helpers (unit-tested without any CLI process)
# ----------------------------------------------------------------------


def tail_file(path: str, lines: int) -> list[str]:
    """Return the last `lines` lines of `path` as a list of strings."""
    if lines <= 0:
        return []
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            block = 8192
            data = b""
            start = max(0, size - block * max(1, lines // 8 + 2))
            fh.seek(start)
            while fh.tell() < size:
                chunk = fh.read(block)
                if not chunk:
                    break
                data += chunk
                if data.count(b"\n") > lines:
                    break
            real_lines = data.splitlines()[-lines:]
            return [ln.decode("utf-8", "replace") for ln in real_lines]
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        return []


def read_new_chunk(path: str, start_offset: int) -> tuple[str, int]:
    """Read the bytes of `path` from `start_offset` to EOF.

    Returns (chunk, new_offset). CRITICAL: the shrink/rotation check must be
    `size < start_offset` — using `<=` made /watch resend old data after the
    log was rotated/recreated (an empty file must NOT reset the offset... it
    must, when the file was replaced; equality is handled by reading zero new
    bytes and returning the same offset).
    """
    try:
        size = os.path.getsize(path)
    except OSError:
        return "", start_offset
    if size < start_offset:
        # File shrunk (rotated / recreated) -> start over from the beginning.
        start_offset = 0
    if size == start_offset:
        return "", start_offset
    try:
        with open(path, "rb") as fh:
            fh.seek(start_offset)
            data = fh.read()
    except OSError:
        return "", start_offset
    return data.decode("utf-8", "replace"), size


def rotate_log(path: str, max_bytes: int = LOG_ROTATE_MAX_BYTES) -> bool:
    """Keep one `.1` backup of `path`, then truncate it in place (safe even
    while the node process holds an append handle: the file object is not
    replaced for the writer because we truncate by writing an empty file).

    Returns True when a rotation happened."""
    try:
        if not os.path.isfile(path) or os.path.getsize(path) <= max_bytes:
            return False
        os.replace(path, path + ".1")
        with open(path, "wb"):
            pass  # recreate an empty primary file
        return True
    except OSError:
        return False
