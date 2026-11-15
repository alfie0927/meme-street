# Quant research {quant}
How professionals test a trading idea, and what decades of published tests found: luck against skill, why most discovered edges are false, which ones lasted, how fast they fade, and why wild days come far more often than they should. Advanced.
TIER: pro

## How a quant thinks {quant-method} [6]
SUMMARY: Turn a trading idea into a claim, a test and a number, and ask the question that matters: could luck have done this?

### A claim you can test
A quant never asks whether a rule "works". The claim is made exact first: buy on this signal, sell on that one, on these stocks, after fees. Then the rule is run over many trades and one number is read: the **average trade**.

Q: Which of these is a claim a test can settle?
- Oversold stocks tend to bounce back sooner or later, given time
+ Buying a close under RSI 30 made money after fees
- Good traders can feel when a stock is about to turn
WHY: Only that one names an entry and a result that can be counted.

### Could luck do this?
Every result is set against what chance alone produces. The yardstick is the **standard error**: the spread of the trades divided by the square root of how many there are. An average of 0.5% from 100 trades that spread 4% each has a standard error of 0.4%.

Q: A rule's trades spread 4% each and there are 100 of them. What is the standard error of the average trade, in percent?
= 0.4 ±0.01
WHY: 4 ÷ √100 = 4 ÷ 10 = 0.4.

### The t-statistic
Divide the average by its standard error and you have the **t-statistic**: how many standard errors the result sits from zero. That 0.5% average is 1.25 standard errors from nothing. Under 2, luck is a fair explanation. The same 0.5% over 400 trades has a t-statistic of 2.5.

Q: An average trade of 0.3% comes with a standard error of 0.3%. What is the t-statistic?
= 1 ±0.01
WHY: 0.3 ÷ 0.3 = 1: one standard error from zero, which chance produces all the time.

Q: Two rules both average 1% a trade with the same spread. One has 25 trades, the other 100. Which result is stronger?
+ The one with 100 trades: its t is twice as high
- The one with 25 trades, because it found the edge faster
- Neither: the same average means the same evidence
WHY: Four times the trades halves the standard error, so the t-statistic doubles: 2 against 1.

### What a test cannot say
A high t-statistic says the past result was unlikely to be luck. It does not say the rule will keep working, and it says nothing at all if you tried many rules and kept the best one. That trap is the next lesson.

Q: A rule shows a t-statistic of 2.4 on last year's candles. What has been shown?
+ The past result is hard to put down to luck alone
- The rule will go on making money through next year
- The rule is safe to trade at full size from today
WHY: A t-statistic measures the past sample. The future, and the size to trade, are separate questions.

HERE: With the Expert pass, the Bots page backtests a rule on the game's candles and compares it with simply holding the stock. Count the trades behind an average before you believe it.

## Fooled by a hundred tests {multiple-testing} [6]
SUMMARY: See why the best of many tested rules looks good by luck alone, and raise the bar for every extra rule you try.

### One test in twenty
A result two standard errors from zero is called significant because luck produces it only about one time in twenty. That protection holds for **one** test. Try 20 useless rules, and the chance that at least one of them clears the bar is 64%.

Q: You test 20 rules that have no edge at all, each against a one-in-twenty bar. How likely is it that at least one passes, in percent?
= 64 ±1
WHY: 1 − 0.95 multiplied by itself 20 times = 0.64. More tests, more lucky passes.

### The best of many
Pick the best of 10 useless rules and it sits, on average, 1.5 standard errors above zero. The best of 100 sits at 2.5, and the best of 1,000 at 3.2. Nothing in those numbers is skill. The winner of a big search always looks like a discovery.

Q: A researcher tries 1,000 rules and reports only the best, which has a t-statistic of 3. What should you make of it?
+ About what the best of 1,000 useless rules shows by luck
- Strong evidence, because a t-statistic of 3 is very rare indeed
- Proof the rule works, since it beat 999 others
WHY: The best of 1,000 rules with no edge averages a t-statistic of about 3.2. This one is no better than chance.

### Raise the bar
The fix is to count your tries and ask more of the winner. One rule tested once may pass at a t-statistic of 2. The best of a hundred needs well over 2.5 before it means anything, and its result on fresh data matters most of all.

Q: Which result deserves the most trust?
- The best of 500 settings, with a t-statistic of 2.6
+ One rule fixed before testing, with a t of 2.6
- The best of 50 rules, with a t-statistic of 2.6
WHY: The same t-statistic means less every time it is the pick of a larger search.

Q: You tested 14 versions of a rule before one passed. What must the write-up include?
+ That 14 were tried, so the pass can be judged against that
- Only the winning rule, to keep the report short and clear for readers
- The winner and the two runners-up, as a fair sample
WHY: With 14 tries the chance of at least one lucky pass is already 51%. The number of tries is part of the result.

### The same trap at home
Moving a stop from 2% to 3%, then the average from 20 candles to 30, then the hours you trade, is running many tests. Each tweak that "improves" last month is a pick from a search, and the search is rarely counted.

