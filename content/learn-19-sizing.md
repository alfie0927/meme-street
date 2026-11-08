# Sizing under uncertainty {sizing-uncertainty}
How much to risk when you do not know your edge for sure: the Kelly criterion and why nobody trades it in full, the losing streaks chance alone will hand you, the risk of ruin, Monte Carlo on your own trades, and how correlation turns five small risks into one big one. Expert.
TIER: expert

## The Kelly criterion {kelly} [6]
SUMMARY: Work out the fraction of capital that grows an account fastest, and see why that fraction is a ceiling, not a target.

### The formula
For a bet that wins a fraction p of the time and pays b times the risk when it does, the fraction of capital that maximises long-run growth is **f\* = p − (1 − p) ÷ b**. Win 55% at 1.5 to 1 and Kelly says risk 25% of the account on each trade.

Q: A setup wins 55% of the time and pays 1.5 times the risk. What is the Kelly fraction, in percent of capital?
= 25 ±1
WHY: 0.55 − 0.45 ÷ 1.5 = 0.55 − 0.30 = 0.25.

Q: A setup wins 40% of the time and pays 1 to 1. What does Kelly say?
+ Risk nothing: the edge is negative
- Risk 40%, the win rate
- Risk 10%, to keep the losses small
WHY: 0.40 − 0.60 ÷ 1 is below zero. A negative Kelly fraction means do not take the bet.

### Why it is a ceiling
Full Kelly maximises growth on paper and produces drawdowns of 50% or more along the way, as a matter of routine. Betting more than Kelly grows slower *and* swings harder; at twice Kelly the long-run growth is zero. Nobody knows their edge well enough to sit at the top of that curve.

Q: You estimate your Kelly fraction at 20% and trade exactly that. Your real edge turns out smaller than you measured. What happens?
+ You are over Kelly: more risk, less growth
- Nothing changes, because Kelly adapts to the real edge
- You grow faster, since more risk always means more return
WHY: Kelly is computed from an estimate. Overestimate the edge and you are on the wrong side of the peak.

[test rr]

### Edges are estimates
A win rate from 50 trades has an error bar of about seven percentage points either way. Kelly on the point estimate can be twice the true figure. The remedy is the next lesson: trade a fraction of the fraction.

Q: Fifty trades gave a 60% win rate. What is the honest reading of that number?
+ Somewhere around 53% to 67%, with 60% the best guess
- Exactly 60%, since fifty trades is a large enough sample to settle it
- Meaningless until a thousand trades are in
WHY: A sample of 50 carries roughly a seven-point standard error. The estimate is useful but soft.

HERE: Your win rate, average win and average loss are on the Your trading card on the Learn page. Put them into the formula before you believe any size.

## Fractional Kelly {fractional-kelly} [5]
SUMMARY: Trade a fraction of the Kelly size, know what growth it gives up and what pain it saves, and pick a fraction you can live with.

### Half the size, three quarters of the growth
Growth against the fraction bet is a hill with its top at Kelly. Half Kelly sits at **75%** of the peak growth with half the swings; quarter Kelly at about 44% of the growth with a quarter of the swings. The hill is flat near the top and steep past it.

Q: You trade half the Kelly fraction. Roughly what share of the maximum long-run growth do you keep, in percent?
= 75 ±1
WHY: Growth at a fraction k of Kelly is about k × (2 − k) of the peak: 0.5 × 1.5 = 0.75.

Q: What does half Kelly buy you compared with full Kelly?
+ Far smaller drawdowns for a modest loss of growth
- Faster growth and smaller drawdowns at the same time, with no trade-off
- The same growth with no drawdowns at all
WHY: Variance falls with the square of the fraction; growth falls only a little near the top.

### The fraction protects against being wrong
Half Kelly on a measured edge is close to full Kelly on an edge half as big. If your estimate is off by a factor of two, half Kelly is still on the safe side of the hill. That is its real job: insurance against your own numbers.

Q: Why do professionals who know Kelly still trade a quarter to a half of it?
+ Their edge is an estimate, and being past the peak is costly
- Exchanges cap position sizes at half the Kelly fraction for retail accounts
- Kelly only applies to casino games, not to markets
WHY: The fraction is a margin for error in the edge itself.

[chart level]

### From fraction to position
Kelly gives a share of capital to risk, not a share to invest. With the stop 5% below the entry and a 2% Kelly fraction, the position is 2% ÷ 5% = 40% of the account in shares, risking 2% of it.

Q: Quarter Kelly works out to a 2% risk per trade. The stop is 4% below the entry. What share of the account goes into the position, in percent?
= 50 ±1
WHY: 2% ÷ 4% = 50% of the account, risking 2% of it if the stop is hit.

HERE: The risk tool on a stock's page sizes a position from the stop and the risk you type. Type the fraction you chose here, not the Kelly number itself.

