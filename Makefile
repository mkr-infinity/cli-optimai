# OptimAI Telegram Node — light local commands only.
# Heavy work (docker build, 80-check suite on CI) stays on GitHub runners.

SHELL := /bin/bash
PY := .venv/bin/python

.PHONY: help venv install test pytest compile check status clean compose-config diag validate git-status help-all check-all env-check logs log compat readiness check-readiness start run setup clean-containers

help:
	@echo "OptimAI CLI Developer Commands:"
	@echo "  make setup           run universal automated environment setup"
	@echo "  make start           launch bot and AI mining node"
	@echo "  make clean-containers purge conflicting OptimAI Docker containers"
	@echo "  make venv            create Python 3.12 venv"
	@echo "  make install         install runtime + dev deps into .venv"
	@echo "  make test            run standalone smoke suite (no network)"
	@echo "  make pytest          run pytest test runner"
	@echo "  make compile         byte-compile bot/*.py"
	@echo "  make check           run compile + smoke tests"
	@echo "  make validate        run compile + smoke tests verification"
	@echo "  make clean           remove bytecode and cache artifacts"
	@echo "  make compat          check OS & device compatibility"
	@echo "  make readiness       run preflight readiness checker"
	@echo "  make diag            run system diagnostic script"
	@echo "  make git-status      verify git working tree cleanliness"
	@echo "  make check-all       run full checks and git status"
	@echo "  make env-check       verify .env file exists"
	@echo "  make logs            tail docker compose container logs"
	@echo "  make compose-config  validate docker-compose.yml with a dummy .env"

setup:
	bash setup.sh

start:
	bash start.sh

run: start

venv:
	uv venv --python 3.12 .venv

install:
	uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt

test:
	$(PY) tests/smoke_test.py

pytest:
	$(PY) -m pytest tests/

compile:
	$(PY) -m py_compile bot/*.py

check: compile test

validate: compile test

clean:
	rm -rf __pycache__ bot/__pycache__ tests/__pycache__ .pytest_cache .coverage
	find . -name __pycache__ -type d -not -path "./.git/*" -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true

compose-config:
	cp .env.example .env
	sed -i "s/^TELEGRAM_BOT_TOKEN=$$/TELEGRAM_BOT_TOKEN=000:dummy/" .env
	sed -i "s/^TELEGRAM_ALLOWED_IDS=$$/TELEGRAM_ALLOWED_IDS=123456789/" .env
	docker compose config > /dev/null
	rm .env

compat:
	bash scripts/check-compatibility.sh

readiness: check-readiness

check-readiness:
	bash scripts/check-readiness.sh

diag:
	bash scripts/system-info.sh

git-status:
	bash scripts/check-git-clean.sh

check-all: check git-status

env-check:
	@test -f .env && echo "[OK] .env exists" || echo "[WARN] .env missing"

logs:
	@if [ -f data/node.log ]; then $(PY) -m bot.main logs; elif docker inspect optimai-telegram-node >/dev/null 2>&1; then docker logs --tail=100 -f optimai-telegram-node; else docker compose logs --tail=100 -f; fi

log: logs

clean-containers:
	@docker rm -f optimai-telegram-node optimai-node 2>/dev/null || true
	@docker network prune -f >/dev/null 2>&1 || true
	@echo "[OK] Purged conflicting OptimAI Docker containers and stale networks"
