# The Learn loop: the ledger

One row per iteration, appended by the loop (`LOOP.md`). The owner may add rows marked **do next** or **won't do**.
B = `tools/learn_check.py` (checks passing / total). C = the simulated learner run that iteration (persona, score / 20).

| # | Date | B | C | Finding | Change | Commit | Left |
|---|---|---|---|---|---|---|---|
| 0 | 2026-11-08 | set-up | (none) | The starting point: Phase 1 and 2 of the roadmap and Rounds 1-4 of the Learn work (LP1-LP15) built locally and tested; the two walkthroughs of 7 November (recall-heavy questions, length bias, duplicates, chartless chart lessons, no tailoring beyond placement) are the backlog | `tools/learn_check.py`, this folder, a test, the docs | (first commit) | B fails on the longest-option share (about 70%) and the core units' interleaving (only Start done); C not yet scored |
| 1 | 2026-11-08 | 6/9 | (none: B failed) | B: the core units' questions all at the end (7% under a section) | Market basics interleaved: its 21 questions moved under the section each tests; the duplicate 'beats the forecast' question replaced by one on noise; the interleave check now counts a question as placed when reading follows it | (this commit) | B: 33 thin lessons, longest-option 71%, interleave 20%; next: Reading charts |
| 2 | 2026-11-08 | 6/9 | (none: B failed) | B: core units' questions at the end (20%) | Reading charts interleaved: 30 questions moved under the section each tests; Ranges and breakouts gains a fake-breakout question. Another session has uncommitted edits in docs/HOW_IT_WORKS.md and the reel tools; this iteration touched neither | (this commit) | B: 33 thin lessons, longest-option 71%, interleave 41%; next: Indicators |
| 3 | 2026-11-08 | 6/9 | (none: B failed) | B: core units' questions at the end (41%) | Indicators interleaved: 21 questions moved under the section each tests | (this commit) | B: 33 thin lessons, longest-option 71%, interleave 55%; next: Orders, then Risk |

## Backlog the walkthroughs left (the loop picks from here when the checks are green)

- do next: interleave the questions of the remaining five core units (Market basics, Reading charts, Indicators, Orders, Risk), one unit per iteration
- rewrite recall questions in the core units as scenarios; balance option lengths (B will fail until under 45%)
- on-topic chart tests in the lessons that teach a kind (`[test pattern flag]`, `[test candle hammer]`); Bollinger and VWAP overlays in `lrnSvg`
- two formats: which chart? (two charts, pick one) and place the stop (click a price)
- tailoring: the next lesson skips mastered units; a daily set of five on `/learn`; the placement offer after a long absence
- difficulty tiers on chart tests from accuracy per kind
- the rsi, ma and candle tests' result text should not quote a later move
- phone layout of the exercise cards at 380 px
