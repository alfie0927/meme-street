# Meme Street roadmap

**Goal (new, 2026-10-13):** a website where people **learn to trade by trading** a realistic, fictional stock market. The
market behaves like a real one: it drifts slowly upwards over time, with corrections, bear phases and long sideways
stretches; scheduled economic news (interest-rate decisions, inflation, jobs) moves it; and prices respect and break
support and resistance the way real charts do, so the setups traders are taught actually appear and can be practised.
Everyone starts with **1,000 MB**. Players who run out, or want more capital, **buy MB packages** (100, 500, 1,000,
5,000 or 10,000 MB). **Challenges award free MB** for completing them. MB are a game currency: they have no cash value and
are never paid out.

**What this replaces.** The old plan was a real-money trading game: buy MB with crypto, withdraw winnings, the house as a
counterparty earning a fee, and every mechanism built as a fair bet so that nobody could have an edge. That plan is
dropped. Section 2 lists what changes and what happens to the code that was built for it.

Companion doc: `HOW_IT_WORKS.md` describes what the code does **today** (still the old fair-bet market, until the tracks
below change it). Update it after every change, and check this file before starting any work.

Size key: **S** = under a day, **M** = a few days, **L** = a week or more.

---

## 1. The new plan on one page

| | |
|---|---|
| **Who it is for** | People who want to learn to trade without risking their own money: beginners, students, people preparing for a real account, classes and trading clubs. |
| **What they do** | Trade a live market of invented companies, indices, ETFs and commodities with real tools (charts, indicators, drawing, orders, stops, position sizing), follow lessons, complete challenges, keep a journal and see their skill improve. |
| **How the site earns** | Selling MB packages (100 / 500 / 1,000 / 5,000 / 10,000 MB). Prices are your decision (B1). A second income that does not depend on people losing (classroom seats, a Pro tier) is recommended (B2). |
| **How the market behaves** | Slow long-run upward drift; regimes (bull, correction, bear, sideways); scheduled macro data and rate decisions with consensus and surprise; fewer, more meaningful headlines; technical structure (support and resistance tested, bounced or broken, false breakouts, retests, trends, volatility squeezes, gaps) and the psychology behind it (overreaction, panic, euphoria, stop runs). |
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

## 3. Where things stand (2026-10-13)

What already exists and carries over unchanged: a tick engine (1 tick = 1 second, 30-minute game days in pre-market,
regular session and after-hours, a 365-day game year), 193 listings in 30 sectors with invented companies (CEOs, products,
supplier and rival links, evolving financials, quarterly earnings on a calendar, company events), the MSI 50 index, sector
indices, ETFs and 2x/3x products; long and short trading, limit, stop-loss, take-profit and bracket orders; accounts with
passwords and email verification (mail not yet switched on), a read-only visitor view and `/about`; portfolio, history
with CSV, watchlist, leaderboards, achievements and quests, profiles, following and a moderated chat; a phone layout; a
crash-proof money ledger; gateways for many connections; an admin dashboard (house, machine health, activity, players,
security); and the live site **https://memestreet.net** (Hetzner, Caddy, admin behind a second password, `/api/health`,
six-hourly backups pulled to the D: drive by `deploy/pull_backups.ps1`). 793 tests run in a few minutes per file and in
about 16 minutes all together.

What does **not** fit the new plan yet: the price process (built to have no direction and no structure), the news mix, the
starting balance, the lottery listings, the contest, the edge checks and the money flow (no purchases).

