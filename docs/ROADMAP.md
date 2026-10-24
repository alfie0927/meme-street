# Meme Street roadmap

**Goal (new, 2026-10-13):** an informational game where people **learn to trade, or just trade for fun**, on a
realistic, fictional stock market. **Technical analysis is the core of it** (section 1A): charts that behave like real
charts and the tools to read them; news and the economy are background. The
market behaves like a real one: it drifts slowly upwards over time, with corrections, bear phases and long sideways
stretches; scheduled economic news (interest-rate decisions, inflation, jobs) moves it; and prices respect and break
support and resistance the way real charts do, so the setups traders are taught actually appear and can be practised.
Everyone starts with **1,000 MB**. Players who run out, or want more capital, **buy MB packages** (1,000, 5,000,
10,000, 50,000 or 100,000 MB). **Challenges award free MB** for completing them. MB are a game currency: they have no cash value and
are never paid out.

**What this replaces.** The old plan was a real-money trading game: buy MB with crypto, withdraw winnings, the house as a
counterparty earning a fee, and every mechanism built as a fair bet so that nobody could have an edge. That plan is
dropped. Section 2 lists what changes and what happens to the code that was built for it.

Companion doc: `HOW_IT_WORKS.md` describes what the code does **today**. Update it after every change, and check this file
before starting any work.

Size key: **S** = under a day, **M** = a few days, **L** = a week or more.

---

## 1. The new plan on one page

| | |
|---|---|
| **Who it is for** | People who want to learn to trade without risking their own money (beginners, students, people preparing for a real account, classes and trading clubs), and people who just want to trade for fun. |
| **What they do** | Trade a live market of invented companies, indices, ETFs and commodities with real tools (charts, indicators, drawing, orders, stops, position sizing), follow lessons, complete challenges and see their skill improve. |
| **How the site earns** | Selling MB packages (1,000 / 5,000 / 10,000 / 50,000 / 100,000 MB). Prices are your decision (B1). A second income that does not depend on people losing (classroom seats, a Pro tier) is recommended (B2). |
| **How the market behaves** | Technical structure first (section 1A): trends, ranges, support and resistance, named chart patterns, volume that confirms, gaps. Around it: slow long-run upward drift; regimes (bull, correction, bear, sideways); scheduled macro data and rate decisions with consensus and surprise; fewer, more meaningful headlines; technical structure (support and resistance tested, bounced or broken, false breakouts, retests, trends, volatility squeezes, gaps) and the psychology behind it (overreaction, panic, euphoria, stop runs). |
| **What it is not** | Not gambling (no cash-out, no prizes with money value), not investment advice, not a broker. |

**Design rules for the new market** (these replace the old "no strategy may have an edge" rule):

1. **Realism you can learn from.** Behaviour that real markets show should appear, at realistic rates: a support level
   holds often enough to be worth trading and breaks often enough that a stop is needed.
2. **No free money.** No simple, unskilled rule (buy everything, buy every dip, always fade, doubling down, shorting
   everything) may beat a sensible baseline (holding the index) by a wide margin. Skill should show as better
   *risk-adjusted* results over many trades, never as a guaranteed win. This is checked by a new test suite (P11).
3. **Players' trades never move prices** (kept from the old plan): the market is the same for everyone, and a big account
   cannot push it.
4. **Paying never buys a rank.** Leaderboards measure return on the money put in, or risk-adjusted skill; buying MB gives
   more capital to practise with, not a better place.
5. **Honest selling.** Prices in real currency are shown before every purchase, MB are clearly worthless outside the site,
   there is no pressure to buy at the moment of a loss, and there are spending limits (M6, R5).
6. **Every MB is accounted for.** The ledger already records every money event; every MB that enters the game will carry
   its source (starting grant, purchase, challenge reward, refund, admin) (M2).

---

## 1A. Technical analysis first (direction set 2026-10-13, after the learn-to-trade build)

**The direction.** Meme Street is an informational game for two kinds of people: those who want to **learn how to
trade**, and those who just want to **trade for fun**. Both are served best by the same thing: a market whose charts
behave like real charts, and the tools to read them. **Technical analysis is the core of the product.** News, the
economy and company stories stay, but as background: they explain some moves and add the occasional jolt, they are
never the main reason a price moves, and a player who ignores them entirely should still have a full game.

**What that means in practice.**

- **The chart is the main screen.** Most of what a player does should happen on a chart: reading it, drawing on it,
  placing trades and stops on it, and reviewing trades on it afterwards.
- **Price structure comes first in the market model.** Most moves should be explainable from the chart (a trend, a
  range, a level, a pattern, volume) rather than from a headline.
- **The standard tools are part of the game, not a paid extra.** A learner cannot learn technical analysis without
  Bollinger bands or MACD, so the paywall moves from *what you can learn* to *convenience and depth* (see TA-B9).
- **Fun players need no homework.** Lessons and challenges are offered, never required; a player can open
  the site and trade straight away, and there are light competitive goals (weekly challenges, leagues) for people who
  play for fun.
- **News is turned down further.** Fewer headlines, smaller macro reactions, the news wire made secondary on the page,
  and "why it moved" explained in technical terms first.

### What exists today, what changes, what is new

The learn-to-trade build (section 3) already has a first version of: drift and market phases, trends in legs, ranges
and breakouts, support and resistance that hold or break (with false breakouts), volume, a capitulation low, the macro
calendar, earnings forecasts; on the chart: volume, SMA 20/50, EMA 20, RSI, Bollinger bands, VWAP, MACD and ATR (the last
four Pro), drawn horizontal levels (kept only in the browser) and a position-size tool; lessons, challenges and a
journal. The plan below builds on it.

#### A. The market: technical structure (extends track P)

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-A1 | Calibrate levels to their targets | Strong levels hold 52-54% today against a 55-65% target; the difference between strong and weak levels is what a player learns to read. | Raise the hold odds for strong, aligned levels; make the approach visibly slow down; check with `realism.py` on fresh seeds. **Done (2026-10-19): the old settings already held 56% on fresh seeds; a small extra for strong levels in line with the trend and a slower approach at strong levels bring them to 59%, weak ones stay at 43%, and trading every level beats holding no more than before (MARKET_REALISM.md).** | S |
| TA-A2 | More kinds of level | Traders watch more than swing points and round numbers. | The previous game day's high, low and close, the day's open, gaps, the 52-game-week high and low, and moving averages (20, 50, 200 game days) acting as moving support and resistance, each with its own hold odds. **Done (2026-10-21): the previous game day's high, low and close, the day's open, the 52-week high and low and the 20/50/200-day averages, each with its own strength, adding up where they meet a swing level or a round number. Bounces are smaller and a stock tests at most one level every 10 minutes, so trading every level test earns about what holding does (HOW_IT_WORKS §6A.4, MARKET_REALISM.md).** | M |
| TA-A3 | Chart patterns that real traders name | Double tops and bottoms, head and shoulders, triangles, flags and pennants, wedges, channels and cup-and-handle are the vocabulary of technical analysis. | The model forms them on purpose at realistic rates (a flag after an impulse, a triangle inside a range, a double top at the end of a trend); the outcome is drawn like a level test, so a pattern completes or fails, never with certainty. **Done (2026-10-21): double tops and bottoms, head and shoulders (and inverse), wedges, ascending, descending and symmetric triangles, flags, channels and cup and handle, about four a stock a game year, each ending one of three ways (works, busted, fails) at odds that leave a confirmed pattern right a little more often than not (§6A.10).** | L |
| TA-A4 | Volume that tells the story | Volume confirmation is taught everywhere; today volume follows the move but tells little. | Rising volume into a true breakout and falling volume on a false one, low volume on pullbacks in a trend, climax volume at blow-off tops and panic lows, divergence (price higher, volume lower) before a reversal. **Done (2026-10-21): less volume on a break that will fail (on average: the two overlap), quiet pullbacks, a weaker last push on lower volume, climaxes on four times the volume (§6A.3, §6A.4).** | M |
| TA-A5 | Candles that mean something | Hammers, engulfing candles and dojis are taught first. | Rejection wicks at levels that hold, engulfing candles at reversals, small-bodied candles before breakouts; at realistic rates, and not reliable on their own. **Done (2026-10-21): a harder push back once the price is through a holding level (wicks), a burst the other way where a trend turns (engulfing candles), a quieter last fifth of a range (small bodies before the breakout).** | M |
| TA-A6 | Timeframes that agree | A trend on the 4-hour chart should contain smaller swings on the 5-minute chart, as real charts do. | Nest the swing structure: intraday legs inside multi-day legs inside the market phase; check that the trend on one timeframe is visible on the next. **Done (2026-10-21): intraday legs of 4 to 12 minutes that alternate inside a trend's legs, adding no drift (§6A.3); the next game day goes the way of a 10-day move about 51-54% of the time.** | M |
| TA-A7 | Gaps | Gaps and gap fills are classic setups. | Opening gaps sized by the overnight move (the after-hours and pre-market sessions already exist), and a realistic share of small gaps that fill during the day. **Done (2026-10-21): the opening jump and the thin sessions already made the gaps; the game-day candle is now the regular session alone, so they show on the D chart, and the previous close is a level where a gap fills. The engine fills 68-75% of small gaps and 14-29% of large ones the same day.** | S |
| TA-A8 | Momentum indicators that behave | RSI divergences and Bollinger squeezes should appear because the structure produces them, not by design of the indicator. | No change to the indicators themselves: tune the structure (trend exhaustion, quiet ranges before breakouts) and measure how often divergences and squeezes precede reversals and breakouts. **Done (2026-10-21): a trend's last push is weaker (divergences before it ends) and a range's end is quieter (squeezes before the breakout); `realism.py` measures both against their baselines (MARKET_REALISM.md).** | S |
| TA-A9 | The realism suite for patterns | Every pattern needs a measured rate and outcome, and no simple pattern rule may print money. | Extend `realism.py`: detect each pattern the way a trader would, count how often it completes and how far it runs, compare simple rules ("buy every bull flag") against holding the index, costs included. **Done (2026-10-21): `game/patterns.py` finds patterns from candles alone (zigzag swing points, textbook templates, two swing sizes) and follows each forward; `realism.py` reports how many of each it finds, how many complete and work, the result of trading them, and how many of the model's own a trader would recognise.** | M |
| TA-A10 | Longer history | Technical work needs months of daily bars; the chart keeps 500 candles per timeframe. | Keep daily candles for many game years and minute candles for longer, in a compact store (was T9). **Done (2026-10-21): game-day candles for ten game years in `data/history.db`, one-minute candles for three real days in `data/minutes.db` (`game/history.py`); a running game rebuilds its days once from its 5-minute and 30-minute candles.** | M |
| TA-A11 | Game-time timeframes | A "1d" candle is 24 real hours today, which is 48 game days; traders think in days. | Offer candles in game time (a game day of 30 minutes, a game week, a game month) next to the real-time ones, and label which is which. **Done (2026-10-21): GAME D, W and M on the chart, with game dates on the scale and in the readout; a game-day candle is the regular session.** **Taken out again on request the same day: the chart offers real-time sizes only; the game days are still kept, for the price model's daily levels.** | S |

