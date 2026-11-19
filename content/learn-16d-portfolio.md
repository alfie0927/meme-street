# Portfolio theory {portfolio}
How to combine stocks and cash the way the textbooks teach it: the risk of a mix, the best mixes, the line that prices risk, which risk is paid for, and how efficient markets really are. Advanced.
TIER: pro

## Two stocks in one portfolio {two-asset-mix} [6]
SUMMARY: Work out the return and the risk of a mix of two stocks, and see why the risk comes out below the average whenever they do not move in lockstep.

### Return: a plain average
Put 60% of the money in a stock expected to make 12% a year and 40% in one expected to make 4%. The mix is expected to make 0.6 × 12 + 0.4 × 4 = 8.8%. The expected return of a mix is always the weighted average of its parts.

Q: You put 70,000 MB in a stock expected to return 10% a year and 30,000 MB in one expected to return 5%. What is the mix expected to return, in percent?
= 8.5 ±0.05
WHY: 0.7 × 10 + 0.3 × 5 = 8.5.

### Risk: not an average
Risk here is volatility, the standard deviation of returns. With weights a and b, volatilities σA and σB and correlation ρ, the mix has **σ² = a²σA² + b²σB² + 2abρσAσB**. Only the last term depends on how the two move together. The correlation lesson showed five banks acting as one bet: this is the arithmetic behind it.

Q: Which part of the formula changes when the correlation between the two stocks changes?
+ The last term, 2abρσAσB
- The first term, a²σA², and nothing else
- Both squared terms, a²σA² and b²σB²
WHY: Only the cross term contains ρ. The squared terms are each stock's own risk, scaled by its weight.

### Three correlations
Take two stocks with 20% volatility each and half the money in each. At a correlation of +1 mixing does nothing. At 0 the risk falls by almost a third. At −1 the two cancel exactly: a perfect hedge, which real stocks almost never offer.

| Correlation | Risk of the 50/50 mix |
| +1 | 20% |
| 0 | 14.1% |
| −1 | 0% |

Q: You put 60% in a stock with 30% volatility and 40% in one with 10% volatility. Their correlation is 0.2. What is the volatility of the mix, in percent?
= 19.2 ±0.2
WHY: √(0.36 × 900 + 0.16 × 100 + 2 × 0.6 × 0.4 × 0.2 × 30 × 10) = √368.8 = 19.2, below the weighted average of 22.

### Why mixing pays
Below a correlation of +1, the risk of a mix is always less than the weighted average of the two risks, while its expected return is exactly the weighted average. Less risk for the same expected return: that is the whole case for diversification.

Q: Two stocks have the same expected return and the same volatility, with a correlation of 0.3. Compared with holding just one, what does a 50/50 mix give?
+ The same expected return with less risk
- A higher expected return with the same risk
- Less risk, paid for with a lower expected return
WHY: Returns average. With a correlation under 1, risk comes out below the average.

Q: Which pair cuts risk the most when mixed 50/50, if their volatilities are equal?
- Two stocks from one industry, correlation 0.8
+ Two stocks with a correlation of 0.1
- Two stocks that moved together every day last month
WHY: The lower the correlation, the smaller the cross term, and the lower the mix's risk.

HERE: Each stock page on Meme Street gives the stock's volatility a year and its beta to the market. The game shows no correlations: compare two charts over the same weeks, or a stock with its sector index, to judge how closely they move.

## The efficient frontier {efficient-frontier} [6]
SUMMARY: Find the mix with the least risk, see why some portfolios are never worth holding, and why the best ones lie along a curve.

### A riskier stock can cut risk
Stock A is expected to return 6% with 10% volatility. Stock B is expected to return 10% with 20% volatility. Their correlation is 0. Put 80% in A and 20% in B, and the mix is expected to return 6.8% with 8.9% volatility: more return than A alone, and less risk.

