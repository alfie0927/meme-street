# Reel brief: more people watching, more people reaching the site

For the reels chat (the session that owns `tools/memestreet_daily_reel/`), from the growth plan
([docs/ROADMAP.md](../docs/ROADMAP.md), the RL and A track). Evidence: [instagram.md](instagram.md), pulled 10 Nov 2026.
The owner took the plan's defaults on 10 Nov, except one: **the posting schedule stays as it is.**

## What the numbers say (38 reels, 30 Oct to 9 Nov)

- Median 61 views; median hold at 3 s 32% (reels_skip_rate 68%). 0 comments, 7 sends, 10 saves in total.
- 99.9% of reach is non-followers, so Instagram does show the reels to strangers. Then 51 profile visits and
  **2 link taps in 29 days**. Reels end with "Join free at memestreet.net"; nobody types it, and the bio link went
  to the home page.
- Holds best: **Stock story** (n=5, 56% kept at 3 s, 2.1x views), **Trader levels** (n=1, 56%, 17 s watch, 3 saves).
- Holds worst: **Daily recap** (n=7, 27%) and **Technical lesson** (n=5, 27%). Both open with a label or a
  definition: "Daily Chart #6 recap", "Chart quiz #2. Lock in…", "Price tells you what happened…".
- Length shows no effect (over 60 s did as well as 30 s). The director reels' length is not the problem.
- 6 to 8 reels a day from 7 Nov did not lift views: the median fell from 67 to 55. (The owner keeps the schedule.)

## Changes, in order

1. **The posting schedule stays as it is** (the owner's decision, 10 Nov). The queue holds 50 rendered reels, three
   a day to 25 Nov; the changes below reach them only through `./rerender.sh <slot>` or in new reels.
2. **The 23:00 UTC "Daily Chart #N recap" keeps its slot** with the rebuilt opening (point 5).
3. **Rotation:** take Technical lesson and Explained like you're 5 out of `ROTATION` (`src/make_spec.py:89-95`).
   The owner rated both Ugly in `RULEBOOK.md` "By format", and they hold 27% and 39%.
4. **The first second.** Frame 1 shows the stake or the odd fact in big words, and the voice says it at 0 s.
   `RULES_V2.md` already asks for this, but recaps and quizzes still open with their own label. Add one check in
   `make_spec.py` that refuses an opening line that is a label (`Daily Chart #`, `Chart quiz #`, `Today we`) or a
   definition ("X is…", "X tells you…"). The brand header fades in after 3 s: one line in `src/reel.html:489`,
   the same as `src/reel_v2.html:474`. Openers that held: "A bed maker that lets you pick your dream?",
   "One escaped dragon shut a motorway for a day.", "Which level of trader are you right now?".
5. **The Daily Chart reel, rebuilt and tested first.** `src/analyze.py` leads with "Daily Chart number N…" (lines
   166-171). Lead with the move instead ("It fell 12% in ten candles. Would you have sold?"), then the reveal, the
   best trade, and "today's chart is in the bio". Test the new opening as trial reels against the old one.
6. **The ending: one ask, and a link people can tap** (decisions 3 and 4, accepted 10 Nov). Spoken and in the end pill:
   "Play today's chart free. Link in bio." with `memestreet.net/daily` shown small (`memestreet.net/play` once that
   page is deployed). This replaces `RULEBOOK.md:41` "Join free at memestreet.net" and the pill at
   `src/reel.html:44` and `src/reel_v2.html:42`; the sign-off rules in `make_spec.py` (537-551, 747, 1210) follow.
   Quiz reels ask for a comment instead; never two asks.
7. **Captions:** first line is the question or the odd fact, never the format's name. Plain searched words
   ("stock market game", "learn to read charts", "practice trading"). At most 5 hashtags. Last line:
   "Today's chart: link in bio." Switch on the existing checker `src/ig/caption.py`.
8. **Honest numbers:** drop the "N players took on this chart" line (`analyze.py:351-352`) until the boards mark
   house bots; today it counts the 72 bots as players.
9. **AI label** (decision 10, accepted 10 Nov): check whether the publishing API takes an AI-content flag; the pipeline
   sets none today (`src/post_instagram.py:90`).

## How to test

- One change at a time, in this order: the opening, then the ending, then length. Trial reels (graduation MANUAL)
  against normal reels; judge after ten pairs on the median hold at 3 s, not on views.
- Pause the automatic evolve step (`lab/trials.py`, `lab/evolve.py`) until reels pass about 300 views. At 60 views
  a 3-point gap in skip rate is one or two people.
- Weekly: `lab/insights.py`, then the three best and three worst openings by hold at 3 s go into the writer's
  brief (`brief()` in `src/make_spec.py:935-978`).
- After a template change, `./rerender.sh <slot>` for the queued reels (local voice, no critic round), and a
  `DRY=1` render the owner watches before the timer resumes.

## Unchanged

The director look, a palette and device per reel, the Kokoro voice at one speed, captions for all the audio, the
owner's verdicts per format in `RULEBOOK.md`, posting without approval. No spending: the owner's rule since
10 Nov. Owner feedback still goes into `RULEBOOK.md` "By format".
