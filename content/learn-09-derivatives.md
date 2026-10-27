# Derivatives {derivatives}
Options from the ground up (calls and puts, pricing, the Greeks, implied volatility, strategies, exercise), then futures, CFDs, swaps and leveraged funds.

## Options: calls, puts, strike, expiry and premium {options-basics} [7]
SUMMARY: What an option is, what it pays, and what it costs.
An **option** is a contract that gives its buyer the **right, but not the obligation**, to buy or sell something at a fixed price by a fixed date.
- A **call** is the right to **buy** at the strike. It pays off if the price ends **above** the strike.
- A **put** is the right to **sell** at the strike. It pays off if the price ends **below** the strike.
- The **strike** is the fixed price.
- The **expiry** is the date the right ends.
- The **premium** is what you pay for the option, up front. For a buyer it is the most you can lose.

### At expiry
- Call payoff = the price minus the strike, if positive; otherwise nothing.
- Put payoff = the strike minus the price, if positive; otherwise nothing.

A 100 call bought for 3: if the stock ends at 110 it pays 10 (a profit of 7); at 103 it pays 3 (break-even); at 95 it pays nothing (you lose the 3).

### Contracts
On exchanges, one contract covers **100 shares**. A premium of 3 a share costs 300 a contract.

### Why buy options
- **Leverage with a limited loss**: a small premium controls the move on 100 shares, and the most you lose is the premium.
- **Insurance**: a put protects shares you own against a fall.
- **Betting on volatility**, not only direction (later lessons).

HERE: Every company and commodity has options, for every player, free ones included. A stock's **Options** tab shows five expiries (the next regular close and 2, 7, 30 and 90 game days later), 13 strikes around the price, calls on the left and puts on the right, with a bid and an ask. One contract is on 100 shares; you buy whole contracts at the ask and sell at the bid, with the usual 0.1% fee. Click any option to see its details and a profit-or-loss chart at expiry.

[try /stock/NVXA] Open Novaxis's Options tab, click a call near the price, and read its breakeven and its profit-or-loss chart.

Q: You buy a 50 put for 2. The stock ends at 44. What is your profit per share?
+ 4
- 6
- -2
WHY: The put pays 50 - 44 = 6; minus the 2 premium: 4.
Q: You buy a 120 call for 5. The stock ends at 118. What happens?
- You make 2
+ The call expires worthless and you lose the 5 premium
- You must buy the stock at 120
WHY: Below the strike a call pays nothing; the buyer's loss is limited to the premium.
Q: A premium of 2.40 a share. What does one contract cost?
- 2.40
+ 240
- 24,000
WHY: One contract is on 100 shares: 100 × 2.40.

## How options are priced: intrinsic and time value {options-pricing} [7]
SUMMARY: What an option's price is made of, and moneyness.
An option's premium has two parts.

### Intrinsic value
What it would pay if it expired right now: for a call, the price minus the strike (if positive); for a put, the strike minus the price. An option with intrinsic value is **in the money (ITM)**; one right at the price is **at the money (ATM)**; one that would pay nothing is **out of the money (OTM)**.

### Time value
Everything above the intrinsic value: the chance that the price moves further in the option's favour before expiry. It is biggest for at-the-money options, grows with the time left and with how much the stock tends to move (its volatility), and melts to zero at expiry.

| Stock at 100 | Strike | Type | Intrinsic | Moneyness |
| 100 call | 100 | call | 0 | at the money |
| 90 call | 90 | call | 10 | in the money |
| 110 call | 110 | call | 0 | out of the money |
| 110 put | 110 | put | 10 | in the money |

### What sets the price
- The stock's price against the strike.
- Time to expiry: more time, more chances, more value.
- **Volatility**: a stock that moves a lot is more likely to end far from the strike: options on it cost more.
- Interest rates and dividends (smaller effects).
The standard formula for all this is **Black-Scholes**.

### Put-call parity
A call minus a put at the same strike and expiry is worth about the expected price at expiry minus the strike. If it were not, there would be a risk-free profit, and traders would take it until it disappeared.

HERE: Options are priced with Black-Scholes on the **expected price at expiry** (the forward: today's price, less any dividend before expiry, plus the stock's expected drift). Nothing is discounted, because MB cash earns no interest here, so put-call parity holds exactly at every strike. The chain shades in-the-money options, and the details panel shows the chance of finishing in the money.

