#!/usr/bin/env bash
# PureGym attendance sampler — silent on success, rate-limited alerts on trouble.
#
# Designed for a Hermes cron job (or any scheduler) that relays stdout to you.
# Exit code is always 0: a scheduler should not page you because a gym's door
# counter blipped. Output only appears when something needs a human.
set -uo pipefail

SKILL_DIR="${PUREGYM_SKILL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# Read the same KEY=VALUE config the Python code uses, without executing it.
load_config() {
  local file="$1" line key val
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    case "$line" in *=*) ;; *) continue ;; esac
    key="${line%%=*}"
    val="${line#*=}"
    key="${key//[[:space:]]/}"
    val="${val%\"}"; val="${val#\"}"; val="${val%\'}"; val="${val#\'}"
    case "$key" in
      PUREGYM_*|SECRET_BACKEND|INFISICAL_*) [ -z "${!key:-}" ] && export "$key=$val" ;;
    esac
  done < "$file"
}

if [ -z "${PUREGYM_CONFIG:-}" ]; then
  for candidate in \
    "${XDG_CONFIG_HOME:-$HOME/.config}/puregym/config.env" \
    "$HOME/.config/puregym/config.env" \
    "$SKILL_DIR/config.env"; do
    if [ -f "$candidate" ]; then PUREGYM_CONFIG="$candidate"; break; fi
  done
fi
[ -n "${PUREGYM_CONFIG:-}" ] && load_config "$PUREGYM_CONFIG"

DATA_DIR="${PUREGYM_DATA_DIR:-$HOME/.local/share/puregym}"
LOG="$DATA_DIR/puregym-sampler.log"
ALERT_STATE="$DATA_DIR/.sampler-alert-ts"
mkdir -p "$DATA_DIR" && chmod 700 "$DATA_DIR" 2>/dev/null

out=$(python3 "$SKILL_DIR/scripts/puregym.py" sample 2>&1)
rc=$?
printf '%s | rc=%s | %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$rc" "$out" >> "$LOG"

# Optional: push a snapshot to a read-only dashboard host.
# Set PUREGYM_DASH_HOST (an ssh alias or user@host) to enable it, and
# PUREGYM_DASH_DIR if the app does not live in /opt/puregym-dash.
if [ "$rc" -eq 0 ] && [ -n "${PUREGYM_DASH_HOST:-}" ]; then
  dash_dir="${PUREGYM_DASH_DIR:-/opt/puregym-dash}"
  if [[ ! "$dash_dir" =~ ^/[A-Za-z0-9._/-]+$ ]]; then
    printf '%s | dashboard sync: unsafe PUREGYM_DASH_DIR, skipped\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
  else
    remote_new="$dash_dir/data/.puregym.sqlite.new"
    # land the copy inside the destination directory, owner-only, then rename
    if rsync -a --chmod=F600 --timeout=20 "$DATA_DIR/puregym.sqlite" \
         "$PUREGYM_DASH_HOST:$remote_new" >>"$LOG" 2>&1; then
      ssh -o BatchMode=yes -o ConnectTimeout=10 "$PUREGYM_DASH_HOST" \
        "mv -f -- '$remote_new' '$dash_dir/data/puregym.sqlite'" >>"$LOG" 2>&1 \
        || printf '%s | dashboard sync: move failed\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
    else
      printf '%s | dashboard sync: rsync failed\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
    fi
  fi
fi

# keep the log bounded and private
tail -n 2000 "$LOG" > "$LOG.tmp" && chmod 600 "$LOG.tmp" && mv "$LOG.tmp" "$LOG"

# ---- alerting: hard failure, or a stale-data WARN from the sampler ----------
msg=""
if [ "$rc" -ne 0 ]; then
  detail=$(printf '%s\n' "$out" | grep -v '^[[:space:]]*$' | tail -1 | cut -c1-200)
  msg="⚠️ PureGym sampler failed (rc=$rc): ${detail:-unknown error}"
elif printf '%s' "$out" | grep -q '^WARN'; then
  msg=$(printf '%s' "$out" | grep '^WARN' | head -1)
fi

if [ -n "$msg" ]; then
  # defence in depth: never relay anything shaped like a token
  msg=$(printf '%s' "$msg" | sed -E 's/[A-Za-z0-9_-]{40,}/[redacted]/g')
  now_epoch=$(date +%s)
  last_epoch=$(cat "$ALERT_STATE" 2>/dev/null || echo 0)
  case "$last_epoch" in ''|*[!0-9]*) last_epoch=0 ;; esac
  # at most one alert per hour, so a flapping counter does not spam you
  if [ $((now_epoch - last_epoch)) -ge 3600 ]; then
    echo "$msg"
    echo "$now_epoch" > "$ALERT_STATE"
  fi
fi
exit 0
