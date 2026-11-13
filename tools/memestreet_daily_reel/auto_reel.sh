#!/usr/bin/env bash
# Make the auto reel for the next posting slot and put it in the queue (queue_post.sh posts it on time).
#   ./auto_reel.sh                    the next slot (03:00, 09:00, 13:00, 18:00, 21:00 UTC) without its reel
#   ./auto_reel.sh 2026-11-05T1200    that slot
# (03:00, 09:00, 13:00 and 21:00 are the viral slots.)
# A slot that already holds a November reel gets a remake of it (queue/<slot>/remake.json); the original is kept in
# queue-originals/. Every reel goes to the film critic (src/critic.py) and is rewritten until he approves it; only an
# approved reel is queued, and the queue posts only approved reels. Late? It posts as soon as it is approved.
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"                 # (Claude Code, the script writer on the plan)
mkdir -p logs queue queue-originals
[ -f queue/.daily-pending ] && { echo "the Daily is due: this run waits for the next timer"; exit 0; }   # (make_reel.sh, the owner 2026-11-10)
exec 8>queue/.auto.lock; flock 8                   # (one reel at a time: the critic has no round limit, so the next run waits)
[ -n "$(find state/format_scores.json -mmin -720 2>/dev/null)" ] || python3 src/format_scores.py >> logs/formats.log 2>&1 || true   # (twice a day: Instagram's numbers per format; make_spec.py drops the worst and repeats the best; its failure never stops a reel)
[ -n "$(find state/reel_ledger.json -mmin -1440 2>/dev/null)" ] || python3 src/learn.py >> logs/learn.log 2>&1 || true   # (once a day: why the best and worst reels did as they did, into state/learned.md for the writer; its failure never stops a reel)
[ -n "$(find state/own_reels.json -mmin -1440 2>/dev/null)" ] || python3 src/own_reels.py >> logs/own_reels.log 2>&1 || true   # (once a day: our own best and worst openings for the writer; its failure never stops a reel)
: # off 2026-11-10, the owner: old-template trial winners must not reach the grid (director reels only) # python3 lab/winners.py >> logs/winners.log 2>&1 || echo "winners step failed (logs/winners.log)"   # (Trial Reels winners take the next slot of their format: the owner, 2026-11-08)
SLOT="${1:-}"
if [ -z "$SLOT" ]; then                              # (made ahead: the earliest slot in the next 36 hours that has no approved reel
  for d in "$(date -u +%F)" "$(date -u -d tomorrow +%F)" "$(date -u -d '2 days' +%F)"; do   #  yet, so posts go out on time)
    for h in 0300 0900 1300 1800 2100; do       # (five a day since 2026-11-12, the owner; 06:00 and 12:00 are gone. The Daily and a news reel come on top)
      s="${d}T$h"; ds=$(( $(date -u -d "${d} ${h:0:2}:${h:2:2}" +%s) - $(date -u +%s) ))
      [ "$ds" -gt 600 ] && [ "$ds" -le 129600 ] || continue
      [ -f "queue/$s/.auto" ] || [ -f "queue/$s/posted.json" ] && continue
      [ "$(cat "queue/$s/.tries" 2>/dev/null || echo 0)" -ge 3 ] && continue   # (held three times: that slot stays empty; the third try since 2026-11-12, when four of eight slots had gone empty)
      SLOT=$s; break 2
    done
  done
  [ -n "$SLOT" ] || { echo "every slot in the next 36 hours has its reel"; exit 0; }
  mkdir -p "queue/$SLOT"; tries=$(cat "queue/$SLOT/.tries" 2>/dev/null || echo 0)
  echo $((tries + 1)) > "queue/$SLOT/.tries"; export REEL_TRY=$tries   # (a second try gets another format)
fi
[ -n "$SLOT" ] || { echo "no slot"; exit 0; }
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
