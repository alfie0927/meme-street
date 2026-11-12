#!/usr/bin/env bash
# The Daily Chart reel, a director reel like every other (the owner, 2026-11-10): today's chart and its analysis (fetch.py,
# analyze.py) go to the writer as facts (make_spec.py --category "Daily recap"), the film critic reviews it, then it posts.
# Safe to run again: the timer runs it at 23:00 and retries through the night (23:40, 01:00, 03:00, 05:00, 08:00 UTC);
# each run carries on from where the last stopped (data fetched -> reel approved -> posted) and does nothing once posted.
#   ./make_reel.sh [YYYY-MM-DD]     (default: today from 22:00 UTC, else yesterday)
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"
H=$(date -u +%-H); DATE="${1:-$( [ "$H" -ge 22 ] && date -u +%F || date -u -d yesterday +%F )}"
W="work/$DATE"; O="out/$DATE"; mkdir -p data work out logs queue
[ -f "$O/posted.json" ] && { echo "Daily $DATE already posted"; exit 0; }
[ -f "data/$DATE.json" ] || [ "$DATE" = "$(date -u +%F)" ] || { echo "no data for $DATE and its chart is gone (the site serves only today's): skipped"; exit 0; }
touch queue/.daily-pending; trap 'rm -f queue/.daily-pending' EXIT   # (auto_reel.sh waits while the Daily is due)
exec 8>queue/.auto.lock; flock -w 5400 8 || { echo "Daily $DATE: the reel lock stayed busy 90 min; the next timer run retries" | tee -a "logs/$DATE.log"; exit 1; }
{
  echo "=== daily $DATE  $(date -u '+%F %T UTC')"
  [ -f "data/$DATE.json" ] || python3 src/fetch.py "data/$DATE.json"
  if [ ! -f "$O/approved.json" ]; then
    n=$(( $(cat "out/.tries-$DATE" 2>/dev/null || echo 0) + 1 )); echo $n > "out/.tries-$DATE"
    [ "$n" -le 3 ] || { echo "Daily $DATE held three times: not posted"; exit 0; }   # (each try is a new script on the plan)
    export DAILY_DATA="data/$DATE.json"
    if [ ! -f "$W/spec.json" ]; then
      rm -rf "$W" "$O"; ok=; for t in 1 2 3; do python3 src/make_spec.py "${DATE}T2300" "$W" --category "Daily recap" && { ok=1; break; }; done; [ -n "$ok" ]
    fi
    python3 src/critic.py loop "$W" "$O" || { rm -rf "$W"; exit 1; }   # (held: the next run writes a fresh script)
  fi
  python3 src/post_instagram.py "$O"                   # (an Instagram error fails the run; the next timer run posts it)
  python3 src/post_elsewhere.py "$O" >> logs/elsewhere.log 2>&1 || true   # (the Daily on the other platforms that have keys: docs/ROADMAP.md A11)
  echo "=== daily done $(date -u '+%T UTC')"
} 2>&1 | tee -a "logs/$DATE.log"
exit "${PIPESTATUS[0]}"
