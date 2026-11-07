#!/usr/bin/env bash
# ============================================================
# optimai-telegram-node — multi-distro VPS & machine setup
# Supports: Arch Linux, EndeavourOS, Debian, Ubuntu, Fedora,
#           CentOS, Rocky, Alma, openSUSE, Alpine.
#
# Run as root:  sudo bash setup-vps.sh
# Idempotent: safe to re-run.
# ============================================================

set -u

C_GREEN='\033[1;32m'; C_YELLOW='\033[1;33m'; C_CYAN='\033[1;36m'; C_RED='\033[1;31m'; C_OFF='\033[0m'
step() { printf "${C_CYAN}==>${C_OFF} ${C_GREEN}%s${C_OFF}\n" "$*"; }
warn() { printf "${C_YELLOW}[skip]${C_OFF} %s\n" "$*"; }
info() { printf "${C_CYAN}[info]${C_OFF} %s\n" "$*"; }

if [ "$(id -u)" -ne 0 ]; then
  printf "${C_RED}ERROR:${C_OFF} run as root: 'sudo bash setup-vps.sh'\n"
  exit 1
fi

# 0) Preflight Device & Architecture Compatibility Check --------------------
step "Preflight: Checking device and architecture compatibility"
OS="$(uname -s)"
ARCH="$(uname -m)"

DISTRO_NAME="$OS"
DISTRO_ID="unknown"
if [ -f /etc/os-release ]; then
  . /etc/os-release
  DISTRO_ID="${ID:-unknown}"
  DISTRO_NAME="${PRETTY_NAME:-${NAME:-$OS}}"
fi

info "Detected OS: $DISTRO_NAME ($ARCH)"

# Compatibility validation (OS & architecture only; RAM/storage not enforced)
if [ "$OS" != "Linux" ]; then
  printf "${C_RED}ERROR: Device is not compatible.${C_OFF}\n"
  printf "Reason: setup-vps.sh is for Linux. Current OS: %s\n" "$OS"
  exit 1
fi

case "$ARCH" in
  x86_64|amd64)
    info "Architecture compatible: 64-bit Linux ($ARCH)"
    ;;
  aarch64|arm64|armv7l|armv6l|arm)
    printf "${C_RED}ERROR: Device is not compatible.${C_OFF}\n"
    printf "Reason: Incompatible architecture '$ARCH' (ARM). The upstream OptimAI Network currently only distributes x86_64 binaries for Linux.\n"
    exit 1
    ;;
  i386|i686)
    printf "${C_RED}ERROR: Device is not compatible.${C_OFF}\n"
    printf "Reason: Incompatible architecture '$ARCH' (32-bit). OptimAI CLI requires a 64-bit operating system.\n"
    exit 1
    ;;
  *)
    printf "${C_RED}ERROR: Device is not compatible.${C_OFF}\n"
    printf "Reason: Unsupported CPU architecture '$ARCH'.\n"
    exit 1
    ;;
esac

# Advisory RAM and storage check (NOT enforced)
if [ -f /proc/meminfo ]; then
  RAM_MB=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
  info "Available memory: ${RAM_MB} MB (advisory only, low-RAM VPS supported)"
fi

# 1) System package updates and Docker installation -------------------------
step "1/5 Installing Docker, Multiplexer & System Dependencies for $DISTRO_NAME"

if command -v pacman >/dev/null 2>&1; then
  # Arch Linux / EndeavourOS / Manjaro
  step "Using pacman package manager"
  pacman -Sy --needed --noconfirm docker docker-compose curl screen python python-pip python-virtualenv ca-certificates procps
elif command -v apt-get >/dev/null 2>&1; then
  # Debian / Ubuntu
  step "Using apt-get package manager"
  apt-get update -y
  if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sh /tmp/get-docker.sh
  fi
  apt-get install -y screen ca-certificates curl python3 python3-pip python3-venv procps || true
  if ! docker compose version >/dev/null 2>&1; then
    apt-get install -y docker-compose-plugin || apt-get install -y docker-compose
  fi
elif command -v dnf >/dev/null 2>&1; then
  # Fedora / RHEL / CentOS / Rocky / Alma
  step "Using dnf package manager"
  dnf install -y docker docker-compose-plugin curl screen python3 python3-pip procps-ng ca-certificates || dnf install -y docker docker-compose curl screen python3 python3-pip procps-ng ca-certificates
elif command -v zypper >/dev/null 2>&1; then
  # openSUSE
  step "Using zypper package manager"
  zypper in -y docker docker-compose curl screen python3 python3-pip ca-certificates
