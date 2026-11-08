# Volatility as an asset {vol-trading}
Volatility is a price, not just a feeling: what the options market expects, how that expectation is shaped by time and by strike, how to measure it against what happens, and how traders buy and sell it. Expert.
TIER: expert

## Realised against implied {realised-vs-implied} [6]
SUMMARY: Measure the volatility a stock actually had, read the volatility its options expect, and see why the two usually differ.

### Two kinds of volatility
**Realised** volatility is what happened: the standard deviation of daily returns, scaled to a year by multiplying by √252. **Implied** volatility is what the options market expects for the time ahead, backed out of option prices. One is history, the other a forecast with money behind it.

Q: A stock's options imply 30% volatility while its last month moved at a 20% pace. Which is the forecast?
+ The 30%: implied volatility is the market's expectation
- The 20%: realised volatility is the forward-looking number
- Both are forecasts, taken over different windows
WHY: Realised is measured from past returns. Implied is priced from options, so it looks ahead.

### From a year to a day
Volatility is quoted a year at a time. To get a day, divide by √252 (about 15.9). A stock at 32% a year moves about 2% on an ordinary day; at 80% a year, about 5%.

Q: A stock's volatility is 32% a year. Roughly what is its typical daily move, in percent?
= 2 ±0.15
WHY: 32 ÷ √252 = 32 ÷ 15.9 ≈ 2.0% a day.

Q: Two stocks: one at 16% a year, one at 64%. How do their daily moves compare?
+ The second moves about four times as much
- The second moves about twice as much, the square root of four
- They move the same each day; only the yearly totals differ
WHY: The √252 scaling is the same for both, so the ratio of yearly figures is the ratio of daily ones.

[test candle]

### The premium in the forecast
Most of the time implied volatility sits above what then gets realised. Option buyers pay for protection, and sellers want paying to carry the risk. The gap is the **variance risk premium**: a reason selling options tends to win slowly and lose fast.

Q: Over a year a stock's options averaged 28% implied while it realised 21%. What did option sellers earn?
+ The gap between the two, as a premium for carrying the risk
- Nothing, because implied and realised volatility always match at expiry
- A loss, since realised volatility below implied favours buyers
WHY: Selling volatility that is not realised collects the difference. It is the business of option sellers.

HERE: The options chain shows each contract's own implied volatility, and a stock's recent range is on its chart. Compare the two before trading an option.

## The term structure {vol-term-structure} [6]
SUMMARY: Read implied volatility across expiries, turn it into an expected move, and see what an event does to the curve.

### Volatility by expiry
Each expiry has its own implied volatility. Plotted by date, that is the **term structure**. Usually it slopes up: more time, more uncertainty, higher volatility. Before a known event or in a panic it inverts, with the nearest expiries the highest.

Q: Implied volatility is 45% for next week's options and 30% for next year's. What is the market saying?
+ Something big is expected soon
- Nothing unusual: near expiries always carry the highest volatility
- The stock will be calmer this week than over the year
WHY: An inverted curve prices a near event. Normally the near expiries are the lowest.

### The expected move
Implied volatility turns into a price range: expected one-standard-deviation move ≈ price × volatility × √(time in years). A 100 stock at 40% over one month (1/12 of a year) is expected to move about 11.5 either way.

Q: A 100 stock has 40% implied volatility. What is the one-standard-deviation move over one month, in MB?
= 11.5 ±0.6
WHY: 100 × 0.40 × √(1/12) = 100 × 0.40 × 0.289 ≈ 11.5.

Q: The expected one-month move is 11.5 on a 100 stock. Roughly how often should the month end outside that range?
+ About one time in three
- Almost never: a standard deviation covers nearly every outcome
- About half the time, since the range is centred on the price
WHY: One standard deviation covers about 68% of outcomes, so about 32% land outside.

[chart breakout]

### An event in the curve
Before earnings, the expiry just after the date carries an extra lump of volatility: the expected jump. The at-the-money **straddle** price is a quick read of it. A straddle costing 8 on a 100 stock says the market expects roughly an 8% move.

Q: The straddle expiring just after earnings costs 6.50 on a 100 stock. Roughly what move is priced in, in percent?
= 6.5 ±0.3
WHY: The straddle's price is the market's expected absolute move, about 6.5%.

The day after, the lump is gone: implied volatility collapses whatever the stock did, so a straddle has to beat the priced move, not merely see one.

Q: After earnings the stock moves 3% and the straddle was priced for 8%. Who did well?
+ Whoever sold the straddle
- Whoever bought the straddle, since the stock did move
- Nobody: a straddle only pays if the stock does not move at all
WHY: The buyer paid for 8% and got 3%. The seller kept most of the premium.

