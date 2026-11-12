# Meme Street: SEO context

Built 2026-11-07 from the code and the live site. Every fact has its source. If the product changes, the product is right.

## What it is
A fictional stock market that runs around the clock, for learning to trade without real money. Everyone starts with
**1,000 MB** (memebucks), practice money with no cash value that is never paid out.
- Start balance 1,000 MB: `game/engine.py` `START_CASH = 1000.0`; docs/ROADMAP.md §0.
- 180+ invented stocks, indices and funds: claimed on `web/about.html` and `web/index.html`. Code has 157 companies
  across `content/base.json`, `expansion.json`, `pack_fiction.json`, `pack_growth.json`, plus indices and derived funds. Not re-counted live.
- Fee 0.1% per side, no hidden spread: `game/engine.py` `FEE = 0.001`.
- Players' trades never move prices: docs/ROADMAP.md §1 rule 3.
- No simple rule beats holding the index by a wide margin (checked by `tools/realism.py`): ROADMAP §1 rule 2.
- 114 lessons in 20 tracks: `content/learn-*.md`, `learning.load_content()` (checked 2026-11-12; /about says "100+").
- Chart tests on real game charts, 11 kinds: ROADMAP §2.
- The Daily Chart: one mystery chart a day, two minutes, one go, streaks and a shareable result: ROADMAP §2, `game/pages.py` `DAILY_TEXT`.
- Charts: five chart types, log scale, 49 indicators (only part of them free), 16 drawing tools, 2,000 candles per timeframe: ROADMAP §2 and §270.
- Options for everyone; leverage up to 10x (Pro); trading bots and backtests (Expert): ROADMAP §2.
- Leaderboards rank return, so buying MB cannot buy a rank: ROADMAP §1 rule 4.
- Sign-up needs a date of birth, 13 or older: ROADMAP §2.

## Prices (`game/economy.py`, USD cents in code)
- MB packs: 1,000 MB $1.99 · 5,000 $7.99 · 10,000 $13.99 · 50,000 $59.99 · 100,000 $99.99.
- Pro $9.99/month or $99.99/year. Expert $29.99/month or $299.99/year.
- New Launch Deal (first 7 days): 9,000 MB $4.99 or 99,000 MB $29.99 once; first month of Pro or Expert half price.
- Prices are shown in the shopper's currency at checkout (`shop_currency`), so pages should not quote a USD price as universal.

## The buyer
Beginners who want to learn trading without risking cash, people who like Wordle-style daily games, and chart-reading
hobbyists. Arrives from Instagram reels today (ROADMAP §3). The conversion is a **signup** (`/#join` opens the form,
`web/index.html` line ~646).

## How the site makes pages (for SEO work)
- FastAPI, `game/pages.py`. The game is one SPA (`web/index.html`); its routes (`/`, `/learn`, `/leaders`, `/stock/X`...) all serve the same file, empty without JavaScript.
- `page_as(path, title, description, extra)` gives an SPA route its own title, description, canonical and JSON-LD.
- Plain server pages: `/about`, `/bots/guide`, `/terms` and `/privacy` (both noindex), `/lessons` and `/lessons/{id}` (`game/lessonpages.py`, from 2026-11-07).
- Sitemap and robots: `game/pages.py` (`public` list). `/api/` is disallowed in robots.txt.
- Lint: `ruff check --select E,F,W --ignore E501,E731,E741,E401 game tools tests`; types: `mypy game ... --ignore-missing-imports` (.github/workflows/tests.yml).

## Competitors (found 2026-11-07 by web search)
| Name | Why it competes | URL |
|---|---|---|
| Investopedia Stock Simulator | the default beginner pick in "best simulator" lists | investopedia.com/simulator |
| Wall Street Survivor | the closest model: free courses + simulator, $100k virtual | wallstreetsurvivor.com |
| HowTheMarketWorks | free classroom simulator | howthemarketworks.com |
| MarketWatch Virtual Stock Exchange | games with friends | marketwatch.com/games |
| Webull / thinkorswim / TradingView paper trading | broker paper accounts, real data | (brokers) |
| Stock Market Game app | 20,185-URL sitemap of programmatic pages | stockmarketgame.net |
| Ticker League, Financhle, Read the Tape | daily chart games (the Daily Chart's rivals) | tickerleague.com |

What only Meme Street has: a market built to be learnable and checked for no free money, the same market for everyone
(no player can move it), lessons that link straight to a live chart, and the Daily Chart as a trading game, not a
guess-the-ticker game. Weakness against all of them: fictional companies, not real tickers.
