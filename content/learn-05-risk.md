# Risk management {risk}
The most important track. How much to risk, how to size a position from the stop, the maths of winning and losing, drawdowns, correlation and the risk of ruin.

## The 1% rule and sizing by risk {position-sizing} [7]
SUMMARY: Deciding how much to lose before deciding how much to buy.
Most beginners decide how much to **buy**. Professionals decide how much to **lose**, and let that set the size.

### The 1% rule
Risk at most **1% of your account** on any one trade (some use 0.5%, some up to 2%). "Risk" means what you lose if the stop is hit, not the size of the position.

### Position size from the stop
1. Decide the stop from the chart (where the idea is wrong).
2. Work out the distance from the entry to the stop.
3. Position size = (account × risk %) ÷ stop distance.

| Account | Risk | Entry | Stop | Distance | Position |
| 1,000 MB | 1% = 10 MB | 50 | 48 | 4% | 250 MB |
| 1,000 MB | 1% = 10 MB | 50 | 45 | 10% | 100 MB |
| 1,000 MB | 1% = 10 MB | 50 | 49.5 | 1% | 1,000 MB |

The wider the stop, the smaller the position. The risk stays the same.

### Why so little?
Because losing streaks happen to every trader. With 1% a trade, ten losses in a row cost about 10% of the account: painful, recoverable. With 10% a trade, the same streak costs two thirds of it.

### Allowing for gaps
A stop can gap. Holding through earnings or into a big release, the real risk can be several times the stop distance: size down further, or step aside.

HERE: The **Position size and risk** tool under every stock's chart does this sum: type the stop, choose 0.5%, 1% or 2% of your equity, choose a target (1.5R, 2R or 3R), and it says how many shares, what you lose at the stop and what you make at the target. **Fill in the trade and the bracket** sets it all up.

[try /stock/CLDR] Open CloudRail, pick a stop from the chart and let the risk tool size a 1% trade.

Q: A 2,000 MB account risks 1% with a stop 5% below the entry. What is the position size?
- 20 MB
+ 400 MB
- 2,000 MB
WHY: 1% of 2,000 is 20 MB of risk; 20 ÷ 5% = 400 MB.
Q: The stop moves twice as far away. What happens to the position size at the same risk?
+ It halves
- It doubles
- It stays the same
WHY: Size = risk ÷ distance; double the distance, half the size.
Q: What does "risk 1%" mean?
- Buy positions worth 1% of the account
+ Lose at most about 1% of the account if the stop is hit
- Expect to make 1%
WHY: Risk is the loss at the stop, not the size of the position.

## R-multiples and reward to risk {r-multiples} [6]
SUMMARY: Measuring every trade in units of its own risk, and what a reward-to-risk ratio buys you.
**R** is the amount you risk on a trade: the distance from entry to stop, in MB. Measuring results in R makes trades of different sizes comparable.
- Stopped out: **-1R**.
- Took profit at twice the risk: **+2R**.
- Closed at break-even: **0R**.

### Reward to risk
The distance to the target divided by the distance to the stop. A long at 100 with a stop at 95 (risk 5) and a target at 110 (reward 10) is **2 to 1**.

### The win rate you need
At a given reward to risk, you break even (before costs) when:

| Reward to risk | Break-even win rate |
| 1 to 1 | 50% |
| 1.5 to 1 | 40% |
| 2 to 1 | 33% |
| 3 to 1 | 25% |

At 3 to 1 you can be wrong three times out of four and still break even. That is why traders look for trades where the target is well beyond the stop.

### The catch
A far target is hit less often. A 3 to 1 trade with a target the price is unlikely to reach is not better than a 1.5 to 1 trade with a realistic one. The target must be somewhere the chart says the price can get to: the next resistance, a measured move.

[test rr]

Q: Long at 40, stop at 38, take-profit at 46. What is the reward to risk?
- 2 to 1
+ 3 to 1
- 1 to 3
WHY: Reward 6 (46 - 40), risk 2 (40 - 38): 3 to 1.
Q: At 2 to 1, what win rate breaks even before costs?
- 50%
+ About 33%
- 10%
WHY: Win 1 in 3: +2R once, -1R twice, 0 overall.
Q: You risked 15 MB and made 45 MB. What is the result in R?
+ +3R
- +45R
- +1R
WHY: 45 ÷ 15 = 3.

## Win rate, payoff and expectancy {expectancy} [7]
SUMMARY: Why a high win rate can lose money and a low one can win, and what to expect from a streak.
### Expectancy
What a strategy makes on average per trade:

Expectancy = (win rate × average win) - (loss rate × average loss)

In R: a strategy that wins 40% of the time, makes 2.5R when it wins and loses 1R when it loses expects 0.4 × 2.5 - 0.6 × 1 = **+0.4R per trade**. Over 100 trades risking 10 MB each, that is about +400 MB, before costs.

