# Valuing a company {valuing}
What a share is worth on paper: its dividends discounted to today, a discounted cash flow model step by step, the discount rate behind it, why most of the value sits far in the future, and buying with a margin of safety. Advanced.
TIER: pro

## The dividend discount model {dividend-model} [6]
SUMMARY: Value a share as the dividends it will pay, discounted to today, and see why the simple formula blows up when growth nears the discount rate.

### Money later is worth less
Money paid later is worth less than money now, because money now could earn a return in the meantime. To find what a future payment is worth today, divide it by (1 + r) once for every year you wait, where r is the return you require. It is the same discounting as a bond: 105 MB in a year, at 5%, is worth 100 MB today.

Q: A share will pay a dividend of 2 MB in one year. You require 8% a year. What is that dividend worth today, in MB?
= 1.85 ±0.01
WHY: 2 ÷ 1.08 = 1.85.

### A share is its dividends
An owner who never sells collects the dividends, and anyone who buys from them later pays for the dividends still to come. So a share is worth every future dividend, each discounted to today and added up. This is the **dividend discount model**, first set out in a 1938 book.

Q: In the dividend discount model, what does a share's value depend on?
+ The dividends still to come, each discounted to today
- The dividends it has paid over the past ten years
- The price other buyers paid for it last quarter
WHY: Only payments still to come are worth anything to a buyer today.

### Constant growth
If the dividend grows at the same rate every year for ever, the sum shrinks to one line: **P = D1 ÷ (r − g)**. D1 is next year's dividend, r the return you require and g the growth rate. A share paying 2 MB next year, with r of 8% and g of 3%, is worth 2 ÷ 0.05 = 40 MB.

Q: Next year's dividend is 3 MB, you require 9% a year, and the dividend grows 4% a year for ever. What is the share worth, in MB?
= 60 ±0.5
WHY: 3 ÷ (0.09 − 0.04) = 3 ÷ 0.05 = 60.

Q: This year's dividend was 2 MB and it grows 4% a year. Which dividend goes on top of the formula?
- 2 MB, the dividend this year's owners were paid
+ 2.08 MB, next year's dividend
- 1.92 MB, this year's dividend less the growth
WHY: The formula wants D1, the next payment: 2 × 1.04 = 2.08.

### Where it breaks
The gap r − g sits underneath. Keep r at 8% and the 2 MB dividend is worth 67 MB at 5% growth, 100 MB at 6%, 200 MB at 7% and 400 MB at 7.5%. As g nears r the value runs off to infinity. So g must be a rate the company could keep up for ever, and that means a modest one.

Q: You value a share with r of 8% and plug in g of 8.5%. What does the formula give?
+ A negative price: the model does not apply
- A very high price, the mark of a great growth company
- The price the share should reach in about eight years
WHY: r − g is negative, so the answer is negative. The constant-growth form needs g below r.

### Turned around
Read backwards, the same line gives the return a price offers: **r = D1 ÷ P + g**, the dividend yield plus the growth. A share at 50 MB paying 2 MB next year and growing 4% offers 4% + 4% = 8% a year.

Q: A share costs 30 MB, pays 1.5 MB next year, and its dividend grows 3% a year. What return does the price offer, in percent a year?
= 8 ±0.1
WHY: 1.5 ÷ 30 = 5%, plus 3% growth: 8%.

HERE: Dividend payers on Meme Street show the year's dividend per share and the yield on their page. The dividend is reset at each quarterly report and follows the company's margin: raised, cut or suspended. Nothing promises it a growth rate, so any g you use is your own forecast.

TIP: The dividend discount model is from John Burr Williams, The Theory of Investment Value, 1938. The constant-growth form is named after Myron Gordon, who published it with Eli Shapiro in 1956.

## A DCF, step by step {dcf-steps} [6]
SUMMARY: Build a discounted cash flow valuation in five steps, from free cash flow to a value per share, on a small worked example.

### Cash instead of dividends
Many companies pay small dividends or none, and return cash through buybacks or keep it to grow. So the usual model values the cash the business produces. The fundamentals unit sketched the idea; this lesson does the sum.

### Step 1: free cash flow
**Free cash flow** is the cash a business makes from its operations minus what it spends on equipment and buildings (capital spending). It is what could be paid out to lenders and shareholders without shrinking the business.

