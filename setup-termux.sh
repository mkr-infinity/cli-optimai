#!/usr/bin/env bash
# ============================================================
# setup-termux.sh — Automated Setup for Android Termux
# OptimAI Telegram Bot (v1.9.0)
#
# Allows running the 24/7 supervisor bot and mining node directly
# on an Android smartphone or tablet using Termux.
# ============================================================

set -euo pipefail

C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_RED='\033[1;31m'
C_OFF='\033[0m'

step() { printf "\n${C_CYAN}==>${C_OFF} ${C_GREEN}%s${C_OFF}\n" "$*"; }
info() { printf "${C_CYAN}[info]${C_OFF} %s\n" "$*"; }
warn() { printf "${C_YELLOW}[warn]${C_OFF} %s\n" "$*"; }
err()  { printf "${C_RED}[error]${C_OFF} %s\n" "$*"; }

# 1. Termux environment verification
step "1/5 Checking Termux environment"
if [ -z "${TERMUX_VERSION:-}" ] && [ ! -d "/data/data/com.termux" ]; then
  warn "This script is tailored for Termux on Android. Proceeding in standard Linux mode."
else
  info "Running inside Termux on Android (v${TERMUX_VERSION:-unknown})"
fi

ARCH="$(uname -m)"
info "Detected architecture: $ARCH"

# 2. Acquire Termux Wake Lock (prevent Android sleep)
step "2/5 Configuring background execution & wake lock"
if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock
  info "Acquired Termux wake-lock: CPU will stay awake while mining in the background."
else
  warn "termux-wake-lock not found. Install 'termux-tools' to keep CPU awake with screen off."
fi

# 3. Install core packages with fallbacks
step "3/5 Installing required Termux packages"
export DEBIAN_FRONTEND=noninteractive
if command -v pkg >/dev/null 2>&1; then
  pkg update -y -o Dpkg::Options::="--force-confold" || {
    warn "pkg update returned a mirror warning. If packages fail, run 'termux-change-repo'."
  }
  pkg install -y -o Dpkg::Options::="--force-confold" python git screen curl clang libffi openssl make proot proot-distro termux-tools docker || {
    warn "Retrying with basic package set..."
    pkg install -y python git screen curl proot-distro termux-tools docker || pkg install -y python git screen curl proot-distro termux-tools
  }
elif command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y python3 python3-venv git screen curl proot-distro
fi

# 4. Set up Python virtual environment
step "4/5 Setting up Python environment and dependencies"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv || {
    warn "venv creation fallback..."
    python3 -m venv --without-pip .venv
    curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    .venv/bin/python /tmp/get-pip.py
  }
fi

.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install -r requirements.txt

# 5. CLI Architecture setup & guidance
step "5/5 OptimAI CLI setup for $ARCH"
CLI_DIR="$HOME/.local/bin"
mkdir -p "$CLI_DIR"
export PATH="$CLI_DIR:$PATH"

case "$ARCH" in
  x86_64|amd64)
    info "x86_64 architecture detected (emulator/Intel Android). Installing native Linux binary..."
    curl -fsSL "https://cli-node.optimai.network/optimai_cli_ubuntu" -o "$CLI_DIR/optimai-bin"
    chmod +x "$CLI_DIR/optimai-bin"
    cat <<'EOF' > "$CLI_DIR/optimai-cli"
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
    chmod +x "$CLI_DIR/optimai-cli"
    "$CLI_DIR/optimai-cli" --help >/dev/null 2>&1 || true
    CLI_VER="$("$CLI_DIR/optimai-cli" --version 2>/dev/null || echo 'ready')"
    info "Installed and primed optimai-cli ($CLI_VER)"
    ;;
  aarch64|arm64)
    info "ARM64 Android device detected."
    info "Upstream distributes x86_64 binaries. PRoot automated bridge available."
    if proot-distro list 2>/dev/null | grep -q "ubuntu.*installed"; then
      info "PRoot Ubuntu environment already installed. Ensuring x86_64 emulation bridge..."
      bash setup-termux-proot.sh
    elif [ -t 0 ]; then
      printf "\n${C_CYAN}Would you like to install PRoot Ubuntu x86_64 emulation for on-device mining now? [Y/n]: ${C_OFF}"
      read -r REPLY || REPLY="y"
      if [[ ! "$REPLY" =~ ^[Nn]$ ]]; then
        bash setup-termux-proot.sh
      fi
    else
      info "Non-interactive shell. Running setup-termux-proot.sh..."
      bash setup-termux-proot.sh || true
    fi
    ;;
  *)
    warn "Unsupported Android CPU architecture: $ARCH"
    ;;
esac

# Create .env template if not present
if [ ! -f ".env" ]; then
  cat <<'EOF' > .env
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_IDS=
NODE_AUTO_START=true
CONTACT_HANDLE=@mkr_infinity
EOF
  info "Created .env template. Please edit .env with your TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS."