### High win rate, losing strategy
Win 80% of trades at +0.5R and lose 20% at -3R (a trader who takes small profits quickly and lets losers run): 0.8 × 0.5 - 0.2 × 3 = **-0.2R per trade**. It feels great most days and empties the account.

### Low win rate, winning strategy
Trend followers often win only 35 to 40% of their trades, with a few big winners paying for many small losses. It feels bad most days and works.

### Streaks are normal
Even with an edge, the order of wins and losses is random. A strategy that wins 40% of the time has about an even chance of **eight losses in a row** somewhere in 100 trades. If eight losses in a row would end your account or your nerve, your risk per trade is too high.

### Small samples lie
Ten trades say almost nothing about a strategy: luck dominates. Judge a strategy over 50 to 100 trades at least.

HERE: Your Portfolio page lists your best and worst closed trades and your realised profit; the History page can be downloaded to a spreadsheet to work out your own win rate, average win, average loss and expectancy.

Q: Wins 50% of the time at +1R, loses 50% at -1R, and pays costs. What is the expectancy?
- Positive
+ Slightly negative, because of costs
- Exactly zero
WHY: Zero before costs; costs make it negative.
Q: 40% wins averaging +2R, 60% losses averaging -1R. Expectancy?
+ +0.2R per trade
- -0.2R per trade
- +0.8R per trade
WHY: 0.4 × 2 - 0.6 × 1 = 0.2R.
Q: A strategy has lost seven trades in a row. What does that prove?
- It has stopped working
+ Very little on its own: streaks happen even with an edge
- It is due a win
WHY: Losing streaks are normal; and the next trade is not "due" anything either.

## Drawdown maths {drawdown} [5]
SUMMARY: Why losses hurt more than gains help, and why protecting capital comes first.
A **drawdown** is the fall from an account's peak to a low. Its cruel maths: the bigger the loss, the much bigger the gain needed to get back.

| Loss | Gain needed to recover |
| 10% | 11% |
| 20% | 25% |
| 30% | 43% |
| 50% | 100% |
| 75% | 300% |
| 90% | 900% |

Lose half and you must double what is left just to get back to where you started. That asymmetry is why every professional's first rule is to keep losses small: a 10% hole is an inconvenience, a 50% hole is a career.

### Maximum drawdown
The deepest drawdown a strategy or an account has had. Two strategies that made the same return are not equal if one of them fell 15% along the way and the other 60%: the second was far riskier and far harder to stick with.

### Recovering
After a drawdown, cut the size, not the discipline. Trading bigger to "win it back" is how drawdowns become blow-ups.

HERE: The Leaders page and your profile show your **worst drawdown**, and your Portfolio's equity curve shows every one of them: the drops from the peak. The leaderboards rank return on the money you put in, so a big drawdown hurts your rank just as it would hurt a real account.

Q: An account falls from 1,000 to 500 MB. What gain does it need to get back to 1,000?
- 50%
+ 100%
- 200%
WHY: 500 must double to reach 1,000.
Q: Two strategies both made 40% last year. One had a 15% maximum drawdown, the other 55%. Which was riskier?
+ The one with the 55% drawdown
- They were equally risky
- The one with the 15% drawdown
WHY: The same return through a much deeper fall means far more risk taken.
Q: After a big drawdown, what is the sensible response?
- Trade bigger to win it back quickly
+ Trade smaller and stick to the plan
- Stop using stops
WHY: Bigger size after losses turns a drawdown into a blow-up.

## Correlation and diversification {correlation} [6]
SUMMARY: When five positions are really one bet, and how to spread risk.
**Correlation** measures how much two prices move together, from +1 (always the same way) through 0 (unrelated) to -1 (always opposite).

### Five trades, one bet
Long five chip makers, risking 1% on each, is not 5% spread over five ideas. They are one idea (chips go up) and they will often all hit their stops on the same day. Count correlated positions as one when you add up your risk.

### Diversification
Spreading money over things that do not move together reduces the swings of the whole account without reducing its expected return as much. A mix of industries, of large and small companies, of stocks and safe havens, is steadier than any one of them.

### Correlations change
In calm markets, stocks drift on their own news. In a sell-off, almost everything falls together: correlations jump towards 1 exactly when diversification is needed most. Safe havens (government bonds, gold) are the usual exception.

### Beta
**Beta** measures how much a stock moves with the market: beta 1.5 means it tends to move 1.5% when the market moves 1%. A portfolio of high-beta stocks is a leveraged bet on the market, however many names are in it.

HERE: Companies here move with the market (through their beta), with their industry and on their own news, and a whole industry can fall while the market rises. In corrections and bear markets the market's share of every move gets bigger, so stocks fall together, as in real markets. **BOND** (Steady Bonds) and **GLDN** (Golden Reserve) are the safe havens.

