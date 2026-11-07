# ⛏️ OptimAI Telegram Node (v1.3.0)

Autonomous 24/7 supervisor and Telegram management bot for the official OptimAI CLI Node.

[![CI](https://github.com/mkr-infinity/optimai-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/mkr-infinity/optimai-cli/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.3.0-orange)](CHANGELOG.md)
[![Telegram](https://img.shields.io/badge/support-%40mkr__infinity-blue)](https://t.me/mkr_infinity)

> [!IMPORTANT]
> **Official OptimAI Reference Notice:**  
> This project is a **24/7 autonomous supervisor and Telegram manager** that wraps the official `optimai-cli`. It is not an alternative documentation site. For native CLI documentation and hardware requirements, visit the official **[OptimAI CLI Node Repository](https://github.com/OptimaiNetwork/OptimAI-CLI-Node)**.  
> Need an OptimAI mining account? **[Register with Referral Code 646D12E7](https://node.optimai.network/register?ref=646D12E7)**.

```
┌──────────┐   outbound polling   ┌────────────────────┐   subprocess    ┌──────────────┐   docker.sock   ┌─────────────┐
│ Telegram │ <──────────────────> │ Telegram Bot       │ <─────────────> │ optimai-cli  │ <─────────────> │ Docker      │
│  Client  │     (no open ports)  │ (Supervisor Loop)  │   NODE_AUTO_... │ + Local Auth │    Workload     │ AI Miner    │
└──────────┘                      └────────────────────┘                 └──────────────┘                 └─────────────┘
```

---

## ⚡ Key Capabilities

* **24/7 Autonomous Supervisor**: Monitors the mining node with auto-restart on crash (exponential backoff 5s → 15s → 60s → 300s & 5-crash circuit breaker).
* **Simultaneous Auto-Start**: Running `bash start.sh` launches both the Telegram bot supervisor and the OptimAI AI miner automatically.
* **Full Remote Control**: Manage login, node state, rewards, live log streaming, and updates directly through Telegram.
* **Persistent Credential Database**: Automatically restores authentication credentials across host reboots and container rebuilds.
* **Universal Deployment**: Runs seamlessly on Cloud VPS, Google Cloud Compute Engine, Local PC, or Android Phone (Termux).

---

## 🚀 Quickstart: 3 Steps to Launch

### 1. Clone & Automated Setup
```bash
git clone https://github.com/mkr-infinity/optimai-cli.git && cd optimai-cli
bash setup.sh
```

> [!NOTE]
> `bash setup.sh` automatically detects your platform (GitHub Codespaces, Android Termux, Linux VPS, macOS, or Windows), installs required system packages, downloads and primes the official OptimAI CLI binary, and configures `.env`.

> [!TIP]
> **Interactive Credentials Intake (60s Timeout):** During setup, the installer prompts you to input your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_IDS`. If entered, the bot and AI miner auto-launch immediately! If skipped (by pressing Enter or waiting 60s), you can manually enter them in `.env`.

> [!IMPORTANT]
> **Mining directly on an Android smartphone or tablet?**  
> Refer to the dedicated **[Android Termux 24/7 Mobile Mining Guide](docs/DEPLOY-TERMUX.md)** for battery management, wake lock setup, and on-device ARM64 PRoot emulation.

### 2. Configure Telegram Credentials (If Skipped)
If you skipped interactive setup, edit `.env` with your editor of choice (`nano .env` or `notepad .env`):
* `TELEGRAM_BOT_TOKEN`: Token obtained from [@BotFather](https://t.me/BotFather).
* `TELEGRAM_ALLOWED_IDS`: Your numeric Telegram ID (obtain via [@userinfobot](https://t.me/userinfobot) or send `/id` to the bot).

### 3. Start Bot & Miner
```bash
bash start.sh
# or: make start (on Windows: .\start.bat)
```

> [!TIP]
> `bash start.sh` auto-detects your platform: it runs via Docker Compose when Docker is present, or through a detached `screen` session for native Linux, GitHub Codespaces, and Android Termux. Both the Telegram supervisor bot and the OptimAI AI miner launch together automatically.

---

## 🗺️ Deployment Platforms

| Platform | Quick Command | Detailed Guide |
|---|---|---|
| **GitHub Codespaces** (1-Click in-browser cloud mining) | `bash setup-codespaces.sh && bash start.sh` | Open in Codespaces, configure `.env`, and start |
| **Cloud VPS / Linux Host** (Ubuntu, Debian, Arch, Fedora) | `sudo bash setup-vps.sh && bash start.sh` | [docs/DEPLOY-VPS.md](docs/DEPLOY-VPS.md) |
| **Google Cloud (GCP)** (Compute Engine VM) | `sudo bash setup-vps.sh && bash start.sh` | [docs/DEPLOY-GCP.md](docs/DEPLOY-GCP.md) |
| **Android Phone / Tablet** (Termux 24/7 mobile mining) | `bash setup-termux.sh && bash start.sh` | [docs/DEPLOY-TERMUX.md](docs/DEPLOY-TERMUX.md) |
| **Windows PC** (Native PowerShell & CMD background node) | `.\setup-windows.bat && .\start.bat` | Run PowerShell setup and launch |
| **macOS** (Apple Silicon M1-M4 & Intel Mac) | `bash setup.sh && bash start.sh` | Run universal setup and launch |

> [!WARNING]
> Google Cloud's Acceptable Use Policy restricts computational and crypto mining on **Free Trial ($300 credit) accounts**. For a suspension-free experience, use standard paid accounts, dedicated VPS hosts, or Android Termux.

---

## 📱 Telegram Command Reference

All commands directly interface with the official upstream `optimai-cli`:

| Command | Upstream CLI Command | Access | Description |
|---|---|---|---|
| `/start` | Welcome Overview | Admin | Live system diagnostics, node status, and quick buttons |
| `/login [email pwd]` | `optimai-cli auth login` | Admin | Authenticate via browser OAuth URL or email/password |
| `/logout` | `optimai-cli auth logout` | Admin | Sign out and purge local stored credentials |
| `/auth_status` | `optimai-cli auth status` | Admin | Check live OptimAI account connection status |
| `/me` | `optimai-cli auth me` | Admin | View authenticated OptimAI profile and node details |
| `/start_node` | `optimai-cli node start` | Admin | Start mining process and Docker AI miner containers |
| `/stop_node` | `optimai-cli node stop` | Admin | Stop node and terminate background mining containers |
| `/restart_node` | Stop + Start | Admin | Gracefully restart node and reset circuit breaker |
| `/status` | `optimai-cli node status` | Admin | Live status: uptime, Docker health, crash counters |
| `/screen` | Detached session | Admin | View background session, worker PID, and live snapshot |
| `/rewards` | `optimai-cli rewards balance` | Admin | Display current OptimAI earned points and rewards |
| `/rewardadded [on\|off]` | Reward Supervisor | Admin | Toggle real-time Telegram alerts on mining reward payout |
| `/logs` (or `/log`) | `tail -n 40 node.log` | Admin | View last 40 lines of node logs in Telegram |
| `/watch [sec]` | `tail -f node.log` | Admin | Live streaming log tail in Telegram (10–600s) |
| `/update_cli` | `optimai-cli update` | Admin | Check for and install upstream CLI updates |
| `/env` | Environment Reader | Admin | View active configuration (.env) with masked secrets |
| `/setenv [KEY VAL]` | Environment Editor | Admin | Update .env configuration and runtime settings directly |
| `/ping` | Control-plane probe | Admin | Check bot response latency (< 50ms) |
| `/uptime` | Supervisor metric | Admin | View bot and node supervisor uptime |
| `/help` | — | Admin | Show full command reference |
| `/id` | — | **Public** | Show numeric Telegram ID (budgeted for strangers) |

### 🖥️ Viewing Logs in Terminal
Stream live node logs in your terminal at any time:
```bash
make logs
# or: python -m bot.main logs
```

---

## ⚙️ Configuration Reference (`.env`)

| Variable | Required | Default | Description |
|---|:---:|:---:|---|
| `TELEGRAM_BOT_TOKEN` | **Yes** | — | Bot API token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_IDS` | **Yes** | — | Comma-separated admin Telegram user IDs |
| `NODE_AUTO_START` | No | `true` | Automatically start mining process when bot boots |
| `LOG_TAIL_LINES` | No | `40` | Default line count returned by `/logs` |
| `WATCH_SECONDS` | No | `120` | Default streaming duration for `/watch` (seconds) |
| `LOGIN_TTL_MINUTES` | No | `15` | Minutes before an interactive login session expires |
| `CONTACT_USERNAME` | No | `mkr_infinity` | Telegram handle displayed to unauthorized visitors |
| `UNAUTH_MAX_MESSAGES` | No | `3` | Max replies a stranger receives before permanent mute |

---

## 🔧 Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| `Not authenticated` | Session expired or first run | Send `/login` to sign in via browser or credentials |
| Bot not responding | Invalid bot token or network offline | Verify `TELEGRAM_BOT_TOKEN` in `.env` and run `make logs` |
| `no Docker daemon here` | Host Docker socket unmounted | Ensure Docker is active or deploy on a standard Linux VPS |
| Node stopped unexpectedly | Circuit breaker opened (5 crashes) | Check error in `/logs`, resolve, then send `/restart_node` |
| CLI update warning in `/status` | Upstream CLI release available | Send `/update_cli` in Telegram to auto-update |

> [!NOTE]
> For step-by-step incident response, circuit breaker recovery, and log inspection, see the **[Troubleshooting Runbook](docs/RUNBOOK.md)**.

---

## 📚 Complete Guides & Documentation Directory

Every deployment target, triage runbook, and project governance policy has a dedicated guide:

| Guide / Manual | Purpose & Target Audience | Link |
|---|---|---|
| 📱 **Android Termux 24/7 Mobile Mining** | Complete guide for running on Android devices, acquiring CPU wake-lock, and bridging ARM64 via PRoot emulation | [docs/DEPLOY-TERMUX.md](docs/DEPLOY-TERMUX.md) |
| ☁️ **Multi-Distro VPS Deployment** | Production setup on Ubuntu, Debian, Arch Linux, Fedora, CentOS, openSUSE, and Alpine hosts | [docs/DEPLOY-VPS.md](docs/DEPLOY-VPS.md) |
| 🌐 **Google Cloud Compute Engine (GCP)** | GCP VM deployment guide with Acceptable Use Policy compliance and billing safeguards | [docs/DEPLOY-GCP.md](docs/DEPLOY-GCP.md) |
| 🛠️ **Operational Runbook & Triage** | Crash diagnosis, circuit breaker recovery, container triage, log inspection, and system health restoration | [docs/RUNBOOK.md](docs/RUNBOOK.md) |
| 🤝 **Contributing & Development** | Developer setup, running the 150+ smoke test suite, code guidelines, and pull request procedures | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 🔒 **Security Policy & Reporting** | Responsible vulnerability disclosure, encrypted reporting channels, and security boundaries | [SECURITY.md](SECURITY.md) |
| 🗺️ **Milestones & Strategic Roadmap** | Product milestones ledger, release history, and planned supervisor capabilities | [ROADMAP.md](ROADMAP.md) |
| 📝 **Version Changelog** | Complete release notes, architectural enhancements, and bug fix ledger | [CHANGELOG.md](CHANGELOG.md) |

---

### Attribution & Author
**OptimAI Telegram Node v1.3.0** — Created by **Mohammad Kaif Raja (mkr-infinity)**  
[Telegram @mkr_infinity](https://t.me/mkr_infinity) · [Support](https://buymeacoffee.com/mkr_infinity) · UPI: `mkr-infinity@ybl`
