#!/usr/bin/env bash
# Every 5 minutes: post the scheduled reels that are due.
#   queue/<YYYY-MM-DDTHHMM, UTC>/reel.mp4 + caption.txt (+ cover.jpg)   e.g. queue/2026-11-05T1800/
# A posted one gets posted.json; one that fails gets failed.txt and is not tried again (delete it to retry).
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
mkdir -p logs queue
exec 9>queue/.lock; flock -n 9 || exit 0             # (the last run is still posting)
now=$(date -u +%Y-%m-%dT%H%M); shopt -s nullglob
for d in queue/*/; do
  d=${d%/}; t=$(basename "$d")
  [[ "$t" > "$now" || -f "$d/posted.json" || -f "$d/failed.txt" ]] && continue
  echo "=== queue $t  $(date -u '+%F %T UTC')" >> logs/queue.log
  python3 src/post_instagram.py "$d" >> logs/queue.log 2>&1 || { date -u > "$d/failed.txt"; echo "FAILED $t" >> logs/queue.log; }
done
