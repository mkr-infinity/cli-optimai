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
step "0/4 Checking device and architecture compatibility"
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
step "1/4 Installing Docker & dependencies for $DISTRO_NAME"

if command -v pacman >/dev/null 2>&1; then
  # Arch Linux / EndeavourOS / Manjaro
  step "Using pacman package manager"
  pacman -Sy --needed --noconfirm docker docker-compose curl screen
elif command -v apt-get >/dev/null 2>&1; then
  # Debian / Ubuntu
  step "Using apt-get package manager"
  apt-get update -y
  if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sh /tmp/get-docker.sh
  fi
  apt-get install -y screen ca-certificates || true
  if ! docker compose version >/dev/null 2>&1; then
    apt-get install -y docker-compose-plugin || apt-get install -y docker-compose
  fi
elif command -v dnf >/dev/null 2>&1; then
  # Fedora / RHEL / CentOS / Rocky / Alma
  step "Using dnf package manager"
  dnf install -y docker docker-compose-plugin curl screen || dnf install -y docker docker-compose curl screen
elif command -v zypper >/dev/null 2>&1; then
  # openSUSE
  step "Using zypper package manager"
  zypper in -y docker docker-compose curl screen
elif command -v apk >/dev/null 2>&1; then
  # Alpine Linux
  step "Using apk package manager"
  apk add docker docker-cli-compose curl gcompat screen
else
  warn "Unknown package manager. Attempting official Docker script"
  if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sh /tmp/get-docker.sh
  fi
fi

# 2) Install compatible official OptimAI CLI binary -------------------------
step "2/4 Installing compatible OptimAI CLI from official website"
CLI_URL="https://cli-node.optimai.network/optimai_cli_ubuntu"

if command -v optimai-cli >/dev/null 2>&1; then
  warn "optimai-cli already installed: $(optimai-cli --version 2>/dev/null || echo 'present')"
else
  info "Downloading compatible CLI binary from $CLI_URL"
  if curl -fsSL "$CLI_URL" -o /usr/local/bin/optimai-cli && chmod +x /usr/local/bin/optimai-cli; then
    printf "${C_GREEN}[ok]${C_OFF} Installed optimai-cli to /usr/local/bin/optimai-cli\n"
  else
    warn "optimai-cli host download skipped (image bundles it)"
  fi
fi

# 3) Enable and start docker service ----------------------------------------
step "3/4 Enabling and starting docker service"
if command -v systemctl >/dev/null 2>&1; then
  systemctl enable --now docker 2>/dev/null || systemctl start docker 2>/dev/null || true
elif command -v service >/dev/null 2>&1; then
  service docker start 2>/dev/null || true
elif command -v rc-service >/dev/null 2>&1; then
  rc-service docker start 2>/dev/null || true
fi

# 4) Swap configuration (advisory, safe for small nodes) --------------------
step "4/4 Checking swap space"
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

printf "\n${C_GREEN}VPS / Machine setup completed.${C_OFF} Preflight status:\n"
problems=0

if command -v docker >/dev/null 2>&1; then
  printf "  ${C_GREEN}[ok]${C_OFF} docker is installed: %s\n" "$(docker --version 2>/dev/null)"
else
  printf "  ${C_RED}[!!]${C_OFF} docker not found in PATH\n"
  problems=$((problems + 1))
fi

if docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1; then
  printf "  ${C_GREEN}[ok]${C_OFF} docker compose is available\n"
else
  printf "  ${C_YELLOW}[??]${C_OFF} docker compose not detected directly\n"
fi

if [ -S /var/run/docker.sock ]; then
  printf "  ${C_GREEN}[ok]${C_OFF} docker socket is active (/var/run/docker.sock)\n"
else
  printf "  ${C_YELLOW}[??]${C_OFF} docker socket not active yet (will mount when daemon starts)\n"
fi

if command -v optimai-cli >/dev/null 2>&1; then
  printf "  ${C_GREEN}[ok]${C_OFF} optimai-cli is ready: %s\n" "$(optimai-cli --version 2>/dev/null || echo 'ready')"
else
  info "optimai-cli host binary optional (Docker image includes bundled CLI)"
fi

if [ "$problems" -eq 0 ]; then
  printf "\n${C_GREEN}All essential preflight checks passed.${C_OFF} Next steps:\n"
else
  printf "\n${C_YELLOW}Setup completed with %s warning(s).${C_OFF} Next steps:\n" "$problems"
fi
printf "  cd optimai-cli\n"
printf "  cp .env.example .env && nano .env      ${C_YELLOW}# fill TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS${C_OFF}\n"
printf "  docker compose up -d --build\n"
printf "  docker compose logs -f\n"
