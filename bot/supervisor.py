# SPDX-License-Identifier: Apache-2.0
"""Desired-state supervisor: the 24/7 engine of the node.

Design:
  - `state.json` (`{"desired": "running"|"stopped"}`) is persisted FIRST in
    every transition, so a stop by the user survives reboots, and a running
    node auto-resumes on boot (when authenticated and NODE_AUTO_START=true).
  - The `optimai-cli node start` process is spawned with its own process
    group (`start_new_session=True`), stdout+stderr appended to node.log.
    There is no `node stop` subcommand: stop = SIGINT to the process GROUP
    (`os.killpg`), 10 s grace, then SIGKILL escalation.
  - Watch loop (5 s tick): dead process while desired=running -> crash ->
    Telegram alert (injected `alert_fn`, MUST be wired from main.py) with
    the last ~15 log lines, scheduled restart with backoff 5s->15s->60s->300s.
  - `_restart_scheduled` guard prevents the double-spawn race between the
    tick loop and the pending backoff timer.
  - Circuit breaker: 5 consecutive crashes -> auto-restart paused with ONE
    alert; `/start_node` (and `/restart_node`) close it.

`stop_loop()` only cancels the watch task — it must NOT kill the node
process (bot shutdown is not a node stop; the container shutdown kills
everything and the persisted desired-state resumes it on the next boot).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
import urllib.error
import urllib.request
from typing import Awaitable, Callable

from .optimai import OptimaiCLI, contains_update_warning, tail_file

log = logging.getLogger(__name__)

BACKOFF_SCHEDULE = [5, 15, 60, 300]  # seconds between crash restarts
CRASH_LIMIT = 5               # consecutive crashes -> circuit breaker opens
WATCH_TICK_SECONDS = 5
STOP_GRACE_SECONDS = 10
HEALTHY_RESET_SECONDS = 120   # a run that lasts this long resets crash counters
CRASH_TAIL_LINES = 15

AlertFn = Callable[[str], "Awaitable[None] | None"]



def breakdown_uptime(seconds: int) -> dict[str, int]:
    """Break down seconds into days, hours, minutes, and seconds."""
    if seconds < 0:
        return {"days": 0, "hours": 0, "minutes": 0, "seconds": 0}
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return {"days": days, "hours": hours, "minutes": minutes, "seconds": secs}

def fmt_uptime(seconds: float | None) -> str:
    """Human uptime like `3h 12m` / `2d 4h` / `45s`."""
    if seconds is None or seconds < 0:
        return "-"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    hours = minutes // 60
    if hours == 0:
        return f"{minutes}m"
    if hours < 48:
        return f"{hours}h {minutes % 60}m"
    days = hours // 24
    return f"{days}d {hours % 24}h"


class Supervisor:
    def __init__(
        self,
        cli: OptimaiCLI,
        data_dir: str,
        state_path: str,
        log_path: str,
        alert_fn: AlertFn | None = None,
    ) -> None:
        self.cli = cli
        self.data_dir = data_dir
        self._state_path = state_path
        self._log_path = log_path
        self._alert_fn = alert_fn

        self.desired: str = self._load_desired()
        self._proc: asyncio.subprocess.Process | None = None
        self._started_at: float | None = None
        self._last_exit_code: int | None = None

        self._consecutive_crashes = 0
        self._last_crash_at: float | None = None
        self._backoff_level = 0
        self._breaker_open = False
        self._restart_scheduled = False
        self._restart_task: asyncio.Task | None = None
        self._watch_task: asyncio.Task | None = None
        self._internet_online = True
        self._last_net_check = time.monotonic()

        # Latest platform health, refreshed by main.py (kept for /status).
        self._authenticated = False
        self._docker_ok = True

    # ------------------------------------------------------------------
    # Desired-state persistence (atomic write)
    # ------------------------------------------------------------------

    
    def reset_crashes_if_stable(self, stable_window_seconds: int = 600) -> bool:
        """Reset crash counter if process has run continuously past the stable window."""
        if self.running and self._started_at:
            if (asyncio.get_running_loop().time() - self._started_at) >= stable_window_seconds:
                if self._consecutive_crashes > 0:
                    self._consecutive_crashes = 0
                    self._backoff_level = 0
                    return True
        return False

    async def check_and_apply_update(self) -> bool:
        """Check for updates or update signal in node log; if detected, update binary and restart."""
        try:
            tail = tail_file(self._log_path, 30)
            has_warning = contains_update_warning("\n".join(tail))

            rc, out, err = await self.cli.run("update", timeout=30)
            up_text = (out + "\n" + err).lower()
            needs_update = (
                has_warning
                or "update available" in up_text
                or "downloading" in up_text
                or "updated" in up_text
            )

            if needs_update:
                await self._alert(
                    "🔄 <b>OptimAI CLI Update Detected:</b> Downloading latest binary and auto-restarting node..."
                )
                from bot.compatibility import download_compatible_cli
                download_compatible_cli(self.cli.binary)
                await self.restart()
                await self._alert(
                    f"✅ <b>Node Auto-Restarted:</b> Successfully updated to the latest OptimAI CLI (PID {self._pid()})."
                )
                return True
        except Exception as exc:
            log.warning("Auto-update check failed: %s", exc)
        return False

    
    def get_uptime_seconds(self) -> int:
        """Return the current running duration in integer seconds."""
        if not self.running or self._started_at is None:
            return 0
        try:
            return max(0, int(asyncio.get_running_loop().time() - self._started_at))
        except RuntimeError:
            return 0

    
    def get_crash_limit(self) -> int:
        """Return the circuit breaker consecutive crash threshold."""
        return CRASH_LIMIT

    
    def format_summary(self) -> str:
        """Return a single-line summary of supervisor state."""
        return f"desired={self.desired} running={self.running} crashes={self._consecutive_crashes}"

    
    def get_consecutive_crashes(self) -> int:
        """Return the number of consecutive crashes since last reset."""
        return self._consecutive_crashes

    
    def get_backoff_level(self) -> int:
        """Return the current exponential backoff level index."""
        return self._backoff_level

    def _load_desired(self) -> str:
        try:
            with open(self._state_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            desired = data.get("desired")
            return desired if desired in ("running", "stopped") else "stopped"
        except (OSError, ValueError, AttributeError):
            return "stopped"

    def _save_desired(self) -> None:
        tmp = self._state_path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"desired": self.desired}, fh)
            os.replace(tmp, self._state_path)
        except OSError as exc:  # persistence must never crash the bot
            log.error("Cannot persist state.json: %s", exc)

    # ------------------------------------------------------------------
    # Lifecycle control
    # ------------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def request_start(self) -> int | None:
        """Set desired=running FIRST (persist), then spawn the node process.
        Returns the PID (existing one when already running)."""
        self.desired = "running"
        self._save_desired()

        if self.running:
            return self._proc.pid  # type: ignore[union-attr]

        if self._restart_task is not None:
            self._restart_task.cancel()
            self._restart_task = None
        self._restart_scheduled = False

        await self._spawn()
        return self._pid()

    def _pid(self) -> int | None:
        if self._proc is not None and self._proc.returncode is None:
            return self._proc.pid
        return None

    async def _spawn(self) -> None:
        env = self.cli._cli_env()
        env["PYTHONUNBUFFERED"] = "1"
        try:
            log_file = open(self._log_path, "ab")
            log_file.write(
                f"\n=== node start requested at {time.strftime('%Y-%m-%d %H:%M:%S %Z')} ===\n".encode()
            )
            log_file.flush()
            proc = await asyncio.create_subprocess_exec(
                self.cli.binary,
                "node",
                "start",
                stdout=log_file,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                start_new_session=True,  # own process group -> group SIGINT
            )
        except FileNotFoundError:
            log.error("OPTIMAI_BIN %r not found; node cannot start", self.cli.binary)
            await self._alert(
                f"Cannot start node: binary {self.cli.binary!r} not found. "
                "Fix OPTIMAI_BIN in .env."
            )
            return
        finally:
            # the file handle belongs to the child after exec; close our copy
            try:
                log_file.close()  # type: ignore[possibly-undefined]
            except UnboundLocalError:
                pass

        self._proc = proc
        self._started_at = time.monotonic()
        log.info("Node process spawned (pid=%s)", proc.pid)

    async def check_network_connectivity(self) -> bool:
        """Lightweight connectivity check to verify outbound internet reachability."""
        def _ping() -> bool:
            try:
                req = urllib.request.Request(
                    "https://node.optimai.network",
                    headers={"User-Agent": "OptimAI-Supervisor/1.3.0"},
                )
                with urllib.request.urlopen(req, timeout=5):
                    return True
            except urllib.error.HTTPError:
                return True
            except Exception:
                return False

        return await asyncio.to_thread(_ping)

    async def request_stop(self) -> None:
        """PERSISTENT stop: desired=stopped FIRST, signal node stop, SIGINT to the process
        group (graceful shutdown), SIGKILL escalation, and terminate background mining containers."""
        self.desired = "stopped"
        self._save_desired()

        # A pending backoff restart must not fire after an explicit stop.
        if self._restart_task is not None:
            self._restart_task.cancel()
            self._restart_task = None
        self._restart_scheduled = False

        # 1. Gracefully notify official CLI to stop node
        try:
            await self.cli.node_stop()
        except Exception as exc:
            log.debug("optimai-cli node stop error: %s", exc)

        proc = self._proc
        if proc is not None and proc.returncode is None:
            try:
                os.killpg(proc.pid, signal.SIGINT)
            except ProcessLookupError:
                pass

            try:
                await asyncio.wait_for(proc.wait(), timeout=STOP_GRACE_SECONDS)
            except asyncio.TimeoutError:
                log.warning("Node ignored SIGINT for %ss; escalating to SIGKILL", STOP_GRACE_SECONDS)
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(proc.wait(), timeout=15)
                except asyncio.TimeoutError:
                    log.error("Node process %s refused to die", proc.pid)

            self._last_exit_code = proc.returncode
            self._started_at = None
            self._proc = None
            log.info("Node process stopped (exit=%s)", self._last_exit_code)

        # 2. Stop any background Docker mining workloads/containers spawned by the node
        try:
            stopped = await self.cli.stop_mining_containers()
            if stopped:
                log.info("Stopped %d background Docker mining container(s)", stopped)
        except Exception as exc:
            log.debug("stop_mining_containers error: %s", exc)

    async def restart(self) -> int | None:
        await self.request_stop()
        return await self.request_start()

    def close_breaker(self) -> None:
        self._breaker_open = False
        self._consecutive_crashes = 0
        self._backoff_level = 0

    # ------------------------------------------------------------------
    # Watch loop (crash detection + backoff restarts + breaker)
    # ------------------------------------------------------------------

    async def start_loop(self) -> None:
        if self._watch_task is None or self._watch_task.done():
            self._watch_task = asyncio.create_task(self._watch_loop())

    async def stop_loop(self) -> None:
        """Cancel the watch task ONLY — never touches the node process."""
        if self._watch_task is not None:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None
        if self._restart_task is not None:
            self._restart_task.cancel()
            self._restart_task = None
            self._restart_scheduled = False

    async def _watch_loop(self) -> None:
        while True:
            await asyncio.sleep(WATCH_TICK_SECONDS)
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # the loop must survive anything
                log.exception("Supervisor tick failed: %s", exc)

    async def _tick(self) -> None:
        proc = self._proc

        now = time.monotonic()
        if now - self._last_net_check >= 45.0:
            self._last_net_check = now
            online = await self.check_network_connectivity()
            if not self._internet_online and online:
                self._internet_online = True
                await self._alert(
                    "🌐 <b>Internet Restored!</b>\n"
                    "Network connectivity to the OptimAI Network has been re-established. "
                    "Mining node background workloads have resumed."
                )
            elif self._internet_online and not online:
                self._internet_online = False
                log.warning("Outbound network connectivity lost")

        # A run that stayed alive this long proves health -> reset counters.
        if (
            proc is not None
            and proc.returncode is None
            and self._started_at is not None
            and time.monotonic() - self._started_at >= HEALTHY_RESET_SECONDS
        ):
            self._consecutive_crashes = 0
            self._backoff_level = 0

        if self.desired != "running":
            # collect exit codes of finished processes for /status
            if proc is not None and proc.returncode is not None:
                self._last_exit_code = proc.returncode
                self._proc = None
                self._started_at = None
            return

        if proc is not None and proc.returncode is None:
            try:
                tail = tail_file(self._log_path, 15)
                if contains_update_warning("\n".join(tail)):
                    log.warning("Detected update warning in log; triggering auto-update...")
                    asyncio.create_task(self.check_and_apply_update())
            except Exception:
                pass
            return  # running as desired

        # ---- crash (or not yet spawned) ----
        if proc is None:
            # Desired running but nothing spawned: only the restart path
            # handles spawning — wait for the scheduled restart task.
            if self._restart_scheduled or self._breaker_open:
                return
            # bot restarted while node was "running": *no* boot-time spawn
            # happened (e.g. not authenticated at boot) -> do it here once
            # the health info says we can; harmless if process just stopped.
        else:
            self._last_exit_code = proc.returncode
            self._proc = None
            self._started_at = None
            await self._handle_crash()

    async def _handle_crash(self) -> None:
        self._consecutive_crashes += 1
        self._last_crash_at = time.time()
        tail = tail_file(self._log_path, CRASH_TAIL_LINES)
        tail_text = "\n".join(tail[-CRASH_TAIL_LINES:])
        log.warning(
            "Node crashed (exit=%s, consecutive=%s/%s)",
            self._last_exit_code,
            self._consecutive_crashes,
            CRASH_LIMIT,
        )

        if self._consecutive_crashes >= CRASH_LIMIT and not self._breaker_open:
            self._breaker_open = True
            await self._alert(
                "⛔️ Node keeps crashing — auto-restart paused (circuit breaker "
                "OPEN).\nFix the issue, then send /restart_node or /start_node.\n\n"
                f"Last exit code: {self._last_exit_code}"
            )
            return

        if self._breaker_open:
            return

        await self._alert(
            f"⚠️ Node crashed unexpectedly (exit code {self._last_exit_code}).\n"
            f"Restart scheduled in {BACKOFF_SCHEDULE[min(self._backoff_level, len(BACKOFF_SCHEDULE) - 1)]}s "
            f"(crash {self._consecutive_crashes}/{CRASH_LIMIT}).\n\n"
            f"<pre>{tail_text if tail_text else '(no log output)'}</pre>"
        )
        self._schedule_restart()

    def _schedule_restart(self) -> None:
        """
        KNOWN BUG GUARD: `_restart_scheduled` prevents the double-spawn race
        between the tick loop and the pending backoff timer — exactly ONE
        timer may be pending at any time.
        """
        if self._restart_scheduled or self._breaker_open or self.desired != "running":
            return
        self._restart_scheduled = True
        delay = BACKOFF_SCHEDULE[min(self._backoff_level, len(BACKOFF_SCHEDULE) - 1)]
        self._backoff_level += 1
        self._restart_task = asyncio.create_task(self._delayed_restart(delay))

    async def _delayed_restart(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            self._restart_scheduled = False
            raise
        self._restart_scheduled = False
        if self.desired == "running" and not self.running and not self._breaker_open:
            await self._spawn()

    # ------------------------------------------------------------------
    # Health + snapshot
    # ------------------------------------------------------------------

    def update_health(self, authenticated: bool, docker_ok: bool) -> None:
        self._authenticated = authenticated
        self._docker_ok = docker_ok

    def snapshot(self) -> dict:
        uptime = None
        if self._started_at is not None and self.running:
            uptime = time.monotonic() - self._started_at
        return {
            "desired": self.desired,
            "running": self.running,
            "pid": self._pid(),
            "uptime": fmt_uptime(uptime),
            "last_exit_code": self._last_exit_code if not self.running else 0,
            "crashes": self._consecutive_crashes,
            "last_crash_at": self._last_crash_at,
            "backoff_level": self._backoff_level,
            "breaker": "OPEN" if self._breaker_open else "CLOSED",
            "authenticated": self._authenticated,
            "docker_ok": self._docker_ok,
        }

    async def _alert(self, text: str) -> None:
        if self._alert_fn is None:
            log.warning("(no alert_fn wired) %s", text)
            return
        try:
            result = self._alert_fn(text)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            log.exception("alert_fn failed")
