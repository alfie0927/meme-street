# How Meme Street works

This document explains the whole system: what each file does, how prices and trading work, how money flows, how news, earnings and ratings are generated, how the social features and the server protocol work, and what to watch out for. Numbers quoted are the current defaults from the content packs (`base.json`, `expansion.json`, `pack_growth.json`, `pack_fiction.json`) and the constants at the top of `engine.py`.

**A guide to the sections.** §1 running it · §2 the files · §3 time · §4 trading · §5 where money lives · §6 how prices move (including volatility, the trading sessions, moonshots and how the tails are kept thin) · §7 news, catalysts, industry-wide shocks, company stories and ratings · §8 listings · §9 indices, ETFs and leveraged products · §10 players, accounts, days, achievements, the daily contest and chat · §11 the web pages · §12 the server, its protocol and gateways (more than one process) · §13 saving and the crash-proof ledger · §14 settings · §15 things to know · §16 tests · §17 the latest economy-check results.

Keep this file in step with the code: update it after every change (see "Keeping the docs current" at the end).

---

## 1. Running it

### Start the server
From the project folder, in PowerShell:

```powershell
cd "C:\Users\alfie\OneDrive\桌面\stock_market_sim"
$env:ADMIN_KEY = "pick-a-long-random-string"     # optional: enables /api/admin/*
.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Then open:
- **http://127.0.0.1:8000** for the market. Open a second browser (or a private window) to play as a second player.
- **http://127.0.0.1:8000/stock/NVXA** for a stock's page (any ticker works, including `MSI` for the index).
- **http://127.0.0.1:8000/holdings** for your holdings, **/portfolio** for your equity curve and profit breakdown, **/history** for every trade and payment (with a CSV download), **/leaders** for the two leaderboards, **/social** for chat and following, **/profile** for your quests, the daily contest, achievements and your account, and **/player/NAME** for another trader's profile.
- **http://127.0.0.1:8000/admin** for the admin dashboard (needs `ADMIN_KEY`).
- **http://127.0.0.1:8000/docs** for FastAPI's automatic API explorer.

Alternatives:
- **VS Code:** Terminal → Run Task → "Meme Street Profile Engine". It runs the same command on port **8002**, so open http://127.0.0.1:8002.
- **While editing code:** add `--reload` so the server restarts when a `.py` file changes. Content `.json` files are hot-reloaded by the engine itself without a restart.

Stop the server with Ctrl+C. It saves `state.json` on a clean shutdown and closes the ledger (`ledger.db`, §13). If the server is killed or crashes instead, nothing is lost: the next start loads the last snapshot and replays the ledger (you'll see "recovered N ledger events" in the log).

**Run only one game server at a time.** Every game server instance reads and writes the same `state.json` and `ledger.db`, so two servers overwrite each other's saves. (Gateways, §12, hold no game and never touch those files; you can run as many as you like next to one game server.) A server also keeps running whatever code it started with: after changing code, stop it and start it again, then hard-refresh the browser (the page is served with `Cache-Control: no-store`, but an already-open tab keeps its old script).

### Letting other people play (sharing it from your own computer)
**In plain English:** the game listens only on your own computer (`127.0.0.1`), so `http://127.0.0.1:8000` works for you and nobody else. To give friends or testers a link while the game keeps running on your PC, use a free Cloudflare **quick tunnel**. Your computer makes an outgoing connection to Cloudflare, and Cloudflare gives you a public `https://….trycloudflare.com` address that forwards to your game. Nothing is opened on your router, your home address is not revealed, and the link works from phones and from other countries.

1. **Start the game** the way you always do. Give it a long secret `ADMIN_KEY` (the admin page is on the same address, so anyone with the link can open `/admin`, though without the key it shows nothing), or none at all (no key switches the admin API off).
2. **First time only:** `python share.py --install`. This downloads Cloudflare's small tunnel program (`cloudflared.exe`) from Cloudflare's own release page on GitHub into a `tools/` folder. (Or install it yourself: `winget install --id Cloudflare.cloudflared`.)
3. **Every time:** in a second terminal, `python share.py`. After a few seconds it prints a box like `https://quiet-river-1234.trycloudflare.com` (and saves it in `share_url.txt`). Send that link to people. It works as long as that window stays open, your computer is awake (turn off sleep) and the game is running. Ctrl+C stops sharing; the game itself is not affected.

What to expect:
- **The link changes every time** you run `share.py`. A permanent address needs a free Cloudflare account and a domain name (a "named tunnel"); that is a hosting job for later.
- **Your PC does the work.** A few dozen testers is fine on a normal computer (§12, Capacity); the tunnel is free and meant for testing, with no uptime promise.
- **Each visitor counts separately.** Everyone arrives through the tunnel from your own computer, so the game reads each visitor's real address from the tunnel's `CF-Connecting-IP` header. It only believes that header when the request really comes from this computer (or `trust_proxy` is on, §14), otherwise anyone could fake it. Without that, the "5 sign-ups per address per hour" limit would have applied to all your visitors together (§10.6).
- **People on the same Wi-Fi** do not need the tunnel: start the game with `--host 0.0.0.0` (`python launch.py --host 0.0.0.0`, or `python -m uvicorn server:app --host 0.0.0.0 --port 8000`), let Python through the Windows firewall when it asks, and open `http://<your PC's address>:8000`. `python share.py --lan` prints that address.
- `share.py` never starts the game and never reads or writes your save; it only checks that something is listening on port 8000 and then starts the tunnel.

### Running it on a real server with its own web address
**In plain English:** the `deploy/` folder takes the game from your computer to a rented server that is on all the time, with a domain name and https. `deploy/DEPLOY.md` is the step-by-step guide (buy a name, rent an Ubuntu 24.04 server, point the name at it, run two commands). What is in the folder:

| File | What it does |
|---|---|
| `DEPLOY.md` | The guide: costs, choosing a name, the server, DNS, setup, moving your saved game, email, protecting the admin page, updating, backups and restoring, monitoring, troubleshooting |
| `upload.ps1` | Run on your Windows computer: sends the code (never the saves or the ledger) to the server, and with `-Restart` restarts the game; `-WithGame` moves your saved game once; `-DryRun` shows what would be sent |
| `setup_server.sh` | Run once on the server as root: installs Python and Caddy, makes the game's user and environment, writes `/etc/memestreet.env` with random keys, installs the services, the firewall (only ssh, http and https), automatic security updates and the backup job |
| `memestreet.service`, `memestreet-gateway.service` | systemd services: the game server (port 8001, only reachable on the machine, saves when told to stop) and the gateways (port 8000); both restart by themselves and start on boot |
| `Caddyfile` | The web server in front: gets and renews the https certificate, redirects `www`, sends traffic to the gateways, adds security headers, and has an optional password block for `/admin` |
| `memestreet.env.example` | The settings kept in `/etc/memestreet.env`: the admin key, the gateway key, how many gateways, the mail service |
| `backup.sh` | Every six hours: copies the save, the charts and a consistent copy of the ledger to `/var/backups/memestreet`, keeping two weeks |

How a visitor's address stays honest behind Caddy: the gateway believes `X-Forwarded-For` and `CF-Connecting-IP` from the machine itself (§10.6), so Caddy removes any `CF-Connecting-IP` the visitor sent and replaces `X-Forwarded-For` with the connection's real address. `tests/test_deploy.py` checks that, that the services and the Caddyfile agree on ports, that every module the server imports is in the upload, and that the scripts have no syntax errors.

### Starting it with `launch.py`, and more than one process
`python launch.py` starts the game in one process on port 8000, the same as the `uvicorn` command above. `python launch.py --gateways 4` starts the **game server** (on `127.0.0.1:8001`, only this computer can reach it) plus **four gateway processes** that listen on port 8000 and hold the players' connections. Players cannot tell the difference. You only need it for a larger crowd (hundreds of players); how it works and what it buys is in §12 ("Gateways"). Options: `--host`, `--port`, `--core-port`. Stop it with Ctrl+C (gateways stop first, then the game, which saves on the way out).

**To start the game over at Day 1**, open the admin page (`/admin`), find **Start the game over**, type `RESET` and press the button. Every player goes back to the starting balance (`signup_bonus`, 10,000 MB), positions are closed at the market price (no fees), orders are cancelled, and the trade history, medals and achievements are cleared. Prices, charts, listings, accounts and passwords stay. The old save and ledger are first copied into a `backups/reset-<date>` folder next to the server, so nothing is lost; every connected page reconnects by itself. (`Engine.reset_to_day_one`, §10.) **Without the admin page** (no `ADMIN_KEY` set, or you prefer the terminal): stop the server, run `python reset_game.py` (it asks you to type `RESET`; `--yes` skips the question) and start the server again. It makes the same backup first and refuses to run while something is listening on port 8000, because a running server would overwrite the result a few seconds later.

**To throw everything away** (a brand-new market, no accounts), stop the server, delete `state.json`, `state.charts.json` **and** `ledger.db` (plus `ledger.db-wal` and `ledger.db-shm` if they exist), and start it again. (Deleting only `state.json` would make the server replay the old ledger into the new game.)

### First-time setup (only once)
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Tests
Run the whole test suite from the project folder (about ten minutes; nothing to install):

```powershell
.venv\Scripts\python.exe -m unittest discover tests -v          # everything below except the slow checks
.venv\Scripts\python.exe -m unittest discover tests -p "test_engine.py"   # just one file (about 50 s)
.venv\Scripts\python.exe tests\stress.py 40 30                  # stress test: 40 clients for 30 seconds
$env:RUN_SLOW = "1"; .venv\Scripts\python.exe -m unittest discover tests -p "test_slow.py" -v   # slow checks
```

See §16 for what the tests cover and when to run which one.

### Economy checks
```powershell
.venv\Scripts\python.exe bots.py all 54 2 2000             # every strategy, 54 seeds x 2 h, 100 bots for the random ones (35 minutes on 18 processes)
.venv\Scripts\python.exe bots.py moon 90 6 1000             # the moonshot study; also `moondense` (a new moonshot every 45 s) and `report`
.venv\Scripts\python.exe sim.py 6 1                      # 6 simulated hours, seed 1, detailed report
.venv\Scripts\python.exe edge.py 20 2 100                # edge check: 20 seeds x 2 h, first seed 100
.venv\Scripts\python.exe edge.py 20 2 100 mean_reversion_halflife_days=730   # same, with a setting changed
.venv\Scripts\python.exe probe.py 60 3                    # where does an edge come from? (see below)
.venv\Scripts\python.exe paired.py 40 2 1000 strategies=value,hodl base: no_limit:daily_move_cap=0   # paired comparison (see below)
.venv\Scripts\python.exe tune.py configs.json 6 6 101    # compare settings: 6 h, 6 seeds starting at 101
```

**What the checks do.** `sim.py` runs the engine on a fake clock with 108 scripted "players" (3 copies of each of 36 strategies) that use only public information, and reports each strategy's return, the house P&L and the token invariant. The first ten probe the original mechanics; the next probes cover what was added with the bigger market (the opening gap, reversals, ETFs, leveraged products, volatility, earnings and trends); then come the sessions, moonshots, distress, catalysts, industry shocks and the hidden company links (§6.6, §6.8, §6.10, §7.13, §7.14, §7.15), and last the order types (§4). The strategies:

| Strategy | What it does |
|---|---|
| `news_chaser` | buys good headlines, sells bad ones, holds 90 s |
| `rumor_trader` | trades rumours, holds 120 s |
| `value` | buys stocks below 90% of their reference price, sells at 99% |
| `dip_buyer` | buys a stock the tick after a sharp drop, sells a minute later |
| `retail` | random small trades |
| `hodl` | buys 8 stocks and holds |
| `short_seller` | shorts after bullish headlines, covers after 90 s |
| `squeeze_hunter` | shorts anything that jumped over 3% in a minute |
| `big_size` | trades headlines with 100% of cash or spare margin, closes after 60 s |
| `mood_oracle` | cheats by reading the engine's hidden mood and trading the index with it; if even this has no edge, nobody who reads the narrative can farm it |
| `gap_long` / `gap_short` | hold three stocks across the opening jump (long, or short): buy just before the regular session opens, sell a few seconds after (§6.8) |
| `reversal_chaser` | trades in the direction a REVERSAL headline points (§7.4) |
| `update_chaser` | the same for UPDATE headlines |
| `partner_chaser` | trades the second company named in a two-company story, in the headline's direction (§7.11) |
| `etf_hodl`, `bull2_hodl`, `bear2_hodl`, `bull3_hodl`, `bear3_hodl` | buy and hold a basket ETF, the 2x long, 2x short, 3x long and 3x short products (`2LMSI`, `2SMSI`, `3LMSI`, `3SMSI`; §9) |
| `vol_chaser` | buys stocks that have just had a burst of big moves (§6.7: volatility clusters but must not predict direction) |
| `earnings_runup` | buys 30 seconds before a company's earnings report and sells 30 seconds after |
| `trend_follower` | buys commodities whose last 10 minutes were up, shorts those that were down, holds 20 minutes (§6.1: this found the commodity-trend edge that was then removed) |
| `open_follow` / `open_fade` | trade the opening jump: buy what jumped up at the open and short what jumped down (follow), or the opposite (fade) (§6.8) |
| `moon_hodl` | buys each brand-new moonshot at its listing and holds it for 20 minutes (§6.10) |
| `moon_sniper` | buys each brand-new moonshot within five seconds of its listing and then waits, with no stop-loss and no time limit, until it is worth a target multiple (1.5x to 20x, a different one for each bot) or goes bankrupt (§17.7) |
| `moon_short` | shorts every moonshot with a share of its cash for 10 minutes |
| `distress_buyer` / `distress_short` | buy, or short, stocks that are just above the distress line, where a rescue or a bankruptcy could come next (§6.6: that bet is built to be fair) |
| `catalyst_follow` / `catalyst_fade` | buy, or short, anything that jumped 25% or more in the last two minutes (§7.13) |
| `industry_follow` / `industry_fade` | when a whole industry has just moved 6% or more as a group, buy (or short) three of its companies in the direction it moved, or the opposite, and hold 5 minutes (§7.14) |
| `bracket_trader` | buys a random ordinary stock with 30% of its cash and at once leaves a take-profit 1% above and a stop-loss 1% below as a bracket (§4): orders fill at the market price, so it earns nothing but loses its fees |
| `relation_oracle` | **cheats**: reads the hidden supplier / customer / rival graph (§7.15). When a company jumps 4% in 30 seconds it buys that company's customers and shorts its rivals (the reverse after a fall) for two minutes. The spillover lands in the same second as the move, so even a trader who can see the links should earn nothing |

`edge.py` runs `sim.py` on many independent seeds in parallel (and skips building the public state, which makes it about ten times faster) and prints, per strategy, the **mean return per seed, its standard error and a t-statistic**. A strategy with a positive mean and `t > 2` is flagged `EDGE` (the house is funding it) and the script exits with code 1; it also fails if the token invariant drifts above 1e-6. A single seed is noise (the `value` strategy swung between −8% and +21% across single seeds), so always judge on many seeds. With 35 strategies, 40 seeds × 2 h takes about 20 minutes with 6 workers and enough free memory. With 35 strategies about one check in twenty flags one by chance (2 standard errors is about a 1-in-20 event): re-run a flagged strategy on fresh seeds before believing it. Some probes only see events with a setting changed (`earnings_runup` needs `earnings_quarter_days=0.05`). It runs 8 processes at a time by default (each uses about 150 MB); set `EDGE_WORKERS=4` (or fewer) if the machine is short of memory, and expect it to take proportionally longer. The workers crash with a `BrokenProcessPool` error when memory runs out.

`paired.py` is the sharper tool for "does this setting matter?". It runs **the same seeds** under several settings and reports, for each strategy, the *difference* from the first (baseline) configuration with its standard error. Because the market paths are identical apart from what the setting changes, a +0.5% effect that is invisible in `edge.py` (noise about 1%) shows up clearly. Example: `python paired.py 40 2 1000 strategies=value,hodl base: no_reversion:mean_reversion_halflife_days=0 no_limit:daily_move_cap=0`. Each configuration is `label:setting=value[,setting=value]`; the first is the baseline. This is how the daily-limit edge was found: switching the limit off changed `value` by −2.7% (t −3.2) while every other mechanism changed it by about zero.

`probe.py` finds *where* a hidden edge comes from. It runs the engine alone on many seeds and reports whether stocks below their reference price beat the rest over the next 30 minutes (a positive number means "buy the dips" is paid for by the house). Switch a mechanism off with a setting (`mood_tilt=0`, `news_followups=false`, `daily_move_cap=0`, `rumor_prob=0`, `mean_reversion_halflife_days=0`, and so on) and compare. One configuration has a standard error near 0.1% per 30 minutes, so only large differences mean anything. `edge.py` also accepts `_strategies='["value","hodl"]'` to run only some strategies, which is faster.

---

## 2. The pieces

| File | Role |
|---|---|
| `engine.py` | The whole game: prices, trading, orders, volatility, the trading sessions, moonshots, catalysts, industry shocks, scheduled company events, news and narrative, company stories, earnings, offerings, bank ratings, indices and ETFs, days, accounting, the house reserve and its risk, save/load and crash recovery. Has no web code. |
| `social.py` | Everything built on top of the players: achievements, daily quests, the daily contest, the day and all-time boards, public profiles, following, and the moderated chat (word filter, reports, auto-mutes, appeals). A mixin of the engine. It never touches real cash or prices (§10). |
| `contest.py` | The paper-money accounts of the daily contest (§10.4): a `Sandbox` that lets the engine's own trading code run against a throwaway house, so a contest trade follows the real rules exactly but can never touch the real economy. |
| `accounts.py` | Passwords (scrypt hashes), login sessions, name rules, the sign-up and login limiters, the list of accounts that share an address, **email addresses** (verification codes, one account per address, recovering a password) (§10.6). A mixin of the engine. |
| `mailer.py` | Sends the verification and password-reset emails over any SMTP service, on a background thread, with retries; with no mail server set it is in *console mode* and keeps the message for the admin page (§10.6). |
| `relations.py` | The hidden links between companies: who supplies whom, who buys from whom, who competes (§7.15). Hand-written for the companies that ship with the game, sector rules for newcomers. |
| `newsgen.py` | The headline writer and the generators: names, products, cities, synonyms, slot filling, the company-story catalogue, the two-company stories (§7.12), the rare catalyst stories (§7.13), the industry-wide shock stories (§7.14) and the moonshot company generator (§6.10). |
| `ledger.py` | The append-only SQLite log of every money event and each player's equity curve (§13). Created as `ledger.db`. Can copy itself (`backup`) and be emptied (`clear`) for a game reset. |
| `server.py` | FastAPI app, the **game server**. Runs the engine in worker threads behind one lock, sends each browser one `init` and then a small `tick` every second over a WebSocket, handles the HTTP endpoints, and (when started with a `CORE_KEY`) accepts gateways (§12). |
| `gateway.py` | A **gateway**: a process that holds players' websockets and passes everything else to the game server over one link. Run several to spread the work of sending updates over several processor cores (§12, "Gateways"). Holds no game state; never imports `server.py`. |
| `wsconn.py`, `netutil.py`, `pages.py` | Small pieces shared by the game server and the gateway: one websocket with its writer queue, working out a caller's real address and the renamed-product table, and the page routes (`/`, `/admin`, `/stock/…`, the logo). |
| `launch.py` | Starts the game: one process, or the game server plus `--gateways N` gateway processes (§1, §12). |
| `deploy/` | Putting the game on a rented server with a domain name and https: a guide, the upload script, the setup script, the services, the web-server file and the backup job (§1, "Running it on a real server") |
| `share.py` | Gives other people a link to the game while it runs on your own computer, through a free Cloudflare quick tunnel (§1, "Letting other people play"). Never starts the game or touches the save. |
| `index.html` | The entire front end: plain HTML, CSS and JS, no build step. One file serves every player page: market, stock, holdings, portfolio, history, leaders, social, profile and player, and the sign-in box (§11). |
| `base.json` | Core content pack: settings, 9 sectors, the original companies, 11 event templates. |
| `expansion.json` | Extra sectors (utilities, industrials, telecom, materials, agriculture, commodities), more companies, risk settings, sector links. |
| `pack_growth.json` | Growth pack: 68 more companies in 7 new sectors (health services, retail, media, autos, real estate, crypto and fintech, space), 14 more news templates, reference financials and the definitions of the themed ETFs and leveraged products. |
| `pack_fiction.json` | **Imaginary industries:** 48 companies in 8 invented sectors (teleportation, weather engineering, time technology, dreams and memory, dragons and creatures, deep-ocean cities, antigravity, alchemy), 24 news templates, reference financials and the Frontier Industries ETF (§8). |
| `events_pack.json` | 17 sector-specific news templates. |
| `market_profiles.json` | Per-ticker reference price, share count, revenue, margin, cash, debt, dividend yield. |
| `space_pack.json.disabled` | Example pack. Rename it to `.json` while running to IPO three space companies live. |
| `tests/` | The automated test suite: engine, server, browser, stress, capacity and slow checks (§16). |
| `.github/workflows/tests.yml` | Runs the test suite automatically on every push if the project is on GitHub. |
| `sim.py` | Headless simulation with 36 scripted "human" strategies (shorting, big size, a mood-reading oracle, and probes for the opening jump, reversals, ETFs, leveraged products, volatility, earnings, trends, moonshots, distress, catalysts, industry shocks and bracket orders); reports returns, house P&L, invariant. |
| `admin.html` | The admin dashboard page, served at `/admin` (§12): house money and risk, server timings, chat moderation with appeals, accounts, email and mail, and the reset button. |
| `paired.py` | Paired comparison: runs the same seeds under different settings and prints the difference with a standard error. The tool that found the daily-limit edge (§6.5). |
| `bots.py` | Many-bot, many-seed study on top of `sim.py`: 100 bots for each strategy that makes random choices, the moonshot-sniper study, how much each strategy traded and the result per unit traded (§17.7). Saves to `sim_results/` |
| `edge.py` | Many-seed edge check on top of `sim.py`: mean, standard error and t-statistic per strategy; fails on any significant edge. |
| `probe.py` | Engine-only drift probe: do below-reference stocks beat the rest? Used to locate a hidden edge by switching mechanisms off. |
| `catalyst_probe.py` | Engine-only: what a stock does in the 5 minutes after a 25% move in 2 minutes (what `catalyst_follow` bets on), ordinary companies and moonshots apart, with the standard error taken across seeds (§17.9). |
| `index_probe.py` | Engine-only: does the MSI 50, the average company, `AIFX` or the leveraged products drift over a 2-hour game? (§17.9) |
| `tune.py` | Runs `sim.py` across several setting overrides and seeds in parallel and prints a comparison table. |
| `state.json` | The save file: a snapshot of the game, written every 30 seconds (generated, git-ignored). The chart candles, most of its size, live in `state.charts.json` beside it, rewritten every five minutes (§13). |
| `reset_game.py` | The command-line version of the admin **Reset** button: back up, then start the game over at Day 1 (stop the server first). |
| `backups/` | Copies of the save and the ledger made by the admin **Reset** button or `reset_game.py` (generated). |
| `ledger.db` | The ledger: every money event and every player's equity curve (generated, git-ignored, with `-wal` and `-shm` files beside it while the server runs). |

---

## 3. Time

- **1 tick = 1 real second.** The server loop calls `engine.tick()` every second.
- **1 game day = 1,800 ticks = 30 real minutes** (`MARKET_DAY_SECONDS`). So the "30m" change shown next to prices (and the index) means one game day.
- **1 game year = 252 game days** (`TRADING_DAYS_PER_YEAR`), which is 126 real hours.
- **1 day = 86,400 s = one real day, midnight to midnight UTC** (`season_seconds`). This is the period of the leaderboard, the daily quests and the daily contest, so all three begin and end together. (Before it was called a *season* and lasted an hour.) The game's own 30-minute "game day" above is a different thing: it is the market's unit of time.

Everything shown to players is in **real time**: chart candle sizes, news and filing timestamps, and the countdowns in "Upcoming events". A countdown reads "4 hrs, 12 minutes, 9 seconds" (units that are zero at the front are left out), never "252m 09s".

**The calendar at a glance**

| Unit | Game time | Real time |
|---|---|---|
| 1 tick | | 1 second |
| 1 game day | 1 day | **30 minutes** |
| 1 day (leaderboard period) | 48 game days | 24 hours, UTC midnight to midnight |
| **1 quarter** (one earnings period) | **63 game days** (a quarter of a 252-day year) | **31.5 hours** |
| 1 game year | 252 game days (4 quarters) | 126 hours (5.25 days) |

A company therefore reports earnings about once every 31.5 real hours, and pays a dividend with each report. Between two reports, a stock lives through roughly 63 game days of news, stories and price moves.

**One 30-minute cycle, minute by minute.** Every game day is 30 real minutes, and it is split into three **sessions** on the real clock, the same for everyone and repeating all day: **pre-market for the first 5 minutes (:00 to :05 and :30 to :35), the regular session for the next 20 (:05 to :25 and :35 to :55) and after-hours for the last 5 (:25 to :30 and :55 to :00)**, then straight back to pre-market. Trading is never refused. What changes is how busy the market is: quiet and thin before and after, a burst and a jump at the open (§6.8). The page shows the session in the header ("Pre-market · opens in 3 minutes, 12 seconds"), a tooltip on that chip with the cycle's clock times in your own time zone, and an amber (pre-market) or purple (after-hours) banner while the market is thin.