Q: After a losing month you adjust three settings until that month would have been a winner. What have you done?
- Fixed the strategy, since it now passes on real data from last month
+ Run a search and kept its luckiest outcome
- Proved the old settings were the only problem
WHY: The month was used to choose the settings, so it can no longer test them.

HERE: A backtest on the Bots page shows one version of a rule at a time. Keep your own count of the versions you tried before the one you like.

## How many trades before it means anything {sample-size} [6]
SUMMARY: Put an error bar on a win rate, and work out how many trades it takes to tell an edge from a coin.

### A coin wins streaks too
Flip a fair coin 20 times and it lands 12 or more heads one time in four. Give 100 traders a coin and ten trades each, and about five of them will win 8 or more. A short winning record is what luck looks like.

Q: A fair coin is flipped 20 times. How often does it show 12 or more heads, in percent?
= 25 ±1
WHY: Adding up the chances of 12, 13 and so on up to 20 heads gives 25.2%.

Q: One hundred traders flip a coin for ten trades each. About how many win 8 or more?
- None: 8 wins out of 10 takes skill
+ About five of them
- About thirty of them
WHY: The chance of 8 or more wins in 10 fair flips is 5.5%, so around five traders in a hundred manage it.

### The error bar on a win rate
A win rate near 50%, measured over n trades, has a standard error of about **50 ÷ √n** percentage points. After 100 trades that is 5 points, so a measured 55% could easily be a true 50%. After 400 trades it is 2.5 points.

Q: You have 400 trades with a win rate near 50%. What is the standard error of that win rate, in percentage points?
= 2.5 ±0.1
WHY: 50 ÷ √400 = 50 ÷ 20 = 2.5.

### How many trades
To tell a 55% win rate from a coin, the gap of 5 points should be at least two standard errors. That needs a standard error of 2.5 points: **400 trades**. A smaller edge needs far more: 52% against 50% takes 2,500.

Q: A trader shows 30 trades with a 60% win rate, wins and losses the same size. What is the honest reading?
+ Too few trades to tell it from a coin
- A proven edge of ten points over a coin flip
- A losing system, since 60% is under break-even here
WHY: 50 ÷ √30 is about 9 points, so 60% is barely one standard error above a coin.

### What to do with a small sample
Keep the size small until the trades are in. Judge the process, never the last ten results. And count every trade: leaving out the "mistakes" turns a record into a story.

Q: Your new setup has won 7 of its first 10 trades. What is the sound next step?
- Double the size while it is working
+ Keep trading it small and keep counting
- Stop: it will now lose to even things out
WHY: A coin wins 7 or more of 10 about one time in six. Ten trades say little, and past flips do not make losses due.

[mine]

HERE: Your win rate and the number of trades behind it are on the Your trading card on the Learn page. Divide 50 by the square root of that number before you trust the rate.

## The factor zoo {factor-zoo} [6]
SUMMARY: Know the handful of stock-picking factors research keeps finding, and why hundreds of published "discoveries" are probably false.

### What a factor is
A **factor** is a measurable trait that has gone with higher returns across many stocks: cheapness (value), small size, recent strength (momentum), steady profits (quality), calm prices (low volatility). Quants rank every stock on the trait, buy the top and sell the bottom.

Q: A quant ranks 500 stocks by their return over the past year, buys the top fifth and sells the bottom fifth. Which factor is this?
- Value: buying what is cheap
+ Momentum: buying recent strength
- Low volatility: buying calm prices
WHY: Ranking on past return and buying the winners is the momentum factor.

### Hundreds of discoveries
By 2016 researchers had published hundreds of factors, each with a test that passed the usual bar of a t-statistic above 2. A review of that work argued the bar was far too low: with so many people testing so many traits, lucky passes were certain.

Q: Why does a t-statistic of 2 mean less for a newly published factor than it did for the first ones?
+ Hundreds of traits were tested, so lucky passes pile up
- Later researchers used smaller samples of stocks and years
- Markets were less random in the early studies
WHY: It is the many-tests trap at the scale of a whole profession: every tested trait is another try.

### A higher hurdle
The review's answer: a newly found factor should clear a t-statistic above **3.0**, not 2.0. Its authors went further and argued that most claimed research findings in financial economics are likely false.

Q: A new factor is published with a t-statistic of 2.3. By the higher hurdle, how should it be treated?
- As established, since it passed the usual bar of 2
+ As unproven until it holds on new data
- As disproved, since it failed 3
WHY: Under the higher hurdle a result is not shown to be false. It is simply not yet evidence.

Q: A factor's average return is 0.6% a month with a standard error of 0.2%. What is its t-statistic?
= 3 ±0.01
WHY: 0.6 ÷ 0.2 = 3: right at the higher hurdle.

TIP: The review is Harvey, Liu and Zhu, "... and the Cross-Section of Expected Returns", Review of Financial Studies, 2016.

### What survives
The few factors still standing share three things: a t-statistic far above the hurdle, the same result in other countries and other decades, and a reason to exist, such as a risk investors are paid to bear or a mistake they keep making.