Q: With the same two stocks, you put 70% in A and 30% in B. What is the volatility of the mix, in percent?
= 9.22 ±0.1
WHY: √(0.49 × 100 + 0.09 × 400) = √85 = 9.22. The correlation is 0, so there is no cross term.

### The minimum-variance mix
For two stocks there is one mix with the least possible risk. With a correlation of 0, the share in A is σB² ÷ (σA² + σB²): here 400 ÷ 500 = 80%. Holding more A than that adds risk and gives up return at the same time.

Q: Two uncorrelated stocks have volatilities of 10% and 30%. What share should go in the calmer one for the least risk, in percent?
= 90 ±0.5
WHY: 30² ÷ (10² + 30²) = 900 ÷ 1,000 = 0.9.

### Dominated mixes
A portfolio is **dominated** when another one offers more expected return for the same or less risk. Nobody who cares about return and risk should hold it. Stock A on its own is dominated by the 80/20 mix above.

Q: Three portfolios: P returns 8% with 12% risk, Q returns 7% with 14% risk, and R returns 9% with 16% risk. Which is dominated?
- P, because it has the lowest return per point of risk
+ Q, since P has more return and less risk
- R, because it carries the most risk of the three
WHY: P beats Q on both counts. R is riskier but pays more, so it is a choice, not a mistake.

### The frontier
With many stocks, every possible mix is a dot on a chart of risk against expected return. The dots fill a region whose left edge bends in a curve. The upper half of that edge, from the minimum-variance mix upwards, is the **efficient frontier**: the most return for each level of risk. This picture comes from a 1952 paper.

Q: Where do the efficient portfolios lie on a chart of risk against expected return?
- Along the lower edge, where each return comes with the least risk
+ On the upper edge, from the minimum-variance mix up
- On a straight line from the calmest stock to the wildest
WHY: Every point on the lower half of the curve has a point directly above it with the same risk and more return.

TIP: The 1952 paper is Markowitz, "Portfolio Selection", Journal of Finance.

### Only as good as its inputs
A frontier is drawn from estimates: returns, volatilities and correlations taken from the past. Each carries error, and correlations rise in a sell-off. Treat the exact weights it gives as a rough guide.

Q: A program drew your frontier from the last three calm months. What is the main danger?
+ Its correlations will be too low for the next sell-off
- Its weights will be too cautious, since calm months overstate risk
- It can only be used on two stocks at a time
WHY: Correlations measured in calm months understate how much stocks move together when the market falls.

HERE: Meme Street has no frontier tool, but the inputs are there: each stock page gives the volatility, and the MSI 50 and the sector indices show how groups of stocks moved together.

## Mixing with cash {capital-allocation} [6]
SUMMARY: Combine a risk-free asset with a risky portfolio, read the straight line they make, and set your risk with the cash share rather than by picking riskier stocks.

### A straight line
Cash at a safe rate rf has no risk. Put a share y of the money in a risky portfolio with expected return E and volatility σ, and the rest in cash. Then the mix returns rf + y × (E − rf) with risk y × σ. Every such mix lies on one straight line, the **capital allocation line**.

Q: The safe rate is 2%. A portfolio is expected to return 8% with 16% volatility. You put 60% in it and 40% in cash. What is the expected return of the mix, in percent?
= 5.6 ±0.05
WHY: 2 + 0.6 × (8 − 2) = 5.6, with 0.6 × 16 = 9.6% risk.

### The slope is the Sharpe ratio
Each point of risk along the line adds (E − rf) ÷ σ of expected return. That is the Sharpe ratio from the lesson on performance statistics. For the portfolio above it is 6 ÷ 16 = 0.375: every 1% of risk pays 0.375% of expected return.

Q: A portfolio is expected to return 11% with 18% volatility, and the safe rate is 2%. What is its Sharpe ratio?
= 0.5 ±0.01
WHY: (11 − 2) ÷ 18 = 0.5.

