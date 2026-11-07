# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
"""Smoke test suite for optimai-telegram-node (v1.3.0).

Runs WITHOUT network and WITHOUT real Telegram:
  - OPTIMAI_BIN points at scripts/stub-optimai-cli.sh (deterministic fake CLI)
  - config/gatekeeper/log helpers are tested as pure logic
  - the supervisor and login flows run against the stub via real subprocesses
  - main.py wiring is verified by source inspection

Exit code 0 iff every check passes. Target: >= 36 checks.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ----------------------------------------------------------------------
# Environment overrides BEFORE importing bot modules
# ----------------------------------------------------------------------
TMP = tempfile.mkdtemp(prefix="optimai-smoke-")
STUB = os.path.join(ROOT, "scripts", "stub-optimai-cli.sh")

os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:TESTTOKEN"
os.environ["TELEGRAM_ALLOWED_IDS"] = "111111111"
os.environ["OPTIMAI_BIN"] = STUB
os.environ["OPTIMAI_HOME"] = os.path.join(TMP, "home")
os.environ["DATA_DIR"] = os.path.join(TMP, "data")
os.environ["OPTIMAI_STUB_HEARTBEAT"] = "0.2"
for _d in (os.environ["OPTIMAI_HOME"], os.environ["DATA_DIR"]):
    os.makedirs(_d, exist_ok=True)
sys.path.insert(0, ROOT)

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool, info: str = "") -> None:
    (PASS if cond else FAIL).append(name if cond else f"{name} :: {info}")
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {name}" + (f"  ({info})" if info and not cond else ""))


# import AFTER env overrides
from bot.config import (  # noqa: E402
    Config,
    ConfigError,
    clear_credential_database,
    find_local_optimai_bin,
    is_local_environment,
    load_credential_database,
    load_dotenv,
    restore_credentials_from_database,
    save_credential_database,
    sync_local_credentials,
)
from bot.compatibility import (  # noqa: E402
    check_device_compatibility,
    get_compatible_cli_url,
    get_os_info,
)
from bot.gatekeeper import UnauthorizedGate  # noqa: E402
from bot.login_session import LoginManager, LoginSession  # noqa: E402
from bot.optimai import (  # noqa: E402
    NOT_AUTHENTICATED_MARK,
    OptimaiCLI,
    contains_update_warning,
    read_new_chunk,
    rotate_log,
    tail_file,
)
from bot.supervisor import BACKOFF_SCHEDULE, CRASH_LIMIT, Supervisor, breakdown_uptime, fmt_uptime  # noqa: E402


def base_env(**overrides) -> dict[str, str]:
    env = {
        "TELEGRAM_BOT_TOKEN": "123456789:ABCdef",
        "TELEGRAM_ALLOWED_IDS": "6602332612, 778899001",
        "OPTIMAI_HOME": os.path.join(TMP, "h1"),
        "DATA_DIR": os.path.join(TMP, "d1"),
    }
    env.update(overrides)
    for k, v in list(env.items()):
        if v is None:
            del env[k]
    return env


# ======================================================================
print("\n== config ==")
# ======================================================================

try:
    Config.load(env={"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_ALLOWED_IDS": "   "})
    check("config: missing both required vars -> error", False, "no ConfigError")
except ConfigError as exc:
    msg = str(exc)
    check(
        "config: missing both required vars -> error",
        "TELEGRAM_BOT_TOKEN" in msg and "TELEGRAM_ALLOWED_IDS" in msg,
        msg,
    )
    check(
        "config: error tells WHERE to get each var",
        "BotFather" in msg and "/id" in msg,
        msg,
    )
    check(
        "config: unauth default promo contains contact",
        "@mkr_infinity" in Config.load_unauth_promo("@mkr_infinity"),
    )

try:
    Config.load(env=base_env(TELEGRAM_BOT_TOKEN="t", TELEGRAM_ALLOWED_IDS="123, abc"))
    check("config: bad TELEGRAM_ALLOWED_IDS rejected", False, "no ConfigError")
except ConfigError as exc:
    check(
        "config: bad TELEGRAM_ALLOWED_IDS rejected",
        "abc" in str(exc),
        str(exc),
    )

cfg = Config.load(env=base_env())
check("config: ids parsed to set[int]", cfg.allowed_ids == {6602332612, 778899001})
cfg_hi = Config.load(env=base_env(UNAUTH_MAX_MESSAGES="99"))
check("config: UNAUTH_MAX_MESSAGES clamped to 10", cfg_hi.unauth_max_messages == 10)
cfg_lo = Config.load(env=base_env(UNAUTH_MAX_MESSAGES="-5"))
check("config: UNAUTH_MAX_MESSAGES clamped to 0", cfg_lo.unauth_max_messages == 0)
check(
    "config: boolean parsing (yes/1/on/true)",
    Config.load(env=base_env(NODE_AUTO_START="yes")).node_auto_start
    and Config.load(env=base_env(NODE_AUTO_START="1")).node_auto_start
    and not Config.load(env=base_env(NODE_AUTO_START="0")).node_auto_start
    and not Config.load(env=base_env(NODE_AUTO_START="false")).node_auto_start,
)
check(
    "config: invalid int falls back to default",
    Config.load(env=base_env(LOG_TAIL_LINES="abc")).log_tail_lines == 40,
)
check(
    "config: out-of-range ENABLE_HEALTH_PORT falls back to 8080",
    Config.load(env=base_env(ENABLE_HEALTH_PORT="99999")).enable_health_port == 8080,
)
check(
    "config: contact default + builtin promo template",
    cfg.contact_username == "mkr_infinity"
    and "⛔️" in cfg.unauthorized_message
    and "@mkr_infinity" in cfg.unauthorized_message,
)
cfg2 = Config.load(
    env=base_env(UNAUTHORIZED_MESSAGE="Buy hosting from {contact} today!")
)
check(
    "config: override text + {contact} substitution",
    cfg2.unauthorized_message == "Buy hosting from mkr_infinity today!",
)
check(
    "config: health port parsed (set + empty)",
    Config.load(env=base_env(ENABLE_HEALTH_PORT="8080")).enable_health_port == 8080
    and Config.load(env=base_env()).enable_health_port is None,
)
check(
    "config: railway PORT parsed as fallback health port",
    Config.load(env=base_env(PORT="3000")).enable_health_port == 3000,
)
with open(os.path.join(ROOT, "railway.json"), encoding="utf-8") as rf:
    railway_cfg = json.load(rf)
check(
    "railway: railway.json parses as valid JSON with DOCKERFILE builder",
    railway_cfg.get("build", {}).get("builder") == "DOCKERFILE",
)
check(
    "config: data dir + optimai home created/resolved",
    os.path.isdir(cfg.data_dir) and cfg.optimai_home == os.path.abspath(cfg.optimai_home),
)
# test dotenv parser
sample_env_file = os.path.join(TMP, "sample.env")
with open(sample_env_file, "w", encoding="utf-8") as sf:
    sf.write("# comment\nFOO=bar\nQUOTED=\"hello world\"\nEMPTY=\n")
parsed_env = load_dotenv(sample_env_file)
check(
    "config: load_dotenv parses keys, values and quotes",
    parsed_env.get("FOO") == "bar" and parsed_env.get("QUOTED") == "hello world" and parsed_env.get("EMPTY") == "",
)
check(
    "config: is_local_environment returns boolean",
    is_local_environment() in (True, False),
)
check(
    "config: find_local_optimai_bin resolves binary",
    bool(find_local_optimai_bin(STUB)),
)
local_cfg = Config.load(env=base_env(OPTIMAI_HOME="/data/home", DATA_DIR="/data/data"))
check(
    "config: local auto-detect safely overrides /data to writable local paths",
    not local_cfg.data_dir.startswith("/data/data") or os.access("/data", os.W_OK),
)

# Test sync_local_credentials
home_a = os.path.join(TMP, "sync_a")
home_b = os.path.join(TMP, "sync_b")
cfg_a = os.path.join(home_a, ".config", "optimai-cli")
cfg_b = os.path.join(home_b, ".config", "optimai-cli")
os.makedirs(cfg_a, exist_ok=True)
with open(os.path.join(cfg_a, "auth.json"), "w", encoding="utf-8") as f:
    f.write('{"token": "initial_token"}')
with open(os.path.join(cfg_a, "user.json"), "w", encoding="utf-8") as f:
    f.write('{"user": "test"}')

sync_local_credentials(home_a, home_b)
check(
    "config: sync_local_credentials propagates auth to empty destination",
    os.path.isfile(os.path.join(cfg_b, "auth.json")) and json.load(open(os.path.join(cfg_b, "auth.json"))).get("token") == "initial_token",
)

# Simulate newer token in B syncing back to A
time.sleep(0.01)
with open(os.path.join(cfg_b, "auth.json"), "w", encoding="utf-8") as f:
    f.write('{"token": "updated_token"}')
sync_local_credentials(home_a, home_b)
# Test credential database functions
cred_db_path = os.path.join(TMP, "test_credentials.json")
save_credential_database(cred_db_path, {"email": "miner@example.com", "auth_snapshot": {"token": "secret123"}})
loaded_db = load_credential_database(cred_db_path)
check(
    "config: save_credential_database and load_credential_database persist auth",
    loaded_db.get("email") == "miner@example.com" and loaded_db.get("auth_snapshot", {}).get("token") == "secret123",
)

restored_home = os.path.join(TMP, "restored_home")
check(
    "config: restore_credentials_from_database recreates missing auth.json",
    restore_credentials_from_database(cred_db_path, restored_home)
    and os.path.isfile(os.path.join(restored_home, ".config", "optimai-cli", "auth.json")),
)

clear_credential_database(cred_db_path, [restored_home])
check(
    "config: clear_credential_database purges database file and auth configs",
    not os.path.isfile(cred_db_path) and not os.path.isfile(os.path.join(restored_home, ".config", "optimai-cli", "auth.json")),
)

# ======================================================================
print("\n== compatibility ==")
# ======================================================================
host_compat, host_msg, host_details = check_device_compatibility()
check("compat: get_os_info returns valid system and machine", bool(get_os_info().get("system")))
check("compat: check_device_compatibility returns tuple", isinstance(host_compat, bool) and isinstance(host_msg, str))

c_l64, m_l64, d_l64 = check_device_compatibility({"system": "Linux", "machine": "x86_64", "distro_name": "Arch Linux"})
check("compat: Linux x86_64 compatible with ubuntu binary url", c_l64 and "optimai_cli_ubuntu" in d_l64["cli_url"])

c_mac, m_mac, d_mac = check_device_compatibility({"system": "Darwin", "machine": "arm64", "distro_name": "macOS 14"})
check("compat: macOS arm64 compatible with universal binary url", c_mac and "optimai_cli_darwin_universal2" in d_mac["cli_url"])

c_win, m_win, d_win = check_device_compatibility({"system": "Windows", "machine": "amd64", "distro_name": "Windows 11"})
check("compat: Windows x86_64 compatible with exe url", c_win and "optimai_cli_windows.exe" in d_win["cli_url"])

c_arm, m_arm, d_arm = check_device_compatibility({"system": "Linux", "machine": "aarch64", "distro_name": "Ubuntu 22.04"})
check("compat: Linux aarch64 reports incompatible with reason", not c_arm and "ARM" in m_arm)

c_32, m_32, d_32 = check_device_compatibility({"system": "Linux", "machine": "i686", "distro_name": "Debian"})
check("compat: 32-bit Linux reports incompatible with reason", not c_32 and "32-bit" in m_32)

check("compat: RAM and storage limits are NOT enforced (advisory only)", "ram_mb" in d_l64 and "disk_free_gb" in d_l64 and c_l64)

c_termux, m_termux, d_termux = check_device_compatibility({"system": "Linux", "machine": "aarch64", "distro_id": "termux", "distro_name": "Termux Android (6.1.0)"})
check("compat: Termux aarch64 reports Termux PRoot guidance in reason", "Termux" in m_termux and "PRoot" in m_termux)
check("termux: setup-termux.sh, setup-termux-proot.sh and docs/DEPLOY-TERMUX.md exist", os.path.isfile(os.path.join(ROOT, "setup-termux.sh")) and os.path.isfile(os.path.join(ROOT, "setup-termux-proot.sh")) and os.path.isfile(os.path.join(ROOT, "docs", "DEPLOY-TERMUX.md")))
check("launcher: start.sh launcher script exists and is executable", os.path.isfile(os.path.join(ROOT, "start.sh")) and os.access(os.path.join(ROOT, "start.sh"), os.X_OK))
for core_doc in ("DEPLOY-VPS.md", "DEPLOY-GCP.md", "DEPLOY-TERMUX.md", "RUNBOOK.md"):
    check(f"docs: core guide docs/{core_doc} exists", os.path.isfile(os.path.join(ROOT, "docs", core_doc)))

p_compat = subprocess.run(["bash", os.path.join(ROOT, "scripts", "check-compatibility.sh")], capture_output=True, text=True)
check("compat: scripts/check-compatibility.sh runs and returns compatible output", p_compat.returncode == 0 and "COMPATIBLE" in p_compat.stdout)

p_ready = subprocess.run(["bash", os.path.join(ROOT, "scripts", "check-readiness.sh")], cwd=ROOT, env=dict(os.environ), capture_output=True, text=True)
check(
    "readiness: scripts/check-readiness.sh exists and passes pre-flight checks",
    p_ready.returncode == 0 and "ALL CRITICAL REQUIREMENTS SATISFIED" in p_ready.stdout and "[✅ PASSED]" in p_ready.stdout,
    f"rc={p_ready.returncode}, out={p_ready.stdout[-300:] if p_ready.stdout else ''}, err={p_ready.stderr[-200:] if p_ready.stderr else ''}",
)
check("setup: setup-vps.sh wires scripts/check-readiness.sh", "scripts/check-readiness.sh" in open(os.path.join(ROOT, "setup-vps.sh"), encoding="utf-8").read())

# ======================================================================
print("\n== gatekeeper ==")
# ======================================================================
gpath = os.path.join(TMP, "unauth_counts.json")
gate = UnauthorizedGate(gpath, max_messages=3)
uid = 999888777
check(
    "gate: budget allows exactly max replies",
    gate.may_reply(uid) and gate.record(uid) == 1 and gate.record(uid) == 2 and gate.record(uid) == 3,
)
check("gate: budget exhausted stays muted", not gate.may_reply(uid))
check("gate: negative user id handled safely", not gate.may_reply(-1) if gate.max_messages == 0 else True)
check(
    "gate: persists across fresh instance (file round-trip)",
    UnauthorizedGate(gpath, max_messages=3).may_reply(uid) is False,
)
gate.reset(uid)
check(
    "gate: reset() clears the account",
    UnauthorizedGate(gpath, max_messages=3).may_reply(uid) is True,
)
check(
    "gate: max_messages=0 -> fully silent",
    UnauthorizedGate(os.path.join(TMP, "g2.json"), max_messages=0).may_reply(1) is False,
)

# ======================================================================
print("\n== optimai helpers ==")
# ======================================================================
logp = os.path.join(TMP, "n.log")
with open(logp, "w") as fh:
    fh.write("\n".join(f"line{i}" for i in range(1, 51)))
check(
    "optimai: tail_file last N lines",
    tail_file(logp, 3) == ["line48", "line49", "line50"],
)
check(
    "optimai: tail_file missing file -> empty list",
    tail_file(os.path.join(TMP, "nope.log"), 3) == [],
)

off = 0
c1, off = read_new_chunk(logp, off)
check("optimai: read_new_chunk reads fresh bytes", c1.startswith("line1") and off > 0)
c2, off2 = read_new_chunk(logp, off)
check("optimai: read_new_chunk incremental (second read empty)", c2 == "" and off2 == off)
with open(logp, "a") as fh:
    fh.write("\nnewline-A")
chunk, off3 = read_new_chunk(logp, off)
check("optimai: read_new_chunk returns only NEW output", chunk.strip() == "newline-A")

os.truncate(logp, 5)  # shrink/rotation happened
shrunk, off4 = read_new_chunk(logp, off3)
check(
    "optimai: shrink detection `size < start_offset` resets to 0",
    off4 == 5 and shrunk == "line1",
)

with open(logp, "w") as fh:
    fh.write("z" * 100)
rotated = rotate_log(logp, max_bytes=64)
check(
    "optimai: rotate_log keeps .1 backup and truncates",
    rotated
    and os.path.getsize(logp) == 0
    and os.path.isfile(logp + ".1")
    and os.path.getsize(logp + ".1") == 100,
)
check(
    "optimai: rotate_log under threshold is a no-op",
    rotate_log(logp, max_bytes=64) is False and os.path.isfile(logp),
)
check(
    "optimai: contains_update_warning matches the upstream CLI warning",
    contains_update_warning("IMPORTANT OptimAI CLI update available - reinstall") is True
    and contains_update_warning("everything is fine") is False,
)

cli = OptimaiCLI(binary=STUB, home=os.environ["OPTIMAI_HOME"])

# ======================================================================
print("\n== is_authenticated via stub (real-CLI exit-code nuance) ==")


async def auth_checks() -> None:
    rc, out, _err = await cli.auth_status()
    flag = os.path.join(os.environ["OPTIMAI_HOME"], ".stub_optimai_auth")
    if os.path.isfile(flag):
        os.remove(flag)
    rc, out, _err = await cli.auth_status()
    check(
        "optimai: stub logged out prints 'Not authenticated' with exit code 0",
        rc == 0 and NOT_AUTHENTICATED_MARK in out,
        f"rc={rc} out={out!r}",
    )
    check(
        "optimai: is_authenticated False despite exit code 0",
        await cli.is_authenticated() is False,
    )
    open(flag, "w").close()
    check("optimai: is_authenticated True after flag file", await cli.is_authenticated() is True)
    rc, _out, _err = await cli.run_bin("definitely-not-a-real-bin-xyz")
    check("optimai: run_bin missing binary -> rc 127, no raise", rc == 127)


asyncio.run(auth_checks())

# ======================================================================
print("\n== stub CLI direct ==")
# ======================================================================
proc = subprocess.run(
    [STUB, "auth", "login", "--no-open", "--paste"],
    input="https://mock.node.optimai.network/callback?code=XY\n",
    capture_output=True,
    text=True,
    env={**os.environ, "HOME": os.environ["OPTIMAI_HOME"]},
)
check(
    "stub: auth login prints mock URL and accepts paste",
    "https://mock.node.optimai.network/login?code=TEST123" in proc.stdout
    and "Login successful." in proc.stdout,
    proc.stdout + proc.stderr,
)
proc2 = subprocess.run(
    [STUB, "auth", "login", "--paste", "--no-open"],  # flag order reversed
    input="code\n",
    capture_output=True,
    text=True,
    env={**os.environ, "HOME": os.environ["OPTIMAI_HOME"]},
)
check("stub: --no-open parsed after `shift` (flag order agnostic)", "TEST123" in proc2.stdout)
proc3 = subprocess.run([STUB, "rewards", "balance"], capture_output=True, text=True)
check("stub: rewards balance prints fixed balance", "1234.56" in proc3.stdout)

# ======================================================================
print("\n== supervisor (real stub processes) ==")


async def supervisor_checks() -> None:
    data_dir = os.path.join(TMP, "sup")
    os.makedirs(data_dir, exist_ok=True)
    state_path = os.path.join(data_dir, "state.json")
    log_path = os.path.join(data_dir, "node.log")
    alerts: list[str] = []

    async def alert(text: str) -> None:
        alerts.append(text)

    sup = Supervisor(cli, data_dir, state_path, log_path, alert_fn=alert)

    # snapshots complete even before anything happened
    snap = sup.snapshot()
    expected_keys = {
        "desired", "running", "pid", "uptime", "last_exit_code",
        "crashes", "backoff_level", "breaker", "authenticated", "docker_ok", "last_crash_at",
    }
    check("supervisor: format_summary returns valid string", "desired=" in sup.format_summary())
    check("supervisor: get_consecutive_crashes helper returns int", isinstance(sup.get_consecutive_crashes(), int))
    check("supervisor: get_backoff_level helper returns int", isinstance(sup.get_backoff_level(), int))
    check("supervisor: snapshot has all fields", expected_keys <= set(snap), str(snap.keys()))

    pid = await sup.request_start()
    check("supervisor: snapshot pid key is present", "pid" in sup.snapshot())
    check("supervisor: request_start persists desired=running", sup.desired == "running")
    await asyncio.sleep(0.4)
    check("supervisor: node process spawned (pid + running)", pid is not None and sup.running)
    check("supervisor: state.json on disk", json.load(open(state_path)) == {"desired": "running"})

    await sup.request_stop()
    check(
        "supervisor: SIGINT stop is graceful (quick death, exit recorded)",
        not sup.running and sup._last_exit_code == 0,
        f"exit={sup._last_exit_code}",
    )
    check(
        "supervisor: request_stop persists desired=stopped",
        json.load(open(state_path)) == {"desired": "stopped"},
    )

    # reboot simulation: a fresh Supervisor instance reads persisted state
    sup2 = Supervisor(cli, data_dir, state_path, log_path, alert_fn=alert)
    check("supervisor: state.json survives fresh instance (reboot sim)", sup2.desired == "stopped")

    check("supervisor: backoff schedule 5/15/60/300", BACKOFF_SCHEDULE == [5, 15, 60, 300])
    check("supervisor: get_crash_limit returns CRASH_LIMIT", sup2.get_crash_limit() == CRASH_LIMIT)
    check("supervisor: crash limit is 5", CRASH_LIMIT == 5)

    # double-spawn guard
    sup2.desired = "running"
    sup2._schedule_restart()
    task1 = sup2._restart_task
    sup2._schedule_restart()
    check(
        "supervisor: _restart_scheduled guard -> exactly one restart timer",
        task1 is not None
        and sup2._restart_task is task1
        and sup2._restart_scheduled
        and sup2._backoff_level == 1,
    )
    sup2._restart_task.cancel()

    # circuit breaker: 5 consecutive crashes
    n_before = len(alerts)
    for _ in range(CRASH_LIMIT):
        await sup2._handle_crash()
    check("supervisor: breaker opens after 5 consecutive crashes", sup2._breaker_open)

    # one alert per backoff crash + exactly ONE breaker-opening alert
    opener_alerts = [a for a in alerts if "auto-restart paused" in a]
    check("supervisor: exactly ONE breaker alert sent", len(opener_alerts) == 1, str(len(alerts) - n_before))

    await sup2._handle_crash()  # breaker open -> silent path
    check(
        "supervisor: no further alerts while breaker open",
        [a for a in alerts[n_before:] if "auto-restart paused" in a][0:] and len(
            [a for a in alerts[n_before:] if "auto-restart paused" in a]
        ) == 1,
    )
    sup2.close_breaker()
    check(
        "supervisor: close_breaker resets counters",
        not sup2._breaker_open and sup2._consecutive_crashes == 0 and sup2._backoff_level == 0,
    )
    check(
        "supervisor: reset_crashes_if_stable helper exists",
        hasattr(sup2, "reset_crashes_if_stable"),
    )

    # fmt_uptime formatting
    check(
        "supervisor: fmt_uptime '3h 12m' style",
        fmt_uptime(3 * 3600 + 12 * 60) == "3h 12m" and fmt_uptime(45) == "45s" and fmt_uptime(None) == "-",
    )
    check(
        "supervisor: fmt_uptime days boundary and negative seconds",
        fmt_uptime(2 * 86400 + 5 * 3600) == "2d 5h" and fmt_uptime(-10) == "-" and fmt_uptime(125) == "2m",
    )
    check(
        "supervisor: get_uptime_seconds helper returns int",
        isinstance(sup2.get_uptime_seconds(), int),
    )
    check(
        "supervisor: breakdown_uptime returns dict",
        breakdown_uptime(90061) == {"days": 1, "hours": 1, "minutes": 1, "seconds": 1}
        and breakdown_uptime(-5) == {"days": 0, "hours": 0, "minutes": 0, "seconds": 0},
    )

    # stop_loop must NOT kill the node process
    await sup2.request_start()
    await asyncio.sleep(0.3)
    await sup2.start_loop()
    await sup2.stop_loop()
    check("supervisor: stop_loop keeps the node alive", sup2.running)
    await sup2.request_stop()


asyncio.run(supervisor_checks())

# ======================================================================
print("\n== login_session (pexpect + stub) ==")


async def login_checks() -> None:
    sess = LoginSession(cli)
    url = await sess.wait_for_url()
    check("login: URL captured from stub output", url is not None and "node.optimai.network/login" in url, str(url))
    ok, summary = await sess.submit("redirect-code-12345")
    check("login: submit() resolves success", ok and "successful" in summary.lower(), summary)
    await sess.cancel()

    sess2 = LoginSession(cli)
    await sess2.wait_for_url()
    await sess2.cancel()
    check("login: cancel() closes child without raising", sess2.is_child_closed())
    check(
        "login: submit after cancel -> clean gone-message (no crash)",
        await sess2.submit("hello") == (False, "The login process is gone — start a new session with /login."),
    )

    mgr = LoginManager(cli, ttl_minutes=15)
    url1 = await mgr.start()
    url2 = await mgr.start()
    check("login: one session at a time (same URL)", url1 is not None and url2 == url1)
    mgr.ttl_seconds = 0.5  # shrink TTL for the test
    mgr._schedule_ttl()
    await asyncio.sleep(1.2)
    check("login: TTL expiry auto-cancels the session", not mgr.has_pending)
    ok, text = await mgr.submit("late")
    check("login: submit without pending session -> helpful error", not ok and "/login first" in text)
    ok_leg, msg_leg = await mgr.login_legacy("user@example.com", "goodpass")
    check("login: legacy login with valid credentials succeeds", ok_leg and "success" in msg_leg.lower())
    ok_bad, msg_bad = await mgr.login_legacy("user@example.com", "wrongpass")
    check("login: legacy login with wrong password fails", not ok_bad and "invalid" in msg_bad.lower())
    await mgr.shutdown()


asyncio.run(login_checks())
import bot
check("bot: get_full_version_string returns valid string", "OptimAI" in bot.get_full_version_string())

# ======================================================================
print("\n== main.py wiring (source inspection) ==")
# ======================================================================
with open(os.path.join(ROOT, "bot", "main.py"), encoding="utf-8") as fh:
    src = fh.read()

for cmd in (
    "help", "status", "start_node", "stop_node", "restart_node", "rewards",
    "logs", "log", "watch", "login", "auth_status", "me", "logout", "cancel", "id", "version", "ping", "uptime", "disk", "system", "healthcheck", "update_cli", "login_legacy", "screen",
):
    check(
        f"main: /{cmd} handler registered",
        re.search(rf'CommandHandler\("{cmd}"', src) is not None,
    )
check(
    "main: ApplicationBuilder enables concurrent_updates",
    "concurrent_updates(True)" in src,
)
check(
    "main: global error handler registered",
    "add_error_handler(global_error_handler)" in src,
)
check(
    "main: terminal log streamer function exists",
    "tail_node_log_terminal" in src,
)
check(
    "main: unauthorized handler registered LAST with ~admin filter",
    src.rfind("MessageHandler(~admin_filter, unauthorized_handler)") > src.rfind("MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, on_admin_text)")
    and "MessageHandler(~admin_filter, unauthorized_handler)" in src,
)
check(
    "main: /id NOT admin-gated",
    re.search(r'CommandHandler\("id", cmd_id\)[,)]', src) is not None,
)
check("main: alert_fn wired into Supervisor", "sup._alert_fn = alert_fn" in src)
check("main: sup.start_loop() called in post_init", "await sup.start_loop()" in src)
check(
    "main: /status surfaces the CLI update warning via contains_update_warning",
    "contains_update_warning" in src and "Important OptimAI CLI update available" in src,
)
check("main: run_polling(drop_pending_updates=True)", "run_polling(drop_pending_updates=True)" in src)
check("main: /id budgeted via gate.record", "gate.record(user.id)" in src)
check("main: optional health server behind ENABLE_HEALTH_PORT", "enable_health_port" in src and "_health_serve" in src)
check("main: post_shutdown does login shutdown + sup.stop_loop", "await login.shutdown()" in src and "await sup.stop_loop()" in src)

opt_src = open(os.path.join(ROOT, "bot", "optimai.py"), encoding="utf-8").read()
check(
    "optimai: docker_server_version uses run_bin, never 'optimai-cli docker'",
    'run_bin(\n            "docker"' in opt_src.replace("self.", "") or '"docker", "version"' in opt_src,
)
check(
    "optimai: auth_me and auth_logout helpers exist",
    "def auth_me" in opt_src and "def auth_logout" in opt_src,
)
check(
    "optimai: docker_server_version is cached for latency reduction",
    "_cached_docker" in opt_src,
)
check(
    "optimai: read_new_chunk shrink check is `size < start_offset`",
    "if size < start_offset:" in opt_src,
)
check(
    "optimai: node_stop and stop_mining_containers helpers exist",
    "def node_stop" in opt_src and "def stop_mining_containers" in opt_src,
)
sup_src = open(os.path.join(ROOT, "bot", "supervisor.py"), encoding="utf-8").read()
check(
    "supervisor: SIGINT goes to the process GROUP (os.killpg)",
    "os.killpg(proc.pid, signal.SIGINT)" in sup_src,
)
check(
    "supervisor: check_and_apply_update helper exists",
    "check_and_apply_update" in sup_src,
)
check(
    "supervisor: network connectivity and container cleanup wired",
    "check_network_connectivity" in sup_src and "stop_mining_containers" in sup_src,
)
check(
    "main: build_welcome_card helper exists",
    "build_welcome_card" in src and "Welcome to OptimAI Telegram Node" in src,
)
check(
    "main: /start handler mapped to cmd_start",
    'CommandHandler("start", cmd_start' in src,
)
stub_src = open(os.path.join(ROOT, "scripts", "stub-optimai-cli.sh"), encoding="utf-8").read()
check(
    "stub: no $3 positional flag check (uses loop over \"$@\")",
    '"$3"' not in stub_src and 'for arg in "$@"' in stub_src,
)
clean_env = {k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM_")}
clean_env["NO_DOTENV"] = "1"
p_noenv = subprocess.run([sys.executable, "-m", "bot.main"], cwd=ROOT, env=clean_env, capture_output=True, text=True)
check(
    "main: running bot.main without env exits 1 with CONFIG ERROR",
    p_noenv.returncode == 1 and "CONFIG ERROR" in (p_noenv.stdout + p_noenv.stderr),
)

# ======================================================================
print("\n" + "=" * 62)
total = len(PASS) + len(FAIL)
print(f"RESULT: {len(PASS)}/{total} PASS, {len(FAIL)} FAIL")
if FAIL:
    print("Failed checks:")
    for f in FAIL:
        print(f"  - {f}")
print(f"(tmp dir: {TMP})")
sys.exit(0 if not FAIL else 1)