Q: Which factor is most likely to be real?
- One that worked in a single country for ten years
+ One found in many countries and decades
- One with the highest return in its original test
WHY: Breadth across markets and time is what separates a factor from a fluke.

HERE: Meme Street's market is checked so that simple tricks, like buying every dip, do not beat holding it. What you practise here is the habit of testing, not a factor.

## Momentum, the stubborn one {momentum-factor} [6]
SUMMARY: Understand the best-documented edge in stock research, how long it lasts, and the way it fails.

### Winners keep winning, for a while
In 1993 a study ranked US stocks by their return over the past 3 to 12 months, bought the winners and sold the losers. The strategy earned significant positive returns over holding periods of 3 to 12 months. It is the opposite of buying what has fallen.

Q: A momentum strategy, as first tested, does what?
+ Buys the past winners and sells the past losers
- Buys the past losers and waits for them to rebound
- Buys whatever rose most in the last hour
WHY: The ranking used returns over months, not hours, and it bought strength.

### It fades
The same study found that part of the extra return made in the first year dissipates over the following two years. Momentum is a drift that lasts months and then gives some back. It is no law that winners rise for ever.

Q: A stock has led the market for ten months. What does the research suggest about the next two years?
- The lead keeps growing at the same pace
+ Part of the gain is likely to be given back
- The stock becomes safer the longer it leads
WHY: The study found part of the first year's extra return dissipating in the two years after.

Q: A momentum portfolio beat the market by 12% in its first year. If a quarter of that is given back over the next two years, how many percentage points are returned?
= 3 ±0.1
WHY: A quarter of 12 is 3.

### Why it might exist
Two explanations compete. News may sink in slowly, so prices under-react at first and catch up over months. Or buyers chase what has risen and push it too far, which would explain the giving back. Both can be true at once.

Q: Good results come out and a stock rises 4% that day, then keeps drifting up for weeks. Which explanation fits?
+ Under-reaction: the news took time to be priced in
- Over-reaction: the first move was far too large
- Randomness: a drift after news cannot be told from noise
WHY: A move that carries on in the same direction is what slow digestion of news looks like.

### How it fails
Momentum's losses are rare, and they come in strings. Later research found them in panic states: after the market has fallen, while prices are wild, as the market rebounds. A stop and a sensible size matter more here than anywhere.

Q: When do momentum strategies tend to take their strings of losses?
- In long, steady uptrends with little news
+ When a fallen market rebounds
- In quiet markets with little news
WHY: The losses were found after market declines, in volatile times, as the market turned back up.

TIP: The studies are Jegadeesh and Titman, Journal of Finance, 1993, and Daniel and Moskowitz, "Momentum Crashes", Journal of Financial Economics, 2016.

HERE: Meme Street's stocks trend and reverse too. Trade strength with the stop already placed, and judge the idea over many trades.

## Edges fade {edge-decay} [6]
SUMMARY: See what happens to a trading edge after it is published, and why an edge everyone knows is worth less.

### Three measurements
A study took 97 published signals for picking stocks and measured each one three times: in the years its original paper tested, in the years after that sample ended, and in the years after the paper came out.

Q: Why measure a signal in the years after its test sample ended but before the paper was published?
+ It shows how much of the first result was luck
- It shows how many traders had read the paper
- It gives the signal more time to grow stronger before it is judged
WHY: Nobody could trade on an unpublished paper, so a drop in those years points to luck in the data, not to crowding.

### The numbers
Returns were **26% lower** out of sample, and **58% lower** after publication. The first drop is the share that was luck in the original test. The rest, about 32 points, is what traders took once the signal was public.

Q: A published signal earned 1% a month in its original test. By the study's averages, about what does it earn after publication, in percent a month?
= 0.42 ±0.02
WHY: 58% lower than 1% leaves 0.42%.

Q: Of the 58% decline, 26 points came before anyone could read the paper. What do the other 32 points measure?
- More luck hidden in the original sample of years
+ Traders using the signal once it was public
- Higher broker fees in the later years
WHY: The out-of-sample drop is the luck. The further drop after publication comes from people trading on it.

### A case: pairs trading
Buying one of two matched stocks and selling the other was a celebrated edge. For the top 20 pairs it earned 0.86% a month from 1962 to 1988, 0.37% a month from 1989 to 2002, and 0.24% a month from 2003 to 2009.

Q: Pairs trading earned 0.86% a month in its early decades and 0.24% in 2003 to 2009. By what percentage had the edge shrunk?
= 72 ±1
WHY: 1 − 0.24 ÷ 0.86 = 0.72.

### What it means for you
An edge you read about in a book, a video or a paper has already paid its discoverers. Expect less than half of what was reported, before costs, and test it on recent data only.

Q: A video shows a rule that made 2% a month in a famous ten-year-old study. What is a sensible expectation today?
- The full 2%, since the study was peer reviewed
+ Much less than 2%, perhaps nothing
- More than 2%, because more people now follow it
WHY: Published edges lose, on average, more than half their return, and popularity spends an edge.

