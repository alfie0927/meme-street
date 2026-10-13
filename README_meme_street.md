# Meme Street: setup and one-week plan

> **This is an old file.** Meme Street is now being turned into a site for learning to trade (1,000 MB to start, MB packages for sale and never cashed out, challenges that award MB, a market with drift, economic data and technical structure). The plan is in `ROADMAP.md`; how the code works today is in `HOW_IT_WORKS.md`. The setup steps below still work; the plan and the "not included" note at the end are from the first week and are out of date.

## Project files
```
engine.py               # market engine: pools, news/events, seasons, scoring, save/load
events_pack.json        # sector-specific news events (every sector has its own)
server.py               # FastAPI + WebSocket server (1 tick per second)
market_model.py         # the price model: drift, market phases, trends, ranges, support/resistance, volume, the macro calendar
realism.py              # checks the price model: long-run return, stylised facts, level odds, no free money (python realism.py)
chart_check.py          # measures the real engine's charts against real-market facts (MARKET_REALISM.md has the research)
economy.py, payments.py # the shop (MB packages, Pro), age rules, spending limits, the free restart; test mode and Stripe
learning.py, lessons.json # lessons with quizzes, challenges that pay MB, the trading journal
requirements.txt
index.html              # web interface
base.json               # sectors, companies, event templates, settings
expansion.json          # extra industries, companies, commodities, dependencies
market_profiles.json    # reference prices, share counts, USD financial estimates
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
1. Put a new `.json` file in the project root with any of `sectors`, `companies`, `templates` and `settings` (copy the shape from `pack_fiction.json`).
2. Within a second the engine reloads it: new sectors, listings and event types appear.
3. A new listing costs nothing: stocks hold no tokens, so the token total never changes.

Content packs are root-level `.json` files. The generated `state.json` is excluded from content loading.

Company fields include `ticker, name, sector, desc`, `asset_type` (`equity`, `fund`, or `commodity`), `beta`, `vol` (annualized decimal), `rating`, `depth`, and `dependencies` (source ticker to return sensitivity). `market_profiles.json` contains USD reference quotes, share-count estimates, market caps, annual revenue, margins, cash/debt estimates, and dividend yields. At load, shares outstanding are normalized from reference market cap / reference quote; each live market cap uses that share count times the displayed quote. Equity financials display in USD billions; commodity prices show their quote unit. Ratings, prices, and financials are illustrative real-market archetypes, not live prices or issuer-reported data.
Template fields include `scope` (market / sector / company), `up` / `down` headlines, `betas` (by ticker, sector id, `self` or `*`), `sev`, `strength`, `weight`, `rumor`, and `chunks`.

The market clock treats 30 minutes as one simulated trading day. Stock and index `1d` changes use a rolling 1,800-second window; detail charts offer day, week, month, and year ranges in this same game clock. Annualized volatility is converted to per-tick correlated market/sector/idiosyncratic returns, news effects are volatility-capped, and each stock has a beta-scaled daily move envelope capped at 15%. Event cadence, internal news impact ranges, rumor delay, event ramp duration, ratings, earnings cadence, and macro-regime timing are controlled by the `settings` objects in the content packs.

Click a ticker to open `/stock/TICKER` for a dedicated detail page. Saved pre-profile positions are automatically rescaled to the reference quote while preserving their AMM liquidation value and the token supply.

## Economics (the market itself is checked by `python realism.py` and `python chart_check.py`; see MARKET_REALISM.md)
- Currency is memebucks (MB). Every token is in exactly one place: player cash, the house reserve, or collected fees. `total_tokens() == minted` at all times; only deposits/withdrawals (`Engine.credit` / `Engine.debit`) and house capital injections change `minted`.
- Only trades move tokens. News, noise, regime shifts, bailouts and mean reversion change prices, never tokens, so they never create or destroy money.
- The house earns the 0.5% fee on each side of every trade. `house_stats()` splits house P&L into fees and liquidity P&L. Players' combined P&L is the mirror image of the house's.
- Nothing is predictable from public information: news direction is a coin flip, breaking news moves prices instantly, rumors move prices by their expected value (the confirmation/correction moves the rest), and dependency/sector spillovers land in the same tick as their cause. Mean reversion acts on each stock's exogenous fair value, never on player price impact.
- A Day (what used to be a season) is a leaderboard period of one real day, midnight to midnight UTC; balances carry over. Day return = equity / (equity at the start of the day + deposits) - 1. See HOW_IT_WORKS.md for how the game works today (this file is older).
- Bankruptcy cashes holders out at the stock's last price (no fee), paid from the house reserve.
- `signup_bonus` (base.json) is the starting balance: 1,000 MB.
- Price shocks carry no built-in direction: regime shifts balance up and down, credit reviews of profitable companies are equally likely to upgrade or downgrade, mean reversion pulls symmetrically in log price, and bankruptcy applies `bankruptcy_haircut` before paying holders so distressed stocks are not a free bet on a bailout.
- Tuning knobs (settings): `volatility_scale`, `event_strength_limits`, `daily_move_cap` (0 disables), `mean_reversion_halflife_days`, `news_move_ranges`, `event_mean_seconds`. Check any change to the market with `realism.py` and `chart_check.py`.

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
- Any way to cash MB out. The old idea of a crypto vault for real tokens was dropped on 2026-10-13: MB are a game currency, bought in packages and never paid out (`ROADMAP.md`).
