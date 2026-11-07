#!/usr/bin/env bash
# ============================================================
# scripts/prompt-login.sh — Interactive Account Login Intake
# OptimAI Telegram Node (v1.3.0)
#
# Offers the two official OptimAI login methods in terminal:
# 1) Browser OAuth / Authorization Key
# 2) Direct Email & Password
# Features a 3-minute (180s) timeout with clean Enter-to-skip.
# ============================================================

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
    printf "\n\033[1;32m[✓]\033[0m Official OptimAI CLI is already authenticated.\n"
    return 0
  fi

  printf "\n\033[1m======================================================================\033[0m\n"
  printf "\033[1;36m  🔑 OPTIMAI ACCOUNT LOGIN (Optional — Auto-timeout: 3 minutes)\033[0m\n"
  printf "\033[1m======================================================================\033[0m\n"
  printf "  Choose your login method to connect this node to your OptimAI account:\n\n"
  printf "  \033[1m1) Browser OAuth / Authorization Key (Recommended)\033[0m\n"
  printf "     Open link in browser, sign in, and paste the authorization key/code.\n\n"
  printf "  \033[1m2) Direct Email & Password\033[0m\n"
  printf "     Sign in directly with your registered OptimAI email and password.\n\n"
  printf "  [Enter 1 or 2, or press Enter to skip / 180s timeout]: "

  read -r -t 180 METHOD_CHOICE || METHOD_CHOICE=""
  METHOD_CHOICE="$(echo "$METHOD_CHOICE" | tr -d '[:space:]')"

  if [ "$METHOD_CHOICE" = "1" ]; then
    printf "\n\033[1;32m==>\033[0m Launching official browser OAuth login flow...\n"
    "$CLI_BIN" auth login --no-open --paste || true
    printf "\n\033[1;32m[✓]\033[0m Login flow complete. Check status anytime with: %s auth status\n\n" "$CLI_BIN"

  elif [ "$METHOD_CHOICE" = "2" ]; then
    printf "\n\033[1;32m==>\033[0m Direct Email & Password Login:\n"
    printf "  Enter your OptimAI email: "
    read -r -t 180 EMAIL_INPUT || EMAIL_INPUT=""
    EMAIL_INPUT="$(echo "$EMAIL_INPUT" | tr -d '[:space:]')"

    printf "  Enter your OptimAI password: "
    read -r -s -t 180 PWD_INPUT || PWD_INPUT=""
    printf "\n"

    if [ -n "$EMAIL_INPUT" ] && [ -n "$PWD_INPUT" ]; then
      printf "  Authenticating with OptimAI Network...\n"
      printf "%s\n%s\n" "$EMAIL_INPUT" "$PWD_INPUT" | "$CLI_BIN" auth login 2>/dev/null || true
      printf "\n\033[1;32m[✓]\033[0m Direct login submitted. Verification: %s auth status\n\n" "$CLI_BIN"
    else
      printf "\n\033[1;33m[!] Email or password empty. Login skipped.\033[0m\n\n"
    fi

  else
    printf "\n\033[1;33m[!] Account login skipped or timed out.\033[0m\n"
    printf "    You can log in at any time:\n"
    printf "    • From Telegram Bot: send \033[1;36m/login\033[0m in Telegram\n"
    printf "    • From Terminal:     run \033[1;36moptimai-cli auth login\033[0m\n\n"
  fi
}
