# SPDX-License-Identifier: Apache-2.0
"""Environment configuration with fail-fast validation.

Loads a `Config` from environment variables (a `.env` file is NOT parsed here;
`docker compose env_file` / Railway variables inject them). Validation happens
BEFORE any network activity: when a required variable is missing the error
lists ALL missing names together with WHERE each value comes from.
"""

from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass, field

_TRUE = {"true", "1", "yes", "on"}

# Built-in unauthorized reply (⛔️ prefix is part of the delivered template).
_BUILTIN_UNAUTHORIZED_TEMPLATE = (
    "⛔️ You are not authorized to use this bot.\n\n"
    "To host your own OptimAI node server (paid), contact @{contact}."
)

REQUIRED_HELP = {
    "TELEGRAM_BOT_TOKEN": "get it from @BotFather (/newbot)",
    "TELEGRAM_ALLOWED_IDS": (
        "message your bot once and it replies with your ID via /id; "
        "then set it in .env (comma-separated numeric IDs)"
    ),
}


class ConfigError(Exception):
    """Raised when configuration is missing or invalid; message is user-facing."""


def load_dotenv(path: str = ".env") -> dict[str, str]:
    """Parse a .env file into a dictionary (standard library only)."""
    loaded: dict[str, str] = {}
    if not os.path.isfile(path):
        return loaded
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    if len(val) >= 2 and (
                        (val.startswith('"') and val.endswith('"'))
                        or (val.startswith("'") and val.endswith("'"))
                    ):
                        val = val[1:-1]
                    loaded[key] = val
    except Exception:
        pass
    return loaded


def is_local_environment() -> bool:
    """True if running bare-metal on a developer/local machine rather than
    inside a Docker container or cloud deployment."""
    if os.path.exists("/.dockerenv"):
        return False
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("CONTAINER"):
        return False
    if os.path.exists("/data") and os.access("/data", os.W_OK):
        return False
    return True


def find_local_optimai_bin(preferred: str | None = None) -> str:
    """Find the best available optimai-cli executable for the current machine."""
    if preferred and preferred.strip():
        pref = os.path.expanduser(preferred.strip())
        which_path = shutil.which(pref)
        if which_path:
            return which_path
        if os.path.isfile(pref) and os.access(pref, os.X_OK):
            return pref

    is_win = platform.system() == "Windows"
    names = ["optimai-cli.exe", "optimai.exe"] if is_win else ["optimai-cli", "optimai"]

    for name in names:
        found = shutil.which(name)
        if found:
            return found

    candidates: list[str] = []
    if is_win:
        appdata = os.environ.get("LOCALAPPDATA", "")
        prog = os.environ.get("ProgramFiles", "C:\\Program Files")
        candidates.extend([
            os.path.join(appdata, "optimai-cli", "optimai-cli.exe"),
            os.path.join(prog, "optimai-cli", "optimai-cli.exe"),
            os.path.abspath(".\\optimai-cli.exe"),
        ])
    else:
        home = os.path.expanduser("~")
        candidates.extend([
            "/usr/local/bin/optimai-cli",
            os.path.join(home, ".local", "bin", "optimai-cli"),
            os.path.join(home, "bin", "optimai-cli"),
            os.path.abspath("./optimai-cli"),
        ])

    for cand in candidates:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand

    return "optimai-cli.exe" if is_win else "optimai-cli"


def _parse_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in _TRUE


def _parse_int(raw: str | None, name: str, default: int, log=None) -> int:
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        if log:
            log.warning("%s=%r is not an integer; using default %s", name, raw, default)
        return default


