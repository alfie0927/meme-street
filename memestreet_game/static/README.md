# Meme Street: the daily stock chart game (the offline copy)

> memestreet.net runs the server version of this game: see `../README.md`. This static copy is kept for game portals.
> It needs no server, but its charts are public files, and it has no accounts and no leaderboard.

One real stock a day, the same for everyone. Two minutes to trade it. Its name at the end.

Like Wordle: one go a day, a streak, stats, and a result to share as coloured squares (no spoilers in it). It is a
static page with no server and no account. Today's game, the stats and the streak are kept in the player's browser.

## How a game goes

- **Play** shows the stock's last 60 trading days. Then the next 120 days print, one a second: two minutes.
- Buy or sell 25, 50, 75 or 100% at the latest close, as often as you like, with no fees. Selling with nothing held
  opens a short, up to the account's worth. Buying covers it. Keys: B, S, 1 to 4.
- At the end the position is valued at the last close, and the return on $10,000 of practice money is the score.
- Then the page names the stock and its dates, shows its real prices, and names any big event inside those months.
  It also shows the best single trade the two minutes offered.
- Prices show from 100 while you play, so the price level does not give the stock away. Dates are hidden until the end.

The rules are those of Meme Street's Daily Chart (`game/daily.py` in this repo), ported to the browser.

## Files

| File | What it is |
|---|---|
| `index.html` | The whole game: page, styles and script. |
| `charts/<k>.json` | One chart per day of the cycle: 180 rebased candles, and the reveal, base64-encoded so a glance at the file does not spoil it. |
| `charts/meta.json` | How many charts there are (366), and the data's source. |
| `build_charts.py` | Builds `charts/` from the source data. `python build_charts.py demo` is its self-check. |

Day 1 is 18 November 2026, in the player's own time zone, and a new day starts at their local midnight, as in Wordle.
Day N plays `charts/((N - 1) mod 366).json`, so a year passes before a chart repeats.

## Run it

It must be served over http, because a page opened as a file cannot fetch its charts:

```
cd memestreet_game
python -m http.server 8765
```

Then open http://127.0.0.1:8765/. Any static host serves it as it is: Cloudflare Pages, GitHub Pages, Netlify, or
itch.io as an HTML game, with the folder zipped and index.html at its root.

## The data

The source is OpenML dataset 43497, "5-years-historical-stock-quotes" (https://www.openml.org/d/43497). It is
released as **CC0: Public Domain**. It has daily, split-adjusted open, high, low, close and volume for every US stock
from 16 February 2016 to 12 February 2021. Stooq and Yahoo forbid redistribution; this set does not.

The 366 charts come from 145 well-known stocks. A chart is kept only if the stock moved a lot inside the two minutes
(high to low of 1.25 times or more). The charts split into thirds: moderate, big and wild moves. No stock appears more
than four times. At most 15% of the charts cover the March 2020 crash. Ten famous moments are always in, among them
the GameStop squeeze, Kodak's July 2020 spike, Facebook's record fall and the 737 MAX grounding.

To rebuild after changing the stock list or the rules, download the data and run the builder. It needs pyarrow.

```
curl -L -o dataset_43497.pq https://data.openml.org/datasets/0004/43497/dataset_43497.pq
python build_charts.py dataset_43497.pq
```

## Limits

- Every chart is a public file, so a determined player can open tomorrow's. Wordle had the same limit. Hiding the
  charts would need a server that sends the candles one at a time, as the site's Daily does.
- There is no leaderboard and no "everyone's results", because those need a server too.
- The data ends in February 2021. Newer charts need a licensed source (docs/ROADMAP.md, RM1).
