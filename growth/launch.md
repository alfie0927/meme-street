# Launch posts: Show HN and the launch lists

For the reach plan (`docs/REACH_PLAN.md`, B2). You post all of these yourself, from your own accounts; nothing
here is sent by a script. Each link carries its own `ref` tag, so its visits and sign-ups show per source in
`tools/visits.py` and on the admin page. Before posting anywhere, read that site's rules on the day: they change.

Three rules for every post:

- **Never ask for votes**, on any site, in any chat. Hacker News and Product Hunt both punish it.
- **Practice money, no cash value.** Say it in every listing. Never "win", "earn" or "profit" about real money.
- **Say what is sold.** MB packages and two memberships are sold (Pro: leverage and 32 more indicators; Expert:
  scripted bots and backtests); MB are never paid out; the return boards rank percentage return on the money put
  in, so bought MB cannot lift a place on them. (The two profit boards rank MB made, so a bigger account can top
  those. If someone asks, say so.)

## Before the first post

1. The reach plan's site changes are live (P1 to P5), and the load check has been run on staging (it has: 200
   visitors, 0 failed, see the Progress table).
2. Open `https://memestreet.net/daily` in a private window on a phone and play it once. A launch day is the wrong
   day to find a fault.
3. Be at the keyboard for the first three hours after posting, to answer every comment.

## Show HN

**When:** a weekday morning, US time (about 8 to 10 am Eastern, which is 1 to 3 pm UK time). Not on the same day
as Product Hunt: one launch a day, so you can answer everyone.

**Where:** news.ycombinator.com/submit. Fill the title and the URL, leave the text box empty, then add the text
below as the first comment straight away.

**Title** (73 characters; the limit is 80):
```
Show HN: A stock market that never closes, with 72 bots and no free money
```

**URL:**
```
https://memestreet.net/?ref=hn
```

**First comment:**
```
Hi HN. Meme Street is a made-up stock market that runs around the clock: 180+ invented companies, indices and funds, news that moves prices, and 72 house bots that trade next to the players. Everyone starts with 1,000 MB of practice money. MB have no cash value and are never paid out.

You can try it without an account. The home page shows the market live, and the Daily Chart (https://memestreet.net/daily) is a two-minute game on one mystery chart a day, the same chart for everyone. Trading in the main market needs an account, which is a name and a password.

Why invented companies: a practice account on real tickers teaches you to look things up, and it only moves when the real market is open. An invented market runs at any hour and can speed time up. One game day is 30 real minutes and a game year is under 8 real days, so an earnings season comes round every two real days.

The rule I held the price model to is "realism you can learn from, but no free money". Prices have trends, ranges that end in breakouts, support and resistance, volatility that clusters, gaps and fat tails, because a learner needs to see those. But a check script simulates many markets and runs the simple strategies on them (buy every dip, fade every rise, momentum, breakouts, buy the 20-day low), and each of them has to earn less than holding the index after costs. Strong price levels hold a little more often than not, about a third of breakouts fail, and every trade costs 0.1%. Nobody's trade moves a price, the house bots' included.

Some details:

- Python and FastAPI. The engine has no web code and runs behind one lock, one tick a second. Each browser gets the full state once and then a small update every second over a WebSocket.
- The live state is in memory. It is saved as a JSON snapshot every 30 seconds plus an append-only SQLite ledger (WAL mode) flushed every tick. After a crash the ledger is replayed over the last snapshot.
- Money is conserved: player cash + house reserve + fees = everything ever minted, checked on every load.
- The front end is one HTML file and plain JavaScript, with no build step.
- The Daily Chart's coming candles never leave the server, so the chart cannot be read ahead from the browser.
- Players can script trading bots in a small rule language and backtest them (a paid feature). The language is parsed, never eval'd.

How it pays for itself: the 114 lessons are open to everyone. The shop sells extra MB and two memberships: Pro adds leverage and 32 more chart indicators, Expert adds the scripted bots and backtests. MB can never be cashed out, and the return boards rank percentage return on the money put in, so buying MB cannot lift a place on them.

I would like to hear where the market feels fake, and whether the Daily is clear in its first ten seconds.
```

**Answering comments.** Answer everything, plainly, and thank people for faults they find. Likely questions and
honest answers:

