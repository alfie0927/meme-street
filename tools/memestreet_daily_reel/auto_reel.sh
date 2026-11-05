#!/usr/bin/env bash
# Make the auto reel for the next posting slot and put it in the queue (queue_post.sh posts it on time).
#   ./auto_reel.sh                    the next slot (03:00, 06:00, 09:00, 12:00, 13:00, 18:00, 21:00 UTC) starting within 3 hours
#   ./auto_reel.sh 2026-11-05T1200    that slot
# (03:00, 09:00, 13:00 and 21:00 are the viral slots.)
# A slot that already holds a November reel gets a remake of it (queue/<slot>/remake.json); if anything fails, the
# reel already there is posted as it is. A remade slot's original is kept in queue-originals/.
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"                 # (Claude Code, the script writer on the plan)
mkdir -p logs queue queue-originals
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
W="work/auto-$SLOT"; O="out/auto-$SLOT"; rm -rf "$W" "$O"
args=(); [ -f "queue/$SLOT/remake.json" ] && args=(--remake "queue/$SLOT/remake.json")
[ -n "${REEL_CATEGORY:-}" ] && args+=(--category "$REEL_CATEGORY")      # (a chosen format, e.g. for a test reel)
{
  echo "=== auto reel $SLOT  $(date -u '+%F %T UTC')"
  if [ -f "prewritten/$SLOT/spec.json" ]; then          # written ahead by a cloud session (prewritten/README.md)
    mkdir -p "$W" && cp "prewritten/$SLOT/spec.json" "prewritten/$SLOT/caption.txt" "$W/" && echo "using the prewritten script"
  else
    python3 src/make_spec.py "$SLOT" "$W" "${args[@]}"
  fi
  python3 src/narrate.py "$W"
  PAGE=reel.html FPS=${AUTO_FPS:-60} python3 src/render.py "$W" "$O"
  [ -n "${LATE_OK:-}" ] || [ "$(date -u +%Y-%m-%dT%H%M)" \< "$SLOT" ] || { echo "too late for $SLOT: the reel already queued posts"; exit 0; }   # (LATE_OK=1: a catch-up, posted at once)
  mkdir -p "queue/.staging/$SLOT" && cp "$O/reel.mp4" "$O/caption.txt" "$O/cover.jpg" "queue/.staging/$SLOT/"
  [ -d "queue/$SLOT" ] && { rm -rf "queue-originals/$SLOT"; mv "queue/$SLOT" "queue-originals/$SLOT"; }
  touch "queue/.staging/$SLOT/.auto"
  mv "queue/.staging/$SLOT" "queue/$SLOT"
  echo "=== queued $SLOT $(date -u '+%T UTC')"
} 2>&1 | tee -a "logs/auto.log"
