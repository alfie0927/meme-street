# How derivatives are priced {pricing}
How professionals put a price on a forward or an option without guessing where the market goes: arbitrage, cost of carry, put-call parity in numbers, the binomial tree and the inputs to Black-Scholes. Advanced.
TIER: pro

## Arbitrage and the law of one price {arbitrage} [6]
SUMMARY: Spot a riskless profit, see why it closes as soon as traders find it, and use "no arbitrage" to put a price on a contract.

### A riskless profit
An **arbitrage** is a set of trades made at the same moment that locks in a profit with no risk: buy something cheap and sell the same thing dear. A share quoted at 50.00 MB in one market and 50.40 MB in another is one. Buy 100 in the first, sell 100 in the second, and 40 MB is yours before costs.

Q: A share trades at 20.00 MB on one exchange and 20.06 MB on another. You buy 500 on the first and sell 500 on the second at the same moment. What is the profit before costs, in MB?
= 30 ±0.5
WHY: 500 × (20.06 − 20.00) = 500 × 0.06 = 30 MB.

Q: Which of these is an arbitrage?
- Buying a share you expect to jump after its results
+ Buying gold in one market as you sell it in another
- Shorting a stock whose price looks far too high
WHY: Only the gold trade is riskless: both sides are done at once, so the profit is fixed when the trades are made. The others are bets.

### Costs come first
The gap must beat what the trades cost. On the 50 MB share above, a fee of 0.1% on each side costs about 10 MB, leaving 29.96 MB. A gap of 0.3% against 0.2% of fees is worth taking. A gap of 0.15% is not.

Q: Two prices differ by 0.15%, and buying and selling cost 0.1% each. What happens if you trade the gap?
+ You lose about 0.05% after the fees
- You make 0.15%, since the gap is riskless
- You make 0.05%, the gap less one of the fees
WHY: 0.15 − 0.1 − 0.1 = −0.05. A gap smaller than the costs is no arbitrage.

### Why it cannot last
Buying in the cheap market pushes its price up, and selling in the dear one pushes that price down. Every trader who spots the gap closes part of it, so in busy markets a gap lasts moments and goes to the fastest. This is the **law of one price**: the same thing sells for the same price everywhere, once costs are counted.

Q: Many fast traders find the same gap between two markets. What happens to it?
- It widens, as their orders draw attention to it
+ Their buying and selling close it within moments
- It stays open, since each takes only a small share
WHY: Buying lifts the cheap price and selling lowers the dear one, until nothing is left to take.

### The pricing tool
Turn the idea round. If two portfolios pay exactly the same in every future outcome, they must cost the same today, or someone buys the cheap one, sells the dear one and keeps the difference. A safe promise of 1,040 MB in a year, when cash earns 4% a year, is worth 1,000 MB today: 1,000 MB in the bank pays the same.

Q: A safe promise pays 2,100 MB in one year, and cash earns 5% a year. What is the promise worth today, in MB?
= 2000 ±1%
WHY: 2,100 ÷ 1.05 = 2,000 MB. Cash of 2,000 MB grows to the same 2,100.

### How derivatives use it
A derivative's payoff depends on another price. Find a mix of shares and cash that pays the same in every outcome, and its cost is the derivative's price, with no guess about where the market is heading. The rest of this unit does exactly that.

Q: Portfolio A costs 98 MB and portfolio B costs 100 MB, and both pay the same in every outcome. What is the arbitrage?
+ Buy A and sell B, keeping 2 MB today
- Buy B, as the dearer one must pay more later
- Buy both, then wait for the two prices to meet
WHY: The two payoffs cancel at the end, so the 2 MB taken today is a profit with no risk.

HERE: Shares on Meme Street trade at one price with no spread, and every trade costs 0.1%. Options are quoted with a bid and an ask about 6% of the value apart, so a gap smaller than that is no arbitrage.

## What a forward should cost {forward-price} [6]
SUMMARY: Work out a fair forward price from the price today, interest and income, and the trade that pulls a futures price back when it strays.

### Buy now or agree now
A **forward** fixes today the price of something delivered later. The same result can be had another way: borrow, buy the thing now and hold it. So the forward must cost what buying and holding costs, the **cost of carry**: F = S × (1 + r)^T, with S the price today, r the yearly interest rate and T the years to delivery.

Q: A share is 200 MB and interest is 4% a year. What is the fair forward price for delivery in six months, in MB?
= 203.96 ±0.1
WHY: 200 × 1.04^0.5 = 203.96 MB.

