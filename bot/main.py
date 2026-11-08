# SPDX-License-Identifier: Apache-2.0
"""Telegram wiring, command handlers, and the entrypoint.

Handler order is bug-prone and implemented EXACTLY as specified:
  1. all admin-gated CommandHandlers
  2. `/id` CommandHandler with NO filter (open to everyone, budgeted)
  3. admin-gated MessageHandler(filters.TEXT & ~filters.COMMAND)  # login paste
  4. MessageHandler(~admin_filter, ANY) -> unauthorized_handler, registered
     LAST in the same group 0.
"""

from __future__ import annotations

import asyncio
import html
import inspect
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import bot
_BOT_START_TIME = time.time()
_BOT_START_MONOTONIC = time.monotonic()
from bot.compatibility import (
    check_device_compatibility,
    download_compatible_cli,
    get_compatible_cli_url,
    get_os_info,
)
from bot.config import (
    Config,
    ConfigError,
    clear_credential_database,
    get_env_file_path,
    load_credential_database,
    load_dotenv,
    mask_secret,
    restore_credentials_from_database,
    save_credential_database,
    sync_all_credentials,
    sync_local_credentials,
    update_env_file,
)
from bot.gatekeeper import UnauthorizedGate
from bot.login_session import LoginManager
from bot.optimai import (
    NOT_AUTHENTICATED_MARK,
    OptimaiCLI,
    contains_update_warning,
    read_new_chunk,
    tail_file,
)
from bot.supervisor import CRASH_LIMIT, Supervisor, fmt_uptime

log = logging.getLogger("bot.main")

CHAT_LIMIT = 4096          # Telegram hard limit per message
SAFE_CHUNK = 3900          # room for tags/escapes inside <pre>
DOCKER_DEAD_WARNING = (
    "⚠️ Warning: Docker daemon not reachable in this environment - node "
    "workloads cannot run here (e.g. Railway). The bot's other commands still "
    "work. Run the node itself on a VPS (README, Deployment A)."
)


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------


def _split_text(text: str, limit: int = SAFE_CHUNK) -> list[str]:
    """Split to respect the Telegram 4096-char limit, preferring line breaks."""
    text = text.strip()
    if len(text) <= limit:
        return [text] if text else []
    parts: list[str] = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        cut = text.rfind("\n", limit - 200, limit)
        if cut <= 0:
            cut = text.rfind(" ", 0, limit)
        if cut <= 0:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts


async def _send_pre(message_target, text: str) -> None:
    """Escape `text` and send it inside <pre> block(s), respecting 4096."""
    text = text.strip()
    if not text:
        return
    for part in _split_text(text):
        escaped = f"<pre>{html.escape(part)}</pre>"
        try:
            res = message_target(escaped, parse_mode=ParseMode.HTML)
        except TypeError:
            res = message_target(escaped)
        if inspect.isawaitable(res):
            await res


async def _reply(
    update: Update,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = ParseMode.HTML,
    **kwargs,
) -> None:
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        text, parse_mode=parse_mode, reply_markup=keyboard, **kwargs
    )


# ----------------------------------------------------------------------
# Application dependencies (stored once in bot_data)
# ----------------------------------------------------------------------


def _wd(context: ContextTypes.DEFAULT_TYPE) -> Tuple[Config, OptimaiCLI, Supervisor, UnauthorizedGate, LoginManager]:
    bd = context.bot_data
    cfg = bd["cfg"]
    try:
        sync_all_credentials(cfg, force=False)
    except Exception:
        pass
    return cfg, bd["cli"], bd["sup"], bd["gate"], bd["login"]


# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------


def check_screen_session() -> tuple[bool, str]:
    """Check if GNU Screen session is active (either enclosing process or screen -ls)."""
    sty = os.environ.get("STY")
    if sty:
        return True, f"Active ('{sty}')"
    screen_bin = shutil.which("screen")
    if screen_bin:
        try:
            res = subprocess.run([screen_bin, "-ls"], capture_output=True, text=True, timeout=2)
            out = res.stdout + res.stderr
            if "optimai" in out.lower():
                for line in out.splitlines():
                    if "optimai" in line.lower():
                        parts = line.strip().split()
                        if parts:
                            return True, f"Active ('{parts[0]}')"
                return True, "Active ('optimai' session)"
            elif "there is a screen on" in out.lower() or "there are screens on" in out.lower():
                return True, "Active (screen attached)"
        except Exception:
            pass
    return False, "Inactive (supervisor daemon)"


