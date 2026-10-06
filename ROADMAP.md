# Meme Street roadmap

Goal: a trading game where players buy memebucks (MB) with crypto and trade fictional stocks. The house earns the 0.1% fee on every trade. No strategy based on public information should be able to win reliably, and the game should feel like a living market: prices that follow stories, news that reads like news, and enough variety that a session stays interesting.

Companion doc: `HOW_IT_WORKS.md` describes what the code does today. Update it after every change, and check this file before starting any work.

Size key: **S** = under a day, **M** = a few days, **L** = a week or more.

---

## 1. Where things stand (2026-10-03)

| Area | State |
|---|---|
| Economy | Every trade fills at the market price against the house. Token conservation holds (drift about 1e-10). Fees are the house's revenue. No price impact from players. Edge-checked on 35 strategies (the original 10, probes for gaps, reversals, ETFs, leveraged products, volatility and earnings, for the opening jump, moonshots, distress, catalysts, industry shocks and the hidden company links, and one that trades with bracket orders): see section 6 for the latest result. Every mechanism (volatility clustering, trading sessions, the opening jump, major-event limits, indices and ETFs, moonshots, catalysts, company events, orders, social features and the paper contest) was built so its expected effect on a price is exactly zero, and the house reserve is kept in proportion to the money at stake. |
| Trading | Long and short, % chips plus an MB amount box, average entry price, **on the market page, the stock page and the holdings page**. **No position limits** (removed on request): the only cap is your cash (a short is paid for out of cash as collateral: no margin multiple, no borrow pool), plus borrow fees and margin calls for shorts. **Fee 0.1% per side** (it was 0.5%). **The market never closes**: a 30-minute cycle on the real clock is 5 minutes of thin pre-market, 20 of regular session (a burst of volume and a jump at the open) and 5 of thin after-hours. **Orders**: limit buy/sell, stop-loss, take-profit and one-click brackets, filled at the market price when triggered. **Trading never pauses** (the circuit breakers were removed on request). |
| Prices | One random-walk "fair" price per stock: three-factor noise scaled by the session, slow mean reversion, news shocks, spillovers, **volatility clustering**, a soft daily limit that **opens up for very strong events**, and distress as a fair rescue-or-bankruptcy bet (a rescue is a doubling, not a ten-fold jump). There are no stock splits any more; share offerings change only the share count. **Moonshots** (tiny, pre-revenue companies with 260-550% volatility that can move hundreds of per cent in a day, go bankrupt easily and keep listing) rare **catalysts** (trial results, approvals, buyouts, audits, tests: a fair bet: the good news gains 10-35%, a setback costs a few per cent, and a rare disaster (6-8% of them, with its own much worse headline) costs 20-70%; a moonshot's is a two-outcome bet up to about +130%) and rare **industry-wide shocks** (a ban, a demand collapse, a probe, a disruptive technology: a fair two-outcome bet that moves every company in a sector together, with no market component, so an industry can crash while the market rises). Hedge assets (gold, bonds) have negative beta. |
| Listings | **193 listings at the start of a game**: 152 companies and funds in 30 sectors (**eight of them imaginary industries**: teleportation, weather engineering, time technology, dreams and memory, dragons and creatures, deep-ocean cities, antigravity, alchemy), 5 commodities, 32 derived assets (the market index, 21 sector indices, 6 themed ETFs, 4 leveraged/inverse products: 2LMSI, 2SMSI, 3LMSI, 3SMSI) and 4 moonshots, with new moonshots listing every ~15 minutes (**NEW** badge for 30 minutes). Indices and ETFs track total return (dividends included). |
| Companies | Every company has a CEO, CFO, flagship product and home city; stories name them and they recur (a CEO who resigned is named later). Companies are also linked by **hidden supplier, customer and rival links** that make sense (a drug maker supplies a hospital chain, an oil producer an airline), that players never see, that decide who appears together in two-company stories and that spill a little of each move over to partners and rivals; a new listing is linked in and its partners get the matching link. Revenue, margin, cash, debt and share count evolve at earnings: **quarterly (31.5 real hours, give or take a few days), spread so there are a few every game day and one is always coming up, and only before the open or after the close**; dividends, buybacks and offerings follow. **Scheduled company events** (guidance updates, investor days, analyst calls, product events) fall between the reports, on the public calendar with no hint of direction. Banks rate stocks from a hidden safety score and the financials, and give a reason for a new price target about 40% of the time. |
| News | 68 templates, 20 company-story kinds, 4 company-event kinds, 5 two-company story kinds, 7 rare catalyst kinds, 7 industry-wide shock kinds, 8 named sources. Headlines are built from slots (names, products, cities, synonyms), so the same story reads differently each time, and none of them talks about the game's own bookkeeping. A hidden mood tilts good vs bad (move size scaled so the expected move is zero). Stories come back as UPDATE or REVERSAL that quote the original. No headline ever repeats. |
| Players | **Accounts with passwords** (scrypt hashes, 30-day sessions, login and sign-up limits, a flag for accounts that share an address, admin password resets), **verified email** (a mailed code proves an address, one account per address, throwaway-mail domains refused, a forgotten password is recovered with a mailed code; `email_mode` off / optional / required), **10,000 MB to start**, and a **Day** (what was a season) that lasts one real day. **Portfolio page** (equity curve, allocation, realised vs unrealised, best and worst trades), **trade history** with filters and CSV download (delisted stocks keep a page you can open from it), **search, sort and watchlist** on the market, **leaderboards** (day and all-time), **achievements and daily quests**, a **daily contest** (everyone trades the same 10,000 MB of paper money under the real rules; medals only), **public profiles** (private by default; holdings shown only after a delay), following, and a **moderated global chat** (a filter that sees through disguises, a trade-first gate, three reports remove a message and mute its author, appeals, a moderator log). All rewards are cosmetic: no social feature touches money or prices. |
| Server | The engine runs in worker threads behind one lock, so a slow tick can't freeze the websockets. Clients get one full `init` and then a small `tick` each second (about 5 kB instead of 120 kB), each socket has its own writer so a slow client never blocks anyone, notices and chat are reliable messages. A crash loses nothing: every money event goes to an append-only SQLite ledger and is replayed after the last snapshot. The save keeps the chart candles in their own file so saving a full-size game takes about 140 ms, not 2.4 s. One process carried 400 simulated players at about half a core (`tests/capacity.py`). **Gateways**: `python launch.py --gateways N` runs the game server plus N gateway processes that hold the players' websockets and spread the work of sending updates over several cores (`HOW_IT_WORKS.md` §12). **Sharing from your own computer**: `python share.py` opens a free Cloudflare tunnel and prints a link anyone can open. Admin dashboard with alerts, charts, server timings, a house-risk report, chat moderation with appeals, accounts, email and mail, and a reset-to-Day-1 button. |
| Checks | `sim.py` (36 strategies, one of which cheats by reading the hidden company links), `bots.py` (100 bots per random strategy over many seeds, the moonshot-sniper study), `edge.py`, `paired.py`, `probe.py`, `tune.py`. A test suite of 740 tests in `tests/` (engine, volatility and sessions, news, wild stocks, industry shocks, company links, the earnings calendar, company events, orders, contests, accounts, email, moderation, house risk, saving, reset, ledger, portfolio, wire protocol, social, server, gateways, browser, stress, capacity and slow checks; the server-side suites can also be run through gateways with `MS_TEST_GATEWAYS=2`) that never touches your save file, and a GitHub workflow that runs it. |

Not done: wallet- or phone-verified accounts, a managed database server, real money. **Deployment** is prepared (`deploy/DEPLOY.md`: a rented server, a domain name, https, services, backups, one-command updates) but needs your domain and server; until then the game runs on your own computer, shared through a tunnel.

---

## 2. The biggest problems right now

The earlier lists have been worked through: accounts with passwords and **verified email with password recovery**, fixed-balance contests, stronger chat moderation, mid-quarter company events, order types, the house's tail risk, and the **single-process server** (gateways, see G10) are all done. Every stock keeps the same pre-market, regular session and after-hours (per-region and per-sector sessions were dropped on request). What is left, ranked by how much it could hurt the game or the house:

| # | Problem | Why it matters | Fix (see track) |
|---|---|---|---|
| 1 | **A lucky win on a moonshot is still possible, just smaller.** The tails are thinner and the reserve is topped up automatically, but with no position limits a fair bet can still be a big one. | The reserve floor is a capital decision for real money. | A12 |

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

### B. Price movement mechanics

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| B6 | Richer correlations | A single market factor plus sector is simplistic. (Industry-wide shocks, §7.14 of `HOW_IT_WORKS.md`, now let a sector move on its own, but they are one-off news, not a standing factor.) | Add factors: rates sensitivity, oil, dollar, risk-on/off. Give each stock exposures. Use them for hedges (gold vs dollar, bonds vs rates, airlines vs oil) instead of one fixed beta. | L |
| B9 | Realistic commodity behaviour | Oil, gas and grain have seasons and supply shocks. (The old slow commodity drift was removed: it was a momentum edge, see `HOW_IT_WORKS.md` 6.1.) | Scheduled inventory reports, OPEC-style meetings and weather shocks as *news* (zero expected move, like every other story), not as a drift; tie airlines and utilities to them. Anything that makes a commodity's next move predictable is an edge and must not come back. | M |
| B10 | Interest rates as a real variable | "Rates" is only a news template today. | A visible policy rate that changes on scheduled dates; affects bonds, banks, growth stocks and gold through the factor model (B6). | L |

### C. News and storytelling

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| C2 | Optional LLM headlines (**not done, needs your decision and an API key**) | Highest variety for the least writing. The slot grammar (C1) already gives thousands of surface forms, so this is now a nice-to-have. | Offline step that pre-generates a few thousand headlines per template and tone, reviewed and loaded as content packs (no live calls in the game loop). It can't be done inside the repo without an LLM service, so it was skipped. | M |
| C5 | Multi-part arcs with stages | Today follow-ups are one-step. | Arc templates: probe, hearing, ruling; clinical trial phase 1, 2, 3; merger rumour, bid, approval or collapse. Players can read the stage and trade the odds; zero expected move at each stage. | L |
| C6 | Scheduled macro calendar | Central bank dates, jobs reports and earnings seasons give structure. | A calendar page and "Upcoming events" entries, with outcomes drawn at the event. Pair with B10. | M |
| C7 | Sources with track records | Every rumour has the same 75% credibility. | Named sources (a rumour mill, a respected wire) with a hidden accuracy that the player can learn from their history; keep the average at zero edge. | M |
| C8 | Analyst consensus and "beat/miss" | Earnings today say "beat" or "missed" with no expectation. | Publish a consensus estimate before each report; the price reacts to the surprise against it. | M |
| C9 | Headlines that name the cause of a move | "Why is X down?" should be answerable from the wire. | Attach each news item to the move it caused (a small "-1.2%" badge on the headline, filled in after the tick). | S |
| C10 | News filters and a ticker-specific feed | The wire is one stream of 30 items. | Filter by sector, watchlist and holdings; search; infinite scroll with saved history (the wire isn't saved today). | M |

### D. Number and variety of stocks

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| D4 | IPO calendar and delisting cycle (partly done) | Moonshots already list every ~15 minutes and bankrupt ones are replaced. Ordinary IPOs and an announced calendar are missing. | Scheduled IPOs of ordinary companies announced days ahead (with a pricing story), an "IPO calendar" page, and more kinds of generated company (small caps, SPAC-like names). | M |
| D5 | Company personalities | Many stocks read the same. (The hidden supplier / customer / rival links already give each company a place in a web of partners.) | Per-company traits: dividend payer, serial acquirer, meme favourite, cyclical, defensive; each changes which stories it gets and how it reacts. | M |
| D6 | Options (much later) | The classic next instrument. | Only after the core economy is proven safe; needs a pricing model and strict risk limits. | L |
| D7 | More listings | 150 companies is plenty to browse, and eight imaginary industries are in. A few real-world themes are still thin. | More content packs (copy `pack_fiction.json`'s or `pack_growth.json`'s shape): international, small caps, more imaginary industries. | S each |

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

### F. Game design and social

| # | Improvement | Why | How | Size |
|---|---|---|---|---|
| F6 | Days with themes | A day is just a leaderboard reset. | Themed days or weeks (a bubble, a recession, a rate-hike year) that change regime odds; announced at the start. | M |
| F7 | Contest formats and prizes | The daily contest is fair (same paper balance for everyone, real rules) but only pays a medal. | A weekly contest, a contest with limited instruments, team entries, and MB prizes only after the legal review (H phase 4). | M |
| F10 | More quests and achievements | 21 achievements and 8 quest types will be done in a few days. | Weekly quests, hidden achievements, seasonal badges, a profile showcase. | S |

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

### H. Launch track (from the earlier roadmap, still valid)

| Phase | What | Done when |
|---|---|---|
| 1. Closed play-money test (weeks 1-2) | Stop other servers, start one server with `ADMIN_KEY` set, use the admin **Reset** to begin at Day 1, run `python share.py` for a public link (it opens a free Cloudflare tunnel to the game on your computer), invite 5-10 people, keep `signup_bonus` at 10000. Watch `invariant_drift`, `fees`, `liquidity_pnl`, `players_pnl`, the house-risk panel, the server timings on the admin page and one player topping every day. | 10+ testers, no crashes for 24 hours, nobody wins every day |
| 2. Hardening (weeks 3-5) | Set `email_mode` to `required` and put real mail (SMTP) behind it before anyone relies on it (done: passwords, sessions, sign-up and login limits, an address-sharing flag, verified email with one account per address, password recovery by email); wallet or phone verification before real money; rate limits on trades and on admin-key guesses (A10); a permanent HTTPS host (the files are in `deploy/`; you buy the domain and rent the server) with searchable logs and daily backups (G11: the six-hourly backup job is in `deploy/`; an off-site copy and a restore drill are not); CI test from `sim.py` (drift under 1e-6); mobile pass (E6). | Done for the email part: a forgotten password is recovered without the admin. Still to do: a permanent host, backups, mobile |
| 3. Public beta, play money (weeks 5-8) | Open signups; measure daily active players, trades per player and fees per player; re-tune `event_mean_seconds`, `news_move_ranges`; ship content packs regularly; watch chat reports (F8). | Stable retention and a healthy house reserve |
| 4. Legal gate | Lawyer's opinion, per country, on gambling or skill-gaming licences, money transmission and virtual-asset rules (KYC/AML), whether withdrawable fictional "stocks" raise securities or derivatives issues, terms of service, age limits, and the privacy of public portfolios and chat. | Written sign-off. Do not build payments before this. |
| 5. Real money | Crypto deposits on `Engine.credit` (after on-chain confirmations); withdrawals on `Engine.debit` (manual approval, daily caps); `signup_bonus` to 0; daily reconciliation (on-chain balance at least player cash plus equity); low caps at launch. | Numbers hold at each cap raise |

---

## 4. Suggested order

| Step | Focus | Items | Why this order |
|---|---|---|---|
| Next (about 2 weeks) | **Run the closed test and decide the open economy questions** | H phase 1, A6 | Everything the closed test needs is built: a ledger that survives crashes, portfolio and history pages, social features, an admin dashboard with timings and moderation. Decide whether very large trades need a price impact (A6, your call). |
| Then (weeks 3-5) | **Hardening** | H phase 2, G11, G8, E6, E8 | Accounts, rate limits, backups, mobile layout and persistent notifications. |
| Then (weeks 5-8) | **Make prices and news feel alive** | C8, C9, C5, C6, E7 | More to wait for between big stories, plus onboarding for new players. |
| Then (weeks 8-12) | **Grow the game** | F6, F7, D4, D5, E1 | Themed days, contest formats, more instruments and chart upgrades. |
| In parallel | **Scale and observe** | G6, G10, G5, G9 | Gateways already carry the connections; the rest is needed once there are thousands of players. |
| Later | **Options, real money** | D6, then phases 4-5 | Only once the market and economy are proven. |

---

## 5. Open questions

| Question | Options | What would decide it |
|---|---|---|
| The house is the counterparty to every trade. Is that acceptable, with no position limits? | Keep (current: the house carries the risk and earns fees; the tails are thinner and the reserve is topped up automatically); cap the house's exposure per stock (A12); add small impact for big trades (A6); hedge house exposure. | The edge-check results (section 6), the house-risk panel, `recapitalized` and `short_shortfall` in the closed test. |
| How much real capital does 1 MB represent? | Set per-stock seed (`depth`) and the reserve from that. | Phase 4 legal advice and a risk budget. |
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
