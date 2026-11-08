# ⛏️ OptimAI Telegram Bot (v1.9.0)

> Autonomous 24/7 supervisor and remote Telegram management bot for the official [OptimAI CLI Node](https://github.com/OptimaiNetwork/OptimAI-CLI-Node).

[![CI](https://github.com/mkr-infinity/cli-optimai/actions/workflows/ci.yml/badge.svg)](https://github.com/mkr-infinity/cli-optimai/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Telegram](https://img.shields.io/badge/support-%40mkr__infinity-blue)](https://t.me/mkr_infinity)

---

## ⚡ Architecture

```
┌──────────────────┐    Polling     ┌───────────────────────┐   Subprocess    ┌──────────────┐   Docker Sock   ┌─────────────┐
│  Telegram App    │ <────────────> │  Telegram Bot         │ <─────────────> │ optimai-cli  │ <─────────────> │ Docker      │
│  (Remote Access) │ (No open ports)│  (Supervisor Loop)    │  Auto-Restart   │ + Local Auth │   Containers    │ AI Miner    │
└──────────────────┘                └───────────────────────┘                 └──────────────┘                 └─────────────┘
```

- **24/7 Supervisor:** Keeps the node alive with exponential backoff and circuit-breaker auto-recovery.
- **Dual Launch:** Starts both the Telegram supervisor bot and the OptimAI AI miner with a single command.
- **Remote Control:** Authenticate, control the node, monitor earnings, and view live logs from Telegram.
- **Cross-Platform:** Runs on Linux VPS, Google Cloud VM, Android (Termux), GitHub Codespaces, macOS, and Windows.

---

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/mkr-infinity/cli-optimai.git && cd cli-optimai
bash setup.sh
```
`setup.sh` auto-detects your environment (Linux, Termux, macOS, Windows, Codespaces), installs required dependencies, and sets up `.env`.

### 2. Configure Credentials
When prompted during setup, or by editing `.env`:
- `TELEGRAM_BOT_TOKEN`: Your bot token from [@BotFather](https://t.me/BotFather)
- `TELEGRAM_ALLOWED_IDS`: Your Telegram user ID from [@userinfobot](https://t.me/userinfobot) (or run `/id` in the bot)

### 3. Launch
```bash
bash start.sh
```
*(On Windows: run `.\start.bat`)*

---

## 📱 Telegram Commands

| Command | Action | Description |
|---|---|---|
| `/start` | Overview | Bot dashboard, node state, and quick action buttons |
| `/login` | `auth login` | Sign in with OptimAI browser flow |
| `/login_legacy <email> <pwd>` | `auth login --legacy` | Sign in directly via email & password |
| `/auth_status` | `auth status` | Check account authentication status |
| `/me` | `auth me` | View account details and node identifier |
| `/start_node` | `node start` | Start the official mining process and Docker containers |
| `/stop_node` | `node stop` | Stop node and background mining containers |
| `/restart_node` | Restart | Gracefully restart the mining node |
| `/status` | `node status` | View uptime, Docker health, and crash statistics |
| `/rewards` | `rewards balance` | Display mined points and rewards balance |
| `/rewardadded [on\|off]` | Alerts | Toggle Telegram alerts when rewards increase |
| `/logs` | View Logs | Display recent node output lines |
| `/watch [sec]` | Live Stream | Stream live node output directly in Telegram (10–600s) |
| `/update_cli` | `update` | Update the official OptimAI CLI binary |
| `/id` | User Info | Show your Telegram user ID *(public)* |

---

## ⚙️ Configuration (`.env`)

| Variable | Required | Default | Description |
|---|:---:|:---:|---|
| `TELEGRAM_BOT_TOKEN` | **Yes** | — | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_IDS` | **Yes** | — | Comma-separated admin Telegram IDs |
| `NODE_AUTO_START` | No | `true` | Automatically run `optimai-cli node start` on boot |
| `LOG_TAIL_LINES` | No | `40` | Number of lines returned by `/logs` |
| `WATCH_SECONDS` | No | `120` | Streaming duration for `/watch` (seconds) |

---

## 🗺️ Deployment Guides

| Platform | Recommended Setup | Guide |
|---|---|---|
| ☁️ **Linux VPS / Server** | `sudo bash setup-vps.sh && bash start.sh` | [docs/DEPLOY-VPS.md](docs/DEPLOY-VPS.md) |
| 📱 **Android Phone (Termux)** | `bash setup-termux.sh && bash start.sh` | [docs/DEPLOY-TERMUX.md](docs/DEPLOY-TERMUX.md) |
| 🌐 **Google Cloud (GCP)** | `sudo bash setup-vps.sh && bash start.sh` | [docs/DEPLOY-GCP.md](docs/DEPLOY-GCP.md) |
| 💻 **GitHub Codespaces** | `bash setup-codespaces.sh && bash start.sh` | Codespaces auto-config |
| 🪟 **Windows (PC)** | `.\setup-windows.bat && .\start.bat` | Native PowerShell/CMD |
| 🛠️ **Troubleshooting** | Diagnostics, crash recovery & logs | [docs/RUNBOOK.md](docs/RUNBOOK.md) |

---

## 🔧 Common Troubleshooting

| Issue | Quick Fix |
|---|---|
| **Not authenticated** | Run `/login_legacy <email> <password>` in Telegram or `optimai-cli auth login --legacy` in terminal. |
| **Docker not running** | Start Docker service (`sudo systemctl start docker` or open Docker Desktop), then run `/start_node`. |
| **Node already running** | Run `/restart_node` in Telegram, or `make stop && make start` in terminal. |
| **Port / Container conflict** | Run `make clean-containers` or restart with `start.sh` and pick `1) Clean Install`. |

---

## 👤 Author & Support

- **Author**: Mohammad Kaif Raja ([@mkr-infinity](https://github.com/mkr-infinity))
- **Telegram**: [@mkr_infinity](https://t.me/mkr_infinity)
- **Support**: [Buy Me a Coffee](https://buymeacoffee.com/mkr_infinity) · UPI: `mkr-infinity@ybl`
- **Official OptimAI**: [optimai.network](https://optimai.network) · [Referral Link (Code: 646D12E7)](https://node.optimai.network/register?ref=646D12E7)
