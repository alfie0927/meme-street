# Indicators {indicators}
TIER: pro
Moving averages, momentum oscillators, volatility bands, volume tools and Fibonacci: what each measures, how traders use it, and why every one of them gives false signals.

## Moving averages {moving-averages} [7]
SUMMARY: SMA and EMA, what they smooth away, crossovers, and averages as moving support.
A **moving average** is the average closing price of the last N candles, recalculated on every candle. It smooths out the noise to show the direction underneath.

### SMA and EMA
- **Simple (SMA)**: every one of the N closes counts the same.
- **Exponential (EMA)**: recent closes count more, so it turns faster, and gets shaken out by noise more often.

Q: Which average turns faster when the trend changes?
+ The exponential, since recent closes count more
- The simple, because it counts every close the same
- Neither: both turn at the same candle by definition
WHY: Weighting recent closes more makes the EMA react sooner, and get shaken more often.

A short average (9, 10, 20) follows the price closely; a long one (100, 200) shows the big trend and turns slowly.

Q: Which average reacts faster to the latest price?
- A 200 SMA
+ A 20 EMA
- They react the same
WHY: Shorter, and exponentially weighted towards recent closes: the 20 EMA turns first.

### How traders use them
- **Direction**: price above a rising 50 or 200 average is an uptrend; below a falling one, a downtrend.
- **Dynamic support and resistance**: in a trend, pullbacks often stop near the 20 or 50 average.
- **Crossovers**: a short average crossing above a long one is a **golden cross**; crossing below, a **death cross**.

Q: What is a golden cross?
+ A short average crossing above a long one
- The price crossing a round number
- A long average crossing above a short one
WHY: The fast average moving above the slow one is the golden cross; the opposite is a death cross.

### The catch: they lag
An average is made of past prices, so it always turns **after** the price has. By the time two averages cross, much of the move has happened. In a range, averages flatten and crossovers flip back and forth (**whipsaws**), each one a small loss. Averages are a filter for direction, not a crystal ball.

Q: Why do crossover systems lose money in a range?
+ The averages flatten and cross back and forth, each signal a small loss
- Ranges have no volume to carry a crossover signal through to a real trend
- They work best in ranges, so a loss means a bug
WHY: Whipsaws: a flat market makes averages cross repeatedly with no follow-through.

HERE: Free on every chart: SMA 10, 20, 50, 100 and 200, and EMA 9, 12, 20, 26, 50, 100 and 200, with your own length, source and colour in each one's settings. The 20, 50 and 200-day averages are also among the levels the price model treats as support and resistance. Pro adds the weighted, Hull, double and triple exponential, and volume-weighted averages.

[test ma]

[try /stock/CLDR?ind=sma20,sma50&tf=1h] Open CloudRail with the 20 and 50 averages on: is the price above a rising 20, and where did the two last cross?

## Momentum: RSI, MACD and stochastic {momentum} [8]
SUMMARY: Oscillators that measure the speed of a move, overbought and oversold, and divergences.
**Momentum** indicators measure how fast the price is moving, not where it is. They swing (oscillate) between fixed bounds, in a panel under the chart.

### RSI (relative strength index)
Compares the size of recent up moves with recent down moves, on a scale of 0 to 100 (14 candles by default).

Q: The RSI compares what over its 14 candles?
+ The size of recent rises with recent falls
- The price with its moving average of the same length
- Today's volume with the volume of the last 14 candles
WHY: RSI is a ratio of up moves to down moves, scaled to 0-100.

- Above **70**: **overbought**: the price has risen fast.
- Below **30**: **oversold**: it has fallen fast.
Overbought does **not** mean "sell". In a strong uptrend the RSI can stay above 70 for a long time while the price keeps rising. Many traders use 40 to 50 as support for the RSI in an uptrend instead.

Q: The RSI is 78 in a strong uptrend. What does that tell you on its own?
+ The price has risen fast; it is not a sell signal by itself
- Sell now, before the RSI falls back under 70
- The trend has ended and will reverse from here within a few candles
WHY: Overbought describes the speed of the rise. Strong trends stay overbought for long stretches.

### Stochastic
Where the close sits within the recent high-low range, 0 to 100, with a slower signal line. Above 80 and below 20 are the extremes; crosses of the two lines there are its signals.

