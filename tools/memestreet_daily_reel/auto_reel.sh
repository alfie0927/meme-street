#!/usr/bin/env bash
# Make the auto reel for the next posting slot and put it in the queue (queue_post.sh posts it on time).
#   ./auto_reel.sh                    the next slot (03:00, 06:00, 09:00, 12:00, 13:00, 18:00, 21:00 UTC) starting within 3 hours
#   ./auto_reel.sh 2026-11-05T1200    that slot
# (03:00, 09:00, 13:00 and 21:00 are the viral slots.)
# A slot that already holds a November reel gets a remake of it (queue/<slot>/remake.json); the original is kept in
# queue-originals/. Every reel goes to the film critic (src/critic.py) and is rewritten until he approves it; only an
# approved reel is queued, and the queue posts only approved reels. Late? It posts as soon as it is approved.
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"                 # (Claude Code, the script writer on the plan)
mkdir -p logs queue queue-originals
exec 8>queue/.auto.lock; flock 8                   # (one reel at a time: the critic has no round limit, so the next run waits)
SLOT="${1:-}"
if [ -z "$SLOT" ]; then
  for h in 0300 0600 0900 1200 1300 1800 2100; do
    for d in "$(date -u +%F)" "$(date -u -d tomorrow +%F)"; do
      s="${d}T$h"; ds=$(( $(date -u -d "${d} ${h:0:2}:${h:2:2}" +%s) - $(date -u +%s) ))
      if [ "$ds" -gt 0 ] && [ "$ds" -le 10800 ]; then SLOT=$s; break 2; fi
    done
  done
fi
[ -n "$SLOT" ] || { echo "no slot in the next 3 hours"; exit 0; }
[ -f "queue/$SLOT/posted.json" ] && { echo "$SLOT is already posted"; exit 0; }
[ -f "queue/$SLOT/.auto" ] && { echo "$SLOT already has its auto reel"; exit 0; }
W="work/auto-$SLOT"; O="out/auto-$SLOT"
[ -n "${RESUME:-}" ] && [ -f "$W/spec.json" ] || { RESUME=; rm -rf "$W" "$O"; }   # (RESUME=1: carry on with the script already written)
args=(); [ -f "queue/$SLOT/remake.json" ] && args=(--remake "queue/$SLOT/remake.json")
[ -n "${REEL_CATEGORY:-}" ] && args+=(--category "$REEL_CATEGORY")      # (a chosen format, e.g. for a test reel)
{
  echo "=== auto reel $SLOT  $(date -u '+%F %T UTC')"
  if [ -z "${RESUME:-}" ]; then                         # (a first draft that fails its checks five times gets two more goes)
    ok=; for try in 1 2 3; do python3 src/make_spec.py "$SLOT" "$W" "${args[@]}" && { ok=1; break; }; done; [ -n "$ok" ]
  fi
  python3 src/critic.py loop "$W" "$O"                   # voice, render, review; rewritten until the critic approves
  mkdir -p "queue/.staging/$SLOT" && cp "$O/reel.mp4" "$O/caption.txt" "$O/cover.jpg" "$O/approved.json" "queue/.staging/$SLOT/"
  [ -d "queue/$SLOT" ] && { rm -rf "queue-originals/$SLOT"; mv "queue/$SLOT" "queue-originals/$SLOT"; }
  touch "queue/.staging/$SLOT/.auto"
  mv "queue/.staging/$SLOT" "queue/$SLOT"
  echo "=== queued $SLOT $(date -u '+%T UTC')"
} 2>&1 | tee -a "logs/auto.log"
