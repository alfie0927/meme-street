#!/usr/bin/env bash
# 23:00 UTC: fetch today's Daily Chart and make its recap reel in the house style (the same writer, voice, music and
# renderer as every other reel). Output: out/<UTC date>/reel.mp4 + caption.txt + cover.jpg.
# The film critic (src/critic.py) reviews it and it is rewritten until he approves; post_reel.sh posts only an approved reel.
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"
DATE="${1:-$(date -u +%F)}"
mkdir -p data work out logs queue
exec 8>queue/.auto.lock; flock 8                   # (one reel job at a time, the auto reels included: two at once ran a 4 GB server out of memory)
{
  echo "=== make_reel $DATE  $(date -u '+%F %T UTC')"
  [ -f "data/$DATE.json" ] || python3 src/fetch.py "data/$DATE.json"
  W="work/$DATE"; rm -rf "$W"
  rm -rf "out/$DATE"
  DAILY_DATA="data/$DATE.json" python3 src/make_spec.py "daily-$DATE" "$W" --category "Daily recap"
  python3 src/critic.py loop "$W" "out/$DATE"            # voice, render, review; rewritten until the critic approves
  echo "=== done $(date -u '+%T UTC')"
} 2>&1 | tee -a "logs/$DATE.log"
