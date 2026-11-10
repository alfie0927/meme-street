# Product Marketing Context

**Document version:** v1
**Last updated:** 2026-11-10

Drafted from the site's own copy (`web/about.html`, `game/pages.py` DAILY_TEXT, the home page), `seo/context.md`
and the Instagram audit in `growth/instagram.md`. When the product changes, the product is right.

## Product Overview
**One-liner:** A made-up stock market that never closes, for learning to trade with practice money.
**What it does:** 180+ invented stocks, indices and funds whose prices follow made-up news, the economy and how
traders act around levels, never the players. Everyone starts with 1,000 MB (memebucks), practice money with no cash
value. Free lessons teach charts, orders and risk on the same market, and the Daily Chart is a two-minute daily
game on one mystery chart, the same for everyone.
**Product category:** stock market game / trading simulator / daily chart game ("like Wordle, for trading").
**Product type:** browser game (one web app, works on phones), no install.
**Business model:** free account. Paid extras: MB packs ($1.99 to $99.99), Pro ($9.99 a month or $99.99 a year),
Expert ($29.99 a month or $299.99 a year). MB are never cashed out. Paying never buys a leaderboard rank.

## Target Audience
**Who:** beginners aged roughly 16 to 30 who want to learn trading without risking money; people who play a daily
game every morning (Wordle and its many "-dle" cousins); chart-reading hobbyists. Minimum age 13.
**Decision-makers:** the player. Later: teachers (economics, business, personal finance) and university investing
societies choosing a game for a group.
**Primary use case:** practise reading charts and placing trades where mistakes cost nothing.
**Jobs to be done:**
- "Let me try trading without losing real money."
- "Give me a two-minute daily puzzle I can share and keep a streak on."
- "Show me whether I can actually read a chart."
**Use cases:**
- The Daily Chart with the morning coffee, result shared to a group chat.
- Working through a lesson, then trying it on a live chart.
- A class or society running a private league (planned).

## Personas
Not applicable (a consumer product). For teachers and societies, see Objections.

## Problems & Pain Points
**Core problem:** learning to trade with real money is expensive, and the first trades usually lose.
**Why alternatives fall short:**
- Broker paper trading needs an account and an app, uses real tickers whose answers you can look up, and stops
  when the market closes.
- Courses are long and dry, with no chart to try it on.
- Guess-the-ticker games test memory, not trading.
**What it costs them:** money lost on first trades, or months of reading without ever practising.
**Emotional tension:** fear of losing money and of looking stupid; doubt about whether they could ever read a chart.

## Competitive Landscape
**Direct:** Investopedia Stock Simulator, Wall Street Survivor, HowTheMarketWorks, MarketWatch Virtual Stock
Exchange: real stocks in market hours, signup first, no daily game.
**Secondary:** broker paper trading (Webull, thinkorswim, TradingView): real data, but an account, an app and
market hours.
**Daily chart games:** Ticker League, Financhle, Read the Tape: mostly guess-the-ticker or one-shot guesses.
**Indirect:** YouTube and Instagram trading education: lots of talk, no practice.

## Differentiation
**Key differentiators:**
- A market built to be learnable and checked for "no free money": simple tricks like buying every dip don't beat
  holding the market (`tools/realism.py`).
- Nobody's trade moves a price, so the same market is fair for everyone.
- It never closes; a full trading day lasts 30 minutes.
- The Daily Chart is a trading game (buy, sell and short for two minutes), not a guess.
- Lessons link straight to a live chart.
**Why that's better:** you practise the real skill (reading and acting on a chart) as often as you like, and
nobody can look up the answer.
**Why customers choose us:** not known yet. Collect it from the first 100 players (growth plan, Part 5).

## Objections
| Objection | Response |
|-----------|----------|
| "It's not real stocks." | That's the point: nobody can look the answer up, and the numbers behave like a market. |
| "Is it gambling or a crypto thing?" | No money goes in to play and none comes out. MB are practice money with no cash value. |
| "Do I have to pay?" | No. The account is free; MB packs and Pro are extras. |
| "I don't have time." | The Daily Chart takes two minutes. |
| (Teachers) "Will students be sold things?" | Planned: class accounts never see the shop. |

**Anti-persona:** people who want real tickers, real-money returns or trading signals; under-13s.

## Switching Dynamics
**Push:** money lost on real trades; dry courses; markets closed when they have time.
**Pull:** a two-minute daily game with a streak and a score to share; a market open at 3 a.m.
**Habit:** broker paper accounts, YouTube tutorials, other daily games.
**Anxiety:** "Will it ask for my card?", "Is a made-up market worth learning on?", the sign-up form itself.

