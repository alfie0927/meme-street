# Meme Street: setup and one-week plan

## Project files
```
engine.py               # market engine: pools, news/events, bots, seasons, scoring, save/load
sim.py                  # headless economy check with adversarial traders
tune.py                 # compare settings across seeds (python tune.py configs.json)
events_pack.json        # sector-specific news events (every sector has its own)
server.py               # FastAPI + WebSocket server (1 tick per second)
requirements.txt
index.html              # web interface
base.json               # sectors, companies, event templates, settings
expansion.json          # extra industries, companies, commodities, dependencies
market_profiles.json    # reference prices, share counts, USD financial estimates
space_pack.json.disabled # example content pack
```

## Run on Windows
```bash
python -m venv .venv
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.venv\\Scripts\\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000 in two browser tabs to try two players.

## Let other people play from your computer
Start the game as above, then in a second terminal run `python share.py` (the first time, `python share.py --install`). It prints a public `https://….trycloudflare.com` link to send to testers; it works while that window stays open and the game is running. Details, and what to set first (an `ADMIN_KEY`), are in `HOW_IT_WORKS.md`, section 1. For a bigger crowd, `python launch.py --gateways 4` runs the game plus four processes that hold the connections (`HOW_IT_WORKS.md`, section 12).

## Add content while the game runs
1. Copy `space_pack.json.disabled` to `space_pack.json` in the project root.
2. Within a second the engine reloads: a new Space sector, 3 IPOs and 2 new event types appear.
3. New companies are funded from the fee treasury first, then by trimming every pool pro rata, so the token total never changes.

Content packs are root-level `.json` files. The generated `state.json` is excluded from content loading.

Company fields include `ticker, name, sector, desc`, `asset_type` (`equity`, `fund`, or `commodity`), `beta`, `vol` (annualized decimal), `rating`, `depth`, and `dependencies` (source ticker to return sensitivity). `market_profiles.json` contains USD reference quotes, share-count estimates, market caps, annual revenue, margins, cash/debt estimates, and dividend yields. At load, shares outstanding are normalized from reference market cap / reference quote; each live market cap uses that share count times the displayed quote. Equity financials display in USD billions; commodity prices show their quote unit. Ratings, prices, and financials are illustrative real-market archetypes, not live prices or issuer-reported data.
Template fields include `scope` (market / sector / company), `up` / `down` headlines, `betas` (by ticker, sector id, `self` or `*`), `sev`, `strength`, `weight`, `rumor`, and `chunks`.

The market clock treats 30 minutes as one simulated trading day. Stock and index `1d` changes use a rolling 1,800-second window; detail charts offer day, week, month, and year ranges in this same game clock. Annualized volatility is converted to per-tick correlated market/sector/idiosyncratic returns, news effects are volatility-capped, and each stock has a beta-scaled daily move envelope capped at 15%. Event cadence, internal news impact ranges, rumor delay, event ramp duration, ratings, earnings cadence, and macro-regime timing are controlled by the `settings` objects in the content packs.

Click a ticker to open `/stock/TICKER` for a dedicated detail page. Saved pre-profile positions are automatically rescaled to the reference quote while preserving their AMM liquidation value and the token supply.

## Economics (checked by `python sim.py [hours] [seed]`)
- Currency is memebucks (MB). Every token is in exactly one place: player cash, a stock pool, the house reserve, or collected fees. `total_tokens() == minted` at all times; only deposits/withdrawals (`Engine.credit` / `Engine.debit`) and house capital injections change `minted`.
- Only trades move tokens. News, noise, regime shifts, bailouts and mean reversion change a pool's share count, not its tokens, so they never create or destroy money.
- The house earns the 0.5% fee on each side of every trade. It also seeds each pool's liquidity and runs the bots; `house_stats()` splits house P&L into fees, liquidity P&L and bot P&L. Players' combined P&L is the mirror image of the house's.
- Nothing is predictable from public information: news direction is a coin flip, breaking news moves prices instantly, rumors move prices by their expected value (the confirmation/correction moves the rest), and dependency/sector spillovers land in the same tick as their cause. Mean reversion acts on each stock's exogenous fair value, never on player price impact.
- A Day (what used to be a season) is a leaderboard period of one real day, midnight to midnight UTC; balances carry over. Day return = equity / (equity at the start of the day + deposits) - 1. See HOW_IT_WORKS.md for how the game works today (this file is older).
- Bankruptcy cashes holders out at the pool's last price (no fee); the remaining pool returns to the house reserve.
- `signup_bonus` (base.json) is a test credit; set it to 0 before real money is involved.
- Price shocks carry no built-in direction: regime shifts balance up and down, credit reviews of profitable companies are equally likely to upgrade or downgrade, mean reversion pulls symmetrically in log price, and bankruptcy applies `bankruptcy_haircut` before paying holders so distressed stocks are not a free bet on a bailout.
- Tuning knobs (settings): `volatility_scale`, `event_strength_limits`, `daily_move_cap` (0 disables), `mean_reversion_halflife_days`, `news_move_ranges`, `event_mean_seconds`. Check any change with `tune.py`; keep `liqPnL` well under `fees` and the `value`/`hodl` columns near zero.

## Admin (set `ADMIN_KEY` in the environment; endpoints are disabled without it)
- `GET /api/admin/stats`: house P&L, fees, player deposits/equity, invariant drift.
- `POST /api/admin/credit` / `POST /api/admin/withdraw` with `{"name": ..., "amount": ...}`: stand-ins for the crypto purchase and cash-out flow.
Send the key in the `X-Admin-Key` header.

## One-week plan
| Day | Goal | Done when |
|---|---|---|
| 1 | Run the skeleton, read engine.py end to end | Two tabs trading against each other |
| 2 | Tuning: use bots to balance volatility, fees, event size and rumor credibility | News bot no longer beats everyone by a wide margin |
| 3 | Content: 30+ companies, 20+ templates, 2 packs | Every sector has 2+ event types |
| 4 | UX: mobile layout, sound and flash on news, tutorial mode, chart page per stock | Friend can play without instructions |
| 5 | Anti-abuse: rate limits, name checks, multi-account detection, order caps | Bot spam and wash trades fail |
| 6 | Deploy (Fly.io / Railway / VPS), HTTPS, logging, SQLite persistence | Public URL, survives a restart |
| 7 | Closed beta with play money, collect feedback, fix | 10+ testers, no crashes for 24h |

## Not included (deliberately)
- The Solana vault for real tokens. Build and audit that only after the play-money version is fun and a lawyer has reviewed it.
