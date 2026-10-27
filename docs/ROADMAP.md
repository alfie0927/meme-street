# Meme Street roadmap

**Goal:** an informational game where people **learn to trade, or just trade for fun**, on a realistic, fictional
stock market. **Technical analysis is the core** (charts that behave like real charts, and the tools to read them);
news and the economy are background. The market drifts slowly upwards, with corrections, bear phases and sideways
stretches, and prices respect and break support and resistance the way real charts do. Everyone starts with
**1,000 MB**; MB are a game currency with no cash value, never paid out. The site earns from **MB packages** and
**Pro and Expert passes** (monthly or yearly). **The Daily Chart** is the daily reason to come back and the thing
people share.

Companion doc: `HOW_IT_WORKS.md` describes what the code does **today**. Update it after every change, and check this
file before starting any work. Size key: **S** = under a day, **M** = a few days, **L** = a week or more.

*Rewritten 2026-10-24: finished and dropped work is reduced to a "done" line per track (the IDs stay, since the code
and HOW_IT_WORKS refer to them); the plan before 2026-10-13 (a real-money game) is gone.*

---

## 1. Design rules

1. **Realism you can learn from.** Behaviour real markets show appears at realistic rates: a support level holds often
   enough to be worth trading and breaks often enough that a stop is needed.
2. **No free money.** No simple, unskilled rule (buy everything, buy every dip, always fade, doubling down, shorting
   everything) may beat holding the index by a wide margin, costs included. Skill shows as better *risk-adjusted*
   results over many trades, never as a guaranteed win. Checked by `tools/realism.py` and `tools/option_check.py`.
3. **Players' trades never move prices.** The market is the same for everyone, and a big account cannot push it.
4. **Paying never buys a rank.** The boards rank return on money put in (and profit), so buying MB gives more capital
   to practise with, not a better place. (Leverage bends this: section 6, risk 4.)
5. **Honest selling.** Prices are shown before every purchase, MB are clearly worthless outside the site, there is no
   purchase prompt at the moment of a loss, and there are spending limits.
6. **Every MB is accounted for.** Every money event is in the ledger with its source (start, purchase, reward, refund,
   admin); `total_tokens == minted` always.

---

## 2. Where things stand (24 October 2026)

**Live on https://memestreet.net** (one Hetzner server, Caddy, a game server and two gateways, fail2ban, the admin
pages behind a second password). **The shop takes real money**: Stripe Checkout through *Managed Payments* (Stripe is
the merchant of record and handles VAT and sales tax), purchases credited within a second by a signed webhook, a
payment check four times a day that completes any purchase whose webhook was lost. Backups every six hours on the
server, copied to this computer every day at 09:00; `/api/health` checked every 15 minutes by GitHub Actions.
10 accounts, some still on the old 10,000-MB start (O11).

| Area | Built | Open |
|---|---|---|
| The market | Drift, regimes, trends in legs, ranges and breakouts, support and resistance of many kinds, volume that confirms, wicks, engulfing turns, squeezes, gaps, ten named chart patterns, volatility clustering and fat tails, sessions; the MSI 50 by market value (sizes on a smooth curve since 2026-10-24); realism and no-free-money checks | P8 psychology, P9 factors, P10 asset classes, P12, P13 |
| Charts and trading | Crosshair, five chart types, log scale, 49 indicators with saved settings, 16 drawing tools saved on the server, your trades and orders on the chart, **2,000 candles in every timeframe**; options for everyone, leverage up to 10x (Pro), trading bots and backtests (Expert) with a guide | TA-B5, TA-B7, TA-B8, TA-B10, TA-B11, TA-B12 |
| The Daily Chart | A numbered mystery chart a day, the same for everyone; two minutes, one go; streaks, stats, a result grid, sharing as text and as a story picture | TA-D5 to TA-D9 |
| Learning | A 96-lesson course in 17 tracks, eleven kinds of chart test on real charts, a glossary; challenges switched off; the quest ladder | TA-C5, TA-C7, L8, L11 |
| Community | 32 house bots that trade and play the Daily Chart like people (2026-10-27); four leaderboards (today or all time, by return or by profit), chat with moderation, follows, public profiles, a daily paper-money contest | S1-S4, TA-D2, TA-D3 |
| Money | 1,000 MB start, MB by source, five packages, the New Launch Deal (first 7 days: a big MB pack once, the first month of Pro or Expert at half price), Pro and Expert monthly (renewing) or yearly, refunds, spending limits, the free restart, tracking links, invite links per account | M4, M8, M9, B4, B5 |
| Rules | Terms and privacy (version of 24 October 2026), a date of birth at sign-up (13 or older), the right-to-cancel waiver at checkout | R4, R5, R7-R9 |
| Running it | Staging copy, rollback, backups off the server, uptime check, CI with lint and types, an error tracker, capacity measured (about 1,000 players at once is comfortable) | O1 email, O4 Cloudflare, O8, O11, E2, E5, E6, E14 |

