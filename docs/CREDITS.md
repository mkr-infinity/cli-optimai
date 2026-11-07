# Credits & Third-Party Notices

## Project

**OptimAI Telegram Node v1.3.0** — Dockerized Telegram bot controlling an
OptimAI Network CLI node 24/7.

- Author: Mohammad Kaif Raja (mkr-infinity)
- Repository: https://github.com/mkr-infinity/optimai-cli
- Telegram: [@mkr_infinity](https://t.me/mkr_infinity) — paid node hosting
- Support: https://buymeacoffee.com/mkr_infinity — UPI: mkr-infinity@ybl
- License: Apache-2.0 (LICENSE at repo root)

Unauthorized modification, redistribution, or commercial sale of this
software is prohibited without prior written permission. Personal use
permitted. Unauthorized removal of attribution is strictly prohibited.

## Dependencies (pinned at build time)

| Dependency | Version | License | Role |
|---|---|---|---|
| [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) | 21.10 | GPL-3.0 (LGPL until v20) | Telegram Bot API framework |
| [pexpect](https://github.com/pexpect/pexpect) | 4.9.0 (only ptyprocess under the hood, ISC) | ISC | drives the CLI's paste-login flow |
| Python | 3.12 (image `python:3.12-slim`) | PSF | runtime |
| Docker CLI static client | 27.3.1 (best-effort ARG) | Apache-2.0 | daemon connectivity check |

## Upstream

| Project | Relation |
|---|---|
| [OptimAI Network / OptimAI-CLI-Node](https://github.com/OptimaiNetwork/OptimAI-CLI-Node) | the controlled node CLI (Apache-2.0); surface verified against v0.1.63 |
| OptimAI docs (docs.optimai.network) | node behavior reference |

## Inspiration

The behavior contract (plan-mode discipline, ask-never-assume, honest
degradation over silent failure) came from the delivered master-build
prompt process. Banner design adapted from the TeleAutomator project
(same author).