HERE: The chain prices a known earnings jump into the expiries after the date, so the term structure here inverts before earnings just as a real one does.

## Skew: the price of fear {vol-skew} [5]
SUMMARY: See why puts and calls at the same distance carry different volatilities, measure the skew, and read what it says.

### Not one volatility but a curve
At one expiry, each strike has its own implied volatility. For stocks the curve slopes down: far puts carry higher volatility than far calls. That is **skew**, and it prices the fact that stocks fall faster than they rise and that people pay for crash protection.

Q: Why do out-of-the-money puts on a stock usually carry higher implied volatility than out-of-the-money calls?
+ Falls are faster than rises, and protection is in demand
- Puts are harder to price, so dealers add a safety margin to them
- Calls expire sooner than puts on most exchanges
WHY: Skew is the market charging for the tail it fears most.

### Measuring it
A common measure: the implied volatility of the 25-delta put minus that of the 25-delta call. Eight points of skew is ordinary for a stock; twenty says protection is expensive.

Q: The 25-delta put trades at 34% volatility and the 25-delta call at 26%. What is the skew, in volatility points?
= 8 ±0.1
WHY: 34 − 26 = 8 points.

Q: Skew jumps from 8 points to 20 in a week with the stock flat. What has changed?
+ Demand for downside protection has risen sharply
- Upside calls have become more expensive than puts
- The stock has become less likely to fall
WHY: Puts bid up against calls means fear of a fall, whatever the price has done.

[test level]

### Trading the curve
A **risk reversal** sells the expensive put and buys the cheap call, or the reverse: a bet on the skew and the direction together. Selling skew earns well until the fall arrives, which is exactly when it costs the most.

Q: You sell a far put and buy a far call on a stock, with no shares. What are you betting on?
+ The stock not falling hard, and the skew coming in
- Volatility rising on both sides of the price
- The stock staying exactly where it is until expiry
WHY: Short the fear, long the upside. It is a directional bet that also sells skew.

HERE: Strikes in the game's chain carry a skew, so a far put shows a higher implied volatility than a far call. Open a chain and compare the two.

## The VIX and the fear gauge {vix-and-fear} [5]
SUMMARY: Know what the VIX measures, turn it into an expected monthly move, and use its habits without being fooled by them.

### What the number is
The **VIX** is the 30-day implied volatility of the S&P 500, quoted a year at a time. At 20 it says the index is expected to move about 5.8% over the next month, one standard deviation. It is a price of protection, not a prediction of direction.

Q: The VIX is 24. Roughly what one-month move does it imply for the index, in percent?
= 6.9 ±0.3
WHY: 24 ÷ √12 = 24 ÷ 3.46 ≈ 6.9%.

Q: The VIX jumps from 15 to 35 in a week. What does that say about direction?
+ Nothing directly: it says moves are expected to be large
- The index is certain to fall by about 35%
- The index is certain to rise, because fear is a buy signal
WHY: Volatility is the size of expected moves. Direction is a separate question.

### Its habits
The VIX mean-reverts: it spends most of its time between 12 and 20 and spikes fast in sell-offs, then decays over weeks. Spikes come with falls because protection is bought in a hurry; that is why it is called a fear gauge.

Q: The VIX has spiked to 45 and the index has fallen 12% in two weeks. What has history usually said about the weeks that follow?
+ Volatility tends to fall back, often with a recovery in prices
- The spike tends to double again within the month
- The VIX stays at that level for a year or more
WHY: Spikes decay. The gauge mean-reverts, and the panics that cause it tend to pass.

[chart candle]

### Products on volatility
Futures and funds on the VIX let traders buy or sell volatility itself. The futures usually sit above the index in calm times, so long funds bleed as they roll; short funds collect until a spike wipes a year of gains in a week.

Q: A fund that is permanently long VIX futures has lost value in a calm year. Why?
+ The futures roll down to the lower index price each month
- The VIX fell to zero and the fund held worthless contracts
- Volatility funds pay a fee that equals their whole return
WHY: Futures above the index converge down to it. Rolling long pays that difference again and again.

WARN: Short-volatility products have gone to zero in a single day. Size them as if that day is coming.

## Vega and buying volatility {vega-and-vol-trades} [6]
SUMMARY: Measure how an option gains from rising volatility, build a position that is long volatility, and see how it makes or loses money day by day.

### Vega
**Vega** is the change in an option's value for a one-point rise in implied volatility. At-the-money options with time left have the most vega; options about to expire have almost none. A long option is long vega: it gains when the market gets more nervous.

