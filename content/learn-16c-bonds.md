# Bond maths {bond-maths}
The sums behind bonds: present value, pricing a bond, yield to maturity, duration and convexity worked in numbers, and the credit spread a company pays over its government. Builds on Bonds and yields. Advanced.
TIER: pro

## Money now and money later {present-value} [6]
SUMMARY: Grow money forward with compounding, bring it back with discounting, and check the rule of 72 against the exact answer.

### Compounding
Money lent at a rate earns interest, and that interest then earns interest too. After n years at a rate r, an amount grows to **future value = present value × (1 + r)ⁿ**. Lend 10,000 MB at 5% a year for 3 years and you get back 11,576.25 MB.

Q: You lend 50,000 MB at 6% a year, compounded once a year, for 2 years. How much do you get back, in MB?
= 56180 ±0.5%
WHY: 50,000 × 1.06 × 1.06 = 56,180.

### Interest on interest
Over long stretches compounding matters most. At 5% a year for 10 years, simple interest adds 50%. Compounding turns 1 MB into 1.63 MB, a gain of 63%: the extra 13 points are interest earned on earlier interest.

Q: Why does 5% a year for 10 years add more than 50%?
- The lender adds a bonus for tying the money up so long
+ Each year's interest earns interest in later years
- Ten years of inflation are added on to the final sum
WHY: Compounding multiplies by 1.05 ten times, which comes to 1.63, because each year's interest joins the amount that earns.

### Discounting
Run the sum backwards and you have **present value = future value ÷ (1 + r)ⁿ**. 10,000 MB promised in 2 years, at 5% a year, is worth 9,070.29 MB today: lend 9,070.29 MB at 5% and in 2 years it grows to exactly 10,000. The rate used is the **discount rate**.

Q: Someone promises you 20,000 MB in 3 years. Money earns 4% a year. What is the promise worth today, in MB?
= 17780 ±0.5%
WHY: 20,000 ÷ 1.04³ = 20,000 ÷ 1.1249 = 17,780.

Q: The discount rate rises from 4% to 6%. What happens to the present value of a fixed payment due in 5 years?
+ It falls, since the payment is divided by more
- It rises, since money now earns more while you wait
- It stays the same, because the payment itself is fixed
WHY: Present value is the payment ÷ (1 + r)ⁿ. A higher r gives a larger divisor and a smaller value today: the bond see-saw in one line.

### The rule of 72
For a quick doubling time, divide 72 by the rate in percent. At 8% a year, 72 ÷ 8 = 9 years. The exact answer is ln 2 ÷ ln(1 + r), which at 8% gives 9.01 years.

Q: Using the rule of 72, how many years does money take to double at 6% a year?
= 12 ±0.1
WHY: 72 ÷ 6 = 12. The exact answer, ln 2 ÷ ln 1.06, is 11.9.

### How close it is
The rule fits best near 8% and stays close from about 6% to 10%. Further out it drifts: at 2% it says 36 years against an exact 35.0, and at 24% it says 3 years against an exact 3.2.

Q: Where is the rule of 72 furthest off, as a share of the true answer?
- At 8% a year, where it is out by a whole year
+ At high rates, such as 24% a year or more
- Between 6% and 10%, where most rates sit
WHY: At 24% it is out by 0.22 years in 3.2, about 7%. At 8% it is out by less than a hundredth of a year.

HERE: MB cash on Meme Street earns no interest, so 100,000 MB left in cash is still 100,000 MB a year later. Interest runs the other way on a leveraged long: the loan's interest is added to the loan as it runs, so later interest is charged on earlier interest too.

## Pricing a bond {bond-price} [6]
SUMMARY: Price a bond as the sum of its discounted coupons and face value, and tell par, premium and discount bonds apart.

### Every payment, discounted
A bond is a list of promised payments: a coupon each year and the face value at the end. Its fair price is the present value of each payment, added up. The rate used is the yield the market asks of bonds like it.

Q: A bond's final payment is 105, due in 3 years. The market asks 6% a year. What is that one payment worth today?
= 88.16 ±0.5%
WHY: 105 ÷ 1.06³ = 105 ÷ 1.191 = 88.16.

### A worked example
Take a bond with a face value of 100, a 5% coupon paid once a year and 3 years left, when the market asks 4%:

- Year 1: 5 ÷ 1.04 = 4.81
- Year 2: 5 ÷ 1.04² = 4.62
- Year 3: 105 ÷ 1.04³ = 93.34
- Price: 4.81 + 4.62 + 93.34 = 102.78

Q: The same bond (5% coupon, 3 years, face value 100) when the market asks 6%. What is its price?
= 97.33 ±0.3%
WHY: 5 ÷ 1.06 + 5 ÷ 1.06² + 105 ÷ 1.06³ = 4.72 + 4.45 + 88.16 = 97.33.

