# The technical write-up: "How I built a stock market that never closes"

For the reach plan (`docs/REACH_PLAN.md`, B2, weeks 3 to 6). You post it, under your own name. Everything below
the line is the article; everything above it is for you.

**Before you post**

- **Make it yours.** It is written in the first person from what the code and `docs/HOW_IT_WORKS.md` say. Read
  it once and change anything that is not how you would say it. Add a line on why you built it where marked.
- **AI help.** Readers on Hacker News and r/Python will ask whether AI wrote the code. Decide your honest answer
  and, if you like, put one sentence about it in the article. It is better said by you than found by them.
- **The bots.** The article says 72 house bots trade beside the players. The pages do not mark them (your
  decision of 10 Nov). Someone may ask; have your answer ready.
- **One home.** Post it first on one site (dev.to is the easiest), then on the others with that first address
  set as the "canonical URL" (dev.to, Hashnode and Medium's import tool all have the field), so search engines
  see one article.
- **Never ask for votes or claps.**

**Where, with each link's tag.** Swap the tag in the article's two links for each place:

| Where | Tag | Notes (check each place's rules on the day) |
|---|---|---|
| dev.to | `ref=devto` | Tags: python, webdev, gamedev, showdev |
| Hashnode | `ref=hashnode` | Set the canonical URL to the dev.to post |
| Medium | `ref=medium` | Use "Import a story", which sets the canonical URL |
| Indie Hackers | `ref=indiehackers` | A post in the product's group; shorter is fine: lead with the save story |
| r/Python | `ref=reddit_python` | The "Showcase" flair has a fixed form: what it does, who it is for, how it compares |
| r/webdev | `ref=reddit_webdev` | Only on Showoff Saturday |
| r/gamedev | `ref=reddit_gamedev` | Only in the Feedback Friday thread |
| Hacker News, as an article | `ref=hn_article` | Weeks after the Show HN, never the same week; submit the dev.to address |
| Python Weekly, PyCoder's Weekly | none | Send the dev.to address through each newsletter's submit form |
| LinkedIn | `ref=linkedin` | Three lines and the link; the article stays on dev.to |

---

# How I built a stock market that never closes

Meme Street is a stock market where every company is invented. It runs around the clock, has 180+ companies,
indices and funds, news that moves prices, and 72 house bots that trade beside the players. Everyone starts with
1,000 MB of practice money, which has no cash value and is never paid out. You can watch it, or play its
two-minute Daily Chart without an account, at https://memestreet.net/?ref=devto.

[One or two sentences in your own words: why you built it.]

This is how it works underneath, and what broke on the way.

## Why invent a market

A practice account on real shares has two problems for a learner. It only moves when the real market is open, and
it teaches you to look things up. An invented market can run at any hour and can speed time up. Here one tick is
one real second, one game day is 30 real minutes, and a game year is 7.6 real days. A company reports earnings
about every two real days. In a week you see what a real market shows in a year.

## One engine, one lock, one tick a second

The server is Python with FastAPI. The engine is one file with no web code in it: it knows about companies,
prices, orders and accounts, and nothing about HTTP. The web layer calls it from worker threads, and every call
takes one lock.

One lock sounds crude. It means every trade and every tick sees one consistent world, with no ordering bugs
between a fill and a price change. The cost is that anything slow under the lock freezes every player at once,
which is the next section's story.

Each browser gets the whole state once, in one `init` message, and then one small `tick` message a second over a
WebSocket. When there are many players, separate gateway processes hold the sockets, so the engine process only
does the market.

Before launching I ran a load check against a staging copy on the real server, which has 2 cores and 4 GB of
memory: 200 visitors arriving over 20 seconds, each watching for 20 seconds. That made 5,000 requests, none
failed, and 95% were answered within 54 ms.

## Saving without a database

The live state is in memory. Two things make it safe:

- **A snapshot.** Every 30 seconds the state is written to a temporary file as JSON, and the file is then swapped
  in for the old one, so a crash mid-write cannot leave half a save.
- **A ledger.** Every event that changes money or positions is appended to a SQLite file in WAL mode, flushed
  once a tick. After a crash, the server loads the last snapshot and replays the events after it.

The first capacity test found the fault in this. On a full-size game the save was 27 MB and took 2.1 to 2.9
seconds, while holding the lock. The whole market froze for over two seconds, every 30 seconds.

There were two causes. First, `json.dump(obj, file)` is much slower than `json.dumps(obj)` followed by one
write: `dump` goes through the pure-Python iterating encoder, and `dumps` uses the C one. That alone was about
four times. Second, 23 of the 27 MB were chart candles, 11 timeframes of 500 candles for every stock, and they
change slowly. They now live in their own file, written every five minutes. If that file is behind after a
crash, the missing candles are rebuilt from the one-minute candles in the main save.

The save went from about 2.4 seconds to about 140 ms. A test pins it.

## Money that cannot leak

One line guards the whole economy:

```
player cash + house reserve + fees = everything ever minted
```

It is checked every time a save loads. Any code path that makes or destroys MB by accident fails at once and
loudly, not weeks later as a player with an odd balance. Every MB that enters an account also carries its
source (the starting grant, a purchase, a lesson reward, a refund), so the boards can rank the return on the
money put in. Buying MB cannot lift a place on them.

## A price model with no free money

The rule I held the model to is "realism you can learn from, but no free money".

Realism first. A stock's drift is the risk-free rate plus its beta times a risk premium, about +5.5% a game
year for the market as a whole. On top of that the market moves through hidden phases (bull, sideways,
correction, bear, recovery). Trends move in legs. Ranges end in breakouts. Support and resistance form at old
swing highs and lows and at round numbers. Volatility has its own random process, so quiet and wild spells
cluster. An economy runs on a calendar, companies report earnings, and news lands on the wire.

Nobody's trade moves a price, the house bots' included. Prices follow the news, the economy and the model. That
choice removed a whole class of problems: nobody can push a thin stock around, and no group of accounts can
farm another.

Then the "no free money" half. A realistic chart is full of patterns, and a pattern that pays is a cheat code.
So a check script simulates many markets and runs the simple strategies on them: buy every 1.5-sigma dip, fade
every rise, follow momentum, buy breakouts, buy 20-day lows. Each must earn less than holding the market, costs
included (every trade costs 0.1%). The patterns stay real but unreliable. A strong price level holds 56% of the
time and a weak one 42%, and a third of breakouts fail. A second script checks the statistics of the charts
themselves: fat tails, volatility clustering, volume and gaps.

Writing the exploit before the feature found real faults. A rule for companies in distress turned out to be a
free short paid for by the house, until its terms were tied together. A daily price limit acted as a wall that
prices bounced off, which is a pattern you could trade. Holding news back would have made the open
predictable. None of these showed in normal play. All of them showed when a simulated strategy went looking.

## A two-minute game the browser cannot read ahead

The Daily Chart is the quick way in: one mystery chart a day, the same for everyone. You see 60 candles of
lead-in, then one new candle a second for 120 seconds, and you buy, sell or short as they print.

The candles still to come never leave the server. The browser is sent one candle a second, and the server prices
each trade at that moment, so there is nothing in the page to read ahead. A visitor without an account is known
by a random id the page makes and keeps in local storage, sent as a request header. There are no cookies.
Visitors can play, but only accounts go on the board.

## Bots, the house's and the players'

72 house bots, each with a persona, trade in the market and play the Daily, so a board is never empty on a quiet
day. They see what a player sees and pay the same fee. In the data every one carries a flag, which is how the
real player counts stay honest.

Players can script their own bots in a small rule language (a paid feature), and backtest them first. A rule is
a condition and an action:

```
cross_above(close, ema(20)) and rsi(14) < 70
```

The text is parsed into a tree and run by a small interpreter that can only read the market and the account.
Nothing is ever passed to `eval`.

## One HTML file

The front end is one HTML file and plain JavaScript, with no framework and no build step. The same file serves
every page, and the script reads the address to decide what to show. For search engines and link previews the
server fills in each address's own title, description and a short readable body before sending it.

Smaller things: passwords are stored as scrypt hashes, and there are 997 tests in 53 files, many of them
running the real server against a temporary copy of a game.

## What I would tell myself at the start

1. **Write the exploit first.** For a market, the test of a new mechanism is a simulated trader trying to milk
   it. If the trader beats holding the index, the mechanism is wrong.
2. **Time everything that runs under the lock.** A single lock is fine until one slow thing hides inside it.
3. **Make conservation of money a hard check on day one.** It turns silent bugs into loud ones.
4. **Snapshot plus an append-only log is enough** for a game this size, and far simpler to reason about than a
   database in the hot path.

You can watch the market live, or play today's chart in two minutes with no account, at
https://memestreet.net/daily?ref=devto. I would like to hear where the market feels fake.
