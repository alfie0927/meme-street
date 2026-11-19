# Probability for traders {probability}
The maths under every trading decision: what a bet is worth, how evidence should change your mind, how wide the spread of outcomes is, how to fit a line and not fool yourself with it, and how a market maker sets a price. The Quant research unit builds on it. Advanced.
TIER: pro

## What a bet is worth {fair-price} [6]
SUMMARY: Work out the fair price of an uncertain payoff, use it to decide whether to stay in a trade, and add up the value of several bets at once.

### The weighted average
The **expected value** of a bet is each outcome times its chance, added up. A die that pays its roll in MB is worth (1 + 2 + 3 + 4 + 5 + 6) ÷ 6 = 3.5 MB a go, though no single roll ever pays 3.5. Expected value is what the bet averages over many tries.

Q: A die pays its roll in MB. What is a fair price for one roll, in MB?
= 3.5 ±0.01
WHY: Each face comes up one time in six: 21 ÷ 6 = 3.5.

Q: A trade has a 40% chance of making 3,000 MB and a 60% chance of losing 1,500 MB. What is its expected value, in MB?
= 300 ±1
WHY: 0.4 × 3,000 − 0.6 × 1,500 = 1,200 − 900 = 300.

### The re-roll game
Now you may roll once more, keeping the second roll. A second roll is worth 3.5, so you re-roll 1, 2 or 3 and keep 4, 5 or 6. The game is worth **4.25 MB**. Charge 1 MB for the re-roll and it is worth 2.5, so you re-roll only 1 or 2, and the game is worth 23/6, about 3.83 MB.

Q: In the re-roll game with no fee, what is the game worth, in MB?
= 4.25 ±0.01
WHY: Half the time you re-roll and expect 3.5. The other half you keep 4, 5 or 6: (4 + 5 + 6) ÷ 6 = 2.5. Total 1.75 + 2.5 = 4.25.

Q: A second roll costs 1 MB and your first roll is a 3. What should you do?
- Roll again, since 3 is below the die's average of 3.5
+ Keep the 3, since a paid re-roll is worth only 2.5
- Roll again, since the fee is small next to the possible 6
WHY: A re-roll averages 3.5 and costs 1, so it is worth 2.5. A 3 in hand beats it.

### Hold or exit
The re-roll is the logic of every open trade. What you have is the trade closed now. What you would get is the expected value of staying, less the costs of staying. Stay only while the second beats the first. Your entry price is not in the sum.

Q: Which question decides whether to stay in an open trade?
- Is the price still above where you bought it?
+ Does what you expect from staying, after costs, beat closing now?
- Have you held it for as long as you first planned?
WHY: The entry price is history. The choice is between two futures: closed now, or held on with its expected value and costs.

### Linearity
Expected values add: the expected value of a sum is the sum of the expected values. This holds even when the bets move together. Their risk does not add this simply, as the lesson on the spread of outcomes shows.

Q: Three open positions have expected values of +200 MB, −50 MB and +120 MB, and two of them move together. What is the expected value of all three, in MB?
= 270 ±1
WHY: 200 − 50 + 120 = 270. Expected values add whether or not the bets are linked.

HERE: Meme Street prices an option at what it is expected to pay at expiry, with no discounting because MB cash earns no interest. A premium and a spread are added on top, so buying options at random loses on average.

## Base rates and new evidence {base-rates} [6]
SUMMARY: Combine how common something is with how good the evidence is, and see why a signal that is "right 80% of the time" is usually wrong about rare moves.

### The witness
In a town, 15% of cabs are blue and 85% green. A witness, right 80% of the time about colour, says the cab in an accident was blue. Most people answer 80%. Count instead: out of 100 cabs, 12 are blue and called blue, and 17 are green and wrongly called blue. Of the 29 called blue, 12 are: about **41%**.

Q: In the cab example, what is the chance the cab was really blue, in percent?
= 41 ±1
WHY: 0.8 × 0.15 = 0.12 called blue rightly; 0.2 × 0.85 = 0.17 wrongly. 0.12 ÷ 0.29 = 0.41.

TIP: The cab problem is from Tversky and Kahneman, "Evidential impact of base rates", 1982.

### The rule behind it
This is **Bayes' rule**. Start from the **base rate**, how common the thing is before any evidence (the prior). Multiply by how often the evidence shows up when it is true. Divide by how often the evidence shows up at all, true or not. Rare things stay unlikely even after good evidence.

Q: Why is the answer 41% and not 80%?
+ Green cabs are so common that their mistakes outnumber the blue hits
- The witness is less reliable at night than in a test
- Bayes' rule always halves the reliability of a witness
WHY: 20% of a big group (17 cabs) beats 80% of a small one (12 cabs).

