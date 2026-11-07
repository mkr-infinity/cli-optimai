# Deployment A — VPS (primary, full node support)

Detailed, step-by-step standalone guide. The short version lives in the
README (§ Beginner guide). Target: a fresh Ubuntu 22.04/24.04 box, EUR 4-6/mo
(Hetzner / Contabo / RackNerd class), 2 GB+ RAM, ~15 GB disk.

## 0. What you need

- VPS IP + root password / SSH key
- Telegram bot token (from @BotFather)
- OptimAI account ([register with ref 646D12E7](https://node.optimai.network/register?ref=646D12E7))
- THIS folder on your PC

## 1. Ship the project to the VPS

```bash
# from your PC, in this folder
zip -r optimai-cli.zip . -x "data/*" ".git/*" ".env"
scp optimai-cli.zip root@YOUR_VPS_IP:~
ssh root@YOUR_VPS_IP
```

## 2. One-shot server preparation (idempotent, safe to re-run)

```bash
bash setup-vps.sh
```

It: upgrades packages → installs Docker Engine + compose plugin + screen + Python 3 →
downloads and configures the official OptimAI CLI miner binary (`/usr/local/bin/optimai-cli`) →
`systemctl enable --now docker` → guarantees >= 2G swap (fallocate/mkswap/
swapon, fstab, swappiness=10) → runs the automated 10-point pre-flight readiness checklist (`[✅ PASSED]`)
verifying all miner requirements before printing next steps.

## 3. Configure ONLY the 2 required values

```bash
cp .env.example .env && nano .env
```

| Variable | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather → /newbot → copy the token |
| `TELEGRAM_ALLOWED_IDS` | leave empty first time — Step 5 fills it |

Optional but recommended for India: `TZ=Asia/Kolkata`. Promo funnel values
(`CONTACT_USERNAME`, `UNAUTH_MAX_MESSAGES`, ...) have good defaults — see
README §4.

## 4. Build and start (the 24/7 layer, part 1)

```bash
docker compose up -d --build
docker compose logs -f
# expect: banner ... then "🤖 Bot online. Node desired: stopped | Docker: ok | Auth: no. Type /help for commands."
```

The container restarts itself forever (`restart: unless-stopped`); reboots
and daemon restarts are covered.

## 5. Claim ownership (one-time bootstrapping)

1. Open the bot in Telegram → send `/id` → it replies with your numeric ID.
2. Put that ID into `TELEGRAM_ALLOWED_IDS=<your id>` in `.env`.
3. `docker compose up -d` (recreates the container with the new env).

## 6. Log in (headless paste flow — no browser on the server)

In Telegram:

```
/login   → open the login page on YOUR device → sign in → copy the final
           redirect URL → paste it into the chat → confirm "Login successful"
```

Session TTL: `LOGIN_TTL_MINUTES` (15 default), cancels with `/cancel`.

## 7. Start the node and verify

```
/start_node   → node spawns in its own process group; supervisor watches it
/status       → Node: running (uptime, PID) | Auth: yes | Docker: ok
/rewards      → current balance
/logs, /watch → live visibility
```

## 8. Ops cheat-sheet

| Task | Command |
|---|---|
| Update code | upload/`git pull` → `docker compose up -d --build` |
| Inspect state | `cat data/state.json` (`{"desired":"running"\|"stopped"}`) |
| Persistent stop | `/stop_node` (survives reboots BY DESIGN) |
| Resume | `/start_node` (also closes the circuit breaker) |
| Crash forensics | crash alert DM + `/logs` (tail of `node.log`) |

## Security posture

- The bot dials OUT only (Telegram long polling): firewall can stay fully
  closed for inbound ports.
- `./data` holds the CLI login + state — treat like credentials; never commit.
- Rotate a leaked token: @BotFather → /revoke → .env → `up -d`.
