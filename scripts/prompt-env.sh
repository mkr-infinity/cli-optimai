#!/usr/bin/env bash
# ============================================================
# scripts/prompt-env.sh — Interactive Telegram Credentials Intake
# OptimAI Telegram Node (v1.9.0)
#
# Prompts the user interactively with a 60-second timeout for
# TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_IDS.
# Safe for non-interactive / headless runners (skips automatically).
# ============================================================

prompt_telegram_credentials() {
  ENV_FILE="${1:-.env}"
  ENV_EXAMPLE="${2:-.env.example}"
  AUTO_START_CMD="${3:-}"

  # If not an interactive terminal and no input piped, do not prompt
  if [ ! -t 0 ] && [ ! -p /dev/stdin ]; then
    return 0
  fi

  # Check if .env already has real credentials configured
  if [ -f "$ENV_FILE" ] && grep -q '^TELEGRAM_BOT_TOKEN=[0-9]' "$ENV_FILE" 2>/dev/null && grep -q '^TELEGRAM_ALLOWED_IDS=[0-9]' "$ENV_FILE" 2>/dev/null; then
    printf "\n\033[1;32m[✓]\033[0m Active Telegram credentials already configured in %s.\n" "$ENV_FILE"
    printf "    Press Enter to keep existing credentials, or type 'r' within 60s to reconfigure: "
    read -r -t 60 RECONFIG || RECONFIG=""
    if [ "$RECONFIG" != "r" ] && [ "$RECONFIG" != "R" ]; then
      if [ -n "$AUTO_START_CMD" ]; then
        eval "$AUTO_START_CMD"
      fi
      return 0
    fi
  fi

  printf "\n\033[1m======================================================================\033[0m\n"
  printf "\033[1;36m  🤖 TELEGRAM CREDENTIALS CONFIGURATION (Auto-timeout: 60 seconds)\033[0m\n"
  printf "\033[1m======================================================================\033[0m\n"
  printf "  Enter your credentials below, or press Enter to skip and configure later.\n\n"

  # 1. Telegram Bot Token
  printf "  1. Enter your \033[1mTELEGRAM_BOT_TOKEN\033[0m (from @BotFather)\n"
  printf "     [Press Enter to skip / 60s timeout]: "
  read -r -t 60 TOKEN_INPUT || TOKEN_INPUT=""
  TOKEN_INPUT="$(echo "$TOKEN_INPUT" | tr -d '[:space:]')"

  # 2. Telegram Allowed IDs
  printf "\n  2. Enter your \033[1mTELEGRAM_ALLOWED_IDS\033[0m (numeric ID from @userinfobot)\n"
  printf "     [Press Enter to skip / 60s timeout]: "
  read -r -t 60 IDS_INPUT || IDS_INPUT=""
  IDS_INPUT="$(echo "$IDS_INPUT" | tr -d '[:space:]')"

  if [ -n "$TOKEN_INPUT" ] && [ -n "$IDS_INPUT" ]; then
    if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_EXAMPLE" ]; then
      cp "$ENV_EXAMPLE" "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"
    elif [ ! -f "$ENV_FILE" ]; then
      touch "$ENV_FILE"
    fi

    # Update or append TELEGRAM_BOT_TOKEN
    if grep -q '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" 2>/dev/null; then
      sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$TOKEN_INPUT|" "$ENV_FILE"
    else
      echo "TELEGRAM_BOT_TOKEN=$TOKEN_INPUT" >> "$ENV_FILE"
    fi

    # Update or append TELEGRAM_ALLOWED_IDS
    if grep -q '^TELEGRAM_ALLOWED_IDS=' "$ENV_FILE" 2>/dev/null; then
      sed -i "s|^TELEGRAM_ALLOWED_IDS=.*|TELEGRAM_ALLOWED_IDS=$IDS_INPUT|" "$ENV_FILE"
    else
      echo "TELEGRAM_ALLOWED_IDS=$IDS_INPUT" >> "$ENV_FILE"
    fi

    # Ensure NODE_AUTO_START=true
    if ! grep -q '^NODE_AUTO_START=' "$ENV_FILE" 2>/dev/null; then
      echo "NODE_AUTO_START=true" >> "$ENV_FILE"
    fi

    printf "\n  \033[1;32m[✓] Telegram credentials successfully configured in %s!\033[0m\n\n" "$ENV_FILE"

    if [ -n "$AUTO_START_CMD" ]; then
      printf "\033[1m======================================================================\033[0m\n"
      printf "\033[1;32m  🚀 Starting OptimAI Bot and AI Miner Node...\033[0m\n"
      printf "\033[1m======================================================================\033[0m\n\n"
      eval "$AUTO_START_CMD"
    fi
  else
    printf "\n  \033[1;33m[!] Credentials setup skipped or timed out.\033[0m\n"
    printf "      Please manually enter your credentials in %s before starting:\n" "$ENV_FILE"
    printf "      \033[1;36mnano %s\033[0m\n\n" "$ENV_FILE"
  fi
}