[try /stock/XTECH] Open the technology index and compare its chart with the MSI 50's: how closely do they move together?

Q: You hold five banks, each risking 1%. How much risk is that really?
- 1%, since they are spread out
+ Closer to 5% on one idea, because banks move together
- 0.2%
WHY: Highly correlated positions behave like one big position.
Q: What tends to happen to correlations in a market sell-off?
+ They rise: most stocks fall together
- They fall to zero
- Nothing changes
WHY: In panics, investors sell everything at once; diversification across stocks helps least when needed most.
Q: A stock has a beta of 2. The market falls 3%. What might the stock do, from beta alone?
- Rise 6%
+ Fall about 6%
- Fall 1.5%
WHY: Beta 2 means roughly twice the market's move: 2 × -3% = -6%.

## Risk of ruin {risk-of-ruin} [6]
SUMMARY: The chance of losing so much that you cannot recover, and how fast it grows with the size of each bet.
**Risk of ruin** is the chance that a series of losses takes your account below a point you cannot come back from. It depends on three things: your edge, your payoff, and how much you risk each time. The last one is the only one you fully control.

### Even a winning strategy can go broke
Take a trader with a genuine edge: they win half their trades, and win 1.5 times what they lose. Over 500 trades, the chance of halving the account at some point:

| Risk per trade | Chance of losing half the account |
| 1% | almost none |
| 2% | almost none |
| 5% | about 2% |
| 10% | about 18% |
| 20% | about 58% |

Same strategy, same edge; the only difference is the size of each bet. Without an edge, any size eventually loses: a trader who wins 40% at 1.5 to 1 (no edge) risking 2% a trade halves the account about a quarter of the time over 500 trades, and at 5% about four times in five.

### Why big bets kill
Large bets make the account's path depend on luck in the short run, and the drawdown maths means a deep hole is very hard to climb out of. A small, steady risk keeps you in the game long enough for an edge to show.

### All-in is the extreme
Putting everything into one trade risks ruin on a single outcome, however good the idea. No idea is good enough for that.

HERE: There is no limit on position size: you can put your whole account into one stock, and with leverage control several times your account. Nothing stops you except your own rules. If you do run out, the low-funds banner offers a free restart, but on a real account there is none.

Q: Same strategy, same edge. What changes the risk of ruin the most?
+ The share of the account risked on each trade
- The colour scheme of the chart
- The number of indicators used
WHY: Bet size is the main lever: small bets make ruin very unlikely for a strategy with an edge.
Q: Can a strategy with a real edge still go broke?
- No, an edge guarantees profit
+ Yes, if it risks too much on each trade
- Only if it trades options
WHY: Big bets let a run of bad luck do damage that the edge cannot repair in time.

## Where stops go {stop-placement} [6]
SUMMARY: Stops at the point where the idea is wrong, outside the noise, and not where everyone else's are.
A stop has one job: to get you out when the reason for the trade is no longer true.

### Technical stops
Put the stop where the chart says the idea is wrong:
- Bought a bounce off support: below the support.
- Bought a breakout: back inside the range.
- Bought a pullback in an uptrend: below the last higher low.
- Traded a pattern: beyond the other side of the pattern.

### Outside the noise
Prices wobble. A stop closer than about one ATR from the entry is inside normal noise and gets hit by chance, even when the trade idea was right. Give the level a margin: a fraction of an ATR beyond it.

### Not exactly where everyone else's is
Stops cluster just beyond obvious levels and round numbers. Prices often poke through those levels, trigger the stops, and come back (a "stop run"). A stop slightly further than the obvious place, with the position sized to match, survives more of those.

### Arbitrary stops
"I always use a 5% stop" ignores the chart: on a calm stock 5% is miles away; on a wild one it is inside a single candle's noise. Stops come from the chart and the volatility, and the size from the stop.

### Never move a stop further away
Moving a stop away from the price as it approaches is turning a planned loss into an unplanned bigger one. Move it only towards profit.

[test stop]

Q: You buy a breakout above 120 from a range of 100 to 120. Where does the stop belong?
- At 119.99
+ Back inside the range, somewhat below 120
- At 100, always
WHY: A close back inside the range means the breakout failed; a little margin keeps it out of the noise.
Q: The stock's ATR is 2 MB. You want a stop 0.3 MB from your entry. What is the problem?
+ It is inside normal noise and likely to be hit by chance
- It is too far away
- There is no problem
WHY: A typical candle moves 2 MB; a 0.3 MB stop will be touched by ordinary movement.
Q: The price is falling towards your stop. What do you do?
- Move the stop further down to give it room
+ Leave it: it is where the idea is wrong
- Remove it
WHY: Widening a stop under pressure turns a planned small loss into a bigger one.
