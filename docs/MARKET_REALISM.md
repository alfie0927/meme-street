# Making Meme Street's charts move like real ones

This is the research behind the price model, what it found wrong with Meme Street's charts, what was changed
(2026-10-13, and the structure a trader reads on 2026-10-21), how to check it, and what is left to do. The code is `market_model.py` and the noise in
`engine._random_market_moves`; `HOW_IT_WORKS.md` §6A describes the mechanics; `chart_check.py` measures the result.

## 1. How real stock prices move: what the research says

Decades of studies of real prices agree on a set of "stylised facts": regularities any realistic model has to
reproduce (Cont 2001 lists eleven; a 2023 re-test on intraday Dow 30 data confirmed eight of them). The ones that matter
most for how a chart looks:

| Fact | What it means on a chart | Evidence |
|---|---|---|
| **No predictability in the direction of the next move** | Up and down minutes alternate like coin flips; trends are only visible over many bars. Individual stocks show slight *negative* autocorrelation at the shortest horizons (one-month reversal), slight momentum over 3-12 months. | Cont 2001; Jegadeesh-Titman; Jegadeesh, Luo, Subrahmanyam and Titman (2023): one-month reversal, 3-12 month momentum, both small |
| **Fat tails** | Big candles happen far more often than a bell curve allows. The tail of returns falls off like a power law with exponent about 3 (the "inverse cubic law"). | Gopikrishnan, Meyer, Amaral, Stanley (1998): exponent 2.8-3.1 on 40 million trades |
| **Volatility clustering with long memory** | Calm stretches and busy stretches: a wild hour is usually followed by more wild hours; the memory lasts days to weeks. | Cont 2001; Corsi's HAR model (2009): volatility as a cascade of daily, weekly and monthly components |
| **The leverage effect** | Volatility rises more after falls than after rises; sell-offs are jumpier than rallies. | Black 1976, Christie 1982, Bekaert and Wu 2000 |
| **Correlations rise in sell-offs** | On bad days everything falls together. | Longin and Solnik 2001; Ang and Chen 2002 (Forbes and Rigobon dispute part of it) |
| **Typical correlation between stocks** | About 0.3 on average (realised equicorrelation of the S&P 500 about 0.33 over 1996-2019; recent implied values lower). | Driessen and Maenhout; Cboe COR3M |
| **Intraday U-shape** | Volatility and volume are highest at the open, lowest at midday, higher again into the close. | Wood, McInish and Ord 1985; Admati and Pfleiderer 1988 |
| **Volume follows the size of the move, and has long memory** | Big candles come with big volume bars; volume itself is persistent. | Karpoff 1987; Lobato and Velasco 2000; Li, Wang, Havlin, Stanley |
| **Prices are discrete and cluster at round numbers** | Prices move in ticks (cents) and pile up at round figures. | Harris 1991 |
| **Order clusters make support and resistance** | Take-profit orders cluster at round numbers and stop trends there; stop-loss orders cluster just beyond them and speed a move up once a level breaks. | Osler 2000, 2003 (New York Fed) |
| **Earnings days are big** | A report typically moves a stock about 2.5-4 times an ordinary day (options price about ±5% for an S&P 500 stock). | Goldman Sachs, ORATS, Pepperstone figures for implied moves |
| **Post-earnings drift** | After a surprise, prices keep drifting the same way for weeks, by a few per cent. | Bernard and Thomas 1989, 1990 |
| **Gaps** | Small opening gaps usually fill the same day; big ones usually do not. | SPY data since 1993: under 0.25% gaps fill 78% the same day, 1-2% gaps 26% |
| **Market phases** | A 10% correction about every two years (average fall 13%), a 20% bear market about every five (average 32%, about 10 months). | Wells Fargo, American Century, Nasdaq since 1950 |
| **Chart patterns** | Patterns carry a little information, never certainty: head-and-shoulders tops fail (do not fall 5%) about a third of the time, double tops about 55-60%. | Lo, Mamaysky and Wang 2000; Bulkowski |

