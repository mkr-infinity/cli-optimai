# ⛏️ OptimAI Telegram Node v1.3.0

![CI](https://github.com/mkr-infinity/optimai-cli/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)
![Version](https://img.shields.io/badge/version-1.3.0-orange)
[![Telegram](https://img.shields.io/badge/contact-%40mkr__infinity-blue)](https://t.me/mkr_infinity)

> [!IMPORTANT]
> **OFFICIAL OPTIMAI CLI REFERENCE & NOTICE:**  
> This repository is **NOT** the official documentation or code repository for the OptimAI CLI itself.  
> For official OptimAI Node CLI documentation, releases, hardware requirements, and native CLI usage, visit:  
> 👉 **[OptimAI Network CLI Node Official Repository](https://github.com/OptimaiNetwork/OptimAI-CLI-Node)** | **[Official Core Node Docs](https://docs.optimai.network/docs/optimai-node/core-node)**  
>  
> **What this repository is:**  
> This project is a **24/7 autonomous production supervisor and Telegram management bot** built to wrap the official `optimai-cli`. It automatically restarts crashed nodes with exponential backoff, manages Docker AI mining containers (`crawl4ai`), syncs local credentials, and provides full remote control from your phone.

> 🚀 **Your 24/7 OptimAI Network node on Google Cloud, controlled entirely from Telegram.**
> Start, stop, monitor rewards, view live logs, and authenticate directly from your phone. Run on Google Cloud Platform (GCP) Compute Engine with full Docker engine access for continuous 24/7 mining.

```
┌──────────┐  long-polling   ┌────────────────────┐  subprocess   ┌──────────────┐  docker.sock  ┌─────────────┐
│ Telegram │ ←──────────────→│  bot container     │←────────────→ │ optimai-cli  │←─────────────→│ host Docker │
│  (you)   │   outbound-only │  (python-telegram) │   wrapping    │ + creds/vol  │   workload    │   engine    │
└──────────┘                 └────────────────────┘               └──────────────┘               └─────────────┘
```

> 🎁 **Need an OptimAI account?**
> 👉 **[Register Here with Referral Code 646D12E7](https://node.optimai.network/register?ref=646D12E7)**

---

## 1. What is This?

`optimai-telegram-node` is a lightweight, Dockerized Python bot designed to manage an **OptimAI Network Node** remotely.

* **24/7 Uptime**: Automatic crash restart with exponential backoff & circuit breaker.
* **Full Remote Control**: 19 commands covering `/status`, `/rewards`, `/logs`, `/watch`, `/login`, and more.
* **Persistent State**: Reboots and Docker rebuilds will **never** lose your login or desired node state.
* **Hosting Mode**: Built-in rate limiter that turns unauthorized messages into a paid hosting funnel to **@mkr_infinity**.
* **Cloud & Local Deployment**: Runs on **Google Cloud (GCP) Compute Engine** with full Docker engine access for real mining, or locally on your own machine.

---

## 2. Prerequisites

| Requirement | Purpose | Recommendation |
|---|---|---|
| **OptimAI Account** | Earning points & mining | **[Register (Ref: 646D12E7)](https://node.optimai.network/register?ref=646D12E7)** |
| **Google Cloud (GCP)** | Running node 24/7 with Docker | Free $300 Trial Credits / Free Tier `e2-micro`/`e2-medium` (Ubuntu 24.04 LTS) |
| **Telegram Account** | Controlling your bot | Free |
| **Telegram Bot** | Interfacing with the server | Free via [@BotFather](https://t.me/BotFather) |

---

## 3. Beginner Quickstart: 5 Steps to 24/7 Mining on Google Cloud

Follow these 5 simple steps to get your node mining on Google Cloud in under 5 minutes.

### 🔹 Step 1: Create Your Telegram Bot
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, give it a name and username (e.g. `MyOptimAINodeBot`).
3. Copy the **HTTP API Token** (format: `123456789:ABCdefGhI...`).

### 🔹 Step 2: Get Your Telegram User ID
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram.
2. Note your numeric **Id** (e.g. `123456789`).

### 🔹 Step 3: Launch Your Google Cloud VM (Compute Engine)

> [!WARNING]
> **Google Cloud Policy Notice & Mining Risk:**
> Google Cloud's [Acceptable Use Policy](https://cloud.google.com/terms/aup) restricts computational and crypto mining on **Free Trial ($300 credit) accounts** without prior written approval. Automated fraud detection may suspend trial projects if continuous intensive mining is flagged. For a 100% suspension-free experience, consider standard paid accounts, dedicated crypto-friendly VPS hosts, or running locally on your own PC.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) > **Compute Engine** > **VM instances**.
2. Click **Create Instance**:
   * **Name**: `optimai-node`
   * **Machine Type**: `e2-micro` (Free Tier eligible) or `e2-medium`
   * **Boot Disk**: `Ubuntu 24.04 LTS` (20 GB balanced persistent disk)
3. Click **Create**, then click the **SSH** button next to your new VM to open a terminal directly in your web browser.

### 🔹 Step 4: Clone & Run Setup on Google Cloud
In the Google Cloud SSH terminal window, paste:
```bash
# 1. Clone this repository
git clone https://github.com/mkr-infinity/optimai-cli.git && cd optimai-cli

# 2. Complete setup & install all miner requirements (Docker, Compose, screen, Python, official CLI binary & pre-flight checker)
sudo bash setup-vps.sh

# 3. Create your configuration
cp .env.example .env
nano .env
```
In `nano`, fill in your two required values:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhI...
TELEGRAM_ALLOWED_IDS=123456789
```
*(Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit).*

> [!TIP]
> **Pre-Flight Readiness Checker:** The setup script automatically executes an automated 10-point readiness check showing green checkmarks (`[✅ PASSED]`) for the CPU architecture, official CLI miner, Docker daemon, Compose plugin, screen multiplexer, Python runtime, networking, and persistent storage. You can re-run this anytime using `make readiness` or `bash scripts/check-readiness.sh`.

### 🔹 Step 5: Start the Container & Login
Launch your bot:
```bash
docker compose up -d --build
```

Now open Telegram and talk to your bot:
* **Option A — Browser OAuth:**
  1. Send `/login` and tap the **Open login page** button.
  2. Sign in with your [OptimAI account](https://node.optimai.network/register?ref=646D12E7).
  3. Copy the final redirect URL from your browser address bar and paste it into chat.
* **Option B — Direct Email & Password:**
  * Send: <code>/login your_email@example.com your_password</code>
* Send `/status` or `/start_node` to begin earning! ⛏️

---

## 4. Running Locally (macOS, Windows, Linux)

You can run the bot on your local personal computer just as easily as on a remote VPS.

### 💻 Option 1: Local with Docker (Recommended)
1. Ensure **Docker Desktop** (macOS/Windows) or **Docker Engine** (Linux) is open and running.
2. Clone and configure:
   ```bash
   git clone https://github.com/mkr-infinity/optimai-cli.git && cd optimai-cli
   cp .env.example .env
   # Enter TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS in .env
   docker compose up -d
   ```

### 🐍 Option 2: Local Native Python (Bare-Metal)
1. Set up a Python 3.12 environment:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Download the official OptimAI CLI binary for your operating system:
   * **Linux**:
     ```bash
     curl -fsSL https://cli-node.optimai.network/optimai_cli_ubuntu -o optimai-cli
     chmod +x optimai-cli && sudo mv optimai-cli /usr/local/bin/
     ```
   * **macOS (Universal)**:
     ```bash
     curl -fsSL https://cli-node.optimai.network/optimai_cli_darwin_universal2 -o optimai-cli
     chmod +x optimai-cli && sudo mv optimai-cli /usr/local/bin/
     ```
   * **Windows (PowerShell)**:
     ```powershell
     curl.exe -fL https://cli-node.optimai.network/optimai_cli_windows.exe -o optimai-cli.exe
     ```
3. Copy config and launch:
   ```bash
   cp .env.example .env
   # Enter your TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS in .env
   python -m bot.main
   ```
   *(The bot automatically detects your local machine environment, auto-loads `.env`, resolves the local `optimai-cli` binary, reuses host `~/.optimai` credentials if present, and routes runtime state to `./data`)*.

### 📱 Option 3: Android Phone / Tablet (Termux)
You can run the node 24/7 on your Android device without a PC or paid VPS:
1. Install **Termux from F-Droid** ([Download](https://f-droid.org/en/packages/com.termux/)).
2. Run the one-shot automated installer in Termux:
   ```bash
   pkg update -y && pkg install -y git curl
   git clone https://github.com/mkr-infinity/optimai-cli.git
   cd optimai-cli
   bash setup-termux.sh
   ```
3. Configure `.env` and launch your 24/7 background session:
   ```bash
   nano .env
   bash run-termux.sh
   ```
*(Detailed guide, wake lock setup, and PRoot x86_64 emulation in [docs/DEPLOY-TERMUX.md](docs/DEPLOY-TERMUX.md))*.

---

## 5. Bot Commands & Official CLI Mapping

Every command sent to the bot targets the official upstream `optimai-cli` directly — no separate account or custom credentials are required.

| Telegram Command | Official CLI Command | Allowed Users | Description |
|---|---|---|---|
| `/login [email pwd]` | `optimai-cli auth login` | Admin | Sign in via browser OAuth URL or direct email/password |
| `/login_legacy` | `optimai-cli auth login --legacy` | Admin | Direct interactive email and password login |
| `/logout` | `optimai-cli auth logout` | Admin | Sign out from OptimAI and clear stored credentials |
| `/auth_status` (or `/auth`) | `optimai-cli auth status` | Admin | Check live OptimAI account login status |
| `/me` | `optimai-cli auth me` | Admin | View authenticated OptimAI profile & Telegram details |
| `/start` | Welcome Overview | Admin | Rich welcome card: system diagnostics, live node status & quick actions |
| `/start_node` | `optimai-cli node start` | Admin | Start the node process and Docker AI miner containers |
| `/stop_node` (or `/stop`) | `optimai-cli node stop` | Admin | Stop the node and terminate all background mining workloads & Docker containers |
| `/restart_node` | Stop + Start | Admin | Restart node & reset circuit breaker |
| `/status` | `optimai-cli node status` | Admin | Live status: node uptime, Docker health, crash count |
| `/screen` | Detached session | Admin | View 24/7 background worker session, PID & interactive buttons |
| `/rewards` | `optimai-cli rewards balance` | Admin | Display current OptimAI points & rewards balance |
| `/logs` (or `/log`) | `tail node.log` | Admin | View the last 40 lines of node logs in Telegram |
| `/watch [sec]` | `tail -f node.log` | Admin | Live streaming log tail in Telegram (10–600s) |
| `/update_cli` (or `/update`)| `optimai-cli update` | Admin | Check for and install upstream CLI updates |
| `/cancel` | Cancel pexpect child | Admin | Cancel an active `/login` session |
| `/version` | `optimai-cli --version` | Admin | Show bot and CLI release versions |
| `/ping` | Control-plane check | Admin | Check bot responsiveness & latency (under 50ms) |
| `/uptime` | Supervisor metric | Admin | View bot and node supervisor uptime |
| `/disk` | `shutil.disk_usage` | Admin | View VPS volume storage usage |
| `/system` | Platform diagnostics | Admin | Diagnostics (OS, distro, CPU architecture, RAM) |
| `/healthcheck` | Subsystem check | Admin | Test internal subsystems (supervisor, data, binary) |
| `/help` | — | Admin | Show full command reference |
| `/id` | — | **Everyone** | Show numeric Telegram ID (budgeted for strangers) |

### 🖥️ Viewing Logs in Terminal
You can view and stream the live OptimAI node logs directly inside your terminal at any time:
```bash
# Option 1: Via Makefile
make logs
# or
make log

# Option 2: Via Python CLI
python -m bot.main logs
# or
python -m bot.main /log

# Option 3: Via helper script
bash scripts/logs.sh
```

### 🖥️ Detached 24/7 Background Session (`/screen`)
In the official OptimAI guide, users run `screen -S optimai` to keep the CLI running in the background. Our bot manages the node in an autonomous background session automatically:
- Send `/screen` in Telegram to inspect the background worker, view active PID, uptime, and latest output snapshot.
- Interactive buttons allow you to refresh status, live-watch logs, or stop/start the node directly.
- Concurrent updates ensure you can send subsequent commands (`/status`, `/rewards`, `/logs`, `/update`) at any time without blocking or interrupting the running node.

### 🔐 Persistent Credentials Database & Clean `/logout`
- **Persistent Database (`credentials.json`)**: When you log in (via browser OAuth or `/login <email> <password>`), the bot stores the session snapshot into a secure, owner-only (`0600`) database file inside `./data`.
- **Automatic Recovery**: If temporary container files or `auth.json` are lost during a rebuild, the bot restores authentication from the database automatically.
- **Clean Purge on `/logout`**: Sending `/logout` cleanly clears the credentials database, host configs, and active session tokens.

### 🔄 Automatic Updates & Real-Time Error Reporting
- **Auto-Download**: If the `optimai-cli` binary is missing on boot, the bot automatically downloads the official release for your operating system and architecture.
- **Auto-Update**: When an update signal is detected in the node log (`Important OptimAI CLI update available`), the supervisor updates the binary and restarts the mining node automatically.
- **Real-Time Error Reporting**: If any command fails or encounters an exception, the exact error details are surfaced directly in Telegram.

---

## 6. Configuration Reference (`.env`)

| Variable | Required? | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | **Yes** | — | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_IDS` | **Yes** | — | Comma-separated admin Telegram IDs |
| `NODE_AUTO_START` | No | `true` | Auto-start mining node on boot if desired=running |
| `LOG_TAIL_LINES` | No | `40` | Number of lines returned by `/logs` |
| `WATCH_SECONDS` | No | `120` | Default streaming duration for `/watch` |
| `LOGIN_TTL_MINUTES` | No | `15` | Minutes before an uncompleted `/login` expires |
| `ENABLE_HEALTH_PORT` | No | `""` | Optional HTTP health port (`GET /health -> 200 OK`) |
| `CONTACT_USERNAME` | No | `mkr_infinity` | Telegram handle displayed to unauthorized strangers |
| `UNAUTH_MAX_MESSAGES` | No | `3` | Max replies a stranger receives before permanent mute |

*(See [docs/ENV-VARS.md](docs/ENV-VARS.md) for full catalog).*

---

## 7. How the 24/7 Guarantee Works

Your node stays online through 3 automated protection layers:

```
┌────────────────────────────────────────────────────────┐
│  Layer 1: Docker Restart Policy (unless-stopped)       │  → Resurrects container on host reboot
├────────────────────────────────────────────────────────┤
│  Layer 2: Desired-State Supervisor (state.json)        │  → Auto-restarts node process on crash
├────────────────────────────────────────────────────────┤
│  Layer 3: Circuit Breaker (5 consecutive crash limit)  │  → Prevents spam; alerts owner to fix
└────────────────────────────────────────────────────────┘
```

* **Crash Recovery**: If the node process crashes, the supervisor restarts it with exponential backoff: **5s → 15s → 60s → 300s**.
* **Circuit Breaker**: After 5 consecutive failures, auto-restart pauses and sends an alert so you can check `/logs`. Sending `/restart_node` resets the breaker.
* **Persistent Stop**: If you send `/stop_node`, the node **stays stopped** even if the VPS restarts. It will never silently resurrect unless you send `/start_node`.

---

## 8. Hosting Provider Mode (Promo Funnel)

When strangers find your bot and message it, they receive:
```text
⛔️ You are not authorized to use this bot.

To host your own OptimAI node server (paid), contact @mkr_infinity.
```
* **Anti-Spam Guarantee**: Each unauthorized user has a lifetime reply budget (default: 3 replies). Once exhausted, they are permanently muted.
* Settings are fully configurable via `CONTACT_USERNAME`, `UNAUTHORIZED_MESSAGE`, and `UNAUTH_MAX_MESSAGES`.

---

## 9. Google Cloud (GCP) 24/7 Mining Deployment

> [!TIP]
> **Why Google Cloud Compute Engine instead of Railway / Render?**
> Serverless container platforms (Railway, Render, Heroku) do not provide a real host Docker daemon (`docker.sock`). On those platforms, `/start_node` fails because mining containers cannot be spawned.
>
> **Google Cloud Compute Engine gives you 100% full mining capability:**
> * ⚡ **Dedicated Docker Engine**: Native `/var/run/docker.sock` access for unrestricted mining.
> * 🎁 **$300 Free Credits / Free Tier**: New Google Cloud accounts get $300 in credits, and `e2-micro` instances are free-tier eligible.
> * 🌐 **Always-On Uptime**: Virtual machines never sleep or timeout like web container platforms.
> * 💻 **Browser SSH**: 1-click terminal in your browser without SSH key setup.

### Quick Deploy with `gcloud` CLI:
```bash
# Launch a dedicated Ubuntu 24.04 instance on Google Cloud
gcloud compute instances create optimai-node \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2404-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=25GB

# Connect to your Google Cloud VM
gcloud compute ssh optimai-node --zone=us-central1-a
```

> [!CAUTION]
> **Google Cloud Mining Risks & Precautions:**
> 1. **Acceptable Use Policy (AUP)**: Google Cloud prohibits cryptocurrency/token mining on **Free Trial accounts** without written authorization. Accounts violating this policy can be automatically suspended.
> 2. **Unexpected Charges**: On paid accounts, sustained high CPU and egress traffic can incur costs once credits lapse. Always configure budget alerts in Google Cloud Billing.
> 3. **Persistent Backups**: Ensure you periodically backup `state.json` (`bash scripts/backup-data.sh`) to avoid losing node state if an instance is stopped.
> 4. **Dedicated Alternatives**: If you prefer a platform with zero policy restrictions on node mining, consider budget VPS hosts (e.g. Hetzner, Contabo) or your local desktop.

*(See [docs/DEPLOY-GCP.md](docs/DEPLOY-GCP.md) for the complete Google Cloud guide).*

---

## 10. Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `Not authenticated` error | Session expired or first run | Run `/login` or `/login email password` |
| Bot not responding | Invalid token or network down | Check `TELEGRAM_BOT_TOKEN` and run `docker compose logs -f` |
| `no Docker daemon here` | Running on container PaaS or socket unmounted | Deploy on Google Cloud Compute Engine VM or start local Docker |
| Node stopped unexpectedly | Crashed 5 times in a row | Send `/logs` to see the error, fix it, then send `/restart_node` |
| Outdated CLI warning | Upstream released an update | Run `/update_cli` in Telegram or rebuild container |

*(See [docs/RUNBOOK.md](docs/RUNBOOK.md) for in-depth incident recovery).*

---

## 11. Growth Ideas

* **Multi-Node Fleet**: Manage 10+ node servers across different Google Cloud zones from a single Telegram channel.
* **Auto-Claim Rewards**: Automate periodic rewards balance scrapes and daily balance summaries.
* **Client Hosting Service**: Charge clients monthly hosting fees to run nodes for them under your referral code.

---

## 12. Security Checklist

* 🔒 **Never commit `.env`** — it contains your live Telegram token.
* 🔒 **Keep `TELEGRAM_ALLOWED_IDS` minimal** — anyone in this list can control your node.
* 🔒 **Strict Firewall** — The bot only uses outbound polling; no open inbound server ports are needed on Google Cloud.

---

## 13. Documentation Index & Guides Directory

A focused set of production guides and technical runbooks is maintained in the [`docs/`](docs/) directory (see **[docs/README.md](docs/README.md)** for the complete guide directory).

### 🚀 Deployment & Platform Runbooks
* **[DEPLOY-VPS.md](docs/DEPLOY-VPS.md)** — *Primary deployment guide*. Automated multi-distro setup on Ubuntu, Debian, Arch, Fedora, openSUSE, and Alpine via `setup-vps.sh`.
* **[DEPLOY-GCP.md](docs/DEPLOY-GCP.md)** — *Read when deploying on Google Cloud*. Step-by-step Compute Engine VM setup, browser SSH, and essential warnings on Free Trial account mining restrictions.
* **[DEPLOY-TERMUX.md](docs/DEPLOY-TERMUX.md)** — *Read when mining on an Android phone or tablet*. F-Droid setup, wake lock background persistence, and on-device ARM64 PRoot Ubuntu x86_64 emulation.
* **[DEPLOY-RAILWAY.md](docs/DEPLOY-RAILWAY.md)** — *Read when running on Railway*. Explains Railway `$PORT` healthchecks and control-plane mode.

### 🛠️ Daily Operations & Troubleshooting
* **[RUNBOOK.md](docs/RUNBOOK.md)** — *Read when the node crashes or throws errors*. Incident response procedures, crash diagnostics, circuit breaker resets, and log inspection.
* **[DAILY-OPS.md](docs/DAILY-OPS.md)** — *Read for daily routine checks*. Quick 2-minute operator checklist to verify node health, rewards balance, and disk space.
* **[TROUBLESHOOTING-SWAP.md](docs/TROUBLESHOOTING-SWAP.md)** — *Read on low-RAM servers (512MB-1GB)*. How to allocate swap memory to avoid Linux OOM kills.

### 💾 Data Safety & Upgrades
* **[BACKUP-RESTORE.md](docs/BACKUP-RESTORE.md)** — *Read to back up credentials*. Snapshot commands for `./data` and host `~/.optimai` credential stores.
* **[UPGRADING.md](docs/UPGRADING.md)** — *Read when upgrading versions*. Zero-downtime container upgrades that preserve credentials and state.

### ⚙️ Architecture & Technical Reference
* **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — *Read to understand internal design*. Architecture diagrams showing Supervisor, pexpect worker, and Docker engine IPC.
* **[ENV-VARS.md](docs/ENV-VARS.md)** — *Read to customize environment variables*. Complete dictionary of every setting with defaults, ranges, and validation rules.
* **[FAQ.md](docs/FAQ.md)** — *Read for quick answers*. Frequently asked questions on referral rewards, Docker permissions, and login sessions.

---

### Attribution

**OptimAI Telegram Node v1.3.0** — Created by **Mohammad Kaif Raja (mkr-infinity)**
[Telegram @mkr_infinity](https://t.me/mkr_infinity) · [Support](https://buymeacoffee.com/mkr_infinity) · UPI: `mkr-infinity@ybl`