### The steepest line wins
Portfolio X: 10% with 20% risk. Portfolio Y: 7% with 10% risk. With a safe rate of 2%, X's line has a slope of 0.4 and Y's 0.5. Hold Y twice over, borrowing at the safe rate, and you get 12% at 20% risk: more than X at the same risk. The best risky portfolio is the one with the steepest line.

Q: Two portfolios at the same safe rate have Sharpe ratios of 0.3 and 0.5. You want 10% risk. Which do you build it from?
+ The 0.5 one, with cash or borrowing to reach 10% risk
- The 0.3 one, if it already has exactly 10% risk alone
- Whichever has the higher expected return before mixing
WHY: The steeper line gives more return at every level of risk, 10% included. In the model borrowing costs the safe rate; real borrowing costs more.

### Dial risk with cash
So the risky mix is chosen once, for its slope, and your appetite for risk sets only the cash share. A cautious investor and a bold one hold the same risky portfolio in different amounts. Swapping into wilder stocks to get more risk usually moves you onto a flatter line.

Q: A 100,000 MB account wants 10% volatility, using an index with 20% volatility and cash. How many MB go in the index?
= 50000 ±1%
WHY: 10 ÷ 20 = 0.5 of the account in the index: 50,000 MB.

Q: You want less risk than your portfolio now carries. What does this lesson suggest?
- Swap your stocks for calmer ones that also pay less
+ Keep the same mix and hold more of the account in cash
- Move everything into one calm stock with a high dividend
WHY: Cash scales the risk down along the same line. Changing the mix risks moving onto a flatter one.

HERE: On Meme Street cash earns no interest, so the safe rate is 0% and the line starts at zero: 40,000 MB in the MSI 50 and 60,000 MB in cash carries 40% of the index's risk and 40% of its expected gain. Borrowing is leverage, which needs the Pro pass and charges interest.

## The CAPM and the security market line {capm} [6]
SUMMARY: Price risk with the capital asset pricing model, read the security market line, and see what decades of data say about it.

### One formula for every asset
If every investor held the same best risky portfolio, it would have to be the whole market. The **capital asset pricing model** (CAPM) follows from that: expected return = rf + β × (market return − rf). A stock is paid for its beta alone. The alpha and beta lesson used the same beta to split a return.

Q: The safe rate is 2% and the market is expected to return 8%. What does the CAPM expect from a stock with a beta of 1.5, in percent?
= 11 ±0.1
WHY: 2 + 1.5 × (8 − 2) = 11.

TIP: The CAPM is usually credited to Sharpe, "Capital Asset Prices", Journal of Finance, 1964, with Treynor, Lintner and Mossin.

### The security market line
Plot expected return against beta and the CAPM is a straight line, the **security market line**. It starts at the safe rate, at a beta of 0, and passes through the market, at a beta of 1. Its slope is the market's extra return over the safe rate.

Q: The safe rate is 3% and the market is expected to return 7%. What does the CAPM expect from a stock with a beta of 0.5, in percent?
= 5 ±0.1
WHY: 3 + 0.5 × (7 − 3) = 5.

### Above and below the line
A stock expected to return more than the line asks for its beta sits above it: by the model it is cheap, with a positive alpha. One below the line is dear. In the model, buyers push a cheap stock's price up and its expected return down until it sits on the line.

Q: The safe rate is 2% and the market is expected to return 8%. A stock with a beta of 0.8 is expected to return 9%. Where does it sit?
+ Above the line, with an alpha of about 2.2%
- On the line, since 9% is close to the market's 8%
- Below the line, because its beta is under 1
WHY: The line asks 2 + 0.8 × 6 = 6.8%. The stock's 9% is 2.2 points above it.

Q: In the model, what happens to a stock that sits above the line?
- It stays there for good, as a reward for its extra risk
+ Buying lifts its price until its expected return falls to the line
- Sellers push it down until its beta rises to match its return
WHY: An expected return above the line is a bargain, and buying it away lowers the return still to come.

