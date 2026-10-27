# Shorting and leverage {shorting}
Profiting from falls, what it costs, short squeezes, margin and leverage, and why leverage cuts both ways.

## How shorting works {shorting-basics} [6]
SUMMARY: Selling what you do not own, buying it back later, and what it costs to hold.
**Shorting** is a bet that a price will fall. In a real market:
1. Your broker lends you shares that belong to someone else.
2. You sell them at today's price.
3. Later you buy the same number back (**cover**) and return them.
If the price fell, you bought back cheaper and keep the difference. If it rose, you pay the difference.

### What makes it risky
- **Unlimited loss**: a stock can only fall to zero (a 100% gain for a short), but it can rise without limit. A short at 50 that runs to 150 has lost twice its value.
- **Borrow fees**: you pay to borrow the shares, every day you hold them. Hard-to-borrow stocks cost much more.
- **Dividends**: a short pays the dividend to the lender.
- **The market's drift**: over the long run markets rise, so a short works against the tide.
- **Recalls and squeezes**: the lender can ask for the shares back, and a crowded short can be squeezed (next lesson).

### Why anyone does it
To profit from falling prices, to hedge a long position (long a company, short its industry index), and because a market where prices can only be bet upwards is a less honest market. Short sellers have exposed many frauds.

HERE: Press **Sell** on a stock you do not hold and the button says **Short**. The amount you short is taken out of your cash and held as collateral; when you cover, you get it back plus your gain or minus your loss. A short pays a **borrow fee** every second it is open (more on a volatile stock, and more when many players are short the same stock: about 0.10% a real hour on gold, 0.14% on Novaxis, 0.27% on DOGO when few are short), pays any dividend that goes ex while it is open, and is closed by a **margin call** if your equity falls below the safety level for all your shorts. You cannot be long and short the same stock at once.

[try /stock/DOGO] Open DOGO Inc and read the costs line under the trade buttons: it shows the borrow fee per hour.

## Short squeezes {squeezes} [5]
SUMMARY: How short sellers rushing to cover can send a price flying.
A **short squeeze** happens when a heavily shorted stock rises and the short sellers rush to buy it back: to cut their losses, or because their margin calls force them to. Their buying pushes the price higher, which forces more shorts to cover, which pushes it higher still.

### The ingredients
- **High short interest**: a large share of the available shares sold short.
- **Days to cover**: short interest divided by daily volume; the more days it would take shorts to buy back, the more violent the rush.
- **A trigger**: good news, a surprise result, or a crowd of buyers deciding to target the shorts (as with GameStop in January 2021, which rose more than twentyfold in weeks).

### Lessons for short sellers
- Size shorts smaller than longs: the upside risk is open-ended.
- Avoid crowded shorts: high borrow fees are a warning sign.
- Always use a stop, and expect it to gap.

HERE: Players' trades never move prices, so a squeeze cannot be caused by players covering. Prices can still jump hard against a short on news, an earnings surprise or a burst of buying in the price model, and the **borrow fee rises** as more players short the same stock (up to four times when it is very crowded), so a crowded short is expensive to hold.

## Margin, leverage, margin calls and liquidation {margin-leverage} [7]
SUMMARY: Trading with borrowed money: margin, maintenance, margin calls and forced closing.
**Leverage** means controlling a position bigger than your own money, by borrowing the rest. At **5x**, 100 MB of your own controls 500 MB of stock; the broker lends you 400 MB and charges interest on it.

### Margin
- **Initial margin**: your own money in the position (100 MB above: 20% of it).
- **Maintenance margin**: the minimum equity the position must keep. If losses take it below that, you get a **margin call**.

### Margin calls and liquidation
In a real market a margin call asks you to add money or reduce the position. If you cannot, or the market moves too fast, the broker **liquidates**: closes the position at the market price, whatever that is. In a fast fall, liquidations trigger more selling and more liquidations, which is how leverage turns falls into crashes.

### The price where you are closed out
At a given leverage, a certain move against you wipes out your margin. The higher the leverage, the smaller the move:

| Leverage | Move that wipes out the margin |
| 2x | 50% |
| 5x | 20% |
| 10x | 10% |

Real brokers close you out before that, at the maintenance level.

HERE: Leverage is part of **Pro**: 1x, 2x, 3x, 5x or 10x on any listing except the leveraged funds. Each position stands on its own margin: when its equity falls to **half the margin it started with**, it is closed at the market price (after a 25% move against you at 2x, 10% at 5x, 5% at 10x). The position box and the Holdings page show the leverage, the loan and **the price where it closes by itself**. The loan costs about 0.06% a real hour. A gap past that price takes the rest from your cash. Plain shorts have their own margin call (previous lesson).

## Why leverage magnifies losses {leverage-maths} [5]
SUMMARY: Leverage changes the size of the bet, never the odds, and makes recovery harder.
### The same move, multiplied
A 3% rise at 5x is +15% on your money. A 3% fall is -15%. Leverage does not make a trade more likely to win; it makes each outcome bigger, in both directions, and the costs (interest, fees on the whole position) bigger too.

### Volatility drag
Swings hurt leveraged accounts more than their size suggests. A stock that falls 10% and rises 10% ends 1% down. At 5x, -50% then +50% ends 25% down. The deeper the swings, the faster a leveraged position decays, even if the price ends where it started.

### Drawdowns arrive faster
With 10x leverage, the drawdown table from the *Risk* track is reached ten times as fast. A 5% move that would be a nuisance unleveraged takes half the account.

### When leverage makes sense
Professionals use leverage with **small risk per trade**: a tight, logical stop and a position sized so the loss at the stop is still 1% of the account. Leverage then lets a small stop-distance trade be big enough to matter, without risking more. Using leverage to make every trade bigger is the opposite: it raises the risk on every trade.

HERE: Leverage on Meme Street changes how big your bet is, never the odds: a leveraged position wins and loses the same price moves, several times as hard, and on average loses the interest and fees several times as fast.
