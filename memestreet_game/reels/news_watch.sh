#!/usr/bin/env bash
# Every 20 minutes (memestreet-reel-news.timer): look for a REALLY big real headline and, when there is one, make its reel
# and post it at once (src/news_reel.py; the owner, 2026-11-12). Reading the feeds is free; Claude is asked only when one
# story is in several outlets. On top of the five reels a day and the Daily; one news reel a day at most.
#   ./news_watch.sh                      one pass
#   touch state/news_off                 stops it (rm state/news_off starts it again)
#   python3 src/news_reel.py feeds       what it sees right now (free)
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"                 # (Claude Code, on the plan)
mkdir -p logs queue state
exec 7>queue/.news.lock; flock -n 7 || exit 0        # (the last pass is still making its reel)
python3 src/news_reel.py watch >> logs/news.log 2>&1
