#!/usr/bin/env bash
# ============================================================
# setup-codespaces.sh — Automated Setup for GitHub Codespaces
# OptimAI Telegram Bot (v1.9.0)
#
# Configures the complete 24/7 supervisor bot, official mining CLI,
# Python virtual environment and dependencies inside GitHub Codespaces.
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_RED='\033[1;31m'
C_BOLD='\033[1m'
C_OFF='\033[0m'

tick() { printf "  ${C_GREEN}[✓]${C_OFF} %-34s %s\n" "$1" "$2"; }
warn() { printf "  ${C_YELLOW}[!]${C_OFF} %-34s %s\n" "$1" "$2"; }
err()  { printf "  ${C_RED}[✗]${C_OFF} %-34s %s\n" "$1" "$2"; }

printf "\n${C_BOLD}======================================================================${C_OFF}\n"
printf "${C_CYAN}         ⛏️  OPTIMAI GITHUB CODESPACES AUTOMATED SETUP${C_OFF}\n"
printf "${C_BOLD}======================================================================${C_OFF}\n"

# 1. Environment & Architecture Verification
OS="$(uname -s)"
ARCH="$(uname -m)"
tick "Environment Check" "GitHub Codespaces Linux ($ARCH)"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    SUDO="sudo"
  fi
fi

# 2. System Packages Installation
export DEBIAN_FRONTEND=noninteractive
if command -v apt-get >/dev/null 2>&1; then
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq screen curl ca-certificates python3 python3-pip python3-venv procps >/dev/null 2>&1 || true
  tick "System Packages" "Installed screen, curl, python3-venv & procps"
fi

# 3. Official OptimAI CLI Binary Installation & Priming
CLI_URL="https://cli-node.optimai.network/optimai_cli_ubuntu"
INSTALL_DIR="/usr/local/bin"
USE_LOCAL=false

if [ -w "$INSTALL_DIR" ] || [ -n "$SUDO" ]; then
  REAL_BIN="$INSTALL_DIR/optimai-bin"
  WRAPPER_BIN="$INSTALL_DIR/optimai-cli"
else
  INSTALL_DIR="$HOME/.local/bin"
  mkdir -p "$INSTALL_DIR"
  REAL_BIN="$INSTALL_DIR/optimai-bin"
  WRAPPER_BIN="$INSTALL_DIR/optimai-cli"
  USE_LOCAL=true
fi

# If optimai-cli already exists in current folder, make executable and install to PATH
if [ -f "./optimai-cli" ]; then
  chmod +x "./optimai-cli"
  if [ -n "$SUDO" ] && [ "$USE_LOCAL" = false ]; then
    $SUDO mv "./optimai-cli" "$REAL_BIN"
  else
    mv "./optimai-cli" "$REAL_BIN"
  fi
else
  # Download official bootstrap binary
  curl -fL "$CLI_URL" -o optimai-cli
  chmod +x optimai-cli
  if [ -n "$SUDO" ] && [ "$USE_LOCAL" = false ]; then
    $SUDO mv optimai-cli "$REAL_BIN"
  else
    mv optimai-cli "$REAL_BIN"
  fi
fi

# Install smart wrapper that syncs credentials bi-directionally and normalizes -v to --version
WRAPPER_SCRIPT='#!/usr/bin/env bash
# Smart wrapper for official optimai-bin:
# 1. Bi-directional credential sync with workspace ./data & credentials.json database
# 2. Flag normalization (-v -> --version)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_TARGET="'"$REAL_BIN"'"
if [ ! -x "$REAL_TARGET" ]; then
  REAL_TARGET="$SCRIPT_DIR/optimai-bin"
fi

# Pre-execution: synchronize credentials from ./data or credentials.json if available
for sync_cand in "$(pwd)/scripts/sync-credentials.sh" "$HOME/cli-optimai/scripts/sync-credentials.sh" "$HOME/optimai-cli/scripts/sync-credentials.sh" "/workspaces/cli-optimai/scripts/sync-credentials.sh" "/workspaces/optimai-cli/scripts/sync-credentials.sh"; do
  if [ -f "$sync_cand" ]; then
    bash "$sync_cand" >/dev/null 2>&1 || true
    break
  fi
