# Indicators {indicators}
Moving averages, momentum oscillators, volatility bands, volume tools and Fibonacci: what each measures, how traders use it, and why every one of them gives false signals.

## Moving averages {moving-averages} [7]
SUMMARY: SMA and EMA, what they smooth away, crossovers, and averages as moving support.
A **moving average** is the average closing price of the last N candles, recalculated on every candle. It smooths out the noise to show the direction underneath.

### SMA and EMA
- **Simple (SMA)**: every one of the N closes counts the same.
- **Exponential (EMA)**: recent closes count more, so it turns faster, and gets shaken out by noise more often.
A short average (9, 10, 20) follows the price closely; a long one (100, 200) shows the big trend and turns slowly.

### How traders use them
- **Direction**: price above a rising 50 or 200 average is an uptrend; below a falling one, a downtrend.
- **Dynamic support and resistance**: in a trend, pullbacks often stop near the 20 or 50 average.
- **Crossovers**: a short average crossing above a long one is a **golden cross**; crossing below, a **death cross**.

### The catch: they lag
An average is made of past prices, so it always turns **after** the price has. By the time two averages cross, much of the move has happened. In a range, averages flatten and crossovers flip back and forth (**whipsaws**), each one a small loss. Averages are a filter for direction, not a crystal ball.

HERE: Free on every chart: SMA 10, 20, 50, 100 and 200, and EMA 9, 12, 20, 26, 50, 100 and 200, with your own length, source and colour in each one's settings. The 20, 50 and 200-day averages are also among the levels the price model treats as support and resistance. Pro adds the weighted, Hull, double and triple exponential, and volume-weighted averages.

[test ma]

## Momentum: RSI, MACD and stochastic {momentum} [8]
SUMMARY: Oscillators that measure the speed of a move, overbought and oversold, and divergences.
**Momentum** indicators measure how fast the price is moving, not where it is. They swing (oscillate) between fixed bounds, in a panel under the chart.

### RSI (relative strength index)
Compares the size of recent up moves with recent down moves, on a scale of 0 to 100 (14 candles by default).
- Above **70**: **overbought**: the price has risen fast.
- Below **30**: **oversold**: it has fallen fast.
Overbought does **not** mean "sell". In a strong uptrend the RSI can stay above 70 for a long time while the price keeps rising. Many traders use 40 to 50 as support for the RSI in an uptrend instead.

### Stochastic
Where the close sits within the recent high-low range, 0 to 100, with a slower signal line. Above 80 and below 20 are the extremes; crosses of the two lines there are its signals.

### MACD
The difference between a 12 and a 26-candle EMA (the MACD line), a 9-candle EMA of that (the signal line), and the gap between them as a histogram. MACD crossing above its signal is bullish momentum; a shrinking histogram means the move is slowing.

### Divergence
The most useful signal from an oscillator: the **price makes a new high but the RSI makes a lower high** (bearish divergence). The price is still rising, but on less momentum. The mirror image at a low is bullish divergence. It warns that a trend is tiring; it does not say when it ends, and a strong trend can show divergence several times before turning.

HERE: Free: **RSI 14**, the **Stochastic** (14, 3, 3) and **Momentum** (10). Pro adds MACD, Stochastic RSI, CCI, Williams %R, rate of change, the Awesome and Ultimate oscillators and TRIX. Trends here often end with a last push on weaker momentum and volume, which shows up as divergence: readable, but never a guarantee.

[test rsi]

## Volatility: Bollinger Bands and ATR {volatility} [6]
SUMMARY: Measuring how much a price moves, the squeeze, and sizing stops by volatility.
**Volatility** is how much a price moves, whichever way. It matters for where you put stops, how big your position is, and when quiet markets are about to wake up.

### Bollinger Bands
A 20-candle moving average with a band two standard deviations above and below it. When the price is volatile the bands widen; when it is quiet they narrow.
- **The squeeze**: bands at their narrowest in a long time. Volatility comes in waves, so a squeeze often comes before a big move (the bands do not say which way).
- **Riding the band**: in a strong trend the price can hug the upper band for a long time. Touching it is not a sell signal.
- **Back to the middle**: in a range, moves to a band often return to the average.

### ATR (average true range)
The average size of a candle's full range (including gaps) over the last 14 candles, in price. If a stock's ATR is 2 MB, a typical candle moves about 2 MB.
- **Stops**: a stop closer than about one ATR is inside normal noise and will be hit by chance. Many traders place stops 1.5 to 3 ATR away, or just beyond a level plus a fraction of an ATR.
- **Position size**: a more volatile stock means a wider stop, so a smaller position for the same risk.

HERE: Bollinger Bands, Keltner Channels, Donchian Channels, ATR, historical volatility and Bollinger bandwidth and %B are Pro indicators. The long and short **position** drawing tools (free) place their stop and target 1.5 and 3 ATR from the entry. Volatility here clusters as it does in real markets: calm spells and storms, with volatility rising more after falls than after rises, and the end of a range is quieter than its start.