### The line is too flat
Real data fit the line poorly. A 1972 test on US stocks found the measured line too flat: low-beta stocks earned more than the model says, and high-beta stocks less.

Q: The measured line is flatter than the CAPM line. What does that mean for low-beta stocks?
+ They earned more than their beta alone predicts
- They earned less than their beta alone predicts
- Their betas were wrong and should be ignored
WHY: A flatter line sits above the CAPM line at low betas and below it at high betas.

### High beta, low alpha
A 2014 paper found high beta going with low alpha in US stocks, in 20 other stock markets, in government and company bonds and in futures. Its explanation: many investors cannot borrow, so to take more market risk they buy high-beta assets instead, and bid them up.

Q: By that explanation, why are high-beta stocks bid up?
+ For investors who cannot borrow, they are the way to take more risk
- Brokers stop small investors from buying low-beta stocks
- High-beta stocks pay larger dividends than other stocks
WHY: Without leverage, a high beta is the only way to a bigger bet on the market, so demand for it runs high.

TIP: The tests are Black, Jensen and Scholes, "The Capital Asset Pricing Model: Some Empirical Tests", 1972, and Frazzini and Pedersen, "Betting against Beta", Journal of Financial Economics, 2014.

HERE: On Meme Street the market is the MSI 50, and each stock page gives the beta (for example "1.20x the market"). Cash earns no interest, so the safe rate is 0% and the security market line starts at zero.

## Risk you can diversify and risk you cannot {systematic-risk} [6]
SUMMARY: Split a stock's risk into the part diversification removes and the part it cannot, see how fast the first falls, and why only the second is paid for.

### Two kinds of risk
A stock's moves have two sources. **Market risk** (systematic) comes from the whole market and is measured by beta. **Specific risk** (idiosyncratic) is the company's own: a product, a lawsuit, a bad quarter. They add as variances: total² = (β × market volatility)² + specific².

Q: A stock has a beta of 1.2, the market's volatility is 15%, and the stock's specific risk is 30%. What is its total volatility, in percent?
= 35 ±0.3
WHY: √(18² + 30²) = √1,224 = 35.0. Market risk is 1.2 × 15 = 18.

### Specific risk shrinks with numbers
Spread money equally over N stocks whose specific risks are unrelated, and the portfolio's specific risk falls to one stock's divided by √N. Market risk does not fall at all, because every stock carries it. Twenty stocks cut 30% of specific risk to 6.7%, and the total heads for the market floor.

Q: Each stock's specific risk is 30%, and the specific risks are unrelated. You hold 25 of them in equal amounts. What is the portfolio's specific risk, in percent?
= 6 ±0.1
WHY: 30 ÷ √25 = 30 ÷ 5 = 6.

Q: You hold 40 stocks, all with betas near 1.5. The market falls 20%. What do the 40 names protect you from?
+ Very little: a fall of about 30% is still expected
- Most of it, as losses on some are offset by gains on others
- Half of it, since 40 stocks halve the market risk
WHY: 1.5 × 20 = 30. Diversification removes specific risk only.

### How many stocks
A 1968 study measured how the risk of random portfolios fell as stocks were added. A widely held view said about 10 stocks capture nearly all the benefit. A 1987 paper disputed it: a well-diversified portfolio of randomly chosen stocks needs at least 30 stocks for an investor who borrows and 40 for one who lends.

Q: By the 1987 paper, what is the least number of randomly chosen stocks a lending investor needs?
- About 10, where the benefit was thought used up
+ About 40
- About 500, a whole market index
WHY: The paper's answer was at least 30 for an investor who borrows and 40 for one who lends.

TIP: The studies are Evans and Archer, Journal of Finance, 1968, and Statman, "How Many Stocks Make a Diversified Portfolio?", Journal of Financial and Quantitative Analysis, 1987.

