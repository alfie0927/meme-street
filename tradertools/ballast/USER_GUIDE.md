# Ballast: how to use it

Ballast is a risk toolkit inside cTrader. It works out how big a trade should be for the risk you choose, places it
with its stop attached, keeps you inside your loss limits, and records how your trades went. It gives no signals and
no advice: every trade is your choice. Try it on a demo account first.

## Open it

In cTrader, Ballast appears where you installed it: in the symbol panel beside the chart, as a tab in Trade Watch,
as its own window, or (on a phone) from a symbol's Overview. It opens on the symbol you are looking at.

## Ticket: size a trade

1. **Buy or Sell**, and the **order**: Market (now), Limit (a better price than now) or Stop (a breakout price).
   Limit and Stop ask for the entry price.
2. **Stop**: where you will be proved wrong. In pips from the entry (a pip is the usual small step: 0.0001 on most
   currency pairs, 0.01 on yen pairs), as a price, or as a multiple of ATR, the market's average move per bar on the
   chart period you choose under Costs.
3. **Target** (optional): a multiple of your risk ("2" means twice what you risk), or a price.
4. **Risk**: a percent of your balance (1% is common), or an amount of money.
5. Under **Costs**, enter your broker's commission once: per lot each side, or per million USD each side. It is in
   cTrader's symbol information or your account's terms. Ballast counts it twice, for opening and closing.

The result shows the size in lots, what you lose if the stop is hit (price and commission), and the reward to risk.
Ballast always rounds down; if even the smallest allowed size would lose more than your risk, it says so and does
not size the trade.

6. **Review order** shows everything once more. **Place order** sends it, once; a double tap does not send two.
   Change anything and the review closes, so you always place what you reviewed.

Ballast refuses a stop that is less than a pip beyond the price the trade would close at (it would be hit at once),
spread-betting accounts (they trade in stakes per point), and a netting account that already holds the symbol (a new
order would change that position).

## Limits: stay inside your loss limits

For anyone with a daily or total loss limit, especially a funded ("prop firm") account.

- **Daily loss limit** and **Total loss limit**: in money, or as a percent of the starting balance.
- **Starting balance**: the account's size when it began (a funded account's size).
- **Daily loss counts from**: your firm's rule, either the day's opening balance or the higher of the opening
  balance and equity. (For the second, keep Ballast open over your firm's day change so it sees the opening equity.)
- **Total loss counts from**: the starting balance, or the highest balance or equity reached (trailing).
- **The day starts at**: your firm's reset time and time zone (for example 00:00 Prague).
- **Open trades**: "count them at their stops" (safer) treats every open trade as if its stop were hit.

Ballast then shows how much of each limit is used, cuts every new trade so a stop-out cannot break either limit,
and stops placing orders when one is reached. If the account's history cannot be read, it blocks orders until it
can, rather than guess. Firms' rules differ and change: read yours and match it here. Ballast protects its own
orders: trades placed elsewhere in cTrader are counted, but not blocked.

## Exposure

Every open position, what it loses at its stop in your money and as a share of your balance, and the total.
Positions without a stop are marked: their loss has no limit.

## Journal

Every trade placed from Ballast, once it closes, in **R**: its result divided by the money it risked. +2 R made
twice the risk; -1 R lost what was planned. Average R above zero over many trades means the way you trade has made
money so far. A small number of trades proves little: wait for 30 or more. Download the journal as a spreadsheet
with **Download as CSV**.

## Sessions

Sydney, Tokyo, London and New York: open or closed, and for how long, in each city's own time. Your broker's hours
for a symbol can differ.

## Privacy

Ballast sends no data anywhere; it cannot (its security policy blocks every network connection). Your settings are
kept in your browser or the cTrader app on your device, separately for each trading account.

## If something looks wrong

Check on a demo account, then write in the product's comments in the cTrader Store with the symbol, your account
currency and what you saw. A wrong size is fixed within 48 hours, or the product comes down until it is.
