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
[ -n "${REEL_OLD:-}" ] && python3 src/story_reel.py next >> logs/story.log 2>&1 || true   # (back 2026-11-19, the owner: "keep making part 5-8 of the roblox story"; its link is the Daily now)   # (the day's part of the story serial, once a day from 10:00 UTC: the owner, 2026-11-14,
                                                                 #  "post them one a day". It takes the pipeline lock itself, so it runs before ours; it does nothing unless a part is due)
exec 8>queue/.auto.lock; flock 8                   # (one reel at a time: the critic has no round limit, so the next run waits)
[ -n "$(find state/format_scores.json -mmin -720 2>/dev/null)" ] || python3 src/format_scores.py >> logs/formats.log 2>&1 || true   # (twice a day: Instagram's numbers per format; make_spec.py drops the worst and repeats the best; its failure never stops a reel)
[ -n "$(find state/reel_ledger.json -mmin -1440 2>/dev/null)" ] || python3 src/learn.py >> logs/learn.log 2>&1 || true   # (once a day: why the best and worst reels did as they did, into state/learned.md for the writer; its failure never stops a reel)
[ -n "$(find state/own_reels.json -mmin -1440 2>/dev/null)" ] || python3 src/own_reels.py >> logs/own_reels.log 2>&1 || true   # (once a day: our own best and worst openings for the writer; its failure never stops a reel)
: # off 2026-11-10, the owner: old-template trial winners must not reach the grid (director reels only) # python3 lab/winners.py >> logs/winners.log 2>&1 || echo "winners step failed (logs/winners.log)"   # (Trial Reels winners take the next slot of their format: the owner, 2026-11-08)
# The owner, 2026-11-22: "only post ONCE a day (at 23:30) and the story should be about the stock that was picked for the daily on
# that day". Unless REEL_OLD is set (the old formats, kept as code), every run makes that one reel: today's Daily stock, its story,
# a flat 2D cartoon explainer, a new scene every sentence (src/explainer/make.py; the owner's reference, 2026-11-22), queued for <today>T2330 when 9 of the 13 simulated viewers watch to the end.
# It does nothing once the day's reel is queued, and stops after three tries.
# The day's two promo reels about the Daily (the owner, 2026-11-24): the 09:00 teaser of the day's chart and a 16:00 promo of the
# game, made from templates (src/explainer/promo.py); a slot already queued or past is left alone; its failure never stops the reel.
[ -z "${REEL_OLD:-}" ] && { python3 src/explainer/promo.py day "$(date -u +%F)" >> logs/promo.log 2>&1 || echo "promo reels not made (logs/promo.log)"; }
if [ -z "${REEL_OLD:-}" ]; then
  # (since 2026-11-27, the owner: "keep this style for each daily reel ... more imaginative every day": the studio's "your money" daily,
  #  a new idea each day; the old explainer only when the studio has failed three times that day)
  python3 src/studio/daily.py "$(date -u +%F)" >> logs/studio.log 2>&1 && exit 0
  [ "$(cat "state/studio-$(date -u +%F).tries" 2>/dev/null || echo 0)" -ge 3 ] || { echo "the studio's daily was not made (logs/studio.log): it tries again next run"; exit 1; }
  python3 src/explainer/make.py daily "$(date -u +%F)" >> logs/explainer.log 2>&1 && exit 0
  echo "today's reel was not made (logs/explainer.log)"; exit 1
fi
SLOT="${1:-}"
if [ -z "$SLOT" ]; then                              # (made ahead: the earliest slot in the next 36 hours that has no approved reel
  for d in "$(date -u +%F)" "$(date -u -d tomorrow +%F)" "$(date -u -d '2 days' +%F)"; do   #  yet, so posts go out on time)
    for h in 0300 0900 1300 1800 2100; do       # (five a day since 2026-11-12, the owner; 06:00 and 12:00 are gone. The Daily and a news reel come on top)
      s="${d}T$h"; ds=$(( $(date -u -d "${d} ${h:0:2}:${h:2:2}" +%s) - $(date -u +%s) ))
      [ "$ds" -gt 600 ] && [ "$ds" -le 129600 ] || continue
      [ "$h" = 2100 ] && [ "$(date -u -d "$d" +%u)" -le 5 ] && [ "$ds" -gt 16200 ] && continue   # (the market reel is made within 4.5 hours of its slot, so its news is today's)
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
# The market's day after the US close (the owner, 2026-11-18: "cover big news headlines, what's happening in the market"): a weekday's
# 21:00 slot is a news reel when a market story passes the research and the fact checks; anything else and the slot gets a game reel.
if [ "${SLOT:11:4}" = "2100" ] && [ "$(date -u -d "${SLOT:0:10}" +%u)" -le 5 ] && [ -z "${REEL_CATEGORY:-}" ] && [ -z "${RESUME:-}" ] && [ ! -f state/news_off ]; then
  echo "=== market today $SLOT  $(date -u '+%F %T UTC')" | tee -a logs/auto.log
  if python3 src/news_reel.py slot "$SLOT" >> logs/news.log 2>&1; then echo "=== queued $SLOT (market today) $(date -u '+%T UTC')" | tee -a logs/auto.log; exit 0; fi
  echo "market today not made for $SLOT (logs/news.log): a game reel instead" | tee -a logs/auto.log