## Losing streaks and drawdowns by chance {losing-streaks} [6]
SUMMARY: Estimate the losing run chance will hand even a good strategy, turn it into a drawdown, and size so that run is survivable.

### Streaks happen to everyone
With a 50% win rate, the longest losing streak in 100 trades is usually about seven. In 1,000 trades, about ten. The rule of thumb: longest streak ≈ log(N) ÷ log(1 ÷ q), with q the loss rate. A streak proves nothing about the edge.

Q: Win rate 50%, 100 trades. Roughly how long is the longest losing streak you should expect?
= 7 ±1
WHY: log(100) ÷ log(2) ≈ 6.6, so about seven in a row at some point.

Q: You have lost six trades in a row with a strategy that wins half the time. What does that tell you?
+ Little: six in a row is within what chance delivers
- The edge is gone and the strategy should be dropped
- The next trade is more likely to win, to even things out
WHY: Six is below the expected longest streak in a hundred trades. The coin has no memory either way.

### From streak to drawdown
Risk 2% a trade and a seven-trade streak takes about 13%, and streaks come with scattered losses around them, so the real drawdown runs deeper. A rough guide: expected worst drawdown ≈ two to three times the longest streak's loss.

Q: You risk 2% a trade. The longest expected losing streak is seven. Roughly what drawdown should you plan for, in percent?
= 30 ±6
WHY: Seven losses at 2% is about 13%; two to three times that for the losses around the streak gives 26% to 40%.

[test stop]

### Size backwards from the pain
Decide the drawdown you could sit through, then set the risk per trade so chance alone cannot exceed it. If 15% is your limit and the guide says the worst drawdown is about fifteen times the risk per trade, the risk per trade is 1%.

Q: You could live with a 15% drawdown. Your planning guide says the worst drawdown is about fifteen times the risk per trade. What risk per trade follows, in percent?
= 1 ±0.1
WHY: 15% ÷ 15 = 1% a trade.

The same arithmetic in reverse says what doubling the size does to the pain.

Q: Two traders have the same edge. One risks 1% a trade, the other 4%. Who sees the deeper drawdown?
+ The 4% trader, about four times as deep
- Both the same, since the edge is the same
- The 1% trader, because small positions lose more often
WHY: Drawdowns scale with risk per trade. The edge sets the direction; the size sets the depth.

HERE: The Leaders page shows each player's worst drawdown. Compare yours with the risk you take per trade: the ratio is the guide this lesson is about.

## Risk of ruin, with a number {ruin-probability} [6]
SUMMARY: Put a number on the chance of losing an unacceptable share of the account before the edge has time to work, and see how size and edge move it.

### The gambler's formula
For even-money bets with an edge e (win rate minus loss rate) and capital of N units of risk, the chance of losing everything before doubling is about **((1 − e) ÷ (1 + e))^N**. The edge helps, but the number of units matters more.

Q: Edge 10% (win rate 55%), capital of 20 risk units. Roughly what is the risk of ruin, in percent?
= 1.8 ±0.4
WHY: (0.9 ÷ 1.1)^20 = 0.818^20 ≈ 0.018, about 1.8%.

Q: Same edge, but you risk 10% a trade, so the account is 10 units. What happens to the risk of ruin?
+ It rises to about 13%, from under 2%
- It halves, because fewer trades mean fewer chances to lose
- It stays the same, since the edge has not changed
WHY: 0.818^10 ≈ 0.134. Halving the units squares the odds of survival the wrong way.

### Ruin is a level you choose
Ruin need not be zero. Most traders set it at the drawdown that would make them stop or that a backer would pull the plug at, often 20% to 30%. Count your units against that level, not against the whole account.

Q: You will stop trading at a 25% drawdown and risk 1% a trade. How many units of risk stand between you and that stop?
= 25 ±1
WHY: 25% ÷ 1% = 25 units before the level you have set.

[chart candle]

### The two levers
Edge and units are the only levers. A bigger edge takes years of work; more units takes one decision about size. That is why size, not setup, decides who is still trading in five years.

Q: Which change lowers the risk of ruin most for the least effort?
+ Risking less per trade, which adds units at once
- Finding a strategy with a higher win rate, which needs years of work
- Trading more often to reach the long run faster
WHY: Units are set by a single decision today. The edge is slow to improve and never certain.

One lever people reach for is not a lever at all: trading more often.

Q: Trading more often with the same size and edge does what to the risk of ruin?
+ Nothing: the probability is about the path, not the clock
- Lowers it, because the long run arrives sooner and the edge shows through
- Raises it, because more trades mean more losses
WHY: The formula has no time in it. Frequency changes how fast you find out, not what you find.

WARN: The formula assumes independent bets of equal size. Correlated positions and doubled sizes after a loss make the real number worse than it says.