| Question | Answer |
|---|---|
| "Is this gambling?" | No money can be won or taken out. MB are practice money with no cash value. |
| "Why would I pay?" | Nothing needs paying for: the market, the Daily, the lessons, 17 indicators and the drawing tools are open. Pro adds leverage and more indicators, Expert adds bots and backtests. Bought MB cannot lift a place on the return boards. |
| "Why not real data?" | An invented market runs at any hour, can speed time up, and nobody can look up what happens next. |
| "Do the bots cheat?" | They see what players see and pay the same 0.1%. Nobody's trade moves a price. |
| "Are the bots labelled on the boards?" | Today the pages do not mark them (your decision of 10 Nov), and the title says they exist. Decide your answer before you post. |
| "Was this written with AI?" | Your own honest answer. Have it ready; it will be asked. |
| "Is it open source?" | Your call; say what is true today. |

If the post does not take off, do not repost for at least a few weeks, and never ask anyone to upvote it.

## Product Hunt

**Account:** your own personal account, made a few days before, with a real name and photo. A company account
cannot launch. **When:** the day starts at 00:01 Pacific time; any weekday. Not the Show HN day.

**Name:** `Meme Street`

**Tagline** (57 characters; the limit is 60):
```
A made-up stock market that never closes. Practice money.
```

**Link:** `https://memestreet.net/?ref=ph`

**Description** (under 260 characters):
```
Learn to trade on a made-up market that runs around the clock: 180+ invented companies, news that moves prices, 114 lessons and a two-minute Daily Chart, the same for everyone. You start with 1,000 MB of practice money. MB have no cash value.
```

**Topics:** Education, Investing, Games (pick from what the form offers; never "Crypto" or "Betting").

**Pricing field:** "Free with paid options" (or the form's nearest choice). The paid options are MB packages and
the Pro and Expert memberships.

**Pictures** (I can make these in the browser when you are ready): the market page, a stock page with its chart
and news, the Daily Chart mid-game, the Daily's result card, a lesson.

**Maker's first comment:**
```
Hi, I made Meme Street.

It is a stock market where every company is invented, so it can run at any hour and nobody can look up what happens next. One game day takes 30 real minutes, so you see in a week what a real market shows in a year: trends, breakouts that fail, earnings days, crashes and recoveries.

The fastest way in is the Daily Chart: one mystery chart a day, the same for everyone, two minutes, no account needed. https://memestreet.net/daily?ref=ph

Everyone starts with 1,000 MB of practice money. MB have no cash value and are never paid out. The 114 lessons are open to all. The shop sells extra MB and two memberships with more tools; bought MB cannot lift a place on the return boards, which rank percentage return.

The rule behind the price model is "realism you can learn from, but no free money": the simple tricks, like buying every dip, are checked to earn less than holding the index after costs.

Tell me where it confused you. That is the most useful thing I can hear today.
```

## The launch lists

The same name, link pattern and texts serve all of these. Use the tagline and description above, or the longer
text below where a form has room. Free listings only: never pay for a "featured" or "skip the queue" spot.

**Longer description** (for forms with room):
```
Meme Street is a made-up stock market that runs around the clock, for learning to trade without risking real cash. There are 180+ invented companies, indices and funds, news that moves prices, a new leaderboard every day and 114 lessons. Everyone starts with 1,000 MB of practice money; MB have no cash value and are never paid out. The Daily Chart is the two-minute way in: one mystery chart a day, the same for everyone, no account needed. Simple tricks such as buying every dip are checked to earn less than holding the index, so what you practise is judgement, not a cheat code.
```

| Where | How (check on the day) | Link to give | Notes |
|---|---|---|---|
| Launching Next | the submit form at launchingnext.com/submit | `https://memestreet.net/?ref=launchingnext` | The free queue is slow. Do not pay to skip it. |
| SideProjectors | add a project as a "showcase", not "for sale" | `https://memestreet.net/?ref=sideprojectors` | |
| Peerlist | Launchpad on your Peerlist profile; launches run by the week | `https://memestreet.net/?ref=peerlist` | Put "practice money, no cash value" in the first line: finance projects get checked. |
| Uneed | the free queue at uneed.best (50 days or more) | `https://memestreet.net/?ref=uneed` | Join the queue now; it costs nothing to wait. |
| SaaSHub | submit a product, then add it as an alternative to Investopedia Simulator and Wall Street Survivor | `https://memestreet.net/?ref=saashub` | |
| AlternativeTo | texts and link are in `growth/directories.md` | `https://memestreet.net/?ref=dir_alternativeto` | |

**Peerlist first line:**
```
A made-up stock market for learning to trade. Practice money only: MB have no cash value and are never paid out.
```

**Categories**, wherever a form asks: education, finance, games or simulation. Never betting, casino or crypto.

## After each post

Add a line to `growth/weekly.md` with the date and the place. On the Monday after, read the `ref` rows: a place
that sent fewer than 5 finished Daily Charts a week after 4 weeks gets no more time.
