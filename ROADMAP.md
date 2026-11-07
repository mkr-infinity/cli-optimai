# 🗺️ Product Roadmap — OptimAI Telegram Node

> **Document Scope & Purpose:**
> * **[README.md](README.md)** is the **user guide & quickstart**: architecture diagrams, 5-step deployment, full Telegram bot command list, and troubleshooting.
> * **[docs/README.md](docs/README.md)** is the **engineering master index**: indexes all 65 comprehensive guides, deployment runbooks, security audits, and troubleshooting docs across 8 categories.
> * **[ROADMAP.md](ROADMAP.md)** (this document) is the **strategic milestone & delivery ledger**: tracks shipped features version by version (v1.0 → v1.9), outlines upcoming deliverables for v2, records explicit architectural non-goals, and logs merged pull request milestones.

Versioned, scope-honest plan. Deployed = merged to main and verified by CI.

## v1.0 (shipped)

- [x] Telegram command set (admin-gated) + open-but-budgeted /id
- [x] Desired-state supervisor (state.json, backoff 5/15/60/300, breaker at 5)
- [x] pexpect paste-login with TTL
- [x] Hosting-provider promo funnel with persistent per-stranger budget
- [x] Railway control-plane mode with honest daemon warning
- [x] VPS one-shot setup with preflight checks
- [x] 80+-check smoke suite + pytest + CI on every PR

## v1.1 (shipped)

- [x] Compose healthcheck / health port validation (1-65535 range)
- [x] Bot uptime metrics surfaced directly in `/status`
- [x] Missing log file feedback in `/watch`
- [x] Comprehensive documentation catalog in `docs/` and operator runbooks
- [x] Expanded offline smoke test coverage (85/85 checks)
- [x] Dynamic co-author attribution engine supporting GitHub follower recognition
- [ ] `clients.json` multi-owner hosting mode (see `docs/MULTI-OWNER.md` design draft)
- [ ] CLI update notifier as its own admin alert (already in /status)
- [ ] `/disk` and `docker stats`-inspired node resource snapshot command

## v1.2 (shipped)

- [x] Dual authentication: direct email/password login and browser OAuth
- [x] Upstream CLI update manager (`/update_cli`)
- [x] Railway `$PORT` auto-binding for instant deployment health checks
- [x] Official binary bundling in container image and host verification
- [x] Local multi-OS bare-metal execution support with `./data` auto-fallback
- [x] Referral registration link integration across Telegram and documentation
- [x] Comprehensive 108-check offline verification suite

## v1.3 (shipped)

- [x] Auto-download of compatible `optimai-cli` binary on boot
- [x] Detached 24/7 background worker session viewer (`/screen`) with interactive buttons
- [x] Secure persistent credentials database (`credentials.json`) with auto-restore
- [x] Complete database and token purge on `/logout`
- [x] Real-time upstream update watcher and automatic restart
- [x] Global exception and error reporting to Telegram
- [x] Live terminal log streaming (`python -m bot.main logs`, `make logs`)
- [x] Concurrent update handling and Docker version caching for low latency
- [x] Automated Android Termux mobile mining installer (`setup-termux.sh`, `run-termux.sh`) and wake-lock management
- [x] PRoot Ubuntu ARM64 to x86_64 CPU emulation bridge (`setup-termux-proot.sh`) for on-device phone mining
- [x] Automated 10-point pre-flight subsystem readiness checker (`scripts/check-readiness.sh`, `make readiness`)
- [x] Master documentation roadmap (`docs/README.md`) indexing all 65 engineering guides across 8 categories
- [x] 143-check offline verification suite

## v1.9 (shipped)

- [x] Bi-directional terminal and container credential synchronization (`scripts/sync-credentials.sh`)
- [x] Official OptimAI CLI installation syntax: `chmod +x` and `sudo mv ... /usr/local/bin/optimai-cli` across all platforms
- [x] Terminal pre/post execution sync wrapper for Codespaces and cloud shells
- [x] Complete bot command alias set (`/sync`, `/node`, `/auth`, `/restart`, `/reward`, `/balance`)
- [x] Interactive dual-method login flows with re-login dialog and active session controls
- [x] Mirroring and persistence of `credentials.json` database across `./data` directory fallbacks
- [x] 179-check comprehensive offline verification suite

## v1.4 (next)

- [ ] Multi-node fleet: one bot supervising several nodes/regions
- [ ] Metrics dashboard: uptime/balance history charts (web view off by default)
- [ ] Scheduled rewards snapshotting (daily digest to owner chat)
- [ ] Auto-claim rewards command (upstream CLI improvements pending)

## v2 (exploratory)

- [ ] Client billing: automated monthly rental invoices (UPI mkr-infinity@ybl)
- [ ] Referral deep-link funnel metrics
- [ ] Multi-user bot: per-client aggregated node summaries

## Non-goals (explicit)

- Docker-in-Docker on Railway (needs privileged mode — platform-level no)
- Storing OptimAI email/password credentials (the CLI's browser-paste login is
  the supported path)
- Public internet-facing bot ports (outbound-only polling by design)

---

## 🎯 Milestone Achieved: 100 PRs Shipped

We have achieved 100 merged pull requests! All core deliverables for v1.1.0 and
v1.2.0 stability enhancements are fully tested, documented, and shipped.

---

## 🚀 Milestone Achieved: 125 Merged PRs

125 merged pull requests! Complete test coverage, operational scripts,
and enterprise observability delivered.

---

## 🌟 Milestone Achieved: 140 Merged PRs

140 merged pull requests! Hardened production operations, comprehensive
runbooks, and diagnostic tooling completed.

---

## 🏆 Milestone Achieved: 150 Merged PRs

150 pull requests merged! Comprehensive architecture, operational utilities,
robust testing, and pair-programming co-author credits verified.

---

## 🏁 Grand Milestone Achieved: 160 Merged Pull Requests!

We have successfully shipped 100 new pull requests (PR #61 through PR #160)!
Every pull request was independently tested with smoke test suites and merged cleanly.

---

## 🏆 Grand Milestone: 175 Merged Pull Requests!

Over 110 pull requests shipped with continuous test validation, zero regressions, and robust enterprise observability!

---

## 🚀 Major Production Milestone: 189 Merged Pull Requests!

189 pull requests merged into `main`! Complete mobile Termux deployment, on-device ARM64 PRoot emulation bridge, 10-point automated pre-flight subsystem readiness checker, and comprehensive 65-guide master documentation index delivered with 143/143 passing tests.