## Monte Carlo on your own trades {monte-carlo} [6]
SUMMARY: Reshuffle your trade history to see the range of outcomes it could have produced, read the percentiles, and know what the method cannot tell you.

### One history is one draw
Your equity curve is one ordering of your trades. Shuffle the same trades a thousand times and each ordering gives a different curve: same end point, different drawdowns on the way. **Monte Carlo** is that reshuffling, done many times, to see the spread.

Q: What does reshuffling the order of past trades change?
+ The path, including the worst drawdown, not the total
- The total return, which depends on the order in which the wins arrive
- Nothing: every ordering gives the same equity curve
WHY: Addition is order-free, so the end is fixed; drawdowns depend on which losses cluster.

### Reading the percentiles
Rank the thousand simulated worst drawdowns. The 95th percentile is the drawdown only one run in twenty exceeded. Plan for that one, not for the median.

Q: You run 1,000 reshuffles and sort the worst drawdowns from best to worst. Which run is the 95th percentile?
= 950 ±1
WHY: 95% of 1,000 runs sit below it: the 950th from the best.

Q: Your real history had a 12% worst drawdown. The 95th percentile of the reshuffles is 24%. What should you plan for?
+ About 24%: your history was one lucky ordering
- 12%: the real drawdown is the only one that happened
- 6%: the simulations average out the bad luck
WHY: The same trades could easily have arrived in a crueller order. The percentile is the honest planning figure.

[test trend]

### What it cannot tell you
Reshuffling assumes the trades are independent and the future draws from the same bag. It cannot show a loss bigger than any you have had, or a market that changes. It measures the luck in the ordering, nothing more.

Q: Your Monte Carlo shows no run worse than a 30% drawdown. What does that guarantee?
+ Nothing about the future: only that your past trades, reordered, stayed within 30%
- That a 30% drawdown is the most you can ever lose
- That the strategy will keep working in the next market regime, whatever it brings and however long it lasts
WHY: The method only shuffles what already happened. New kinds of loss are outside the bag.

The second blind spot is the shuffle itself, which treats every trade as unrelated to the one before.

Q: Which assumption does reshuffling make that real trading often breaks?
+ That each trade's result is independent of the last
- That every trade is exactly the same size in MB as every other
- That losses are always smaller than wins
WHY: Losing streaks in real trading often share a cause, such as one regime. Shuffling breaks that link.

HERE: The History page downloads every trade as a file. Reshuffle the results in a spreadsheet, or let a bot's backtest report do it, before you size up.

## Correlation: five risks or one {portfolio-risk} [5]
SUMMARY: Add up the risk of several positions properly, see how correlation turns separate stops into one, and size the book rather than the trade.

### Risks do not simply add
Two positions each risking 1%: if they move together, the risk is 2%. If they move independently, the combined risk is about √2 ≈ 1.41%. Correlation decides where between those two numbers you are, and in a sell-off the answer drifts towards 2%.

Q: Two positions each risk 1% of the account and their returns are uncorrelated. Roughly what is the combined risk, in percent?
= 1.41 ±0.05
WHY: √(1² + 1²) = √2 ≈ 1.41%.

Q: Five bank stocks, each risking 1%. In a sector sell-off, what is the real risk?
+ About 5%: the stops will be hit together
- About 2.2%, the square root of five
- About 1%, because diversification across five names removes the rest
WHY: Same sector, same shock. Correlation near one means the risks add in full.

### Correlation rises when it hurts
In calm markets stocks go their own way. In a panic they fall together, and the diversification you counted on disappears. Measure correlation in the bad months, not the average month.

Q: Your portfolio's correlations were low all year, then every position fell on the same day. What happened?
+ Correlations rose in the sell-off, as they usually do
- The market made an error that will be corrected in the next session
- Your positions were secretly the same stock
WHY: Correlation is not constant. It rises exactly when the protection it offered is needed.

[test level]

### Size the book, not the trade
Set a limit on the total risk open at once, with correlated positions counted as one. Many traders cap open risk at 5% or 6% of the account, and sector exposure at a share of that.

Q: Your rule caps open risk at 6%. You risk 1% a trade and treat correlated names as one position. You hold three technology stocks and two unrelated ones. How many positions does the rule count?
= 3 ±0
WHY: The three technology stocks count as one, plus two others: three positions, 3% of open risk.

A stop protects a trade. Only a cap on open risk protects the account.

Q: Why set a cap on total open risk at all, if each trade has a stop?
+ Because many stops can be hit on the same day
- Because stops expire when more than one position is open
- Because brokers charge more for several open positions
WHY: Each stop limits one trade. The book's loss on a bad day is the sum of the stops that fire together.

HERE: The Holdings page lists every open position and its stop. Add the risks up by sector before the next entry: that total is the number this lesson is about.
