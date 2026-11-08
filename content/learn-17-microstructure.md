# Market microstructure {microstructure}
How prices are actually made: the order book, who is pressing, what a big order costs, how the open and close are set, and how professionals feed an order into the market. Expert.
TIER: expert

## The order book {order-book} [5]
SUMMARY: Read bids, asks, depth and queue position, and price a spread in basis points.

### Two sides of a price
A price is two numbers. The **bid** is the most anyone will pay right now; the **ask** is the least anyone will sell for. The gap is the **spread**. A market order crosses it: you buy at the ask and sell at the bid, so every round trip costs one spread before the price has moved at all.

Q: You buy at the ask and sell a second later at the bid. What did the round trip cost, before fees?
+ One spread
- Nothing, because the price did not move in between
- Half a spread, because each side pays half of it
WHY: Buying at the ask and selling at the bid pays the whole gap. The spread is the first cost of every trade.

### Depth and the queue
Behind the best bid and ask sit more orders at worse prices: the **depth**. At each price the orders wait in a queue, first come first served. A limit order joins the back of its queue and fills only when everything ahead of it has traded or been cancelled.

Q: You place a limit buy at the best bid, where 5,000 shares already wait. A seller sells 2,000 shares at that price. What happened to your order?
+ Nothing yet: 3,000 shares are still ahead of it
- It filled first, because it was the newest order at that price
- It filled in part, in proportion to its share of the queue
WHY: Queues fill from the front. Your order waits until the 5,000 ahead of it are gone.

[chart level]

### The spread in basis points
Spreads are compared in **basis points**: the spread divided by the mid price, times 10,000. A 0.05 spread on a 50.00 stock is 10 bps. The same 0.05 on a 5.00 stock is 100 bps: ten times costlier to trade in and out of.

Q: A stock is bid 24.98 and asked 25.02. What is the spread in basis points?
= 16 ±1
WHY: 0.04 divided by the 25.00 mid, times 10,000, is 16 bps.

Compare two stocks by their spreads in basis points, never in cents: a cent means little on an expensive stock and a lot on a cheap one.

Q: Which is cheaper to trade in and out of?
+ A 200.00 stock with a 0.04 spread
- A 10.00 stock with a 0.03 spread, the tighter one in cents
- They cost the same, because both spreads are under five cents
WHY: 0.04 on 200.00 is 2 bps; 0.03 on 10.00 is 30 bps. Cents mislead; basis points do not.

HERE: Meme Street fills a market order at one price with a fee instead of a spread: the game simplifies the book on purpose. These lessons are about the real one.
[try /stock/NVXA?tf=1m] Open Novaxis on 1-minute candles and note how far the price moves between two trades a minute apart: in a real market a spread hides a cost of that size in every round trip.

## Market impact {market-impact} [6]
SUMMARY: Why a big order moves the price against you, and the square-root rule that estimates by how much.

### Eating the book
A market order larger than the best ask takes the next price level, then the next. Your average price climbs as you go. That climb is **market impact**, and it is paid before the market has moved for any other reason.

Q: You buy 10,000 shares at market when only 2,000 sit at the best ask. What happens to your average price?
+ It rises through the levels above the best ask
- It stays at the best ask for all 10,000 shares
- It falls, because large buyers are given a discount by the exchange
WHY: Each level has limited shares; a big order takes them in turn and the average climbs.

[chart breakout]

### The square-root law
Impact grows with the **square root** of order size, not in a straight line. A common estimate: impact ≈ Y × σ × √(Q ÷ V), with σ the day's volatility, Q your order, V the day's volume and Y about 1. Four times the order means twice the impact.

Q: Daily volatility is 2%, you want to buy 1% of the day's volume, and Y is 1. Roughly what impact does the rule predict, in percent?
= 0.2 ±10%
WHY: 2% × √0.01 = 2% × 0.1 = 0.2%.

Q: You double the order size. Under the square-root law, impact rises by about:
+ 41%, the square root of two
- 100%, in step with the size of the order
- 25%, because the depth absorbs most of it
WHY: √2 ≈ 1.41. Impact grows slower than size, which is why big traders still trade big.

### Hide the size
Traders split a large order into pieces over time, or into **dark pools** where the size is not shown. The trade-off is speed: the slower you go, the more the price can move away for reasons that have nothing to do with you.