## Customer Language
**How they describe the problem:** no verbatim quotes yet (0 comments on Instagram; 14 accounts). Collect from the
welcome emails and any comment or message, word for word.
**How they describe us:** none yet.
**Words to use:** made-up market, practice money, no cash value, today's chart, two minutes, no sign-up, streak,
beat my score, learn to read charts.
**Words to avoid:** get rich, profit, guaranteed, free money, investment advice, "everything is free", real
tickers, signals.
**Glossary:**
| Term | Meaning |
|------|---------|
| MB, memebucks | Practice money. Every account starts with 1,000; no cash value, never paid out. |
| Daily Chart | One mystery chart a day, the same for everyone; two minutes to trade it; new at midnight UTC. |
| MSI 50 | The index of the 50 biggest made-up companies. |
| House bots | 72 computer traders that play the market around the clock. |

## Brand Voice
| Attribute | Means | Doesn't mean | Example line |
|-----------|-------|--------------|--------------|
| Plain | Short sentences, everyday words | Jargon, hype | "A stock market that never closes, made of companies that don't exist." |
| Honest | Says what it isn't and what can go wrong | Fine print | "You can lose your balance, especially by shorting or trading moonshots." |
| Playful | Odd made-up companies, a game's energy | Clowning about money | "This company doesn't use trucks." |
| Fair | Skill shows, nothing is bought | "Win big" | "Ranks count your returns, so buying MB can't buy a better rank." |

**Tone by context:**
- Support: direct and short, answer first.
- Launch: the product's own facts; never invented numbers.
- Errors: say what happened and what to do next.
- Sales: practice money, no cash value, every time MB are mentioned.
- Social: a stake or an odd fact first, never a label or a definition (see Learnings).
**Terms we own:** Meme Street, memebucks (MB), the Daily Chart, the MSI 50.
**Never use (and why):** "get rich" and profit promises (it teaches, it doesn't pay); "everything is free" (MB packs
and Pro cost money); real company names or tickers (everything is fictional).

## Proof Points
**Metrics:** 157 companies (180+ stocks, indices and funds), 96 lessons in 17 tracks, 49 indicators, 16 drawing
tools, 72 house bots, a 0.1% fee and no hidden spread; the market checked for "no free money" by simulating many
markets with dozens of strategies.
**Customers:** none to cite yet.
**Testimonials:** none yet.
**Value themes:**
| Theme | Proof |
|-------|-------|
| Safe to fail | 1,000 MB of practice money, no cash value |
| Fair | Nobody's trade moves a price; paying can't buy a rank |
| Learnable | Lessons on the same market; the no-free-money checks |
| Quick | The Daily Chart takes two minutes |

## Goals
**Business goal:** people (house bots excluded) who finish a Daily Chart or make a trade each week; 120 by 1 Feb 2027.
**Conversion action:** finish today's Daily Chart, then save the result with an account.
**Current metrics (10 Nov 2026):** 14 accounts, 0 new since 31 Oct; Instagram reached 3,751 accounts in 29 days,
51 profile visits, 2 link taps; reels median 61 views, 32% held at 3 s.

## Paid Ads
None. Owner's rule since 2026-11-10: no spending unless there is no free route (growth plan, "Spending: none").

## Learnings
*Decisions and tested lessons. Newest first. Keep it to about 20 active entries.*
| Date | Learning | Evidence | Applies to | Status |
|------|----------|----------|------------|--------|
| 2026-11-10 | Reels that open with a label ("Daily Chart #6 recap") or a definition lose most viewers in 3 s. | Recaps n=7 and technical lessons n=5: 27% held at 3 s vs 32% account median | Reels, Shorts, TikTok | active |
| 2026-11-10 | An odd fact about a made-up company holds viewers best. | Stock stories n=5: 56% held, 2.1x median views | Reels, captions, Stories | active |
| 2026-11-10 | Instagram viewers rarely reach the site: 51 profile visits and 2 link taps from 3,751 reached in 29 days. | Account insights | Profile, reel endings | active |
| 2026-11-10 | The 448 followers are inactive; reach is 99.9% non-followers. | Gender unknown for 438 of 440; 5 followers reached in 29 days | Instagram | active |
| 2026-11-10 | No spending unless there is no free route. | Owner's decision | All channels | active |

## Changelog
*Newest first. One line per revision: what changed and why.*
- v1 (2026-11-10) — Initial context, drafted from the site's copy, seo/context.md and the Instagram audit.