elif command -v apk >/dev/null 2>&1; then
  # Alpine Linux
  step "Using apk package manager"
  apk add docker docker-cli-compose curl gcompat screen python3 py3-pip ca-certificates
else
  warn "Unknown package manager. Attempting official Docker script"
  if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sh /tmp/get-docker.sh
  fi
fi

# 2) Install compatible official OptimAI CLI binary -------------------------
step "2/5 Installing compatible OptimAI CLI miner binary from official website"
CLI_URL="https://cli-node.optimai.network/optimai_cli_ubuntu"

if command -v optimai-cli >/dev/null 2>&1; then
  warn "optimai-cli already installed: $(optimai-cli --version 2>/dev/null || echo 'present')"
else
  info "Downloading compatible CLI binary from $CLI_URL"
  if curl -fsSL "$CLI_URL" -o /usr/local/bin/optimai-cli && chmod +x /usr/local/bin/optimai-cli; then
    printf "${C_GREEN}[ok]${C_OFF} Installed optimai-cli to /usr/local/bin/optimai-cli (%s)\n" "$(/usr/local/bin/optimai-cli --version 2>/dev/null || echo 'ready')"
  else
    warn "optimai-cli host download skipped (image bundles it)"
  fi
fi

# 3) Enable and start docker service ----------------------------------------
step "3/5 Enabling and starting docker service"
if command -v systemctl >/dev/null 2>&1; then
  systemctl enable --now docker 2>/dev/null || systemctl start docker 2>/dev/null || true
elif command -v service >/dev/null 2>&1; then
  service docker start 2>/dev/null || true
elif command -v rc-service >/dev/null 2>&1; then
  rc-service docker start 2>/dev/null || true
fi

# Wait briefly for docker daemon socket activation
for i in {1..5}; do
  [ -S /var/run/docker.sock ] && break
  sleep 1
done

# 4) Swap configuration (advisory, safe for small nodes) --------------------
step "4/5 Checking swap space"
swap_mb() { awk '/SwapTotal/ {printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo 0; }
if [ "$(swap_mb)" -lt 2048 ] && command -v fallocate >/dev/null 2>&1; then
  if [ -f /swapfile ]; then
    if ! swapon --show --noheadings 2>/dev/null | grep -q '^/swapfile'; then
      chmod 600 /swapfile 2>/dev/null; mkswap /swapfile >/dev/null 2>&1; swapon /swapfile 2>/dev/null || true
    fi
  else
    step "Creating 2G swapfile for stability"
    fallocate -l 2G /swapfile 2>/dev/null && chmod 600 /swapfile && mkswap /swapfile >/dev/null 2>&1 && swapon /swapfile 2>/dev/null || warn "Could not create swapfile (unprivileged or unsupported filesystem)"
  fi
  if [ -f /swapfile ] && ! grep -q '^/swapfile ' /etc/fstab 2>/dev/null; then
    echo '/swapfile none swap sw 0 0' >> /etc/fstab 2>/dev/null || true
  fi
  sysctl -w vm.swappiness=10 >/dev/null 2>&1 || true
  printf "${C_GREEN}Swap configured:${C_OFF} $(swap_mb) MB total\n"
else
  info "Swap status: $(swap_mb) MB (advisory)"
fi

# 5) Ensure persistent directories and environment configuration ------------
step "5/5 Initializing storage directories and environment"
mkdir -p ./data/data ./data/home ~/.optimai
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  info "Created initial .env from .env.example template"
fi

# Run comprehensive pre-flight readiness checklist
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/scripts/check-readiness.sh" ]; then
  bash "$SCRIPT_DIR/scripts/check-readiness.sh" || true
elif [ -f scripts/check-readiness.sh ]; then
  bash scripts/check-readiness.sh || true
fi

# 6) Auto-launch Bot & Mining Node if configured ----------------------------
if [ -f .env ] && grep -q '^TELEGRAM_BOT_TOKEN=[0-9]' .env 2>/dev/null; then
  step "Auto-starting OptimAI Bot and AI Miner..."
  bash "$SCRIPT_DIR/start.sh"
else
  printf "\n${C_GREEN}Setup Complete! To start your bot & mining node:${C_OFF}\n"
  printf "  1. Configure credentials:  ${C_YELLOW}nano .env${C_OFF}\n"
  printf "  2. Start bot & miner:      ${C_GREEN}bash start.sh${C_OFF}\n\n"
fi