Q: Why split a large order over an afternoon rather than send it at once?
+ To lower its impact on the price
- To pay the exchange's lower afternoon fee schedule
- To make the order count as several trades in the books
WHY: Smaller pieces take less depth at a time and let the book refill between them.

WARN: Part of the impact is permanent: some of the move stays after you finish, so your exit faces it again on the way out.

## Order flow and imbalance {order-flow} [6]
SUMMARY: Tell who the aggressor is in each trade, measure the imbalance between buyers and sellers, and read what it says about the next few minutes.

### Aggressors
Every trade has a passive side, the resting limit order, and an aggressive side, the order that crossed the spread to hit it. Trades at the ask are **buyer-aggressed**; trades at the bid are **seller-aggressed**. Order flow is the running total of the two.

Q: A trade prints at the ask price. Who was the aggressor?
+ The buyer, who crossed the spread
- The seller, who lowered the price to meet the buyer
- Neither: a trade at the ask is a matched auction
WHY: Hitting the ask takes a resting sell order. The buyer paid to trade now.

### Imbalance
**Imbalance** = (buy volume − sell volume) ÷ (buy volume + sell volume), from −1 to +1. A reading near +1 means buyers are doing nearly all the lifting. Prices tend to follow imbalance over the next few minutes, more so when the book is thin.

Q: In the last minute 30,000 shares traded at the ask and 10,000 at the bid. What is the imbalance?
= 0.5 ±0.02
WHY: (30,000 − 10,000) ÷ 40,000 = 0.5.

Q: Imbalance has been +0.8 for ten minutes but the price has not moved. What is the likeliest reading?
+ A large passive seller is absorbing the buying
- The data is wrong, because strong buying always lifts the price
- Buyers are about to give up, so a crash is certain
WHY: A wall. Someone is selling everything the buyers want at one price. When the wall goes, the move is fast.

### Flow is not the whole story
Flow tells you who is pressing now, not why or for how long. Pair it with levels: imbalance into a resistance that holds is a fade; imbalance through it is a breakout with fuel behind it.

[test breakout]

TIP: On a thin stock a single aggressive order can print a +0.9 minute. Read imbalance over several minutes, and against the size of the book.

## Auctions: the open and the close {auctions} [5]
SUMMARY: Why the first and last minutes trade differently, how an auction sets one price, and what the closing imbalance tells you.

### One price for everyone
The open and the close are **auctions**, not continuous trading. Orders pile up, and the exchange picks the single price that matches the most shares. Everyone in the auction trades at that price, whatever limit they gave.

Q: In an auction, 200,000 shares would match at 50.10 and 120,000 at 50.20. Where does the exchange set the price?
+ 50.10, where the most shares trade
- 50.20, the higher of the two, to favour the sellers
- 50.15, the midpoint between the two candidates
WHY: The auction price maximises the volume traded.

### The closing imbalance
Before the close, exchanges publish the **imbalance**: shares waiting to buy or sell in the auction with no match yet. A large buy imbalance pulls the closing price up as traders step in to supply it. Index funds, which must trade at the close, are often the reason.

Q: Ten minutes before the close a stock shows a 2,000,000-share buy imbalance. What usually happens?
+ The price drifts up into the close as sellers are drawn in
- Nothing, because buy and sell imbalances cancel out by the bell
- The exchange halts the stock until the imbalance clears
WHY: Someone must sell those shares at the auction, and they want a better price for doing it.

Q: A closing auction matches 1,200,000 shares, of which index funds account for 900,000. What share of the auction is index-fund trading, in percent?
= 75 ±1
WHY: 900,000 ÷ 1,200,000 = 75%.

[chart candle]

### Why the first minutes are wild
At the open, overnight news meets a thin book. Spreads are wide, impact is high and the first prints often overshoot. Many traders wait fifteen minutes before touching anything.

Q: Why is a market order in the first minute of the day costlier than the same order at 11 am?
+ The book is thin and the spread wide after the open
- Exchanges charge double fees in the first minute of trading
- Prices are frozen for the first minute, so the order has to wait
WHY: Thin depth and wide spreads make every market order pay more impact.

The close is the opposite case: the deepest minutes of the day, because the funds that are valued at the closing price have to trade there.

Q: Why do index funds trade heavily at the close?
+ They track the closing price, so trading there avoids tracking error
- The closing auction is free of fees for passive funds
- Their rules forbid any trading before the last ten minutes of the day
WHY: A fund valued at the close that trades at the close matches its index exactly.