async def build_welcome_card(cfg: Config, cli: OptimaiCLI, sup: Supervisor) -> tuple[str, InlineKeyboardMarkup]:
    """Construct an informative welcome and status overview card with action buttons."""
    (auth_res, (docker_ok, docker_ver)) = await asyncio.gather(
        cli.auth_status(),
        cli.docker_server_version(),
    )
    rc, out, err = auth_res
    auth_text = out + err
    authenticated = rc == 0 and NOT_AUTHENTICATED_MARK not in auth_text
    sup.update_health(authenticated, docker_ok)
    snap = sup.snapshot()

    os_info = get_os_info()
    distro_name = os_info.get("distro_name", "Linux")
    machine = os_info.get("machine", "x86_64")
    if "termux" in distro_name.lower():
        mode = "Android Termux"
    elif cfg.is_local:
        mode = "Local Machine"
    else:
        mode = "Cloud VM / Container"

    node_status_badge = (
        f"🟢 <b>Running</b> (PID <code>{snap['pid']}</code>, Uptime <code>{snap['uptime']}</code>)"
        if snap["running"]
        else "🔴 <b>Stopped</b> (Offline)"
    )
    auth_badge = "✅ <b>Authenticated</b>" if snap["authenticated"] else "❌ <b>Not Logged In</b> (send /login)"
    docker_badge = f"✅ <b>Reachable</b> (v{docker_ver})" if snap["docker_ok"] else "⚠️ <b>Not Reachable</b>"

    screen_active, screen_desc = check_screen_session()
    screen_badge = f"🟢 <b>{screen_desc}</b>" if screen_active else f"⚪ <b>{screen_desc}</b>"
    reward_alerts_badge = (
        "🔔 <b>ON (real-time)</b>"
        if getattr(sup, "notify_rewards", True)
        else "🔕 <b>OFF</b> (/rewardadded on)"
    )

    text = (
        f"👋 <b>Welcome to OptimAI Telegram Bot v{bot.__version__}</b> ⛏️\n"
        "<i>Autonomous 24/7 Mining Supervisor & Remote Controller</i>\n\n"
        "📊 <b>System & Node Overview:</b>\n"
        f"• <b>Node Status:</b> {node_status_badge}\n"
        f"• <b>OptimAI Auth:</b> {auth_badge}\n"
        f"• <b>Docker AI Miner:</b> {docker_badge}\n"
        f"• <b>Screen Session:</b> {screen_badge}\n"
        f"• <b>Reward Alerts:</b> {reward_alerts_badge}\n"
        f"• <b>Machine / Host:</b> {html.escape(distro_name)} ({machine}) [{mode}]\n"
        f"• <b>Supervisor:</b> Desired: <code>{snap['desired']}</code> | Breaker: <code>{snap['breaker']}</code>\n\n"
        "⚡ <b>Essential Commands:</b>\n"
        "/start_node — Start mining in 24/7 background session\n"
        "/stop_node — Stop mining & background worker workloads\n"
        "/status — Full live status & system diagnostic\n"
        "/screen — View detached 24/7 background worker session\n"
        "/rewards — Check mining points & rewards balance\n"
        "/rewardadded — Toggle real-time reward alerts (on/off)\n"
        "/env — View & configure environment (.env)\n"
        "/logs — View recent node log output\n"
        "/login — Authenticate your OptimAI account\n"
        "/help — View complete command catalog\n\n"
        '🎁 Need an OptimAI account? <a href="https://node.optimai.network/register?ref=646D12E7">Register here (Ref: 646D12E7)</a>'
    )

    buttons = [
        [
            InlineKeyboardButton("🛑 Stop Node" if snap["running"] else "▶️ Start Node",
                                 callback_data="screen_stop" if snap["running"] else "screen_start"),
            InlineKeyboardButton("📊 Status", callback_data="welcome_status"),
        ],
        [
            InlineKeyboardButton("🖥️ Screen Session", callback_data="screen_refresh"),
            InlineKeyboardButton("💰 Rewards", callback_data="welcome_rewards"),
        ],
        [
            InlineKeyboardButton("🔑 Login", callback_data="welcome_login"),
            InlineKeyboardButton("📜 Logs", callback_data="welcome_logs"),
        ],
        [
            InlineKeyboardButton("✨ Register (Ref: 646D12E7)", url="https://node.optimai.network/register?ref=646D12E7"),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    return text, keyboard


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display comprehensive welcome banner, current node state, and quick controls."""
    cfg, cli, sup, _gate, _login = _wd(context)
    text, keyboard = await build_welcome_card(cfg, cli, sup)
    await _reply(update, text, keyboard)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, _cli, _sup, _gate, _login = _wd(context)
    help_text = (
        "<b>OptimAI Telegram Bot — commands</b>\n\n"
        "<b>Node Management:</b>\n"
        "/start — welcome overview, system health & quick controls\n"
        "/start_node (or /startnode) — start the node and Docker AI mining\n"
        "/stop_node (or /stop, /stopnode) — stop the node & background workloads\n"
        "/restart_node (or /restart, /restartnode) — restart node & reset circuit breaker\n"
        "/node [start|stop|restart|status] — official CLI node controller\n"
        "/status (or /nodestatus) — view node status, health, Docker & uptime\n"
        "/screen — view 24/7 background worker session\n"
        "/logs (or /log) — show latest node output\n"
        "/watch [seconds] — live-tail logs in chat (10-600s)\n\n"
        "<b>OptimAI Account (official CLI):</b>\n"
        "/login — browser login via Node Dashboard (optimai-cli auth login)\n"
        "/login --legacy [email pwd] — legacy login via email & password (optimai-cli auth login --legacy)\n"
        "/auth [login|logout|me|status] — official CLI auth controller\n"
        "/auth_status — check OptimAI authentication status\n"
        "/me — view OptimAI CLI profile & Telegram account\n"
        "/sync — force bi-directional credential & database sync with terminal\n"
        "/logout — sign out from OptimAI account\n"
        "/rewards (or /reward, /balance) — check OptimAI mining rewards balance\n"
        "/rewardadded [on|off] — toggle real-time mining reward notifications\n"
        "/cancel — cancel pending login session\n\n"
        "<b>System & Diagnostics:</b>\n"
        "/update_cli (or /update) — update official optimai-cli\n"
        "/env — view active environment configuration (.env)\n"
        "/setenv [KEY VALUE] — update .env configuration directly\n"
        "/version — bot + CLI versions\n"
        "/ping — test bot responsiveness\n"
        "/uptime — node supervisor uptime and state\n"
        "/disk — storage volume disk usage\n"
        "/system — platform and runtime diagnostics\n"
        "/healthcheck — check internal bot subsystems\n"
        "/id — (open to everyone) your numeric Telegram ID\n"
    )
    await _reply(update, help_text)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    (auth_res, (docker_ok, _)) = await asyncio.gather(
        cli.auth_status(),
        cli.docker_server_version(),
    )
    rc, out, err = auth_res
    auth_text = out + err
    authenticated = rc == 0 and NOT_AUTHENTICATED_MARK not in auth_text
    sup.update_health(authenticated, docker_ok)
    snap = sup.snapshot()

    _ok, node_out = await cli.node_status()
    if snap["running"]:
        node_line = f"🟢 running (PID {snap['pid']}, Uptime {snap['uptime']})"
        node_detail = f"\n<pre>{html.escape(node_out)}</pre>" if node_out else ""
    else:
        node_line = "🔴 stopped (offline)"
        node_detail = (
            f"\n<pre>{html.escape(node_out)}</pre>\n<i>Node is stopped. Send /start_node or tap ▶️ Start Node below.</i>"
            if node_out
            else "\n<i>Node is stopped. Send /start_node or tap ▶️ Start Node below.</i>"
        )

    bot_uptime_line = f"Bot uptime: {fmt_uptime(time.monotonic() - _BOT_START_MONOTONIC)}"
    breaker_line = (
        f"crashes: {snap['crashes']}/{CRASH_LIMIT} | backoff level: "
        f"{snap['backoff_level']} | circuit breaker: {snap['breaker']}"
    )
    screen_active, screen_desc = check_screen_session()
    reward_notify = (
        "🔔 ON (real-time alerts)"
        if getattr(sup, "notify_rewards", True)
        else "🔕 OFF (/rewardadded on)"
    )

    lines = [
        "<b>Node status</b> (live)",
        f"Node: {node_line}{node_detail}",
        bot_uptime_line,
        f"Desired state: {snap['desired']} (pid: {snap['pid'] or 'none'})",
        f"Authenticated: {'✅ yes' if snap['authenticated'] else '❌ no — run /login'}",
        f"Docker: {'✅ reachable' if snap['docker_ok'] else '❌ NOT REACHABLE'}",
        f"Screen session: {'🟢 ' if screen_active else '⚪ '}{screen_desc}",
        f"Reward alerts: {reward_notify}",
        f"Last exit code: {snap['last_exit_code']}",
        breaker_line,
    ]
    if not snap["docker_ok"]:
        lines.append(DOCKER_DEAD_WARNING)
    if contains_update_warning(auth_text):
        lines.append(
            "⚠️ Important OptimAI CLI update available — send /update_cli to auto-update."
        )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛑 Stop Node" if snap["running"] else "▶️ Start Node",
                                 callback_data="screen_stop" if snap["running"] else "screen_start"),
            InlineKeyboardButton("🔄 Refresh", callback_data="welcome_status"),
        ],
        [
            InlineKeyboardButton("🖥️ Screen Session", callback_data="screen_refresh"),
            InlineKeyboardButton("💰 Rewards", callback_data="welcome_rewards"),
        ],
        [
            InlineKeyboardButton("📜 Logs", callback_data="welcome_logs"),
        ],
    ])
    await _reply(update, "\n".join(lines), keyboard)


async def cmd_start_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    docker_ok, _ = await cli.docker_server_version()
    is_termux = bool(os.environ.get("TERMUX_VERSION")) or os.path.isdir("/data/data/com.termux")
    docker_available = docker_ok or os.path.exists("/var/run/docker.sock") or cfg.is_local or is_termux
    if not docker_available:
        await _reply(
            update,
            "⛔️ Cannot start node: no Docker daemon here. Deploy on a VPS with "
            "Docker (README, Deployment A). On Railway only the bot's "
            "control-plane works (/login /rewards /logs /status).",
        )
        return
    sync_all_credentials(cfg, force=False)
    if cfg.is_local:
        sync_local_credentials(cfg.optimai_home, os.path.expanduser("~"))
    if not await cli.is_authenticated():
        await _reply(
            update,
            "⚠️ <b>Not authenticated:</b> Please log in first using /login before starting the node.",
        )
        return
    sup.close_breaker()
    pid = await sup.request_start()
    await asyncio.sleep(1.5)
    recent = sup.get_recent_output(6)
    out_snippet = "\n".join(recent).strip() if recent else ""
    if sup.running:
        msg = (
            f"🚀 <b>Node started successfully (PID {sup._pid() or pid})!</b>\n"
            f"Desired state: <b>running</b>. It will run 24/7 and auto-restart on crashes.\n"
        )
        if out_snippet:
            msg += f"\n📋 <b>Initial Output:</b>\n<pre>{html.escape(out_snippet)}</pre>\n"
        msg += "\n💡 Docker AI miner containers are starting. Check /status or /logs for live progress."
        await _reply(update, msg)
    else:
        exit_code = sup._last_exit_code
        msg = f"⚠️ <b>Node process exited during startup (exit code {exit_code}):</b>\n"
        if out_snippet:
            msg += f"<pre>{html.escape(out_snippet)}</pre>\n"
        msg += "\nCheck /logs or run <code>optimai-cli node start</code> in terminal for diagnostic details."
        await _reply(update, msg)


async def cmd_stop_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    docker_ok, _ = await cli.docker_server_version()
    is_termux = bool(os.environ.get("TERMUX_VERSION")) or os.path.isdir("/data/data/com.termux")
    docker_available = docker_ok or os.path.exists("/var/run/docker.sock") or cfg.is_local or is_termux
    if not docker_available and sup._pid() is None:
        await _reply(
            update,
            "⛔️ Cannot control the node here: no Docker daemon (Railway "
            "control-plane only; README, Deployment A).",
        )
        return
    await sup.request_stop()
    await _reply(
        update,
        "🛑 <b>Node stopped:</b> Background node process and all associated mining "
        "workloads have been stopped. Send /start_node whenever you want to resume.",
    )


async def cmd_restart_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    docker_ok, _ = await cli.docker_server_version()
    is_termux = bool(os.environ.get("TERMUX_VERSION")) or os.path.isdir("/data/data/com.termux")
    docker_available = docker_ok or os.path.exists("/var/run/docker.sock") or cfg.is_local or is_termux
    if not docker_available:
        await _reply(
            update,
            "⛔️ Cannot restart node: no Docker daemon here. Deploy on a VPS with "
            "Docker (README, Deployment A). On Railway only the bot's "
            "control-plane works (/login /rewards /logs /status).",
        )
        return
    sync_all_credentials(cfg, force=False)
    sup.close_breaker()
    pid = await sup.restart()
    await asyncio.sleep(1.5)
    recent = sup.get_recent_output(6)
    out_snippet = "\n".join(recent).strip() if recent else ""
    if sup.running:
        msg = (
            f"🔄 <b>Node restarted successfully (PID {sup._pid() or pid})!</b>\n"
            f"Desired state: <b>running</b>. Circuit breaker closed.\n"
        )
        if out_snippet:
            msg += f"\n📋 <b>Initial Output:</b>\n<pre>{html.escape(out_snippet)}</pre>\n"
        msg += "\n💡 Check /status or /logs for live progress."
        await _reply(update, msg)
    else:
        exit_code = sup._last_exit_code
        msg = f"⚠️ <b>Node process exited after restart (exit code {exit_code}):</b>\n"
        if out_snippet:
            msg += f"<pre>{html.escape(out_snippet)}</pre>\n"
        msg += "\nCheck /logs for diagnostic details."
        await _reply(update, msg)


async def cmd_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    ok, text = await cli.rewards_balance()
    body = text if text else "(empty response)"
    if not ok and "Not authenticated" in body:
        await _reply(
            update,
            f"<pre>{html.escape(body)}</pre>\n\n💡 Not authenticated — send /login first.",
        )
    else:
        await _send_pre(lambda msg, **kw: _reply(update, msg, **kw), body)


async def cmd_rewardadded(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle or configure real-time mining reward notifications."""
    _cfg, _cli, sup, _gate, _login = _wd(context)
    if context.args:
        arg = context.args[0].lower().strip()
        if arg in ("on", "true", "enable", "yes", "1"):
            sup.set_notify_rewards(True)
        elif arg in ("off", "false", "disable", "no", "0"):
            sup.set_notify_rewards(False)
        else:
            await _reply(
                update,
                "⚠️ <b>Usage:</b> <code>/rewardadded on</code> or <code>/rewardadded off</code>\n"
                f"Currently reward alerts are: <b>{'🔔 ON' if sup.notify_rewards else '🔕 OFF'}</b>.",
            )
            return
    else:
        sup.set_notify_rewards(not sup.notify_rewards)

    if sup.notify_rewards:
        await _reply(
            update,
            "🔔 <b>Mining Reward Alerts: ENABLED</b>\n\n"
            "You will receive an instant Telegram message whenever mining earns new OPTIM rewards, including:\n"
            "• <b>Workload / Task name</b>\n"
            "• <b>Amount earned</b> (+OPTIM)\n"
            "• <b>Updated total balance</b>\n\n"
            "<i>To turn off alerts at any time, send: /rewardadded off</i>",
        )
    else:
        await _reply(
            update,
            "🔕 <b>Mining Reward Alerts: DISABLED</b>\n\n"
            "Real-time reward notifications are now muted. You can still check your balance at any time with /rewards.\n\n"
            "<i>To re-enable alerts at any time, send: /rewardadded on</i>",
        )


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    path = cfg.node_log_path()
    lines = tail_file(path, cfg.log_tail_lines)
    if not lines:
        await _reply(update, "📝 node.log is empty.")
        return
    await _send_pre(lambda msg, **kw: _reply(update, msg, **kw), "\n".join(lines))


async def cmd_watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    seconds = cfg.watch_seconds
    if context.args:
        try:
            seconds = int(context.args[0])
        except (ValueError, TypeError):
            seconds = cfg.watch_seconds
    seconds = max(10, min(600, seconds))

    path = cfg.node_log_path()
    if not os.path.exists(path):
        await _reply(
            update,
            "ℹ️ <b>Node log file not yet created.</b>\n"
            "The node has not produced any logs yet. Use /start_node to begin running, "
            "or wait a moment for initial log output to be written.",
        )
        return
    try:
        offset = os.path.getsize(path)
    except OSError:
        offset = 0

    deadline = asyncio.get_running_loop().time() + seconds
    sent_any = False
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            break
        chunk, offset = read_new_chunk(path, offset)
        tail = chunk.strip()
        if tail:
            sent_any = True
            for part in _split_text(tail):
                await _send_pre(lambda msg, **kw: _reply(update, msg, **kw), part)
        await asyncio.sleep(min(1.0, max(0.1, remaining)))
    if sent_any:
        await _reply(update, f"👁 Watch ended ({seconds}s). Freshest output delivered above.")
    else:
        await _reply(update, f"👁 Watch ended ({seconds}s). No new node output appeared.")


async def _execute_email_password_login(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    email: str,
    password: str,
) -> None:
    cfg, cli, sup, _gate, login = _wd(context)
    context.user_data.pop("awaiting_credentials_until", None)
    await _reply(update, "⏳ Attempting direct email & password authentication...")
    ok, msg = await login.login_legacy(email, password)
    if ok:
        auth_file = os.path.join(cfg.optimai_home, ".config", "optimai-cli", "auth.json")
        if not os.path.isfile(auth_file):
            u_auth = os.path.expanduser("~/.config/optimai-cli/auth.json")
            if os.path.isfile(u_auth):
                auth_file = u_auth
        if os.path.isfile(auth_file):
            try:
                snap_data = json.load(open(auth_file))
                user_file = os.path.join(os.path.dirname(auth_file), "user.json")
                u_snap = json.load(open(user_file)) if os.path.isfile(user_file) else {}
                save_credential_database(
                    cfg.credentials_path(),
                    {
                        "email": email or u_snap.get("email", ""),
                        "auth_type": "legacy",
                        "auth_snapshot": snap_data,
                        "user_snapshot": u_snap,
                        "updated_at": time.time(),
                    },
                )
            except Exception:
                pass
        sync_all_credentials(cfg, force=True)
        docker_ok, _ = await cli.docker_server_version()
        is_termux = bool(os.environ.get("TERMUX_VERSION")) or os.path.isdir("/data/data/com.termux")
        docker_available = docker_ok or os.path.exists("/var/run/docker.sock") or cfg.is_local or is_termux
        auto_msg = ""
        if cfg.node_auto_start and docker_available and not sup.running:
            pid = await sup.request_start()
            auto_msg = f"\n\n🚀 <b>Mining Started:</b> Node and Docker AI miner spawned automatically (PID {pid})!"
        await _reply(
            update,
            f"✅ <b>Login successful</b>\n\n{html.escape(msg)}\n<i>Credentials saved to database & synchronized with terminal.</i>{auto_msg}\n\n"
            f"{'Use /status to monitor mining.' if auto_msg else 'Use /start_node to start mining!'}",
        )
    else:
        await _reply(
            update,
            f"❌ <b>Login failed</b>\n\n{html.escape(msg)}\n\n"
            "Check your credentials or choose Method 1 (Browser OAuth) below.",
        )


async def cmd_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, login = _wd(context)
    if await cli.is_authenticated():
        if not context.args:
            _rc, out_me, _ = await cli.auth_me()
            email_info = out_me.strip() or "Connected"
            auth_msg = (
                f"✅ <b>Already Authenticated:</b>\n"
                f"<pre>{html.escape(email_info)}</pre>\n\n"
                "Your node is linked to your OptimAI account. To switch accounts or re-login, choose an option below:\n\n"
                "• Send <code>/login --legacy email password</code> to sign in with another account\n"
                "• Send <code>/sync</code> to synchronize credentials with terminal\n"
                "• Send <code>/logout</code> to disconnect"
            )
            auth_kbd = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🌐 Re-login (Browser)", callback_data="login_method_browser"),
                    InlineKeyboardButton("📧 Re-login (Legacy)", callback_data="login_method_legacy"),
                ],
                [
                    InlineKeyboardButton("🔄 Sync Terminal (/sync)", callback_data="welcome_sync"),
                    InlineKeyboardButton("🚪 Logout", callback_data="login_logout"),
                ],
            ])
            await _reply(update, auth_msg, auth_kbd)
            return

    # Direct arguments handling matching official CLI:
    # 1) /login --legacy <email> <password> or /login <email> <password> -> Legacy Login
    # 2) /login --legacy (or /login legacy) -> prompt for Legacy Login credentials
    # 3) /login browser (or oauth) -> launch Browser Login directly
    if context.args:
        args = list(context.args)
        is_legacy = False
        if args[0].lower() in ("--legacy", "-legacy", "legacy"):
            is_legacy = True
            args.pop(0)

        if is_legacy:
            if len(args) >= 2:
                email = args[0]
                password = args[1]
                await _execute_email_password_login(update, context, email, password)
                return
            context.user_data["awaiting_credentials_until"] = time.monotonic() + 180
            pwd_text = (
                "📧 <b>Legacy Login (optimai-cli auth login --legacy)</b>\n\n"
                "If you prefer to use email/password instead of browser login:\n\n"
                "1. <b>Reply directly in this chat</b> with:\n"
                "<code>your_email@example.com your_password</code>\n\n"
                "2. Or send the command:\n"
                "<code>/login --legacy your_email@example.com your_password</code>\n\n"
                "⏱️ <i>Session active for 3 minutes. Send /cancel at any time to abort.</i>"
            )
            await _reply(update, pwd_text)
            return

        if len(args) == 1 and args[0].lower() in ("browser", "oauth", "dashboard", "1"):
            url = await login.start()
            if not url:
                await _reply(update, "❌ Could not start browser login flow. Try again or use /login --legacy.")
                return
            oauth_text = (
                "🌐 <b>Browser Login (optimai-cli auth login)</b>\n\n"
                "This will open your browser to sign in via the OptimAI Node Dashboard:\n\n"
                "1. Tap <b>Open Login Page</b> below to sign in.\n"
                "2. After signing in, copy the authorization key or redirect URL.\n"
                "3. <b>Paste the key or URL directly here</b> in this chat.\n\n"
                "⏱️ <i>Session active for 3 minutes. Send /cancel at any time to abort.</i>"
            )
            oauth_kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Open Login Page", url=url)],
                [InlineKeyboardButton("❌ Cancel Login", callback_data="login_cancel")],
            ])
            await _reply(update, oauth_text, oauth_kbd)
            return

        if len(args) >= 2:
            email = args[0]
            password = args[1]
            await _execute_email_password_login(update, context, email, password)
            return

    # No arguments: present the two official login methods
    text = (
        "🔑 <b>OptimAI Account Authentication</b>\n\n"
        "Choose your preferred sign-in method to connect this node to your OptimAI account:\n\n"
        "🌐 <b>1) Browser Login (default):</b>\n"
        "<code>optimai-cli auth login</code>\n"
        "Sign in via the OptimAI Node Dashboard in your browser, then paste the redirect URL or key here within 3 minutes.\n\n"
        "📧 <b>2) Legacy Login (email/password):</b>\n"
        "<code>optimai-cli auth login --legacy</code>\n"
        "If you prefer to use email/password instead of browser login:\n"
        "<code>/login --legacy your_email@example.com your_password</code>\n\n"
        "<i>Need an account? Tap Register below.</i>"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 Browser Login (auth login)", callback_data="login_method_browser"),
        ],
        [
            InlineKeyboardButton("📧 Legacy Login (auth login --legacy)", callback_data="login_method_legacy"),
        ],
        [
            InlineKeyboardButton("✨ Register (Ref: 646D12E7)", url="https://node.optimai.network/register?ref=646D12E7"),
            InlineKeyboardButton("❌ Cancel", callback_data="login_cancel"),
        ],
    ])
    await _reply(update, text, keyboard)