### Par, premium and discount
When the coupon equals the market's yield, the price is exactly the face value: the bond trades at **par**. A coupon above the yield lifts the price over face value, a **premium**. A coupon below it pulls the price under, a **discount**. At 4% the bond above sold at a premium; at 6%, at a discount.

Q: A bond pays a 3% coupon. New bonds of the same kind yield 5%. How does it trade?
- At par, since its face value is still 100
+ At a discount, below its face value
- At a premium, as older bonds are scarcer
WHY: Its coupon is below the market's yield, so buyers pay less than 100 to bring their return up to 5%.

Q: A bond with a face value of 100 trades at 104. What do you know about it?
+ Its coupon is above the yield the market asks
- Its yield is above its own coupon rate
- Its issuer is about to repay it early at 104
WHY: A premium means the coupon pays more than the market requires, so buyers bid the price over face value.

### A bond with no coupon
A **zero-coupon bond** pays only its face value at maturity, so its price is one discounted payment. At 5% a year, 100 due in 5 years costs 78.35. The 21.65 gap is the whole of the interest.

Q: A zero-coupon bond pays 100 in 10 years. The market asks 4% a year. What is its price?
= 67.56 ±0.5%
WHY: 100 ÷ 1.04¹⁰ = 100 ÷ 1.480 = 67.56.

HERE: Meme Street has no single bonds to price. BOND (Steady Bonds), a short-dated government bond fund, trades like a share at one price.

## Yield to maturity {yield-to-maturity} [6]
SUMMARY: Find the one rate that makes a bond's discounted payments equal its price, set it against the current yield, and see the price-yield see-saw in numbers.

### The sum run backwards
Pricing starts from a yield and finds the price. Markets usually go the other way: given the price, which single rate makes the discounted payments add up to it? That rate is the **yield to maturity**. It assumes you hold to the end and every payment arrives.

Q: A bond is priced at 98.17. What is its yield to maturity?
+ The rate at which its discounted payments add to 98.17
- Its yearly coupon divided by its face value of 100
- The rate the central bank sets for overnight loans
WHY: Yield to maturity is defined by the price: the one discount rate that makes the payments worth exactly what the bond costs.

### Trial and error
With more than one payment there is no neat formula: you try rates until the sum matches. A 3-year 5% bond priced at 97.33 is too cheap for 5%, which would give 100, so try higher. At 6% the payments add to 97.33: the yield to maturity is 6%.

Q: A bond with a 5% coupon trades at 103. To find its yield to maturity, which way do you move from 5%?
+ Down: a price over 100 means a yield under the coupon
- Up: a higher price means the bond pays more each year
- Neither: the yield to maturity equals the coupon
WHY: At 5% the payments add to exactly 100. Only a lower rate makes them add to 103.

### One year: a phone sum
With one year left there is one payment, so the sum is short: yield = final payment ÷ price − 1. A 5% bond with a year to run, priced at 95, pays 105 at the end: 105 ÷ 95 − 1 = 10.53%.

Q: A bond with a 3% coupon and one year left is priced at 99. What is its yield to maturity, in percent?
= 4.04 ±0.05
WHY: It pays 103 at the end. 103 ÷ 99 − 1 = 0.0404.

### Current yield is a shortcut
The **current yield** is the coupon divided by the price: 5 ÷ 95 = 5.26% for that bond. It ignores the gain from 95 back to 100 at maturity, so for a discount bond it sits below the yield to maturity. For a premium bond the order flips.

Q: A bond pays a 6% coupon and costs 108. What is its current yield, in percent?
= 5.56 ±0.05
WHY: 6 ÷ 108 = 0.0556. Its yield to maturity is lower still, because the 8 paid over face value is lost by maturity.

Q: A bond bought at a discount has a 4% coupon. From highest to lowest, how do its three rates line up?
+ Yield to maturity, current yield, coupon rate
- Coupon rate, current yield, yield to maturity
- All three equal, as they would be for a bond at par
WHY: Bought under 100, it gains on the way to maturity, and only the yield to maturity counts that gain.

### The see-saw in numbers
A 10-year bond with a 5% coupon costs 100 at a 5% yield. At 4% it costs 108.11; at 6% it costs 92.64. One point of yield moved the price about 8% each way, and the rise was bigger than the fall.

Q: That 10-year 5% bond goes from a 5% yield to 6%. By what percentage does its price fall?
= 7.36 ±0.05
WHY: From 100 to 92.64 is a fall of 7.36%. The fall to 4% would have been a gain of 8.11%.

HERE: The game has no bond quotes and no yields to read. Its one rate is the policy rate set by the Reserve Board, shown on the Calendar page. When a rate decision surprises upwards, the bond fund BOND tends to slip: the same see-saw.

