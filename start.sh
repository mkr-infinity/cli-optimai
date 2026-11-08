#!/usr/bin/env bash
# ============================================================
# start.sh — Universal Launcher for OptimAI Telegram Bot & Miner
# OptimAI Telegram Bot (v1.9.0)
#
# Starts both the 24/7 Telegram supervisor bot AND the OptimAI
# mining node in the background across VPS, local machine & Termux.
# ============================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_RED='\033[1;31m'
C_BOLD='\033[1m'
C_OFF='\033[0m'

step() { printf "${C_CYAN}==>${C_OFF} ${C_GREEN}%s${C_OFF}\n" "$*"; }
info() { printf "${C_CYAN}[info]${C_OFF} %s\n" "$*"; }
warn() { printf "${C_YELLOW}[warn]${C_OFF} %s\n" "$*"; }

# 1. Environment file check
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    warn "Created .env from .env.example. Please configure TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS in .env"
  else
    printf "${C_RED}ERROR: .env file missing!${C_OFF}\n"
    exit 1
  fi
fi

# Ensure NODE_AUTO_START=true so mining automatically starts with bot
export NODE_AUTO_START=true

# Ensure storage directories and permissions
mkdir -p ./data/data ./data/home ~/.optimai 2>/dev/null || true
chmod -R a+rwX ./data 2>/dev/null || true

# If optimai-cli is present locally, make executable and install to PATH
if [ -f "./optimai-cli" ] && [ ! -x "/usr/local/bin/optimai-cli" ]; then
  chmod +x "./optimai-cli"
  sudo mv "./optimai-cli" /usr/local/bin/optimai-cli 2>/dev/null || mv "./optimai-cli" "$HOME/.local/bin/optimai-cli" 2>/dev/null || true
fi

# Bi-directional credential & database sync before starting
if [ -f scripts/sync-credentials.sh ]; then
  bash scripts/sync-credentials.sh >/dev/null 2>&1 || true
fi

