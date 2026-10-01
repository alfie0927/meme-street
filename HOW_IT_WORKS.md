# How Meme Street works

This document explains the whole system: what each file does, how prices and trading work, how money flows, how news, earnings and ratings are generated, and what to watch out for. Numbers quoted are the current defaults from `base.json` / `expansion.json` and the constants at the top of `engine.py`.

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
- **http://127.0.0.1:8000/holdings** for your holdings.
- **http://127.0.0.1:8000/docs** for FastAPI's automatic API explorer.

Alternatives:
- **VS Code:** Terminal → Run Task → "Meme Street Profile Engine". It runs the same command on port **8002**, so open http://127.0.0.1:8002.
- **While editing code:** add `--reload` so the server restarts when a `.py` file changes. Content `.json` files are hot-reloaded by the engine itself without a restart.

Stop the server with Ctrl+C. It saves `state.json` on a clean shutdown.

**Run only one server at a time.** Every server instance reads and writes the same `state.json`, so two servers overwrite each other's saves. A server also keeps running whatever code it started with: after changing code, stop it and start it again, then hard-refresh the browser (the page is served with `Cache-Control: no-store`, but an already-open tab keeps its old script).

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
| `engine.py` | The whole game: prices, trading, news and narrative, company stories, earnings, bank ratings, bots, seasons, accounting, save/load. Has no web code. |
| `server.py` | FastAPI app. Runs `engine.tick()` once a second, pushes state to browsers over WebSockets, and handles HTTP endpoints. |
| `index.html` | The entire front end: plain HTML, CSS and JS, no build step. One file serves three pages: the market (`/`), a stock (`/stock/{ticker}`) and holdings (`/holdings`). |
| `base.json` | Core content pack: settings, 9 sectors, the original companies, 11 event templates. |
| `expansion.json` | Extra sectors (utilities, industrials, telecom, materials, agriculture, commodities), more companies, risk settings, sector links. |
| `events_pack.json` | 17 sector-specific news templates. |
| `market_profiles.json` | Per-ticker reference price, share count, revenue, margin, cash, debt, dividend yield. |
| `space_pack.json.disabled` | Example pack. Rename it to `.json` while running to IPO three space companies live. |
| `sim.py` | Headless simulation with scripted "human" strategies; reports returns, house P&L, invariant. |
| `tune.py` | Runs `sim.py` across several setting overrides and seeds in parallel and prints a comparison table. |
| `state.json` | The save file (generated, git-ignored). |

---

## 3. Time

- **1 tick = 1 real second.** The server loop calls `engine.tick()` every second.
- **1 game day = 1,800 ticks = 30 real minutes** (`MARKET_DAY_SECONDS`). So the "30m" change shown next to prices (and the index) means one game day.
- **1 game year = 252 game days** (`TRADING_DAYS_PER_YEAR`), which is 126 real hours.
- **1 season = 3,600 s = 1 real hour** (`season_seconds`).

Everything shown to players is in **real time**: chart candle sizes, news and filing timestamps, and the countdowns in "Upcoming events".

