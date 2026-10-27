# How Meme Street works

This document explains the whole system: what each file does, how prices and trading work, how money flows, how news, earnings and ratings are generated, how the social features and the server protocol work, and what to watch out for. Numbers quoted are the current defaults from the content packs (in `content/`: `base.json`, `expansion.json`, `pack_growth.json`, `pack_fiction.json`) and the constants at the top of `game/engine.py`. File names without a folder are in `game/` (code), `web/` (pages), `content/` (packs) or `tools/` (scripts): §1, "Where things are".

**A guide to the sections.** §1 running it · §2 the files · §3 time · §4 trading · §5 where money lives · §6 how prices move (including volatility, the trading sessions, moonshots and how the tails are kept thin) · §7 news, catalysts, industry-wide shocks, company stories and ratings · §8 listings · §9 indices, ETFs and leveraged products · §10 players, accounts, days, achievements, the daily contest and chat · §11 the web pages · §12 the server, its protocol and gateways (more than one process) · §13 saving and the crash-proof ledger · §14 settings · §15 things to know · §16 tests · §17 the latest economy-check results.

Keep this file in step with the code: update it after every change (see "Keeping the docs current" at the end).

> **Change of direction (2026-10-13), and what is built.** The shop, the new price model, the macro calendar, the chart tools and learning now exist (§6A, §10.9, §10.10, §11). The paragraph below is the original note.
>
> **Change of direction (2026-10-13).** Meme Street is becoming a site for **learning to trade**: everyone starts with 1,000 MB, more MB is bought in packages (1,000 to 100,000 MB since 2026-10-14) and never cashed out, challenges award free MB, and the market is being rebuilt to drift slowly upwards with regimes, scheduled economic data (interest rates, inflation, jobs) and technical structure (support and resistance that holds or breaks). `ROADMAP.md` has the plan. **This file still describes the code as it is today**, which was built for the old plan (a real-money game in which every mechanism is a fair bet and nobody can have an edge). Sections that only matter for that old plan (the house's capital risk, the house-edge discussion in section 15, the fee-based revenue model in section 17.10) say so where they start; they will change or go as the new tracks are built.

---

## 1. Running it

### Where things are
The project is split into folders by what things are. `game/paths.py` knows where each one is, so nothing depends on the
folder the game is started from.

| Folder | What is in it |
|---|---|
| `game/` | The Python code the server runs (§2) |
| `web/` | The pages: `index.html` (the whole player site) and its chart, `chart.js`, `admin.html` (`/admin`), `about.html` (`/about`), `shop_pay.html` (the pretend checkout in test mode, `/shop/pay`) |
| `content/` | The content packs: every `.json` file here is read at start and reloaded within a second when it changes (settings, sectors, companies, news templates, lessons) |
| `tools/` | Scripts you run by hand: `launch.py`, `reset_game.py`, `share.py`, `chart_check.py`, `realism.py` |
| `data/` | What the running game writes, **never in git**: the save (`state.json`, `state.charts.json`), the ledger (`ledger.db`), `backups/`, this computer's admin key (`admin_key.txt`), the last share link and simulation results (`sim_results/`) |
| `docs/` | This guide, `ROADMAP.md` (the plan), `MARKET_REALISM.md` (the research behind the charts) and `COUNCIL.md` (verdicts from `/council`) |
| `deploy/` | Putting the game on a rented server (below) |
| `tests/` | The test suite (§16) |
| `brand/` | The logo and the header image (an old screenshot and promo video were removed on 2026-10-20; they are in the git history) |

The top folder only holds `start_game.ps1` (start the game), `README.md`, `requirements.txt` and `requirements-lock.txt`.

### Start the server
From the project folder, in PowerShell:

```powershell
cd "D:\stock_market_sim"                         # (the project has lived on the D: drive since 2026-10-10)
$env:ADMIN_KEY = "pick-a-long-random-string"     # optional: enables /api/admin/*
.venv\Scripts\python.exe -m uvicorn server:app --app-dir game --host 127.0.0.1 --port 8000
```

(`--app-dir game` tells uvicorn where the code is. Starting it from inside `game\` without that option works as well.)

Or just run `powershell -File D:\stock_market_sim\start_game.ps1`: it does the same, keeps the admin key in `data\admin_key.txt` (made on the first run, never sent to git) and runs the shop in **test mode** (`PAYMENTS=test`, a pretend checkout, §10.9). `-Fresh` starts a new game (the old save, charts and ledger are moved to `data\backups\before_fresh_<time>\`; move them back to return to it); `-Payments off` closes the shop (do that before sharing the game with `tools\share.py`, or anyone could give themselves MB). `requirements-lock.txt` lists the exact package versions the game was tested with; `pip install -r requirements-lock.txt` rebuilds the environment identically.

Then open:
- **http://127.0.0.1:8000** for the market. Open a second browser (or a private window) to play as a second player.
- **http://127.0.0.1:8000/stock/NVXA** for a stock's page (any ticker works, including `MSI` for the index).
- **http://127.0.0.1:8000/holdings** for your holdings, **/portfolio** for your equity curve and profit breakdown, **/history** for every trade and payment (with a CSV download), **/leaders** for the two leaderboards, **/social** for chat and following, **/profile** for your quests, the daily contest, achievements and your account, and **/player/NAME** for another trader's profile.
- **/learn** for the course and the chart tests on real charts, **/calendar** for the economic calendar and **/shop** for MB packages, Pro and Expert (§10.9, §10.10, §6A).
- **http://127.0.0.1:8000/admin** for the admin dashboard (needs `ADMIN_KEY`).
- **http://127.0.0.1:8000/docs** for FastAPI's automatic API explorer.

Alternatives:
- **VS Code:** Terminal → Run Task → "Meme Street Profile Engine". It runs the same command on port **8002**, so open http://127.0.0.1:8002.
- **While editing code:** add `--reload` so the server restarts when a `.py` file changes. Content `.json` files are hot-reloaded by the engine itself without a restart.

Stop the server with Ctrl+C. It saves `data\state.json` on a clean shutdown and closes the ledger (`data\ledger.db`, §13). If the server is killed or crashes instead, nothing is lost: the next start loads the last snapshot and replays the ledger (you'll see "recovered N ledger events" in the log).

**Run only one game server at a time.** Every game server instance reads and writes the same `data\state.json` and `data\ledger.db`, so two servers overwrite each other's saves. (Gateways, §12, hold no game and never touch those files; you can run as many as you like next to one game server.) A server also keeps running whatever code it started with: after changing code, stop it and start it again, then hard-refresh the browser (the page is served with `Cache-Control: no-store`, but an already-open tab keeps its old script).

### Letting other people play (sharing it from your own computer)
**In plain English:** the game listens only on your own computer (`127.0.0.1`), so `http://127.0.0.1:8000` works for you and nobody else. To give friends or testers a link while the game keeps running on your PC, use a free Cloudflare **quick tunnel**. Your computer makes an outgoing connection to Cloudflare, and Cloudflare gives you a public `https://….trycloudflare.com` address that forwards to your game. Nothing is opened on your router, your home address is not revealed, and the link works from phones and from other countries.

1. **Start the game** the way you always do. Give it a long secret `ADMIN_KEY` (the admin page is on the same address, so anyone with the link can open `/admin`, though without the key it shows nothing), or none at all (no key switches the admin API off).
2. **First time only:** `python tools\share.py --install`. This downloads Cloudflare's small tunnel program (`cloudflared.exe`) from Cloudflare's own release page on GitHub into the `tools\` folder (git ignores it). (Or install it yourself: `winget install --id Cloudflare.cloudflared`.)
3. **Every time:** in a second terminal, `python tools\share.py`. After a few seconds it prints a box like `https://quiet-river-1234.trycloudflare.com` (and saves it in `data\share_url.txt`). Send that link to people. It works as long as that window stays open, your computer is awake (turn off sleep) and the game is running. Ctrl+C stops sharing; the game itself is not affected.

What to expect:
- **The link changes every time** you run `share.py`. A permanent address needs a free Cloudflare account and a domain name (a "named tunnel"); that is a hosting job for later.
- **Your PC does the work.** A few dozen testers is fine on a normal computer (§12, Capacity); the tunnel is free and meant for testing, with no uptime promise.
- **Each visitor counts separately.** Everyone arrives through the tunnel from your own computer, so the game reads each visitor's real address from the tunnel's `CF-Connecting-IP` header. It only believes that header when the request really comes from this computer (or `trust_proxy` is on, §14), otherwise anyone could fake it. Without that, the "5 sign-ups per address per hour" limit would have applied to all your visitors together (§10.6).
- **People on the same Wi-Fi** do not need the tunnel: start the game with `--host 0.0.0.0` (`python tools\launch.py --host 0.0.0.0`, or `python -m uvicorn server:app --app-dir game --host 0.0.0.0 --port 8000`), let Python through the Windows firewall when it asks, and open `http://<your PC's address>:8000`. `python tools\share.py --lan` prints that address.
- `share.py` never starts the game and never reads or writes your save; it only checks that something is listening on port 8000 and then starts the tunnel.

### Running it on a real server with its own web address
**In plain English:** the `deploy/` folder takes the game from your computer to a rented server that is on all the time, with a domain name and https. `deploy/DEPLOY.md` is the step-by-step guide (buy a name, rent an Ubuntu 24.04 server, point the name at it, run two commands). On the server the game lives in `/opt/memestreet` with the same folders (its save in `/opt/memestreet/data`). What is in the folder:

| File | What it does |
|---|---|
| `DEPLOY.md` | The guide: costs, choosing a name, the server, DNS, setup, moving your saved game, email, protecting the admin page, updating, backups and restoring, monitoring, troubleshooting |
| `upload.ps1` | Run on your Windows computer: sends the code (`game/`, `web/`, `content/`, `tools/`, the logo and `deploy/`; never `data/`) to the server and runs `update_server.sh` there; with `-Restart` the game restarts; `-WithGame` moves your saved game once; `-DryRun` shows what would be sent |
| `update_server.sh` | Run on the server by `upload.ps1` after every upload: installs changed service files and the backup job, and moves a game from the old one-folder layout (before October 2026) into `data/` (stopping the game for that moment and taking a backup first) |
| `pull_backups.ps1` | Run on your Windows computer: copies the newest server backups (default the last four, one day) into `D:\meme_street_backups`, checks each arrived whole (a `.complete` marker), and changes nothing on the server (`deploy/DEPLOY.md`, Backups). |
| `set_stripe.ps1` | Run on your Windows computer: asks for the Stripe key and the webhook's signing secret (typed hidden; test keys refused, since anyone could pay with Stripe's test card), writes `PAYMENTS=stripe`, them and `SITE_URL` into the server's `/etc/memestreet.env` over ssh (never in a command line), restarts the game and asks it (the admin shop endpoint, on the server) whether the shop is taking payments. `deploy/DEPLOY.md` step 5b has the Stripe dashboard steps (since 2026-10-24). |
| `set_mail.ps1` | Run on your Windows computer: asks for the SMTP user, key (typed hidden) and from-address, writes them into the server's `/etc/memestreet.env` over ssh (the key never in a command line), restarts the game and checks the game now says mail is ready. |
| `setup_server.sh` | Run once on the server as root: installs Python and Caddy, makes the game's user and environment, writes `/etc/memestreet.env` with random keys, installs the services, the firewall (only ssh, http and https), automatic security updates and the backup job |
| `memestreet.service`, `memestreet-gateway.service` | systemd services: the game server (port 8001, only reachable on the machine, saves when told to stop) and the gateways (port 8000); both run in `/opt/memestreet/game`, restart by themselves and start on boot |
| `Caddyfile` | The web server in front: gets and renews the https certificate, redirects `www`, sends traffic to the gateways, adds security headers, and has an optional password block for `/admin` |
| `memestreet.env.example` | The settings kept in `/etc/memestreet.env`: the admin key, the gateway key, how many gateways, the mail service |
| `backup.sh` | Every six hours: copies the save, the charts and a consistent copy of the ledger from `/opt/memestreet/data` to `/var/backups/memestreet`, keeping two weeks |

How a visitor's address stays honest behind Caddy: the gateway believes `X-Forwarded-For` and `CF-Connecting-IP` from the machine itself (§10.6), so Caddy removes any `CF-Connecting-IP` the visitor sent and replaces `X-Forwarded-For` with the connection's real address. `tests/test_deploy.py` checks that, that the services and the Caddyfile agree on ports, that every module the server imports is in the upload, that the update script never deletes a save, and that the scripts have no syntax errors.

### Starting it with `tools\launch.py`, and more than one process
`python tools\launch.py` starts the game in one process on port 8000, the same as the `uvicorn` command above. `python tools\launch.py --gateways 4` starts the **game server** (on `127.0.0.1:8001`, only this computer can reach it) plus **four gateway processes** that listen on port 8000 and hold the players' connections. Players cannot tell the difference. You only need it for a larger crowd (hundreds of players); how it works and what it buys is in §12 ("Gateways"). Options: `--host`, `--port`, `--core-port`. Stop it with Ctrl+C (gateways stop first, then the game, which saves on the way out).

**To start the game over at Day 1**, open the admin page (`/admin`), go to the **System** tab's *Danger zone*, type `RESET` and press the button. Every player goes back to the starting balance (`signup_bonus`, 1,000 MB), positions are closed at the market price (no fees), orders are cancelled, and the trade history, medals and achievements are cleared. Prices, charts, listings, accounts and passwords stay. **The admin page starts again too**: no fees collected, the house reserve back at its capital, every player's MB-by-source back to just the starting balance (so the Total MB card shows only the new starting MB), the Total MB and P&L charts empty, the quest ladder, challenges, achievements and trade counts cleared, and the Shop panel counting from the reset (paid orders from before are kept as records, can still be refunded by id, and are summed on one line). Lessons passed stay. The old save and ledger are first copied into a `data/backups/reset-<date>` folder, so nothing is lost; every connected page reconnects by itself. (`Engine.reset_to_day_one`, §10.) **Without the admin page** (no `ADMIN_KEY` set, or you prefer the terminal): stop the server, run `python tools\reset_game.py` (it asks you to type `RESET`; `--yes` skips the question) and start the server again. It makes the same backup first and refuses to run while something is listening on port 8000, because a running server would overwrite the result a few seconds later.

**To throw everything away** (a brand-new market, no accounts), stop the server, delete `state.json`, `state.charts.json` **and** `ledger.db` (plus `ledger.db-wal` and `ledger.db-shm` if they exist) from `data\`, and start it again. (Deleting only `state.json` would make the server replay the old ledger into the new game.) `start_game.ps1 -Fresh` does this for you and keeps the old files.

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

See §16 for what the tests cover and when to run which one. The tests never touch `data\`: a test that needs a running server copies the game into a temporary folder with the same layout and starts it there (`copy_project` in `tests/_helpers.py`).

**Lint and types** (ROADMAP E13; the same commands run on every push, §16): install the two tools once with `.venv\Scripts\python.exe -m pip install ruff==0.6.9 mypy==1.11.2`, then

```powershell
.venv\Scripts\python.exe -m ruff check --select E,F,W --ignore E501,E731,E741,E401 game tools tests
.venv\Scripts\python.exe -m mypy game tools\realism.py tools\pricing_model.py --ignore-missing-imports
```

Ruff checks for errors, warnings and the pyflakes rules (unused names and imports, undefined names); long lines, lambdas given a name, `l` for a candle's low and several imports on one line are the house style. mypy is a light pass: most functions have no type annotations, so it checks what it can see.

### Market checks
```powershell
.venv\Scripts\python.exe tools\chart_check.py 12 7            # the real engine's charts against the facts of real prices (12 game days, seed 7; about 5 minutes)
.venv\Scripts\python.exe tools\chart_check.py 12 7 --cached   # re-read the last run of that length and seed (cached in data\sim_results\)
.venv\Scripts\python.exe tools\realism.py 2 3 40 801          # the price model alone: long run, levels, and no free money (2 game years, 3 markets, 40 stocks)
```
`MARKET_REALISM.md` (in `docs/`) explains both, the research behind their targets, and the latest results (§6A.9).

```powershell
.venv\Scripts\python.exe tools\pricing_model.py                 # what 1,000 sign-ups might bring in, and which assumption matters most (ROADMAP M7)
```

**Removed on 2026-10-13.** The old market had to give nobody an edge, and a set of tools checked that: `sim.py` (108
scripted traders following 36 strategies on a fake clock), `bots.py` (many-bot studies), `edge.py` (the same on many
seeds), `paired.py` (the same seeds under two settings), `probe.py` (where an edge comes from), `tune.py` (comparing
settings) and two probes. With the learn-to-trade market the rule is "realism you can learn from, but no free money"
(ROADMAP.md section 1), checked by the two tools above, so they were removed (they are in the git history). Their
last results are kept in §17 as history.

---

## 2. The pieces

### The code (`game/`)

| File | Role |
|---|---|
| `engine.py` | The whole game: prices, trading, orders, volatility, the trading sessions, moonshots, catalysts, industry shocks, scheduled company events, news and narrative, company stories, earnings, offerings, bank ratings, indices and ETFs, days, accounting, save/load and crash recovery. Has no web code. |
| `market_model.py` | The learn-to-trade price model: drift, market phases, trends, ranges and breakouts, support and resistance (with the daily chart's levels), chart patterns, stochastic volatility, volume, the economy and its calendar (§6A). |
| `patterns.py` | Finds chart patterns in candles the way a trader would (double tops, head and shoulders, triangles, flags, wedges, channels, cup and handle) and follows each forward like a trade (§6A.10). Used by `realism.py`; ready for a screener. |
| `options.py` | Options on the stocks, for everyone: the chain of calls and puts (Black-Scholes on the stock's own volatility, plus a premium and a spread), buying, selling back and settling at expiry (§4, "Options"). A mixin of the engine. |
| `bots.py` | Trading bots and backtests (Expert): the safe rule language (parsed, never `eval`), the indicators, the news score, running a player's bots on each finished candle, and the backtest (§10.12). A mixin of the engine. |
| `daily.py` | The Daily Chart: the day's two-minute chart made by the price model, each player's game (paper money) and the day's board (§10.13). A mixin of the engine. |
| `history.py` | The long price history: game-day candles for many game years and one-minute candles for a few real days, in SQLite files next to the save (§11, §13). |
| `errortrack.py` | A small error tracker: every error the server logs, grouped by where it was raised and counted, for the admin page (§12). |
| `economy.py`, `payments.py` | The shop: MB packages, Pro and Expert, age rules, spending limits, the free restart, and the payment providers (off, test, Stripe) (§10.9). |
| `learning.py` | The Learn page's course (read from `content/learn-*.md`), its chart tests, and the challenges (switched off) (§10.10). |
| `drills.py` | The chart tests: finds a moment of each kind on real candles (a level test, a breakout, a pattern...) and reads the right answer from the candles that follow (§10.10). |
| `ladder.py` | The quest ladder: 30 one-off quests in Bronze, Silver, Gold and Diamond tiers that pay MB once, and the titles and name colours Diamond quests unlock (§10.11). |
| `social.py` | Everything built on top of the players: achievements, daily quests, the daily contest, the day and all-time boards, public profiles, following, and the moderated chat (word filter, reports, auto-mutes, appeals). A mixin of the engine. It never touches real cash or prices (§10). |
| `contest.py` | The paper-money accounts of the daily contest (§10.4): a `Sandbox` that lets the engine's own trading code run against a throwaway house, so a contest trade follows the real rules exactly but can never touch the real economy. |
| `accounts.py` | Passwords (scrypt hashes), login sessions, name rules, the sign-up and login limiters, the list of accounts that share an address, **email addresses** (verification codes, one account per address, recovering a password) (§10.6). A mixin of the engine. |
| `mailer.py` | Sends the verification and password-reset emails over any SMTP service, on a background thread, with retries; with no mail server set it is in *console mode* and keeps the message for the admin page (§10.6). |
| `relations.py` | The hidden links between companies: who supplies whom, who buys from whom, who competes (§7.15). Hand-written for the companies that ship with the game, sector rules for newcomers. |
| `newsgen.py` | The headline writer and the generators: names, products, cities, synonyms, slot filling, the company-story catalogue, the two-company stories (§7.12), the rare catalyst stories (§7.13), the industry-wide shock stories (§7.14) and the moonshot company generator (§6.10). |
| `ledger.py` | The append-only SQLite log of every money event and each player's equity curve (§13). Created as `data/ledger.db`. Can copy itself (`backup`) and be emptied (`clear`) for a game reset. |
| `server.py` | FastAPI app, the **game server**. Runs the engine in worker threads behind one lock, sends each browser one `init` and then a small `tick` every second over a WebSocket, handles the HTTP endpoints, and (when started with a `CORE_KEY`) accepts gateways (§12). |
| `gateway.py` | A **gateway**: a process that holds players' websockets and passes everything else to the game server over one link. Run several to spread the work of sending updates over several processor cores (§12, "Gateways"). Holds no game state; never imports `server.py`. |
| `wsconn.py`, `netutil.py`, `pages.py` | Small pieces shared by the game server and the gateway: one websocket with its writer queue, working out a caller's real address and the renamed-product table, and the page routes (`/`, `/admin`, `/stock/…`, the logo), which serve the files in `web/` and `brand/`. |
| `paths.py` | Where every folder is (`web/`, `content/`, `data/`, ...), worked out from its own location. Everything that opens a project file goes through it. |

### The pages (`web/`)

| File | Role |
|---|---|
| `index.html` | The front end: plain HTML, CSS and JS, no build step. One file serves every player page: market, stock (with its Options tab), holdings, portfolio, history, leaders, social, profile and player, learn, calendar, bots, shop, and the sign-in box (§11). |
| `chart.js` | The stock page's chart, loaded by `index.html` (served at `/js/chart.js`): the candles, the crosshair, your trades on the chart, the indicators and their settings, the drawing tools, the chart's size and the position-size box (ROADMAP TA-F2). It shares the page's globals, so the two work like one script; the page connects to the game only once both have loaded. |
| `bots.js` | The Bots page (served at `/js/bots.js`): the list of a player's bots, the editor with its templates, and the backtest with its equity curve (§10.12). Shares the page's globals like `chart.js`. |
| `learn.js` | The Learn page (served at `/js/learn.js`): the course, a lesson, and the chart tests with their chart (§10.10). |
| `daily.js` | The Daily page (served at `/js/daily.js`): the start screen, the chart painting one candle a second, the buy and sell buttons, the result and the board (§10.13). |
| `admin.html` | The admin dashboard page, served at `/admin` (§12; in tabs since 2026-10-26: Overview, Players with every action on the picked player, Shop, Chat, Market, System): the total MB in the game, the shop, the price model, server timings, chat moderation with appeals, accounts, the errors the server logged, email and mail, adding or taking back MB, and the reset button. |
| `about.html` | The public "what is Meme Street" page, served at `/about` (no game connection; §11). |
| `shop_pay.html` | The pretend checkout used while the shop is in test mode (`/shop/pay`, §10.9). |

### The content (`content/`)
Every `.json` file here is a content pack: the engine reads them all in name order (a later file's settings win) and reloads them within a second when one changes. To add content while the game runs, put a new `.json` file here (§8).

| File | Role |
|---|---|
| `base.json` | Core content pack: settings, 9 sectors, the original companies, 11 event templates. |
| `expansion.json` | Extra sectors (utilities, industrials, telecom, materials, agriculture, commodities), more companies, risk settings, sector links. |
| `pack_growth.json` | Growth pack: 68 more companies in 7 new sectors (health services, retail, media, autos, real estate, crypto and fintech, space), 14 more news templates, reference financials and the definitions of the themed ETFs and leveraged products. |
| `pack_fiction.json` | **Imaginary industries:** 48 companies in 8 invented sectors (teleportation, weather engineering, time technology, dreams and memory, dragons and creatures, deep-ocean cities, antigravity, alchemy), 24 news templates, reference financials and the Frontier Industries ETF (§8). |
| `events_pack.json` | 17 sector-specific news templates. |
| `market_profiles.json` | Per-ticker reference price, share count, revenue, margin, cash, debt, dividend yield. |
| `learn-00-start.md` ... `learn-16-plan.md` | The course: one plain-text file per track, with its lessons (§10.10). |

### The tools (`tools/`)

| File | Role |
|---|---|
| `launch.py` | Starts the game: one process, or the game server plus `--gateways N` gateway processes (§1, §12). |
| `reset_game.py` | The command-line version of the admin **Reset** button: back up, then start the game over at Day 1 (stop the server first). |
| `share.py` | Gives other people a link to the game while it runs on your own computer, through a free Cloudflare quick tunnel (§1, "Letting other people play"). Never starts the game or touches the save. |
| `chart_check.py` | Runs the real engine with nobody trading and measures its charts against the known facts of real prices (§6A.9, `docs/MARKET_REALISM.md`). |
| `realism.py` | Runs the price model on its own for game years: the long-run return, levels, gaps, the structure a trader reads, chart patterns, and the "no free money" check (§6A.9). |
| `option_check.py` | Runs the real engine and buys options at random on paper (calls, puts, straddles, strangles; held or sold halfway) to check that none of them is free money (§4, §17.11). |
| `pricing_model.py` | What a cohort of sign-ups might bring in from MB packages and Pro, with every behaviour an assumption and the sensitivity to each (ROADMAP M7). |

### What the game writes (`data/`, never in git)

| File | Role |
|---|---|
| `state.json` | The save file: a snapshot of the game, written every 30 seconds. The chart candles, most of its size, live in `state.charts.json` beside it, rewritten every five minutes (§13). |
| `ledger.db` | The ledger: every money event and every player's equity curve (with `-wal` and `-shm` files beside it while the server runs). |
| `history.db` | Game-day candles (the regular session) of every listing for `history_game_years` (10) game years: the price model's daily levels come back from it after a restart (§6A.4). Backed up with the save. |
| `minutes.db` | One-minute candles for `history_minute_days` (3) real days, and every other timeframe's last 2,000 candles in a table each, so every chart (and a backtest, §10.12) reaches back 2,000 candles (§11). Not backed up. |
| `backups/` | Copies of the save and the ledger made by the admin **Reset** button, `reset_game.py` or `start_game.ps1 -Fresh`. |
| `admin_key.txt`, `share_url.txt`, `sim_results/` | This computer's admin key (made by `start_game.ps1`), the last link from `share.py`, and the market checks' cached runs. |

### Everything else

| File | Role |
|---|---|
| `deploy/` | Putting the game on a rented server with a domain name and https: a guide, the upload and update scripts, the setup script, the services, the web-server file and the backup job (§1, "Running it on a real server") |
| `tests/` | The automated test suite: engine, server, browser, stress, capacity and slow checks (§16). |
| `.github/workflows/tests.yml` | Runs Ruff, mypy and the test suite automatically on every push (the project is on GitHub). |

---

## 3. Time

- **1 tick = 1 real second.** The server loop calls `engine.tick()` every second.
- **1 game day = 1,800 ticks = 30 real minutes** (`MARKET_DAY_SECONDS`). So the "30m" change shown next to prices (and the index) means one game day.
- **1 game year = 365 game days** (`TRADING_DAYS_PER_YEAR`), which is 182.5 real hours (7 days 14½ hours). It was 252 (a real trading year) until 2026-10-09; the market never closes, so a calendar year is the natural length, and everything that is "per year" is worked out from this one number: the quarter, and how a stock's yearly volatility becomes a daily and a per-second one.
- **1 day = 86,400 s = one real day, midnight to midnight UTC** (`season_seconds`). This is the period of the leaderboard, the daily quests and the daily contest, so all three begin and end together. (Before it was called a *season* and lasted an hour.) The game's own 30-minute "game day" above is a different thing: it is the market's unit of time.

Everything shown to players is in **real time**: chart candle sizes, news and filing timestamps, and the countdowns in "Upcoming events". A countdown reads "4 hrs, 12 minutes, 9 seconds" (units that are zero at the front are left out), never "252m 09s".

**The calendar at a glance**

| Unit | Game time | Real time |
|---|---|---|
| 1 tick | | 1 second |
| 1 game day | 1 day | **30 minutes** |
| 1 day (leaderboard period) | 48 game days | 24 hours, UTC midnight to midnight |
| **1 quarter** (one earnings period) | **91.25 game days** (a quarter of a 365-day year) | **45.6 hours** (45 h 37 min) |
| 1 game year | 365 game days (4 quarters) | 182.5 hours (7.6 days) |

A company therefore reports earnings about once every 45.6 real hours (a day and 21 hours), and pays a dividend with each report. Between two reports, a stock lives through roughly 91 game days of news, stories and price moves. (The quarter was 63 game days, 31.5 hours, before the year was set to 365 days: reports came a day and a quarter apart, which felt too often.)

**One 30-minute cycle, minute by minute.** Every game day is 30 real minutes, and it is split into three **sessions** on the real clock, the same for everyone and repeating all day: **pre-market for the first 5 minutes (:00 to :05 and :30 to :35), the regular session for the next 20 (:05 to :25 and :35 to :55) and after-hours for the last 5 (:25 to :30 and :55 to :00)**, then straight back to pre-market. Trading is never refused. What changes is how busy the market is: quiet and thin before and after, a burst and a jump at the open (§6.8). The page shows the session in the header ("Pre-market · opens in 3 minutes, 12 seconds"), a tooltip on that chip with the cycle's clock times in your own time zone, and an amber (pre-market) or purple (after-hours) banner while the market is thin.

Annualised volatility `σ` (each company's `vol`) converts to:
- daily: `σ_d = σ / √365`
- per tick: `σ_tick = σ / √(365 × 1800)`

Example, NVXA (`vol` 0.42): `σ_d` = 2.20% per game day and `σ_tick` = 0.052% per second. **A longer year means calmer days:** with 252 days the same 42% was 2.65% a day, so every price now moves about 17% less per game day (the square root of 252/365 is 0.83) while its stated yearly volatility is unchanged. The size caps that depend on a daily move (news impacts, the soft daily limit, margin) shrink with it.

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

**When a gap goes past the collateral.** If a stock jumps so far, so fast (an opening jump, a catalyst, a moonshot's 100% day) that the loss is bigger than the collateral and your cash can't pay the rest, you lose the collateral and your cash, the short is closed, and **the house absorbs the rest**. That loss is counted in `short_shortfall` in the admin overview's `stats` (`/api/admin/overview`). A cover you ask for yourself is refused if you couldn't pay the loss ("Not enough cash to cover the loss on this short"); a margin call and a bankruptcy are not refused.

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
- **Where:** the stock page has an order panel; the holdings page lists **Open orders** with a cancel button. Over the socket: `{"type":"order","action":"place|bracket|cancel|exit",...}` (§12).
- **The holdings page's Take profit and Stop-loss columns**: every position shows its take-profit and its stop-loss trigger (with how far it is from the price), or "-" when there is none. Click one to type a price (Enter or **Set**), **Remove** it, or × to leave it. That sends `{"type":"order","action":"exit","ticker","kind":"take_profit|stop_loss","trigger": price or null}` (`Engine.set_exit`): an existing exit is moved (the same side-of-the-price checks as a new order), a new one closes the whole position, and when the other exit is already set the two are paired as a bracket (whichever is hit first cancels the other). Removing one leaves the other on its own.

### Leverage (Pro)
**In plain English:** with leverage you control more stock than your MB pay for. At 5x, 100 MB of your own buys 500 MB of stock: a 2% rise makes you 10%, and a 2% fall loses you 10%. The house lends you the rest and charges interest on it. Leverage changes how big the bet is, never the odds: a leveraged position wins and loses the same price moves, five times as hard, so on average it loses the interest and the fees five times as fast.

- **Who and where.** Pro (and Expert, which includes Pro). The stock page has a **Leverage** box beside the size chips (1x, 2x, 3x, 5x, 10x); `{"type":"trade",...,"lev":5}` over the socket. Any listing except the leveraged products (the 2x and 3x funds, which are leveraged already). Up to `MAX_LEVERAGE` (10x).
- **A long:** you put in `c` MB; the house lends `c × (lev − 1)` (a `lend` event in the ledger) and `c × lev` buys the stock (with the usual 0.1% fee on all of it). The loan grows by `leverage_rate_day` (0.03%) a game day, about 0.06% a real hour (1.4% a real day) at the default rate, added to the loan (`p.loan_int` keeps how much). Selling repays the same share of the loan out of what the sale brings (`repay`); the interest counts in the trade's realised P/L.
- **A short:** you post `gross / lev` as collateral instead of the whole amount (`p.collat`); the borrow fee (§4, "Shorting") is on the whole short, as before.
- **Margin.** Each position stands on its own margin (isolated). Its own equity (what selling it would bring less the loan, or the collateral plus the gain or less the loss for a short) is checked every second; when it falls to **half the margin it started with** (`0.5 / lev` of the position's value: 25% at 2x, 5% at 10x), the position is **closed at the market price** and a message says so (`Your 5x position in NVXA ran out of margin and was closed at the market price.`). The position box and the holdings page show the leverage, the margin, the loan and **the price where it closes by itself** (`liquidation_price`). A gap past that price is paid out of your cash; what your cash cannot pay, the house absorbs (`lev_shortfall`, or `short_shortfall` for a short; on the admin page's stats).
- **Adding to a position** keeps its leverage: buying 3x into a 5x position is refused ("You hold NVXA at 5x: add at 5x, or close it first"). A plain (1x) short still has the account-wide margin call of §4; a leveraged one has only its own.
- Bankruptcy and delisting repay the loan first; a reset (§10) closes leveraged positions like any other.

### Options
**In plain English:** an option is a bet on where a stock will be at a set time. A **call** pays what the price ends above the **strike** at **expiry**; a **put** pays what it ends below. You pay a price (the *premium*) up front, and that is the most you can lose; you can sell it back before expiry. Its price is tied to the stock's: it moves every second as the stock moves, by about its **delta** for each 1 MB. (`options.py`; since 2026-10-21, reworked the same day to price and behave like real options.)

**For everyone**, free players included. Companies and commodities have options; the indices, funds and leveraged products do not.

**The Options tab** (beside *Chart* on a stock's page; the chart and its tools are hidden while it is open):
- **Expiries** as chips: the next regular close, and the closes 2, 7, 30 and 90 game days later, each with the time left and its at-the-money implied volatility (the *term structure*).
- A line with the price, the **expected price at expiry** (the forward), the implied volatility, and **the move the options expect** by expiry (± one standard deviation, in MB and %); a note when earnings are due before the expiry (the prices include a bigger move, which goes once the report is out) or a dividend goes ex (calls cheaper, puts dearer).
- **The chain**: the 13 listed strikes nearest the price, calls on the left and puts on the right, each with its **bid** and **ask** and one more column you choose (**Delta, Gamma, Theta, Vega, IV, Chance ITM** or **Open interest**; remembered). In-the-money cells are shaded and a teal line marks where the price is. The page asks for the chain **every second** and changes only the numbers in place, so the quotes follow the stock tick by tick (each **bid and ask flashes green when it ticks up and red when it ticks down**, as do the detail panel's prices and a position's worth) and a click is never lost to a redraw (the table is rebuilt only when the strikes, the expiry or the column change).
- **Click a call or a put** (anywhere on its side of the row; visitors too) to open its **details**: bid, ask and value a share, what **one contract (100 shares)** costs, the strike's own IV, the chance of finishing in the money, the breakeven and the open interest; **the Greeks** in a table, each **a share and for one contract** with a sentence on what it means (delta: "moves like −32.7 shares"; gamma: how many shares delta changes per 1 MB; theta: MB a game day; vega: MB per point of IV; rho: MB per point of drift); a **profit-or-loss chart at expiry for one contract** (since 2026-10-23: a legend above it, *Price*, *Breakeven*, *Most you can lose*, *Strike*, so nothing is written over the lines; a P/L scale in MB and a price scale on round numbers; the profit shaded green and the loss red; the breakeven as a dot; and **under the pointer, what the contract pays if the price ends there**, e.g. "Ends at 11.71: +30.88 MB"); and the **number of contracts** to buy, with what they cost ("2 × 100 × 2.65 = 530.00 MB (+0.53 fee)"). Everything updates every second; the panel opens below the chain and scrolls into view, × closes it.
- **Your contracts** on the stock under the chain, and every contract on the holdings page (**Options**), with the number of contracts, cost, worth now (the bid), P/L, **delta** (how many shares the position moves like) and **theta a day** (what time takes from it in a game day), and **Sell 1** and **Sell all** (just **Sell** for a single contract). Both tables update in place too.

**Contracts.** **One contract is on 100 shares**, as on real exchanges, and **only whole contracts** are bought and sold (since 2026-10-23; before that one contract was on one share and bought in fractions by the MB). Prices are quoted a share, so a contract costs 100 times its price: an ask of 2.65 is 265 MB a contract, plus the 0.1% fee. At most 10,000 contracts an order. A position's `qty` is kept in shares (100 a contract), so the ledger, the crash replay and settlement work as before; a position bought in fractions before the change can still be sold (Sell 1 sells what is left of it). European style, settled in cash (like index options in real markets): no shares change hands, and at expiry the payoff (`max(0, price − strike)` a share for a call, `max(0, strike − price)` for a put, times 100 a contract) is paid into your cash with no fee (`opt_expire`). A contract can be bought until a minute before it expires.

**Strikes are listed, as on an exchange.** When an expiry is first asked for, 13 strikes are listed around the price, 2.5% to 5% apart on round numbers. They stay until that expiry passes; as the price moves, new strikes are added so there are always six above and six below it (at the spacing that suits the new price), and the chain shows the 13 nearest. Nothing jumps when the price moves: the rows stay and the shading moves. (The list is not saved; after a restart an expiry is listed again, keeping every strike someone holds.)

**How the price is worked out** (`options.contract`, Black-Scholes-Merton):
- **On the forward**: today's price, less a dividend that goes ex before the expiry (the engine drops the price by it on the ex-date), grown at the stock's **expected drift** (`option_carry`: the price model's rate plus beta times the equity premium; the rate alone for commodities; none for moonshots). **Nothing is discounted**, because MB cash earns no interest in the game, so a contract is worth what it is expected to pay. That keeps **put-call parity** (call − put = forward − strike, the same at every strike) and means a deep in-the-money call is no cheaper a way to borrow than leverage.
- **Implied volatility, by expiry** (`option_vol`): **what the stock really does**, the larger of its realised volatility over the last 20 regular-session closes and over the last 80 game days (`_realised_vol`). The stated volatility is only the noise: the price model's trends, swings, levels and news make real moves about twice as big (a check on the engine found realised variance 2 to 5 times the stated, and both estimates unbiased within ±30%), so a new game or listing with fewer than 10 days of history uses twice the stated volatility (`option_vol_guess`). Then the volatility-clustering multiplier of the moment (§6.7), fading back to normal over the contract's life at the engine's own pace (`vol_cluster_decay_days`), scales half the variance (`CLUSTER_SHARE`, as measured: a calm spell's next days move about 0.8 times as much, a storm's about 1.5 times). After a storm the short expiries cost the most (an inverted term structure); in a calm they cost the least (an upward-sloping one), as in real markets. Plus `option_vol_premium` (15%): real options cost more than the moves they insure (the variance risk premium).
- **Implied volatility, by strike** (`options.smile`): a **skew**, measured in standard deviations from the forward (so short expiries have the steepest skew across strikes). Ordinary stocks: lower strikes cost more volatility (`option_skew`, 0.08: puts below the price are crash insurance). It turns into a **call skew** for the wildest stocks (volatility 0.4 to 1.2 a year: their moves jump up more than down, like meme stocks' in real markets), and commodities have none. Both wings cost a little more (`option_smile`, 0.08). The smile moves with the forward, so a strike's IV changes a little as the stock moves.
- **Earnings**: if the company reports before the expiry, the price includes a jump of about three ordinary days' moves (that expiry's IV is higher); once the report is out the premium is gone (the **volatility crush**).
- **The Greeks**, at each strike's own IV: **delta** (the change for a 1 MB move; about the chance of finishing in the money; a call between 0 and 1, a put between 0 and −1), **gamma** (the change in delta for a 1 MB move; highest at the money and near expiry), **theta** (the change in a game day if nothing else moves; it speeds up near expiry; a deep in-the-money put's can be positive), **vega** (for one point of IV; bigger for longer expiries), **rho** (for one point of the drift; calls positive, puts negative) and the **chance of finishing in the money** (N(d2) on the expected drift). `test_options.py` checks each against a finite difference of the price.
- **Bid and ask**: `option_spread` (6%) of the value apart and at least `option_min_spread` (0.1%) of the share price, so cheap far-out contracts have wide spreads, on the price ticks of the real markets: 0.01 under 3 MB and 0.05 from 3 MB (0.0001 on stocks under 1 MB). The usual 0.1% fee is on what you pay or get.

**No free money.** With the premium and the spread, buying at random loses on average: `test_options.py` checks calls and puts from 10% below to 10% above the price on a stock that moves at its stated volatility, and a check on the real engine (§17.11: 4 seeds × 60 game days, every stock with options every 10 minutes) finds that every straddle and strangle loses in every seed, whether held to expiry (−22% to −91% on average) or sold at the bid halfway, on every expiry, in calm, normal and stormy spells, on tame and wild stocks, and in a new game's first days. Single calls and puts follow the market's direction, as buying the stock does.

**The money**: the house is the other side of every contract, as for shares. What you pay goes to the house reserve and what you get comes out of it, the ledger records every purchase, sale and settlement (`opt_buy`, `opt_sell`, `opt_expire`) so a crash loses none, and equity counts each contract at its bid. At most 40 open option positions a player. The free restart counts options as open positions; **Close all positions** sells them too; a reset closes them at the bid. **Open interest** is what all players hold of a contract.

Over HTTP: `GET /api/options/{ticker}?exp=`, `POST /api/options/buy`, `POST /api/options/sell` (§12). Bots can buy calls and puts on any of the five expiries, as many whole contracts as their size buys (§10.12); backtests price and size them the same way.

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
Equity = cash + the sale value of each long (`shares × price × (1 − fee)`, less its loan if it is leveraged) + for each short its collateral plus the gain or less the loss (at the cost to buy it back, `shares × price × (1 + fee)`) + each option contract at its bid.

---

## 5. Where money lives (conservation)

Every memebuck is in exactly one of three places:

```
player cash  +  house reserve  +  fees  =  minted
```

`total_tokens() == minted` is checked by `sim.py` (drift about 1e-10, floating-point rounding) and logged on load.

**What changes `minted`** (money entering or leaving the game):
- `credit(player, amount)`: a deposit or signup bonus (in the new plan: a purchased MB package or a challenge reward; MB are never cashed out)
- `debit(player, amount)`: a withdrawal (only free cash, not positions)
- the house putting in capital: the 50,000 MB reserve (`house_seed`) and the **automatic top-up of the reserve** when it falls below its floor (§6.11; recorded as a `recap` event in the ledger and counted in `recapitalized`)
- a **game reset** (§1): closing positions settles with the house, and setting every balance back to the start mints or burns the difference, so the books still balance

**What moves money between places:** trades (player cash ↔ house reserve, fees → fees), leverage (the house lends towards a leveraged long and is repaid when it is sold, interest included), options (premiums to the house, sales and payoffs from it) and bankruptcy (holders are paid from the house reserve a fraction of the last price, §6.6).

**What never moves money:** news, noise, mean reversion, regimes, earnings, rescues, **catalysts**, **offerings** (only the share count changes), **volatility** and the **trading sessions**. They change prices only. The social features (achievements, quests, the daily contest, chat, profiles) never touch real money at all: the contest uses a separate paper account (§10.4), and their rewards are medals and badges, and a test (§16) runs two identical markets, one with heavy social activity, and checks that every price and the token books are identical.

**Every money event is also written to the ledger** (§13): joins, deposits, withdrawals, buys, sells, shorts, covers, margin calls, loans and repayments (leverage), option purchases, sales and settlements, dividends, borrow fees, bankruptcy payouts and reserve top-ups, each with the change it made to the player's cash, the house reserve, the fees and the position's cost. After a crash the server replays the events recorded since the last snapshot, so no trade is lost. The ledger is also where the history page and the CSV export come from.

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

r = (σ_market·Z_market + σ_sector·Z_sector + σ_idio·Z_idio) × volatility_scale / √(365 × 1800)
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

The **game-day candle** (§11, "Game time") is the regular session alone, so on a game-day chart the after-hours, the pre-market and the opening jump add up to the gap between one close and the next open (ROADMAP TA-A7).

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

### 6.10A IPOs and takeovers: ordinary companies that join and leave (since 2026-10-24)
**In plain English:** about 15 new companies list a game year (one every 12 real hours or so, at random), from any industry and of any size; each is announced a game day (30 minutes) before it trades. Once the market has 200 ordinary companies, each new listing is matched by a takeover of the smallest company outside the MSI 50, so the market stays about that size. (Moonshots, §6.10, are a separate kind and stay switched off.)

- **When** (`Engine._ipos`, every tick): the wait to the next announcement is random with a mean of a game year divided by `ipo_per_year` (15); `0` switches IPOs off. One IPO is announced at a time.
- **The company** (`newsgen.make_company`): an industry chosen at random from the 28 with templates (`newsgen.IPO_SECTORS`: Commodities and Safe Havens have none); a name and a four-letter ticker never used before (`IPO_PREFIXES`, `IPO_JOINS` and the industry's suffixes, e.g. *Northgate Software*, NORS); a description from the industry's templates; a size of **small** (half: 0.3 to 2 B MB), **mid** (a third: 2 to 10 B) or **large** (a seventh: 10 to 120 B), spread evenly on a log scale; a share price from 6 to 150 MB. Its volatility, beta, sensitivity and depth are the median of the companies already in its industry (volatility times 1.3, 1.1 or 0.95 by size, and a 15% spread: a young company moves more), its revenue the industry's revenue per MB of market value (with some spread), its margin a little below the industry's (5 points lower again if small), its cash the industry's plus 8-18% of its value (what the IPO raised), its debt 70% of the industry's, and a dividend only if large (half the industry's yield).
- **The announcement:** "IPO ahead: Northgate Software (NORS), a small Technology company, lists in about 30 minutes at 23.50 MB a share." on the wire, and an **IPO** row in *Upcoming events* (always listed, with no link until it trades). The announced IPO is saved with the game (`pending_ipo`).
- **The listing:** at the announced price, with **no first-day pop** (rule 2: a pop that always came would be free money); it then trades like any other company: the price model, earnings, events, its suppliers and rivals (`_sync_relations`), a cast (`_assign_personas`), a "NEW LISTING" headline. It is kept with the game like a moonshot (`generated`), and its charts start on the day it lists.
- **Takeovers** (`Engine._make_room`): past `max_companies` (200) ordinary companies, the smallest by market value that is not in the MSI 50 and listed at least 30 game days ago is bought for cash by the largest company in its industry: "Bluecore Financial buys Pinnacle Asset Management for cash at the market price, 8.91 MB a share; PNCL is delisted and its holders are paid out." Holders are paid at the market price, shorts close there, options settle, and it goes to the archive with the reason *Taken over* (its page and chart can still be opened). **No premium**: a takeover that always paid more than the price would make holding the smallest companies free money. The payout is the same code as a bankruptcy's (`Engine._cash_out`).

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

**3. A risk report for the admin** (`house_risk()`, shown on the admin page and in the `stats` of `/api/admin/overview`). The house is the other side of every position, so a stock that players hold net long hurts the house when it rises and one they hold net short hurts it when it falls. For each stock the page shows the players' **net** position in MB, three of its own daily sigmas, and what that move would cost the house. The **stress loss** is the total if every stock moved three daily sigmas against the house at once (deliberately pessimistic, since the stocks are not all driven by one thing; a short is capped at the whole position). The page warns when the stress loss is larger than the reserve and when one stock is more than half the risk.

**Honest limits.** None of this makes a lucky win impossible: a player who goes all in on a moonshot can still win a lot, because the bet is fair and fair bets have winners. What it does is make the biggest swings smaller, keep the reserve ahead of the exposure, and show the exposure. If real money is ever used, the floor is the operator's capital decision (`ROADMAP.md`, A12).

---

## 6A. The learn-to-trade price model (`market_model.py`, on since 2026-10-13)

With `market_model` set to 2 (base.json) the market is no longer a fair random walk: it drifts slowly upwards, goes through hidden phases, trends, ranges, reacts at support and resistance and to a scheduled economy. Sections 6.1 (noise), 6.4 (spillovers), 6.5 (the soft daily brake), 6.7 (clustering) and 6.8 (sessions) still apply; **6.2 (mean reversion to a fixed price) and the old regime shocks are replaced**, and the zero-edge reasoning in 6.2, 7 and 17 belongs to the old market. The design rule is now **realism you can learn from, but no free money** (ROADMAP.md section 1). Setting `market_model` to 1 brings the old market back (the test suite's engine tests use it unless they ask for 2).

Each second the engine calls `MarketModel.step(now, dt, listings, activity, sessions)` (`Engine._model_step`). It returns, for every company and commodity (never an index or fund, which follow their members), an extra return that is queued like any other move, a **noise multiplier** that scales that second's random shock, and a **volume multiplier**. Everything below is hidden; players see only prices, volume and the macro releases.

### 6A.1 Drift and fair value
Every listing has an expected return a game year of `rf + beta x erp` (`rf` 1.5%, `erp` 4%: about +5.5% for a beta-1 company; commodities `rf`; moonshots 0), applied as a drift in log price. A game year is 7.6 real days, so this is about +0.03% a real hour: invisible in a session, clear over weeks. Each listing also has a **fair value** that grows at the same rate (plus 60% of the market phase's drift); the price is pulled towards it with a half-life of 120 game days (`anchor_halflife_days`), which keeps prices from wandering off for ever without making the pull worth trading.

### 6A.2 Market phases (regimes)
| Phase | Drift a game year | Noise | Average length | Next |
|---|---|---|---|---|
| bull | +14% | x0.85 | 70 game days | sideways, correction, sometimes bear |
| sideways | 0% | x0.8 | 40 | bull, correction, bear |
| correction | -110% (a fast 5-10% fall) | x1.35 | 9 | recovery, sideways, bear |
| bear | -45% | x1.5 | 45 | recovery |
| recovery | +50% | x1.1 | 25 | bull, sideways |

Lengths are random (exponential, between 0.3 and 3 times the average). The phases' own drifts are centred so they **add nothing in the long run** (their time-weighted average, +3.2% a year, is taken out), so the long-run return is the drift of 6A.1. The economy shifts the odds of the next phase: hot inflation with tight money makes corrections and bear markets likelier, shrinking growth makes a bear market likelier, strong growth a bull market. The headline tone (§7.3) follows the phase. The admin page shows the phase; players never do.

### 6A.3 Swings: trends, ranges and breakouts
Each listing is, at any time, in one of three modes, for a random spell of game days:
- **trend** (8-30 days): a drift of about twice the stock's volatility a game year in one direction, delivered in **legs**: an impulse (2-5 days, 3.5x) then a pullback (1-2.5 days, against the trend at 0.9x). Volume is higher in impulses (1.15x) than in pullbacks (0.85x). **The last impulse** (the one that runs past the trend's end) has 0.7x the drift and the volume (`exhaustion`): the price makes a new high on less momentum and less volume, the divergence traders watch for (TA-A4, TA-A8). **Intraday legs** (TA-A6): inside a trend the price swings in legs of 4 to 12 minutes that alternate up and down, each about 0.2 daily sigmas (`subleg_*`); up and down legs are the same size on average, so they add no drift, but a trend on the hourly chart becomes a run of higher highs and higher lows on the 5-minute chart.
- **range** (10-35 days): the price is pulled back towards the middle of the range (half-life 3 game days), the noise is 0.8x and volume 0.65x. The **last fifth of a range is quieter still** (0.6x noise, 0.65x volume: small candles, narrow Bollinger bands; the squeeze before the breakout, TA-A5). A range always ends in a **breakout**: a burst of 0.5 daily sigmas over 90 seconds, with 1.6x noise and 2.5x volume, upwards 62% of the time in a bull phase, 38% in a falling one. 65% of breakouts start a trend that way.
- **free**: just the drift and the noise.
In a sideways phase ranges are likelier. **How a trend ends**: 35% of the time with a **climax** (TA-A4): a move of 0.35 daily sigmas the trend's way over 150 seconds on 4x volume and 1.4x noise, a blow-off top or a panic low for one stock. When a trend **reverses**, it turns with a burst of 0.3 daily sigmas the new way over two minutes (1.3x noise, 2x volume: an engulfing candle, TA-A5). Instead of these, a trend's end, a range's start, a trend's start or an impulse leg can also be a **chart pattern** (§6A.10). Every burst is sized when it starts, in that moment's volatility (`sw.bursts`, saved).

### 6A.4 Support and resistance
Every listing keeps its own 5-minute bars (the last 400, rebuilt from the 5-minute candles after a restart) and, every 15 minutes, finds its **levels**: swing highs and lows (a bar higher or lower than the four on each side), grouped when within 0.4% of each other (a group of three is a level touched three times), plus the round numbers just above and below the price (140 and 150 near 145; `round_step`).

**Levels from the daily chart** (TA-A2, TA-A7; 2026-10-21). Each listing also keeps its own regular-session game days (the last 370, given back by the engine's game-day candles after a restart, §11), and these are levels too, each counting as a level of a given strength (`strength_*`):

| Level | Strength | |
|---|---|---|
| the previous game day's high and low | 2 | |
| the previous game day's close | 1 | where an opening gap fills (TA-A7) |
| today's open | 1 | |
| the 52-week high and low (364 game days, once there are 60) | 3 | |
| the 20, 50 and 200-day averages of the closes | 1, 2, 3 | moving support and resistance |

Where one lies within 0.4% of a swing level or a round number they add up (a confluence: the 52-week high on a swing high is a strength-4 level). They change when a session opens or closes.

Only levels where the price has actually turned (at least one swing high or low), and the daily ones, are tested; a bare round number is not a level on its own, but it makes a level it coincides with stronger. All sizes below are in **today's volatility** (the stock's daily sigma times its current volatility multiplier, §6A.5), as traders size reactions in ATR, **fixed when the test begins** (with the leverage effect a push sized second by second grew as it pushed down and shrank as it pushed up, and with the daily levels that added up to a steady fall; found 2026-10-21). Levels are tested **only in the regular session**, and a stock starts **no new test within 10 minutes of its last** (`test_gap_seconds`). When the price comes within a quarter of a daily sigma of a level, that is a **test**, and its outcome is drawn there and then:
- it **holds** with probability `0.40 + 0.09 x touches (up to 4) + 0.07 if it is a round number + 0.10 if it lines up with the trend (support in an uptrend) - 0.10 if against it + 0.05 more for a strong level (3+ touches or round) in line with the trend - 0.07 x the times it was tested in the last 3 game days`, between 25% and 75% (strong levels end up holding about 59% of the time, weak ones 43%; MARKET_REALISM.md). While a strong level is tested the price **slows down**: its noise is 0.8x on a test that will hold and 0.9x on the way to one that will break (`level_approach_vol`; ROADMAP TA-A1, 2026-10-19). A hold is a quick rejection: the price is pushed away from the level at 0.12 daily sigmas in 40 seconds, on 1.3x volume, until it is a quarter of a daily sigma away (`bounce_reach` 1.0 band; it was 2.5 bands until 2026-10-21: with the daily levels a stock is near some level most of the time, and bigger bounces let "trade every level test" beat holding the market several times over). Once the price is through the level the push back is up to three times harder (`wick_push`): the long wick of a rejection (TA-A5).
- otherwise it **breaks**: once the price goes through (nothing pushes it there), it follows through (0.45 daily sigmas over 75 seconds, 1.25x noise, 2.5x volume: the stop-loss orders beyond the level, Osler 2003) - unless the break is **false** (30%, 40% against the trend): it comes on less volume (1.9x instead of 2.5x, TA-A4: a hint, not a tell, as the two overlap in the noise), and one to four minutes after crossing the price is pushed back inside on 1.8x volume.
The same level is not tested again within 20 minutes. Noise can still go through a level that was due to hold: the test then simply ends, with no push either way. (Slow pushes and pushes on every crossing made one-minute returns trend, which real prices do not: MARKET_REALISM.md section 2.) Everything the model pushes is damped in the thin pre-market and after-hours (`activity`), never amplified; a test not yet decided when the regular session ends is dropped (in the thin sessions a level due to break was seldom reached before its test ran out, while one due to hold still pushed: trading every level test earned twice what holding the market did, found 2026-10-21 once `realism.py` modelled the sessions).

### 6A.5 Volatility, volume and panics
- **Stochastic volatility** (`market_model.AR`, the `sv_*` settings): each listing's volatility multiplier is `exp(X - var)`, where X is the sum of three of its own components (half-lives 10 minutes, 2 game days and 15 game days; standard deviations 0.30, 0.35 and 0.35) and two market-wide ones every listing shares (20 minutes and 2 game days; 0.20 and 0.30), so calm and busy spells come at several time scales at once (Corsi's HAR cascade) and stocks get busy together. `var` keeps each stock's average variance at its stated volatility. Each second's move feeds the fast and medium components with the opposite sign (a fall raises volatility).
- **Fat tails**: company shocks are Student t with 4 degrees of freedom (`engine._student_t4`, scaled to variance 1), capped at 8 sigmas a second; with the volatility above, one-minute returns have tails like real stocks (exponent about 3).
- **A bigger market factor** (0.21 x beta instead of 0.18, industries 0.10 instead of 0.08), raised further in a correction (x1.35) or a bear market (x1.3), so stocks move together more in sell-offs.
- **Ticks**: with the new model the quoted price (`Stock.price`) is on a grid: whole cents, or 0.0001 MB below 1 MB; trades fill at the quoted price. `fair` underneath stays continuous.
- **The daily brake** (§6.5) is 1.5 times wider and grows with today's volatility, so a volatile day can range much further (real stocks have no soft brake).
- The engine's clustering (§6.7) now weighs a fall 1.25x and a rise 0.75x, so volatility rises more after falls (the **leverage effect**), and it measures surprises against the model's own multiplier so a quiet range does not drag volatility down for ever.
- **Volume** (`Engine._volume`): every candle has a sixth number, the shares traded: `shares outstanding x daily_turnover (0.4%) / 1800` a second, times the session factor, the model's volume multiplier (which includes the stock's own volume mood, half-life a game day; a random factor for each minute; and the volatility components to the power 0.6), the phase's noise to the power 1.2, and `0.4 + 0.6 x |this second's move in sigmas|`. Indices and funds have none. Players' trades are not in it (they never move prices).
- **Capitulation**: in a correction or a bear market, once the market (the equal-weighted average of the model's listings) is 14% below its 60-day high, each game day has a 30% chance of a panic low (at most one every 20 game days): a drop of 1.6 market daily sigmas over 2 minutes on 4x volume and 2.2x noise, then a rebound of 1.3 over 10 minutes, a headline ("Panic selling sweeps the market..."), and the phase turns to recovery.

### 6A.6 The economy and the calendar
A hidden economy moves slowly: **growth** (towards 3.0% in a bull phase, 1.8% sideways, 1.5% in a correction, -1% in a bear market, 2.4% in a recovery), **unemployment** (falls when growth is strong), **inflation** (rises with growth, falls when the real interest rate is high) and the **policy rate**, set by *the Reserve Board*. The bank follows a rule (`taylor`: neutral real rate 0.75% + inflation + half the inflation gap + half the growth gap, in quarter points).

Releases come on a fixed calendar from the clock (the same after a restart; `Economy.KINDS`), 150 s into the game day, the rate decision 1050 s in:

| Release | How often |
|---|---|
| Weekly jobless claims | every 7 game days |
| Business survey (PMI), jobs report, consumer prices (CPI), retail sales | every 30.4 game days (about 15 real hours) |
| GDP growth | every 91.25 game days |
| Interest-rate decision | 8 a game year (every 45.6 game days) |

Each has a **forecast** published 3-10 game days ahead (it never changes once published), drawn from the economy at that moment plus forecasters' error. The figure itself is the economy plus measurement noise, so the **surprise** (figure minus forecast, in standard deviations) is what matters. A surprise becomes a *growth* surprise and/or a *rates* surprise (hot CPI and strong jobs push rates; claims are inverted); rate decisions are priced as a probability ("a 0.25-point rise expected (72%)") and the surprise is the decision minus the expected move. The market reacts through each listing's beta (`0.6 x growth - 0.7 x rates`, times 0.3 market daily sigmas: `release_sigmas`, 0.55 until 2026-10-19, ROADMAP TA-E1) plus its industry's sensitivity (`GROWTH_TILT`, `RATES_TILT`: banks gain on higher rates, property, tech, crypto and utilities lose, defensives hold up when growth disappoints). Most of the move comes within 45 seconds (real releases are priced in seconds), with extra noise and volume while it happens (`release_noise` 0.5 and `release_volume` 1.8, halved from 1.0 and 2.5 so a release is a bump on the chart rather than the story of the day); a quarter of releases **whipsaw** (the first 8 seconds go the wrong way). The market's noise is 0.85x in the five minutes before a release and up to 1.8x just after it. Each release is a `macro` headline ("Consumer prices (CPI): 3.4% a year, above the 3.2% forecast - inflation runs hot").

`GET /api/calendar` and the **Calendar** page show the next releases with their forecasts, the latest results, the policy rate and the next earnings forecasts; the macro releases also appear in *Upcoming events* (the list shows the next 20 events, and always includes the next economic release, even when 20 company events come first).

**The Calendar page is a month grid** (`GET /api/calendar/month?offset=k`, `Engine.calendar_month`). It runs on **game days**: one cell is one game day (30 real minutes), seven make a week (Monday to Sunday) and the months are a real calendar's, in a game calendar that began on 1 September 2026 (UTC) as 1 January of Year 1 (the page writes "September, Year 6"), so a game month passes in about 15 real hours and a game year in about 7.6 real days. Each cell shows the day, the real time it starts, up to three release chips (blue before the release, grey once it is out; the calendar never labels a result good or bad news) and how many earnings reports and company events fall on it. **Previous / Next** move a month (up to two game years either way), **Today** comes back, and clicking a day lists its releases with their forecast or result, its earnings reports (the forecast EPS from three game days ahead, then the reported EPS and whether it beat) and its company events. Results are kept for the last 200 releases (about two game years). The *Latest releases* table stays below the grid.

### 6A.7 Earnings against a forecast
Three game days before a report, analysts publish a **forecast EPS** (`Engine._earnings_forecast`): what the stories announced since the last report imply (§7.7), plus a 1% error. It shows in *Upcoming events* and on the Calendar page. The report then says whether the company beat, matched or missed it, and the price reacts to the surprise in units of how big surprises usually are for that company (the 1% forecast error, revenue noise and margin noise), times three daily sigmas, at most five: about 2.5-4 times an ordinary day's move, like real earnings days. After a big surprise (over 2%) the price keeps drifting the same way by 15% of the reaction over three game days (**post-earnings drift**).

### 6A.8 Fewer headlines
With the new model `base.json` cuts the news: a random event every 15 minutes on average (was 2), a company issue every 20 (was 1.7), offerings every 2 hours; stories about two companies, catalysts, industry-wide shocks and new moonshots are off. Macro releases, earnings, ratings and scheduled company events carry the news.

### 6A.10 Chart patterns (TA-A3, TA-A9; 2026-10-21)
Now and then a listing traces a named pattern on purpose (`market_model.PATTERNS`, mode `pattern`):

| When | Pattern (and its mirror image) | How often |
|---|---|---|
| a trend ends | double top / bottom (45%), head and shoulders / inverse (30%), rising / falling wedge (25%) | 22% of trend ends (`pattern_end_chance`) |
| a range begins after a trend | ascending or descending triangle (the trend's way) or a symmetric one, half and half | 25% (`pattern_triangle_chance`) |
| a trend begins | an up or down channel (10%); before an up-trend a cup and handle (8%) | `pattern_channel_chance`, `pattern_cup_chance` |
| an impulse leg begins in a trend | a bull or bear flag: a sharp pole, then a quiet drift back | 7% (`pattern_flag_chance`) |

That is about four patterns a stock a game year. Each is a script of legs: levels in units of its size S (2.5 times the stock's usual daily move, read off its own game days, times a size for the kind: 1.0 for a flag up to 2.0 for a cup and handle) reached over a few game days each (doubled by `pattern_days`), with the noise and volume of each leg (a triangle's legs grow quieter, a second top comes on less volume, a breakout on more). The price follows each leg's path loosely: it is pulled towards a point that moves along it (time constant a quarter of the leg, never under half a game day), with 0.85x the usual noise, so the shapes come out as imperfect as real ones. When the body is done, the ending is drawn:

| Ending | | Odds (double top; most others) |
|---|---|---|
| **works** | breaks out the way it points and runs to about its measured move | 35%; 37-41% |
| **busted** | breaks out a little, then turns back through the other side | 29%; 25-28% |
| **fails** | turns before breaking out | 36%; about 35% |

So a pattern that has broken out is right a little more often than not, never with certainty, and a flag or a triangle that never broke out was simply a pause. After a pattern the listing trends the way it broke. Patterns are saved with the model (`sw.pat`) and carry on after a restart. The odds and sizes were set with `realism.py` (§6A.9): with bigger, faster patterns (3 daily moves, legs half as long) buying every 1.5-sigma dip lost 1.6% a trade and buying 20-day highs earned 0.8% a trade, short-term momentum real markets do not have.

**Finding them** (`patterns.py`, TA-A9): `find(candles, swing)` finds patterns the way a trader would, from candles alone: swing points from a zigzag (a high is a swing high once the price has fallen `swing` below it, so each is known only when confirmed, never earlier), then a template on the last few: two tops within a third of the pattern's height, a head clearly above its shoulders, tops and bottoms that converge (triangles, wedges) or move together (channels), a flag that gives back at most half of a fast move (read off a finer zigzag), a cup with a rim at either side and a small handle. `find_all` uses several swing sizes (1.5 and 2.5 daily moves on game-day candles), and `outcome` follows a pattern forward like a trade: does a close break its trigger within 10 candles (it completes), and does the price then reach the measured move before a close beyond the other side (it works)? The screener (TA-B8) and the lessons on real game charts (TA-C2) can use it.

### 6A.9 Checking it: `chart_check.py`, `realism.py` and MARKET_REALISM.md
`MARKET_REALISM.md` has the research on how real prices move (with sources), what was wrong with the charts, what was
changed on 2026-10-13 and the next steps.

- `python tools/chart_check.py [game_days] [seed] [--cached]` runs the **real engine** (no players) on a fixed clock and
  measures one-minute candles against the stylised facts of real stocks: fat tails and the tail exponent, no
  minute-to-minute direction, volatility memory and the leverage effect, volume against the size of the move and its
  memory, the intraday U-shape, correlation between stocks, daily tails, gap fills, earnings days and ticks, each with
  its target. About 20 seconds a game day; results are cached in `data/sim_results/`.
- `python tools/realism.py [game_years] [seeds] [stocks] [first_seed]` runs the price model on its own in 10-second steps
  (with the engine's noise, clustering, daily brake and, since 2026-10-21, its trading sessions and opening jump rebuilt),
  about 50 times faster than the engine. It reports the long run, the stylised facts, levels by strength and by kind,
  opening gaps, the "no free money" strategies (§1 of the ROADMAP's design rules: dips, momentum, breakouts, every level
  test, the daily levels, fading gaps, every completed chart pattern), the structure a trader reads (volume on breakouts
  that run against ones that fail, climaxes, quiet pullbacks, wicks, engulfing candles, the squeeze, timeframes that
  agree, RSI divergences and Bollinger squeezes, each against its baseline) and the chart patterns: how many of each
  `patterns.py` finds on the game-day charts, how many complete and work, the result of trading them, and how many of
  the patterns the model made a trader would have recognised. The model can write what it does to a list
  (`MarketModel.trace`) for this. It is an approximation of the engine (its gap fills differ: use `chart_check.py`).

The latest results are in MARKET_REALISM.md section 4 (2026-10-21): the chart checks as before Phase 2 (the tail
exponent and the market's one-minute autocorrelation just outside their targets on some seeds), levels holding 63% (strong)
and 48% (weak), the structure readable but never certain, and no simple strategy beating holding the market, costs
included (trading every level test +0.06% a trade, every completed chart pattern -3.3%).
Rumours are rarer and slower with the new model (25% of stories, confirmed after 3 to 10 minutes; `rumor_prob`,
`rumor_delay_seconds` in base.json): a rumour confirmed a minute later made one-minute returns trend.

---

## 7. News, catalysts, narrative, company stories and ratings

### 7.1 When things happen
- **Random events:** a Poisson process with mean gap `event_mean_seconds` = 120 s.
- **Company stories** (§7.7): mean gap `issue_mean_seconds` = 100 s across the whole market.
- **Two-company stories** (§7.11): mean gap `cross_mean_seconds` = 240 s.
- **Catalysts** (§7.13): rare news that moves one stock a lot, mean gap `catalyst_mean_seconds` = 480 s across the whole market.
- **Industry-wide shocks** (§7.14): news that moves a whole sector at once, mean gap `sector_shock_mean_seconds` = 600 s.
- **Earnings:** every equity with revenue reports **once a quarter**: 91.25 game days, which is **45.6 real hours** (§7.7). The first report is a random time within the first quarter, so companies report on different days. "Upcoming events" shows the countdowns, in days and hours.
- **Bank reviews:** each equity is reviewed every `rating_review_seconds` = 1,800–4,500 s (600–1,500 until 2026-10-19, ROADMAP TA-E2). They are not scheduled publicly. A review that keeps the rating is published as a "reiterates its view" note only `rating_reiterate_share` (15%, was 40%) of the time.
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
**In plain English:** a "quarter" in this game is 91.25 game days, which is **45.6 real hours**. Every company with revenue reports once per quarter, **only before the open or after the close**, and the reports are spread out so there are always a few every game day and one is always coming up.

- **Only in pre-market or after-hours.** A report is scheduled into the first 5 minutes of a 30-minute cycle (pre-market) or the last 5 (after-hours), at a random second, never in the regular session. Which of the two is a coin toss for each report. (A flat market with no sessions, or a demo with a quarter shorter than a game day, has no such windows.) §6.8 describes the cycle.
- **Spread, not bunched.** With about 150 reporting companies on a 91-game-day quarter there are about 1.7 reports per game day. The first reports are placed by **best-candidate sampling**: for each company a dozen random times in the coming quarter are tried and the one farthest from every report already on the calendar is taken, so there are no long dry stretches and no pile-ups ("Upcoming events" always has something near). A company listed later gets a slot the same way, in a quiet part of the calendar. (Real companies bunch their reports into a few weeks; the game deliberately does not.)
- **A quarter apart, give or take a few days.** After a report the next one is a quarter after its nominal slot **plus or minus up to 4 game days** (about 2 real hours; `earnings_jitter_days`), then moved into the next pre-market or after-hours window. The slots drift a little each quarter but stay spread out, so the gap between two reports of the same company is 45.6 hours give or take a couple.
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
All `*.json` files in `content/` are **content packs**, merged in alphabetical order. Later files override earlier ones with the same id or ticker. A pack can contain:
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

**Company size: small, mid and large caps (since 2026-10-14).** A company is a **small cap** below 2 billion of market value, a **mid cap** from 2 to 10 billion and a **large cap** from 10 billion (the usual bands; `SMALL_CAP` and `LARGE_CAP` in the engine). The stock page shows the size next to the market cap, the market search finds "small cap", "mid cap" or "large cap", and on a phone the market can be sorted by size. Every industry has at least two sizes and most have all three: 56 large, 48 mid and 43 small caps (plus the three meme stocks, which are small or mid, and the two safe-haven funds). The MSI 50 follows the 50 largest, so it is roughly the large caps. Sizes were spread out on 2026-10-14 (before that nearly every company was worth over 6 billion): each company's revenue, cash and debt were scaled with its market value so its margins, earnings per share and P/E stayed the same, and small caps were given more volatility (×1.3 against a large cap; mid caps ×1.1) and a slightly higher beta (+0.10; mid +0.05), as small companies have in real markets. Their trading volume is lower too, because volume follows the number of shares.

Each company's description says what it sells, to whom and how it earns its money, and what sets it apart from the others in its industry (written to match its size and its suppliers, customers and rivals, §7.15).

**Changing a company's size later.** The save keeps each company's market value from the content (`cap_base`). If a content pack later gives a company a different `market_cap`, the next start scales the revenue, cash and debt it has built up in the game (and its past reports) by the same factor (`Engine._fit_financials`), so its P/E and earnings per share carry on unchanged. A save from before `cap_base` existed uses the table of the old values (`CAPS_BEFORE_SIZES`).

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
- **Re-ranking:** at the start of every game day (30 minutes) the list is made again, so a company that has grown can join and one that has shrunk can drop out; the index keeps its level and simply carries on with the new members. If a member is **delisted** the list is made again at once, so there are still 50. A new listing waits for the next game day. The current members are saved with the game (a save without them, from the old version, picks them on load) and the stock page says "Weighted by market value: the 50 largest companies, re-ranked every game day".
- **Still a fair bet:** the members and their weights are fixed from prices that are already known before the second starts, and every member's expected move is zero, so any such average has an expected move of zero (§15). Trading `MSI` never moves it. The tickers did not change: the index is still `MSI` and the leveraged products are still `2LMSI`, `2SMSI`, `3LMSI` and `3SMSI`; only their names now say "MSI 50".
- **The sizes behind the weights** (since 2026-10-24, on request): Novaxis used to be worth 3,000 B MB and the next company 287 B, so it was about 43% of a new game's index (62% in the live game after its run-up). The 50 largest companies now sit on a smooth curve in the order they were: Novaxis stays at 3,000 B MB and each next one is about 6.4% smaller (CloudRail 2,810, Bankr 2,630, Ostrava Oil 2,460, ClickCart 2,310 ... Fieldstone AgTech 120), so a new game's weights run from 6.6% down to 0.26%, with the top ten about half. Their revenue, cash, debt and share counts in the content were scaled by the same factor, so P/E, earnings per share and every ratio are unchanged; a running game picks it up at its next start ("Changing a company's size later", §7). The other companies are unchanged (the next largest is 22 B MB), so the members rarely change now. Volume bars are bigger for the resized companies (they follow the share count). Prices still move the weights: a member that doubles counts twice as much.
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
- New players are credited `signup_bonus`: **1,000 MB** (since 2026-10-13; it was 10,000 MB before, and accounts made before then keep what they had).
- `deposited` tracks net money in (signup + deposits − withdrawals). **All-time P&L = equity − deposited.**

### There are no house bots
Players can run their own trading bots on their own accounts (Expert, §10.12); there are no bots of the house's. The game used to have eight house-funded bots (random, momentum, contrarian and news traders) that traded a little each minute so the market and the leaderboards were never empty. They were removed on 2026-10-05 (on request): every trade is now a real player's, and the game starts with no players at all. The old `bots`, `bot_cash` and `bot_action_probability` settings are ignored.

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

### 10.3 Leaderboards (four boards: today and all time, by return and by profit)
The **Leaders** page has two switches: **Today** or **All time**, and **Rank by Return** (%) or **Profit** (MB; remembered in the browser), so four boards, computed once per second from the same data (a short day-return list, with no other columns, is also in the sidebar of the market page). Each shows both figures, the one it ranks by first:

| Board | Ranked by | In plain English |
|---|---|---|
| **Today, by return** (`season`) | `equity ÷ day base − 1` | who is up the most today, as a share of what their account was worth when the day began; deposits don't count (§10 above). Lists only players who **have made a trade today** |
| **Today, by profit** (`day_pnl`) | `equity − day base`, in MB | who has made the most MB today (a big account can top it with a small return) |
| **All time, by return** (`ret`) | `(equity − money paid in) ÷ money paid in` | the best return on everything put in since joining (the starting balance, purchases and rewards). Lists only players who **have ever made a trade** |
| **All time, by profit** (`pnl`) | `equity − money paid in`, in MB | who has made the most MB since joining |

**Only traders are on a board.** A player who has joined, deposited or just looked around is on neither board, and has no rank (the header says "unranked", the profile shows "-", and under the Leaders table: "You are not on this board yet: it lists only people who have made a trade today"). The test is the period the board covers: the day board uses the day's trade count (which is zeroed when a day ends and by a game reset, so the day board starts every morning empty and fills as people trade), the all-time board uses "has ever traded" (any trade counted, an open position or a realised result). What counts as a trade: a buy, sell, short or cover, including a fill of an order you placed. What does not: a margin call (the game closing your shorts), a deposit, a **paper trade in the daily contest** (that is a separate account), and joining. Bots are treated like everyone else, so a bot appears once it has traded. The sidebar list on the market page is the top ten of the day board and says "Nobody has made a trade today" when it is empty; the Leaders page shows how many people are on each board (`counts` in `GET /api/boards`). The day's winner (the news line at the end of a day) is likewise taken from the day board, so it is never someone who did nothing.

**Drawdown** is the biggest fall from your best level today, measured on `equity ÷ day base` (so paying money in or taking it out is not a gain or a loss: when you deposit, the peak is scaled by the same factor). It resets each day. It is no longer a board of its own (there used to be a "risk-adjusted" board, `day return ÷ max(drawdown, 2%)`, and a "Score" column; both were removed), but it is still tracked: your worst drawdown today is shown on your profile and under the Leaders table.

### 10.4 The daily contest (fixed-balance paper trading)
**In plain English:** once a day there is a race that is fair by construction. Everyone who enters gets the **same paper balance** (1,000 MB, `contest_balance`) and trades it at the live prices, under the real rules, in a **separate paper account**. Whoever has the best return at midnight UTC wins a medal. Nobody's real money is involved either way: the paper account can't touch your real balance, the house reserve or any price, and the prizes are cosmetic (medals).

*(The first version ranked the return of your real account since you joined, in equity leagues. That favoured whoever timed their entry well and could let a rich account crush a new one. A fixed balance for everyone removes both.)*

- **When.** The **Daily Marathon** runs from midnight to midnight UTC, like a day (§10), and entries are open for the first 12 hours (`contest_join_seconds`). There is one at a time. The Hourly Sprint was removed.
- **Joining** is one click on the profile page and can't be undone: you get `contest_balance` of paper money. The profile page then shows your paper equity, free cash, rank and open positions, a ticker box with size chips and **Buy** and **Sell / short** buttons, and a Close button on each position. Bots can't enter.
- **Your paper account follows the real rules exactly** because it runs the engine's own trading code (`contest.py`, below): the same 0.1% fee, the same margin and maintenance levels for shorts, the borrow fee, ex-dividend payments, the bankruptcy payout, margin calls (your short is closed and a message tells you), the 1-second cooldown. Differences: no orders, and each entrant borrows on their own (one entrant's shorts never use up another's shares to borrow).
- **How it's built without touching the real game.** `contest.Sandbox` looks like the engine to the engine's trading code, with its own throwaway house, fee pool and short-interest, and passes everything else (prices, settings, the clock) through. Social hooks (achievements, quests) are switched off for it, nothing is written to the ledger, and the real players, house reserve and token books are never in its way. A test runs two identical worlds, one with six entrants trading furiously in a contest, and checks that every price, the house, the fees and every real balance are identical.
- **Standing** is `(paper equity − 10,000) ÷ 10,000`. **When it ends**, the top three get a medal (1st, 2nd, 3rd) on their profile, a message and the *On the podium* achievement; everyone else is told their place ("you finished #5 of 23"). The last 20 results are kept and shown on the profile page. Other players see only names and returns, never positions.
- Contests are saved with the game, paper positions included, so a restart doesn't lose them. Contests from before paper accounts existed are dropped when an old save loads (their entrants had no paper balance).

### 10.5 Profiles, privacy and following
- **Private by default.** Another player opening your profile (`/player/YourName`) sees only your name, medals, achievements and how many people follow you.
- **Public if you opt in** (a checkbox on your profile page). Then they also see your day return, your return since joining, your ranks and trade count, and **what you held** with a delay: the game takes a snapshot of every player's positions every 30 seconds and shows the newest snapshot that is **at least 5 minutes old** (`public_delay_seconds`). It shows each position's **share of your account** ("Long CLDR 18.4%", "SHORT NVXA 6.1%"), never sizes in MB or shares. So nobody can copy a trade as it happens, and nobody learns how rich you are.
- **You always see your own**, whatever the setting.
- **The leaderboards are public.** If you rank high on a board you appear there with your name and numbers whatever your privacy setting says, like in any ranked game. The setting controls your profile page and your holdings, not the rankings. (If boards should respect it too, that is a one-line change in `social.py`'s `boards_for`; see `ROADMAP.md`, open questions.)
- **Following.** Follow up to 20 players (never yourself) from their profile or by name on the Social page. The Following tab lists each with their results (or "private").

### 10.6 Accounts: passwords, email, sessions and abuse limits
**An email address is part of signing up** (since 2026-10-25, on request; the setting `signup_email`, on): the sign-up form shows an **Email address** box whatever `email_mode` is, the page and the server both refuse a sign-up without a well-formed address, and an address already on another account (verified or not) is refused. The account keeps it from the start, unverified (`p.email`, `email_verified` false); while mail is not set up nothing is sent, and once it is, the player can verify it from Profile (and with `email_mode` on, a code goes out at sign-up as before). Older accounts are not asked.

**Deleting an account** (since 2026-10-25, the admin page's **Delete account** box, `POST /api/admin/delete_player {name, confirm}`): the name must be typed again. A monthly pass still renewing is cancelled at the payment provider first (if that fails, nothing is deleted). Then `Engine.delete_player`: positions are closed at the market price (as in a reset), orders go, and the cash left leaves the game (`minted` goes down by it and the ledger records a `delete` event, so the tokens still balance and a crash before the next save replays it); `_forget` removes the player, its sessions (its open pages are logged out), its email and codes, others' follows of it, its board place, its Daily Chart game and stats and its contest entries. Its paid orders stay in the shop's books (real payments, refundable at the provider). The game is saved straight away.

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

### 10.9 The shop: MB packages, Pro and Expert (monthly or yearly), age rules, spending limits and the free restart (`economy.py`, `payments.py`)
MB are a game currency: bought, earned or granted, **never paid out** (there is no withdrawal for players). Every MB that enters an account is counted by **source** (`p.mb_by_source`): `grant` (the starting 1,000 MB), `purchase`, `challenge` (lessons and challenges, §10.10), `restart` (the free restart), `refund` (taken back, negative) and `admin`. All of it counts as money put in (`deposited`), so buying or earning MB **never lifts a return or a rank**: the boards measure returns on the money put in. A save from before sources were kept counts everything as `grant`.

**The catalogue** (`shop_packages`, `shop_pro`, `shop_expert` in base.json; prices in US cents, `shop_currency`):

| Item | Price | Per 1,000 MB |
|---|---|---|
| 1,000 MB | US$1.99 | US$1.99 |
| 5,000 MB | US$7.99 | US$1.60 |
| 10,000 MB | US$13.99 | US$1.40 |
| 50,000 MB | US$59.99 | US$1.20 |
| 100,000 MB | US$99.99 | US$1.00 |

(Since 2026-10-14; before that the packages were 100 to 10,000 MB at US$0.99 to US$39.99. Every package fits under the default monthly spending limit of US$150.)

**The New Launch Deal** (since 2026-10-27, on request; `economy.LAUNCH_DEALS`): **9,000 MB for US$4.99** or **99,000 MB for US$29.99**, one of them, **once**, in an account's first `launch_deal_days` (7) days (30 until later the same day, on request) (`Engine.deal_until`: none once a deal order is paid or refunded, or the account is older; an account with no joining time never gets it). Checkout names it "9,000 MB (New Launch Deal)"; it is an ordinary package for everything else (the ledger, refunds, the spending limits). The shop shows a strip at the top while it is on ("NEW LAUNCH DEAL: 9,000 MB for US$4.99 or 99,000 MB for US$29.99, once, in your first 7 days (5 days left)") and, the first time the shop opens in a browser session, a pop-up with both deals, each saying how much less per MB it is than the regular pack of about the same size (60% and 70%), and **Get it**, which opens the usual buy box. It never appears anywhere but the shop.
| **Pro, monthly** (renews every month until cancelled) | US$9.99 a month | |
| **Pro, yearly** (one payment) | US$99.99 | |
| **Expert, monthly** (renews every month until cancelled) | US$29.99 a month | |
| **Expert, yearly** (one payment) | US$299.99 | |

(Since 2026-10-23; before that the passes were 30 days or a year, one payment each: Pro US$4.99 and US$39.99, Expert US$12.99 and US$99.99. A pass bought then keeps its time.)

**Pro** is the income that does not depend on anyone losing: **leverage up to 10x** on any listing but the leveraged products (§4), 32 more chart indicators, among them Bollinger bands, MACD, Ichimoku, VWAP, ATR and ADX (§11), and a PRO badge; never MB. Leverage gives no edge (the same odds, a bigger bet, interest to pay), but it does make results swing more, so a leveraged player is more likely to top (or sink to the bottom of) a day's board by luck: see ROADMAP, "Leverage and the boards".

**Expert** (since 2026-10-21) includes everything in Pro, plus **trading bots** the player scripts (rules on the candles, the indicators, the account and a news score from the player's own words; they can trade shares, leveraged positions and options) and **backtests** that run a bot over the price history first (§10.12). The Shop lists both, with what each gives (`PRO_FEATURES`, `EXPERT_FEATURES` in `economy.py`). An Expert pass is kept in `p.expert_until`; `is_pro` is true for either pass, so an Expert player has every Pro tool. The badge in the header reads PRO or EXPERT. When Expert ends (or the admin takes it away) the player's bots are switched off and kept. The 17 free indicators (every moving average, RSI, Stochastic, Momentum, Auto Fibonacci, the volume average) and all the drawing tools stay free. The admin page can also give a player Pro or Expert for a number of days or take it away (`POST /api/admin/pro` with `tier`, §12). A pass is a one-off payment; nothing renews by itself; a second pass extends the first.

**A purchase is an order.** `POST /api/shop/checkout {sku, consent}` checks the rules and makes an order (`create_order`); the buyer is sent to the payment page; the order is completed **exactly once** by `complete_order`, which credits the MB or extends Pro or Expert and writes a `purchase` event to the money ledger (so a crash cannot lose it; a purchase made after the last snapshot is rebuilt from the ledger, order and all). A retried confirmation does nothing; a wrong amount is refused; an order not paid within a day expires. The admin can **refund** a paid order after refunding the payment at the provider: it takes back the MB the player still has free (never more than the order gave) or the Pro or Expert time.

**Payments** (`payments.py`, the `PAYMENTS` environment variable):
- `off` (the default, and the live site for now): the shop shows its prices and sells nothing.
- `test`: a pretend checkout page on this site (`/shop/pay`, "Pay (test)") completes the order without money. `start_game.ps1` turns it on locally. **Never on a public site**: anyone could give themselves MB.
- `stripe`: Stripe Checkout. Needs `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` and `SITE_URL`. The buyer pays on Stripe's page; Stripe calls `POST /api/shop/stripe/webhook`, and only an event whose `Stripe-Signature` (an HMAC-SHA256 of the timestamp and the body with the webhook secret, at most 5 minutes old) checks out completes an order. The browser is never trusted to say it paid. No extra package is needed. **Tax** (since 2026-10-24): the live Stripe account uses *Managed Payments* (Stripe sells as the merchant of record and handles VAT and sales tax), which refuses a product without an eligible tax code, so every checkout names one: `txcd_10201004` (video games, streamed, subscription) for a monthly pass and `txcd_10201003` (video games, streamed, not a subscription) for MB packages and yearly passes (`payments.TAX_CODE_*`). Prices are sent as **tax-included** (`tax_behavior: inclusive`): the buyer pays the price the shop shows (as EU and UK law asks for consumers), the tax comes out of it, and the amount Stripe charges stays the order's price, which `complete_order` checks. **The gateway passes the `Stripe-Signature` header on** (`gateway.FORWARD_HEADERS`; fixed 2026-10-24: before, the live site's gateway dropped it, every webhook was refused as unsigned, and a paid order waited for the payment check, up to six hours). A refused webhook is now logged as a warning ("stripe webhook refused: no/a bad signature"), so a wrong signing secret or a lost header shows in the server log; `test_gateway.StripeThroughGatewayTests` sends a signed one through a gateway.

**Before the shop takes real money** (2026-10-19, ROADMAP step 1):
- **Terms and privacy.** `/terms` and `/privacy` (`web/terms.html`, `web/privacy.html`) say what MB are (no cash value, never paid out or transferred), the age rules, purchases, refunds, fair play, chat rules, our responsibility, and what data is kept and who sees it. Contact: memestreet.game@gmail.com (both pages; on request they name no operator or country, since 2026-10-20). A lawyer should still read both (R4). Every game page has a footer with About, Terms, Privacy, the contact address ("Contact Us: memestreet.game@gmail.com", since 2026-10-24, also on the about page, the bot guide and the privacy page; the terms end with it) and "everything here is fictional and nothing is investment advice"; the about page links them too. The sign-up box says "By creating an account you agree to the terms and the privacy policy", and every new account records the version it agreed to (`p.terms = {v, at}`, `economy.TERMS_VERSION`; saved).
- **Consent at checkout.** The tick before Buy reads "The card I pay with is mine or I have the card holder's permission, and I want my purchase added straight away, so I lose the 14-day right to cancel", the waiver that EU and UK law asks for when digital content is delivered at once. Each order keeps it (`consent`).
- **Receipts.** When real email is on (O1) and the buyer's address is verified, a receipt is mailed for every completed order (item, price, order id, time, that MB have no cash value and that the right to cancel ended). Without mail nothing is sent; the order is still in *Your purchases*.
- **The payment check** (O7). A webhook can be lost (an outage, a restart at the wrong moment). Four times a day while `PAYMENTS=stripe`, the server asks Stripe for every checkout paid in the last three days (`Payments.paid_sessions`, 100 a page) and completes any order still pending or expired (`Engine.reconcile_paid`: exactly once, the amount must match). A paid checkout that cannot be completed (unknown order, wrong amount, account gone) is listed for the admin. The admin page's shop panel shows the last check (when, how many, completed late, problems) and a **Check now** button (`POST /api/admin/payment_check`).
- **A trap for sign-up bots** (R6). The sign-up box has a field people never see (`website`); a request that fills it in is refused and counts against the address's sign-up limit.
- **Rewards only for verified accounts** (R6), switched off until real email works: with `rewards_need_email` on, challenges and ladder quests still complete for an account without a verified address but pay no MB, and say why. Extra accounts gain nothing else: MB cannot be moved between accounts.

**Monthly passes renew** (since 2026-10-23). A monthly Pro or Expert is a subscription: the first month is paid at the checkout, and every month after that the payment provider charges the same price by itself until the player cancels. Each month paid adds 30 days and is a paid order of its own (`renew-<invoice>`, listed in *Your purchases*, refundable, in the ledger as a `purchase`), exactly once per invoice. The player's subscription is kept as `p.subs[kind]` (`{order, sub, provider, status, price_cents, sku}`; saved, and rebuilt from the ledger after a crash). On the Shop page a monthly pass shows "Your monthly Pro renews on 22 Nov 2026 at US$9.99" and a **Cancel** button: cancelling stops the next payment at the provider (Stripe: `cancel_at_period_end`) and keeps the pass on to the end of the month already paid ("cancelled"). A player can't hold two renewing passes of the same tier, or buy more of a tier while a monthly one renews (cancel first). With Stripe: the checkout is in subscription mode; each later month arrives as a signed `invoice.paid` webhook (`billing_reason: subscription_cycle`; its subscription is read from `subscription` or, in Stripe's API from 2025-03-31 on, which a new Stripe account gets, from `parent.subscription_details.subscription`, so renewals are found either way; the first month comes with `checkout.session.completed`, which carries the subscription id); `customer.subscription.deleted` marks it ended; and the payment check four times a day also lists paid invoices, so a renewal whose webhook was lost is still added. In the test mode nothing bills: a monthly pass renews itself when its month is about up (a pretend invoice), so the cycle can be tried. Receipts say that a monthly pass renews and how to cancel it; the terms (section 4, version of 23 October 2026) say so too.

**Buying: one box with the rules.** The Shop page is the packages, Pro, Expert and *Your purchases* (the free restart, *Before you buy*, the spending limit and *Where your MB came from* were taken off the page on 2026-10-23). **Buy** opens a box: what it is, the price (a month, for a monthly pass), whether it renews, and one tick: "The card I pay with is mine or I have the card holder's permission, and I want it added straight away, so I lose the 14-day right to cancel" plus, for a monthly pass, "I agree it renews every month at US$9.99 until I cancel". **Continue to payment** is on only once it is ticked, and starts the checkout with `consent` and `renew_ok` (the server also takes `adult`, the same tick from a page loaded before the change).

**Tracking links** (since 2026-10-24, ROADMAP B4, for advertising): a link such as `memestreet.net/?ref=ig_story1` (also on `/about` and `/daily`) is remembered in the browser (`localStorage.ms_ref`, the first one only, letters, digits, `-` and `_`, at most 40) and sent with the sign-up (`ref` on `/api/register` and `/api/join`, cleaned on the server, `server.clean_ref`); the account keeps it (`p.ref`). The admin page's shop panel has **Where players came from**: sign-ups, buyers and revenue per link (`Engine._by_ref`), "no link" for the rest. No cookies and no third party, so the privacy policy's "no tracking" still holds.

**Invite links** (since 2026-10-27, on request): every account has its own **invite code** (`p.invite`, 7 characters from an alphabet without 0, 1, i, l or o, made the first time it is needed and kept; `Engine.invite_code`), so its link is `memestreet.net/?ref=<code>`, the same `?ref=` as a tracking link. At sign-up, a `ref` that is another account's code makes that account the inviter (`p.invited_by`, `Engine.note_invite`; nobody invites themselves). The **Profile** page shows *Invite friends*: the link with a **Copy** button and how many have joined through it; the Daily Chart's shared result carries the player's own code (a visitor's share, `daily_share`). The admin page shows each account's code and inviter and whom it invited, an **Invited** column in the players list, and an **Invites** panel (who brought whom) on the Players tab; *Where players came from* counts every invited sign-up on one line, "invited by a player". Rewards for inviting may come later; nothing is paid for it now.

**Age: a date of birth at sign-up, no age rule for buying** (since 2026-10-24, on request; before, buying needed `buy_min_age`, 18, and the tick said "I am 18 or over"). Signing up with a password asks for the **date of birth** (a date field; `birth_date`, "YYYY-MM-DD") and needs `min_age` (13) on the day (`Engine.birth_date_problem`: a real date, not in the future, at most 120 years ago); a page loaded before the change may still send only the year, which is still accepted (`birth_year_problem`). The account keeps `birth_date` and `birth_year`. **An account from before** (only a year, or nothing) is asked on its next visit: while the site asks for passwords, `me_state` carries `need_dob` and the page shows a box with a date field and **Save** and nothing else (no close button, no reason given; on request it is just part of signing up), which posts `POST /api/account/birth_date` (`Engine.set_birth_date`: once, with the same check) and goes away. The terms (version of 24 October 2026) say 13 or older to make an account and that under-18s should ask a parent or guardian before buying; the privacy policy says the date of birth is kept to check the age.

**Spending limits.** At most `spend_cap_month_cents` (US$500 since 2026-10-23, so a yearly Expert fits; it was US$150) in any 30 days, and `purchases_per_day` (3) purchases a day; a monthly renewal counts towards them but is never refused. (A player's own lower limit was removed on 2026-10-26: its control had left the Shop page, so nothing could set it.)

**The free restart.** An account whose equity is below `restart_below` (50 MB) and that has no open positions can top its cash back up to the starting balance once every `restart_days` (7) days, for nothing (`POST /api/restart`). It is offered by the red banner that appears when a player is nearly out of MB (with **Close all positions**, the shop and the lessons on risk), no longer on the Shop page.

The admin page's **Shop** panel shows the payment mode, revenue (all time and 30 days, and per day), paid orders, buyers, Pro and Expert members, refunds, orders waiting for payment, where the players' MB came from and the latest orders with a Refund button.

### 10.10 Learning: the course and chart tests (`learning.py`, `drills.py`, `content/learn-*.md`, `web/learn.js`)
**Rebuilt 2026-10-27, on request** ("completely rehaul the learn to trade page... very meticulous, with the lessons, real chart tests... cover everything there is in the market"). Before, it was twelve short lessons with their quizzes switched off. **Nothing on the Learn page pays MB** (the lesson reward and the three challenges for passing lessons were removed); **visitors can use all of it** (read, take chart tests), and only a player's progress is kept. **The quizzes were taken out the same day, on request** ("get rid of the 'check what you learnt' sections"): the 236 questions, their endpoint and the page's quiz are gone, and a lesson now counts as read when a signed-in player opens it.

**The course** is 17 tracks and 96 lessons (about 26,500 words), in order: *Start here* (how Meme Street works, a first trade with a stop, finding your way), then 1 *Market basics* (shares and IPOs, exchanges, indices and ETFs, market cap and liquidity, the bid and ask, how prices move, sessions, halts), 2 *Reading charts* (candles, timeframes and log scale, trends, support and resistance, ranges and breakouts, volume, reversal and continuation patterns, gaps and fair value gaps, several timeframes), 3 *Indicators* (moving averages, RSI, MACD and stochastic with divergence, Bollinger Bands and ATR, VWAP and OBV, Fibonacci, ADX, SuperTrend and Ichimoku, combining indicators), 4 *Orders* (order types, brackets, trailing stops and scaling, slippage, gaps and fees), 5 *Risk management* (the 1% rule and sizing, R-multiples, expectancy, drawdown maths, correlation, risk of ruin, where stops go), 6 *Shorting and leverage*, 7 *Fundamentals* (statements, key numbers, valuation, dividends and dilution, earnings season, sectors, ratings), 8 *Macro* (inflation and central banks, rates, the data releases, surprises, the cycle and rotation, risk-on and risk-off, the yield curve), 9 *Derivatives* (options, pricing, the Greeks, implied volatility, strategies, exercise, futures, CFDs, swaps and leveraged fund decay), 10 *Beyond stocks* (bonds, commodities, forex, crypto, REITs and index funds), 11 *Strategies and styles*, 12 *Psychology*, 13 *Testing and automation* (backtesting, walk-forward, performance statistics, bots), 14 *How real markets work* (order books and market makers, corporate actions, brokers and regulation, taxes), 15 *From game to real life* (why most day traders lose, scams, the money basics first, what carries over) and 16 *Putting it together* (a trading plan, a checklist, a weekly review, a glossary). Every lesson teaches the real-market idea and then says, in an **On Meme Street** box, how the game does it (no spread or halts, the 30-minute day, buy-only options, takeovers without a premium and so on), with practice links to the right page.

**The files.** One plain-text file per track, `content/learn-00-start.md` to `content/learn-16-plan.md`, read in file-name order when the server starts (`learning.load_content`, `parse_learn`; the format is in its docstring): `# Track {id}` and its blurb, `## Lesson {id} [minutes]`, `SUMMARY:`, paragraphs (`**bold**` and `[text](/path)` allowed), `### headings`, `- lists`, `TIP:` / `HERE:` (On Meme Street) / `WARN:` boxes, `| tables |`, `[chart kind]` (an example on a real chart), `[test kind]` (a chart test), `[try /path] text` (a practice box). A file that does not parse stops the server with the file and line (a test parses every file). `deploy/upload.ps1` sends `content/*.md`. (`content/lessons.json` is gone.)

**Progress.** A lesson a signed-in player opens counts as read (`Engine.lesson` with the player, kept in `lessons_passed` with when it was first read; the field kept its name from the quiz days, so older passes count as read), and the list marks it *Read*; a visitor's reading is not kept. A new player sees the blue strip on the market page ("New to trading? Start with the first lesson", to `welcome`) until they hide it or read a lesson.

**Chart tests** (`drills.py`, ROADMAP TA-C2 and TA-C3): a **real chart from the game**, stopped at a moment worth asking about, a question with two to five answers, and then the candles that came next, with what happened, the idea behind it and which stock and candle size it was. Eleven kinds:

| Kind | The question | Where the answer comes from |
|---|---|---|
| Bounce or break? (`level`) | the price is back at a swing high or low: hold or break? | the closes after: a move of one ATR away (held) or one ATR through that stays (broke); fake breaks are left out |
| Read the trend (`trend`) | up, down or a range? | the last two swing highs and lows (zigzag of 3 typical candles), labelled *Higher high*, *Lower low*... |
| Name the pattern (`pattern`) | which of four names? | `patterns.find` at two swing sizes; then `patterns.outcome`: completed and worked, failed or never broke out, with its trigger, invalidation and measured move drawn |
| Real or fake breakout? (`breakout`) | the first close beyond the last 20 candles' high or low | ran on by an ATR without closing back inside (real) or closed back inside within six candles (fake); the breakout's volume against its average is reported |
| Name the candle (`candle`) | doji, hammer, shooting star, bullish or bearish engulfing, marubozu | the candle's shape (`candle_kind`, one name per candle) |
| Read the RSI (`rsi`) | overbought, oversold or neutral? (an RSI panel is drawn) | RSI 14 at 72 and over, 28 and under, or 45 to 55 |
| Moving-average cross (`ma`) | golden cross, death cross or none? (the 20 and 50 averages drawn) | the averages at the last candle |
| Fibonacci pullback (`fib`) | how much of the swing did the pullback give back? | the swing and pullback within 4 points of a level |
| Reward to risk (`rr`) | entry, stop and target drawn: 1, 1.5, 2 or 3 to 1? | the lines; then which one the price hit first |
| Where does the stop go? (`stop`) | a long bounce off support: below the support, a hair under the entry, or far away? | always below the support; the answer shows what each stop would have done |
| Up or down next? (`next`) | higher or lower ten candles on? | the close ten candles later; a player's score drifts to 50%, which is the lesson |

Kinds with two outcomes pick the outcome first and then a moment that had it, so they come out about half and half and always answering the same way scores 50%. **Where the charts come from** (`Engine._drill_find`): a company or commodity and a candle size (1, 5 or 15 minutes, or 1 hour) at random, up to 40 tries, from the candles in memory (the newest 500 of each size, without the one still forming); a game too new to have 150 of them uses a chart from the price model (the Daily Chart's maker) instead. A window of up to 160 candles before the moment is shown (enough for a 50-candle average), with room on the right for the answer, so the candles do not move when it arrives. **The answer is kept on the server** (`_drill_q`, in memory: up to 3,000 open tests, each for up to 3 hours; a restart forgets them and the page simply fetches a new one), so it cannot be read before answering; one answer per test. A player's score per kind is kept (`drills`) and shown on the Learn page; nothing is paid. Lessons embed tests with `[test kind]` and examples with `[chart kind]`: an example is the same thing with the answer behind a *Show the answer* button, the same one for everyone for 15 minutes (`_drill_ex`).

**The page** (`web/learn.js`, served at `/js/learn.js`): `/learn` shows the progress (lessons read, chart tests right), the eleven chart tests and a *Mixed* one, and the 17 tracks as cards with their blurb, progress bar and numbered lessons; `/learn?l=<id>` a lesson (its track, the blocks, the example charts and tests, and links to the lessons before and after); `/learn?test=<kind>` a page of chart tests (*Another chart* after each). Each view is drawn once when it opens, never redrawn under the reader. The chart is an SVG: candles, volume, the test's lines (levels teal, stops red, targets green, the entry amber, triggers purple) with price tags, labelled points, the 20 and 50 averages or an RSI panel when the test needs them, and once answered a dashed line at the moment of the question with *what came next* shaded after it.

**Challenges are switched off** (since 2026-10-23, the setting `challenges: false` in `base.json`, on request): no challenge is offered or pays anything (`_challenges()` offers none). When the setting is on they reward the habits the lessons teach, never volume or luck:

| Challenge | How | When | MB |
|---|---|---|---|
| Protect a trade | put a stop-loss (or a bracket) on an open position | once | 25 |
| Set a target | put a take-profit on an open position | once | 25 |
| Every trade protected | stop-losses on 5 positions | weekly | 60 |
| Plan the trade, trade the plan | close 3 positions that had a stop-loss, win or lose | weekly | 75 |
| Every trade has a target | take-profits on 5 positions | weekly | 50 |

Weeks run Monday to Sunday (UTC). Challenges pay at most `challenge_week_cap` (500 MB) a week; beyond that a challenge still completes but pays nothing. A second stop on the same position does not count again.

**The trading journal was removed** (2026-10-20, on request): its page, its endpoints, its three challenges and its four ladder quests are gone. An old save's journal entries are dropped when it loads.

### 10.11 The quest ladder: Bronze, Silver, Gold and Diamond (`ladder.py`)
Thirty one-off quests on the profile page, in four tiers that each open and close like a drop-down (the first unfinished tier starts open; the page remembers which are open). Each quest pays MB once, more the higher the tier: **Bronze 10, Silver 25, Gold 75, Diamond 150** (1,780 MB for the whole ladder), credited as `challenge` MB, which counts as money put in, so it never lifts a return or a rank, and there is no weekly cap because nothing can be done twice.

| Tier | Quests (target) |
|---|---|
| Bronze | 5 trades; 5 different stocks; 3 profitable closes; a stop-loss on a position; a short; a take-profit on a position; trading on 3 days; a dividend |
| Silver | 50 trades; 8 industries; 20 profitable closes; 10 closes of positions that had a stop; 5 profitable shorts; 25 different stocks; 7 days; 250 MB of realised profit |
| Gold | 250 trades; 75 profitable closes; 40 closes with a stop; 25 profitable shorts; a day in the top 10 of the day board with a positive return; 20 days; 1,000 MB of realised profit; 10 winners held for at least an hour |
| Diamond | **Top Trader** (3 days in the top 3 with a positive return), **Market Veteran** (1,000 trades), **Risk Master** (150 closes with a stop), **Money Maker** (5,000 MB of realised profit), **Chart Master** (300 profitable closes), **Legend** (every other quest) |

**Diamond quests unlock a title and a name colour** (gold, cyan, emerald, ruby, violet and, for Legend, diamond). No ladder quest shares a name with an achievement (§10.1): the ladder's are *Warming up*, *Window shopping*, *Small wins*, *Safety net*, *Going short*, *Set a target*, *Coming back*, *Paid to wait* (Bronze), *Getting busy*, *All over the map*, *Winning habit*, *Plan the trade*, *Short seller*, *Explorer*, *A week of trading*, *Paying off* (Silver), *Busy desk*, *Consistent*, *Trade the plan*, *Bear market pro*, *On the board*, *A month of trading*, *Real money*, *Patience pays* (Gold) and the six Diamond ones. Under *Your name on the boards and in chat* the player picks which title and colour to wear (`POST /api/ladder/style`), and the name then shows that way on the day and all-time boards, the market page's board, in chat messages (from the moment they are sent) and on the public profile, which also shows how far up the ladder the player is. Colours come from a fixed palette and titles from a fixed list, so nothing a player types reaches the page.

Progress uses the counters the game already keeps (trades, profitable closes, shorts, dividends, realised profit; so an active player finds some quests done the first time they look, and is paid for them then) and a few the ladder keeps (`p.ladder`: stocks and industries traded, stops and take-profits placed, closes of positions that had a stop, days traded, day-board finishes counted when the day ends, winners held an hour). A game reset starts the ladder, titles and colours again, like the achievements. As with the other rewards, a reward paid in the last seconds before a crash can be paid again after the restart (the snapshot is at most 30 seconds old).

### 10.12 Trading bots and backtests (Expert, `bots.py`, `web/bots.js`)
**In plain English:** a bot is a set of rules you write ("buy when the price crosses above the 20 EMA, sell when it reaches the 200 EMA") that trades on your account while you are away. A backtest runs the same rules over the past first, so you can see how they would have done.

**A bot** has a name, up to 10 stocks, one candle size (1m, 5m, 15m, 30m or 1h), up to 10 rules, an optional stop and target (% against or for the position, from its entry), at most so many trades a game day, and its news words. A player can have 5 bots. Each **rule** is a condition and an action:
- **Conditions** are written in a small language (parsed by `bots.parse`, never `eval`; at most 300 characters): numbers, `+ - * / %`, comparisons, `and or not`, brackets; the last finished candle's `open high low close volume` (`prev(x, n)` looks n candles back) and `price` (now); the indicators `sma(n) ema(n) wma(n) rsi(n) macd(f,s) macd_signal(f,s,g) macd_hist(f,s,g) atr(n) bb_upper(n,k) bb_mid(n) bb_lower(n,k) stoch_k(n) stoch_d(n,d) highest(n) lowest(n) change(n) volume_sma(n) vwap()` (`highest(n)` and `lowest(n)` are of the n candles before this one, so a breakout reads `close > highest(20)`); `cross_above(a, b)`, `cross_below(a, b)`; the account (`position long short flat entry pnl_pct cash equity calls puts`); the news (`news_score`, `market_news`); `abs min max`. A rule that does not parse is refused when the bot is saved, with the place it went wrong.
- **Actions:** buy (open a long), sell (close it), short, cover, close (either), buy a call, buy a put (at a strike a given % out of the money and one of the four expiries) and sell the options held on the stock. Buys, shorts and options are sized as a % of the free cash or an amount of MB (options: as many whole 100-share contracts as that buys); buys and shorts can be leveraged (Pro, §4).
- **The news score** is the bot's own: each headline about the stock (or, for `market_news`, about no single company) is scored by adding the weights of the words and phrases it contains (the player's list; `upgrade*` matches "upgraded"; a default list to start from), and older headlines count less, halving every *half-life* real minutes (30 by default). It reads only the headline text, never anything hidden, so it is exactly what a player reading the wire could do.

**Running.** Every second, for each switched-on bot of a player whose Expert pass is on, the engine looks at each of its stocks: when a candle of the bot's size has closed since it last looked, the rules are worked out on the finished candles, and **the first rule that is true and makes sense for the position** (no buy while already long, no cover while not short...) is carried out through `Engine.trade` or `buy_option`, the very code a click uses: the same fees, cooldowns, cash and leverage rules. One action a candle per stock. Stops and targets are checked every second and close the position. A sell, cover or close closes **the whole position** in the stock, so the stocks a bot trades are best left to it. Each bot keeps a log of its last 40 actions and why (*What it did* on its card); a message tells the player when the bots are switched off because Expert ended. Bots are saved with the game.

**Backtests** (`POST /api/bots/backtest`): the bot is run over the candles the game keeps for one of its stocks at one candle size (up to 5,000: 2,000 of each size and three real days of 1m candles, from `minutes.db`), starting from a chosen amount of MB: rules at each candle's close, orders filled at the **next candle's open**, the same 0.1% fee, leverage with its interest and its margin, stops and targets on the candles' highs and lows, options priced as the game prices them (on the stock's recent volatility, with the premium and the spread), and the news score from the headlines the stock has kept. The result is the return against just holding the stock, the trades, the win rate, the average win and loss, the profit factor, the worst drawdown, the fees, the time in the market, the equity curve and the trade log. The candles are gathered under the game's lock and the run happens in a worker thread without it, at most one every 3 seconds a player, so a backtest never holds up the game. A backtest only shows the past: the market has no free money in it (§6A.9), so a rule that did well over three days has usually found luck, not an edge (the result says so).

**The page** (`/bots`, `web/bots.js`): without Expert it explains what bots do and links to the Shop. With it: each bot's card (stocks, candle size, trades today, its rules in plain words, Switch on/off, Edit, Delete, *What it did*), **New bot** and five templates (EMA trend, RSI dip, Breakout on volume, News momentum, Calls on good news); the editor (name, stocks, candle size, the rules as rows of condition, action, size and leverage or strike and expiry, stop, target, trades a day, the news words, and a reference of everything a rule can use); and the backtest under it.

**The guide** (`/bots/guide`, `web/bots-guide.html`; since 2026-10-24, on request): a page for players on setting a bot up step by step, how it runs, writing rules, every word a rule can use (candles, indicators with their defaults, crosses, the account, the news), the actions and sizes, news scores with the default words, backtests, examples, the limits and what to check when a bot does nothing. The Bots page links to it (in the explanation without Expert, above the bots, and from *What a rule can use* in the editor). `test_bots.GuideTests` checks that it names every function, value, action, candle size and default news word the code has, so it can't fall behind.

**Endpoints:** `GET /api/bots`, `POST /api/bots/save`, `/toggle`, `/delete` and `/backtest` (§12).

### 10.13 The Daily Chart (`daily.py`, `web/daily.js`; since 2026-10-23, relaunched 2026-10-24)
**Relaunched like the daily word games (2026-10-24, on request: "repeatability, competitiveness, simplicity and aesthetics", after Wordle and the like).** It was archived for a day (off the site; the `daily_chart` setting, now on again) and came back with:
- **A number a day**: *Daily Chart #1* is 24 October 2026 (`daily.EPOCH_DAY`); the header of the page shows the number, the date and how many have played.
- **Stats and streaks** per account (kept in the save with the game, `daily_game["stats"]`, counted once per game when it ends): games played, the **streak** of days in a row (a missed day ends it; yesterday still counts while today is unplayed), the best streak, the average and best return, and how often the player beat just holding the stock. A **Stats** button shows them.
- **A result grid**: 8 squares, one per 15 seconds of the two minutes, green where the account's worth rose, red where it fell, grey where it stayed flat (in cash, or a move under 0.05%) (`DailyMixin._daily_grid`, from the trades and the closes).
- **The look**: one centred column. Before playing: "Two minutes. One chart. The same one for everyone.", the streak, a big **Play** button, today's best and the last days' winners. Playing: a big timer (red and pulsing in the last 15 seconds) and the live return, the chart (the lead-in shaded), the position in one line, a row of sizes (25/50/75/100%, remembered) and two big **Buy**/**Sell** buttons that read **Cover**/**Short** when that is what they do; on a keyboard **B**, **S** and **1-4**. Afterwards a result card, as a box when the game ends and at the top of the page: the return, the place, the squares (appearing one by one), what the stock did and whether you beat it, the stats, **Share** and **Story picture**, and a live countdown to the next chart; then the chart, everyone's returns and the board. **?** opens a short *How to play*. A visitor without an account sees the pitch and *Create an account to play*.
- **Sharing**: **Share** gives the result as text, Wordle-style ("Meme Street Daily Chart #1 / +2.7% · 1st of 57 / the squares as emoji / the streak / https://memestreet.net/daily?ref=<the player's invite code>"): a phone's share sheet (with the picture where it takes files), otherwise copied. **Story picture** draws a 1080 x 1920 PNG for an Instagram story (the number, the date, the return, the place, the squares, the day's line, the stock's move, "Can you beat it?" and the address) and shares or downloads it. The link carries the player's invite code, so sign-ups from shared results count as invited by them on the admin page (§10.9).

- **Volume builds into the close** (2026-10-26, on request): the model's calm patches could leave the last seconds of a game with almost no volume. The last 30 seconds (`CLOSE_RAMP`) now build like a real close: at least 80% of the chart's usual volume (its mean without the top tenth, so a climax does not set the bar), rising by up to 60% towards the final candle. Quiet stretches earlier in the game stay, since volume drying up before a breakout is one of the things the game teaches. A day's chart is saved, so the change starts with the next new chart.

- **More technical** (2026-10-26, on request: "more emphasis on the technical features, not crazy", since the game teaches technical analysis). The chart's price model (`market_model.py`) now runs with the Daily Chart's own settings (`daily.TECHNICAL`; the market keeps its defaults, where a reliable edge would be free money): levels come from the swings a player can see (the model's bars are 60 model seconds, two candles, with a swing being the high or low of 3 bars either side; the market's are 5 minutes and 4) and from **fair value gaps** (`fvg_levels`: the middle of a three-bar gap the price has not filled is a level of strength 2); a stock tests a level at most every 300 model seconds (10 candles; the market: 600); levels hold somewhat more often (`hold_base` 0.46, `hold_per_touch` 0.10, `hold_strong_aligned` 0.08) and bounce visibly (`bounce_sigmas` 0.18, `bounce_reach` 1.6); breakouts run further (`follow_sigmas` 0.6); patterns form at the chart's scale (`pattern_days` 0.8) and a little more often. Measured on 200 charts, from the model's own tests: **13 level tests a chart** (8 at swings, 4 at fair value gaps; before: 6, mostly invisible), **60% end in a visible bounce**, 28% go through, 12% neither (before: 42%, 35%, 24%); a level meant to hold is seen to bounce 81% of the time (before: 55%). Against the same moves shuffled into a random walk: breakouts fail 44% of the time (55% at random), named patterns 2.1 a chart (1.4), flags several times as often. Fakeouts and failed levels stay common.
- **No overlays** (since 2026-10-27, on request: the 20 EMA and VWAP switches were taken off the chart).
- **What today's chart did** (after the game): the levels the chart tested (`chart["levels"]`: where the model tested a level, from `MarketModel.trace` "level" entries, as support, resistance or a fair value gap; whether each test **held, broke or was a fake break is read from the candles that follow** (`_seen`: the price moved two candles' usual move away on its side, or closed that far through and stayed, or went through and came back within 8 candles), so the breakdown never contradicts what the player saw; a test that shows none of these within 15 candles is left out; tests of one level grouped, at most `LEVELS_SHOWN` 6, the most tested first) are listed under the finished chart in words, in a drop-down, **The levels this chart tested (N)**, closed at first (since 2026-10-27, on request); opening it also draws them on the chart, each as a soft band in its colour over the stretch where it was tested, its number in a small tag at the band's start and a dot at each test (teal held, orange broke, purple fake break)  ("Fair value gap at 17.35 (the middle of the gap): held twice"). They are sent only once the game is over (`_daily_state`), since during it they would tell the future.

What follows is the game itself, as before.

**In plain English:** a two-minute daily game. Everyone gets the same mystery chart that day and 1,000 MB of practice money; the best returns top the board. It is just for fun: nothing in it touches anyone's real MB.

**The chart of the day** is made once, the first time anyone asks for it that day (days are UTC, like the game's), by the game's own price model (§6A: trends in legs, ranges and breakouts, support and resistance from swing points and the day's levels, chart patterns, volatility clustering with the leverage effect) driving one made-up stock with no name, with the engine's kind of noise on top (`make_chart`). The model runs three game days first, so the stock has swings, levels and a market phase (picked at random) before the chart begins; then each one-second candle is 30 seconds of the model (`MODEL_SECONDS`), so the two minutes hold about an hour of game time: several legs, tests of levels, breakouts. Candles have volume too. The volatility is drawn each day, mostly about 120% a game year (from 40% to 350%): the price usually swings 10% to 20% inside the two minutes (the median day 12% from its high to its low; some days far more). The starting price is drawn too (4 to 600 MB). The seed is the day and a random salt kept in the save, so the chart cannot be worked out in advance even from the code, and the chart itself is saved with the game, so a restart or a new version of the code changes nothing on the day. Making it takes about 0.1 seconds.

**A game** (one a day for each account; visitors are asked to sign in):
- **Start** shows the chart's last minute at once (60 candles, `HISTORY`), to read the levels and the trend from. Then a new one-second candle appears every second for two minutes (`LIVE`, 120), with **the countdown in big figures in the chart's corner**, and the price, the cash, the position (shares, or the short), the total and the return above it.
- **Buy 25%, 50%, 75% or 100%** of the cash, or **sell 25%, 50%, 75% or 100%** of the shares, at the close of the latest candle, with no fees. **Selling with no shares opens a short** of that share of what the account is worth (a short already open counts against it, so the most anyone can be short is the account's worth: 1x); **buying while short covers** that share of the short. The two rows of buttons say what they will do: Buy or Cover, Sell or Short. Buys and covers show on the chart as green triangles, sells and shorts as red ones.
- When the two minutes are up, what is held (or owed) is valued at the last candle's close and the score is the return on the 1,000 MB, never below −100% (a short that more than doubles against you just loses everything). **A summary pops up**: the return, what you finished with, your place and the share of the other players you beat; **everyone's returns today as a distribution** (a histogram, gains green and losses red, with a line at 0% and a teal line where you landed); what the stock itself did (its return, high and low) and whether you beat just holding it. It pops up once (reopened with **See the summary**); under it stay the result, the whole chart with the trades, and the board.

**Fair play.** The candles still to come never leave the server: the page asks once a second for the candles shown so far (`GET /api/daily/state?since=`), and asking ahead returns nothing. A trade is priced on the server, at the candle showing when it arrives. Nobody can see the chart before they start, the whole chart is shown only after their own game, and the board shows only names, returns and the number of trades. A game runs on the server's clock: closing the page does not stop it, and it ends (holdings valued at the last close) when its two minutes are up, whenever the player next looks.

**The board**: today's finished games, best return first (a tie goes to whoever finished first), the top 20 shown with the player's own row highlighted; under it, the last 7 days' winners. At midnight UTC the day's top three and the number of players are kept and a new chart is made.

**Endpoints:** `GET /api/daily`, `POST /api/daily/start`, `GET /api/daily/state?since=`, `POST /api/daily/trade` (§12). Kept in the save as `daily_game` (the salt, today's chart, today's games, the last 7 days); not in the money ledger, since no real money moves.

---

## 11. The web pages and charts

### Pages
The logo in the header (and the tab icon) is `brand/memestreet_logo_peaks.png`, served at `/brand/memestreet_logo_peaks.png` (only the two named brand images are served), shown with rounded corners.

Every page has the same header (index, cash, equity, P&L, day return, rank, the day's countdown, the market status chip) and the same navigation. Nothing on any page shows the market's mood or regime.

- **Visitors (not signed in).** The market (`/`) and a stock's page (`/stock/NVXA`) open without an account: a visitor sees the live prices, charts, the news wire and the stock facts, under a welcome card ("A fictional stock market that never closes... You are watching it live. Create an account to trade.", with Create account, Sign in and How it works). The menu shows only the market and the header only the index and the day timer; the buy and sell controls are replaced by "Create an account to trade this stock". Anything that needs an account opens the sign-in box with the reason, and on these two pages the box has a **Keep watching the market** button; on every other page (holdings, portfolio, history, leaders, social, profile, a player's page) the sign-in box cannot be closed. Signing up or in turns the same page into the player view without a reload. Behind the scenes a visitor is attached to one hidden, read-only "guest" (§12). **The top-10 leaderboard (names and returns) is part of what a visitor sees**, as it is for every player; say so in the privacy policy (ROADMAP J1).
- **About (`/about`):** a plain page for people who have not signed up: what the game is (180+ listings), how it works as a plain list (news, what you can trade, why it is fair, learning as you go, competing, and what trading costs: "0.1% of its size, as a real broker would charge you"), and four questions (is it real money: no, MB are a practice currency with no cash value that is never paid out; are the companies real: no; can I lose everything; does it work on a phone). It never says the game is free. Its buttons go to the market and to `/#join`, which opens the sign-up box. Every page also has a description and share tags (title, text, image) so a link looks right in chat apps, and a stock's page sets the tab title to its ticker and name.
- **Market (`/`):** a table of every listing, under a sticky header (the index, cash, equity, P&L, day return, rank, and the session chip; §6.8). Above the table:
  - a **search box** (matches ticker, company name and sector; `nvx` finds NVXA, `index` finds the indices and ETFs),
  - the buy/sell **size chips** and the **amount box**,
  - the **industry chips**: ★ Watchlist, All, **Indices & ETFs** and one chip per industry (30 of them now). Only the **first row** is shown; the arrow at the right (**▾ All industries (30)**) unfolds all of them and turns into **▴ Show less**. An industry you pick from the hidden rows moves to the front so you can always see what is selected. The fold state is remembered.

  Each row shows the **ticker with the company name beside it** (there is no description on this page: it is on the stock page), the price, the 30-minute change in a small tinted box, a trend sparkline, how much you hold, and Buy and Sell buttons. **Sorting:** click a column header (Ticker, Company, Price, 30m, Held); click again to reverse; an arrow shows the sort. **The table only re-sorts every 3 seconds and never while the pointer is over it**, so rows don't jump away under your finger. **Watchlist:** click the ☆ at the start of a row; it turns gold ★. Your sort, search, industry, fold state and watchlist are **remembered in your browser** (`localStorage`). Each row can carry a green **NEW** **badge** (listed in the last 30 minutes, §8). The Held column shows the position's value in MB, with `(short)` after a short. **Prices are plain white**; a price that jumps more than 0.15% in one tick flashes green or red for about a second, so the everyday small ticks leave the table calm and the colour never contradicts the 30m pill. A 30m change that rounds to 0.0% shows as a grey pill. The buttons are never greyed out: you can trade in every session. Beside the table: the news wire (times and ticker links), **upcoming events** (one row each: a coloured kind label for Earnings, Investor day, Guidance update, Analyst call or Product event, the ticker, the company name on one line, and a short countdown such as "20 min 51 s" that turns blue in the last five minutes), the top-10 leaderboard.
- **Stock (`/stock/{ticker}`):** top to bottom, in the order a trader needs it: the name, star and badges with the **timeframe buttons on one row beside them**, the price and change; buy/sell (labelled **Short** / **Cover** when that is what the button will do) with the size chips and the **amount box**; a costs line ("Shorting takes the amount out of your cash as collateral and gives it back when you cover · borrow fee 0.27% per hour. There is no limit on how much of this you can buy or short."); your position box (shares, average entry price, value, gain or loss, dividends, borrow fees paid); **the chart**; the folded **order panel** (limit buy and sell, stop-loss, take-profit and a one-click bracket, with the list of your open orders for this stock and a cancel button; §4) and position-size tool; then *About the company*: the **description** (derived assets add "Tracks: ..."), the **company's cast** (CEO, CFO, product, city and former CEOs; §7.10) and the financial facts (market cap, P/E and dividend yield are **recomputed from the live price every second**; margins and yields are shown as plain levels, a stock with no dividend says *None*; the price is not repeated there). Last, *Earnings history* (the latest four reports, **Show all** for the rest; each report's "behind the numbers" list is clamped to two lines, click it to read it all) and *Company news & analyst notes* (a dozen headlines, **Show older news** for 25 more; §7.7). Headlines here and on the news wire are plain text with their kind (BREAKING, RUMOR, CONFIRMED...) as a small coloured tag in front.
- **Holdings (`/holdings`):** cash, net positions value, total cost, open P/L and equity, then **size chips and an amount box** (the same as on the market page) and one row per holding: ticker and company, side (Long or SHORT), shares, average entry price, price, value, dividends received or paid, P/L (MB with the % beside it, one column), take profit and stop-loss (§4) and **Buy and Sell buttons at the end of the row**, so you can add to, trim or close a position right there (for a short the buttons read **Cover** and **Short**). Below the table, **Open orders** lists every order you have left, with a cancel button. The chips pick a share of cash (Buy) or of the position (Sell); an amount typed in the box overrides them.
- **Portfolio (`/portfolio`):** the "how am I doing" page. Ten figures (equity, cash, money paid in, total profit and return, realised profit, unrealised profit, fees paid, dividends, borrow fees, trades today); an **equity curve** (one point per minute for the last day, with a dotted line at the money you paid in, green above it and red below); an **allocation bar** (cash and each position as a share of your account); the open positions with unrealised and realised profit; your **5 best and 5 worst closed trades**; and realised profit by stock. *Realised profit* is booked when you sell or cover and is net of the fees you paid to open the position; *unrealised* is what you'd make or lose if you closed now (before the exit fee). Total profit = realised + unrealised + dividends − borrow fees − the exit fee on what's still open.
- **History (`/history`):** every trade and payment, newest first, 50 at a time with **Load older**. Filter chips: All, Trades, Buys (buys and covers), Sells (sells and shorts), Dividends, MB added (the fee column stays in the table; there is no separate fees tab). **MB that was added says where it came from**: *Starting MB*, *Reward* (a challenge or a ladder quest), *Free restart*, *Added by an admin* (the ledger keeps the source; `GET /api/history` returns it as `src`). **Borrow fees are charged every few minutes while a short is open, so back-to-back ones in the same stock are folded into one row** ("Borrow fee ×4", the fees and cash added up), and an amount under 0.01 MB is shown with four decimals rather than as 0.00. **A stock that was delisted can still be opened from here:** click its ticker and you get its stock page with the chart, the financials, the cast and the news log, marked *Delisted* with no buy or sell buttons (the game keeps the last 60 delisted companies' pages). Columns: time, type, ticker, shares, price, amount, fee, realised P/L (on closing trades only) and cash change. **Download CSV** gives the whole history, oldest first, for a spreadsheet (§12). The page refreshes itself every 15 seconds.
- **Leaders (`/leaders`):** the two boards of §10.3 as tabs (only people who have traded appear on them), with your row highlighted and your rank (or "not on this board yet") and drawdown underneath. Names link to profiles (bots, marked 🤖, don't).
- **Social (`/social`):** *Chat* (the share-a-trade menu; a note when you are muted, with the appeal box, or how many trades are left before you can chat; a red dot on the nav when something arrives elsewhere) and *Following*. There are no clubs.
- **Profile (`/profile`):** your ranks and worst drawdown, today's three quests, the quest ladder (§10.11), the **daily contest** (join button, your paper equity, rank and return, the paper trading panel, the leaders, the last results, where contests nobody entered are folded into one line; §10.4), all achievements (an unlocked one shows when, on its own line), your medals, the privacy checkbox and your **account** (is there a password, set or change it, log out other devices, log out; §10.6).
- **Player (`/player/{name}`):** another trader's public profile (§10.5) with a Follow button.
- **Bots (`/bots`):** the player's trading bots and backtests (Expert, §10.12). **The bot guide** (`/bots/guide`): how to set one up and every command a rule can use (§10.12).
- **Index and fund pages** (the MSI 50, the sector indices, the themed ETFs, the leveraged products; since 2026-10-23): under *About the index* or *About the fund*, **Holdings** in place of the company news: every holding with its weight (a bar and a %), its live price and 30-minute change, biggest first, built the way the index is (`engine.holdings_for`: the MSI 50 by market value, a sector index by company size, a themed ETF in equal weights, a leveraged product a multiple of what it tracks); a row opens that stock's page.
- **In the header** (since 2026-10-23): the **MSI 50** figure is a link to the MSI 50's page, and beside the session chip a **Daily Chart** button ("Daily" on a phone) opens the Daily Chart (§10.13).
- **The market table** has a **Mkt cap** column after the price (click to sort; the funds show "-"); on a phone the sort box has *Largest companies first* instead.
- **The portfolio's equity chart** (redrawn 2026-10-23): the equity line over a gradient (green when above the money paid in, red below), a dashed line at the money paid in, a legend (*Equity*, *Money paid in*), a scale on round numbers, five times along the bottom, and under the pointer the worth at that minute and the gain or loss against the money paid in.
- **Daily (`/daily`):** the Daily Chart, a two-minute game on one mystery stock, the same chart for everyone that day, with the day's board (§10.13). Reached from the **Daily Chart** button in the header, beside the market's session chip, on every page (not from the menu; filled in while on the page).
- **The stock page's Options tab** (beside *Chart*): the option chain, the buy box and your contracts on the stock (§4, "Options"). The chart, its tools and the timeframe buttons are hidden while it is open. **Leverage** (Pro) is a box beside the size chips; the position box shows the leverage, margin, loan and the price where the position closes by itself (§4).

Messages from the game (achievements, quests, contest results, margin calls) stack in the top-right corner for five seconds and **never cover a trade result**, which shows at the bottom of the page.

In **pre-market** a thin amber banner and in **after-hours** a thin purple one say that trading is thin and prices move less (§6.8), on the market and stock pages (where you trade); on every page the header chip names the session and counts down to the next one. Nothing is ever disabled.

**The look: a trading terminal** (since 2026-10-18, ROADMAP U9). Near-black panels (`#08090b` page, `#0d1013` panels), one accent colour, teal `#4cc3cc` from the logo, and plain green `#3ad07a` and red `#f25c54` for gains and losses; the same hex values are used in the charts, the admin page and the test checkout. **Every page uses one font** (since 2026-10-23, on request): the system's monospaced font (`--mono`: Cascadia Mono, SF Mono, Consolas...), for the interface, every number and the paragraphs alike, on the game, the about, terms and privacy pages, the test checkout and the admin page; buttons, fields and menus inherit it; no web fonts are loaded. Paragraphs are 13 px (lessons 13.5 px), like the rest. Corners are square (2 to 3 px), panels are flat with no shadows, a panel's title is bold with a rule under it, and figures sit in a ruled grid rather than in boxes. The menu marks the current page with a teal line under it. Buy and Sell are outlined in green and red and fill in on hover; the stock page's own Buy and Sell are solid. There are no emoji: no industry icons, medals read 1st, 2nd and 3rd, the ladder's tiers are told apart by their coloured edge, an unlocked achievement by its teal edge. **A ticker tape** under the header scrolls the 40 biggest companies (price and ▲/▼ change, each a link to its page); its prices update in place so it never jumps, it pauses under the pointer, and it stands still for people who ask their system for less motion. Help text is a sentence or two; the long explanations are in the lessons, the about page and here.

**Consistency rules** (the look of every page, kept the same since the polish pass of 2026-10-14, checked again on every page on a laptop and a phone on 2026-10-23: one font, no text overlapping other text, nothing wider than the screen, spelling, capitals):
- **Green and red follow the number as it is shown.** An amount that rounds to 0.00 MB, or a return that rounds to 0.0%, is plain and has no sign ("0.00 MB", "0.0%"), never a green "+0.00".
- **Every progress row looks the same**: the daily quests, the ladder quests and the Learn page's challenges each have the name and description on the left, the progress (and reward) on the right and a thin bar underneath.
- **Every page except the market is centred, at most 1,240 px wide**, and a table never runs out of its card (the holdings table scrolls inside its card on a narrow laptop). A lesson is read in a narrower card (860 px). The portfolio's ten figures are two rows of five.
- **Text columns are left-aligned and number columns right-aligned** (the shop's MB column).
- **The shop puts *Before you buy* (the birth year and the over-18 tick box) above the packages**, and while Buy is off a line under *MB packages* says what turns it on. Package and Pro cards are the same width (at most 210 px).
- **The admin page uses the game's colours, font and corner radius**, with even gaps between its rows of cards and a pinned header.
- Plurals are written out ("1 position", "2 days", "3 devices", "1 entry"), never "position(s)"; an unranked player's rank is "-", never "#-".
- **Numbers have thousands separators everywhere**, the header too ("1,042.65 MB"); dates are written "23 Oct" or "22 Nov 2026", never "22/11/2026". British spelling (realised, colour, centre). **Take-profit** and **stop-loss** are hyphenated, as nouns and as labels.
- **A chart's price-scale label never hides under a price tag**: a label within a tag's height of the price now, your average entry or an order is left out (the stock chart and the Daily Chart).
- **The menu keeps *Market* highlighted on a stock's page** (as it keeps *Leaders* highlighted on a player's page).
- **Controls appear when they can be used**: the holdings page shows its size chips only once you hold something.
- **Placeholders fit their box on a phone** ("Say something", "The plan: why this trade, and when you get out"); the rules they used to carry are in the hint under the box.
- **On a phone, achievements and shop packages are two to a row**, so neither list is a long single column.

The table and chart are updated **in place** (not rebuilt) every second, so a click is never lost to a redraw.

### On a phone (screens under 760 px wide)
The same page serves laptops and phones; a set of rules in `index.html` that applies **only below 760 px** turns it into a phone layout, so the laptop view is exactly as before. Before this (2026-10-06) the market, holdings, portfolio and history tables were up to 956 px wide on a 390 px phone and scrolled sideways, hiding the 30m change and the Buy and Sell buttons, and the header took about 40% of the screen and stayed there. Now:
- **The header is compact and pinned.** The logo and the market chip share one row, the menu is **one row you can swipe sideways** (the current page is scrolled into view), and the figures are a 3 x 2 grid plus the day countdown. Only the logo and menu rows stay pinned while you scroll; the figures scroll away.
- **The market is one card per stock:** star, ticker with the company name under it, price, the 30m change, and the Buy / Short buttons, all on screen. The column headings that sort on a laptop are replaced by a **sort box** (A to Z, biggest gainers, biggest fallers, price high or low, my holdings first). The industry chips are one row you swipe sideways. The trend sparkline and the Held column are hidden (the stock page has them).
- **Stock names on the news wire and in upcoming events are links** (since 2026-10-24, on request): on the wire, the name of every company a headline is about (its tickers) and the `[TICKER]` tag after it open that stock's page, underlined faintly so they show in a headline of any colour; in *Upcoming events* a company's ticker (teal) and name do the same (a macro release has no link).
- **The news wire, upcoming events and the leaderboard are above the table, folded**: the news wire is open (about 200 px, scrolls), the other two open when you tap their heading. On a laptop they sit beside the table; on a phone they would otherwise be below 190 stock cards.
- **Holdings and the portfolio's open positions are cards**, each figure with its label (side, shares, average entry, price, value, dividends, P/L), and big Buy / Sell (or Cover / Short) buttons. **So are the open orders, the option positions and the history** (since 2026-10-23: they used to scroll sideways, hiding the Sell and Cancel buttons): each row a card with a label on each figure, the buttons full width, and the history's empty figures left out. The closed-trade tables and the following list still scroll sideways inside their card.
- **The chart is drawn for a phone** (a 400-unit-wide drawing instead of 960) so its price labels are about 9 px on screen instead of about 4; the period buttons wrap into rows.
- **Fields are 16 px**, so iPhones do not zoom in when you tap one; buttons are at least 34 px tall; pop-up messages sit at the bottom of the screen instead of covering the header.
- The grid no longer lets a wide table stretch the page (`minmax(0, 1fr)`), so **no page is wider than the screen**.
`tests/test_browser.py` (`BrowserPhone`) drives the pages in a 390 x 844 touch browser and checks all of this, including that no page is wider than the screen, that the header stays at the top while scrolling, and that the laptop layout (table headings, the pinned header, unfolded side panels) is unchanged. Not done yet: a pull-up trade ticket instead of the buttons on each card, and installing the game as an app on the home screen (`ROADMAP.md`, E6).

### Candles and timeframes
The engine keeps real-time candles for 11 timeframes, each updated on every tick: **30s, 1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1M, 1Y**, where 1d is 24 real hours, 1M is 30 real days and 1Y is 365 real days. Each timeframe keeps its last 500 candles in memory and in the save. **A chart shows up to 2,000 candles in every timeframe** (`CHART_CANDLES`; since 2026-10-24, on request; it was 500, and 1,440 for 1m): each finished candle is also written to `data/minutes.db`, the one-minute candles to its `candles` table (three real days) and every other timeframe's to a table of its own (`tf_30s`, `tf_5m` ... `tf_1y`, each trimmed once an hour to its last 2,010 candles), and a chart takes its older candles from there (`Engine.chart_for`). Memory and the save stay at 500 a timeframe because the chart file is saved inside the game's tick: at 2,000 it would grow to about 200 MB and hold the game up for many seconds every five minutes. Candles of a long timeframe fill in over real time, so a fresh server shows few 1d, 1M or 1Y candles, and 2,000 of them take years. **A chart refreshes itself every 10 seconds with only its newest candles**: it asks with `since` (the start of its newest candle) and the answer, when memory still reaches back that far, is the candles from then on (`since` in the reply), which replace its newest and join the end (a page keeps at most 2,000); without `since`, or from too long ago, it gets the whole chart. This keeps a 2,000-candle chart from being sent in full every 10 seconds (about 170 KB each time).

**Game time was taken out again** (on request, 2026-10-21): the chart offers only the real-time sizes. (For one day it also offered **GAME D W M**: a candle per **game day**, **game week** (Monday to Sunday of the game calendar, §6A.6) or **game month**, with game dates on the time scale ("12 Mar", "Jun Y5") and in the readout ("27 Jul Y7", "Week of 24 Jul Y7"). A game-day candle covers **the regular session only** (00:05 to 00:25 of the 30-minute cycle), like a real daily chart, so the move from one close to the next open (after-hours, pre-market and the opening jump, §6.8) shows as a **gap** (TA-A7); it grows on the page only while the regular session is on. They come from the **long history** (TA-A10, `history.py`): every listing's game days are written to `data/history.db` as each session closes and kept for `history_game_years` (10) game years; each listing keeps its last 400 in memory (`Stock.days`, for the price model's daily levels), with today's session under way in `Stock.reg` (saved). A chart gets up to 1,500 game days (about four game years); weeks and months are built from up to ten game years. A game from before the file existed gets its game days rebuilt once from its 5-minute candles (the regular sessions of about 80 game days) and its 30-minute ones (whole game days, further back).) The game days are still written to `history.db` and read back for the price model's daily levels.

### Chart behaviour
- The **newest candle sits in the middle** and everything shifts left as candles arrive. The first candles are **thick** and get thinner as more are created, down to a minimum width.
- **Zoom** with the buttons or the scroll wheel (around the pointer). You can **zoom out as far as you like**, well past the first candle. **Drag** to pan. "Reset view" restores the default.
- The vertical scale fits the candles currently in view, plus the live price and your average price, until you **drag the chart up or down**: the chart moves in any direction (sideways through time, up and down through prices), and the first clear vertical drag (8 pixels) takes the price scale off automatic so it stays where you put it. **Fit prices** (shown only then), a double-click on the chart or **Reset view** puts it back on automatic; a new stock or candle size starts on automatic. **Drag up or down on the prices at the right** (or scroll over them) to stretch or squeeze the price range around its middle: down shows a wider range (the candles get shorter), up a narrower one (they get taller); a double-click on the prices puts the scale back on automatic.
- **Lines with a tag on the price scale** (ROADMAP TA-B6): the live price (teal), your average entry if you hold the stock (amber, dotted) and **your open orders in this stock**: stop-loss *SL* in red, take-profit *TP* in green, limit orders in grey. Orders within 10% of the price are kept in view; tags that would overlap are moved apart.
- **Your trades on the chart** (TA-B6): a green arrow under the price where you bought or covered, a red one over it where you sold, shorted or were margin-called, at the price you got (hover one for what, how much and when). They come from the money ledger (`GET /api/history?ticker=NVXA`), fetched again whenever your position or orders in the stock change. **My trades** under the chart switches them off.
- The current candle updates with the live price; when a new time bucket starts, the page opens a new candle.
- The "30m" change is the current price vs the price 1,800 s ago (from the minute candles). The trend sparkline is the last 60 one-second prices.
- **Volume** bars sit under the price (green for a candle that closed up, red for down), scaled to the tallest bar in view (§6A.5).
- **Chart types and the price scale** (TA-B2), in the box under the chart: **candles**, **hollow candles** (a candle that closed up is an outline), **bars** (OHLC: the open as a tick to the left, the close to the right), **line** (the closes) and **Heikin-Ashi** (each candle averages its prices with the one before: open = the middle of the previous candle's body, close = the average of open, high, low and close, so a trend reads as a run of one colour; the readout shows these values, the indicators still use the real prices). **Log** switches to a logarithmic price scale, where equal percentage moves are the same height; dragging and stretching the scale then work in percentages too.
- **The crosshair and readout** (TA-B1): over the chart the pointer has a crosshair with the price at its height on the right and the candle's time at the bottom. The **readout** above the chart shows that candle (date and time, open, high, low, close, the change from the candle before, volume) and the value of every indicator on it, each in its own colour; with the pointer elsewhere it shows the newest candle. On a touch screen a tap puts the crosshair on a candle and a drag moves the chart.
- **Indicators** (the **Indicators** button above the chart): a box that searches **49 indicators** by name, group or keyword ("average", "rsi", "fib", "volume", "trend"; the descriptions are searched only when nothing else matches), with All / Free / Pro / On tabs. Each row says what the indicator means and whether it is **FREE** or **PRO**. Switched-on indicators show as chips with a × to remove them; the choice is remembered in the browser. Everything is worked out in the page from the candles it has (nothing changes in the game).
  - **Free (17):** SMA 10, 20, 50, 100 and 200; EMA 9, 12, 20, 26, 50, 100 and 200; **Auto Fibonacci** (the 23.6% to 78.6% retracement levels between the highest and lowest price on screen, measured in the direction of the move); **RSI 14**, **Stochastic** (14, 3, 3) and **Momentum** (10) panels; and the 20-candle **volume average** over the volume bars.
  - **Pro (32, §10.9):** WMA, Hull MA, DEMA, TEMA and VWMA (20); Bollinger Bands (20, 2), Keltner Channels, Donchian Channels, Envelopes and a 100-candle regression channel; VWAP and pivot points (P, R1, R2, S1, S2 from the previous game day; both on intraday charts only); Parabolic SAR, SuperTrend and the Ichimoku Cloud (drawn 26 candles ahead); and panels for MACD, Stochastic RSI, CCI, Williams %R, rate of change, the Awesome Oscillator, TRIX, the Ultimate Oscillator, ADX with +DI/-DI, Aroon, ATR, historical volatility (yearly, in game time), Bollinger bandwidth and %B, on-balance volume, the Money Flow Index and Chaikin Money Flow. A Pro indicator a player switched on while Pro stays listed (greyed) after Pro ends and draws again when it comes back.
  - Over-the-price indicators draw on the candles (bands and clouds shaded) with their names in a legend; each oscillator gets its own panel under the volume, with its reference levels (70/30, 80/20, zero...) and its latest value. `tests/test_chart_tools.py` checks the formulas against plain Python versions.
  - **Settings for each indicator** (TA-B3): the small sliders button on an indicator's chip opens its settings, applied as you type: its **length** (and, where it has them, a second length, a signal length or a width: MACD's fast, slow and signal; Bollinger's and Keltner's width; the envelope's percentage; SuperTrend's ATR multiple; the stochastic's smoothing), its **source** (close, open, high, low, (H+L)/2, (H+L+C)/3 or (O+H+L+C)/4, for the indicators worked out from one price: the moving averages, Bollinger, envelopes, regression, RSI, momentum, MACD, Stochastic RSI, rate of change, TRIX, the volatility ones and Keltner's middle line) and its **colour**. A changed indicator is named by its settings (*SMA 9*, *MACD (8, 21, 5)*). Ichimoku, pivots, Auto Fibonacci, VWAP, the Parabolic SAR, the Awesome and Ultimate oscillators and OBV have fixed settings.
  - **The chart set-up follows the player** (TA-B3, TA-B4): which indicators are on, their settings, the chart type, the log scale and *My trades* are kept on the server for a signed-in player (`GET/POST /api/chart`) as well as in the browser, so they are the same on another browser or a phone. The first time an account is used with this, it takes the browser's set-up. A visitor keeps it in the browser only.
- **Drawing tools**: a small floating bar over the chart: a grip to drag it anywhere (the position is remembered), the **arrow**, the **last tool you used** (one click to draw another), a **bin** while a drawing is selected, and a **▾** button that opens a drop-down with every tool (icon and name), plus *Hide drawings* and *Clear all*. Picking a tool closes the drop-down again, so the chart stays clear. The drop-down opens upwards or to the left when the bar sits near the bottom or the right edge.
  - **Select** (the arrow): click a drawing to select it, drag it to move it or drag its round handles to reshape it; **Delete** (or the bin) removes it, Esc deselects.
  - **Horizontal line** (a support or resistance level, labelled with its price), **vertical line**, **trend line** (drag from one point to another, or click twice), **ray** (a trend line carried on to the right), **box**, **circle** (drag from the centre), **Fibonacci retracement** (drag from the start of a swing to its end: the 0.236 to 0.786 levels, labelled with their prices and shaded), **brush** (hold and draw), **path** (click each point; double-click, Enter or tapping the last point again finishes) and **head and shoulders** (click its 7 points; it labels the shoulders and the head and draws the neckline).
  - **Long position** and **short position**: one click at the entry places a target box (green) and a stop box (red), 3 and 1.5 average true ranges away (a 2R trade); it shows the target and stop prices with their percentage moves and the reward-to-risk ratio. Drag the edges to change the target, the stop or the length, or the entry handle to move it. It only draws: nothing is traded (the risk tool and the bracket do that).
  - **Parallel channel** (click the two ends of the first line, then a third point for the width: a shaded channel with a dashed middle line) and **Fibonacci extension** (click the start of a move, its end, and the end of the pullback: levels at 0, 61.8%, 100%, 127.2%, 161.8%, 200% and 261.8% of the move, measured from the end of the pullback, the usual targets) (TA-B4).
  - **Text note**, an eye to hide and show the drawings, and a broom to clear every drawing on the stock.
  - Drawings are kept per stock (up to 80), in time and price, so they stay on the right candles when you zoom, pan or change the candle size or scale. For a signed-in player they are kept **on the server** too (`GET/POST /api/drawings/{ticker}`, the 100 stocks changed most recently), so they follow the player to another browser or a phone; the first time a stock is opened, what the browser has is sent up. The server checks every drawing first (known tools, finite times and positive prices, notes of at most 80 characters, colours as #rrggbb; `chartprefs.py`). The levels drawn with the old "Draw a level" button became horizontal lines.
- **The chart's size**: drag the bar under the chart to make the price chart taller or shorter (remembered); **Full screen** fills the window with the chart, its indicators and tools (Esc or the button to leave). On a laptop the chart is drawn at the width of its box, so text stays the same size however wide it is.
- **Position size and risk** (a fold-out under the orders): type a stop-loss (and optionally an entry), pick the risk (0.5%, 1% or 2% of equity) and a target (1.5R, 2R, 3R); it says how many shares to buy or short, what that costs, what you lose at the stop and make at the target, and **Fill in the trade and the bracket** puts the amount in the trade box and the stop and target in the bracket (you still press Buy and Set bracket). A stop above the entry means a short.

---

## 12. Server and protocol

### HTTP
Player endpoints need the player's **session token** in an `X-Token` header (the page sends it; a missing or wrong token gets **401**). Admin endpoints need `X-Admin-Key` (**403** without it). Lookups are rate limited per player: a call that comes too soon gets **429** `{"error":"slow down"}` (the page waits 0.45 s and tries once more).

| Endpoint | Who | Purpose |
|---|---|---|
| `GET /`, `/stock/{ticker}`, `/holdings`, `/portfolio`, `/history`, `/leaders`, `/social`, `/profile`, `/player/{name}`, `/learn`, `/calendar`, `/shop` | anyone | the web page (`Cache-Control: no-store`) |
| `GET /shop/pay` | anyone | the pretend checkout page of the test mode (§10.9) |
| `GET /api/auth_mode` | anyone | `{passwords, email, mail_ready}`: whether accounts need passwords, the `email_mode` (`off`/`optional`/`required`) and whether mail can really be sent (the sign-in box asks this) |
| `GET /api/calendar` | anyone | the economic calendar (§6A.6): `{on, upcoming: [{t, kind, name, forecast}], past: [releases with actual, consensus, text, growth_z, rates_z, market_z], rate, bank, earnings: [{ticker, name, at, forecast}]}` |
| `GET /api/calendar/month?offset=0` | anyone | the calendar page's month grid: `{on, offset, title, today, weeks: [[{n, day, label, in, today, t, macro: [{kind, short, name, t, forecast or out, text, consensus, unit, z}], earnings: [{ticker, name, t, forecast or out, eps, beat}], events: [{ticker, name, t, label}]}]], rate, bank, now, day_seconds}`; `offset` is clamped to ±24 months |
| `POST /api/ladder/style` `{title, color}` | player | wear an unlocked title and name colour ("" for none) |
| `GET /api/learn` | anyone | the tracks and lessons (with which a player has read), the chart tests with the player's scores, and the challenges when they are on (§10.10) |
| `GET /api/learn/lesson/{id}` | anyone | one lesson: its blocks, track, and the lessons before and after; with a player's token it counts as read |
| `GET /api/learn/test?kind=` (`&example=1`) | anyone | a chart test (`kind` from `drills.KINDS` or `any`): `{id, title, q, options, tf, candles, lines, marks, overlay, panel}`; with `example=1`, a lesson's example with its answer; about three a second of each |
| `POST /api/learn/test` `{id, choice}` | anyone | mark a chart test → `{right, answer, result, explain, candles (what came next), lines, marks, where, score}` (`score` for a player); `{expired: true}` if it is unknown or over 3 hours old |
| `GET /api/shop` | player | the catalogue with prices, Pro status, the age and spending rules, the last 30 purchases, the free restart's status, MB by source, `selling` and the payment `mode` (§10.9) |
| `POST /api/shop/checkout` `{sku, consent, renew_ok}` | player | start a purchase → `{url, order, price}` (the payment page, or `/shop/pay?order=` in test mode); a monthly pass needs `renew_ok`; 400 with the reason (age, cap, daily limit, a monthly pass of that tier already renewing, shop closed) |
| `POST /api/shop/cancel` `{kind}` | player | cancel a monthly Pro or Expert: no more payments (at Stripe too), on to the end of the month paid for → `{ok, msg}` |
| `GET /api/shop/order/{id}` · `POST /api/shop/test_pay` `{order, action}` | player | the test checkout (PAYMENTS=test only; 404 otherwise): pay or cancel your own order |
| `POST /api/shop/stripe/webhook` | Stripe | only with a valid `Stripe-Signature` (PAYMENTS=stripe only): `checkout.session.completed` completes a paid order (and starts a monthly pass's subscription), `invoice.paid` for a later month adds 30 days, `customer.subscription.deleted` ends a subscription |
| `POST /api/admin/payment_check` | admin | run the payment check now (Stripe only): completes paid orders whose webhook never came |
| `GET /terms` · `GET /privacy` | anyone | the terms of use and the privacy policy |
| `POST /api/account/birth_date` `{date}` | player | an account from before dates of birth were asked gives it once ("YYYY-MM-DD") |
| `POST /api/restart` · `POST /api/close_all` | player | the free restart; close every position at the market price (and sell every option) |
| `GET /api/options/{ticker}?exp=` | anyone | one expiry of the option chain (§4; the second expiry when `exp` is left out or gone): `{ticker, price, exp, expiries, term (ATM IV of each expiry), forward, carry, iv, div, div_t, earnings, now, fee, rows: [{K, call: {bid, ask, mid, iv, delta, gamma, theta, vega, rho, itm, oi}, put: {...}}]}`; worked out once a second however many ask; `{error}` for a listing without options |
| `POST /api/options/buy` `{ticker, kind, strike, expiry, contracts}` · `POST /api/options/sell` `{id, contracts}` or `{id, fraction}` | player | buy whole contracts (100 shares each) at the ask (`amount` MB instead buys as many whole contracts as it pays for: the bots); sell whole contracts back at the bid (more than held: all of it), or a fraction of the position (1: all). `{ok, msg}` |
| `GET /api/daily` | player | the Daily Chart (§10.13; 404 if `daily_chart` is off), with `number` and the player's `stats`, and in a finished `game` the `grid`: `{day, live, history, cash, chips, status (new, running or done), board (the top 20: name, ret, trades), players, past (the last 7 days' top three), next (when the next chart comes), game (the player's game, if any)}` |
| `POST /api/daily/start` · `GET /api/daily/state?since=` · `POST /api/daily/trade` `{side, pct}` | player | start today's game (once a day); the candles shown so far from `since` (never one still to come), the cash, the shares (negative: a short), the price, the total, the trades and the time left, or at the end the whole chart, the return, the place, `dist` (every finished player's return, no names), `hold` (the stock's own return) and its high and low; `side` buy (`pct` of the cash, or covering `pct` of a short) or sell (`pct` of the shares, or with none a short of `pct` of the account), `pct` 0.25, 0.5, 0.75 or 1, at the last candle's close |
| `GET /api/bots` | player | the player's bots, whether Expert is on, the limits, the candle sizes, the default news words and what a rule can use (§10.12) |
| `POST /api/bots/save` `{bot}` · `/toggle` `{id, on}` · `/delete` `{id}` | player | save a bot (checked first: Expert, stocks, rules that parse; 400 with the reason), switch it on or off, delete it |
| `POST /api/bots/backtest` `{bot, ticker, timeframe, bars, cash}` | player | run a bot over the past (Expert; one every 3 s): `{return, buy_hold, trades, win_rate, avg_win, avg_loss, profit_factor, max_drawdown, fees, exposure, curve, log, candles, from, to, note}` or `{error}` |
| `GET /api/admin/shop` · `POST /api/admin/refund` `{id}` | admin | sales, Pro members, MB by source, the latest orders; mark a paid order refunded |
| `GET /api/admin/errors` | admin | every error the server has logged since it started (ROADMAP E13, `errortrack.py`): each kind (where it was raised and what it was) with how often, when it was last seen, the last message and its traceback; at most 100 kinds |
| `GET /js/chart.js` · `GET /js/bots.js` · `GET /js/daily.js` | none | the chart's, the Bots page's and the Daily page's scripts (`web/`), checked against the browser's copy on every load (`no-cache`) |
| `GET /api/admin/model` | admin | the price model behind the scenes: phase, days left in it, the hidden economy, how many listings trend or range, levels under test |
| `GET /api/health` | anyone | for an outside uptime monitor: `{ok, tick_age_s, saved_ago_s, uptime_s}`, **200** while the game has ticked in the last 15 seconds and saved in the last five minutes (the first three minutes after a start are forgiven), **503** when it is stuck. No key, nothing private, never rate limited; it works through a gateway, and if the game or the server is down the gateway or Caddy answers with an error, so a monitor sees that too |
| `POST /api/register` `{name, password, birth_date, email?}` | anyone | create an account → `{token, name}` (a session token), plus `email_sent`/`email_msg` when an address was given and its code was mailed. 400 with the reason for a weak password, a taken or reserved name, a bad, disposable or already used address (or a missing one in `required` mode); 429 after too many sign-ups from one address |
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
| `GET /api/history?limit=50&before=<seq>&kind=buy,sell&ticker=NVXA` | player | the ledger, newest first, with paging (`next_before` is the cursor), kind filters and one stock's entries with `ticker` (the chart's trade markers); `limit` is capped at 500 |
| `GET /api/chart` · `POST /api/chart` `{ind, set, ctype, log, trades}` | player | the chart set-up kept for the player: indicators on, their settings, chart type, log scale, trade markers (`chartprefs.py`, §11) |
| `GET /api/drawings/{ticker}` · `POST /api/drawings/{ticker}` `[drawings]` | player | the player's drawings on one stock (up to 80), checked before they are kept (§11) |
| `GET /api/history.csv` | player | the whole history as a CSV file download (one per 2 s) |
| `GET /api/me` | player | achievements, quests, the daily contest (with your paper account), following, ranks, drawdown, privacy, mute and appeal status, whether you can chat yet, and whether you have a password and how many devices are logged in |
| `GET /api/boards` | player | the day and all-time leaderboards (top 20 each, only people who have traded in that period) with your ranks (`null` if you are not on a board), how many are on each (`counts`) and your worst drawdown today |
| `POST /api/tournament/join` `{id}` | player | enter the daily contest and get its paper balance (§10.4) → `{ok, msg}` |
| `GET /api/profile/{name}` | player | another player's public profile (§10.5); 404 if unknown |
| `GET /api/following`, `POST /api/follow` `{name}`, `POST /api/unfollow` `{name}` | player | the follow list |
| `POST /api/public` `{public}` | player | set your privacy |
| `GET /admin` | anyone | the admin dashboard page (shows nothing until the key is entered) |
| `GET /api/admin/overview` | admin | the dashboard's live numbers, in one call: `online_players` (who is on now), `stats` (house P&L breakdown, deposits, invariant drift, `borrow_fees`, `short_shortfall`, `short_interest`, `recapitalized`, `risk` (§6.11)), the series, funnel and `perf` (server timings) |
| `GET /api/admin/insights` | admin | the deeper numbers the dashboard asks for every 20 seconds: market and game state, activity over time from the ledger, biggest players and positions, orders, chat and moderation counts, the settings in effect, the machine (`ops`), connections, and the wrong-key log (`security`) |
| `GET /api/admin/players` | admin | every account, newest first: name, joined, last seen, email (and verified), pass, equity, P&L, return, trades, positions, the link they came by |
| `GET /api/admin/player/{name}` | admin | one player's holdings and last 100 trades |
| `GET /api/admin/chat` | admin | latest chat messages, reports, who is muted, open and decided appeals, the moderator log, running contests |
| `POST /api/admin/appeal` `{id, decision}` | admin | `lift` or `deny` a muted player's appeal |
| `GET /api/admin/accounts` | admin | how many accounts have passwords, how many have a verified email, the `email_mode`, mail status, how many logged-in devices, and which accounts share an address (never the address itself) |
| `GET /api/admin/mail` | admin | whether mail is configured, how many were sent or failed, and the recent messages (in console mode with their codes) |
| `POST /api/admin/email` `{name, action: verify\|clear}` | admin | mark a player's address verified, or remove it |
| `POST /api/admin/delete_player` `{name, confirm}` | admin | delete an account for good (§10.6): `confirm` is the name again; a renewing monthly pass is cancelled at the provider first → `{ok, msg}` |
| `POST /api/admin/reset_password` `{name}` | admin | give a player a temporary password (returned once) and end their sessions |
| `POST /api/admin/reset` `{confirm: "RESET"}` | admin | back up the save and the ledger into `data/backups/`, then start the game over at Day 1 (§1, §10) |
| `POST /api/admin/chat/delete` `{id}` | admin | delete a chat message (everyone's screen updates) |
| `POST /api/admin/mute` `{name, seconds}` | admin | mute a player's chat (`0` lifts it) |
| `POST /api/admin/credit` `{name, amount, note?}` | admin | add MB to a player (source `admin`, counted as money put in so it never lifts a return or rank); the player gets a message with the note. 400 unless 0 < amount ≤ 1,000,000; 404 for an unknown name (names match whatever the case). The admin page's **Accounts** card has the form (Add MB / Take back MB, with a confirmation) |
| `POST /api/admin/pro` `{name, days?, remove?, tier?, note?}` | admin | `tier` is `pro` (the default) or `expert`: give a player that pass for `days` more days (added to any Pro they have, bought or given; 400 unless 0 < days ≤ 3,650) or end it now with `remove` (bought time included). Pro is tools only, so no MB move and nothing is ledgered; the game saves at once. The player gets a message with the note. 404 for an unknown player |
| `POST /api/admin/withdraw` `{name, amount, note?}` | admin | remove MB from a player's free cash (taken off the `admin` source, so the sources still add up); the player gets a message. Same limits |

Every handler runs its engine work in a worker thread under the engine lock (see "Threads" below), so none can freeze the game.

Admin endpoints need the `X-Admin-Key` header to match the `ADMIN_KEY` environment variable. They are disabled if it isn't set.

`GET /internal/gateway` is a websocket for gateways only (§12, "Gateways"). It needs the `CORE_KEY` environment variable to be set and the same key in the `key` query parameter; with no `CORE_KEY` the door is shut.

### Admin dashboard (`/admin`)
**In plain English:** one page where you can watch the house. Is money being created or destroyed? Is the house winning or losing? Who is winning, and how? Is anyone getting margin-called?

**How to open it**
1. Start the server with an admin key: `$env:ADMIN_KEY = "a-long-random-string"` (see §1).
2. Open `http://127.0.0.1:8000/admin`, type the key and press Enter.
3. The page refreshes every 5 seconds: the overview and chat every time, the open tab's own data with them (players, shop, market or system), the deeper numbers every 20 seconds; a refresh never starts while the last one is still running. The key is kept in that browser tab only (session storage) and sent in a header; it is never in the URL or the page. Press **Lock** to forget it. A wrong key is refused and the page locks again.

**What's on the page** (redone 2026-10-26, on request: "way easier to use and look at"). A header with **Find a player** (names suggested as you type; Enter opens the player), when it last updated, *Open the site* and **Lock**; under it six **tabs** (remembered in the address, e.g. `/admin#players`). *Chat* shows a red count of reported messages and open appeals, *System* of machine warnings. An action's result appears as a small message in the corner. Every list of players is clickable and opens that player on the Players tab.

| Tab | What is on it |
|---|---|
| **Overview** | **Alerts** at the top (every rule below in one list, or a green "All good"); **Online now** (since 2026-10-26, on request: who is on, `online_players` in the overview: each signed-in player with a page open, with their pass, equity, return, trades, positions and how many pages they have open; click one to open them on the Players tab; visitors without an account are only counted); ten figures: players (signed up today, seen in 24 hours), on now (signed-in players, and visitors), trades (and per minute), total MB (started with, bought), players' P&L (on the money put in), fees (and borrow fees), margin calls, short interest (and shortfall), **Books** (balanced, or the token drift in red) and the game tick; *Who is on* (player pages and visitors, last 2 hours); *Trades per hour* (24 bars, your time, details on hover); *The last 7 days* (sign-ups, traders, trades, money traded, fees per UTC day); total MB and fees, and players' combined P&L (charts of the last 2 hours) |
| **Players** | **Every account** (`GET /api/admin/players`, newest first): name, pass, email (with a tick when verified), joined, last seen, equity, return, how many they invited; a search box (name or email). **The picked player**: their email, when they joined, date of birth, the link they came by (or who invited them), their invite code and whom they invited, their pass and a renewing monthly one; equity, cash, P&L, trades today; **Actions** on that player without typing the name again: **Add / Take back MB** (with a note), **Give / Take away Pro or Expert** (days, note), **Reset password** (the temporary password shown once, ready to copy), **Mark email verified**, **Remove email**, **Mute 1 hour**, **Unmute**, **Delete account** (the name typed again); their open positions and last 100 trades. The panel does not refresh while you type in it. Below: top by profit, *How far people get* (the funnel and sign-ups a day), the biggest players (richest, most trades today, most fees), everyone's all-time return in bands, and **Accounts** (counts, and accounts that share an address) |
| **Shop** | The payment mode and **Check payments now** (Stripe); revenue (all time, 30 days), paid orders, buyers, Pro and Expert members, refunded, waiting; revenue a day; **Latest orders** with **Refund** (after refunding in Stripe); *Where players came from* (`?ref=` links: sign-ups, buyers, revenue); where the players' MB came from |
| **Chat** | Reported messages (grouped, with who reported them) with **Delete** and **Mute 1h**, and who is muted with **Unmute**; **Appeals** with **Lift mute** / **Keep mute**; the latest 60 messages with **Delete**, **Mute 10m**, **1h**; the moderator log |
| **Market** | Game day, MSI 50, listings, news in the last hour, the next event, delisted so far, open orders, positions; the price model (phase, the hidden economy, how many listings trend or range, levels being tested); most traded stocks (24 hours); biggest open positions; **House risk** (reserve, stress loss, the stocks players hold most of); recent margin calls; orders and contests |
| **System** | Server up for, memory, disk free, last save, last backup, the ledger, connected now; errors since the server started (open one for the traceback); **Email** (whether it is set up, the last messages); admin security (wrong keys, lock-outs); **Settings in effect** (folded); the **Danger zone**: type `RESET` to start the game over at Day 1 (asks once more) |

**Alert rules**

| Alert | Raised when |
|---|---|
| Red: token drift | the money-conservation check is above 0.000001 |
| Amber: one stock is the risk | one stock is more than half the stress loss (and over 1,000 MB) |
| Amber: shortfall | a gapped short has cost the house anything |
| Amber: a player is far ahead | the best human is up more than 50% with at least 20 trades (look at their trade log) |
| Red / amber: the disk is nearly full | less than 5% (red) or 15% (amber) of the disk is free; the game cannot save when it is full |
| Red: no recent save | the game has not written its save for two minutes (it saves every 30 seconds) |
| Amber / red: an old backup | the newest backup is over 8 hours (amber) or over 24 hours (red) old, when the backup folder exists (the job runs every 6 hours) |
| Red: someone was locked out | an address was blocked from the admin interface in the last hour (below) |
| Amber: wrong admin keys | five or more wrong keys in the last hour |
| Amber: reports and appeals | reported chat messages or open mute appeals are waiting |

**Admin lock-out.** Every wrong admin key is counted per address (the real caller, also behind the proxy or a gateway). **Ten wrong keys within ten minutes from one address lock that address out of the whole admin interface, even with the right key, until the oldest of them has aged out** (the answer is 429 "too many wrong keys: try again in N s"); the players' side of the game is not affected. The count, the lock-outs and the last 15 attempts (time, address, what) are on the dashboard. On **memestreet.net** there is also a second password in front of the whole admin interface (`/admin`, `/admin/*`, `/api/admin/*`), asked for by Caddy before the request reaches the game (`deploy/DEPLOY.md`, step 7; done 2026-10-10, and the admin key was replaced at the same time). The browser asks for it once, then the admin page asks for the admin key as usual; both are in `live_admin_credentials.txt` in the project folder, which git ignores. The admin page itself stops at the first refusal, so typing the key wrong once or twice never gets near the limit.

**What backs it.** The engine keeps each player's last 100 trades (saved with the game), a log of the last 50 margin calls, counters, and a sample of house and player money every 10 seconds (in memory only). `engine.admin_overview()` and `engine.admin_player()` build the data; `server.py` serves it. Everything on the page is also available as JSON from the two endpoints.

**Limits.** There is no rate limit on admin-key guesses yet (see `ROADMAP.md`, A10), so don't expose `/admin` to the open internet without HTTPS and a long key.

### The WebSocket protocol (`/ws?token=…`)
**In plain English:** when a page connects, the server sends it **everything once** (`init`). After that, every second it sends only **what changed** (`tick`): the prices, your own numbers, and any new headlines. Slower-changing facts (ratings, margin and borrow numbers, financials, the leaderboard, the earnings calendar) come every fifth tick, and only when they changed. This replaced sending the whole market (about 120 kB) to every player every second.

**Visitors.** A page with no account connects with the token `guest` (`/ws?token=guest`). The game attaches it to **one hidden, read-only guest player** (`Engine.guest`, the same for every visitor): it is never in `players` or `by_token`, has no money, is not counted in the player count, and **cannot be logged in as** (it is looked up only by the websocket, never by `player_for`, so a request to any ordinary page with `X-Token: guest` is refused with 401). A visitor's connection gets the same `init` (with empty chat, cash 0 and no holdings) and the same ticks as a player, and may ask for `history`, `company` and `sync`. **Every other message** (trade, order, contest trade, chat, report, appeal) is answered with "Create an account or sign in to do that" and changes nothing. **Chat messages and chat deletions are not sent to visitors** (the game marks them members-only; gateways honour the mark). The admin page counts visitors apart from players ("N online · M watching"). A test runs all of this straight at the game and through a gateway.

**Server → client**

| Message | When | Contents |
|---|---|---|
| `init` | on connect, and again after a `sync` | everything: every stock (static facts including `listed_at`, slow numbers, price, change, a 60-point sparkline), sectors, the index, 30 headlines, the calendar, the leaderboard, your cash/equity/holdings and open orders, recent chat, the session (`market`: phase, whether the regular session is on, what comes next and when), the engine clock `t`, a tick counter `seq` and `static_v`. About 140 kB, once |
| `tick` | every second | `seq`, `t` (engine time), `px` (`{ticker: [price, change]}` for every listing), `idx` (market index value and change), `sec` (sector index values), `market` (the session: `phase` pre/open/after, `open`, `next`, `changes_in`, `pre`, `after`, `cycle`), `season` (the day number) and `season_left` (seconds left in the day), `players`, `news` (new headlines), `static_v`, and **`me`**: your cash, equity, return, P&L, rank, positions and (when they changed) your open orders. Every fifth tick also `board` (top 10), `slow` (rating, borrow fee and crowding, financials: only stocks that changed, everything once a minute) and `upcoming` (only when the calendar changed). About 4-12 kB |
| `notice` | when something happens to you | one-off messages (achievement, quest, contest result, mute or appeal outcome, margin call). Delivered as their own reliable messages, so skipping a tick can never lose one |
| `result` | after a trade, an order, a contest trade, a report or an appeal | `{ok, msg}` (`contest: true` for a paper trade) |
| `history`, `company` | on request | chart candles; the company's cast, news log and earnings history |
| `chat`, `chat_delete`, `chat_error` | chat | a new message (to everyone; the history comes in `init`); a deletion by a moderator or by enough reports; why your message was refused |
| `error` | bad or expired token | the page then shows the sign-in box |

**Client → server**
- `{"type":"trade","ticker":"NVXA","side":"buy","pct":0.25}` (or `"amount": 50` in MB, which overrides `pct`) → `result`
- `{"type":"history","ticker":"NVXA","period":"30s|1m|5m|15m|30m|1h|2h|4h|1d|1mo|1y","since":1761300000}` → `history`: up to 2,000 candles; with `since` (optional, a chart refreshing itself) only those from that start on, and the reply carries `since` (old period names fall back to 30s)
- `{"type":"company","ticker":"NVXA"}` → `company`
- `{"type":"order","action":"place","ticker":"NVXA","kind":"limit_buy|limit_sell|stop_loss|take_profit","trigger":41.5,"pct":0.25}` (or `"amount"` in MB), `{"type":"order","action":"bracket","ticker":"NVXA","take_profit":50,"stop_loss":40}`, `{"type":"order","action":"cancel","id":7}` → `result` (one per 0.2 s)
- `{"type":"contest_trade","id":"marathon-1791...","ticker":"NVXA","side":"buy|sell","pct":0.25}` (or `"amount"`) → `result` with `contest: true`: a paper trade in the daily contest (§10.4)
- `{"type":"chat","text":"...","channel":"global"}` (any other channel is refused), optionally `"share": <time of one of your trades>` → a `chat` message to everyone, or `chat_error`
- `{"type":"chat_report","id":12}` (the third different reporter removes the message and mutes its author, §10.7), `{"type":"chat_appeal","text":"..."}`
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

**Starting it.** `python tools/launch.py --gateways 4` (§1) starts the game server on `127.0.0.1:8001` and four gateway worker processes sharing port 8000. The launcher makes a random `CORE_KEY` and gives it to both sides; a gateway connects to the game server's `/internal/gateway` websocket and has to present it (without a `CORE_KEY` the game server refuses all gateways, so a normal start exposes nothing). `python tools/launch.py` alone is the old single-process game. The tests can run the whole suite through gateways: `MS_TEST_GATEWAYS=2 python -m unittest discover tests` (§16).

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

**In plain English:** the game is saved in two ways that back each other up. A **snapshot** (`data/state.json`) is a photo of the whole game every 30 seconds. The **ledger** (`data/ledger.db`) is a notebook where every change to anyone's money is written down the moment it happens. If the server crashes, the next start loads the last photo and then replays the notebook entries written after it, so **nothing is lost, not even the last second**.

### The snapshot (`state.json`)
- **When:** every 30 ticks, on shutdown, and straight after a recovery. It writes `state.json.tmp` and then replaces `state.json`, so a crash mid-write can't leave a half file. A new account, a password change and an admin reset also save at once. **If Windows refuses to swap the file in** ("Access is denied": OneDrive, a virus scanner or a backup tool has it open for a moment, which this project's OneDrive folder invites), the save tries again up to eight times over a few seconds, and if it still can't it logs a warning and tries again at the next save (the chart file in half a minute) instead of raising an error in the game loop. Keeping the game folder out of OneDrive's sync avoids it altogether.
- **Two files.** On a long-running game the chart candles (11 timeframes × 500 candles × every stock) were 23 of the 27 MB, and they change slowly. They now live in **`state.charts.json`**, which the periodic save rewrites only every `charts_save_seconds` (300 s) and a clean shutdown always writes; `state.json` keeps everything else including the one-minute candles. If the chart file is a few minutes behind after a crash, the candles it is missing are rebuilt from the one-minute candles when it loads; if it is missing or unreadable the charts are rebuilt from them too (older than a few hours is lost, the 30-second candles of the gap stay empty). A save from before the split, with the charts inline, loads normally. **Why:** a save of the full game took about 2.4 s with the old `json.dump` (a slow Python path) while holding the game lock, which froze every trade and update for that long every 30 seconds; with the fast encoder and the split it takes about 140 ms.
- **What's saved (schema 7):** per stock: `base` (its size), `fair` (the price), candles for every timeframe, today's regular-session candle while it is under way (`reg`; the finished game days are in `history.db`, below), rating, hidden safety, mood, trend, **volatility multiplier**, **when it was listed (`listed_at`)**, share adjustments from buybacks and offerings, **the persona (CEO, CFO, product, city, former CEOs)**, **its earnings slot**, financials (revenue, margin, cash, debt, long-run margin), declared dividend and pending ex-date, pending stories, scheduled company events, any pending share offering, the stock's news log, earnings reports, schedules; globally: **the moonshot companies generated so far (`generated`)**, **the supplier / customer / rival graph (`relations`)**, house reserve, fees, house capital, minted, the index, regime, market and sector mood, market volatility, crisis end time, every headline printed (last 6,000), remembered story threads, season data, the margin-call log and counters, and **the ledger position this snapshot covers (`ledger_seq`)**; per player: cash, holdings (negative = short), cost basis, entry fees, realised profit per stock, fees paid, trade count, dividends received, borrow fees paid, their last 100 trades, margin calls, deposits, day base, **open orders**, **the password hash, address tags and sign-up time**, and **all social data**: achievements and their counters, today's progress and quests done, streak, drawdown tracker, medals, privacy, following, strikes, open-position times. Chat, mutes, reports, appeals, the moderator log, the running contest (with every entrant's paper account) and finished contests are saved too, and so are the login sessions (only their hashes), the address salt, the delisted-stock archive (the last 60 companies' charts, news and facts, so their pages still open) and `recapitalized`.
- **Not saved:** the admin charts' history (they restart empty), the global news wire (`news_log`), rumours waiting to confirm, sparklines, equity snapshots, trade cooldowns, the delayed-holdings snapshots (they refill in a few minutes). Per-stock news logs *are* saved.
- **Older saves** load: a save with the old leveraged tickers is migrated (§9), contests from before paper accounts are dropped, accounts without passwords stay usable, a save without the chart file keeps its inline charts, schemas before 7 get the old pool price as the market price, positions starting at the current price as their average entry, and ratings recomputed; a save with no social section just starts everyone with no achievements; a save from before moonshots simply gets four new ones; a ticker new to the content since the save is marked NEW; a save that still has seed tokens inside its stocks has them retired (§5), and a stock removed from content is simply dropped.

### The ledger (`ledger.py`, `ledger.db`)
A SQLite file in WAL mode with two tables, flushed once per tick:
- **`events`** (append-only, never edited or deleted, except by an admin reset, which copies the file to `data/backups/` first): one row per money event: `join`, `credit`, `debit`, `buy`, `sell`, `short`, `cover`, `margin_call`, `margin`, `dividend`, `borrow` (borrow fees are summed and written every 10 seconds), `delist_payout`, `delist`, `recap` (a top-up of the house reserve). Old ledgers may also hold `split` rows, which are ignored. Each row records the time, player, ticker, shares, price, and the **changes** to the player's cash, the house reserve, fees and the position's cost basis, plus the realised profit on closing trades.
- **`curve`**: each player's equity and cash once a minute (the equity curve on the portfolio page; the last 1,440 points are reloaded at start).

**Recovery.** On start the engine loads `state.json`, reads `ledger_seq`, and replays every event after it (`Engine._replay`): cash, holdings, cost basis, fees, house reserve, dividends, borrow fees, counters, and players who joined after the snapshot. It then checks the **token invariant** (the books still balance to within a millionth) and saves a fresh snapshot. A test kills an engine in the middle of play and checks that the recovered state matches the live one trade for trade. **Not recovered:** prices, news and the social counters since the last snapshot (up to 30 seconds), and borrow fees charged in the last few seconds before the crash (they are written every 10 seconds): they are cosmetic, random or tiny. Trades, deposits, dividends and payouts are exact.

**What it's for besides recovery:** the history page and CSV export (§11, §12), realised profit and best/worst trades, and the equity curve. With `ledger_path=None` (tests, `sim.py`) the engine runs without a ledger and the history page falls back to each player's last 100 trades in memory.

**Housekeeping (see `ROADMAP.md`, G11):** the file only grows. Back it up with the snapshot. To start a new game delete both (§1).

### The price history (`history.py`, `history.db`, `minutes.db`)
Two more SQLite files in WAL mode beside the save (ROADMAP TA-A10, 2026-10-21), each one table of candles keyed by ticker and start time, written in one transaction a tick (`CandleStore.flush`) and read by chart requests under a lock:
- **`history.db`**: every listing's **game-day candles** (the regular session, §11), written as each session closes, kept for `history_game_years` (10) game years (pruned once an hour). On start each listing reads back its last 400 (`Stock.days`) and the price model its last 370; a game that has no file yet rebuilds them once from its 5-minute and 30-minute candles. A save that ended in the middle of a session carries that session on (`reg`), or closes it if it has ended since. Backed up with the save (`deploy/backup.sh`, compressed) and copied by `upload.ps1 -WithGame`, the staging copy and `start_game.ps1 -Fresh` (which moves it aside with the rest).
- **`minutes.db`**: **one-minute candles**, written as each minute ends, kept for `history_minute_days` (3) real days; the 1m chart reaches back into it. Since 2026-10-24 also **every other timeframe's finished candles**, a table each (`tf_30s` ... `tf_1y`, kept to their last 2,010), so every chart reaches back 2,000 candles (§11). Not backed up (detail that rebuilds itself; about 60 MB, growing to a few hundred MB as the long timeframes fill).
The old `daily_hist` (whole 30-minute cycles, one game year, read by nothing) is no longer kept or saved.

---

## 14. Settings reference

**How to change a setting.** Settings live in the content packs (`base.json` has the defaults). To change one without editing a shipped file, make a new file in `content/` such as `my_settings.json` containing only `{"settings": {"email_mode": "required"}}`: packs are merged in alphabetical order and later files win, and the game re-reads packs about once a second, so most changes apply without a restart (a few, such as the ones that decide what exists at the start of a new game, only matter then).

| Setting | Default | Effect |
|---|---|---|
| `signup_bonus` | 1000 | MB credited to new players and to everyone on a game reset (the `grant` source, §10.9) |
| `market_model` | 2 | 2: the learn-to-trade price model (§6A); 1: the old zero-drift market (§6.2 and the regime shocks) |
| `price_model` | (none) | a dict overriding `market_model.DEFAULTS`, e.g. `{"erp": 0.035, "hold_base": 0.45}` (§6A). Phase 2's (2026-10-21): `daily_levels` (1) and `strength_*` (§6A.4), `bounce_reach` (1.0) and `test_gap_seconds` (600), `true_break_volume` / `false_break_volume` (2.5 / 1.9), `climax_*`, `exhaustion` (0.7), `wick_push` (2), `reversal_*`, `squeeze_*`, `subleg_*` (§6A.3), and `patterns` (1), `pattern_size` (2.5), `pattern_days` (2), `pattern_pull`, `pattern_noise` and the `pattern_*_chance` settings (§6A.10) |
| `daily_turnover` | 0.004 | share of a company's shares traded in a game day, for the volume bars (§6A.5) |
| `min_age` | 13 | the age to sign up (§10.9; buying has no age rule since 2026-10-24) |
| `shop_packages` / `shop_pro` / `shop_expert` / `shop_currency` | see §10.9 / `usd` | the catalogue, prices in cents |
| `leverage_rate_day` | 0.0003 | interest on a leveraged long's loan, a share of it per game day (§4) |
| `option_vol_premium` | 0.15 | how much more than the stock's realised volatility an option is priced on (§4) |
| `option_vol_guess` | 2.0 | the stated volatility times this stands in for the realised one while a stock has under 10 game days of history (§4) |
| `option_skew` / `option_smile` | 0.08 / 0.08 | the slope of the options' volatility skew (lower strikes dearer; reversed for the wildest stocks) and its curvature (both wings dearer), per standard deviation from the forward (§4) |
| `option_spread` / `option_min_spread` | 0.06 / 0.001 | the gap between an option's bid and ask, as a share of its price, and at least this share of the share price |
| `spend_cap_month_cents` / `purchases_per_day` | 50000 / 3 | the spending limits (§10.9) |
| `challenges` | false | the Learn page's challenges and their MB (§10.10) |
| `daily_chart` | true | the Daily Chart's endpoints (§10.13) |
| `restart_below` / `restart_days` | 50 / 7 | the free restart: below this equity, once every this many days (§10.9) |
| `quest_ladder` | true | the Bronze-to-Diamond quest ladder (§10.11): off, nothing completes or pays (the test worlds switch it off) |
| `challenge_week_cap` | 500 | most MB from challenges in a week (§10.10) |
| `rewards_need_email` | false | pay challenge and quest MB only to accounts with a verified email address (turn on once real email works, O1) |
| `house_seed` | 50000 | starting house reserve (funds new listings) |
| `season_seconds` | 86400 | length of a day (the old season): the leaderboard period; the day ends at the next multiple of it since the epoch, so 86400 means UTC midnight |
| `event_mean_seconds` | 120 | average gap between random news events |
| `issue_mean_seconds` | 100 | average gap between company stories (§7.7) |
| `mood_tilt` | 1.0 | scales how strongly the hidden mood tilts headline direction; 0 turns the tilt off (for experiments) |
| `news_followups` | false (true in the code) | whether stories are remembered for follow-ups ("UPDATE:", "REVERSAL:"); off since 2026-10-19 (ROADMAP TA-E2: news turned down) |
| `dividends_enabled` | true | `false` stops reports from declaring dividends (for experiments) |
| `news_strength_weights` | 25/40/25/10% | how often each strength appears |
| `news_move_ranges` | see §7.5 | raw impact before the clamp |
| `event_strength_limits` | 0.1/0.35/0.65/1.0 | event size cap, as a multiple of daily σ (the real size control) |
| `rumor_prob` / `rumor_credibility` / `rumor_delay_seconds` | 0.6 / 0.75 / 45–90 | rumour frequency, accuracy, time until confirmation |
| `earnings_quarter_days` | not set (a quarter of `TRADING_DAYS_PER_YEAR`: 91.25 = 45.6 real hours) | length of a fiscal quarter in game days; set it to override the year-derived default; every report and dividend is one quarter apart, give or take `earnings_jitter_days` (a quarter shorter than a game day is a demo: no windows, no jitter beyond 15%) |
| `earnings_jitter_days` | 4 | how many game days (2 real hours per 4) a report may drift from exactly one quarter after the last (§7.7) |
| `relation_spillover` | 1.0 | scales how much a company's suppliers, customers and rivals move it (§7.15); 0 switches it off |
| `premarket_seconds` / `aftermarket_seconds` | 300 / 300 | length of pre-market and after-hours at the start and end of each 30-minute cycle (§6.8); both `0` switches the sessions off |
| `extended_noise` | 0.35 | noise multiplier in pre-market and after-hours |
| `open_burst` / `open_burst_seconds` | 2.5 / 150 | extra noise at the open and how fast it fades |
| `close_burst` / `close_burst_seconds` | 1.5 / 120 | extra noise into the close and how long it lasts |
| `open_jump_seconds` | 90 | size of the opening jump, in seconds' worth of ordinary noise |
| `short_cap_frac` / `short_cap_index` | 0.25 / 16000 | the yardstick for how crowded a short is (a share of a stock's size, and a fixed figure for indices): it only scales the borrow fee, it no longer limits anything |
| `borrow_base_day` / `borrow_vol_day` | 0.0003 / 0.001 | borrow fee per game day: base plus this × volatility, then × (1 + 3 × how crowded the stock is) |
| `rating_review_seconds` / `rating_reiterate_share` | 1800–4500 / 0.15 | bank review interval per stock (real seconds; 600–1500 before TA-E2) and the share of unchanged reviews published as a note (0.4 before) |
| `regime_days` | 7–14 | regime length (game days) |
| `volatility_scale` | 1.0 | multiplies all noise and event caps |
| `commodity_trend` | 0 | multiplier on the old commodity drift (§6.1); keep at 0, because any value above it is a momentum edge |
| `daily_move_cap` | 0.15 | largest daily limit `L` for the soft daily brake (§6.5); 0 switches it off |
| `mean_reversion_halflife_days` | 90 | reversion speed; keep at 90 or more (see §6.2) |
| `distress_price_ratio` | 0.25 | a company this far below its reference price is resolved (§6.6) |
| `bankruptcy_chance` / `bankruptcy_payout` | 0.5 / 0.25 | ordinary company: chance of bankruptcy, and the share of the price holders get; the rescue jump follows from the two (×1.75) |
| `moonshot_bankruptcy_chance` / `moonshot_bankruptcy_payout` | 0.6 / 0.03 | the same for moonshots (rescue ×2.45) |
| `ipo_per_year` / `max_companies` | 15 / 200 | new companies a game year (0: none) and the number of ordinary companies past which each IPO is matched by a takeover (§6.10A) |
| `moonshot_initial` / `moonshot_max` / `moonshot_mean_seconds` | 4 / 8 / 900 | moonshots at the start of a new game, the most that may trade at once, and the average gap between new listings (§6.10) |
| `catalyst_mean_seconds` / `catalyst_moonshot_weight` | 480 / 10 | average gap between catalysts across the market, and how much likelier a moonshot is to get one (§7.13) |
| `catalyst_moonshot_scale` | 0.7 | multiplies the upside range of a moonshot's catalysts (§6.11); the loss is re-derived so the bet stays fair |
| `sector_shock_mean_seconds` | 600 | average gap between industry-wide shocks (§7.14); a very large number switches them off |
| `sector_shock_size` | 1.0 | multiplies the size of every industry-wide shock (§7.14): 0.5 for half-size moves, 1.5 for half as big again |
| `sector_links` | expansion.json | cross-sector spillovers |
| `vol_cluster_k` / `vol_cluster_decay_days` | 0.01 / 1.0 | volatility clustering: how strongly a big move raises the multiplier and its half-life in game days (§6.7); `vol_cluster_k=0` switches it off |
| `major_event_limit_boost` / `major_event_boost_seconds` | 2.5 / 600 | how much a "very strong" event loosens a stock's daily limit and for how long (§6.5) |
| `offering_mean_seconds` / `offering_delay_seconds` | 1200 / 300 | average gap between share offerings across the market, and the time from announcement to completion (§6.9) |
| `company_events_per_quarter` | 1.0 (1.5 in the code) | scheduled company events (guidance, investor day, analyst call, product event) per company per quarter; 0 switches them off (§7.16) |
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
| `signup_email` | true | an email address is needed to sign up (stored unverified until mail works, §10.6) |
| `email_mode` | off, or optional once `SMTP_HOST` is set | `off`, `optional` or `required` (a verified email is needed to trade, place orders, enter the contest or chat) (§10.6) |
| `email_code_minutes` / `email_max_tries` / `email_resend_seconds` / `email_sends_per_hour` | 15 / 5 / 60 / 5 | how long an emailed code works, wrong guesses before it dies, the wait before another code, and codes per address per hour |
| `mail_per_hour` | 200 | a ceiling on all mail the game sends in an hour (0 = none) |
| `blocked_email_domains` | none | extra throwaway-mail domains to refuse, on top of the built-in list |
| `charts_save_seconds` | 300 | how often the periodic save rewrites the chart file (§13) |
| `history_game_years` | 10 | how many game years of game-day candles `history.db` keeps (§13), and how far back the W and M charts reach |
| `history_minute_days` | 3 | how many real days of one-minute candles `minutes.db` keeps (§13) |
| `cross_mean_seconds` | 240 | average gap between two-company stories (§7.11) |
| `auto_sector_indices` / `sector_index_min_members` | true / 3 | create a tradable index for every sector with at least this many companies (§9) |
| `public_delay_seconds` | 300 | how old a holdings snapshot must be before other players can see it (§10.5) |
| `chat_enabled` | true | `false` turns chat off for everyone (§10.7) |

**Environment variables** (not settings: they are about the machine, not the game): `ADMIN_KEY` (switches the admin API on), `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `SMTP_SECURITY` (sending mail, §10.6), `CORE_KEY` (the game server accepts gateways that present it; set by `launch.py --gateways`), `CORE_URL` and `TRUST_PROXY=1` (for a gateway, §12).

Constants in `engine.py`: `FEE` 0.1% (it was 0.5% until 2026-10-03; see the note in §15), `COOLDOWN` 1 s, `MAX_TICK_MOVE` 15%, `SNAP_EVERY` 5 s, `MARKET_DAY_SECONDS` 1800, `TIMEFRAMES`, the narrative text pools, `BANKS`, `RATINGS`. In `newsgen.py`: the name, city and product pools, `ISSUE_KINDS` (company stories), `CROSS_KINDS` (two-company stories), `SYNONYMS`, `SOURCES`. In `social.py`: `ACHIEVEMENTS`, `QUESTS`, `CONTESTS`, `CONTEST_BALANCE`, the chat limits (`CHAT_MAX` 200, `CHAT_MIN_GAP` 1.5 s, `CHAT_PER_MINUTE` 15), the word lists (`BAD_WORDS`, `BAD_WORDS_EXACT`), `MUTE_STEPS` (10 minutes, an hour, a day), `FOLLOW_MAX` 20, `SNAP_EVERY` 30 s (holdings snapshots). In `accounts.py`: the scrypt cost, `MIN_PASSWORD` 8, `SESSION_DAYS` 30, `MAX_SESSIONS` 10, the reserved names, the list of too-common passwords and of throwaway-mail domains.

Per-template field `good` (`"down"`): marks the "down" text as the good news.

Old fields the game ignores (none of them is in the content files any more; removed 2026-10-20): `bots`, `bot_cash`, `bot_action_probability`, `close_seconds`, `bailout_chance`, `bailout_return`, `bankruptcy_haircut`, `position_cap_base`, `position_cap_abs_frac`, `split_price_ratio`, `split_delay_seconds`, the club settings, `event_duration_scale`, `rating_review_days`, `earnings_initial_seconds` / `earnings_interval_seconds` (replaced by `earnings_quarter_days`), `sev` / `chunks` in templates, and the `earnings` trait (every equity with revenue reports). `season_seconds` values other than whole days no longer line up with the daily contest.

The margin-call levels (25% to 75%) in §4 are fixed in the code (`maintenance`).

**Before changing any of these**, run `tune.py` on the old and new values with a fresh first seed. Keep the `value` and `hodl` columns near zero and `drift` at about 1e-10.

---

## 15. Things to know

*(The next three points were written for the old real-money plan, in which the house paid winners real money. In the new plan MB are never cashed out, so they describe bookkeeping, not risk; see `ROADMAP.md` M9 and X1.)*

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
- **The ledger is not a backup.** It lives next to `state.json` in `data/`; copy the save, the chart file and the ledger. Money events since the last snapshot are replayed after a crash, but achievement counters and chat since then are not. The admin **Reset** button makes such a copy for you in `backups/` before it clears anything.
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
| `test_browser.py` | drives the real pages in headless Edge or Chrome: the original flows, **search/sort/watchlist, the market layout, trading from the holdings page, the three sessions, every other page including the contest panel, a delisted stock's page, the order panel, password sign-up / log out / log in / change password, email sign-up / code / forgot-password recovery, reconnecting, the whole game on a phone-sized screen, and a visitor who is not signed in (watching, being asked to sign in, signing up on the same page)**. Skipped if no browser is installed | 11 | about 6 min |
| `test_market_changes.py` | **the leveraged products** (2LMSI, 2SMSI, 3LMSI, 3SMSI, the old ones migrated and withdrawn, redirects), **no splits**, **offerings** (only the share count changes, announced on the wire, no price or cash effect), **delisted stocks keeping a page**, one-day days | 30 | about 15 s |
| `test_orders.py` | **orders**: limit, stop-loss, take-profit and bracket validation, filling at the market price (including through a gap), close-only, one-cancels-other, cancel, expiry, limits per player, persistence and crash recovery, **no effect on any price** | 27 | about 20 s |
| `test_company_events.py` | **scheduled company events**: schedule, spread, calendar entries without a hint of direction, firing, the next report naming them, **every kind a fair bet**, conservation, persistence | 16 | about 5 s |
| `test_no_halts.py` | **no trading halts**: the circuit-breaker code and state are gone, a stock and the whole market can be traded straight after a crash, no halt news is printed over a wild hour, a stop-loss fills through a crash at once, no halt field is sent to the page, old halt settings do nothing | 7 | about 15 s |
| `test_contests.py` | **the daily contest**: the same paper balance for everyone, **a paper trade follows the real rules exactly (compared with a real twin)**, margin calls, borrow fees, dividends, bankruptcy payouts, ranking, medals, **no effect at all on prices, the house or real balances**, persistence, old contests dropped | 25 | about 40 s |
| `test_accounts.py` | **accounts**: password hashing, sessions (expiry, the ten-session cap, ending one or all), the old token working only without a password, reserved names, the sign-up and login limiters over HTTP, password change, admin reset, address flags, persistence, the browser-free parts of sign-in; an email needed to sign up, an address only once; deleting an account (everything closed and forgotten, the books balanced, replayed after a crash) and the admin endpoint | 39 | about 20 s |
| `test_moderation.py` | **chat moderation**: the word filter (disguises caught, ordinary words left alone, accents kept), the trade-first gate, three reports removing a message and muting its author, growing mutes, appeals, the moderator log, persistence | 23 | about 5 s |
| `test_house_risk.py` | **house tail risk**: the thinner rescue and catalyst tails (still fair bets), the reserve floor and automatic top-up (books balance, **no price or balance changes**, ledger recovery), the exposure report | 16 | about 12 s |
| `test_save.py` | **saving**: the chart file split, the periodic save rewriting charts only when due, a stale or broken chart file, old saves with inline charts, **the save and its chart file never being read as content packs** | 14 | about 50 s |
| `test_email.py` | **email on accounts**: address rules and spellings of one mailbox, throwaway domains, six-digit codes (hashed, expiring, limited tries, resend limits, one use), one account per address, an unproven claim losing, `required` mode blocking trades, orders, contests and chat (and not a verified player's paper account), password recovery (same answer for any name, one use, ends every session), saving and old saves, the mailer (background thread, retries, console mode, the queue ceiling), the whole flow over HTTP and the sign-up limit counting each visitor behind a tunnel separately | 45 | about 40 s |
| `test_gateway.py` | **gateways**: two gateways and a game server: init and ticks with each player's own numbers, trades, chat and charts across gateways, ordered messages, ordinary requests and pages through a gateway, the closed door without the key, a flooding page, a gateway dying, **the game server restarting and the gateways finding it again**, `launch.py --gateways 2`, and `share.py` (the whole flow against a stand-in for cloudflared, finding the link, refusing when the game is not running or the program is missing); a signed Stripe webhook through a gateway | 22 | about 30 s |
| `test_deploy.py` | **the deployment files**: the services, the Caddyfile (including the documented admin-password block), the PowerShell helpers (valid PowerShell; the mail helper never puts the key on a command line) and the environment example agree on ports and keys, every environment variable the code reads is in the example, a visitor cannot fake his address through the web server, the scripts have no syntax errors, and the upload includes every module the server needs and never a save, a ledger or a test | 12 | about 3 s |
| `test_health.py` | **the uptime address**: `/api/health` answers 200 with exactly four fields and `no-store` while the game ticks, needs no key and is never locked out by wrong admin keys, and works through a gateway | 3 | about 10 s |
| `test_msi50.py` | **the MSI 50**: its name everywhere, exactly 50 members that are the biggest companies and only companies (no moonshots, funds, commodities or indices), the return is the market-value-weighted return of the members, a bigger member moves it more, outsiders cannot move it, the leveraged products follow it, re-ranking at a new game day, a delisted member replaced at once, fewer than 50 companies, the members survive a restart and an old save without them, trading it never moves it and the books balance | 13 | about 5 s |
| `test_admin_insights.py` | **the dashboard's deeper numbers** (15 tests): the ledger's hourly, daily and per-stock summaries (hand-made events with known answers, an empty ledger), the engine's insights (market counts add up, orders, positions, biggest players, chat, settings in effect), the save time, the endpoint's key check and every panel, plausible machine numbers, visitors counted apart, wrong keys counted and listed with their address, ten wrong keys locking an address out (even with the right key, the game itself unaffected) and the same through a gateway | 15 | about 15 s |
| `test_guest.py` | **visitors and the funnel** (22 tests, the server ones both straight at the game and through a gateway): the hidden guest is not a player and cannot be logged in as, a visitor gets the market, ticks, charts and company pages with no money and no chat, cannot trade, order, chat, report or appeal and changes nothing in the books, never receives chat, is counted apart from players in the admin overview, `/about` and the visitor welcome card are served, the funnel counts sign-ups, traders, emails, fees and who pays them | 22 | about 20 s |
| `test_economy.py` | **the shop**: MB by source, the catalogue, the New Launch Deal (once, in the first 7 days), invite codes (unique, kept, counted for the inviter, over HTTP too), an order paid once however often it is confirmed, wrong amounts, Pro adding up, refunds, expiry, the age rules, the spending cap and daily limit, the self-set limit (raising waits a day), the free restart, orders and Pro surviving a crash (the ledger replays a purchase), Stripe's signature (wrong secret, changed body, a replay), the Stripe request, the whole flow through a test server, the shop closed when payments are off, sign-up needing a birth year, and a browser buying a package through the test checkout; tracking links: kept at sign-up and cleaned, sign-ups, buyers and revenue per link | 27 | about 25 s |
| `test_shop_safety.py` | **before the shop opens**: the terms version recorded at sign-up, the consent kept with each order, receipts only to verified addresses, the payment check completing a missed (even expired) order exactly once and refusing a wrong amount, Stripe's list read page by page, the sign-up trap, rewards held back without a verified address, the terms and privacy pages | 13 | about 12 s |
| `test_chart_prefs.py` | **chart basics**: the chart set-up and drawings kept per player and checked first (bad ids, colours, numbers, notes, too many), only the newest 100 stocks keep drawings, saving and loading, the endpoints, one stock's history; in a browser the five chart types and the log scale, the crosshair and readout, an indicator's length renaming it, the channel and Fibonacci extension tools, a trade arrow and a stop tag on the chart, and drawings and settings coming back in a new browser | 7 | about 45 s |
| `test_history.py` | **the long price history** (TA-A10): candles written, read back in order, replaced and trimmed; a game-day candle is the regular session only and the next open gaps from the last close; the days survive a restart (and a restart in the after-hours keeps today's finished candle); the 1m chart reaches into the minute file; an old game's days rebuilt from its 5-minute candles; every timeframe's chart reaches back 2,000 candles through its table in minutes.db, a refresh with `since` gets only the newest, each table is trimmed to its own 2,000 | 6 | about 4 min |
| `test_ipos.py` | **IPOs and takeovers** (§6.10A): every industry makes a sound company like its peers, in all three sizes; about 15 a game year (and none when switched off); announced a game day ahead (the wire, Upcoming events) and listed at that price; a save keeps the announced IPO and the new company; past the limit the smallest company outside the MSI 50 is bought at the market price, holders are paid, the books balance | 5 | under a second |
| `test_options.py` | **options** (§4): the value and every Greek against finite differences, put-call parity on the forward (with a dividend and an earnings jump), the Greeks behaving as real ones do (delta about a half at the money and 1 or 0 near expiry, gamma highest at the money and near expiry, theta faster near expiry, vega growing with time, rho's signs), the skew, **buying calls and puts at random loses on average** (no free money), quotes following the stock (delta, gamma and the smile), listed strikes that stay while new ones are added, the term structure following the volatility clustering, earnings and the crush, dividends, the chain and its open interest (in contracts), **whole contracts of 100 shares** (the cost, refusing fractions, zero, too many and what the cash cannot pay, selling one of several or more than held), a position bought in fractions before still selling, buying and selling with the books balanced, the rules, settlement at expiry, a bankruptcy settling its options, a save (the held strike still listed) and a crash losing none | 18 | about 1 min |
| `test_leverage.py` | **leverage** (§4): only for Pro and never on the leveraged products, a leveraged long (the loan, the books, the liquidation price), interest adding to the loan, the close when the margin runs out, a gap past the margin paid from cash then by the house, a leveraged short, adding at the same leverage, a save and a crash keeping every loan and collateral | 8 | about 1 min |
| `test_bots.py` | **bots and backtests** (§10.12): the rule language parses and refuses with a reason, the indicators against hand calculations, crosses, the news score from the bot's own words, a bot checked before it is saved, only for Expert, a bot buying then selling on its rules, stops, leverage and options, bots switched off when Expert ends, bots surviving a save; backtests filling at the next open and compared with holding, stops and a margin call on a candle's range, news and options in a backtest, and the HTTP endpoint; the guide is served and names every word, action and default news word | 15 | about 2 min |
| `test_trading_tools.py` | **the new tools in a real browser**: the Options tab (the chain, quotes that change with the stock, clicking a contract for all its Greeks, buying one whole contract, the position, selling it back from the holdings page), leverage refused without Pro and a 5x position with the price where it closes, and the Bots page (the Expert pitch, a bot from a template, saved, backtested and switched on) | 1 | about 1 min |
| `test_daily.py` | **the Daily Chart** (§10.13): the chart the same for the same seed and sound (high ≥ open and close ≥ low > 0), volatile and different from day to day, not a plain random walk (big moves follow big moves, fat tails); the same chart for everyone and made once a day; candles shown one a second and **never ahead** (asking ahead gets nothing, nor does anyone who has not started); trades at the last close, the rules, **shorts** (selling with no shares, the 1x limit, covering, a new short when flat), a short never losing more than everything, the end valuing what is held at the last close, the whole chart at the end; one game a day, visitors refused, the board in order; a new day's new chart keeping yesterday's winner; a save keeping the salt, the chart and the trades; the summary's data (everyone's returns, the stock's own move, high and low); the endpoints over HTTP; archived: no page, script or endpoints while `daily_chart` is off; numbered days, streaks (a missed day ends one) and stats; the result grid; on the site and switchable off | 16 | about 30 s |
| `test_subscriptions.py` | **monthly passes** (§10.9): the prices, the renewal agreed first and one at a time, the test mode renewing each month until cancelled, provider renewals once per invoice and the subscription ending, the daily check catching a lost renewal, a crash and a save keeping the subscription, the receipt; Stripe's subscription checkout, its events, cancelling there and the paid-invoice list | 12 | under a second |
| `test_structure.py` | **Phase 2 of the price model** (TA-A2 to TA-A9): game days and the daily levels (yesterday's high, low and close, the open, the averages, the 52-week range, a confluence adding up); tests only in the regular session, reactions sized when they begin, the harder push through a level (the wick), less volume on a break that will fail, no test straight after another; the trend's weaker last push, a climax and a reversal burst, the squeeze at the end of a range, intraday legs that alternate and add no drift; every pattern ending its three ways and handing over to a trend, a double top's shape, mirror images and odds that are never a sure thing, a pattern surviving a save; the zigzag confirming only after the turn, textbook shapes found and followed, a pattern that breaks the wrong way failing, no pattern counted twice; and `realism.py` running with its structure and pattern reports | 21 | about 3 s |
| `test_errortrack.py` | **the error tracker** (E13): errors grouped by where they were raised and counted with their traceback, warnings left out, a bounded number of kinds, never raising; `/api/admin/errors` for the admin key only | 3 | about 12 s |
| `test_pricing_model.py` | **the pricing model** (M7): the game's packages and prices, revenue scaling with sign-ups and nothing when nobody pays, retention falling, the sensitivity covering every assumption | 3 | under a second |
| `test_market_model.py` | **the price model**: the phases add no long-run drift, the drift by beta, phases change and are bounded, a quiet market follows its drift, levels from swing highs and lows and round numbers, a held support pushes up and a break goes through, strong levels hold more often and repeated tests weaken them, ranges pull to the middle, pulses deliver exactly their move (and whipsaws go the wrong way first), the release calendar (8 rate decisions, 12 CPIs, 52 claims a year), forecasts fixed once published, releases against the forecast, rate decisions in quarter points; in the engine: candles with volume, money conserved, player trades never moving prices, a macro headline and move, earnings against a forecast, the model surviving a save and an old save loading; `/api/calendar` and `/api/admin/model` | 22 | about 5 s |
| `test_learning.py` | **learning**: every course file parses and every lesson is complete (a summary, blocks of known kinds, links to real pages), a bad file is refused, a lesson comes with its track and neighbours, opening one counts it as read (once) and pays nothing, a visitor's reading is not kept, chart tests hide their answer until answered, count a player's score, expire, use real candles once there are some, and every kind can be asked; a lesson's example stays 15 minutes; challenges off (what ships) and, switched on, a stop completing "protect a trade" (once per position) and a closed position counting as planned, a take-profit counting for its challenges and the ladder, the state surviving a save; the endpoints over HTTP for a visitor and a player; and a browser reading the course, a lesson with its example chart and a chart test and no quiz, the lesson then counting as read, a page of chart tests (and no Journal in the menu), reading the calendar and using the chart's volume, RSI, a Pro indicator, a drawn level and the risk tool | 18 | about 70 s |
| `test_drills.py` | **chart tests**: every kind is found on the price model's charts and is well formed (nothing from the future before the answer), the two-outcome kinds come out about half and half, a level's answer is what the closes did, the reward-to-risk answer matches its lines, a candle's answer is its shape, and too few or broken candles give nothing | 6 | under a second |
| `test_ladder.py` | **the quest ladder, exits and the calendar grid**: four tiers paying more as they go up, Bronze quests completed by trading and paid once as money put in, stops and shorts counting, a Diamond quest unlocking a title and colour that then show on the boards, in chat and on the profile (and locked ones refused), day-board finishes counted only with a positive return, the ladder surviving a save and a reset clearing it; setting, moving, pairing and removing take-profits and stops (and the right side of the price for longs and shorts), a paired exit closing the position and taking the other with it; the month grid (one cell a day, weeks from Monday, today marked, weekly claims on one weekday, released results shown, months cycling and clamped, over HTTP); and a browser run through the holdings boxes, the ladder's drop-downs and the calendar's grid | 13 | about 50 s |
| `test_chart_tools.py` | **the chart's tools**, in a real browser: 49 indicators (17 free), their formulas against plain Python versions (SMA, EMA, WMA, RSI, ATR, Stochastic, Williams %R, CCI, OBV, CMF, MFI, rate of change, Bollinger), the searchable Indicators box, a Pro indicator refused until the admin gives Pro (then drawn), the drawing toolbar (draw, select, move and delete a trend line; the long-position and Fibonacci tools; hiding drawings; the small bar and its drop-down; dragging the toolbar), dragging the chart up and down and Fit prices, the resize bar (no Taller/Shorter buttons) and full screen; and the admin Pro endpoint (forbidden without the key, unknown player, bad day counts, days adding up, taking Pro away) | 2 | about 40 s |
| `test_companies.py` | **the companies**: every industry has at least two sizes (small, mid, large cap) and there are plenty of each, small caps more volatile than large ones, a distinct description for every company, financials in proportion to size, and the save migration that scales a company's financials when its size changes | 6 | under a second |
| `test_no_pools.py` | **stocks hold no tokens**: the books are cash + reserve + fees, the house capital is only the starting reserve and top-ups, a new listing costs the house nothing, and **a save from the old version with seed tokens inside every stock is converted** (the reserve, fees and players' money are unchanged, minted and house capital drop by the retired tokens, the clean save loads the same again, a crash before the first save is harmless, the game keeps balancing afterwards) | 7 | about 15 s |
| `test_no_bots.py` | **no bots**: a new game has no players and none appear, the old bot settings do nothing, no board, profile or stat has a bot field, and **a save from the old version with house-funded bots loads cleanly** (the bots are settled and removed, the tokens balance, the humans are untouched, the clean save loads the same again, a crash before the first save is harmless) | 8 | about 30 s |
| `test_reset.py` | **starting over at Day 1**: everyone on the starting balance, nothing held, the market untouched, identity kept, the books balance, the ledger restarts and still explains every balance, a crash right after a reset loses nothing, the admin endpoint (key, the word RESET, the backup), and `reset_game.py` (it backs up, resets, and refuses while the server runs or without the word) | 15 | about 90 s |
| `stress.py` | a stress tool, not a unit test: many clients hammering one server (below) | | 30 s by default |
| `capacity.py` | a capacity tool: many ordinary players on one server, with the CPU, tick time and bytes per player reported (below) | | 40 s by default |
| `test_slow.py` | a slow stress run (20 clients for 15 seconds), only with `RUN_SLOW=1` (the old edge checks were removed with their tools) | 1 | about 30 s |
| `_helpers.py`, `_cdp.py` | shared code: fake-clock engine builder, the isolated server runner, a tiny browser driver | | |

**Your save file is never touched.** Engine tests use an engine with no save file (or a temporary one). Server, stress and browser tests start the server from a temporary copy of the project in a temporary folder and delete it afterwards. Browser tests also launch a headless browser with a temporary profile folder (over 100 MB each); the helper now kills the browser's child processes and deletes that folder when a test ends, and retries the deletion on Windows, where an earlier version left one behind per browser and filled the disk (a full disk makes servers and tests fail in confusing ways). If a run is killed half way, leftover `meme_street_test_*` and `meme_street_browser_*` folders in your temp folder are safe to delete.

### What the engine tests prove
- **Money is conserved** after hundreds of random trades by several players (token drift stays below 0.000001).
- **Trading:** a buy plus sell costs exactly two fees (about 1%); the average entry price is share-weighted and doesn't change when you sell part; a typed amount overrides the percentage; bad amounts (0, negative, NaN, infinity, huge, text) are refused; the 1-second cooldown works; the index price equals the index level.
- **No position limits:** a 100% buy goes through whatever the stock's volatility; a rich player isn't capped by the depth of a stock; a short is limited only by your cash (it is taken out of cash as collateral), with no margin multiple or borrow pool; selling is never blocked.
- **Shorting:** opening and covering works and keeps money conserved; proceeds stay locked (withdrawals blocked); you can't short beyond your margin; covering part keeps the average price; **a margin call triggers exactly when equity falls below the maintenance level** (tested on calm, medium and wild stocks, never before and never late); a gap past the call leaves cash at zero and the house's shortfall is counted; shorts in a bankrupt stock close without negative cash.
- **Borrow fee:** the fee charged over a minute matches the formula to within 2%, goes to the house, and money stays conserved.
- **Dividends:** on the ex-date a long holder is paid, a short holder pays, the price drops by exactly the dividend, and money stays conserved.
- **Earnings:** a quarter is 91.25 game days = 45.6 hours (a quarter of the 365-day game year); first reports are spread across the quarter; the next report is a quarter after the last give or take the jitter (and exactly a quarter with none); the headline names at most three stories and counts the rest; a report declares a dividend that follows the margin and is suspended for a loss.
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
- A 20-client, 15-second stress run. (The old edge and paired checks went with the edge tools on 2026-10-13, §1.)

The market's own checks are `python tools/chart_check.py` and `python tools/realism.py` (§1, "Market checks"; §6A.9). Run them before shipping any change to prices, news, fees, limits or dividends.

### Which check when

| You changed... | Run |
|---|---|
| anything in the engine | `python -m unittest discover tests` |
| `server.py`, `index.html` or `chart.js` | the same (includes the server and browser tests) |
| prices, news, fees, margin, dividends, earnings, volatility, sessions, orders, company events, indices, moonshots, distress, catalysts | the tests, then `python tools/chart_check.py 12 7` and `python tools/realism.py 2 3 40 <fresh seed>` (§6A.9) |
| anything in `social.py` or `contest.py` | the tests; the "social features never move a price" and "a contest changes nothing outside itself" tests are the ones that matter |
| `accounts.py`, `mailer.py`, sign-in or the admin reset | the tests (`test_accounts.py`, `test_email.py`, `test_reset.py`, the password and email browser tests) |
| `server.py`, `gateway.py`, `wsconn.py`, `tools/launch.py` | the tests, then the server suites again through gateways: `$env:MS_TEST_GATEWAYS = "2"; python -m unittest test_server test_accounts test_email test_reset test_contests test_social test_orders test_browser` (from `tests/`), and `python tests/capacity.py 400 40 2` |
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
`.github/workflows/tests.yml` runs on every push and pull request: a **lint** job (Ruff and the light mypy pass, §1, ROADMAP E13) and the test suite in four parts side by side, each failing test run once more on its own (ROADMAP E12). The slow checks and the market checks (`realism.py`, `chart_check.py`) are run by hand.

---

## 17. Latest economy-check results

> **History.** These are the results of the old zero-edge market's checks (`sim.py`, `bots.py`, `edge.py`, `paired.py`, `probe.py`), which were removed on 2026-10-13 with that rule. The market today is checked with `chart_check.py` and `realism.py`; the results are in MARKET_REALISM.md section 4.

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
- **Test suite (2026-10-13, after the realism work and the clean-up):** 829 tests (828 run by default, 1 slow one with `RUN_SLOW=1`); the last full run passed completely. Before the clean-up (which removed the old edge tools and their tests): 849 tests (845 run by default, 4 slow ones); the last full run (15 minutes) had one failure, a bracket test that counted the new challenge reward as trading profit (fixed and re-run). Before that build: 793 tests (789 run by default). The last full run (12 minutes, after the last change) passed completely. Earlier in this release a full run found one race in the gateway (it closed a page before an error message went out; fixed) and, while the study tools were being written, 21 failures caused by `bots.py` replacing the engine's public-state and leaderboard builders when it was imported (it now does that only inside its worker processes); both are fixed. The server, accounts, email, reset, contest, social, order and browser suites were also run through two gateways (`MS_TEST_GATEWAYS=2`) and passed, and the stress test passes both ways. The edge checks were re-run for this release as the many-bot study (§17.7): no price, news or fee code changed, only the accounts, the server, the sharing tools, the leaderboards and the way content files are found.
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

### 17.10 What is a player worth? (2026-10-09)

*(Superseded on 2026-10-13: the site will earn from MB packages, not from the trading fee. The method below still holds for the fee, but the pricing model that matters now is `ROADMAP.md` M7.)*
*(`revenue_model.py` and its test were removed on 2026-10-13: fees are no longer the income. This section is kept as history.)* `python revenue_model.py` answers the question the roadmap asked: how much does the 0.1% fee bring in per player? **How people play in it is an assumption** (there are no real players yet), written in one table at the top of the file and replaceable from a JSON file; the admin page's new *Players and fees* panel is where the real numbers will come from.

The one rule it rests on: **in a fair market a player's money can only be used up by fees** (the other side of their trades averages zero), so what a player is ever worth to the game is bounded by their balance. A player who trades `trades` times a day with `size` of their balance each pays `r = fee x trades x size` of their balance a day, and `balance x (1 - (1 - r) ^ days)` over `days` days. What they have left when they stop is not income.

With the starting 10,000 MB, a 0.1% fee and this mix of players (all assumptions):

| Player type | Share | Trades a day | Size | Days | Fees take a day | Fees paid | Left | Share of all fees |
|---|---|---|---|---|---|---|---|---|
| Looker (signs up, glances, drifts away) | 40% | 1 | 10% | 3 | 0.01% | 3 | 9,997 | 0% |
| Casual | 30% | 4 | 25% | 14 | 0.10% | 139 | 9,861 | 6% |
| Regular | 20% | 15 | 25% | 30 | 0.38% | 1,066 | 8,934 | 30% |
| Active | 8% | 60 | 25% | 30 | 1.50% | 3,645 | 6,355 | 41% |
| Grinder (a bot-like human) | 2% | 300 | 25% | 21 | 7.50% | 8,055 | 1,945 | 23% |

**1,000 sign-ups bring about 709,000 MB, 709 MB each, 7.1% of the starting balance. The heaviest-paying 10% of players pay 64% of it.** The fee level (same players): 0.05% gives 4.0% of the balance, 0.1% gives 7.1%, 0.2% gives 11.6%, 0.3% gives 15.0%; twice the fee is less than twice the income, because balances run out. What it says: **income follows how much people trade and how much money they put in, not how many sign up**; a looker pays almost nothing and a handful of heavy traders pay most of it, so the money questions are how to attract and keep active traders and what fee they will accept (ROADMAP A14, I2). For scale, the simulator's bots trade far more than people (a bracket-order bot 14 times its balance in two game hours, a news-chasing bot 78 times), which is why their turnover is shown but not used. To turn MB into money, pass `mb_value=` (what 1 MB is worth); that is still an open question (ROADMAP section 5).

### 17.11 Options: no free money on the real engine (2026-10-22)
**Why.** Options priced on the stocks' stated volatility looked fine in a test with a textbook stock, but the engine's prices move about twice as much as their stated volatility (the price model's structure on top of the noise). The first version of the reworked pricing (the stated volatility with a term structure, a 90% realised floor, a 10% premium and a steep put skew) was **free money on the wild stocks**: their at-the-money straddles paid +2% to +10% in every one of 4 seeds, and out-of-the-money calls far more.

**The check** (`python tools/option_check.py SEED GAME_DAYS`): the real engine, 4 seeds × 60 game days; every 10 minutes, for every stock with options, on the first four expiries, paper purchases at the ask (plus the fee) of calls and puts at the money, 5% and 10% out and 10% in the money, and straddles and 5% and 10% strangles; each either held to expiry (a delisted stock pays as if at 0) or sold at the bid halfway to expiry. About 3 million contracts a seed. A probe of volatility estimates (the next 1 and 7 game days' realised variance over the estimate, by kind of stock and clustering state) chose the inputs: the last 20 regular-session closes and the last 80 game days are both unbiased within about ±30% across seeds; 5-minute candles are noisier; the stated volatility is 2 to 5 times too small in variance.

**Result with the pricing that shipped** (realised volatility, half the variance following the clustering, a 15% premium, a mild put skew that turns into a call skew for the wild stocks), average of the 4 seeds (range):

| Bought | Held to expiry | Sold halfway |
|---|---|---|
| Straddle, tame stocks | −24.5% (−30% to −17%) | −15.6% |
| Straddle, wild stocks | −24.0% (−27% to −19%) | −13.2% |
| 5% strangle, tame / wild | −55% / −34% | −37% / −18% |
| 10% strangle, tame / wild | −73% / −45% | −52% / −24% |
| Straddle by expiry: next close, 2, 7, 30 game days | −27%, −24%, −22%, −23% (the 30-day one +3% in one seed) | −20%, −14%, −13%, −12% |
| Straddle in calm, normal, stormy spells | −23%, −23%, −26% | −15%, −14%, −15% |
| Straddle in a new game's first 15 game days / after | −31% / −22% | −19% / −14% |
| Call at the money / 10% in the money | −12% / +1% (−8% to +9%: the market's direction) | −9% / −4% |
| Put at the money / 10% out | −39% / −80% | −23% / −52% |

Every direction-neutral group loses in every seed but one (the 30-day straddle and strangles in a seed with a strong trend, +2% to +5%: what a real straddle buyer can win in such a market). Single calls and puts follow the market's direction, as the stock does; a 10%-in-the-money call is close to owning the stock and gains in the seeds where the market rose.

---

## Keeping the docs current

After every code or content change, update this file so it describes what the code does now, and tick or adjust the matching items in `ROADMAP.md`. Check `ROADMAP.md` before starting any new work.
