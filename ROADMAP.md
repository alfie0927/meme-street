# Meme Street roadmap

Goal: a trading game where players buy memebucks (MB) with crypto and trade fictional stocks against each other. The house earns the 0.5% fee on every trade. Player profits come from other players' losses, and no strategy based on public information should be able to win reliably from the house.

## Where things stand (2026-10-01)

Done:
- Token conservation. Tokens move only through trades, fees are separate house revenue, and the token invariant holds to about 1e-10.
- **Changed 2026-10-01: player trades no longer move prices.** Every trade fills at the market price against the house, so the economy is no longer player-vs-player (see open questions). The old "no house-funded edges" result (six strategies, house pool liquidity roughly flat) was measured on the old pool design; re-check it with `sim.py` and `tune.py` before relying on it.
- Seasons are leaderboard periods only; balances carry over.
- MB currency in the UI and admin stats/credit/withdraw endpoints.
- Charts with 11 real-time timeframes (30s to 1Y), a centred newest candle that thins out as candles arrive, free zoom-out, and a dotted average-entry line. A holdings page with average entry price and gain or loss.
- The Meme Street Index is tradable (`MSI`). Gold, gold trust and bonds hedge the market (negative beta); commodities trend.
- Company stories, earnings and bank ratings: stories are announced in the news first, earnings then change revenue, margin and debt and cite them, and ratings come from hidden safety, volatility, beta and the financials. Each stock page shows its earnings history and news log.
- News with a hidden narrative: market, sector and company moods (regime, crisis) tilt whether headlines skew good or bad, but players are never shown the mood and nothing in the wording names it. The price move is scaled so the expected move stays zero, and no two headlines are identical.
- News memory: stories can come back as follow-ups (continuations) or switch-ups (reversals) that quote the original headline, with sizes balanced so neither is a free bet. Follow-ups to company stories also change the next earnings report.
- Shorting and typed amounts: Sell with no position opens a short (Buy then covers it); shorts are limited to 1x equity, proceeds are locked as collateral, and a margin call closes them below 25%. An MB amount box overrides the percentage chips.
- Server hardening: background per-client sends with a timeout, malformed-message handling, lookup rate limits, and a front end that updates in place (no lost clicks). Stress-tested with 60 clients.
- 42 listings (including `MSI`) and 31 event templates, with every sector covered.
- `sim.py` and `tune.py` for checking any change to the economy.

Not done: anything to do with real money, accounts, a production database, or deployment.

## Phase 1: Closed play-money test (weeks 1-2)

Setup:
- [ ] Stop any running servers, delete `state.json`, and start one server (the VS Code task, port 8002). Only one server may run at a time because they share the save file.
- [ ] Set `ADMIN_KEY` before starting the server so `/api/admin/stats` works.
- [ ] Make it reachable for friends: a tunnel (Cloudflare Tunnel or ngrok) is fine at this stage.
- [ ] Invite 5-10 people. Keep `signup_bonus` at 1000.

What to watch (`GET /api/admin/stats` with header `X-Admin-Key`):
| Metric | Healthy | Investigate if |
|---|---|---|
| `invariant_drift` | about 0 | above 0.000001 |
| `fees` | grows with activity | flat while people are trading |
| `liquidity_pnl` | small, positive or negative | a steady loss above about 30% of `fees` |
| `players_pnl` | about minus `fees` | positive and growing (someone found an edge) |
| One player's season return | spread across players | the same player tops every season by a wide margin |

Questions for testers:
- Was it obvious what to do within the first minute?
- Did prices and news feel connected?
- Did you feel you lost to other players or to "the game"?
- Would you come back tomorrow? What would make you?

Done when: 10+ testers have played, there have been no crashes for 24 hours, and nobody has a strategy that wins every season.

## Phase 2: Hardening (weeks 3-5)

- [ ] Replace `state.json` with SQLite (later Postgres) and append-only ledgers for trades, deposits and withdrawals. Today a crash loses up to 30 seconds of trades.
- [ ] Real accounts. Today the only login is a token in the browser's localStorage, so clearing the browser loses the account. Use email login or wallet sign-in.
- [ ] Rate limits on `/api/join` and on trades per account. (Done so far: 1 s trade cooldown per stock, history lookups limited to one per 0.2 s per connection, oversized or malformed messages ignored.)
- [ ] Multi-account detection (IP, device, wallet). This matters once deposits are real; while the signup bonus exists, it matters for test-credit farming.
- [ ] Deploy with HTTPS (Fly.io, Railway or a VPS). Ship logs somewhere searchable, and set up a daily database backup.
- [ ] Tests: turn `sim.py` checks into a CI test that fails if `invariant_drift` exceeds 1e-6 or if `liquidity_pnl` falls below -0.3 x `fees`.
- [ ] Mobile layout pass.