Annualised volatility `σ` (each company's `vol`) converts to:
- daily: `σ_d = σ / √252`
- per tick: `σ_tick = σ / √(252 × 1800)`

Example, NVXA (`vol` 0.42): `σ_d` = 2.65% per game day and `σ_tick` = 0.062% per second.

---

## 4. Trading: how prices and trades work

**Player trades never move a price.** A stock's price is a single outside-world value (`fair`, see §6) driven only by noise, news, earnings and regimes. Players trade at that price against **the house**, long or short.

### Buying with `c` MB
```
fee    = c × 0.001               → house fee revenue
shares = (c − fee) / price       → given to the player
house reserve += c − fee
```

### Selling `sh` shares
```
gross    = sh × price
fee      = gross × 0.001         → house fee revenue
proceeds = gross − fee           → to the player (paid from the house reserve)
```

### Typing an amount
Next to the size chips there is an **amount box** (in MB). If it has a number in it, that number is used instead of the chip percentage: Buy spends that many MB, Sell sells that many MB worth, Short opens a short of that many MB, and Cover buys back that many MB. Picking a chip clears the box. The server accepts `amount` on a trade message; invalid, negative, zero, NaN or absurdly large amounts are rejected.

### There is no limit on the size of a position
You can put all your cash into one stock, however volatile it is, and a rich player can hold far more than the stock's size (its `depth`). Selling is never limited. The only things that cap a trade are the cash you have (buys) and, for shorts, **margin** and the **shares available to borrow** (below). There used to be a per-stock position limit (a share of your equity, smaller for volatile stocks); it was removed on request.

**What that means.** One player can win or lose a very large amount on a single stock, and the house is on the other side of it. Every price move is still a fair bet, so removing the limit adds *risk*, not *edge*: a player who puts everything into a moonshot (§6.10) is making a big, fair gamble. The house is kept safe without limiting anyone by **thinning the tails of the price moves** (a rescue after a collapse is a doubling now, not a ten-fold jump; moonshots are braked harder; their catalysts are smaller) and by **keeping the house reserve in proportion to the money at stake**, topping it up automatically (§6.11). The admin page shows what players' positions could cost the house (§12). A short is paid for out of your cash like a buy; only the borrow fee and the margin call (below) apply to shorts.

### Shorting
**In plain English:** a short is a bet that a stock will fall. You borrow shares, sell them, and later buy them back. If the price fell you keep the difference; if it rose you lose it. **The amount you short is taken out of your cash** (it does not increase your cash) and held as collateral; when you cover, the collateral comes back with the gain added or the loss taken off. **There is no other limit**: no margin multiple, no borrow pool, no cap on how much you can short, only the cash you have.

**Opening and closing**
- **Pressing Sell when you hold none of the stock opens a short** (the button says "Short"). The chips are a share of your free cash, or type an amount in MB; that amount (plus the fee) leaves your cash at once. `Shorted 12.30 CLDR for 553.70 MB (taken out of your cash as collateral)`.
- **Pressing Buy while you are short covers it** (the button says "Cover"). The chips mean a share of the short position, an amount means MB worth to buy back. You can't hold a long and a short in the same stock; cover first.
- Fees are 0.1% when you open and 0.1% when you cover, the same as any trade, plus the borrow fee below.
- The average entry price, the amber chart line and the gain or loss all work for shorts (a short gains when the price falls).

```
open:   cash −= gross + fee          (gross = shares × price; the house holds the gross as your collateral)
cover:  cash += 2 × collateral − (shares × price) − fee      (for the part you cover)
equity: cash + Σ longs + Σ shorts (2 × collateral − buy-back cost incl. fee)
```
*Example:* you have 10,000 MB and short 5,000 MB of NVXA. Cash falls to 5,000 MB (about 4,995 of collateral plus a 5 MB fee). If NVXA then falls 20% and you cover, you get back 2 × 5,000 − 4,000 = 6,000 MB less the fee, so your cash goes to about 11,000. If it rises 20% instead you get back 4,000 MB and your cash is about 9,000. Closed at the same price you lose only the two fees (about 0.2%).

**Two things still protect the house** (each has a setting in §14):

**1. The borrow fee.** Holding a short costs money every second, charged from your cash and paid to the house:

`fee per game day = (0.03% + 0.1% × volatility) × (1 + 3 × how crowded the stock is)`, as a share of the short's value. "Crowded" is the total value shorted in that stock compared with a quarter of its size (`depth`, `short_cap_frac`), and it only changes the fee, never stops a short.

| Stock | Fee per real hour when few shares are shorted | When very crowded (4×) |
|---|---|---|
| GOLD | 0.10% | 0.40% |
| NVXA | 0.14% | 0.58% |
| DOGO | 0.27% | 1.08% |

*Example:* you hold a 286 MB short in NVXA for 4 hours while it is 5% crowded. The rate is 0.144% × 1.15 = 0.166% per hour, so you pay about 1.9 MB, on top of the 0.2% in trading fees. Shorts are deliberately not free to hold. Each holding's total fee shows in the position box ("Borrow fees paid").

**2. The margin call.** Because the collateral is the whole amount you shorted, a short can only lose more than its collateral if the price more than doubles. Each tick the engine adds up, over all your shorts, `value × the maintenance level` (25% for calm stocks up to 50% for memes, up to 75% for moonshots). If your **equity falls below that total**, **every short is closed at the market price** and a message tells you: `Margin call: your short in BYTE was closed at the market price.`

**When a gap goes past the collateral.** If a stock jumps so far, so fast (an opening jump, a catalyst, a moonshot's 100% day) that the loss is bigger than the collateral and your cash can't pay the rest, you lose the collateral and your cash, the short is closed, and **the house absorbs the rest**. That loss is counted in `short_shortfall` in `/api/admin/stats`. A cover you ask for yourself is refused if you couldn't pay the loss ("Not enough cash to cover the loss on this short"); a margin call and a bankruptcy are not refused.

**Old saves.** A save made when a short *added* its proceeds to your cash is converted when it loads: each open short's collateral (twice its entry value: the proceeds that had been added and the same amount held) moves out of the cash into the house, so nobody's equity changes. (`Engine._migrate_short_model`.)

### Orders: limit, stop-loss and take-profit
**In plain English:** you can leave an instruction that the server carries out for you when the price reaches a level, so you don't have to watch the screen. An order is nothing more than a market trade that happens later, at the price of that moment.

| Order | Waits for | Then |
|---|---|---|
| **Limit buy** | the price to fall to your trigger or lower | buys (with a share of free cash, or an amount in MB) |
| **Limit sell** | the price to rise to your trigger or higher | sells (or opens a short if you hold none) |
| **Stop-loss** | your position to move **against** you to the trigger | closes the position |
| **Take-profit** | your position to move **in your favour** to the trigger | closes the position |
| **Bracket** | either of a take-profit and a stop-loss that you set together | closes the position and cancels the other one (one-cancels-other) |

- Stops and take-profits need an open position and are **close-only**: they can only close it, never flip you the other way. For a long the stop is below the price and the take-profit above; for a short the reverse. A trigger on the wrong side of the current price is refused with a message that says which side it must be on.
- **They fill at the market price, not at the trigger.** If the price gaps through your trigger you get the new price. There is no price improvement and no slippage, and an order never moves a price. Because it is exactly the trade you could have made by hand at that moment, an order gives nobody an edge (the simulator's `bracket_trader` takes a profit and a stop on every position and loses just its fees).
- An order is checked once a second. It is carried out under the usual rules: cooldown and cash. If it can't be filled (no cash for a limit buy, say) it is cancelled with a message to you.
- You can have up to 20 open orders (`max_orders`) and 6 in one stock. An order expires after 7 days (`order_expiry_seconds`). Orders are saved with the game and survive a restart.
- **Where:** the stock page has an order panel; the holdings page lists **Open orders** with a cancel button. Over the socket: `{"type":"order","action":"place|bracket|cancel",...}` (§12).

### There are no trading halts
Trading never pauses. However far or fast a price or the whole market moves, you can still buy, sell, short and cover, and your orders and margin calls still run. (The game used to pause trading in a stock for a minute after an extreme move, and in the whole market for two minutes after a 4% move in the index. That "circuit breaker" was removed on request on 2026-10-04: it only ever restricted what players could do, never a price, so removing it changes no price and no expected result, but it means a crash can be traded straight through, and the house carries that risk, §6.11.) The old `halts_enabled`, `halt_move`, `halt_window_seconds`, `halt_seconds`, `halt_market_move` and `halt_market_seconds` settings in a content pack are simply ignored.

### The market never closes
Pre-market, the regular session and after-hours all let you trade, with the usual 0.1% fee and no spread (§3, §6.8). Everything else keeps working too: charts, news, the portfolio and history pages, chat, margin calls and borrow fees. **Ex-dividend dates and bankruptcy or rescue decisions happen when the regular session opens**, as in a real market; positions are otherwise untouched. Set `premarket_seconds` and `aftermarket_seconds` to `0` to switch the sessions off and get a flat, always-open market.

### Limits per trade
- **Minimum:** 1 MB.
- **Cooldown:** 1 second between trades in the same stock (`COOLDOWN`). The page also ignores a second click on the same stock within 0.3 s.
- **Size:** limited only by your free cash (buys and shorts). There is no position limit and no slippage: you get the displayed price.

### Round trip
Buying and immediately selling back returns `c × 0.999 × 0.999`: about **0.2% lost to fees, nothing else**. A short opened and closed at the same price loses about 0.2% the same way.

### Average entry price
Each player has a `cost` per ticker: the total entry value of the open position (for a short, the value of the shares when sold). A buy or short adds `shares × price`. A sell or cover removes the same fraction of cost as of shares, so **the average entry price (`cost / |shares|`) is a share-weighted average across all entries and doesn't change when you close part of a position.** It is shown on the holdings page, in the stock page's position box, and as the dotted amber line on the chart. Saves from before cost tracking start each position at the price when the new code first loaded.

### Equity
Equity = cash + the sale value of each long (`shares × price × (1 − fee)`) − the cost to buy back each short (`shares × price × (1 + fee)`).

---

## 5. Where money lives (conservation)

Every memebuck is in exactly one of three places:

```
player cash  +  house reserve  +  fees  =  minted
```

`total_tokens() == minted` is checked by `sim.py` (drift about 1e-10, floating-point rounding) and logged on load.

**What changes `minted`** (money entering or leaving the game):
- `credit(player, amount)`: a deposit or signup bonus (later: a crypto purchase)
- `debit(player, amount)`: a withdrawal (only free cash, not positions)
- the house putting in capital: the 50,000 MB reserve (`house_seed`) and the **automatic top-up of the reserve** when it falls below its floor (§6.11; recorded as a `recap` event in the ledger and counted in `recapitalized`)
- a **game reset** (§1): closing positions settles with the house, and setting every balance back to the start mints or burns the difference, so the books still balance

**What moves money between places:** trades (player cash ↔ house reserve, fees → fees) and bankruptcy (holders are paid from the house reserve a fraction of the last price, §6.6).

**What never moves money:** news, noise, mean reversion, regimes, earnings, rescues, **catalysts**, **offerings** (only the share count changes), **volatility** and the **trading sessions**. They change prices only. The social features (achievements, quests, the daily contest, chat, profiles) never touch real money at all: the contest uses a separate paper account (§10.4), and their rewards are medals and badges, and a test (§16) runs two identical markets, one with heavy social activity, and checks that every price and the token books are identical.

**Every money event is also written to the ledger** (§13): joins, deposits, withdrawals, buys, sells, shorts, covers, margin calls, dividends, borrow fees, bankruptcy payouts and reserve top-ups, each with the change it made to the player's cash, the house reserve, the fees and the position's cost. After a crash the server replays the events recorded since the last snapshot, so no trade is lost. The ledger is also where the history page and the CSV export come from.

### Who pays whom (important design change)
Before, every stock was a constant-product pool (and later held seed tokens, see below), so a player's trade moved the price and winners were mostly paid by other players. Because trades no longer move prices, **the house is the counterparty to every trade**:
- If a player profits, the money comes out of the house reserve. If a player loses, it goes into the reserve.
- **House P&L = −(players' combined trading P&L).** The fees the players paid are part of it; what is left over after the fees is `liquidity_pnl` (the admin page calls it the **trading result**), what the house won or lost as the counterparty to everyone's trades. Example: players +73 MB after fees, fees collected 20 MB: the house's trading result is −93 and its P&L is −93 + 20 = −73 (the players' +73 is already net of the fees they paid). `house_stats()` reports the parts.
- The house reserve is kept above a floor in proportion to the players' money and the risk they have taken on (§6.11), and is topped up automatically, so it does not go negative. With no position limit (§4) a big winning bet on a moonshot (§6.10) is paid from here, and the admin page shows how much the players' positions could cost (§12).

Because there is no price impact, **no public-information edge may exist**. That is why news (§7), mean reversion (§6.2) and earnings are built so their expected price move is zero. `sim.py` checks it (see `ROADMAP.md`).

**Stocks hold no tokens.** Until 2026-10-05 every stock held "seed liquidity" (`T`, the content pack's `depth`, 2,500 to 40,000 MB each, about 2.6 million MB in all) that the house put in at listing. It was a leftover of the old pool design: trades never touched it, every winner was paid from the reserve, and it only sat there, which made the admin page's "house capital" look 20 times larger than the money that can actually pay anyone. It is gone. A new listing now costs the house nothing and a delisted or bankrupt stock returns nothing, because it never held anything.

`depth` is still in the content packs, but it now means only the stock's **size**: `base` (equal to `depth`) is the weight a stock has in the indices and sector spillovers, and the yardstick for how crowded a short is (§4). The news effect used to be scaled by `T / base`, which was always exactly 1, so removing it changes no price.

**Old saves are converted on the first load.** The seed tokens of every stock in the save are retired: they are taken out of `minted` and out of the house capital, and **the reserve, the fees and every player's cash and positions stay exactly as they were** (the log says "retired N MB of seed tokens"). The clean save is written at once, and loading it again changes nothing. A test (`test_no_pools.py`) builds a save in the old format and checks all of this, including a crash before the first save. The house reserve does not grow by the retired tokens (they were never spendable); that is why the admin card now reads "capital put in" and shows only the starting reserve and the top-ups.

---

## 6. Price dynamics: what moves prices each tick

Each stock's `price` equals its `fair` value. Every outside move with return `r` is applied as `fair ← fair × (1 + r)`.

During a tick, all outside moves are **queued**, combined, and applied together in `_flush_moves`, in this order:

### 6.1 Random noise (`_random_market_moves`)
A three-factor model, drawn fresh each tick:
```
σ_market = β × 0.18
σ_sector = 0.08
σ_idio   = √max(σ² − σ_market² − σ_sector², 0.005²)

r = (σ_market·Z_market + σ_sector·Z_sector + σ_idio·Z_idio) × volatility_scale / √(252 × 1800)
     × (volatility multiplier, §6.7) × (session factor, §6.8)
```
`Z_market` is shared by all stocks this tick, `Z_sector` by the stocks in one sector, and `Z_idio` is per stock. The result is clamped to ±1% per tick for ordinary stocks (five typical seconds of noise, with a floor of 1%, so the clamp grows with the volatility of a moonshot).

**Negative betas are hedges.** Gold (`GOLD`, β −0.3), the gold trust (`GLDN`, β −0.25) and the bond fund (`BOND`, β −0.15) move against the market factor, so they tend to rise when the market falls and vice versa. Regime shifts and market-wide news also move stocks by `β × index move`, so the same sign applies there: gold rises in a recession and falls in a boom. Several templates also list gold-specific betas (war, flight to safety and so on).

**Commodities used to trend, and no longer do.** They once added a slow, mean-reverting drift on top of the noise (`trend ← 0.998·trend + small shock`) so they ran in supply/demand cycles. A drift that persists for minutes is predictable by construction: this one had a half-life of about 6 minutes and, for the oil price, a typical size of about a third of the noise over 20 minutes, so a trader who simply went with the last 10 minutes' direction should win a little. An engine-only probe (`probe2`-style: 36 seeds x 4 h, commodities only) measured it: +0.15% over the next 20 minutes before fees (+0.26% when the last move was over 1%, correlation +0.06). That is far below the 1% round-trip fee, and its quoted t-statistic (4.1) is overstated because the samples overlap (an honest figure is nearer 1.7), so it is not proof on its own, but a predictable drift is exactly what the house must not fund. Commodities are now pure noise like every other stock, and the same probe on fresh seeds gives -0.12% (correlation -0.05, about 1.4 standard errors once the overlap is allowed for): no usable signal in either direction. Volatility clustering (§6.7) still gives them calm and stormy stretches without making any direction likelier. The old drift can be switched back on for experiments with `commodity_trend` (a multiplier on its size, default 0); the `trend_follower` strategy in `sim.py` and the probe in §17 are what check it.

### 6.2 Mean reversion (`_mean_revert`)
A slow pull of `fair` back toward the reference price `P0`:
```
rate = 1 − 0.5^(1 / (H × 1800))       H = mean_reversion_halflife_days = 90
r    = (P0 / fair)^rate − 1
```
Symmetric in log price. With `H` = 90 game days (45 real hours), half of any gap closes in about 2 real days. **Moonshots (§6.10) are not pulled back at all**: a pull on a stock that is supposed to be a free random walk would be a predictable drift.

*Why 90 and not faster:* at `H` = 7, a stock that dropped below 0.9× bounced about +1.8% in the next 30 minutes, which beats the 1% round-trip fee. With no price impact that would be a free edge against the house. Keep `H` at 90 or more.

*Checked on many seeds (2026-10-02):* with the 10-strategy simulator, the `value` strategy (which buys dips) returned +1.3% (t 1.2) at `H` = 90, +1.3% (t 1.2) at `H` = 730 and +2.3% (t 2.4) with reversion off. Reversion was therefore not what made it profitable. The profit came from the news (see below), and with the news fixed a fresh 40-seed run gave `value` +0.6% (t 0.7), no strategy flagged. `H` stays at 90.

**Hidden reversion is easy to create by accident.** Any news mechanism whose average move depends on the stock's state (below its reference, just fell, just rose) is a mean-reversion or momentum edge that `value` or `dip_buyer` farms. One was found this way: continuation follow-ups used a weaker strength tier than reversals, so the average follow-up leaned toward a reversal (`value` +3.1%, t 3.2). Both branches now use the same strength and differ only by the 0.8×/1.2× scale. A second one was the hard daily clamp, which acted as a reflecting wall (see §6.5). Any rule that treats up and down moves differently depending on where the price is can do the same, so scale moves by a number known in advance, never by their direction.

**Resolved (2026-10-02): the leftover edge was the daily limit, not reversion.** After the follow-up fix, `value` still leaned positive (+0.6% and +1.8% on two 40-seed runs). A paired run on the same 40 seeds with one mechanism switched off at a time found the cause: **the daily limit** (−2.7% without it, t −3.2). Mean reversion (−0.04%), dividends, rating notes, company stories, the mood tilt and follow-ups made no significant difference. The limit is now a soft, direction-blind brake (§6.5). With it, 40 fresh seeds give `value` −0.4% (t −0.5) and no strategy is flagged, and a run with a short quarter flags nothing either. `paired.py` (§1) is the tool that found this.

### 6.3 News events (`_spawn_event`)
See §7. Each event queues a return per affected stock. Earnings reactions (§7.8) are queued the same way.

### 6.4 Dependency spillovers (`_dependency_returns`)
After the above is queued, spillovers are added **in the same tick**:
- **Company links:** `dependencies: {source_ticker: sensitivity}` gives `r_target += sensitivity × r_source`.
- **Sector links:** `sector_links: {source_sector: {target_sector: k}}`, using the base-weighted average of the source sector's queued returns. For example, energy → airlines −0.18.
- **Supplier, customer and rival links** (§7.15): a company's own suppliers, customers and rivals add a little to its move: +0.10 of a supplier's move, +0.15 of a customer's, −0.12 of a rival's (a customer doing well means orders for you; a rival doing well takes yours). The setting `relation_spillover` scales it (0 switches it off).

### 6.5 Limits (`_flush_moves`)
- At most ±15% per tick (`MAX_TICK_MOVE`).
- **A soft daily limit.** Every outside move is shrunk by a damping factor that depends on how far the stock has **already moved today** (measured from its price at the start of the game day):

  `damping = 1 ÷ (1 + (x ÷ L)^4)`, where `x = |ln(price now ÷ price at the day's start)|` and `L = min(daily_move_cap = 15%, σ_d × (1.5 + 0.75 × min(|β|, 2)))` (NVXA: L = 6.6%). **Moonshots** (§6.10) skip the 15% cap and use `L × 3` (it was ×6: a run-away moonshot is braked sooner now, §6.11), so a 100% day is still allowed.

| How far the stock has already moved today | Damping | A news shock that would move it 2% moves it... |
|---|---|---|
| 0 (the day's start) | 1.00 | 2.00% |
| half the limit (3.3% for NVXA) | 0.94 | 1.88% |
| the limit (6.6%) | 0.50 | 1.00% |
| 1.5 × the limit | 0.17 | 0.33% |
| 2 × the limit | 0.06 | 0.12% |

  The day's start resets every game day (30 real minutes), so the limit is a brake on one day's move, not a permanent ceiling. Player trades are never limited (and never move prices anyway).

**Why a soft, direction-blind brake and not a hard wall.** The first version was a hard clamp: a price could not go past ±L from the day's start. That created a bias. Near the day's lower limit, further falls were cut off but rises were allowed, so a stock that had fallen all day tended to bounce back. A dip-buying strategy farmed that bounce: over two hours it earned about **+2.7%** more than it did with the clamp switched off (t = 3.2 on 40 paired seeds). That was the "small residual edge" found earlier.

The damping factor looks only at *where the price is now*, never at the *direction* of the move, so an up move and a down move are shrunk by exactly the same amount. Scaling every move by a number that is known in advance leaves the expected move at exactly zero, so there is nothing to bounce off. After the change the same paired test shows no significant difference with the limit on or off (+0.8%, t = 1.0), and `value` earns −0.4% on 40 fresh seeds, which is just the fees.

The setting `daily_move_cap` still controls the maximum `L` (set it to 0 to switch the limit off). The tests in §16 check that the factor is the same above and below the open, that an up and a down move are shrunk equally, that there is no protection from further falls near the lower limit, and (slow test) that switching the limit off doesn't make a dip-buying strategy worse.

**Very strong events open the limit for a while.** When a "very strong" event hits a stock (§7.5, about one headline in ten), that stock's daily limit `L` is multiplied by `major_event_limit_boost` (2.5) for `major_event_boost_seconds` (600 s = 10 real minutes). Without this a huge story would be squashed by the brake and a "very strong" headline would feel no bigger than a "strong" one. (The page no longer shows a badge for this.) Because the boost is known when the shock is applied and does not depend on its direction, it changes how far a move can go, not which way (the damping stays direction-blind).

### 6.6 Distress: rescue or bankruptcy, as a fair bet (`_check_distress`)
When `fair / P0 ≤ distress_price_ratio` (0.25, i.e. down 75% from its reference price) a company is resolved, once, one of two ways:

| | Chance | What happens |
|---|---|---|
| **Bankruptcy** | `q` | holders are paid **a fraction `b` of the last price** from the house reserve (no fee), shorts close at that price and the ticker is **delisted for good** |
| **Rescue** | `1 − q` | a surprise investor or lifeline deal: the price jumps by `(1 − q·b) ÷ (1 − q)` times, and the rating is reset to at least B |

**Why those numbers are tied together.** The two outcomes are chosen so that `q × b + (1 − q) × (jump multiple) = 1`: the *expected* value of the stock right after the event equals its value right before. So buying or shorting a stock that is about to be resolved has no expected gain or loss. (The first version, a 75% chance of losing half the price against a 25% chance of +25%, expected to lose 31% at the trigger: a house-funded **free short** for anyone who shorted a stock sliding towards the line. Ordinary stocks almost never fall 75%, so the earlier checks never looked there; moonshots do it all the time, which is how it was found. A test now checks the terms add up.)

| Stock | `q` | `b` | Rescue jump |
|---|---|---|---|
| Ordinary company | 50% | 25% | ×1.75 |
| Moonshot (§6.10) | 60% | 3% | ×2.45 |

For example, a moonshot at 0.20× its reference price: 6 times in 10 it files for bankruptcy and holders get 3% of the price; 4 times in 10 it is rescued and the price goes up about 2.45 times. **Why not more likely bankruptcy?** The rescue jump is `(1 − q·b) ÷ (1 − q)`, so the likelier the bankruptcy, the bigger the rare rescue has to be to keep the bet fair: with q = 90% the rescue was a ten-fold jump (×9.73), and with q = 75% it was ×3.25. A ten-fold jump is exactly the heavy tail that can hurt the house when a player has put everything into one stock, so the chances were moved towards a more even coin and the jump shrank to ×2.45 and ×1.75. The bet is exactly as fair as before (a test checks it for every stock type); only its shape is less extreme (§6.11). A stock is checked once per distress episode, and again once it has climbed clear of the line (above 1.25× the threshold); if it is rescued and then keeps falling to a quarter of the threshold it is resolved again, and a price below a thousandth of its reference simply fails. (With the old ×3.25 and ×9.7 rescues a stock always jumped clear of the line; the gentler ×1.75 and ×2.45 do not always, and for a while a rescued stock that kept collapsing was never looked at again.) Indices, ETFs and leveraged products (§9) are never checked. Distress is decided when the regular session opens (§6.8). Settings: `bankruptcy_chance`, `bankruptcy_payout`, `moonshot_bankruptcy_chance`, `moonshot_bankruptcy_payout` (§14).

### 6.7 Volatility clustering: calm stretches and storms
**In plain English:** real markets are not equally jumpy all the time. After a big move the next moves tend to be big too, and calm days tend to follow calm days. Each stock now has a **volatility multiplier** (`volm`) that scales how large its random noise is. A big move raises it, quiet ticks lower it, and it always drifts back toward 1.

```
after every tick:  volm += 0.01 × ( |move| / normal_move − 0.8 × current_multiplier )     (0.8 is the average size of a normal shock)
then it decays:    volm → 1 + (volm − 1) × 0.5^(1 / half-life)               half-life = 1 game day = 30 real minutes
kept between 0.5 and 3.0
the noise on the next tick is multiplied by  volm × market_volm
```

- **What "normal_move" means.** It is the size of a normal second *for the current session* (§6.8): a move is compared with what the thin pre-market or the busy open was expected to deliver, so the known shape of the day is never read as calm or as a storm. (A first version compared every move with a plain normal second, so the quiet pre-market sank the multiplier to its floor of 0.5 in every cycle, which halved the opening jump and the first minutes of the session. It is measured on the company's own move *before* the daily brake (§6.5) and *before* the spillovers from its partners and rivals (§7.15) too: the brake's 5% or so of shrinkage had been read as calm and had left ordinary stocks at about 0.6 of their stated volatility, and the spillovers add a little more than the noise the multiplier is measured against.)
- **The average is held at 1.** The update is very sensitive: news adds a little more than the noise it is measured against, and with a half-life of a game day an excess of 1% would lift the average multiplier by about 27%. So one **common factor**, the same for every ordinary stock and known in advance, pulls the average back towards 1 by 0.2% of the gap each second (a time constant of about eight minutes). That is slow enough that a market-wide storm (a very strong macro headline lifts every stock's multiplier at once) still lasts several minutes, and fast enough to cancel the bias. Individual storms and calms stay; with it the average sits at about 0.97-1.0 and a stock's stated volatility is its real one. (A first version pulled 10 times faster and erased a market-wide storm within a couple of minutes.) Moonshots are left alone, because their catalysts are meant to leave them jumpy.

- **A market-wide multiplier** (`market_volm`) rises in a Recession (1.2×), a Bubble (1.15×) and above all in a crisis (1.5×), sinks a little in a Boom (0.95×) and relaxes toward its target at 150 s per e-fold. So when the market is in trouble, everything gets jumpier together.
- **The page does not show it.** It used to drive a yellow VOLATILE tag; the tag is gone, and the number is no longer sent to the page (it also hinted at the market regime). You can still see how jumpy a stock is on its chart.
- **Example:** NVXA normally moves 0.062% per second. After a run of large moves its multiplier might reach 1.8, so it moves about 0.11% per second until it settles; half an hour later the excess has halved.

**Why this gives nobody an edge.** The multiplier is worked out from *past* moves and then multiplies a fresh, zero-mean random shock. It changes how big the next move is, never which way it points, so the expected move stays exactly zero. The simulator has a `vol_chaser` that buys stocks that have just had a burst of big moves; the paired check (§17) shows no gain from it. Switch clustering off with `vol_cluster_k=0` to compare. The state is saved, so a restart doesn't reset the calm and the storms.

### 6.8 Trading sessions: quiet before and after, a burst and a jump at the open
**In plain English:** a real market is not equally busy all day. Almost nothing happens before the open and after the close, a flood of orders arrives at the opening bell, it calms down through the day, and picks up a little into the close. The game copies that on the 30-minute cycle, on the real clock:

| Session | When | How the market behaves |
|---|---|---|
| **Pre-market** | first 5 minutes (`premarket_seconds` = 300): :00-:05 and :30-:35 | thin: ordinary noise is **0.35×** its normal size (`extended_noise`) |
| **Regular session** | next 20 minutes: :05-:25 and :35-:55 | busy: a **burst** at the open (2.5× at first, fading over about 2.5 minutes), a calm middle, a smaller burst (1.5×) in the last 2 minutes before the close |
| **After-hours** | last 5 minutes (`aftermarket_seconds` = 300): :25-:30 and :55-:00 | thin again, 0.35× |

**The opening jump.** The moment the regular session opens, every stock gets a fresh, independent shock the size of about 90 seconds' worth of ordinary noise (`open_jump_seconds`), with the usual market, sector and company parts: the whole market tends to gap the same way at the open and a volatile stock gaps more. For NVXA a typical jump is about 0.6%.

```
noise this second = ordinary noise × (volatility multiplier §6.7) × (session factor)
session factor:   pre-market and after-hours 0.35; regular session: burst-then-calm-then-burst shape × a constant
opening second:   + one extra random jump, drawn fresh, size ≈ √90 seconds of noise
```

- **The day keeps its volatility.** The constant in the regular-session factor is computed so that pre-market + regular session + after-hours + the opening jump add up to exactly one normal day of variance. A stock's annual volatility (`vol`) is what it always was; the sessions only decide *when* in the half hour it moves. A test adds the whole cycle up.
- **No direction anywhere.** Every factor is known in advance and the same for up and down moves, and the opening jump is a new random draw, independent of everything that happened in pre-market. So the sessions change how much prices move, never which way: you cannot make money by trading the open, or by watching pre-market to guess the jump. (An earlier design held news back during the closed minute and released it as a gap at the open. That made the gap *predictable from the news that had piled up*, so it was dropped: news now acts the moment it happens, in every session.) The simulator's `gap_long`/`gap_short` (hold across the jump) and `open_follow`/`open_fade` (trade what the jump did) all lose about their fees (§17).
- **Trading, news, margin calls and borrow fees carry on in every session.** News arrives at the same rate whatever the time. Ex-dividend dates and bankruptcy or rescue decisions take effect when the regular session opens. The opening jump goes through the same daily brake as any other move (almost nothing has moved yet at the open, so the brake is barely felt), and, being expected, it does not raise the volatility multiplier: the multiplier measures it against the jump it was expected to be (§6.7).
- **The page** shows the session in one header chip (there is no chart of it; an earlier version drew a bar chart of the cycle's busyness and it was removed). Hover the chip for the clock times in your own time zone. The chip says "Pre-market · opens in 3m 12s", "Market open · closes in 12m 04s" or "After-hours · pre-market in 1m 20s".
- `premarket_seconds = 0` and `aftermarket_seconds = 0` together switch the sessions off completely (the tests and the browser tests do this so they don't depend on the time of day). The two together can't take more than 29 minutes of the cycle: at least a minute of regular session is always left.

### 6.9 Offerings and buybacks (stock splits no longer exist)
**Stock splits were removed.** (A repeating-split bug in the old code had pushed 22 stocks of one real save to prices like 3e-22, shown as 0.0000 MB: the split left the price above twice its own shrinking reference, so it split again, and again. When a save loads, every stock is put back on its original scale: prices, charts, dividends and trigger prices times the split factor, shares divided by it, so every position keeps its value.) Splitting a stock rescaled its price, its charts, every position and every average entry price, and it kept breaking things, so there are no splits any more and no split badge. (Old saves load fine: a split already done stays done.)

**Offerings.** About every 20 minutes (`offering_mean_seconds`, 1,200 s) a company announces a **public offering** of 1-4% new shares, and `offering_delay_seconds` (300 s) later it completes: *"Quill Foods announces a public offering of 1.2 million new shares (2.1% of its shares outstanding), to settle in about 5 minutes."* then *"Quill Foods completes its share offering: shares outstanding rise to 58.3 million."* **The only thing that changes is the number of shares outstanding** in the stock's info (and so its market cap and earnings per share). No price move, no cash, no change in the financials. The price is a fair bet, and an offering is not news about the business, so there is nothing to trade on; a test checks that an offering changes no price and no balance. The announcement and the completion are on the news wire and in the company's news log.

**Buybacks** are still company stories (§7.7): "Quill Foods announces a buyback of 2.4% of its shares" retires shares. The share count changes at the next earnings report, cash moves by `change × market cap`, and the story moves the price like any other news, with the same zero-expected-move scaling.

### 6.10 Moonshots: tiny, wild companies that keep joining the market
**In plain English:** besides the steady companies there are lottery tickets: tiny, pre-revenue companies (a gene therapy waiting for one trial result, a rocket one test flight from the Moon, a fusion reactor, a quantum chip) that can move **hundreds of per cent in a day**, can be worth ten times as much by evening or almost nothing, and **go bankrupt easily**. Biotech is the commonest kind, but there are space, fusion, quantum, crypto, teleportation, time and antigravity ones too. New ones keep arriving, and the dead ones are replaced.

| | An ordinary stock | A moonshot |
|---|---|---|
| Annual volatility | 20-105% | **260-550%**: a typical day moves 16-35%, and clusters (one day +100%, the next -10%, then +20%, -2%, -5%, +3%...) |
| Beta (sensitivity to the market) | 0.5-2 | **2.5-4.5** |
| Size (`depth`) | 12,000-40,000 MB | **2,500-5,000 MB** (a tiny weight in every index) |
| Price | 8-260 MB | 0.6-14 MB |
| Revenue, earnings, dividends | yes | **none** (pre-revenue) |
| Daily limit | soft brake at about 2.5 daily sigmas, at most 15% | the brake is **3× looser** and has no 15% cap, so a 100% day is allowed |
| Pull back toward the reference price | very slow | **none** (a free random walk) |
| Margin to short | 1-2× | **up to 3×** (maintenance up to 75%) |
| Borrow pool for shorting | 25% of `depth` | 25% of a small `depth`: 625-1,250 MB for everyone together |
| Distress | 50% bankrupt, ×1.75 rescue | **60% bankrupt (holders get 3%), ×2.45 rescue** (§6.6) |
| Rare catalysts (§7.13) | now and then | **10× as likely, and bigger** (their upside is trimmed to 70%, §6.11) |

- **How new ones arrive.** A new game starts with 4 moonshots (`moonshot_initial`). About every 15 minutes (`moonshot_mean_seconds`) another one lists, as long as fewer than 8 are trading (`moonshot_max`), so a bankrupt one is eventually replaced. Each is generated: a name (like "Madyne Oncology" or "Xygen Power"), a ticker, a one-line description of what it does and what result decides its fate. A listing prints a "NEW LISTING" headline and shows the **NEW** badge for 30 minutes (§8, §11). A bankrupt moonshot is gone for good and its ticker is never reused. They are saved with the game and come back after a restart (§13).
- **Why a typical moonshot goes down, and why that is fair.** The *average* price change is zero, like everything else here. But with huge volatility the *typical* (median) path falls, because a big gain followed by an equal percentage loss leaves you behind (+100% then -50% is back where you started, but +100% then -100% is not). A few paths soar, which keeps the average level. That is the lottery-ticket shape: most fall and many fail, a few multiply. Nothing is rigged against you and nothing is rigged for you.
- **No edge.** Moonshots have no mean reversion (that would be a predictable drift), their noise has no direction, their catalysts and distress outcomes are fair bets (§6.6, §7.13), and they list at their reference price with no first-day pop. The simulator's `moon_hodl` (buy every new listing), `moon_short`, `distress_buyer` and `distress_short` test this (§17).
- **The house carries more risk,** and that is what §6.11 is about. With no position limit (§4) one player can win a large sum on a moonshot, and the house pays it. It is a fair bet in expectation but a heavy tail, so moonshots have a higher borrow fee and margin-call level, a tighter daily brake, smaller catalysts and a gentler rescue, and the house reserve is kept in proportion to the money at stake.
- Moonshots are ordinary listings for everything else: they trade, appear in sector indices where the sector fits, can be starred and searched, and move with the market and their sector.

### 6.11 Keeping the tails thin and the house safe (no limit on position size)
**In plain English:** players may put as much as they like into any stock. Every bet is fair, but a fair bet can still be a big one: if a player puts everything into a moonshot and it jumps ten-fold, the house pays. You cannot cap that by limiting the player (that was the request), so the game works on two other things: how extreme the price moves can be, and how big a cushion the house keeps.

**1. Thinner tails (the price moves themselves).** Each change keeps every bet exactly fair; only the *shape* is less extreme. Measured on 8 simulated worlds of 3 hours, over every 30-minute window of every stock:

| | Before | After |
|---|---|---|
| A rescue after a collapse, ordinary company | ×3.25 | **×1.75** |
| A rescue after a collapse, moonshot | ×9.73 | **×2.45** |
| A moonshot's daily limit multiple | ×6 | **×3** |
| A moonshot catalyst's upside | +80% to +190% | **+56% to +133%** (`catalyst_moonshot_scale` 0.7; the loss is re-derived so the bet stays fair) |

**What that did to the moonshots** (every 30-minute window of every moonshot, 8 worlds × 3 hours; before and after both run on the same seeds, `scratchpad` script `tails.py`):

| 30-minute return of a moonshot | Before | After |
|---|---|---|
| Standard deviation | 102% | **64%** |
| Excess kurtosis (how heavy the tails are; a bell curve is 0) | 75 | **20** |
| 99th percentile (1 window in 100 is better than) | +504% | **+223%** |
| 99.9th percentile | +1,276% | **+583%** |
| Best window seen | +1,495% | **+733%** |
| Worst window (loss) | −97% | −98% |

Ordinary stocks were unchanged by this when it was done (their 99th percentile was +22% to +27% and their 99.9th about +55% to +60% on both runs, coming from catalysts and industry shocks); the ordinary catalysts were reined in separately on 2026-10-05 (§7.13). The loss side was never the problem (a stock can only lose 100%); the **upside** was. A moonshot is still a lottery ticket (one 30-minute window in a thousand is still above +580%): that is what the lottery is, and the house reserve is sized for it (below) rather than the lottery being removed. (Both runs' mean is positive only because a stock that goes bankrupt drops out of the sample before its last, worst window; it is not an edge.)

**2. A house reserve in proportion to the money at stake.** Every five seconds the engine checks the reserve against a **floor**: the larger of 10% of the human players' total equity (`reserve_floor_frac`) and half of the **stress loss** (`reserve_stress_frac`), and never less than `reserve_floor_min`. If the reserve is below the floor it is topped up to it, the new money being recorded as house capital (`recapitalized`, and a `recap` event in the ledger so a crash can't lose it). **This changes no price and no payout**: every winner is paid in full either way, and a test runs the same market with the top-up on and off and gets identical prices and balances. It only means the house's capital grows when players are collectively winning. `reserve_recap=false` switches it off; the alerts below remain.

**3. A risk report for the admin** (`house_risk()`, shown on the admin page and in `/api/admin/stats`). The house is the other side of every position, so a stock that players hold net long hurts the house when it rises and one they hold net short hurts it when it falls. For each stock the page shows the players' **net** position in MB, three of its own daily sigmas, and what that move would cost the house. The **stress loss** is the total if every stock moved three daily sigmas against the house at once (deliberately pessimistic, since the stocks are not all driven by one thing; a short is capped at the whole position). The page warns when the stress loss is larger than the reserve and when one stock is more than half the risk.

**Honest limits.** None of this makes a lucky win impossible: a player who goes all in on a moonshot can still win a lot, because the bet is fair and fair bets have winners. What it does is make the biggest swings smaller, keep the reserve ahead of the exposure, and show the exposure. If real money is ever used, the floor is the operator's capital decision (`ROADMAP.md`, A12).

---

## 7. News, catalysts, narrative, company stories and ratings

### 7.1 When things happen
- **Random events:** a Poisson process with mean gap `event_mean_seconds` = 120 s.
- **Company stories** (§7.7): mean gap `issue_mean_seconds` = 100 s across the whole market.
- **Two-company stories** (§7.11): mean gap `cross_mean_seconds` = 240 s.
- **Catalysts** (§7.13): rare news that moves one stock a lot, mean gap `catalyst_mean_seconds` = 480 s across the whole market.
- **Industry-wide shocks** (§7.14): news that moves a whole sector at once, mean gap `sector_shock_mean_seconds` = 600 s.
- **Earnings:** every equity with revenue reports **once a quarter**: 63 game days, which is **31.5 real hours** (§7.7). The first report is a random time within the first quarter, so companies report on different days. "Upcoming events" shows the countdowns, in days and hours.
- **Bank reviews:** each equity is reviewed every `rating_review_seconds` = 600–1,500 s. They are not scheduled publicly.
- **Follow-ups and switch-ups** to remembered stories (§7.4): 2-8 minutes after the original.
- **Regime shifts:** every 7–14 game days (3.5–7 real hours).

### 7.2 Picking and scoping a template
A template is chosen with probability proportional to its `weight` (weight-0 templates never fire randomly). Each has a `scope`:
- `market`: affects everything through `betas`, plus a market-wide move `index_move = index_bias × impact` applied to every stock by its beta. A negative `index_bias` means the template's **"up" text is bad news** for the market (for example "Ceasefire collapses" has −0.6).
- `sector`: a sector; `self` in `betas` means that sector.
- `company`: a company; `self` means that company.

`betas` can key on a ticker, a sector id, `self`, or `*`, and add up per stock. The index (`MSI`) is never hit by news directly; it moves only because its constituents do.

A template can set `"good": "down"` to say its "down" text is the good news (used by `credit_stress`). Otherwise "good" means the "up" text unless `index_bias < 0`.

### 7.3 The hidden narrative: mood tilts what kind of news you get
The engine keeps a **mood** from −1 (gloom) to +1 (euphoria). **Players are never shown it**: it is not in the state sent to the browser, not in the header, and no headline names it, the regime or a crisis.
- **Market mood** eases (time constant 150 s) toward a target set by the regime: Recession −0.6, Expansion +0.15, Boom +0.55, Bubble +0.75. A **crisis** (see below) makes the target −0.9.
- **Sector moods** and **company moods** start at 0, are nudged by news about them (bigger nudges for stronger news) and decay back (400 s and 600 s). So a company with a run of good news is a little likelier to get more.

The chance that a random headline is **good news** is `0.5 + 0.3 × mood`, limited to 15–85%. For a sector event the mood is `0.6 × sector + 0.4 × market`; for a company event it is `0.5 × company + 0.3 × sector + 0.2 × market`. Over a long time, a Boom prints more good headlines, a Recession more bad ones. Players can only infer this by watching the news flow.

**A crisis** starts silently when a "very strong" market-wide bad event fires. It lasts 8–15 real minutes and just makes bad headlines much likelier. It is never announced.

Regime shifts are still a market-wide price move, announced by tone only ("Selling sweeps the market as confidence cracks"), never by name.

**Why this gives nobody an edge.** If the likelier direction moved prices as much as the unlikelier one, a Boom's drift would be free money. So the headline's price move is scaled by `2 × (1 − p)`, where `p` is the chance of that direction. At `p` = 0.8 the common headline moves prices 0.4× as much and the rare one 1.6×. The expected move of any headline stays exactly zero: knowing the mood doesn't tell you where prices go. Moves from explicit directions (bank notes, company stories) use the same rule.

### 7.4 Headlines are unique, and the wire remembers
- Each headline is **dressed** with an optional lead-in ("Desk note:") and a tail that fits its tone (good or bad) or is generic. Nothing in the wording reveals the mood.
- `Engine._unique` checks every headline against all headlines ever printed (the last 6,000 are kept and saved). A repeat gets extra tails; if all of them are taken it gets a timestamp, so **no two headlines are ever identical**.
- **Follow-ups and switch-ups.** When a market, sector or company story breaks, it is remembered with probability 0.30–0.35 (0.55 for company stories). 2 to 8 minutes later it **comes back**:
  - **UPDATE:** it continues, with 60% chance ("The damage deepens: new details emerge after '…'", "Analysts lift estimates following '…'"), or
  - **REVERSAL:** a switch-up with 40% chance ("Relief: new details soften the blow from '…'", "Reality check: new details cast doubt on '…'").
  The follow-up quotes the original headline, moves prices like any news, and can chain once or twice more (30% each time). **To stop momentum from being a free edge**, the likelier continuation moves prices 0.8× and the rarer reversal 1.2× **at the same strength tier**, so the expected move of a follow-up is zero whichever way you bet. (Using a weaker tier for one branch would break this; see §6.2.)
- Follow-ups to a company story also change what that company's next earnings report shows (a continuation adds half the original effect, a reversal undoes 70% of it), and the report names them ("further developments in …", "a reversal after …").
- Memory is saved with the game state (up to 40 stories), and every headline that names a stock stays in that stock's news log.

### 7.5 Size of the move
```
strength ~ news_strength_weights   (bystander 25%, weak 40%, strong 25%, very strong 10%)
impact   ~ Uniform(news_move_ranges[strength])
           bystander 0–0.5% · weak 1–3% · strong 4–9% · very strong 10–18%

per stock:
  v        = clamp(√(σ / 0.30), 0.5, 1.8)          more volatile stocks react more
  R        = β·index_move·v + impact·beta_i·sens·v
  R        = clamp(R, ±σ_d × event_strength_limits[strength] × clamp(|β|, 0.5, 2))
```
then multiplied by the narrative scale from §7.3. **The final clamp usually decides the size.** To make news bigger or smaller, change `event_strength_limits` and check with `tune.py`.

### 7.6 Breaking news vs rumours
- **Breaking:** the full move happens instantly in the same tick as the headline.
- **Rumour** (`rumor: true` templates, with probability `rumor_prob` = 60%): the rumour shows a direction correct with probability `rumor_credibility` = 0.75, the price moves by its expected value (`0.5 × R`), and 45–90 s later a **CONFIRMED** or **CORRECTION** headline moves it the rest of the way. Expected profit from trading a rumour is zero.
- **The hidden mood waits for the truth.** The mood moves with the tone of each headline (§7.3). For a rumour that tone is the *true* direction, which the price has not yet fully moved to (only the expected half has), so if the mood moved at once, anyone who could read it would know where the rest of the move goes. It now reacts only when the rumour is confirmed or corrected (and a crisis, which a very strong bad market story can start, waits too). This was found when the fee was cut to 0.1%: the mood-reading oracle (§1) earned +0.4% per 2 hours (t +3) that a 1% round-trip fee had been hiding, +0.9% before fees in an engine-only probe (t +4.0); with the fix it earns +0.05% (t +0.4). Players cannot see the mood, so this was never an edge for them, but a hidden edge is a hole in the fairness argument.

### 7.7 Company stories and earnings (the "reason" for a change)
Financials (revenue, net margin, cash, debt) now **evolve** and are saved. They don't change at random: a big change needs a story that was **in the news first**.

1. **A story breaks** (`_issues`). A random equity gets a headline such as "X warns of supply-chain disruption at a key supplier", "X's CEO faces board pressure", "X wins a major multi-year contract" or "X pays down debt ahead of schedule". There are 20 kinds (10 bad, 10 good) with 90 phrasings between them, including a change of CEO, share buybacks (§6.9) and a data breach, a recall, a labour dispute, a lost customer, a new contract and more. Each story names the company's real CEO, CFO, product, city, supplier, customer or rival (§7.10). The chance of good news is `0.5 + 0.25 × (safety − 0.5) + 0.25 × company mood`, so weaker or gloomier companies draw bad news a little more often. The price reacts immediately (a "weak" or "strong" company event).
2. **The story is remembered** against the company with its effect on margin, revenue and debt. **The effect is scaled to the price move the story caused** (between 0.25× and 2.5× of its catalogue size, debt effects 0.5×–1.5×), so a story the market shrugged off changes the numbers little and a big shock changes them a lot. Earnings therefore confirm the price instead of contradicting it, and the P/E stays steady. Follow-ups (§7.4) are scaled the same way.
3. **At the next quarterly report** all remembered stories are applied together:
   - margin moves by the stories' effect plus a small noise term (±0.8 points); revenue moves by the stories' effect plus small noise (±1%). There is **no built-in growth and no pull back toward a long-run margin**: those would be predictable earnings changes that the price doesn't already contain.
   - debt scales by the stories' effect; cash grows by 12% of net income (if cash would go negative, the shortfall becomes debt)
   - an **EARNINGS** headline reports revenue and margin, **names what drove it** ("Driven by a supply-chain disruption; new management and 24 smaller developments."), and states the dividend (below). It says nothing about the game's own bookkeeping: no "as flagged in earlier news", no "expected", no hint of what the company had pending
   - the price reaction is only the **unannounced** change in net income (noise in margin and revenue, capped at ±6%), because the stories already moved the price when they broke.
4. If the company had no stories pending, the headline simply doesn't say what drove it, and the numbers barely move.

#### When companies report (the quarter)
**In plain English:** a "quarter" in this game is 63 game days, which is **31.5 real hours**. Every company with revenue reports once per quarter, **only before the open or after the close**, and the reports are spread out so there are always a few every game day and one is always coming up.

- **Only in pre-market or after-hours.** A report is scheduled into the first 5 minutes of a 30-minute cycle (pre-market) or the last 5 (after-hours), at a random second, never in the regular session. Which of the two is a coin toss for each report. (A flat market with no sessions, or a demo with a quarter shorter than a game day, has no such windows.) §6.8 describes the cycle.
- **Spread, not bunched.** With about 150 reporting companies on a 63-game-day quarter there are about 2.4 reports per game day. The first reports are placed by **best-candidate sampling**: for each company a dozen random times in the coming quarter are tried and the one farthest from every report already on the calendar is taken, so there are no long dry stretches and no pile-ups ("Upcoming events" always has something near). A company listed later gets a slot the same way, in a quiet part of the calendar. (Real companies bunch their reports into a few weeks; the game deliberately does not.)
- **A quarter apart, give or take a few days.** After a report the next one is a quarter after its nominal slot **plus or minus up to 4 game days** (about 2 real hours; `earnings_jitter_days`), then moved into the next pre-market or after-hours window. The slots drift a little each quarter but stay spread out, so the gap between two reports of the same company is 31.5 hours give or take a couple.
- **Restarts and old saves.** The nominal slot is saved. A save from before this calendar has its upcoming reports moved into windows; a report that would have fallen due while the server was down is given a fresh slot instead of all firing at once.
- **Many stories per quarter.** Company stories arrive about every 100 seconds across the whole market, so each company collects roughly 30 of them per quarter. They all stay "pending" until the report, which applies them together. The headline names the **three biggest** and counts the rest ("Driven by a supply-chain disruption; new management; a major contract win and 24 smaller developments."). The company's earnings history on its stock page lists up to six, and says how many more there were.
- **Why long quarters don't make prices jump at the report:** each story already moved the price when it broke, and its effect on the numbers was scaled to match that move. The report mostly confirms prices; only the small unannounced part (margin and revenue noise) moves the price. The calendar is public (the "Upcoming events" list), and a report's reaction has no expected move, so knowing when one is due is no edge (the simulator's `earnings_runup` checks this).
- To test or demo earnings quickly, shorten the quarter with `earnings_quarter_days` (for example `0.01` is an 18-second quarter; the browser test uses it).

#### Dividends
Equities with a dividend yield in `market_profiles.json` pay dividends, **one per quarter**, so the yield is a true annual figure again.
- **Declared with each report.** The dividend per share is `annual yield × reference price ÷ 4`, scaled by how the company's margin compares with its starting margin (between 0× and 1.5×). A higher margin **raises** it, a lower one **cuts** it, and a company with a negative margin **suspends** it. The headline says which: "It raises its dividend to 0.6940 MB per share, going ex-dividend in 5 minutes." (A report that comes out in after-hours says "going ex-dividend when the market next opens" instead, because ex-dividend dates take effect at the open.)
- **5 minutes later, in the regular session, it goes ex-dividend** (a headline announces it). Every long holder receives `shares × dividend` from the house, every short holder pays it (never more than their cash), and the price drops by the dividend. Holding through the ex-date therefore has no expected gain or loss, and buying just before and selling just after only costs fees.
- Dividends received are tracked per holding (holdings page *Dividends* column and the stock page position box). They are not included in the position's P/L %.
- **"Dividend yield"** on the stock page is `4 × the declared dividend ÷ the live price`, an annual figure.

So a firm that is doing well can report badly, but only after a story the player could have seen. **Players can look back:** every stock page lists *Earnings history* (each report with the stories behind the numbers and when they broke) and *Company news & analyst notes* (every headline that named the stock).

### 7.8 Bank ratings
Rating ladder: `D C CC CCC B BB BBB A AA AAA`.

- Each equity has a hidden **safety** score (0.3–0.85 at listing, drifting slightly at each review). Banks "know" it; players have to infer it.
- A bank's **score** (0–1) is `0.30·safety + 0.25·(1 − volatility penalty) + 0.15·(1 − beta penalty) + 0.30·balance sheet`, where the balance sheet combines margin, cash minus debt, and debt relative to revenue. The score is stretched onto the ladder, and each of 6 fictional banks has a small bias (some are stricter).
- At each review a bank compares its target rating with the current one. If they differ, it moves the rating **one notch** toward the target (70% of the time) and publishes it as a price-target note. **About two notes in five (40%) give a reason** (*"Quill Capital lowers price target on X to 80.17 MB, citing leverage concerns"*); the other three in five just state the new target (*"Quill Capital lowers price target on X to 80.17 MB"*). A reason is a true one drawn from the company's public figures (thinner margins, leverage, cash burn, a stronger balance sheet, a defensive profile...), never the hidden safety score. The note moves the price as a "weak" company event, with or without a reason. If nothing changes, it sometimes publishes a "reiterates" note with no price move.
- Initial ratings come from the same formula, so ratings now reflect safety, volatility, beta and the financials, and change as earnings change those financials.
- Commodities, funds and the index have no rating.

### 7.9 (removed)
This section described the "hints" that the news bots read. The bots are gone (§10), and so are the hints.

### 7.10 People, products and places
**In plain English:** every company has a cast. The news names them, and they come back later.

Each equity gets a **persona** the first time it is listed, built from its ticker so it is the same on every server start, and saved with the game:

| Field | Example (NVXA) | Where it comes from |
|---|---|---|
| CEO and CFO | Tariq Takahashi, Ingrid Brennan | 50 first names × 52 surnames |
| Flagship product | Helix Pro (and a second product, Vector Chip 9) | a sector-specific word pair: chips get "Nova Core" or "Helix Pro", drugs get "Curalex", airlines get "Skyline Express" |
| Home city | Shenzhen | 50 cities |

- **A story is only used if every name it needs exists for that company.** A story about "{supplier} outage disrupts shipments to {name}" is skipped for a company without a supplier. (Suppliers, customers and rivals are not part of the cast: they live in the hidden graph of §7.15, and a company may have several, one, or none.)
- **People change.** A "CEO steps down" story picks a new CEO from the name pool (never one already at the company), installs them, and remembers the former CEO (the last three are kept). Later stories name the new CEO, and some name the old one ("Bella Costa, who left Pinnacle Foods last year, publicly criticises Marcus Delacroix's strategy"). The stock page shows the CEO, the former CEOs, the CFO, the product and the city. It does **not** list suppliers, customers or rivals: those stay internal, and players learn of them only through the news.
- **Examples of real headlines the game produced:** "Beatrice Abara clashes with Annika Draper over Pinnacle Asset Management's spending plans" (a CEO and a CFO) · "Hackers hit ChatterBox Social's systems; Kwame Sterling says an investigation is under way" · "CloudRail lands a flagship AI customer".

### 7.11 Stories about two companies
**In plain English:** some news belongs to two firms at once: a supplier's outage hurts its customer, a rival's recall helps you, a partnership lifts both. About every 4 minutes (`cross_mean_seconds`) the game picks a company and one of its customers or rivals (§7.15) and writes one headline about both. A company with no customer or rival is never picked for such a story.

- There are 5 kinds with 28 phrasings: a **supply-chain** story (the second company is the customer, weight +0.5: "X halts shipments to Y after a plant accident"), a **rivalry** (the rival moves the other way, weight −0.6: "X wins a contract that Y had been chasing"), a **partnership** (customer, +0.8: "X and Y announce a joint venture"), **takeover talk** (rival, −0.25: "Y offers to buy X at a hefty premium") and an **antitrust** probe or clearance (rival, +0.7). The weight (`other_weight`) says how strongly the second company moves compared with the first and in which direction.
- Both companies get a move at the same moment and **both** remember the story, so each company's next earnings report counts it among what drove the numbers.
- The direction is a coin tilted by the first company's safety score and the hidden mood, with the move scaled by `2 × (1 − p)` as in §7.3, so **the expected move of the pair is zero** whichever way you bet. The simulator's `partner_chaser` trades the second company in the headline's direction (§17).
- Example: "Pinnacle Foods wins a contract that QuickStitch Fashion had been chasing": the winner rises and its rival falls.

### 7.12 How a headline is built (`newsgen.py`)
**In plain English:** a headline is assembled from pieces, so the same story reads differently each time and no one sentence repeats.

1. **Pick the story and the company.** A weighted random choice, tilted by mood and the company's safety (§7.3, §7.7).
2. **Fill the slots.** A phrasing such as `{ceo} faces board pressure over missed targets at {name}` has slots for the name, CEO, CFO, product, city, supplier, customer, rival, new CEO, former CEO and a percentage. Several phrasings exist for each story, and one is chosen at random from those that can be filled.
3. **Swap words.** Event templates get a random pass through a synonym table (a "surge" can be a "jump" or a "spike"), and apostrophes are tidied ("Kowalski's" but "Williams'").
4. **Dress it.** A lead-in ("Developing:", "Wire flash:", "Meme Wire reports:" from one of 8 named sources) and a tail matching the tone ("as nerves fray", "the tape is busy") are added at random.
5. **Make it unique.** Nothing is printed twice, ever (§7.4).
6. **Follow-ups quote it.** UPDATE and REVERSAL headlines (§7.4) quote the original verbatim inside quotation marks, so a story reads as a thread.

The earnings headline also carries a short quote from the CEO or CFO whose tone follows the surprise (positive: "{ceo} said results 'beat our own expectations'", flat: "{cfo} said results were 'steady'", negative: "{ceo} called the quarter 'disappointing'"). Combining names, products, cities, synonyms, lead-ins and tails gives far more surface forms than the old whole-sentence variants, but there is no live text generation: the same `random` seed always produces the same headline, which keeps the game testable. An offline step with a language model could widen the pool further (see `ROADMAP.md`, C2); it was left out because it needs an outside service.

### 7.13 Catalysts: rare news that can move a stock a lot
**In plain English:** about every 8 minutes, one company somewhere on the market gets a **catalyst**: a drug trial result, a regulator's decision, a buyout offer, an audit, a contract, a prototype test, a viral moment. A catalyst moves the price by far more than ordinary news, **whatever the stock's beta**: a calm utility can jump 20% or fall 40% just as a meme stock can. The headline starts with "BREAKING:" and the move happens in that second. **A big fall is rare, and it only comes with really bad news.** (Until 2026-10-05 about half of all catalysts were falls of 25% to 77%, which was far too violent: a stock lost 40% on a headline about a postponed approval. See "What changed" below.)

- **Every catalyst is a fair bet.** The expected move is exactly zero: the chances times the sizes of the good outcome and of the bad outcomes cancel, whatever sizes are drawn, so there is nothing to gain by guessing.
- **An ordinary company gets three outcomes** (`newsgen.CATALYST_TIERS`):
  - **good news** (40% to 60% of the time, depending on the kind): a gain of about 10% to 35%, worked out from the other two so that the bet is fair;
  - **a setback** (about a third to a half of the time, 72% for a buyout): the shares slip 3% to 14% on a mild headline ("{name} restates a quarter's results and pays a fine", "Regulators ask {name} for more data");
  - **a disaster** (6% to 8%): a big fall of 20% to 70%, on a headline of its own that is a lot worse ("{name} cancels the launch of its new product after pre-orders collapse: 'there is simply no demand'", "{name} admits it overstated revenue for years; its finance chief is arrested", "Patients die in {name}'s trial: regulators order the study stopped", "{name} loses its biggest customer and announces deep job cuts").
- **Seven kinds**, each with three good-news, three setback and three disaster headlines: *trial* (pharma and healthcare: 40% good, 52% setback, 8% disaster), *approval* (anyone: 55 / 38 / 7), *buyout* (anyone: 22 / 72 / 6), *audit* (anyone: 60 / 34 / 6), *contract* (defense, industrials, space, tech, energy, utilities, antigravity, ocean, teleportation: 42 / 50 / 8), *test* (space, antigravity, teleportation, time, ocean, creatures, weather, alchemy, tech, energy: 40 / 52 / 8) and *hype* (media, retail, crypto, memes, dreams, consumer: 45 / 47 / 8). A kind is picked from the ones that fit the company's sector.
- **A worked example.** An audit: 60% cleared, 34% setback, 6% fraud. The setback is drawn as, say, 8% and the disaster as 55%. The gain is then (0.34 × 8% + 0.06 × 55%) ÷ 0.60 = 10.0%, so 0.60 × 10.0% = 0.34 × 8% + 0.06 × 55%: a clean audit adds 10%, a restatement costs 8%, a fraud costs 55%, and the expected move is zero.
- **A moonshot keeps the old two-outcome bet** (a chance `p` of good news and a gain `up`; the loss is `p × up ÷ (1 − p)`, never more than 95%): a moonshot is a lottery ticket by design, and its upside is trimmed to 70% (§6.11). Its catalysts are ten times as likely (`catalyst_moonshot_weight`), and a moonshot's catalyst can still lose 50% to 90% or gain +60% to +130%.
- **Who gets one.** Any company with a cast of people (§7.10), but a moonshot is ten times as likely.
- **No warning, no rumour step.** The move is applied directly to the price, in the same second as the headline, so nobody can get in first. It is not held back by the per-second or daily limits and it makes the stock jumpier for a while (§6.7). It can push a company across the distress line (§6.6).
- **What changed, measured** (the engine alone, 14 seeds x 2 hours = 28 market hours, the same seeds before and after):

| One-second moves of ordinary companies | Before | After |
|---|---|---|
| a fall of 40% or more | 27 (about one an hour) | 5 (one every five hours) |
| a fall of 25% to 40% | 34 | 3 |
| a rise of 40% or more | 25 | 0 |
| a rise of 25% to 40% | 36 | 2 |
| all falls of 15% or more | 80 | 19 |

  The biggest falls are now: an accounting fraud (-63%), a whistleblower exposing fraud (-63%), a finance chief arrested (-54%), a safety recall (-44%), a scrapped lead drug (-42%). Industry-wide shocks (§7.14, falls of 4% to 13%, about a rise of 19% at the extreme) and moonshots were not changed.
- Tests fire thousands of catalysts and check that the average move is zero for both ordinary stocks and moonshots, that every kind's three chances add to one with a rare disaster, that the gain works out to a fair bet for every size drawn, that a fall of 25% or more happens in 3% to 12% of ordinary catalysts (and 40% or more in under 7%), that nothing loses more than 95%, and that a moonshot still gets the two-outcome bet. The simulator's `catalyst_follow` and `catalyst_fade` trade the aftermath (§17.8).

### 7.14 Industry-wide shocks: a whole sector can go down while the market goes up
**In plain English:** about every 10 minutes one whole industry gets news that hits every company in it together: a ban or a tough new law, a collapse in demand, a cost spike, an industry-wide probe, a technology that makes the business obsolete, a funding squeeze, a tariff (or the good version of each: rules scrapped, demand surging, a trade deal). The headline starts with "INDUSTRY ALERT:" and every company in the sector moves in the same second. Because it has **no market component**, the sector can fall 7% while the rest of the market is up; the sector's own index (for example `XENER`) and any ETF holding it fall with it.

- **Seven kinds**, each with several phrasings per direction: *rules* (new rules or a new law), *demand*, *costs*, *probe*, *disrupt* (a breakthrough technology), *credit* (lenders pull back or funding returns) and *trade* (tariffs or a trade deal). Examples: "Regulators unveil sweeping new rules for the Energy sector: shares slump across the board"; "Demand for Teleportation products surges and the whole sector rallies"; "A breakthrough technology threatens to make the Retail business obsolete: the sector sinks".
- **It is a fair two-outcome bet.** Each kind has a chance `p` (45-55%) that the news is good for the industry. The failure has size `bad` (4-13%, depending on the kind) and probability `1 − p`; the good outcome has probability `p` and size `(1 − p) × bad ÷ p`, so `p × up + (1 − p) × (−bad) = 0`: the expected move is exactly zero. Where failures are the rarer outcome (p below 50%: rules, disruption) they are also the bigger one, so a crash is a real event; where they are the commoner outcome the matching rally is a little smaller. **The sizes are modest on purpose.** Measured over thousands of shocks, one company's move has a median of about **7%**, a 90th percentile of 11.5% and a maximum of about 19% (an earlier version moved whole sectors 20-30%, and up to 49% at the extreme, which was far too much). The setting `sector_shock_size` multiplies every size: `0.5` halves them, `1.5` makes them half as big again.
- **Each company moves by the sector's size times its own exposure** (0.7 to 1.3, drawn without regard to the direction). A weak or strong day for the whole industry therefore still sorts its companies a little, and the expected move of every single company stays zero. Nobody can lose more than 95%.
- **Which sectors.** Any sector with at least two companies: the real ones (technology, energy, pharma, airlines...) and the imaginary ones (teleportation, dreams, dragons...). Moonshots in a sector are hit as well. Safe havens and commodities, which have no companies, are not.
- **No warning.** The moves are applied in the same second as the headline, straight to the prices (not held back by the per-second or daily limits; the shock is meant to be big), and every company in the sector becomes jumpier for a while (§6.7). The usual spillovers follow: company links (a supplier) and sector links (an energy collapse helps airlines a little), which have no expected move either. The headline is kept in every company's own news log, and the wire links its four biggest companies.
- **Industry shocks are checked by:** a test that fires thousands and measures the average move of every company, the sector and the spillover into another sector (all zero); a test that the market can be up while a sector collapses and nothing else moves; the simulator's `industry_follow` and `industry_fade` strategies, which trade a sector's aftermath (§17).
- **Setting:** `sector_shock_mean_seconds` (600; a very large number switches it off).

### 7.15 Suppliers, customers and rivals: the hidden links between companies
**In plain English:** companies are connected. A drug maker supplies a hospital chain, an oil producer supplies an airline, a chip foundry supplies the chip designers, two banks compete. Those connections can move a stock (a rival doing well tends to pull yours down; a customer doing well tends to lift its suppliers) and they decide which companies appear together in a story. **Players never see them**: the stock page doesn't list them and no message carries them. You can only infer them from the news, which is the point.

- **Not every company has them.** About four in ten companies have no supplier, four in ten have no customer and a third have no rival, and a few have several. (Before, every company was given one of each at random, which produced nonsense.)
- **They make sense.** For the companies that ship with the game the links are written by hand from what each company does: *CuraGen supplies Meridian Health Systems and CareRx Pharmacy; Ostrava Oil supplies SkyJet Airways and BlueFlame Gas Utilities; NanoCircuit Foundry supplies Novaxis Chips; Lithic Materials supplies CellStack Batteries, which supplies VoltRider Motors; VoltRider competes with Crestline Automotive and with the hover-car maker LevitateX.* There are about 180 supplier links and 74 pairs of rivals.
- **A new company is linked in, and so are the companies it touches.** When a company lists while the game is running (from a content pack), it is linked by **sector rules**: a drug company can supply hospitals and pharmacies (not dentists), a chip designer can supply carmakers and telecom firms, and companies in the same sector can compete. Each rule has a probability and a pattern the customer's description must match, and the draw for a pair of companies is fixed, so a restart doesn't change it. **The existing companies get the other side of every new link**: a new biopharma company that supplies a hospital chain makes the hospital chain's list of suppliers one longer. Nothing that already existed is rearranged. A newcomer takes at most three links of a kind; no company ever has more than eight of one kind.
- **A bankrupt company is removed**, so nobody is left with a supplier that no longer exists. Moonshots, funds, commodities and derived assets are not part of the graph.
- **What the links do.** (1) **Stories:** a two-company story (§7.11) pairs a company with one of its real customers or rivals, and company stories that name "a supplier" or "a rival" name one of the company's own. (2) **Spillover** (§6.4): a company's move adds +0.10 of its supplier's, +0.15 of its customer's and −0.12 of its rival's. A company with several links gets the average push divided by the square root of how many there are, so a company with many links is not made more volatile than one with few. Catalysts (§7.13) and industry shocks (§7.14) spill over the same way.
- **No edge.** Every spillover is a fixed fraction of a zero-mean move applied in the same second as the move that causes it, so there is nothing to see first, and the expected move stays zero. The simulator's `relation_oracle` cheats by reading the graph and trading it, and should earn nothing (§17); a test checks that the spillover has no average and that a busy company is not noticeably jumpier.
- **Saved** with the game (`relations`), and rebuilt from the companies when an older save has none. `relation_spillover` (1.0) scales the spillover; 0 switches it off.

### 7.16 Scheduled company events between the reports
**In plain English:** between two earnings reports a company now has one or two **scheduled events**: a **guidance update**, an **investor day**, a **call with analysts** or a **product event**. They are on the public calendar ("Upcoming events") with only a label, for example "Investor day · Quill Foods · in 2 hours, 4 minutes", so there is always something to look forward to. What the event *says* is a surprise, and nothing is printed about it before it happens.

- **How many and when.** About 1.5 per company per quarter (`company_events_per_quarter`; 0 switches them off), planned a quarter ahead by the same best-candidate sampling as the earnings (so there are no dry stretches and no pile-ups) and kept at least a game day away from the company's own report. A company listed later gets its events too. Moonshots and funds have none.
- **When one happens** a headline names the company ("Quill Foods raises its full-year outlook", "Analysts leave Quill Foods's call unconvinced"), the price reacts, and the effect on margin and revenue is remembered like any company story, so the next earnings report names it as one of the things that drove the quarter ("Driven by an investor day; ...").
- **It is a fair bet.** Good or bad is a coin tilted by the company's safety and mood (like the other stories), and the size is scaled by `2 × (1 − the chance of the outcome that happened)`, so the likelier outcome moves the price less and the expected move is exactly zero (a test fires each kind 2,500 times and checks the mean). Knowing when an event is due is therefore no edge: the calendar tells you *when*, never *which way*.

---

## 8. Stocks, content packs and new listings

### 8.1 Where stocks come from
All `*.json` files in the project folder (except `state.json`) are **content packs**, merged in alphabetical order. Later files override earlier ones with the same id or ticker. A pack can contain:
- `settings`: any tuning value
- `sectors`: `{id, name, icon}`
- `companies`: `{ticker, name, sector, desc, asset_type, beta, vol, sens, depth, rating, margin, traits, dependencies}`
- `templates`: news events (see §7)
- `profiles`: reference financials (from `market_profiles.json` and `pack_growth.json`), merged into the matching company
- `derived`: definitions of themed ETFs and leveraged products (§9), used by `pack_growth.json`

**Today's market (192 listings at the start of a fresh game):** 152 companies and funds in 30 sectors (technology, energy, pharma, defense, airlines, consumer, finance, utilities, industrials, telecom, materials, agriculture, health services, retail, media, autos, real estate, crypto and fintech, space, meme and safe havens, plus **eight imaginary industries**, below), five commodities (crude oil, natural gas, wheat, copper, gold), 31 derived assets (§9) and 4 moonshots (§6.10) that come and go.

**The imaginary industries (`pack_fiction.json`)** are companies in invented businesses that do invented things, each with a one-line description on its stock page: **Teleportation** (PhaseJump Logistics ships cargo through teleport gates), **Weather Engineering** (CloudSeed sells rain on demand; StormShield steers hurricanes away from coastlines), **Time Technology** (Chronos Labs sells chambers that give workers an extra hour a day), **Dreams & Memory** (DreamWeave records dreams as entertainment; MemoryBank lends out memories), **Dragons & Creatures** (Ember Dragon Ranches breeds dragons for heavy lifting; Griffin Air Freight flies cargo on griffins), **Deep Ocean Cities** (Abyssal Habitats builds apartment towers on the sea floor; KelpWorks farms giant kelp), **Antigravity** (LevitateX makes hover-cars; HoverRail builds floating trains) and **Alchemy & Enchanted Goods** (GoldMaker Labs turns lead into gold; RuneWorks sells locks no thief can pick). Each has six companies, its own news templates, products and suppliers, a tradable sector index and a place in the Frontier Industries ETF `FRNT`. `pack_growth.json` is the template for adding more: copy its shape, give each company a sector, a reference profile and a `depth` (its size), and drop the file next to the others. It is picked up without a restart.

A company whose `sector` doesn't exist is skipped.

### 8.2 Listing (IPO)
Every tick, the engine compares content files' modification times and reloads them if any changed:
- **New ticker:** listed immediately, funded from the house reserve (any shortfall is minted as house capital). A "NEW LISTING" headline goes out, its earnings slot is picked in a quiet part of the calendar (§7.7), its review is scheduled, and it is linked into the supplier, customer and rival graph (§7.15): existing companies it supplies or competes with get the matching link.
- **Existing ticker:** descriptive fields (name, beta, vol, description) update in place. **Financials do not reset**, because they now evolve with earnings.
- **Removed ticker:** stays trading until the next restart (see §15).
- **Delisted tickers** (bankrupt) never relist.
- **The NEW badge.** Every listing carries the time it joined (`listed_at`). For 30 minutes after that the market table and the stock page show a green **NEW** badge by the name. A company counts as new if it is a moonshot that listed later (§6.10), a ticker added to a content file while the game was running, or a ticker that wasn't in the save when the server last started. Companies that have been there since the game began never carry it, and neither do derived assets.

### 8.3 Financials
`market_profiles.json` gives each company its starting reference price, market cap, revenue, margin, cash, debt and dividend yield. The page derives:
```
shares outstanding = reference market cap / reference price   (billions)
market cap         = shares outstanding × live price
net income         = revenue × margin
EPS                = net income / shares outstanding
P/E                = market cap / net income        (equities with positive earnings)
dividend yield     = 4 × declared quarterly dividend per share / live price (see §7.7)
```
Revenue, margin, cash and debt change at earnings (§7.7), feed the bank ratings (§7.8), and scale with the price moves of the stories behind them. Share counts and the reference price stay fixed. Market cap figures are in billions of MB.

`asset_type` is `equity`, `fund`, `commodity` or `index`. Prices are shown as plain "MB" (no per-barrel or per-ounce unit).

---

## 9. Indices, ETFs and leveraged products

**In plain English:** besides company shares you can trade whole baskets: the entire market, a whole sector, a themed fund, or a bet that is two times (or the opposite of) the market. These are **derived assets**. They have no company behind them and nothing can move them directly. Every second their price is **computed from the returns of the stocks inside them**.

All 32 derived assets start at 100 MB, have an `asset_type` of `index`, have no size of their own (`depth` 0), and show on the market under the **Indices & ETFs** chip.

| Kind | Tickers | How the price moves each second |
|---|---|---|
| **Market index** | `MSI` (the **MSI 50**) | `I ← I × (1 + Σ w_i × r_i / Σ w_i)` over the 50 largest companies, where `w_i` is a company's market value (shares × price) at the start of the second and `r_i` its return. See below |
| **Sector indices** (21) | `XTECH`, `XENER`, `XPHAR`, `XCONS`, `XFINA`, `XINDU`, `XHEAL`, `XRETA`, `XMEDI`, `XAUTO`, `XREAL`, `XCRYP`, `XSPAC`, and for the imaginary industries `XPORT`, `XWEAT`, `XCHRO`, `XDREA`, `XCREA`, `XOCEA`, `XANTI`, `XALCH` | the same, over the stocks of one sector. Created for every sector with at least 3 companies (`sector_index_min_members`), except safe havens, memes and commodities |
| **Themed ETFs** (6) | `AIFX` (AI & Cloud), `GRNX` (Clean Energy), `DIVX` (Dividend Income), `FINX` (Fintech & Crypto), `SPCX` (Space), `FRNT` (Frontier Industries: companies from the imaginary sectors) | **equal-weighted**: the plain average of the members' returns. Members are listed in `pack_growth.json` and on the stock page ("Tracks: Equal weights in NVXA, CLDR, ...") |
| **Leveraged and inverse** (4) | `2LMSI` (2x Long MSI 50), `2SMSI` (2x Short MSI 50), `3LMSI` (3x Long MSI 50), `3SMSI` (3x Short MSI 50) | `lev × MSI's return` every second (`2SMSI` is −2×, `3SMSI` −3×) |

**The MSI 50 in detail.** The market index used to follow every listing (161 of them) with weights taken from `depth`, which was an arbitrary size and not a real market value, so it behaved like a plain average of everything, funds, commodities and moonshots included. It now works like a real "top 50" index:
- **Who is in:** the 50 companies (`index_size`) with the largest market value, `shares × price`. **Moonshots, funds, commodities and the other indices are never in it**, so it is a gauge of the main market. If fewer than 50 companies exist, it has them all.
- **Weights:** each member's market value at the start of the second, so a company that has doubled counts twice as much. A company outside the 50 cannot move the index at all (a test moves every outsider by +25% and checks the index does not change).
- **Re-ranking:** at the start of every game day (30 minutes) the list is made again, so a company that has grown can join and one that has shrunk can drop out; the index keeps its level and simply carries on with the new members. If a member is **delisted** the list is made again at once, so there are still 50. A new listing waits for the next game day. The current members are saved with the game (a save without them, from the old version, picks them on load) and the stock page says "Tracks: The 50 largest companies, weighted by market value".
- **Still a fair bet:** the members and their weights are fixed from prices that are already known before the second starts, and every member's expected move is zero, so any such average has an expected move of zero (§15). Trading `MSI` never moves it. The tickers did not change: the index is still `MSI` and the leveraged products are still `2LMSI`, `2SMSI`, `3LMSI` and `3SMSI`; only their names now say "MSI 50".
- The sector indices (weighted by `depth`) and the equal-weight ETFs work as before.

**Example.** In one second the MSI 50 rises 0.10%. `2LMSI` rises 0.20%, `3LMSI` 0.30%, `2SMSI` falls 0.20% and `3SMSI` 0.30%. If `AIFX`'s ten members rise 0.30%, 0.10%, −0.05%, ... and average +0.08%, `AIFX` rises 0.08%.

**They trade like stocks.** Buy, sell, short and cover at the market price against the house, with the usual 0.1% fee and borrow fees. Their volatility (which sets the margin) is 80% of the members' average for a basket (diversification) and `|leverage| × the underlying's` for a leveraged product: `3LMSI` is about 3× as volatile as the market. The crowding figure that scales their borrow fee uses the fixed `short_cap_index` (16,000 MB).

**Total return, so no hidden leak.** When a member goes ex-dividend its price drops by the dividend. The index adds that drop back, so holding `DIVX` is like holding its members and reinvesting what they pay. (Before this was added, an ETF holder would have lost the yield every ex-date: a small, house-funded penalty. A test checks the fix.)

**Leveraged products and "decay".** The multiple is reset **every second** (the "daily reset" of real leveraged ETFs, at one-second speed). That keeps the product a fair gamble: its *expected* price never moves, like the index's. But in a choppy market it **loses value along the way**, because gains and losses don't cancel: if MSI goes +1% then −1% (−0.01% overall), `2LMSI` goes +2% then −2% (−0.04% overall) and `3LMSI` +3% then −3% (−0.09%). Over a long, jittery stretch a typical `2LMSI` or `3SMSI` drifts down while a lucky few soar, which is why the description says so. A test simulates 400 paths and checks that the average price stays at its start while the median falls.

**Safety.** News never names a derived asset, banks never rate it, it pays no dividends and has no earnings, and distress and offerings skip it. The simulator's `etf_hodl`, `bull2_hodl`, `bear2_hodl`, `bull3_hodl` and `bear3_hodl` buy and hold one each for hours; none shows an edge (§17).

**The old products.** `BEAR1` (Market Bear 1x) and `BULL1` were withdrawn, and `BULL2` and `BEAR2` were renamed `2LMSI` and `2SMSI`. A save from before the change is migrated when it loads: the tickers are renamed everywhere (positions, history, charts, orders), and anyone holding the withdrawn `BEAR1` is paid out at its last price (a short is closed at it), the way a delisting works, so nobody loses a position. An old link to `/stock/BULL2` redirects to `/stock/2LMSI`.

**The page.** The stock page shows "Tracks: ..." for derived assets and labels them *Index*, *ETF* or *Leveraged product*. The sector chips along the market table still show the older display-only sector index (`100 × Σ base_i × (p_i ÷ P0_i) / Σ base_i`), which is not the same number as the tradable `X...` index.

---

## 10. Players, days, leaderboard

### Players
- An account is a **name and a password** (§10.6). The name is 2-16 letters, numbers, `_-. `, unique ignoring case, and not a reserved word (`admin`, `moderator`, `house`, `memestreet`...). Signing in gives the browser a session token; the account's own internal token never leaves the server (for accounts with a password).
- New players are credited `signup_bonus`: **10,000 MB** of test money. Set it to 0 before real money.
- `deposited` tracks net money in (signup + deposits − withdrawals). **All-time P&L = equity − deposited.**

### There are no bots
The game used to have eight house-funded bots (random, momentum, contrarian and news traders) that traded a little each minute so the market and the leaderboards were never empty. They were removed on 2026-10-05 (on request): every trade is now a real player's, and the game starts with no players at all. The old `bots`, `bot_cash` and `bot_action_probability` settings are ignored.

**A save from an older version that still has bots** loads normally: on the first start each bot's positions are closed at the market price, whatever it holds goes back to the house reserve (it was house money in the first place), and the bots are removed, all before the game runs. No token is created or lost (a test checks the books balance to 1e-6, that the human players' cash and positions are untouched, and that loading the cleaned save again changes nothing), the cleaned save is written at once, and the log says "removed N bots; X MB went back to the house reserve". The reserve grows by the bots' cash; the house's debt to them for their open positions simply ends. Their trades stay in the ledger's history, which only records what happened.

### Days (what used to be seasons)
- A **day** is one real day, midnight to midnight UTC (`season_seconds` = 86,400), so it lines up with the daily quests and the daily contest. At midnight the day ends, the top 5 are recorded and a news item announces the winner ("DAY 19 OVER. Winner: ..."), and Day 20 begins. The header shows "Day 19 ends in 4 hrs, 12 minutes, 9 seconds".
- **Balances are never reset** by a day ending. Each player's `season_base` is set to their current equity.
- **Day return** = `equity / season_base − 1`. Deposits during a day are added to `season_base`.
- The leaderboard sorts by day return. (It used to show a Sharpe-style "Score" column too; that column and the equity snapshots behind it were removed.)
- **Starting over.** The admin page's **Reset** button (§1, §12) puts everything back to Day 1: every player gets the starting balance again, positions are closed at the market price without fees, orders are cancelled, and the trade history, medals, achievements, counters and day history are cleared. What stays: the market (prices, charts, listings, news), accounts (names, passwords, who follows whom, privacy) and the chat moderation record. The tokens still balance (closing a position settles with the house; setting a balance mints or burns the difference). The ledger is emptied and begins again with each player's `join` and starting `credit`, after the old one has been copied to `backups/`.

### 10.1 Achievements
**In plain English:** small goals that unlock a badge. They are checked after every trade and every five seconds, and unlocking one pops a message in the corner of the page. There are 21 (`ACHIEVEMENTS` in `social.py`); your profile page shows all of them, locked ones greyed out, and other players can see the ones you've unlocked.

| Achievement | How you get it |
|---|---|
| First steps · Getting active · Market regular · Floor trader | make your 1st, 10th, 100th and 500th trade (a lifetime count that survives day rollovers) |
| Bear in the woods · Sold high, bought low | open your first short · close a short at a profit |
| Trial by fire | get margin-called (and keep playing) |
| Dividend collector | receive a dividend |
| Not all eggs · Wide net · Belt and braces | hold 5 positions at once · stocks in 4 different sectors · a safe haven or inverse product alongside 2+ stocks |
| Whole market · Safe harbour | trade an index, ETF or leveraged product · trade a safe haven (bonds, gold) |
| In the green · Big win | 100 MB of realised profit in total · 100 MB profit on a single trade |
| Diamond hands | close at a profit after holding for an hour |
| Caught the reversal | hold a stock through a **REVERSAL** headline about it and close at a profit within ten minutes |
| Up ten · Up twenty-five | reach +10% / +25% day return |
| On the podium | finish in the top three of a daily contest |
| Daily grind | complete all of a day's quests |

### 10.2 Daily quests
Every day (UTC) the game draws **three quests** from eight kinds using a random generator seeded by the date, so everyone gets the same three and they change at midnight UTC. The kinds: make N trades (4-12), trade stocks in N sectors (2-4), close N positions at a profit (1-3), open a short, hold N positions at once (3-6), trade an index/ETF/leveraged product, receive a dividend, trade N hundred MB in total (200-800). Progress shows as a bar on your profile. Completing a quest pops a message, completing all three starts or extends your **streak** (consecutive days with all three done) and unlocks *Daily grind*. **Quests pay nothing** but pride: no MB, no edge.

### 10.3 Leaderboards (the two boards)
The **Leaders** page has two boards (a short day-return list, with no other columns, is also in the sidebar of the market page), computed once per second from the same data:

| Board | Ranked by | In plain English |
|---|---|---|
| **Day return** | `equity ÷ day base − 1` | who is up the most today; deposits don't count (§10 above). Lists only players who **have made a trade today** |
| **All-time P&L** | `equity − money paid in`, in MB, with the return on money paid in beside it | who has made the most since joining. Lists only players who **have ever made a trade** |

**Only traders are on a board.** A player who has joined, deposited or just looked around is on neither board, and has no rank (the header says "unranked", the profile shows "-", and under the Leaders table: "You are not on this board yet: it lists only people who have made a trade today"). The test is the period the board covers: the day board uses the day's trade count (which is zeroed when a day ends and by a game reset, so the day board starts every morning empty and fills as people trade), the all-time board uses "has ever traded" (any trade counted, an open position or a realised result). What counts as a trade: a buy, sell, short or cover, including a fill of an order you placed. What does not: a margin call (the game closing your shorts), a deposit, a **paper trade in the daily contest** (that is a separate account), and joining. Bots are treated like everyone else, so a bot appears once it has traded. The sidebar list on the market page is the top ten of the day board and says "Nobody has made a trade today" when it is empty; the Leaders page shows how many people are on each board (`counts` in `GET /api/boards`). The day's winner (the news line at the end of a day) is likewise taken from the day board, so it is never someone who did nothing.

**Drawdown** is the biggest fall from your best level today, measured on `equity ÷ day base` (so paying money in or taking it out is not a gain or a loss: when you deposit, the peak is scaled by the same factor). It resets each day. It is no longer a board of its own (there used to be a "risk-adjusted" board, `day return ÷ max(drawdown, 2%)`, and a "Score" column; both were removed), but it is still tracked: your worst drawdown today is shown on your profile and under the Leaders table.

### 10.4 The daily contest (fixed-balance paper trading)
**In plain English:** once a day there is a race that is fair by construction. Everyone who enters gets the **same paper balance** (10,000 MB, `contest_balance`) and trades it at the live prices, under the real rules, in a **separate paper account**. Whoever has the best return at midnight UTC wins a medal. Nobody's real money is involved either way: the paper account can't touch your real balance, the house reserve or any price, and the prizes are cosmetic (medals).

*(The first version ranked the return of your real account since you joined, in equity leagues. That favoured whoever timed their entry well and could let a rich account crush a new one. A fixed balance for everyone removes both.)*

- **When.** The **Daily Marathon** runs from midnight to midnight UTC, like a day (§10), and entries are open for the first 12 hours (`contest_join_seconds`). There is one at a time. The Hourly Sprint was removed.
- **Joining** is one click on the profile page and can't be undone: you get `contest_balance` of paper money. The profile page then shows your paper equity, free cash, rank and open positions, a ticker box with size chips and **Buy** and **Sell / short** buttons, and a Close button on each position. Bots can't enter.
- **Your paper account follows the real rules exactly** because it runs the engine's own trading code (`contest.py`, below): the same 0.1% fee, the same margin and maintenance levels for shorts, the borrow fee, ex-dividend payments, the bankruptcy payout, margin calls (your short is closed and a message tells you), the 1-second cooldown. Differences: no orders, and each entrant borrows on their own (one entrant's shorts never use up another's shares to borrow).
- **How it's built without touching the real game.** `contest.Sandbox` looks like the engine to the engine's trading code, with its own throwaway house, fee pool and short-interest, and passes everything else (prices, settings, the clock) through. Social hooks (achievements, quests) are switched off for it, nothing is written to the ledger, and the real players, house reserve and token books are never in its way. A test runs two identical worlds, one with six entrants trading furiously in a contest, and checks that every price, the house, the fees and every real balance are identical.
- **Standing** is `(paper equity − 10,000) ÷ 10,000`. **When it ends**, the top three get a medal (🥇🥈🥉) on their profile, a message and the *On the podium* achievement; everyone else is told their place ("you finished #5 of 23"). The last 20 results are kept and shown on the profile page. Other players see only names and returns, never positions.
- Contests are saved with the game, paper positions included, so a restart doesn't lose them. Contests from before paper accounts existed are dropped when an old save loads (their entrants had no paper balance).

### 10.5 Profiles, privacy and following
- **Private by default.** Another player opening your profile (`/player/YourName`) sees only your name, medals, achievements and how many people follow you.
- **Public if you opt in** (a checkbox on your profile page). Then they also see your day return, your return since joining, your ranks and trade count, and **what you held** with a delay: the game takes a snapshot of every player's positions every 30 seconds and shows the newest snapshot that is **at least 5 minutes old** (`public_delay_seconds`). It shows each position's **share of your account** ("Long CLDR 18.4%", "SHORT NVXA 6.1%"), never sizes in MB or shares. So nobody can copy a trade as it happens, and nobody learns how rich you are.
- **You always see your own**, whatever the setting.
- **The leaderboards are public.** If you rank high on a board you appear there with your name and numbers whatever your privacy setting says, like in any ranked game. The setting controls your profile page and your holdings, not the rankings. (If boards should respect it too, that is a one-line change in `social.py`'s `boards_for`; see `ROADMAP.md`, open questions.)
- **Following.** Follow up to 20 players (never yourself) from their profile or by name on the Social page. The Following tab lists each with their results (or "private").

### 10.6 Accounts: passwords, email, sessions and abuse limits
**In plain English:** an account is a name plus a password, so clearing the browser no longer loses it, you can log in from another device, and nobody can take your name. The sign-in box has **Log in** and **Create account** tabs (a first visit opens on Create account). An account can also have a **verified email address**: it is how you get back in if you forget the password, and (when switched on) the proof that one person is behind one account.

- **The password is never stored.** Only a salted **scrypt** hash is (about 60 ms and 16 MB to check, which makes guessing slow), so nobody, including the admin, can read it. Passwords are 8-128 characters; a few of the most obvious ones ("password", "12345678", the name itself) are refused.
- **Sessions.** Logging in gives the browser a random 256-bit session token, which is what the page sends from then on. The server keeps only its hash. A session lasts 30 days from last use; an account keeps at most 10 (logging in on an 11th device ends the oldest). **Log out** ends this one, **Log out other devices** ends the rest, and changing the password ends all the others.
- **Accounts from before passwords** (made with just a name, tied to one browser) keep working with their old token so nobody is locked out of a game in progress. The profile page nags them to set a password; once one is set the old token stops working and the browser gets a session. Only accounts *without* a password can use the old token.
- **Limits.** Failed logins: 5 per name in 15 minutes and 20 per address in 10 minutes (`login_fails_per_name`, `login_fails_per_ip`), then `429` with a `Retry-After`; the same answer comes back for a wrong name and a wrong password, and a name that doesn't exist still costs a hash, so neither the answer nor the timing says whether a name exists. Sign-ups: 5 new accounts per address per hour (`signups_per_ip_hour`). At most four password hashes run at once.
- **Where an address comes from.** Normally it is read from the connection. A forwarding header (`CF-Connecting-IP` or `X-Forwarded-For`, which anyone can send) is believed only when the request came from this very computer (a tunnel or a proxy running here, §1) or when `trust_proxy` is on (a proxy on another machine, §14). Behind a gateway (§12) the gateway works the address out the same way and passes it on, and the game server believes it.
- **Spotting one person with many accounts.** Each account remembers salted **tags** of the last five addresses it signed up or logged in from (never the address). The admin page lists accounts that share a tag ("3 accounts share an address: ..."). It is a flag to look at, not proof (a household, a school).
- **A name-only game.** `require_password=false` brings back the old name-only `POST /api/join` (the tests and a closed friends-only game use it). With the default `true` it answers 400 "Create an account with a password".
- Accounts are saved immediately when created or changed (a password nobody can recreate must survive a crash).

**Email (`accounts.py`, `mailer.py`).** The `email_mode` setting is `off` (no email asked for), `optional` (asked for at sign-up, never needed) or `required` (a verified address is needed before an account can trade, place orders, enter the daily contest or chat; bots are exempt). With no setting it is `off` until the server finds that mail can really be sent (an `SMTP_HOST` is set), and then `optional`: asking for an address that no mail will ever reach would only confuse people. In `required` mode an existing account without an address is blocked in the same way until it adds and verifies one on the Profile page, and the error message says so.
- **Verifying.** The player types an address (at sign-up, or later under Account on the Profile page). The game mails a **six-digit code**; typing it back marks the address *verified*. A code works for 15 minutes (`email_code_minutes`), allows 5 wrong guesses (`email_max_tries`) and then dies, can be asked for again only after 60 seconds (`email_resend_seconds`), and at most 5 times an hour per address (`email_sends_per_hour`). Codes are kept only as salted hashes (also across a restart: a code mailed just before a restart still works).
- **One account per address.** A verified address belongs to one account. Spellings of one mailbox count as the same: `A.l.i.c.e+games@gmail.com`, `alice@gmail.com` and `alice@googlemail.com` are one Gmail address (Gmail ignores dots and the part after a plus sign; other providers ignore the plus part). Someone who typed an address but cannot read that inbox never owns it: whoever proves it first wins, and the other claim is dropped. Throwaway-inbox services (mailinator, guerrillamail, 10minutemail and about forty more) are refused, and the admin can add more domains with `blocked_email_domains`. (This stops casual multi-accounting. It does not stop someone who makes real new addresses; that is what the shared-address flags and, later, phone or wallet checks are for.)
- **Forgotten password.** On the login tab, **Forgot your password?** asks for the trader name and mails an **eight-character reset code** (letters and digits, no 0/O or 1/I/L) to that account's *verified* address, valid 15 minutes, 5 wrong guesses. The code plus a new password sets the password, ends every old session and logs the player in. The answer to "send me a code" is the same whether or not the name exists or has a verified address, so it cannot be used to find out who has an account. An account with no verified address still needs the admin's **Reset password** (a temporary password shown once).
- **Mail limits.** At most `mail_per_hour` (200) messages an hour in total, 12 address changes or resends an hour per caller address, 10 forgot-password requests an hour per address, and 10 wrong reset attempts per name in 15 minutes. These keep abuse from running up an email bill or getting the sender blacklisted.
- **Sending.** Mail goes through any SMTP service (Resend, Brevo, Postmark, Amazon SES, Mailgun, a Gmail app password...), set by environment variables: `SMTP_HOST`, `SMTP_PORT` (587 STARTTLS, or 465 TLS), `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` (an address the service lets you send from), `SMTP_SECURITY` (`starttls`, `ssl`, `none`). It is sent on a background thread (a slow mail server never holds up the game) and retried twice. With **no `SMTP_HOST`** the game is in **console mode**: nothing leaves the machine, the message (code included) is written to the server log and shown on the admin page under *Email and mail*, so you can try everything on your own computer and hand a code to a tester yourself. `GET /api/auth_mode` tells the sign-in box whether mail is really set up. For mail to reach inboxes (and not spam) the sender domain needs the SPF and DKIM records your mail service tells you to add.
- **What is private.** An address is never in a public profile, a leaderboard, a chat message or a websocket broadcast; its owner sees it masked (`a***@example.com`). The admin sees addresses only in the mail list. Verified addresses are kept through a game reset (a reset clears progress, not accounts).
- **Admin support actions.** *Mark email verified* (you checked another way) and *Remove email* on the admin page, both written to the moderator log.

### 10.7 Chat and moderation
One global chat on the Social page (private club chats went away with the clubs). It is **moderated**, because anything people can type can be abused:

| Safeguard | What it does |
|---|---|
| Cleaning | Every message loses control and invisible characters (including the right-to-left override), has runs of spaces collapsed and links replaced with `[link]`. Maximum 200 characters |
| **A word filter that sees through disguises** | About 30 rude words in English, Spanish, French, German, Portuguese and Italian (plus any the content packs add with `chat_bad_words`) are masked with asterisks. It tolerates look-alike characters (`sh!t`, `$h1t`, `a$$hole`), repeated letters (`fuuuck`), up to three separators between letters (`f u c k`, `f.u.c.k`), accents and full-width letters (`ｆｕｃｋ`). A match must start a word, so `class hit`, `Scunthorpe`, `bitcoin` and `assume` are left alone, and a few words that begin ordinary ones (`retard`, `puta`) only count as whole words so `flame retardant` and `putative` are fine. The message keeps its own accents and length |
| **A trade-first gate** | A new account must have made `chat_min_trades` (3) trades before it can chat or report, so a throwaway account can't spam or mass-report. The Social page says how many are left |
| Rate limits | One message per 1.5 seconds, 15 per minute, and the same message can't be repeated within 15 seconds |
| **Reports that act by themselves** | The 🚩 beside a message reports it (once per message per player). When `chat_report_threshold` (3) *different* players have reported one message it is **removed from everyone's screen and its author is muted automatically**: 10 minutes the first time, an hour the second, a day from the third on (a "strike"). The author is told why. A moderator can still review every report |
| **Appeals** | A muted player can send a short appeal from the Social page (one open appeal at a time). The admin page lists them with **Lift mute** (the mute ends, the strike is forgiven, the player is told) and **Keep mute** |
| **A moderator log** | Every moderation action is recorded with who did it, to whom, when and why: automatic mutes (with the report count), admin deletes, mutes and unmutes, appeals and how they were decided. The admin page shows the latest; it is saved with the game |
| Admin tools | The admin page lists the latest messages and the reports (grouped by message, with who reported it), and can **delete** a message (it disappears from everyone's screen at once) or **mute** a player for 10 minutes, an hour, or lift a mute |
| Switch | `chat_enabled=false` turns chat off for everyone |
| Escaping | Messages are stored as typed and shown as plain text, so `<script>` is harmless |

**Sharing a trade.** The message box has a "Share one of your recent trades" menu. The server finds that trade in *your own* log by its time, so you can't invent one, and the message shows "BUY 12.30 CLDR @ 45.2 MB" with a link to the stock. Only your last 100 trades can be shared. Bots can't chat.

### 10.8 Why none of this gives anyone an edge
- **No social feature ever touches cash or a price.** Rewards are medals, badges, streaks and bragging rights. A test runs two identical markets, one with heavy social activity (chat, following, contests, profile views), and checks that **every price and the token books are identical** after 120 ticks.
- **Public holdings are delayed and shown as percentages.** Even if you copy someone, you copy a 5-minute-old guess, and since no trade moves a price, copying doesn't move anything either.
- **The daily contest is paper money, the same balance for everyone, and pays only a medal** (§10.4).
- The only state that could be abused is chat (spam, abuse) and the accounts themselves, which is why they have the rules above and in §10.6.

---

## 11. The web pages and charts

### Pages
The logo in the header (and the tab icon) is `brand/memestreet_logo_peaks.png`, served at `/brand/memestreet_logo_peaks.png` (only the two named brand images are served), shown with rounded corners.

Every page has the same header (index, cash, equity, P&L, day return, rank, the day's countdown, the market status chip) and the same navigation. Nothing on any page shows the market's mood or regime.

- **Market (`/`):** a table of every listing, under a sticky header (the index, cash, equity, P&L, day return, rank, and the session chip; §6.8). Above the table:
  - a **search box** (matches ticker, company name and sector; `nvx` finds NVXA, `index` finds the indices and ETFs),
  - the buy/sell **size chips** and the **amount box**,
  - the **industry chips**: ★ Watchlist, All, **Indices & ETFs** and one chip per industry (30 of them now). Only the **first row** is shown; the arrow at the right (**▾ All industries (30)**) unfolds all of them and turns into **▴ Show less**. An industry you pick from the hidden rows moves to the front so you can always see what is selected. The fold state is remembered.

  Each row shows the sector icon, the **ticker with the company name beside it** (there is no description on this page: it is on the stock page), the price, the 30-minute change as a coloured pill, a trend sparkline, how much you hold, and Buy and Sell buttons. **Sorting:** click a column header (Ticker, Company, Price, 30m, Held); click again to reverse; an arrow shows the sort. **The table only re-sorts every 3 seconds and never while the pointer is over it**, so rows don't jump away under your finger. **Watchlist:** click the ☆ at the start of a row; it turns gold ★. Your sort, search, industry, fold state and watchlist are **remembered in your browser** (`localStorage`). Each row can carry a green **NEW** **badge** (listed in the last 30 minutes, §8). The Held column shows `(short)` for shorts. The buttons are never greyed out: you can trade in every session. Beside the table: the news wire (times and ticker links), **upcoming events** (one row each: a coloured kind label for Earnings, Investor day, Guidance update, Analyst call or Product event, the ticker, the company name on one line, and a short countdown such as "20 min 51 s" that turns blue in the last five minutes), the top-10 leaderboard.
- **Stock (`/stock/{ticker}`):** price and change, the star, badges, the **description** (derived assets add "Tracks: ..."), the **company's cast** (CEO, CFO, product, city and former CEOs; §7.10), buy/sell (labelled **Short** / **Cover** when that is what the button will do), the **amount box**, a costs line ("Shorting takes the amount out of your cash as collateral and gives it back when you cover · borrow fee 0.27% per hour. There is no limit on how much of this you can buy or short."), your position box (shares, average entry price, value, gain or loss, dividends, borrow fees paid), an **order panel** (limit buy and sell, stop-loss, take-profit and a one-click bracket, with the list of your open orders for this stock and a cancel button; §4), the chart, financial facts (market cap, P/E and dividend yield are **recomputed from the live price every second**), *Earnings history* and *Company news & analyst notes* (§7.7).
- **Holdings (`/holdings`):** cash, net positions value, total cost, open P/L and equity, then **size chips and an amount box** (the same as on the market page) and one row per holding: ticker and company, side (Long or SHORT), shares, average entry price, price, value, dividends received or paid, P/L in MB and in %, and **Buy and Sell buttons at the end of the row**, so you can add to, trim or close a position right there (for a short the buttons read **Cover** and **Short**). Below the table, **Open orders** lists every order you have left, with a cancel button. The chips pick a share of cash (Buy) or of the position (Sell); an amount typed in the box overrides them.
- **Portfolio (`/portfolio`):** the "how am I doing" page. Ten figures (equity, cash, money paid in, total profit and return, realised profit, unrealised profit, fees paid, dividends, borrow fees, trades today); an **equity curve** (one point per minute for the last day, with a dotted line at the money you paid in, green above it and red below); an **allocation bar** (cash and each position as a share of your account); the open positions with unrealised and realised profit; your **5 best and 5 worst closed trades**; and realised profit by stock. *Realised profit* is booked when you sell or cover and is net of the fees you paid to open the position; *unrealised* is what you'd make or lose if you closed now (before the exit fee). Total profit = realised + unrealised + dividends − borrow fees − the exit fee on what's still open.
- **History (`/history`):** every trade and payment, newest first, 50 at a time with **Load older**. Filter chips: All, Trades, Buys (buys and covers), Sells (sells and shorts), Dividends, Deposits (the fee column stays in the table; there is no separate fees tab). **A stock that was delisted can still be opened from here:** click its ticker and you get its stock page with the chart, the financials, the cast and the news log, marked *Delisted* with no buy or sell buttons (the game keeps the last 60 delisted companies' pages). Columns: time, type, ticker, shares, price, amount, fee, realised P/L (on closing trades only) and cash change. **Download CSV** gives the whole history, oldest first, for a spreadsheet (§12). The page refreshes itself every 15 seconds.
- **Leaders (`/leaders`):** the two boards of §10.3 as tabs (only people who have traded appear on them), with your row highlighted and your rank (or "not on this board yet") and drawdown underneath. Names link to profiles (bots, marked 🤖, don't).
- **Social (`/social`):** *Chat* (the share-a-trade menu; a note when you are muted, with the appeal box, or how many trades are left before you can chat; a red dot on the nav when something arrives elsewhere) and *Following*. There are no clubs.
- **Profile (`/profile`):** your ranks and worst drawdown, today's three quests with progress bars, the **daily contest** (join button, your paper equity, rank and return, the paper trading panel, the leaders, the last results; §10.4), all achievements, your medals, the privacy checkbox and your **account** (is there a password, set or change it, log out other devices, log out; §10.6).
- **Player (`/player/{name}`):** another trader's public profile (§10.5) with a Follow button.

Messages from the game (achievements, quests, contest results, margin calls) stack in the top-right corner for five seconds and **never cover a trade result**, which shows at the bottom of the page.

In **pre-market** a thin amber banner and in **after-hours** a thin purple one say that trading is thin and prices move less (§6.8); the header chip names the session and counts down to the next one. Nothing is ever disabled.

The table and chart are updated **in place** (not rebuilt) every second, so a click is never lost to a redraw.

### Candles and timeframes
The engine keeps real-time candles for 11 timeframes, each updated on every tick: **30s, 1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1M, 1Y**, where 1d is 24 real hours, 1M is 30 real days and 1Y is 365 real days. Each timeframe keeps its last 500 candles and is saved. Candles of a long timeframe fill in over real time, so a fresh server shows few 1d, 1M or 1Y candles.

### Chart behaviour
- The **newest candle sits in the middle** and everything shifts left as candles arrive. The first candles are **thick** and get thinner as more are created, down to a minimum width.
- **Zoom** with the buttons or the scroll wheel (around the pointer). You can **zoom out as far as you like**, well past the first candle. **Drag** to pan. "Reset view" restores the default.
- The vertical scale fits only the candles currently in view, plus the live price and your average price.
- A **blue dashed line** marks the live price. If you hold the stock, an **amber dotted line** marks your average entry price and updates with each buy.
- The current candle updates with the live price; when a new time bucket starts, the page opens a new candle.
- The "30m" change is the current price vs the price 1,800 s ago (from the minute candles). The trend sparkline is the last 60 one-second prices.

---

## 12. Server and protocol

### HTTP
Player endpoints need the player's **session token** in an `X-Token` header (the page sends it; a missing or wrong token gets **401**). Admin endpoints need `X-Admin-Key` (**403** without it). Lookups are rate limited per player: a call that comes too soon gets **429** `{"error":"slow down"}` (the page waits 0.45 s and tries once more).

| Endpoint | Who | Purpose |
|---|---|---|
| `GET /`, `/stock/{ticker}`, `/holdings`, `/portfolio`, `/history`, `/leaders`, `/social`, `/profile`, `/player/{name}` | anyone | the web page (`Cache-Control: no-store`) |
| `GET /api/auth_mode` | anyone | `{passwords, email, mail_ready}`: whether accounts need passwords, the `email_mode` (`off`/`optional`/`required`) and whether mail can really be sent (the sign-in box asks this) |
| `POST /api/register` `{name, password, email?}` | anyone | create an account → `{token, name}` (a session token), plus `email_sent`/`email_msg` when an address was given and its code was mailed. 400 with the reason for a weak password, a taken or reserved name, a bad, disposable or already used address (or a missing one in `required` mode); 429 after too many sign-ups from one address |
| `POST /api/login` `{name, password}` | anyone | log in → `{token, name}`. 401 "Wrong name or password" (the same for an unknown name); 429 with `Retry-After` after too many failures |
| `POST /api/join` `{name}` | anyone | the old name-only sign-up, only while `require_password` is off (else 400) |
| `POST /api/logout` | player | end this session |
| `POST /api/account/password` `{current, new}` | player | set or change the password (`current` is not needed for an account that has none yet); ends the other sessions and returns a fresh `token` |
| `POST /api/account/logout_all` | player | end every session except this one |
| `POST /api/account/email` `{email}` | player | add or change the account's address: a code is mailed to it → `{ok, msg}` (§10.6) |
| `POST /api/account/email/resend` | player | mail the code for the waiting address again (60 s between codes) |
| `POST /api/account/email/verify` `{code}` | player | the six-digit code from the email → `{ok, msg}`; the address is then verified |
| `POST /api/account/forgot` `{name}` | anyone | mail a reset code to that account's verified address. The answer is the same whatever the name |
| `POST /api/account/recover` `{name, code, password}` | anyone | the reset code plus a new password → `{token, name}` (logged in; every old session ended). 400 for a wrong or expired code or a weak password |
| `GET /api/portfolio` | player | equity, cash, profit split, positions, allocation, equity curve, best/worst trades (§11) |
| `GET /api/history?limit=50&before=<seq>&kind=buy,sell` | player | the ledger, newest first, with paging (`next_before` is the cursor) and kind filters; `limit` is capped at 500 |
| `GET /api/history.csv` | player | the whole history as a CSV file download (one per 2 s) |
| `GET /api/me` | player | achievements, quests, the daily contest (with your paper account), following, ranks, drawdown, privacy, mute and appeal status, whether you can chat yet, and whether you have a password and how many devices are logged in |
| `GET /api/boards` | player | the day and all-time leaderboards (top 20 each, only people who have traded in that period) with your ranks (`null` if you are not on a board), how many are on each (`counts`) and your worst drawdown today |
| `POST /api/tournament/join` `{id}` | player | enter the daily contest and get its paper balance (§10.4) → `{ok, msg}` |
| `GET /api/profile/{name}` | player | another player's public profile (§10.5); 404 if unknown |
| `GET /api/following`, `POST /api/follow` `{name}`, `POST /api/unfollow` `{name}` | player | the follow list |
| `POST /api/public` `{public}` | player | set your privacy |
| `GET /api/admin/stats` | admin | house P&L breakdown, deposits, invariant drift, `borrow_fees`, `short_shortfall` (losses the house absorbed on gapped shorts), total `short_interest`, `recapitalized` (what the reserve has been topped up by) and `risk` (the exposure table and stress loss, §6.11) |
| `GET /admin` | anyone | the admin dashboard page (shows nothing until the key is entered) |
| `GET /api/admin/overview` | admin | everything the dashboard shows, in one call, including `perf` (server timings) |
| `GET /api/admin/player/{name}` | admin | one player's holdings and last 100 trades |
| `GET /api/admin/chat` | admin | latest chat messages, reports, who is muted, open and decided appeals, the moderator log, running contests |
| `POST /api/admin/appeal` `{id, decision}` | admin | `lift` or `deny` a muted player's appeal |
| `GET /api/admin/accounts` | admin | how many accounts have passwords, how many have a verified email, the `email_mode`, mail status, how many logged-in devices, and which accounts share an address (never the address itself) |
| `GET /api/admin/mail` | admin | whether mail is configured, how many were sent or failed, and the recent messages (in console mode with their codes) |
| `POST /api/admin/email` `{name, action: verify\|clear}` | admin | mark a player's address verified, or remove it |
| `POST /api/admin/reset_password` `{name}` | admin | give a player a temporary password (returned once) and end their sessions |
| `POST /api/admin/reset` `{confirm: "RESET"}` | admin | back up the save and the ledger into `backups/`, then start the game over at Day 1 (§1, §10) |
| `POST /api/admin/chat/delete` `{id}` | admin | delete a chat message (everyone's screen updates) |
| `POST /api/admin/mute` `{name, seconds}` | admin | mute a player's chat (`0` lifts it) |
| `POST /api/admin/credit` `{name, amount}` | admin | add MB to a player |
| `POST /api/admin/withdraw` `{name, amount}` | admin | remove MB from a player's free cash |

Every handler runs its engine work in a worker thread under the engine lock (see "Threads" below), so none can freeze the game.

Admin endpoints need the `X-Admin-Key` header to match the `ADMIN_KEY` environment variable. They are disabled if it isn't set.

`GET /internal/gateway` is a websocket for gateways only (§12, "Gateways"). It needs the `CORE_KEY` environment variable to be set and the same key in the `key` query parameter; with no `CORE_KEY` the door is shut.

### Admin dashboard (`/admin`)
**In plain English:** one page where you can watch the house. Is money being created or destroyed? Is the house winning or losing? Who is winning, and how? Is anyone getting margin-called?

**How to open it**
1. Start the server with an admin key: `$env:ADMIN_KEY = "a-long-random-string"` (see §1).
2. Open `http://127.0.0.1:8000/admin`, type the key and press Enter.
3. The page refreshes every 5 seconds. The key is kept in that browser tab only (session storage) and sent in a header; it is never in the URL or the page. Press **Lock** to forget it. A wrong key is refused and the page locks again.

**What's on the page**

| Part | What it shows | How to read it |
|---|---|---|
| **Alerts** (top) | Plain-language warnings, or a green "No alerts" line | See the rules below |
| **House reserve** | MB in the reserve, and total house capital | Kept above its floor automatically (§6.11) |
| **Fees collected** | All fees, and how much of that is borrow fees | Grows with activity |
| **House P&L** | Fees and liquidity, broken down | The house should earn about the fees |
| **Humans P&L** | Players' combined all-time P&L and how much they deposited | Should be about minus the fees (plus a little luck) |
| **Players** | How many players, and how many are connected | |
| **Trades** | Total trades and trades per minute over the last 5 minutes | |
| **Short interest** | MB currently shorted across all stocks, and the shortfall | Shortfall above 0 means a gap cost the house money |
| **Margin calls** | Count since the server started | |
| **Token drift** | The money-conservation check | Must stay at 0 / below 1e-6 |
| **Game tick time** | Average milliseconds the engine takes per second, and the slowest of the last two minutes | Typically 10-20 ms with 40 busy clients; above 500 ms is amber |
| **Late ticks** | Ticks that took more than a second (the loop could not keep pace) | Should stay 0; above 2 is amber |
| **Sending updates** | Time spent handing the per-tick messages to the sockets | A fraction of a millisecond |
| **Saving state** | How long the last snapshot took (every 30 s; the chart file is written separately every 5 minutes) | About 140 ms on a full-size game; above 800 ms is amber |
| **House risk** | Reserve, the floor it is topped up to, what has been topped up so far, the **stress loss**, and a table of the stocks players hold most of (net long or short, three daily sigmas, what it could cost the house) | §6.11. A stress loss above the reserve, or one stock being most of it, raises an alert |
| **Chat moderation** (four boxes) | Latest 40 messages with **Delete** and **Mute 10m / 1h** buttons; reported messages grouped by message (who reported them, how many); who is muted with **Unmute**; **Appeals** from muted players with **Lift mute** / **Keep mute**; the **moderator log** (every automatic and manual action) | Appeals and reports are the first thing to check each day |
| **Accounts** | Accounts with and without passwords, how many have a verified email and the `email_mode`, logged-in devices, accounts that share an address, and a **Reset password** box | §10.6 |
| **Email and mail** | Whether an SMTP server is set (a red warning in console mode), sent / failed / waiting counts, the last 15 messages (in console mode with their codes), and **Mark email verified** / **Remove email** boxes | §10.6 |
| **Gateways** | How many gateway processes are connected (0 = everything in one process) | §12 |
| **Start the game over** | A box where you type `RESET`, and the button | §1, §10. Backs up first |
| **Two line charts** | House reserve and fees; players' P&L, sampled every 10 seconds for the last 2 hours | A house reserve that trends down while fees go up means players are winning |
| **Returns bars** | How many human players are in each all-time return band (below -50% ... above +50%) | A long right tail may mean someone found an edge |
| **Recent margin calls** | When, who, which stocks were closed, and how much the house lost | |
| **Top winners** | The 10 best human players by P&L: equity, P&L, return, trades, open positions, margin calls | **Click a row** to open that player |
| **Player detail** | Cash, equity, deposits, dividends, borrow fees, open positions with P/L, and their **last 100 trades** (time, type, ticker, shares, price, MB, fee) | Types: buy, sell, short, cover, margin_call |

**Alert rules**

| Alert | Raised when |
|---|---|
| Red: token drift | the money-conservation check is above 0.000001 |
| Red: negative reserve | the house reserve is below zero (the automatic top-up normally prevents it) |
| Amber: stress loss | the stress loss (§6.11) is bigger than the reserve |
| Amber: one stock is the risk | one stock is more than half the stress loss (and over 1,000 MB) |
| Amber: shortfall | a gapped short has cost the house anything |
| Amber: a player is far ahead | the best human is up more than 50% with at least 20 trades (look at their trade log) |

**What backs it.** The engine keeps each player's last 100 trades (saved with the game), a log of the last 50 margin calls, counters, and a sample of house and player money every 10 seconds (in memory only). `engine.admin_overview()` and `engine.admin_player()` build the data; `server.py` serves it. Everything on the page is also available as JSON from the two endpoints.

**Limits.** There is no rate limit on admin-key guesses yet (see `ROADMAP.md`, A10), so don't expose `/admin` to the open internet without HTTPS and a long key.

### The WebSocket protocol (`/ws?token=…`)
**In plain English:** when a page connects, the server sends it **everything once** (`init`). After that, every second it sends only **what changed** (`tick`): the prices, your own numbers, and any new headlines. Slower-changing facts (ratings, margin and borrow numbers, financials, the leaderboard, the earnings calendar) come every fifth tick, and only when they changed. This replaced sending the whole market (about 120 kB) to every player every second.

**Server → client**

| Message | When | Contents |
|---|---|---|
| `init` | on connect, and again after a `sync` | everything: every stock (static facts including `listed_at`, slow numbers, price, change, a 60-point sparkline), sectors, the index, 30 headlines, the calendar, the leaderboard, your cash/equity/holdings and open orders, recent chat, the session (`market`: phase, whether the regular session is on, what comes next and when), the engine clock `t`, a tick counter `seq` and `static_v`. About 140 kB, once |
| `tick` | every second | `seq`, `t` (engine time), `px` (`{ticker: [price, change]}` for every listing), `idx` (market index value and change), `sec` (sector index values), `market` (the session: `phase` pre/open/after, `open`, `next`, `changes_in`, `pre`, `after`, `cycle`), `season` (the day number) and `season_left` (seconds left in the day), `players`, `news` (new headlines), `static_v`, and **`me`**: your cash, equity, return, P&L, rank, positions and (when they changed) your open orders. Every fifth tick also `board` (top 10), `slow` (rating, borrow fee and crowding, financials: only stocks that changed, everything once a minute) and `upcoming` (only when the calendar changed). About 4-12 kB |
| `notice` | when something happens to you | one-off messages (achievement, quest, contest result, mute or appeal outcome, margin call). Delivered as their own reliable messages, so skipping a tick can never lose one |
| `result` | after a trade, an order, a contest trade, a report or an appeal | `{ok, msg}` (`contest: true` for a paper trade) |
| `history`, `company` | on request | chart candles; the company's cast, news log and earnings history |
| `chat`, `chat_history`, `chat_delete`, `chat_error` | chat | a new message (to everyone); the history; a deletion by a moderator or by enough reports; why your message was refused |
| `error` | bad or expired token | the page then shows the sign-in box |

**Client → server**
- `{"type":"trade","ticker":"NVXA","side":"buy","pct":0.25}` (or `"amount": 50` in MB, which overrides `pct`) → `result`
- `{"type":"history","ticker":"NVXA","period":"30s|1m|5m|15m|30m|1h|2h|4h|1d|1mo|1y"}` → `history` (old period names fall back to 30s)
- `{"type":"company","ticker":"NVXA"}` → `company`
- `{"type":"order","action":"place","ticker":"NVXA","kind":"limit_buy|limit_sell|stop_loss|take_profit","trigger":41.5,"pct":0.25}` (or `"amount"` in MB), `{"type":"order","action":"bracket","ticker":"NVXA","take_profit":50,"stop_loss":40}`, `{"type":"order","action":"cancel","id":7}` → `result` (one per 0.2 s)
- `{"type":"contest_trade","id":"marathon-1791...","ticker":"NVXA","side":"buy|sell","pct":0.25}` (or `"amount"`) → `result` with `contest: true`: a paper trade in the daily contest (§10.4)
- `{"type":"chat","text":"...","channel":"global"}` (any other channel is refused), optionally `"share": <time of one of your trades>` → a `chat` message to everyone, or `chat_error`
- `{"type":"chat_history"}`, `{"type":"chat_report","id":12}` (the third different reporter removes the message and mutes its author, §10.7), `{"type":"chat_appeal","text":"..."}`
- `{"type":"sync"}` → a fresh `init` (at most once every 2 s)

**How the page merges ticks.** It keeps the `init` as its state and applies each tick on top: new prices (and appends the price to each sparkline), your numbers, new headlines (de-duplicated by id), and any `slow`, `board` or `upcoming` that came with it. Price-derived numbers (market cap, P/E, dividend yield) are **recomputed from the live price** instead of being sent, which is why slow updates stay small. If a tick's `seq` jumps by more than 4, or `static_v` changes (a listing was added or removed), the page sends `sync` and starts again from a fresh `init`. Each tick repeats the last 5 seconds of headlines so a skipped tick loses nothing.

**What it saves.** Measured with 192 listings: the old per-second state was **120 kB per player**, a tick is **about 6 kB on average** (the heavy fifth tick a little more, the once-a-minute full refresh about 54 kB, the first `init` about 140 kB). 100 players cost about 1 MB/s instead of 12 MB/s, and the server serialises the shared part of each tick **once**, then appends each player's own `me`.

### Threads, the loop and robustness
**In plain English:** the game engine is not thread-safe, so exactly one thread uses it at a time (a lock). Everything that touches it (the tick, every trade, every lookup, every HTTP endpoint) runs in a worker thread and takes the lock, so the web server's main loop (which only moves bytes) is never blocked by game work.

- **`game_loop`:** once a second, a worker runs `tick_step`: advance the game, save every 30 ticks, build the shared tick message, serialise it once, and prepare each connected player's `me` (and take their pending notices). The loop then hands each client its message and sleeps for the rest of the second. Timings are recorded (§12, admin dashboard) and ticks that overrun a second are counted as **late**.
- **One writer per connection.** Each socket has an outbox (results, chat, notices, in order) and a single **tick slot**. A client that is slow replaces its waiting tick with the newest one, so it **skips** ticks instead of building a backlog, and it never blocks anyone else. A send that takes over 3 s, or an outbox of more than 200 unread messages, drops that client.
- Messages that aren't valid JSON objects, are over 2,000 characters, or have bad fields are ignored. History and company lookups are limited to one per 0.2 s per connection; chat has its own limits (§10.7); `sync` is limited to one per 2 s.
- **Shutdown:** the loop is stopped, the state is saved and the ledger is closed, all under the lock.
- The page reconnects automatically with a growing delay (1 s up to 10 s), keeps one socket at a time, and gets a fresh `init` each time. A connection is keyed by the account's internal token, never the session token, so two tabs of one player share one update.
- **Capacity.** One process on this machine, with a full-size game (193 listings, a 27 MB save) and ordinary players (one trade every ~15 s, a chart every ~20 s): 100 players use about 18% of one CPU core, 200 about 29% and 400 about 51%; the tick takes 54-65 ms on average whatever the number of players, each player receives about 10 kB a second (400 players ≈ 4 MB/s of upload), and no tick came late. One core therefore carries roughly 700-800 simultaneous players before the tick work alone fills it. `python tests/capacity.py 200 40` measures it (§16). Beyond that, run gateways (next section: the game server alone then carries roughly 4,000 players); past that the roadmap lists what is left (G10: splitting the engine itself, a database).

### Gateways: more than one process
**In plain English:** one Python process runs the game and also sends every connected player their once-a-second update. Running the game is cheap (about 55 ms a second however many players there are). Sending is what costs: a page's worth of prices per player per second, each one packed, compressed and written to a network socket, all on one processor core. A **gateway** is a second kind of process that takes the sending (and the holding of connections) off the game server. You can run several, one per core, and the game server keeps doing only the thinking. The market itself is still one process, because it is one shared thing: one set of prices, one lock, one save file.

```
browsers ──websocket──▶ gateway (1..N processes) ──one link each──▶ game server
                         holds the connections,                     prices, trades, accounts,
                         sends the updates                          saves, news (one process)
```

**Starting it.** `python launch.py --gateways 4` (§1) starts the game server on `127.0.0.1:8001` and four gateway worker processes sharing port 8000. The launcher makes a random `CORE_KEY` and gives it to both sides; a gateway connects to the game server's `/internal/gateway` websocket and has to present it (without a `CORE_KEY` the game server refuses all gateways, so a normal start exposes nothing). `python launch.py` alone is the old single-process game. The tests can run the whole suite through gateways: `MS_TEST_GATEWAYS=2 python -m unittest discover tests` (§16).

**What a gateway does.** It serves the pages (the game, `/admin`, the logo; the same code as the game server, `pages.py`); holds each browser's websocket; applies the once-a-second update; forwards the browser's messages (trade, chat, chart request...) to the game server, which answers over the same link; and passes every ordinary `/api/...` request to the game server, adding the caller's real address (§10.6). A request is run through the game server's own app exactly as if it had arrived directly, so sign-in, portfolio and admin behave identically (and every limit, header and status code is the same). It holds **no game state at all**: restart a gateway at any moment and its pages reconnect through it or another one.

**What travels on the link.**

| Direction | Message | Meaning |
|---|---|---|
| gateway → game | `open` (connection id, the page's token) | a page connected; the game checks the token and sends back its `init` |
| gateway → game | `msg` (connection id, the raw text) | the page sent a message; the game handles a page's messages one at a time, in order, with the very same code as a direct websocket |
| gateway → game | `close` | the page went away |
| gateway → game | `http` (id, method, path, headers, body) | an ordinary request, answered with `http_res` |
| game → gateway | `to` (connection id, text) | a message for one page: `init`, a trade result, a chart |
| game → gateway | `opened` (connection id, player key) | the page's `init` has been sent; updates may follow (never before) |
| game → gateway | `bc` (text, who) | a broadcast: a chat message or a deletion for everyone, a notice for one player |
| game → gateway | `hangup` | close that page (a reset, a bad token, too many unread messages) |
| game → gateway | the tick frame | once a second: the part every player gets, then one line per player on that gateway with that player's own numbers |

**The once-a-second update.** The game server builds the shared part of the tick once, as before, and each player's own `me` part (cash, equity, positions: about 15 microseconds each), but it no longer joins them or sends a page-sized message per player. It sends each gateway **one frame**: the shared JSON, then one `player-key <tab> me-JSON` line for each player connected to that gateway. The gateway splices the two together for each page (`shared[:-1] + ',"me":' + me + "}"`, a string join) and writes it to that page's socket. Link traffic is therefore about 6.5 kB plus 0.6 kB per player a second, not 7 kB per player. Messages that must not be lost (results, chat, notices) go as their own ordered frames, ahead of the tick; the tick uses a one-slot "latest only" queue, so a slow link skips a tick instead of building a backlog (the same rule as for a slow browser, §12 "Threads").

**When things break.**
- *A gateway dies:* the game server forgets its pages (the online count drops) and carries on; the browsers reconnect, to another gateway if the proxy or the launcher has one.
- *The game server restarts:* each gateway closes its pages' sockets (so the browsers reconnect with their usual backoff and get a fresh `init`), answers ordinary requests with `503` "The game is restarting" and a `Retry-After`, and tries the link again with a growing delay (one to five seconds) until it is back. Nothing needs restarting by hand. (The game is down for a restart exactly as it would be in one process: the game server saves on the way out and recovers from its ledger.)
- *A page floods the gateway:* each page may send 20 messages a second on average (a burst of 40); beyond that its messages are dropped, and a page that keeps flooding is hung up on. The game server's own per-message limits (orders, lookups, chat) still apply behind it.
- *A request is too big or takes too long:* over 64 kB is refused (413); no answer within 30 s is a 504.

**Security.** The game server's port (8001) listens only on this computer. Gateways authenticate with `CORE_KEY` (compared in constant time). The caller's address is worked out by the gateway (from `CF-Connecting-IP` / `X-Forwarded-For` only when the request came from this computer or `TRUST_PROXY=1` is set) and passed to the game server in a header it believes only from a local caller; a client-supplied forwarding header never reaches the game server. Only the headers the game needs (`X-Token`, `X-Admin-Key`, `Content-Type`, `Accept`, `User-Agent`) are passed on.

**What it buys, measured** (`python tests/capacity.py <players> 40 <gateways>`, a full-size game, ordinary players; the CPU figures add up the game server and every gateway, and the last column is the game server alone):

| Players | Layout | Total CPU* | Game server alone* | Average tick | Memory | Late ticks |
|---|---|---|---|---|---|---|
| 400 | one process | 29% | 29% | 27 ms | 168 MB | 0 |
| 400 | game + 2 gateways | 41% | 13% | 30 ms | 303 MB | 0 |
| 400 | game + 4 gateways | 44% | 13% | 29 ms | 433 MB | 0 |
| 1,000 | one process | 62% | 62% | 49 ms | 237 MB | 0 |
| 1,000 | game + 4 gateways | 99% | 30% | 49 ms | 544 MB | 0 |
| 2,000 | game + 4 gateways | 164% | 50% | 75 ms | 662 MB | 0 |

\* As a share of one processor core (so 164% is one and a half cores in all). The total is a little higher with gateways (there are more messages to pass around); what matters is that the game server's own core is no longer the one doing the sending. **One process alone fills its core at roughly 1,600 players; with gateways the game server alone carries roughly 4,000 before its core is full**, and the sending is spread over the gateways (about 28% of a core each at 2,000 players with four of them). This machine and a copy of the real save; the earlier single-process figures in the capacity section below were taken on a busier moment and are higher, so compare the layouts within one table, not across them.

**What it does not do.** The game server is still one process on one core (one lock), so past what the game server alone can carry (about 4,000 players, above), more gateways do not help; going further means splitting the engine itself (ROADMAP G10). The database is still SQLite and a single writer, which is fine for one game server. Gateways and the game server must be on the same machine or a trusted private network (the link is not encrypted), and the pages are served from the project folder, so every gateway needs a copy of it.

---

## 13. Saving and the crash-proof ledger

**In plain English:** the game is saved in two ways that back each other up. A **snapshot** (`state.json`) is a photo of the whole game every 30 seconds. The **ledger** (`ledger.db`) is a notebook where every change to anyone's money is written down the moment it happens. If the server crashes, the next start loads the last photo and then replays the notebook entries written after it, so **nothing is lost, not even the last second**.

### The snapshot (`state.json`)
- **When:** every 30 ticks, on shutdown, and straight after a recovery. It writes `state.json.tmp` and then replaces `state.json`, so a crash mid-write can't leave a half file. A new account, a password change and an admin reset also save at once. **If Windows refuses to swap the file in** ("Access is denied": OneDrive, a virus scanner or a backup tool has it open for a moment, which this project's OneDrive folder invites), the save tries again up to eight times over a few seconds, and if it still can't it logs a warning and tries again at the next save (the chart file in half a minute) instead of raising an error in the game loop. Keeping the game folder out of OneDrive's sync avoids it altogether.
- **Two files.** On a long-running game the chart candles (11 timeframes × 500 candles × every stock) were 23 of the 27 MB, and they change slowly. They now live in **`state.charts.json`**, which the periodic save rewrites only every `charts_save_seconds` (300 s) and a clean shutdown always writes; `state.json` keeps everything else including the one-minute candles. If the chart file is a few minutes behind after a crash, the candles it is missing are rebuilt from the one-minute candles when it loads; if it is missing or unreadable the charts are rebuilt from them too (older than a few hours is lost, the 30-second candles of the gap stay empty). A save from before the split, with the charts inline, loads normally. **Why:** a save of the full game took about 2.4 s with the old `json.dump` (a slow Python path) while holding the game lock, which froze every trade and update for that long every 30 seconds; with the fast encoder and the split it takes about 140 ms.
- **What's saved (schema 7):** per stock: `base` (its size), `fair` (the price), candles for every timeframe, daily candles, rating, hidden safety, mood, trend, **volatility multiplier**, **when it was listed (`listed_at`)**, share adjustments from buybacks and offerings, **the persona (CEO, CFO, product, city, former CEOs)**, **its earnings slot**, financials (revenue, margin, cash, debt, long-run margin), declared dividend and pending ex-date, pending stories, scheduled company events, any pending share offering, the stock's news log, earnings reports, schedules; globally: **the moonshot companies generated so far (`generated`)**, **the supplier / customer / rival graph (`relations`)**, house reserve, fees, house capital, minted, the index, regime, market and sector mood, market volatility, crisis end time, every headline printed (last 6,000), remembered story threads, season data, the margin-call log and counters, and **the ledger position this snapshot covers (`ledger_seq`)**; per player: cash, holdings (negative = short), cost basis, entry fees, realised profit per stock, fees paid, trade count, dividends received, borrow fees paid, their last 100 trades, margin calls, deposits, day base, **open orders**, **the password hash, address tags and sign-up time**, and **all social data**: achievements and their counters, today's progress and quests done, streak, drawdown tracker, medals, privacy, following, strikes, open-position times. Chat, mutes, reports, appeals, the moderator log, the running contest (with every entrant's paper account) and finished contests are saved too, and so are the login sessions (only their hashes), the address salt, the delisted-stock archive (the last 60 companies' charts, news and facts, so their pages still open) and `recapitalized`.
- **Not saved:** the admin charts' history (they restart empty), the global news wire (`news_log`), rumours waiting to confirm, sparklines, equity snapshots, trade cooldowns, the delayed-holdings snapshots (they refill in a few minutes). Per-stock news logs *are* saved.
- **Older saves** load: a save with the old leveraged tickers is migrated (§9), contests from before paper accounts are dropped, accounts without passwords stay usable, a save without the chart file keeps its inline charts, schemas before 7 get the old pool price as the market price, positions starting at the current price as their average entry, and ratings recomputed; a save with no social section just starts everyone with no achievements; a save from before moonshots simply gets four new ones; a ticker new to the content since the save is marked NEW; a save that still has seed tokens inside its stocks has them retired (§5), and a stock removed from content is simply dropped.

### The ledger (`ledger.py`, `ledger.db`)
A SQLite file in WAL mode with two tables, flushed once per tick:
- **`events`** (append-only, never edited or deleted, except by an admin reset, which copies the file to `backups/` first): one row per money event: `join`, `credit`, `debit`, `buy`, `sell`, `short`, `cover`, `margin_call`, `margin`, `dividend`, `borrow` (borrow fees are summed and written every 10 seconds), `delist_payout`, `delist`, `recap` (a top-up of the house reserve). Old ledgers may also hold `split` rows, which are ignored. Each row records the time, player, ticker, shares, price, and the **changes** to the player's cash, the house reserve, fees and the position's cost basis, plus the realised profit on closing trades.
- **`curve`**: each player's equity and cash once a minute (the equity curve on the portfolio page; the last 1,440 points are reloaded at start).

**Recovery.** On start the engine loads `state.json`, reads `ledger_seq`, and replays every event after it (`Engine._replay`): cash, holdings, cost basis, fees, house reserve, dividends, borrow fees, counters, and players who joined after the snapshot. It then checks the **token invariant** (the books still balance to within a millionth) and saves a fresh snapshot. A test kills an engine in the middle of play and checks that the recovered state matches the live one trade for trade. **Not recovered:** prices, news and the social counters since the last snapshot (up to 30 seconds), and borrow fees charged in the last few seconds before the crash (they are written every 10 seconds): they are cosmetic, random or tiny. Trades, deposits, dividends and payouts are exact.

**What it's for besides recovery:** the history page and CSV export (§11, §12), realised profit and best/worst trades, and the equity curve. With `ledger_path=None` (tests, `sim.py`) the engine runs without a ledger and the history page falls back to each player's last 100 trades in memory.

**Housekeeping (see `ROADMAP.md`, G11):** the file only grows. Back it up with the snapshot. To start a new game delete both (§1).

---

## 14. Settings reference

**How to change a setting.** Settings live in the content packs (`base.json` has the defaults). To change one without editing a shipped file, make a new root-level file such as `my_settings.json` containing only `{"settings": {"email_mode": "required"}}`: packs are merged in alphabetical order and later files win, and the game re-reads packs about once a second, so most changes apply without a restart (a few, such as the ones that decide what exists at the start of a new game, only matter then).

| Setting | Default | Effect |
|---|---|---|
| `signup_bonus` | 10000 | MB credited to new players and to everyone on a game reset (0 for real money) |
| `house_seed` | 50000 | starting house reserve (funds new listings) |
| `season_seconds` | 86400 | length of a day (the old season): the leaderboard period; the day ends at the next multiple of it since the epoch, so 86400 means UTC midnight |
| `event_mean_seconds` | 120 | average gap between random news events |
| `issue_mean_seconds` | 100 | average gap between company stories (§7.7) |
| `mood_tilt` | 1.0 | scales how strongly the hidden mood tilts headline direction; 0 turns the tilt off (for experiments) |
| `news_followups` | true | `false` stops stories from being remembered for follow-ups (for experiments) |
| `dividends_enabled` | true | `false` stops reports from declaring dividends (for experiments) |
| `news_strength_weights` | 25/40/25/10% | how often each strength appears |
| `news_move_ranges` | see §7.5 | raw impact before the clamp |
| `event_strength_limits` | 0.1/0.35/0.65/1.0 | event size cap, as a multiple of daily σ (the real size control) |
| `rumor_prob` / `rumor_credibility` / `rumor_delay_seconds` | 0.6 / 0.75 / 45–90 | rumour frequency, accuracy, time until confirmation |
| `earnings_quarter_days` | 63 | length of a fiscal quarter in game days (63 = 31.5 real hours); every report and dividend is one quarter apart, give or take `earnings_jitter_days` (a quarter shorter than a game day is a demo: no windows, no jitter beyond 15%) |
| `earnings_jitter_days` | 4 | how many game days (2 real hours per 4) a report may drift from exactly one quarter after the last (§7.7) |
| `relation_spillover` | 1.0 | scales how much a company's suppliers, customers and rivals move it (§7.15); 0 switches it off |
| `premarket_seconds` / `aftermarket_seconds` | 300 / 300 | length of pre-market and after-hours at the start and end of each 30-minute cycle (§6.8); both `0` switches the sessions off |
| `extended_noise` | 0.35 | noise multiplier in pre-market and after-hours |
| `open_burst` / `open_burst_seconds` | 2.5 / 150 | extra noise at the open and how fast it fades |
| `close_burst` / `close_burst_seconds` | 1.5 / 120 | extra noise into the close and how long it lasts |
| `open_jump_seconds` | 90 | size of the opening jump, in seconds' worth of ordinary noise |
| `short_cap_frac` / `short_cap_index` | 0.25 / 16000 | the yardstick for how crowded a short is (a share of a stock's size, and a fixed figure for indices): it only scales the borrow fee, it no longer limits anything |
| `borrow_base_day` / `borrow_vol_day` | 0.0003 / 0.001 | borrow fee per game day: base plus this × volatility, then × (1 + 3 × how crowded the stock is) |
| `rating_review_seconds` | 600–1500 | bank review interval per stock (real seconds) |
| `regime_days` | 7–14 | regime length (game days) |
| `volatility_scale` | 1.0 | multiplies all noise and event caps |
| `commodity_trend` | 0 | multiplier on the old commodity drift (§6.1); keep at 0, because any value above it is a momentum edge |
| `daily_move_cap` | 0.15 | largest daily limit `L` for the soft daily brake (§6.5); 0 switches it off |
| `mean_reversion_halflife_days` | 90 | reversion speed; keep at 90 or more (see §6.2) |
| `distress_price_ratio` | 0.25 | a company this far below its reference price is resolved (§6.6) |
| `bankruptcy_chance` / `bankruptcy_payout` | 0.5 / 0.25 | ordinary company: chance of bankruptcy, and the share of the price holders get; the rescue jump follows from the two (×1.75) |
| `moonshot_bankruptcy_chance` / `moonshot_bankruptcy_payout` | 0.6 / 0.03 | the same for moonshots (rescue ×2.45) |
| `moonshot_initial` / `moonshot_max` / `moonshot_mean_seconds` | 4 / 8 / 900 | moonshots at the start of a new game, the most that may trade at once, and the average gap between new listings (§6.10) |
| `catalyst_mean_seconds` / `catalyst_moonshot_weight` | 480 / 10 | average gap between catalysts across the market, and how much likelier a moonshot is to get one (§7.13) |
| `catalyst_moonshot_scale` | 0.7 | multiplies the upside range of a moonshot's catalysts (§6.11); the loss is re-derived so the bet stays fair |
| `sector_shock_mean_seconds` | 600 | average gap between industry-wide shocks (§7.14); a very large number switches them off |
| `sector_shock_size` | 1.0 | multiplies the size of every industry-wide shock (§7.14): 0.5 for half-size moves, 1.5 for half as big again |
| `sector_links` | expansion.json | cross-sector spillovers |
| `vol_cluster_k` / `vol_cluster_decay_days` | 0.01 / 1.0 | volatility clustering: how strongly a big move raises the multiplier and its half-life in game days (§6.7); `vol_cluster_k=0` switches it off |
| `major_event_limit_boost` / `major_event_boost_seconds` | 2.5 / 600 | how much a "very strong" event loosens a stock's daily limit and for how long (§6.5) |
| `offering_mean_seconds` / `offering_delay_seconds` | 1200 / 300 | average gap between share offerings across the market, and the time from announcement to completion (§6.9) |
| `company_events_per_quarter` | 1.5 | scheduled company events (guidance, investor day, analyst call, product event) per company per quarter; 0 switches them off (§7.16) |
| `max_orders` / `order_expiry_seconds` | 20 / 604800 | open orders a player may have, and how long an order lives (§4) |
| `reserve_recap` | true | `false` stops the automatic top-up of the house reserve (§6.11) |
| `reserve_floor_frac` / `reserve_stress_frac` / `reserve_floor_min` | 0.10 / 0.5 / 0 | the reserve is topped up to the largest of this share of the human players' equity, this share of the stress loss, and this many MB |
| `chat_min_trades` | 3 | trades a new account must make before it can chat or report (§10.7) |
| `chat_report_threshold` | 3 | different players who must report a message for it to be removed and its author muted |
| `chat_bad_words` | none | extra words for the chat filter, for example from a content pack |
| `contest_balance` / `contest_join_seconds` | 10000 / 43200 | the paper balance every entrant gets, and how long after the start of the day entries stay open (§10.4) |
| `require_password` | true | `false` allows the old name-only sign-up (§10.6) |
| `signups_per_ip_hour` / `login_fails_per_name` / `login_fails_per_ip` | 5 / 5 / 20 | new accounts per address per hour; failed logins per name in 15 minutes; failed logins per address in 10 minutes |
| `trust_proxy` | false | believe `X-Forwarded-For` / `CF-Connecting-IP` from any caller, for a proxy on another machine. A request that comes from this very computer (a tunnel or proxy running here, or a gateway) is always believed (§1, §10.6) |
| `email_mode` | off, or optional once `SMTP_HOST` is set | `off`, `optional` or `required` (a verified email is needed to trade, place orders, enter the contest or chat) (§10.6) |
| `email_code_minutes` / `email_max_tries` / `email_resend_seconds` / `email_sends_per_hour` | 15 / 5 / 60 / 5 | how long an emailed code works, wrong guesses before it dies, the wait before another code, and codes per address per hour |
| `mail_per_hour` | 200 | a ceiling on all mail the game sends in an hour (0 = none) |
| `blocked_email_domains` | none | extra throwaway-mail domains to refuse, on top of the built-in list |
| `charts_save_seconds` | 300 | how often the periodic save rewrites the chart file (§13) |
| `cross_mean_seconds` | 240 | average gap between two-company stories (§7.11) |
| `auto_sector_indices` / `sector_index_min_members` | true / 3 | create a tradable index for every sector with at least this many companies (§9) |
| `public_delay_seconds` | 300 | how old a holdings snapshot must be before other players can see it (§10.5) |
| `chat_enabled` | true | `false` turns chat off for everyone (§10.7) |

**Environment variables** (not settings: they are about the machine, not the game): `ADMIN_KEY` (switches the admin API on), `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `SMTP_SECURITY` (sending mail, §10.6), `CORE_KEY` (the game server accepts gateways that present it; set by `launch.py --gateways`), `CORE_URL` and `TRUST_PROXY=1` (for a gateway, §12).

Constants in `engine.py`: `FEE` 0.1% (it was 0.5% until 2026-10-03; see the note in §15), `COOLDOWN` 1 s, `MAX_TICK_MOVE` 15%, `SNAP_EVERY` 5 s, `MARKET_DAY_SECONDS` 1800, `TIMEFRAMES`, the narrative text pools, `BANKS`, `RATINGS`. In `newsgen.py`: the name, city and product pools, `ISSUE_KINDS` (company stories), `CROSS_KINDS` (two-company stories), `SYNONYMS`, `SOURCES`. In `social.py`: `ACHIEVEMENTS`, `QUESTS`, `CONTESTS`, `CONTEST_BALANCE`, the chat limits (`CHAT_MAX` 200, `CHAT_MIN_GAP` 1.5 s, `CHAT_PER_MINUTE` 15), the word lists (`BAD_WORDS`, `BAD_WORDS_EXACT`), `MUTE_STEPS` (10 minutes, an hour, a day), `FOLLOW_MAX` 20, `SNAP_EVERY` 30 s (holdings snapshots). In `accounts.py`: the scrypt cost, `MIN_PASSWORD` 8, `SESSION_DAYS` 30, `MAX_SESSIONS` 10, the reserved names, the list of too-common passwords and of throwaway-mail domains.

Per-template field `good` (`"down"`): marks the "down" text as the good news.

Fields now ignored: `bots`, `bot_cash` and `bot_action_probability` (there are no bots), `close_seconds`, `bailout_chance`, `bailout_return`, `bankruptcy_haircut`, `position_cap_base`, `position_cap_abs_frac` (replaced by the sessions, the fair distress terms and the removal of position limits), `split_price_ratio` and `split_delay_seconds` (there are no splits), the club settings, and `season_seconds` values other than whole days no longer line up with the daily contest, `event_duration_scale`, `sev` / `chunks` in templates, `rating_review_days`, `earnings_initial_seconds` / `earnings_interval_seconds` (replaced by `earnings_quarter_days`), and the `earnings` trait (every equity with revenue reports).

The margin-call levels (25% to 75%) in §4 are fixed in the code (`maintenance`).

**Before changing any of these**, run `tune.py` on the old and new values with a fresh first seed. Keep the `value` and `hodl` columns near zero and `drift` at about 1e-10.

---

## 15. Things to know

- **The house is the counterparty.** With no price impact, every trade is against the house reserve. Over many players the house earns the fees, but a lucky or skilled player is paid by the house, not by other players. This differs from the goal in `ROADMAP.md` ("player profits come from other players' losses"); decide whether that is acceptable before real money.
- **No edge is allowed.** News, mean reversion and earnings are built to have zero expected move. Anything that makes prices predictable from public information is a house-funded edge now, with no slippage to stop it.
- **The house carries the risk, and there is no cap on position size.** A player can put everything into one wild stock and win a large sum on a moonshot, paid by the house. What keeps that in check without limiting anyone (§6.11): thinner tails (a rescue is ×1.75 or ×2.45, moonshots are braked harder and their catalysts trimmed), a house reserve topped up automatically to a floor that follows the players' money and the stress loss, and an admin risk report with alerts. Shorts are paid for out of cash, pay borrow fees, and the margin call closes shorts that go too far. A stock that gaps past a margin call can still cost the house the difference (`short_shortfall`). Decide before real money whether the floor is enough; it is the operator's capital decision (`ROADMAP.md`, A12).
- **Fees are the business, and they are small.** 0.1% per side means about 0.2% per round trip (it was 0.5% and 1%, which meant a trade had to gain over 1% just to break even). The house earns about a fifth of what it did from the same trading, and the fee is also the cushion that makes any tiny, undiscovered edge unprofitable: the edge checks of §17 were re-run at the new fee (§17.5), and `FEE` is the one number to raise if a check ever shows a strategy beating it.
- **Is a built-in house edge a good idea?** (The question was a 1% edge: "if this ran forever the house should make 1%".) The game already has a house edge, in the open: the fee. The many-bot study measured it (§17.7): players lose **0.107% +/- 0.011% of everything they trade**, which is the 0.1% fee and a little borrow cost. So "1% of what players trade" would mean a fee of about **1% per side (2% a round trip)**, ten times today's, and 1% of a round trip (0.5% per side) is the level that was cut because it was too high. In the study the active strategies traded 14 to 164 times their capital in two hours, so at 1% per side they would have lost everything several times over (the news chaser 78 times its money traded: 7.8% lost at today's fee, 78% at 1%). It cannot be done through the prices either: prices that drift against players would help anyone who shorts, and the house is the counterparty to the shorts too, so only a cost that applies to both sides (a fee or a spread) is direction-blind. Hiding it in the price drift would also break the rule that no strategy has an edge, and with real money a disclosed fee is far easier to defend than a rigged price. The better lever is the size of the fee against the number of players and how much they trade, judged on revenue per player in the closed test (`ROADMAP.md`, open questions); and the bigger risk for the house is not too small an edge but variance: 100 players sniping moonshots swung the house by a standard deviation of 430,000 to 974,000 MB per market against 1,900 to 11,000 MB of fees (§17.7), which no realistic edge covers: that is what the reserve and ROADMAP A12 are for.
- **Player-vs-player profit** no longer exists in the pricing; a player's gain is the house's loss.
- **Removing a company from the content files** while players hold it isn't handled well. On the next restart, its listing is dropped and holders' shares are discarded. Delist through gameplay first.
- **Signup bonus farming is limited, not impossible.** Accounts need a password and a sign-up is limited to 5 per address per hour, and accounts that share an address are listed for the admin, and with `email_mode` set to `required` each account needs its own verified email address (§10.6). A determined person with many real addresses can still make many accounts, each with 10,000 MB. That is harmless with play money; with money of value you would add a phone or wallet check on top (`ROADMAP.md`, H).
- **Chat moderation is automatic but not perfect.** The word filter sees through common disguises, three different reports remove a message and mute its author with growing mutes, and muted players can appeal, but a filter never catches everything (other languages, new slang), and a coordinated group could mass-report someone (the trade-first gate, the three-different-reporters rule and appeals soften that). A public launch needs a human moderator reading the log (`ROADMAP.md`, F8).
- **The old name-only accounts have no password until their owner sets one.** They work with their old token, which lives only in that browser. Until a password is set, clearing the browser loses the account.
- **Earnings come out only in pre-market or after-hours,** on the same real clock as the sessions, so a report is due in one of the two five-minute windows of a half hour; with the sessions switched off they come out at any time.
- **Suppliers, customers and rivals are internal.** Players can only infer them from the news. They are saved with the game; a company added to a content pack is linked in by sector rules, and for the companies that ship with the game the links are hand-written in `relations.py` (edit them there).
- **Sessions use the real clock.** Pre-market, the regular session and after-hours follow the server's clock (UTC, the same for everyone), so a game started at 12:17 begins in the regular session. The page shows the times in your own time zone. A server that is already running keeps the code it started with: restart it to get new sessions, moonshots and catalysts.
- **Passwords are the login now.** The browser keeps a session token in `localStorage`; losing it just means logging in again. A forgotten password is recovered with a code mailed to the account's verified email (§10.6); an account with no verified email still needs the admin's **Reset password**.
- **Only one server per save file and ledger.** Two servers would overwrite each other's snapshots and interleave their ledgers.
- **The ledger is not a backup.** It lives next to `state.json`; copy the save, the chart file and the ledger. Money events since the last snapshot are replayed after a crash, but achievement counters and chat since then are not. The admin **Reset** button makes such a copy for you in `backups/` before it clears anything.
- **Chart history is rewritten every five minutes,** so after a crash the newest part of the 30-second charts may have a gap (the one-minute and longer candles are rebuilt).

---

## 16. Tests

**In plain English:** the tests are small programs that play the game for you and check that the rules still hold. If you change the engine and a test fails, you've broken something that used to work. They exist so that changes to prices, news, fees or limits can't quietly lose the house money or break the page.

### What's in `tests/`

| File | What it checks | Tests | Speed |
|---|---|---|---|
| `test_engine.py` | trading, **no position limits**, shorting, margin, borrow fees, **the soft daily limit**, dividends, earnings schedule, news, **the bigger market (listings, sector indices, ETFs, leveraged products, total return)**, **the NEW badge and listing times**, **no commodity drift**, admin data, saving | 70 | about 50 s |
| `test_volatility.py` | **volatility clustering, the major-event limit boost, and the trading sessions** (the 5 / 20 / 5 cycle, thin noise outside the regular session, the opening jump, the day keeping its volatility, no direction anywhere) | 27 | about 15 s |
| `test_wild.py` | **moonshots and catalysts**: the generator, listing and replacement over time, no tickers reused, persistence, the wide daily limit, margin and borrow safety, **fair distress terms**, **fair catalysts**, and conservation with everything running | 35 | about 10 s |
| `test_sector.py` | **industry-wide shocks** (every kind is a fair bet, every company's expected move is zero, the whole sector moves the same way and nothing else does, a sector can fall while the market rises, spillovers have no direction, headlines are unique and name the sector, conservation) and **the volatility multiplier staying centred on 1 through every session** | 21 | about 40 s |
| `test_relations.py` | **the hidden supplier / customer / rival graph**: sensible links, consistency from both sides, sparsity, a new company linking in (and the hospital chain gaining a supplier), removal on bankruptcy, saving and old saves, nothing visible to players, stories pairing only linked companies, spillover signs, no average and no extra volatility, conservation | 23 | about 15 s |
| `test_calendar.py` | **the earnings calendar** (reports spread so one is always coming, only in pre-market or after-hours, a quarter apart give or take a few days, new listings take a quiet slot, old saves are moved into windows), **bank notes giving a reason about 40% of the time**, and **headlines with no hidden information** | 17 | about 55 s |
| `test_news.py` | **personas, the slot grammar, story kinds and uniqueness, CEO changes, buybacks and offerings, two-company stories** | 33 | about 15 s |
| `test_ledger.py` | **the ledger and crash recovery**: every event kind is recorded with the right deltas, cash/house/fees equal the sums of the ledger, realised profit adds up, a crash loses no trades | 24 | about 10 s |
| `test_portfolio.py` | **the portfolio page data and the trade history** (curve, allocation, realised vs unrealised, best/worst, paging, filters, CSV) | 16 | about 3 s |
| `test_wire.py` | **the delta protocol's engine side**: init + ticks equal a full state, slow data only when changed, the session profile only in `init`, no hidden state on the wire | 17 | about 3 s |
| `test_social.py` | **achievements, quests, boards and drawdown, profiles and privacy, following, chat, persistence**, and that none of it moves a price | 73 | about 20 s |
| `test_server.py` | the real web server (run in an isolated copy): pages, joining, the WebSocket protocol, trades, **orders and paper contest trades over the socket**, bad input, **portfolio/history/CSV, social endpoints, chat and moderation (including the three-report auto-mute and an appeal) over the wire, 401/403/429, a burst of requests that must not make ticks late**, admin | 36 | about 55 s |
| `test_browser.py` | drives the real pages in headless Edge or Chrome: the original flows, **search/sort/watchlist, the market layout, trading from the holdings page, the three sessions, every other page including the contest panel, a delisted stock's page, the order panel, password sign-up / log out / log in / change password, email sign-up / code / forgot-password recovery, reconnecting**. Skipped if no browser is installed | 9 | about 4 min |
| `test_market_changes.py` | **the leveraged products** (2LMSI, 2SMSI, 3LMSI, 3SMSI, the old ones migrated and withdrawn, redirects), **no splits**, **offerings** (only the share count changes, announced on the wire, no price or cash effect), **delisted stocks keeping a page**, one-day days | 30 | about 15 s |
| `test_orders.py` | **orders**: limit, stop-loss, take-profit and bracket validation, filling at the market price (including through a gap), close-only, one-cancels-other, cancel, expiry, limits per player, persistence and crash recovery, **no effect on any price** | 27 | about 20 s |
| `test_company_events.py` | **scheduled company events**: schedule, spread, calendar entries without a hint of direction, firing, the next report naming them, **every kind a fair bet**, conservation, persistence | 16 | about 5 s |
| `test_no_halts.py` | **no trading halts**: the circuit-breaker code and state are gone, a stock and the whole market can be traded straight after a crash, no halt news is printed over a wild hour, a stop-loss fills through a crash at once, no halt field is sent to the page, old halt settings do nothing | 7 | about 15 s |
| `test_contests.py` | **the daily contest**: the same paper balance for everyone, **a paper trade follows the real rules exactly (compared with a real twin)**, margin calls, borrow fees, dividends, bankruptcy payouts, ranking, medals, **no effect at all on prices, the house or real balances**, persistence, old contests dropped | 25 | about 40 s |
| `test_accounts.py` | **accounts**: password hashing, sessions (expiry, the ten-session cap, ending one or all), the old token working only without a password, reserved names, the sign-up and login limiters over HTTP, password change, admin reset, address flags, persistence, the browser-free parts of sign-in | 36 | about 20 s |
| `test_moderation.py` | **chat moderation**: the word filter (disguises caught, ordinary words left alone, accents kept), the trade-first gate, three reports removing a message and muting its author, growing mutes, appeals, the moderator log, persistence | 23 | about 5 s |
| `test_house_risk.py` | **house tail risk**: the thinner rescue and catalyst tails (still fair bets), the reserve floor and automatic top-up (books balance, **no price or balance changes**, ledger recovery), the exposure report | 16 | about 12 s |
| `test_save.py` | **saving**: the chart file split, the periodic save rewriting charts only when due, a stale or broken chart file, old saves with inline charts, **the save and its chart file never being read as content packs** | 14 | about 50 s |
| `test_email.py` | **email on accounts**: address rules and spellings of one mailbox, throwaway domains, six-digit codes (hashed, expiring, limited tries, resend limits, one use), one account per address, an unproven claim losing, `required` mode blocking trades, orders, contests and chat (and not a verified player's paper account), password recovery (same answer for any name, one use, ends every session), saving and old saves, the mailer (background thread, retries, console mode, the queue ceiling), the whole flow over HTTP and the sign-up limit counting each visitor behind a tunnel separately | 45 | about 40 s |
| `test_gateway.py` | **gateways**: two gateways and a game server: init and ticks with each player's own numbers, trades, chat and charts across gateways, ordered messages, ordinary requests and pages through a gateway, the closed door without the key, a flooding page, a gateway dying, **the game server restarting and the gateways finding it again**, `launch.py --gateways 2`, and `share.py` (the whole flow against a stand-in for cloudflared, finding the link, refusing when the game is not running or the program is missing) | 21 | about 30 s |
| `test_bots.py` | **the moonshot sniper and the many-bot runs**: it buys a new listing once with its stake, ignores everything else, waits for its target, never sells at a loss, counts a bankruptcy, does not count a sale the game refused as a hit; the number of bots per strategy, copies of a fixed rule ending with identical money while random ones differ, turnover reported | 12 | about 40 s |
| `test_deploy.py` | **the deployment files**: the services, the Caddyfile and the environment example agree on ports and keys, every environment variable the code reads is in the example, a visitor cannot fake his address through the web server, the scripts have no syntax errors, and the upload includes every module the server needs and never a save, a ledger or a test | 9 | about 3 s |
| `test_msi50.py` | **the MSI 50**: its name everywhere, exactly 50 members that are the biggest companies and only companies (no moonshots, funds, commodities or indices), the return is the market-value-weighted return of the members, a bigger member moves it more, outsiders cannot move it, the leveraged products follow it, re-ranking at a new game day, a delisted member replaced at once, fewer than 50 companies, the members survive a restart and an old save without them, trading it never moves it and the books balance | 13 | about 5 s |
| `test_no_pools.py` | **stocks hold no tokens**: the books are cash + reserve + fees, the house capital is only the starting reserve and top-ups, a new listing costs the house nothing, and **a save from the old version with seed tokens inside every stock is converted** (the reserve, fees and players' money are unchanged, minted and house capital drop by the retired tokens, the clean save loads the same again, a crash before the first save is harmless, the game keeps balancing afterwards) | 7 | about 15 s |
| `test_no_bots.py` | **no bots**: a new game has no players and none appear, the old bot settings do nothing, no board, profile or stat has a bot field, and **a save from the old version with house-funded bots loads cleanly** (the bots are settled and removed, the tokens balance, the humans are untouched, the clean save loads the same again, a crash before the first save is harmless) | 8 | about 30 s |
| `test_reset.py` | **starting over at Day 1**: everyone on the starting balance, nothing held, the market untouched, identity kept, the books balance, the ledger restarts and still explains every balance, a crash right after a reset loses nothing, the admin endpoint (key, the word RESET, the backup), and `reset_game.py` (it backs up, resets, and refuses while the server runs or without the word) | 15 | about 90 s |
| `stress.py` | a stress tool, not a unit test: many clients hammering one server (below) | | 30 s by default |
| `capacity.py` | a capacity tool: many ordinary players on one server, with the CPU, tick time and bytes per player reported (below) | | 40 s by default |
| `test_slow.py` | slow statistical checks, run only with `RUN_SLOW=1`: a stress run, small edge checks and the paired daily-limit check | 4 | a few minutes |
| `_helpers.py`, `_cdp.py` | shared code: fake-clock engine builder, the isolated server runner, a tiny browser driver | | |

**Your save file is never touched.** Engine tests use an engine with no save file (or a temporary one). Server, stress and browser tests start the server from a temporary copy of the project in a temporary folder and delete it afterwards. Browser tests also launch a headless browser with a temporary profile folder (over 100 MB each); the helper now kills the browser's child processes and deletes that folder when a test ends, and retries the deletion on Windows, where an earlier version left one behind per browser and filled the disk (a full disk makes servers and tests fail in confusing ways). If a run is killed half way, leftover `meme_street_test_*` and `meme_street_browser_*` folders in your temp folder are safe to delete.

### What the engine tests prove
- **Money is conserved** after hundreds of random trades by several players (token drift stays below 0.000001).
- **Trading:** a buy plus sell costs exactly two fees (about 1%); the average entry price is share-weighted and doesn't change when you sell part; a typed amount overrides the percentage; bad amounts (0, negative, NaN, infinity, huge, text) are refused; the 1-second cooldown works; the index price equals the index level.
- **No position limits:** a 100% buy goes through whatever the stock's volatility; a rich player isn't capped by the depth of a stock; a short is limited only by your cash (it is taken out of cash as collateral), with no margin multiple or borrow pool; selling is never blocked.
- **Shorting:** opening and covering works and keeps money conserved; proceeds stay locked (withdrawals blocked); you can't short beyond your margin; covering part keeps the average price; **a margin call triggers exactly when equity falls below the maintenance level** (tested on calm, medium and wild stocks, never before and never late); a gap past the call leaves cash at zero and the house's shortfall is counted; shorts in a bankrupt stock close without negative cash.
- **Borrow fee:** the fee charged over a minute matches the formula to within 2%, goes to the house, and money stays conserved.
- **Dividends:** on the ex-date a long holder is paid, a short holder pays, the price drops by exactly the dividend, and money stays conserved.
- **Earnings:** a quarter is 63 game days = 31.5 hours; first reports are spread across the quarter; the next report is a quarter after the last give or take the jitter (and exactly a quarter with none); the headline names at most three stories and counts the rest; a report declares a dividend that follows the margin and is suspended for a loss.
- **News:** across 3,000 ticks of very busy news (hundreds of headlines) **no headline is ever repeated**; follow-ups (UPDATE) and reversals (REVERSAL) both appear; both branches use **the same strength** with scales 0.8 and 1.2 (so their expected move is zero; this is the check that would have caught the edge bug found in §6.2); the headline-direction scaling cancels exactly for every mood; **the hidden mood is never sent to players** and macro headlines never name the regime; news never targets the index directly.
- **The soft daily limit:** the damping factor is 1.0 at the day's start and 0.5 at the limit; it is identical above and below the open; an up move and a down move are shrunk by exactly the same amount; there is no protection from further falls near the lower limit (the old reflecting wall); a zero cap switches it off; and 60 shocks in a row are held to a few limits instead of running away.
- **Admin data:** every kind of trade (buy, sell, short, cover) is logged with its fee; only the last 100 are kept; a margin call is logged for the player and the house with the house's loss; the house series is sampled every 10 seconds; the overview has the right shape and the return distribution counts every human; player detail is case-insensitive and unknown players return nothing; trade and margin logs survive a restart.
- **Saving:** a full save and load keeps holdings, cost basis, dividends, borrow fees, pending dividends, prices, earnings dates, the headline history and token accounting; saving leaves no temp file behind.
- **The bigger market:** every sector index is the base-weighted return of its members, an ETF the equal-weighted return, a leveraged product exactly `lev × MSI's return` each tick (and a martingale that decays when choppy); **ETFs add dividends back** (total return); derived assets trade and conserve money, are never named in news, and survive a restart.
- **Offerings (there are no splits):** an offering announces, completes and changes only the share count (market cap and EPS follow), never a price, a balance or the books; a split can no longer happen; a save with a pending split or the old leveraged tickers loads and is migrated.
- **Orders:** every kind validates its trigger against the current price and says which side it must be; a fill happens at the market price of that moment (also through a gap); a stop or take-profit is close-only; a bracket cancels its partner; expire, are limited per player and survive a restart and a crash; **an order changes no price and costs nothing extra**.
- **No halts:** after a 50% crash in one stock or a 15% fall across the market, trading and orders carry on at once; no halt news is ever printed; the page data has no halt field.
- **Company events:** each company has one or two events a quarter, spread out and clear of its report; they are on the calendar with only a label; each kind is a fair bet (2,500 firings, mean zero); the next report names them; nothing is announced early.
- **The daily contest:** every entrant gets the same paper balance; a paper trade matches a real twin's cash, shares and fees exactly; margin calls, borrow fees, dividends and bankruptcy payouts work on paper accounts; one entrant's shorts don't use another's borrow room; standings, medals and notices; **two identical worlds, one with six entrants trading furiously in a contest, have identical prices, house, fees and real balances**; a restart keeps the paper accounts; a contest from the old design is dropped.
- **Accounts:** a password checks out and a wrong one doesn't, only a salted hash is stored, sessions expire and end, the old token works only for accounts without a password, reserved names are refused, sign-up and login limits answer 429, the answer is the same for a wrong name and a wrong password, a password change ends the other sessions, an admin reset works, accounts that share an address are flagged without showing it, and all of it survives a restart.
- **Chat moderation:** disguised rude words are masked and ordinary words (`bitcoin`, `class hit`, `Scunthorpe`) are not; the trade-first gate; three different reporters remove a message and mute its author for 10 minutes, an hour, a day; appeals can be lifted or kept; the moderator log records every action.
- **House risk:** every rescue and catalyst is still a fair bet after the thinning; a moonshot catalyst never exceeds the trimmed upside; the reserve is topped up to its floor with the books balanced and **no price or balance different from a run without it**; the top-up survives a restart and a crash; the exposure report is right.
- **Saving and reset:** the chart file is separate, rewritten only when due, and rebuilt when stale or broken; old saves load; a game reset leaves every player on the starting balance with the books balanced and the ledger consistent.
- **Volatility:** calm and stormy stretches cluster; a big move raises the multiplier and it decays over a day or two; it stays between 0.5 and 3; clustering never makes any direction likelier; a crisis raises market-wide volatility; a very strong event (and only a very strong one) loosens the daily limit for 10 minutes; the state survives a restart.
- **Sessions:** the phase follows the real clock (pre-market 0-300 s, regular 300-1500 s, after-hours 1500-1800 s) and zero lengths mean no sessions; nothing is ever refused because of the time of day; noise is 0.35× outside the regular session and 2.5× at the open; **one whole cycle adds up to exactly one normal day of variance**; there is exactly one opening jump per cycle and none without sessions, and it is zero-mean and the right size; **the pre-market move doesn't predict the opening jump**; news, margin calls and borrow fees run in every session; dividends, splits and distress decisions wait for the open; money is conserved across every session; the session info for the page has the phase, the next change and its countdown.
- **News:** every company has a persona that is the same on every start and survives a restart; stories name the company's people, products and cities; no story repeats a headline; a CEO change updates the persona and later stories name the new CEO; buybacks retire shares and pay cash, offerings issue them, EPS follows; two-company stories name both firms and move both (rivals in opposite directions, partners together); **the direction scaling of every story kind cancels, so the expected move stays zero**; money is conserved with all the new stories.
- **Industry-wide shocks:** every kind satisfies `p × up + (1 − p) × (−bad) = 0` and the rarer outcome is the bigger one; over thousands of shocks the average move of every company in the sector, and of the sector as a whole, is zero; a failure moves every company in the sector down (and a good outcome up) by 0.7-1.3 times the sector's size and moves no unrelated stock; **no company ever moves 20% in one shock, the typical move is 5-10% and moves over 15% are rare**; the size setting scales every shock; **the market can be up 3% while a sector collapses**; the sector's index follows it down; moonshots in the sector are hit too; spillovers follow the usual links with no average; the headline names the sector, is never repeated and sits in every member's news log; shocks arrive over time and switch off; money is conserved with them running.
- **The volatility multiplier:** the average over ordinary stocks stays between 0.85 and 1.2 through every pre-market, regular session and after-hours (it used to sink to 0.5 each pre-market).
- **Moonshots:** a new game starts with four, none of them marked NEW; each is tiny, extremely volatile, beta 2.5-4.5, pre-revenue and in an industry that exists; biotech is the commonest kind; new ones list over time up to the maximum and a listing has no first-day pop; **a bankrupt ticker is never reused**; they and the dead survive a restart; the daily limit lets them run (and stays direction-blind); their noise is many times a normal stock's; **they are not pulled back to their reference price**; margin and maintenance rise for them and only for them; shorting is limited by a small borrow pool.
- **Distress:** for every stock type the bankruptcy chance, the payout and the rescue jump satisfy `q × b + (1 − q) × (1 + jump) = 1`; moonshots go bankrupt more often and are wiped out; a forced bankruptcy pays the fraction and delists, a forced rescue multiplies the price by the fair amount; over many draws it is a fair bet.
- **Catalysts:** every moonshot kind is a fair two-outcome bet (`p × up + (1 − p) × loss = 0`) and every ordinary kind a fair three-outcome bet (the three chances add to one, a disaster has a chance of at most 10% and a size of 20% to 70%, the gain works out to a fair bet for every size drawn and stays under 40%); the texts name the company and a disaster has its own headlines; one catalyst moves one stock and prints a headline; the expected move is zero; a fall of 25% or more is the rare case (3% to 12% of ordinary catalysts) and nothing loses more than 95%; moonshots get bigger and more frequent ones; a catalyst makes the stock jumpier afterwards; **money is conserved with catalysts, moonshots and bankruptcies all running**.
- **The ledger:** each event kind is recorded with its deltas; the sum of a player's ledger deltas equals their cash; the house and fee totals equal their ledger sums; realised profit is net of all fees; **a crash loses no trades** (a player who joined after the snapshot is recovered, a second restart replays nothing, a clean shutdown replays nothing, an old snapshot without a ledger position doesn't double-count).
- **Portfolio and history:** realised plus unrealised equals the total profit (less the exit fee), allocation adds to 100%, best/worst come from the ledger, paging walks every event with no gap or repeat, filters ignore unknown kinds, the CSV parses and its cash column sums to the player's cash, players only see their own.
- **The protocol:** a client that applies `init` plus every tick matches a full state through 200 ticks of trades, news and rating changes; slow numbers go out only when changed and everything once a minute; price-derived numbers are not sent; headlines repeat for 5 seconds so a skipped tick loses nothing; no mood, narrative, safety score, token or persona leaks.
- **Social (73 tests):** every achievement's trigger and its negative case (a losing short is not a *Sold high, bought low*; a reversal before you opened doesn't count); quests are the same for everyone, reset at midnight UTC and keep a streak only across consecutive days; the drawdown measures the fall from the peak, ignores deposits and withdrawals and resets each day; profiles are private by default, holdings appear only after the delay and never reveal sizes; follow limits; chat (cleaning, rate limits, repeat blocking, mutes, trade sharing from your own log, reports, deletion); persistence of all of it; an old save loads; and **two identical markets, one with heavy social activity, have identical prices and balanced books**.

### What the server and browser tests prove
- Pages are served with `no-store`; joining rules (taken names, short names, missing field); a bad token is refused.
- The `init` message has everything the page needs (including the margin and borrow fields and the session profile) and **no mood or narrative data**; each `tick` is small, numbered, carries every price and the player's own numbers, and no notices (those come as their own messages); slow data arrives on every fifth tick; `sync` returns a fresh `init`; an achievement notice arrives as its own message.
- **Portfolio, history and CSV** work over HTTP (and refuse a missing or wrong token), players can't read each other's data, lookups are rate limited and recover; `/api/me` and `/api/boards` have the right shape and never contain a token; the daily contest can be joined over HTTP and traded over the socket; profiles are private until the player opts in; follow and unfollow work; the club endpoints are gone and chat is global only.
- **Chat over the wire:** a message is cleaned, reaches everyone, and appears in a late joiner's history; rate limits answer with a reason; a shared trade carries its details; a moderator can delete (everyone's screen updates) and mute (the player is refused), a report appears in the admin view, **three reports remove a message and mute its author and the admin can lift the mute on appeal**.
- **Threads:** ten clients hammering lookups and trades while ticks run, plus admin calls, never make the game late (the slowest tick and the late-tick count come from `/api/admin/overview`).
- Through the real WebSocket: a typed-amount buy, a short, seeing it as a short in the next state, and the cover; a buy far bigger than the old position limit goes through; **history and company requests sent together are both answered** (a bug found while writing these tests); every timeframe answers; unknown stocks return an error; ten kinds of malformed messages don't break the connection; 12 clients all receive updates; admin endpoints need the key; an admin credit shows up; the server log has no traceback through our own code.
- The admin page is served with `no-store` and never contains the key; the overview and player endpoints need the key (403 without it), return the right shape, and show a player's trades.
- **In the browser, the new pages:** search narrows the table (and an empty search shows a message); sorting by price and by ticker orders the rows and shows an arrow; the **Indices & ETFs** chip shows only indices and ETFs; stars fill, the **watchlist** filter shows only starred stocks and **survives a reload**; a **closed** market shows the banner, the CLOSED chip and disabled buttons (market and stock pages); the **portfolio** page shows its figures, positions, allocation bar and curve; the **history** page lists the trades and a deposit, filters work, and **the CSV download produces a file** with the right header; **leaders** lists me once I have traded and says where I am, there is no risk-adjusted board, the market tab's leaderboard has no Score column and my row is highlighted; the **profile** page shows three quests, the achievement grid, the daily contest (joining opens the paper panel, a paper buy and close work) and remembers the privacy setting; **social** shows my chat message, has no clubs tab, and refuses to follow a name that doesn't exist; **a delisted stock opens from the history page** with no trade buttons; **orders can be placed, bracketed and cancelled from the stock page**; **a password sign-up, a mismatch, a weak password, log out, a wrong password, log in and a password change all work**; **my player page** says "This is you" and lists achievements, an unknown player is handled; after `ws.close()` the page **reconnects and keeps updating**, and a sync gives a fresh state.
- **In the browser, the new layout:** the market table shows the company name beside each ticker and no description; there is no VOLATILE or BIG NEWS badge; **only the first row of industries is visible and the arrow unfolds the rest** (and a hidden industry picked from there stays visible); a fictional industry lists its companies; **the holdings page has a Buy and a Sell button on every row and they trade**; the header chip names the session and explains the cycle in local time, there is no activity chart, the amber banner appears in pre-market and the purple one in after-hours, buttons stay enabled in extended hours and a trade goes through.
- In the browser, the original flows: the table has rows; no mood element exists; the buttons are the same elements after several re-renders (so clicks aren't lost); the amount box shorts with the typed amount; Sell becomes "Short" and Buy becomes "Cover" at the right moments; a chip clears the box; a typed buy works; the holdings page shows SHORT and Long rows; the stock page shows the limits line, the short in the position box and the amber average line; the chart survives zooming far out; Cover works; **an EARNINGS headline appears** (using an 18-second quarter); the **admin page** is locked first, refuses a wrong key, then shows its cards, alerts and charts, lists the player and opens their trade log; and there are **no JavaScript errors**.

### The stress test
`python tests/stress.py 40 30` starts an isolated server and runs 40 clients for 30 seconds. Each client keeps sending a random mix of valid and invalid trades (wrong sides, tickers, sizes and amounts), history and company requests, **chat messages (valid, empty, oversized, with links, in the wrong channel), reports, sync requests and calls to the social and portfolio HTTP endpoints**, text that isn't JSON, JSON that isn't an object and 5,000-character messages, and keeps dropping and reconnecting. One more client never reads its socket (a slow client). It reports message counts, the server's tick timings and the average tick size, and **passes only if**: no connection errors, no HTTP 5xx, the game kept ticking (longest gap between updates under 4 seconds, no more than a few late ticks), no traceback passed through our code, and money stayed conserved. A typical run on this machine (40 clients, 25 seconds): about 20,000 trade replies, 1,400 social HTTP calls, 5,500 chat messages, average server tick 14 ms (slowest 56 ms), **no late ticks**, longest gap between updates 1.05 s, drift 5e-10.

### The capacity test
`python tests/capacity.py 200 40 [gateways]` (optionally `CAPACITY_STATE=<path to a save>` to start from a real, full-size game; a third number starts that many gateway processes, §12) starts an isolated server and connects 200 **ordinary** players for 40 seconds: each reads the updates, trades about every 15 seconds, looks at a chart about every 20 and opens a company page about every 30. The clients only count bytes, so the machine is spent on the server. It reports the server's average and slowest tick, the sending time, late ticks, the time the periodic save took, bytes per player per second, and the server process's CPU and memory. The numbers on a full-size game (193 listings, 27 MB save):

| Players | Average tick | Slowest tick* | Late ticks | CPU (share of one core) | Memory | Per player |
|---|---|---|---|---|---|---|
| 100 | 54 ms | 632 ms | 0 | 18% | 206 MB | 10.9 kB/s |
| 200 | 55 ms | 676 ms | 0 | 29% | 219 MB | 10.2 kB/s |
| 400 | 65 ms | 604 ms | 1 | 51% | 251 MB | 9.1 kB/s |

(The same test with gateways, on a later run, is in §12, "Gateways".)

\* The slowest tick is the one that writes the chart file every five minutes (and the first save). Before the chart file was split off the periodic save took 2.1-2.9 s (a 2.4 s freeze every 30 seconds) and the average tick was 270-380 ms; now the save takes about 140 ms. The per-player tick work is small (about 0.1% of a core per player); the fixed cost of a tick is the 54 ms of the engine itself.

### The slow checks (`RUN_SLOW=1`)
- A 20-client, 15-second stress run.
- A small edge check (12 seeds × 1 hour): no strategy may earn a clearly positive mean (t above 3). It is deliberately loose because 12 seeds are noisy.
- A **paired** check on 24 seeds: switching the daily limit off must not make the dip-buying `value` strategy significantly worse (before the soft limit it did, by 2.7%, t −3.2).
- The same with a 2-game-day quarter, so every company reports several times and the earnings and dividend path is covered by the simulator (a normal 2-hour simulation sees almost no reports now that a quarter is 31.5 hours).

The **real** edge check is still `python edge.py 40 2 <a first seed you haven't used>` (about 7 minutes; see §1). Run it before shipping any change to prices, news, fees, limits or dividends.

### Which check when

| You changed... | Run |
|---|---|
| anything in the engine | `python -m unittest discover tests` |
| `server.py` or `index.html` | the same (includes the server and browser tests) |
| prices, news, fees, margin, dividends, earnings, volatility, sessions, orders, company events, indices, moonshots, distress, catalysts, the house reserve | the tests, then `python edge.py 40 2 <fresh seed>`, then `RUN_SLOW=1` slow checks (and a `paired.py` run for the mechanism you touched, §17) |
| anything in `social.py` or `contest.py` | the tests; the "social features never move a price" and "a contest changes nothing outside itself" tests are the ones that matter |
| `accounts.py`, `mailer.py`, sign-in or the admin reset | the tests (`test_accounts.py`, `test_email.py`, `test_reset.py`, the password and email browser tests) |
| `server.py`, `gateway.py`, `wsconn.py`, `launch.py` | the tests, then the server suites again through gateways: `$env:MS_TEST_GATEWAYS = "2"; python -m unittest test_server test_accounts test_email test_reset test_contests test_social test_orders test_browser` (from `tests/`), and `python tests/capacity.py 400 40 2` |
| saving (`save`/`_load_state`) or the server's capacity | `test_save.py`, then `python tests/capacity.py 200 40` with `CAPACITY_STATE` pointing at a copy of a real save |
| the protocol in `server.py` or the page's merge code | the tests, then `python tests/stress.py 40 30` |
| before a release | everything above plus `python tests/stress.py 60 60` |

### A failing test: what it usually means

| Failing test group | Likely cause |
|---|---|
| conservation / "drift" | a trade, fee, dividend or payout moves money without a matching entry on the other side |
| shorting and margin tests | a margin or borrow formula changed |
| distress, catalyst or session fairness tests | an outcome, a chance or a scaling factor changed so the expected move is no longer zero: an edge for traders (§6.6, §6.8, §7.13) |
| "headline printed twice" | uniqueness check bypassed (a path calls `news_log` directly instead of `news()`) |
| follow-up strength / scale | the follow-up branches no longer cancel: an edge for traders (see §6.2) |
| "mood" tests | a field with hidden state was added to the `init` or `tick` message or a headline |
| server tests | a protocol or rate-limit change |
| wire tests | a field was added to the per-tick message that changes every tick (it defeats the deltas), or the page's merge no longer matches the full state |
| ledger tests | a money event was added without a ledger entry, or an entry's deltas don't match what the engine did |
| social "no effect on prices" | a social function touched cash, a price, or the random number stream (it must not draw from `random`) |
| browser tests | the page's HTML ids or text changed (update the test) or a JavaScript error was introduced |

### Adding a test
Use the helpers in `tests/_helpers.py`. A new engine test is a few lines:

```python
from _helpers import make_engine, join, drift

class MyTests(unittest.TestCase):
    def test_something(self):
        e = make_engine(seed=1)          # fresh engine, no save file, fake clock in e.now
        p = join(e, "player1")          # a player with 1,000 MB (the tests' money; the game itself starts people on 10,000)
        ok, msg = e.trade(p, "GOLD", "buy", 0.1)
        self.assertTrue(ok, msg)
        self.assertLess(abs(drift(e)), 1e-6)   # money is conserved
```

Advance time with `advance(e, seconds)` (whole one-second ticks) or move the clock with `e.now += 2` to get past the trade cooldown.

### Running the tests automatically
`.github/workflows/tests.yml` runs `python -m unittest discover tests -v` on every push and pull request if the project is hosted on GitHub. The slow checks and the 40-seed edge check are run by hand.

---

## 17. Latest economy-check results

The checks of §1 and §16 were run on the release that added orders, circuit breakers, company events, the daily contest with paper accounts, password accounts, the stronger chat moderation, the thinner tails and the reserve floor, the one-day days and 10,000 MB start, and the faster save. These are the numbers from 2026-10-03.

### 17.1 The main check: 35 strategies, 40 fresh seeds, 2 hours each (the 36th, `moon_sniper`, is in §17.7)
`python edge.py 40 2 41000` (first seed 41000, never used for tuning; 31 minutes with 6 workers). **Run at the old 0.5% fee and the old shorting rules**; §17.5 repeats it at the current ones. A strategy is flagged only if its mean is positive by more than 2 standard errors. (Every player here starts with 10,000 MB, the new starting balance.)

| Strategy | Mean return | Std error | t | Reading |
|---|---|---|---|---|
| `news_chaser` | −32.6% | 0.9% | −37.5 | pays fees on hundreds of trades |
| `rumor_trader` | −6.4% | 0.9% | −7.2 |  |
| `value` | −2.5% | 2.9% | −0.9 | the dip buyer: no edge |
| `dip_buyer` | −9.2% | 17.7% | −0.5 | buys falling stocks, including falling moonshots |
| `retail` | +0.5% | 1.8% | +0.2 |  |
| `hodl` | +1.4% | 1.6% | +0.9 | holding a basket pays its entry fees and nothing else |
| `short_seller` | −28.1% | 0.5% | −61.9 |  |
| `squeeze_hunter` | −17.3% | 0.9% | −19.4 |  |
| `big_size` | −71.8% | 0.8% | −92.0 | all its cash or margin on every headline (no position limit) |
| `mood_oracle` | −0.1% | 0.1% | −0.6 | **reading the hidden mood directly earns nothing** |
| `gap_long` | −2.7% | 0.2% | −11.1 | holding across the opening jump, long |
| `gap_short` | −2.0% | 0.1% | −17.5 | and short: both lose about the fees |
| `open_follow` | −6.4% | 0.2% | −26.9 | trading in the direction of the opening jump |
| `open_fade` | −6.3% | 0.3% | −20.4 | and against it: neither direction pays |
| `reversal_chaser` | −4.5% | 0.3% | −14.9 |  |
| `update_chaser` | −7.7% | 0.4% | −18.8 |  |
| `partner_chaser` | −10.8% | 0.5% | −21.6 | trades the second company of a two-company story |
| `etf_hodl` | −0.5% | 1.6% | −0.3 |  |
| `bull2_hodl` | +0.1% | 1.6% | +0.1 | `2LMSI`, the 2x long product |
| `bear2_hodl` | −2.2% | 1.6% | −1.3 | `2SMSI`, the 2x short product |
| `bull3_hodl` | +0.6% | 2.5% | +0.2 | `3LMSI`, the 3x long product |
| `bear3_hodl` | −2.9% | 2.5% | −1.2 | `3SMSI`, the 3x short product |
| `vol_chaser` | −41.1% | 1.0% | −42.4 |  |
| `earnings_runup` | −1.9% | 0.4% | −4.8 | buys before a report, sells after: fees |
| `trend_follower` | −3.4% | 0.3% | −10.7 | commodities have no drift (§6.1) |
| `moon_hodl` | +2.7% | 2.9% | +0.9 | buys every new moonshot and holds 20 minutes |
| `moon_short` | −2.5% | 2.0% | −1.3 |  |
| `distress_buyer` | +0.2% | 5.9% | +0.0 | heavy-tailed: see the note below |
| `distress_short` | −0.5% | 0.6% | −0.8 |  |
| `catalyst_follow` | −1.3% | 3.8% | −0.3 |  |
| `catalyst_fade` | −1.5% | 0.4% | −3.8 |  |
| `industry_follow` | −4.8% | 0.7% | −6.8 |  |
| `industry_fade` | −4.9% | 0.7% | −7.1 |  |
| `relation_oracle` | −34.7% | 1.0% | −34.4 | **cheats** by reading the hidden supplier / customer / rival links (§7.15): earns nothing |
| `bracket_trader` | −6.5% | 0.4% | −15.8 | buys a stock and leaves a take-profit and a stop-loss 1% either side (§4): orders are a convenience and cost only the fees |

**No strategy is flagged.** Average fees 102,199 MB, average house P&L +93446 MB, **maximum token drift 1.7e-08** (it is larger than the 1e-9 of the 1,000 MB days only because the sums are ten times bigger: the same floating-point rounding on bigger numbers; the limit is 1e-6). Every strategy that trades a lot loses roughly its fees; the ones that trade little sit near zero, as designed. The new ones behave: `bracket_trader` (orders) loses only the round-trip fees of its many trades, `bull3_hodl` and `bear3_hodl` hold the 3x products with no edge, and `moon_hodl` (+2.7%, t +0.9) is noise on a heavy-tailed bet.

**`distress_buyer` is still a heavy-tailed bet, but a thinner-tailed one.** On this seed set its mean is +0.2% with a standard error of 5.9%, against a standard error of 54% on one earlier seed set, when a rescue was ×9.7 and a few lucky big bets dominated the average. That is the thinning of §6.11 showing up in an actual strategy's results.

### 17.2 Paired comparison: do the new mechanisms pay anyone?
`python paired.py 24 2 46000 strategies=value,hodl,bracket_trader,earnings_runup base: no_events:company_events_per_quarter=0 no_halts:halts_enabled=false no_recap:reserve_recap=false` (21 minutes). The same 24 seeds run with each new mechanism switched off, and the change from the baseline is measured. A mechanism that was paying a strategy would make its result **fall** when switched off. (Circuit breakers have since been removed, so that switch and its row below no longer exist; the result stands as the record that they never changed a price.)

| Switched off | `value` | `hodl` | `bracket_trader` | `earnings_runup` |
|---|---|---|---|---|
| company events | −7.6% (t −1.5) | −4.9% (t −1.3) | −0.2% (t −0.3) | +0.1% (t +0.1) |
| circuit breakers | −5.0% (t −1.3) | −4.6% (t −1.4) | +0.8% (t +1.3) | +0.1% (t +0.1) |
| the reserve top-up | −1.4% (t −0.3) | −2.0% (t −0.6) | +0.3% (t +0.4) | −1.1% (t −1.7) |

Nothing is beyond |t| 2, and no row has a consistent sign. **The reserve top-up is a useful control:** it provably changes no price (a test runs the market with it on and off and gets identical prices and balances), yet its row shows differences of the same size as the others. That is the run-to-run noise of the simulator itself (an engine starts its clock from the real time, which decides where the sessions and day boundaries fall, so two runs started at different moments are not exactly the same market; the order in which players act also varies between runs), which is the yardstick for reading the other two rows: they are noise too. `bracket_trader`, which uses orders, is unchanged by any of them (−7% in every configuration: its fees).

### 17.3 Probes that need a setting to see enough events
Each of these forces the rare mechanism to happen far more often, so a small edge would show.
- **Distress, with the new terms:** `python edge.py 60 2 43000 distress_price_ratio=0.8 _strategies='["distress_buyer","distress_short","hodl","value"]'` (every stock that loses 20% is resolved, so there are thousands of events; 21 minutes): `distress_buyer` +0.4% (t +0.3), `distress_short` −0.3% (t −1.2), `hodl` +7.2% (t +1.3), `value` +0.5%, drift 1.4e-9. Buying or shorting stocks at the distress line earns nothing with the 50% / 60% bankruptcy chances and the ×1.75 / ×2.45 rescues, so the thinner tail of §6.11 is still an exactly fair bet. (The `distress_buyer` standard error is 1.1% here against 5.9% in the main check because the probe is built for a very large number of events.)
- **Moonshots:** `python edge.py 40 2 44000 moonshot_mean_seconds=120 moonshot_max=12 _strategies='["moon_hodl","moon_short","hodl","value"]'` (a new moonshot every two minutes, up to 12 at once; 11 minutes): `moon_hodl` +3.5% (t +0.9), `moon_short` −3.9% (t −2.2, negative), `hodl` −0.9%, drift 1.4e-9. Buying every lottery ticket earns nothing before fees, and shorting every one pays borrow fees and loses.
- **Catalysts, with the trimmed moonshot upside:** `python edge.py 40 2 45000 catalyst_mean_seconds=15 _strategies='["catalyst_follow","catalyst_fade","hodl","value"]'` (a catalyst every 15 seconds on average instead of every 8 minutes; 10 minutes): `catalyst_follow` −3.7% (t −0.4), `catalyst_fade` −12.0% (t −4.5), `hodl` +0.4%, drift 3.7e-9. Trading either side of a catalyst's aftermath loses its fees and nothing more.
- **The opening jump, catalysts (default rate), industry shocks, earnings in their windows, splits:** unchanged since the previous release; see the main check above for the strategies that cover them (`open_follow`, `open_fade`, `gap_*`, `catalyst_*`, `industry_*`, `earnings_runup`). Splits no longer exist.

### 17.4 What the checks found in this release
1. **The save froze the game for 2.4 seconds every 30 seconds** on a full-size game. The capacity test (§16) found it: on the real 27 MB save the periodic save took 2.1-2.9 s while holding the game lock, and the average tick was 270-380 ms. Two causes: `json.dump` to a file uses a slow pure-Python path (4x slower than `json.dumps`), and 23 of the 27 MB were chart candles written every time. The fast encoder plus a separate chart file (§13) brought the save to about 140 ms. A test pins the new behaviour.
2. **A moonshot's tail was the problem, not the house's cushion.** Measured over every 30-minute window of 8 simulated worlds (§6.11): before, a moonshot's best window was +1,495% and one in a thousand beat +1,276%; after, +733% and +583%, with the excess kurtosis falling from 75 to 20. The changes (a gentler rescue, a tighter daily brake, trimmed catalysts) leave every bet exactly fair, which the tests check.
3. **A JavaScript syntax error would have broken the admin page.** An apostrophe in a new alert text ("the house's risk") ended its string early. The browser test of the admin page caught it before it shipped.
4. **Three tests were fragile and are fixed:** one depended on whether the 30 test seconds crossed a minute boundary on the wall clock (the archived chart had one candle or two), one forbade the word "mood" in headlines and an old macro headline ("Risk-off mood sweeps trading floors") contained it (reworded to "sentiment", which is also the cleaner choice given the hidden mood must never be named), and one compared a loaded game with a live one while the test clock ran ahead of the real clock.
5. **Starting money changed ten-fold, and the tests did not.** The game now starts everyone on 10,000 MB, but the test worlds are forced back to 1,000 MB so hundreds of tests keep their numbers; the settings that make the tests' world quiet (no sessions, no moonshots) also turn off the chat gate and the password requirement.
6. **A new module is again a file the isolated test server must be told about** (`contest.py`, `accounts.py`), the same lesson as `relations.py` before.

Earlier findings that still stand: distress was a house-funded free short until its terms were tied together (§6.6); holding news back would have made the open predictable (§6.8); the volatility multiplier needed three fixes (§6.7); ETFs leaked dividends (§9); commodities had a predictable drift (§6.1); the daily limit acted as a reflecting wall (§6.5); follow-ups used unequal strengths (§6.2).

### 17.5 After the fee was cut to 0.1% and shorts were paid for out of cash
A 0.5% fee meant a trade had to gain over 1% just to break even, so the fee was cut to **0.1% per side**, and a short now takes its amount out of cash with no borrow pool or margin multiple (§4). Both change what the edge checks can see: the fee is the cushion that hides a small edge. `python edge.py 40 2 47000` (35 strategies, 26 minutes; the first attempt crashed on a strategy that assumed a short always opens, fixed in `sim.py`):

| Strategy | Mean return | t |
|---|---|---|
| `news_chaser` | -9.32% | -8.1 |
| `rumor_trader` | -0.40% | -0.3 |
| `value` | -0.32% | -0.1 |
| `dip_buyer` | -33.13% | -3.6 |
| `retail` | -0.94% | -0.5 |
| `hodl` | -1.40% | -1.6 |
| `short_seller` | -7.01% | -6.6 |
| `squeeze_hunter` | -11.97% | -3.2 |
| `big_size` | -14.62% | -4.8 |
| `mood_oracle` | +0.24% | +2.0 |
| `gap_long` | -0.58% | -2.5 |
| `gap_short` | -0.74% | -2.5 |
| `open_follow` | -1.05% | -2.8 |
| `open_fade` | -0.54% | -1.4 |
| `reversal_chaser` | -0.69% | -1.6 |
| `update_chaser` | -2.34% | -4.5 |
| `partner_chaser` | -2.86% | -4.8 |
| `etf_hodl` | -0.10% | -0.1 |
| `bull2_hodl` | -0.47% | -0.2 |
| `bear2_hodl` | +0.59% | +0.3 |
| `bull3_hodl` | -0.43% | -0.1 |
| `bear3_hodl` | +1.12% | +0.4 |
| `vol_chaser` | -10.69% | -6.1 |
| `earnings_runup` | -0.07% | -0.2 |
| `trend_follower` | -1.19% | -4.4 |
| `moon_hodl` | +2.89% | +1.1 |
| `moon_short` | -0.60% | -0.1 |
| `distress_buyer` | -6.36% | -1.2 |
| `distress_short` | +6.65% | +1.4 |
| `catalyst_follow` | -6.65% | -1.9 |
| `catalyst_fade` | +2.53% | +0.7 |
| `industry_follow` | -0.93% | -1.3 |
| `industry_fade` | -1.49% | -2.1 |
| `relation_oracle` | -6.14% | -4.9 |
| `bracket_trader` | -2.04% | -5.7 |

Fees fell to an average of 28,320 MB (from 102,199) and the house's average P&L to +33,319 MB. No strategy is flagged, but **`mood_oracle`, the strategy that reads the hidden mood, came out at +0.24% (t +2.0)**, where it had been −0.1% (t −0.6) with the old fee. It was re-run on 60 fresh seeds: **+0.37% (t +3.0)**, and with `mood_tilt=0` −0.05% (t −0.2). An engine-only probe (it trades the index with the mood for two game hours and ignores fees) found +0.9% per two hours (t +4.0) in the one regime a two-hour run sees. The cause was that the hidden mood moved the instant a **rumour** broke, carrying the rumour's *true* direction while the price had only moved by the rumour's expected part; so the mood told you where the rest of the move would go (§7.6). The mood now reacts only when the rumour is confirmed or corrected. After the fix the probe gives +0.05% (t +0.4), and `python edge.py 60 2 49000` on fresh seeds gives `mood_oracle` −0.17% (t −1.3), `rumor_trader` −1.6%, `news_chaser` −6.8%, `short_seller` −8.4% (all fees): the oracle's edge is gone. The old fee had been hiding this for the whole game. It was never available to players (they cannot read the mood), but it is exactly the kind of leak the fee-cushion can mask: **after any fee change, re-run `edge.py` and look at `mood_oracle` and `relation_oracle` first.**

Also found on the way: stocks showing 0.0000 MB were the old splits' fault (§6.9), and a rescued stock that kept falling was never looked at again (§6.6); both fixed.

### 17.6 The rest of the checks
- **Test suite:** 739 tests (735 run by default, 4 slow ones with `RUN_SLOW=1`). The last full run (12 minutes, after the last change) passed completely. Earlier in this release a full run found one race in the gateway (it closed a page before an error message went out; fixed) and, while the study tools were being written, 21 failures caused by `bots.py` replacing the engine's public-state and leaderboard builders when it was imported (it now does that only inside its worker processes); both are fixed. The server, accounts, email, reset, contest, social, order and browser suites were also run through two gateways (`MS_TEST_GATEWAYS=2`) and passed, and the stress test passes both ways. The edge checks were re-run for this release as the many-bot study (§17.7): no price, news or fee code changed, only the accounts, the server, the sharing tools, the leaderboards and the way content files are found.
- **Slow checks (`RUN_SLOW=1`):** the 20-client stress run, the 12-seed edge check, the 2-game-day-quarter edge check and the paired daily-limit check all pass (17 minutes).
- **Stress (`python tests/stress.py 40 30`):** passes: about 22,800 trade replies, 6,000 chat messages and 1,600 social HTTP calls from 40 clients (plus 251 reconnects and malformed input); server tick 37 ms on average (slowest 82 ms); **no late ticks**; longest gap between updates 1.10 s; average tick 7.4 kB with 193 listings; token drift 4.7e-10; no traceback through our code.
- **Capacity (`tests/capacity.py`, §16):** 100, 200 and 400 ordinary players on a full-size game: 18%, 29% and 51% of one core, a 54-65 ms tick, no more than one late tick.
- **Browser:** eight browser tests pass with no JavaScript errors on any page (including the password sign-in, the paper contest panel, the order panel and a delisted stock's page).

**To reproduce:** `python edge.py 40 2 <new seed>` (about 30 minutes with 6 workers), the `paired.py` and probe lines above, `python tests/stress.py 40 30` and `python tests/capacity.py 200 40`. Use a seed that hasn't been used; 100, 1000-1089, 2000-2053, 3000-3161, 9000-9307, 7000, 8000, 9000, 9100, 12000, 20000, 21000, 22000, 23000, 24000, 25000, 26000, 30000, 31000, 32000, 33000, 34000, 35000, 36000, 37000, 38000, 39000, 40000, 41000, 43000, 44000, 45000 and 46000 are taken.

### 17.7 The many-bot study: 100 bots per random strategy, and the moonshot sniper (2026-10-04)
**Why.** To measure two things properly: whether buying every new moonshot and waiting for it to "go up like crazy" can pay (a new strategy, `moon_sniper`), and what the house really earns from what players trade (the question behind "should there be a built-in house edge?").

**What changed in the tools.**
- `moon_sniper` buys each brand-new moonshot within five seconds of its listing, with a fixed share of its free cash (10%, 25% or 50%), and then holds with **no stop-loss and no time limit** until the price is `target` times what it paid (1.5×, 2×, 3×, 5×, 10× or 20×) or the company goes bankrupt. Its 100 bots cover all 18 target and stake combinations, so one run shows which target works best.
- `bots.py` (new, §1) runs many seeds in parallel, with many bots for the strategies that need them, and reports the mean return, the standard error **across seeds**, the share of bots that made money, how much each strategy traded and the result per unit traded. `python bots.py all`, `moon`, `moondense` and `report` (to print saved studies again, from `sim_results/`).
- **Why only six strategies get 100 bots.** A player's trades never move a price, so every bot that follows a fixed rule makes exactly the same trades as its copies and ends with exactly the same money (measured: the spread across 3 copies is 0.000000 for 29 of the 35 older strategies). More copies of those add nothing; more seeds (more markets) are what add information. Only `retail`, `hodl`, `gap_long`, `gap_short`, `bracket_trader` (random choices) and `moon_sniper` (a different target and stake for each bot) differ between copies, so they get 100 each. The standard error is taken across seeds because all bots in one market share its luck (the 100 sniper bots in one market end up within about 56 points of each other, but the markets' averages differ by 65 points).

**A. Every strategy, 54 fresh seeds (2000-2053) x 2 hours.** (`python bots.py all 54 2 2000`, 35 minutes on 18 processes.)

| Strategy | Mean return | Std error | t | Traded (x its money) | Result per unit traded |
|---|---|---|---|---|---|
| `news_chaser` | -8.48% | 1.20% | -7.1 | 77.7 | -0.109% |
| `short_seller` | -8.32% | 1.04% | -8.0 | 83.0 | -0.100% |
| `squeeze_hunter` | -12.06% | 3.44% | -3.5 | 117.2 | -0.103% |
| `big_size` | -20.42% | 3.11% | -6.6 | 164.1 | -0.124% |
| `vol_chaser` | -9.16% | 1.31% | -7.0 | 100.5 | -0.091% |
| `relation_oracle` | -7.32% | 1.06% | -6.9 | 55.8 | -0.131% |
| `bracket_trader` (100 bots) | -1.11% | 0.15% | -7.3 | 14.0 | -0.079% |
| `gap_long` / `gap_short` (100 bots each) | -0.67% / -0.47% | 0.13% / 0.12% | -5.1 / -4.0 | 5.2 / 5.3 | -0.128% / -0.088% |
| `retail` (100 bots) | +1.41% | 1.02% | +1.4 | 1.6 | (too little trading to read) |
| `hodl` (100 bots) | +1.07% | 0.69% | +1.5 | 0.6 | (too little trading to read) |
| `mood_oracle` | -0.16% | 0.15% | -1.1 | 0.8 | |
| `moon_hodl` / `moon_short` | +2.00% / -3.05% | 2.99% / 6.55% | +0.7 / -0.5 | 2.0 / 58.2 | |
| `moon_sniper` (100 bots) | -4.99% | 4.41% | -1.1 | 1.0 | |

(The other strategies are in the saved results: `sim_results/bots_all_2000.json`.) **No strategy shows an edge.** The only positive readings above two standard errors are the buy-and-hold index products (`etf_hodl` +2.7%, t 1.8; `bull2_hodl` +3.1%, t 2.0; `bull3_hodl` +4.8%, t 2.0), and they are one observation, not five: they all measure the same index, with the short products (`bear2_hodl`, `bear3_hodl`) mirror-imaged at -3.4% and -4.9%. To settle it, the engine alone (no traders) was run on **216 fresh seeds x 2 hours** (9000-9107 and 9200-9307): the market index moved **+0.80% +/- 0.63% in the first 108 and -0.81% +/- 0.65% in the second 108, +0.00% +/- 0.45% pooled**, and the equal-weighted average company -0.46% +/- 0.49%. There is no drift: the first reading was luck. Average fees 55,384 MB, average house P&L +75,399 MB, maximum token drift 2.5e-07.

**What the house earns from what players trade.** Pooling the 20 strategies that traded at least 8 times their money, the players' loss per unit of money traded was **0.107% +/- 0.011%**: the 0.1% fee plus a little borrow cost, which is exactly what a fair market with a 0.1% fee should give (§15, "Fees are the business").

**B. The moonshot sniper.** Two kinds of market, both with 100 sniper bots per seed:
- *Normal* (a new moonshot every ~15 minutes): 90 seeds x 6 hours (1000-1089), 10.7 listings per run, about 960 listings.
- *Dense* (`moonshot_mean_seconds` 45 and `moonshot_max` 30, so a new moonshot every 45 seconds and up to 30 at once): 162 seeds x 2 hours (3000-3161), 31 listings per run, about 5,000 listings. This measures the fairness of moonshots about five times more precisely.

| Market | `moon_sniper` mean return | Std error | t | Bots that made money | Median bot | 5th / 95th percentile | Best bot |
|---|---|---|---|---|---|---|---|
| Normal, 90 seeds x 6 h | +9.13% | 8.29% | +1.1 | 40.8% | -15.9% | -90% / +176% | +3,390% |
| Dense, 162 seeds x 2 h | +2.73% | 3.38% | +0.8 | 44.0% | -5.8% | -60% / +87% | +572% |

By target (dense market, 162 seeds; the normal market gives the same picture with more bankruptcies):

| Target | Mean return | t | Median bot | Bots that made money | Positions that reached it | Positions lost to bankruptcy |
|---|---|---|---|---|---|---|
| 1.5x | +2.08% | +0.8 | -1.2% | 48.8% | 43.7% | 10.9% |
| 2x | +2.39% | +0.8 | -1.3% | 48.4% | 24.3% | 12.5% |
| 3x | +0.95% | +0.3 | -7.5% | 42.2% | 10.2% | 13.6% |
| 5x | +2.38% | +0.6 | -10.7% | 42.0% | 3.2% | 14.0% |
| 10x | +4.96% | +1.0 | -11.1% | 40.5% | 0.7% | 14.3% |
| 20x | +4.19% | +0.9 | -11.1% | 40.9% | 0.1% | 14.3% |

In the normal 6-hour market (36 seeds with exact counters), a position that waited for 10x reached it 4.6% of the time and was lost to bankruptcy 44% of the time; for 20x, 2.2% and 44%.

**What it says.**
1. **There is no profitable way to snipe moonshots, and no best target.** The average is statistically zero (+2.7% +/- 3.4%; the fee drag expected from this much trading is only about -0.2%), no target and no stake is significantly better than another (every t is below 1.1), and the strategy that holds a new moonshot for exactly 20 minutes (`moon_hodl`) is, if anything, a little negative (-3.8% +/- 1.7% over the 162 dense seeds). This is what moonshots are built to be: fair bets.
2. **But it is a lottery with a long right tail.** Most bots lose: only 41% to 44% make money, the median bot is down 6% to 16%, and in the normal market one in four loses more than half its money while one in ten gains over 100%. The mean sits above the median because a few bots win very big.
3. **"Wait until they go up like crazy" almost never happens, and waiting is expensive.** Of the positions that waited for 10x, under 1% got there in two hours and under 5% in six, while over 40% ended in bankruptcy in six hours. Taking a small profit (1.5x to 2x) beats waiting on the typical bot (median -1% against -11%), though not on the average.
4. **The house pays for the tail.** With 100 sniper bots (1,000,000 MB of capital), the house's profit and loss per market has an average of -84,000 MB (normal, 6 h) or -26,000 MB (dense, 2 h), which is zero within the noise, but a **standard deviation of 974,000 MB and 432,000 MB**, and a worst market of **-4,443,000 MB** and **-1,690,000 MB**: more than the bots' whole capital, because a bot that wins on one listing reinvests in the next. The fees in the same markets were only about 11,000 and 1,900 MB. See "Is a built-in house edge a good idea?" in §15.

**C. Bugs found on the way (both fixed).**
- **The game read its own chart file as a content pack.** Every `.json` file in the project folder is read as a content pack, and the rule excluded only the save file (`state.json`), not `state.charts.json` (tens of MB, rewritten every five minutes). In a running game each chart save therefore looked like a content change, so the game re-read every pack including that 26 MB file (about a second, in the tick), and a read could fail with "Permission denied" while the file was being replaced (this is what stopped the first attempt at this study). Both files are now excluded, and four tests cover it. Restart a server that was started before this change to get the fix.
- The first version of the sniper's counters counted a refused sale (a circuit breaker, a cooldown) as a hit on every tick; the returns were never affected. (Those studies were run while trading halts still existed; most of the refused sales in them were halts. Halts were removed afterwards and an 18-seed re-run of the dense market (seeds 4000-4017) gave the same picture: the sniper +6.1% +/- 13.8%, no refused sales, token drift 4.5e-08.) Fixed and tested; the hit and bankruptcy shares above come from runs with the fixed counters.

### 17.8 After the catalysts were reined in (2026-10-05)
Ordinary companies' catalysts became three-outcome bets with a rare disaster (§7.13), so every strategy was checked again: `python bots.py all 54 2 6000` (54 fresh seeds x 2 hours, 100 bots for each random strategy, 24 minutes on 18 processes).

- **No strategy shows an edge.** The best reading is `value` at +6.35% (t +1.1); the index products are +1.4% to +2.3% (`bull2_hodl`, `bull3_hodl`, t +0.8 and +0.9) and -0.4% (`etf_hodl`), the opposite of the first study's pattern, which is what noise looks like.
- **The strategies that trade the catalysts' aftermath earn nothing:** `catalyst_follow` -1.34% (t -0.4) and `catalyst_fade` -2.09% (t -0.5), with the fee drag expected from their turnover of about 10 and 24 times their money.
- **`mood_oracle`** (reads the hidden mood) -0.30% (t -1.9); **`relation_oracle`** (reads the hidden company links) -5.03% (t -5.3), both losing their fees.
- **The result per unit traded** stays at about -0.1% for the strategies that trade the most (`news_chaser` -0.092%, `short_seller` -0.100%, `big_size` -0.100%, `bracket_trader` -0.095%, `vol_chaser` -0.099%): the 0.1% fee and nothing else.
- **The house:** average fees 57,520 MB, average house P&L +15,947 MB, maximum token drift 2.2e-07.
- The distribution of moves is in §7.13 (a fall of 40% or more in an ordinary company went from about one an hour to one every five hours).

### 17.9 The big overnight check on the MSI 50 and everything else (2026-10-06)
After the MSI 50 (§9) went in, the first 72-market edge checks showed a few readings above two standard errors (`catalyst_follow` +12%, t +2.6; `moon_hodl` +7.6%, t +2.1), so three much bigger studies were run. All results are in `sim_results/`.

**1. Every strategy, 300 fresh markets x 2 hours** (`python bots.py all 300 2 70000`, in two files because a background command may run only two hours: `bots_all_70000.json` has 182 markets and `bots_all_70182.json` has 118; the combined table is `bots_all_300_seeds_report.txt`, made with `python bots.py report all <both files>`; 100 bots for every random strategy, one copy of each fixed-rule strategy). **No strategy has an edge.**
- The only readings above two standard errors that are positive: `bear2_hodl` +1.82% (t +2.0) and `bear3_hodl` +2.77% (t +2.0). They are the mirror image of `bull2_hodl` -2.20% (t -2.4), `bull3_hodl` -3.18% (t -2.3) and `etf_hodl` -1.36% (t -2.3): one fact, that the index happened to fall in these markets, counted five times (the products are all the same market). Test 3 shows the index does not drift.
- `catalyst_follow` fell from t +2.6 to **+0.79% (t +0.4)** with the bigger sample, `catalyst_fade` is -3.03% (t -1.8), `moon_hodl` +2.25% (t +1.6) and `moon_sniper` (100 bots) -0.94% (t -0.4). The earlier readings were luck: `moon_hodl` has also been -3.8% (t -2.2) in the dense-moonshot study (§17.7), so its sign flips from study to study.
- The strategies that trade a lot all lose **about -0.10% per unit traded: the fee and nothing else** (`news_chaser` -0.105%, `short_seller` -0.102%, `vol_chaser` -0.110%, `bracket_trader` -0.110%, `trend_follower` -0.089%). `mood_oracle` -0.05% (t -0.6) and `relation_oracle` -5.77% (t -13.7), which loses its fees, show the hidden mood and hidden company links are not a leak. House: average fees 56,713 MB, average house P&L +75,588 MB, maximum token drift 2.2e-07.

**2. After a catalyst-sized move** (`python catalyst_probe.py 200 2 60000`, 200 markets, `catalyst_probe_60000.txt`). Every time a company's price was 25% above or below its price two minutes earlier, the probe recorded its next five minutes (bankruptcies valued at the price holders are paid):

| After a 25%+ move in 2 minutes | events | next 5 minutes | t |
|---|---|---|---|
| moonshot, up | 4,928 | -0.11% | -0.3 |
| moonshot, down | 3,313 | -0.65% | -0.9 |
| ordinary company, up | 128 | +0.28% | +0.7 |
| ordinary company, down | 124 | +0.05% | +0.2 |

All are zero within the error: **there is nothing to gain by following or fading a big move**. (The first version of the probe showed moonshots rising by +1.4% to +3.2% afterwards, t +3.4 to +5.5. That was the probe's own bug: a bankrupt moonshot (-97%) was valued at its price from the tick before, while a rescued one (+145%) was counted in full. It now values a delisted stock at the final price, `archive[ticker]["final_price"]`.)

**3. Does the index drift?** (`python index_probe.py 250 2 80000`, 250 markets of 2 hours with no traders, `index_probe_80000.txt`):

| series | mean return in 2 h | std err | t |
|---|---|---|---|
| MSI 50 | +0.41% | 0.57% | +0.7 |
| the average ordinary company | +0.09% | 0.45% | +0.2 |
| `AIFX` ETF | +0.60% | 0.75% | +0.8 |
| 2x Long (`2LMSI`) | +0.80% | 1.17% | +0.7 |
| 2x Short (`2SMSI`) | -0.94% | 1.09% | -0.9 |

No drift, so the MSI 50's weighting and re-ranking give nobody an edge. The negative index readings in the strategy table were luck.

**How to read these tables.** A study measures 36 strategies, so one or two will show |t| of 2 by chance, and strategies that hold the same assets (the index products; `moon_hodl` and `moon_sniper`) share one market and are not independent evidence. A real edge shows up the same way in every sample and grows with the sample (an edge of +1% with a standard error of 0.5% would have a t of +5 or more with 300 markets). Moonshot returns are extremely skewed (a few huge winners, a median near zero), so a t-statistic on them is looser than it looks; that is why the dense-moonshot study (§17.7) is the better judge, and it has the opposite sign.

---

## Keeping the docs current

After every code or content change, update this file so it describes what the code does now, and tick or adjust the matching items in `ROADMAP.md`. Check `ROADMAP.md` before starting any new work.
