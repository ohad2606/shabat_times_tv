#!/usr/bin/env bash
# Deploy a design to the TV display.
#
#   ./tv-deploy.sh page.html              -> becomes /tv/
#   ./tv-deploy.sh page.html logo.png ... -> extra files land in /tv/ alongside it
#   ./tv-deploy.sh --dir ./build          -> publishes a whole folder (needs index.html)
#
# Every deploy bumps the version marker, so any TV already on the page
# refreshes itself within ~10 seconds. No remote needed.

set -euo pipefail
ROOT=/var/www/tv

usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
[ $# -ge 1 ] || usage

if [ "${1:-}" = "--dir" ]; then
  SRC="${2:?--dir needs a folder}"
  [ -f "$SRC/index.html" ] || { echo "error: $SRC/index.html not found" >&2; exit 1; }
  # Keep the infrastructure files, replace everything else.
  find "$ROOT" -mindepth 1 -maxdepth 1 ! -name '_reload.js' ! -name '_version.txt' -exec rm -rf {} +
  cp -r "$SRC"/. "$ROOT"/
else
  MAIN="$1"; shift
  [ -f "$MAIN" ] || { echo "error: $MAIN not found" >&2; exit 1; }
  cp "$MAIN" "$ROOT/index.html"
  for f in "$@"; do cp -r "$f" "$ROOT"/; done
fi

date +%s > "$ROOT/_version.txt"
chmod -R a+rX "$ROOT"

IP=$(curl -s --max-time 5 https://api.ipify.org || echo "<server-ip>")
echo "deployed -> http://$IP/tv/"
echo "connected TVs will refresh within ~10s"