---

## 3. Launching on Instagram

Done for the launch (2026-10-24): tracking links for every ad (B4), the Daily Chart relaunched with streaks and
sharing (TA-D4), purchases credited at once (O7), a date of birth at sign-up, the bot guide, 2,000-candle charts.

| # | Before or while advertising | Who | Size |
|---|---|---|---|
| G1 | **Real email** (O1): without it nobody can reset a forgotten password and no receipts go out. A Resend account and its DNS records, then `deploy\set_mail.ps1`. | you, then me | S |
| G2 | **Test inside Instagram's own browser** on a phone (ad clicks open there): sign-up, the date-of-birth box, a package, a **monthly** pass and Cancel, the Daily Chart and its Share and Story picture. Refund the test purchases in Stripe. | you | S |
| G3 | **The old accounts** (O11): reset everyone to 1,000 MB before new players arrive, or keep them. | your decision | S |
| G4 | **Who runs the site** (R9) and **a lawyer's read** (R4): UK and EU consumer law usually wants a business name and an address; the terms name neither. | you | S |
| G5 | **Ad wording**: Meta reviews anything that looks financial. No "make money", "get rich" or real-looking returns; say "practice money, no cash value". A tracking link per ad (`memestreet.net/?ref=ig_story1`), read on the admin page. | you | S |
| G6 | **Alerts on your phone** if the site goes down: UptimeRobot on `https://memestreet.net/api/health` (the GitHub check emails, more slowly). | you | S |
| G7 | **Moderators** for chat once there are regulars (the moderation tools exist). | you | S |
| G8 | **Watch disputes**: under-18s can buy since 2026-10-24, and Managed Payments needs a low dispute rate to stay on; consider a lower spending limit than US$500 a month (R5). | you | S |

---

## 4. Suggested order

| Phase | Focus | Items | Done when |
|---|---|---|---|
| 1 (now) | **The launch** | G1-G8 | Players arrive from ads, can recover their accounts, and every purchase is credited |
| 2 | **The Daily Chart as the hook** | TA-D5 play without an account, TA-D6 past charts, TA-D7 friends and groups, TA-D8 streak badges, TA-D9 reminders | A shared result turns into a played game and a sign-up |
| 3 | **Trading on the chart** | TA-B5 trade from the chart, TA-B7 alerts, TA-B12 the trading screen, TA-E4 why it moved | From spotting a setup to a sized, bracketed order without leaving the chart |
| 4 | **Learning around the chart** | TA-C5, TA-C7, L8, L11 | The course and chart tests are built (2026-10-27); next the coach comments on trades, tooltips, onboarding and more tests |
| 5 | **Depth and groups** | TA-B8 screener, TA-B10 layouts, TA-B11 replay, TA-D2, TA-D3, S1 classrooms | Players find, rehearse and compete on setups |
| Alongside | **Running it** | O4, O8, E2, E5, E6, E9-E11, E14, M8, M9, R5, R7, R8, X2, X7 | |