## Phase 3: Public beta, still play money (weeks 5-8)

- [ ] Open signups. Measure daily active players, trades per player and fee revenue per player.
- [ ] Re-run `tune.py` with real activity levels and adjust `event_mean_seconds`, `news_move_ranges` and `bot_action_probability`.
- [ ] Decide what to do with bots before money is real (see open questions).
- [ ] Add content packs regularly. New listings are funded from the house reserve.

## Phase 4: Legal gate (before any real money)

Selling MB for crypto, letting players cash out, and the house providing pool liquidity and running bots can all fall under regulation. Get a lawyer's opinion, for the countries you'll allow, on:
- Gambling or skill-gaming licensing
- Money transmission and virtual-asset rules, including identity checks and anti-money-laundering requirements
- Whether trading fictional "stocks" for withdrawable value raises securities or derivatives issues
- Terms of service, age limits, restricted countries, and how house-run bots are disclosed

Do not build the payment flow until this answer is in.

## Phase 5: Real money (after legal sign-off)

- [ ] Crypto deposits build on `Engine.credit`. Credit only after enough on-chain confirmations.
- [ ] Withdrawals build on `Engine.debit`. Approve them manually at first, with per-day caps.
- [ ] Set `signup_bonus` to 0.
- [ ] Reconcile daily: on-chain balance must be at least player cash plus player equity.
- [ ] Launch with low deposit caps, then raise them as the numbers hold.

## Open questions

- **The house is now the counterparty to every trade (new).** With no price impact, a winning player is paid from the house reserve and a losing player pays it. The roadmap's goal was that profits come from other players' losses. Options: keep it (the house takes the market risk and earns fees), add per-player or per-stock position limits, make the house hedge, or bring back some price impact. Watch `house_reserve` and `players_pnl` in `/api/admin/stats`; the reserve can now go negative.
- **House capital at risk.** The house put about 834,000 MB into listings (`depth`), bot bankrolls and the reserve. The listing seed no longer affects prices, but the reserve now pays out player winnings. Decide what 1 MB costs and how much real capital that represents.
- **No size limits on trades.** There is no slippage and no cap, so a player can put their whole free cash into any stock at the shown price. Consider caps before real money.
- **Shorting risk to the house (new).** Shorts are paid for by the house like every other trade. If a stock gaps up faster than the 25% margin call can react (a very strong event), the player's cash can run out and the house eats the loss. There is no borrow fee. Test with `sim.py` strategies that short, and consider a borrow fee, lower leverage, or a per-stock short cap before real money.
- **Hidden mood can still be inferred.** Players can't see the mood, but they could estimate it by counting good and bad headlines. That has no price edge by design (the move size is scaled to cancel it), but check this with `sim.py` once a "mood-reading" strategy exists.
- **Narrative news edge.** Headlines skew good or bad with the mood, but the price move is scaled to keep the expected move zero. Verify with `sim.py` and `tune.py` over several seeds that no strategy profits from the regime or crisis state.
- **Bots.** They trade with house money. When they win, the house is taking money from players beyond fees. Options: remove them for real money, label them clearly (they already show a robot icon), or keep them only in a play-money mode.
- **Value strategy (re-check needed).** After the no-price-impact change, five fresh seeds (2026-10-01, 3-4h each) gave `value` returns of +20.5%, +0.5%, +1.6%, +9.8% and +2.6% on only 2-9 trades per run, while news chasing, rumour trading and dip buying lost to fees. The average is positive but noisy. With no slippage, buying below the reference price is now paid for by the house, so run `tune.py` over many seeds and consider a longer mean-reversion half-life if it holds. Before the change: buying stocks below their reference price still made money in the simulations, but almost all of it came from other players. Keep `mean_reversion_halflife_days` at 90 or longer; at 7 it was a house-funded edge.
- **Fee level.** 0.5% per side is the main revenue lever. Higher fees mean more revenue per trade but fewer trades. Test 0.3%, 0.5% and 1% in beta.

## Checking any economy change

```bash
.venv\Scripts\python.exe sim.py 6 1                      # one detailed run
.venv\Scripts\python.exe tune.py configs.json 6 6 101    # compare settings on fresh seeds
```
Configs that run on the same seeds share market paths, so confirm any conclusion on a fresh starting seed.