@dataclass
class Config:
    @staticmethod
    def load_unauth_promo(contact: str) -> str:
        return f"Contact {contact} for hosting inquiries."

    """Validated configuration; see `.env.example` for the full contract."""

    telegram_bot_token: str
    allowed_ids: set[int]

    node_auto_start: bool = True
    log_tail_lines: int = 40
    watch_seconds: int = 120
    login_ttl_minutes: int = 15
    enable_health_port: int | None = None

    contact_username: str = "mkr_infinity"
    unauthorized_message: str = ""
    unauth_max_messages: int = 3

    optimai_home: str = "/data/home"
    data_dir: str = "/data/data"
    optimai_bin: str = "optimai-cli"
    is_local: bool = False

    @classmethod
    def load(cls, env: dict[str, str] | None = None, log=None) -> "Config":
        if env is None:
            env = dict(os.environ)
            # Auto-load .env when running locally if TELEGRAM_BOT_TOKEN not in env
            if not env.get("NO_DOTENV") and not (env.get("TELEGRAM_BOT_TOKEN") or "").strip():
                for candidate in [".env", os.path.join(os.path.dirname(__file__), "..", ".env")]:
                    cand_path = os.path.abspath(candidate)
                    if os.path.isfile(cand_path):
                        for k, v in load_dotenv(cand_path).items():
                            if k not in env or not env[k].strip():
                                env[k] = v
                                os.environ.setdefault(k, v)
                        break

        # --- required vars, fail-fast, ALL missing reported at once ---
        missing = [
            name
            for name in REQUIRED_HELP
            if not (env.get(name) or "").strip()
        ]
        if missing:
            details = "; ".join(f"{name}: {REQUIRED_HELP[name]}" for name in missing)
            raise ConfigError(
                "Missing required env vars: " + ", ".join(missing) + ". " + details
            )

        # --- TELEGRAM_ALLOWED_IDS: comma-separated numeric IDs -> set[int] ---
        allowed: set[int] = set()
        for segment in env["TELEGRAM_ALLOWED_IDS"].split(","):
            segment = segment.strip()
            if not segment:
                continue
            if not segment.lstrip("-").isdigit() or segment.startswith("-"):
                raise ConfigError(
                    f"TELEGRAM_ALLOWED_IDS contains a non-numeric value: {segment!r}. "
                    "Telegram user IDs are positive integers, e.g. 6602332612."
                )
            allowed.add(int(segment))
        if not allowed:
            raise ConfigError(
                "TELEGRAM_ALLOWED_IDS must contain at least one numeric user ID "
                "(e.g. TELEGRAM_ALLOWED_IDS=6602332612)."
            )

        # --- optional ints with defaults ---
        log_tail_lines = _parse_int(env.get("LOG_TAIL_LINES"), "LOG_TAIL_LINES", 40, log)
        watch_seconds = _parse_int(env.get("WATCH_SECONDS"), "WATCH_SECONDS", 120, log)
        login_ttl = _parse_int(
            env.get("LOGIN_TTL_MINUTES"), "LOGIN_TTL_MINUTES", 15, log
        )

        # --- health port: empty = disabled (supports ENABLE_HEALTH_PORT and Railway's PORT) ---
        port_raw = (env.get("ENABLE_HEALTH_PORT") or env.get("PORT") or "").strip()
        health_port: int | None = None
        if port_raw:
            health_port = _parse_int(port_raw, "ENABLE_HEALTH_PORT", 8080, log)
            if health_port is not None and not (1 <= health_port <= 65535):
                if log:
                    if callable(log):
                        log(f"ENABLE_HEALTH_PORT={health_port} out of range 1-65535; falling back to 8080")
                    elif hasattr(log, "warning"):
                        log.warning("ENABLE_HEALTH_PORT=%s out of range 1-65535; falling back to 8080", health_port)
                health_port = 8080

        # --- hosting-provider mode ---
        contact = (env.get("CONTACT_USERNAME") or "").strip() or "mkr_infinity"
        contact = contact.lstrip("@")

        unauth_max = _parse_int(
            env.get("UNAUTH_MAX_MESSAGES"), "UNAUTH_MAX_MESSAGES", 3, log
        )
        unauth_max = max(0, min(10, unauth_max))

        override = (env.get("UNAUTHORIZED_MESSAGE") or "").strip()
        unauthorized_message = override if override else _BUILTIN_UNAUTHORIZED_TEMPLATE
        unauthorized_message = unauthorized_message.replace("{contact}", contact)

        # --- auto-detect environment and machine setup ---
        is_local = is_local_environment()
        has_writable_data = os.path.exists("/data") and os.access("/data", os.W_OK)

        raw_data = (env.get("DATA_DIR") or "").strip()
        if not is_local and has_writable_data:
            data_dir = os.path.abspath(os.path.expanduser(raw_data or "/data/data"))
        else:
            # Running locally or /data not writable:
            # If raw_data is empty or points to container path /data/..., route to ./data
            if not raw_data or raw_data.startswith("/data"):
                data_dir = os.path.abspath("./data")
            else:
                data_dir = os.path.abspath(os.path.expanduser(raw_data))

        raw_home = (env.get("OPTIMAI_HOME") or "").strip()
        if not is_local and has_writable_data:
            optimai_home = os.path.abspath(os.path.expanduser(raw_home or "/data/home"))
        else:
            # Running locally:
            # If user already has ~/.optimai on their machine, use ~ so optimai-cli
            # can find the existing CLI core and credentials!
            user_home = os.path.expanduser("~")
            existing_optimai = os.path.join(user_home, ".optimai")
            if not raw_home or raw_home.startswith("/data"):
                if os.path.isdir(existing_optimai):
                    optimai_home = user_home
                else:
                    optimai_home = os.path.abspath("./data/home")
            else:
                optimai_home = os.path.abspath(os.path.expanduser(raw_home))

        # Binary resolution
        raw_bin = (env.get("OPTIMAI_BIN") or "").strip()
        if is_local:
            optimai_bin = find_local_optimai_bin(raw_bin)
        else:
            optimai_bin = raw_bin or "optimai-cli"

        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(optimai_home, exist_ok=True)

        return cls(
            telegram_bot_token=env["TELEGRAM_BOT_TOKEN"].strip(),
            allowed_ids=allowed,
            node_auto_start=_parse_bool(env.get("NODE_AUTO_START"), True),
            log_tail_lines=max(1, log_tail_lines),
            watch_seconds=watch_seconds,
            login_ttl_minutes=max(1, login_ttl),
            enable_health_port=health_port,
            contact_username=contact,
            unauthorized_message=unauthorized_message,
            unauth_max_messages=unauth_max,
            optimai_home=optimai_home,
            data_dir=data_dir,
            optimai_bin=optimai_bin,
            is_local=is_local,
        )

    def node_log_path(self) -> str:
        return os.path.join(self.data_dir, "node.log")

    def state_path(self) -> str:
        return os.path.join(self.data_dir, "state.json")

    def unauth_counts_path(self) -> str:
        return os.path.join(self.data_dir, "unauth_counts.json")
