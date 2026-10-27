# How real markets work {real-markets}
Order books, market makers and high-frequency trading, corporate actions, brokers and regulation, and a general look at taxes.

## Market makers, order books and high-frequency trading {market-makers} [7]
SUMMARY: Where orders actually go, who is on the other side, and what the fastest traders do.
### The order book
An exchange keeps an **order book** for every stock: all the limit orders waiting to buy (bids) and to sell (asks), sorted by price.

| Bids (buyers) | Price | Asks (sellers) |
| | 100.04 | 900 |
| | 100.03 | 400 |
| | 100.02 | 1,200 |
| 500 | 100.00 | |
| 1,500 | 99.99 | |
| 2,000 | 99.98 | |

A market buy order for 1,500 shares takes the 1,200 at 100.02 and 300 of the 400 at 100.03: big orders "walk the book" and get a worse average price. That is **price impact**, and why big investors split orders over hours or days.

### Market makers
Firms that always quote both a bid and an ask, earning the spread in return for providing **liquidity**: someone is always there to trade with. They try not to hold big positions themselves, constantly adjusting their quotes.

### High-frequency trading (HFT)
Computer-driven firms trading in microseconds, from servers placed next to the exchange's own. Most act as market makers; others profit from tiny price differences between exchanges (arbitrage). They have made spreads much tighter for everyone; critics say they can withdraw liquidity just when it is needed, as in the 2010 "flash crash".

### Dark pools and order routing
Not every trade happens on a public exchange. Big orders often go to **dark pools** (private venues where orders are hidden until they trade), and many retail brokers route orders to market makers who pay for them (**payment for order flow**).

HERE: There is no order book: every trade is against the house at the displayed price, so no order, however big, moves the price or walks a book. That keeps the game fair for small and large accounts alike; in real markets, size and speed matter.

Q: Using the book above, a market order buys 1,500 shares. What is the worst price paid?
+ 100.03
- 100.02
- 100.04
WHY: It takes all 1,200 at 100.02 and then 300 at 100.03.
Q: How do market makers earn a living?
- From commissions on every trade
+ Mostly from the spread between their bid and ask
- From the exchange's profits
WHY: Buying at the bid and selling at the ask, many times a day.

## IPOs, splits, dividend dates and other corporate actions {corporate-actions} [7]
SUMMARY: The events that change a company's shares, and what each means for a holder.
### IPOs
A company sells shares to the public for the first time, at a price set with its banks. Real IPOs are often priced a little low, so the first day can "pop"; many then lag the market for years. Insiders are usually barred from selling for some months (the **lock-up**); when it ends, the price can sag.

### Stock splits
A 2-for-1 split doubles the number of shares and halves the price: nothing about the company changes, like cutting a pizza into more slices. Splits make shares cheaper to buy in round lots. A **reverse split** does the opposite, often for struggling companies whose price has fallen very low.

### Dividend dates
Declaration, ex-dividend (buy before it to receive the dividend; the price drops by about the dividend that morning), record date, payment date.

### Mergers and acquisitions
One company buys another, for cash or shares, usually at a **premium** to the market price. The target's shares jump towards the offer price; the buyer's often fall. A gap between the price and the offer remains until the deal closes, reflecting the risk it fails (traders who bet on deals closing do **merger arbitrage**).

### Spin-offs, rights issues and buybacks
- **Spin-off**: a company floats part of itself as a separate company, giving its shareholders shares in the new one.
- **Rights issue**: existing shareholders may buy new shares at a discount; those who do not take part are diluted.
- **Buybacks**: the company buys its own shares, raising earnings per share.

HERE: New companies list through **IPOs** about 15 times a game year, announced half an hour ahead, at their announced price with **no first-day pop**. When the market is full, the smallest company outside the MSI 50 is **taken over** for cash by the biggest in its industry, at the market price with **no premium** (a premium that always came would be free money for holding small companies). **There are no stock splits.** Companies do announce share **offerings** (more shares, no price move on their own) and **buybacks**, and dividend payers go ex-dividend five minutes after their report.