### Only market risk is paid
Anyone can remove specific risk by owning more stocks, so in the CAPM nobody is paid to carry it. A concentrated bet on one company takes extra risk for no extra expected return. Only beta earns the premium.

Q: Two stocks have the same beta. One has twice the specific risk of the other. What does the CAPM expect from the riskier one?
+ The same expected return as the calmer stock
- A higher expected return, to pay for the extra risk
- A lower expected return, since its risk is easy to remove
WHY: In the model expected return depends on beta alone. Specific risk earns nothing.

HERE: Meme Street moves each company with the market (by its beta), with its industry and on its own news. Industry risk sits in between: five stocks from one sector share it. Over 150 companies and funds in 30 sectors are listed, so spread across sectors, not only across names.

## Efficient markets {market-efficiency} [6]
SUMMARY: Know the weak, semi-strong and strong forms of market efficiency, what each would rule out for a trader, and where the evidence leaves you.

### Prices that already know
A market is **efficient** when prices already reflect the available information, so nobody can earn more than their risk pays by using it. A 1970 review sorted the idea into three forms by how much information the price holds. In such a market, beating it for years is mostly luck.

Q: In an efficient market, what is the expected reward for trading on information everyone already has?
- A small, steady edge for whoever acts on it first
+ Only what the risk carried pays
- A return that grows the longer the position is held
WHY: Information already in the price cannot be used to earn more than the risk pays.

Q: A thousand fund managers each have an even chance of beating the market in any year. About how many beat it five years running by luck alone?
= 31 ±1
WHY: 1,000 × 0.5⁵ = 31.25. A five-year record proves little when a thousand people are trying.

TIP: The review is Fama, "Efficient Capital Markets: A Review of Theory and Empirical Work", Journal of Finance, 1970.

### The weak form
Prices hold everything in past prices and volume. If this holds, chart patterns and indicators cannot earn an edge after costs, because whatever the chart shows is already in the price. [Random or real?](/learn?l=random-walk) and [Do chart rules work?](/learn?l=chart-rule-evidence) weigh the evidence.

Q: If only the weak form holds, which approach loses its edge?
+ Buying when a short moving average crosses above a long one
- Buying shares after a careful study of the annual report
- Buying shares before unpublished results come out
WHY: The weak form covers past prices only. Public accounts and private news are outside it.

### The semi-strong form
Prices hold all public information: results, news, reports, the economy. If this holds, reading the accounts or trading the headline comes too late, because the price moved when the news came out. Only information others lack would help.

Q: A company beats its forecast and the price jumps within seconds. You buy a minute later. Under the semi-strong form, what edge do you have?
- The part of the jump the market has not yet priced
+ None: the news was in the price before you bought
- A small edge that grows the longer you hold the stock
WHY: The semi-strong form says public news is priced as it arrives.

### The strong form
Prices hold all information, private included. If this held, even company insiders could not profit from what they know. The evidence has generally not supported this form.

Q: Which finding would count against the strong form?
+ Insiders earning more on their own company's shares
- Index funds beating most actively managed funds
- Prices reacting within seconds to public news
WHY: The strong form says private information is already in the price, so insiders should earn nothing extra.

### The honest middle ground
Markets are close to efficient, not perfectly so. If prices held every piece of information, nobody would be paid to gather it. Small edges exist, they shrink once known, and costs eat most of them: [Famous anomalies](/learn?l=anomalies) shows it. The sound default is to treat a price as fair until a test says otherwise.

Q: What is the sensible working stance for a trader?
- Every price is wrong, so trade against the crowd
+ Treat prices as fair until a tested edge says otherwise
- No edge can ever exist, so there is no point testing
WHY: Close to efficient means edges are rare and small, not impossible. A test, not a hunch, decides.

HERE: Meme Street's prices follow its news and its price model, never the players' trades, and the market is built so that simple known tricks should not beat holding the MSI 50 after costs. Treat it as close to efficient: an edge here needs the same testing as anywhere.
