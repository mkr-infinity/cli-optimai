# 📚 OptimAI Telegram Node — Documentation Directory

Welcome to the official documentation directory for **OptimAI Telegram Node**. Every guide below is practical, scope-honest, and maintained for production operations.

---

## 🧭 Core Documentation Index

### 🚀 1. Deployment Guides (Where to Run Your Node)

| Guide | When to Read / Purpose |
|---|---|
| **[DEPLOY-VPS.md](DEPLOY-VPS.md)** | **Deploying on Bare-Metal or Cloud VPS Hosts** (DigitalOcean, Hetzner, Linode, AWS EC2, OVH).<br>Explains multi-distro automated installation via `setup-vps.sh` (Debian, Ubuntu, Arch, Fedora, openSUSE, Alpine). |
| **[DEPLOY-GCP.md](DEPLOY-GCP.md)** | **Deploying on Google Cloud (GCP) Compute Engine**.<br>Step-by-step VM creation in browser SSH, Docker setup, and critical guidance on Google Cloud Free Trial mining restrictions & risk mitigation. |
| **[DEPLOY-TERMUX.md](DEPLOY-TERMUX.md)** | **Running 24/7 on an Android Phone or Tablet**.<br>Explains F-Droid installation, wake-lock background persistence, battery saver exemption, and on-device ARM64 PRoot Ubuntu x86_64 emulation. |
| **[DEPLOY-RAILWAY.md](DEPLOY-RAILWAY.md)** | **Deploying on Railway or Container PaaS**.<br>Explains Railway `$PORT` binding, HTTP healthchecks, and the control-plane mode (for monitoring when host Docker socket is absent). |

---

### 🛠️ 2. Operations & Troubleshooting

| Guide | When to Read / Purpose |
|---|---|
| **[RUNBOOK.md](RUNBOOK.md)** | **Incident response & troubleshooting**.<br>What to do when something breaks, circuit breaker resets, log inspection, and recovery flowcharts. |
| **[DAILY-OPS.md](DAILY-OPS.md)** | **Day-to-day operator routine**.<br>Quick 2-minute checklist to verify node health, rewards balance, supervisor status, and disk storage from Telegram. |
| **[TROUBLESHOOTING-SWAP.md](TROUBLESHOOTING-SWAP.md)** | **Running on low-RAM VPS instances (512MB-1GB)**.<br>How to allocate a 2GB-4GB swapfile so Docker AI mining containers never trigger the Linux OOM killer. |

---

### 💾 3. Data Safety & Lifecycle

| Guide | When to Read / Purpose |
|---|---|
| **[BACKUP-RESTORE.md](BACKUP-RESTORE.md)** | **Backing up or restoring node credentials and state**.<br>One-line commands to take clean tarball snapshots of `./data` and host `~/.optimai` directories. |
| **[UPGRADING.md](UPGRADING.md)** | **Upgrading between releases safely**.<br>Step-by-step upgrade commands that preserve authentication credentials, state, and rate limits without downtime. |

---

### ⚙️ 4. Architecture & Technical Reference

| Guide | When to Read / Purpose |
|---|---|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | **Understanding internal bot architecture**.<br>Visual architecture diagrams showing communication between Supervisor, pexpect login manager, and Docker engine. |
| **[ENV-VARS.md](ENV-VARS.md)** | **Customizing configuration settings**.<br>Exhaustive dictionary of all environment variables with defaults, types, valid ranges, and fallback behavior. |
| **[FAQ.md](FAQ.md)** | **Frequently asked questions & quick answers**.<br>Common answers regarding referral rewards, Google Cloud mining policies, Docker permissions, and login sessions. |

---

### Root Documentation & Community Policies

* **[README.md](../README.md)** — Project homepage, visual architecture, 5-step quickstart, and command reference.
* **[ROADMAP.md](../ROADMAP.md)** — Strategic milestones, version delivery ledger, and non-goals.
* **[CHANGELOG.md](../CHANGELOG.md)** — Version release notes and change history.
* **[CONTRIBUTING.md](../CONTRIBUTING.md)** — Contributor guidelines and workflow.
* **[SECURITY.md](../SECURITY.md)** — Vulnerability reporting and security disclosure policy.
* **[CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)** — Community standards and contributor etiquette.
* **[LICENSE](../LICENSE)** — Apache 2.0 open-source license.

---

### Root Documentation & Community Policies

* **[README.md](../README.md)** — Project homepage, visual architecture, 5-step quickstart, and command reference.
* **[CHANGELOG.md](../CHANGELOG.md)** — Version release notes and change history.
* **[ROADMAP.md](../ROADMAP.md)** — Project goals, feature milestones, and non-goals.
* **[CONTRIBUTING.md](../CONTRIBUTING.md)** — Contributor guidelines and pairing workflow.
* **[SECURITY.md](../SECURITY.md)** — Vulnerability reporting and security disclosure policy.
* **[CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)** — Community standards and contributor etiquette.
* **[LICENSE](../LICENSE)** — Apache 2.0 open-source license.