Not done at all: payments, the macro economy, technical tools on the chart, lessons, challenges with rewards, a journal,
classrooms, terms and privacy pages, real email, an uptime monitor, daily automatic backups.

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
| M7 | A pricing model | `revenue_model.py` models fee income, which is no longer the income. | Replace it with a model of package sales: share of players who buy, package mix, how often accounts run out (from the market's difficulty and the bust rule), free MB from challenges; output per 1,000 sign-ups and its sensitivity to each assumption. Fill it with real numbers after M3 ships. | S |
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
| N6 | An economic calendar page | Scheduled events are only useful if players can see them coming. | Upcoming releases and earnings with consensus; after the release, the actual, the surprise and how the market reacted. | S |
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
| T9 | Longer price history | Technical work needs months of daily bars; charts keep the last 500 candles per timeframe. | Keep daily candles for many game years, and minute candles for longer than now, in a compact store. | M |

### L. Learning: lessons, challenges and the journal

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| L1 | A curriculum | What to teach, in what order. | Levels: basics (orders, long and short), risk (stops, sizing, R multiples), market structure (trends and ranges), support and resistance, breakouts and false breakouts, volume, indicators, chart patterns, macro (rates, inflation, jobs), earnings, psychology (fear of missing out, revenge trading), a trading plan and a journal. | S |
| L2 | Lessons | Short, interactive and tied to the live market. | One page per topic, with examples taken from the game's own recent charts ("NVXA bounced off support here yesterday"), ending in a challenge. | L |
| L3 | A challenge engine | Challenges teach by doing and pay free MB (M5). | Challenges defined in a content file: an objective checked from the ledger, orders and positions (execution: "a stop on every trade today"; risk: "risk at most 1% per trade for ten trades"; setups: "buy within 1% of a marked support and exit at 1R or more"; macro: "trade the CPI reaction"; consistency: "a positive week with a drawdown under 5%"), a time window, prerequisites, a reward and caps. Built on the existing quests and achievements code; each challenge tested against ways to game it. | L |
| L4 | A trade journal | Reviewing trades is how traders improve. | Every trade logged with the setup tag, a note, the chart at entry and exit, the R multiple, the best and worst point while open; statistics by setup; a weekly review. | M |
| L5 | A skill profile | Progress should be visible as skill, not just balance. | Win rate, average R, expectancy, profit factor, largest drawdown, risk discipline (stops used, risk per trade), over time and by setup. | M |
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

### E. Engineering

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| E1 | The price process as its own module | Track P rewrites the core; today it is spread through a 3,600-line `engine.py`. | Move price generation (noise, regimes, levels, news reactions) behind one interface with its own tests, keeping the rest of the engine as it is. First step of the P track. | L |
| E2 | Split the big files | `engine.py` and `index.html` are hard to change safely. | Modules for prices, news, orders, accounts, indices; the page's CSS and JavaScript in their own files. | L |
| E5 | Determinism and replay | Calibration (P11), replay mode (T8) and bug reports need repeatable markets. | A seeded random stream per market and a tool that replays any period. | M |
| E6 | Observability | Alerts only while someone looks at the dashboard. | Structured logs, metrics, alerts for drift, late ticks and errors. | M |
| E7 | Content tooling | Packs are edited by hand. | A validator and a preview for content packs. | S |
| E8 | Admin follow-ups | Admin actions are limited. | Credit, refund, freeze a player, an audit log of every admin action, per-player CSV, longer chart history. Needed for purchases and refunds. | M |
| E9 | Rough edges | Small things that add up. | Sparklines reset on restart, the news wire is not saved, the content files are checked every tick (an every-few-seconds check is enough), achievement counters since the last snapshot are lost in a crash. | S |
| E10 | Scale the game server | Gateways carry connections; the market is one process. | Only when needed (around 4,000 players): engine in its own process, Postgres, per-client subscriptions. | L |
| E11 | Ledger housekeeping | The ledger only grows. | Rotation of the equity-curve table, a restore drill, a snapshot-versus-ledger check. | S |
| E12 | A faster test suite and CI that passes | 16 minutes locally; the GitHub run fails. | Parallel runs, per-test time limits, a quick subset; fix the failing GitHub run (its summary page lists the failures) and run the browser tests there. | M |
| E13 | Lint, types and error tracking | Mistakes are found only when a test hits them. | Ruff, a light mypy pass, an error tracker. | S |

### O. Running memestreet.net

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| O1 | Real email | Passwords cannot be recovered; challenge and purchase receipts need email. | A Resend account and its DNS records, then `deploy/set_mail.ps1` (ready). | S |
| O2 | Daily backups off the server | `deploy/pull_backups.ps1` exists but only runs when started. | A daily Windows scheduled task (one line in `deploy/DEPLOY.md`), and the provider's own backups. | S |
| O3 | An uptime monitor | Nobody is told if the site stops. | UptimeRobot on `https://memestreet.net/api/health` (ready). | S |
| O4 | Cloudflare in front | Shield and country information. | Proxy on, `TRUST_PROXY`, static caching. | S |
| O5 | Safer updates and a staging copy | Updates go straight to the live game. | Tests before upload, a one-command rollback, a staging site. | M |
| O6 | Harden the server | Payments raise the stakes. | SSH keys only, fail2ban, rotated keys, a list of secrets and where they live. | S |
| O7 | Payment webhooks that never lose a purchase | A missed webhook is a customer who paid and got nothing. | Signed, idempotent, logged, retried; a daily reconciliation against the provider (pairs with M3). | S |
| O8 | Capacity and status | Know the limits; tell players about outages. | A load test, a cost table, a status page. | M |
| O11 | Reset the live game for the new rules | 8 accounts are on 10,000 MB and the old market. | Announce, back up, reset everyone to 1,000 MB when M1 and the new market ship (the admin reset already exists). | S |

### R. Rules, legal and player protection

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| R1 | Terms, privacy and disclaimers | No rules exist yet, and 8 people have signed up. | Terms (MB have no cash value, cannot be cashed out or transferred; purchase and refund terms), a privacy policy, and an education disclaimer (fictional companies, not investment advice), linked from every page and accepted at sign-up. | S |
| R2 | An age policy | Trading education attracts teenagers; selling them currency needs rules. | A minimum age (for example 13 to use the site and 18, or parental consent, to buy), an age question at sign-up and at checkout, and a privacy approach for young users (UK Children's Code, US COPPA if under 13 is allowed: easier not to). Your decision. | S |
| R3 | Consumer rules for digital purchases | Required where you sell. | Prices with tax shown before buying, receipts, the EU and UK right to withdraw (waived with consent when MB are delivered at once), a refund policy; a merchant of record (M3) takes most of this on. | S |
| R4 | A short legal check | Much smaller than the old question, but still worth an hour of a lawyer's time. | Confirm that selling a game currency that can never be cashed out, with skill-based play and MB-only rewards, is not gambling where you sell; and what an education site may say in adverts. | S |
| R5 | Responsible spending | People who lose may chase losses with money. | Spending caps and cool-offs (M6), no purchase prompts at a loss, a spending history, a clear note that buying MB does not make anyone a better trader. | S |
| R6 | Abuse and duplicate accounts | Free MB invite farming. | A captcha at sign-up, grouping accounts by address and device, rewards only for verified accounts. | M |
| R7 | Data rights | Players should be able to leave. | Download my data, delete my account. | M |
| R8 | A "how this market works" page | Transparency builds trust, and explaining the simulation teaches too. | What drives prices (drift, regimes, macro, levels, psychology), what is random, and that player trades never move prices. | S |

### B. Business and growth

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| B1 | Package prices | The income. | Decide the price of each package (with a better rate for bigger ones), a first-purchase offer if wanted, regional pricing. Your decision. | S |
| B2 | Income that does not depend on losses | Package sales fall as teaching improves. | Classroom seats (S1) and/or a Pro tier (replay, advanced indicators, journal analytics, more alerts). Your decision. | S |
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
| X3 | The "no edge" rule and its tools | Replaced by the realism and "no free money" suite (P11). Until P11 exists the old checks still guard the old market. | S |
| X4 | `revenue_model.py` | Superseded by the pricing model (M7); kept until then. | S |
| X5 | The daily paper-money contest | Becomes challenge weeks (S3). | S |
| X6 | The 10,000 MB start | 1,000 MB (M1). | S |
| X7 | 3x products and very risky instruments | Keep for advanced players with clear warnings, or remove. Your decision. | S |
| X8 | The house-risk panel as a capital tool | Becomes a positioning view (M9). | S |
| X9 | Admin "withdraw" | No cash-out: keep only as an admin correction, renamed. | S |

---

## 6. Suggested order

| Phase | Focus | Items | Done when |
|---|---|---|---|
| 0. Now (this week) | **Decide, protect, stop building on the old model** | Your decisions (B1 prices, B2, R2 age, M4 the out-of-money rule, X7, B9 name), O1 email, O2 daily backups, O3 monitor, R1 terms and privacy | The live site has rules, mail and a monitor; the open questions in section 7 are answered |
| 1. Market, version 1 (2-4 weeks) | **A market that drifts, cycles and reacts to the economy** | E1, P1, P2, P3, P12, N1, N4, N2, N3, N5, N6, P7, P11 (first targets), T1, T2 | The realism suite passes; the market goes up over game years with corrections, bears and ranges; rate decisions, CPI and jobs reports move it; you are happy with how it feels |
| 2. Technical structure (3-6 weeks) | **Levels, trends, squeezes and psychology** | P4, P5, P6, P8, P9, P10, T3, T4, T5, T7, N7, N9 | Support and resistance tests, breakouts, false breakouts and retests appear at target rates, and no simple rule prints money |
| 3. The learning loop (2-4 weeks) | **1,000 MB, lessons, challenges with rewards, a journal** | M1, O11, M2, M5, L1, L2 (first ten lessons), L3, L4, L5, L8, L9, S3 | A new player can learn, practise, complete challenges, earn MB and review their trades |
| 4. Paid MB (2-3 weeks) | **Packages, safely** | R2-R5, M3, M4, M6, O7, E8, B4, M7 | A first small group can buy packages; receipts, refunds and limits work; the funnel shows buyers |
| 5. Grow | **Classrooms, replay, search** | S1, T8, T9, E5, B2, B3, B5, B6, U1-U4, L6, L7 | Teachers run classes; lessons bring visitors |
| Alongside | **Engineering and operations** | E2, E6, E9-E13, O4-O8, U7 | |

---

## 7. Open questions (your decisions)

| Question | Options | What would decide it |
|---|---|---|
| What do the packages cost? | For example 100 MB for a small amount up to 10,000 MB with a better rate; one currency or regional prices. | What comparable learning apps charge, and how fast 1,000 MB runs out in the new market (M7). |
| What happens when an account runs out? | Only buying more; a free restart on a timer (for example once a week); a free restart after finishing a risk lesson. | Whether the site should earn from losses or from wanting more capital (section 4, risk 2). |
| Should there be a second income? | Classroom seats; a Pro tier; neither. | Interest from teachers and clubs; what the packages bring in. |
| What is the minimum age, and the age to buy? | 13 to use and 18 to buy; 16 and 18; 18 for everything. | The audience you want, and the privacy rules for young users. |
| How many free MB can challenges give? | A weekly budget per active player (for example 200-500 MB), one-time rewards for first lessons. | The pricing model (M7) and how often people buy. |
| How fast should the market grow? | About +8% per game year for the index (with a 365-day game year that is about +36% per real month); slower; or a longer game year so the drift is gentler in real time. | Whether "slowly upwards" should be visible within a week of play or only over months. |
| Costs: a flat fee or commission plus spread? | Keep 0.1% per side; a realistic commission and spread; spreads that widen in fast or thin markets. | Teaching value versus simplicity (M8). |
| Keep 3x products, shorting and very risky instruments? | Keep everything for advanced levels; unlock by level; remove 3x. | How advanced the audience is (X7). |
| Leaderboards: what do they rank? | Return on money put in (purchases cannot buy rank); a risk-adjusted board (removed earlier on request); consistency; leagues by level. | Whether you want to reward skill over luck. |
| Keep the name "Meme Street"? | Keep; rename for a teaching audience. | Who you want to reach (B9). |
| Moonshots? | Remove; keep as an opt-in speculative section. | Whether lottery-like stocks belong in a training market (X2). |
| An AI coach? | Rule-based only; an LLM coach (an API cost per player). | The cost per player and what it adds (L7). |

---

## 8. Checking a market change

Until the realism suite (P11) exists, changes to the *old* market are still checked the old way (the test suite, then
`edge.py`, `paired.py`, `probe.py`; `HOW_IT_WORKS.md` section 17 has the method and the last results). For the new
market:

1. The test suite (`python -m unittest discover tests`), which guards money conservation, the ledger and the rule that
   player trades never move prices.
2. The realism suite (P11): stylised facts, pattern rates within their target bands, and the "no free money" strategy
   comparison against holding the index, costs included, on markets never used for tuning.
3. A look at the charts by a person: does it look like a market a trader would recognise?
4. Update `HOW_IT_WORKS.md` and this file.
