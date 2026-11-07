#!/usr/bin/env bash
# ============================================================
# setup.sh — Universal Auto-Detecting Installer
# OptimAI Telegram Node (v1.3.0)
#
# Detects the operating environment (GitHub Codespaces, Android Termux,
# Linux VPS/Bare-Metal, macOS, or Windows) and runs the tailored setup.
# ============================================================

set -u

C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_BOLD='\033[1m'
C_OFF='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

printf "\n${C_BOLD}======================================================================${C_OFF}\n"
printf "${C_CYAN}         ⛏️  OPTIMAI UNIVERSAL ENVIRONMENT DETECTOR${C_OFF}\n"
printf "${C_BOLD}======================================================================${C_OFF}\n"

# 1. Android Termux
if [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then
  printf "  ${C_GREEN}[✓]${C_OFF} Detected Platform: ${C_BOLD}Android Termux${C_OFF}\n"
  printf "  Routing to setup-termux.sh...\n\n"
  exec bash "$SCRIPT_DIR/setup-termux.sh" "$@"

# 2. GitHub Codespaces
elif [ "${CODESPACES:-}" = "true" ] || [ -n "${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-}" ] || [[ "$SCRIPT_DIR" == /workspaces/* ]]; then
  printf "  ${C_GREEN}[✓]${C_OFF} Detected Platform: ${C_BOLD}GitHub Codespaces${C_OFF}\n"
  printf "  Routing to setup-codespaces.sh...\n\n"
  exec bash "$SCRIPT_DIR/setup-codespaces.sh" "$@"

# 3. Windows (Git Bash / MSYS / Cygwin)
elif [[ "${OSTYPE:-}" == "msys"* || "${OSTYPE:-}" == "cygwin"* || -n "${WINDIR:-}" ]]; then
  printf "  ${C_GREEN}[✓]${C_OFF} Detected Platform: ${C_BOLD}Windows${C_OFF}\n"
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/setup-windows.ps1"
    exit $?
  elif command -v powershell >/dev/null 2>&1; then
    powershell -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT_DIR/setup-windows.ps1"
    exit $?
  else
    printf "${C_YELLOW}PowerShell not found. Please run setup-windows.bat in cmd.${C_OFF}\n"
    exit 1
  fi

# 4. macOS (Darwin)
elif [ "$(uname -s)" = "Darwin" ]; then
  printf "  ${C_GREEN}[✓]${C_OFF} Detected Platform: ${C_BOLD}macOS (Darwin)${C_OFF}\n"
  ARCH="$(uname -m)"
  printf "  Architecture: %s\n" "$ARCH"

  # Install official Darwin binary
  mkdir -p "$HOME/.local/bin" ./data/data ./data/home ~/.optimai
  CLI_URL="https://cli-node.optimai.network/optimai_cli_darwin_universal2"
  printf "  Downloading official macOS OptimAI CLI...\n"
  curl -fsSL "$CLI_URL" -o "$HOME/.local/bin/optimai-bin"
  chmod +x "$HOME/.local/bin/optimai-bin"

  cat <<'EOF' > "$HOME/.local/bin/optimai-cli"
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
  chmod +x "$HOME/.local/bin/optimai-cli"
  export PATH="$HOME/.local/bin:$PATH"

  # Prime CLI
  "$HOME/.local/bin/optimai-cli" --help >/dev/null 2>&1 || true

  # Python virtual environment
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
  fi
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt -q

  if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
  fi

  if [ -f "$SCRIPT_DIR/scripts/prompt-login.sh" ]; then
    . "$SCRIPT_DIR/scripts/prompt-login.sh"
    prompt_account_login "$HOME/.local/bin/optimai-cli"
  fi

  if [ -f "$SCRIPT_DIR/scripts/prompt-env.sh" ]; then
    . "$SCRIPT_DIR/scripts/prompt-env.sh"
    prompt_telegram_credentials "$SCRIPT_DIR/.env" "$SCRIPT_DIR/.env.example" "bash '$SCRIPT_DIR/start.sh'"
  fi

  if [ ! -f .env ] || ! grep -q '^TELEGRAM_BOT_TOKEN=[0-9]' .env 2>/dev/null; then
    printf "\n${C_GREEN}Setup Complete! Edit .env and start with: bash start.sh${C_OFF}\n\n"
  fi
  exit 0

# 5. Linux VPS / Bare-Metal Linux
else
  printf "  ${C_GREEN}[✓]${C_OFF} Detected Platform: ${C_BOLD}Linux (VPS / Bare-Metal)${C_OFF}\n"
  if [ "$(id -u)" -ne 0 ]; then
    if sudo -n true 2>/dev/null; then
      exec sudo bash "$SCRIPT_DIR/setup-vps.sh" "$@"
    elif [ -t 0 ] && command -v sudo >/dev/null 2>&1; then
      printf "  Elevating with sudo to execute setup-vps.sh...\n\n"
      exec sudo bash "$SCRIPT_DIR/setup-vps.sh" "$@"
    else
      printf "${C_YELLOW}Notice: Running user-level setup (non-root / non-interactive)...${C_OFF}\n"
      exec bash "$SCRIPT_DIR/setup-codespaces.sh" "$@"
    fi
  else
    exec bash "$SCRIPT_DIR/setup-vps.sh" "$@"
  fi
fi