TIP: The studies are McLean and Pontiff, Journal of Finance, 2016, and Do and Faff, Financial Analysts Journal, 2010.

HERE: Meme Street's market is checked against simple published tricks. A rule that looks good here over a few days has usually found luck: test it again next week.

## Fat tails and clusters {fat-tails} [6]
SUMMARY: Learn why extreme days come far more often than the bell curve says, why they arrive in bunches, and what that does to stops and size.

### The bell curve's promise
If daily moves followed a bell curve, a move beyond 3 standard deviations would come about once in a year and a half, one beyond 4 about once in 63 years, and one beyond 5 about once in 7,000 years.

Q: On a bell curve, about how often should a daily move beyond 4 standard deviations happen?
- About once a year
- About once in a decade or so
+ About once in 63 years
WHY: The chance is 0.006% a day: one trading day in about 15,800.

### What markets do
On 19 October 1987 the Dow Jones index of US stocks fell 22.6% in one day. With a usual daily move of about 1%, that is more than 20 standard deviations: a day the bell curve says should never come. Real returns have **fat tails**.

Q: A stock's usual daily move is 2%. Today it falls 14%. How many standard deviations is that?
= 7 ±0.1
WHY: 14 ÷ 2 = 7. On a bell curve that never happens. In markets it does.

Q: After a one-day fall of 22.6%, what gain is needed to get back to the starting price, in percent?
= 29.2 ±0.3
WHY: 1 ÷ (1 − 0.226) − 1 = 0.292. A fall always needs a bigger gain to undo it.

### They come in bunches
Big moves are followed by more big moves, up or down, and calm days by calm days. This is **volatility clustering**. Tomorrow's direction is hard to call, but its size is not: after a wild day, expect another.

Q: A stock that usually moves 1% a day has just moved 6%. What does clustering say about tomorrow?
- It will fall, to correct the jump
- It will be calm, since the news is already out
+ Another large move, in either direction
WHY: The size of moves clusters. The direction does not.

### What to do about it
A stop set in the calm weeks is too tight in a wild one, and a position sized for normal days is too big when the range doubles. Size from the recent range, and never treat the worst day you have seen as the worst there can be.

Q: After a week of unusually large candles, what keeps your risk the same?
+ A wider stop and a smaller position
- A tighter stop and a larger position, to catch the moves
- The usual stop and size, since wild weeks average out
WHY: When the range grows the stop needs more room, and the size must fall so the loss at the stop is unchanged.

HERE: News on Meme Street can move a stock by several of its usual candles at once. Place the stop when you place the trade, and size for the wild day.

## Random or real? {random-walk} [6]
SUMMARY: See how random numbers draw convincing charts, what is and is not predictable in prices, and how to use that when you read a chart.

### Charts from a coin
In 1959 a statistician built price charts from random numbers alone. They showed trends, tops and bottoms, and could not be told from real stock charts. A walk of 100 coin flips typically ends about 10 steps from where it began: enough to draw a trend.

Q: A chart drawn from coin flips shows a clean uptrend with two pullbacks. What does that prove about real uptrends?
- That real trends are always random and never worth trading
+ That a trend shape can appear with no cause
- That coin flips can forecast real prices
WHY: Random series produce shapes that look meaningful. It does not follow that every real shape is random.

Q: A coin walk typically ends about the square root of its number of steps away from the start. After 400 flips, about how many steps is that?
= 20 ±1
WHY: √400 = 20.

### What a random walk means
In a **random walk** each change is independent of the ones before: the next step cannot be forecast from the path so far. If prices were a pure random walk, no chart reading, indicator or backtest could have an edge, and the best forecast of tomorrow would be today.

Q: If a price follows a pure random walk, what is the best forecast of tomorrow's price?
+ Today's price
- A return towards last week's average
- A continuation of the latest trend
WHY: With independent steps the past path adds nothing, so the forecast is where the price stands now.

### Not quite random
Real prices are close to random, and not exactly. A well-known 1988 test rejected the pure random walk for weekly US stock returns. Momentum over months and the clustering of wild days are two of the departures. They are small, which is why edges are thin.

Q: What does "close to random, but not exactly" mean for a trader?
- Chart reading is useless and should be dropped
- Patterns work reliably if they look clear enough
+ Real edges exist, but they are small
WHY: Small departures from randomness leave thin edges: visible in a large sample, never in one trade.

### Reading a chart honestly
So a pattern is a hypothesis. Ask how often it led where you expect, over how many cases, and what the same test shows on a random series. One perfect example proves as much as one lucky coin flip.

Q: You find a pattern that was followed by a rise 9 times out of 10 on one stock last month. What is the right next step?
+ Count it over many stocks and months
- Trade it at full size while it is still working
- Discard it, since all patterns are random
WHY: Ten cases on one stock is a tiny sample, picked after the fact. The count over many cases is the evidence.

TIP: The chart experiment is Roberts, Journal of Finance, 1959. The test is Lo and MacKinlay, Review of Financial Studies, 1988.