## Duration in numbers {duration-maths} [6]
SUMMARY: Work out Macaulay and modified duration, and use them to estimate how far a bond's price moves, in percent and in MB, when its yield changes.

### The average wait
**Macaulay duration** is the average time until a bond's money arrives, each year weighted by its share of the price: the present value of that year's payment ÷ the price. A 3-year 5% bond priced at 100 at a 5% yield gets 4.76% of its value in year 1, 4.54% in year 2 and 90.70% in year 3.

Q: Using those weights, what is that bond's Macaulay duration, in years?
= 2.86 ±0.02
WHY: 1 × 0.0476 + 2 × 0.0454 + 3 × 0.9070 = 2.86 years: a little under the 3-year maturity, because the coupons come earlier.

### Coupons pull it shorter
Money that arrives early shortens the average wait. A zero-coupon bond pays everything at the end, so its Macaulay duration is its maturity. Bigger coupons shorten it: over 10 years at a 5% yield, a 2% coupon gives about 9.0 years and an 8% coupon about 7.5.

Q: What is the Macaulay duration of a 7-year zero-coupon bond, in years?
= 7 ±0.01
WHY: Its one payment comes in year 7, so all the weight sits there.

Q: Two 10-year bonds have the same yield. Which has the longer duration?
+ The one with the 2% coupon
- The one with the 8% coupon
- Neither: equal maturities give equal durations
WHY: A smaller coupon puts more of the value at the end, so the average wait is longer.

### Modified duration
To turn the wait into a price sensitivity, divide by one plus the yield: **modified duration = Macaulay duration ÷ (1 + yield)**. For the 3-year bond, 2.86 ÷ 1.05 = 2.72. Then **price change ≈ −modified duration × change in yield**.

Q: A bond's Macaulay duration is 8.4 years and its yield is 5%. What is its modified duration?
= 8 ±0.02
WHY: 8.4 ÷ 1.05 = 8.0.

Q: A bond has a modified duration of 7. Its yield rises by half a percentage point. About how much does its price change, in percent?
= -3.5 ±0.05
WHY: −7 × 0.5 = −3.5%.

### In MB
Duration also sizes a loss. 20,000 MB of bonds with a modified duration of 5 lose about 5% of 20,000, or 1,000 MB, if yields rise one point. For small moves the estimate is close: for the 3-year bond and a 0.1-point rise, both the estimate and the exact sum give a fall of 0.27%.

Q: You hold 30,000 MB of bonds with a modified duration of 4. Yields fall by 1 percentage point. About how much does the holding gain, in MB?
= 1200 ±1%
WHY: 4 × 1% = 4%, and 4% of 30,000 is 1,200 MB.

HERE: Meme Street's BOND is described as a short-duration government bond fund, and it is built to move little. The game does not publish a duration for it.

## Convexity {convexity} [6]
SUMMARY: See where duration's straight line goes wrong on big moves, add the convexity correction, and learn why bond prices rise more than they fall.

### A curve, not a line
Duration draws a straight line: each point of yield costs the same. The real link between price and yield is a curve. For small moves the line and the curve agree. For big ones they part, and for an ordinary bond the line gives too low a price both ways.

Q: A 10-year zero-coupon bond at a 5% yield has a modified duration of 9.52. Yields jump 2 points. What fall does duration alone predict, in percent?
= 19.05 ±0.1
WHY: 9.52 × 2 = 19.05%. The exact fall is 17.2%: the straight line overstates it.

### The correction
The second-order estimate adds **convexity**: price change ≈ −D × Δy + ½ × C × Δy², with Δy as a decimal (2 points = 0.02). The 10-year zero has a convexity of about 100: ½ × 100 × 0.02² = 0.02, or +2%. The estimate becomes −17.05%, against an exact −17.2%.

Q: A bond has a modified duration of 8 and a convexity of 80. Yields rise 1 point. What is the estimated price change, in percent?
= -7.6 ±0.05
WHY: −8 × 0.01 + ½ × 80 × 0.01² = −0.08 + 0.004 = −0.076, or −7.6%.

Q: Why does the convexity term add to the price whether yields rise or fall?
+ The change in yield is squared, so its sign drops out
- Convexity flips its sign with the move in yield
- Duration counts the fall, and this term the rise
WHY: Δy² is positive for a rise and for a fall, so a positive convexity always lifts the estimate.

### Up more than down
So equal moves in yield are not equal in price. The 10-year zero gains 21.2% if yields fall 2 points and loses 17.2% if they rise 2. For a fixed-coupon bond with no early-repayment feature, the gain from a fall in yield beats the loss from an equal rise.