async def cmd_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /node [start|stop|restart|status] matching official CLI subcommands."""
    if context.args:
        sub = context.args[0].lower().strip()
        context.args = list(context.args[1:])
        if sub in ("start", "run", "up"):
            await cmd_start_node(update, context)
            return
        elif sub in ("stop", "down", "kill"):
            await cmd_stop_node(update, context)
            return
        elif sub in ("restart", "reboot"):
            await cmd_restart_node(update, context)
            return
        elif sub in ("status", "info"):
            await cmd_status(update, context)
            return
    await cmd_status(update, context)


async def cmd_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /auth [login|logout|status|me] matching official CLI subcommands."""
    if context.args:
        sub = context.args[0].lower().strip()
        context.args = list(context.args[1:])
        if sub in ("login", "signin"):
            await cmd_login(update, context)
            return
        elif sub in ("logout", "signout"):
            await cmd_logout(update, context)
            return
        elif sub in ("me", "profile", "whoami"):
            await cmd_me(update, context)
            return
        elif sub in ("status", "check"):
            await cmd_auth_status(update, context)
            return
    await cmd_auth_status(update, context)


async def cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Force bi-directional credential and database sync between bot and workspace terminal."""
    cfg, cli, _sup, _gate, _login = _wd(context)
    sync_all_credentials(cfg, force=True)
    restore_credentials_from_database(cfg.credentials_path(), cfg.optimai_home)
    for h in (os.path.expanduser("~"), "/data/home", "./data/home"):
        if os.path.isdir(h):
            sync_local_credentials(cfg.optimai_home, h)
            restore_credentials_from_database(cfg.credentials_path(), h)
    rc, out, err = await cli.auth_status()
    auth_summary = (out + err).strip() or f"status code {rc}"
    await _reply(
        update,
        "🔄 <b>Credential & Database Synchronization Complete</b>\n\n"
        f"• <b>Auth Status:</b> <code>{html.escape(auth_summary)}</code>\n"
        f"• <b>Database:</b> <code>{html.escape(cfg.credentials_path())}</code>\n"
        f"• <b>OptimAI Home:</b> <code>{html.escape(cfg.optimai_home)}</code>\n"
        f"• <b>Host Terminal:</b> Synced with workspace (<code>~/.config/optimai-cli</code>)\n\n"
        "<i>Your authenticated OptimAI session is active across both the Telegram bot and the terminal!</i>",
    )


async def cmd_update_cli(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, _sup, _gate, _login = _wd(context)
    compat, reason, details = check_device_compatibility()
    if not compat:
        await _reply(
            update,
            f"❌ <b>Device Incompatible with OptimAI CLI:</b>\n"
            f"{html.escape(reason)}\n\n"
            "<i>Note: RAM/storage minimums are not enforced; OS or CPU architecture is unsupported.</i>",
        )
        return

    await _reply(update, "⏳ Checking for OptimAI CLI updates...")
    rc, out, err = await cli.run("update", timeout=60)
    text = (out + "\n" + err).strip() or f"(exit code {rc})"

    # If CLI binary is missing (rc=127) or update requests reinstallation, download the compatible binary
    if rc == 127 or "reinstall" in text.lower():
        cli_url = details.get("cli_url")
        target_path = cfg.optimai_bin if os.path.isabs(cfg.optimai_bin) else shutil.which(cfg.optimai_bin) or "/usr/local/bin/optimai-cli"
        await _reply(update, f"📥 Installing/updating compatible CLI from:\n<code>{cli_url}</code>\nTarget: <code>{target_path}</code>")
        success, dl_msg = download_compatible_cli(target_path, url=cli_url)
        text += f"\n\nInstall Result: {'✅' if success else '❌'} {dl_msg}"

    await _reply(update, f"🔄 <b>CLI Update Result:</b>\n<pre>{html.escape(text)}</pre>")


async def cmd_env(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View current environment configuration (.env) with sensitive secrets masked."""
    cfg, _cli, _sup, _gate, _login = _wd(context)
    env_path = get_env_file_path()
    dotenv = load_dotenv(env_path) if os.path.isfile(env_path) else {}

    keys_order = [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_IDS",
        "NODE_AUTO_START",
        "LOG_TAIL_LINES",
        "WATCH_SECONDS",
        "LOGIN_TTL_MINUTES",
        "ENABLE_HEALTH_PORT",
        "TZ",
        "CONTACT_USERNAME",
        "UNAUTH_MAX_MESSAGES",
        "OPTIMAI_HOME",
        "DATA_DIR",
    ]
    lines = [
        "⚙️ <b>Active Environment Configuration</b>",
        f"<i>Source: <code>{html.escape(env_path)}</code></i>\n",
    ]

    for k in keys_order:
        val = dotenv.get(k) or os.environ.get(k, "")
        masked = mask_secret(k, val) if val else "<i>(not set)</i>"
        lines.append(f"• <b>{k}:</b> <code>{html.escape(masked)}</code>")

    # Any other custom keys in .env
    for k, v in dotenv.items():
        if k not in keys_order and not k.startswith("#"):
            lines.append(f"• <b>{html.escape(k)}:</b> <code>{html.escape(mask_secret(k, v))}</code>")

    lines.append(
        "\n📝 <b>To update any variable:</b>\n"
        "Send: <code>/setenv KEY VALUE</code>\n"
        "Example: <code>/setenv NODE_AUTO_START true</code>"
    )
    await _reply(update, "\n".join(lines))


