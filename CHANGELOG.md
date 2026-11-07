# Changelog

## v1.9.0 — 2026-11-08

### Added
- Bi-directional credential synchronization between container / database / host terminal (`scripts/sync-credentials.sh`, `bot/config.py`).
- Official OptimAI CLI installation syntax: `chmod +x optimai-cli` and `sudo mv optimai-cli /usr/local/bin/optimai-cli` across all setup scripts.
- Pre/post execution sync wrapper in `/usr/local/bin/optimai-cli` to keep Codespaces and VPS terminals authenticated in real time.
- Bot command aliases and controls: `/sync`, `/node`, `/auth`, `/restart`, `/reward`, `/balance`, `/startnode`, `/stopnode`, `/restartnode`, `/nodestatus`.
- Direct dual authentication flows: `/login` (OAuth browser), `/login --legacy` (email/password), and `/login_legacy` with active re-login inspection dialog.
- Mirroring of credentials database (`credentials.json`) across parent and alternate `./data` folders.
- Repository rename updates to `https://github.com/mkr-infinity/cli-optimai`.
- Expanded smoke test verification suite to 179/179 automated checks with 100% pass rate.

## v1.3.0 — 2026-11-07

### Added
- Auto-download of compatible `optimai-cli` binary on startup if missing.
- Autonomous background worker session viewer via `/screen` command with live PID, uptime, and inline interactive action buttons.
- Persistent credentials database (`credentials.json` in DATA_DIR) with automatic restoration if `auth.json` is lost.
- Complete database and token purge on `/logout`.
- Automated upstream update watcher: detects `Important OptimAI CLI update available` in logs, downloads update, and restarts node automatically.
- Global error handler surfacing all unhandled exceptions and command errors directly to Telegram users.
- Live terminal log streaming (`python -m bot.main logs`, `make logs`, `scripts/logs.sh`).
- Concurrent update handling in `python-telegram-bot` and Docker version caching to eliminate bot command latency.
- Comprehensive smoke test suite expanded to 134 checks with 100% pass rate.

## v1.2.0 — 2026-11-07

### Added
- Dual authentication flow: direct email/password login (`/login <email> <password>` and `/login_legacy`) alongside browser OAuth flow.
- Upstream CLI update command (`/update_cli` and `/update`) for automated optimai-cli version management.
- Bundled official `optimai-cli` Linux binary into Dockerfile and added host installation checks in `setup-vps.sh`.
- Automatic Railway `$PORT` detection and HTTP health server binding (`GET /health -> 200 OK`).
- Multi-environment local execution guide and auto-fallback storage path (`./data`) when running outside Docker on macOS, Linux, and Windows.
- Auto-detection for local machines: zero-config `.env` loading, binary location discovery (`/usr/local/bin`, `~/.local/bin`, Windows Program Files), host `~/.optimai` reuse, and protected gitignore rules.
- OptimAI referral link (`https://node.optimai.network/register?ref=646D12E7`) integrated across Telegram inline buttons and guides.
- Streamlined 5-step beginner setup guide and visual cheatsheet in `README.md`.
- Multi-distribution compatibility engine (`bot/compatibility.py` and `scripts/check-compatibility.sh`) detecting Arch Linux, EndeavourOS, Debian, Ubuntu, Fedora, openSUSE, Alpine, macOS, and Windows.
- Google Cloud Platform (GCP) 24/7 mining focus: added `docs/DEPLOY-GCP.md`, redesigned quickstart for GCP Compute Engine with web SSH, contrasted full Docker mining capability against serverless container platforms, and added comprehensive Acceptable Use Policy (AUP) risk warnings regarding Free Trial account suspensions and financial protections.
- Intelligent package manager detection across `pacman`, `apt`, `dnf`, `zypper`, and `apk` in `setup-vps.sh`.
- Explicit OS & architecture preflight validation with detailed explanatory failure messages; RAM and storage checks are strictly advisory and never forced.
- Expanded smoke test coverage to 121 automated checks.

## v1.1.0 — 2026-11-07

### Added
- Bot uptime monitoring surfaced directly in `/status` output.
- Missing log file feedback in `/watch` command for clean initial-run ergonomics.
- Port range validation (1-65535) for `ENABLE_HEALTH_PORT` with safe fallback to 8080.
- Expanded offline smoke test coverage (84/84 checks).
- Full documentation catalog in `docs/` covering architecture, daily operations, performance benchmarks, testing guides, comparison matrix, and upgrading procedures.
- Enhanced `Makefile` targets (`check`, `pytest`) for fast local developer workflows.
- Dynamic co-author attribution engine supporting GitHub follower recognition.

## v1.0.0 — 2026-11-07

First stable release of **OptimAI Telegram Node**: a Dockerized Python Telegram
bot that runs an OptimAI Network CLI node 24/7 on a VPS, controlled entirely
from Telegram, with an honest Railway control-plane mode.

### Added
- Telegram command set (admin-gated): `/help`, `/status`, `/start_node`,
  `/stop_node`, `/restart_node`, `/rewards`, `/logs`, `/watch`, `/login`,
  `/auth_status`, `/me`, `/cancel`, `/version` — and `/id`, open to everyone
  (counted toward the unauthorized promo budget).
- Desired-state supervisor: `state.json` persistence, SIGINT process-group
  stop, crash auto-restart with 5s→15s→60s→300s backoff, 5-crash circuit
  breaker with exactly one alert, Telegram crash alerts with the last 15 log
  lines.
- pexpect paste-login (`auth login --no-open --paste`), TTL expiry, single
  pending session, safe cancel.
- Hosting-provider promo funnel: `CONTACT_USERNAME`, `UNAUTHORIZED_MESSAGE`
  override with `{contact}`, per-stranger budget persisted in
  `unauth_counts.json`.
- Railway deployment files: `railway.json` (DOCKERFILE + ON_FAILURE) and
  `Procfile` (worker); honest "no Docker daemon" warning from `/status`,
  `/start_node`, `/stop_node`, `/restart_node`.
- Docker/VPS: `python:3.12-slim` image with the static Docker CLI client
  (best-effort, pinned 27.3.1), `docker-compose.yml` with `restart:
  unless-stopped` + `init: true` + socket + `./data:/data`, idempotent
  `setup-vps.sh` (Docker via get.docker.com, 2G swap, preflight checks).
- Tests: 80→83-check smoke suite with a deterministic stub CLI
  (`scripts/stub-optimai-cli.sh`), pytest wrapper, GitHub Actions CI
  (compile → suite → pytest → compose config) on every PR.
- Startup banner v1.0.0 with attribution (Mohammad Kaif Raja / mkr-infinity).

### Verified against the real CLI (v0.1.63)
- `auth login --no-open --paste` exists exactly as used by the bot.
- No `node stop` subcommand → stop = SIGINT to the process group.
- Logged-out `auth status` prints `Not authenticated` with **exit code 0** →
  auth detection is substring-based, never exit-code-only.

### Known limitations
- Railway cannot run the node workload (no docker.sock, no privileged mode) —
  by platform design; the bot warns instead of failing.
- `node start` runtime shape (attached vs daemonized) is only observable on a
  logged-in VPS; the supervisor handles both.
