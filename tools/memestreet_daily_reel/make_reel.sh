#!/usr/bin/env bash
# 23:30 UTC: fetch today's Daily Chart, analyse it, narrate, render. Output: out/<UTC date>/reel.mp4 + caption.txt
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
DATE="${1:-$(date -u +%F)}"
mkdir -p data work out logs
{
  echo "=== make_reel $DATE  $(date -u '+%F %T UTC')"
  [ -f "data/$DATE.json" ] || python3 src/fetch.py "data/$DATE.json"
  python3 src/analyze.py "data/$DATE.json" "work/$DATE"
  python3 src/voice.py "work/$DATE"
  python3 src/render.py "work/$DATE" "out/$DATE"
  echo "=== done $(date -u '+%T UTC')"
} 2>&1 | tee -a "logs/$DATE.log"
