#!/usr/bin/env bash
# 00:00 UTC: publish the reel made at 23:30 the previous (UTC) day.
#   ./post_reel.sh --check     test the Instagram connection (posts nothing)
#   ./post_reel.sh --dry-run   show what would be posted
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
mkdir -p logs
if [ "${1:-}" = "--check" ]; then python3 src/post_instagram.py --check; exit; fi
DATE="${DATE:-$(date -u -d 'yesterday' +%F)}"
python3 src/post_instagram.py "out/$DATE" "$@" 2>&1 | tee -a "logs/$DATE.log"
