# Changelog

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
- Expanded smoke test coverage to 112 automated checks.

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
