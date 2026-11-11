# Meme Street roadmap

**Goal:** an informational game where people **learn to trade, or just trade for fun**, on a realistic, fictional
stock market. **Technical analysis is the core** (charts that behave like real charts, and the tools to read them);
news and the economy are background. The market drifts slowly upwards, with corrections, bear phases and sideways
stretches, and prices respect and break support and resistance the way real charts do. Everyone starts with
**1,000 MB**; MB are a game currency with no cash value, never paid out. The site earns from **MB packages** and
**Pro and Expert passes** (monthly or yearly). **The Daily Chart** is the daily reason to come back and the thing
people share. From this phase on, the course is a **path** (units, exercises, XP, a streak), and the site builds a
**bridge to real markets**: real delayed charts to practise on, and an honest page about going live.

Companion doc: `HOW_IT_WORKS.md` describes what the code does **today**. Update it after every change, and check this
file before starting any work. Size key: **S** = under a day, **M** = a few days, **L** = a week or more.

*Rewritten 2026-11-07 after a review of the site through three players' eyes (section 3). Finished and dropped work
is reduced to a "done" line per track (the IDs stay, since the code and HOW_IT_WORKS refer to them). The earlier
rewrite was 2026-10-24; the plan before 2026-10-13 (a real-money game) is gone.*

---

## 1. Design rules

1. **Realism you can learn from.** Behaviour real markets show appears at realistic rates: a support level holds often
   enough to be worth trading and breaks often enough that a stop is needed.
2. **No free money.** No simple, unskilled rule (buy everything, buy every dip, always fade, doubling down, shorting
   everything, selling every option) may beat holding the index by a wide margin, costs included. Skill shows as better
   *risk-adjusted* results over many trades, never as a guaranteed win. Checked by `tools/realism.py` and
   `tools/option_check.py`.
3. **Players' trades never move prices.** The market is the same for everyone, and a big account cannot push it.
4. **Paying never buys a rank.** The return boards rank return on money put in, so buying MB gives more capital to
   practise with, not a better place. (The profit boards and leverage bend this: section 6, risks 4 and 11.)
5. **Honest selling.** Prices are shown before every purchase, MB are clearly worthless outside the site, there is no
   purchase prompt at the moment of a loss, and there are spending limits.
6. **Every MB is accounted for.** Every money event is in the ledger with its source (start, purchase, reward, refund,
   admin); `total_tokens == minted` always.
7. **One meaning per word.** One daily game (the Daily Chart), one learning streak, one badge system. Nothing on the
   profile that pays nothing and teaches nothing.

---

## 2. Where things stand (7 November 2026)

**Live on https://memestreet.net** (one Hetzner server, Caddy, a game server and two gateways, fail2ban, the admin
pages behind a second password). **The shop takes real money**: Stripe Checkout through *Managed Payments*, purchases
credited within a second by a signed webhook, a payment check four times a day. **Email is live** (O1 done: sign-up
needs a 6-digit code sent by mail since 2026-10-31, so passwords can be reset and receipts and reminders can go out).
Backups every six hours on the server, copied to this computer every day; `/api/health` checked every 15 minutes.
Since 24 October: visitors play the Daily Chart without an account and signing up afterwards keeps the game (TA-D5,
2026-11-01); the 96 lessons are public server pages at `/lessons` with a sitemap and daily SEO runs (B10 in part,
2026-11-07); an admin Daily tab; 72 house bots that trade and play the Daily like people.

| Area | Built | Open |
|---|---|---|
| The market | Drift, regimes, trends in legs, ranges and breakouts, support and resistance of many kinds, volume that confirms, wicks, engulfing turns, squeezes, gaps, ten named chart patterns, volatility clustering and fat tails, sessions, IPOs and takeovers; 157 content listings in 30 sectors, the MSI 50 by market value; realism and no-free-money checks | P15 more companies and industries, P10 asset classes, P8, P9, P12, P13 |
| Charts and trading | Crosshair, five chart types, log scale, 49 indicators with saved settings, 16 drawing tools saved on the server, trades and orders on the chart, 2,000 candles in every timeframe; options (buy-only) for everyone, leverage up to 10x (Pro), trading bots and single-ticker backtests (Expert) with a guide | U11 beginner fixes, TA-B5, TA-B7, TA-B8, TA-B10, TA-B11, TA-B12, T14 writing options and spreads, T15 bots next |
| The Daily Chart | A numbered mystery chart a day, the same for everyone, playable without an account; two minutes, one go; streaks, stats, a result grid, sharing as text and as a story picture; the levels the chart tested | TA-D6 to TA-D12 |
| Learning | A 96-lesson course in 17 tracks, eleven kinds of chart test on real charts, a glossary, public lesson pages; "read" means "opened", nothing is checked | LP1 to LP8 (the learning path) |
| Community | 72 house bots; four leaderboards; chat with moderation, follows, public profiles; badges (the daily contest, daily quests and the quest ladder were removed 2026-11-07) | S1-S4, TA-D7 |
| Money | 1,000 MB start, MB by source, five packages, the New Launch Deal, Pro and Expert monthly or yearly, refunds, spending limits, the free restart, tracking and invite links | M10 shop fixes, M11 trial, M12 things MB buy, M13 funnel, M4, M8, M9, B5, B6 |
| Real markets | Nothing yet: no real tickers, data or broker anywhere in the code | RM1 to RM6 |
| Rules | Terms and privacy (24 October 2026), a date of birth at sign-up, the right-to-cancel waiver, email verification | R4, R5, R7-R10 |
| Running it | Staging, rollback, backups off the server, uptime check, CI with lint and types, an error tracker, capacity measured (about 1,000 players at once), email | O4, O8, O11, E2, E5, E6, E9, E11, E14 |