fi
# A crazy true stock story at 13:00 and a stock explainer at 18:00 (the owner, 2026-11-19), researched and fact-checked
# (src/stock_story.py); on a slot's first try only, and anything else and the same run makes a game reel.
# 13:00 is the day's complete "In this town" story first (src/town_story.py: the form of the genre's most-watched stories,
# research/niche3d_2026-11-21.md); state/town_story_off turns it off. 18:00 takes turns between the crazy stock history and
# the explainer, by the day of the year.
if [ "${SLOT:11:4}" = 1300 ] && [ -z "${REEL_CATEGORY:-}" ] && [ -z "${RESUME:-}" ] && [ ! -f state/town_story_off ] && [ "$(cat "queue/$SLOT/.tries" 2>/dev/null || echo 1)" -le 1 ]; then
  echo "=== in this town $SLOT  $(date -u '+%F %T UTC')" | tee -a logs/auto.log
  if python3 src/town_story.py slot "$SLOT" >> logs/town.log 2>&1; then echo "=== queued $SLOT (in this town) $(date -u '+%T UTC')" | tee -a logs/auto.log; exit 0; fi
  echo "the town story was not made for $SLOT (logs/town.log): a stock story instead" | tee -a logs/auto.log
fi
# 18:00 on an explainer day is a "What if" first (src/whatif.py: the form of the reel the owner chose as the model, 2026-11-22: one
# hypothetical about the viewer and money, the catch, the loop); state/whatif_off turns it off, and anything else makes the explainer.
if [ "${SLOT:11:4}" = 1800 ] && [ $(( 10#$(date -u -d "${SLOT:0:10}" +%j) % 2 )) -ne 0 ] && [ -z "${REEL_CATEGORY:-}" ] && [ -z "${RESUME:-}" ] && [ ! -f state/whatif_off ] && [ "$(cat "queue/$SLOT/.tries" 2>/dev/null || echo 1)" -le 1 ]; then
  echo "=== what if $SLOT  $(date -u '+%F %T UTC')" | tee -a logs/auto.log
  if python3 src/whatif.py slot "$SLOT" >> logs/town.log 2>&1; then echo "=== queued $SLOT (what if) $(date -u '+%T UTC')" | tee -a logs/auto.log; exit 0; fi
  echo "the what if was not made for $SLOT (logs/town.log): the explainer instead" | tee -a logs/auto.log
fi
case "${SLOT:11:4}" in 1300) KIND=story ;; 1800) [ $(( 10#$(date -u -d "${SLOT:0:10}" +%j) % 2 )) -eq 0 ] && KIND=story || KIND=explainer ;; *) KIND= ;; esac
if [ -n "$KIND" ] && [ -z "${REEL_CATEGORY:-}" ] && [ -z "${RESUME:-}" ] && [ ! -f state/stories_off ] && [ "$(cat "queue/$SLOT/.tries" 2>/dev/null || echo 1)" -le 1 ]; then
  echo "=== $KIND $SLOT  $(date -u '+%F %T UTC')" | tee -a logs/auto.log
  if python3 src/stock_story.py slot "$SLOT" "$KIND" >> logs/stories.log 2>&1; then echo "=== queued $SLOT ($KIND) $(date -u '+%T UTC')" | tee -a logs/auto.log; exit 0; fi
  echo "$KIND not made for $SLOT (logs/stories.log): a game reel instead" | tee -a logs/auto.log
fi
# The Daily's game reels are filmed in the 3D town first (the owner, 2026-11-21: "they should be more 3d animation style";
# src/town_daily.py: the real chart on the square's screen); on a slot's first try only, and if it is not made the same run
# makes the flat reel. state/town_off turns it off.
if [ -z "${REEL_CATEGORY:-}" ] && [ -z "${RESUME:-}" ] && [ ! -f state/town_off ] && [ "$(cat "queue/$SLOT/.tries" 2>/dev/null || echo 1)" -le 1 ]; then
  echo "=== town reel $SLOT  $(date -u '+%F %T UTC')" | tee -a logs/auto.log
  if python3 src/town_daily.py slot "$SLOT" >> logs/town.log 2>&1; then echo "=== queued $SLOT (town) $(date -u '+%T UTC')" | tee -a logs/auto.log; exit 0; fi
  echo "town reel not made for $SLOT (logs/town.log): the flat reel instead" | tee -a logs/auto.log
fi
W="work/auto-$SLOT"; O="out/auto-$SLOT"; export REEL_SLOT="$SLOT"   # (Yesterday's stock reads the Daily before this slot's day)
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
