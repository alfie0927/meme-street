#!/usr/bin/env bash
# The Trial Reels test (2026-11-07, the owner's go): each day one brief becomes two reels, the current one (v1) and
# version 2 (v2: RULES_V2.md, src/reel_v2.html), both posted as Trial Reels (non-followers only, off the grid; Instagram
# shares one with followers if it performs) five minutes apart, so each pair compares the two versions on the same
# facts, chart, hour and audience pool. The regular slots are untouched. Results: lab/insights.py.
#   ./trial_pair.sh                    today's pair at 15:30 and 15:35 UTC (memestreet-reel-trial.timer runs it at 06:30)
#   ./trial_pair.sh 2026-11-08T1530    that pair
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"
mkdir -p logs queue
exec 8>queue/.auto.lock; flock 8                     # (one reel job at a time: the server has room for one)
A="${1:-$(date -u +%F)T1530}"; B="${A%T*}T$(printf %04d $((10#${A#*T} + 5)))"
for s in "$A" "$B"; do [ -e "queue/$s" ] && { echo "$s is taken already"; exit 0; }; done
CATS=("Chart quiz" "Stock story" "Technical lesson" "Chart twist")   # (a different format each day, in turn)
CAT="${CATS[$(( 10#$(date -u -d "${A%T*}" +%j) % ${#CATS[@]} ))]}"
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
  echo "=== trial pair queued $A + $B $(date -u '+%T UTC')"
} 2>&1 | tee -a logs/trial.log
