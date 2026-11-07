# Upgrading & Maintenance Runbook

Step-by-step instructions for safely upgrading `optimai-cli` (OptimAI Telegram Node) between releases without losing authentication credentials, node state, or rate limit history.

## Zero Data-Loss Invariant

All persistent state is stored outside container ephemeral layers:
- **`~/.optimai/`** (host mount to `/data/home`): stores CLI authentication tokens and upstream binary caches.
- **`./data/`** (host mount to `/data/data`): stores `state.json` (desired state, PID, uptime) and `unauth_counts.json` (unauthorized promo tracking).

Upgrades recreate only the stateless container layers.

## Standard Upgrade Procedure (VPS)

```bash
# 1. Navigate to the project directory
cd ~/optimai-cli  # or your clone path

# 2. Pull the latest release code
git pull origin main

# 3. Rebuild and restart the container
docker compose up -d --build

# 4. Verify running container and logs
docker compose ps
docker compose logs --tail=30 optimai-bot
```

## Post-Upgrade Verification

1. Open Telegram chat with your bot and run `/status`.
2. Confirm:
   - Node status is `running`.
   - Authenticated shows `✅ yes`.
   - Docker shows `✅ reachable`.
   - Bot uptime has reset to `0s` (confirming fresh process started cleanly).

## Rollback Procedure

If an upstream change introduces issues on your environment:

```bash
# Checkout previous git tag/commit
git checkout v1.3.0

# Re-up the previous container image
docker compose up -d --build
```
