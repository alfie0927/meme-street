# Orders and trade management {orders}
Order types, brackets, trailing stops, scaling in and out, and the costs that eat into every trade: slippage, gaps and fees.

## Market, limit, stop and stop-limit orders {order-types} [7]
SUMMARY: The four basic order types: what each guarantees, and what it does not.
### Market order
"Buy (or sell) now, at whatever the price is." It is guaranteed to fill, but not at a guaranteed price: in a fast or thin market you can get a worse price than the one you saw.

### Limit order
"Buy at this price **or lower**" (or sell at this price or higher). You control the price, but it may never fill if the market does not come to you. Limit orders are how you avoid paying the spread, and how you buy a pullback without watching the screen.

### Stop order
"When the price reaches this level, send a market order." A **stop-loss** below your long position sells if the price falls there. A stop can also be used to **enter**: a buy stop above resistance buys the breakout. Once triggered it is a market order, so it fills at the next available price, which can be far from the stop in a gap.

### Stop-limit order
"When the price reaches the stop, place a limit order." It protects you from a terrible fill, but if the price gaps past your limit, nothing fills at all and you are still in the falling position. Most traders protect positions with plain stops for that reason.

| Order | Guarantees a fill? | Guarantees the price? |
| Market | yes | no |
| Limit | no | yes (or better) |
| Stop | yes, once triggered | no |
| Stop-limit | no | yes, if it fills |

HERE: You can place **limit buys** (the price falls to your trigger), **limit sells** (it rises to your trigger; with no shares, this opens a short), **stop-losses** and **take-profits** (they only close a position, never open or flip one) and **brackets**. Every order is a market trade that happens later: it fills at the market price of the moment it triggers, which in a jump can be past your trigger. There are no stop-limit or stop-entry orders. Up to 20 open orders (6 in one stock), each for up to 7 days. Orders show on the chart as lines with tags.

[try /stock/NVXA] Open the order panel under Novaxis's chart and look at each kind of order (you do not have to place one).

## Brackets: a stop-loss and a take-profit together {brackets} [5]
SUMMARY: Setting both exits at once, one-cancels-other, and why every trade should have both.
A **bracket** is two exit orders around a position: a **stop-loss** below (for a long) and a **take-profit** above. When one fills, the other is cancelled automatically (**one-cancels-other**, OCO).

### Why it helps
- The trade is planned in full before it starts: entry, the price where you are wrong, the price where you take the profit.
- You do not have to watch the screen.
- It stops the two classic mistakes: letting a loser run because "it will come back", and grabbing a small profit too early out of fear.

### Choosing the two prices
- The **stop** goes where the trade idea is proved wrong: beyond the level or pattern that made you take it, outside normal noise.
- The **target** goes where the price can realistically reach: the next resistance, a measured move, a Fibonacci extension.
- Then check the ratio: the target should be further than the stop. The *Risk* track shows why.

HERE: The order panel has a one-click **bracket**. On the Holdings page, every position has *Take profit* and *Stop-loss* columns you can click to set or move them; when both are set they are paired as a bracket. The **Position size and risk** tool works out the size from the stop and fills in the trade and the bracket for you.

[test rr]

## Trailing stops, partial exits and scaling {trailing-scaling} [6]
SUMMARY: Letting winners run, taking some profit, and building or reducing a position in steps.
### Trailing stops
A **trailing stop** follows the price: in a long trade it moves up as the price rises, staying a set distance (a percentage, a few ATRs) below the high, and never moves down. It locks in profit while leaving the trade room to run. The trade-off: too tight and an ordinary pullback stops you out of a good trend; too loose and you give back a lot before it triggers.

Ways to trail a stop:
- Below each new **higher low** in an uptrend.
- A few **ATR** below the highest close.
- Under a **moving average** or the SuperTrend line.

### Moving to break-even
Once a trade is well in profit (say, by one times the risk), many traders move the stop to the entry price. The trade can no longer lose (apart from a gap), at the cost of being stopped out by a normal pullback more often.

### Partial exits
Sell part of the position at a first target (often a third or a half) and let the rest run with a trailing stop. You bank something, and keep a chance of the big move.

### Scaling in
Building a position in steps: half at the first signal, the rest when the trade proves itself (a breakout holds its retest). Adding to **winners** is a plan; adding to **losers** to lower your average price ("averaging down") is how small losses become account-ending ones.

HERE: There is no automatic trailing stop: you trail by hand, moving the stop-loss up on the Holdings page or by dragging your plan along. Sell part of a position with the size chips (25%, 50%...) or by typing an amount in MB. Adding to a position averages your entry price, shown as the amber dotted line on the chart.

## Slippage, gaps through stops, and fees {costs} [5]
SUMMARY: The costs that do not show on the chart, and how they add up.
### Slippage
The difference between the price you expected and the price you got. It comes from the market moving while your order travels, from thin order books (your order eats through several price levels), and from fast markets. Slippage is worst on market and stop orders in small stocks and around news.

### Gaps through stops
A stop is a promise to **try** to get out at your price. If a stock closes at 50 and opens at 40 after bad news, a stop at 48 fills around 40. Every stop can gap; that is why position size must allow for losses bigger than the stop distance in the worst cases, and why holding big positions through earnings is a gamble.

### Fees and spreads
- **Commission**: a fee per trade or per share.
- **The spread**: you buy at the ask and sell at the bid.
- **Financing**: interest on borrowed money, borrow fees on shorts.
A strategy that makes 0.1% a trade before costs and pays 0.2% in costs loses money. The more often you trade, the more costs matter: they are the one part of the result that is certain.

### Adding it up
A trader making 500 round trips a year at 0.2% each pays 100% of the money traded in costs over the year (on a fully invested account). Fewer, better trades usually beat many mediocre ones.

HERE: Every trade costs **0.1%** each way; shares have no spread and no slippage (you get the price on the screen), but orders fill at the market price when they trigger, so a jump at the open or on earnings can carry the price past your stop. Shorts pay a borrow fee and leveraged positions pay interest. The Portfolio page shows the fees you have paid.

[try /portfolio] Open your portfolio and find how much you have paid in fees so far.
