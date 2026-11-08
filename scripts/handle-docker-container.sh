#!/usr/bin/env bash
# ============================================================
# scripts/handle-docker-container.sh — Docker Container Lifecycle & Conflict Resolver
# OptimAI Telegram Node (v1.9.0)
#
# Robustly handles all Docker conflict states:
#   - Container running vs stopped vs paused vs dead vs restarting
#   - Container name collisions across project renames (optimai-cli vs cli-optimai)
#   - Stale network endpoints, port collisions, and orphaned worker containers
#
# Interactive prompt with auto-timeout (default 60s):
#   1) Clean Install (Recommended) — stop (with kill fallback) & purge container, start fresh
#   2) Use Existing Container — resume, unpause, or attach; auto-fallbacks to Clean Install if broken
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

get_docker_bin() {
  if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
      echo "docker"
      return 0
    elif command -v sudo >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
      echo "sudo docker"
      return 0
    fi
    echo "docker"
    return 0
  fi
  return 1
}

detect_conflicting_container() {
  local target_name="${1:-optimai-telegram-node}"
  local d_bin
  d_bin="$(get_docker_bin)" || return 1

  if ! $d_bin info >/dev/null 2>&1; then
    return 1
  fi

  # Exact match for container name (with or without leading slash)
  local cid
  cid="$($d_bin ps -a --filter "name=^/${target_name}$" --format "{{.ID}}" 2>/dev/null | head -n1)"
  if [ -z "$cid" ]; then
    cid="$($d_bin ps -a --filter "name=^${target_name}$" --format "{{.ID}}" 2>/dev/null | head -n1)"
  fi

  if [ -n "$cid" ]; then
    echo "$cid"
    return 0
  fi
  return 1
}

find_any_conflicting_container() {
  local d_bin
  d_bin="$(get_docker_bin)" || return 1

  for name in "${TARGET_CONTAINER_NAMES[@]}"; do
    local found
    found="$(detect_conflicting_container "$name")"
    if [ -n "$found" ]; then
      echo "$found"
      return 0
    fi
  done

  # Also search for any container with optimai-telegram in its name
  local fuzzy_cid
  fuzzy_cid="$($d_bin ps -a --filter "name=optimai-telegram" --format "{{.ID}}" 2>/dev/null | head -n1)"
  if [ -n "$fuzzy_cid" ]; then
    echo "$fuzzy_cid"
    return 0
  fi

  return 1
}

# Safely purge a container regardless of state (running, paused, dead, restarting)
purge_container() {
  local cid="${1:-}"
  local d_bin
  d_bin="$(get_docker_bin)" || return 1

  if [ -n "$cid" ]; then
    # Unpause if paused so docker can stop/kill it cleanly
    $d_bin unpause "$cid" >/dev/null 2>&1 || true
    # Attempt graceful stop, fallback to kill
    $d_bin stop -t 3 "$cid" >/dev/null 2>&1 || $d_bin kill "$cid" >/dev/null 2>&1 || true
    # Force remove container
    $d_bin rm -f "$cid" >/dev/null 2>&1 || true
  fi

  # Also ensure target names are fully free
  for name in "${TARGET_CONTAINER_NAMES[@]}"; do
    $d_bin unpause "$name" >/dev/null 2>&1 || true
    $d_bin stop -t 3 "$name" >/dev/null 2>&1 || $d_bin kill "$name" >/dev/null 2>&1 || true
    $d_bin rm -f "$name" >/dev/null 2>&1 || true
  done

  # Clean stale network endpoints
  $d_bin network disconnect -f cli-optimai_default "$cid" >/dev/null 2>&1 || true
  $d_bin network disconnect -f optimai-cli_default "$cid" >/dev/null 2>&1 || true
}