#### B. The tools: charts and trading on the chart (extends track T)

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-B1 | A crosshair with a readout | Basic to every chart. | Crosshair with the time, open, high, low, close, volume and indicator values under the pointer; works by touch on phones. **Done (2026-10-19): a crosshair with the price and time on the scales, and a readout above the chart (time, OHLC, change, volume, every indicator's value); a tap on a touch screen.** | S |
| TA-B2 | Chart types and scales | Traders switch views. | Candles, hollow candles, bars, line and Heikin-Ashi; linear and log scale. **Done (2026-10-19): candles, hollow candles, bars, line, Heikin-Ashi and a log scale.** | S |
| TA-B3 | Indicator settings and more indicators | Periods are chosen, not fixed. | **More indicators: done (2026-10-14)**: 49, searchable, 17 free (HOW_IT_WORKS §11). Still to do: settings per indicator (period, source, colour) and saving the set per player on the server. **Settings done (2026-10-19): length, second length, signal, width, source and colour per indicator, saved on the server with the rest of the set-up (`chartprefs.py`).** | M |
| TA-B4 | Full drawing tools, saved to the account | Levels are drawn today only in one browser. | **Tools: done (2026-10-14)**: a floating, draggable toolbar with horizontal and vertical lines, trend lines, rays, boxes, circles, Fibonacci retracements, brush, path, head and shoulders, long and short positions and text, with select, move, reshape and delete (§11), plus a taller and full-screen chart. Still to do: channels and Fibonacci extensions, and saving drawings on the server so they follow the player to a phone (today they stay in one browser). **Done (2026-10-19): parallel channels and Fibonacci extensions, and drawings kept on the server per player and stock.** | M |
| TA-B5 | Trade from the chart | Entry, stop and target belong on the chart. | Drag lines for entry, stop and target; the risk-reward ratio and the size for the chosen risk update as you drag; one click places the order and its bracket. Today's position-size box becomes this. | M |
| TA-B6 | Your trades on the chart | Seeing where you bought and sold is how you learn from it. | Markers for every buy, sell, stop and target on the chart, and the open position's entry, stop and target lines. **Done (2026-10-19): arrows for every buy, sell, short and cover, and tagged lines for your stop-loss, take-profit and limit orders next to the average entry.** | S |
| TA-B7 | Alerts | Waiting for a setup should not mean staring. | Alerts when the price crosses a drawn line or an indicator condition is met; in the page, and by email once mail is on (was T6). | M |
| TA-B8 | A setup screener | Finding setups is a skill to practise. | Scan the market for stocks near strong support or resistance, breakouts on volume, squeezes, RSI extremes and divergences, gaps, new highs and lows, named patterns (was T7). | M |
| TA-B9 | Rethink what Pro includes | Gating standard indicators blocks learning, and technical analysis is now the core. | **Decided for now (2026-10-14): the drawing tools and 17 indicators (all moving averages, RSI, Stochastic, Momentum, Auto Fibonacci, volume average) are free; 32 more indicators are Pro.** **2026-10-21: Pro also gives leverage up to 10x (T11), and a new tier above it, Expert (US$12.99 for 30 days, US$99.99 a year), adds trading bots and backtests (T12, T13) to everything in Pro; options are free for everyone (T10).** The earlier recommendation was: every standard indicator and drawing tool free; Pro becomes the screener, alerts beyond a few, multi-chart layouts, replay, saved layouts, deeper journal analytics and pattern statistics. Your decision (section 7). | S |
| TA-B10 | Multi-chart layouts and comparison | Setups are read across timeframes and against the index. | Two or four charts side by side, linked timeframes, an index or sector overlay, relative strength (was T5, U4). | M |
| TA-B11 | Replay mode | Practising on the past, bar by bar, is the best technical-analysis teacher there is. | Pick a stock and a past period, step through it bar by bar and trade it in a practice account (was T8; needs TA-A10 and E5). | L |
| TA-B12 | The chart as the home screen | Most players should land on a chart, not a table. | A trading screen: the chart in the middle, a watchlist on one side, the order ticket and positions on the other, the news wire small and folded. The market table stays as the "all stocks" view. | M |

#### C. Learning built around the chart (extends track L)

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-C1 | A technical-analysis curriculum | Eight of the twelve lessons are technical today; the order and depth should follow the chart. | Levels: reading candles and volume, trend and structure, support and resistance, patterns, indicators, multiple timeframes, risk and trade management, a trading plan. The macro and earnings lessons move to an optional "Context" group. | M |
| TA-C2 | Lessons on live and past charts | A lesson should show the setup on a real chart from the game. | Each lesson embeds charts from the game's own history ("here is where NVXA's support held twice and broke the third time"), picked by the pattern detectors (TA-A9). | M |
| TA-C3 | Spot-the-setup exercises | Pattern recognition is learnt by doing, quickly, with feedback. | Show a past chart, ask "mark the support", "bounce or break?", "where does the stop go?", reveal what happened next, score it; small capped MB rewards (was L6). | M |
| TA-C4 | Technical challenges | Challenges should practise chart skills. | "Trade a breakout that came with rising volume, with a stop below the level", "draw three levels that later held", "close five trades at 2R or better"; checked from the drawings, orders and journal. | M |
| TA-C5 | A coach that reads the chart | Feedback after a trade turns mistakes into lessons. | Rule-based remarks from the chart context: "you bought into resistance", "your stop was inside normal noise (under one ATR)", "you chased a candle three ATRs from the average" (was L7). | M |
| TA-C6 | Journal entries with the chart | Reviewing trades is how traders improve. | Attach the chart (with the player's drawings) at entry and exit to every journal entry; tag the setup automatically from the pattern detectors, editable. **Dropped (2026-10-20): there is no journal any more.** | M |
| TA-C7 | A glossary and tooltips | Words like "R", "VWAP", "divergence" stop beginners. | Tooltips on every indicator and tool, a glossary page (was L9). | S |

#### D. Playing for fun (extends track S)

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-D1 | No homework | Fun players should not be pushed through lessons. | Keep the onboarding strip one click to hide; nothing locked behind lessons; a "just let me trade" path on sign-up. | S |
| TA-D2 | Weekly competitions and leagues | Light, social goals keep people coming back. | Weekly challenges ranked on return on money put in and on risk-adjusted return, leagues by level, small capped MB prizes (was S3, S5). | M |
| TA-D3 | Share a chart | Explaining a trade idea is both fun and learning. | Share a chart with drawings in chat or by link (was S4). | M |
| TA-D4 | The Daily Chart | A short daily game brings people back every day and teaches reading a chart fast. | **Done (2026-10-23):** one mystery stock a day made by the price model (levels, trends, patterns, high volatility), the same for everyone; 1,000 MB of practice money, two minutes of one-second candles after a one-minute lead-in, buy or sell 25 to 100%; one go a day; the day's board and the last 7 days' winners (HOW_IT_WORKS §10.13). Then: shorting, a countdown on the chart, a summary with everyone's returns as a distribution, a button in the header instead of a menu item. Next, if wanted: a medal or a small MB prize for the day's top three (watching for extra accounts), sharing a result, a practice round on an old chart. **Archived (2026-10-24), on request, to be worked on again:** off the site (no header button, page, script or endpoints; the `daily_chart` setting), with all the code kept (HOW_IT_WORKS §10.13 says how to bring it back). | M |

#### E. News and the economy: turned down (changes track N)

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-E1 | Smaller macro reactions | A release should be a bump on the chart, not the story of the day. | Halve the market reaction to a release surprise (`release_sigmas` 0.55 to about 0.3) and the post-release volatility burst; keep the calendar. **Done (2026-10-19): `release_sigmas` 0.3, and the burst after a release halved.** | S |
| TA-E2 | Fewer headlines again | The wire still carries ratings, company events and stories. | Fewer rating notes and company events; no follow-ups; earnings, macro releases and the occasional big story only. **Done (2026-10-19): no follow-ups, bank reviews a third as often and few "reiterates" notes, 1 company event a quarter (was 1.5).** | S |
| TA-E3 | The news wire becomes secondary | It takes a third of the market page. | Fold it into a smaller panel (open on request) on the market page and the trading screen. **Done (2026-10-19): the news wire is a folded panel, open on request (remembered), on laptops and phones.** | S |
| TA-E4 | "Why it moved", technical first | Players should learn to explain moves from the chart. | Each stock page says what happened in chart terms ("broke resistance at 145 on twice the usual volume", "bounced off the 50-day average"), with a headline only when there was one (was N7). | M |
| TA-E5 | Drop or park the rest | They add news, not chart skill. | Park N8 (better company stories), N9 (a daily wrap: later, and written around the chart), N10 (LLM headlines); keep N5 (earnings forecasts) and N6 (the calendar). | S |

#### F. Housekeeping

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-F1 | Admin: total MB instead of the house | The house carries no risk now that nothing is paid out. | Done (2026-10-13): the dashboard shows the total MB in the players' hands (starting, bought, rewards, other, plus the players' P&L, so it moves as people trade) instead of the house reserve, and no house P&L. Still to do: retire the house-risk panel and the reserve top-ups from the dashboard and the engine (M9). | S |
| TA-F2 | Split the chart code out of `index.html` | The chart is becoming the biggest part of the page. | Move the chart, indicators and drawing tools into their own script file with tests (E2). **Done (2026-10-21): `web/chart.js` (the chart, indicators, drawing tools, chart size and position size: about 680 lines out of `index.html`), served at `/js/chart.js`; the browser tests cover it.** | M |
| TA-F3 | A browser test for every tool | Chart tools break silently. | **Mostly done (2026-10-14)**: `tests/test_chart_tools.py` draws, selects, moves and deletes, and checks 13 indicators against Python. Still to do: placing orders from the chart. | M |

---

## 2. What changes from the old plan

| Area | Old plan | New plan | What happens to the existing code |
|---|---|---|---|
| Money | Buy MB with crypto, withdraw winnings | Buy MB packages, never withdraw | `Engine.credit` becomes the purchase and reward path (M2, M3); cash-out (`debit` as a withdrawal) is dropped, kept only for admin corrections (X9) |
| Starting balance | 10,000 MB | **1,000 MB** | `signup_bonus` 1000 (M1); the live game is reset when the new economy ships (O11) |
| How the site earns | 0.1% fee on every trade | MB packages (and optionally classrooms / Pro) | The fee becomes a realistic trading cost, not income (M8); `revenue_model.py` is replaced (M7) |
| The house | Counterparty with real risk: reserve, floors, top-ups, stress loss | Only bookkeeping: nobody is paid out | Conservation checks stay; capital rules and reserve alarms are retired (M9) |
| Prices | A fair random walk: expected move zero everywhere, a hidden mood, mean reversion to a fixed reference | Drift, regimes, macro, technical structure (track P) | The price process is rebuilt in its own module (E1, P1-P12) |
| News | Frequent stories, rare two-outcome catalysts and industry shocks | Fewer headlines; a macro calendar; earnings with consensus | Track N; catalysts and lottery stories retired (X2) |
| Lottery-like listings | Moonshots: tiny companies, 260-550% volatility, 60% bankruptcy | Not part of a training market | Removed from the default market or moved to an opt-in speculative section (X2) |
| Competition | Daily paper-money race for medals | Challenges that teach a skill and award MB | The contest code becomes the challenge engine's base (L3, X5) |
| Checks | `edge.py`: no strategy may beat the house | Realism and "no free money" suite | The strategy simulator is reused with new targets (P11, X3) |
| Legal | Gambling, money transmission, KYC/AML, securities questions | Consumer law for digital purchases, minors, payments, education claims | Track R; the real-money items are retired (X1) |

Old roadmap IDs are retired. Where `HOW_IT_WORKS.md` still mentions one, this is where it went: A10 → E8 (admin follow-ups),
A12 → X1 (retired), A14 → M8 (costs), C2 → N10 (LLM headlines), E6 → U1 (phone, second step), F8 → done (chat moderation),
G10 → E10 (scale), G11 → E11 (ledger housekeeping), I2 → decided (packages; B1, B2), I4 → B4 (funnel), J1 → R1 (terms).

---

## 3. Where things stand (2026-10-21)

**Live on https://memestreet.net** (Hetzner, Caddy, fail2ban, admin behind a second password, `/api/health` watched every
15 minutes, backups every six hours on the server and pulled to this computer daily): the learn-to-trade market and its
tools as listed below, with the shop built but closed until a payment provider is chosen.