Q: A company's cash from operations is 120 million MB and its capital spending is 45 million MB. What is its free cash flow, in millions of MB?
= 75 ±0.5
WHY: 120 − 45 = 75.

Q: Why does a DCF start from free cash flow rather than net income?
- Net income is not audited, so it cannot be trusted
+ It counts equipment spending when the cash goes out
- Free cash flow is always higher, so the value is fairer
WHY: Profit spreads the cost of equipment over years. Free cash flow counts it when it is paid, which is what an owner could really take out.

### Step 2: forecast a few years
Write down the free cash flow for each of the next five years or so. Our example company made 10 million MB last year, and we forecast 6% growth a year: 10.6, 11.2, 11.9, 12.6 and 13.4 million.

Q: Why does the year-by-year forecast usually stop after about five years?
+ Further out, yearly guesses are no better than one steady rule
- Accounting rules forbid forecasts longer than five years
- Cash flows after five years are worth nothing today
WHY: Detail far ahead is false precision. Later years still count, through the terminal value.

### Step 3: a terminal value
After year 5, assume steady growth at a low rate for good, and value all of it at once with the constant-growth line: **TV = year 6 cash flow ÷ (r − g)**. At r of 9% and g of 2%: 13.4 × 1.02 ÷ 0.07 = 195 million MB, valued at year 5.

Q: Year 5's free cash flow is 8 million MB. After that it grows 3% a year for ever, and the discount rate is 10%. What is the terminal value, in millions of MB?
= 117.7 ±1
WHY: 8 × 1.03 ÷ (0.10 − 0.03) = 8.24 ÷ 0.07 = 117.7.

### Step 4: discount everything
Divide each year's cash by 1.09 once per year, and the terminal value by 1.09 five times. The total is the value of the whole business, its **enterprise value**.

| Year | Cash flow | Discount factor at 9% | Worth today |
| 1 | 10.6 | 0.917 | 9.7 |
| 2 | 11.2 | 0.842 | 9.5 |
| 3 | 11.9 | 0.772 | 9.2 |
| 4 | 12.6 | 0.708 | 8.9 |
| 5 | 13.4 | 0.650 | 8.7 |
| Terminal value | 195.0 | 0.650 | 126.7 |
| Total | | | 172.8 |

Q: A terminal value of 100 million MB is reached at the end of year 3. At 10% a year, what is it worth today, in millions of MB?
= 75.1 ±0.5
WHY: 100 ÷ 1.1³ = 100 ÷ 1.331 = 75.1.

### Step 5: from the business to a share
Enterprise value belongs to lenders and shareholders together. Take off net debt (debt minus cash), then divide by the number of shares. With net debt of 20 million MB and 5 million shares: (172.8 − 20) ÷ 5 = 30.6 MB a share.

Q: A DCF gives an enterprise value of 150 million MB. Net debt is 30 million MB and there are 4 million shares. What is the value per share, in MB?
= 30 ±0.2
WHY: (150 − 30) ÷ 4 = 30.

HERE: Meme Street's company pages have no cash flow statement. They show revenue, net margin, net income, earnings per share, cash, debt and the share count, so net income is the nearest stand-in for free cash flow. Revenue and margins change only with the company's news: nothing builds growth in.

## The discount rate {cost-of-capital} [6]
SUMMARY: Work out the rate a DCF discounts at: the cost of equity, the cost of debt after tax, and their weighted average.

### What r stands for
The discount rate is the return investors could expect elsewhere for the same risk. For the company it is a cost: what it must offer to raise the money. Riskier businesses face higher rates, and a higher rate means a lower value today.

Q: Two companies are forecast to produce the same cash flows, but one is far riskier. How do their DCF values compare?
+ The riskier one is worth less: its cash is discounted harder
- The riskier one is worth more, as risk is paid with return
- They are worth the same, since the cash flows are the same
WHY: Same cash, higher discount rate, lower value today. Buyers pay less now in order to expect more back.

### The cost of equity
Shareholders' required return is usually estimated with the capital asset pricing model (CAPM): the risk-free rate plus beta times the market's extra return over it. With a risk-free rate of 4%, a beta of 1.2 and a market premium of 5%: 4 + 1.2 × 5 = 10%.

