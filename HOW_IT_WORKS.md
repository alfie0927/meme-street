# How Meme Street works

This document explains the whole system: what each file does, the math behind prices and trading, how money flows, how news and new stocks are generated, and what to watch out for. Numbers quoted are the current defaults from `base.json` / `expansion.json` and the constants at the top of `engine.py`.

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
- **http://127.0.0.1:8000** for the game. Open a second browser (or a private window) to play as a second player.
- **http://127.0.0.1:8000/stock/NVXA** for a stock's detail page (any ticker works).
- **http://127.0.0.1:8000/docs** for FastAPI's automatic API explorer, where you can try `/api/join` and the admin endpoints from the browser.

Alternatives:
- **VS Code:** Terminal → Run Task → "Meme Street Profile Engine". It runs the same command on port **8002**, so open http://127.0.0.1:8002.
- **While editing code:** add `--reload` so the server restarts when a `.py` file changes. Content `.json` files are hot-reloaded by the engine itself without a restart.

Stop the server with Ctrl+C. It saves `state.json` on a clean shutdown.

**Run only one server at a time.** Every server instance reads and writes the same `state.json`, so two servers overwrite each other's saves. A server also keeps running whatever code it started with: after pulling new code, stop it and start it again.

**To reset the game**, stop the server, delete `state.json`, and start it again. A fresh market, fresh bots and fresh accounts are created.

### First-time setup (only once)
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Economy checks
```powershell
.venv\Scripts\python.exe sim.py 6 1                      # 6 simulated hours, seed 1, detailed report
.venv\Scripts\python.exe tune.py configs.json 6 6 101    # compare settings: 6 h, 6 seeds starting at 101
```

---

## 2. The pieces

| File | Role |
|---|---|
| `engine.py` | The whole game: market maker, price dynamics, news, bots, seasons, accounting, save/load. Has no web code. |
| `server.py` | FastAPI app. Runs `engine.tick()` once a second, pushes state to browsers over WebSockets, and handles HTTP endpoints. |
| `index.html` | The entire front end: plain HTML, CSS and JS with no build step. The same file serves `/` and `/stock/{ticker}`. |
| `base.json` | Core content pack: settings, 9 sectors, the original companies, 11 event templates. |
| `expansion.json` | Extra sectors (utilities, industrials, telecom, materials, agriculture, commodities), more companies, risk settings, sector links. |
| `events_pack.json` | 17 sector-specific news templates. |
| `market_profiles.json` | Per-ticker reference price, share count, revenue, margin, cash, debt, dividend yield, price unit. |
| `space_pack.json.disabled` | Example pack. Rename it to `.json` while running to IPO three space companies live. |
| `sim.py` | Headless simulation with scripted "human" strategies; reports returns, house P&L, invariant. |
| `tune.py` | Runs `sim.py` across several setting overrides and seeds in parallel and prints a comparison table. |
| `state.json` | The save file (generated, git-ignored). |

---

## 3. Time

- **1 tick = 1 real second.** The server loop calls `engine.tick()` every second.
- **1 game day = 1,800 ticks = 30 real minutes** (`MARKET_DAY_SECONDS`).
- **1 game year = 252 game days** (`TRADING_DAYS_PER_YEAR`), which is 126 real hours.
- **1 season = 3,600 s = 1 real hour = 2 game days** (`season_seconds`).

So "1d" in the UI means the last 30 real minutes. Week, month and year charts cover 7, 30 and 365 game days (3.5 hours, 15 hours and about 7.6 days in real time).