### A signal on a rare move
Big moves of 10% come on 2% of days. A signal fires before 80% of them, and also on 10% of ordinary days. When it fires, the chance of a big move is 0.016 ÷ (0.016 + 0.098), about **14%**. "Right 80% of the time" was about the big days, not about the signal's alarms.

Q: Using those numbers, when the signal fires, what is the chance a big move follows, in percent?
= 14 ±1
WHY: 0.8 × 0.02 = 0.016 true alarms; 0.1 × 0.98 = 0.098 false ones. 0.016 ÷ 0.114 = 0.14.

### Streaks and skill
Of 1,000 traders, one always wins and 999 flip coins. One of them wins 10 in a row. A coin flipper does that one time in 1,024, so 999 flippers produce about 0.98 such streaks against the skilled trader's one. The chance this streak is skill is 1,024 ÷ 2,023, about **51%**.

Q: Of 1,000 traders, one always wins and the rest flip coins. A trader wins 10 in a row. How likely is it skill?
- About 99.9%, since 10 coin wins in a row is a 1-in-1,024 event
+ About 51%, since 999 coin flippers make about one such streak
- About 0.1%, since only 1 trader in 1,000 has any skill
WHY: 1 ÷ (1 + 999 ÷ 1,024) = 1,024 ÷ 2,023 = 0.506.

### The prior matters
Make the skilled traders 1 in 100 instead and the same streak says skill about 91% of the time. The evidence did not change, only the base rate. Ask how common real edges are before you judge one streak.

Q: One trader in 100 always wins and the rest flip coins. A trader wins 10 in a row. How likely is it skill, in percent?
= 91 ±1
WHY: 1,024 ÷ (1,024 + 99) = 0.91.

HERE: The option chain's **Chance ITM** column gives each strike's chance of finishing in the money. Treat it as the base rate, and ask how strong your evidence is before you bet against it.

## The spread of outcomes {spread-of-outcomes} [6]
SUMMARY: Measure how far results scatter with the variance and standard deviation, and scale them by position size, number of bets and time.

### Variance and standard deviation
The **variance** is the average squared distance of the outcomes from their mean. Its square root, the **standard deviation**, is in the same units as the outcome, here MB. A trade that makes or loses 1,000 MB with equal chance has a standard deviation of 1,000 MB.

### Size scales it
Multiply a bet by a and the variance grows by a², so the standard deviation grows by a. Double the position, double the standard deviation. Adding a fixed amount, such as a fee, moves the mean and leaves the spread alone: the variance of aX + b is a² times the variance of X, with no b in it.

Q: A position's result has a standard deviation of 800 MB. You triple its size. What is the new standard deviation, in MB?
= 2400 ±1
WHY: The standard deviation scales with the size: 3 × 800 = 2,400. The variance grows 9 times.

### Many independent bets
Variances of independent bets add. So n bets, each with standard deviation σ, have a total standard deviation of σ × √n, and their average has σ ÷ √n. A hundred trades of 500 MB each spread 5,000 MB in total, and their average trade spreads 50 MB.

Q: You make 25 independent trades, each with a standard deviation of 400 MB. What is the standard deviation of the total, in MB?
= 2000 ±1
WHY: 400 × √25 = 400 × 5 = 2,000.

### Over time
If days are independent, daily returns add up in the same way, so volatility grows with the square root of time. Real markets usually count **252 trading days** a year: a stock that moves 1.5% on a typical day has a yearly volatility of about 1.5 × √252 = 23.8%.

Q: A stock's daily standard deviation is 1.5%. Using 252 trading days, what is its yearly volatility, in percent?
= 23.8 ±0.2
WHY: √252 = 15.87, and 1.5 × 15.87 = 23.8.

### Differences and correlation
The gap between two independent things has variance 2σ², so a standard deviation of σ × √2. All of these rules need the bets to be **uncorrelated**. The full sum is Var(X + Y) = Var(X) + Var(Y) + 2 Cov(X, Y). When bets move together, the covariance is added on and the √n saving disappears.

Q: Two unrelated stocks each move 2% on a typical day. What is the standard deviation of the gap between their daily returns, in percent?
= 2.83 ±0.03
WHY: 2 × √2 = 2.83. Variances add for a difference too.

Q: You hold 25 equal positions that all move as one. How does the standard deviation of the total compare with one position's?
+ About 25 times, because covariance takes away the square-root saving
- About 5 times, the square root of 25 positions
- The same, because the positions spread the risk out
WHY: Perfectly correlated bets add like one big bet: 25 × σ. The √25 rule needs independence.