### MACD
The difference between a 12 and a 26-candle EMA (the MACD line), a 9-candle EMA of that (the signal line), and the gap between them as a histogram. MACD crossing above its signal is bullish momentum; a shrinking histogram means the move is slowing.

Q: What is the MACD line?
+ The difference between a 12 and a 26-candle EMA
- The 200-day average drawn under the price as a separate line
- The RSI smoothed with a 9-candle average
WHY: MACD = EMA 12 minus EMA 26; its 9-candle EMA is the signal line.

### Divergence
The most useful signal from an oscillator: the **price makes a new high but the RSI makes a lower high** (bearish divergence). The price is still rising, but on less momentum. The mirror image at a low is bullish divergence. It warns that a trend is tiring; it does not say when it ends, and a strong trend can show divergence several times before turning.

Q: The price makes a higher high but the RSI makes a lower high. What is this?
+ Bearish divergence
- Bullish divergence
- A golden cross
WHY: Price up, momentum down: the move is tiring.

HERE: Free: **RSI 14**, the **Stochastic** (14, 3, 3) and **Momentum** (10). Pro adds MACD, Stochastic RSI, CCI, Williams %R, rate of change, the Awesome and Ultimate oscillators and TRIX. Trends here often end with a last push on weaker momentum and volume, which shows up as divergence: readable, but never a guarantee.

[test rsi]

[try /stock/NVXA?ind=rsi&tf=15m] Open Novaxis with the RSI on, 15-minute candles: find the last time it went over 70 or under 30 and see what the price did next.

## Volatility: Bollinger Bands and ATR {volatility} [6]
SUMMARY: Measuring how much a price moves, the squeeze, and sizing stops by volatility.

**Volatility** is how much a price moves, whichever way. It matters for where you put stops, how big your position is, and when quiet markets are about to wake up.

### Bollinger Bands

A 20-candle moving average with a band two standard deviations above and below it. When the price is volatile the bands widen; when it is quiet they narrow.

Q: A stock's Bollinger Bands have widened sharply this week. What happened?
+ The price became more volatile
- The price rose above its 20-candle average
- Volume fell, so the bands lost their anchor
WHY: The bands are two standard deviations wide: they widen when moves get bigger.

- **The squeeze**: bands at their narrowest in a long time. Volatility comes in waves, so a squeeze often comes before a big move (the bands do not say which way).
- **Riding the band**: in a strong trend the price can hug the upper band for a long time. Touching it is not a sell signal.

- **Back to the middle**: in a range, moves to a band often return to the average.

Q: Bollinger Bands are at their narrowest in weeks. What does that suggest?
+ The market is quiet, and a bigger move may follow, in either direction
- The price will fall as the bands close in on it
- Nothing ever happens after a squeeze like this one, the bands stay narrow
WHY: Volatility comes in waves; the squeeze says a move may come, not which way.

### ATR (average true range)

The average size of a candle's full range (including gaps) over the last 14 candles, in price. If a stock's ATR is 2 MB, a typical candle moves about 2 MB.

- **Stops**: a stop closer than about one ATR is inside normal noise and will be hit by chance. Many traders place stops 1.5 to 3 ATR away, or just beyond a level plus a fraction of an ATR.
- **Position size**: a more volatile stock means a wider stop, so a smaller position for the same risk.

Q: A stock's ATR is 3 MB. Where would a 0.5 MB stop most likely be?
+ Inside normal noise, likely to be hit by chance
- Safely outside the noise of a 3 MB range
- Exactly right for a stock that moves 3 MB in a candle
WHY: A typical candle moves 3 MB; a 0.5 MB stop will be touched by ordinary wobbles.

Q: Two stocks, the same risk budget. Stock B's ATR is twice stock A's. How should the positions compare?
+ B's should be about half as big, because its stop is twice as far
- B's should be twice as big to match its larger moves and bigger range
- The same: the risk budget is all that counts
WHY: Risk = size × stop distance. A stop twice as far needs half the size for the same risk.

HERE: Bollinger Bands, Keltner Channels, Donchian Channels, ATR, historical volatility and Bollinger bandwidth and %B are Pro indicators. The long and short **position** drawing tools (free) place their stop and target 1.5 and 3 ATR from the entry.

HERE: Volatility here clusters as it does in real markets: calm spells and storms, with volatility rising more after falls than after rises, and the end of a range is quieter than its start.

[test stop]

