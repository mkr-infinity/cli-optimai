#!/usr/bin/env bash
# ============================================================
# scripts/sync-credentials.sh — Bi-directional Credential Synchronizer
# OptimAI Telegram Node (v1.3.0)
#
# Synchronizes official OptimAI CLI authentication credentials and
# identity between host user home ($HOME/.config/optimai-cli),
# container/workspace storage (./data/home/.config/optimai-cli), and
# persistent database files (credentials.json).
# ============================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

sync_credentials() {
  if ! command -v python3 >/dev/null 2>&1; then
    return 0
  fi

  python3 - <<'EOF'
import os
import json
import shutil
import time

cwd = os.getcwd()
root = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else cwd

candidate_data_dirs = [
    os.path.join(cwd, "data"),
    os.path.join(cwd, "..", "data"),
    os.path.join(root, "data"),
    os.path.expanduser("~/optimai-cli/data"),
    "/workspaces/optimai-cli/data",
    "/data",
]

# Find valid data directory
data_dir = None
for d in candidate_data_dirs:
    if os.path.isdir(d):
        data_dir = os.path.abspath(d)
        break

user_home = os.path.expanduser("~")
user_cfg = os.path.join(user_home, ".config", "optimai-cli")
user_auth = os.path.join(user_cfg, "auth.json")

data_home_cfg = os.path.join(data_dir, "home", ".config", "optimai-cli") if data_dir else None
data_auth = os.path.join(data_home_cfg, "auth.json") if data_home_cfg else None

db_files = []
if data_dir:
    db_files.extend([
        os.path.join(data_dir, "credentials.json"),
        os.path.join(data_dir, "data", "credentials.json"),
    ])
db_files.append(os.path.join(user_cfg, "credentials.json"))

# 1. Determine which auth source is newest and valid
has_user_auth = os.path.isfile(user_auth) and os.path.getsize(user_auth) > 0
has_data_auth = bool(data_auth and os.path.isfile(data_auth) and os.path.getsize(data_auth) > 0)

# Check database snapshots
db_data = None
db_mtime = 0
for db_f in db_files:
    if os.path.isfile(db_f) and os.path.getsize(db_f) > 0:
        try:
            with open(db_f, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
                if loaded.get("auth_snapshot"):
                    mtime = os.path.getmtime(db_f)
                    if mtime > db_mtime:
                        db_mtime = mtime
                        db_data = loaded
        except Exception:
            pass

user_mtime = os.path.getmtime(user_auth) if has_user_auth else 0
data_mtime = os.path.getmtime(data_auth) if has_data_auth else 0

active_source = None
if has_user_auth and has_data_auth:
    active_source = user_cfg if user_mtime >= data_mtime else data_home_cfg
elif has_user_auth:
    active_source = user_cfg
elif has_data_auth:
    active_source = data_home_cfg

# If neither directory has auth, but database has snapshot: restore to both
if not active_source and db_data and db_data.get("auth_snapshot"):
    for target in (user_cfg, data_home_cfg):
        if not target:
            continue
        try:
            os.makedirs(target, exist_ok=True)
            with open(os.path.join(target, "auth.json"), "w", encoding="utf-8") as fh:
                json.dump(db_data["auth_snapshot"], fh, indent=2)
            if db_data.get("user_snapshot"):
                with open(os.path.join(target, "user.json"), "w", encoding="utf-8") as fh:
                    json.dump(db_data["user_snapshot"], fh, indent=2)
        except Exception:
            pass
    active_source = user_cfg

# If we have an active source, synchronize all configuration files to the other target
if active_source:
    target_cfg = data_home_cfg if active_source == user_cfg else user_cfg
    if target_cfg and target_cfg != active_source:
        try:
            os.makedirs(target_cfg, exist_ok=True)
            for fname in ("auth.json", "user.json", "device.json", "node_identity.json", "uptime.json"):
                sfile = os.path.join(active_source, fname)
                dfile = os.path.join(target_cfg, fname)
                if os.path.isfile(sfile) and os.path.getsize(sfile) > 0:
                    shutil.copy2(sfile, dfile)
        except Exception:
            pass

    # Ensure credentials.json database is always updated with the latest snapshot
    try:
        active_auth_file = os.path.join(active_source, "auth.json")
        if os.path.isfile(active_auth_file) and os.path.getsize(active_auth_file) > 0:
            auth_snap = json.load(open(active_auth_file, "r", encoding="utf-8"))
            user_f = os.path.join(active_source, "user.json")
            u_snap = json.load(open(user_f, "r", encoding="utf-8")) if os.path.isfile(user_f) else {}
            db_payload = {
                "auth_type": "synced",
                "auth_snapshot": auth_snap,
                "user_snapshot": u_snap,
                "updated_at": time.time(),
            }
            if u_snap.get("email"):
                db_payload["email"] = u_snap["email"]
            for db_p in db_files:
                try:
                    os.makedirs(os.path.dirname(db_p), exist_ok=True)
                    tmp_p = db_p + ".tmp"
                    with open(tmp_p, "w", encoding="utf-8") as fh:
                        json.dump(db_payload, fh, indent=2)
                    os.replace(tmp_p, db_p)
                except Exception:
                    pass
    except Exception:
        pass

EOF
}

sync_credentials