HERE: A stock's page shows its volatility a year. Meme Street's game year is 365 game days, so divide by √365 for a game day: NVXA at 42% a year moves about 2.2% a game day. That figure is the noise alone; trends and news make real moves larger.

## Ranges with confidence {ranges-confidence} [6]
SUMMARY: Turn a mean and a standard deviation into a range with a stated chance, read a confidence interval correctly, and check whether your own ranges are honest.

### The bell curve
On a **normal** (bell) curve about 68% of outcomes fall within one standard deviation of the mean, 95% within two and 99.7% within three. To cover a chosen share, multiply by a **z** value: ±0.674 for 50%, ±1.645 for 90%, ±1.96 for 95%. Real returns have fatter tails than this, as a later lesson shows.

Q: A price of 100 MB has a daily standard deviation of 2 MB. On a bell curve, what is the top of the 90% range for tomorrow, in MB?
= 103.29 ±0.05
WHY: 100 + 1.645 × 2 = 103.29.

### Counting wins
A count of wins in n independent tries at chance p has mean n × p and standard deviation √(n × p × (1 − p)). A team with an even chance in each of 162 games expects 81 wins, give or take 6.36. Its 50% range is about 76.7 to 85.3, its 90% range about 70.5 to 91.5.

Q: A rule wins half its trades. Over 162 trades, what is the standard deviation of its number of wins?
= 6.36 ±0.05
WHY: √(162 × 0.5 × 0.5) = √40.5 = 6.36.

Q: Using that standard deviation, what is the top of the 90% range for the number of wins?
= 91.5 ±0.2
WHY: 81 + 1.645 × 6.36 = 91.5.

### What 95% means
A **95% confidence interval** comes from a method that, used again and again, captures the true value 95% of the time. Any one interval either holds the true value or does not. The 95% describes the method, not the chance for a single interval.

Q: A study reports a 95% confidence interval for a rule's average trade. Which reading is correct?
- There is a 95% chance this particular interval holds the true average
+ Intervals made this way hold the true average 95% of the time
- 95% of the rule's trades will land inside the interval
WHY: The true value is fixed. The 95% is the hit rate of the method that drew the interval.

### Calibration
If you give 90% ranges, about one in ten should miss. Many more misses and you are overconfident; none at all and your ranges are too wide. Keep a tally of your forecasts and check it.

Q: You give 20 ranges, each meant to be 90% sure. How many should miss?
= 2 ±0.1
WHY: 10% of 20 is 2. Eight misses would mean your ranges are far too narrow.

### Useful as well as right
A range of 0 to 1,000 MB for tomorrow's price never misses and tells you nothing. The skill is a range that is honest and as narrow as your knowledge allows.

Q: Which forecast is most useful?
- A price between 0 and 1,000 MB, which is never wrong
+ A 90% range of 96.7 to 103.3 MB that misses one time in ten
- A single price of 100 MB, stated as certain
WHY: A calibrated range is narrow enough to act on and honest about how often it misses.

HERE: A stock's **Options** tab shows the move the options expect by expiry, ± one standard deviation. On a bell curve the price would end inside it about two times in three; fat tails make the big misses come more often.

## Fitting a line {regression-line} [6]
SUMMARY: Fit the least-squares line, see that a stock's beta is its slope, read R squared, and know when a slope is evidence.

### Least squares
A straight line through a cloud of points is fitted by **least squares**: it makes the sum of the squared vertical misses as small as possible. Its slope is the **covariance** of X and Y divided by the **variance** of X. Equivalently, slope = correlation × (standard deviation of Y ÷ standard deviation of X).

Q: A stock's daily returns have a covariance of 3 with the market's, and the market's variance is 2 (both in %²). What is the slope of the stock on the market?
= 1.5 ±0.01
WHY: 3 ÷ 2 = 1.5.

### Beta is a slope
Put the market's returns on X and a stock's on Y, and the slope is the stock's **beta**. A correlation of 0.6 with a stock spread of 3% and a market spread of 1.5% gives a beta of 0.6 × 3 ÷ 1.5 = 1.2.

Q: Correlation 0.8, stock standard deviation 2.5%, market standard deviation 1%. What is the beta?
= 2 ±0.01
WHY: 0.8 × 2.5 ÷ 1 = 2.

### The two lines
Regressing Y on X and X on Y gives two different lines. The first minimises vertical misses, the second horizontal ones, and their slopes are not each other's reciprocal. Their product is the correlation squared. Only a perfect correlation makes the two lines one.