---

## 5. Tracks: what is open

### TA-D. Playing for fun, and the Daily Chart

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-D2 | Weekly competitions and leagues | Light, social goals keep people coming back. | Weekly events ranked on return on money put in and risk-adjusted return, leagues by level, small capped MB prizes. | M |
| TA-D3 | Share a chart | Explaining a trade idea is fun and teaches. | Share a chart with drawings in chat or by link. | M |
| TA-D5 | Play the Daily Chart without an account | Someone who taps a shared result should be playing in one tap; asking for an account first loses most of them. | A visitor plays today's chart in the browser; at the end, "Create an account to keep your result and start a streak" saves it to the new account. One go a day per browser, and only accounts count on the board. | M |
| TA-D6 | Past charts | Wordle's archive keeps people playing between days. | Play any earlier Daily Chart for practice (not on the board), with its result and the day's winner. | S |
| TA-D7 | Friends and groups | Beating friends is the strongest daily pull. | Today's results of the people you follow next to yours; a group code (a class, a group chat) with its own daily and weekly board. | M |
| TA-D8 | Streak and result badges | Small rewards for coming back. | Badges for 7, 30 and 100-day streaks, a first place, beating the stock five days running; on the profile. | S |
| TA-D9 | A reminder | "The new chart is out" brings people back. | An optional email (needs O1) or browser notification when the new chart starts, never more than once a day. | S |

Done: **TA-D1** no homework (nothing locked behind lessons, the onboarding strip one click to hide). **TA-D4** the Daily
Chart (2026-10-23; relaunched 2026-10-24 with day numbers, streaks, stats, a result grid, Share and a story picture;
2026-10-26 more technical: visible support, resistance and fair value gaps, EMA and VWAP overlays, and an after-game
breakdown of the levels the chart tested; HOW_IT_WORKS §10.13).

### TA-B. Charts and trading tools

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-B5 | Trade from the chart | Entry, stop and target belong on the chart. | Drag lines for entry, stop and target; the risk-reward ratio and the size for the chosen risk update as you drag; one click places the order and its bracket. | M |
| TA-B7 | Alerts | Waiting for a setup should not mean staring. | When the price crosses a drawn line or an indicator condition is met; in the page, and by email once O1 is on. | M |
| TA-B8 | A setup screener | Finding setups is a skill to practise. | Stocks near strong levels, breakouts on volume, squeezes, RSI extremes and divergences, gaps, new highs and lows, named patterns. | M |
| TA-B10 | Multi-chart layouts | Setups are read across timeframes and against the index. | Two or four charts, linked timeframes, an index or sector overlay, relative strength. | M |
| TA-B11 | Replay mode | Practising on the past, bar by bar, is the best teacher. | Pick a stock and a past period, step through it and trade it in a practice account (needs E5). | L |
| TA-B12 | The chart as the home screen | Most players should land on a chart, not a table. | The chart in the middle, a watchlist, the order ticket and positions; the market table stays as "all stocks". | M |

Done: **TA-B1** crosshair, **TA-B2** chart types and log scale, **TA-B3** 49 indicators with settings, **TA-B4**
drawing tools saved on the server, **TA-B6** trades on the chart, **TA-B9** what Pro includes (decided), **TA-A10**
longer history and **2,000 candles a chart** (2026-10-24). **T10** options for everyone, **T11** leverage (Pro),
**T12** trading bots (Expert) and their guide at `/bots/guide` (2026-10-24), **T13** backtests (2,000 candles of each
size). T1-T9 were done or moved into the TA-B items. Next for options, if wanted: writing them with margin, spreads as
one order. Next for bots: alerts from a rule, sharing bots, walk-forward backtests.

