# 📚 OptimAI Telegram Node — Documentation Master Index

Welcome to the comprehensive documentation directory for **OptimAI Telegram Node**. Every guide is written to be practical, scope-honest, and actionable.

Use the quick guide below to find the exact document you need.

---

## 🧭 Documentation Roadmap (Why & When to Read)

### 🚀 1. Deployment Guides (Where to Run Your Node)

| Guide | When to Read / Purpose |
|---|---|
| **[DEPLOY-GCP.md](DEPLOY-GCP.md)** | **Deploying on Google Cloud (GCP) Compute Engine**.<br>Explains step-by-step VM creation in browser SSH, Docker setup, and critical guidance on Google Cloud Free Trial mining restrictions & risk mitigation. |
| **[DEPLOY-TERMUX.md](DEPLOY-TERMUX.md)** | **Running 24/7 on an Android Phone or Tablet**.<br>Explains F-Droid installation, wake-lock background persistence, battery saver exemption, and on-device ARM64 PRoot Ubuntu x86_64 emulation. |
| **[DEPLOY-VPS.md](DEPLOY-VPS.md)** | **Deploying on Bare-Metal or Cloud VPS Hosts** (DigitalOcean, Hetzner, Linode, AWS EC2, OVH).<br>Explains multi-distro automated installation via `setup-vps.sh` (Debian, Arch, Fedora, openSUSE, Alpine). |
| **[DEPLOY-RAILWAY.md](DEPLOY-RAILWAY.md)** | **Deploying on Railway or Container PaaS**.<br>Explains Railway `$PORT` binding, HTTP healthchecks, and the control-plane mode (for monitoring when host Docker socket is absent). |

---

### 🛠️ 2. Daily Operations, Runbooks & Troubleshooting

| Guide | When to Read / Purpose |
|---|---|
| **[RUNBOOK.md](RUNBOOK.md)** | **When something breaks or the node crashes repeatedly**.<br>Step-by-step incident response procedures, circuit breaker resets, log inspections, and recovery flowcharts. |
| **[DAILY-OPS.md](DAILY-OPS.md)** | **Day-to-day operator routine**.<br>Quick 2-minute checklist to verify node health, rewards balance, supervisor status, and disk storage from Telegram. |
| **[MAINTENANCE.md](MAINTENANCE.md)** | **Routine volume & system maintenance**.<br>How to prune old Docker volumes, check log file rotation, and safely restart servers without losing state. |
| **[DISASTER-RECOVERY.md](DISASTER-RECOVERY.md)** | **Recovering from cold reboots, power cuts, or server crashes**.<br>How `credentials.json` and `state.json` automatically restore mining sessions without user intervention. |
| **[ERROR-CATALOG.md](ERROR-CATALOG.md)** | **Decoding unfamiliar errors or CLI exit codes**.<br>Complete catalog mapping CLI exit codes (0, 1, 2, 64, 126, 127) and error messages to exact solutions. |
| **[BACKUP-RESTORE.md](BACKUP-RESTORE.md)** | **Backing up or restoring node credentials and data**.<br>One-line commands to take clean tarball snapshots of `./data` and host `~/.optimai` directories. |
| **[STORAGE.md](STORAGE.md)** | **Understanding how state and credentials are saved**.<br>Explains volume mounts, atomic temporary file replacement, and database safety guarantees. |
| **[STORAGE-BACKUP-POLICY.md](STORAGE-BACKUP-POLICY.md)** | **Enterprise backup policy and RPO/RTO objectives**.<br>Formal retention policies, snapshot intervals, and disaster recovery recovery-point targets. |
| **[TROUBLESHOOTING-SWAP.md](TROUBLESHOOTING-SWAP.md)** | **Running on low-RAM VPS instances (512MB-1GB)**.<br>How to allocate a 2GB-4GB swapfile so Docker AI mining containers never trigger the Linux OOM killer. |
| **[MIGRATION.md](MIGRATION.md)** | **Migrating your node from one server to another**.<br>Zero-downtime migration steps to transfer credentials and state without re-authenticating. |

---

### 🔐 3. Security, Hardening & Compliance

