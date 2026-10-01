# Meme Street roadmap

Goal: a trading game where players buy memebucks (MB) with crypto and trade fictional stocks against each other. The house earns the 0.5% fee on every trade. Player profits come from other players' losses, and no strategy based on public information should be able to win reliably from the house.

## Where things stand (2026-10-01)

Done:
- Zero-sum economy. Tokens move only through trades, fees are separate house revenue, and the token invariant holds to about 1e-10.
- No known house-funded edges. Six simulated strategies were tested (news chasing, rumor trading, value, dip buying, buy-and-hold, retail). On fresh seeds, house pool liquidity is roughly flat (-56 to -136 MB per 6h) against about 3,800 MB in fees.
- Seasons are leaderboard periods only; balances carry over.
- MB currency in the UI, accurate candlestick charts, and admin stats/credit/withdraw endpoints.
- 41 listings and 31 event templates, with every sector covered.
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
- [ ] Rate limits on `/api/join` and on trades per account.
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

- **House capital at risk.** The pools are seeded with about 834,000 MB of house liquidity, and that liquidity is the counterparty to every player. Decide what 1 MB costs and how much real capital that represents. Pool `depth` in the content packs sets it.
- **Bots.** They trade with house money. When they win, the house is taking money from players beyond fees. Options: remove them for real money, label them clearly (they already show a robot icon), or keep them only in a play-money mode.
- **Value strategy.** Buying stocks below their reference price still made money in the simulations, but almost all of it came from other players. Keep `mean_reversion_halflife_days` at 90 or longer; at 7 it was a house-funded edge.
- **Fee level.** 0.5% per side is the main revenue lever. Higher fees mean more revenue per trade but fewer trades. Test 0.3%, 0.5% and 1% in beta.

## Checking any economy change

```bash
.venv\Scripts\python.exe sim.py 6 1                      # one detailed run
.venv\Scripts\python.exe tune.py configs.json 6 6 101    # compare settings on fresh seeds
```
Configs that run on the same seeds share market paths, so confirm any conclusion on a fresh starting seed.
