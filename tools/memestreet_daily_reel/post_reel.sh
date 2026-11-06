#!/usr/bin/env bash
# 23:30 UTC: publish today's reel (made from 23:00) once the film critic has approved it; if it is still being made or
# reviewed, wait for it (up to two hours). An unapproved reel is never posted.
#   ./post_reel.sh --check     test the Instagram connection (posts nothing)
#   ./post_reel.sh --dry-run   show what would be posted
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
mkdir -p logs
if [ "${1:-}" = "--check" ]; then python3 src/post_instagram.py --check; exit; fi
DATE="${DATE:-$(date -u +%F)}"
for _ in $(seq 240); do
  state=$(systemctl show -p ActiveState --value memestreet-reel-make)   # (a running oneshot is "activating", not "active")
  [ -f "out/$DATE/reel.mp4" ] && [ "$state" != activating ] && [ "$state" != active ] && break
  sleep 30
done
[ -f "out/$DATE/approved.json" ] || { echo "out/$DATE was not approved by the critic: not posted" | tee -a "logs/$DATE.log"; exit 1; }
python3 src/post_instagram.py "out/$DATE" "$@" 2>&1 | tee -a "logs/$DATE.log"
