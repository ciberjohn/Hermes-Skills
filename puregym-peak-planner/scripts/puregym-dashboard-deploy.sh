#!/usr/bin/env bash
# Deploy the PureGym dashboard to a remote host and restart it.
#
# The dashboard host needs: python3 (stdlib only), the app in $DASH_REMOTE,
# a data/ subdirectory, and a service manager unit (or equivalent) named
# $DASH_SERVICE. Reach it over a private network (Tailscale, WireGuard, LAN)
# and keep the app bound to loopback on the far side — never exposed publicly.
#
# Required env: DASH_HOST (ssh alias or user@host)
# Optional:     DASH_REMOTE (/opt/puregym-dash), DASH_SERVICE (puregym-dash),
#               DASH_PORT (8099), PUREGYM_DASH_URL (published health check)
set -euo pipefail

SKILL_DIR="${PUREGYM_SKILL_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DATA_DIR="${PUREGYM_DATA_DIR:-$HOME/.local/share/puregym}"
DASH_HOST="${DASH_HOST:?set DASH_HOST to the dashboard host}"
DASH_REMOTE="${DASH_REMOTE:-/opt/puregym-dash}"
DASH_SERVICE="${DASH_SERVICE:-puregym-dash}"
DASH_PORT="${DASH_PORT:-8099}"

# Everything below is embedded in remote shell commands, so validate hard.
for pair in "DASH_HOST=$DASH_HOST" "DASH_REMOTE=$DASH_REMOTE" "DASH_SERVICE=$DASH_SERVICE"; do
  name="${pair%%=*}"; value="${pair#*=}"
  if [[ ! "$value" =~ ^[A-Za-z0-9._@:/-]+$ ]]; then
    echo "refusing: $name contains characters that are unsafe in a shell: $value" >&2
    exit 2
  fi
done
if [[ ! "$DASH_PORT" =~ ^[0-9]{2,5}$ ]]; then
  echo "refusing: DASH_PORT is not a port number" >&2
  exit 2
fi

remote_new="$DASH_REMOTE/data/.puregym.sqlite.new"

echo "→ copying app.py"
scp -q "$SKILL_DIR/dashboard/app.py" "$DASH_HOST:$DASH_REMOTE/app.py"
echo "→ creating data dir"
ssh -o BatchMode=yes "$DASH_HOST" "mkdir -p -- '$DASH_REMOTE/data'"
echo "→ pushing current database"
scp -q -p "$DATA_DIR/puregym.sqlite" "$DASH_HOST:$remote_new"
ssh -o BatchMode=yes "$DASH_HOST" \
  "chmod 600 -- '$remote_new' && mv -f -- '$remote_new' '$DASH_REMOTE/data/puregym.sqlite'"
echo "→ restarting service"
ssh -o BatchMode=yes "$DASH_HOST" "sudo systemctl restart '$DASH_SERVICE'"
sleep 1
echo "→ health (loopback)"
ssh -o BatchMode=yes "$DASH_HOST" "curl -s -m5 'http://127.0.0.1:$DASH_PORT/healthz'" && echo
if [ -n "${PUREGYM_DASH_URL:-}" ]; then
  echo "→ health (published URL)"
  curl -s -m8 -o /dev/null -w "%{http_code} $PUREGYM_DASH_URL/healthz\n" \
    "${PUREGYM_DASH_URL%/}/healthz"
fi
