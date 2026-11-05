#!/usr/bin/env bash
# 23:00 UTC: fetch today's Daily Chart and make its recap reel in the house style (the same writer, voice, music and
# renderer as every other reel). Output: out/<UTC date>/reel.mp4 + caption.txt + cover.jpg.
# If the house-style path fails, the older recap (analyze.py + voice.py + recap.html) is made instead, so no night is missed.
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"
DATE="${1:-$(date -u +%F)}"
mkdir -p data work out logs
{
  echo "=== make_reel $DATE  $(date -u '+%F %T UTC')"
  [ -f "data/$DATE.json" ] || python3 src/fetch.py "data/$DATE.json"
  W="work/$DATE"; rm -rf "$W"
  if DAILY_DATA="data/$DATE.json" python3 src/make_spec.py "daily-$DATE" "$W" --category "Daily recap" \
     && python3 src/narrate.py "$W" && PAGE=reel.html FPS=${AUTO_FPS:-60} python3 src/render.py "$W" "out/$DATE"; then
    echo "house style"
  else
    echo "house style failed: the older recap is made instead"; rm -rf "$W"
    python3 src/analyze.py "data/$DATE.json" "$W"
    python3 src/voice.py "$W"
    python3 src/render.py "$W" "out/$DATE"
  fi
  echo "=== done $(date -u '+%T UTC')"
} 2>&1 | tee -a "logs/$DATE.log"