## Volume tools: VWAP, OBV and money flow {volume-tools} [5]
SUMMARY: Indicators built from volume, and the one the professionals watch most.
### VWAP
The **volume-weighted average price**: the average price of every share traded since the session began, weighted by volume. It is the price the "average" buyer paid today.
- Big funds judge their trading against it: buying below the VWAP is a good fill.
- Intraday traders treat it as a line of fair value: above it, buyers are in control; below it, sellers.
- It starts again every session.

Q: The price has been above VWAP all afternoon. What does that say about the day's buyers?
+ On average, everyone who bought today is in profit
- Volume is falling as the session goes on into the close
- The stock is overbought and due to fall
WHY: VWAP is the day's average price weighted by volume; above it, the average buyer of the day is ahead.

Q: The price is above the session's VWAP. What does that suggest?
+ Buyers have been in control so far this session
- The stock is overvalued against its peers in the sector
- Volume is low compared with yesterday
WHY: Above the average price paid today, today's buyers are on average in profit; it is read as strength.

### On-balance volume (OBV)
A running total that adds the volume of every up candle and subtracts every down candle's. If the OBV is rising while the price is flat, volume is coming in on the up candles: possible quiet buying.

Q: The price is flat but the OBV keeps rising. What might be happening?
- Nothing
+ Volume is coming in on up candles
- The stock is about to be delisted
WHY: OBV adds up-candle volume and subtracts down-candle volume, so it can rise while the price is flat.

### Money Flow Index and Chaikin Money Flow
Like the RSI, but with volume included (MFI), or a measure of whether candles close near their highs on high volume (CMF). They try to show whether money is flowing in or out.

### The volume average
The simplest volume tool: a moving average over the volume bars, so you can see at a glance whether today's volume is above or below normal.

Q: Today's volume bar sits far above its 20-candle average. What does that tell you?
+ Far more shares traded than usual
- The price is above its own 20-candle average
- Money is flowing out of the stock
WHY: The volume average is the normal level; a bar far above it is unusual participation.

HERE: The 20-candle **volume average** is free. VWAP (on intraday charts, starting each game day), OBV, the Money Flow Index and Chaikin Money Flow are Pro. The Daily Chart has its own VWAP and 20 EMA switches for everyone.

[chart breakout]

## Fibonacci retracements and extensions {fibonacci} [6]
SUMMARY: The retracement levels, how traders use them in pullbacks, and extensions as targets.
After a swing, prices usually pull back part of the way before continuing. **Fibonacci retracements** divide the swing at **23.6%, 38.2%, 50%, 61.8% and 78.6%**, ratios that come from the Fibonacci sequence (50% is not a Fibonacci ratio but is always included).

### Using retracements
- Draw from the start of the swing to its end.
- In a healthy trend, pullbacks often stop between **38.2% and 61.8%**.
- A pullback past **78.6%** suggests the trend is in trouble.
- The levels are strongest where they line up with something else: an old support, a moving average, a round number.

Q: A rally from 100 to 150 pulls back to 131. Roughly which retracement level is that?
- 23.6%
+ 38.2%
- 61.8%
WHY: The swing is 50 points; 150 − 131 = 19, and 19 ÷ 50 is 38%: the 38.2% level.

Q: A stock rises from 100 to 150. Where is the 61.8% retracement?
- 130.90
+ 119.10
- 161.80
WHY: 61.8% of the 50-point swing is 30.9; 150 - 30.9 = 119.1.

### Extensions
To estimate how far the next leg could go, **extensions** project the swing beyond its end: 127.2%, 161.8% and 200% of it, measured from the end of the pullback. Traders use them as targets.

### Why they work (when they do)
Partly because so many traders watch the same levels and place orders there. They are zones, not exact prices, and plenty of pullbacks ignore them entirely.

Q: In a healthy uptrend, where do pullbacks often stop?
+ Between 38.2% and 61.8% of the swing
- Below 100% of the swing, past its start
- Never at any Fibonacci level in practice
WHY: That middle zone is where traders most often see trend pullbacks end.

HERE: **Auto Fibonacci** (free) draws the retracement levels between the highest and lowest price on screen. The drawing tools have a **Fibonacci retracement** (drag from the start of a swing to its end) and a **Fibonacci extension** (click the start, the end and the end of the pullback).

[test fib]

## Trend strength: ADX, SuperTrend and Ichimoku {trend-strength} [5]
SUMMARY: Indicators that say whether a market is trending at all, and trend-following lines.
Many indicators work in trends and fail in ranges (moving averages) or the other way round (oscillators at extremes). Knowing **whether** the market is trending is half the battle.