### The continuous form
Textbooks often add the interest continuously instead: F = S × e^(rT). For a 100 MB share at 5% for a year that gives 105.13 MB, a little above the 105 of yearly interest, because interest is earned on interest at every instant.

Q: A share is 100 MB and interest is 6% a year, added continuously. What is the fair one-year forward, in MB?
= 106.18 ±0.05
WHY: 100 × e^0.06 = 106.18 MB.

### Take off the income
The owner of the share collects any dividend paid before delivery, and the forward buyer does not. So the dividend comes off first: F = (S − D) × (1 + r)^T, with D the dividend's value today. A 100 MB share with a dividend worth 2 MB, at 5% for a year, has a forward of 102.90 MB. For a commodity, the cost of storing it is added instead.

Q: A share is 50 MB and pays a dividend worth 1 MB today before delivery. Interest is 4% a year. What is the fair one-year forward, in MB?
= 50.96 ±0.05
WHY: (50 − 1) × 1.04 = 50.96 MB.

### When the price strays
Say a 100 MB share at 5% has a one-year futures price of 108, three above fair. Borrow 100, buy the share and sell the future at 108. In a year deliver the share, collect 108 and repay 105: 3 MB with no risk. This is **cash-and-carry**. Below fair, the reverse works: short the share, lend the cash and buy the future.

Q: A share is 80 MB, interest is 5% a year, and its one-year future trades at 86 MB. What does cash-and-carry lock in per share, in MB?
= 2 ±0.05
WHY: Fair is 80 × 1.05 = 84. Sell the future at 86, deliver the share bought with borrowed money, repay 84: 2 MB.

Q: A future trades below its fair cost-of-carry price. Which trade locks in the gap?
- Borrow, buy the share and sell the future
+ Short the share, lend the cash and buy the future
- Buy the future alone and hold it to delivery
WHY: The cheap side is the future, so it is bought, and the share is sold against it. Buying the future alone is a bet on the price.

### Contango and backwardation again
The [futures lesson](/lessons/futures) showed later months costing more (contango) or less (backwardation). Cost of carry explains contango: interest and storage make later delivery dearer. Backwardation comes when holding the thing now is worth something in itself, as when supplies are short. That benefit is called the **convenience yield**.

Q: Wheat is plentiful, storage is cheap and interest is 5% a year. What shape should its futures curve have?
+ Later months a little dearer, from the carry
- Later months cheaper, since the rate is high
- Flat, since storage cancels out the interest
WHY: With nothing scarce, the cost of carry sets the curve, and interest and storage both add to later prices.

HERE: There are no futures or forwards to trade on Meme Street, and the commodities trade at their spot price. The Options tab shows an **expected price at expiry** (the forward): today's price less a dividend that goes ex before expiry, grown at the stock's expected drift rather than at an interest rate, since MB cash earns nothing.

## Put-call parity in numbers {parity-in-numbers} [6]
SUMMARY: Write put-call parity with interest in it, build a share, a call or a put out of the other pieces, and turn a mispriced pair into a riskless profit.

### The equation
Now the numbers. For European options on one share with the same strike K and expiry T: **C − P = S − K × e^(−rT)**. The right side is the share less what the strike is worth today. With yearly interest, K × e^(−rT) becomes K ÷ (1 + r)^T: at S = K = 100, 5% and a year, the call is worth 4.76 more than the put.

Q: A share is 50 MB. A call and a put both have a strike of 48 and six months to expiry, and interest is 4% a year, added continuously. How much more is the call worth than the put, in MB?
= 2.95 ±0.05
WHY: 50 − 48 × e^(−0.04 × 0.5) = 50 − 47.05 = 2.95 MB.

### Why it must hold
A long call with a short put pays the share's final price less K, whatever happens: above K the call pays, below K the put costs you. A share bought with borrowed money worth K at expiry pays exactly the same. Same payoff, so the same price today.

Q: You hold a long call and a short put, both with a strike of 100. At expiry the share is at 90. What does the pair pay per share?
- 0, since the call expires worthless
+ −10, the share's price less the strike
- +10, what the put pays its holder
WHY: The call pays nothing and the short put costs 10: 90 − 100 = −10.

### Synthetic positions
Rearrange the equation and any piece can be built from the others. Traders use these copies when one piece is dearer or harder to trade.
- Long call + short put + cash worth K at expiry = long share
- Long call + short share + cash lent = long put
- Long put + long share + cash borrowed = long call