## Volume tools: VWAP, OBV and money flow {volume-tools} [5]
SUMMARY: Indicators built from volume, and the one the professionals watch most.
### VWAP
The **volume-weighted average price**: the average price of every share traded since the session began, weighted by volume. It is the price the "average" buyer paid today.
- Big funds judge their trading against it: buying below the VWAP is a good fill.
- Intraday traders treat it as a line of fair value: above it, buyers are in control; below it, sellers.
- It starts again every session.

### On-balance volume (OBV)
A running total that adds the volume of every up candle and subtracts every down candle's. If the OBV is rising while the price is flat, volume is coming in on the up candles: possible quiet buying.

### Money Flow Index and Chaikin Money Flow
Like the RSI, but with volume included (MFI), or a measure of whether candles close near their highs on high volume (CMF). They try to show whether money is flowing in or out.

### The volume average
The simplest volume tool: a moving average over the volume bars, so you can see at a glance whether today's volume is above or below normal.

HERE: The 20-candle **volume average** is free. VWAP (on intraday charts, starting each game day), OBV, the Money Flow Index and Chaikin Money Flow are Pro. The Daily Chart has its own VWAP and 20 EMA switches for everyone.

## Fibonacci retracements and extensions {fibonacci} [6]
SUMMARY: The retracement levels, how traders use them in pullbacks, and extensions as targets.
After a swing, prices usually pull back part of the way before continuing. **Fibonacci retracements** divide the swing at **23.6%, 38.2%, 50%, 61.8% and 78.6%**, ratios that come from the Fibonacci sequence (50% is not a Fibonacci ratio but is always included).

### Using retracements
- Draw from the start of the swing to its end.
- In a healthy trend, pullbacks often stop between **38.2% and 61.8%**.
- A pullback past **78.6%** suggests the trend is in trouble.
- The levels are strongest where they line up with something else: an old support, a moving average, a round number.

### Extensions
To estimate how far the next leg could go, **extensions** project the swing beyond its end: 127.2%, 161.8% and 200% of it, measured from the end of the pullback. Traders use them as targets.

### Why they work (when they do)
Partly because so many traders watch the same levels and place orders there. They are zones, not exact prices, and plenty of pullbacks ignore them entirely.

HERE: **Auto Fibonacci** (free) draws the retracement levels between the highest and lowest price on screen. The drawing tools have a **Fibonacci retracement** (drag from the start of a swing to its end) and a **Fibonacci extension** (click the start, the end and the end of the pullback).

[test fib]

## Trend strength: ADX, SuperTrend and Ichimoku {trend-strength} [5]
SUMMARY: Indicators that say whether a market is trending at all, and trend-following lines.
Many indicators work in trends and fail in ranges (moving averages) or the other way round (oscillators at extremes). Knowing **whether** the market is trending is half the battle.

### ADX
The **average directional index** measures trend strength from 0 to 100, regardless of direction. Below about 20: no real trend, range tools work better. Above 25: a trend worth following. Its companions +DI and -DI show which side is stronger.

### Aroon
How recently the price made its highest high and lowest low in a window. A recent high and a stale low mean an uptrend.

### Parabolic SAR and SuperTrend
Trailing lines under the price in an uptrend and above it in a downtrend. When the price crosses the line it flips sides. Traders use them as **trailing stops**: they follow the trend and get out when it turns, at the cost of being shaken out by deep pullbacks.

### Ichimoku Cloud
A Japanese system on one chart: two averages of the highs and lows (the conversion and base lines), a "cloud" between two lines drawn 26 candles ahead, and a lagging line. Price above the cloud is an uptrend, below it a downtrend, inside it no clear trend; the cloud's edges act as support and resistance.

HERE: ADX with +DI and -DI, Aroon, the Parabolic SAR, SuperTrend and the Ichimoku Cloud are Pro indicators. Trends here come and go: a stock trends for a spell, ranges for a spell, and sometimes just drifts.

## Combining indicators, and false signals {combining-indicators} [6]
SUMMARY: Why more indicators is not better, how to combine them sensibly, and living with false signals.
### They mostly say the same thing
RSI, stochastic, CCI, Williams %R and momentum are all built from the same closes over the same recent window. Five of them agreeing is one opinion repeated five times, not five confirmations. Putting a dozen on a chart only makes it harder to read.

### Combine different kinds
A sensible set uses one tool from each family:
- **Trend**: a moving average or two (is the market going anywhere?).
- **Momentum**: one oscillator (is the move speeding up or tiring?).
- **Volatility**: ATR or bands (how far is normal, where does the stop go?).
- **Volume**: volume bars and their average (is anyone taking part?).
Then the chart itself (trend structure and levels) comes first, and the indicators second.

### Every indicator gives false signals
Each one is a summary of past prices. In the right conditions it helps; in the wrong ones it misleads: crossovers whipsaw in ranges, oscillators stay overbought in trends, bands get walked. There is no setting that removes false signals without removing the good ones too. Tuning the settings until the past looks perfect (overfitting) makes it worse, not better: the *Testing* track explains why.

### What actually makes money
Not the indicator: the plan around it. A modest signal with a sensible stop, a target bigger than the risk, and a position sized so one loss does not hurt, beats a brilliant signal traded carelessly.

[try /stock/NVXA] On Novaxis, switch on one moving average, the RSI and the volume average. Leave everything else off and read the chart for ten minutes.
