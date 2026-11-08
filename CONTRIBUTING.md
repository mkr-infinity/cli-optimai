# Contributing to OptimAI Telegram Bot

Thanks for your interest! This is a single-owner hosting project by
**Mohammad Kaif Raja (mkr-infinity)**, but useful PRs are welcome.

## Ground rules

- **Plan first, then code.** For anything beyond a typo fix, propose the change
  in an issue or a draft PR before writing lots of code.
- **Small, focused PRs.** One feature or one fix per PR. No drive-by refactors.
- **Never commit secrets.** The real `.env` is gitignored on purpose. If you
  leak a token, rotate it via @BotFather → `/revoke`.
- **The bot must degrade honestly.** Any new feature has to keep working on
  Railway (no Docker daemon) and on a VPS with Docker. Respect the existing
  warning paths.

## How to build locally (light)

```bash
uv venv --python 3.12 && uv pip install --python .venv/bin/python \
  -r requirements.txt -r requirements-dev.txt
```

## How to test (no network, no real Telegram needed)

```bash
make check                               # byte-compile + run 85-check suite
make pytest                              # pytest runner
make status                              # inspect branch and commit stats
```

CI (`.github/workflows/ci.yml`) runs all three plus `docker compose config`
on every PR — you do not need Docker installed locally.

## Commit conventions

Conventional messages, exactly like `git log`:

```
feat: config loader
fix: pexpect closed is an attribute, not a method
docs: readme
test: smoke suite
```

## Branch → PR → merge flow

This repo is a personal fast-moving project: branches derive from a fresh
`origin/main` (`git switch main && git pull && git switch -c feat/...`),
CI must be green, then the PR is merged with a merge commit and the branch
is deleted. Keep `main` deployable at all times: `docker compose up -d --build`
(README, Deployment A) should always produce a working bot.