# 2. Check execution mode (Docker vs Native/Termux)
IS_TERMUX=false
if [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then
  IS_TERMUX=true
fi

# Check if Telegram credentials are configured in .env
HAS_TELEGRAM_TOKEN=false
if [ -f .env ] && grep -q '^TELEGRAM_BOT_TOKEN=[0-9]' .env 2>/dev/null && grep -q '^TELEGRAM_ALLOWED_IDS=[0-9]' .env 2>/dev/null; then
  HAS_TELEGRAM_TOKEN=true
fi

# If Telegram credentials are not configured, start the official OptimAI mining node directly
if [ "$HAS_TELEGRAM_TOKEN" = false ]; then
  printf "\n${C_BOLD}======================================================================${C_OFF}\n"
  printf "${C_CYAN}  ⛏️  Starting Official OptimAI Node (optimai-cli node start)...${C_OFF}\n"
  printf "${C_BOLD}======================================================================${C_OFF}\n"
  printf "  Notice: Telegram Bot credentials not configured in .env.\n"
  printf "  Starting the official OptimAI mining node directly in background...\n\n"

  CLI_BIN="optimai-cli"
  if ! command -v "$CLI_BIN" >/dev/null 2>&1; then
    if [ -x "/usr/local/bin/optimai-cli" ]; then
      CLI_BIN="/usr/local/bin/optimai-cli"
    elif [ -x "$HOME/.local/bin/optimai-cli" ]; then
      CLI_BIN="$HOME/.local/bin/optimai-cli"
    fi
  fi

  if command -v screen >/dev/null 2>&1; then
    screen -dmS optimai "$CLI_BIN" node start
    printf "  ${C_GREEN}[🚀] OptimAI Node running in screen session!${C_OFF}\n"
    printf "  • Command:        ${C_CYAN}%s node start${C_OFF}\n" "$CLI_BIN"
    printf "  • View Terminal:  ${C_CYAN}screen -r optimai${C_OFF} (Detach: Ctrl+A then D)\n"
    printf "  • Check Status:   ${C_CYAN}%s node status${C_OFF}\n" "$CLI_BIN"
    printf "  • View Rewards:   ${C_CYAN}%s rewards balance${C_OFF}\n" "$CLI_BIN"
    printf "  • Stop Node:      Press ${C_CYAN}Ctrl+C${C_OFF} in screen session\n\n"
  else
    mkdir -p ./data 2>/dev/null || true
    nohup "$CLI_BIN" node start > ./data/node.log 2>&1 </dev/null &
    printf "  ${C_GREEN}[🚀] OptimAI Node started in background (PID %s)!${C_OFF}\n" "$!"
    printf "  • Command:      ${C_CYAN}%s node start${C_OFF}\n" "$CLI_BIN"
    printf "  • Check Status: ${C_CYAN}%s node status${C_OFF}\n" "$CLI_BIN"
    printf "  • View Rewards: ${C_CYAN}%s rewards balance${C_OFF}\n\n" "$CLI_BIN"
  fi
  printf "  💡 Tip: To enable 24/7 Telegram Remote Bot control, add your token to .env:\n"
  printf "     ${C_YELLOW}nano .env${C_OFF} -> set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS\n"
  printf "     Then run: ${C_GREEN}bash start.sh${C_OFF}\n\n"
  exit 0
fi

DOCKER_AVAILABLE=false
if [ "$IS_TERMUX" = false ] && command -v docker >/dev/null 2>&1; then
  if [ -S /var/run/docker.sock ] || docker info >/dev/null 2>&1; then
    DOCKER_AVAILABLE=true
  fi
fi

# 3. Launch Both Bot and Miner
if [ "$DOCKER_AVAILABLE" = true ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  REUSE_EXISTING=false

  # Pre-flight container conflict check & interactive resolution
  for conflict_resolver in "$SCRIPT_DIR/scripts/handle-docker-container.sh" "scripts/handle-docker-container.sh"; do
    if [ -f "$conflict_resolver" ]; then
      . "$conflict_resolver"
      resolve_container_conflict "" 60
      CONFLICT_RES=$?
      if [ $CONFLICT_RES -eq 2 ]; then
        REUSE_EXISTING=true
      fi
      break
    fi
  done

  if [ "$REUSE_EXISTING" = false ]; then
    step "Starting OptimAI Bot & AI Miner via Docker Compose..."
    if docker compose version >/dev/null 2>&1; then
      if command -v safe_docker_compose_up >/dev/null 2>&1; then
        safe_docker_compose_up "docker compose"
      else
        docker compose up -d --build
      fi
    elif command -v docker-compose >/dev/null 2>&1; then
      if command -v safe_docker_compose_up >/dev/null 2>&1; then
        safe_docker_compose_up "docker-compose"
      else
        docker-compose up -d --build
      fi
    else
      docker rm -f optimai-telegram-bot optimai-telegram-node optimai-node >/dev/null 2>&1 || true
      docker run -d --name optimai-telegram-bot --restart unless-stopped -v /var/run/docker.sock:/var/run/docker.sock -v ./data:/data optimai-telegram-bot
    fi
  fi

  printf "\n${C_BOLD}======================================================================${C_OFF}\n"
  printf "${C_GREEN}  🚀 OptimAI Telegram Bot & AI Miner Started Successfully!${C_OFF}\n"
  printf "${C_BOLD}======================================================================${C_OFF}\n"
  if [ "$REUSE_EXISTING" = true ]; then
    printf "  • Supervisor Bot:  ${C_GREEN}RUNNING${C_OFF} (Docker Container - Reused Existing)\n"
  else
    printf "  • Supervisor Bot:  ${C_GREEN}RUNNING${C_OFF} (Docker Container)\n"
  fi
  printf "  • AI Miner Node:   ${C_GREEN}RUNNING${C_OFF} (Auto-started with NODE_AUTO_START=true)\n"
  printf "  • Live Logs:       ${C_CYAN}make logs${C_OFF} or ${C_CYAN}docker compose logs -f${C_OFF}\n"
  printf "  • Telegram Bot:    Open Telegram and send ${C_GREEN}/start${C_OFF} or ${C_GREEN}/status${C_OFF}\n"
  printf "%s\n\n" "======================================================================"

elif [ "$IS_TERMUX" = true ]; then
  step "Starting OptimAI Bot & Miner on Android Termux..."
  if [ -f run-termux.sh ]; then
    bash run-termux.sh
  elif [ -x .venv/bin/python ]; then
    if command -v termux-wake-lock >/dev/null 2>&1; then
      termux-wake-lock
    fi
    screen -dmS optimai bash -c "cd $(pwd) && export NODE_AUTO_START=true && .venv/bin/python -m bot.main"
    printf "\n${C_GREEN}✅ Launched in background screen session!${C_OFF}\n"
    printf "• View terminal:  screen -r optimai\n"
    printf "• Telegram:       Send /start in Telegram\n"
  else
    warn "Python environment not ready. Run 'bash setup-termux.sh' first."
    exit 1
  fi

else
  # Native Linux/macOS Python execution
  step "Starting OptimAI Bot & Miner locally in background screen session..."
  PY_BIN="python3"
  if [ -x .venv/bin/python ]; then
    PY_BIN=".venv/bin/python"
  fi

  if command -v screen >/dev/null 2>&1; then
    if screen -ls 2>/dev/null | grep -q "optimai"; then
      warn "An OptimAI screen session ('optimai') is already active."
      info "Attaching or viewing: screen -r optimai"
      info "To restart cleanly:   screen -S optimai -X quit && bash start.sh"
    else
      screen -dmS optimai bash -c "cd $(pwd) && export NODE_AUTO_START=true && $PY_BIN -m bot.main"
    fi
    printf "\n${C_BOLD}======================================================================${C_OFF}\n"
    printf "${C_GREEN}  🚀 OptimAI Bot & Miner Started in Background Screen Session!${C_OFF}\n"
    printf "${C_BOLD}======================================================================${C_OFF}\n"
    printf "  • Screen Session:  ${C_GREEN}optimai${C_OFF} (screen -r optimai)\n"
    printf "  • AI Miner Node:   ${C_GREEN}RUNNING${C_OFF} (NODE_AUTO_START=true)\n"
    printf "  • Live Logs:       ${C_CYAN}make logs${C_OFF} or ${C_CYAN}python -m bot.main logs${C_OFF}\n"
    printf "  • Telegram:        Send ${C_GREEN}/start${C_OFF} in Telegram\n"
    printf "%s\n\n" "======================================================================"
  else
    info "Launching bot and miner in current terminal (screen not installed)..."
    export NODE_AUTO_START=true
    $PY_BIN -m bot.main
  fi
fi