Q: A stock at 80 splits 2-for-1. You owned 10 shares. What do you own now?
+ 20 shares at about 40
- 10 shares at 160
- 20 shares at 80
WHY: Twice the shares at half the price: the same value.
Q: A company agrees to be bought at 50 a share. Its stock trades at 48. Why the gap?
- An error
+ The risk the deal fails, and the time until it closes
- The buyer is overpaying
WHY: The discount is the market's price for the deal's risk and the wait.

## Brokers, fees and regulation {brokers} [6]
SUMMARY: How to choose a broker, the costs to compare, and who protects your money.
### What a broker does
Holds your money and shares, sends your orders to the market, and reports to the tax authorities. Choose one that is **regulated** where you live.

### Costs to compare
- **Commission** per trade (many now advertise zero).
- **Spreads and order routing**: "commission-free" brokers often earn from payment for order flow, which can mean slightly worse prices.
- **Currency conversion** fees on foreign shares (often the biggest hidden cost).
- **Account and inactivity fees**, and fund charges.
- **Financing**: interest on margin, overnight charges on CFDs.

### Regulation and protection
Markets are policed by regulators: the SEC in the US, the FCA in the UK, ESMA and national regulators in the EU. They require disclosure, ban insider trading and market manipulation, and set rules for brokers. If a regulated broker fails, schemes such as SIPC (US) and the FSCS (UK) protect clients' assets up to a limit. They do **not** protect you from investment losses.

### Red flags
An unregulated broker, pressure to deposit more, difficulty withdrawing money, "account managers" who trade for you: walk away (see the *Scams* lesson).

HERE: Meme Street's fee is a flat 0.1% of every trade, like a modest broker's commission, with no spread on shares, no account fees and no currency to convert. MB are practice money: there is no broker, no deposit protection and nothing to withdraw.

Q: What does investor protection such as SIPC or the FSCS cover?
- Losses from bad investments
+ Your assets if a regulated broker fails, up to a limit
- Any losing trade
WHY: It protects against the broker's failure, not against market losses.
Q: How do many "commission-free" brokers earn money?
+ Payment for order flow, spreads, currency fees and lending
- They do not need to
- From the government
WHY: Zero commission rarely means zero cost.

## Taxes: a general overview {taxes} [5]
SUMMARY: The usual ways trading and investing are taxed, in general terms only.
Tax rules differ a great deal between countries and change often. This is a general picture, not advice: check the rules where you live, or ask a qualified adviser.

### Common ideas
- **Capital gains tax**: on the profit when you sell for more than you paid. Many countries tax gains on investments held for longer at a lower rate than short-term gains.
- **Losses** can often be set against gains to reduce the tax.
- **Dividend tax**: dividends are usually taxed as income, sometimes at a special rate, and foreign dividends may have tax withheld at source.
- **Tax-free accounts**: many countries offer accounts where investments grow without tax (ISAs in the UK, IRAs and 401(k)s in the US), with yearly limits.
- **Frequent traders** may be taxed as running a business in some countries.
- **Records**: keep a record of every trade, with dates, prices and fees.

### Why it matters to a trader
Frequent trading turns every gain into a taxable event; a long-term holder can defer tax for years. After tax, the gap between an active trader and a buy-and-hold investor usually widens in the investor's favour.

HERE: MB have no cash value and are never paid out, so nothing here is taxed. The History page's CSV download is the kind of record a real trader keeps for tax.

Q: In many countries, what usually happens with losses on investments?
+ They can be set against gains to reduce the tax
- They are taxed as income
- They must be repaid
WHY: Offsetting losses against gains is common, within each country's rules.
Q: Why does frequent trading often cost more tax than buying and holding?
- Traders pay a special penalty
+ Every gain is realised and taxed each year, often at higher short-term rates
- Holding is never taxed
WHY: Holding defers tax until sale and often qualifies for lower long-term rates.