async def cmd_setenv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set or update an environment variable directly from Telegram."""
    cfg, _cli, _sup, _gate, login = _wd(context)
    if not context.args:
        help_text = (
            "⚙️ <b>Environment Variable Editor (/setenv)</b>\n\n"
            "Update your configuration directly from Telegram without SSH or editing files:\n\n"
            "<b>Usage:</b> <code>/setenv KEY VALUE</code> (or <code>/setenv KEY=VALUE</code>)\n\n"
            "<b>Common Settings:</b>\n"
            "• <code>/setenv NODE_AUTO_START true</code> (or false)\n"
            "• <code>/setenv TELEGRAM_ALLOWED_IDS 6602332612</code>\n"
            "• <code>/setenv LOG_TAIL_LINES 50</code>\n"
            "• <code>/setenv WATCH_SECONDS 180</code>\n"
            "• <code>/setenv LOGIN_TTL_MINUTES 3</code>\n"
            "• <code>/setenv CONTACT_USERNAME my_handle</code>\n"
            "• <code>/setenv TELEGRAM_BOT_TOKEN 123456:ABC...</code>\n\n"
            "<i>Send /env at any time to view all configured variables.</i>"
        )
        await _reply(update, help_text)
        return

    raw = " ".join(context.args).strip()
    if "=" in raw:
        key, val = raw.split("=", 1)
    else:
        parts = raw.split(None, 1)
        key = parts[0]
        val = parts[1] if len(parts) > 1 else ""

    key = key.strip().upper()
    val = val.strip()

    if not re.match(r"^[A-Z0-9_]+$", key):
        await _reply(update, "❌ Invalid environment key. Use uppercase letters, numbers, and underscores (e.g. <code>NODE_AUTO_START</code>).")
        return

    env_path = update_env_file(key, val)
    os.environ[key] = val

    # Dynamically apply to running Config
    if key == "NODE_AUTO_START":
        cfg.node_auto_start = val.lower() in ("true", "1", "yes", "on")
    elif key == "LOG_TAIL_LINES":
        try:
            cfg.log_tail_lines = max(1, min(500, int(val)))
        except ValueError:
            pass
    elif key == "WATCH_SECONDS":
        try:
            cfg.watch_seconds = max(10, min(600, int(val)))
        except ValueError:
            pass
    elif key == "LOGIN_TTL_MINUTES":
        try:
            cfg.login_ttl_minutes = max(1, int(val))
            login.ttl_seconds = max(60, cfg.login_ttl_minutes * 60)
        except ValueError:
            pass
    elif key == "CONTACT_USERNAME":
        cfg.contact_username = val.lstrip("@")
    elif key == "UNAUTH_MAX_MESSAGES":
        try:
            cfg.unauth_max_messages = max(0, min(10, int(val)))
        except ValueError:
            pass
    elif key == "TELEGRAM_ALLOWED_IDS":
        try:
            new_ids = {int(x.strip()) for x in val.split(",") if x.strip()}
            cfg.allowed_ids = new_ids
        except ValueError:
            pass

    masked_val = mask_secret(key, val)
    await _reply(
        update,
        f"✅ <b>Environment variable saved:</b>\n"
        f"• <b>Key:</b> <code>{html.escape(key)}</code>\n"
        f"• <b>Value:</b> <code>{html.escape(masked_val)}</code>\n"
        f"• <b>File:</b> <code>{html.escape(env_path)}</code>\n\n"
        f"<i>Configuration written to .env and applied to active session.</i>",
    )


async def cmd_auth_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    rc, out, err = await cli.auth_status()
    text = (out + err).strip() or f"(no output, exit code {rc})"
    await _send_pre(lambda msg, **kw: _reply(update, msg, **kw), text)


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    user = update.effective_user
    if user is None:
        return
    is_admin = user.id in cfg.allowed_ids
    rc, out, err = await cli.auth_me()
    opt_me = (out + err).strip() or "(not authenticated)"
    await _reply(
        update,
        "👤 <b>Account Details</b>\n\n"
        f"<b>Telegram User:</b> {html.escape(user.full_name)} (<code>{user.id}</code>)\n"
        f"<b>Admin authorized:</b> {'✅ yes' if is_admin else '❌ no'}\n\n"
        f"<b>OptimAI CLI (<code>optimai-cli auth me</code>):</b>\n"
        f"<pre>{html.escape(opt_me)}</pre>",
    )


async def cmd_logout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    if sup.running:
        await sup.request_stop()
    rc, out, err = await cli.auth_logout()
    text = (out + err).strip() or "Logged out."
    clear_credential_database(cfg.credentials_path(), [cfg.optimai_home, os.path.expanduser("~")])
    await _reply(
        update,
        f"🚪 <b>OptimAI Account Logged Out:</b>\n<pre>{html.escape(text)}</pre>\n\n"
        "🧹 <b>Credentials Database Cleared:</b> Saved credentials and database session have been completely purged.\n"
        "Send /login whenever you want to authenticate again.",
    )


async def cmd_screen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the detached 24/7 background worker session (equivalent to screen -S optimai)."""
    cfg, cli, sup, _gate, _login = _wd(context)
    snap = sup.snapshot()
    tail = tail_file(cfg.node_log_path(), 6)
    tail_text = "\n".join(tail).strip() or "(no log output yet)"
    mode = "Local Machine" if cfg.is_local else "Cloud VM / Container"
    status_badge = "🟢 Running (Background Session)" if snap["running"] else "🛑 Stopped"
    screen_active, screen_desc = check_screen_session()

    text = (
        "🖥️ <b>OptimAI Background Worker Session</b> (screen mode)\n\n"
        f"• <b>Status:</b> {status_badge}\n"
        f"• <b>Screen Session:</b> {'🟢 ' if screen_active else '⚪ '}{screen_desc}\n"
        f"• <b>Session PID:</b> <code>{snap['pid'] or 'detached/none'}</code>\n"
        f"• <b>Uptime:</b> <code>{snap['uptime']}</code>\n"
        f"• <b>Environment:</b> {mode}\n"
        f"• <b>Binary:</b> <code>{cfg.optimai_bin}</code>\n"
        f"• <b>Desired State:</b> <code>{snap['desired']}</code> (survives reboots)\n\n"
        "<b>Latest Session Output (node.log):</b>\n"
        f"<pre>{html.escape(tail_text)}</pre>\n\n"
        "<i>Mining runs autonomously in the background 24/7. You can send any command anytime without interrupting execution.</i>"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh Screen", callback_data="screen_refresh"),
            InlineKeyboardButton("📜 Live Watch", callback_data="screen_watch"),
        ],
        [
            InlineKeyboardButton("🛑 Stop Node" if snap["running"] else "🚀 Start Node",
                                 callback_data="screen_stop" if snap["running"] else "screen_start"),
        ],
    ])
    await _reply(update, text, keyboard)