Q: An option has a vega of 0.12 per share and the contract covers 100 shares. Implied volatility rises five points. What does the contract gain, in MB?
= 60 ±1
WHY: 0.12 × 5 × 100 = 60 MB.

Q: Which position gains most from a rise in implied volatility alone?
+ A long at-the-money option with three months left
- A long option expiring tomorrow, deep in the money
- A short at-the-money option with three months left
WHY: Vega is largest at the money with time left, and long options own it; short options owe it.

### The straddle
Buy the call and the put at the same strike and you own a **straddle**: long vega, long gamma, short theta. It does not care which way the stock goes, only how far and how fast, and it pays for the privilege every day.

Q: You buy a straddle and the stock drifts sideways for a month while implied volatility holds steady. What happens?
+ You lose the time decay, day after day
- You gain, because the straddle profits from a calm stock
- Nothing: a straddle only changes value at expiry
WHY: Theta is the rent on a long straddle. Without movement or a rise in volatility, rent is all you pay.

[test trend]

### Gamma scalping
A delta-hedged straddle earns from movement: buy as the stock falls, sell as it rises, pocket the difference. Over time the trade wins if the volatility realised beats the volatility paid, and loses if the stock is quieter than its options expected.

Q: You hedge a long straddle daily. Over the month the stock realised 35% volatility while you paid 25%. What was the result?
+ A profit: realised beat implied
- A loss: hedging gives away all the movement you need
- Nothing: hedging makes a straddle a zero-return position
WHY: Gamma scalping converts movement into money. More movement than paid for is the profit.

Strip the direction away and one question is left: did the stock move more or less than its options said it would?

Q: What is the real bet in a hedged long straddle?
+ That realised volatility will exceed the implied volatility paid
- That the stock will end far above the strike
- That implied volatility will fall before expiry
WHY: Direction is hedged away. What is left is realised against implied.

HERE: The chain shows each contract's vega next to delta and gamma, so you can see how much a position gains for each point of volatility.

## Selling volatility and its risks {selling-vol-risk} [6]
SUMMARY: Understand how selling options earns, where it loses far more than it earned, and how to size it so one night cannot end you.

### The business of selling
Selling options collects premium and, on average, the variance risk premium with it. The seller is short vega and short gamma: paid every quiet day, hurt on every violent one. The pattern is many small wins and rare large losses.

Q: Over a year an option seller wins 48 trades out of 52. What does that say about the strategy?
+ Little by itself: the four losses decide the year
- It is clearly profitable, with a 92% win rate
- It has no risk left, since losses are so rare
WHY: Short volatility loses big when it loses. The win rate hides the shape of the losses.

### Where the loss comes from
Sell a straddle for 6 on a 100 stock and you are fine while the stock stays within 94 to 106. Outside that, every point is a point lost. A move to 112 costs 12 against 6 collected: a loss equal to everything made.

Q: You sold a straddle for 6.00 on a 100 stock. It expires with the stock at 112. What is the loss per contract of 100 shares, in MB?
= 600 ±1
WHY: The call is worth 12, minus the 6 collected, is 6 a share: 600 MB a contract.

Q: Which move hurts a short straddle most?
+ A large overnight gap, which no hedge can catch
- A slow drift within the range over several weeks
- A fall in implied volatility after the trade is on
WHY: Gaps skip past the hedge. Slow drifts and falling volatility are what the seller wants.

[chart breakout]

### Sizing a short option book
Size short options by the worst gap, not the premium. A rule many desks use: the loss on a three-standard-deviation move must stay under a fixed share of equity, often two or three percent. Naked short calls have no worst case at all.

Q: Your rule allows a 2% loss on a three-standard-deviation move. Equity is 50,000 MB and such a move would cost 500 MB a contract. How many contracts may you sell?
= 2 ±0
WHY: 2% of 50,000 is 1,000 MB; 1,000 ÷ 500 = 2 contracts.

The side matters as much as the size. A short put's loss stops at zero; a short call's does not stop anywhere.

Q: Why is a naked short call more dangerous than a naked short put?
+ A stock can rise without limit, so the loss has no ceiling
- Calls carry more time decay than puts at every strike
- Exchanges forbid hedging a short call with shares
WHY: A put's worst case is the stock at zero. A call's worst case has no number.

WARN: "It has never moved that far" is the sentence before every blow-up in this business. Size for the move that has not happened yet.

HERE: Writing options is not in the game yet; it is planned for Pro, with margin set from the move the chain prices. Until then, buy a straddle before an earnings date to feel the side the seller is on.