Q: The bond with a duration of 8 and a convexity of 80 sees yields fall 1 point instead. What is the estimated price change, in percent?
= 8.4 ±0.05
WHY: +0.08 + 0.004 = +0.084: a gain of 8.4%, bigger than the 7.6% loss for a 1-point rise.

Q: The 10-year zero loses 17.2% when yields rise 2 points. What happens when they fall 2 points?
- It gains 17.2%, the mirror of the loss
+ It gains more than 17.2%
- It gains less, as face value caps the price
WHY: Positive convexity: the price curve steepens as yields fall, so the gain, 21.2%, beats the loss.

### When it matters
Convexity is larger for longer maturities, lower coupons and lower yields, and its term grows with the square of the move. On the 10-year zero, a 0.1-point move leaves duration alone out by about 0.005 points. For long bonds and big moves it is a large part of the answer.

Q: For which holding does the convexity term matter most?
- A 1-year bond after a move of 0.1 points
- A 5-year bond after a move of 0.25 points
+ A 30-year zero after a 2-point move
WHY: Convexity grows with maturity, and its term with the square of the move: long bond, big move.

HERE: Meme Street has no bonds to measure, but a bought call on Meme Street is convex in the same way: its value rises faster as the share climbs than it falls as the share drops, and it can lose no more than its premium.

## Credit spreads and default {credit-spreads} [6]
SUMMARY: Read a company's yield over its government's, put a number on the expected loss from default, and know where investment grade ends.

### The spread
A company is less sure to pay than its government, so its bonds yield more. The gap between the two yields, at the same maturity, is the **credit spread**. It is quoted in **basis points**, hundredths of a percentage point: a gap of 1% is 100 basis points.

Q: A company's 5-year bond yields 6.5% and the government's 5-year bond yields 4.25%. What is the credit spread, in basis points?
= 225 ±1
WHY: 6.5 − 4.25 = 2.25 percentage points, or 225 basis points.

### Expected loss
Lenders put a number on default with **expected loss = probability of default × loss given default**. Loss given default is the share not recovered: a defaulted bond that returns 40 of its 100 has a loss given default of 60%. Times the amount lent, it gives the expected loss in money.

Q: You lend 10,000 MB to a company with a 3% chance of default this year and a loss given default of 60%. What is the expected loss, in MB?
= 180 ±1
WHY: 10,000 × 0.03 × 0.6 = 180 MB.

Q: Two bonds have the same chance of default. One is expected to recover 70 of its 100, the other 20. Which has the larger expected loss?
+ The one expected to recover 20
- The one expected to recover 70
- Neither, as the chance of default is equal
WHY: Loss given default is 80% against 30%, so with the same chance of default the expected loss is far bigger.

### More than the expected loss
If expected loss were the whole story, the spread would equal it. It does not: a 2001 study found expected default losses can explain less than 20% of the spread. The rest pays for bearing risk, for bonds that are harder to sell, and in the US for state taxes.

TIP: The study is Elton, Gruber, Agrawal and Mann, "Explaining the Rate Spread on Corporate Bonds", Journal of Finance, 2001, summarised in a 2004 Economic Letter of the Federal Reserve Bank of San Francisco.

Q: A bond's spread is 300 basis points and its expected default loss is 50 basis points a year. What does most of the rest pay for?
+ Risk, poorer liquidity and taxes
- Inflation, which only company bonds suffer
- The government's own chance of default
WHY: Expected losses explain only part of a spread. The rest pays for risk, for a bond that is harder to sell, and, in the US, for state taxes.

### Where investment grade ends
The rating ladder from the Analysts and credit ratings lesson splits at one rung. **Investment grade** is BBB− or higher on two agencies' scales and Baa3 or higher on the third. Anything lower is **high yield**, and pays a wider spread.

TIP: BBB− is the lowest investment grade at S&P and Fitch; Baa3 is the lowest at Moody's.

Q: A bond is rated BB+ by one agency. Where does it sit?
- At the lowest rung of investment grade
+ One rung under investment grade, in high yield
- In default, since it is rated below BBB
WHY: BBB− is the lowest investment-grade rung. BB+ is the next one down, the top of high yield.

### Recessions widen spreads
Credit spreads tend to widen in recessions and shrink in expansions. In bad times lenders ask for more pay for the same risk, so a company's borrowing gets dearer just when its business is weakest.

Q: A recession begins. What usually happens to the gap between company and government bond yields?
+ It widens, as lenders want more pay for the risk
- It narrows, as rates are cut for every borrower
- It stays fixed, since ratings move only slowly
WHY: Spreads tend to widen in recessions and shrink in expansions.

HERE: Meme Street has no company bonds, so there is no spread to read. Six fictional banks rate every company from D to AAA, and when a company goes bankrupt its shareholders are paid a fraction of the last price: the game's version of a recovery.