| Area | Built | Still open |
|---|---|---|
| The market (P, TA-A) | Drift, phases, trends in legs, ranges and breakouts, support and resistance from swing points, round numbers and the daily chart, volume that confirms (on average), wicks, engulfing turns, squeezes, intraday legs, climaxes, gaps, ten kinds of named chart pattern; stochastic volatility, fat tails, sessions; checked by `realism.py` (with the pattern suite) and `chart_check.py` | P8 overreactions, short squeezes and stop runs; P9 more factors; P10 asset classes; P13; the engine's tail exponent and the market's one-minute autocorrelation are just outside their targets on some seeds (as before Phase 2) |
| News and the economy (N, TA-E) | The central bank and the macro calendar with forecasts, earnings forecasts and drift, far fewer headlines, the news wire folded | TA-E4 why it moved; N8-N10 parked |
| Charts and trading tools (T, TA-B) | Crosshair and readout, five chart types and a log scale, 49 indicators with settings saved per player, 16 drawing tools saved on the server, your trades and orders on the chart, real-time candles (game-time candles were taken out again on request), ten game years of daily history; options for everyone (T10), leverage up to 10x with Pro (T11), trading bots and backtests with Expert (T12, T13) | TA-B5 trade from the chart, TA-B7 alerts, TA-B8 screener, TA-B10 layouts, TA-B11 replay, TA-B12 the trading screen |
| Learning (L, TA-C) | Twelve lessons (quizzes switched off), challenges paying MB, the quest ladder; the journal was removed | TA-C1 to TA-C7 |
| Money (M, B, R) | 1,000 MB start, MB by source, packages, Pro and Expert, test checkout and Stripe Checkout with a signed webhook, receipts, refunds, spending limits, the free restart, terms and privacy, the age policy, a pricing model (M7) | M3 the payment provider (Paddle or Lemon Squeezy as merchant of record, or Stripe), R4 a lawyer's read, M8 costs, M9 the house |
| Running it (O, E) | Staging copy, rollback, daily backups off the server, uptime checks, fail2ban, CI in four parts plus lint and types, an error tracker on the admin page | O1 real email (a Resend account), O4 Cloudflare (your account and name servers), O8 capacity, O11 resetting the old 10,000-MB accounts, E2 splitting `engine.py`, E5, E6 |