HERE: Meme Street has no auction: the game's day opens and closes on the same tick-by-tick price, so the opening overshoot and the closing imbalance are things to know for the real market.

## Execution algorithms {execution-algos} [6]
SUMMARY: TWAP, VWAP and participation orders: how large traders feed an order into the market, and how to judge the fill afterwards.

### Slicing by time
A **TWAP** order splits the size into equal slices over a window: 20,000 shares over 100 minutes is 200 a minute. Simple and predictable, and blind to volume: it trades the same amount in a dead minute as in a busy one.

Q: A TWAP for 30,000 shares runs from 10:00 to 12:30. How many shares a minute does it send?
= 200 ±1
WHY: 150 minutes; 30,000 ÷ 150 = 200.

### Slicing by volume
A **VWAP** order trades in proportion to the day's usual volume curve: more at the open and the close, less at lunch. Its benchmark is the volume-weighted average price. Beating it means you bought below the average everyone paid that day.

Q: Your VWAP buy order filled at an average of 50.40 on a day whose VWAP ended at 50.25. How did the execution do?
+ Worse than the benchmark by 15 cents a share
- Better, because the fill was above the day's average
- The same, since VWAP orders always match the benchmark
WHY: A buyer wants to be below VWAP. Paying 15 cents more than the average is slippage against the benchmark.

### Participation
A **percentage-of-volume** order follows the market: trade 10% of whatever volume prints. It hides inside the flow and finishes whenever the market decides.

Q: Which order type finishes at a time nobody can know in advance?
+ Percentage of volume, which trades only as volume arrives
- TWAP, which spreads the order over fixed minutes
- A market order, which takes the whole book at once and is done
WHY: Participation depends on other people's trading. A quiet day stretches it out.

[test trend]

### Judging a fill
Compare the average fill with the **arrival price** (the mid when you decided), with VWAP, and with the close. Arrival-price slippage is the honest one: it includes the impact your own trading caused.

Q: Arrival price 20.00, average fill 20.06, 5,000 shares bought. What did slippage cost in MB?
= 300 ±1
WHY: 0.06 × 5,000 = 300 MB.

[try /stock/NVXA?ind=vwap&tf=5m] Open Novaxis with VWAP on: is the price above or below the day's average paid so far?

## Liquidity and when it vanishes {liquidity} [5]
SUMMARY: What liquidity really measures, why it disappears in a panic, and how to size a position for the exit rather than the entry.

### Three faces of liquidity
Liquidity is how much you can trade, how fast, for how little impact. Tight spreads, deep books and quick recovery after a trade are its three signs. A stock can have one without the others.

Q: Which stock is the most liquid?
+ Spread 1 bp, 50,000 shares at each level, the book refilling in seconds
- Spread 1 bp with 500 shares at each level and a slow refill after every trade
- Spread 40 bps but 50,000 shares at the best quotes and nothing behind them
WHY: All three signs at once: tight, deep and quick to recover.

### It leaves when you need it
In a panic, market makers widen spreads and pull depth. The same order that cost 5 bps at noon costs 50 at the worst minute. Liquidity is lowest exactly when the most people want out.

Q: The same market sell order costs 5 bps in a calm hour and 60 bps during a sharp sell-off. What changed?
+ Depth was pulled and spreads widened as makers stepped back
- The exchange raised its fees for the whole duration of the fall
- Nothing: the extra cost was only the price falling while you sold
WHY: Makers protect themselves in a fall by quoting less and wider. Your order pays for it.

[test level]

### Size for the exit
A position you can enter in a minute may take an hour to leave in a crash. A rule of thumb: keep a position under a few percent of the stock's average daily volume, so your exit does not become the news.

Q: A stock trades 400,000 shares a day. Under a 2% rule, what is the largest position in shares?
= 8000 ±1
WHY: 400,000 × 0.02 = 8,000 shares.

WARN: The rule is about the day you have to leave, not the day you arrive. A quiet entry says nothing about a crowded exit.

The habit to build: before the entry, ask how you would leave this position in an hour on the worst day of the year.

Q: Why size by the exit rather than the entry?
+ Getting out in a hurry costs far more than getting in at leisure
- Entries are always free of fees, so only the exits ever cost anything
- Brokers only enforce size limits when a position is being sold
WHY: Entries can wait for liquidity. Exits in a panic cannot, and they pay the widest spreads of the day.

HERE: A stock's volume shows under its chart in the game. The simulation does not thin the book in a crash, so this lesson is about what carries over to a real market.
