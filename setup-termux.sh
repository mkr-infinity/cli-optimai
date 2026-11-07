#!/usr/bin/env bash
# ============================================================
# setup-termux.sh — Automated Setup for Android Termux
# OptimAI Telegram Node (v1.3.0)
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

# 3. Install core packages
step "3/5 Installing required Termux packages"
if command -v pkg >/dev/null 2>&1; then
  pkg update -y
  pkg install -y python git screen curl proot-distro termux-tools
elif command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y python3 python3-venv git screen curl proot-distro
fi

# 4. Set up Python virtual environment
step "4/5 Setting up Python environment and dependencies"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 5. CLI Architecture setup & guidance
step "5/5 OptimAI CLI setup for $ARCH"
CLI_DIR="$HOME/.local/bin"
mkdir -p "$CLI_DIR"
export PATH="$CLI_DIR:$PATH"

case "$ARCH" in
  x86_64|amd64)
    info "x86_64 architecture detected (emulator/Intel Android). Installing native Linux binary..."
    curl -fsSL "https://cli-node.optimai.network/optimai_cli_ubuntu" -o "$CLI_DIR/optimai-cli"
    chmod +x "$CLI_DIR/optimai-cli"
    info "Installed optimai-cli to $CLI_DIR/optimai-cli"
    ;;
  aarch64|arm64)
    info "ARM64 Android device detected."
    info "The upstream OptimAI CLI distributes x86_64 Linux binaries."
    info "You can run in two ways on Android:"
    echo "  1) Control-Plane & Remote Management: Bot runs natively in Termux."
    echo "  2) Full Mining on Device via PRoot Ubuntu (Box64/QEMU x86_64 emulation):"
    echo "     proot-distro install ubuntu"
    echo "     proot-distro login ubuntu"
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
# Acquire wake lock so Android does not kill the process
if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock
fi

# Run in detached screen session
screen -dmS optimai bash -c "cd $(pwd) && .venv/bin/python -m bot.main"

echo "✅ OptimAI Telegram Node launched in background screen session!"
echo "• View terminal session:   screen -r optimai"
echo "• Detach from session:     Press Ctrl+A then D"
echo "• View live logs:          make logs"
echo "• Manage node from phone:  Open your bot in Telegram"
EOF
chmod +x run-termux.sh

printf "\n${C_GREEN}============================================================${C_OFF}\n"
printf "${C_GREEN} Termux Setup Complete! ⛏️${C_OFF}\n"
printf " 1. Configure credentials:  nano .env\n"
printf " 2. Start mining bot:       bash run-termux.sh\n"
printf " 3. Attach to screen:       screen -r optimai\n"
printf "${C_GREEN}============================================================${C_OFF}\n"
