#!/usr/bin/env bash
# ============================================================
# scripts/prompt-login.sh — Interactive Account Login Intake & Node Launcher
# OptimAI Telegram Bot (v1.9.0)
#
# Offers the two official OptimAI login methods in terminal:
# 1) Browser OAuth / Authorization Key (optimai-cli auth login)
# 2) Direct Email & Password (optimai-cli auth login --legacy)
#
# Once authenticated, verifies Docker and auto-starts the official
# OptimAI mining node: optimai-cli node start
# ============================================================

start_optimai_node() {
  CLI_BIN="${1:-optimai-cli}"
  if ! command -v "$CLI_BIN" >/dev/null 2>&1; then
    if [ -x "/usr/local/bin/optimai-cli" ]; then
      CLI_BIN="/usr/local/bin/optimai-cli"
    elif [ -x "$HOME/.local/bin/optimai-cli" ]; then
      CLI_BIN="$HOME/.local/bin/optimai-cli"
    else
      return 0
    fi
  fi

  # If Telegram credentials are configured or SUPPRESS_DIRECT_NODE_START is true,
  # the 24/7 supervisor bot will manage and auto-start both the bot and the mining node.
  HAS_TELEGRAM_TOKEN=false
  if [ -f .env ] && grep -q '^TELEGRAM_BOT_TOKEN=[0-9]' .env 2>/dev/null && grep -q '^TELEGRAM_ALLOWED_IDS=[0-9]' .env 2>/dev/null; then
    HAS_TELEGRAM_TOKEN=true
  fi

  if [ "${SUPPRESS_DIRECT_NODE_START:-false}" = "true" ] || [ "$HAS_TELEGRAM_TOKEN" = "true" ]; then
    printf "\n\033[1;32m[✓]\033[0m Official OptimAI CLI authenticated and primed!\n"
    printf "    The 24/7 Telegram Bot supervisor will manage and auto-start both\n"
    printf "    the Telegram bot controller and the mining node (%s node start).\n\n" "$CLI_BIN"
    return 0
  fi

  # Check if running in automated test suite
  if [ -n "${OPTIMAI_STUB_AUTH_FILE:-}" ]; then
    printf "\033[1;32m[✓]\033[0m Official OptimAI Node ready to run: %s node start\n" "$CLI_BIN"
    return 0
  fi

  # Check if node is already running
  NODE_STAT="$("$CLI_BIN" node status 2>/dev/null || true)"
  if echo "$NODE_STAT" | grep -qiE "running|active|PID|another node instance"; then
    printf "\n\033[1;32m[✓]\033[0m Official OptimAI Node is already running.\n"
    return 0
  fi

  # Check Docker requirement: "Keep Docker Desktop running before you start the node."
  DOCKER_OK=false
  IS_TERMUX=false
  if [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then
    IS_TERMUX=true
  fi

  if [ -S /var/run/docker.sock ] || docker info >/dev/null 2>&1; then
    DOCKER_OK=true
  elif command -v systemctl >/dev/null 2>&1 && sudo -n systemctl start docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
      DOCKER_OK=true
    fi
  fi

  if [ "$DOCKER_OK" = false ]; then
    if [ "$IS_TERMUX" = true ]; then
      printf "\n\033[1;36m[i] Android Termux environment detected.\033[0m\n"
      printf "    Starting official OptimAI Node via Termux / PRoot bridge (%s node start)...\n" "$CLI_BIN"
    else
      printf "\n\033[1;33m[!] Notice: Docker is not currently running.\033[0m\n"
      printf "    \033[1mTip: Keep Docker Desktop (Windows/macOS) or Docker Engine (Linux) running before you start the node.\033[0m\n"
      printf "    Once Docker is running, start your node with:\n"
      printf "    \033[1;32m%s node start\033[0m\n\n" "$CLI_BIN"
      return 0
    fi
  fi

  printf "\n\033[1;32m==>\033[0m Starting official OptimAI Node (%s node start)...\n" "$CLI_BIN"
  if command -v screen >/dev/null 2>&1; then
    screen -dmS optimai "$CLI_BIN" node start
    printf "\n\033[1;32m[🚀] OptimAI Node started in background screen session!\033[0m\n"
    printf "    • Command:          \033[1;36m%s node start\033[0m\n" "$CLI_BIN"
    printf "    • View Terminal:    \033[1;36mscreen -r optimai\033[0m (Detach: Press Ctrl+A then D)\n"
    printf "    • Check Status:     \033[1;36m%s node status\033[0m\n" "$CLI_BIN"
    printf "    • View Rewards:     \033[1;36m%s rewards balance\033[0m\n" "$CLI_BIN"
    printf "    • Stop Node:        Press \033[1;36mCtrl+C\033[0m in screen session\n\n"
  else
    mkdir -p ./data 2>/dev/null || true
    nohup "$CLI_BIN" node start > ./data/node.log 2>&1 </dev/null &
    NODE_PID=$!
    printf "\n\033[1;32m[🚀] OptimAI Node started in background (PID %s)!\033[0m\n" "$NODE_PID"
    printf "    • Command:          \033[1;36m%s node start\033[0m\n" "$CLI_BIN"
    printf "    • Check Status:     \033[1;36m%s node status\033[0m\n" "$CLI_BIN"
    printf "    • View Rewards:     \033[1;36m%s rewards balance\033[0m\n" "$CLI_BIN"
    printf "    • Stop Node:        \033[1;36mkill %s\033[0m\n\n" "$NODE_PID"
  fi
}

prompt_account_login() {
  CLI_BIN="${1:-optimai-cli}"
  if ! command -v "$CLI_BIN" >/dev/null 2>&1; then
    if [ -x "/usr/local/bin/optimai-cli" ]; then
      CLI_BIN="/usr/local/bin/optimai-cli"
    elif [ -x "$HOME/.local/bin/optimai-cli" ]; then
      CLI_BIN="$HOME/.local/bin/optimai-cli"
    else
      return 0
    fi
  fi

  # Skip if non-interactive and no piped input
  if [ ! -t 0 ] && [ ! -p /dev/stdin ]; then
    return 0
  fi

  # Check if already authenticated
  STATUS_OUT="$("$CLI_BIN" auth status 2>/dev/null || true)"
  if echo "$STATUS_OUT" | grep -qiE "not authenticated|not logged in|unauthenticated"; then
    : # Not authenticated, proceed to prompt
  elif echo "$STATUS_OUT" | grep -qiE "authenticated|logged in|user:"; then
    printf "\n\033[1;32m[✓]\033[0m Official OptimAI CLI is already authenticated:\n"
    printf "    • %s\n" "$STATUS_OUT"
    start_optimai_node "$CLI_BIN"
    return 0
  fi

  printf "\n\033[1m======================================================================\033[0m\n"
  printf "\033[1;36m  🔑 OPTIMAI ACCOUNT LOGIN (Optional — Auto-timeout: 3 minutes)\033[0m\n"
  printf "\033[1m======================================================================\033[0m\n"
  printf "  Choose your sign-in method to connect this node to your OptimAI account:\n\n"
  printf "  \033[1m1) Browser Login: optimai-cli auth login (Recommended)\033[0m\n"
  printf "     Sign in via the OptimAI Node Dashboard in your browser and complete login.\n\n"
  printf "  \033[1m2) Legacy Login (email/password): optimai-cli auth login --legacy\033[0m\n"
  printf "     If you prefer to use email/password instead of browser login.\n\n"
  printf "  [Enter 1 or 2, or press Enter to skip / 180s timeout]: "

  read -r -t 180 METHOD_CHOICE || METHOD_CHOICE=""
  METHOD_CHOICE="$(echo "$METHOD_CHOICE" | tr -d '[:space:]')"

  if [ "$METHOD_CHOICE" = "1" ]; then
    printf "\n\033[1;32m==>\033[0m Launching Browser Login (optimai-cli auth login)...\n"
    "$CLI_BIN" auth login --no-open --paste || true
    for sync_cand in "$SCRIPT_DIR/sync-credentials.sh" "$SCRIPT_DIR/../scripts/sync-credentials.sh" "scripts/sync-credentials.sh"; do
      if [ -f "$sync_cand" ]; then
        bash "$sync_cand" >/dev/null 2>&1 || true
        break
      fi
    done
    STATUS_CHECK="$("$CLI_BIN" auth status 2>&1 || true)"
    if echo "$STATUS_CHECK" | grep -qiE "not authenticated|unauthenticated|not logged in" || [ -z "$STATUS_CHECK" ]; then
      printf "\n\033[1;31m[❌] Authentication failed:\033[0m %s\n" "${STATUS_CHECK:-No authentication confirmation received}"
      printf "    Please verify your authorization code or URL, then try again.\n\n"
    elif echo "$STATUS_CHECK" | grep -qiE "authenticated|logged in|user:"; then
      printf "\n\033[1;32m[✓] Authenticated successfully with OptimAI Network!\033[0m\n"
      printf "    • %s\n\n" "$STATUS_CHECK"
      start_optimai_node "$CLI_BIN"
    else
      printf "\n\033[1;31m[❌] Authentication failed:\033[0m %s\n" "$STATUS_CHECK"
      printf "    Please verify your authorization code or URL, then try again.\n\n"
    fi

  elif [ "$METHOD_CHOICE" = "2" ]; then
    printf "\n\033[1;32m==>\033[0m Legacy Login (optimai-cli auth login --legacy):\n"
    printf "  Enter your OptimAI email: "
    read -r -t 180 EMAIL_INPUT || EMAIL_INPUT=""
    EMAIL_INPUT="$(echo "$EMAIL_INPUT" | tr -d '[:space:]')"

    printf "  Enter your OptimAI password: "
    read -r -s -t 180 PWD_INPUT || PWD_INPUT=""
    printf "\n"

    if [ -n "$EMAIL_INPUT" ] && [ -n "$PWD_INPUT" ]; then
      printf "  Authenticating with OptimAI Network (legacy login)...\n"
      LOGIN_OUT="$(printf "%s\n%s\n" "$EMAIL_INPUT" "$PWD_INPUT" | "$CLI_BIN" auth login --legacy 2>&1 || true)"
      FILTERED_OUT="$(printf "%s\n" "$LOGIN_OUT" | sed -E 's/(Email: *|Password: *)+//g' | grep -v '^[[:space:]]*$' || true)"
      if [ -n "$FILTERED_OUT" ]; then
        printf "%s\n" "$FILTERED_OUT"
      fi
      for sync_cand in "$SCRIPT_DIR/sync-credentials.sh" "$SCRIPT_DIR/../scripts/sync-credentials.sh" "scripts/sync-credentials.sh"; do
        if [ -f "$sync_cand" ]; then
          bash "$sync_cand" >/dev/null 2>&1 || true
          break
        fi
      done

      STATUS_CHECK="$("$CLI_BIN" auth status 2>&1 || true)"
      if echo "$STATUS_CHECK" | grep -qiE "not authenticated|unauthenticated|not logged in" || [ -z "$STATUS_CHECK" ]; then
        ERR_MSG="$(printf "%s\n" "$LOGIN_OUT" | grep -iE "error|invalid|fail|incorrect|wrong|denied" | head -n 2)"
        printf "\n\033[1;31m[❌] Authentication failed with OptimAI Network:\033[0m %s\n" "${ERR_MSG:-$STATUS_CHECK}"
        printf "    The node reported that the email or password entered is incorrect.\n"
        printf "    Please re-run 'bash start.sh' or '%s auth login --legacy' with the correct details.\n\n" "$CLI_BIN"
      elif echo "$STATUS_CHECK" | grep -qiE "authenticated|logged in|user:"; then
        printf "\n\033[1;32m[✓]\033[0m Legacy login submitted: Authenticated successfully with OptimAI Network!\n"
        printf "    • %s\n\n" "$STATUS_CHECK"
        start_optimai_node "$CLI_BIN"
      else
        ERR_MSG="$(printf "%s\n" "$LOGIN_OUT" | grep -iE "error|invalid|fail|incorrect|wrong|denied" | head -n 2)"
        printf "\n\033[1;31m[❌] Authentication failed with OptimAI Network:\033[0m %s\n" "${ERR_MSG:-$STATUS_CHECK}"
        printf "    The node reported that the email or password entered is incorrect.\n"
        printf "    Please re-run 'bash start.sh' or '%s auth login --legacy' with the correct details.\n\n" "$CLI_BIN"
      fi
    else
      printf "\n\033[1;33m[!] Email or password empty. Login skipped.\033[0m\n\n"
    fi

  else
    printf "\n\033[1;33m[!] Account login skipped or timed out.\033[0m\n"
    printf "    You can sign in at any time:\n"
    printf "    • From Telegram Bot: send \033[1;36m/login\033[0m or \033[1;36m/login --legacy\033[0m\n"
    printf "    • Browser Login:     run \033[1;36moptimai-cli auth login\033[0m\n"
    printf "    • Legacy Login:      run \033[1;36moptimai-cli auth login --legacy\033[0m\n\n"
  fi
}