### TA-C and L. Learning

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-C5 | A coach that reads the chart | Feedback turns mistakes into lessons. | Rule-based remarks: "you bought into resistance", "your stop was inside normal noise". | M |
| TA-C7 | Tooltips | "R", "VWAP" and "divergence" stop beginners. | Tooltips on every indicator and tool, linking to its lesson (the glossary lesson exists). | S |
| L8 | Onboarding | New players need a first good trade, with a stop. | A guided first run on the stock page itself (the *Start here* lessons cover it in words). | S |
| L11 | More chart tests | Tests are the stickiest part of the course. | Volume reading, gaps and fair value gaps, divergences, multi-timeframe agreement; a daily set of five with a streak. | M |

Done: **the course rebuilt** (2026-10-27): 17 tracks and 96 lessons from market basics to derivatives, macro, testing and real
life (no MB; their quizzes were taken out the same day, on request), **TA-C1** curriculum, **TA-C2** example charts from the game's own
history, **TA-C3** and **TA-C4** eleven kinds of chart test on real charts (bounce or break, breakouts, patterns, candles,
RSI, crosses, Fibonacci, reward to risk, stops, trends, up or down), a glossary, and **L10** the lesson files checked by
a test (HOW_IT_WORKS §10.10). Dropped or earlier: the twelve old lessons; **L3** challenges (built, switched off 2026-10-23); the quest ladder; **L4** journal and
**TA-C6** removed 2026-10-20; **L5** skill profile dropped with it.

### P and TA-A. The market

| # | Change | Why | How | Size |
|---|---|---|---|---|
| P8 | Market psychology | Real markets overreact, panic and chase. | Overreactions that partly retrace, "buy the rumour, sell the news", short squeezes when short interest is high, stop runs past obvious levels; each at a measured rate, checked for free money. | L |
| P9 | Factors and correlations | One market factor plus sectors is too simple for macro to matter. | Factors for rates, oil, the dollar and risk-on/off, an exposure per listing, correlations that rise in sell-offs. | L |
| P10 | Asset classes that behave like themselves | Bonds, gold, oil and defensives teach different lessons. | Bonds fall when rates rise, gold reacts to real rates and fear, defensives hold up in bear phases. | M |
| P12 | Retire what conflicts | Leftovers of the old zero-drift market. | The hidden mood, two-outcome catalysts and distress bets, kept only where they fit; each change checked by `realism.py`. | M |
| P13 | A gentler market for beginners | Beginners may want calmer conditions. | A second, calmer market for the first lessons, or a difficulty setting. Later. | M |

Done: **P1-P7** (drift, regimes, ranges, support and resistance, trends in legs, volatility structure, volume),
**P11** the realism and no-free-money suite, and **P14 IPOs and takeovers** (2026-10-24: about 15 new companies a game
year from any industry and size, announced a game day ahead, listed with no pop; past 200 companies each is matched by
a takeover of the smallest outside the MSI 50 at the market price; HOW_IT_WORKS §6.10A); **TA-A1 to TA-A9** (levels calibrated, more kinds of level, named
patterns, volume, candles, timeframes that agree, gaps, momentum structure, the pattern suite); **TA-A11** game-time
candles (built, then taken out on request). Volatility checked 2026-10-24: game-day moves match the stated volatility
(median about 43% a year; Novaxis 49%), so nothing was changed.

### TA-E and N. News and the economy

| # | Change | Why | How | Size |
|---|---|---|---|---|
| TA-E4 | "Why it moved", technical first | Players should learn to explain moves from the chart. | Each stock page says what happened in chart terms ("broke resistance at 145 on twice the usual volume"), with a headline only when there was one (was N7). | M |
| N8-N10 | Parked | They add news, not chart skill. | Better company stories, a daily wrap written around the chart, LLM headlines. | M |

Done: **TA-E1 to TA-E3** (smaller macro reactions, fewer headlines, the wire folded; its stock names link to their
pages since 2026-10-24); **N1-N6** (fewer headlines, a central bank, data releases, a hidden economy, earnings with
forecasts, the calendar).

