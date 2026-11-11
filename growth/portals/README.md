# Game portals: the files to upload and what to write

The portal build from `docs/REACH_PLAN.md`. You submit each one yourself; I never log in as you.

## The files

| File | What it is |
|---|---|
| `daily_standalone.zip` | The Daily Chart as one page (`index.html`, 160 KB): thirty baked charts, no server, no sign-in, no link, no request to any address. It plays the moment it opens. |
| `daily_standalone.html` | The same page, unzipped. Double-click it to try it. |
| `daily_itch.zip` | One page that shows the live Daily from memestreet.net in a frame, tagged `ref=itch`. It only works once `/embed/daily` and the new Caddy rule are live. |
| `shots/` | Four pictures of the game for the listings. |

Rebuild and check after any change to `tools/portal_daily.html` or to the Daily's rules:

```
python tools/portal_build.py --check growth/portals/shots
```

The check plays thirty scripted games in a headless browser and compares every trade, the result and the result grid
with the game's own rules in `game/daily.py`. It also fails if the page asks the network for anything.

The standalone game differs from the live Daily in three ways, and the listing should not claim otherwise: the charts
are in the file (a month of them, the day picks the first one), there is no board or streak, and nothing is saved.

## Where each file goes

| Portal | File | Notes |
|---|---|---|
| itch.io | `daily_itch.zip` once the frame is live; `daily_standalone.zip` before that | Kind of project: HTML. Upload the zip and tick "This file will be played in the browser". Frame size 960 x 720, with the mobile friendly and fullscreen options on. The page text may link to `https://memestreet.net/?ref=itch`. After publishing, open the page: if the frame is blank, itch.io serves games from a host that is not in the list in `deploy/Caddyfile`; add it there. |
| CrazyGames | `daily_standalone.zip` | Their rules (docs.crazygames.com/requirements, read 11 Nov 2026 through a search summary, not first hand): without their SDK the whole game must be under 50 MB, or 20 MB for phones; content must suit PEGI 12; the only ads allowed are theirs. Their SDK is needed for a full launch. The file carries no SDK, so expect a basic launch at most; say if you want the SDK added. |
| Coolmath Games, Playgama, Y8 | `daily_standalone.zip` | I have not read their current rules. Read them on the day. |

One line on the end screen names memestreet.net as plain text (it is not a link). If a portal refuses any address in a
game, delete the line under the `SITE` comment in `tools/portal_daily.html` and rebuild.

Visits that come from the standalone game cannot be counted, because it has no link to tag. Only the itch.io frame and
the links you put in a listing's text show up under their `ref` in the admin page's visitor table.

## Listing text

**Title:** Daily Chart: the two-minute trading game

**One line:** One made-up stock, two minutes, 1,000 of practice money. Can you beat the chart?

**Description:**

A new candle prints every second. Buy if you think the price will rise. Short if you think it will fall. Two minutes
later the game shows your return, a grid of how each fifteen seconds went, and whether you beat simply holding the stock.

The stock is made up and so is the money: MB are practice money with no cash value, and nothing here is investment
advice. There is nothing to buy and nothing to sign up for in this version.

From the makers of Meme Street, a made-up stock market that never closes.

**Controls:** Mouse or touch. Keys: B buys, S sells or shorts, 1 to 4 pick the size (25, 50, 75 or 100%).

**Genre and tags:** simulation, strategy, educational, finance, stock market, trading, short session, single player

**Age:** No violence, no chat, no purchases. It teaches short selling, which some children's portals may not want.
