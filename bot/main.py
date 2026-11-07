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
import logging
import os
import sys
import time
from typing import Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import bot
_BOT_START_TIME = time.time()
from bot.compatibility import (
    check_device_compatibility,
    download_compatible_cli,
    get_compatible_cli_url,
)
from bot.config import Config, ConfigError
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
        await message_target(
            f"<pre>{html.escape(part)}</pre>", parse_mode=ParseMode.HTML
        )


async def _reply(update: Update, text: str, keyboard: InlineKeyboardMarkup | None = None) -> None:
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.HTML, reply_markup=keyboard
    )


# ----------------------------------------------------------------------
# Application dependencies (stored once in bot_data)
# ----------------------------------------------------------------------


def _wd(context: ContextTypes.DEFAULT_TYPE) -> Tuple[Config, OptimaiCLI, Supervisor, UnauthorizedGate, LoginManager]:
    bd = context.bot_data
    return bd["cfg"], bd["cli"], bd["sup"], bd["gate"], bd["login"]


# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, _cli, _sup, _gate, _login = _wd(context)
    help_text = (
        "<b>OptimAI Telegram Node — commands</b>\n\n"
        "/help — show this list\n"
        "/status — node running? uptime, auth, docker, crashes\n"
        "/start_node — starts the optimai node (persistent)\n"
        "/stop_node — persistent stop; survives reboots\n"
        "/restart_node — stop + start, closes the circuit breaker\n"
        "/rewards — OptimAI rewards balance\n"
        "/logs — last lines of node.log\n"
        "/watch [seconds] — live-tail node.log (10-600)\n"
        "/login [email password] — browser OAuth or email/password sign-in\n"
        "/auth_status — CLI auth status\n"
        "/me — your Telegram ID and name\n"
        "/cancel — cancel the pending /login session\n"
        "/update_cli — check and update upstream optimai-cli\n"
        "/version — bot + CLI versions\n"
        "/ping — test bot responsiveness\n"
        "/uptime — node supervisor uptime and state\n"
        "/disk — storage volume disk usage\n"
        "/system — platform and runtime diagnostics\n"
        "/healthcheck — check internal bot subsystems\n"
        "/id — (anyone) your numeric Telegram ID\n"
    )
    await _reply(update, help_text)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    rc, out, err = await cli.auth_status()
    auth_text = out + err
    authenticated = rc == 0 and NOT_AUTHENTICATED_MARK not in auth_text
    docker_ok, _ = await cli.docker_server_version()
    sup.update_health(authenticated, docker_ok)
    snap = sup.snapshot()

    node_line = f"running ({snap['uptime']}, PID {snap['pid']})" if snap["running"] else "stopped"
    bot_uptime_line = f"Bot uptime: {fmt_uptime(time.monotonic() - _BOT_START_MONOTONIC)}"
    breaker_line = (
        f"crashes: {snap['crashes']}/{CRASH_LIMIT} | backoff level: "
        f"{snap['backoff_level']} | circuit breaker: {snap['breaker']}"
    )
    lines = [
        "<b>Node status</b> (live)",
        f"Node: {node_line}",
        bot_uptime_line,
        f"Desired state: {snap['desired']} (pid: {snap['pid'] or 'none'})",
        f"Authenticated: {'✅ yes' if snap['authenticated'] else '❌ no — run /login'}",
        f"Docker: {'✅ reachable' if snap['docker_ok'] else '❌ NOT REACHABLE'}",
        f"Last exit code: {snap['last_exit_code']}",
        breaker_line,
    ]
    if not snap["docker_ok"]:
        lines.append(DOCKER_DEAD_WARNING)
    if contains_update_warning(auth_text):
        lines.append(
            "⚠️ Important OptimAI CLI update available — reinstall the CLI per "
            "README (run `optimai-cli update` steps on the VPS host)."
        )
    await _reply(update, "\n".join(lines))


async def cmd_start_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    docker_ok, _ = await cli.docker_server_version()
    if not docker_ok:
        await _reply(
            update,
            "⛔️ Cannot start node: no Docker daemon here. Deploy on a VPS with "
            "Docker (README, Deployment A). On Railway only the bot's "
            "control-plane works (/login /rewards /logs /status).",
        )
        return
    sup.close_breaker()
    pid = await sup.request_start()
    await _reply(
        update,
        f"🚀 Node starting (PID {pid}). Desired state: running. It will run 24/7 "
        "and auto-restart on crashes. Check /status.",
    )


