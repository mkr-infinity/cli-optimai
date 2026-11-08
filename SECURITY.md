# Security Policy — OptimAI Telegram Bot

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ yes    |
| < 1.0   | ❌ no     |

## How to report a vulnerability

1. Do NOT open a public issue describing the vulnerability.
2. Contact the maintainer privately:
   - Telegram: [@mkr_infinity](https://t.me/mkr_infinity)
   - Or via a GitHub repository-security advisory (Settings → Security → Advisories → New advisory draft)
3. Include: description, reproduction steps, affected version, impact.
4. Expect a first response within 72 hours; fixes ship as a patch release.

## Scope notes for this project

- The real `.env` holds the Telegram bot token and must NEVER be committed
  (see .gitignore). A leaked token must be revoked immediately via
  @BotFather → /revoke.
- The docker socket mount (`/var/run/docker.sock`) is intentionally powerful —
  do not expose it to untrusted containers or redistribute the stack with
  modified mounts.
- `TELEGRAM_ALLOWED_IDS` must contain only the owner's numeric Telegram ID(s):
  every ID in it can stop/start the earning node.