fi

# Create run-termux.sh helper
cat <<'EOF' > run-termux.sh
#!/usr/bin/env bash
# ============================================================
# run-termux.sh — Universal Launcher for Android Termux
# OptimAI Telegram Bot & AI Miner (v1.9.0)
# ============================================================
set -u

# Acquire wake lock so Android does not kill the process
if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock
fi

export PATH="$HOME/.local/bin:${PREFIX:-/data/data/com.termux/files/usr}/bin:$PATH"

# Check if Telegram credentials are configured in .env
HAS_TELEGRAM=false
if [ -f .env ] && grep -q '^TELEGRAM_BOT_TOKEN=[0-9]' .env 2>/dev/null && grep -q '^TELEGRAM_ALLOWED_IDS=[0-9]' .env 2>/dev/null; then
  HAS_TELEGRAM=true
fi

if [ "$HAS_TELEGRAM" = true ]; then
  screen -dmS optimai bash -c "cd $(pwd) && export NODE_AUTO_START=true && .venv/bin/python -m bot.main"

  printf "\n\033[1;32m============================================================\033[0m\n"
  printf "\033[1;32m  🚀 OptimAI Telegram Bot & Miner Started in Background!\033[0m\n"
  printf "\033[1;32m============================================================\033[0m\n"
  printf "  • Screen Session:   \033[1;36moptimai\033[0m (screen -r optimai)\n"
  printf "  • Detach Screen:    Press \033[1;36mCtrl+A then D\033[0m\n"
  printf "  • Bot Controller:   Open Telegram and send \033[1;32m/start\033[0m\n"
  printf "  • Node Workload:    Running 24/7 with auto-restart\n\n"
else
  CLI_BIN="optimai-cli"
  if ! command -v "$CLI_BIN" >/dev/null 2>&1; then
    if [ -x "$HOME/.local/bin/optimai-cli" ]; then
      CLI_BIN="$HOME/.local/bin/optimai-cli"
    elif [ -x "${PREFIX:-/data/data/com.termux/files/usr}/bin/optimai-cli" ]; then
      CLI_BIN="${PREFIX:-/data/data/com.termux/files/usr}/bin/optimai-cli"
    fi
  fi

  screen -dmS optimai bash -c "cd $(pwd) && $CLI_BIN node start"
  printf "\n\033[1;32m============================================================\033[0m\n"
  printf "\033[1;32m  ⛏️  OptimAI Miner Node Running in Background (No Bot)!\033[0m\n"
  printf "\033[1;32m============================================================\033[0m\n"
  printf "  • Command:          \033[1;36m%s node start\033[0m\n" "$CLI_BIN"
  printf "  • View Console:     \033[1;36mscreen -r optimai\033[0m\n"
  printf "  • Check Status:     \033[1;36m%s node status\033[0m\n" "$CLI_BIN"
  printf "  • View Rewards:     \033[1;36m%s rewards balance\033[0m\n" "$CLI_BIN"
  printf "  • Add Bot Later:    Configure \033[1;36mnano .env\033[0m with token and re-run \033[1;32mbash run-termux.sh\033[0m\n\n"
fi
EOF
chmod +x run-termux.sh

# 6. Run visual pre-flight readiness check
if [ -f scripts/check-readiness.sh ]; then
  bash scripts/check-readiness.sh || true
fi

# 7. Interactive Credentials Intake & Auto-Launch
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_CAND="optimai-cli"
if ! command -v "$CLI_CAND" >/dev/null 2>&1; then
  if [ -x "$HOME/.local/bin/optimai-cli" ]; then
    CLI_CAND="$HOME/.local/bin/optimai-cli"
  elif [ -x "${PREFIX:-/data/data/com.termux/files/usr}/bin/optimai-cli" ]; then
    CLI_CAND="${PREFIX:-/data/data/com.termux/files/usr}/bin/optimai-cli"
  fi
fi

if [ -f "$SCRIPT_DIR/scripts/prompt-login.sh" ]; then
  . "$SCRIPT_DIR/scripts/prompt-login.sh"
  prompt_account_login "$CLI_CAND"
fi

if [ -f "$SCRIPT_DIR/scripts/prompt-env.sh" ]; then
  . "$SCRIPT_DIR/scripts/prompt-env.sh"
  prompt_telegram_credentials "$SCRIPT_DIR/.env" "$SCRIPT_DIR/.env.example" "bash '$SCRIPT_DIR/run-termux.sh'"
fi

# Auto-start check: if not already running, launch run-termux.sh
if ! screen -ls 2>/dev/null | grep -q "optimai"; then
  bash "$SCRIPT_DIR/run-termux.sh"
fi
