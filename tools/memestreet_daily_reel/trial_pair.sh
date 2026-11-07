#!/usr/bin/env bash
# The Trial Reels test (2026-11-07, the owner's go): each day one brief becomes two reels, the current one (v1) and
# version 2 (v2: RULES_V2.md, src/reel_v2.html), both posted as Trial Reels (non-followers only, off the grid; Instagram
# shares one with followers if it performs) five minutes apart, so each pair compares the two versions on the same
# facts, chart, hour and audience pool. The regular slots are untouched. Results: lab/insights.py.
# Back to back (the owner: "run continuously so we can see improvements every new version"): the timer starts the next
# pair once 9.5 hours have passed since the last (about 5 Trial Reels a day, the owner's choice), and only when no regular slot due within 6
# hours is waiting for its reel. Each pair is the next of eight formats and carries the version of RULES_V2.md it was made
# with (lab/evolve.py makes a new version each day from the results).
#   ./trial_pair.sh                    the next pair, posted as soon as it is made
#   ./trial_pair.sh 2026-11-08T1530    that pair
set -euo pipefail
cd "$(dirname "$0")"; set -a; . ./config.env; set +a
export PATH="$HOME/.local/bin:$PATH"
mkdir -p logs queue
exec 8>queue/.auto.lock; flock 8                     # (one reel job at a time: the server has room for one)
A="${1:-}"
if [ -z "$A" ]; then                                 # (back to back: the next pair is made as soon as the last one is)
  [ -n "$(find queue -name trial.json -newermt "-570 minutes" 2>/dev/null)" ] && { echo "a pair in the last 9.5 hours: waiting (about 5 Trial Reels a day, spread out)"; exit 0; }
  for h in 0300 0600 0900 1200 1300 1800 2100; do      # (the regular reels come first: a slot due within 6 hours without its reel waits for the maker)
    for d in "$(date -u +%F)" "$(date -u -d tomorrow +%F)"; do
      ds=$(( $(date -u -d "$d ${h:0:2}:${h:2:2}" +%s) - $(date -u +%s) ))
      [ "$ds" -gt 0 ] && [ "$ds" -le 21600 ] && [ ! -f "queue/${d}T$h/.auto" ] && [ ! -f "queue/${d}T$h/posted.json" ] && [ ! -f "queue/${d}T$h/approved.json" ] && { echo "regular slot ${d}T$h comes first"; exit 0; }
    done
  done
  t=$(( ($(date -u +%s) / 300 + 1) * 300 ))           # (named for the next 5 minutes: it posts as soon as it is made)
  while [ -e "queue/$(date -u -d @$t +%FT%H%M)" ] || [ -e "queue/$(date -u -d @$((t + 300)) +%FT%H%M)" ]; do t=$((t + 600)); done
  A=$(date -u -d @$t +%FT%H%M)
fi
B=$(date -u -d "@$(( $(date -u -d "${A%T*} ${A:11:2}:${A:13:2}" +%s) + 300 ))" +%FT%H%M)
for s in "$A" "$B"; do [ -e "queue/$s" ] && { echo "$s is taken already"; exit 0; }; done
CATS=("Chart quiz" "Stock story" "Technical lesson" "Chart twist" "Chart breakdown" "Stick skit" "Trading mistake" "Myth or fact")
CAT="${CATS[$(( $(find queue -name trial.json | wc -l) / 2 % ${#CATS[@]} ))]}"   # (each pair the next format, in turn)
VER=$(grep -m1 -oP '^Version: \K\d+' RULES_V2.md || echo 1)   # (the version of the rules under test: the scoreboard groups by it)
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
    echo "{\"variant\": \"$3\", \"pair\": \"$A\", \"category\": \"$CAT\", \"version\": $VER}" > "queue/.staging/$1/trial.json"
  done
  mv "queue/.staging/$A" "queue/$A"; mv "queue/.staging/$B" "queue/$B"   # (both or neither)
  for x in "$W1 $O1 v1" "$W2 $O2 v2"; do set -- $x; python3 lab/audience.py pack "$1" "$2" "lab/data/trial/$A-$3" || true; done
  python3 -c "import sys,json; sys.path.insert(0,'lab'); import audience as S; s=S.both('lab/data/trial/$A-v1','lab/data/trial/$A-v2'); json.dump({'share_preferring_v1': s, 'pick': 'v1' if s['watch_longer'] > .5 else 'v2'}, open('lab/data/trial/$A-sim.json','w'))" | tail -1 || true   # (the simulated verdict, saved before the real one: lab/trials.py scores it)
  echo "=== trial pair queued $A + $B $(date -u '+%T UTC')"
} 2>&1 | tee -a logs/trial.log