Annualised volatility `σ` (each company's `vol`) converts to:
- daily: `σ_d = σ / √252`
- per tick: `σ_tick = σ / √(252 × 1800)`

Example, NVXA (`vol` 0.42): `σ_d` = 2.65% per game day and `σ_tick` = 0.062% per second.

---

## 4. Trading: how prices and trades work

**Player trades never move a price.** A stock's price is a single outside-world value (`fair`, see §6) driven only by noise, news, earnings and regimes. Players trade at that price against **the house**, long or short.

### Buying with `c` MB
```
fee    = c × 0.005               → house fee revenue
shares = (c − fee) / price       → given to the player
house reserve += c − fee
```

### Selling `sh` shares
```
gross    = sh × price
fee      = gross × 0.005         → house fee revenue
proceeds = gross − fee           → to the player (paid from the house reserve)
```

### Typing an amount
Next to the size chips there is an **amount box** (in MB). If it has a number in it, that number is used instead of the chip percentage: Buy spends that many MB, Sell sells that many MB worth, Short opens a short of that many MB, and Cover buys back that many MB. Picking a chip clears the box. The server accepts `amount` on a trade message; invalid, negative, zero, NaN or absurdly large amounts are rejected.

### Shorting
- **Sell when you hold none of the stock opens a short** (the button is labelled "Short"). The shares are sold at the market price and the proceeds are paid to you, but they stay **locked as collateral** while the short is open. The sell chips and the amount box set the size, as a share of your spare margin (below).
- **Buy while you are short covers it** (the button is labelled "Cover"). The chips mean a share of your short position; an amount means MB to spend buying back. You can't hold a long and a short in the same stock; cover first.
- **Your spare margin** is `equity − cost to close all your shorts`. A new short can be at most that big, so total shorts never exceed your equity (1× leverage).
- **Locked cash:** buys and withdrawals can only use `free cash = cash − cost to close all shorts`.
- **Margin call:** each tick, if equity falls below **25%** of what closing all your shorts would cost, every short is closed at the market price (you pay what you have, never going negative) and a toast says so. A short in a stock that goes bankrupt is closed at the haircut price.
- Fees are the same 0.5% on opening and on covering. There is no borrow charge.
- The average entry price, the amber chart line and the gain or loss work for shorts too (a short gains when the price falls).

### Limits per trade
- **Minimum:** 1 MB.
- **Cooldown:** 1 second between trades in the same stock (`COOLDOWN`). The page also ignores a second click on the same stock within 0.3 s.
- No size caps and no slippage: you get the displayed price. Limits are only your free cash and spare margin.

### Round trip
Buying and immediately selling back returns `c × 0.995 × 0.995`: about **1% lost to fees, nothing else**. A short opened and closed at the same price loses about 1% the same way.

### Average entry price
Each player has a `cost` per ticker: the total entry value of the open position (for a short, the value of the shares when sold). A buy or short adds `shares × price`. A sell or cover removes the same fraction of cost as of shares, so **the average entry price (`cost / |shares|`) is a share-weighted average across all entries and doesn't change when you close part of a position.** It is shown on the holdings page, in the stock page's position box, and as the dotted amber line on the chart. Saves from before cost tracking start each position at the price when the new code first loaded.

### Equity
Equity = cash + the sale value of each long (`shares × price × (1 − fee)`) − the cost to buy back each short (`shares × price × (1 + fee)`).

---

## 5. Where money lives (conservation)

Every memebuck is in exactly one of four places:

```
player cash  +  Σ stock T (seed liquidity)  +  house reserve  +  fees  =  minted
```

`total_tokens() == minted` is checked by `sim.py` (drift about 1e-10, floating-point rounding) and logged on load.

**What changes `minted`** (money entering or leaving the game):
- `credit(player, amount)`: a deposit or signup bonus (later: a crypto purchase)
- `debit(player, amount)`: a withdrawal (only free cash, not positions)
- the house putting in capital: listing seeds, the 50,000 MB reserve (`house_seed`), and bot bankrolls (`bot_cash`)

**What moves money between places:** trades (player cash ↔ house reserve, fees → fees) and bankruptcy (holders are paid from the house reserve at the haircut price, and the stock's seed liquidity returns to the reserve).

**What never moves money:** news, noise, mean reversion, regimes, earnings and bailouts. They change prices only.

### Who pays whom (important design change)
Before, every stock was a constant-product pool, so a player's trade moved the price and winners were mostly paid by other players. Because trades no longer move prices, **the house is the counterparty to every trade**:
- If a player profits, the money comes out of the house reserve. If a player loses, it goes into the reserve.
- **House P&L = fees − players' combined trading P&L − bot P&L.** `house_stats()` reports the parts.
- The house reserve can go below zero in the ledger if players win a lot. Nothing stops trades when it does, so watch `house_reserve` in `/api/admin/stats`.

Because there is no price impact, **no public-information edge may exist**. That is why news (§7), mean reversion (§6.2) and earnings are built so their expected price move is zero. `sim.py` checks it (see `ROADMAP.md`).

`T` per stock (the content pack's `depth`) is now just seed money the house put in at listing. It no longer affects prices, but it still counts toward house capital, and a stock's `base` (its `T` at listing) is the weight used for the indices and sector spillovers.

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
```
`Z_market` is shared by all stocks this tick, `Z_sector` by the stocks in one sector, and `Z_idio` is per stock. The result is clamped to ±1% per tick.

**Negative betas are hedges.** Gold (`GOLD`, β −0.3), the gold trust (`GLDN`, β −0.25) and the bond fund (`BOND`, β −0.15) move against the market factor, so they tend to rise when the market falls and vice versa. Regime shifts and market-wide news also move stocks by `β × index move`, so the same sign applies there: gold rises in a recession and falls in a boom. Several templates also list gold-specific betas (war, flight to safety and so on).

**Commodities trend.** `asset_type: commodity` stocks add a slow, mean-reverting drift on top of the noise (`trend ← 0.998·trend + small shock`), so they run in supply/demand cycles instead of pure noise.

### 6.2 Mean reversion (`_mean_revert`)
A slow pull of `fair` back toward the reference price `P0`:
```
rate = 1 − 0.5^(1 / (H × 1800))       H = mean_reversion_halflife_days = 90
r    = (P0 / fair)^rate − 1
```
Symmetric in log price. With `H` = 90 game days (45 real hours), half of any gap closes in about 2 real days.

*Why 90 and not faster:* at `H` = 7, a stock that dropped below 0.9× bounced about +1.8% in the next 30 minutes, which beats the 1% round-trip fee. With no price impact that would be a free edge against the house. Keep `H` at 90 or more.

### 6.3 News events (`_spawn_event`)
See §7. Each event queues a return per affected stock. Earnings reactions (§7.8) are queued the same way.

### 6.4 Dependency spillovers (`_dependency_returns`)
After the above is queued, spillovers are added **in the same tick**:
- **Company links:** `dependencies: {source_ticker: sensitivity}` gives `r_target += sensitivity × r_source`.
- **Sector links:** `sector_links: {source_sector: {target_sector: k}}`, using the base-weighted average of the source sector's queued returns. For example, energy → airlines −0.18.

### 6.5 Limits (`_flush_moves`)
- At most ±15% per tick (`MAX_TICK_MOVE`).
- A **daily envelope** on `fair`, measured from its value at the start of the game day: `±min(daily_move_cap = 15%, σ_d × (1.5 + 0.75 × min(|β|, 2)))`. NVXA: ±6.6% per game day.

### 6.6 Distress, bailout, bankruptcy (`_check_distress`)
When `fair / P0 ≤ distress_price_ratio` (0.25, i.e. down 75%):
- With probability `bailout_chance` (25%), a bailout: price ×1.25, and the rating is reset to at least B.
- Otherwise bankruptcy: the price is cut by `bankruptcy_haircut` (50%), every holder is paid `shares × price` from the house reserve (no fee), the stock's seed liquidity returns to the reserve, and the ticker is delisted permanently.

A stock is checked once per distress episode, and again only after it recovers above 2× the threshold. The index (`MSI`) is never checked.

---

## 7. News, narrative, company stories and ratings

### 7.1 When things happen
- **Random events:** a Poisson process with mean gap `event_mean_seconds` = 120 s.
- **Company stories** (§7.7): mean gap `issue_mean_seconds` = 100 s across the whole market.
- **Earnings:** every equity with revenue reports first after 1,800–5,400 s, then every 3,600–10,800 s. They show in "Upcoming events" as real-time countdowns.
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
  The follow-up quotes the original headline, moves prices like any news, and can chain once or twice more (30% each time). **To stop momentum from being a free edge**, the likelier continuation moves prices 0.8× and the rarer reversal 1.2×, so the expected move of a follow-up is zero whichever way you bet.
- Follow-ups to a company story also change what that company's next earnings report shows (a continuation adds half the original effect, a reversal undoes 70% of it), and the report names them ("further developments in …", "a reversal after …").
- Memory is saved with the game state (up to 40 stories), and every headline that names a stock stays in that stock's news log.

### 7.5 Size of the move
```
strength ~ news_strength_weights   (bystander 25%, weak 40%, strong 25%, very strong 10%)
impact   ~ Uniform(news_move_ranges[strength])
           bystander 0–0.5% · weak 1–3% · strong 4–9% · very strong 10–18%

per stock:
  v        = clamp(√(σ / 0.30), 0.5, 1.8)          more volatile stocks react more
  crowd    = clamp(T / base, 0.5, 2)
  R        = β·index_move·v + impact·beta_i·sens·crowd·v
  R        = clamp(R, ±σ_d × event_strength_limits[strength] × clamp(|β|, 0.5, 2))
```
then multiplied by the narrative scale from §7.3. **The final clamp usually decides the size.** To make news bigger or smaller, change `event_strength_limits` and check with `tune.py`.

### 7.6 Breaking news vs rumours
- **Breaking:** the full move happens instantly in the same tick as the headline.
- **Rumour** (`rumor: true` templates, with probability `rumor_prob` = 60%): the rumour shows a direction correct with probability `rumor_credibility` = 0.75, the price moves by its expected value (`0.5 × R`), and 45–90 s later a **CONFIRMED** or **CORRECTION** headline moves it the rest of the way. Expected profit from trading a rumour is zero.

### 7.7 Company stories and earnings (the "reason" for a change)
Financials (revenue, net margin, cash, debt) now **evolve** and are saved. They don't change at random: a big change needs a story that was **in the news first**.

1. **A story breaks** (`_issues`). A random equity gets a headline such as "X warns of supply-chain disruption at a key supplier", "X's CEO faces board pressure", "X wins a major multi-year contract" or "X pays down debt ahead of schedule". There are 6 negative and 5 positive kinds. The chance of good news is `0.5 + 0.25 × (safety − 0.5) + 0.25 × company mood`, so weaker or gloomier companies draw bad news a little more often. The price reacts immediately (a "weak" or "strong" company event).
2. **The story is remembered** against the company with its effect on margin, revenue and debt.
3. **At the next earnings report** all remembered stories are applied together:
   - margin moves by the stories' effect, then 15% of the way back toward the company's long-run margin, plus a small noise term (±0.8 points)
   - revenue grows 1% plus the stories' effect plus small noise (±1%)
   - debt scales by the stories' effect; cash grows by 12% of net income (if cash would go negative, the shortfall becomes debt)
   - an **EARNINGS** headline reports revenue and margin and **names the earlier stories** ("Driven by a supply-chain disruption; new management, as flagged in earlier news.")
   - the price reaction is only the unannounced noise (capped at ±6%), since the stories already moved the price.
4. If no story was flagged, the headline says "No major changes were flagged beforehand" and the numbers barely move.

So a firm that is doing well can report badly, but only after a story the player could have seen. **Players can look back:** every stock page lists *Earnings history* (each report with the stories that caused it and when they were flagged) and *Company news & analyst notes* (every headline that named the stock).

### 7.8 Bank ratings
Rating ladder: `D C CC CCC B BB BBB A AA AAA`.

- Each equity has a hidden **safety** score (0.3–0.85 at listing, drifting slightly at each review). Banks "know" it; players have to infer it.
- A bank's **score** (0–1) is `0.30·safety + 0.25·(1 − volatility penalty) + 0.15·(1 − beta penalty) + 0.30·balance sheet`, where the balance sheet combines margin, cash minus debt, and debt relative to revenue. The score is stretched onto the ladder, and each of 6 fictional banks has a small bias (some are stricter).
- At each review a bank compares its target rating with the current one. If they differ, it moves the rating **one notch** toward the target (70% of the time) and publishes it as a price-target note: *"Quill Capital lowers price target on X to 80.17 MB, citing leverage concerns"*. The note moves the price as a "weak" company event. If nothing changes, it sometimes publishes a "reiterates" note with no price move.
- Initial ratings come from the same formula, so ratings now reflect safety, volatility, beta and the financials, and change as earnings change those financials.
- Commodities, funds and the index have no rating.

### 7.9 News for the bots
Each event leaves a "hint" (direction and betas). Only the news bots use hints, and only after the price has already moved.

---

## 8. Stocks, content packs and new listings

### 8.1 Where stocks come from
All `*.json` files in the project folder (except `state.json`) are **content packs**, merged in alphabetical order. Later files override earlier ones with the same id or ticker. A pack can contain:
- `settings`: any tuning value
- `sectors`: `{id, name, icon}`
- `companies`: `{ticker, name, sector, desc, asset_type, beta, vol, sens, depth, rating, margin, traits, dependencies}`
- `templates`: news events (see §7)
- `profiles`: reference financials (from `market_profiles.json`), merged into the matching company

A company whose `sector` doesn't exist is skipped.

### 8.2 Listing (IPO)
Every tick, the engine compares content files' modification times and reloads them if any changed:
- **New ticker:** listed immediately, funded from the house reserve (any shortfall is minted as house capital). A "NEW LISTING" headline goes out, and earnings and review schedules are set.
- **Existing ticker:** descriptive fields (name, beta, vol, description) update in place. **Financials do not reset**, because they now evolve with earnings.
- **Removed ticker:** stays trading until the next restart (see §15).
- **Delisted tickers** (bankrupt) never relist.

### 8.3 Financials
`market_profiles.json` gives each company its starting reference price, market cap, revenue, margin, cash, debt and dividend yield. The page derives:
```
shares outstanding = reference market cap / reference price   (billions)
market cap         = shares outstanding × live price
net income         = revenue × margin
EPS                = net income / shares outstanding
P/E                = market cap / net income        (equities with positive earnings)
dividend yield     = reference yield × reference price / live price
```
Revenue, margin, cash and debt change at earnings (§7.7) and feed the bank ratings (§7.8). Share counts and the reference price stay fixed. Market cap figures are in billions of MB.

`asset_type` is `equity`, `fund`, `commodity` or `index`. Prices are shown as plain "MB" (no per-barrel or per-ounce unit).

---

## 9. Indices and trading the index

- **Meme Street Index:** starts at 100. Each tick it compounds the `base`-weighted average of every stock's price change: `I ← I × (1 + Σ base_i·(p_i/p_i,prev − 1) / Σ base_i)`.
- **It is tradable** as ticker **`MSI`** (asset type `index`), at a price equal to the index level. It trades like any stock: at the market price against the house, with the 1-day (30m) change, charts, holdings and average price all working. News, noise and distress never touch it directly.
- **Sector index:** `100 × Σ base_i·(p_i / P0_i) / Σ base_i` over the sector's stocks. It is shown on stock pages but isn't tradable.

---

## 10. Players, bots, seasons, leaderboard

### Players
- `POST /api/join {name}` creates an account (2–16 letters, numbers, `_-. `, unique, case-insensitive) and returns a **token**. The browser keeps it in `localStorage`, and that token is the whole login.
- New players are credited `signup_bonus` (1,000 MB test credit). Set it to 0 before real money.
- `deposited` tracks net money in (signup + deposits − withdrawals). **All-time P&L = equity − deposited.**

### Bots
Eight bots (2 each of random, momentum, contrarian and news), each with 1,000 MB of house capital. Each tick, each bot acts with probability `bot_action_probability` (1%):
- **random:** 60% buy 5–20% of cash in a random stock; otherwise sell half or all of a holding.
- **momentum:** sells its worst 60-second performer and buys 25% of cash in the best.
- **contrarian:** the reverse of momentum.
- **news:** reacts to hints under 8 s old.

Bots show a 🤖 on the leaderboard. Their profit or loss is the house's (`bots_pnl`).

### Seasons
- Every `season_seconds` (1 hour) a season ends. The top 5 are recorded and a news item announces the winner.
- **Balances are never reset.** Each player's `season_base` is set to their current equity.
- **Season return** = `equity / season_base − 1`. Deposits during a season are added to `season_base`.
- The leaderboard sorts by season return. The **Score** column is a Sharpe-style ratio over the last 240 snapshots (every 5 s); it isn't used for ranking.

---

## 11. The web pages and charts

### Pages
- **Market (`/`):** a table of every listing (including `MSI`; the Held column shows `(short)` for shorts), sector filters, buy/sell size chips and the amount box, news wire (with times and ticker links), upcoming events, leaderboard. The header shows the index, cash, equity, P&L, season return and rank. Nothing on any page shows the market's mood or regime.
- **Stock (`/stock/{ticker}`):** price and change, description, buy/sell (labelled **Short** / **Cover** when that is what the button will do), the **amount box**, your position box (shares, average entry price, value, gain or loss; labelled "short" for shorts), the chart, financial facts, *Earnings history* and *Company news & analyst notes* (§7.7).
- **Holdings (`/holdings`):** cash, positions value, total cost, open P/L and equity, plus one row per holding: side (Long or SHORT), shares, average entry price, price, value, P/L in MB and in %.

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
| Endpoint | Purpose |
|---|---|
| `GET /`, `GET /holdings`, `GET /stock/{ticker}` | the web page (`Cache-Control: no-store`) |
| `POST /api/join` `{name}` | create a player → `{token, name}` |
| `GET /api/admin/stats` | house P&L breakdown, deposits, invariant drift |
| `POST /api/admin/credit` `{name, amount}` | add MB to a player |
| `POST /api/admin/withdraw` `{name, amount}` | remove MB from a player's free cash |

Admin endpoints need the `X-Admin-Key` header to match the `ADMIN_KEY` environment variable. They are disabled if it isn't set.

### WebSocket `/ws?token=…`
- **Server → client every second:** `{"type":"state", ...}` with cash, equity, season return, P&L, **holdings** (ticker, `side`, shares, avg entry price, price, cost, value, P/L, P/L %), `notices` (one-off messages such as margin calls), and no narrative or mood data, all stocks (price, 30m change, sparkline, financials), sectors, the last 30 news items, upcoming events, the leaderboard top 10, your rank and the player count.
- **Client → server:**
  - `{"type":"trade","ticker":"NVXA","side":"buy","pct":0.25}` or with `"amount": 50` (MB, overrides `pct`) → `{"type":"result","ok":..,"msg":..}`
  - `{"type":"history","ticker":"NVXA","period":"30s|1m|5m|15m|30m|1h|2h|4h|1d|1mo|1y"}` → `{"type":"history","period":..,"candles":[{t,o,h,l,c}...],"now":..}` (old period names fall back to 30s)
  - `{"type":"company","ticker":"NVXA"}` → `{"type":"company","log":[...],"reports":[...]}` for the stock page's news log and earnings history

### Loop and robustness
`game_loop` in `server.py`: tick, save every 30 ticks, then start one **background send task per connected client** and sleep for the rest of the second.
- A client that is still receiving the previous update is skipped, and a send that takes over 3 s drops that client, so one stuck connection can't delay the game.
- Messages that aren't valid JSON objects, are over 2,000 characters, or have bad fields are ignored. History and company lookups are limited to one per 0.2 s per connection.
- The page reconnects automatically with a growing delay, and keeps one socket at a time.

---

## 13. Saving and loading

- **When:** every 30 ticks and on shutdown. The save writes `state.json.tmp` and then replaces `state.json`.
- **What's saved (schema 7):** per stock: seed liquidity `T`, `base`, `fair` (the price), candles for every timeframe, daily candles, rating, hidden safety, mood, trend, **financials** (revenue, margin, cash, debt, long-run margin), pending stories, news log, earnings reports, schedules; globally: house reserve, fees, house capital, minted, index, regime, market and sector mood, crisis end time, **every headline printed (last 6,000)**, remembered story threads, season data; players: cash, holdings (negative = short), **cost basis**, deposited, season base.
- **Not saved:** the global news wire (`news_log`), rumours waiting to confirm, sparklines, equity snapshots, trade cooldowns. Per-stock news logs *are* saved.
- **Older saves** (before schema 7) load with the old pool price as the market price, positions starting at the current price as their average entry, ratings recomputed, and the old pool fields dropped.
- **Up to 30 seconds of trades can be lost in a crash** (see `ROADMAP.md`, phase 2).

---

## 14. Settings reference

| Setting | Default | Effect |
|---|---|---|
| `signup_bonus` | 1000 | MB credited to new players (0 for real money) |
| `bots` / `bot_cash` / `bot_action_probability` | 8 / 1000 / 0.01 | bot count, bankroll, chance of acting per tick |
| `house_seed` | 50000 | starting house reserve (funds new listings) |
| `season_seconds` | 3600 | season length |
| `event_mean_seconds` | 120 | average gap between random news events |
| `issue_mean_seconds` | 100 | average gap between company stories (§7.7) |
| `news_strength_weights` | 25/40/25/10% | how often each strength appears |
| `news_move_ranges` | see §7.5 | raw impact before the clamp |
| `event_strength_limits` | 0.1/0.35/0.65/1.0 | event size cap, as a multiple of daily σ (the real size control) |
| `rumor_prob` / `rumor_credibility` / `rumor_delay_seconds` | 0.6 / 0.75 / 45–90 | rumour frequency, accuracy, time until confirmation |
| `earnings_initial_seconds` / `earnings_interval_seconds` | 1800–5400 / 3600–10800 | earnings schedule (real seconds) |
| `rating_review_seconds` | 600–1500 | bank review interval per stock (real seconds) |
| `regime_days` | 7–14 | regime length (game days) |
| `volatility_scale` | 1.0 | multiplies all noise and event caps |
| `daily_move_cap` | 0.15 | daily envelope cap; 0 disables the envelope |
| `mean_reversion_halflife_days` | 90 | reversion speed; keep at 90 or more (see §6.2) |
| `distress_price_ratio` / `bailout_chance` / `bailout_return` / `bankruptcy_haircut` | 0.25 / 0.25 / 0.25 / 0.5 | failure mechanics |
| `sector_links` | expansion.json | cross-sector spillovers |

Constants in `engine.py`: `FEE` 0.5%, `COOLDOWN` 1 s, `MAX_TICK_MOVE` 15%, `SNAP_EVERY` 5 s, `MARKET_DAY_SECONDS` 1800, `TIMEFRAMES`, the narrative text pools and `ISSUES` (company stories), `BANKS`, `RATINGS`.

Per-template field `good` (`"down"`): marks the "down" text as the good news.

Fields now ignored: `event_duration_scale`, `sev` / `chunks` in templates, `rating_review_days`, and the `earnings` trait (every equity with revenue reports).

**Before changing any of these**, run `tune.py` on the old and new values with a fresh first seed. Keep the `value` and `hodl` columns near zero and `drift` at about 1e-10.

---

## 15. Things to know

- **The house is the counterparty.** With no price impact, every trade is against the house reserve. Over many players the house earns the fees, but a lucky or skilled player is paid by the house, not by other players. This differs from the goal in `ROADMAP.md` ("player profits come from other players' losses"); decide whether that is acceptable before real money.
- **No edge is allowed.** News, mean reversion and earnings are built to have zero expected move. Anything that makes prices predictable from public information is a house-funded edge now, with no slippage to stop it.
- **Few size limits.** A player can trade their whole free cash in any stock at the displayed price, and short up to 1× their equity. A short in a stock that jumps can close at a loss the house absorbs if the player's cash runs out before a margin call fires.
- **Fees are the business.** 0.5% per side means about 1% per round trip.
- **Player-vs-player profit** no longer exists in the pricing; a player's gain is the house's loss.
- **Bots are house money.** If they beat players, the house earns beyond fees (see `ROADMAP.md`).
- **Removing a company from the content files** while players hold it isn't handled well. On the next restart, its listing is dropped and holders' shares are discarded. Delist through gameplay first.
- **Signup bonus farming:** anyone can create unlimited accounts, each with 1,000 MB. Needs rate limits (or the bonus at 0) before MB is worth anything.
- **The token in localStorage is the only login.** Clearing the browser loses the account.
- **Only one server per save file.**

---

## Keeping the docs current

After every code or content change, update this file so it describes what the code does now, and tick or adjust the matching items in `ROADMAP.md`. Check `ROADMAP.md` before starting any new work.