Q: The stock-on-market slope is 1.2 and the correlation is 0.6. What is the slope of the market on the stock?
= 0.3 ±0.01
WHY: The product of the two slopes is 0.6² = 0.36, so 0.36 ÷ 1.2 = 0.3, not 1 ÷ 1.2.

### R squared
**R squared** is the share of Y's variance the line explains. With one input it is the correlation squared. A correlation of 0.6 explains 36% of the stock's day-to-day variance; the other 64% is the stock's own.

Q: A stock's correlation with the market is 0.6. What share of its variance does the market explain?
- 60%, the correlation itself
+ 36%, the correlation squared
- 64%, one minus the correlation squared
WHY: R squared is r²: 0.6² = 0.36. The remaining 64% is not explained by the market.

### When a slope counts
A fitted slope has a **standard error**. Divide the slope by it for a t-statistic, which the Quant research unit explains in full. Under about 2, chance could have drawn the line.

Q: A slope of 0.8 comes with a standard error of 0.5. What is the honest reading?
+ Weak evidence: t is only 1.6
- Strong evidence, since the slope is clearly above zero
- No relationship at all, since 0.8 is below 1
WHY: 0.8 ÷ 0.5 = 1.6, under the usual bar of about 2.

HERE: A stock's page shows its **beta to the market**. Fit your own slope to a few days of its candles and it will scatter around that figure: a short sample gives a noisy slope.

## Simple models, complex models {bias-variance} [6]
SUMMARY: See why a model can be wrong by being too simple or too flexible, why a perfect fit to the past is a warning, and how shrinking helps.

### Two ways to be wrong
A model's error on new data comes from three parts: **bias**, being wrong the same way every time because the model is too simple; **variance**, changing with every new sample because it is too flexible; and noise no model can remove. Lowering one usually raises the other.

Q: A rule uses only "buy when the price is above its 200-candle average" and misses every turn. Which error is that?
+ Bias: the model is too simple to follow the turns
- Variance: the model changes with every new sample
- Noise: no model could have seen these turns
WHY: A simple rule that is wrong in the same way every time has high bias.

### The memoriser
The most flexible model predicts each new case from the single most similar past case (one **nearest neighbour**). On the past it is perfect, because every past case is its own nearest neighbour. On new data it copies whatever noise came with that one case.

Q: "Find the past day most like today and trade what followed it." On the days it was built from, how often is it right, in percent?
= 100 ±0.1
WHY: Each past day is its own closest match, so it repeats what happened. A perfect past fit says nothing about the future.

Q: The same rule is tested on new days. What is the likely result?
- About as good as on the past, since the past days were real
+ Much worse, since one past day is mostly noise
- Better than on the past, since it has more days to compare
WHY: One case carries its own luck. A rule that copies single cases has high variance.

### More inputs than evidence
A line through 2 points fits them exactly. A curve with 12 adjustable numbers can pass through 12 monthly returns exactly. When the settings are as many as the cases, the fit is guaranteed and means nothing. The Backtesting lesson shows this in a rule; this is why it happens.

Q: How many adjustable numbers does a curve need to pass exactly through 12 monthly returns?
= 12 ±0.1
WHY: One number per point lets the curve hit each one, noise and all.

### Shrinking
The cure is to accept a little bias for much less variance. **Ridge** regression multiplies every coefficient by the same factor below 1. **Lasso** moves each one towards zero by a fixed amount, setting the small ones to exactly zero.

Q: Lasso moves every coefficient 0.2 towards zero and stops at zero. What do 0.5, 0.15 and −0.3 become?
+ 0.3, 0 and −0.1
- 0.4, 0.12 and −0.24
- 0.3, −0.05 and −0.5
WHY: 0.5 − 0.2 = 0.3; 0.15 would cross zero, so it stops at 0; −0.3 moves up to −0.1.

HERE: With the Expert pass, the Bots page backtests a rule on the game's candles. A rule with few settings that does well is worth more than one with many that does a little better.

## Cause or coincidence {cause-or-coincidence} [6]
SUMMARY: Tell a cause from a correlation: the third variable, selection bias, reverse cause, and why a random comparison settles it.

### Three ways to be fooled
When two things move together, one may cause the other. Or a **third variable** may drive both. Or the cause may run the other way. Or it may be chance. A correlation cannot tell these apart.

Q: Stocks with the most news stories this week rose the most. Which explanation fits a cause running the other way?
- The news stories made buyers rush in and lift the prices
+ The rises drew the news coverage
- A strong market lifted both the prices and the coverage
WHY: A big move is itself news. The arrow can point from price to story.

