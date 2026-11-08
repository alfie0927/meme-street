# The Learn loop: the rubric

What "right" means for the Learn section (`/learn`), measured the same way every iteration. The loop (`LOOP.md`)
stops when **B passes, every persona in C scores at target, and two iterations in a row find nothing of size S or
larger.** Sizes: S under a day, M a few days.

## A. The learner's journey (what the whole thing must do)

1. A new account is offered the placement test; its result sets where the path starts and marks the units known as passed.
2. Every lesson is short (under 600 prose words), reads in cards, and asks a question under the section it tests, not only at the end.
3. Every lesson has at least three exercises, one of which applies the idea (a number, a chart, a scenario); chart-reading lessons have a chart test narrowed to their topic.
4. A wrong answer is explained and the right answer shown; the same question earns nothing twice.
5. Each lesson ends with something to do: a market task, a "try it" link that opens the live chart set up for it, or a chart test; passing lights up the next lesson.
6. The path shows progress (level, XP, streak, goal, share of the course, finished units folding) and celebrates the first XP of a day, the goal, a level, a finished unit.
7. The experience is tailored: the review asks about the skills missed most, the habits and "Your trading" use the player's own trades, the next step skips what the placement or review has shown is known.
8. Nothing is gameable: options shuffled, no position or length bias, the coin-flip test out of the weak spots, the league counting only real exercise XP.

## B. The automated checks: `python tools/learn_check.py`

Exits 1 when any check fails. The thresholds are the constants at the top of the tool.

| Check | Threshold |
|---|---|
| Every lesson parses | always |
| Exercises per lesson | at least 3 (the glossary is a reference) |
| Prose words per lesson | at most 600 |
| Right answer is the longest option | under 45% of questions |
| Near-duplicate questions | none over 85% shared words |
| Chart lessons (Charts, Indicators, Orders, Strategies units) | each has a `[chart]` or `[test]` |
| `[try]` links | every path a route or `/stock/`, every `?ind=` id and `?tf=` size known to `web/chart.js` |
| `[task]` kinds | each named in `tests/test_learning.py` |
| Core units (Start, Market basics, Reading charts, Indicators, Orders, Risk) | at least 80% of questions under a section, not after the last heading |

Also every iteration: `python -m unittest test_learning test_drills` (from `tests/`), `node --check web/learn.js`,
and the inline script of `web/index.html` parsed with node.

## C. The simulated learners: three walkthroughs, 20 points each, target 18

Run as an Explore agent (read-only; GET requests to the local server allowed, never POST) with the checklist below
verbatim. It answers each point yes or no with a file:line, then lists its findings ranked by size with the fix it
would make. One persona per iteration, in rotation.

### C1. A complete beginner on day one

1. After signing up, the market page points at the first lesson until it is passed.
2. `/learn` opens on a clear "start here" card with the first lesson and how long it takes.
3. The placement test is offered and explained in one sentence.
4. Lesson 1 has a question within its first two sections.
5. Lesson 1 reads in under 3 minutes before the first interaction.
6. A wrong answer is explained and the right one shown; a right one earns XP visibly.
7. The task says exactly what to do and where, and the page where it is done is one click away.
8. Returning from the market, the lesson shows the task done without a reload.
9. Passing lesson 1 is celebrated once (not twice) and the next lesson lights up.
10. XP, the streak and the goal are visible on the path and mean something to a newcomer.
11. The goal is reachable in one sitting but not by two answers.
12. The streak's day is explained (UTC) and does not clash with the game's 30-minute day.
13. Nothing on the path mentions MB, quests, medals or any removed feature.
14. The copy nowhere promises what the page does not do (e.g. "every lesson has a chart test").
15. The phone layout of a lesson and its exercises works at 380 px (buttons full width, no overflow).
16. The chart test inside a lesson is on the lesson's topic.
17. The example chart in a lesson loads and its answer can be shown.
18. Tomorrow has a reason to come back that the page states (goal, streak, daily set, habits).
19. The profile shows the learning record that the path shows.
20. No dead end: every page of the Learn section links back to the path.

### C2. Week two, twenty lessons passed

1. The path shows which units are done, which is next, and how far through the course the player is.
2. Finished units fold; the next lesson is one click.
3. Each of the last five lessons passed had at least one apply-style exercise (a number, a chart, a scenario).
4. No question so far was answerable from its length or position.
5. The chart tests taken were on topic and their explanations taught something beyond "the price went up".
6. The weak-spot card names skills the player actually missed, and the review asks about them with questions the player has not just seen.
7. The coin-flip test never appears as a weak spot.
8. The review pays XP once a day per question and never passes a lesson.
9. The league shows real learners, the player's rank, and resets weekly; nothing in it can be farmed in a minute.
10. Levels are visible and the next one is in reach of a week's work.
11. Habits for the week are shown with progress and reset on Monday.
12. The "Your trading" card reflects trades made this week and links each weakness to a lesson.
13. Tasks completed on the market show up on the lessons that asked for them.
14. Lessons already passed can be reopened and show the answers given.
15. The unit pages have no repeated question across units.
16. The next lesson is never one the placement or review has shown the player knows.
17. Each unit's exercise count is roughly even (no 2-question lessons next to 8-question ones).
18. Nothing in the units 7-16 is still pure recall of one sentence in the text (sample five questions).
19. A unit finishing is celebrated and visible on the profile.
20. The page loads in under a second on the local server and nothing errors in the console.

### C3. A trader who wants it useful

1. "Your trading" exists on the path and shows the last seven days of closes with win rate, average win and loss, profit factor, fees, stop coverage, exits and average R.
2. Each number is explained in one line and linked to the lesson that improves it.
3. The risk lessons show the same numbers inside the lesson with the lesson's slant.
4. A trade closed with a stop appears as "with a stop" and gets an R.
5. The habits cover stops, planned closes, targets and sizing, and the sizing habit uses the actual risk at the stop.
6. Every indicator lesson has a "try it" link that opens a live chart with that indicator on and the right candle size.
7. The orders, bracket, sizing and stop tools on the stock page each link to their lesson.
8. The tasks cover a limit order, a trailing stop, a bracket, an option, a note on a trade, a short with a stop.
9. The journal (notes on trades) is reachable from the lesson that teaches it and from History.
10. The expectancy, R and sizing questions are generated with fresh numbers and graded with a tolerance.
11. The Testing unit's lessons connect to the bots and backtests pages where they exist.
12. The Real markets and Real life units say plainly what carries over from the game and what does not.
13. The glossary is reachable from any lesson and is not a step on the path.
14. Chart tests can be taken on their own, by kind, with a running score and the balance-by-design note.
15. The weak-spot review draws on chart-test kinds as well as units.
16. Nothing in the Learn section pays MB or changes a price.
17. The HOW_IT_WORKS §10.10 description matches what the pages do.
18. The public lesson pages (`/lessons/{id}`) show the questions and tasks as links into the game.
19. A placed player (placement passed units) sees a sensible next lesson, not lesson 1.
20. The tooltips on indicators name their lesson and the link works.