Q: The stock is at 80. What is the intrinsic value of a 70 call?
+ 10
- 0
- 70
WHY: 80 - 70 = 10.
Q: The stock is at 80. What is the intrinsic value of a 70 put?
- 10
+ 0
- -10
WHY: A put pays the strike minus the price only if positive; 70 - 80 is negative, so 0.
Q: Which option has the most time value, all else equal?
- Deep in the money
+ At the money
- Far out of the money
WHY: The outcome is most uncertain at the money, so the "chance" part of the price is largest there.

## The Greeks {greeks} [8]
SUMMARY: Delta, gamma, theta and vega: how an option's price reacts to the stock, time and volatility.
The **Greeks** measure how an option's price changes when one thing changes and the rest stay put.

### Delta
How much the option moves for a 1-point move in the stock. A call's delta is between 0 and 1; a put's between 0 and -1. An at-the-money call has a delta of about 0.5: it moves about half as much as the stock. Delta is also roughly the chance of finishing in the money. A contract with a delta of 0.4 moves like 40 shares.

### Gamma
How fast delta changes as the stock moves. Highest for at-the-money options near expiry, where delta can swing from near 0 to near 1 in a small move. High gamma means an option's behaviour changes quickly.

### Theta
How much value the option loses each day from the passing of time, all else equal: **time decay**. It is the price a buyer pays for waiting, and it speeds up near expiry. An option buyer needs the move to come soon enough to beat theta.

### Vega
How much the option's price changes for a one-point change in implied volatility. Longer-dated options have more vega. If volatility expectations fall, every option gets cheaper, even with the stock unchanged.

### Rho
Sensitivity to interest rates (here, to the expected drift). Small for short-dated options.

| Greek | Measures | Buyer of a call wants |
| Delta | move with the stock | the stock to rise |
| Gamma | change in delta | big moves |
| Theta | daily time decay | the move to come soon |
| Vega | sensitivity to volatility | volatility expectations to rise |

HERE: The chain can show any Greek in its extra column, and the details panel lists them all, each **a share and for one contract**, with a sentence on what it means ("moves like 32.7 shares"). Your contracts list their total delta and their theta a game day, so you can see what time is costing you.

Q: A call has a delta of 0.6. The stock rises 2. Roughly how much does the call gain?
+ 1.2
- 2
- 0.6
WHY: Delta × move = 0.6 × 2.
Q: Which Greek measures time decay?
- Delta
+ Theta
- Vega
WHY: Theta is the value lost per day as expiry approaches.
Q: Implied volatility falls sharply while the stock stays put. What happens to options?
- Nothing
+ They get cheaper, especially long-dated ones (vega)
- Calls rise and puts fall
WHY: Lower expected volatility lowers every option's value through vega.

## Implied volatility and the IV crush {implied-vol} [6]
SUMMARY: The volatility priced into options, why it jumps before earnings, and why it collapses after.
**Implied volatility (IV)** is the volatility that, put into the pricing formula, gives the option's market price. It is the market's estimate of how much the stock will move, expressed as a yearly percentage. High IV: big moves expected, expensive options.

### IV and real volatility
Options usually cost a little **more** than the moves they end up insuring: the sellers want paying for the risk (the variance risk premium). On average, buying options loses a little for that reason.

### The smile and the skew
Options at different strikes trade at different IVs. Puts well below the price usually cost more (crash insurance is in demand): that is the **skew**. Very speculative stocks can show the opposite: calls far above the price cost more.

### The term structure
Short and long expiries can have different IVs. After a storm, short ones cost more; in a calm, less.

### The IV crush
Before an earnings report, IV rises: everyone knows a big move is coming, so options are bid up. The moment the report is out, the uncertainty is gone and IV collapses. A trader who bought calls before earnings can be **right about the direction and still lose**, if the move was smaller than the options had priced in.

### The expected move
At-the-money options tell you the move the market expects: roughly, the price of an at-the-money straddle (a call plus a put) is the expected size of the move by expiry.

HERE: IV here comes from what the stock has really been doing (its realised volatility, the bigger of a short and a long window), scaled by the current calm or storm, plus a 15% premium. Ordinary stocks have a put skew, the wildest a call skew, commodities none. When a report falls before an expiry, that expiry's IV includes the earnings jump, and it vanishes once the report is out: the **IV crush**. The Options tab shows each expiry's IV and the move the options expect.