async def cmd_stop_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    docker_ok, _ = await cli.docker_server_version()
    if not docker_ok and sup._pid() is None:
        await _reply(
            update,
            "⛔️ Cannot control the node here: no Docker daemon (Railway "
            "control-plane only; README, Deployment A).",
        )
        return
    await sup.request_stop()
    await _reply(
        update,
        "🛑 Node stopped. This persists: it will NOT come back after a reboot "
        "until you send /start_node.",
    )


async def cmd_restart_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    docker_ok, _ = await cli.docker_server_version()
    if not docker_ok:
        await _reply(
            update,
            "⛔️ Cannot restart node: no Docker daemon here. Deploy on a VPS with "
            "Docker (README, Deployment A). On Railway only the bot's "
            "control-plane works (/login /rewards /logs /status).",
        )
        return
    sup.close_breaker()
    pid = await sup.restart()
    await _reply(
        update,
        f"🔄 Node restarted (PID {pid}). Desired state: running. Circuit breaker "
        "closed.",
    )


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
        await _send_pre(lambda msg: _reply(update, msg), body)


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    path = cfg.node_log_path()
    lines = tail_file(path, cfg.log_tail_lines)
    if not lines:
        await _reply(update, "📝 node.log is empty.")
        return
    await _send_pre(lambda msg: _reply(update, msg), "\n".join(lines))


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
                await _send_pre(lambda msg: _reply(update, msg), part)
        await asyncio.sleep(min(1.0, max(0.1, remaining)))
    if sent_any:
        await _reply(update, f"👁 Watch ended ({seconds}s). Freshest output delivered above.")
    else:
        await _reply(update, f"👁 Watch ended ({seconds}s). No new node output appeared.")