Two lessons follow for a game:

1. **Most of what makes a chart look real is in the noise, not in the patterns**: fat tails, volatility that clusters,
   volume that moves with it, ticks, and a quiet midday. A market built from patterns on a smooth random walk looks
   fake however good the patterns are.
2. **Structure must not become predictability.** Real support and resistance, trends and earnings drift are weak
   effects buried in noise. If they are strong enough to see on every one-minute chart, they are strong enough to farm.

## 2. What was wrong with Meme Street's charts

`chart_check.py` runs the real engine and measures these facts on one-minute candles (a game day of 30 minutes plays
the part of a trading day, so one minute is about 13 minutes of a real session). Before the changes:

| Check | Before | Real target |
|---|---|---|
| Direction of the next minute (sign autocorrelation) | +0.07 to +0.09: 54% of minutes kept going the same way | about 0 |
| Volatility memory, lag 10 / 30 minutes | about 0.0 | clearly positive, slow to fade |
| Volatility after falls vs rises | no difference | higher after falls |
| Correlation between stocks | 0.10-0.19 | about 0.2-0.45 |
| Fat tails of game-day returns (kurtosis) | 2.6 (thinner than normal) | 4-10 |
| Earnings day vs an ordinary day | 0.8-1.3x | 2.5-4x |
| Prices on a tick grid | never | always |

Causes found by switching parts off one at a time (with a fixed clock so runs are comparable):

- **The support and resistance reactions were too slow and too big.** A bounce was a steady push over four minutes,
  and a break pushed on in its direction: on a one-minute chart that is a little trend every time a level is touched.
  Worse, a level that was meant to hold but was pierced by noise was treated as a break and pushed on, so volatile
  spells turned into trends.
- **The rumour system** moved a price half-way, then 45-90 seconds later 75% of the time moved it the rest of the way:
  a built-in one-minute momentum.
- **The model's pushes ran at full strength in the thin pre-market and after-hours**, where the ordinary noise is a third
  of normal, so they became steady drifts.
- **The old soft daily brake** shrank a stock's moves once it was far from the day's open. On a volatile day that is
  exactly what happens, so it erased volatile days, and with them volatility memory and fat daily tails.
- **One volatility clock only** (a GARCH-like multiplier with a one-day half-life), no tail fattening, a market factor
  too small, and earnings reactions sized from tiny accounting noise.

## 3. What was changed

