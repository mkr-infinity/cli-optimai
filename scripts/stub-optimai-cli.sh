#!/usr/bin/env bash
# ============================================================
# stub-optimai-cli.sh — deterministic fake `optimai-cli` for the
# smoke test suite. Behaviors (mirrors the verified CLI surface):
#   auth login --no-open --paste -> prints the mock login URL, then
#                                   reads a line from stdin and prints
#                                   "Login successful."
#   auth status                  -> authenticated state from a flag file
#   node start                   -> "Node started (mock)" + heartbeats
#                                   every ~2s; exits gracefully on SIGINT
#   node stop                    -> "Node stopped (mock)"
#   rewards balance              -> fixed balance
#   --version                    -> "optimai-cli, version 0.1.63"
#
# ARG PARSING FIX: after `shift`, remaining args are $1 $2 ... — never
# check $3 for --no-open; scan the remaining argument list instead.
#
# Auth flag file: ${OPTIMAI_STUB_AUTH_FILE:-${HOME}/.stub_optimai_auth}
#   exists = authenticated, absent = "Not authenticated"
# Heartbeat interval: OPTIMAI_STUB_HEARTBEAT (default 2s)
# ============================================================

set -u

AUTH_FLAG="${OPTIMAI_STUB_AUTH_FILE:-${HOME:-/tmp}/.stub_optimai_auth}"
HEARTBEAT="${OPTIMAI_STUB_HEARTBEAT:-2}"
HEARTBEAT_LOG="${OPTIMAI_STUB_HEARTBEAT_LOG:-${HOME:-/tmp}/.stub_node_heartbeat}"

if [ "${1:-}" = "--version" ]; then
  echo "optimai-cli, version 0.1.63"
  exit 0
fi

cmd="${1:-}"
sub=""
if [ $# -gt 0 ]; then shift; fi
if [ $# -gt 0 ]; then sub="$1"; shift; fi

no_open=false
paste=false
legacy=false
for arg in "$@"; do
  case "$arg" in
    --no-open) no_open=true ;;
    --paste)   paste=true ;;
    --legacy)  legacy=true ;;
  esac
done

case "$cmd" in
  update)
    echo "Checking for OptimAI CLI updates..."
    echo "CLI is up to date (version 0.1.63)."
    exit 0
    ;;
  auth)
    case "$sub" in
      login)
        if [ "$legacy" = true ]; then
          printf "Email: "
          IFS= read -r email
          printf "Password: "
          IFS= read -r pass
          if [ "$pass" = "badpass" ] || [ "$pass" = "wrongpass" ]; then
            echo "Error: Invalid password"
            exit 1
          fi
          touch "$AUTH_FLAG"
          echo "Login successful."
          exit 0
        elif [ "$no_open" = true ]; then
          echo "Visit this URL to log in:"
          echo "https://mock.node.optimai.network/login?code=TEST123"
          echo "Then paste the redirect URL or code back into this prompt:"
          IFS= read -r REPLY
          if [ -n "$REPLY" ]; then
            echo "$AUTH_FLAG" | sed 's#^#touch file: #' >/dev/null
            touch "$AUTH_FLAG"
            echo "Login successful."
          else
            echo "Error: no redirect input received"
            exit 1
          fi
        else
          echo "Error: this stub only supports --no-open (headless)"
          exit 2
        fi
        ;;
      status)
        if [ -f "$AUTH_FLAG" ]; then
          echo "Authenticated as stub@example.com"
        else
          echo "Not authenticated"
        fi
        ;;
      me)
        if [ -f "$AUTH_FLAG" ]; then
          echo "Logged in as stub@example.com"
        else
          echo "Not authenticated"
        fi
        ;;
      logout)
        rm -f "$AUTH_FLAG"
        echo "Logged out successfully."
        ;;
      *)
        echo "Error: unknown auth subcommand: ${sub:-?}"
        exit 1
        ;;
    esac
    ;;

  node)
    case "$sub" in
      start)
        echo "Node started (mock)"
        trap 'echo "Node stopped (mock)"; exit 0' INT TERM
        i=0
        while :; do
          sleep "$HEARTBEAT"
          i=$((i + 1))
          echo "heartbeat $i: node running (mock)" >> "$HEARTBEAT_LOG.tmp" 2>/dev/null || true
          mv -f "$HEARTBEAT_LOG.tmp" "${HEARTBEAT_LOG}.hb" 2>/dev/null || true
        done
        ;;
      stop)
        echo "Node stopped (mock)"
        ;;
      status)
        echo "node status: running (mock)"
        ;;
      *)
        echo "Error: unknown node subcommand: ${sub:-?}"
        exit 1
        ;;
    esac
    ;;

  rewards)
    case "$sub" in
      balance)
        echo "Total rewards: 1234.56 OPTIMAI (stub)"
        ;;
      *)
        echo "Error: unknown rewards subcommand: ${sub:-?}"
        exit 1
        ;;
    esac
    ;;

  *)
    echo "Error: unknown command: ${cmd:-?}" >&2
    exit 64
    ;;
esac