Q: The risk-free rate is 3%, a company's beta is 0.8 and the market premium is 5%. What is its cost of equity, in percent?
= 7 ±0.1
WHY: 3 + 0.8 × 5 = 7.

HERE: Every Meme Street stock page shows its beta, as "x the market". MB cash earns no interest, so the game's risk-free rate is 0%: the cost of equity is just beta times the premium you ask of the market.

### The cost of debt, after tax
Lenders ask less than shareholders, since they are paid first. Interest is also taken off profit before tax is charged, which makes debt cheaper still: the cost after tax is the interest rate × (1 − the tax rate). A 6% loan at a 25% tax rate costs 4.5%.

Q: A company borrows at 8% and pays tax at 25%. What is its cost of debt after tax, in percent?
= 6 ±0.1
WHY: 8 × (1 − 0.25) = 6.

### The weighted average
The **weighted average cost of capital** (WACC) mixes the two by how much of each the company uses, at market values. Shares worth 600 million MB at 10% and debt of 400 million MB at 4.5% after tax give 0.6 × 10 + 0.4 × 4.5 = 7.8%.

Q: Equity worth 750 million MB costs 11%. Debt of 250 million MB costs 6% before tax, and tax is 20%. What is the WACC, in percent?
= 9.45 ±0.05
WHY: Debt after tax is 6 × 0.8 = 4.8%. Then 0.75 × 11 + 0.25 × 4.8 = 8.25 + 1.2 = 9.45.

Q: Which weights go into the WACC?
- The amounts raised when the shares and debt were first issued
+ What the shares and the debt are worth today
- An even split, half equity and half debt, for every company
WHY: The weights are market values: what investors could get for each slice now.

### More debt is no free lunch
Debt is the cheaper slice, so borrowing more seems to lower the WACC. But each extra loan makes the shares riskier, and their cost rises; past some point lenders charge more too. A 1958 paper showed that, leaving taxes aside, the mix alone does not change a company's value.

Q: A company swaps shares for cheap debt to cut its WACC. What does finance theory say happens next?
- Its value keeps rising, since every loan is cheaper than equity
- Its lenders cut their rate, since the company is now larger
+ Its shares become riskier and their cost rises
WHY: More debt puts more risk on each share. The tax saving on interest is the lasting gain, and too much debt brings its own costs.

TIP: The 1958 paper is Modigliani and Miller, "The Cost of Capital, Corporation Finance and the Theory of Investment", American Economic Review.

## Where the value hides {terminal-value} [6]
SUMMARY: See how much of a DCF sits in the terminal value, how far one point on growth or the discount rate moves it, and why a careful answer is a range.

### Most of it is far away
In the worked DCF two lessons back, the five forecast years are worth 46 million MB today and the terminal value 127 million: 73% of the total. Practitioners' guides put the usual share at around three-quarters. Most of a DCF rests on what happens after the forecast ends.

Q: The forecast years are worth 40 million MB today and the terminal value 120 million MB today. What share of the value is the terminal value, in percent?
= 75 ±0.5
WHY: 120 ÷ (40 + 120) = 0.75.

### One point on the gap
The terminal value divides by r − g. At a gap of 5 points it is 20 times next year's cash, and at 4 points it is 25 times. Closing the gap by one point lifts the terminal value by a quarter.

Q: A terminal value uses r of 9% and g of 3%. An analyst raises g to 4%, with next year's cash unchanged. By what percentage does the terminal value rise?
= 20 ±0.5
WHY: 1 ÷ 0.06 = 16.7 times; 1 ÷ 0.05 = 20 times. 20 ÷ 16.7 = 1.2.

### The table
Run the same example at other inputs and the value per share fills a table. The middle cell is the 30.6 MB found before.

| Discount rate | g of 1% | g of 2% | g of 3% |
| 8% | 31.7 | 36.4 | 43.0 |
| 9% | 27.2 | 30.6 | 35.1 |
| 10% | 23.6 | 26.1 | 29.4 |

Q: In the table, the discount rate falls from 9% to 8% with growth at 2%. By about what percentage does the value per share rise?
= 19 ±1
WHY: 36.4 ÷ 30.6 = 1.19.

