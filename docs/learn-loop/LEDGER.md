# The Learn loop: the ledger

One row per iteration, appended by the loop (`LOOP.md`). The owner may add rows marked **do next** or **won't do**.
B = `tools/learn_check.py` (checks passing / total). C = the simulated learner run that iteration (persona, score / 20).

| # | Date | B | C | Finding | Change | Commit | Left |
|---|---|---|---|---|---|---|---|
| 0 | 2026-11-08 | set-up | (none) | The starting point: Phase 1 and 2 of the roadmap and Rounds 1-4 of the Learn work (LP1-LP15) built locally and tested; the two walkthroughs of 7 November (recall-heavy questions, length bias, duplicates, chartless chart lessons, no tailoring beyond placement) are the backlog | `tools/learn_check.py`, this folder, a test, the docs | (first commit) | B fails on the longest-option share (about 70%) and the core units' interleaving (only Start done); C not yet scored |
| 1 | 2026-11-08 | 6/9 | (none: B failed) | B: the core units' questions all at the end (7% under a section) | Market basics interleaved: its 21 questions moved under the section each tests; the duplicate 'beats the forecast' question replaced by one on noise; the interleave check now counts a question as placed when reading follows it | (this commit) | B: 33 thin lessons, longest-option 71%, interleave 20%; next: Reading charts |
| 2 | 2026-11-08 | 6/9 | (none: B failed) | B: core units' questions at the end (20%) | Reading charts interleaved: 30 questions moved under the section each tests; Ranges and breakouts gains a fake-breakout question. Another session has uncommitted edits in docs/HOW_IT_WORKS.md and the reel tools; this iteration touched neither | (this commit) | B: 33 thin lessons, longest-option 71%, interleave 41%; next: Indicators |
| 3 | 2026-11-08 | 6/9 | (none: B failed) | B: core units' questions at the end (41%) | Indicators interleaved: 21 questions moved under the section each tests | (this commit) | B: 33 thin lessons, longest-option 71%, interleave 55%; next: Orders, then Risk |
| 4 | 2026-11-08 | 7/9 | (none: B failed) | B: core units' questions at the end (55%) | Orders and Risk interleaved: 36 questions and the four generated calculations moved under the section each tests; the placement rule counts the one exercise right after a section's last paragraph. The interleave check passes (97%) | (this commit) | B: 33 thin lessons, longest-option 71%; next: the longest-option bias in the core units (rewrite options to balanced lengths) |
| 5 | 2026-11-08 | 7/9 | (none: B failed) | B: the right answer is the longest option in 71% of questions | 40 questions in Start, Market basics, Orders and Risk rewritten with wrong options as detailed as the right one; 23 right answers across all units lost a trailing ': explanation' (the WHY keeps it). Share now 56% | (this commit) | B: 33 thin lessons, longest-option 56% (target under 45%); next: Reading charts and Indicators options |
| 6 | 2026-11-08 | 8/9 | (none: B failed) | B: the right answer is the longest option in 56% of questions | Reading charts and Indicators: 25 questions rewritten with wrong options as detailed as the right one; then across the six core units the longest wrong option of 44 questions gained a plausible qualifier. Share now 36%: the check passes | (this commit) | B: 33 thin lessons (2 exercises each, all outside the core units); next: a third exercise for each |
| 7 | 2026-11-08 | 9/9 | (none: B failed at the start) | B: 33 lessons with only two exercises | A third, scenario-style question for each of the 33 (now 278 questions). B passes every check | (this commit) | C not yet scored; next: the beginner walkthrough (C1) |
| 8 | 2026-11-08 | 9/9 | C1 beginner 12/20 | Seven S findings from the beginner walkthrough: the goal reached by two answers; a task box stuck on 'Not yet' after Back; intro copy promising a chart test and a task in every lesson and mentioning MB; XP and the streak unexplained; no reason to come back stated; exercise buttons not full width on a phone; the first task opening the MSI 50 index | Default goal 50; a `pageshow` redraw; honest intro copy; an XP-rules line and a streak tooltip; a come-back line tied to the goal and streak; phone CSS for the cards; the task opens Novaxis and asks for about 10 MB (all seven taken as one set: each a line) | (this commit) | C1 to be re-scored next; C2 and C3 not yet run |

## Backlog the walkthroughs left (the loop picks from here when the checks are green)

- done (loops 1-4): the six core units interleaved
- done (loops 5-6): option lengths balanced in the core units; recall questions in the core units still to turn into scenarios
- on-topic chart tests in the lessons that teach a kind (`[test pattern flag]`, `[test candle hammer]`); Bollinger and VWAP overlays in `lrnSvg`
- two formats: which chart? (two charts, pick one) and place the stop (click a price)
- tailoring: the next lesson skips mastered units; a daily set of five on `/learn`; the placement offer after a long absence
- difficulty tiers on chart tests from accuracy per kind
- the rsi, ma and candle tests' result text should not quote a later move
- phone layout of the exercise cards at 380 px
