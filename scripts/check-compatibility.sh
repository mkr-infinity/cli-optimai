#!/usr/bin/env bash
# ============================================================
# Device and OS Compatibility Checker for OptimAI Network CLI
# Runs on any Unix/Linux/macOS terminal without root.
# ============================================================

set -u

C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_RED='\033[1;31m'
C_OFF='\033[0m'

OS="$(uname -s)"
ARCH="$(uname -m)"

# Distro detection
DISTRO_NAME="$OS"
if [ "$OS" = "Linux" ]; then
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_NAME="${PRETTY_NAME:-${NAME:-Linux}}"
  elif [ -f /etc/arch-release ]; then
    DISTRO_NAME="Arch Linux"
  elif [ -f /etc/debian_version ]; then
    DISTRO_NAME="Debian"
  fi
elif [ "$OS" = "Darwin" ]; then
  DISTRO_NAME="macOS $(sw_vers -productVersion 2>/dev/null || echo '')"
fi

printf "${C_CYAN}=== OptimAI CLI Device Compatibility Check ===${C_OFF}\n"
printf "Operating System: %s\n" "$DISTRO_NAME"
printf "Kernel:           %s %s\n" "$OS" "$(uname -r)"
printf "Architecture:     %s\n" "$ARCH"

# RAM & Disk (Advisory only — NOT enforced)
if [ -f /proc/meminfo ]; then
  RAM_MB=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
  printf "Memory (RAM):     %s MB (advisory only)\n" "$RAM_MB"
fi
if command -v df >/dev/null 2>&1; then
  DISK_FREE=$(df -h . | awk 'NR==2 {print $4}')
  printf "Free Disk:        %s (advisory only)\n" "$DISK_FREE"
fi

printf "%s\n" "----------------------------------------------"

COMPATIBLE=0
CLI_URL=""
REASON=""

if [ "$OS" = "Linux" ]; then
  case "$ARCH" in
    x86_64|amd64)
      COMPATIBLE=1
      CLI_URL="https://cli-node.optimai.network/optimai_cli_ubuntu"
      REASON="64-bit Linux is fully supported across Arch, Debian, Ubuntu, Fedora, openSUSE, etc."
      ;;
    aarch64|arm64|armv7l|armv6l|arm)
      COMPATIBLE=0
      REASON="Incompatible architecture: Linux $ARCH (ARM). The upstream OptimAI Network currently only distributes x86_64 binaries for Linux. (macOS Apple Silicon is supported via darwin_universal2, but Linux ARM is not yet published)."
      ;;
    i386|i686)
      COMPATIBLE=0
      REASON="Incompatible architecture: 32-bit Linux. OptimAI CLI requires a 64-bit operating system."
      ;;
    *)
      COMPATIBLE=0
      REASON="Incompatible architecture: '$ARCH' is not supported by OptimAI CLI."
      ;;
  esac
elif [ "$OS" = "Darwin" ]; then
  case "$ARCH" in
    x86_64|arm64)
      COMPATIBLE=1
      CLI_URL="https://cli-node.optimai.network/optimai_cli_darwin_universal2"
      REASON="macOS ($ARCH) is fully supported via the universal binary (Intel & Apple Silicon)."
      ;;
    *)
      COMPATIBLE=0
      REASON="Unsupported macOS architecture: $ARCH."
      ;;
  esac
elif echo "$OS" | grep -qi "MINGW\|MSYS\|CYGWIN"; then
  COMPATIBLE=1
  CLI_URL="https://cli-node.optimai.network/optimai_cli_windows.exe"
  REASON="Windows 64-bit is supported."
else
  COMPATIBLE=0
  REASON="Unsupported operating system: $OS. OptimAI CLI is officially supported on Linux, macOS, and Windows."
fi

if [ "$COMPATIBLE" -eq 1 ]; then
  printf "${C_GREEN}[RESULT: COMPATIBLE]${C_OFF}\n"
  printf "Status: %s\n" "$REASON"
  printf "Compatible CLI URL:\n  %s\n" "$CLI_URL"
  exit 0
else
  printf "${C_RED}[RESULT: INCOMPATIBLE]${C_OFF}\n"
  printf "Reason: %s\n" "$REASON"
  exit 1
fi