| Guide | When to Read / Purpose |
|---|---|
| **[SECURITY-CHECKLIST.md](SECURITY-CHECKLIST.md)** | **Production server hardening checklist**.<br>Must-read before running in production: firewall rules, token protection, and user permission limits. |
| **[SECRETS-MANAGEMENT.md](SECRETS-MANAGEMENT.md)** | **Understanding how API tokens and credentials are kept safe**.<br>Explains `0600` owner-only database permissions, `.env` gitignore protection, and memory-only storage. |
| **[CONTAINER-SECURITY.md](CONTAINER-SECURITY.md)** | **Container isolation & privilege boundaries**.<br>Detailed security review of the static Docker client, socket mount boundaries, and unprivileged user execution. |
| **[SSH-PRACTICES.md](SSH-PRACTICES.md)** | **Hardening VPS SSH access**.<br>How to disable root password login, configure ed25519 keys, and implement fail2ban for brute-force protection. |
| **[THREAT-MODEL.md](THREAT-MODEL.md)** | **Evaluating system threats and attack surfaces**.<br>Formal threat modeling covering Telegram bot attacks, prompt injection, and host escape defenses. |
| **[SECURITY-INCIDENT.md](SECURITY-INCIDENT.md)** | **Emergency response if a bot token or server is compromised**.<br>Immediate containment playbooks, token revocation steps, and forensic auditing commands. |
| **[AUDIT-TRAIL.md](AUDIT-TRAIL.md)** | **Reviewing administrative actions & stranger visits**.<br>Explains how admin commands, authentication sessions, and unauthorized pings are logged for auditing. |

---

### ⚙️ 4. Configuration, Architecture & Engineering Specs

| Guide | When to Read / Purpose |
|---|---|
| **[ENV-VARS.md](ENV-VARS.md)** | **Customizing configuration settings**.<br>Exhaustive dictionary of all environment variables with defaults, types, valid ranges, and fallback behavior. |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | **Understanding internal bot architecture**.<br>Visual architecture diagrams showing communication between Supervisor, pexpect login manager, and Docker engine. |
| **[STATE-MACHINE.md](STATE-MACHINE.md)** | **Understanding the supervisor state engine**.<br>State transitions covering desired state (`running` vs `stopped`), crash detection, backoff schedule, and circuit breakers. |
| **[API.md](API.md)** | **Technical specification of Telegram bot commands**.<br>Detailed IPC input/output contracts, argument parsing, rate limits, and permission gates for all 19 commands. |
| **[DOCKER-COMPOSE-SPECS.md](DOCKER-COMPOSE-SPECS.md)** | **Customizing Docker Compose configurations**.<br>Deep dive into volume bindings, environment propagation, restart policies, and healthcheck endpoints. |
| **[CONTAINER-RESOURCE-LIMITS.md](CONTAINER-RESOURCE-LIMITS.md)** | **Capping CPU and RAM usage**.<br>How to apply Docker `--cpus` and `--memory` limits to prevent mining containers from overloading low-spec hosts. |
| **[RATE-LIMITING.md](RATE-LIMITING.md)** | **Configuring anti-spam & stranger budgets**.<br>Explains how unauthorized Telegram users are rate-limited and routed to your hosting promo funnel. |
| **[GLOSSARY.md](GLOSSARY.md)** | **Understanding technical terminology**.<br>Definitions for core terms: circuit breaker, exponential backoff, crawl4ai, pexpect, detached screen session. |
| **[SYSTEMD.md](SYSTEMD.md)** | **Running without Docker via native systemd**.<br>Complete unit file configuration (`/etc/systemd/system/optimai-bot.service`) for running natively on host boot. |

---

### 📊 5. Observability, Performance & Hardware