Q: You own a share and a put on it. By put-call parity, which position does that match?
+ A long call, plus cash borrowed
- A short call, plus cash lent out
- A long put, with twice the protection
WHY: P + S = C + K × e^(−rT): a share with a put behaves like a call with the strike's value held in cash.

### A worked mispricing
At S = K = 100, 5% continuous interest and a year, parity says C − P = 4.88. A call at 10 and a put at 4 make a gap of 6, so the call is 1.12 too dear. Sell the call, buy the put and the share, and borrow 95.12: you take in 1.12 today. At expiry, share plus put less call is exactly 100: the loan.

Q: Same share and options, but the call trades at 9.50 and the put at 4.00. Selling the call, buying the put and the share and borrowing 95.12 locks in how much per contract of 100 shares, in MB?
= 62.3 ±1
WHY: 9.50 − 4.00 − 100 + 95.12 = 0.623 a share, times 100 = 62.3 MB.

### The Meme Street version
Where cash earns no interest, nothing is discounted and the equation loses its e: C − P = F − K, with F the expected price at expiry. A call is then worth F − K more than the put at the same strike, at every strike.

Q: With no interest, the forward is 102 MB and a call with a strike of 100 is worth 7 MB. What is the put on the same strike worth, in MB?
= 5 ±0.05
WHY: C − P = F − K = 2, so P = 7 − 2 = 5 MB.

HERE: The values in the chain keep C − P = F − K exactly, as the derivatives unit says. You can build a synthetic put here (buy a call and short the share, which pays a borrow fee), but not a synthetic share: you cannot sell an option you do not own.

## A one-step binomial tree {binomial-tree} [6]
SUMMARY: Price a call by copying it with shares and cash in a world with two outcomes, and see why the real chance of a rise never enters the price.

### Two outcomes
Strip the market down to one step. A share at 100 MB will be 120 or 90 in a year, and cash earns 5% a year. A call with a strike of 100 then pays 20 if the share rises (Cu) and nothing if it falls (Cd). What is that call worth today?

Q: In the same tree, what does a put with a strike of 100 pay if the share falls to 90, in MB?
= 10 ±0.01
WHY: 100 − 90 = 10. If the share rises to 120 the put pays nothing.

### Way one: copy it
Hold Δ = (Cu − Cd) ÷ (Su − Sd) = 20 ÷ 30 = two thirds of a share. That is worth 80 if the share rises and 60 if it falls: 60 more than the call either way. So borrow what 60 is worth today, 60 ÷ 1.05 = 57.14. The shares cost 66.67, less the loan: the copy costs 9.52, and so must the call.

Q: A share at 50 MB will be 60 or 40. How many shares copy one call with a strike of 50?
= 0.5 ±0.01
WHY: Δ = (10 − 0) ÷ (60 − 40) = 0.5.

### Way two: the risk-neutral probability
Take p = ((1 + r) − d) ÷ (u − d), with u and d the up and down multipliers: (1.05 − 0.9) ÷ (1.2 − 0.9) = 0.5. Weight the payoffs by p and discount: (0.5 × 20 + 0.5 × 0) ÷ 1.05 = 9.52. The same answer, by a shorter road.

Q: A share can rise by 10% or fall by 5% in one step, and cash earns 2% over the step. What is the risk-neutral probability of the rise?
= 0.467 ±0.005
WHY: (1.02 − 0.95) ÷ (1.10 − 0.95) = 0.07 ÷ 0.15 = 0.467.

Q: The share at 50 MB will be 60 or 40, and cash earns nothing. What is a call with a strike of 50 worth, in MB?
= 5 ±0.05
WHY: p = (1 − 0.8) ÷ (1.2 − 0.8) = 0.5, so the call is 0.5 × 10 + 0.5 × 0 = 5 MB.

### The real chance does not enter
Nowhere did we use how likely a rise really is. Whether a forecaster says 90% or 10%, the copy costs 9.52, and any other price for the call is an arbitrage against it. The real chance is already inside today's share price. So p is no forecast: it is the weight that makes the share earn exactly the safe rate.

Q: A forecaster raises the real chance of a rise from 50% to 80%. The share's price, the two outcomes and the rate stay the same. What happens to the call's value?
- It rises, since the call now pays out more often
+ Nothing: the shares and cash that copy it cost the same
- It falls, since a likelier rise makes the share less risky
WHY: The copy of shares and cash pays the same as the call in both outcomes, and its cost does not depend on which outcome is likely.

