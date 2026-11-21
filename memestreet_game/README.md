# Meme Street Daily

Since 18 November 2026, memestreet.net is just this game, and this folder is its project home. The owner's words: "route
the daily to memestreet.net. that's ALL there should be. the rest of memestreet is being retired."

One real US stock chart a day, the same for everyone. Two minutes to trade it with practice money, then its name is
revealed. You don't need an account. A free account keeps your streak on every device, and adds a weekly streak freeze,
your history and the archive of past days.

## Where everything is

| Part | Where | What it is |
|---|---|---|
| The reels | `memestreet_game/reels/` | The Daily's reel pipeline: it writes, voices, renders, reviews and posts. It deploys to the reel server with `reels/deploy.sh`. |
| The game page | `web/daily.html` | What memestreet.net shows: the game, the result and reveal, sign-up and log-in, stats, history, the archive replays, sharing. |
| The admin page | `web/admin_daily.html` | memestreet.net/admin, with the admin key. It has eight tabs: today, the day-by-day log, players, streaks, coming back, the stocks, sources and sharing, and sign-ups. |
| The game's rules and numbers | `game/daily.py` | It picks the day's real chart, runs the game on the server (candles still to come never reach the browser), and keeps streaks for visitors and members, the freeze, history, archive and admin numbers. |
| Just the Daily | `game/pages.py`, `game/server.py`, `game/engine.py` | `DAILY_ONLY`: every other page sends people to `/`, every other API returns 410, and the market stands still. The code of the retired site stays, unserved. `MS_FULL_SITE=1` serves it again. |
| The real charts | `content/daily_real.json` and `reels/src/daily_reel_charts.json` | 366 charts for the game (a year without a repeat) and 186 other stretches for the reels, so a reel never shows a chart the game will play. Both come from `tools/daily_bank.py`. |
| The tests | `tests/test_daily.py`, `tests/test_daily_only.py` | The game, the streaks, the merge when a visitor signs up, the freeze, the archive, the admin numbers and the site's routes. |
| The offline copy | `memestreet_game/static/` | The first version: one static page with no server, its charts in files. It is kept for game portals. memestreet.net does not use it. |

The live site's code stays in `game/` and `web/`, because that is what the server at /opt/memestreet runs and what
`deploy/upload.ps1` sends. Moving it here would mean changing the live service.

## The data

The source is OpenML dataset 43497, "5-years-historical-stock-quotes" (https://www.openml.org/d/43497), released as
**CC0: Public Domain**. It has daily, split-adjusted prices for every US stock from February 2016 to February 2021.
To rebuild both banks:

```
curl -L -o dataset_43497.pq https://data.openml.org/datasets/0004/43497/dataset_43497.pq
python tools/daily_bank.py dataset_43497.pq
```

Stooq and Yahoo forbid redistribution. Newer charts need a licensed source, and that costs money (docs/ROADMAP.md, RM1).

## The reels

Five a day, every one about the Daily:

| Slot (UTC) | Format | What it is |
|---|---|---|
| 10:00 | Money On Your Chest | The serial, one part a day, in the 3D town (`src/story_reel.py`, `src/stories.json`). |
| 03:00 | Yesterday's stock | The Daily that ended at midnight, replayed: how players did, the best trade, then the name. When last night's chart wasn't a real one, a Beat the chart reel takes the slot. |
| 09:00, and 21:00 at weekends | Guess the stock | A real stretch from the reel bank plays out. Three names to pick from, then the reveal. |
| 13:00 | In this town | One complete story a day in the 3D toy-block town, on the form of the "In This Town" stories (`reels/research/niche3d_2026-11-21.md`): a rule ("In this town, money shrinks when you're scared"), neighbours coping, one loved person, a crisis, a twist that carries one trading idea as a truth about people, a question on screen at the end. About 95 seconds, no sign-off (`src/town_story.py`). If it can't be made: a crazy stock story, then a game reel. |
| 18:00 | Crazy stock history / Stock explainer | They take turns by the day: the whole history of one famous stock moment, or one idea explained through such a story; researched, fact-checked, acted out in the 3D town (`src/stock_story.py`). If it can't be made: a game reel. |
| 21:00 on weekdays | Market today | The day's biggest market story after the US close, researched across three outlets and fact-checked twice. If no story passes, a game reel takes the slot. |
| after 23:00 | Daily recap | Tonight's chart, revealed: the stock, what a candle was and the dates, the levels it tested and how each held, and when it moved a lot, the reason from the news, fact-checked. |

Since 2026-11-21 the game reels (Yesterday's stock, Guess the stock, Beat the chart) are filmed in the 3D town first, the real chart on the square's big screen (`src/town_daily.py`); the flat stick-figure reel is made only when the town's one fails. Higher or lower, Market today and the recap are still flat. No AI video (Higgsfield was tried for one reel on 2026-11-19 and stopped).

None of them names or hints at today's stock before the recap.

The voice is ElevenLabs. Each line is read knowing the lines either side (so a sentence ends like a sentence), with a breath
after it before the cut, and a countdown is a real three-second pause with a tick each second, never spoken.

Two tools the owner asked for were reviewed on 2026-11-19 before use. **open-higgsfield** (github.com/wide-trace/open-higgsfield,
a web front end for the Higgsfield platform) is clean; the pipeline already spoke to that platform (`src/footage.py`), so it now
uses the newer models open-higgsfield maps (Soul 2 for the still, Kling 3.0 Turbo to move it, 1080x1920), with the old pair as a
fallback, under the $60 monthly cap in `footage.py` (`HF_MONTHLY_CAP`). **voicestudio** (github.com/debpalash/voicestudio,
AGPL-3.0, local text-to-speech) is clean too (its telemetry is opt-in; its pipe-to-shell installer was not run), but its engines
need far more memory than the reel server has (2 cores, 3 GB); running it means a bigger server, the owner's call. Deploy from Git Bash:

```
memestreet_game/reels/deploy.sh
```

The old folder `tools/memestreet_daily_reel/` is retired, and its `deploy.sh` refuses to run.