| Guide | When to Read / Purpose |
|---|---|
| **[OBSERVABILITY.md](OBSERVABILITY.md)** | **Monitoring uptime, logs, and health signals**.<br>Overview of log tailing, `/watch` streaming, HTTP healthcheck probes, and system uptime monitoring. |
| **[METRICS.md](METRICS.md)** | **Reviewing performance metrics**.<br>Explains internal supervisor metrics (uptime seconds, crash count, backoff level, Docker status). |
| **[METRICS-EXPORTER.md](METRICS-EXPORTER.md)** | **Connecting to Prometheus or Grafana**.<br>How to export bot metrics and node health data to external monitoring dashboards. |
| **[PERFORMANCE.md](PERFORMANCE.md)** | **Understanding low-latency optimizations**.<br>Explains concurrent updates in PTB, 15-second Docker version caching, and sub-50ms command execution. |
| **[BENCHMARKS.md](BENCHMARKS.md)** | **Reviewing system benchmark results**.<br>Measured memory consumption (<60MB RSS for bot), CPU utilization, and crash recovery timing. |
| **[HARDWARE.md](HARDWARE.md)** | **Choosing host hardware specifications**.<br>Hardware recommendations for web crawling, HTML normalization, and on-device quantized LLM tasks. |
| **[CAPACITY-PLANNING.md](CAPACITY-PLANNING.md)** | **Planning multi-node scale**.<br>Estimates bandwidth, CPU, and RAM consumption when scaling to 5, 10, or 25+ concurrent nodes. |
| **[TIME-SYNCHRONIZATION.md](TIME-SYNCHRONIZATION.md)** | **Preventing authentication clock-drift errors**.<br>How to configure chrony/NTP on Linux servers so token validations and OAuth timestamps never expire prematurely. |

---

### 🌐 6. Networking, DNS & Multi-Region

| Guide | When to Read / Purpose |
|---|---|
| **[NETWORKING.md](NETWORKING.md)** | **Understanding network traffic & firewall requirements**.<br>Explains why the bot requires zero inbound open ports (outbound long-polling) and lists all outbound API domains. |
| **[NETWORK-TOPOLOGY.md](NETWORK-TOPOLOGY.md)** | **Visualizing network topology**.<br>Visual network flowcharts mapping Telegram servers, container networking, and OptimAI core node endpoints. |
| **[DNS-CONFIGURATION.md](DNS-CONFIGURATION.md)** | **Configuring DNS resolvers**.<br>DNS resolution troubleshooting, resolver fallback configurations, and local hosts file overrides. |
| **[TELEGRAM-WEBHOOKS.md](TELEGRAM-WEBHOOKS.md)** | **Understanding Webhooks vs Long-Polling**.<br>Detailed technical comparison explaining why outbound long-polling is strictly superior for secure VPS node hosting. |
| **[MULTI-REGION.md](MULTI-REGION.md)** | **Managing nodes across multiple cloud regions**.<br>Architectural strategies for running nodes across US, Europe, and Asia-Pacific to maximize network rewards. |
| **[HIGH-AVAILABILITY.md](HIGH-AVAILABILITY.md)** | **Configuring high-availability clusters**.<br>Redundancy patterns, dual-server supervisor setups, and state synchronization across regions. |
| **[FAILOVER.md](FAILOVER.md)** | **Automating server failovers**.<br>Procedures and scripts for promoting a standby server to active mining when a primary server experiences downtime. |

---

### 💼 7. Hosting Business & Fleet Economics

| Guide | When to Read / Purpose |
|---|---|
| **[HOSTING-PACKAGES.md](HOSTING-PACKAGES.md)** | **Launching a paid node hosting business**.<br>Business model guide: packaging 24/7 managed node hosting for clients, pricing tiers, and client onboarding. |
| **[COSTS.md](COSTS.md)** | **Comparing cloud vs VPS hosting costs**.<br>Comprehensive cost breakdown contrasting Google Cloud Free Tier, $4 VPS instances, and $0 Android Termux setups. |
| **[PROMO-FUNNEL.md](PROMO-FUNNEL.md)** | **Customizing client lead generation**.<br>How to customize stranger welcome messages, pricing cards, and link your Telegram contact handle (`CONTACT_HANDLE`). |
| **[MULTI-OWNER.md](MULTI-OWNER.md)** | **Hosting multiple clients on a single bot**.<br>Design specifications for managing client fleets, aggregated balance reporting, and client isolation. |

---