HERE: Meme Street's prices follow the game's news and its price model, never the players' trades. A level or a pattern here holds often, not always: count your cases.

## Signal, noise and many small bets {breadth} [6]
SUMMARY: Learn why a small edge used many times beats a big edge used rarely, and what "independent" has to mean.

### Skill times the square root of breadth
A rule of thumb from portfolio research: the quality of a strategy's results grows with **skill per bet** times the **square root of the number of independent bets**. Skill is how well forecasts match outcomes, where 0 is a coin and 1 is perfect. It is an approximation, and a useful one.

Q: A strategy's skill per bet is 0.05 and it makes 400 independent bets a year. What does skill times the square root of breadth give?
= 1 ±0.01
WHY: 0.05 × √400 = 0.05 × 20 = 1.

### Small edge, many bets
A skill of 0.05 is tiny: barely better than a coin. Used 400 times a year it scores 1.0. A far better forecaster, with a skill of 0.10 and only 25 bets a year, scores 0.5. Quant firms are built on the first kind.

Q: A skill of 0.10 with 25 independent bets a year scores what?
= 0.5 ±0.01
WHY: 0.10 × √25 = 0.10 × 5 = 0.5.

Q: Trader A has twice the skill per bet of trader B. B makes sixteen times as many independent bets. Whose results are better by this rule?
- A, because skill always counts for more than activity
+ B: sixteen times the bets is worth four times the skill
- Neither: the two effects cancel each other out exactly
WHY: The square root of 16 is 4, which beats A's factor of 2.

### Independent is the catch
Ten trades on ten stocks that all move with the market are closer to one bet than to ten. Breadth counts only bets whose outcomes do not depend on each other. Trading more often on the same idea adds costs, not breadth.

Q: You buy five bank stocks on the same morning for the same reason. About how many independent bets is that?
- Five, since there are five positions
+ Close to one
- Twenty-five, since each affects the others
WHY: Stocks bought for one reason in one sector win or lose together.

Q: Which change adds real breadth?
+ A second rule that wins at different times
- Trading the same rule twice as often on the same stock
- Splitting each position into two smaller orders
WHY: Breadth is independent bets. The same bet made more often, or cut in two, is still one bet.

### What it means for a small account
Nobody makes 400 independent bets a year by hand. The lesson is the direction: several small, different, tested edges beat one big conviction, and no single trade deserves a size that only certainty could justify.

Q: Your best idea of the year arrives. What does this lesson say about its size?
+ The usual size: it is still one bet
- Much larger than usual, since conviction is rare
- Ten times larger, split over ten separate orders
WHY: A single bet carries its own luck, however sure it feels.

TIP: The rule is known as the fundamental law of active management (Grinold, Journal of Portfolio Management, 1989).

HERE: On Meme Street the same news often moves a whole sector. Five positions in one sector are close to one bet: size them as one.

## Skill or just the market {alpha-beta} [6]
SUMMARY: Split a return into the part the market gave you and the part you earned, and stop mistaking a rising market for skill.

### Beta: the market's share
A stock's **beta** is how much it tends to move when the market moves 1%. A beta of 1.5 means about 1.5% for every 1% in the market, up and down. Most of what a stock does in a month is the market, scaled by its beta.

Q: The market rises 10% and your stock has a beta of 1.5. What return does the market alone explain, in percent?
= 15 ±0.1
WHY: 1.5 × 10 = 15.

### Alpha: what is left
**Alpha** is the return minus what beta explains. A stock up 12% in a month when its beta called for 15% has an alpha of −3%: it rose, and it still did worse than its own risk promised.

Q: Your portfolio made 20% in a year when the market made 10%. The portfolio's beta is 2. What is its alpha, in percent?
= 0 ±0.1
WHY: Beta explains 2 × 10 = 20. Nothing is left: the whole gain was market risk.

Q: In a year when the market rose 25%, a trader with a beta of 2 made 40%. What does that show?
- Great skill: 40% beat the market by 15 points that year
+ Negative alpha: that risk should have made 50%
- Nothing, since one year is always luck
WHY: 2 × 25 = 50. Making 40 with that much market risk is under-performance.

### Why it matters
In a rising market almost everything bought makes money, and high-beta stocks make the most. The test of a rule is what it adds beyond holding. That is why a backtest sets a rule beside simply holding the same stock over the same candles.

Q: A rule that buys breakouts made 30% while holding the same stocks made 35%. What is the honest summary?
+ The rule lost 5 points against doing nothing
- The rule works: a return of 30% is strong by any measure
- The rule is safer, so 30% counts as a win
WHY: The market made the money. The rule's own contribution was negative.

### Beta cuts both ways
The beta that flatters a portfolio on the way up multiplies the fall. A beta of 2 turns a 20% market drop into about 40%, which then needs a gain of 67% to recover. High returns in a boom are a description of risk taken.

Q: The market falls 20% and your portfolio's beta is 2. What gain is needed afterwards to get back to where you started, in percent?
= 67 ±1
WHY: A 40% fall leaves 60. 100 ÷ 60 − 1 = 0.67.