Q: Before earnings, an option's IV is 80%; after, 40%. What has happened to the option's price, all else equal?
+ It has fallen a lot: the IV crush
- It has doubled
- Nothing
WHY: Lower IV means cheaper options; the earnings premium disappears with the uncertainty.
Q: You buy calls before earnings; the stock rises 2%; the calls lose money. Why?
- The broker made an error
+ The move was smaller than the options had priced in, and IV collapsed
- Calls always lose after earnings
WHY: Being right on direction is not enough if the move is smaller than expected.
Q: Why do puts below the price usually have higher IV than calls above it?
- They are rarer
+ Investors pay extra for crash insurance
- Because of dividends
WHY: Demand for protection against falls pushes put prices, and their IV, up.

## Option strategies {option-strategies} [9]
SUMMARY: Covered calls, protective puts, spreads, straddles and strangles, and iron condors.
Options can be combined to shape a bet.

### Protective put
Own the shares and buy a put below the price. The put caps your loss for its life, like insurance: you pay the premium, and keep the upside.

### Covered call
Own the shares and **sell** a call above the price. You collect the premium, which cushions a fall a little, but give away the upside above the strike. Popular for income, in flat or slowly rising markets.

### Vertical spreads
Buy one option and sell another of the same kind and expiry at a different strike.
- **Bull call spread**: buy a call, sell a higher call. Cheaper than the call alone; the gain is capped at the difference between the strikes.
- **Bear put spread**: the mirror image for a fall.

### Straddles and strangles
- **Long straddle**: buy a call and a put at the same strike. Profits if the stock moves a lot, either way. Loses if it sits still.
- **Long strangle**: the same with out-of-the-money options: cheaper, needs a bigger move.
These are bets on **volatility**, and they pay a lot of time value: they need the move to be bigger than the options already expect.

### Iron condor
**Sell** a strangle and buy a further-out one as protection. Profits if the stock stays in a range; the loss is capped by the wings. It is the classic "sell volatility" trade: many small wins and the occasional big loss.

### Buying versus selling options
Buyers have limited losses and pay time decay; sellers collect time decay and carry the risk of big moves. Neither side has a free lunch: options are priced so that, on average, both are paid for the risk they carry, with the sellers slightly ahead (the variance risk premium) and occasionally hit hard.

HERE: On Meme Street you can **buy** calls and puts and sell back what you hold; you cannot sell (write) options you do not own. So **protective puts**, long calls and puts, **long straddles** and **long strangles** can all be built here; covered calls, spreads that sell an option, and iron condors need a real broker. A check on the engine found that buying straddles and strangles at random loses on average, whatever the expiry and the mood, as theory says.

Q: Which strategy profits from a big move in either direction?
+ A long straddle
- A covered call
- An iron condor
WHY: Owning both a call and a put pays off if the stock moves far, up or down.
Q: What does a protective put do for a shareholder?
- Increases the dividend
+ Caps the loss below the put's strike for its life, at the cost of the premium
- Removes the upside
WHY: The put pays when the price falls below its strike, offsetting the loss on the shares.
Q: Who collects time decay?
- Option buyers
+ Option sellers
- Nobody
WHY: Time value melts in the seller's favour; buyers pay it.

## Exercise and assignment: European and American {exercise} [5]
SUMMARY: When an option can be used, what happens at expiry, and cash settlement.
### Exercising
Using the option: a call holder buys at the strike, a put holder sells at the strike. The seller who has to deliver is **assigned**.

### European and American style
- **American** options can be exercised any day up to expiry. Most single-stock options in the US are American.
- **European** options can only be exercised at expiry. Most index options are European.
In practice, it is rarely worth exercising an American option early (you throw away its time value; selling it is usually better), except sometimes just before a dividend.

### Physical and cash settlement
- **Physical**: shares change hands at the strike.
- **Cash**: no shares move; the holder is simply paid the intrinsic value in cash. Index options are cash-settled.

### At expiry
In-the-money options are usually exercised automatically; out-of-the-money ones expire worthless.

HERE: Options here are **European and cash-settled**: no shares ever change hands. At expiry an in-the-money contract pays its intrinsic value (times 100) into your cash with no fee, and an out-of-the-money one expires worthless. Before then you can sell it back at the bid at any time, which is how you take a profit early. A contract can be bought until a minute before it expires.

