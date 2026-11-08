# The Learn loop: the rubric (v2, 2026-11-08)

What "right" means for the Learn section (`/learn`), measured the same way every iteration. The loop (`LOOP.md`)
stops when **B passes, every persona in C scores at target, and two iterations in a row find nothing of size S or
larger.** Sizes: S under a day, M a few days, L a week or more (L items go to the ledger as "needs the owner").

v1 (the rubric the first twelve iterations ran against) is in git history. v2 changes the goal: the Learn section
should feel like Duolingo. Placement first and alone on the screen; a path of lessons that opens one by one from
where the placement lands you; a lesson that is a run of short cards (teach, ask, chart, number, do), never a wall
of text; praise and animation for doing well; the free course limited, the full course for Pro and Expert; and a
far wider range of lessons, up to skills experienced traders do not have.

## A. The learner's journey (what the whole thing must do)

1. **Placement first.** A new account's first visit to `/learn` shows one thing: the placement test, with one sentence
   of why and a "Start from the beginning" link under it. No path, no XP panel, no league, nothing else, until it is
   taken or skipped. The placement covers every unit, including the advanced ones, and stops early once the learner
   has missed enough in a row to place them.
2. **Tailored start.** The result places the learner on the path: everything before the landing point is marked
   known, the landing lesson is open, everything after is locked until the lesson before it is finished. The result
   screen says in one line where they landed and why ("You know your charts and orders; we start you at Risk").
3. **The path.** `/learn` is a single path, top to bottom, every unit and lesson visible (known, open, locked). The
   open lesson is the one that stands out and starts with one tap. Finished units fold; the current unit is open.
   The glossary and the chart-test practice page sit beside the path, never on it.
4. **The lesson is a run of cards.** It opens on a goal screen (title, one sentence of what you will be able to do,
   minutes, number of cards). Then one card at a time, moved by Next or by answering: a teach card (at most 70 words,
   often with a chart or a diagram), a question, a chart test, a number to work out, a tap-the-chart, a market task,
   or a try-it link. No more than two teach cards in a row. A progress bar at the top shows how far through the run.
5. **Mistakes come back.** A wrong answer is explained and the right one shown, earns nothing, and the card is asked
   again at the end of the run. The lesson is finished when every card is done and every mistake redone. A right
   answer earns XP at once and visibly.
6. **Praise and animation.** A run of right answers is noticed ("3 in a row", "Perfect so far") with a short CSS
   animation (under a second, no library, honours `prefers-reduced-motion`). The end screen celebrates with an
   animation and shows XP earned, accuracy, time, the streak, and one button: the next lesson. Celebrations are
   earned (a perfect run, a unit finished, a level, the goal, a streak milestone) and never repeat for the same event.
7. **Tailored throughout.** The review asks about the skills missed most, the missed questions first; the habits and
   "Your trading" use the player's own trades; a unit mastered in the placement or the review is skipped by the path's
   next step; the daily goal and streak bring the learner back and say so.
