#!/usr/bin/env bash
# ============================================================
# scripts/handle-docker-container.sh — Docker Container Lifecycle & Conflict Resolver
# OptimAI Telegram Node (v1.9.0)
#
# Detects existing containers named 'optimai-telegram-node' or 'optimai-node'.
# Interactively prompts user with auto-timeout (default 60s) to choose between:
#   1) Clean Install (Recommended) — remove conflicting container and start fresh
#   2) Use Existing Container — keep and resume/start the existing container
# Also provides automatic recovery if Docker Compose encounters a name conflict.
# ============================================================

set -u

TARGET_CONTAINER_NAMES=("optimai-telegram-node" "optimai-node")
PROMPT_TIMEOUT="${CONTAINER_PROMPT_TIMEOUT:-60}"

# Color codes
C_GREEN='\033[1;32m'
C_YELLOW='\033[1;33m'
C_CYAN='\033[1;36m'
C_RED='\033[1;31m'
C_BOLD='\033[1m'
C_OFF='\033[0m'

detect_conflicting_container() {
  local target_name="${1:-optimai-telegram-node}"
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  if ! docker info >/dev/null 2>&1; then
    return 1
  fi

  # Exact match for container name (with or without leading slash)
  local cid
  cid="$(docker ps -a --filter "name=^/${target_name}$" --format "{{.ID}}" 2>/dev/null | head -n1)"
  if [ -z "$cid" ]; then
    cid="$(docker ps -a --filter "name=^${target_name}$" --format "{{.ID}}" 2>/dev/null | head -n1)"
  fi

  if [ -n "$cid" ]; then
    echo "$cid"
    return 0
  fi
  return 1
}

find_any_conflicting_container() {
  for name in "${TARGET_CONTAINER_NAMES[@]}"; do
    local found
    found="$(detect_conflicting_container "$name")"
    if [ -n "$found" ]; then
      echo "$found"
      return 0
    fi
  done
  return 1
}

# Returns:
#   0 -> Clean install selected / container removed / ready for fresh start
#   2 -> Use existing container selected / started / reuse existing
#   1 -> Cancelled or error
resolve_container_conflict() {
  local cid="${1:-}"
  local timeout_sec="${2:-$PROMPT_TIMEOUT}"

  if [ -z "$cid" ]; then
    cid="$(find_any_conflicting_container || true)"
  fi

  if [ -z "$cid" ]; then
    # No conflict found
    return 0
  fi

  # Extract container metadata
  local c_name c_status c_image c_running
  c_name="$(docker inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||' || echo "optimai-telegram-node")"
  c_status="$(docker inspect --format '{{.State.Status}}' "$cid" 2>/dev/null || echo "unknown")"
  c_image="$(docker inspect --format '{{.Config.Image}}' "$cid" 2>/dev/null || echo "optimai-telegram-node")"
  c_running="$(docker inspect --format '{{.State.Running}}' "$cid" 2>/dev/null || echo "false")"

  printf "\n%b======================================================================%b\n" "$C_BOLD" "$C_OFF"
  printf "%b  ⚠️  DOCKER CONTAINER CONFLICT DETECTED%b\n" "$C_YELLOW" "$C_OFF"
  printf "%b======================================================================%b\n" "$C_BOLD" "$C_OFF"
  printf "  A container named %b/%s%b (%s) already exists:\n" "$C_CYAN" "$c_name" "$C_OFF" "${cid:0:12}"
  printf "  • Status:  %b%s%b (Running: %s)\n" "$C_YELLOW" "$c_status" "$C_OFF" "$c_running"
  printf "  • Image:   %s\n\n" "$c_image"
  printf "  What would you like to do?\n\n"
  printf "  %b1) Clean Install (Recommended)%b\n" "$C_BOLD" "$C_OFF"
  printf "     Stop and remove the conflicting container, then build & start fresh.\n"
  printf "     Persistent data (credentials and node identity) in ./data survive.\n\n"
  printf "  %b2) Use Existing Container%b\n" "$C_BOLD" "$C_OFF"
  printf "     Keep and reuse/start the existing container without recreating it.\n\n"
  printf "  Choose an option [1/2] (Default: 1 in %ss, or press Enter): " "$timeout_sec"

  local choice=""
  read -r -t "$timeout_sec" choice || choice=""
  choice="$(echo "$choice" | tr -d '[:space:]')"
  if [ -z "$choice" ]; then
    choice="1"
  fi

  if [ "$choice" = "2" ]; then
    printf "\n%b==>%b Selected: %bUse Existing Container%b\n" "$C_GREEN" "$C_OFF" "$C_BOLD" "$C_OFF"
    if [ "$c_running" != "true" ]; then
      printf "  Starting existing container %s...\n" "$c_name"
      docker start "$cid" >/dev/null 2>&1 || true
    fi
    printf "%b[✓]%b Container %b%s%b (%s) is now running!\n\n" "$C_GREEN" "$C_OFF" "$C_CYAN" "$c_name" "$C_OFF" "${cid:0:12}"
    return 2
  else
    printf "\n%b==>%b Selected: %bClean Install%b\n" "$C_GREEN" "$C_OFF" "$C_BOLD" "$C_OFF"
    printf "  Stopping and removing conflicting container %s (%s)...\n" "$c_name" "${cid:0:12}"
    docker stop -t 5 "$cid" >/dev/null 2>&1 || true
    docker rm -f "$cid" >/dev/null 2>&1 || true
    for extra_name in "${TARGET_CONTAINER_NAMES[@]}"; do
      docker rm -f "$extra_name" >/dev/null 2>&1 || true
    done
    printf "%b[✓]%b Conflicting container removed. Proceeding with clean install!\n\n" "$C_GREEN" "$C_OFF"
    return 0
  fi
}

safe_docker_compose_up() {
  local compose_cmd="${1:-docker compose}"
  local output=""
  local status=0

  output="$($compose_cmd up -d --build 2>&1)" || status=$?
  echo "$output"

  if [ $status -ne 0 ]; then
    if echo "$output" | grep -qiE "Conflict.*The container name.*already in use|is already in use by container"; then
      printf "\n%b[!] Container name conflict encountered during startup.%b\n" "$C_YELLOW" "$C_OFF"
      local conflict_id=""
      conflict_id="$(echo "$output" | grep -oE 'in use by container "[^"]+"' | sed -E 's/in use by container "([^"]+)"/\1/' | head -n1)"
      if [ -n "$conflict_id" ]; then
        printf "    Removing conflicting container ID %s...\n" "$conflict_id"
        docker rm -f "$conflict_id" >/dev/null 2>&1 || true
      fi
      for name in "${TARGET_CONTAINER_NAMES[@]}"; do
        docker rm -f "$name" >/dev/null 2>&1 || true
      done
      printf "%b[✓] Conflicting container purged. Retrying start...%b\n\n" "$C_GREEN" "$C_OFF"
      $compose_cmd up -d --build
      return $?
    fi
    return $status
  fi
  return 0
}

# If script is executed directly (not sourced), run resolution
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  resolve_container_conflict
fi
