# Ballast: how to use it

Ballast is a risk toolkit inside cTrader. It works out the position size for the risk you choose, places the trade
with its stop attached, sizes new trades to fit the loss limits you enter, and records your results. It gives no
signals and no advice: every trade is your choice. Try it on a demo account first.

**Ballast Free** has the Ticket (sizing, costs, ATR stops), Exposure and Sessions; it does not place orders.
**Ballast** adds the Place button, Limits and the Journal.

## Open it

In cTrader, Ballast appears where you installed it: in the symbol panel beside the chart, as a tab in Trade Watch,
as its own window, or (on a phone) from a symbol's Overview. It opens on the symbol you are looking at; type another
name in the symbol box to change it. Numbers follow your device's format (1,250.50 or 1.250,50).

## Ticket: size a trade

1. **Buy or Sell**, and the **order**: Market (now), Limit (a better price than now) or Stop (a breakout price).
   Limit and Stop ask for the entry price.
2. **Stop**: where you will be proved wrong. In pips from the entry (a pip is the usual small step: 0.0001 on most
   currency pairs, 0.01 on yen pairs; indices and crypto use points), as a price, or as a multiple of ATR, the
   market's average move per bar on the chart period you choose.
3. **Target** (optional): a multiple of your risk ("2" means twice what you risk), or a price.
4. **Risk**: a percent of your balance, or an amount of money. The 0.5%, 1% and 2% buttons fill it in.
5. **Costs**: choose how your broker charges commission (per lot each side, per million USD each side, or a percent
   of the trade's value each side) and enter the figure once; it is in cTrader's symbol information or your account's
   terms. Choose "none" if you pay none. Until you choose, the ticket reminds you that commission is not counted.

The result shows the size in lots, the stop as a price, what you lose if the stop is hit (price and commission), what
one pip is worth, and the reward to risk with the win rate it needs to break even. When the symbol's currency is not
your account's, the rate used is shown. Ballast always rounds down; if even the smallest allowed size would lose more
than your risk, it says so and does not size the trade.

6. **Review order** (or Enter) shows everything once more, in place of the form. The button names the trade, for
   example **Buy 0.50 lots EURUSD**; it sends the order once, and a double tap does not send two. **Back** returns to
   the form; **New trade** starts the next one.

Ballast checks everything again at the moment you press the button: if the price, your limits or your account changed
since the review, it says so and sends nothing. It also refuses:
- a stop less than a pip beyond the price the trade would close at (for a limit or stop order, allowing for today's
  spread when it fills), because it would be hit at once;
- spread-betting accounts (they trade in stakes per point);
- a netting account that already holds the symbol or has an order on it (a new order would change that position);
- a price that has not updated for two minutes.

## Limits: size new trades to your loss limits

For anyone with a daily or total loss limit, especially a funded ("prop firm") account. Settings are kept for each
trading account on this device.

- **Daily loss limit** and **Total loss limit**: as a percent of the starting balance, or in money.
- **Starting balance**: the account's size when it began (a funded account's size). A percent limit needs it.
- **Daily loss counts from**: your firm's rule, either the day's opening balance or the higher of the opening
  balance and equity. For the second, Ballast uses the opening balance when nothing was open as the day began;
  otherwise it needs the opening equity, which it records if it is open when the day starts, or which you type in.
- **Total loss counts from**: the starting balance (static), or the highest balance or equity reached (trailing).
  For a trailing limit, type your firm's current lowest allowed equity, and again when it changes: Ballast cannot see
  a peak reached while it was closed.
- **The day starts at**: your firm's reset time and time zone (for example 00:00 Prague). Ballast shows when that is
  in your own time.
- **Open trades**: "count them at their stops" (the default, and the careful choice) treats every open position and
  pending order as if its stop were hit.
- **Exact figures from your firm**: when your firm's dashboard shows today's lowest allowed equity, or today's opening
  equity, type it here and Ballast uses it instead of its own sum. Today's figures clear when the day resets.

Ballast then shows what you have lost so far, what you would have lost if every open stop were hit, and the most a new
trade may lose. Each new trade is cut to fit, and at a limit Ballast places no orders until it resets. When it cannot
check the figures (the history, positions or orders did not load, the balance is stale, an open trade cannot be valued,
a pending order has no stop), it blocks orders and says why, rather than guess.

Firms' rules differ and change: read yours and match it here. Ballast protects its own orders: trades placed
elsewhere in cTrader are counted, but not blocked. A stop is not a guaranteed price, so a gap can still pass a limit.

## Exposure

Every open position and pending order, what it loses at its stop in your money and as a share of your balance, and
the total. Positions without a stop are marked: their loss has no limit.

## Journal

Every trade placed from Ballast, once it closes, in **R**: its result divided by the money it risked. +2 R made
twice the risk; -1 R lost what was planned. The journal shows win rate, average R, profit factor and the longest
losing run, overall and by symbol. A small number of trades says little: wait for 30 or more. **Download as CSV**
opens in any spreadsheet.

## Sessions

Sydney, Tokyo, London and New York: open or closed, and for how long, in each city's own time. Your broker's hours
for a symbol can differ.

## Privacy

Ballast sends no data anywhere; it cannot (its security policy blocks every network connection). Your settings are
kept in your browser or the cTrader app on your device, separately for each trading account.

## If something looks wrong

Check on a demo account, then write in the product's comments in the cTrader Store with the symbol, your account
currency and what you saw. A wrong size is fixed within 48 hours, or the product comes down until it is.
