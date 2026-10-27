# Testing and automation {testing}
Advanced. Backtesting and the overfitting trap, walk-forward and out-of-sample testing, the statistics that judge a strategy, and building a trading bot.

## Backtesting and the overfitting trap {backtesting} [7]
SUMMARY: Testing rules on past data, and the many ways a backtest can lie.
A **backtest** runs a set of precise rules over past prices to see how they would have done: every entry, exit, cost and result, as if traded at the time.

### What a backtest can tell you
- Whether an idea had any edge at all in the past.
- Its likely win rate, average win and loss, drawdowns and losing streaks: what it would **feel** like to trade.
- Whether costs eat the edge.

### How backtests lie
- **Overfitting (curve fitting)**: tweak the settings until the past looks perfect (a 17-candle average, an RSI of 31.5, stops at 2.3 ATR) and you have described the noise of that particular past, not a pattern that will repeat. The more settings you try, the more certain it is that the best one looks great by luck.
- **Look-ahead bias**: using information the trader could not have had at the time (today's close to decide to buy at today's open).
- **Survivorship bias**: testing only on companies that still exist today, forgetting the ones that went bust.
- **Ignoring costs**: fees, spreads and slippage, which kill high-frequency ideas.
- **Too few trades**: 15 trades prove nothing.

### Signs of overfitting
- Many rules and settings, each with an oddly specific value.
- Results that fall apart if a setting changes a little.
- A smooth equity curve with no losing months: real edges are lumpy.
- It works on one stock and one period, and nowhere else.

### Keep it simple
Robust strategies tend to have few rules, round settings, and work across many stocks and periods without retuning. If a small change in a setting turns a winner into a loser, there was never an edge.

HERE: With the **Expert** pass, the Bots page backtests any bot on the candles the game keeps (up to 5,000 per candle size), with orders filled at the next candle's open, the same 0.1% fee, leverage costs and options priced as the game prices them. The result compares the bot with simply holding the stock. The market has no free money in it, so a rule that did well over a few days has usually found luck: the result says so.

Q: You try 500 combinations of settings and pick the best. What is the main danger?
+ The best one looks good mostly by luck: overfitting
- It will be too slow
- None, more tests mean more certainty
WHY: With enough tries, some settings fit the past's noise perfectly and fail on new data.
Q: A backtest buys at the open using that day's closing price to decide. What is wrong?
- Nothing
+ Look-ahead bias: the close was not known at the open
- Survivorship bias
WHY: The rule uses information from the future.
Q: Which strategy is more likely to be robust?
- Twelve rules with very precise settings that win on one stock
+ Three simple rules that work on many stocks with round settings
- One that never had a losing month in the test
WHY: Simplicity and breadth are signs of a real effect; precision and perfection are signs of fitting noise.

## Walk-forward and out-of-sample testing {walk-forward} [6]
SUMMARY: Keeping some data back, and testing the way you would really trade.
### In-sample and out-of-sample
Split the history in two:
- **In-sample**: the part you use to design and tune the strategy.
- **Out-of-sample**: a part you never look at until the end. Run the finished strategy on it once.
If it does about as well out-of-sample, you may have something. If it collapses, the in-sample result was fitted to noise. Look at the out-of-sample data more than once, tweaking each time, and it stops being out-of-sample.

### Walk-forward testing
Repeat that through time: tune on months 1 to 6, test on month 7; tune on 2 to 7, test on 8; and so on. The joined-up test months show how the strategy would have done if you had really traded it, re-tuning as you went.

### Paper trading
After testing, trade it with no real money (or tiny size) for a while. Live markets reveal problems no backtest shows: fills, delays, and how you feel following the rules.

### Different markets
A strategy that works on one stock should be tried on others and in other conditions (rising, falling, flat). An edge that exists only in one place and one period is probably not an edge.

HERE: A backtest here can run on any of a bot's stocks and at any of its candle sizes: design a bot on one stock, then test it unchanged on others. Meme Street itself is paper trading: real prices, practice money.

Q: You tuned a strategy on 2019 to 2022 and kept 2023 untouched. What is 2023?
+ Out-of-sample data
- In-sample data
- Useless
WHY: Data not used in designing the strategy tests whether it generalises.
Q: You test on the out-of-sample data, tweak, and test again, ten times. What has happened?
- The strategy is now ten times more reliable
+ The out-of-sample data has been used for fitting, so it no longer tests anything
- Nothing
WHY: Each look leaks information into the design.