Annualised volatility `σ` (each company's `vol`) converts to:
- daily: `σ_d = σ / √252`
- per tick: `σ_tick = σ / √(252 × 1800)`

Example, NVXA (`vol` 0.42): `σ_d` = 2.65% per game day and `σ_tick` = 0.062% per second.

---

## 4. The market maker: how prices and trades work

Every stock is an **automated market maker (AMM) pool**, the same constant-product design as Uniswap. There is no order book: players always trade against the pool.

Each pool holds:
- `T`: memebucks (tokens) in the pool
- `S`: shares in the pool

**Price:** `p = T / S`

At listing, `T = depth` (from the content pack, typically 20,000 MB) and `S = depth / initial_price`, so the opening price equals the reference price. NVXA: `T` = 20,000, `S` = 149.25, `p` = 134.00.

### Buying with `c` MB
```
fee     = c × 0.005               → house fee revenue (never enters the pool)
t       = c − fee                 → enters the pool
S_new   = T × S / (T + t)         → T × S is unchanged by the trade
shares  = S − S_new               → given to the player
T_new   = T + t
```
The new price is `p × (1 + t/T)²`, so **your own price impact grows with the square of your trade's share of the pool**. Spending 5% of the pool moves the price up about 10.25%.

### Selling `sh` shares
```
T_new    = T × S / (S + sh)
gross    = T − T_new              → leaves the pool
fee      = gross × 0.005          → house fee revenue
proceeds = gross − fee            → to the player
```

### Limits per trade
- **Buy:** at most `0.05 × T / (1 − fee)` MB, so the net amount entering is at most 5% of the pool (`MAX_POOL_FRAC`). Larger orders are trimmed and the toast says "capped by pool depth".
- **Sell:** at most 25% of the pool's shares `S` per trade.
- **Minimum buy:** 1 MB.
- **Cooldown:** 1 second between trades in the same stock (`COOLDOWN`).
- Sizes are a fraction of your cash (buy) or of your position (sell), using the 10/25/50/100% chips.

### Round trip
Buying and immediately selling back with nobody else trading returns exactly `c × 0.995 × 0.995`: about **1% lost to fees, nothing to slippage**. The curve gives back the slippage when you sell. If other players trade in between, you gain or lose relative to them.

### Equity
A player's equity = cash + the **liquidation value** of each position, meaning what `quote_sell` would actually pay after slippage and fee. This is a conservative valuation: big positions are worth less than `shares × price`.

---

## 5. Where money lives (the zero-sum design)

Every memebuck is in exactly one of four places:

```
player cash  +  Σ pool T  +  house reserve  +  fees  =  minted
```

`total_tokens() == minted` is checked by `sim.py` (drift is about 1e-10, which is floating-point rounding) and logged on load.

**What changes `minted`** (money entering or leaving the game):
- `credit(player, amount)`: a deposit or signup bonus (later: a crypto purchase)
- `debit(player, amount)`: a withdrawal (only free cash, not positions)
- the house putting in capital: pool seeds at listing, the 50,000 MB reserve (`house_seed`), and bot bankrolls (`bot_cash`)

**What moves money between places:** only trades (cash ↔ pool, fees → house) and bankruptcy (pool → players at the haircut price, the remainder → house reserve).

**What never moves money:** news, noise, mean reversion, regimes and bailouts. They change the pool's **share count** `S`, never its tokens `T` (see §6). This is the key design decision. Price changes alone can't create or destroy memebucks; they only change who would get what when people sell.

### Who pays whom
The pools are seeded with house money (about 776,000 MB across 41 listings, plus the 50,000 reserve and 8,000 for bots = **834,000 MB of house capital**). That liquidity is the counterparty to every trade. So:
- If a player profits, the money comes from other players who sold to or bought from the same pool, or from the house's pool liquidity.
- **House P&L = fees + liquidity P&L + bot P&L = −(players' combined P&L).** `house_stats()` reports each part.
- Constant-product pools can never be fully drained: as `S` shrinks the price rises without limit, so the most the house can lose is bounded by what it put into the pools.

The design goal, checked with `sim.py`, is that liquidity P&L stays near zero, so the house's income is the fees and players' gains come from other players.

---

## 6. Price dynamics: what moves prices each tick

Each stock has two prices:
- `price = T / S`: the tradable price, which includes every player's price impact
- `fair`: an "outside world" value that follows news and noise and **excludes player impact**

Every outside move with return `r` is applied as:
```
S    ← S / (1 + r)       → price × (1 + r), T unchanged
fair ← fair × (1 + r)
```

During a tick, all outside moves are **queued**, combined, and applied together in `_flush_moves`, in this order:

### 6.1 Random noise (`_random_market_moves`)
A three-factor model, drawn fresh each tick:
```
σ_market = β × 0.18
σ_sector = 0.08
σ_idio   = √max(σ² − σ_market² − σ_sector², 0.005²)

r = (σ_market·Z_market + σ_sector·Z_sector + σ_idio·Z_idio) × volatility_scale / √(252 × 1800)
```
`Z_market` is shared by all stocks this tick, `Z_sector` by the stocks in one sector, and `Z_idio` is per stock (all standard normal). The result is clamped to ±1% per tick. Over a game day, each stock moves with standard deviation about `σ_d`, correlated through market and sector.

### 6.2 Mean reversion (`_mean_revert`)
A slow pull of `fair` back toward the reference price `P0`:
```
rate = 1 − 0.5^(1 / (H × 1800))       H = mean_reversion_halflife_days = 90
r    = (P0 / fair)^rate − 1
```
It is symmetric in log price: a stock at 0.8× is pulled up exactly as hard as one at 1.25× is pulled down. With `H` = 90 game days (45 real hours), half of any gap closes in about 2 real days. Player impact is never reverted, because only `fair` is targeted.

*Why 90 and not faster:* at `H` = 7, a stock that dropped below 0.9× bounced about +1.8% in the next 30 minutes, which beats the 1% round-trip fee. Anyone could farm that, and the house's liquidity paid for it. At 90, the bounce is +0.3% ± 0.3%, which is not exploitable.

### 6.3 News events (`_spawn_event`)
See §7. Each event queues a return per affected stock.

### 6.4 Dependency spillovers (`_dependency_returns`)
After all of the above is queued, spillovers are added **in the same tick**:
- **Company links:** each company can list `dependencies: {source_ticker: sensitivity}`, giving `r_target += sensitivity × r_source`.
- **Sector links:** `sector_links: {source_sector: {target_sector: k}}`. The source sector's return is the pool-size-weighted average of its stocks' queued returns. For example, energy → airlines −0.18: an oil spike drags airlines down.

Spillovers use only the outside returns from this tick, not player trades, so you can't push one stock to move another.

### 6.5 Limits (`_flush_moves`)
- At most ±15% per tick (`MAX_TICK_MOVE`).
- A **daily envelope** on `fair`, measured from its value at the start of the game day: `±min(daily_move_cap = 15%, σ_d × (1.5 + 0.75 × min(|β|, 2)))`. NVXA: ±6.6% per game day from outside causes. Player trades are not limited.

### 6.6 Distress, bailout, bankruptcy (`_check_distress`)
When `fair / P0 ≤ distress_price_ratio` (0.25, i.e. down 75% from outside causes):
- With probability `bailout_chance` (25%), a bailout: price ×1.25, and the rating is reset to at least B.
- Otherwise bankruptcy: the price is cut by `bankruptcy_haircut` (50%), every holder is sold out along the curve with no fee, the remaining pool tokens go to the house reserve, and the ticker is delisted permanently.

A stock is checked once per distress episode. It can be checked again after recovering above 2× the threshold.

---

## 7. News

### 7.1 When news happens
- **Random events:** arrivals follow a Poisson process with mean gap `event_mean_seconds` = 120 s, so the gap is exponentially distributed and averages about one event every 2 real minutes.
- **Earnings:** each company with the `earnings` trait reports first after 1,800–5,400 s and then every 3,600–10,800 s, using the `earnings` template. These show in "Upcoming events".
- **Bank rating reviews:** every equity is reviewed every 7–14 game days (shown in "Upcoming events").
- **Regime shifts:** every 7–14 game days (3.5–7 real hours).

### 7.2 Picking and scoping a template
A random template is chosen with probability proportional to its `weight` (templates with weight 0, like `earnings`, only fire on schedule). Each has a `scope`:
- `market`: affects everything through `betas`, plus a market-wide move `index_move = index_bias × impact` applied to every stock by its beta. `index_bias` sets which way the whole market goes for the "up" headline. For example, "Ceasefire collapses" has −0.6, so the market falls while defense rises.
- `sector`: a sector (fixed or random); `self` in `betas` means that sector.
- `company`: a company (fixed `ticker`, a random one in `sector`, or any company); `self` means that company.

`betas` can key on a ticker, a sector id, `self`, or `*` (everything). They add up per stock, so a stock can be hit both as itself and through its sector.

### 7.3 Size of the move
```
strength ~ news_strength_weights   (bystander 25%, weak 40%, strong 25%, very strong 10%)
impact   ~ Uniform(news_move_ranges[strength])
           bystander 0–0.5% · weak 1–3% · strong 4–9% · very strong 10–18%

per stock:
  v        = clamp(√(σ / 0.30), 0.5, 1.8)          more volatile stocks react more
  crowd    = clamp(T / depth, 0.5, 2)               crowded pools react more
  R        = β·index_move·v + impact·beta_i·sens·crowd·v
  R        = clamp(R, ±σ_d × event_strength_limits[strength] × clamp(|β|, 0.5, 2))
             limits: bystander 0.1 · weak 0.35 · strong 0.65 · very strong 1.0 (× daily σ)
```
**In practice the final clamp decides the size.** For NVXA, even a "weak" headline computes to about 1.4–4.3% but is capped at 1.25%, and "very strong" is capped at 3.6%. To make news bigger or smaller, change `event_strength_limits` (and check with `tune.py`).

### 7.4 Direction
**A fair coin flip**, every time. The "up" or "down" headline text is chosen to match. Nothing about recent prices, the regime or other news makes either direction more likely, so the wire can't be front-run.

### 7.5 Breaking news vs rumours
- **Breaking** (non-rumour templates, or 40% of rumour-enabled ones): the full move happens **instantly** in the same tick as the headline. Players see the headline and the new price together, so there's nothing to front-run.
- **Rumour** (`rumor: true` templates, with probability `rumor_prob` = 60%):
  1. The rumour shows a direction that is correct with probability `c` = `rumor_credibility` = 0.75.
  2. The price immediately moves by the rumour's **expected value**: `pre = shown × (2c − 1) × R = shown × 0.5 × R`.
  3. 45–90 s later a **CONFIRMED** or **CORRECTION** headline arrives, and the price moves the rest of the way to the true outcome: `rest = (1 + sign·R) / (1 + pre) − 1`.

   Expected profit from trading on the rumour (to first order): `0.75 × (+0.5R) + 0.25 × (−1.5R) = 0`. Rumours are drama, not free money.

### 7.6 Ratings and regimes
- **Rating review:** profitable companies are upgraded 15%, downgraded 15%, maintained 70% (symmetric, so the scheduled date carries no expected move). Loss-making companies (`margin < 0`) are downgraded 65% of the time. Up or down fires a "weak" company event.
- **Regime:** the next regime is Expansion 44% (weak, random direction), Boom 22% (strong up), Bubble 12% (very strong up), or Recession 22% (strong down). A Bubble is always followed by a Recession (very strong down), so up and down shocks balance over time. The shift is applied instantly, scaled by each stock's beta.

### 7.7 News for the bots
Each event also leaves a "hint" (direction and betas). Only the news bots use hints, and only after the price has already moved.

---

## 8. Stocks, content packs and new listings

### 8.1 Where stocks come from
All `*.json` files in the project folder (except `state.json`) are **content packs**, merged in alphabetical order. Later files override earlier ones with the same id or ticker. A pack can contain:
- `settings`: any tuning value (later packs override earlier ones)
- `sectors`: `{id, name, icon}`
- `companies`: `{ticker, name, sector, desc, asset_type, beta, vol, sens, depth, rating, margin, traits, dependencies}`
- `templates`: news events (see §7)
- `profiles`: reference financials (from `market_profiles.json`), merged into the matching company

A company whose `sector` doesn't exist is skipped.

### 8.2 Listing (IPO)
Every tick, the engine compares content files' modification times. If any changed, it reloads them:
- **New ticker:** listed immediately. Its pool (`depth` tokens) is funded from the house reserve. If the reserve is short, the gap is minted as new house capital. A "NEW LISTING" headline goes out, and earnings and rating schedules are set.
- **Existing ticker:** its descriptive fields (name, beta, vol, financials) update in place. Its pool doesn't change.
- **Removed ticker:** stays trading until the next restart (see §13).
- **Delisted tickers** (bankrupt) never relist.

### 8.3 Financials are display-only
`market_profiles.json` gives each company a reference price, market cap, revenue, margin, cash, debt and dividend yield. The UI derives:
```
shares outstanding = reference market cap / reference price   (billions)
market cap         = shares outstanding × live price
net income         = revenue × margin
EPS                = net income / shares outstanding
P/E                = market cap / net income        (equities with positive earnings)
dividend yield     = reference yield × reference price / live price
```
These numbers are for flavour and realism only. **Trading uses only the pool** (`T`, `S`) and the price dynamics above. Market cap figures are in billions of MB; commodity prices show their unit (MB/barrel, MB/troy oz and so on).

`asset_type` is `equity`, `fund` or `commodity`. Funds and commodities skip rating reviews and show a shorter fact panel.

---

## 9. Indices

- **Meme Street Index:** starts at 100. Each tick it compounds the pool-size-weighted average of every stock's price change: `I ← I × (1 + Σ depth_i·(p_i/p_i,prev − 1) / Σ depth_i)`. It can't be traded.
- **Sector index:** `100 × Σ depth_i·(p_i / P0_i) / Σ depth_i` over the sector's stocks. 100 means the sector is at its reference prices.

---

## 10. Players, bots, seasons, leaderboard

### Players
- `POST /api/join {name}` creates an account (2–16 letters, numbers, `_-. `, unique, case-insensitive) and returns a **token**. The browser keeps it in `localStorage`, and that token is the whole login.
- New players are credited `signup_bonus` (1,000 MB test credit). Set it to 0 before real money.
- `deposited` tracks net money in (signup + deposits − withdrawals). **All-time P&L = equity − deposited.**

### Bots
Eight bots (2 each of random, momentum, contrarian and news), each with 1,000 MB of house capital. Each tick, each bot acts with probability `bot_action_probability` (1%), so about once per 100 s:
- **random:** 60% buy 5–20% of cash in a random stock; otherwise sell half or all of a holding.
- **momentum:** sells its worst 60-second performer and buys 25% of cash in the best.
- **contrarian:** the reverse of momentum.
- **news:** reacts to hints under 8 s old: sells holdings the news hits by more than 0.3, buys the top 2 it helps.

Bots show a 🤖 on the leaderboard. Their profit or loss is the house's (`bots_pnl`).

### Seasons
- Every `season_seconds` (1 hour) a season ends. The top 5 are recorded in history and a news item announces the winner.
- **Balances are never reset.** Each player's `season_base` is set to their current equity, so the next season's leaderboard starts from zero for everyone.
- **Season return** = `equity / season_base − 1`. Deposits during a season are added to `season_base`, so depositing doesn't count as a gain.
- The leaderboard sorts by season return. The **Score** column is a Sharpe-style ratio: the mean divided by the standard deviation of equity changes over the last 240 snapshots (taken every 5 s, so the last 20 minutes). It's shown but not used for ranking.

---

## 11. Charts and history

- **Minute candles:** every price change (trades and ticks) updates the current one-minute candle's high, low and close. The last 2 game days (120 candles) are kept and saved.
- **Day chart:** the minute candles from the last 1,800 s.
- **Daily candles:** when the game day rolls over, the finished day's open, high, low and close are stored under that day's number (up to 366 are kept and saved).
- **Week / Month:** the last 7 or 30 daily candles plus today's live candle. **Year:** 365 daily candles grouped into weekly candles.
- **"1d" change:** the current price vs the open of the first minute candle within the last 1,800 s.
- **Sparkline:** the last 60 one-second prices (not saved, so it rebuilds after a restart).
- The browser re-requests history every 5 s and updates the last candle with every live price. Hover a candle for its open, high, low and close. Scroll to zoom and drag to pan.

---

## 12. Server and protocol

### HTTP
| Endpoint | Purpose |
|---|---|
| `GET /` , `GET /stock/{ticker}` | the web page |
| `POST /api/join` `{name}` | create a player → `{token, name}` |
| `GET /api/admin/stats` | house P&L breakdown, deposits, invariant drift |
| `POST /api/admin/credit` `{name, amount}` | add MB to a player (stand-in for a crypto purchase) |
| `POST /api/admin/withdraw` `{name, amount}` | remove MB from a player's free cash |

Admin endpoints need the `X-Admin-Key` header to match the `ADMIN_KEY` environment variable. They are disabled if it isn't set.

### WebSocket `/ws?token=…`
- **Server → client every second:** `{"type":"state", ...}` with cash, equity, season return, P&L, holdings, all stocks (price, 1d change, sparkline, financials), sectors and sector indices, the last 30 news items, upcoming events, the top 10 of the leaderboard, your rank and the player count.
- **Client → server:**
  - `{"type":"trade","ticker":"NVXA","side":"buy","pct":0.25}` → reply `{"type":"result","ok":..,"msg":..}`
  - `{"type":"history","ticker":"NVXA","period":"day|week|month|year"}` → reply `{"type":"history","candles":[{t,o,h,l,c}...]}`

### Loop
`game_loop` in `server.py`: tick, save every 30 ticks, send each connected client its state, then sleep for the rest of the second. Everything runs on one asyncio thread, so trades, admin calls and ticks never run at the same time.

---

## 13. Saving and loading

- **When:** every 30 ticks and on shutdown. The save writes `state.json.tmp` and then replaces `state.json`, so a crash mid-write can't corrupt it.
- **What's saved (schema 6):** pools (`T`, `S`, depth, `fair`), candles, ratings, schedules, the house reserve, fees, house capital, minted, the index, regime, season number and end time, history, and players (cash, holdings, deposited, season base).
- **Not saved:** the news log, rumours waiting to confirm, sparklines, equity snapshots, trade cooldowns. They start empty after a restart. Earnings and reviews that fell due while the server was down are rescheduled, so they don't all fire at once.
- **Old saves** (schema 5 and earlier) are migrated: the old treasury becomes the house reserve, mislabelled daily candles are fixed, and any token gap left by the old engine is booked as house capital (with a log warning).
- **Up to 30 seconds of trades can be lost in a crash.** That's fine for play money, but not for real money (see `ROADMAP.md`, phase 2).

---

## 14. Settings reference

| Setting | Default | Effect |
|---|---|---|
| `signup_bonus` | 1000 | MB credited to new players (0 for real money) |
| `bots` / `bot_cash` / `bot_action_probability` | 8 / 1000 / 0.01 | bot count, bankroll, chance of acting per tick |
| `house_seed` | 50000 | starting house reserve (funds new listings) |
| `season_seconds` | 3600 | season length |
| `event_mean_seconds` | 120 | average gap between random news events |
| `news_strength_weights` | 25/40/25/10% | how often each strength appears |
| `news_move_ranges` | see §7.3 | raw impact before the clamp |
| `event_strength_limits` | 0.1/0.35/0.65/1.0 | event size cap, as a multiple of daily σ (the real size control) |
| `rumor_prob` / `rumor_credibility` / `rumor_delay_seconds` | 0.6 / 0.75 / 45–90 | rumour frequency, accuracy, time until confirmation |
| `earnings_initial_seconds` / `earnings_interval_seconds` | 1800–5400 / 3600–10800 | earnings schedule |
| `rating_review_days` | 7–14 | rating review interval (game days) |
| `regime_days` | 7–14 | regime length (game days) |
| `volatility_scale` | 1.0 | multiplies all noise and event caps |
| `daily_move_cap` | 0.15 | daily envelope cap; 0 disables the envelope |
| `mean_reversion_halflife_days` | 90 | reversion speed; keep at 90 or more (see §6.2) |
| `distress_price_ratio` / `bailout_chance` / `bailout_return` / `bankruptcy_haircut` | 0.25 / 0.25 / 0.25 / 0.5 | failure mechanics |
| `sector_links` | expansion.json | cross-sector spillovers |

Constants in `engine.py`: `FEE` 0.5%, `COOLDOWN` 1 s, `MAX_POOL_FRAC` 5%, `MAX_TICK_MOVE` 15%, `SNAP_EVERY` 5 s, `MARKET_DAY_SECONDS` 1800.

Leftover fields from the old engine that are now ignored: `event_duration_scale`, and `sev` / `chunks` in templates.

**Before changing any of these**, run `tune.py` on the old and new values with a fresh first seed. Keep `liqPnL` well below `fees`, keep the `value` and `hodl` columns near zero, and keep `drift` at about 1e-10.

---

## 15. Things to know

- **The house is the liquidity.** Pool depth is real money at risk once MB has value. Bigger depth means smaller price impact for players but more capital tied up. Liquidity P&L should hover around zero; watch it in `/api/admin/stats`.
- **Fees are the business.** 0.5% per side means about 1% per round trip. In the 6-hour simulations, 18 active traders generated about 3,700–4,400 MB in fees.
- **Player-vs-player profit is intended.** In the simulations, rumour traders profit mainly by selling to news chasers who buy late. That is exactly the "winners are paid by losers" behaviour you want.
- **Bots are house money.** If they beat players, the house is earning beyond fees. Decide how to handle them before real money (see `ROADMAP.md`).
- **Removing a company from the content files** while players hold it isn't handled well. On the next restart, its pool goes to the house and holders' shares count for nothing. Delist through gameplay, or pay holders out first, before deleting a company.
- **Signup bonus farming:** anyone can create unlimited accounts, each with 1,000 MB. That's harmless now, but it needs rate limits or the bonus set to 0 before MB is worth anything.
- **The token in localStorage is the only login.** Clearing the browser loses the account.
- **Only one server per save file.**
- **The README's original "one-week plan"** is superseded by `ROADMAP.md`.