### M and B. Money and growth

| # | Change | Why | How | Size |
|---|---|---|---|---|
| M4 | When an account runs out | The moment a player busts teaches the most and is the least fair time to sell. | A page that shows what happened (the biggest losses, the risk taken, the risk lessons) with the options; today a red banner offers the free restart, the shop and the lessons. | S |
| M8 | Trading costs that teach | Costs decide whether a pattern pays. | Keep 0.1% a side, or a commission and a spread that widens in thin and fast markets; checked with the realism suite. | M |
| M9 | Simplify the house | Nobody is paid out, so the house carries no risk. | Retire the capital rule, reserve floors, top-ups and alarms; the house-risk panel becomes "where players are positioned". | S |
| B4 | The funnel with purchases | Know what the ads bring. | **Tracking links done (2026-10-24): sign-ups, buyers and revenue per `?ref=` link on the admin page.** Still to do: buyers per 1,000 sign-ups, spend per buyer, out-of-money to purchase, cohorts by week. | S |
| B5 | Referral rewards | Word of mouth. | Every account has an invite link and the admin page counts who invited whom (2026-10-27); next, a capped MB reward for both once the friend verifies and plays. | S |
| B6 | Email that brings people back | Value, not spam. | Welcome, a weekly review, the Daily Chart reminder (TA-D9), receipts, an unsubscribe link (needs O1). | M |
| B7 | Community | Somewhere to talk and announce. | A Discord or Instagram broadcast channel with the daily winners. | S |
| B8 | Teachers and creators | Each brings a group. | Classrooms (S1) with a free trial, a creator programme. | M |
| B9 | Name and brand | "Meme Street" was chosen for a meme-stock game. | Keep it or rename for a teaching audience; check trademarks and domains. Your decision. | S |
| B10 | Pages people can find | A teaching site grows through search and shared lessons. | Public lesson pages, the about page with a real screenshot, share cards for stocks and results. | M |

Done: **M1** 1,000 MB start, **M2** MB by source, **M3** the shop (Stripe Managed Payments, live 2026-10-24), **M5**
challenge rewards (off with the challenges), **M6** spending limits, **M7** the pricing model (`tools/pricing_model.py`;
fill it with real numbers now), **B1** package prices (US$1.99 to US$99.99), **B2/B3** Pro US$9.99 and Expert US$29.99 a
month renewing, or US$99.99 and US$299.99 a year.

### S and U. Community and interface

| # | Change | Why | How | Size |
|---|---|---|---|---|
| S1 | Classrooms | Teachers and clubs are natural buyers, and an income that does not depend on losses. | A teacher account, a class with a join code, assigned lessons, a class board and progress. | L |
| S2 | Boards that reward skill | Raw returns reward luck and leverage. | A risk-adjusted or consistency board, leagues by level, leverage counted or capped (risk 4). Four boards exist (today or all time, by return or profit). | S |
| S3 | Challenge weeks | Replaces the daily paper-money contest. | Weekly themed events with the same starting balance and a skill objective. | M |
| S4 | Sharing ideas | Explaining a trade is learning. | A trade idea (a chart with levels and a plan) shared with followers, delayed; a room per stock. | M |
| U1 | Phone, second step | Ad traffic is almost all phones. | A pull-up trade ticket, an installable web app, a check on real phones. | M |
| U2 | Notifications | Messages vanish after a few seconds. | A list, sounds, browser notifications for fills, alerts and the Daily Chart. | S |
| U3 | "While you were away" | Coming back should show what happened. | Equity change, fills, news on holdings. | S |
| U5 | Accessibility and a light theme | Wider reach. | Arrows beside colours, keyboard shortcuts, a light theme, translations. | M |
| U6 | Market overview | Seeing the whole market is a skill. | A heatmap; the MSI 50 page with its holdings exists. | M |
| U7 | Low-data mode | A stock page used to cost about 18 MB an hour. | Pause when hidden, send only what is visible (charts already refresh with their newest candles only). | S |