### ADX
The **average directional index** measures trend strength from 0 to 100, regardless of direction. Below about 20: no real trend, range tools work better. Above 25: a trend worth following. Its companions +DI and -DI show which side is stronger.

Q: ADX is at 12 and falling. What does that tell a trend follower?
+ There is little trend to follow
- A strong downtrend is under way
- A breakout is about to happen
WHY: ADX measures the strength of a trend, not its direction; below about 20 the market is drifting sideways.

Q: The ADX reads 14. What does it suggest?
+ No strong trend
- A very strong uptrend
- A very strong downtrend
WHY: ADX measures strength, not direction, and readings under about 20 mean no real trend.

### Aroon
How recently the price made its highest high and lowest low in a window. A recent high and a stale low mean an uptrend.

### Parabolic SAR and SuperTrend
Trailing lines under the price in an uptrend and above it in a downtrend. When the price crosses the line it flips sides. Traders use them as **trailing stops**: they follow the trend and get out when it turns, at the cost of being shaken out by deep pullbacks.

Q: How do traders often use SuperTrend or the Parabolic SAR?
+ As a trailing stop that follows the trend
- As a price target for the next move
- To measure the volume behind a trend as it develops
WHY: The line trails the price and flips when the trend turns, which makes it a natural trailing stop.

### Ichimoku Cloud
A Japanese system on one chart: two averages of the highs and lows (the conversion and base lines), a "cloud" between two lines drawn 26 candles ahead, and a lagging line. Price above the cloud is an uptrend, below it a downtrend, inside it no clear trend; the cloud's edges act as support and resistance.

HERE: ADX with +DI and -DI, Aroon, the Parabolic SAR, SuperTrend and the Ichimoku Cloud are Pro indicators. Trends here come and go: a stock trends for a spell, ranges for a spell, and sometimes just drifts.

[test trend]

## Combining indicators, and false signals {combining-indicators} [6]
SUMMARY: Why more indicators is not better, how to combine them sensibly, and living with false signals.
### They mostly say the same thing
RSI, stochastic, CCI, Williams %R and momentum are all built from the same closes over the same recent window. Five of them agreeing is one opinion repeated five times, not five confirmations. Putting a dozen on a chart only makes it harder to read.

Q: RSI, stochastic and Williams %R all say "oversold". How much confirmation is that?
- Three independent confirmations
+ Little more than one
- None at all
WHY: Indicators from one family repeat the same information.

### Combine different kinds
A sensible set uses one tool from each family:
- **Trend**: a moving average or two (is the market going anywhere?).
- **Momentum**: one oscillator (is the move speeding up or tiring?).
- **Volatility**: ATR or bands (how far is normal, where does the stop go?).
- **Volume**: volume bars and their average (is anyone taking part?).

Q: You have two moving averages and the MACD on your chart. What family is missing?
+ Volatility, such as ATR or bands
- Momentum, since the MACD measures trend only
- Nothing: three indicators always cover the families
WHY: Averages are trend, MACD is momentum; nothing on that chart measures how much the price moves.

Then the chart itself (trend structure and levels) comes first, and the indicators second.

Q: Which set covers different kinds of information?
+ A moving average, the RSI, ATR and volume
- RSI, stochastic and CCI
- Five moving averages of different lengths
WHY: Trend, momentum, volatility and volume are four different questions.

### Every indicator gives false signals
Each one is a summary of past prices. In the right conditions it helps; in the wrong ones it misleads: crossovers whipsaw in ranges, oscillators stay overbought in trends, bands get walked. There is no setting that removes false signals without removing the good ones too. Tuning the settings until the past looks perfect (overfitting) makes it worse, not better: the *Testing* track explains why.

Q: How do you get rid of all false signals?
- Find the perfect settings
- Use more indicators
+ You cannot
WHY: Every indicator misleads sometimes; risk management is what keeps the false signals cheap.

### What actually makes money
Not the indicator: the plan around it. A modest signal with a sensible stop, a target bigger than the risk, and a position sized so one loss does not hurt, beats a brilliant signal traded carelessly.

[try /stock/NVXA?ind=sma20,rsi&tf=1h] On Novaxis with the 20 average and the RSI already on: hourly candles. Leave everything else off and read the chart for ten minutes.

[test ma]