**Still open from the launch list (yours):** G2 test inside Instagram's browser on a phone, G3 the old 10,000-MB
accounts (O11), G4 and R9 who runs the site, G5 ad wording, G6 phone alerts (UptimeRobot), G7 chat moderators, G8
watch disputes and the spending limit (R5). G1 (email) is done.

---

## 3. What a user finds today (review of 7 November 2026)

The site read through the code and the live pages as three players would. Each point names the item that fixes it.

**A new trader, first five minutes**

- Lands on a table of 180 tickers, not a chart or a lesson; after a five-field sign-up nothing is guided (TA-B12, LP1).
- Five different "daily" things (Day return, "Day N ends in", Daily Chart, Daily quests, Daily contest) and two
  streaks that are not the Daily's (U10).
- The leverage select is shown to a free player and only refuses on Buy; the default chart is 30-second candles; Sell
  turns into Short with nothing held and no warning; "beta", "annual volatility" and "bank rating" are unexplained on
  every stock; there is no way to size an order in shares (U11).
- A lesson counts as "read" when opened; the first-trade task is a link nothing checks; the chart tests sit above the
  course on `/learn`; 10 of 17 tracks have no exercise at all (LP1, LP2, LP4).
- On a phone, a visitor off the Market page has no sign-up button (U11).
- After the Daily, an account holder gets Share and Story picture and nothing else; the Daily is missing from the menu
  and the profile (TA-D10, TA-D11).

**An intermediate trader**

- Has candles, five chart types, 17 free indicators, drawings, limit, stop, take-profit and bracket orders, a risk
  sizer, calls and puts with Greeks, shorting.
- Cannot place a trailing stop or a stop-limit, trade from the chart (TA-B5), set an alert (TA-B7), write an option or
  trade a spread (T14), keep a journal (U11), or use MACD, Bollinger, VWAP and ATR without Pro (M11, a trial).

**An experienced trader**

- Has Expert bots and single-ticker backtests, a history CSV, an equity curve, today's drawdown.
- Missing: a screener (TA-B8), multi-chart (TA-B10), replay (TA-B11), alerts, a journal, any risk-adjusted statistic
  (no Sharpe anywhere), walk-forward tests, parameter sweeps, portfolio backtests, sharing bots (T15), real charts (RM).

**The shop**

- An Expert purchase thanks the buyer for "0 MB"; visitors cannot see prices; "buying MB never lifts your rank" is
  false for the two profit boards (M10). MB buy nothing but capital, and the free restart covers running out, so the
  passes carry the revenue (M11, M12). Shop views, buy-box opens and checkout starts are not counted (M13).

**The docs**

- HOW_IT_WORKS still says visitors must sign up for the Daily (§10.13), counts 31 derived assets in §8 and 32 in §9,
  used 10,000 for the contest balance and said sector shocks come every 600 s. The first three were fixed with U10 (2026-11-07); the sector-shock
  line waits for P12 (E9).

---

## 4. Suggested order

| Phase | Focus | Items | Done when |
|---|---|---|---|
| 1 (done 2026-11-07, local only until deployed) | **The cut and the quick fixes** | U10, U11, M10, TA-D10, TA-D11, the doc fixes | One daily thing, a cleaner profile, a Daily that leads somewhere, prices visible to visitors |
| 2 (done 2026-11-07, local only until deployed) | **The learning path** | LP1 to LP8 | A newcomer passes unit 1 by doing its exercises and placing a stopped trade; a learning streak |
| 3 (about two weeks) | **The Daily as the hook** | TA-D6, TA-D7, TA-D8, TA-D9, M11, M13 | Archive, friends, badges, the reminder mail; a Pro trial started from a locked tool |
| 4 (about two weeks) | **Real markets, part 1** | RM1, RM2, RM3, RM5 (without broker links) | Real delayed charts to read, test on and backtest on |
| 5 (about two weeks) | **Trading depth** | T14, T15, TA-B7 | A Pro sells a covered call and a vertical as one order; an Expert runs a walk-forward test and gets a rule alert |
| 6 (about two weeks) | **Breadth and the chart home** | P15, TA-B12, TA-B5, TA-B8, M12 | About 220 companies in 38 sectors; trade from the chart; a screener; things to spend MB on |
| 7 | **Real markets, part 2** | RM4, RM6, P10 | The Real Daily; exportable alerts; bonds, gold and oil that behave like themselves |
| Alongside | **Running it** | E2, E5, E6, E9, E11, E14, O4, O8, R5, R7, R10, X2, X7 | |