## Sharpe, drawdown and profit factor {performance-stats} [6]
SUMMARY: The numbers that judge a strategy beyond its total return.
Return alone says little: how much risk was taken to get it?

| Statistic | What it is | Rough guide |
| Total return | what it made | compare with holding the index |
| Win rate | share of trades that made money | means little alone |
| Average win / average loss | the payoff | with the win rate, gives expectancy |
| Profit factor | gross profit ÷ gross loss | above 1 makes money; 1.5+ is good; 3+ is suspicious |
| Maximum drawdown | worst fall from a peak | can you live through it? |
| Sharpe ratio | average return ÷ volatility of returns (above cash), yearly | 1 is decent, 2 is very good, above 3 deserves suspicion |
| Time in the market | share of time holding a position | less time, less exposure |
| Number of trades | the sample | under 30 means little |

### Reading them together
- A high return with a 60% drawdown is a strategy few people could actually follow.
- A profit factor of 1.1 after costs is fragile: a small change in conditions and it is gone.
- A Sharpe ratio above 3 in a backtest is more likely a bug or overfitting than a discovery.

### The benchmark again
Every statistic should be compared with buying and holding the same thing over the same period.

HERE: A backtest on the Bots page reports the return against holding the stock, the trades, the win rate, the average win and loss, the **profit factor**, the **worst drawdown**, the fees, the time in the market and the equity curve.

Q: Gross profit 3,000 MB, gross loss 2,000 MB. What is the profit factor?
+ 1.5
- 1,000
- 0.67
WHY: 3,000 ÷ 2,000 = 1.5.
Q: A backtest shows a Sharpe ratio of 6. What is the most likely explanation?
- A genius strategy
+ An error, look-ahead bias or overfitting
- A normal result
WHY: Sharpe ratios that high are extremely rare in real trading; suspect the test first.

## Building and judging a trading bot {bots} [7]
SUMMARY: Turning a strategy into rules a computer can follow, and testing it honestly.
A **trading bot** follows written rules without hesitation, fatigue or fear. It does exactly what you tell it, including the mistakes.

### From idea to rules
"Buy pullbacks in an uptrend" has to become precise:
- **Trend**: close above the 50 EMA, and the 50 EMA above the 200 EMA.
- **Pullback**: RSI(14) below 40.
- **Entry**: buy when the RSI crosses back above 40.
- **Exit**: stop 2 ATR below the entry, target 4 ATR above, or close below the 50 EMA.
- **Size**: a fixed share of the account per trade.

### Testing it honestly
1. Backtest on one stock. Look at the trades, not just the total: are they the trades you meant?
2. Test it unchanged on other stocks and candle sizes.
3. Check the statistics: enough trades, a drawdown you could live with, a result compared with holding.
4. Run it small, live, and compare with the backtest.

### What bots are good and bad at
- Good: consistency, speed, never skipping a signal, never moving a stop.
- Bad: context. A bot does not know an earnings report is due unless you tell it, or that the market has just crashed.

### Keep watching it
Markets change. A bot that worked for months can stop working. Decide in advance what result (a drawdown, a run of losses) means switching it off.

HERE: With the **Expert** pass you can run up to five bots, each on up to ten stocks at one candle size, with up to ten rules written in a small language: candles, indicators (moving averages, RSI, MACD, ATR, Bollinger Bands, the stochastic, VWAP, highest and lowest), crosses, your position and a news score from words you choose. The bot guide lists every word a rule can use, with examples.

[try /bots/guide] Read the bot guide and write down, in its rule language, the pullback strategy described above.

Q: A bot buys every time the RSI drops below 30, with no stop. What is the biggest risk?
+ A falling stock stays oversold and the bot keeps buying with no exit
- It trades too rarely
- RSI cannot be used by bots
WHY: Without a stop or a trend filter, a mean-reversion bot can ride a collapse all the way down.
Q: What is a bot better at than a person?
- Understanding the news in context
+ Following the rules every time, without fear or fatigue
- Knowing when the market has changed
WHY: Consistency is a bot's strength; judgement and context are not.