**Waiting on you:** the payment provider (M3), a Resend account for email (O1), a Cloudflare account and the name-server
change (O4), a lawyer's read of the terms and privacy pages (R4), and the go-ahead to reset the old accounts (O11).

---

## 4. The biggest decisions and risks

| # | Decision or risk | Why it matters | Where |
|---|---|---|---|
| 1 | **Rebuilding the price process** is the largest and riskiest piece of work. Support and resistance, trends and regimes must appear at believable rates without becoming a money machine, and the drift must be visible over weeks but not over a session. | It is the product. A market that is too random teaches nothing; one that is too regular is exploited in a day. | P1-P12, E1 |
| 2 | **Selling MB to people who run out.** Without leverage, losing *everything* in a cash account is rare (stocks seldom go to zero; fees and repeated losses drain slowly), so most purchases will be "I want more capital", not "I lost it all". And the better the teaching, the less people lose. | Revenue that depends on losses works against the product's purpose and draws scrutiny when the users are young or vulnerable. | M4, M6, B1, B2, R2-R5 |
| 3 | **Free MB from challenges** must be worth chasing but must not remove the reason to buy, and must not be farmable with extra accounts. | Too little and challenges feel pointless; too much and nobody buys. | M5, L3, R6 |
| 4 | **Age and consumer law.** A trading-education site will attract teenagers; selling them currency needs an age policy, clear prices, receipts and a refund rule. | The cheapest mistakes to avoid and the most expensive to fix later. | R1-R4 |
| 5 | **The live site has 8 accounts on the old rules** (10,000 MB, old market). | They need a clear notice and a reset when the new economy ships. | O11 |
| 6 | **The name.** "Meme Street" suits a meme-stock game more than a place to learn. | Cheap to change now, expensive later (domain, brand, search). | B9 |
| 7 | **Leverage and the boards** (2026-10-21). Leverage is a Pro tool, and it gives no edge (the same odds, a bigger bet, interest to pay), but it makes results swing more: a 10x player is far more likely to top a day's board, or to lose everything, by luck. That bends the rule "paying never buys a rank", and wiping out an account becomes common, which makes MB sales lean on losses (risk 2). | The boards are a promise that skill wins; revenue from losses works against the product. | T11, M4, section 7 (leaderboards) |

---

## 5. Tracks

### M. MB economy and purchases

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| M1 | Everyone starts with 1,000 MB | The new model. | `signup_bonus` 1000 (the tests already use 1,000). Check what 1,000 MB means against share prices (gold is about 2,400 MB a share: fractional shares already work, but the page should show "you can buy 0.4 shares") and against minimum sensible trade sizes. The live game is reset (O11). | S |
| M2 | Where every MB comes from | Purchases, rewards and grants must be told apart for receipts, refunds, statistics and abuse checks. | A `source` on every credit in the ledger (grant, purchase, challenge, refund, admin) and per-player totals by source; the admin page shows them. | S |
| M3 | Packages and checkout | The income. | A payment provider's hosted checkout (a *merchant of record* such as Paddle or Lemon Squeezy handles VAT and sales tax worldwide for a solo seller; Stripe Checkout is the alternative), five packages, a signed webhook that credits MB exactly once (never trusting the browser), receipts, a purchase history page, refunds that take back unspent MB, chargebacks that freeze the account. Test mode first. | M |
| M4 | What happens when an account runs out | The moment a player busts is when the site teaches the most, and when pressure to buy is least fair. | A "your account is out of money" page that shows what happened (biggest losses, risk taken, a link to the risk lessons) and the options: buy a package, or a free restart on a timer (for example 1,000 MB once a week) if you decide to offer one. No purchase pop-up during trading. | S |
| M5 | Challenge rewards | Free MB for learning. | Rewards are paid by the challenge engine (L3) into the ledger with source `challenge`; one-time and repeatable challenges, daily and weekly caps, rewards only for verified accounts, a weekly budget per active player as a setting, and a check in the pricing model (M7) that rewards do not remove the reason to buy. | S |
| M6 | Spending safeguards | Selling currency in a game that people can lose needs limits. | A default monthly cap, player-set lower caps, a cool-off after several purchases in a day, a "what I have spent" page with real-currency totals, and a confirmation step that shows the price. | S |
| M7 | A pricing model | `revenue_model.py` models fee income, which is no longer the income. | Replace it with a model of package sales: share of players who buy, package mix, how often accounts run out (from the market's difficulty and the bust rule), free MB from challenges; output per 1,000 sign-ups and its sensitivity to each assumption. Fill it with real numbers after M3 ships. **Built (2026-10-21): `tools/pricing_model.py`, with every behaviour an assumption in one table and the sensitivity to each (with today's guesses about US$0.30 net a sign-up over 26 weeks; retention and the share who buy without having run out matter most). Fill it in once the shop has real numbers.** | S |
| M8 | Trading costs that teach | Costs are part of trading; they are no longer the site's income. | Decide the cost model: keep 0.1% per side, or a commission plus a bid-ask spread that widens in thin sessions, fast markets and small companies, and slippage on market orders in fast moves (never moving the price). Show costs per trade in the journal. Any change is checked with the realism suite (P11): costs decide whether a pattern pays. | M |
| M9 | Simplify the house | Nobody is paid out, so the house carries no real risk. | Keep the conservation checks and the ledger; retire the capital rule, the reserve floor and top-ups as a risk control, and the reserve alarms; turn the admin's house-risk panel into "where players are positioned", which is still interesting. | S |

### P. The price model (the core of the new product)

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| P1 | Slow long-run drift | Real markets go up over years; the user asked for it. | Each listing gets an expected return per game year (the index about +6% to +9%, quality companies and defensives lower and steadier, small and speculative ones higher and more volatile, bonds and gold their own); applied as a drift in log price, so a buy-and-hold of the index makes money over many game years and a session shows almost none of it (at 365 game days a game year is 7.6 real days: +8% a game year is about +0.04% a real hour). Mean reversion to a fixed reference price is replaced by reversion to a drifting fair value, or dropped. | M |
| P2 | Market regimes | Bull markets, corrections, bear markets and long sideways stretches are what make a market feel real, and what technical traders must adapt to. | A hidden regime process (bull, correction, bear, sideways, recovery) with realistic durations and depths in game time (a 10% correction about once a game year, a 20% bear market every few game years, sideways phases of weeks to months), each with its own drift, volatility and correlation; the economy (N4) shifts the odds. Players never see the state, only its effect. | L |
| P3 | Ranges and sideways markets | "Price moves sideways for extended periods" is a request and a teaching staple. | In a range a stock oscillates between a floor and a ceiling with mean reversion inside it, volume dries up, and the range ends in a breakout whose direction leans with the regime. | M |
| P4 | Support and resistance | The heart of technical trading: levels are tested, and either hold or break. | Each listing remembers its levels: earlier swing highs and lows, the edges of past ranges, round numbers, the 52-week high and low, and the 50 and 200 game-day averages. When price nears a level the process changes: the approach slows, then the level either holds (a bounce, more likely for a strong level: several earlier touches, high volume there, in line with the trend) or breaks (more likely after repeated tests, on a volume surge, against a weak level). A break can follow through, fail and fall back inside (a false breakout or stop run), or come back to retest the level from the other side (a broken resistance acting as support). The rates are set from real-market statistics and checked by P11. | L |
| P5 | Trends and swing structure | Trends of higher highs and higher lows, pullbacks and exhaustion are taught everywhere. | Moves come in legs (an impulse, then a pullback), pullbacks often stop near the moving averages or the last broken level, and trends end with a failed new high, a divergence or a climax. | L |
| P6 | Volatility structure | Squeezes and expansions, opening spikes and quiet middays are real and tradable. | Volatility compression before a move (a narrowing range) and expansion after it, volatility rising when prices fall (the leverage effect), the existing clustering and session pattern, opening gaps and the tendency of small gaps to fill. | M |
| P7 | Volume | Volume confirms breakouts and marks climaxes; there is none today. | A volume series per listing, linked to volatility, news, level tests and breakouts (high on a true break, low in ranges, a spike at panic lows and euphoric highs), shown under the chart (T1). | M |
| P8 | Market psychology | Real markets overreact, panic and chase. | News overreactions that partly retrace, "buy the rumour, sell the news" around scheduled events, round-number magnetism, sector herding, capitulation lows with long wicks and huge volume, blow-off tops, short squeezes when short interest is high (the game tracks it), and stop runs just past obvious levels. Each one has a rate and is checked by P11. | L |
| P9 | Factors and correlations | One market factor plus sectors is too simple for macro to matter. | Factors for the market, interest rates, oil, the dollar and risk-on/off, an exposure to each per listing, and correlations that rise in sell-offs. Macro news (track N) moves the factors. | L |
| P10 | Asset classes that behave like themselves | Bonds, gold, oil and defensive stocks teach different lessons. | Bonds fall when rates rise (by their duration), gold reacts to real rates and fear, oil to supply news and growth, defensives hold up in bear phases and cyclicals lead in recoveries, small companies move more. | M |
| P11 | The realism and "no free money" suite | The old edge checks ask "can anyone win?"; the new question is "does it look and act like a market, and is there free money?". | Reuse the strategy simulator (`sim.py`, `bots.py`, `edge.py`) with new targets: (a) stylised facts of real returns (fat tails, volatility clustering, almost no autocorrelation of returns, drawdown and regime statistics); (b) pattern rates within target bands (for example: a strong support holds 55-65% of the time; 20-35% of breakouts fail); (c) strategies measured against holding the index, costs included: no unskilled rule may beat it by more than a set margin, and a disciplined rule-follower (enters at a level, stops below it, sizes by risk) may do modestly better. Runs over hundreds of markets, like the old studies. | L |
| P12 | Retire what conflicts | The old process was built to have no direction. | The hidden mood, the fixed-reference mean reversion, the daily move envelope, two-outcome catalysts and distress bets are replaced or kept only where they still fit; each removal checked by P11. | M |
| P13 | A market made for practice | Beginners may want calmer conditions. | Optionally a second, gentler market (lower volatility, clearer levels) for the first lessons, or a difficulty setting per classroom. Later. | M |