done

args=()
for arg in "$@"; do
  if [ "$arg" = "-v" ]; then
    args+=("--version")
  else
    args+=("$arg")
  fi
done

"$REAL_TARGET" "${args[@]}"
RC=$?

# Post-execution: sync updated credentials back to ./data and credentials.json database
for sync_cand in "$(pwd)/scripts/sync-credentials.sh" "$HOME/cli-optimai/scripts/sync-credentials.sh" "$HOME/optimai-cli/scripts/sync-credentials.sh" "/workspaces/cli-optimai/scripts/sync-credentials.sh" "/workspaces/optimai-cli/scripts/sync-credentials.sh"; do
  if [ -f "$sync_cand" ]; then
    bash "$sync_cand" >/dev/null 2>&1 || true
    break
  fi
done

exit $RC
'

if [ -n "$SUDO" ] && [ "$USE_LOCAL" = false ]; then
  echo "$WRAPPER_SCRIPT" | $SUDO tee "$WRAPPER_BIN" > /dev/null
  $SUDO chmod +x "$WRAPPER_BIN"
  $SUDO chmod +x "$REAL_BIN"
else
  echo "$WRAPPER_SCRIPT" > "$WRAPPER_BIN"
  chmod +x "$WRAPPER_BIN"
  chmod +x "$REAL_BIN"
fi

# Ensure in PATH
if [ "$USE_LOCAL" = true ]; then
  export PATH="$HOME/.local/bin:$PATH"
fi

# Prime the core CLI immediately (downloads core CLI 0.1.63 into ~/.optimai)
"$WRAPPER_BIN" --help >/dev/null 2>&1 || true
CLI_VER="$("$WRAPPER_BIN" --version 2>/dev/null || echo '0.1.63')"
tick "Official OptimAI CLI" "Installed & core primed ($CLI_VER)"

# 4. Python Virtual Environment & Dependencies
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

if [ ! -x ".venv/bin/pip" ]; then
  .venv/bin/python -m ensurepip --default-pip 2>/dev/null || true
fi

if [ -x ".venv/bin/pip" ]; then
  .venv/bin/pip install --upgrade pip -q >/dev/null 2>&1 || true
  .venv/bin/pip install -r requirements.txt -q
elif command -v uv >/dev/null 2>&1; then
  uv pip install --python .venv/bin/python -r requirements.txt -q
else
  .venv/bin/python -m pip install -r requirements.txt -q
fi
tick "Python Virtual Environment" "Dependencies installed in .venv"

# 5. Storage Directories & Environment Configuration
mkdir -p ./data/data ./data/home ~/.optimai
chmod -R a+rwX ./data 2>/dev/null || true
if [ -f scripts/sync-credentials.sh ]; then
  bash scripts/sync-credentials.sh >/dev/null 2>&1 || true
fi
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  tick "Configuration File" "Created .env from .env.example template"
else
  tick "Configuration File" ".env present and ready"
fi

# 6. Pre-flight Readiness Checklist
if [ -f scripts/check-readiness.sh ]; then
  printf "\n"
  bash scripts/check-readiness.sh || true
fi

# 7. Interactive Credentials Intake & Auto-Launch
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/scripts/prompt-login.sh" ]; then
  . "$SCRIPT_DIR/scripts/prompt-login.sh"
  SUPPRESS_DIRECT_NODE_START=true prompt_account_login "optimai-cli"
fi
if [ -f "$SCRIPT_DIR/scripts/sync-credentials.sh" ]; then
  bash "$SCRIPT_DIR/scripts/sync-credentials.sh" >/dev/null 2>&1 || true
fi

if [ -f "$SCRIPT_DIR/scripts/prompt-env.sh" ]; then
  . "$SCRIPT_DIR/scripts/prompt-env.sh"
  prompt_telegram_credentials "$SCRIPT_DIR/.env" "$SCRIPT_DIR/.env.example" "bash '$SCRIPT_DIR/start.sh'"
fi

# Auto-start check: if not already running, launch start.sh
if ! screen -ls 2>/dev/null | grep -q "optimai" && ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "optimai"; then
  bash "$SCRIPT_DIR/start.sh"
fi
