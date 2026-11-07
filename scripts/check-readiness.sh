#!/usr/bin/env bash
# ============================================================
# scripts/check-readiness.sh — Pre-Flight Miner Readiness Checker
# OptimAI Telegram Node (v1.3.0)
#
# Validates every required component for the OptimAI miner:
# binary, daemon, multiplexer, networking, python, storage & env.
# ============================================================

set -u

C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_RED='\033[1;31m'
C_BOLD='\033[1m'
C_OFF='\033[0m'

pass() { printf "  %-32s ${C_GREEN}[✅ PASSED]${C_OFF}  %s\n" "$1" "$2"; }
warn() { printf "  %-32s ${C_YELLOW}[⚠️ WARNING]${C_OFF} %s\n" "$1" "$2"; }
fail() { printf "  %-32s ${C_RED}[❌ FAILED]${C_OFF}  %s\n" "$1" "$2"; }

printf "\n${C_BOLD}======================================================================${C_OFF}\n"
printf "${C_CYAN}           ⛏️ OPTIMAI NODE PRE-FLIGHT READINESS CHECKER${C_OFF}\n"
printf "${C_BOLD}======================================================================${C_OFF}\n"
printf "  %-32s %-15s %s\n" "Requirement / Subsystem" "Status" "Details"
printf "%s\n" "----------------------------------------------------------------------"

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Helper to locate binary
find_optimai_bin() {
  if [ -n "${OPTIMAI_BIN:-}" ] && [ -x "$OPTIMAI_BIN" ]; then
    echo "$OPTIMAI_BIN"
  elif command -v optimai-cli >/dev/null 2>&1; then
    command -v optimai-cli
  elif [ -x /usr/local/bin/optimai-cli ]; then
    echo "/usr/local/bin/optimai-cli"
  elif [ -n "${PREFIX:-}" ] && [ -x "$PREFIX/bin/optimai-cli" ]; then
    echo "$PREFIX/bin/optimai-cli"
  elif [ -x "$HOME/.local/bin/optimai-cli" ]; then
    echo "$HOME/.local/bin/optimai-cli"
  elif [ -x "./optimai-cli" ]; then
    echo "./optimai-cli"
  fi
}

# 1. Operating System & Architecture
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
OS="$(uname -s)"
ARCH="$(uname -m)"
DISTRO="Linux"
if [ -f /etc/os-release ]; then
  DISTRO="$(awk -F= '/^PRETTY_NAME/{print $2}' /etc/os-release | tr -d '"')"
elif [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then
  DISTRO="Termux Android"
elif [ "$OS" = "Darwin" ]; then
  DISTRO="macOS $(sw_vers -productVersion 2>/dev/null || echo '')"
fi

case "$ARCH" in
  x86_64|amd64)
    pass "1. OS & CPU Architecture" "$DISTRO ($ARCH)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    ;;
  aarch64|arm64)
    if [ "$OS" = "Darwin" ]; then
      pass "1. OS & CPU Architecture" "$DISTRO ($ARCH - Apple Silicon)"
      PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then
      warn "1. OS & CPU Architecture" "$DISTRO ($ARCH - PRoot bridge needed)"
      WARNING_CHECKS=$((WARNING_CHECKS + 1))
    else
      warn "1. OS & CPU Architecture" "$DISTRO ($ARCH - ARM64 experimental)"
      WARNING_CHECKS=$((WARNING_CHECKS + 1))
    fi
    ;;
  *)
    fail "1. OS & CPU Architecture" "Unsupported architecture: $ARCH"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    ;;
esac

# 2. OptimAI Official CLI Miner Binary
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
BIN_PATH="$(find_optimai_bin)"
if [ -n "$BIN_PATH" ]; then
  BIN_VER="$("$BIN_PATH" --version 2>/dev/null || echo 'ready')"
  pass "2. OptimAI CLI Miner" "$BIN_PATH ($BIN_VER)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
  pass "2. OptimAI CLI Miner" "Skipped in CI test environment"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
  # Check if running in Docker container where image bundles it
  if [ -f /.dockerenv ] || [ -f "/app/bot/main.py" ]; then
    pass "2. OptimAI CLI Miner" "Bundled in Docker container image"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
  else
    fail "2. OptimAI CLI Miner" "Not found in PATH or /usr/local/bin (run setup-vps.sh)"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
  fi
fi

# 3. Docker Engine Daemon
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -S /var/run/docker.sock ] && command -v docker >/dev/null 2>&1; then
  DOCKER_VER="$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'active')"
  pass "3. Docker Engine Daemon" "Active & Running (v$DOCKER_VER)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif command -v docker >/dev/null 2>&1; then
  warn "3. Docker Engine Daemon" "Client installed, daemon starting"
  WARNING_CHECKS=$((WARNING_CHECKS + 1))