async def on_screen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    data = query.data
    cfg, cli, sup, _gate, _login = _wd(context)
    if data == "screen_refresh":
        await cmd_screen(update, context)
    elif data == "screen_stop":
        await sup.request_stop()
        if query.message and query.message.text and "Welcome" in query.message.text:
            text, keyboard = await build_welcome_card(cfg, cli, sup)
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await cmd_screen(update, context)
    elif data == "screen_start":
        docker_ok, _ = await cli.docker_server_version()
        if not docker_ok:
            if query.message:
                await query.message.reply_text("⛔️ Cannot start node: Docker daemon not reachable.")
            return
        await sup.request_start()
        if query.message and query.message.text and "Welcome" in query.message.text:
            text, keyboard = await build_welcome_card(cfg, cli, sup)
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await cmd_screen(update, context)
    elif data == "screen_watch":
        await cmd_watch(update, context)
    elif data == "welcome_status":
        await cmd_status(update, context)
    elif data == "welcome_rewards":
        await cmd_rewards(update, context)
    elif data == "welcome_logs":
        await cmd_logs(update, context)
    elif data == "welcome_login":
        await cmd_login(update, context)
    elif data == "welcome_sync":
        await cmd_sync(update, context)
    elif data == "login_logout":
        await cmd_logout(update, context)
    elif data == "welcome_refresh":
        text, keyboard = await build_welcome_card(cfg, cli, sup)
        if query.message:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await _reply(update, text, keyboard)
    elif data in ("login_method_browser", "login_method_oauth"):
        url = await _login.start()
        if not url:
            if query.message:
                await query.message.reply_text("❌ Could not start login flow (no URL captured from CLI). Try again or use /login --legacy.")
            return
        oauth_text = (
            "🌐 <b>Browser Login (optimai-cli auth login)</b>\n\n"
            "This will open your browser to sign in via the OptimAI Node Dashboard:\n\n"
            "1. Tap <b>Open Login Page</b> below.\n"
            "2. Sign in via the OptimAI Node Dashboard.\n"
            "3. Copy the authorization key or redirect URL and <b>paste it directly here</b>.\n\n"
            "⏱️ <i>Session active for 3 minutes. Send /cancel at any time to abort.</i>"
        )
        oauth_kbd = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Open Login Page", url=url)],
            [InlineKeyboardButton("❌ Cancel Login", callback_data="login_cancel")],
        ])
        if query.message:
            await query.message.reply_text(oauth_text, reply_markup=oauth_kbd, parse_mode=ParseMode.HTML)
    elif data in ("login_method_legacy", "login_method_password"):
        context.user_data["awaiting_credentials_until"] = time.monotonic() + 180
        pwd_text = (
            "📧 <b>Legacy Login (optimai-cli auth login --legacy)</b>\n\n"
            "If you prefer to use email/password instead of browser login:\n\n"
            "1. <b>Reply directly in this chat</b> with:\n"
            "<code>your_email@example.com your_password</code>\n\n"
            "2. Or send the command:\n"
            "<code>/login --legacy your_email@example.com your_password</code>\n\n"
            "⏱️ <i>Session active for 3 minutes. Send /cancel at any time to abort.</i>"
        )
        if query.message:
            await query.message.reply_text(pwd_text, parse_mode=ParseMode.HTML)
    elif data == "login_cancel":
        cancelled = await _login.cancel()
        had_creds = bool(context.user_data.pop("awaiting_credentials_until", None))
        msg = "✅ Login session cancelled." if (cancelled or had_creds) else "ℹ️ No pending login session."
        if query.message:
            await query.message.reply_text(msg)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, login = _wd(context)
    cancelled = await login.cancel()
    had_creds = bool(context.user_data.pop("awaiting_credentials_until", None))
    if cancelled or had_creds:
        await _reply(update, "🚫 Pending login session cancelled.")
    else:
        await _reply(update, "ℹ️ No pending login session.")