### N. Macro, earnings and news

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| N1 | Far fewer headlines | News should be events, not noise; the user asked for less. | Cut random company stories sharply (to a handful per game day across the market), keep scheduled company events and earnings, and let macro drive the big days. | S |
| N2 | A central bank and interest rates | Rate decisions move everything and are taught everywhere. | A policy rate, meetings on a published calendar (about eight a game year), a market expectation before each one ("hold expected, 30% chance of a cut"), a decision drawn from the hidden economy (N4), and a reaction to the *surprise* through the factors (P9): bonds, banks, growth and real-estate stocks, gold, the dollar. Quiet before, volatile after, sometimes a whipsaw. | L |
| N3 | Economic data releases | CPI, jobs and growth reports make the market realistic and give traders scheduled events to plan around. | Monthly CPI and jobs reports, quarterly GDP, and a few others (retail sales, business surveys, weekly jobless claims), each with a consensus forecast and an actual figure; the reaction follows the surprise and what it means for rates. | M |
| N4 | A hidden economy | Data, rates, earnings and regimes should tell one story. | A slowly moving economy (inflation, growth, unemployment, the policy rate) that produces the data, sets the central bank's decisions, tilts company earnings and shifts the regime odds (P2). Players see only the releases. | L |
| N5 | Earnings with consensus | Every report now says "beat expectations" with no expectation behind it. | A consensus estimate published before each report, actual vs consensus as the surprise, guidance, a reaction to the surprise, and a drift for a few days after big surprises (post-earnings drift). Optionally earnings *seasons* instead of reports spread evenly. | M |
| N6 | An economic calendar page | Scheduled events are only useful if players can see them coming. | Upcoming releases and earnings with consensus; after the release, the actual, the surprise and how the market reacted. **Done; since 2026-10-14 a month grid of game days with Previous / Next / Today and a detail list per day (HOW_IT_WORKS §6A.6).** | S |
| N7 | Every move explained | "Why did it move?" should always have an answer, which is how people learn. | Link each headline to the move it caused, and give each stock page a "why it moved today" line combining news, macro and technical events ("broke resistance at 145 on high volume"). | S |
| N8 | Company stories, fewer and better | Stories still give companies character. | Keep company events, earnings and a few story kinds; retire two-company stories and catalysts (X2); later, multi-stage stories (a merger: rumour, bid, approval or collapse). | M |
| N9 | A daily market wrap | A summary of the day is a lesson in itself and the best email. | Auto-written each game day: the index, the macro data, the biggest movers and the technical events behind them. | S |
| N10 | LLM-written headlines (optional) | Variety for little writing. | Pre-generated offline and reviewed; never live in the game loop. Needs your decision and an API key. | M |