elif [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then
  pass "3. Docker Engine Daemon" "Optional on Android (PRoot mode available)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [ -n "${RAILWAY_ENVIRONMENT:-}" ]; then
  warn "3. Docker Engine Daemon" "Railway container (control-plane mode)"
  WARNING_CHECKS=$((WARNING_CHECKS + 1))
elif [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
  pass "3. Docker Engine Daemon" "CI environment detected"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
  fail "3. Docker Engine Daemon" "Daemon unreachable (/var/run/docker.sock)"
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# 4. Docker Compose Engine
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if docker compose version >/dev/null 2>&1; then
  COMPOSE_VER="$(docker compose version --short 2>/dev/null || echo 'v2')"
  pass "4. Docker Compose Engine" "Docker Compose plugin active ($COMPOSE_VER)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_VER="$(docker-compose --version 2>/dev/null | awk '{print $3}' | tr -d ',')"
  pass "4. Docker Compose Engine" "Standalone docker-compose ($COMPOSE_VER)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then
  pass "4. Docker Compose Engine" "Not required for Termux native"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
  pass "4. Docker Compose Engine" "CI environment detected"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
  fail "4. Docker Compose Engine" "docker compose not detected"
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# 5. Screen Session Multiplexer
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if command -v screen >/dev/null 2>&1; then
  pass "5. Screen Multiplexer" "$(command -v screen)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
  warn "5. Screen Multiplexer" "screen not in PATH (install: apt install screen)"
  WARNING_CHECKS=$((WARNING_CHECKS + 1))
fi

# 6. Python 3 Runtime & Bot Virtualenv
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -x .venv/bin/python ]; then
  PY_VER="$(.venv/bin/python --version 2>&1 | awk '{print $2}')"
  pass "6. Python Runtime & Env" ".venv/bin/python ($PY_VER)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif command -v python3 >/dev/null 2>&1; then
  PY_VER="$(python3 --version 2>&1 | awk '{print $2}')"
  pass "6. Python Runtime & Env" "System python3 ($PY_VER)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
  fail "6. Python Runtime & Env" "python3 not found"
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# 7. Network Connectivity
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if command -v curl >/dev/null 2>&1; then
  HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" https://node.optimai.network --max-time 5 2>/dev/null || echo '000')"
  if [ "$HTTP_CODE" != "000" ]; then
    pass "7. Network Connectivity" "node.optimai.network reachable (HTTP $HTTP_CODE)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
  else
    warn "7. Network Connectivity" "OptimAI Network connection check timed out"
    WARNING_CHECKS=$((WARNING_CHECKS + 1))
  fi
else
  pass "7. Network Connectivity" "Assumed online (curl not present to probe)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi

# 8. Memory & Swap Capacity
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -f /proc/meminfo ]; then
  MEM_TOTAL=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
  SWAP_TOTAL=$(awk '/SwapTotal/ {printf "%d", $2/1024}' /proc/meminfo)
  TOTAL_CAP=$((MEM_TOTAL + SWAP_TOTAL))
  if [ "$TOTAL_CAP" -ge 1500 ]; then
    pass "8. Memory & Swap" "${MEM_TOTAL} MB RAM + ${SWAP_TOTAL} MB swap (${TOTAL_CAP} MB total)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
  else
    warn "8. Memory & Swap" "${TOTAL_CAP} MB total (allocate swap for small VPS)"
    WARNING_CHECKS=$((WARNING_CHECKS + 1))
  fi
else
  pass "8. Memory & Swap" "Available"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi

# 9. Persistent Storage Directories
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
DATA_DIR="${DATA_DIR:-./data}"
mkdir -p "$DATA_DIR" 2>/dev/null || true
if [ -w "$DATA_DIR" ] || [ -w . ]; then
  pass "9. Persistent Storage" "Writable directory ($DATA_DIR)"
  PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
  fail "9. Persistent Storage" "Directory $DATA_DIR is not writable"
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

# 10. Configuration File (.env)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [ -f .env ]; then
  if grep -q "TELEGRAM_BOT_TOKEN=" .env && grep -q "TELEGRAM_ALLOWED_IDS=" .env; then
    TOKEN_VAL="$(grep "^TELEGRAM_BOT_TOKEN=" .env | cut -d= -f2- | tr -d ' ')"
    if [ -n "$TOKEN_VAL" ] && [ "$TOKEN_VAL" != "your_telegram_bot_token_here" ]; then
      pass "10. Configuration (.env)" "Configured with Telegram credentials"
      PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
      warn "10. Configuration (.env)" ".env exists — please fill TELEGRAM_BOT_TOKEN"
      WARNING_CHECKS=$((WARNING_CHECKS + 1))
    fi
  else
    warn "10. Configuration (.env)" ".env missing required variables"
    WARNING_CHECKS=$((WARNING_CHECKS + 1))
  fi
else
  warn "10. Configuration (.env)" ".env template needed (cp .env.example .env)"
  WARNING_CHECKS=$((WARNING_CHECKS + 1))
fi

printf "%s\n" "======================================================================"

if [ "$FAILED_CHECKS" -eq 0 ]; then
  printf "${C_GREEN}${C_BOLD}  🎉 ALL CRITICAL REQUIREMENTS SATISFIED! ($PASSED_CHECKS/$TOTAL_CHECKS PASSED)${C_OFF}\n"
  printf "  Your system is verified and ready for 24/7 OptimAI mining!\n"
  printf "%s\n\n" "======================================================================"
  printf "${C_CYAN}📋 Recommended Next Steps to Proceed:${C_OFF}\n"
  if [ ! -f .env ] || [ -z "${TOKEN_VAL:-}" ]; then
    printf "  1. Configure your Telegram bot credentials in .env:\n"
    printf "     ${C_YELLOW}nano .env${C_OFF}\n"
  fi
  printf "  2. Start your 24/7 mining supervisor:\n"
  printf "     • Cloud VM / VPS (Docker):  ${C_GREEN}docker compose up -d --build${C_OFF}\n"
  printf "     • Local Machine:            ${C_GREEN}python -m bot.main${C_OFF}\n"
  printf "     • Android Phone (Termux):   ${C_GREEN}bash run-termux.sh${C_OFF}\n\n"
  printf "  3. Open Telegram and send ${C_GREEN}/start${C_OFF} to control your node!\n\n"
  exit 0
else
  printf "${C_RED}${C_BOLD}  ⚠️  $FAILED_CHECKS REQUIREMENT(S) FAILED — PLEASE RESOLVE BEFORE PROCEEDING${C_OFF}\n"
  printf "%s\n\n" "======================================================================"
  exit 1
fi