HERE: The MSI 50 index of Meme Street's 50 biggest companies is the market to compare with. Ask what your month made beyond it.

## Correlated is not cointegrated {cointegration} [6]
SUMMARY: Tell two stocks that move together from two stocks that are tied together, and see why pairs trading needs the second.

### Moving together
Two stocks are **correlated** when their daily moves tend to share a direction. Most stocks are, because the market moves them all. Correlation says nothing about how far apart the two prices may wander over a year.

Q: Two stocks rise and fall on the same days, but one gains 1% a day and the other 0.5%. After a year, what has happened to the gap between them?
+ It has grown enormously
- It has stayed about the same, as they are correlated
- It has closed, as correlated prices converge
WHY: Same direction every day, different size: perfectly correlated, and drifting apart for ever.

### Tied together
Two prices are **cointegrated** when the gap between them keeps returning to a usual level, as if joined by elastic. Each price can wander anywhere. The **spread** between them cannot stray for long, and that returning spread is what a pairs trader trades.

Q: What does a pairs trader need from two stocks?
- Daily moves in the same direction most of the time
+ A spread that keeps coming back to its usual level
- The same price, so that one share of each cancels out
WHY: The profit comes from the spread returning. Moves in the same direction do not bring it back.

### Reading the spread
Measure the spread's average and its usual swing. A **z-score** says how stretched it is: the distance from the average, counted in swings. A spread that averages 2.0 and usually swings 0.5 has a z-score of 3 when it reaches 3.5.

Q: A spread averages 4.0 with a usual swing of 0.8. Today it is 5.6. What is its z-score?
= 2 ±0.05
WHY: (5.6 − 4.0) ÷ 0.8 = 2.

### When the elastic snaps
The tie between two companies is a fact about their businesses, and businesses change: a takeover, a new product, a scandal. Then the spread leaves and never returns, and the trader who kept adding is ruined. A stop on the spread is not optional.

Q: The spread between two long-tied stocks reaches a z-score of 4 after one of them announces a takeover. What is the sound reading?
- An even better entry: the spread is more stretched than ever
+ The tie may be broken, so the old average is gone
- A certain profit, since cointegrated spreads always return
WHY: A stretched spread with a reason behind it is a changed relationship, not an opportunity.

Q: Two stocks have a correlation of 0.9. What does that tell you about the spread between their prices?
+ Nothing: correlation does not tie prices together
- That it will return to its average within a few weeks
- That it cannot grow by more than a tenth
WHY: Correlation is about the direction of daily moves. Only a returning spread makes a pair.

HERE: On Meme Street you can be long one stock and short another. Put a stop on each leg: the game's companies change with their news, as real ones do.

## The same rule in a trend and in a chop {regimes} [6]
SUMMARY: See why one rule can win for months and then lose for months with nothing wrong in it, and how to tell which market you are in.

### Two markets in one
Markets alternate between **trending** stretches, where moves carry on, and **choppy** ones, where they reverse. A breakout rule makes its money in the first and gives it back in the second. A buy-the-dip rule does the opposite. Neither is broken when it loses: the market changed.

Q: A breakout rule made money for three months and has now lost for six weeks. What is the first thing to check?
+ Whether the market went from trending to choppy
- Whether the settings need re-tuning to the last six weeks
- Whether to double the size and win the losses back
WHY: A rule built for trends loses in a range by design. Re-tuning to the latest weeks fits the noise.

### Measuring it
One simple gauge is the **efficiency ratio**: the net move over a stretch divided by the total distance travelled. A price that went from 100 to 110 in a straight line scores 1. One that got there by travelling 40 points up and down scores 0.25.

Q: Over 20 candles a price moves from 50 to 56, and the candle-to-candle moves add up to 24. What is the efficiency ratio?
= 0.25 ±0.01
WHY: Net move 6 ÷ distance travelled 24 = 0.25: mostly chop.

Q: Which stretch suits a trend-following rule?
- An efficiency ratio of 0.1: lots of travel, little progress
+ An efficiency ratio of 0.7
- Any stretch, since a good rule works in every market
WHY: A high ratio means moves carried on, which is what trend rules need.

### Why averages hide it
A backtest over a year blends both markets into one average. A rule that makes 3% a trade in trends and loses 4% in chop can show "no edge" overall and still be useful, if you can tell which market you are in before you trade.

Q: A rule averages +2% a trade on trending charts and −2% on choppy ones, with equal numbers of trades on each. What is its average over all of them, in percent?
= 0 ±0.05
WHY: The two halves cancel. One average hides two opposite results.

### The honest limit
Regimes are clear afterwards and blurry at the time. A filter that says "trending" is itself a rule that can be fitted to the past. Keep it simple, test it on data it has not seen, and size as if it will be wrong at the turn.

Q: You add a trend filter that would have removed every losing month of last year. What is the right suspicion?
- None: a filter that removes losses is always an improvement
+ It may be fitted to last year
- Filters never work, so it should be dropped untested
WHY: A filter chosen because it fixes the past is another search with a lucky winner. It must pass on new data.

