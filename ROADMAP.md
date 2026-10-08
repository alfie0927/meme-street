# Meme Street roadmap

Goal: a trading game where players buy memebucks (MB) with crypto and trade fictional stocks. The house earns the 0.1% fee on every trade. No strategy based on public information should be able to win reliably, and the game should feel like a living market: prices that follow stories, news that reads like news, and enough variety that a session stays interesting.

Companion doc: `HOW_IT_WORKS.md` describes what the code does today. Update it after every change, and check this file before starting any work.

Size key: **S** = under a day, **M** = a few days, **L** = a week or more.

---

## 1. Where things stand (2026-10-08)

| Area | State |
|---|---|
| Economy | Every trade fills at the market price against the house. Token conservation holds (drift about 1e-10). Fees are the house's revenue. No price impact from players. Edge-checked on 35 strategies (the original 10, probes for gaps, reversals, ETFs, leveraged products, volatility and earnings, for the opening jump, moonshots, distress, catalysts, industry shocks and the hidden company links, and one that trades with bracket orders): see section 6 for the latest result. Overnight check (2026-10-06): 300 fresh markets x 36 strategies, a catalyst probe and an index probe found no edge (`HOW_IT_WORKS.md` §17.9). Every mechanism (volatility clustering, trading sessions, the opening jump, major-event limits, indices and ETFs, moonshots, catalysts, company events, orders, social features and the paper contest) was built so its expected effect on a price is exactly zero, and the house reserve is kept in proportion to the money at stake. |
| Trading | Long and short, % chips plus an MB amount box, average entry price, **on the market page, the stock page and the holdings page**. **No position limits** (removed on request): the only cap is your cash (a short is paid for out of cash as collateral: no margin multiple, no borrow pool), plus borrow fees and margin calls for shorts. **Fee 0.1% per side** (it was 0.5%). **The market never closes**: a 30-minute cycle on the real clock is 5 minutes of thin pre-market, 20 of regular session (a burst of volume and a jump at the open) and 5 of thin after-hours. **Orders**: limit buy/sell, stop-loss, take-profit and one-click brackets, filled at the market price when triggered. **Trading never pauses** (the circuit breakers were removed on request). |
| Prices | One random-walk "fair" price per stock: three-factor noise scaled by the session, slow mean reversion, news shocks, spillovers, **volatility clustering**, a soft daily limit that **opens up for very strong events**, and distress as a fair rescue-or-bankruptcy bet (a rescue is a doubling, not a ten-fold jump). There are no stock splits any more; share offerings change only the share count. **Moonshots** (tiny, pre-revenue companies with 260-550% volatility that can move hundreds of per cent in a day, go bankrupt easily and keep listing) rare **catalysts** (trial results, approvals, buyouts, audits, tests: a fair bet: the good news gains 10-35%, a setback costs a few per cent, and a rare disaster (6-8% of them, with its own much worse headline) costs 20-70%; a moonshot's is a two-outcome bet up to about +130%) and rare **industry-wide shocks** (a ban, a demand collapse, a probe, a disruptive technology: a fair two-outcome bet that moves every company in a sector together, with no market component, so an industry can crash while the market rises). Hedge assets (gold, bonds) have negative beta. |
| Listings | **193 listings at the start of a game**: 152 companies and funds in 30 sectors (**eight of them imaginary industries**: teleportation, weather engineering, time technology, dreams and memory, dragons and creatures, deep-ocean cities, antigravity, alchemy), 5 commodities, 32 derived assets (the **MSI 50**, which follows the 50 largest companies by market value and is re-ranked every game day; 21 sector indices, 6 themed ETFs, 4 leveraged/inverse products: 2LMSI, 2SMSI, 3LMSI, 3SMSI) and 4 moonshots, with new moonshots listing every ~15 minutes (**NEW** badge for 30 minutes). Indices and ETFs track total return (dividends included). |
| Companies | Every company has a CEO, CFO, flagship product and home city; stories name them and they recur (a CEO who resigned is named later). Companies are also linked by **hidden supplier, customer and rival links** that make sense (a drug maker supplies a hospital chain, an oil producer an airline), that players never see, that decide who appears together in two-company stories and that spill a little of each move over to partners and rivals; a new listing is linked in and its partners get the matching link. Revenue, margin, cash, debt and share count evolve at earnings: **quarterly (31.5 real hours, give or take a few days), spread so there are a few every game day and one is always coming up, and only before the open or after the close**; dividends, buybacks and offerings follow. **Scheduled company events** (guidance updates, investor days, analyst calls, product events) fall between the reports, on the public calendar with no hint of direction. Banks rate stocks from a hidden safety score and the financials, and give a reason for a new price target about 40% of the time. |
| News | 68 templates, 20 company-story kinds, 4 company-event kinds, 5 two-company story kinds, 7 rare catalyst kinds, 7 industry-wide shock kinds, 8 named sources. Headlines are built from slots (names, products, cities, synonyms), so the same story reads differently each time, and none of them talks about the game's own bookkeeping. A hidden mood tilts good vs bad (move size scaled so the expected move is zero). Stories come back as UPDATE or REVERSAL that quote the original. No headline ever repeats. |
| Players | **Accounts with passwords** (scrypt hashes, 30-day sessions, login and sign-up limits, a flag for accounts that share an address, admin password resets), **verified email** (a mailed code proves an address, one account per address, throwaway-mail domains refused, a forgotten password is recovered with a mailed code; `email_mode` off / optional / required), **10,000 MB to start**, and a **Day** (what was a season) that lasts one real day. **Portfolio page** (equity curve, allocation, realised vs unrealised, best and worst trades), **trade history** with filters and CSV download (delisted stocks keep a page you can open from it), **search, sort and watchlist** on the market, **leaderboards** (day and all-time), **achievements and daily quests**, a **daily contest** (everyone trades the same 10,000 MB of paper money under the real rules; medals only), **public profiles** (private by default; holdings shown only after a delay), following, and a **moderated global chat** (a filter that sees through disguises, a trade-first gate, three reports remove a message and mute its author, appeals, a moderator log). All rewards are cosmetic: no social feature touches money or prices. |
| Server | The engine runs in worker threads behind one lock, so a slow tick can't freeze the websockets. Clients get one full `init` and then a small `tick` each second (about 5 kB instead of 120 kB), each socket has its own writer so a slow client never blocks anyone, notices and chat are reliable messages. A crash loses nothing: every money event goes to an append-only SQLite ledger and is replayed after the last snapshot. The save keeps the chart candles in their own file so saving a full-size game takes about 140 ms, not 2.4 s. One process carried 400 simulated players at about half a core (`tests/capacity.py`). **Gateways**: `python launch.py --gateways N` runs the game server plus N gateway processes that hold the players' websockets and spread the work of sending updates over several cores (`HOW_IT_WORKS.md` §12). **Live at https://memestreet.net** (a rented Hetzner server, https through Caddy, backups every six hours, `deploy/upload.ps1` updates it with one command). It can still be shared from your own computer with `python share.py`. **Phones**: below 760 px wide the pages become cards, with a compact pinned header and a chart drawn for a small screen. Admin dashboard with alerts, charts, server timings, a house-risk report, chat moderation with appeals, accounts, email and mail, and a reset-to-Day-1 button. |
| Checks | `sim.py` (36 strategies, one of which cheats by reading the hidden company links), `bots.py` (100 bots per random strategy over many seeds, the moonshot-sniper study), `edge.py`, `paired.py`, `probe.py`, `tune.py`, `catalyst_probe.py` and `index_probe.py` (engine-only checks of what a stock does after a big move and whether the index drifts). A test suite of 740 tests in `tests/` (engine, volatility and sessions, news, wild stocks, industry shocks, company links, the earnings calendar, company events, orders, contests, accounts, email, moderation, house risk, saving, reset, ledger, portfolio, wire protocol, social, server, gateways, browser, stress, capacity and slow checks; the server-side suites can also be run through gateways with `MS_TEST_GATEWAYS=2`) that never touches your save file, and a GitHub workflow that runs it. |

Not done: wallet- or phone-verified accounts, a managed database server, real money, real email (the live site has none yet), legal pages, protection for `/admin` beyond its key, and off-site backups. Tracks I, J and K below list what a public, paid launch still needs.

---

## 2. The biggest problems right now

The earlier lists have been worked through: accounts with passwords and verified email, fixed-balance contests, stronger chat moderation, company events, order types, the house's tail risk, the single-process server (gateways), the live server, the MSI 50 and the phone layout are all done. What is left, ranked by how much it could hurt the game, the house or the business:

| # | Problem | Why it matters | Fix (see track) |
|---|---|---|---|
| 1 | **The live site is open to the world but not ready for strangers.** `/admin` is protected only by its key, nothing sends email, there are no terms, privacy policy or age check, and the only backups are on the same server. | One leaked key or one dead disk ends the game; strangers need rules to agree to before any money is involved. | K1, K2, K3, K4, J1 |
| 2 | **A visitor cannot see the game before signing up.** The first thing anyone sees is a sign-in box. | You pay (in time or money) for every visitor and lose most of them before they see a single price. | I6, I1 |
| 3 | **How the game earns money is still only "the 0.1% fee".** Nothing models what a player is worth, and nothing else is planned. | Every pricing, bonus and marketing decision needs a number. | A13, I2, I4 |
| 4 | **A lucky win on a moonshot is still possible, just smaller.** The tails are thinner and the reserve is topped up automatically, but with no position limits a fair bet can still be a big one. | The reserve floor is a capital decision for real money. | A12, A15 |

Finished items keep their old IDs in the tables below, so completed ones (A1-A5, A7, A8, A9, B1, B2, B3, B4, B5, B7, B8, B11, C1, C3, C4, C11, D1, D2, D3, E2, E3, E4, E5, E9, F1, F2, F3, F4, F5, F7, F8, F9, G1, G2, G3, G4) are simply missing. C2, D4, E8 and G10 are partly done, as noted.

---

## 3. Improvement tracks

### A. Economy and risk (do first: everything else builds on it)

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| A6 | Optional price impact for very large trades | Without it, size is free. **This is your decision**: it conflicts with the "player trades never move prices" rule, so it was deliberately left alone. | A tiny square-root impact term above a threshold, restored by fair value (never counted as news). | M |
| A12 | The house capital rule for real money | **New numbers (`HOW_IT_WORKS.md` §17.7):** 100 players who all buy every new moonshot (1,000,000 MB of capital) cost the house a worst case of -4.4 million MB in one 6-hour market (a standard deviation of 974,000 MB), because winners reinvest; the average is zero. Thinner tails, an automatic reserve top-up (the larger of 10% of the players' equity and half the stress loss) and the admin risk report are in. With real money the floor is not free: someone has to fund it. | Decide the capital the operator is willing to put behind the game, whether the floor fraction should be higher, and whether the stress loss should page you. Optionally a per-stock cap on the *house's* exposure (a rule about the house, not a limit on any player). | S |
| A10 | Admin dashboard follow-ups | The dashboard has server timings, the house-risk panel, chat moderation with appeals, accounts, password resets and a game reset, but no protection against key guessing and no audit log of admin actions other than moderation. | Rate-limit and log failed admin keys; add actions (credit, withdraw, freeze a player) with an audit log; export any player's trades as CSV. (The house's exposure by stock is on the page now.) | M |
| A11 | ETF realism | Indices and ETFs are free to hold: no expense ratio, no creation/redemption, no tracking difference. | Decide whether an expense ratio (a small, known, house-favouring drag) is wanted; if so show it on the stock page. | S |
| A13 | Revenue model: what is a player worth? | The only income is the fee, and nothing says how much a player pays per day. The simulator already has 36 kinds of player. | Treat each strategy as a player type (the retail, news-chasing, bracket-trading and buy-and-hold ones), give each a share of the player base, and report fees per player per day at 0.05%, 0.1%, 0.2% and 0.3%. Add a whale scenario (one big player) against the reserve. Output a one-page table you can plan prices with. | S |
| A14 | Fee tiers and promotions | A flat fee treats a 100-trades-a-day player like a once-a-week one, and a launch needs something to give away. | Optional volume discounts, a first-week fee holiday and referral rebates, all as a fee change only (never a price change). Keep a floor, because the fee is also the cushion against any undiscovered edge; re-run `edge.py` after any change. | S |
| A15 | Reserve alarms and a house-side safety switch | The reserve is topped up automatically, but nothing warns you or slows the house's exposure when a few players are winning big. | Page the admin (phone push or email) when the reserve falls below half its floor or the stress loss passes a limit; an admin switch that stops new moonshot listings and widens the floor. It is a rule about the house, not a limit on any player. | S |

### B. Price movement mechanics

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| B6 | Richer correlations | A single market factor plus sector is simplistic. (Industry-wide shocks, §7.14 of `HOW_IT_WORKS.md`, now let a sector move on its own, but they are one-off news, not a standing factor.) | Add factors: rates sensitivity, oil, dollar, risk-on/off. Give each stock exposures. Use them for hedges (gold vs dollar, bonds vs rates, airlines vs oil) instead of one fixed beta. | L |
| B9 | Realistic commodity behaviour | Oil, gas and grain have seasons and supply shocks. (The old slow commodity drift was removed: it was a momentum edge, see `HOW_IT_WORKS.md` 6.1.) | Scheduled inventory reports, OPEC-style meetings and weather shocks as *news* (zero expected move, like every other story), not as a drift; tie airlines and utilities to them. Anything that makes a commodity's next move predictable is an edge and must not come back. | M |
| B10 | Interest rates as a real variable | "Rates" is only a news template today. | A visible policy rate that changes on scheduled dates; affects bonds, banks, growth stocks and gold through the factor model (B6). | L |
| B12 | A public volatility gauge ("the fear index") | Volatility already clusters (calm stretches and storms), but players cannot see it, so a storm just feels random. | Show a realised-volatility gauge for the MSI 50 in the header and on the market page (calm / normal / stormy, from the last hour). It tells size, not direction, so it gives no edge (check with `edge.py`). Optionally a tradable volatility product later. | S |

### C. News and storytelling

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| C2 | Optional LLM headlines (**not done, needs your decision and an API key**) | Highest variety for the least writing. The slot grammar (C1) already gives thousands of surface forms, so this is now a nice-to-have. | Offline step that pre-generates a few thousand headlines per template and tone, reviewed and loaded as content packs (no live calls in the game loop). It can't be done inside the repo without an LLM service, so it was skipped. | M |
| C5 | Multi-part arcs with stages | Today follow-ups are one-step. | Arc templates: probe, hearing, ruling; clinical trial phase 1, 2, 3; **mergers and takeovers** (a rumour, a bid at a premium, regulators, approval or collapse; the target is then delisted at the deal price). Players can read the stage and trade the odds; zero expected move at each stage. | L |
| C6 | Scheduled macro calendar | Central bank dates, jobs reports and earnings seasons give structure. | A calendar page and "Upcoming events" entries, with outcomes drawn at the event. Pair with B10. | M |
| C7 | Sources with track records | Every rumour has the same 75% credibility. | Named sources (a rumour mill, a respected wire) with a hidden accuracy that the player can learn from their history; keep the average at zero edge. | M |
| C8 | Analyst consensus and "beat/miss" | Earnings today say "beat" or "missed" with no expectation. | Publish a consensus estimate before each report; the price reacts to the surprise against it. | M |
| C9 | Headlines that name the cause of a move | "Why is X down?" should be answerable from the wire. | Attach each news item to the move it caused (a small "-1.2%" badge on the headline, filled in after the tick). | S |
| C10 | News filters and a ticker-specific feed | The wire is one stream of 30 items. | Filter by sector, watchlist and holdings; search; infinite scroll with saved history (the wire isn't saved today). | M |
| C12 | Index changes as news | A real index announces who joins and who leaves; the MSI 50 re-ranks silently every game day. | A wire item at each re-rank ("Chronos Labs joins the MSI 50; Beamline Couriers leaves"). The price effect stays zero: the re-rank uses prices that are already known and news is only a headline. Check that nothing trades on it. | S |
| C13 | A daily wrap ("Meme Street Close") | There is no summary of a day: the biggest movers, the story of the day, the index, the best trader. A recap is also the best email and share card. | Write it automatically at the end of each game day from the day's data, show it on the market page and keep an archive. Feeds I7 (email digest) and I8 (the community channel). | S |
| C14 | Rating changes and price targets as a page | Banks rate stocks and give targets, but only as one-line news. | A page that lists every rating change and target by bank, with each bank's hit rate so far (keep the average at zero edge, as with C7). | S |

### D. Number and variety of stocks

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| D4 | IPO calendar and delisting cycle (partly done) | Moonshots already list every ~15 minutes and bankrupt ones are replaced. Ordinary IPOs and an announced calendar are missing. | Scheduled IPOs of ordinary companies announced days ahead (with a pricing story), an "IPO calendar" page, and more kinds of generated company (small caps, SPAC-like names). | M |
| D5 | Company personalities | Many stocks read the same. (The hidden supplier / customer / rival links already give each company a place in a web of partners.) | Per-company traits: dividend payer, serial acquirer, meme favourite, cyclical, defensive; each changes which stories it gets and how it reacts. | M |
| D6 | Options (much later) | The classic next instrument. | Only after the core economy is proven safe; needs a pricing model and strict risk limits. | L |
| D7 | More listings | 150 companies is plenty to browse, and eight imaginary industries are in. A few real-world themes are still thin. | More content packs (copy `pack_fiction.json`'s or `pack_growth.json`'s shape): international, small caps, more imaginary industries. | S each |
| D8 | A moonshot index | Moonshots are the most exciting thing in the game, but you have to pick one and most go bust. | A tradable basket (equal weight of the moonshots that are listed, dropping the bankrupt ones at their payout price), with its own page. Like every ETF it is a fair bet. | S |
| D9 | Sector and size indices beside the MSI 50 | The MSI 50 follows the top of the market; there is nothing for the middle and the bottom. | An "MSI Mid 100" (ranks 51 to 150) and a small-cap basket with the same weighting and re-rank rules, and 2x/inverse products only if people ask. | S |

### E. UI and UX

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| E1 | Chart upgrades | Missing basics for a trading screen. (There are no volume bars on stock charts; the activity chart of the trading cycle that the market page briefly had was removed on request.) | Volume bars (trade counts), crosshair with OHLC readout, line/area toggle, moving averages, compare with the index, drawing of the average line for each lot. | M |
| E6 | Mobile layout, second step | The phone layout is done (card rows, compact pinned header, readable chart, folded news; `HOW_IT_WORKS.md` §11). Left: trading from the market still means tapping the Buy button on each card, and the game cannot be installed on the home screen. | A pull-up trade ticket (size chips and amount in one sheet), a web app manifest so it installs like an app, and a check on real phones (Safari and Chrome). | S |
| E7 | Onboarding | New players land in a table with no guidance. | A 3-step first-run tour, a glossary tooltip for "short", "cover", "margin", "beta", and a safe "practice" mode. | S |
| E8 | Notifications (partly done) | Achievement, quest, contest and margin messages now stack in the corner and are delivered reliably, but they vanish after a few seconds. | A persistent notification list, optional sound, and browser notifications for margin calls and followed stocks. | S |
| E10 | Accessibility and theme | Colour-only up/down and a single dark theme. | Arrows beside colours, keyboard shortcuts for buy/sell/cover, light theme, reduced-motion option. | S |
| E11 | Make the stock page richer | Key facts are spread out. | Sections for "why it moved today", next earnings date, rating history with the bank that changed it, and related stocks. | M |
| E12 | Charts for portfolio and profiles | The equity curve is a plain line. | Drawdown shading, a benchmark line (the index), trade markers on the curve, a longer history than one day. | M |
| E13 | A market heatmap | The market page is a list of 193 rows; there is no way to see the whole market at a glance. | A page of tiles sized by market value and coloured by the 30-minute change, grouped by sector, click to open a stock. Uses numbers the page already receives. | S |
| E14 | An MSI 50 page | The index is new and nobody can see what is in it. | A page with the 50 members, their weights, how much each added to today's move, and who joined or left at the last re-rank (pairs with C12). | S |
| E15 | A screener and movers | Finding a stock means scrolling or searching. | Filters (sector, volatility, P/E, dividend yield, market value, held by me), top gainers and losers, and "most traded by players" (delayed and as shares of the total, never sizes, so it hands nobody a signal). | M |
| E16 | Price alerts and watchlist alerts | You have to keep the page open to notice a price. | "Tell me when X passes Y" and "tell me about news on my holdings", delivered in the page, by email and by browser push (pairs with E8 and I7). Alerts only report; they never trade. | M |
| E17 | A "while you were away" summary | Returning players land in the same table as always, with no sign of what happened. | On sign-in: your equity change since the last visit, orders that filled, news on what you hold, quests and the new day. It is the main reason to come back tomorrow. | S |
| E18 | Sound and touch feedback | Fills, margin calls and big news are silent. | Optional sounds and phone vibration for fills, margin calls and breaking news on your holdings, off by default. | S |
| E19 | Light theme, languages and number formats | One dark theme and English only, for a game meant to be global. | A light theme (with E10), translated pages (start with Spanish, Portuguese, Turkish and German; the news stays English), and local number formats. | M |
| E20 | A desktop trading screen | Power users want several charts and a watchlist side by side. | A customisable layout (a few chart panes, watchlist, news, positions) with saved layouts. Much later. | L |
| E21 | Low-data mode for phones | The game sends about 5 kB a second, which is 18 MB an hour on mobile data. | Pause updates when the tab is hidden, slow them to every few seconds on request, send only the rows that are on screen, and compress the messages (pairs with G10's per-client subscriptions). | S |

### F. Game design and social

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| F6 | Days with themes | A day is just a leaderboard reset. | Themed days or weeks (a bubble, a recession, a rate-hike year) that change regime odds; announced at the start. | M |
| F7 | Contest formats and prizes | The daily contest is fair (same paper balance for everyone, real rules) but only pays a medal. | A weekly contest, a contest with limited instruments, team entries, and MB prizes only after the legal review (H phase 4). | M |
| F10 | More quests and achievements | 21 achievements and 8 quest types will be done in a few days. | Weekly quests, hidden achievements, seasonal badges, a profile showcase. | S |
| F11 | A chat room for each stock | One global chat mixes everything; a stock's own page is where people want to talk about it. | A chat room on each stock page (the same filter, reports and mutes as the global chat), with the most active rooms listed. | M |
| F12 | Friends and private leagues | A leaderboard of strangers is weak; a league of friends is what makes people come back and invite others. | A league with an invite code, its own day and all-time boards, and an optional paper-money format. Streamers and groups can host one (pairs with I9). | M |
| F13 | Streaks, levels and titles (cosmetic only) | Quests give a reason to come once a day but nothing builds up over weeks. | Streak counters, levels from trades and quests, profile titles. Never anything that pays MB or changes a price. | S |
| F14 | Head-to-head challenges | Players cannot challenge a friend. | "Beat me this week": two players (or a player and the index) on the same paper balance, one winner, medals only. | M |
| F15 | Bring your own bot (API keys) | Players who write trading programs have no way in, and an outside AI cannot connect at all. | Personal API keys with rate limits, a read-only market feed, a paper account and a live account, and a separate "bots" leaderboard so they do not compete with people. | L |
| F16 | An academy | New players do not know what shorting, margin or an ETF is. | Short lessons linked from the page (with E7's tour), each ending in a paper-trade exercise. | S |

### G. Engineering and operations

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| G5 | Replays and determinism | Hard to reproduce a bug or an exploit. | The ledger already records every money event; add a seeded RNG per session and a replay tool that reconstructs any hour. | M |
| G6 | Observability | Tick time and send time are on the admin page; there are no logs or alerts in production. | Structured logs, metrics export, alerts on invariant drift, late ticks and a negative house reserve. | M |
| G7 | Config and content tooling | Content is edited by hand in JSON. | A validator for content packs (missing sectors, bad betas, duplicate tickers) and a content-preview command that simulates a pack for an hour. | S |
| G8 | Fix known rough edges | Small things that add up. | Sparklines reset on restart; the global news wire isn't saved; removing a company from content drops holders' shares; old `rating_review_days` setting still in packs; the "Upcoming events" list shows only earnings; achievement counters since the last snapshot are lost in a crash (money is not). | S |
| G9 | Run the browser test in CI and add more flows | The GitHub workflow runs the test suite, but the browser test depends on a browser being present. | Install headless Chrome in the workflow; add flows for mobile width. | S |
| G10 | Scale the game server itself (partly done) | **Gateways are done** (`python launch.py --gateways N`, `HOW_IT_WORKS.md` section 12): the connections and the once-a-second sending run in as many processes as you like, and the game server alone then carries roughly 4,000 ordinary players (one process alone, about 1,600). What is left: the market is still one process with one lock, one core and one SQLite file. | Only when one core stops being enough (the next ceiling, around 4,000 players): move the engine to its own process with a message queue for trades, Postgres instead of SQLite, and per-client subscriptions so only the visible prices are sent. | L |
| G11 | Ledger housekeeping | The ledger only grows (the admin Reset makes a backup, but there is no scheduled one). | Daily backup, rotation of the equity-curve table, a restore drill, and a command that checks a snapshot against the ledger. | S |
| G12 | Stop re-checking the content files every tick | Every tick the engine reads the modification time of every content file. In a simulation that is wasted work, and with 14 processes at once it made Windows refuse a read ("insufficient system resources") and crashed a study. | Check at most every few seconds (a `content_reload_seconds` setting), and not at all in `sim.py`. | S |
| G13 | Keep the game's data out of OneDrive | The project folder lives inside OneDrive, which sometimes holds `state.json` open ("could not replace state.json") and could create conflicted copies of the ledger. | An environment variable (`MS_DATA_DIR`) for where the save, charts, ledger and backups live, with a default outside the synced folder, and a note in the docs. | S |
| G14 | A faster, steadier test suite | The suite takes 16 to 25 minutes, once got stuck for 50 minutes without saying where, and two full runs a day is a lot of waiting. | A per-test time limit that names the stuck test, the files run in parallel processes, the browser tests marked so they can be skipped, and a quick "smoke" subset (about 2 minutes) for small changes. | M |
| G15 | Split the two big files | `engine.py` is about 3,600 lines and `index.html` is one 960-line file with very long lines. Changes are slow to review and easy to get wrong. | Split the engine into modules (prices, news, orders, accounts, indices) with the same behaviour, and move the page's CSS and JavaScript into their own files. No behaviour change; the tests are the safety net. | L |
| G16 | Linting and type checks | Mistakes like a missing variable are only found when a test happens to hit them. | Ruff and a light mypy pass in the CI workflow, fixing what they find once. | S |
| G17 | Error tracking | An exception in production is only a line in a log file. | Send unhandled exceptions to a tracker (Sentry's free tier or a self-hosted one) and group repeats; tie to K4's alerts. | S |

### H. Launch track (from the earlier roadmap, still valid)

| Phase | What | Done when |
|---|---|---|
| 1. Closed play-money test (weeks 1-2) | The game is live at https://memestreet.net with a fresh market (2026-10-06). First finish K1 to K4 and J1 below, then invite 5-10 people (`python share.py` is still there for a game on your own computer), keep `signup_bonus` at 10000. Watch `invariant_drift`, `fees`, `liquidity_pnl`, `players_pnl`, the house-risk panel, the server timings on the admin page and one player topping every day. | 10+ testers, no crashes for 24 hours, nobody wins every day |
| 2. Hardening (weeks 3-5) | Set `email_mode` to `required` and put real mail (SMTP) behind it before anyone relies on it (done: passwords, sessions, sign-up and login limits, an address-sharing flag, verified email with one account per address, password recovery by email); wallet or phone verification before real money; rate limits on trades and on admin-key guesses (A10); a permanent HTTPS host (the files are in `deploy/`; you buy the domain and rent the server) with searchable logs and daily backups (G11: the six-hourly backup job is in `deploy/`; an off-site copy and a restore drill are not); CI test from `sim.py` (drift under 1e-6); mobile pass (E6). | Done for the email part: a forgotten password is recovered without the admin. Still to do: a permanent host, backups, mobile |
| 3. Public beta, play money (weeks 5-8) | Open signups; measure daily active players, trades per player and fees per player; re-tune `event_mean_seconds`, `news_move_ranges`; ship content packs regularly; watch chat reports (F8). | Stable retention and a healthy house reserve |
| 4. Legal gate | Lawyer's opinion, per country, on gambling or skill-gaming licences, money transmission and virtual-asset rules (KYC/AML), whether withdrawable fictional "stocks" raise securities or derivatives issues, terms of service, age limits, and the privacy of public portfolios and chat. | Written sign-off. Do not build payments before this. |
| 5. Real money | Crypto deposits on `Engine.credit` (after on-chain confirmations); withdrawals on `Engine.debit` (manual approval, daily caps); `signup_bonus` to 0; daily reconciliation (on-chain balance at least player cash plus equity); low caps at launch. | Numbers hold at each cap raise |

### I. Business and growth

The game is meant to make money, so these are about getting players, keeping them and knowing what each one is worth. Nothing here changes a price.

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| I1 | A landing page | The site opens straight into a sign-in box, so a visitor never learns what Meme Street is. | A public page that says what it is in four sentences (it is not free to play), shows screenshots and the live MSI 50, explains how the fair market works, and has a sign-up button, a waitlist box and links to the terms (J1). | S |
| I2 | Decide how it earns | Fees are the plan today and nothing else is modelled. | Compare (a) the fee (done), (b) paid-entry contests with a rake (needs the legal sign-off, H phase 4), (c) cosmetic items such as themes, badges and chat colours, (d) a "Pro" subscription (alerts, extra charts, the API of F15), (e) deposit or withdrawal fees. Use A13's numbers. This is your decision. | S |
| I3 | A referral programme | Word of mouth is the cheapest way to grow. | Invite links. A reward that cannot be farmed: a cosmetic for both sides after the friend verifies an email and makes a first trade (with real money, never free MB). | M |
| I4 | A funnel and retention page in the admin | There is no count of visitors, sign-ups, first trades or returning players. | Privacy-friendly counts from the game's own data: visitors, sign-ups, verified, first trade, back on day 1 / 7 / 30, trades and fees per player, and a cohort table. No third-party scripts. | M |
| I5 | Share cards and link previews | A shared link to the site shows a bare address in chat apps. | Preview tags (title, description, image) for stock pages, profiles and the leaderboard, and a "my day" image (return, rank, best trade) that is made to be posted. | M |
| I6 | Let visitors watch before they join | The sign-in box hides the market, so nobody sees a price before giving a name. | A read-only market for logged-out visitors (prices, charts, the news wire, the leaderboard), with "sign in to trade". Also gives search engines pages to index, and each page its own title and description. | M |
| I7 | Email that brings people back | Email is built for codes only; the live site sends none yet (K2). | A welcome, the daily wrap (C13), margin-call and filled-order notices, a "we miss you" after a week away, with an unsubscribe link that works. | M |
| I8 | A community channel | Players have nowhere to talk outside the game, and you have nowhere to announce things. | A Discord or Telegram server with a bot that posts the daily winners, the wrap and big breaking stories (a webhook, no player data). | S |
| I9 | Tools for streamers and groups | One streamer with an audience is worth many ads. | Private leagues with a code (F12), a custom contest they can name, and an overlay page for a stream. | M |
| I10 | The name and the brand | "Meme Street" is not yet checked for conflicts, and only `memestreet.net` is registered. | A trademark search in your target countries, the `.com` and common variants if free, matching social handles, and a one-page brand kit (logo, colours). Not code. | S |

### J. Trust, rules and player protection

Needed before strangers (and certainly before real money). None of it changes a price.

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| J1 | Terms, privacy policy and an age check | The site has no rules and no age limit. | A terms page, a privacy policy, a risk warning, a "you are 18 or older" box at sign-up, and links in a footer. Have them read by a lawyer before real money. | S |
| J2 | Block places you cannot serve | Real-money games are restricted in some countries. | With Cloudflare in front (K5) the country of each visitor is known: show a notice and refuse sign-up and deposits from blocked countries. | S |
| J3 | Responsible play tools | A game people pay into must let them set limits. | Player-set deposit, loss and time limits, a cool-off period, self-exclusion, a session reminder, and a "what I have put in and taken out" page. | M |
| J4 | Two-step sign-in and identity checks | A password is not enough to guard money. | Authenticator-app codes for sign-in and withdrawals, then identity and sanctions checks through a provider before the first withdrawal (H phase 4 and 5). | L |
| J5 | A "how we keep it fair" page | Trust is the product when money is involved, and the proof is already in the repository. | A plain page with the no-edge rules, the results of the many-market studies, the house's running profit against its fees, and a download of every stock's price history so anyone can test it. | S |
| J6 | Provable fairness | Players have to take it on trust that prices are not steered. | Publish a hash of each hour's random seed before it starts and reveal the seed afterwards, so anyone can replay the hour and confirm the prices. Needs G5 (a seeded, replayable engine). | L |
| J7 | Data rights | Players should be able to take their data or leave. | Download all my data, delete my account (positions closed, history anonymised), and a stated retention period. | M |
| J8 | Stopping abuse | Fake and duplicate accounts are the usual way a bonus or a contest is cheated. | A captcha on sign-up (Cloudflare Turnstile is free), grouping accounts by device and address with a review list in the admin, and limits that tighten when something looks wrong. | M |
| J9 | Admin roles and an audit log | Everything in the admin works with one key. | Separate admin and moderator roles, an audit log of every admin action (A10), and a second person's approval for large withdrawals. | M |

### K. Running memestreet.net

The live server is a single rented machine (`deploy/DEPLOY.md`). These make it safe to leave running.

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| K1 | Protect `/admin` | The admin page is open to the internet behind one key, and the key was shown in a chat once. | A password or an address allow-list in front of it in Caddy, a new `ADMIN_KEY`, and a lock-out after failed tries (A10). Do this first. | S |
| K2 | Real email | The live site cannot send mail, so accounts cannot be verified and a forgotten password cannot be recovered. | A mail provider (Resend, Postmark or SES), the SPF, DKIM and DMARC records for memestreet.net, `MAIL_*` settings on the server, then `email_mode` to `optional`. | S |
| K3 | Backups somewhere else | The six-hourly backups sit on the same disk as the game, so one dead disk loses both. | Copy them nightly to another place (Hetzner Storage Box or object storage), an alert if a copy is missing, and a restore drill onto a spare machine (G11). | S |
| K4 | Know when it is down | Nobody is told if the site stops, the disk fills or the reserve goes negative. | An outside uptime check on the `/health` address that messages your phone, disk and memory alerts, and log rotation. | S |
| K5 | Put Cloudflare in front | The site is "DNS only", so the server's address is public and there is no shield against floods. | Turn the orange cloud on (websockets work), set `TRUST_PROXY`, cache the static files, and use the country header for J2. Test that sign-in, the websocket and the gateway still work. | S |
| K6 | Safer updates | An update goes straight to the live game and the old version is overwritten. | The upload script runs the quick tests first, keeps the previous release for a one-command rollback, and logs what was sent. | S |
| K7 | A second copy to try things on | Changes meet real browsers only after they are live. | A small staging server (or a second port on the same one) with its own game, updated first. | S |
| K8 | Harden the server | Defaults are not enough for a machine that will hold money. | Check SSH is keys only, add fail2ban, rotate `ADMIN_KEY` and `CORE_KEY`, and keep a list of every secret and where it lives. | S |
| K9 | A capacity plan | Nobody knows when the small server will stop being enough or what the next size costs. | A load test with 1,000 sockets from another machine against the real setup, then a table: players, server size, monthly cost. | M |
| K10 | A status page and an incident note | Players ask what is happening when the site is slow or down. | A static status page and a short template for telling players what happened. | S |

---

## 4. Suggested order

| Step | Focus | Items | Why this order |
|---|---|---|---|
| Now (this week) | **Make the live site safe** | K1, K2, K3, K4, J1 | The site is public. Lock the admin page, send real email, copy the backups elsewhere, get told when it is down, and put terms and an age check in front of strangers. All small. |
| Next (about 2 weeks) | **Let people in, and see what they do** | I6, I1, I4, H phase 1, A13 | A visitor should see prices before signing up, a landing page should say what this is, and you need counts and a revenue model before spending on growth. Then the closed test with 5-10 people. |
| Then (weeks 3-5) | **Hardening and retention** | H phase 2, G11, G8, G12, G13, E17, E8, E16, K5, K6 | Backups, safe updates, alerts, and the first reasons to return tomorrow (a "while you were away" summary and price alerts). |
| Then (weeks 5-8) | **Make prices and news feel alive** | C12, C13, C8, C9, C5, C6, E7, E13, E14 | More to read and see between big stories, plus onboarding and the heatmap and MSI 50 pages. |
| Then (weeks 8-12) | **Grow the game** | I3, I5, I7, F12, F11, F6, F7, D4, D5, D8, E1 | Referrals, share cards, email, leagues with friends, stock chat rooms, themed days, contests and chart upgrades. |
| In parallel | **Scale, observe and keep it maintainable** | G6, G10, G5, G9, G14, G15, G16, G17, K9 | Gateways carry the connections already; the rest is needed once there are thousands of players and more than one person editing the code. |
| Before real money | **Trust and the law** | J2 to J9, I2, A14, A15, then phases 4-5 | Responsible-play tools, two-step sign-in, a fairness page and a lawyer. Do not build payments before this. |
| Later | **Options and bring-your-own-bot** | D6, F15, E20 | Only once the market and economy are proven. |

---

## 5. Open questions

| Question | Options | What would decide it |
|---|---|---|
| The house is the counterparty to every trade. Is that acceptable, with no position limits? | Keep (current: the house carries the risk and earns fees; the tails are thinner and the reserve is topped up automatically); cap the house's exposure per stock (A12); add small impact for big trades (A6); hedge house exposure. | The edge-check results (section 6), the house-risk panel, `recapitalized` and `short_shortfall` in the closed test. |
| How much real capital does 1 MB represent? | Set the starting reserve (`house_seed`) and the reserve floor from that (stocks no longer hold seed tokens: `depth` is only a size). | Phase 4 legal advice and a risk budget. |
| Fee level | 0.1% per side now (it was 0.5%, which made a round trip cost 1%); keep, or 0.05%-0.3%; maybe lower fees for high volume. The fee is also the cushion against any small undiscovered edge, so re-run the edge check after any change. | Trade count vs fee revenue in the beta. |
| Keep the hidden mood? | Keep; make it a tradable "sentiment" signal later; drop it. | Tested: the `mood_oracle` strategy, which reads the hidden mood directly, has no edge, so the mood gives no price edge. Keep it, and re-run after any news change. (The per-stock volatility number that used to hint at the regime is no longer sent to the page.) |
| Is a 31.5-hour quarter too slow for a session? | Keep (realistic, rare reports feel like events); shorten with `earnings_quarter_days` for a faster game; add mid-quarter events (C11). | Playtester feedback on how often anything scheduled happens. |
| Is the 5 / 20 / 5-minute cycle the right rhythm? | Keep; change `premarket_seconds` and `aftermarket_seconds`; set both to 0 for a flat market. | Whether players enjoy the burst and the jump at the open, or find the quiet stretches dull. |
| Should public portfolios stay private by default? And should private players appear on the leaderboards? | Keep private by default (current) and leaderboards open to everyone who ranks (current); hide private players from the boards; make results public by default and holdings opt-in. | Playtester feedback and the legal review of showing player data. |
| How often should a whole industry crash? | Keep (one shock every ~10 minutes, 7 kinds, failures 4-13%, a typical company moving about 7%); make them rarer or milder (`sector_shock_mean_seconds`, `sector_shock_size`); give each sector its own standing factor (B6). | Playtester feedback: do sector crashes feel like events or like noise? |
| How wild should moonshots be? | Keep (260-550% volatility, 60% bankruptcy and a ×2.45 rescue, a 3× looser daily brake, 4 to 8 at a time); make them rarer or tamer; cap what one player can win on one (A12). | Playtester feedback and how often the house reserve swings. |
| How should contests pay out? | Cosmetic only (current: a medal for a paper-money contest); MB prizes funded from fees after the legal review (F7). | The legal gate and whether people care about medals. |
| How real should fundamentals be? | Light (current), or P/E-driven valuation with sector norms. | Playtester feedback: "did prices and news feel connected?" |
| Should email be required? | `off` (current, until a mail service is set up), `optional` (asked for, never needed); `required` (needed to trade, enter contests and chat). Needs a real mail service first (`HOW_IT_WORKS.md` §10.6). | Closed-test feedback on how much the extra step costs sign-ups, and the number of duplicate accounts the admin page flags. |
| Should the house have a built-in edge beyond the fee (the idea: 1% of what players trade)? | No (recommended): keep prices fair and the edge in the open. Measured edge today: 0.107% of everything traded (the 0.1% fee plus borrow cost). 1% of turnover would be a 1% fee per side, ten times today's, and active traders would lose everything in hours; a hidden price drift is not direction-blind (shorts would win) and is hard to defend with real money. Options: raise the fee a little (0.15%-0.3%), add a spread on leveraged products, add withdrawal or deposit fees, and cap the house's exposure to moonshots (A12). | Revenue per player and trades per player in the closed test, and the house-risk panel (the study found a standard deviation of 430,000-974,000 MB per market for 100 coordinated moonshot players against a few thousand MB of fees). |
| Is 10,000 MB the right starting stake? | Keep; change `signup_bonus` and `contest_balance` together (the reserve floor scales with it). | How fast players run out of money or get bored of small numbers. |
| Should prices drift upwards, as real markets do? | Not now (you decided against it). If it comes back: (1) prices drift up and every position pays an equal holding cost, so a buy-and-holder still averages zero (fair, mostly cosmetic); (2) hidden bull and bear phases that average zero, so there are real rallies and crashes but nothing to predict (needs an `edge.py` check that nobody can guess the phase); (3) a drift the house pays for, which is a standing cost that grows with player money. A real upward drift with a house that pays winners always means buy-and-hold wins. | Whether the market feels too flat in the closed test, and the revenue model (A13). |
| How does Meme Street earn beyond the fee? | Nothing else (today); paid-entry contests with a rake (legal gate); cosmetics; a Pro subscription; deposit or withdrawal fees (I2). | A13's revenue per player and the legal advice. |
| Should visitors be able to browse before signing up? | Yes, read-only (I6: more sign-ups, indexable pages); no (the sign-in box stays: simpler, nothing to scrape). | Whether the extra load and the scraping risk are acceptable; a guest view costs the server almost nothing. |
| Which countries first? | One or two where the legal route is clearest; everywhere that is not blocked (J2). | The lawyer's opinion (H phase 4). |
| Should the MSI 50 stay at 50 members and re-rank every game day? | Keep; change `index_size`; re-rank daily or weekly (a slower re-rank is closer to a real index, a faster one tracks growth sooner). | Whether players find the changing membership confusing once E14 and C12 show it. |

---

## 6. Checking any economy change

Any change to prices, news, fees, trading or risk rules must pass these before it ships. Start with the test suite (about ten minutes), which also guards the money-conservation rule, the limits and the "social features never move a price" rule:

```bash
.venv\Scripts\python.exe -m unittest discover tests -v
```

Then the strategy checks:

```bash
.venv\Scripts\python.exe sim.py 6 1                      # one detailed run: invariant drift, strategy returns, house P&L
.venv\Scripts\python.exe edge.py 40 2 100                # the real test: 40 seeds, mean/std error/t per strategy (about 20 minutes with 35 strategies)
.venv\Scripts\python.exe paired.py 40 2 1000 strategies=value,hodl base: no_limit:daily_move_cap=0   # same seeds, one setting changed: which mechanism pays a strategy?
.venv\Scripts\python.exe probe.py 60 3 news_followups=false   # engine-only drift probe
.venv\Scripts\python.exe tune.py configs.json 6 6 101    # compare settings on fresh seeds
```

- `invariant_drift` stays about 1e-10, and the house reserve doesn't trend negative.
- `edge.py` flags no strategy (none with a positive mean beyond 2 standard errors) on 40 seeds that haven't been used for tuning. Use a new first seed each time; one seed is noise. With 35 strategies, about one in twenty checks flags one by chance: re-run the flagged strategy on fresh seeds before believing it.
- Some probes need a setting to see enough events in a two-hour run: `earnings_runup` needs `earnings_quarter_days=0.05`, `gap_long`/`gap_short` and `open_follow`/`open_fade` need the default sessions (they do nothing with `premarket_seconds=0,aftermarket_seconds=0`), and `moon_hodl`, `distress_*`, `catalyst_*` and `industry_*` need the default moonshot, catalyst and industry-shock settings (switch them off with `moonshot_initial=0,moonshot_mean_seconds=1e12`, `catalyst_mean_seconds=1e12` and `sector_shock_mean_seconds=1e12` to compare).
- Configs on the same seeds share market paths, so confirm any conclusion on a fresh starting seed.
- If a strategy looks profitable, find the cause with `paired.py` (switch one mechanism off at a time on the same seeds) before changing anything: that is how the daily-limit edge was found.
- Update `HOW_IT_WORKS.md` and tick items here.

**Latest results (2026-10-03):** see the end of section 17 in `HOW_IT_WORKS.md` for the numbers of the last run.
