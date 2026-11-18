# Ballast: the cTrader Store listing

Everything the Store's "Publish a product" form asks for, ready to paste. The rules it was written to (checked
18 November 2026, help.ctrader.com/ctrader-store/how-tos/publish-a-product): name 6 to 40 characters, short
description up to 120, full description at least 300, at least three screenshots at least 800 px wide, a 300 x 300
image, no links to other stores or social media, no profit claims.

## Two products

| | Ballast (the paid plugin) | Ballast Free (the trial, attached to the paid one) |
|---|---|---|
| Plugin URL | `https://<your Pages address>/index.html` | `https://<your Pages address>/trial/` |
| What it does | Everything | Sizes trades, shows the limits, exposure, journal and sessions; does not place orders |
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
Ballast is a risk toolkit that sits inside cTrader, on Web, desktop and the phone apps. It does the sums every trader should do before a trade, and keeps you inside the loss limits you set.

TICKET: the right size, every time
- Set your risk as a percent of your balance or an amount of money, and your stop in pips, as a price, or as a multiple of the market's volatility (ATR).
- Ballast works out the largest size whose loss at the stop is no more than your risk, commission included, for forex, crosses, gold, indices and crypto, in your account's currency.
- It always rounds down, never up. If even the smallest allowed size would lose more than you chose, it tells you and places nothing.
- Review the order, then place it with its stop and target attached. Nothing is sent until you press Place.

LIMITS: built for funded accounts
- Enter your daily and total loss limits the way your firm counts them: from the day's opening balance or the higher of balance and equity, static or trailing, with the day starting at your firm's reset time (Prague, broker server time, New York, or your own).
- Open trades are counted at their stops, so a new trade is cut to the room you have left and can never add up to a breach.
- When a limit is reached, Ballast stops placing orders until it resets.

EXPOSURE: see what is really at risk
- Every open position's loss at its stop, in your money and as a share of your balance, and the total. Positions without a stop are flagged.

JOURNAL: know if your trading works
- Every trade placed from Ballast is recorded in R (its result divided by what it risked): win rate, average R, profit factor, longest losing run, results by symbol, and a CSV download. A position closed in parts counts as one trade.

SESSIONS: the market's clock
- Sydney, Tokyo, London and New York, open or closed and for how long, with daylight saving right in every country.

WHAT IT DOES NOT DO
- No buy or sell signals and no advice: you choose every trade.
- It cannot block orders placed elsewhere in cTrader, though it counts them.
- A stop is not a guaranteed price: in a fast market or over a gap the loss can be larger than planned.
- It sends no data anywhere. Your settings stay on your device.

Ballast Free (the trial) sizes trades and shows your limits, exposure, journal and sessions; the full version also places orders from the review and enforces your limits on them. Try it on a demo account first. Trading involves risk; this tool does not make trading profitable.
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
| Does it include commission? | Yes: enter your commission once under Costs (per lot or per million) and every size includes it, both sides. |
| Will it stop me breaching my prop firm's limits? | It cuts every trade placed from Ballast to the room your limits leave, counting open trades at their stops, and stops placing orders at the limit. It cannot stop orders placed elsewhere in cTrader, and a gap past a stop can cost more than planned. |
| Does it send my data anywhere? | No. It cannot: its security policy blocks every network connection. Settings are stored on your device. |
| Signals? | None, ever. It sizes, checks and records the trades you choose. |
