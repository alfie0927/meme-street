# Ballast: the cTrader Store listing

Everything the Store's "Publish a product" form asks for, ready to paste. The rules it was written to (checked
18 November 2026, help.ctrader.com/ctrader-store/how-tos/publish-a-product): name 6 to 40 characters, short
description up to 120, full description at least 300, at least three screenshots at least 800 px wide, a 300 x 300
image, no links to other stores or social media, no profit claims.

## Two products

| | Ballast (the paid plugin) | Ballast Free (the trial, attached to the paid one) |
|---|---|---|
| Plugin URL | `https://<your Pages address>/index.html` | `https://<your Pages address>/trial/` |
| What it does | Everything | Ticket sizing (with costs and ATR), Exposure and Sessions; no Place button, no Limits, no Journal |
| Price | Subscription: **US$9.99 a month** or **US$79 a year** (proposal; your call) | Free |

Why these prices: the visible sellers of risk tools on the Store charge one-off $19 to $45, and a $45 one sold 58 in
under a year. Ballast bundles five tools, so a small subscription is fair, and the yearly price (about 6.6 months)
rewards staying. If subscriptions sell badly after 90 days, add a one-off price beside them (the Store allows both).

## Name (6 to 40)

```
Ballast Risk Toolkit
```

## Short description (up to 120)

```
Size every trade from your risk and stop, guard prop-firm loss limits, see open risk, and journal in R. No signals.
```
(114 characters)

## Full description

```
Ballast is a risk toolkit that sits inside cTrader, on Web, desktop and the phone apps. It works out the position size for the risk you choose, places the trade with its stop attached, sizes new trades to fit the loss limits you enter, and records your results in R.

TICKET: the size for your risk
- Set your risk as a percent of your balance or an amount of money, and your stop in pips, as a price, or as a multiple of the market's volatility (ATR).
- Ballast works out the largest size whose loss at the stop is no more than your risk, commission included (per lot, per million or a percent of value), for forex, crosses, gold, indices and crypto, in your account's currency. Currency conversions are valued at the stop as well as now, and the worse rate is used.
- It always rounds down. If even the smallest allowed size would lose more than you chose, it tells you and places nothing.
- Review the order, then place it with its stop and target attached. Nothing is sent until you press Place, and a double tap sends one order.

LIMITS: built for funded accounts
- Enter your daily and total loss limits the way your firm counts them: from the day's opening balance or the higher of balance and equity, static or trailing, with the day starting at your firm's reset time (Prague, broker server time, New York, or your own). Where your firm's dashboard shows an exact figure, such as today's lowest allowed equity, type it in and Ballast uses it.
- Open positions and pending orders are counted as if their stops were hit, and each new trade is cut to the room that leaves.
- When a limit is reached, or the figures cannot be read, Ballast places no orders until it can check them again.

EXPOSURE: what is at risk now
- Every open position and pending order, its loss at the stop in your money and as a share of your balance, and the total. Positions without a stop are flagged.

JOURNAL: your trades in R
- Every trade placed from Ballast is recorded in R (its result divided by what it risked): win rate, average R, profit factor, longest losing run, results by symbol, and a CSV download. A position closed in parts counts as one trade.

SESSIONS: the market's clock
- Sydney, Tokyo, London and New York, open or closed and for how long, with daylight saving handled for each city.

WHAT IT DOES NOT DO
- No buy or sell signals and no advice: you choose every trade.
- It cannot block orders placed elsewhere in cTrader, though it counts them.
- A stop is not a guaranteed price: in a fast market or over a gap the loss can be larger than planned, and a limit can still be passed.
- Your firm's rules are yours to enter correctly; Ballast follows what you set.
- It sends no data anywhere. Your settings stay on your device.

Ballast Free sizes trades (with commission and ATR stops) and shows your exposure and the sessions. The full version adds placing orders from the review, the loss limits and the journal. Try it on a demo account first. Trading involves risk; this tool does not make trading profitable.
```

## Images

| What | File |
|---|---|
| 300 x 300 image | `listing/store-image-300.png` |
| Screenshots (840 px wide, made against the stand-in account; replace with ones from your demo account if you prefer) | `listing/screenshot-1-ticket.png`, `screenshot-2-limits.png`, `screenshot-3-journal.png`, `screenshot-4-exposure.png` |

## Placements to tick when building the plugin

- Desktop and Web: "Block in Active Symbol Panel" (size L), "Tab in Trade Watch", "Separate window".
- Mobile: "Bottom sheet from the symbol Overview tab" (80%) and "Bottom sheet from the Trade app tabs" (80%).

## Answers to likely buyer questions (for the comments)

| Question | Answer |
|---|---|
| Does it work with my broker? | It works on any cTrader account. Sizes use your broker's own lot sizes and steps, read from cTrader. |
| Does it include commission? | Yes: enter your commission once under Costs (per lot, per million USD, or a percent of value) and every size includes it, both sides. Until you set it, the ticket reminds you. |
| Will it stop me breaching my prop firm's limits? | It cuts every trade placed from Ballast to the room your limits leave, counting open trades and pending orders at their stops, and stops placing orders at the limit. It cannot stop orders placed elsewhere in cTrader, it follows the rules you enter, and a gap past a stop can cost more than planned. |
| Does it send my data anywhere? | No. It cannot: its security policy blocks every network connection. Settings are stored on your device. |
| Signals? | None, ever. It sizes, checks and records the trades you choose. |