Done: **S5** streaks (the Daily Chart's), **U8** a consistent look, **U9** the trading-terminal look, visual passes over
every page (2026-10-23).

### E and O. Engineering and running the site

| # | Change | Why | How | Size |
|---|---|---|---|---|
| E2 | Split `engine.py` | It is hard to change safely. | Modules for prices, news, orders, accounts, indices (the chart, bots, options, the Daily Chart and the history are already their own files). | L |
| E5 | Determinism and replay | Calibration, replay (TA-B11) and bug reports need repeatable markets. | A seeded random stream per market and a tool that replays any period. | M |
| E6 | Observability | Problems are seen only on the dashboard. | Structured logs, metrics, alerts for late ticks and errors. | M |
| E7 | Content tooling | Packs are edited by hand. | A validator and a preview for content packs. | S |
| E9 | Rough edges | Small things add up. | Sparklines reset on restart, the news wire is not saved, content files are checked every tick. | S |
| E10 | Scale the game server | Gateways carry connections; the market is one process. | Only when needed (thousands of players at once). | L |
| E11 | Ledger housekeeping and a restore drill | The ledger only grows; a backup is only good if it restores. | Rotation, a restore drill from the PC copy, a snapshot-versus-ledger check. | S |
| E14 | A fast local test run | The whole suite takes about 40 minutes in one process. | Run the modules in parallel across the cores (about 10 minutes); day to day, run only the tests relevant to a change. | S |
| O1 | Real email | Password recovery, receipts, reminders. | A Resend account, its DNS records, `deploy\set_mail.ps1` (ready). | S |
| O4 | Cloudflare in front | Shield and caching. | The server is ready; the account and the name servers are yours. | S |
| O8 | Status and capacity | Know the limits; tell players about outages. | Capacity is measured (about 1,000 players at once is comfortable on this server); a status page. | S |
| O11 | Reset the old accounts | Some accounts still have the old 10,000-MB start. | Announce, back up, reset to 1,000 MB (the admin reset exists), or decide to keep them (G3). | S |

Done: **TA-F1** the admin's total MB, **TA-F2** the chart's code in `web/chart.js`, **TA-F3** browser tests for the chart tools; **E1** the price model in its own module, **E8** admin credit, refund and corrections, **E12** CI in parallel
parts, **E13** lint, types and an error tracker; **O2** backups off the server (daily to this computer), **O3** uptime
check, **O5** staging and rollback, **O6** a hardened server, **O7** payment webhooks that never lose a purchase
(signed, idempotent, checked four times a day; the gateway passes Stripe's signature on since 2026-10-24),
`deploy\set_stripe.ps1` for the keys.

### R and X. Rules, and what is left of the old plan

| # | Change | Why | How | Size |
|---|---|---|---|---|
| R4 | A lawyer's read | Selling a game currency to the public. | The terms and privacy pages; what the ads may say; that a currency that can never be cashed out is not gambling where you sell. | S |
| R5 | Responsible spending | People who lose may chase losses; under-18s can buy. | Spending limits exist (US$500 in 30 days, 3 purchases a day, a lower limit by request); consider a lower default, a cool-off, a clear note that buying MB does not make anyone a better trader. | S |
| R7 | Data rights | Players should be able to leave. | **The admin can delete an account (2026-10-25).** Still to do: a player downloads their data and deletes their own account. | M |
| R8 | "How this market works" | Transparency builds trust and teaches. | What drives prices, what is random, that player trades never move prices. | S |
| R9 | Who runs the site | Consumer law usually requires the seller's name and address. | A business name and a contact address in the terms (Stripe is the merchant of record for the sale itself). Your decision. | S |
| X2 | Moonshots and two-outcome catalysts | Lottery tickets do not teach trading. | Remove from the default market or move to an opt-in section. Your decision. | M |
| X7 | 3x products and very risky instruments | For advanced players only? | Keep with warnings, unlock by level, or remove. Your decision. | S |
| X9 | Admin "withdraw" | Nothing is cashed out. | Keep only as an admin correction, renamed. | S |

Done or decided: **R1** terms and privacy (version of 24 October 2026), **R2** the age policy (13 or older with a date of
birth at sign-up; no age rule for buying since 2026-10-24, on request), **R3** consumer rules (the right-to-cancel
waiver at checkout; tax handled by Stripe as merchant of record), **R6** a sign-up bot trap; **X1** the real-money plan
dropped, **X3/X4** the old edge and fee tools removed, **X5** the daily contest stays for now, **X6** 1,000 MB start
(old accounts: O11), **X8** with M9.

---

## 6. Risks

| # | Risk | Why it matters | Where |
|---|---|---|---|
| 1 | **The market must be realistic without free money.** | It is the product: too random teaches nothing, too regular is exploited in a day. | P8-P13, `realism.py` |
| 2 | **Revenue from losses.** MB packages sell best when people lose. | It works against teaching and draws scrutiny with young users; the passes help. | M4, R5 |
| 3 | **Minors buying** (no age rule since 2026-10-24). | Parents' disputes and refunds; Managed Payments needs a low dispute rate to stay on. | G8, R5 |
| 4 | **Leverage and the boards.** A 10x player tops a day's board, or loses everything, by luck. | The boards promise that skill wins. | S2, T11 |
| 5 | **No email yet.** | A player who forgets a password needs you to give a temporary one. | O1 |
| 6 | **One server.** | Backups are daily on this computer, but a restore has never been rehearsed. | E11, O8 |
| 7 | **The name.** "Meme Street" suits a meme-stock game more than a place to learn. | Cheap to change now, expensive later. | B9 |

---

## 7. Decisions

**Decided:** the payment provider (Stripe, through Managed Payments, 2026-10-24); package prices; Pro and Expert, monthly
or yearly; what Pro includes (32 of 49 indicators and leverage; Expert adds bots and backtests; options for everyone);
real-time chart timeframes only; 13 or older to sign up, no age rule to buy; challenges off; four leaderboards; a free
restart when nearly out (below 50 MB, once a week); the Daily Chart back and on the site.

**Open (yours):**

| Question | Options |
|---|---|
| The old accounts (G3, O11) | Reset to 1,000 MB before the ads; keep them. |
| The default spending limit (R5) | Keep US$500 in 30 days; lower it for everyone. |
| Who the site names as its operator (R9) | A business name and an address; a registered agent. |
| The name (B9) | Keep "Meme Street"; rename for a teaching audience. |
| Moonshots and 3x products (X2, X7) | Keep with warnings; unlock by level; remove. |
| Costs (M8) | 0.1% a side; a commission and a spread. |
| The boards and leverage (S2) | Count leverage as it is; cap it on the boards; a separate board. |
| Daily Chart prizes (TA-D8) | Badges only; a small MB prize for the day's top three (watching for extra accounts). |
| An AI coach (TA-C5) | Rule-based only; an LLM coach (an API cost per player). |

---

## 8. Checking a market change

1. The tests relevant to the change (`python -m unittest test_<module>` in `tests/`); the whole suite
   (`python -m unittest discover tests`, about 40 minutes) only for sweeping changes. They guard money conservation,
   the ledger and the rule that player trades never move prices.
2. `python tools/chart_check.py 12 <seed>` on two or three seeds: the charts against the facts of real prices
   (MARKET_REALISM.md has the targets and the last results).
3. `python tools/realism.py`: stylised facts, pattern rates within their target bands, and the no-free-money strategy
   comparison against holding the index, costs included, on markets never used for tuning; `tools/option_check.py`
   for options.
4. A look at the charts by a person: does it look like a market a trader would recognise?
5. Update `HOW_IT_WORKS.md` and this file.