8. **Free, Pro, Expert.** A free player can finish two lessons a day (each a few minutes); the allowance resets at
   the same UTC midnight as the goal and the streak, and the path says so when it runs out ("Two lessons done today.
   Back tomorrow, or Pro for the whole path"). Pro removes the limit for the core and intermediate units; Expert adds
   the advanced units. The placement, the review and the chart-test practice are never limited. A locked lesson is
   visible on the path with its goal and a lock, and opening it shows what the tier unlocks and a link to the shop.
   Nothing in the Learn section costs or pays MB, and nothing moves a price.
9. **Range.** At least 130 lessons in at least 20 units. At least three advanced units (Expert) of at least five
   lessons each that teach what most retail traders never learn: market microstructure and order flow; volatility
   as an asset (implied vs realised, term structure, skew, VIX); second-order options Greeks and dealer positioning
   (gamma, vanna, charm); position sizing under uncertainty (Kelly, fractional Kelly, drawdown maths, Monte Carlo);
   pairs, cointegration and regime detection; execution and market impact (TWAP, VWAP, the square-root law);
   event-driven trading (earnings straddles, post-earnings drift); factor and intermarket analysis; overfitting and
   the deflated Sharpe ratio. Each advanced lesson has at least one exercise that needs a calculation or a chart.
10. **Nothing gameable.** Options shuffled, no position or length bias, wrong answers earn nothing, the review pays
    only for what it served, the league counts people only, the coin-flip test is out of the weak spots.
11. **Power-ups.** Lessons give power-ups as rewards (a perfect run, a unit finished, a streak milestone, the daily
    goal several days running), never for MB. They sit in an inventory on the path and on the stock page, each with
    one line of what it does and how it was earned. The set, to be added to as the loop goes:
    - **Streak freeze**: a missed day does not break the streak (one held at a time, used automatically).
    - **See the future**: on one stock, draws the next five game minutes as faded candles on the live chart, so the
      player can check their analysis before risking anything. They may trade on it. Once used, that player cannot
      trade options for the rest of that game day (the chart's header says so), because a known path makes options
      a certainty. The engine must commit to the path it showed: the preview is the future, not a forecast.
    - **Second look**: redo one wrong card at once instead of at the end of the run.
    - **Chart hint**: one chart test shows the level or pattern it is asking about.
    - **Double XP**: the next lesson pays twice.
    Each power-up is one row in a table in the content or the engine (name, effect, how earned, limits) so the checks
    can read it; using one is a notice; "See the future" is marked on the trade in History.

## B. The automated checks: `python tools/learn_check.py`

Exits 1 when any check fails. The thresholds are the constants at the top of the tool. Rows marked **new** do not
exist yet: the first iterations build them (a check the loop adds counts as that iteration's finding).

| Check | Threshold |
|---|---|
| Every lesson parses | always |
| Every lesson has a goal line (`SUMMARY:`) | always |
| Exercises per lesson | at least 4 (the glossary is a reference) |
| Prose words per lesson | at most 500 |
| **new** Words per teach card (one paragraph or list) | at most 70 |
| **new** Teach cards in a row without an exercise, chart or task between | at most 2 |
| Right answer is the longest option | under 45% of questions, in every unit |
| Near-duplicate questions | none over 85% shared words, across and within lessons |
| **new** Throwaway wrong options ("None", "Nothing", "Never", one or two words) | none |
| Chart lessons (Charts, Indicators, Orders, Strategies, every advanced unit) | each has a `[chart]` or `[test]` |
| `[try]` links | every path a route or `/stock/`, every `?ind=` id and `?tf=` size known to `web/chart.js` |
| `[task]` kinds | each named in `tests/test_learning.py` |
| All units | at least 80% of questions under a section, not after the last heading |
| **new** Tier marker on every unit (`free`, `pro`, `expert`) and the free set as A8 says | always |
| **new** Lessons and units | at least 130 lessons, at least 20 units, at least 3 Expert units of 5 or more lessons |
| **new** Placement covers every unit | `PLACEMENT_UNITS` equals the unit count |
| **new** Advanced lessons apply | every Expert lesson has a `[calc]`, a `= value` question, a `[test]` or a `[chart]` |
| **new** Power-ups defined | every power-up has a name, effect, how earned and limits in one table; every lesson reward names a power-up in it |
| **new** Daily allowance and power-ups tested | `tests/test_learning.py` covers the two-lesson day and its reset, the streak freeze, and "See the future" blocking options for the day and committing the path |

Also every iteration: `python -m unittest test_learning test_drills` (from `tests/`), `node --check web/learn.js`,
and the inline script of `web/index.html` parsed with node.

## C. The simulated learners: three walkthroughs, 20 points each, target 18

Run as an Explore agent (read-only; GET requests to the local server allowed, and the POSTs needed to register a
test account, take the placement and answer cards) with the checklist below verbatim. It answers each point yes or
no with a file:line, then lists its findings ranked by size with the fix it would make. One persona per iteration,
in rotation.

### C1. A complete beginner on day one

1. The first visit to `/learn` shows only the placement test and a "Start from the beginning" link, nothing else.
2. The placement is explained in one sentence and takes under five minutes; it stops early once the beginner has missed enough.
3. The result says in one line where they landed and why, and the path opens there with one button.
4. Skipping the placement lands on lesson 1 with the same one-button start.
5. The path shows every lesson as known, open or locked; only one lesson is open.
6. Lesson 1 opens on a goal screen: what you will be able to do, minutes, cards.
7. No card in lesson 1 is over 70 words; no more than two teach cards in a row.
8. The first question comes within the first three cards.
9. A wrong answer is explained, earns nothing, and comes back at the end of the run.
10. A right answer earns XP visibly at once; three right in a row is praised with an animation.
11. The end screen celebrates with an animation, shows XP, accuracy and the streak, and has one button: the next lesson.
12. The next lesson is unlocked only when this one is finished (every card done, mistakes redone).
13. The market task says exactly what to do and where; the page is one click away; coming back shows it done without a reload.
14. XP, the streak and the goal appear on the path after the first lesson and mean something to a newcomer (one line each).
15. Nothing on the path mentions MB, quests, medals or any removed feature; no copy promises what the page does not do.
16. The phone layout at 380 px: one card fills the screen, buttons full width, no horizontal scroll.
17. The animations are short, CSS only, and off under `prefers-reduced-motion`.
18. After two lessons the path says the day's free lessons are done, when they reset, and what Pro unlocks, with the shop one tap away; the review and chart practice still work.
19. Tomorrow has a stated reason to come back (goal, streak, habits, a power-up to earn) and the profile shows the same record the path shows.
20. No dead end: every screen of the Learn section has a way back to the path.

### C2. Week two, placed at Risk, Pro subscriber, twenty lessons done

1. The path shows the units the placement marked known, the current unit open, the rest locked, and the share of the course done.
2. The path's next lesson skips any unit the review has shown mastered and never points at a lesson waiting only on a task.
3. Each of the last five lessons had at least two exercise kinds (question, chart test, number, tap-the-chart, task).
4. No question was answerable from its length, position or a throwaway wrong option.
5. The chart tests taken were on the lesson's topic and their explanations taught something beyond "the price went up".
6. The weak-spot card names skills actually missed; the review serves the missed questions first, none seen that day.
7. The coin-flip test never appears as a weak spot; the Start unit's site questions do not count as a skill.
8. The review pays XP only for the questions it served, once a day each, and never finishes a lesson.
9. The league shows people only, the player's rank, resets weekly, and random clicking cannot climb it (wrong answers earn nothing).
10. Levels are visible and the next one is in reach of a week's work.
11. Habits for the week are shown with progress and reset on Monday; "Your trading" uses the same week.
12. "Your trading" reflects this week's trades, says what each number means in one line, and links each weakness to a lesson.
13. Tasks completed on the market show up on the lessons that asked for them.
14. A finished lesson can be reopened as a recap: the cards and the player's own answers, nothing re-earned.
15. No question is repeated within a lesson or across units.
16. A perfect run or a unit finished gave a power-up; the inventory shows it with one line of what it does; a streak freeze saved a missed day without a click.
17. Nothing in units 7 onward is pure recall of one sentence of the text (sample five questions).
18. A unit finished is celebrated once and visible on the profile; a perfect run is celebrated separately.
19. Pro removed the daily limit; the Expert units show their goals and a lock with what Expert adds.
20. `/learn` and a lesson load in under a second on the local server, and nothing errors in the console.

### C3. An experienced trader with Expert, looking for what they do not know

1. The placement recognises experience: a trader who knows charts, orders, risk and options is placed at or past the intermediate units in under five minutes.
2. At least three Expert units exist with at least five lessons each, on the topics A9 names.
3. Every Expert lesson has an exercise that needs a calculation or a chart, graded with a tolerance where it is a number.
4. The Expert lessons teach something a trader of five years would not already know (sample three; name the thing).
5. The advanced maths (Kelly, drawdown, Monte Carlo, deflated Sharpe) is right, with a worked example on a card.
6. The options Greeks lessons connect to the game's options chain where it shows the numbers they teach.
7. "Your trading" shows win rate, average win and loss, profit factor, fees, stop coverage, exits and average R, each labelled with its window.
8. A trade closed with a stop appears as "with a stop" and gets an R; cancelling the stop or adding to the position updates both.
9. The sizing habit uses the actual risk at the stop and matches the rule the lessons teach.
10. Every indicator lesson has a try-it link that opens a live chart with that indicator on and the right candle size.
11. The orders, bracket, sizing and stop tools on the stock page each link to their lesson, and the indicator tooltips do too.
12. "See the future" draws five game minutes of faded candles that the market then follows exactly; the trade on it is marked in History; options are blocked for that player until the game day ends, and the header says so.
13. The Testing unit's lessons connect to the bots and backtests pages; the Real markets and Real life units say what carries over and what does not.
14. Power-ups cannot be bought with MB, stacked past their limits, or used through the API after their limit; "See the future" works on one stock at a time.
15. The glossary is reachable from any lesson and is not a step on the path.
16. Nothing in the Learn section pays MB or changes a price; Expert is a subscription, not a purchase of answers.
17. The HOW_IT_WORKS §10.10 description and the `learning.py` header docstring match what the pages do.
18. The public lesson pages (`/lessons/{id}`) render every lesson (no 500s), show the goal and the cards' questions as links into the game, and mark the tier.
19. The lesson content never overclaims about the game's realism (prices, fills, spreads) and says when the game simplifies.
20. Nothing is gameable through the API: wrong answers, replayed reviews, bots and the coin-flip test all earn nothing.