---

## 5. Tracks: what is open

### TA-D. Playing for fun, and the Daily Chart

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-D2 | Weekly competitions and leagues | Light, social goals keep people coming back. | Weekly events ranked on return on money put in and risk-adjusted return, leagues by level, small capped MB prizes. | M |
| TA-D3 | Share a chart | Explaining a trade idea is fun and teaches. | Share a chart with drawings in chat or by link. | M |
| TA-D6 | Past charts | Wordle's archive keeps people playing between days. | Keep every finished chart (its candles and levels) in `daily_game["archive"]`; a practice replay kept apart from plays and stats; a list page with each day's winner. The chart must be stored, not regenerated: a code change would alter old charts. | S |
| TA-D7 | Friends and groups | Beating friends is the strongest daily pull. | Today's results of the people you follow next to yours (`_daily_board` filtered by `p.following`); later a group code (a class, a group chat) with its own daily and weekly board. | S, then M |
| TA-D8 | Streak and result badges | Small rewards for coming back. | Badges for 7, 30 and 100-day streaks, a first place, beating the stock five days running; entries in `ACHIEVEMENTS` (`social.py`), a Daily row on the profile. | S |
| TA-D9 | A reminder | "The new chart is out" brings people back. | **The email is done (2026-11-10):** opt-in from the Daily result, a confirmed address only, one a day when the new chart starts from "Meme Street Game", at most 70 a day, one-click unsubscribe. Browser notifications later (they need a service worker). | S |
| TA-D12 | A Real Daily | The same game on a real chart teaches that the skill carries over. | Once RM1 exists: an unnamed real ticker and period from the real-candle archive, revealed at the end. Its own board. | M |

Done: **TA-D1** no homework. **TA-D4** the Daily Chart (2026-10-23; relaunched 2026-10-24; more technical 2026-10-26).
**TA-D5** play without an account (2026-11-01: a visitor plays in the browser, three games a day per address; signing
up afterwards puts the game on the board and starts the streak; HOW_IT_WORKS §10.13). **TA-D10** the result card's next step (2026-11-07: the best single trade on offer, the levels open by default, the matching lesson and "Trade a live stock"). **TA-D11** the Daily in the menu and the player's Daily record on the profile and public profile (2026-11-07).

### LP. The learning path (new track, 2026-11-07)

Replaces the open TA-C5, TA-C7, L8 and L11 and the dormant challenges. The course stays free and browsable; the path
adds order, exercises, XP and a streak. No MB is paid for learning (XP instead) unless decided otherwise (section 7).

| # | Change | Why | How | Size |
|---|---|---|---|---|

