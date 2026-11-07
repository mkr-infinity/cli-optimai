#!/usr/bin/env bash
# ============================================================
# setup-termux-proot.sh — Full On-Device ARM64 Mining via PRoot
# OptimAI Telegram Node (v1.3.0)
#
# Enables running the official x86_64 OptimAI CLI binary on
# ARM64 Android phones using PRoot Ubuntu and QEMU x86_64 emulation.
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

step "1/4 Verifying Termux packages & PRoot Distro"
if ! command -v proot-distro >/dev/null 2>&1; then
  info "Installing proot-distro..."
  pkg update -y || true
  pkg install -y proot-distro
fi

step "2/4 Installing Ubuntu environment inside Termux"
if proot-distro list 2>/dev/null | grep -q "ubuntu.*installed"; then
  info "Ubuntu rootfs is already installed."
else
  info "Downloading and provisioning Ubuntu rootfs (this may take 1-2 minutes)..."
  proot-distro install ubuntu
fi

step "3/4 Installing QEMU emulation & official OptimAI CLI in Ubuntu"
info "Configuring x86_64 emulation, downloading and priming optimai-cli..."
proot-distro login ubuntu -- bash -c '
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y -q
  apt-get install -y -q curl ca-certificates qemu-user-static
  curl -fsSL "https://cli-node.optimai.network/optimai_cli_ubuntu" -o /usr/local/bin/optimai-bin
  chmod +x /usr/local/bin/optimai-bin
  cat <<INNER_EOF > /usr/local/bin/optimai-cli
#!/usr/bin/env bash
args=()
for arg in "\$@"; do
  if [ "\$arg" = "-v" ]; then
    args+=("--version")
  else
    args+=("\$arg")
  fi
done
exec /usr/local/bin/optimai-bin "\${args[@]}"
INNER_EOF
  chmod +x /usr/local/bin/optimai-cli
  /usr/local/bin/optimai-cli --help >/dev/null 2>&1 || true
'

step "4/4 Creating transparent Termux CLI bridge"
PREFIX_DIR="${PREFIX:-/data/data/com.termux/files/usr}"
WRAPPER_PATH="$PREFIX_DIR/bin/optimai-cli"
USER_BIN="$HOME/.local/bin/optimai-cli"

mkdir -p "$PREFIX_DIR/bin" "$HOME/.local/bin"

cat <<'EOF' > "$WRAPPER_PATH"
#!/usr/bin/env bash
# Transparent bridge from Termux into PRoot Ubuntu x86_64 emulation
args=()
for arg in "$@"; do
  if [ "$arg" = "-v" ]; then
    args+=("--version")
  else
    args+=("$arg")
  fi
done
exec proot-distro login ubuntu -- /usr/local/bin/optimai-cli "${args[@]}"
EOF
chmod +x "$WRAPPER_PATH"
cp -f "$WRAPPER_PATH" "$USER_BIN"

printf "\n${C_GREEN}============================================================${C_OFF}\n"
printf "${C_GREEN} PRoot On-Device Mining Setup Complete! ⛏️${C_OFF}\n"
printf " The official OptimAI CLI is now bridged to Termux.\n"
printf " Test it by running:        optimai-cli --version\n"
printf " Launch your bot:           bash run-termux.sh\n"
printf "${C_GREEN}============================================================${C_OFF}\n"