### T. Technical tools and charts

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| T1 | Volume bars and a crosshair | Basics of any trading screen. | Volume under the candles (P7), a crosshair with open, high, low, close and volume. | S |
| T2 | Indicators | Taught everywhere. | Moving averages (20, 50, 200; simple and exponential), VWAP, Bollinger bands, RSI, MACD, ATR; computed in the page from the candles. | M |
| T3 | Drawing tools | Marking levels and trendlines is how traders find setups. | Horizontal levels, trendlines, channels, Fibonacci retracements and notes, saved per player and stock, usable on phones. | M |
| T4 | Risk tools on the chart | Position sizing and a stop are the first habits to teach. | Click to set entry, stop and target; the page shows the risk-reward ratio and the position size for a chosen risk (for example 1% of the account), and places the bracket order (brackets already exist). | M |
| T5 | Multi-timeframe and comparison | Setups are read across timeframes and against the index. | Linked timeframes, an index or sector overlay, relative strength. | S |
| T6 | Alerts on levels and indicators | Waiting for a setup should not mean staring at a chart. | Alerts when price crosses a drawn level or an indicator condition is met, in the page and by email (O1). | M |
| T7 | A setup screener | Finding setups is a skill to practise. | Scans for stocks near support or resistance, breakouts, squeezes, RSI extremes, gaps and new highs or lows. | M |
| T8 | Replay mode | Practising on the past, bar by bar, is the best teaching tool there is. | Pick a stock and a past period, step through it bar by bar and trade it in a separate practice account (the contest's paper-account code is a base); needs a longer price history (T9) and a deterministic engine (E5). | L |
| T9 | Longer price history | Technical work needs months of daily bars; charts keep the last 500 candles per timeframe. | Keep daily candles for many game years, and minute candles for longer than now, in a compact store. **Done as TA-A10 (2026-10-21).** | M |
| T10 | Options | Calls and puts are how traders bet on a move, or on a quiet spell, with a known most-you-can-lose. | **Done (2026-10-21), for everyone:** an Options tab on each stock page; five expiries (to 90 game days), listed strikes that stay while new ones are added, quotes that follow the stock every second, Black-Scholes-Merton on the forward (drift, dividends) with a skew, a term structure that follows the volatility clustering and the earnings crush; every Greek a share and per contract (click a call or a put), the chance of finishing in the money, open interest and a payoff chart; quotes that flash green or red as they tick; whole contracts of 100 shares (2026-10-23); cash-settled at expiry; bought and sold back, not written; no free money on the real engine (HOW_IT_WORKS §4). Next, if wanted: writing options with margin, spreads as one order (verticals, straddles), American style with early exercise, an options lesson. | M |
| T11 | Leverage | Real accounts trade on margin; it is the lesson about risk that matters most. | **Done (2026-10-21), Pro:** up to 10x on any listing but the leveraged products, isolated per position, interest on the loan, closed at the market when its margin halves, the price where that happens shown on the position (§4). See section 4, risk 7. | M |
| T12 | Trading bots (Expert) | Turning a rule into code is how traders test and discipline themselves. | **Done (2026-10-21):** up to 5 bots, each with up to 10 rules in a small safe language (candles, 20 indicators, crosses, the account, a news score from the player's own words), trading shares, leverage and options through the same code as a click; stops, targets and a daily trade cap (§10.12). Next, if wanted: alerts from a rule (T6), sharing bots, a bot leaderboard. | L |
| T13 | Backtests (Expert) | Seeing how a rule did in the past, and that it usually stops working, teaches more than any lesson. | **Done (2026-10-21):** a bot run over the kept candles (up to 5,000, three real days of 1m) with the game's own fees, leverage and option prices, against just holding (§10.12). Next: longer intraday history, walk-forward (fit on one stretch, test on the next) to show overfitting. | M |

### L. Learning: lessons and challenges (the journal was removed on 2026-10-20)

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| L1 | A curriculum | What to teach, in what order. | Levels: basics (orders, long and short), risk (stops, sizing, R multiples), market structure (trends and ranges), support and resistance, breakouts and false breakouts, volume, indicators, chart patterns, macro (rates, inflation, jobs), earnings, psychology (fear of missing out, revenge trading), a trading plan and a journal. | S |
| L2 | Lessons | Short, interactive and tied to the live market. | One page per topic, with examples taken from the game's own recent charts ("NVXA bounced off support here yesterday"), ending in a challenge. | L |
| L3 | A challenge engine | Challenges teach by doing and pay free MB (M5). **Partly done: the quest ladder (2026-10-14, `ladder.py`): 30 one-off quests in Bronze, Silver, Gold and Diamond tiers, paying more as they go up, with Diamond titles and name colours (HOW_IT_WORKS §10.11).** | Challenges defined in a content file: an objective checked from the ledger, orders and positions (execution: "a stop on every trade today"; risk: "risk at most 1% per trade for ten trades"; setups: "buy within 1% of a marked support and exit at 1R or more"; macro: "trade the CPI reaction"; consistency: "a positive week with a drawdown under 5%"), a time window, prerequisites, a reward and caps. Built on the existing quests and achievements code; each challenge tested against ways to game it. | L |
| L4 | A trade journal | Reviewing trades is how traders improve. | Every trade logged with the setup tag, a note, the chart at entry and exit, the R multiple, the best and worst point while open; statistics by setup; a weekly review. **Removed (2026-10-20, on request): the journal, its page, challenges and ladder quests are gone.** | M |
| L5 | A skill profile | Progress should be visible as skill, not just balance. | Win rate, average R, expectancy, profit factor, largest drawdown, risk discipline (stops used, risk per trade), over time and by setup. **Dropped with the journal (2026-10-20); a skill profile would now be built from the trade history instead.** | M |
| L6 | Spot-the-setup exercises | Pattern recognition is practised quickly with feedback. | Show a past chart ("support or resistance?", "break or bounce?"), reveal what happened next; small capped MB rewards. | M |
| L7 | A coach | Feedback after a trade turns mistakes into lessons. | Rule-based remarks first ("you bought into resistance with no stop"); an LLM coach later if you want one (needs an API key). | M |
| L8 | Onboarding | New players need a first good trade, with a stop. | A short first-run path: what MB are, the market, a first trade with a stop, the journal. | S |
| L9 | A glossary | Words like "short", "R", "VWAP" stop beginners. | Tooltips and a glossary page. | S |
| L10 | Content tooling | Lessons and challenges will be written often. | A validator for the lesson and challenge files and a preview command. | S |

### S. Classrooms, community and competition

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| S1 | Classrooms | Teachers, schools and trading clubs are the natural buyers of a teaching site (and an income that does not depend on losses, B2). | A teacher account, a class with a join code, assigned lessons and challenges, a class leaderboard and a progress dashboard, optionally a class's own market. | L |
| S2 | Leaderboards that reward skill | Raw returns reward luck and size; the old risk-adjusted board was removed on request when the goal was different. | Rank by return on money put in (purchases cannot buy rank; the existing return formula already counts credits as money put in), plus a risk-adjusted or consistency board and leagues by level. Your decision. | S |
| S3 | Challenge weeks instead of the daily race | The daily paper-money race was a contest for medals. | Weekly themed events with the same starting balance for everyone and a skill objective; reuses the contest's paper-account code (X5). | M |
| S4 | Sharing ideas | Explaining a trade is learning too. | Share a trade idea (a chart with levels and a plan) with followers, delayed; a discussion room per stock. | M |
| S5 | Streaks, levels and titles | Long-term motivation. | Tied to lessons and challenges, never to balance. | S |

### U. Interface

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| U1 | Phone, second step | Trading on a phone still means the Buy button on each card. | A pull-up trade ticket with the risk tools (T4), an installable web app, a check on real phones. | M |
| U2 | Notifications | Messages vanish after a few seconds. | A persistent list, sounds, browser notifications for fills, alerts and challenge results. | S |
| U3 | A "while you were away" summary | Coming back should show what happened. | Equity change, filled orders, macro releases and news on holdings, challenges finished. | S |
| U4 | A desktop trading screen | Technical traders want several charts. | Saved layouts with chart panes, watchlist, calendar, positions. | L |
| U5 | Accessibility, light theme, languages | Wider reach. | Arrows beside colours, keyboard shortcuts, a light theme, translations of the interface and lessons. | M |
| U6 | Market overview pages | Seeing the whole market is a skill. | A heatmap, an MSI 50 page, a stock page with the "why it moved" line, levels and the calendar. | M |
| U7 | Low-data mode | 18 MB an hour on mobile data. | Pause when hidden, send only visible rows, compress. | S |
| U8 | A look that stays consistent | Pages built at different times drift apart in sizes, colours and wording. | **Done (2026-10-14): a polish pass over every page** (the stock page puts price, trade bar and chart first; one progress-row style; green and red only for numbers that are not zero once rounded; the admin page in the game's colours; plurals written out; HOW_IT_WORKS §11, *Consistency rules*). Repeat it after each big feature: screenshot every page on a laptop and a phone and fix what looks out of place. | S |
| U9 | A look of its own | The pages look like a generic AI-built dashboard: dark navy, bright blue, pills, emoji, rounded cards in rounded cards, small grey capital headings and a paragraph of help under every heading. | **Done (2026-10-18): the trading-terminal look** (checklist below). | M |

#### U9 checklist: a look that is not "AI-generated"
**Done (2026-10-18), in the trading-terminal direction** (HOW_IT_WORKS §11, *The look*). Checked page by page with laptop and phone screenshots; element ids kept so the tests still pass.

**The decision: the trading terminal** (chosen 2026-10-18). The two options were: A *financial newspaper* look (cream or off-black paper, a serif for headlines, thin rules) or a *trading terminal* look (black, one accent colour, a monospaced face for numbers, dense rows). Every item below follows from that choice.

Colour, type and shape
- [x] Replace the stock palette (navy `#0a0e14`, bright blue `#5aa2ff`, mint green and coral red) with our own, starting from the logo's teal; drop the soft radial glow behind every page.
- [x] Replace Inter / Segoe UI with two typefaces that have character: one for headings, a tabular or monospaced one for prices and figures.
- [x] Fewer pills: chips, buttons, badges, tabs and the market-status chip are all fully rounded (11 places). Square-ish buttons, tabs that look like tabs.
- [x] Fewer boxes: every section sits in a rounded card with a drop shadow, and figures sit in more rounded tiles inside it (the `finance-grid`). Use rules, whitespace and flat tables instead.
- [x] Headings: the small grey capital letter-spaced label over every section ("YOUR HOLDINGS", "EARNINGS HISTORY") is a template look. Use real headings of different sizes.
- [x] Buy and Sell: the see-through green and red buttons with coloured borders. Solid, plainer buttons; the colour in one place.
- [x] The gold gradient PRO badge, the ✔ ticks and the → arrows on links.

Icons and emoji
- [x] The emoji industry icons on every market row and chip (💻 ⛽ 💊 🛡️ ✈️ 🏦, from `content/base.json`): simple drawn icons, or none (the ticker is enough).
- [x] The emoji on achievements, medals and the ladder (🏅 🔒 🥉 🥈 🥇 💎 🚩): drawn badges in the new style.

Words
- [x] Cut the help paragraph under every heading (Learn, Calendar, Journal, Shop, Profile, the contest, chat) to one short sentence, or a small "?" that opens it; the long explanations live in the lessons and on the about page.
- [x] Fewer "X: Y" sentences ("They reward habits, not luck: ...", "Pre-market: trading is thin, so ...") and fewer "not X, but Y" ones. Write the way a person would say it.
- [x] The about page is the standard AI landing page: a pill tag, a two-line giant headline, six feature cards in a 3 x 2 grid and an FAQ of fold-outs. Lead with a real screenshot of the market and the chart, then a few plain paragraphs. (Done as plain text and a ruled list; the screenshot is still to do, as the server serves only the two brand images.)

Layout and personality
- [x] Not everything the same size and spacing: the market and stock pages dense like a trading screen (shorter rows, a tighter header), the lessons laid out like an article.
- [x] The header's seven identical stat boxes: one compact strip of figures.
- [x] One signature detail only Meme Street has, for example a scrolling ticker tape of prices under the header, or the news wire set like a newspaper column.
- [x] Charts and the admin page in the same new style.

### E. Engineering

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| E1 | The price process as its own module | Track P rewrites the core; today it is spread through a 3,600-line `engine.py`. | Move price generation (noise, regimes, levels, news reactions) behind one interface with its own tests, keeping the rest of the engine as it is. First step of the P track. | L |
| E2 | Split the big files | `engine.py` and `index.html` are hard to change safely. | Modules for prices, news, orders, accounts, indices; the page's CSS and JavaScript in their own files. **Started (2026-10-21): the chart's JavaScript is in `web/chart.js` (TA-F2) and the price history in `game/history.py`; `engine.py` is still one file.** | L |
| E5 | Determinism and replay | Calibration (P11), replay mode (T8) and bug reports need repeatable markets. | A seeded random stream per market and a tool that replays any period. | M |
| E6 | Observability | Alerts only while someone looks at the dashboard. | Structured logs, metrics, alerts for drift, late ticks and errors. | M |
| E7 | Content tooling | Packs are edited by hand. | A validator and a preview for content packs. | S |
| E8 | Admin follow-ups | Admin actions are limited. | Credit, refund, freeze a player, an audit log of every admin action, per-player CSV, longer chart history. Needed for purchases and refunds. | M |
| E9 | Rough edges | Small things that add up. | Sparklines reset on restart, the news wire is not saved, the content files are checked every tick (an every-few-seconds check is enough), achievement counters since the last snapshot are lost in a crash. | S |
| E10 | Scale the game server | Gateways carry connections; the market is one process. | Only when needed (around 4,000 players): engine in its own process, Postgres, per-client subscriptions. | L |
| E11 | Ledger housekeeping | The ledger only grows. | Rotation of the equity-curve table, a restore drill, a snapshot-versus-ledger check. | S |
| E12 | A faster test suite and CI that passes | 16 minutes locally; the GitHub run fails. | Parallel runs, per-test time limits, a quick subset; fix the failing GitHub run (its summary page lists the failures) and run the browser tests there. **Done (2026-10-19, takes effect once pushed): four parallel parts, a 30-minute limit, a failed test run once more on its own (flaky ones are marked, real failures fail), failures as annotations anyone can read, newer actions.** | M |
| E13 | Lint, types and error tracking | Mistakes are found only when a test hits them. | Ruff, a light mypy pass, an error tracker. **Done (2026-10-21): Ruff (errors, warnings, pyflakes) and a light mypy pass, both clean and both in CI; a built-in error tracker (`game/errortrack.py`) groups every logged error for the admin page (`/api/admin/errors`). A hosted tracker such as Sentry needs an account of yours.** | S |

### O. Running memestreet.net

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| O1 | Real email | Passwords cannot be recovered; challenge and purchase receipts need email. | A Resend account and its DNS records, then `deploy/set_mail.ps1` (ready). | S |
| O2 | Daily backups off the server | `deploy/pull_backups.ps1` exists but only runs when started. | A daily Windows scheduled task (one line in `deploy/DEPLOY.md`), and the provider's own backups. **Done (2026-10-19): `deploy/schedule_backups.ps1` set up the daily task on this computer (09:00, or when it is next on; keeps the newest 60). Still yours: the provider's own backups (Hetzner console, about 20% of the server price).** | S |
| O3 | An uptime monitor | Nobody is told if the site stops. | UptimeRobot on `https://memestreet.net/api/health` (ready). **Done (2026-10-19): a GitHub Actions check every 15 minutes (`.github/workflows/uptime.yml`, emails on failure; starts once pushed). UptimeRobot on top is still worth it for faster, phone alerts.** | S |
| O4 | Cloudflare in front | Shield and country information. | Proxy on, `TRUST_PROXY`, static caching. **Server ready (2026-10-19): Caddy believes `CF-Connecting-IP` only from Cloudflare's addresses, live and in `deploy/Caddyfile`. Still yours: the Cloudflare account and the name servers (DEPLOY.md, *Cloudflare in front*).** | S |
| O5 | Safer updates and a staging copy | Updates go straight to the live game. | Tests before upload, a one-command rollback, a staging site. **Done (2026-10-19): every upload keeps the code it replaces and `deploy/rollback.ps1` puts it back; `upload.ps1 -Staging` runs the new code on the server next to the live game, on a copy of the newest backup, through a tunnel. Tests before upload stay a habit (the GitHub run).** | M |
| O6 | Harden the server | Payments raise the stakes. | SSH keys only, fail2ban, rotated keys, a list of secrets and where they live. **Done (2026-10-19): ssh was already keys-only; fail2ban now guards ssh; the list of secrets and how to change each is in DEPLOY.md.** | S |
| O7 | Payment webhooks that never lose a purchase | A missed webhook is a customer who paid and got nothing. | Signed, idempotent, logged, retried; a daily reconciliation against the provider (pairs with M3). **Built (2026-10-19): the payment check four times a day against Stripe's list of paid checkouts, completing missed orders exactly once, with a line and a Check now button on the admin page; receipts after every completed order.** | S |
| O8 | Capacity and status | Know the limits; tell players about outages. | A load test, a cost table, a status page. | M |
| O11 | Reset the live game for the new rules | 8 accounts are on 10,000 MB and the old market. | Announce, back up, reset everyone to 1,000 MB when M1 and the new market ship (the admin reset already exists). | S |

### R. Rules, legal and player protection

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| R1 | Terms, privacy and disclaimers | No rules exist yet, and 8 people have signed up. | Terms (MB have no cash value, cannot be cashed out or transferred; purchase and refund terms), a privacy policy, and an education disclaimer (fictional companies, not investment advice), linked from every page and accepted at sign-up. **Built (2026-10-19, not yet live): `/terms`, `/privacy`, a footer on every page, the notice at sign-up and the version recorded per account (HOW_IT_WORKS §10.9). Live since 2026-10-20 with the contact email memestreet.game@gmail.com and no operator name or country (on request). Still to do: have a lawyer read both (R4).** | S |
| R2 | An age policy | Trading education attracts teenagers; selling them currency needs rules. | A minimum age (for example 13 to use the site and 18, or parental consent, to buy), an age question at sign-up and at checkout, and a privacy approach for young users (UK Children's Code, US COPPA if under 13 is allowed: easier not to). Your decision. | S |
| R3 | Consumer rules for digital purchases | Required where you sell. | Prices with tax shown before buying, receipts, the EU and UK right to withdraw (waived with consent when MB are delivered at once), a refund policy; a merchant of record (M3) takes most of this on. **Built (2026-10-19): the right-to-cancel waiver in the checkout tick, kept with each order; receipts by email once O1 is on; refunds in the terms. Still open: tax shown with prices, which depends on M3.** | S |
| R4 | A short legal check | Much smaller than the old question, but still worth an hour of a lawyer's time. | Confirm that selling a game currency that can never be cashed out, with skill-based play and MB-only rewards, is not gambling where you sell; and what an education site may say in adverts. | S |
| R5 | Responsible spending | People who lose may chase losses with money. | Spending caps and cool-offs (M6), no purchase prompts at a loss, a spending history, a clear note that buying MB does not make anyone a better trader. | S |
| R6 | Abuse and duplicate accounts | Free MB invite farming. | A captcha at sign-up, grouping accounts by address and device, rewards only for verified accounts. **Built (2026-10-19): a hidden-field trap for sign-up bots and `rewards_need_email` (turn on with O1). Skipped: a captcha service and per-address reward caps, because MB cannot be moved between accounts, so extra accounts gain nothing; revisit with referrals (B5).** | M |
| R7 | Data rights | Players should be able to leave. | Download my data, delete my account. | M |
| R8 | A "how this market works" page | Transparency builds trust, and explaining the simulation teaches too. | What drives prices (drift, regimes, macro, levels, psychology), what is random, and that player trades never move prices. | S |

### B. Business and growth

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| B1 | Package prices | The income. | Decide the price of each package (with a better rate for bigger ones), a first-purchase offer if wanted, regional pricing. Your decision. | S |
| B2 | Income that does not depend on losses | Package sales fall as teaching improves. | Classroom seats (S1) and/or a Pro tier (replay, advanced indicators, journal analytics, more alerts). Your decision. | S |
| B3 | Subscriptions | Monthly income that does not depend on losses. | **Done (2026-10-23):** Pro US$9.99 and Expert US$29.99 a month, renewing until cancelled (Stripe subscriptions; a Cancel button; renewals by webhook and the daily check), or US$99.99 and US$299.99 a year in one payment; the Shop page cut to the packages, the passes and the purchases, with the age and consent rules in a box at Buy. Next: a reminder email before a yearly pass ends, a way to switch between monthly and yearly. | M |
| B3 | A landing page and lessons people can find | A teaching site grows through search and shared lessons. | Public lesson pages, a landing page that says what it is (not "free", not "get rich"), share cards. | M |
| B4 | A funnel with purchases | The admin funnel counts sign-ups and trades only. | Add first purchase, buyers per 1,000 sign-ups, average spend per buyer, out-of-money to purchase rate, refunds, cohorts by week. | S |
| B5 | Referrals | Word of mouth. | Invite links with a capped MB reward for both after the friend verifies and completes a first lesson. | M |
| B6 | Email that teaches | Bringing people back with value. | Welcome path, weekly review, the daily wrap, challenge and purchase receipts, an unsubscribe link. | M |
| B7 | Community | Somewhere to talk and announce. | A Discord with the daily wrap and challenge results. | S |
| B8 | Teachers and creators | Each brings a group. | Classrooms (S1) with a free trial, a creator programme. | M |
| B9 | Name and brand | "Meme Street" was chosen for a meme-stock game. | Decide whether to keep it for a teaching site; check trademarks and domains either way. Your decision. | S |

### X. Retire from the old plan

| # | What | How | Size |
|---|---|---|---|
| X1 | The real-money plan | Dropped: crypto deposits and withdrawals, KYC and identity checks, the house capital rule, reserve alarms, provably fair seeds, the gambling licence question, country blocking for real money. Nothing to remove in code except the comments that still describe it. | S |
| X2 | Moonshots and two-outcome catalysts | Lottery tickets do not teach trading. Remove from the default market (or move to an opt-in speculative section); retire catalysts and industry-wide two-outcome shocks once the macro engine (N2-N4) gives the market its big days. | M |
| X3 | The "no edge" rule and its tools | **Done (2026-10-13):** `sim.py`, `bots.py`, `edge.py`, `paired.py`, `tune.py` and the probes were removed; `realism.py` and `chart_check.py` (MARKET_REALISM.md) replace them. | S |
| X4 | `revenue_model.py` | **Done (2026-10-13):** removed (it modelled fee income); M7 will model package and Pro sales. | S |
| X5 | The daily paper-money contest | Becomes challenge weeks (S3). | S |
| X6 | The 10,000 MB start | 1,000 MB (M1). | S |
| X7 | 3x products and very risky instruments | Keep for advanced players with clear warnings, or remove. Your decision. | S |
| X8 | The house-risk panel as a capital tool | Becomes a positioning view (M9). | S |
| X9 | Admin "withdraw" | No cash-out: keep only as an admin correction, renamed. | S |

---

## 6. Suggested order

Since 2026-10-13 the order follows section 1A: technical analysis first. Phases 0, 1, 3 and 4 of the earlier order are
largely built (section 3); what remains of them is listed under "Alongside". **Phase 1 (chart basics) was done on
2026-10-19 and Phase 2 (structure) on 2026-10-21; Phase 3 is next.**

| Phase | Focus | Items | Done when |
|---|---|---|---|
| 1. Chart basics (1-2 weeks) | **A chart a trader is at home on** | TA-B1 crosshair, TA-B2 chart types, TA-B3 indicator settings, TA-B9 the Pro decision, TA-B4 drawing tools saved to the account, TA-B6 trades on the chart, TA-A1 level calibration, TA-E1 to TA-E3 news turned down | A trader can read, draw and mark up any chart, on a laptop or a phone, and the market's levels hit their targets |
| 2. Structure (3-5 weeks) | **Charts that teach** | TA-A2 more kinds of level, TA-A4 volume, TA-A5 candles, TA-A6 timeframes that agree, TA-A7 gaps, TA-A3 named patterns, TA-A8, TA-A9 the pattern suite, TA-A10 longer history, TA-A11 game-time timeframes (later taken out) | Each pattern appears at its target rate with a realistic success rate, and no simple pattern rule beats holding the index |
| 3. Trading on the chart (2-3 weeks) | **Plan, place and manage a trade where you see it** | TA-B5 trade from the chart, TA-B7 alerts, TA-B12 the trading screen, TA-E4 why it moved | A player can go from spotting a setup to a sized, bracketed order without leaving the chart |
| 4. Learning around the chart (3-4 weeks) | **Lessons, exercises and feedback on real charts** | TA-C1 to TA-C7 | The curriculum is technical first, every lesson shows real game charts, and the coach comments on trades |
| 5. Depth and fun (ongoing) | **Screener, replay, competitions** | TA-B8 screener, TA-B10 layouts, TA-B11 replay, TA-D1 to TA-D3, S1 classrooms | Players can find, rehearse and compete on setups |
| Alongside | **Rules, money and operations** | R1 terms and privacy (before the shop opens), O1 email, O2 daily backups, O3 monitor, M3 choice of payment provider, M7 pricing model, TA-F1 to TA-F3, E2, E5, E6, E9-E13, O4-O8 | The shop can open safely |

---

## 7. Open questions (your decisions)

| Question | Options | What would decide it |
|---|---|---|
| What does Pro include, now that technical analysis is the core? | Keep the four advanced indicators Pro-only; **make every standard indicator and drawing tool free and sell convenience and depth (screener, alerts, layouts, replay, pattern statistics)** (recommended); no Pro. | Whether learners can learn the whole subject without paying (TA-B9). |
| How visible should chart patterns be? | Textbook-clear (easy to learn, easy to exploit); realistic (often messy, often failing); a gentler practice market for beginners (P13). | Teaching value against "no free money" (TA-A3, TA-A9). |
| Which timeframes should the chart offer? | **Decided 2026-10-21: real time only** (game time was built and taken out again). | (TA-A11) |
| What do the packages cost? | For example 100 MB for a small amount up to 10,000 MB with a better rate; one currency or regional prices. | What comparable learning apps charge, and how fast 1,000 MB runs out in the new market (M7). |
| What happens when an account runs out? | Only buying more; a free restart on a timer (for example once a week); a free restart after finishing a risk lesson. | Whether the site should earn from losses or from wanting more capital (section 4, risk 2). |
| Should there be a second income? | Classroom seats; a Pro tier; neither. | Interest from teachers and clubs; what the packages bring in. |
| What is the minimum age, and the age to buy? | 13 to use and 18 to buy; 16 and 18; 18 for everything. | The audience you want, and the privacy rules for young users. |
| How many free MB can challenges give? | A weekly budget per active player (for example 200-500 MB), one-time rewards for first lessons. | The pricing model (M7) and how often people buy. |
| How fast should the market grow? | About +8% per game year for the index (with a 365-day game year that is about +36% per real month); slower; or a longer game year so the drift is gentler in real time. | Whether "slowly upwards" should be visible within a week of play or only over months. |
| Costs: a flat fee or commission plus spread? | Keep 0.1% per side; a realistic commission and spread; spreads that widen in fast or thin markets. | Teaching value versus simplicity (M8). |
| Keep 3x products, shorting and very risky instruments? | Keep everything for advanced levels; unlock by level; remove 3x. | How advanced the audience is (X7). |
| Leaderboards: what do they rank? | Return on money put in (purchases cannot buy rank); a risk-adjusted board (removed earlier on request); consistency; leagues by level; **leverage: count it as it is (today), cap it on the boards, or a separate board for leveraged accounts** (section 4, risk 7). | Whether you want to reward skill over luck. |
| Keep the name "Meme Street"? | Keep; rename for a teaching audience. | Who you want to reach (B9). |
| Moonshots? | Remove; keep as an opt-in speculative section. | Whether lottery-like stocks belong in a training market (X2). |
| An AI coach? | Rule-based only; an LLM coach (an API cost per player). | The cost per player and what it adds (L7). |

---

## 8. Checking a market change

The old market's edge tools (`edge.py`, `paired.py`, `probe.py`) were removed on 2026-10-13 with the zero-edge rule;
`HOW_IT_WORKS.md` section 17 keeps their last results as history. For the market today:

1. The test suite (`python -m unittest discover tests`), which guards money conservation, the ledger and the rule that
   player trades never move prices.
2. `python tools/chart_check.py 12 <seed>` on two or three seeds: the charts against the facts of real prices
   (MARKET_REALISM.md section 4 has the targets and the last results).
3. The realism suite (P11, `python tools/realism.py`): stylised facts, pattern rates within their target bands, and the "no free money" strategy
   comparison against holding the index, costs included, on markets never used for tuning.
4. A look at the charts by a person: does it look like a market a trader would recognise?
5. Update `HOW_IT_WORKS.md` and this file.
