#!/usr/bin/env bash
# ============================================================
# setup-codespaces.sh — Automated Setup for GitHub Codespaces
# OptimAI Telegram Node (v1.3.0)
#
# Configures the complete 24/7 supervisor bot, official mining CLI,
# Python virtual environment and dependencies inside GitHub Codespaces.
# ============================================================

set -euo pipefail

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

# Download official bootstrap binary
if [ -n "$SUDO" ] && [ "$USE_LOCAL" = false ]; then
  $SUDO curl -fsSL "$CLI_URL" -o "$REAL_BIN"
  $SUDO chmod +x "$REAL_BIN"
  
  # Install smart wrapper that normalizes -v to --version
  $SUDO tee "$WRAPPER_BIN" > /dev/null <<'EOF'
#!/usr/bin/env bash
args=()
for arg in "$@"; do
  if [ "$arg" = "-v" ]; then
    args+=("--version")
  else
    args+=("$arg")
  fi
done
exec /usr/local/bin/optimai-bin "${args[@]}"
EOF
  $SUDO chmod +x "$WRAPPER_BIN"
else
  curl -fsSL "$CLI_URL" -o "$REAL_BIN"
  chmod +x "$REAL_BIN"
  cat <<'EOF' > "$WRAPPER_BIN"
#!/usr/bin/env bash
REAL_TARGET="$(dirname "$0")/optimai-bin"
args=()
for arg in "$@"; do
  if [ "$arg" = "-v" ]; then
    args+=("--version")
  else
    args+=("$arg")
  fi
done
exec "$REAL_TARGET" "${args[@]}"
EOF
  chmod +x "$WRAPPER_BIN"
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
  prompt_account_login "optimai-cli"
fi

if [ -f "$SCRIPT_DIR/scripts/prompt-env.sh" ]; then
  . "$SCRIPT_DIR/scripts/prompt-env.sh"
  prompt_telegram_credentials "$SCRIPT_DIR/.env" "$SCRIPT_DIR/.env.example" "bash '$SCRIPT_DIR/start.sh'"
fi

if [ ! -f .env ] || ! grep -q '^TELEGRAM_BOT_TOKEN=[0-9]' .env 2>/dev/null; then
  printf "\n${C_BOLD}======================================================================${C_OFF}\n"
  printf "${C_GREEN}  🎉 GitHub Codespaces Setup Complete! Node is Ready to Run!${C_OFF}\n"
  printf "${C_BOLD}======================================================================${C_OFF}\n"
  printf "  1. Enter your Telegram credentials:  ${C_YELLOW}nano .env${C_OFF}\n"
  printf "     (Set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS)\n"
  printf "  2. Start Bot and AI Miner together:  ${C_GREEN}bash start.sh${C_OFF} (or ${C_CYAN}make start${C_OFF})\n"
  printf "  3. Telegram Bot Control:             Send ${C_GREEN}/start${C_OFF} or ${C_GREEN}/status${C_OFF} in Telegram\n"
  printf "%s\n\n" "======================================================================"
fi