Q: Which change in the table moves the value more, starting from the middle cell?
+ The discount rate down one point, to 8%
- Growth up one point, to 3%
- Both move it by the same amount
WHY: 9% to 8% gives 36.4 MB, up 19%. Growth to 3% gives 35.1 MB, up 15%.

### A range, not a number
One point either way on both inputs spans 23.6 to 43.0 MB: 23% below the middle to 41% above. Nobody knows those inputs to a point, so an honest DCF is a range. A better use is to turn it round: ask what growth the price already assumes.

Q: A share is at 50 MB, next year's cash per share is 2.5 MB, it is all paid out, and you require 9%. What growth a year does the price assume, in percent?
= 4 ±0.1
WHY: g = r − D1 ÷ P = 9% − 5% = 4%.

Q: A friend's DCF says a share is worth exactly 30.55 MB. What is the honest way to report it?
- As 30.55 MB, since every step of the sum was done with care
+ As a range, with the inputs that produce each end
- As 31 MB, rounded so the reader is not distracted
WHY: Small, unknowable changes in r and g move the answer by a third or more.

HERE: Meme Street shows earnings per share and the live P/E for every company. Earnings ÷ price is the cash yield if all profit were paid out, so the rate you require minus that yield is the growth the price assumes.

TIP: The three-quarters figure is from Wall Street Prep's guide to terminal value.

## Margin of safety and the moody market {margin-of-safety} [6]
SUMMARY: Buy well below a careful estimate because the estimate can be wrong, treat the market's daily price as an offer you may refuse, and see how this differs from trading a chart.

### Room for being wrong
A valuation is an estimate with a wide error. The **margin of safety** is the gap between that estimate and the price you pay. Buy at 35 MB a share you value at 50 MB, and the estimate can be 30% too high before you have overpaid.

Q: You value a share at 80 MB and insist on a 25% margin of safety. What is the most you will pay, in MB?
= 60 ±0.5
WHY: 80 × (1 − 0.25) = 60.

Q: You bought at 42 MB a share you value at 60 MB. By what percentage can your estimate be too high before you have overpaid?
= 30 ±0.5
WHY: 1 − 42 ÷ 60 = 0.3.

### How wide a margin
Value investors ask a small discount of steady, well-understood businesses and a large one of uncertain ones: commonly about 10% for the first, and up to half for the speculative. The wider the DCF range from the last lesson, the wider the margin it calls for.

Q: Which share needs the widest margin of safety?
- A steady utility whose DCF range runs from 45 to 52 MB
+ A young company whose DCF range runs from 20 to 60 MB
- A large food maker whose DCF range runs from 38 to 46 MB
WHY: The wider the range of honest estimates, the more room you need for being wrong.

### The moody partner
A 1949 book pictured the market as a business partner who names a price for your share every day, offering to buy yours or sell you his. Some days he is gloomy and asks too little, some days euphoric and asks too much. You are free to ignore him: he will be back tomorrow.

Q: A share you value at 50 MB falls from 48 to 36 MB in a week, with no news about the business. What does the parable suggest?
- Sell at once, before the price falls any further
- Lower your estimate to 36 MB, since price is value
+ Weigh his offer: his mood fell, not the business
WHY: The parable separates price from value. A lower price is a chance to buy, if your estimate survives a second look.

### Unlike a chart trade
A chart trader asks where the price goes next and leaves at a stop when it goes the other way. A value buyer asks what the business is worth and holds while the price is below that, sometimes for years. A falling price is the first one's exit and may be the second one's chance to add.

Q: A trade hits its stop, and instead of selling you call it a long-term value holding. What has gone wrong?
+ The exit was dropped for a reason made up afterwards
- Nothing, since a falling stock always becomes good value in time
- The stop itself, since no good trader ever uses one
WHY: A value case is made before buying, from the business. A losing trade does not become one by a new label.

HERE: On Meme Street a company's figures change with the stories that already moved its price, so the P/E tends to stay steady. A cheap-looking number is where the question starts, not the answer.

TIP: The moody partner is Mr. Market, from Benjamin Graham's The Intelligent Investor (1949). The term margin of safety comes from Graham and Dodd's Security Analysis (1934).