def _get_git_rev() -> str:
    try:
        import subprocess
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "release"


def _format_timestamp(ts: float | None) -> str:
    if not ts:
        return "(never)"
    import datetime
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

async def cmd_version(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    rc, out, err = await cli.run("--version", timeout=30)
    cli_version = (out + err).strip() or f"(unknown, exit code {rc})"
    await _reply(
        update,
        "ℹ️ <b>Versions</b>\n"
        f"Bot: OptimAI Telegram Bot v{bot.__version__} (online: {_format_timestamp(_BOT_START_TIME)}) (rev {_get_git_rev()})\n"
        f"CLI: {html.escape(cli_version)}",
    )



async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    snap = sup.snapshot()
    await _reply(
        update,
        f"⏱️ <b>Uptime:</b> {snap['uptime']}\n"
        f"<b>Desired state:</b> <code>{snap['desired']}</code>\n"
        f"<b>Total crashes:</b> {snap['crashes']}",
    )


async def cmd_disk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import shutil
    cfg, _cli, _sup, _gate, _login = _wd(context)
    total, used, free = shutil.disk_usage(cfg.data_dir)
    gb = 1024 ** 3
    pct = round((used / total) * 100, 1) if total > 0 else 0
    await _reply(
        update,
        f"💾 <b>Data Storage ({cfg.data_dir})</b>\n"
        f"Total: {total / gb:.1f} GB\n"
        f"Used: {used / gb:.1f} GB ({pct}%)\n"
        f"Free: {free / gb:.1f} GB",
    )



def _get_proc_memory() -> str:
    try:
        import resource
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        kb = rusage.ru_maxrss
        return f"{kb / 1024:.1f} MB (max RSS)"
    except Exception:
        return "(unavailable)"

async def cmd_system(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import platform, os
    cfg, _cli, _sup, _gate, _login = _wd(context)
    mode = "Local Machine" if cfg.is_local else "Container / Cloud"
    compat, _, details = check_device_compatibility()
    compat_badge = "✅ Compatible" if compat else "❌ Incompatible"
    await _reply(
        update,
        "🖥️ <b>System diagnostics</b>\n"
        f"Environment: <b>{mode}</b>\n"
        f"Compatibility: <b>{compat_badge}</b> ({details.get('distro_name', '')}, {details.get('machine', '')})\n"
        f"Python: {platform.python_version()} ({platform.python_implementation()})\n"
        f"OS: {platform.system()} {platform.release()} ({platform.machine()})\n"
        f"CLI: <code>{cfg.optimai_bin}</code>\n"
        f"Home: <code>{cfg.optimai_home}</code>\n"
        f"Data: <code>{cfg.data_dir}</code>\n"
        f"PID: {os.getpid()}\nRAM: {_get_proc_memory()}",
    )


async def cmd_healthcheck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import os
    cfg, _cli, sup, _gate, _login = _wd(context)
    snap = sup.snapshot()
    data_ok = os.access(cfg.data_dir, os.W_OK)
    bin_ok = os.path.isfile(cfg.optimai_bin) and os.access(cfg.optimai_bin, os.X_OK)
    mode = "Local" if cfg.is_local else "Container"
    compat, _, _ = check_device_compatibility()
    await _reply(
        update,
        "🩺 <b>Subsystem healthcheck</b>\n"
        f"Environment: <b>{mode}</b>\n"
        f"Device compatible: {'✅ yes' if compat else '❌ no'}\n"
        f"Supervisor desired: <code>{snap['desired']}</code>\n"
        f"Circuit breaker: {snap['breaker']}\n"
        f"Data dir writable: {'✅ yes' if data_ok else '❌ no'}\n"
        f"CLI executable: {'✅ yes' if bin_ok else '⚠️ not resolved'}",
    )

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "🏓 <b>Pong!</b> Bot control-plane is responsive.")


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """OPEN TO EVERYONE (NOT admin-gated), but budgeted via the gate."""
    cfg, cli, sup, gate, _login = _wd(context)
    user = update.effective_user
    if user is None:
        return
    gate.record(user.id)
    await _reply(
        update,
        f"🆔 Your Telegram ID: <code>{user.id}</code>. Send this ID to the bot "
        "owner to get access.",
    )


async def on_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin plain text: handles OAuth paste or direct email/password login."""
    cfg, cli, sup, _gate, login = _wd(context)
    message = update.effective_message
    if message is None or not message.text:
        return

    text = message.text.strip()
    awaiting_creds = context.user_data.get("awaiting_credentials_until", 0) > time.monotonic()
    parts = text.split()
    if parts and parts[0].lower() in ("--legacy", "-legacy", "legacy"):
        parts.pop(0)
    looks_like_creds = len(parts) >= 2 and "@" in parts[0]

    # Handle Legacy Login: Direct email & password entered in chat
    if (awaiting_creds and len(parts) >= 2) or (looks_like_creds and not login.has_pending):
        email = parts[0]
        password = " ".join(parts[1:])
        await _execute_email_password_login(update, context, email, password)
        return

    # Handle Method 1: Browser OAuth redirect URL or key paste
    if login.has_pending:
        ok, summary = await login.submit(text)
        header = (
            "✅ Login successful — OptimAI session saved." if ok else "❌ Login failed:"
        )
        tail = summary[:1500]
        auto_msg = ""
        if ok:
            auth_file = os.path.join(cfg.optimai_home, ".config", "optimai-cli", "auth.json")
            if not os.path.isfile(auth_file):
                u_auth = os.path.expanduser("~/.config/optimai-cli/auth.json")
                if os.path.isfile(u_auth):
                    auth_file = u_auth
            if os.path.isfile(auth_file):
                try:
                    snap_data = json.load(open(auth_file))
                    user_file = os.path.join(os.path.dirname(auth_file), "user.json")
                    u_snap = json.load(open(user_file)) if os.path.isfile(user_file) else {}
                    save_credential_database(
                        cfg.credentials_path(),
                        {
                            "email": u_snap.get("email", ""),
                            "auth_type": "oauth",
                            "auth_snapshot": snap_data,
                            "user_snapshot": u_snap,
                            "updated_at": time.time(),
                        },
                    )
                except Exception:
                    pass
            sync_all_credentials(cfg, force=True)
            docker_ok, _ = await cli.docker_server_version()
            is_termux = bool(os.environ.get("TERMUX_VERSION")) or os.path.isdir("/data/data/com.termux")
            docker_available = docker_ok or os.path.exists("/var/run/docker.sock") or cfg.is_local or is_termux
            if cfg.node_auto_start and docker_available and not sup.running:
                pid = await sup.request_start()
                auto_msg = f"\n\n🚀 <b>Mining Started:</b> Node and Docker AI miner spawned automatically (PID {pid})!"
        await _reply(update, f"{header}\n\n<pre>{html.escape(tail)}</pre>\n<i>Credentials saved to database & synchronized with terminal.</i>{auto_msg}")
        return

    # Check if text looks like an authorization key or redirect URL without active session
    if not login.has_pending and ("node.optimai.network" in text.lower() or "code=" in text.lower()):
        await _reply(
            update,
            "💡 <b>Authentication Key Detected:</b>\n\n"
            "To complete login, please start a browser login session first by sending /login, "
            "then paste your redirect key or authorization code within 3 minutes.\n\n"
            "Send /login to begin.",
        )
        return

    # Ignore ordinary friendly chat
    return


async def unauthorized_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stranger message: promo reply with a persisted per-account budget."""
    cfg, cli, sup, gate, _login = _wd(context)
    user = update.effective_user
    if user is None:
        return
    text = cfg.unauthorized_message  # {contact} already substituted in Config
    if gate.may_reply(user.id):
        gate.record(user.id)
        if update.effective_message:
            await update.effective_message.reply_text(text)
        log.info("Promo reply sent to unauthorized user %s (count used +=1)", user.id)
    else:
        log.info("Silent: unauthorized user %s has no promo budget left", user.id)


# ----------------------------------------------------------------------
# Lifecycle hooks
# ----------------------------------------------------------------------


async def _post_init(app: Application) -> None:
    cfg: Config = app.bot_data["cfg"]
    cli: OptimaiCLI = app.bot_data["cli"]
    sup: Supervisor = app.bot_data["sup"]
    gate: UnauthorizedGate = app.bot_data["gate"]
    login: LoginManager = app.bot_data["login"]

    async def alert_fn(text: str) -> None:
        for uid in sorted(cfg.allowed_ids):
            try:
                await app.bot.send_message(uid, text, parse_mode=ParseMode.HTML)
            except Exception as exc:
                log.warning("Crash alert to %s failed: %s", uid, exc)

    # KNOWN FIX: alert_fn MUST be wired into the Supervisor here...
    sup._alert_fn = alert_fn
    login._alert_fn = alert_fn

    # ...and the watch loop MUST be started.
    await sup.start_loop()

    # Optional health endpoint (platform healthchecks).
    if cfg.enable_health_port:
        server = await asyncio.start_server(_health_serve, "0.0.0.0", cfg.enable_health_port)
        app.bot_data["health_server"] = server
        log.info("Health port %s open (GET /health -> 200 OK)", cfg.enable_health_port)

    # Ensure binary exists (auto-download compatible release if missing)
    bin_path = cfg.optimai_bin if os.path.isabs(cfg.optimai_bin) else shutil.which(cfg.optimai_bin)
    if not bin_path or not os.access(bin_path, os.X_OK):
        target = cfg.optimai_bin if os.path.isabs(cfg.optimai_bin) else "/usr/local/bin/optimai-cli"
        log.info("OptimAI CLI binary missing; downloading compatible release to %s...", target)
        download_compatible_cli(target)

    # Restore credentials from persistent database file if available
    sync_all_credentials(cfg, force=True)
    restore_credentials_from_database(cfg.credentials_path(), cfg.optimai_home)
    if cfg.is_local:
        sync_local_credentials(cfg.optimai_home, os.path.expanduser("~"))
    authenticated = await cli.is_authenticated()
    if authenticated:
        data_auth = os.path.join(cfg.optimai_home, ".config", "optimai-cli", "auth.json")
        if os.path.isfile(data_auth):
            try:
                snap_auth = json.load(open(data_auth))
                user_file = os.path.join(cfg.optimai_home, ".config", "optimai-cli", "user.json")
                u_snap = json.load(open(user_file)) if os.path.isfile(user_file) else {}
                save_credential_database(
                    cfg.credentials_path(),
                    {"auth_snapshot": snap_auth, "user_snapshot": u_snap, "updated_at": time.time()},
                )
            except Exception:
                pass

    docker_ok, docker_ver = await cli.docker_server_version()
    is_termux = bool(os.environ.get("TERMUX_VERSION")) or os.path.isdir("/data/data/com.termux")
    effective_docker_ok = docker_ok or is_termux or os.path.exists("/var/run/docker.sock") or cfg.is_local
    sup.update_health(authenticated, effective_docker_ok)

    has_explicit_state = os.path.exists(sup._state_path)
    should_auto_start = (
        cfg.node_auto_start
        and authenticated
        and effective_docker_ok
        and not sup.running
        and (sup.desired == "running" or not has_explicit_state)
    )
    if should_auto_start:
        await sup.request_start()
        log.info(
            "Auto-started node (desired=%s, has_explicit_state=%s, NODE_AUTO_START=true)",
            sup.desired,
            has_explicit_state,
        )

    welcome_text, welcome_keyboard = await build_welcome_card(cfg, cli, sup)
    for uid in sorted(cfg.allowed_ids):
        try:
            await app.bot.send_message(
                uid, welcome_text, reply_markup=welcome_keyboard, parse_mode=ParseMode.HTML
            )
        except Exception as exc:
            log.warning("Boot message to %s failed: %s", uid, exc)


async def _health_serve(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        await reader.read(1024)  # drain request head
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
        await writer.drain()
    finally:
        writer.close()


async def _post_shutdown(app: Application) -> None:
    sup: Supervisor = app.bot_data["sup"]
    login: LoginManager = app.bot_data["login"]

    # Stop the watch task (never kills the node process itself).
    await sup.stop_loop()

    # Cancel any pending login session and kill its child process.
    try:
        await login.shutdown()
    except Exception:
        log.exception("Login shutdown failed")

    server = app.bot_data.get("health_server")
    if server is not None:
        server.close()
        await server.wait_closed()
        app.bot_data.pop("health_server", None)


# ----------------------------------------------------------------------
# Wiring
# ----------------------------------------------------------------------


def register_handlers(app: Application, admin_filter) -> None:
    handlers = [
        # 1. admin-gated commands
        CommandHandler("help", cmd_help, filters=admin_filter),
        CommandHandler("h", cmd_help, filters=admin_filter),
        CommandHandler("status", cmd_status, filters=admin_filter),
        CommandHandler("stat", cmd_status, filters=admin_filter),
        CommandHandler("nodestatus", cmd_status, filters=admin_filter),
        CommandHandler("start_node", cmd_start_node, filters=admin_filter),
        CommandHandler("startnode", cmd_start_node, filters=admin_filter),
        CommandHandler("start", cmd_start, filters=admin_filter),
        CommandHandler("stop_node", cmd_stop_node, filters=admin_filter),
        CommandHandler("stopnode", cmd_stop_node, filters=admin_filter),
        CommandHandler("stop", cmd_stop_node, filters=admin_filter),
        CommandHandler("restart_node", cmd_restart_node, filters=admin_filter),
        CommandHandler("restartnode", cmd_restart_node, filters=admin_filter),
        CommandHandler("restart", cmd_restart_node, filters=admin_filter),
        CommandHandler("node", cmd_node, filters=admin_filter),
        CommandHandler("rewards", cmd_rewards, filters=admin_filter),
        CommandHandler("reward", cmd_rewards, filters=admin_filter),
        CommandHandler("balance", cmd_rewards, filters=admin_filter),
        CommandHandler("rewardadded", cmd_rewardadded, filters=admin_filter),
        CommandHandler("logs", cmd_logs, filters=admin_filter),
        CommandHandler("log", cmd_logs, filters=admin_filter),
        CommandHandler("watch", cmd_watch, filters=admin_filter),
        CommandHandler("login", cmd_login, filters=admin_filter),
        CommandHandler("login_legacy", cmd_login, filters=admin_filter),
        CommandHandler("logout", cmd_logout, filters=admin_filter),
        CommandHandler("auth_status", cmd_auth_status, filters=admin_filter),
        CommandHandler("auth", cmd_auth, filters=admin_filter),
        CommandHandler("me", cmd_me, filters=admin_filter),
        CommandHandler("sync", cmd_sync, filters=admin_filter),
        CommandHandler("cancel", cmd_cancel, filters=admin_filter),
        CommandHandler("update_cli", cmd_update_cli, filters=admin_filter),
        CommandHandler("update", cmd_update_cli, filters=admin_filter),
        CommandHandler("env", cmd_env, filters=admin_filter),
        CommandHandler("setenv", cmd_setenv, filters=admin_filter),
        CommandHandler("version", cmd_version, filters=admin_filter),
        CommandHandler("ping", cmd_ping, filters=admin_filter),
        CommandHandler("uptime", cmd_uptime, filters=admin_filter),
        CommandHandler("disk", cmd_disk, filters=admin_filter),
        CommandHandler("system", cmd_system, filters=admin_filter),
        CommandHandler("healthcheck", cmd_healthcheck, filters=admin_filter),
        CommandHandler("screen", cmd_screen, filters=admin_filter),
        # 2. /id — OPEN to everyone (registered before the text handlers)
        CommandHandler("id", cmd_id),
        # 3. interactive screen callbacks
        CallbackQueryHandler(on_screen_callback),
        # 4. admin plain text -> login paste
        MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, on_admin_text),
        # 5. unauthorized catch-all — registered LAST, same group
        MessageHandler(~admin_filter, unauthorized_handler),
    ]
    for handler in handlers:
        app.add_handler(handler)


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Report unhandled command errors directly back to the user in Telegram."""
    log.error("Exception while handling Telegram update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        err_text = html.escape(str(context.error) or "Internal command execution error.")
        try:
            await update.effective_message.reply_text(
                f"⚠️ <b>Command Execution Error:</b>\n<pre>{err_text}</pre>\n\n"
                "<i>Error captured and logged. Check /status or send /help.</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


def build_app(cfg: Config) -> Application:
    app = (
        ApplicationBuilder()
        .token(cfg.telegram_bot_token)
        .concurrent_updates(True)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    app.add_error_handler(global_error_handler)
    cli = OptimaiCLI(binary=cfg.optimai_bin, home=cfg.optimai_home)
    sup = Supervisor(
        cli=cli,
        data_dir=cfg.data_dir,
        state_path=cfg.state_path(),
        log_path=cfg.node_log_path(),
        cfg=cfg,
    )
    gate = UnauthorizedGate(cfg.unauth_counts_path(), max_messages=cfg.unauth_max_messages)
    login = LoginManager(cli, ttl_minutes=cfg.login_ttl_minutes)

    app.bot_data.update(cfg=cfg, cli=cli, sup=sup, gate=gate, login=login)
    admin_filter = filters.User(user_id=sorted(cfg.allowed_ids))
    register_handlers(app, admin_filter)
    return app


def tail_node_log_terminal(log_path: str) -> None:
    """Stream OptimAI node logs directly in the terminal (runs on `python -m bot.main logs`)."""
    print(f"📖 Streaming OptimAI node logs from: {log_path} (Press Ctrl+C to exit)\n")
    if not os.path.exists(log_path):
        print(f"File {log_path} not found yet. Waiting for node process to write logs...")
        while not os.path.exists(log_path):
            time.sleep(0.5)

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
            for line in lines[-40:]:
                sys.stdout.write(line)
            sys.stdout.flush()

        offset = os.path.getsize(log_path)
        while True:
            chunk, offset = read_new_chunk(log_path, offset)
            if chunk:
                sys.stdout.write(chunk)
                sys.stdout.flush()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n👋 Stopped watching node logs.")


def main() -> None:
    bot.print_banner()

    # Terminal log viewer: python -m bot.main logs / make logs / scripts/logs.sh
    if any(arg in sys.argv[1:] for arg in ("logs", "log", "/logs", "/log", "--logs", "-l")):
        try:
            cfg = Config.load()
            log_path = cfg.node_log_path()
        except Exception:
            log_path = os.path.abspath("./data/node.log")
        tail_node_log_terminal(log_path)
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("Starting OptimAI Telegram Bot v%s", bot.__version__)

    try:
        cfg = Config.load()
    except ConfigError as exc:
        log.error("%s", exc)
        sys.stderr.write(f"CONFIG ERROR: {exc}\n")
        sys.exit(1)

    app = build_app(cfg)
    mode_label = "LOCAL (auto-detected machine)" if cfg.is_local else "CONTAINER / CLOUD"
    log.info(
        "Config ok [%s]: %s admin id(s), data_dir=%s, optimai_home=%s, optimai_bin=%s, health=%s",
        mode_label,
        len(cfg.allowed_ids),
        cfg.data_dir,
        cfg.optimai_home,
        cfg.optimai_bin,
        cfg.enable_health_port or "off",
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