HERE: Meme Street's price model makes trending legs and ranges on purpose. Before a trade, say which one you think this is, and check afterwards.

## The edge on paper and the edge after costs {costs-capacity} [6]
SUMMARY: Subtract what trading costs from what a rule earns, and see why small, frequent edges are the first to die.

### The round trip
Every trade pays to get in and to get out. On Meme Street the fee is 0.1% a side, so 0.2% for the round trip. A rule that averages 0.15% a trade before costs loses 0.05% a trade after them.

Q: A rule averages 0.5% a trade before costs. The fee is 0.1% on the way in and 0.1% on the way out. What is the average after fees, in percent?
= 0.3 ±0.01
WHY: 0.5 − 0.2 = 0.3.

### Frequency multiplies it
Costs are paid per trade. A day trader making 250 round trips a year at 0.2% each pays 50% of the traded amount in fees. A swing trader making 25 pays 5%. The faster the rule, the bigger the edge it needs to exist at all.

Q: A rule makes 100 round trips a year, each costing 0.2%. What do the costs add up to over the year, in percent of the amount traded?
= 20 ±0.5
WHY: 100 × 0.2 = 20.

Q: A rule earns 0.1% a trade before costs and trades 400 times a year. The round trip costs 0.2%. What happens?
+ It loses: every trade gives up 0.1% after costs
- It wins: four hundred small gains add up over the year
- It breaks even, since costs are already in the price
WHY: 0.1 − 0.2 = −0.1 a trade, four hundred times.

### More than the fee
Real markets add the **spread** between the bid and the ask, and **slippage** when an order moves the price or the price moves first. In thin stocks these can dwarf the fee. A backtest that fills every order at the last price tested a market that does not exist.

Q: A backtest assumes every order fills at the closing price with no spread. For which rule is that most misleading?
+ A fast rule in small, thinly traded stocks
- A slow rule trading the largest stocks a few times a year
- Any rule equally, since the error is the same on each trade
WHY: Spread and slippage are largest in thin stocks and are paid on every trade.

### Capacity
An edge also has a size limit. A rule that works with a small account may fail with a large one, because large orders move the price against themselves. An edge is worth only as much money as it can carry.

Q: Why can a small account sometimes use an edge that a large fund cannot?
- Small accounts are charged lower fees on every trade
+ Its orders are too small to move the price
- Funds are not allowed to trade small stocks
WHY: The cost of moving the price grows with the size of the order. A small order takes the price it sees.

HERE: Every trade on Meme Street costs 0.1% of its size, with no hidden spread, and your trades never move a price. Real markets charge more: test with the costs you would really pay.

## Famous anomalies, after they were famous {anomalies} [6]
SUMMARY: Follow four celebrated market "anomalies" past their publication dates, and learn to ask of any edge: is it still there?

### The celebrated four
By the 1980s researchers had found that small companies beat large ones (the size effect), cheap stocks beat expensive ones (the value effect), Mondays were worse than other days (the weekend effect), and high dividend yields went before higher returns.

Q: Which of these was the "weekend effect"?
- Stocks rising in the last hour of each trading day
+ Mondays showing worse returns than other days
- Markets closing higher before public holidays
WHY: It was a day-of-the-week pattern: the return from Friday's close to Monday's close was unusually poor.

### What happened next
A review written in 2002 followed these effects past the papers that made them famous. All four, it found, seem to have weakened or disappeared after publication.

Q: Suppose an effect earned 6% a year before it was published and 2% a year after. By what percentage did it shrink?
= 67 ±1
WHY: 1 − 2 ÷ 6 = 0.67.

Q: Four famous effects weakened or vanished after the papers about them appeared. Which explanation covers both luck and crowding?
+ Part was chance, and traders took the rest
- Markets became much less efficient after the 1980s
- The original researchers made errors in their arithmetic
WHY: An effect found in one sample is partly luck, and what is real gets traded away once it is known.

### One that hung on
The same review found that the January effect in small companies, the "turn-of-the-year" effect, became weaker in the years after it was first documented, though some evidence of it remains. Weaker, not gone.

Q: An effect in small companies is weaker after publication, with some of it remaining. What might let part of an edge survive?
- Nobody having heard of it at all
+ It being costly or awkward to trade
- Regulators protecting it from the large funds
WHY: An edge in small, thinly traded stocks is hard to use with real money, so some of it can last.

### The question to ask
Of any edge you are shown, ask three things. When was it found? Has it been tested on the years since? Who is trading it now? An edge with no answer to the second question is a history lesson.

Q: A course teaches a pattern "proven over 1990 to 2005". What is missing?
+ Any test on the years since
- A longer list of stocks from those same years
- Nothing: fifteen years is a long enough sample
WHY: The years after an edge became known are the only fair test of it.

TIP: The review is Schwert, "Anomalies and Market Efficiency", Handbook of the Economics of Finance, 2003.

HERE: Meme Street's market is re-checked so that simple known tricks do not beat holding it. Treat anything that "always works" here as a result to test again.