### From one step to many
Real prices take more than two values. Cut the year into many small steps sized to the stock's volatility, run the same rule backwards from expiry, and the tree's price closes in on the Black-Scholes price of the next lesson. In the tree above the put is worth 4.76, and C − P = 9.52 − 4.76 = 100 − 100 ÷ 1.05, as parity requires.

Q: In the one-step tree above, the call is worth 9.52 MB. Using put-call parity with yearly interest, what is the put with a strike of 100 worth, in MB?
= 4.76 ±0.05
WHY: P = C − S + K ÷ 1.05 = 9.52 − 100 + 95.24 = 4.76 MB, the same as (0.5 × 0 + 0.5 × 10) ÷ 1.05.

TIP: The many-step tree is from Cox, Ross and Rubinstein, "Option Pricing: A Simplified Approach", Journal of Financial Economics, 1979.

HERE: On Meme Street nothing is discounted and the forward grows at the stock's expected drift, so a contract is priced at what it is expected to pay under the game's own price model, with the premium and the spread on top.

## Black-Scholes without the calculus {black-scholes-inputs} [6]
SUMMARY: Read the standard option formula's inputs, which way each one moves a call and a put, what N(d2) means, and where its assumptions break.

### The formula, once
For a European call on a share with no dividend: **C = S × N(d1) − K × e^(−rT) × N(d2)**, where d1 = [ln(S ÷ K) + (r + σ² ÷ 2) × T] ÷ (σ × √T) and d2 = d1 − σ × √T. σ is the yearly volatility, and N( ) is the chance that a bell-curve draw lands below its input.

Q: A share is 100 MB, the strike is 100, there is a year to go, volatility is 20% and the rate is 0. Then d1 = 0.1, d2 = −0.1, N(0.1) = 0.540 and N(−0.1) = 0.460. What is the call worth, in MB?
= 8 ±0.1
WHY: 100 × 0.540 − 100 × 0.460 = 54.0 − 46.0 = 8.0 MB. With a rate of 0, e^(−rT) is 1.

### Six inputs
| Input rises | Call | Put |
| Share price | up | down |
| Strike | down | up |
| Time to expiry | usually up | usually up |
| Volatility | up | up |
| Interest rate | up | down |
| Dividends before expiry | down | up |

Q: Interest rates rise and nothing else changes. What happens to a call and a put on the same share?
- Both gain, since every option is worth more
+ The call gains a little and the put loses a little
- The call loses a little and the put gains a little
WHY: A higher rate makes the strike cheaper to pay later, which helps the call and hurts the put.

Q: Which of these is not an input to Black-Scholes?
+ How fast the share is expected to grow
- How much the share tends to move each year
- The dividends paid before the option expires
WHY: As in the binomial tree, the expected return drops out. Volatility and dividends both enter.

### What N(d2) means
N(d2) is the chance the call finishes in the money in the risk-neutral world of the last lesson, where the share grows at the safe rate. It is not the real chance: a share expected to grow faster has a higher real chance of finishing above the strike.

Q: A call's N(d2) is 0.46. What is the best reading of it?
- A 46% real chance of the call paying out at expiry
+ A 46% chance of paying out if the share grows at the safe rate
- The call moving 0.46 MB for every 1 MB the share moves up
WHY: N(d2) is the risk-neutral chance of exercise. The real chance depends on the share's expected growth, and the move per 1 MB is delta.

### Where it fails
The formula assumes volatility is constant, prices move without jumps, trading is continuous and costs nothing, and the rate is fixed. Real markets break all four. Implied volatility differs from strike to strike, which is the [skew](/lessons/vol-skew). Earnings and gaps are jumps that no continuous hedge can follow.

Q: Puts below the price carry 30% implied volatility and calls above it 22%, on the same expiry. Which assumption does that break?
+ That one constant volatility fits every strike
- That no dividend is paid before the expiry
- That the interest rate stays fixed to expiry
WHY: Under the formula every strike would show the same volatility. A skew says the market prices the tails differently.

TIP: The formula is from Black and Scholes, "The Pricing of Options and Corporate Liabilities", Journal of Political Economy, 1973, with Merton's "Theory of Rational Option Pricing" the same year. Merton and Scholes received the 1997 Nobel prize in economics. Black had died in 1995.

HERE: Meme Street uses the formula on the forward with nothing discounted, C = F × N(d1) − K × N(d2), and the chain's Chance ITM column is N(d2). Volatility is not constant here either: each strike has its own, and an earnings jump is added before a report.