async def cmd_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, login = _wd(context)
    if await cli.is_authenticated():
        await _reply(update, "✅ Already authenticated. Use /auth_status for details.")
        return

    # Check for direct email + password arguments: /login <email> <password>
    if context.args and len(context.args) >= 2:
        email = context.args[0]
        password = context.args[1]
        await _reply(update, "⏳ Attempting email & password authentication...")
        ok, msg = await login.login_legacy(email, password)
        if ok:
            await _reply(
                update,
                f"✅ <b>Login successful</b>\n\n{html.escape(msg)}\n\n"
                "Use /start_node to start mining!",
            )
        else:
            await _reply(
                update,
                f"❌ <b>Login failed</b>\n\n{html.escape(msg)}\n\n"
                "Check your credentials or use the browser login flow.",
            )
        return

    url = await login.start()
    if not url:
        await _reply(
            update,
            "❌ Could not start the login flow (no URL captured from the CLI). "
            "Check `docker compose logs -f` for details.",
        )
        return
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔑 Open login page", url=url)],
            [InlineKeyboardButton("✨ Register (Ref: 646D12E7)", url="https://node.optimai.network/register?ref=646D12E7")],
        ]
    )
    await _reply(
        update,
        "🔑 <b>OptimAI Account Authentication</b>\n\n"
        "<b>Method 1 (Browser OAuth):</b>\n"
        "1. Tap <b>Open login page</b> below.\n"
        "2. Sign in, copy the final redirect URL, and paste it here.\n\n"
        "<b>Method 2 (Direct Email & Password):</b>\n"
        "Send: <code>/login your_email@example.com your_password</code>\n\n"
        "Need an account? Tap <b>Register</b> below.",
        keyboard,
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


async def cmd_auth_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    rc, out, err = await cli.auth_status()
    text = (out + err).strip() or f"(no output, exit code {rc})"
    await _send_pre(lambda msg: _reply(update, msg), text)


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, _login = _wd(context)
    user = update.effective_user
    if user is None:
        return
    is_admin = user.id in cfg.allowed_ids
    await _reply(
        update,
        "👤 <b>Your account</b>\n"
        f"ID: <code>{user.id}</code>\n"
        f"Name: {html.escape(user.full_name)}\n"
        f"Admin: {'✅ yes' if is_admin else '❌ no'}",
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg, cli, sup, _gate, login = _wd(context)
    cancelled = await login.cancel()
    if cancelled:
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
        f"Bot: OptimAI Telegram Node v{bot.__version__} (online: {_format_timestamp(_BOT_START_TIME)}) (rev {_get_git_rev()})\n"
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
    """Admin plain text while a login session is pending = pasted redirect."""
    cfg, cli, sup, _gate, login = _wd(context)
    if not login.has_pending:
        return  # ignore friendly chat
    message = update.effective_message
    if message is None or not message.text:
        return
    ok, summary = await login.submit(message.text)
    header = (
        "✅ Login successful — OptimAI session saved." if ok else "❌ Login failed:"
    )
    tail = summary[:1500]
    await _reply(update, f"{header}\n\n<pre>{html.escape(tail)}</pre>")


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

    # Platform health + auto-resume.
    authenticated = await cli.is_authenticated()
    docker_ok, docker_ver = await cli.docker_server_version()
    sup.update_health(authenticated, docker_ok)

    if (
        cfg.node_auto_start
        and sup.desired == "running"
        and authenticated
        and docker_ok
        and not sup.running
    ):
        await sup.request_start()
        log.info("Auto-resumed node (desired=running, NODE_AUTO_START=true)")

    boot = [
        (
            f"🤖 Bot online. Node desired: {sup.desired} | Docker: "
            f"{'ok' if docker_ok else 'NOT REACHABLE'} | Auth: {'yes' if authenticated else 'no'}. "
            "Type /help for commands."
        )
    ]
    if not docker_ok:
        boot.append(DOCKER_DEAD_WARNING)
    for uid in sorted(cfg.allowed_ids):
        try:
            await app.bot.send_message(uid, "\n".join(boot))
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
        CommandHandler("status", cmd_status, filters=admin_filter),
        CommandHandler("start_node", cmd_start_node, filters=admin_filter),
        CommandHandler("stop_node", cmd_stop_node, filters=admin_filter),
        CommandHandler("restart_node", cmd_restart_node, filters=admin_filter),
        CommandHandler("rewards", cmd_rewards, filters=admin_filter),
        CommandHandler("logs", cmd_logs, filters=admin_filter),
        CommandHandler("watch", cmd_watch, filters=admin_filter),
        CommandHandler("login", cmd_login, filters=admin_filter),
        CommandHandler("login_legacy", cmd_login, filters=admin_filter),
        CommandHandler("auth_status", cmd_auth_status, filters=admin_filter),
        CommandHandler("me", cmd_me, filters=admin_filter),
        CommandHandler("cancel", cmd_cancel, filters=admin_filter),
        CommandHandler("update_cli", cmd_update_cli, filters=admin_filter),
        CommandHandler("version", cmd_version, filters=admin_filter),
        CommandHandler("ping", cmd_ping, filters=admin_filter),
        CommandHandler("uptime", cmd_uptime, filters=admin_filter),
        CommandHandler("disk", cmd_disk, filters=admin_filter),
        CommandHandler("system", cmd_system, filters=admin_filter),
        CommandHandler("healthcheck", cmd_healthcheck, filters=admin_filter),
        # 2. /id — OPEN to everyone (registered before the text handlers)
        CommandHandler("id", cmd_id),
        # 3. admin plain text -> login paste
        MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, on_admin_text),
        # 4. unauthorized catch-all — registered LAST, same group
        MessageHandler(~admin_filter, unauthorized_handler),
    ]
    for handler in handlers:
        app.add_handler(handler)


def build_app(cfg: Config) -> Application:
    app = (
        ApplicationBuilder()
        .token(cfg.telegram_bot_token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    cli = OptimaiCLI(binary=cfg.optimai_bin, home=cfg.optimai_home)
    sup = Supervisor(
        cli=cli,
        data_dir=cfg.data_dir,
        state_path=cfg.state_path(),
        log_path=cfg.node_log_path(),
    )
    gate = UnauthorizedGate(cfg.unauth_counts_path(), max_messages=cfg.unauth_max_messages)
    login = LoginManager(cli, ttl_minutes=cfg.login_ttl_minutes)

    app.bot_data.update(cfg=cfg, cli=cli, sup=sup, gate=gate, login=login)
    admin_filter = filters.User(user_id=sorted(cfg.allowed_ids))
    register_handlers(app, admin_filter)
    return app


def main() -> None:
    bot.print_banner()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("Starting OptimAI Telegram Node v%s", bot.__version__)

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