## Do chart rules work? What 95 studies found {chart-rule-evidence} [6]
SUMMARY: Read the published evidence on technical trading rules the way a quant would: what was found, and what was wrong with how it was tested.

### The tally
A 2007 survey collected the modern studies of technical trading rules. Of 95 studies, 56 found the rules profitable, 20 found they were not, and 19 were mixed. The profits were found at least until the early 1990s.

Q: Of 95 studies, 56 reported profitable technical rules. What share is that, in percent?
= 59 ±1
WHY: 56 ÷ 95 = 0.59.

### The warning with it
The same survey warned that most of those studies had problems in their testing: data snooping, rules or search methods picked after the results were seen, and trouble estimating risk and transaction costs. A count of positive studies is no count of real edges.

Q: Why is "56 of 95 studies found profits" weaker evidence than it sounds?
+ Most of the studies had testing problems
- Studies with losses are published more often than studies with profits
- The studies were all run on one single stock
WHY: The survey itself warned of data snooping, rules chosen after the fact, and costs and risk that were hard to estimate.

### A test that counted the tries
One study took a famous set of 26 chart rules, widened it to a much larger universe of rules, ran them on 100 years of daily data for the Dow Jones index, and adjusted the result for every rule tried. That adjustment, for the whole search, is the step most studies skipped.

Q: What made that study's method stronger than a test of one hand-picked rule?
- It used a hundred years of data, which removes all luck
+ It judged the best rule against all the rules tried
- It tested only the rules traders were already using
WHY: Judging the winner against the whole search is the cure for data snooping. Long data alone does not remove the luck of the pick.

### What to take from it
Chart rules are neither worthless nor proven. The evidence for them is strongest up to the early 1990s, and much of it is before costs or before the search was counted. Treat a chart rule like any claim: one rule, written first, costs in, fresh data.

Q: Which test of a moving-average rule would a quant trust most?
- The best of 200 average lengths over the last ten years
+ One length fixed in advance, with costs, on unseen data
- The rule's best year, to show what it is able to do
WHY: Fixed first, costs in, fresh data: each one removes a testing problem the survey named.

Q: A video shows a chart rule winning on five hand-picked examples. Which testing problem is this?
+ Choosing the cases after seeing the results
- Charging too high a transaction cost on each trade
- Using too long a sample of years
WHY: Examples picked afterwards prove nothing about the cases that are not shown.

TIP: The survey is Park and Irwin, Journal of Economic Surveys, 2007. The counting test is Sullivan, Timmermann and White, Journal of Finance, 1999.

HERE: On Meme Street a chart signal works often, not always. Count your own cases, with the fee in, before you size up.

## From idea to live trade: a research checklist {research-checklist} [6]
SUMMARY: Put the whole unit to work: take one trading idea from a hunch to a small live trade without fooling yourself on the way.

### 1. Write the claim first
Before any test, write the rule in full: entry, exit, stop, stocks, timeframe, costs. Write what result would make you drop it. A claim fixed in advance is one test. A claim shaped while testing is a search.

Q: You write down the rule, and the result that would make you drop it, before running the test. What does this protect against?
+ Changing the rule until the past looks good
- High transaction costs during the test itself
- A market that changes after the test is done
WHY: A rule fixed first cannot be bent to fit the data.

### 2. Count trades and tries
Run it. Read the number of trades before the average: under 30 says nothing, and a win rate needs hundreds. Keep a tally of every version you try, and raise the bar with each one.

Q: Your test shows 18 trades and a 72% win rate. What is the next step?
- Trade it: 72% is far above a coin flip
+ Get many more trades first
- Drop it: only 100% would be convincing
WHY: Eighteen trades leave an error bar of about 12 points either side of the win rate.

### 3. Hold data back
Tune on one part of the history and test once on a part you have not looked at. If the result collapses there, the first one was fitted. Then ask what the rule adds beyond simply holding.

Q: A rule made 3% a trade on the data it was tuned on and 0.2% on the data held back. Which number do you plan with?
- 3%, the result from the larger sample
- The average of the two, 1.6%
+ 0.2%, the one not fitted
WHY: Only the held-back result was untouched by the tuning.

### 4. Costs in, size small
Subtract the full round trip. If an edge remains, trade it at a size where ten losses in a row would not hurt, and keep counting. The live trades are the first data nobody could have fitted.

Q: After fees a rule's average trade is 0.1%, with a standard error of 0.2%. What is its t-statistic?
= 0.5 ±0.01
WHY: 0.1 ÷ 0.2 = 0.5: far inside what luck produces. There is no edge to trade yet.

Q: A rule passes every step. What size should the first live trades be?
+ Small enough that a losing streak changes nothing
- Full size, since the testing is now finished and passed
- Double size, to make up for the time spent testing
WHY: Live results are new data. A tested rule can still fail, and a small size is the price of finding out.

HERE: With the Expert pass the Bots page runs these steps on the game's candles: a rule in exact words, a backtest with the 0.1% fee, and the result beside simply holding the stock.