| Change | Where | Grounded in |
|---|---|---|
| **Stochastic volatility in three speeds** (half-lives 10 minutes, 2 game days, 15 game days) plus two market-wide components every stock shares; normalised so each stock's average volatility is unchanged | `market_model.py` (`AR`, `sv_*` settings) | Corsi's HAR cascade; long memory |
| **Falls feed volatility** (the leverage effect), and the old clustering weighs falls 1.25x | `market_model.py`, `engine._update_volatility` | Black, Christie |
| **Fat-tailed shocks**: company shocks are Student t (4 degrees of freedom), capped at 8 sigmas a second | `engine._student_t4` | inverse cubic law |
| **A bigger market factor that grows in sell-offs** (0.21 instead of 0.18; x1.35 in a correction, x1.3 in a bear market) | `engine._random_market_moves`, `REGIME_MARKET_FACTOR` | Longin-Solnik, Ang-Chen |
| **Volume with its own memory**: a volume mood per stock (half-life a game day), minute-to-minute noise, and a link to the volatility components | `market_model.py` | Karpoff; volume long memory |
| **Prices on a tick grid**: whole cents, 0.0001 MB below 1 MB; trades fill at the quoted price | `Stock.price` | Harris |
| **Earnings reactions of about three daily sigmas per standard surprise** | `engine._earnings_vs_forecast` | implied earnings moves |
| **Support and resistance as fast reactions, sized in today's volatility**: a hold is a quick rejection (0.12 daily sigmas in 40 s, a wick); a real break follows through (0.45 in 75 s); a noise-pierced level just ends; no push towards a level; only levels where price has actually turned count (round numbers strengthen them) | `market_model._level_step` | Osler: reversals at levels, acceleration on breaks |
| **The model's pushes follow trading activity** (damped in thin sessions, never amplified) | `MarketModel.step(activity=...)` | intraday U-shape |
| **Macro releases priced in seconds** (most of the move within 45 s), panic lows shorter | `market_model.py` | how data releases trade |
| **Rumours rarer and slower** (25% of stories, confirmed after 3-10 minutes) | `base.json` | news is mostly a single jump |
| **The daily brake widened** (1.5x, and with today's volatility) | `engine._envelope_damping` | real stocks have no soft brake |

## 4. Where it stands now

`python tools/chart_check.py 12 <seed>` (12 game days, about 5 minutes):

| Check | After (seeds 7, 8, 9) | Target |
|---|---|---|
| Kurtosis of one-minute returns | 29-37 | above 6 |
| Tail exponent | 2.7-3.3 | about 3 |
| Same direction next minute | -0.03 to +0.03 | about 0 |
| Market average, lag 1 | -0.07 to +0.07 | about 0 |
| Volatility memory, lag 1 / 10 / 30 min | 0.29-0.33 / 0.14-0.20 / 0.06-0.12 | positive, slow to fade |
| Volatility after falls | -0.07 to -0.10 | negative |
| Volume vs size of move | +0.27 to +0.34 | 0.3-0.6 |
| Volume memory, lag 1 / 10 | 0.70 / 0.36 | high, slow to fade |
| Open / close vs midday | 1.9-3.0x / 1.0-1.5x | U-shape |
| Correlation between stocks | 0.20-0.44 | 0.2-0.45 |
| Kurtosis of game-day returns | 8-24 | 4-10 for an index, often higher for single stocks |
| Small / large gaps filled the same day | 61-82% / 13-31% | 60-85% / under 40% |
| Earnings day vs usual day | 2.3-4.1x | 2.5-4x |
| Prices on a tick | 100% | 100% |

And the "no free money" check (`python tools/realism.py 2 3 40 801`): buying every 1.5-sigma dip, fading every rise,
momentum, breakouts and buying 20-day lows all earn less than holding the market, costs included; trading every
level test earns about +0.09% a trade (less than holding over a game year); trading only strong levels with the trend
earns about +0.3% a trade. Strong levels hold 56% of the time, weak ones 42%, a third of breaks fail.

**Levels calibrated, news turned down (2026-10-19, ROADMAP TA-A1, TA-E1, TA-E2).** A strong level (3+ touches or a round
number) in line with the trend now holds 5 points more often (`hold_strong_aligned`), and while a strong level is tested the
noise is 0.8x (0.9x before the price reaches a level that will break): the approach visibly slows. Macro releases move the
market 0.3 daily sigmas per standard deviation of surprise (was 0.55), with half the extra noise and volume after them.
`python tools/realism.py 2 3 40 601`, old settings against new on the same seeds: strong levels held 56% then 59% (target
55-65%), weak ones 43% both times, 34% and 33% of breaks failed. The "no free money" picture did not change: trading every
level test earned +25.4% a game year against +22.2% for holding the market before, +23.2% against +19.2% after (the extra is
about the market's drift over the hour each trade lasts); strong levels with the trend +14.3% and +10.7%, both below holding.
Two broader versions tried first (higher odds for every level, a slower approach at every level) also reached 59% but let
trading every level beat holding by 9 to 12 points, so they were dropped. Seeds 401, 501 and 601 differ a lot in their
market return (-8% to +9% a game year), so compare settings on the same seeds.

**After company sizes were spread out (2026-10-14)**: small caps now carry 1.3 times the volatility of a large cap (most of it
their own, not the market's), so stocks move together a little less. Seed 7 over 12 game days: every check in range, with
the correlation between stocks at 0.19 (it was 0.2 to 0.44 before), earnings days 3.9x, the market's lag-1 autocorrelation
-0.05 and the close's burst 1.43x. An 8-day run of the same seed read 0.06 for the correlation: with only 8 daily returns per
stock that number is very noisy, so judge it on 12 days or more. If later runs keep it under 0.2, raise the market factor
for small caps slightly rather than lowering their volatility.

Known gaps: the close's burst is sometimes flat (0.98-1.5x midday); the daily tails of a few volatile stocks are very fat
(one seed's pooled kurtosis was 24); `realism.py` is a faster approximation of the engine and its long-run market return
is noisy (-11% to +11% a game year across four-market runs with different phase mixes: the drift of +5.5% a game year
is still there, but the fatter tails and the leverage effect make individual runs wander more).

**The structure a trader reads (2026-10-21, ROADMAP Phase 2: TA-A2 to TA-A11).** Levels from the daily chart (the
previous day's high, low and close, the open, the 52-week range, the 20/50/200-day averages), volume that tells the story
(on average), wicks, engulfing turns, squeezes, a weaker last push, climaxes, intraday legs, ten kinds of named chart
pattern and gaps between one session's close and the next open (HOW_IT_WORKS §6A.3, §6A.4, §6A.10, §11). `realism.py` now rebuilds the
engine's trading sessions and opening jump, measures the structure and finds the patterns with `patterns.py`.

*What the checks found on the way, and fixed:*
- **Trading every level test beat holding the market by a wide margin, before any of the new work** (+46% a game year
  against +33% on the seeds that were reported as +23% against +19% in October; +73% against +15% on others). The edge
  came from ranges (a level marks a range's edge, and the range pulls the price back to its middle) and from the size of
  a hold's bounce (it pushed until the price was 2.5 bands away). With the daily levels a stock is near some level most of
  the time and it grew to +262% a game year. Now a hold pushes until the price is one band away (`bounce_reach`) and a
  stock starts no new test within 10 minutes of its last (`test_gap_seconds`).
- **Levels in the thin sessions**: in the pre-market and after-hours a level due to break was seldom reached before its
  test ran out, while one due to hold still pushed. Levels are now tested in the regular session only.
- **A steady fall from the leverage effect**: a reaction sized in the volatility of each second grew as it pushed down
  (a fall raises volatility) and shrank as it pushed up. With the daily levels that bias took the market to -29% a game
  year. Every reaction is now sized when it begins.
- **Patterns that moved too fast**: the first patterns (3 daily moves in legs of 3-5 game days) gave the market a
  short-term momentum real markets do not have: buying every 1.5-sigma dip lost 1.6% a trade, buying a 20-day high earned
  0.8% a trade. They are now 2.5 daily moves with legs twice as long, and a pattern that has broken out is busted (turns
  back through the other side) more often than at first.

*Results, `python tools/realism.py 2 3 40 901` (seeds 901-903, fresh: the settings were tuned on 601, 602, 701 and
801-803):*

| | Result | Target |
|---|---|---|
| Market return a game year | +5.9% (+13.2%, +0.3%, +4.1%) | +5% to +10% |
| Strong / weak levels held | 63% / 48% (swing 58%, the open 59%, yesterday's close 60%, yesterday's high and low 63-64%, the averages 61-64%, the 52-week range 65-68%) | 55-65% / 40-50% |
| Breaks that failed | 33% | 20-35% |
| Autocorrelation of 5-minute market returns | +0.027 | near 0 |
| Volume where a level breaks, times the usual: breaks that run / fail | 1.34x / 1.21x | more on the ones that run, overlapping |
| Impulse legs / pullbacks, volume | 1.51x / 1.27x | pullbacks quieter |
| Wick on the level's side, the bar that probed it: held / broke / any bar | 0.24 / 0.22 / 0.19 | longer where it held |
| Engulfing 15-minute candle where a trend turned / any candle | 23% / 21% (27-38% on other seeds) | more where it turned |
| 5-minute moves in the two hours before a range breaks out | 0.85x usual | a squeeze |
| Next game day goes the way of a 10-day move | 52.7% | a little over 50% |
| RSI divergence: the next 10 game days the expected way, against any new extreme | bearish +0.31 vs -0.17 sigma; bullish +0.34 vs +0.13 | divergences help, never reliably |
| Patterns made by the model / found by a trader's scan | about 3.8 a stock a game year; most kinds found 20-65% of the time, symmetric triangles and cups 0-10% | |

*No free money (costs included, per trade and per stock a game year; holding: +2.43% a trade, +85% a game year, as a few
small caps soared):* trade every level test +0.06% (+29%); only strong levels with the trend +0.19% (+37%); only the
daily levels +0.11% (+41%); buy a 20-day high +0.78% (+27%); buy a 20-day low +1.01% (+16%); momentum +0.05% (+5%);
buy every 1.5-sigma dip -0.31%; fade every opening gap -0.57%; **trade every completed chart pattern -3.3% a trade**
(completed 22-67% of the time, reaching the measured move 11-60% of those, by kind). Every rule earns less than holding.

*The engine itself, `python tools/chart_check.py 12 <seed>`, before and after Phase 2 on the same seeds:*

| Seed (before / after) | Tail exponent | Market lag-1 autocorrelation | Volume vs size of move | Small gaps filled | Large gaps filled |
|---|---|---|---|---|---|
| 7 | 2.77 / 2.39 | +0.091 / +0.115 | 0.31 / 0.24 | 71% / 70% | 15% / 14% |
| 9 | 2.70 / 2.72 | +0.034 / +0.062 | 0.30 / 0.29 | 72% / 70% | 24% / 20% |
| 10 | 2.30 / 2.44 | +0.003 / +0.035 | 0.29 / 0.29 | 70% / 68% | 24% / 29% |
| 11 | 2.29 / 2.64 | +0.122 / +0.111 | 0.28 / 0.33 | 70% / 71% | 12% / 27% |
| 8 (after only) | 2.80 | +0.043 | 0.25 | 75% | 25% |

Phase 2 changed none of these beyond the spread between seeds; the tail exponent (target 2.5-4) and the market's
one-minute autocorrelation (within +-0.1) were already just outside their targets on some seeds before it, and still are.
`realism.py`'s gap fills (52% small, 50% large) are an artefact of its 10-second steps and approximations: the engine
fills 68-75% of small gaps and 14-29% of large ones (targets 60-85% and under 40%). Seed-to-seed spread is large, so
compare settings on the same seeds. The engine is about 5% slower a tick (7.4 against 7.0 ms for 189 listings).

## 5. What to do next (in order)

1. **Watch it live for a few days** and look at the 1h, 15m and 5m charts of a few stocks: levels at yesterday's
   high and low and the averages, gaps at the open, a few named patterns. Your eye is the last test (ROADMAP section 8).
2. **Calibrate the long-run return on the engine itself**, not only `realism.py`: run the engine for a few game years in
   the background and adjust `erp` until the MSI 50 averages +5-10% a game year across seeds.
3. **Thinner tails and no one-minute momentum in the market average** on every seed: the tail exponent sits at 2.3-2.8
   and the market's lag-1 autocorrelation reaches +0.12 on some seeds (both before and after Phase 2).
4. **Osler's asymmetry** at round numbers (take-profits just before them, stops just beyond them).
5. **One-month reversal and 3-12 month momentum** at their (small) real sizes, now that a game year of daily candles is
   kept (`history.db`).
6. **A bid-ask spread** that widens in thin sessions and fast markets (ROADMAP M8): real costs, and the source of the
   slight negative autocorrelation real tick data shows.
7. **Recognisable symmetric triangles and cups**: the scan finds few of the ones the model makes.

## Sources

- Cont, R. (2001), *Empirical properties of asset returns: stylized facts and statistical issues*, Quantitative Finance 1(2) — [IDEAS](https://ideas.repec.org/a/taf/quantf/v1y2001i2p223-236.html); re-test on intraday data: [arXiv 2311.07738](https://arxiv.org/pdf/2311.07738)
- Gopikrishnan, Meyer, Amaral, Stanley (1998), *Inverse cubic law for the distribution of stock price variations* — [arXiv](https://arxiv.org/pdf/cond-mat/9803374)
- Corsi, F. (2009), *A simple approximate long-memory model of realized volatility* — [SSRN](https://papers.ssrn.com/abstract=1365738); [Corsi, Audrino, Renò handbook chapter](https://openaccess.city.ac.uk/id/eprint/4438/5/CorsiAudrinoReno_Handbook_sub2011.pdf)
- Leverage and volatility feedback: [Bekaert and Wu (2000)](https://www.bauer.uh.edu/wu/Papers/RFS2000_AsyVol.pdf); [Is the "leverage effect" a leverage effect?](https://archive.nyu.edu/jspui/bitstream/2451/26702/2/FIN-00-037.pdf)
- Asymmetric correlations: [Ang and Chen (2002)](https://estima.com/forum/download/file.php?id=1865); [Hong, Tu and Zhou](https://hong.economics.cornell.edu/papers/Asymmetries%20in%20Stock%20Returns-%20Statistical%20Tests%20and%20Economic%20Evaluation.pdf)
- Correlation levels: [Driessen and Maenhout data (OSF)](https://osf.io/ckgyf); [Cboe implied correlation](https://cdn.cboe.com/resources/indices/documents/Implied_Correlation-WhitePaper-v1.0.5.pdf)
- Intraday patterns: [Admati and Pfleiderer (1988) summary](https://academicnewsletter.sufe.edu.cn/info/355980); [Abhyankar, Copeland, Wong](https://orca.cardiff.ac.uk/id/eprint/49180/)
- Volume: [Karpoff (1987)](https://ideas.repec.org/a/cup/jfinqa/v22y1987i01p109-126_01.html); [Long memory in trading volume](https://e-archivo.uc3m.es/entities/publication/521532cd-8e5e-4bf6-a104-3285be09a569); [Li, Wang, Havlin, Stanley](https://arxiv.org/pdf/1106.1415)
- Price clustering: [Harris (1991)](https://ideas.repec.org/a/oup/rfinst/v4y1991i3p389-415.html)
- Support and resistance from order clustering: [Osler, New York Fed Staff Report 125](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf); [price cascades, Staff Report 150](https://econpapers.repec.org/RePEc:fip:fednsr:150)
- Earnings moves: [Pepperstone](https://pepperstone.com/en-gb/insights/market-analysis/shares/us-q426-earnings-season-could-s-p-500-stocks-see-record-volatility-); [CNBC / Goldman Sachs](https://www.cnbc.com/2019/01/14/goldman-this-chart-shows-we-are-likely-in-for-a-wild-earnings-season.html); [ORATS](https://orats.com/blog/get-ready-for-a-wild-earnings-season)
- Post-earnings drift: [overview](https://en.wikipedia.org/wiki/Post%E2%80%93earnings-announcement_drift); [Quantpedia: 50 years of PEAD research](https://quantpedia.com/Blog/Details/50-years-in-pead-research)
- Reversal and momentum: [Jegadeesh, Luo, Subrahmanyam, Titman](https://business.ucr.edu/media/12011/download)
- Gaps: [SPY gap statistics](https://www.thetrading.tools/gap-analysis); [Trade That Swing](https://tradethatswing.com/high-probability-stock-market-statistics/)
- Corrections and bear markets: [Advisor Perspectives](https://www.advisorperspectives.com/commentaries/2015/08/28/how-long-do-stock-market-corrections-last); [American Century](https://res.americancentury.com/docs/bouncing-back-from-market-corrections.pdf); [Nasdaq](https://www.nasdaq.com/articles/how-long-do-stock-market-corrections-last-2018-04-11)
- Chart patterns: [Lo, Mamaysky, Wang (2000)](https://www.nber.org/papers/w7613); [Bulkowski, pattern confirmation statistics](https://thepatternsite.com/Confirmation.html)