Q: Your European call is deep in the money a week before expiry. Can you exercise it now?
- Yes, any time
+ No, only at expiry, but you can sell it
- Only if the stock pays a dividend
WHY: European options are exercised only at expiry; selling captures the value before then.
Q: A cash-settled 50 call expires with the stock at 58. What do you receive per share?
+ 8 in cash
- 100 shares
- Nothing
WHY: Cash settlement pays the intrinsic value: 58 - 50.

## Futures: contracts, margin, contango and backwardation {futures} [6]
SUMMARY: Agreements to buy or sell later, how their margin works, and the shape of a futures curve.
A **futures contract** is an agreement to buy or sell something (oil, wheat, gold, an index, a currency) at a set price on a set future date. Unlike an option, **both sides are obliged**.

### Why they exist
A farmer sells wheat futures in spring to lock in a price for the autumn harvest; a bakery buys them to lock in its costs. Speculators take the other side, betting on the price.

### Margin and daily settlement
You post a small **margin** (often 5 to 10% of the contract's value), so futures are heavily leveraged. Every day gains and losses are settled in cash (**marked to market**): losses must be paid at once, or the position is closed.

### Contango and backwardation
Futures for different months trade at different prices.
- **Contango**: later months cost more than the spot price (storage and financing costs). Common in oil and gold.
- **Backwardation**: later months cost less. Happens when something is scarce right now.
A fund that holds futures and **rolls** them each month (sells the expiring one, buys the next) loses a little on each roll in contango: this "roll yield" can make a commodity fund trail the commodity's spot price badly over years.

HERE: There are no futures here. The five commodities (crude oil, natural gas, wheat, copper and gold) trade at their **spot** price, like shares, with no expiry and no roll. Real commodity funds that hold futures can behave quite differently from the spot price.

Q: What is the key difference between a future and an option for the buyer?
+ The future is an obligation; the option is a right
- Futures cannot lose money
- Options have no expiry
WHY: Both sides of a future must complete it; an option buyer can walk away.
Q: In contango, how do later futures compare with the spot price?
- Lower
+ Higher
- The same
WHY: Contango is an upward-sloping futures curve.

## CFDs, swaps, and leveraged fund decay {other-products} [6]
SUMMARY: Contracts for difference, swaps in one paragraph, and why leveraged and inverse funds lose value over time.
### CFDs (contracts for difference)
A contract with a broker that pays the change in an asset's price, without owning the asset. Leveraged, available long or short, with overnight financing charges. Popular with retail traders outside the US (where they are banned). Regulators require brokers to publish the share of retail accounts that lose money on CFDs, and it is usually between 60% and 80%. You are trading against the broker, and the leverage is the danger.

### Swaps
Two parties exchange streams of payments: fixed interest for floating, one currency for another, or the return on an asset for a fee (a total return swap). They are tools for banks, funds and companies, not for individuals, but they are how many funds get their exposure.

### Leveraged and inverse funds: the decay
A 2x fund aims to move twice the index **each day** (it resets its leverage daily). Over one day it does. Over longer periods, in a choppy market, it loses value even if the index ends flat:

| Day | Index | Index level | 2x fund |
| start | | 100 | 100 |
| 1 | +10% | 110 | 120 |
| 2 | -9.1% | 100 | 98.2 |

The index is back to 100; the 2x fund is down 1.8%. Repeat that over months of ups and downs and the fund drifts lower, while a few lucky smooth trends make it soar. Inverse funds decay the same way. They are tools for short-term bets, not for holding.

HERE: **2LMSI** and **3LMSI** move two and three times the MSI 50, **2SMSI** and **3SMSI** two and three times the opposite, with the multiple reset **every second**. Their expected price stays level, but in a jittery market the typical path drifts down while a few soar: exactly the decay above. You cannot add leverage on top of them.

[try /stock/3LMSI] Compare 3LMSI's chart with the MSI 50's over a long timeframe.

Q: The index goes +5% then -5%. Roughly what does a 3x daily fund do over the two days?
- +0%
+ About -2.3%
- +15%
WHY: 1.15 × 0.85 = 0.9775; the index itself is down only 0.25%.
Q: Why are CFDs risky for beginners?
+ They are leveraged, so small moves make big gains and losses, and most retail accounts lose
- They are illegal everywhere
- They never pay out
WHY: Leverage magnifies losses; regulators' own figures show most retail CFD traders lose.