### The market is the third variable
A signal fires on 40 stocks in a week when the market rises 5%. The stocks rise 7% on average. With an average beta of 1.2, the market alone explains 1.2 × 5 = 6%. The signal's own share is about 1 point, and it may be luck.

Q: In that week, how many percentage points of the 7% rise are left for the signal?
= 1 ±0.05
WHY: 7 − 1.2 × 5 = 7 − 6 = 1.

Q: A rule bought only in a month when every stock rose. What does its 100% win rate show?
- The rule has a strong edge that will hold in every kind of market
- The rule is broken, since nothing wins every trade
+ Nothing about the rule yet: the market won those trades
WHY: When every stock rose, any entry won. The market is the third variable.

### Selection bias
Traders who use stops make more than traders who do not. Stops may help, or the traders who choose stops may simply be the experienced ones. When people choose their own group, the groups differ in more than the thing studied.

Q: Why is "traders who use stops earn more" weak evidence that stops cause better results?
+ The traders who chose stops may differ in skill or experience
- Stops never change results, so the gap between the groups must be chance
- Traders who use stops trade fewer stocks than the rest
WHY: Self-chosen groups carry their differences with them. That is selection bias.

### The random comparison
A **randomised trial** lets chance decide who gets the treatment, so third variables, known and unknown, spread evenly across both groups. A trader can copy it: compare the signal's entries with random entries on the same stocks over the same hours.

Q: How do you check that a signal adds something beyond the market?
- Count how many of its trades made money during the last rising month
+ Compare it with random entries on the same stocks and hours
- Test it again on the stocks that rose the most
WHY: Random entries face the same market. Only the signal's own effect is left in the difference.

HERE: Stocks on Meme Street move with the market through their beta, with their industry and on their own news. Set any signal's results beside the MSI 50 index over the same hours.

## Quoting a market {making-a-market} [6]
SUMMARY: Set a bid and an ask from a fair value, widen them with doubt, lean them when you hold a position, move them after each trade, and add up the result.

### Fair value and width
A **market maker** quotes a bid and an ask, written bid@ask: 76@86 means it buys at 76 and sells at 86. The middle is its estimate of fair value. The width reflects its doubt: tight on a die worth 3.5, wide on a number it can only guess.

Q: Your fair value for a contract is 81 and you must quote 10 wide. What is your bid?
= 76 ±0.01
WHY: Half the width either side: 81 − 5 = 76, so the quote is 76@86.

### Leaning on a position
A market maker wants to be flat. Holding a long position, it lowers both prices, so others buy from it more readily and sell to it less. With a fair value of 50 and a long position, 43@53 gives up some profit on a sale to shed the risk.

Q: Your fair value is 50 and you are short. Which quote leans the right way?
+ 47@57, raised so others sell to you more readily
- 43@53, lowered so others buy from you more readily
- 45@55, the same either side whatever you hold
WHY: Short, you want to buy. Raising the bid invites sellers, and raising the ask slows further buying from you.

### Who is trading with you
Someone who buys at your ask may know more than you. That risk, **adverse selection**, is why quotes move after every trade: a buy at your ask is evidence that fair value is higher, so both prices go up.

Q: Someone buys at your ask of 86. What should your next quote do?
- Stay at 76@86, since one trade proves nothing
+ Move up, since the buyer may know the value is higher
- Move down, to win the next trade back from the buyer
WHY: The trade is information. Leaving the quote invites the same informed buyer again.

### Adding it up
On a contract paying one MB per win in a 162-game season, the quotes and trades ran like this. Pair each sale with a purchase: sold 86 and bought 85 makes 1; sold 93 and bought 84 makes 9. The sale at 91 is still open.

| Your quote | They | You |
| 76@86 | buy | sell at 86 |
| 81@91 | buy | sell at 91 |
| 85@95 | sell | buy at 85 |
| 83@93 | buy | sell at 93 |
| 84@94 | sell | buy at 84 |

Q: What is the profit on the paired trades, in MB?
= 10 ±0.01
WHY: (86 − 85) + (93 − 84) = 1 + 9 = 10, and you are short one at 91.

Q: The season ends at 90 wins. What is your total result, in MB?
= 11 ±0.01
WHY: The short at 91 settles at 90 and makes 1, on top of the 10.

Q: Above how many wins does the whole game lose money?
= 101 ±0.01
WHY: The total is 10 + (91 − wins) = 101 − wins, which is negative above 101.

HERE: Shares on Meme Street have no spread: one price and a 0.1% fee. Options do: the chain quotes a bid and an ask about 6% of the contract's value apart. You can buy and sell back, but you cannot quote your own.
