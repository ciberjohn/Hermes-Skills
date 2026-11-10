#!/usr/bin/env bash
# PureGym daily advice — prints the quiet-hours brief for today.
# Designed for a scheduled job that delivers its stdout as a message.
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

python3 "$SKILL_DIR/scripts/puregym.py" report --day today 2>&1 \
  || echo "⚠️ PureGym brief failed — sampler log: $DATA_DIR/puregym-sampler.log"

# Optional: link the dashboard, if you run one.
if [ -n "${PUREGYM_DASH_URL:-}" ]; then
  echo
  echo "📊 $PUREGYM_DASH_URL"
fi