Done: **LP16** the Learn loop (2026-11-08: `docs/learn-loop/` with the rubric, the iteration prompt and the ledger, and `tools/learn_check.py`; the loop fixes one finding an iteration and commits locally until the rubric passes or 12 iterations). **LP15** better exercises (2026-11-08: number and generated-calculation questions, chart tests narrowed to the lesson, charts in the eleven chart lessons that had none, duplicates cut, a scenario question for each thin core lesson, the Start unit interleaved; the rest of the six core units' hand rewrite, the which-chart and place-the-stop formats and the Bollinger and VWAP overlays are still to do). **LP14** enjoyable (2026-11-08: XP levels, streak, goal and level-up notices, a chosen daily goal, finished units fold, a course percentage, a unit-finished notice, exercises one at a time). **LP10** your trading on the path and in the risk lessons, **LP11** this week's habits for XP (the challenges, back on, no MB), **LP12** apply-it-now links that open a chart with the taught indicators on, **LP13** five more market tasks (all 2026-11-07). **LP9** fairness (2026-11-07: shuffled options, the coin-flip test out of the review, review XP once a day, answers shown again, questions before tasks, the glossary a reference, closes, stops, exit reasons and R recorded for LP10). **LP5** the weak-skill review, **LP7** this week's learners (an XP league, no MB) and **LP8** tooltips linking indicators and the ticket to their lessons (all 2026-11-07). **LP6** the placement test (2026-11-07: twelve questions, one per unit in order; the units known in a row are marked passed and the path starts at the first missed). **LP1 to LP4** (2026-11-07): the path (units in order, the next lesson, lessons passed when their exercises are done), exercises in every lesson (the 236 questions back as the pass check, 14 chart tests, 6 market tasks), XP with a daily goal and one learning streak, and the tasks checked by the engine on the live market; the learning record on the profiles. **The course rebuilt** (2026-10-27): 17 tracks and 96 lessons, **TA-C1** curriculum, **TA-C2** example charts
from the game's own history, **TA-C3** and **TA-C4** eleven kinds of chart test, a glossary, **L10** the lesson files
checked by a test; **B10 in part**: public lesson pages (2026-11-07, `lessonpages.py`). Folded into LP: **TA-C5** the
coach (LP4 and TA-D10 give rule-based feedback), **TA-C7** tooltips (LP8), **L8** onboarding (LP1 and LP4), **L11**
more chart tests (LP2). Dropped or earlier: the twelve old lessons; **L3** challenges (off since 2026-10-23, retired by
LP4); the quest ladder (U10); **L4** journal (returns in its simplest form under U11) and **TA-C6**; **L5**.

### TA-B and U. Charts, trading tools and the interface

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-B5 | Trade from the chart | Entry, stop and target belong on the chart. | Drag lines for entry, stop and target; the risk-reward ratio and the size for the chosen risk update as you drag; one click places the order and its bracket. | M |
| TA-B7 | Alerts | Waiting for a setup should not mean staring. | When the price crosses a drawn line or a bot rule is true (T15's "alert" action); in the page, and by email. Shared with RM6. | M |
| TA-B8 | A setup screener | Finding setups is a skill to practise. | Stocks near strong levels, breakouts on volume, squeezes, RSI extremes and divergences, gaps, new highs and lows, named patterns. | M |
| TA-B10 | Multi-chart layouts | Setups are read across timeframes and against the index. | Two or four charts, linked timeframes, an index or sector overlay, relative strength. | M |
| TA-B11 | Replay mode | Practising on the past, bar by bar, is the best teacher. | Pick a stock and a past period, step through it and trade it in a practice account (needs E5). | L |
| TA-B12 | The chart as the home screen | Most players should land on a chart, not a table. | The chart in the middle, a watchlist, the order ticket and positions; the market table stays as "all stocks". | M |
| U1 | Phone, second step | Ad traffic is almost all phones. | A pull-up trade ticket, an installable web app, a check on real phones. The installable part is built (2026-11-11, `/manifest.json`, not live). | M |
| U2 | Notifications | Messages vanish after a few seconds. | A list, sounds, browser notifications for fills, alerts and the Daily Chart. | S |
| U3 | "While you were away" | Coming back should show what happened. | Equity change, fills, news on holdings. | S |
| U5 | Accessibility and a light theme | Wider reach. | Arrows beside colours, keyboard shortcuts, a light theme, translations. | M |
| U6 | Market overview | Seeing the whole market is a skill. | A heatmap; the MSI 50 page with its holdings exists. | M |
| U7 | Low-data mode | A stock page used to cost about 18 MB an hour. | Pause when hidden, send only what is visible. | S |

Done: **U10** the cut (2026-11-07: daily quests, the quest ladder, the daily contest and medals removed; achievements are **Badges**; the header says **Today** and **Session N ends in**). **U11** beginner fixes (2026-11-07: the leverage select only for Pro with a lock chip for the rest, 5-minute candles by default, a shares box, a trailing stop order, the first accidental short asks once, the stock subtitle in plain words with a tooltip, a sign-up button for phone visitors on every page, a note per trade on the History page). **U12** the menu (2026-11-08: seven tabs, Market, Learn, Daily, Portfolio with Holdings · Overview · History chips, Leaders, Social, Profile with a Bots chip; the Shop a header button; on a phone a bar fixed to the bottom with a More sheet; the concept explanations cut from the pages with a `?` to the lesson in their place; the holdings table without its Dividends column; the account first on the profile; a second pass the same day: a delisted stock's price no longer reads "MB MB", a strip lights one chip, the phone header is two short rows with no Daily button, notes sit above the toast, the calendar's releases table fits a phone, the chart's mouse hint and the shop's self-opening deal pop-up are gone). **TA-B1** crosshair, **TA-B2** chart types and log scale, **TA-B3** 49 indicators with settings, **TA-B4**
drawing tools saved on the server, **TA-B6** trades on the chart, **TA-B9** what Pro includes (decided), **TA-A10**
longer history and 2,000 candles a chart (2026-10-24); **T10** options for everyone, **T11** leverage (Pro), **T12**
trading bots (Expert) and their guide at `/bots/guide`, **T13** backtests. T1-T9 were done or moved into the TA-B
items. **S5** streaks (the Daily Chart's), **U8** a consistent look, **U9** the trading-terminal look, visual passes
over every page (2026-10-23).

### T. Options, bots and backtests (new items 2026-11-07)

| # | Change | Why | How | Size |
|---|---|---|---|---|
| T14 | Writing options and spreads (Pro) | Buy-only options teach half the subject; covered calls and spreads are what most real option traders do. | Sell to open: a covered call (shares held, nothing reserved), a cash-secured put (cash reserved), a naked option with margin (the premium plus the larger of 20% of the underlying less the out-of-the-money amount and 10% of the underlying, marked every tick, liquidated like leverage). Assignment is cash settlement at expiry (European stays). Spreads as one order: vertical, straddle, strangle, iron condor, with net premium and net margin; the payoff chart covers the whole position; the chain gets a sell side and a strategy builder. `option_check.py` gains short straddles, covered calls and credit spreads: selling volatility must not beat holding the index after spread, fee and jump risk (the 15% variance premium is the risk; tune the spread or the premium if it does). | L |
| T15 | Bots and backtests, next | Single-ticker backtests with no risk-adjusted numbers teach overfitting. | Sharpe, Sortino, CAGR, time in market and a benchmark line in the report (S). A walk-forward split, 70/30 or rolling windows, both results shown (S). A parameter sweep over one or two numbers, at most 50 runs, one job at a time in the worker thread, a heatmap (M). A portfolio backtest across the bot's tickers with shared cash (M). A stop and target per rule, partial closes (S). Share a bot by public link (copies `clean_bot` JSON) and a bot board by live return (S-M). An "alert" action that notifies instead of trading (TA-B7). Export bot JSON (RM6). `run_backtest` is already pure (candles in, report out), so all of this fits. **Not planned:** Python bots; sandboxing user code on the one game server is not worth it. | M overall |

Options later, if wanted: limit orders on options, implied-volatility history, options on the MSI 50 and the ETFs.

### RM. The bridge to real markets (new track, 2026-11-07)

The market stays fictional (rule 3). Real data enters as **delayed real charts to practise on**, never as something
to trade for money, and the site says so on every real-chart page.

| # | Change | Why | How | Size |
|---|---|---|---|---|
| RM1 | Real candles | Everything else in this track needs them. | A licensed source for about 100 real tickers, daily and hourly, delayed. Stooq and Yahoo do not allow redistribution on a public site, so the candidates are tiers with display rights (Twelve Data, EODHD, Alpha Vantage, Tiingo, Polygon). `tools/real_import.py` writes `data/real.db` in the same `(tk,t,o,h,l,c,v)` shape as `history.db`; `GET /api/real/{tk}/candles`. **Decision: the source and its monthly cost.** | S once decided |
| RM2 | Real charts page | Reading a real chart with the same tools shows the skill carries over. | `chart.js` over real candles with indicators and drawings; the eleven chart tests on real charts (the drills take any candle list). Marked "real market, delayed, practice money". | M |
| RM3 | Backtests on real candles | An Expert's rule tested on a real history is a real result. | `run_backtest` with real rows and a real risk-free rate for options. | S |
| RM4 | The Real Daily | See TA-D12. | | M |
| RM5 | "Ready for real money?" | The honest end of the course. | A readiness checklist from the player's own record (trades, share with a stop, worst drawdown, months of consistency, units passed), what carries over (from the *From game to real life* track), how to choose a broker. **Broker links only after R10:** affiliate links to brokers are financial promotions in the UK and EU and may need an approved firm; the first version has no links. | S-M |
| RM6 | Export your tools | An experienced player wants their rules on real tickers. | Download bot JSON and alert rules; `tools/real_alerts.py` evaluates them on the player's own computer against free delayed quotes (personal use, where Stooq and Yahoo are fine). | S |

### P and TA-A. The market

| # | Change | Why | How | Size |
|---|---|---|---|---|
| P15 | More companies and industries | 157 listings in 30 sectors, seven of them with only two members; the IPOs add variety but not breadth. | A new pack `content/pack_depth.json` of about 60 companies: fill the two-member sectors to four and add eight industries (semiconductors, banks split from finance, insurance, shipping and logistics, luxury, gaming, biotech split from pharma, food and drink). Each new sector needs rows in `newsgen.PRODUCTS` and `IPO_SECTORS`, `relations.SUPPLY` and `RIVAL_CROSS`, and the growth and rates tilts in `market_model.py`; sector indices appear by themselves. Raise `max_companies` to 260. Measure the tick with `tests/capacity.py` before and after (54-65 ms at 193 listings today); the market table may need virtual rows past about 250. | M |
| P10 | Asset classes that behave like themselves | Bonds, gold, oil and defensives teach different lessons. | Bonds fall when rates rise, gold reacts to real rates and fear, defensives hold up in bear phases; factors for rates, oil and the dollar with an exposure per listing (P9 in small steps). The realism suite must pass after each. | M |
| P8 | Market psychology | Real markets overreact, panic and chase. | Overreactions that partly retrace, "buy the rumour, sell the news", short squeezes when short interest is high, stop runs past obvious levels; each at a measured rate, checked for free money. | L |
| P9 | Factors and correlations | One market factor plus sectors is too simple for macro to matter. | Risk-on/off and correlations that rise in sell-offs, on top of P10's factors. | L |
| P12 | Retire what conflicts | Leftovers of the old zero-drift market. | The hidden mood, two-outcome catalysts and distress bets, kept only where they fit; moonshots, sector shocks and catalysts are already switched off in `base.json`. | M |
| P13 | A gentler market for beginners | Beginners may want calmer conditions. | A second, calmer market for the first units, or a difficulty setting. Later. | M |

Done: **P1-P7**, **P11** the realism and no-free-money suite, **P14** IPOs and takeovers (2026-10-24), **TA-A1 to
TA-A9**, **TA-A11** game-time candles (built, then taken out on request). Volatility checked 2026-10-24.

### TA-E and N. News and the economy

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-E4 | "Why it moved", technical first | Players should learn to explain moves from the chart. | Each stock page says what happened in chart terms, with a headline only when there was one (was N7). | M |
| N8-N10 | Parked | They add news, not chart skill. | Better company stories, a daily wrap written around the chart, LLM headlines. | M |

Done: **TA-E1 to TA-E3**, **N1-N6**.

### M and B. Money and growth

**Growth plan (2026-11-10):** [GROWTH_PLAN.md](GROWTH_PLAN.md), the owner-approved plan to get players, with no spending. Done on 10 Nov: an account without the emailed-code wall (`signup_verify` off; the address is confirmed later on the Profile), *Play today's chart* first in the home page's intro box, `/play` for the reels, a visitor's Daily result before the save box, *beat my score* links, the first unit outside the free day, house bots flagged in the data (no visible tag: the owner's call), boards and player pages open to visitors, the Daily reminder email (TA-D9), and the visit log (`deploy/Caddyfile`, on since 10 Nov) with `game/visitlog.py`, `tools/visits.py`, the admin page's *Visitors from Instagram* and the privacy page. Still open from it: G2 (the sign-up tried on a phone inside Instagram's browser), TA-D8, TA-D7, B5, one password box with a *show* switch, and the reel changes in `growth/reel-brief.md` for the reels chat. The posting schedule stays as it is (owner, 10 Nov).

**Reach plan (2026-11-11):** [REACH_PLAN.md](REACH_PLAN.md), the owner-approved plan for more reel views (A1 to A11, in `tools/memestreet_daily_reel`) and more people on the site (P1 to P5 and every free channel), still with no spending; its *Progress* table says what is done. Built on 11 Nov on the owner's computer, and waiting for the owner's word to be committed and put live: a challenge link's own preview title (P1), the Daily in a frame (B11), `/llms.txt` and IndexNow (B12), the load check (B13, run on staging), the web app manifest (the installable part of U1), six comparison pages at `/vs` (`game/vspages.py`), the Daily as one file for game portals (`tools/portal_build.py`, `growth/portals/`), and the reel changes A2 to A11, which the owner watches in one full render before the timer uses them. Drafted for the owner to send: the directory texts, the launch posts, the write-up, the lesson plan and the cross-posting steps (all in `growth/`). Still the owner's: A1 (the Account Status screenshot), the platform sign-ups and keys, Bing Webmaster Tools, the portal uploads, a check of each comparison page against the other site, and the yes for the live Caddy change. `docs/HOW_IT_WORKS.md` has what each piece does (the reach plan block at the end of section 10).

| # | Change | Why | How | Size |
|---|---|---|---|---|
| M11 | A Pro trial | The locked-tool moments are the real upsell; a taste sells better than a lock. | Seven days of Pro, started at sign-up or the first time a Pro tool is tapped, then the normal price; once per account; Stripe's trial on the monthly pass or a flag in the game. | S-M |
| M12 | Things MB can buy | MB buy nothing but capital, so there is little reason to buy them. | Name colours and a title (the ladder's cosmetics, repurposed), chart themes, a custom Daily share card, an extra practice go of the Daily (not on the board), gifting MB to a friend. All through the ledger with their own source. | M |
| M13 | The funnel | Know what the ads bring. | Count shop views, buy-box opens and checkout starts; buyers per 1,000 sign-ups, spend per buyer, out-of-money to purchase, cohorts by week on the admin page (the rest of B4). | S |
| M4 | When an account runs out | The moment a player busts teaches the most and is the least fair time to sell. | A page that shows what happened (the biggest losses, the risk taken, the risk units) with the options; today a red banner offers the free restart, the shop and the lessons. | S |
| M8 | Trading costs that teach | Costs decide whether a pattern pays. | Keep 0.1% a side, or a commission and a spread that widens in thin and fast markets; checked with the realism suite. | M |
| M9 | Simplify the house | Nobody is paid out, so the house carries no risk. | Retire the capital rule, reserve floors, top-ups and alarms; the house-risk panel becomes "where players are positioned". | S |
| B5 | Referral rewards | Word of mouth. | Invite links and counts exist (2026-10-27); next, a capped MB reward for both once the friend verifies and plays. | S |
| B6 | Email that brings people back | Value, not spam. | Welcome, a weekly review, the Daily reminder (TA-D9), receipts, an unsubscribe link. | M |
| B7 | Community | Somewhere to talk and announce. | A Discord or Instagram broadcast channel with the daily winners. | S |
| B8 | Teachers and creators | Each brings a group. | Classrooms (S1) with a free trial, a creator programme. | M |
| B9 | Name and brand | "Meme Street" was chosen for a meme-stock game. | Keep it or rename for a teaching audience. Your decision. | S |
| B10 | Pages people can find | A teaching site grows through search. | Public lesson pages done (2026-11-07); next share cards for stocks and results, the exercises linked from the lesson pages (LP8). | S |
| B11 | The Daily inside a frame | itch.io, blogs and teachers can only show the Daily if another site may frame it. | `/embed/daily`: for that path only, `deploy/Caddyfile` drops `X-Frame-Options` and names the allowed hosts in `frame-ancestors`; first check on staging how a visitor's game survives inside a frame (REACH_PLAN P2). Built 2026-11-11, not live: the Caddy rule waits for the owner's yes. | S |
| B12 | Found by Bing and AI search | Google is not the only door. | `/llms.txt`, an IndexNow key route with a ping from the SEO deploy, Bing Webmaster Tools (the owner verifies the site) (REACH_PLAN P4). Built 2026-11-11, not live; Bing Webmaster Tools is the owner's. | S |
| B13 | A load check before a launch day | A front-page day must not take the site down. | A short script against staging: many visitors opening the Daily at once (REACH_PLAN P5). Built and run 2026-11-11 (`tools/load_check.py`): 200 visitors, 5,000 requests, none failed. | S |

Done: **M10** shop fixes (2026-11-07: the Expert thank-you, visitors see the shop and its prices with a sign-up button, the rank claim now says "the return boards"). **M1** 1,000 MB start, **M2** MB by source, **M3** the shop (live 2026-10-24), **M5** challenge rewards (off),
**M6** spending limits, **M7** the pricing model, **B1** package prices, **B2/B3** Pro and Expert prices, **B4**
tracking links (the rest is M13).

### S. Community

| # | Change | Why | How | Size |
|---|---|---|---|---|
| S1 | Classrooms | Teachers and clubs are natural buyers. | A teacher account, a class with a join code, assigned units, a class board and progress. | L |
| S2 | Boards that reward skill | Raw returns reward luck and leverage. | A risk-adjusted or consistency board, leagues by level, leverage counted or capped (risk 4). | S |
| S3 | Challenge weeks | Replaces the daily contest (removed by U10). | Weekly themed events with the same starting balance and a skill objective. | M |
| S4 | Sharing ideas | Explaining a trade is learning. | A trade idea (a chart with levels and a plan) shared with followers, delayed; a room per stock. | M |

### E and O. Engineering and running the site

| # | Change | Why | How | Size |
|---|---|---|---|---|
| E2 | Split `engine.py` | It is hard to change safely. | Modules for prices, news, orders, accounts, indices. | L |
| E5 | Determinism and replay | Calibration, replay (TA-B11) and bug reports need repeatable markets. | A seeded random stream per market and a tool that replays any period. | M |
| E6 | Observability | Problems are seen only on the dashboard. | Structured logs, metrics, alerts for late ticks and errors. | M |
| E7 | Content tooling | Packs are edited by hand; P15 adds a big one. | A validator and a preview for content packs. | S |
| E9 | Rough edges | Small things add up. | Sparklines reset on restart, the news wire is not saved, content files are checked every tick, the four HOW_IT_WORKS mismatches in section 3. | S |
| E10 | Scale the game server | The market is one process. | Only when needed (thousands of players at once). | L |
| E11 | Ledger housekeeping and a restore drill | A backup is only good if it restores. | Rotation, a restore drill from the PC copy, a snapshot-versus-ledger check. | S |
| E14 | A fast local test run | The whole suite takes about 40 minutes in one process. | Run the modules in parallel across the cores; day to day, run only the tests relevant to a change. | S |
| O4 | Cloudflare in front | Shield and caching. | The server is ready; the account and the name servers are yours. | S |
| O8 | Status and capacity | Know the limits; tell players about outages. | A status page. | S |
| O11 | Reset the old accounts | Some accounts still have the old 10,000-MB start. | Announce, back up, reset, or decide to keep them (G3). | S |

Done: **TA-F1**, **TA-F2**, **TA-F3**, **E1**, **E8**, **E12**, **E13**, **O1** real email (2026-10-31), **O2**, **O3**,
**O5**, **O6**, **O7**.

### R and X. Rules, and what is left of the old plan

| # | Change | Why | How | Size |
|---|---|---|---|---|
| R4 | A lawyer's read | Selling a game currency to the public. | The terms and privacy pages; what the ads may say. | S |
| R5 | Responsible spending | People who lose may chase losses; under-18s can buy. | Consider a lower default than US$500 in 30 days, a cool-off, a clear note that buying MB does not make anyone a better trader. | S |
| R7 | Data rights | Players should be able to leave. | The admin can delete an account (2026-10-25); still to do: a player downloads their data and deletes their own account. | M |
| R8 | "How this market works" | Transparency builds trust and teaches. | What drives prices, what is random, that player trades never move prices. | S |
| R9 | Who runs the site | Consumer law usually requires the seller's name and address. | A business name and a contact address in the terms. Your decision. | S |
| R10 | Real-market rules | RM1 and RM5 touch licences and financial-promotion law. | The data licence allows display on a public site; broker links, if any, comply with UK and EU financial-promotion rules (an approved firm or none); every real-chart page says "delayed, practice money, not advice". | S |
| X2 | Moonshots and two-outcome catalysts | Lottery tickets do not teach trading. | Switched off in `base.json`; remove the code or keep as an opt-in section. Your decision. | M |
| X7 | 3x products and very risky instruments | For advanced players only? | Kept for now (decided 2026-11-07); warnings or an unlock by unit later. | S |
| X9 | Admin "withdraw" | Nothing is cashed out. | Keep only as an admin correction, renamed. | S |

Done or decided: **R1** terms and privacy (24 October 2026), **R2** the age policy, **R3** consumer rules, **R6** a
sign-up bot trap; **X1** the real-money plan dropped, **X3/X4** the old edge and fee tools removed, **X5** the daily
contest (now removed by U10), **X6** 1,000 MB start, **X8** with M9.

---

## 6. Risks

| # | Risk | Why it matters | Where |
|---|---|---|---|
| 1 | **The market must be realistic without free money.** | It is the product: too random teaches nothing, too regular is exploited in a day. | P8-P15, `realism.py` |
| 2 | **Revenue from losses.** MB packages sell best when people lose. | It works against teaching and draws scrutiny with young users; the passes and M12 help. | M4, M12, R5 |
| 3 | **Minors buying.** | Parents' disputes and refunds; Managed Payments needs a low dispute rate. | G8, R5 |
| 4 | **Leverage and the boards.** A 10x player tops a day's board, or loses everything, by luck. | The boards promise that skill wins. | S2, T11 |
| 5 | **One server.** | A restore has never been rehearsed. | E11, O8 |
| 6 | **The name.** "Meme Street" suits a meme-stock game more than a place to learn. | Cheap to change now, expensive later. | B9 |
| 7 | **Real data licence and cost.** | Free sources forbid redistribution; a paid tier is a monthly bill before the feature earns. | RM1, R10 |
| 8 | **Financial promotions.** Broker links from a UK-run site may need an approved firm. | Fines, and the trust the site runs on. | RM5, R10 |
| 9 | **Selling volatility as free money.** Written options earn the variance premium. | T14 must be checked like every market change. | T14, `option_check.py` |
| 10 | **The learning path grows the save.** Per-attempt records for every player. | `state.json` is written every few seconds. | LP5 (cap the lists) |
| 11 | **The profit boards.** A big account tops them with a small return. | The "paying never buys a rank" claim is false there today. | M10 |
| 12 | **Fewer MB sinks after the cut.** The ladder paid 1,780 MB in all. | Until M12, MB only buy capital. | U10, M12 |

---

## 7. Decisions

**Decided:** Stripe through Managed Payments; package prices; Pro and Expert, monthly or yearly; what Pro includes;
real-time chart timeframes only; 13 or older to sign up, no age rule to buy; four leaderboards; a free restart when
nearly out; the Daily Chart on the site and open to visitors. **2026-11-07:** remove daily quests, the quest ladder,
the daily contest and medals (U10); keep 3x products, the bank rating label and chat; the full learning path with
exercises, XP, a streak and review (LP); options writing with margin and spreads as one order, Pro only (T14); all
three real-market bridges (RM); no Python bots (T15).

**Open (yours):**

| Question | Options |
|---|---|
| The real-data source (RM1) | Twelve Data, EODHD, Alpha Vantage, Tiingo or Polygon; which tier and monthly cost; daily only or hourly too. |
| Broker links (RM5, R10) | None (a plain how-to-choose page); links through an approved firm; affiliate links after legal advice. |
| House bots on the Daily board | Keep as they are; cap how many show on the board; mark them. |
| Exercises back in lessons (LP2) | Five per lesson as the pass check (the plan); fewer; chart tests only. |
| MB for learning (LP) | None, XP only (the plan); a small capped MB reward for finishing a unit. |
| The profit boards and the rank claim (M10) | Reword the claim; rank profit on the start balance only; drop the profit boards. |
| "Session" instead of "Day" (U10) | Rename; keep "Day" and rename the Daily Chart instead. |
| The old accounts (G3, O11) | Reset to 1,000 MB; keep them. |
| The default spending limit (R5) | Keep US$500 in 30 days; lower it. |
| Who the site names as its operator (R9) | A business name and an address; a registered agent. |
| The name (B9) | Keep "Meme Street"; rename for a teaching audience. |
| Moonshots (X2) | Remove the code; keep as an opt-in section. |
| Costs (M8) | 0.1% a side; a commission and a spread. |
| The boards and leverage (S2) | Count leverage as it is; cap it on the boards; a separate board. |
| Daily Chart prizes (TA-D8) | Badges only; a small MB prize for the day's top three. |

---

## 8. Checking a market change

1. The tests relevant to the change (`python -m unittest test_<module>` in `tests/`); the whole suite
   (`python -m unittest discover tests`, about 40 minutes) only for sweeping changes. They guard money conservation,
   the ledger and the rule that player trades never move prices.
2. `python tools/chart_check.py 12 <seed>` on two or three seeds: the charts against the facts of real prices
   (MARKET_REALISM.md has the targets and the last results).
3. `python tools/realism.py`: stylised facts, pattern rates within their target bands, and the no-free-money strategy
   comparison against holding the index, costs included, on markets never used for tuning; `tools/option_check.py`
   for options (extended by T14 to written options and spreads).
4. A look at the charts by a person: does it look like a market a trader would recognise?
5. Update `HOW_IT_WORKS.md` and this file.
