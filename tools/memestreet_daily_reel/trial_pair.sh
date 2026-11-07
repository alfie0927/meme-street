#!/usr/bin/env bash
# The Trial Reels test (2026-11-07, the owner's go): each day one brief becomes two reels, the current one (v1) and
# version 2 (v2: RULES_V2.md, src/reel_v2.html), both posted as Trial Reels (non-followers only, off the grid; Instagram
# shares one with followers if it performs) five minutes apart, so each pair compares the two versions on the same
# facts, chart, hour and audience pool. The regular slots are untouched. Results: lab/insights.py.
# Three pairs a day (10:30, 15:30, 22:30 UTC; the owner: "run more pairs, we just want to see what does well"), each a
# different format in turn, so the pairs also show which formats work.
#   ./trial_pair.sh                    the next pair time 1-24 hours ahead that has no pair yet (the hourly timer)
#   ./trial_pair.sh 2026-11-08T1530    that pair
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"
mkdir -p logs queue
exec 8>queue/.auto.lock; flock 8                     # (one reel job at a time: the server has room for one)
TIMES=(1030 1530 2230)
A="${1:-}"
if [ -z "$A" ]; then
  for d in "$(date -u +%F)" "$(date -u -d tomorrow +%F)"; do
    for h in "${TIMES[@]}"; do
      ds=$(( $(date -u -d "$d ${h:0:2}:${h:2:2}" +%s) - $(date -u +%s) ))
      [ "$ds" -gt 3600 ] && [ "$ds" -le 86400 ] && [ ! -e "queue/${d}T$h" ] && { A="${d}T$h"; break 2; }
    done
  done
  [ -n "$A" ] || { echo "every pair in the next 24 hours is made"; exit 0; }
fi
B="${A%T*}T$(printf %04d $((10#${A#*T} + 5)))"
for s in "$A" "$B"; do [ -e "queue/$s" ] && { echo "$s is taken already"; exit 0; }; done
CATS=("Chart quiz" "Stock story" "Technical lesson" "Chart twist" "Chart breakdown" "Stick skit" "Trading mistake" "Myth or fact")
k=0; for i in "${!TIMES[@]}"; do [ "${TIMES[$i]}" = "${A#*T}" ] && k=$i; done   # (each pair a different format, in turn)
CAT="${CATS[$(( (10#$(date -u -d "${A%T*}" +%j) * ${#TIMES[@]} + k) % ${#CATS[@]} ))]}"
W1="work/trial-$A"; W2="work/trial-$B"; O1="out/trial-$A"; O2="out/trial-$B"
{
  echo "=== trial pair $A + $B ($CAT)  $(date -u '+%F %T UTC')"
  rm -rf "$W1" "$W2" "$O1" "$O2"
  python3 src/make_spec.py pair "$A" "$W1" "$W2" --category "$CAT"
  python3 src/critic.py loop "$W1" "$O1"            # (the same one-pass safety check as every reel; a held one stops the pair)
  REEL_V2=1 REEL_PAGE=reel_v2.html python3 src/critic.py loop "$W2" "$O2"
  for x in "$A $O1 v1" "$B $O2 v2"; do
    set -- $x
    mkdir -p "queue/.staging/$1" && cp "$2/reel.mp4" "$2/caption.txt" "$2/cover.jpg" "$2/approved.json" "queue/.staging/$1/"
    echo "{\"variant\": \"$3\", \"pair\": \"$A\", \"category\": \"$CAT\"}" > "queue/.staging/$1/trial.json"
  done
  mv "queue/.staging/$A" "queue/$A"; mv "queue/.staging/$B" "queue/$B"   # (both or neither)
  for x in "$W1 $O1 v1" "$W2 $O2 v2"; do set -- $x; python3 lab/audience.py pack "$1" "$2" "lab/data/trial/$A-$3" || true; done
  python3 lab/audience.py both "lab/data/trial/$A-v1" "lab/data/trial/$A-v2" | tail -1 || true   # (the simulated verdict, logged before the real one)
  echo "=== trial pair queued $A + $B $(date -u '+%T UTC')"
} 2>&1 | tee -a logs/trial.log