### 🔄 8. Upgrades, Testing & Community Policies

| Guide | When to Read / Purpose |
|---|---|
| **[UPGRADING.md](UPGRADING.md)** | **Upgrading between releases safely**.<br>Step-by-step upgrade commands that preserve authentication credentials, state, and rate limits without downtime. |
| **[UPGRADE-VERIFICATION.md](UPGRADE-VERIFICATION.md)** | **Verifying a successful upgrade**.<br>Checklist to confirm node uptime, Docker connectivity, and credential database integrity after an upgrade. |
| **[TESTING.md](TESTING.md)** | **Running automated tests locally**.<br>How to run the 140-check offline smoke suite with deterministic stub binaries (`make check`, `make pytest`). |
| **[TESTING-MATRIX.md](TESTING-MATRIX.md)** | **Reviewing the OS compatibility test matrix**.<br>Verified platform compatibility across Arch, Debian, Ubuntu, Fedora, openSUSE, Alpine, macOS, Windows, and Termux. |
| **[PRODUCTION-READINESS.md](PRODUCTION-READINESS.md)** | **Production launch readiness assessment**.<br>Formal production launch verification criteria covering logging, alerts, security, and supervisor resilience. |
| **[RELEASE-POLICY.md](RELEASE-POLICY.md)** | **Release versioning policy**.<br>Semantic versioning rules (`v1.x.y`), branching conventions, and changelog maintenance standards. |
| **[RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md)** | **Checklist for publishing releases**.<br>Comprehensive checklist to execute before publishing a new production version. |
| **[LOGGING-POLICY.md](LOGGING-POLICY.md)** | **Log redaction & privacy policies**.<br>Strict privacy standards ensuring tokens, passwords, and user information are never written to disk logs. |
| **[LOG-ROTATION-TUNING.md](LOG-ROTATION-TUNING.md)** | **Tuning log file rotation & backup limits**.<br>How to configure log rotation file size thresholds (`LOG_ROTATE_BYTES`) and backup counts. |
| **[LOG-AGGREGATION.md](LOG-AGGREGATION.md)** | **Centralizing logs with Loki or Papertrail**.<br>How to forward node logs to external aggregation pipelines for remote monitoring. |
| **[CRON-AUTOMATION.md](CRON-AUTOMATION.md)** | **Scheduling automated maintenance tasks**.<br>Automating periodic rewards summaries, log cleanups, and system health checks using Linux cron. |
| **[FAQ.md](FAQ.md)** | **Frequently asked questions & quick answers**.<br>Common answers regarding referral rewards, Google Cloud mining policies, Docker permissions, and login sessions. |
| **[COMPARISON.md](COMPARISON.md)** | **Comparing against raw CLI / tmux setups**.<br>Feature comparison matrix showing advantages over unmonitored raw CLI and standard terminal multiplexers. |
| **[CREDITS.md](CREDITS.md)** | **Attribution and third-party notices**.<br>Author attribution, project licensing, and open-source dependency acknowledgments. |
| **[ANNOUNCEMENTS.md](ANNOUNCEMENTS.md)** | **Release announcements and changelog highlights**.<br>Version history highlights, community milestones, and roadmap achievements. |
| **[CONTRIBUTING-WORKFLOW.md](CONTRIBUTING-WORKFLOW.md)** | **Contributing code & pull request guidelines**.<br>Contributor workflow, branch naming standards, and testing requirements for opening PRs. |

---

### Root Documentation & Community Policies

* **[README.md](../README.md)** — Project homepage, visual architecture, 5-step quickstart, and command reference.
* **[CHANGELOG.md](../CHANGELOG.md)** — Version release notes and change history.
* **[ROADMAP.md](../ROADMAP.md)** — Project goals, feature milestones, and non-goals.
* **[CONTRIBUTING.md](../CONTRIBUTING.md)** — Contributor guidelines and pairing workflow.
* **[SECURITY.md](../SECURITY.md)** — Vulnerability reporting and security disclosure policy.
* **[CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)** — Community standards and contributor etiquette.
* **[LICENSE](../LICENSE)** — Apache 2.0 open-source license.
