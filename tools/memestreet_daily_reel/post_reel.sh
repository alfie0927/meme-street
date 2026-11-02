#!/usr/bin/env bash
# 23:30 UTC: publish today's reel (made from 23:00); if it is still being made, wait for it (up to an hour).
#   ./post_reel.sh --check     test the Instagram connection (posts nothing)
#   ./post_reel.sh --dry-run   show what would be posted
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
mkdir -p logs
if [ "${1:-}" = "--check" ]; then python3 src/post_instagram.py --check; exit; fi
DATE="${DATE:-$(date -u +%F)}"
for _ in $(seq 120); do
  state=$(systemctl show -p ActiveState --value memestreet-reel-make)   # (a running oneshot is "activating", not "active")
  [ -f "out/$DATE/reel.mp4" ] && [ "$state" != activating ] && [ "$state" != active ] && break
  sleep 30
done
python3 src/post_instagram.py "out/$DATE" "$@" 2>&1 | tee -a "logs/$DATE.log"