# Returns:
#   0 -> Clean install selected / container removed / ready for fresh start
#   2 -> Use existing container selected / successfully started or running / reuse existing
#   1 -> Cancelled or unrecoverable error
resolve_container_conflict() {
  local cid="${1:-}"
  local timeout_sec="${2:-$PROMPT_TIMEOUT}"
  local d_bin
  d_bin="$(get_docker_bin)" || return 0

  if [ -z "$cid" ]; then
    cid="$(find_any_conflicting_container || true)"
  fi

  if [ -z "$cid" ]; then
    # No conflict found
    return 0
  fi

  # Extract container metadata
  local c_name c_status c_image c_running c_exit c_uptime
  c_name="$($d_bin inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's|^/||' || echo "optimai-telegram-node")"
  c_status="$($d_bin inspect --format '{{.State.Status}}' "$cid" 2>/dev/null || echo "unknown")"
  c_image="$($d_bin inspect --format '{{.Config.Image}}' "$cid" 2>/dev/null || echo "optimai-telegram-node")"
  c_running="$($d_bin inspect --format '{{.State.Running}}' "$cid" 2>/dev/null || echo "false")"
  c_exit="$($d_bin inspect --format '{{.State.ExitCode}}' "$cid" 2>/dev/null || echo "0")"

  local status_desc="$c_status"
  if [ "$c_running" = "true" ]; then
    status_desc="${c_status} (active)"
  elif [ "$c_status" = "exited" ]; then
    status_desc="exited (code ${c_exit})"
  fi

  printf "\n%b======================================================================%b\n" "$C_BOLD" "$C_OFF"
  printf "%b  ⚠️  DOCKER CONTAINER CONFLICT DETECTED%b\n" "$C_YELLOW" "$C_OFF"
  printf "%b======================================================================%b\n" "$C_BOLD" "$C_OFF"
  printf "  A container named %b/%s%b (%s) already exists:\n" "$C_CYAN" "$c_name" "$C_OFF" "${cid:0:12}"
  printf "  • Current State: %b%s%b\n" "$C_YELLOW" "$status_desc" "$C_OFF"
  printf "  • Image Tag:     %s\n\n" "$c_image"
  printf "  What would you like to do?\n\n"
  printf "  %b1) Clean Install (Recommended)%b\n" "$C_BOLD" "$C_OFF"
  printf "     Stop (if running) and remove the conflicting container, then build & start fresh.\n"
  printf "     Persistent credentials and data in ./data remain fully preserved.\n\n"
  printf "  %b2) Use Existing Container%b\n" "$C_BOLD" "$C_OFF"
  if [ "$c_running" = "true" ]; then
    printf "     Keep the container currently running without stopping or recreating it.\n\n"
  elif [ "$c_status" = "paused" ]; then
    printf "     Unpause and resume the existing container.\n\n"
  else
    printf "     Start and resume the existing stopped container.\n\n"
  fi
  printf "  Choose an option [1/2] (Default: 1 in %ss, or press Enter): " "$timeout_sec"

  local choice=""
  read -r -t "$timeout_sec" choice || choice=""
  choice="$(echo "$choice" | tr -d '[:space:]')"
  if [ -z "$choice" ]; then
    choice="1"
  fi

  if [ "$choice" = "2" ]; then
    printf "\n%b==>%b Selected: %bUse Existing Container%b\n" "$C_GREEN" "$C_OFF" "$C_BOLD" "$C_OFF"

    # Handle running state
    if [ "$c_running" = "true" ]; then
      printf "%b[✓]%b Container %b%s%b (%s) is already running and active!\n\n" "$C_GREEN" "$C_OFF" "$C_CYAN" "$c_name" "$C_OFF" "${cid:0:12}"
      return 2
    fi

    # Handle paused state
    if [ "$c_status" = "paused" ]; then
      printf "  Unpausing container %s...\n" "$c_name"
      if $d_bin unpause "$cid" >/dev/null 2>&1; then
        printf "%b[✓]%b Container %b%s%b (%s) unpaused and resumed!\n\n" "$C_GREEN" "$C_OFF" "$C_CYAN" "$c_name" "$C_OFF" "${cid:0:12}"
        return 2
      else
        printf "%b[!] Unpause failed. Falling back to Clean Install...%b\n" "$C_YELLOW" "$C_OFF"
        purge_container "$cid"
        return 0
      fi
    fi

    # Handle stopped / exited / created state
    printf "  Starting existing container %s (%s)...\n" "$c_name" "${cid:0:12}"
    local start_err=""
    if start_err="$($d_bin start "$cid" 2>&1)"; then
      # Verify it stayed running (didn't crash immediately)
      sleep 1
      local now_running
      now_running="$($d_bin inspect --format '{{.State.Running}}' "$cid" 2>/dev/null || echo "false")"
      if [ "$now_running" = "true" ]; then
        printf "%b[✓]%b Container %b%s%b (%s) started successfully!\n\n" "$C_GREEN" "$C_OFF" "$C_CYAN" "$c_name" "$C_OFF" "${cid:0:12}"
        return 2
      else
        local exit_code
        exit_code="$($d_bin inspect --format '{{.State.ExitCode}}' "$cid" 2>/dev/null || echo "unknown")"
        printf "%b[!] Existing container exited immediately after start (Exit code: %s).%b\n" "$C_YELLOW" "$exit_code" "$C_OFF"
        printf "    The previous container is broken or outdated.\n"
        printf "    Falling back to %bClean Install%b to rebuild fresh...\n\n" "$C_BOLD" "$C_OFF"
        purge_container "$cid"
        return 0
      fi
    else
      printf "%b[!] Could not start existing container:%b %s\n" "$C_YELLOW" "$C_OFF" "$start_err"
      printf "    Falling back to %bClean Install%b to rebuild fresh...\n\n" "$C_BOLD" "$C_OFF"
      purge_container "$cid"
      return 0
    fi

  else
    printf "\n%b==>%b Selected: %bClean Install%b\n" "$C_GREEN" "$C_OFF" "$C_BOLD" "$C_OFF"
    printf "  Purging conflicting container %s (%s)...\n" "$c_name" "${cid:0:12}"
    purge_container "$cid"
    printf "%b[✓]%b Conflicting container removed cleanly. Proceeding with fresh start!\n\n" "$C_GREEN" "$C_OFF"
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
    # Check for container name, endpoint, network, or removal conflicts
    if echo "$output" | grep -qiE "Conflict.*The container name.*already in use|is already in use by container|endpoint with name.*already exists in network|network.*already exists|is marked for removal"; then
      printf "\n%b[!] Docker conflict encountered during startup:%b\n" "$C_YELLOW" "$C_OFF"

      local conflict_id=""
      conflict_id="$(echo "$output" | grep -oE 'in use by container "[^"]+"' | sed -E 's/in use by container "([^"]+)"/\1/' | head -n1)"
      if [ -n "$conflict_id" ]; then
        printf "    Purging conflicting container ID %s...\n" "$conflict_id"
        purge_container "$conflict_id"
      else
        printf "    Purging all conflicting optimai container instances...\n"
        purge_container ""
      fi

      # Prune conflicting networks
      docker network prune -f >/dev/null 2>&1 || true

      printf "%b[✓] Conflicting resources purged. Retrying start...%b\n\n" "$C_GREEN" "$C_OFF"
      $compose_cmd up -d --build
      return $?

    elif echo "$output" | grep -qiE "port is already allocated|address already in use"; then
      printf "\n%b[!] Port conflict encountered on host.%b\n" "$C_RED" "$C_OFF"
      printf "    A service is already listening on the configured health port.\n"
      printf "    Retrying with health port disabled...\n"
      ENABLE_HEALTH_PORT="" $compose_cmd up -d --build
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
