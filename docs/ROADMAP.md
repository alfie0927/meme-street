# Meme Street roadmap

**Goal:** an informational game where people **learn to trade, or just trade for fun**, on a realistic, fictional
stock market. **Technical analysis is the core** (charts that behave like real charts, and the tools to read them);
news and the economy are background. Everyone starts with **1,000 MB**; MB are a game currency with no cash value,
never paid out. The site earns from **MB packages** and **Pro and Expert passes**. **The Daily Chart** is the front
door, the daily reason to come back and the thing people share: every link lands on it and it needs no account. The
course is a **path** (units, exercises, XP, a streak). **Instagram reels are how people find the site**: eight a day,
written, rendered and posted by the pipeline in `tools/memestreet_daily_reel`. Later the site builds a **bridge to
real markets**.

**This file is the one plan, for the site and for the reels.** Check it before starting any work, and update
`HOW_IT_WORKS.md` (what the code does **today**) after every change. Section 3 is the order of work, section 4 is
what only you can do, section 5 lists everything open by track.

Size key: **S** = under a day, **M** = a few days, **L** = a week or more. "Me" is Claude, "you" is the owner. IDs are
kept from earlier plans because the code and `HOW_IT_WORKS.md` refer to them: the site's tracks as before, **A1 to
A11** the reel steps of the reach plan, **RL** new reel items, **RC** reach and distribution.

*Rewritten 2026-11-12 as a single plan. It replaces `docs/REACH_PLAN.md` (11 Nov) and `docs/GROWTH_PLAN.md` (9 Nov):
their open items, rules, findings and targets are folded in here, and both files are in git history up to commit
2cc9309. Earlier rewrites: 2026-11-07 (a review through three players' eyes), 2026-10-24.*

---

## 1. Rules

**The product**

1. **Realism you can learn from.** Behaviour real markets show appears at realistic rates: a support level holds often
   enough to be worth trading and breaks often enough that a stop is needed.
2. **No free money.** No simple, unskilled rule (buy everything, buy every dip, always fade, doubling down, shorting
   everything, selling every option) may beat holding the index by a wide margin, costs included. Skill shows as better
   *risk-adjusted* results over many trades, never as a guaranteed win. Checked by `tools/realism.py` and
   `tools/option_check.py`.
3. **Players' trades never move prices.** The market is the same for everyone, and a big account cannot push it.
4. **Paying never buys a rank.** The return boards rank return on money put in, so buying MB gives more capital to
   practise with, not a better place. (The profit boards and leverage bend this: section 7, risks 4 and 11.)
5. **Honest selling.** Prices are shown before every purchase, MB are clearly worthless outside the site, there is no
   purchase prompt at the moment of a loss, and there are spending limits.
6. **Every MB is accounted for.** Every money event is in the ledger with its source (start, purchase, reward, refund,
   admin); `total_tokens == minted` always.
7. **One meaning per word.** One daily game (the Daily Chart), one learning streak, one badge system. Nothing on the
   profile that pays nothing and teaches nothing.

**Getting players**

8. **No spending without your yes.** The free route first: no ads or boosted posts, free listings only, each app's own
   scheduler, the mail service's free plan (the reminder email stops at 70 a day so sign-up codes always get through),
   the local voice and the Claude plan for reels. `TOGETHER_API_KEY` and `OPENAI_API_KEY` are never set.
9. **The posting schedule.** Since 12 November (your call that evening): five reels a day (03:00, 09:00, 13:00,
   18:00, 21:00 UTC), the Daily after 23:00, and a news reel on top when a really big headline breaks (one a day at
   most). The five take turns through every format in one cycle, one reel of each format a day. The slots and the
   count change only when you say so.
10. **Reels:** only director reels reach the grid (each its own device and palette), no 3D and no AI video, Trial
    Reels off, the local Kokoro voice, captions for every spoken word, posted without approval. The craft rules and
    every piece of your feedback live in `tools/memestreet_daily_reel/RULEBOOK.md`.
11. **Honest copy.** No profit promises; always "practice money, no cash value"; no real tickers (a news reel may name a real company and its boss, with no ticker
    symbol and no advice on the share: your call, 12 November); "free account" and
    "play free", never "everything is free"; never ask for votes; say what is sold. No visible "bot" tag (the flag
    stays in the data), and bots are not counted as players.
12. **Nothing fake.** No bought followers or likes, no pods, no follow-for-a-prize giveaways. Creators get an Expert
    account, never cash, and mark posts as gifted. Class accounts never see the shop. Emails only to people who opted
    in, with one-click unsubscribe.
13. **Your name, your hands.** Community posts are written and posted by you. Every first post on a new platform is
    confirmed with you. I never log in as you.
14. **Secrets and the shared checkout.** Never opened: `data/admin_key.txt`, `data/live_admin_credentials.txt`, the
    reel folder's `config.env` (on the server its keys are only loaded, never printed; never upload this PC's copy,
    it wipes the server's Claude login). A Caddy change needs your yes. Several chats work in this checkout: stage
    files by name, never `git commit -a`. A push to `main` goes live with the next SEO run.

---

## 2. Where things stand (12 November 2026)

### The site

**Live on https://memestreet.net** (one Hetzner server, Caddy, a game server and two gateways, fail2ban, the admin
pages behind a second password). **The shop takes real money** (Stripe through Managed Payments, live). Email is
live. Backups every six hours, copied to this computer daily; `/api/health` checked every 15 minutes. Since 7
November: the learning path, the seven-tab menu, an account without the emailed-code wall, the Daily as the front
door (`/play`, *beat my score* links with their own preview title, guest boards, a reminder email), the Daily inside
a frame for itch.io (`/embed/daily`), the visit log, six comparison pages at `/vs`, three calculators at `/tools`,
`/llms.txt`, IndexNow and the web app manifest. About 1,000 tests in 57 files.

| Area | Built | Open |
|---|---|---|
| The market | Drift, regimes, trends in legs, ranges and breakouts, support and resistance of many kinds, volume that confirms, ten named chart patterns, volatility clustering and fat tails, sessions, IPOs and takeovers; 157 companies in 30 sectors (193 listings with the indices and funds), 72 house bots; realism and no-free-money checks | P15, P10, P8, P9, P12, P13, the MARKET_REALISM list |
| Charts and trading | Five chart types, 49 indicators, 16 drawing tools saved on the server, trades and orders on the chart, 2,000 candles a timeframe; limit, stop, trailing and bracket orders; options (buy-only), leverage to 10x (Pro), bots and single-ticker backtests (Expert) | TA-B5, TA-B7, TA-B8, TA-B10, TA-B11, TA-B12, T14, T15, U1 to U7 |
| The Daily Chart | A numbered mystery chart a day, the same for everyone, no account needed; streaks, stats, a result grid, sharing as text, picture and challenge link; a next step on the result card; the reminder email; framed for other sites | TA-D2, TA-D3, TA-D6, TA-D7, TA-D8, TA-D12, browser notifications |
| Learning | A path of **114 lessons in 20 units** (one free start unit, 16 Pro, 3 Expert): placement first, lessons as runs of cards, exercises, XP, levels, a streak, a daily goal, review, leagues; a free tier of two lessons a day; eleven kinds of chart test; public lesson pages | The Learn loop's 8 failing checks, power-ups, the rest of LP15 |
| Found by people | The daily SEO routine (Search Console verified), public lessons, calculators, comparison pages, `/llms.txt`, IndexNow, tracking links, the visit log | Bing, SEO backlog 4, 8, 9, 10, 12, 13; every send in section 4 |
| Community | Four leaderboards open to visitors; chat with moderation, follows, public profiles; badges | S1 to S4, TA-D7 |
| Money | 1,000 MB start, MB by source, five packages, the New Launch Deal, Pro and Expert monthly or yearly, refunds, spending limits, the free restart, invite links | M11, M12, M13, M4, M8, M9, B5, B6 |
| Real markets | Nothing yet: no real tickers, data or broker anywhere in the code | RM1 to RM6 |
| Rules | Terms and privacy, a date of birth at sign-up, the right-to-cancel waiver | R4, R5, R7 to R10 |
| Running it | Staging, rollback, backups off the server, uptime check, CI with lint and types, an error tracker, capacity measured (about 1,000 players at once; 200 visitors opening the Daily at once, none failed) | O4, O8, O11, E2, E5, E6, E7, E9, E11, E14 |

Off on purpose: challenges (`challenges: false` since 23 October), moonshots, sector shocks and two-outcome catalysts.

### The reels

A pipeline on the server (`/opt/memestreet-daily-reel`) writes each reel with Claude, renders it, sends it to a film
critic (two rounds, one rewrite) and queues it; approved reels post on time by themselves. Every reel is a
**director reel**: its own device, palette and scene code, a punch headline, captions for every word. The Daily Chart
reel is made after 23:00 from the day's real chart and retried through the night.

- **Formats in rotation (19):** Stock story, Trading mistake, Expectation vs reality, Trade diary, Chart quiz,
  Technical lesson, Chart breakdown, Breaking news, Instant replay, Strategy test, Chart twist, Hard truth, Big
  players, Guess the move, Trader levels, Stick skit, Rewind, Two traders, Candles talk. Plus the Daily recap, and an
  explainer at 18:00 every third day (Meme Street explained, Daily Chart explained, in turn).
- **Instagram's numbers steer it** (`src/format_scores.py`, twice a day): a format with three or more scored reels is
  cut when its median skip rate is 8 points worse than all reels' and made daily when 8 points better; at least nine
  formats always stay.
- **New on 12 November:** seven formats on trial, the first-3-seconds checklist in every writer prompt, every kind of
  chart test in turn (reels had nearly all been about levels and breakouts), **Technical lesson** back as one lesson
  of the site's curriculum taught in depth, **Strategy test** ("we tested it": `src/backtest.py` runs a rule on every
  listed stock and the reel may say only its numbers), captions lower.
- **Two copies of the code, becoming one (RL1, 12 November).** The server ran the 12 November work; the repo held
  that and the reach plan's reel changes (A2 to A5, A8 to A10, the Loop format), which were **not** on the server. A
  file-by-file comparison found nothing on the server that the repo lacks, so the repo's reel folder is committed and
  sent to the server with `./deploy.sh` (one bundle of the folder's code; the swap waits for the pipeline lock so it
  lands between two reels, keeps the old files in `/root/reel-deploy/<time>/before.tgz`, runs the self-checks and
  puts the old files back if one fails; `logs/deploy.log` on the server has the result). From now on every reel
  change is made in the repo and sent with that script; code is never edited on the server.
- Timers on: auto, make, queue, research. Off: evolve (the lab), trial, post. Waiting for your one command: news
  (section 4).
- **Five a day, one cycle (12 November, evening).** `auto_reel.sh` makes the 03:00, 09:00, 13:00, 18:00 and 21:00
  slots only, and `brief()` in `make_spec.py` picks each reel's format from every format, the one out longest ago
  first (boosted formats first, cut ones never), whatever the hour. **What went wrong that night:** RL1's deploy was
  already waiting on the server with a bundle built at 18:02, before these changes; it ran at 20:04 and put the
  older files back, so the server made seven reels again and lost the "meembucks" line until `./deploy.sh` sent
  the repo again at 10:34 UTC on 13 November. Reels made for the dropped slots were moved to free slots (15T0300,
  15T0900, 16T0300); 13 and 14 November have five each. A deploy bundle is a snapshot: after any reel change, run
  `./deploy.sh` and read `logs/deploy.log`.
- **News reels (12 November, evening).** `src/news_reel.py`, run by `news_watch.sh` every 20 minutes: it reads 15
  free news feeds; only when one story is in four or more outlets is Claude asked whether it is really big; then a
  researcher with web search builds a fact pack (each claim with its status and outlet), the writer makes a director
  reel of the format `Market news`, a fact check reads the script against the pack before the voice and again after
  the critic's rewrite, and an approved reel is queued to post at once. Never deaths, disasters, violence, war,
  crime against a person, health, children or elections; nobody named but the public figures at the centre; an
  unproven allegation is left out altogether; one a day at most; `touch state/news_off` stops it. A full dry run on
  the Huang story (12 November) ran every step and was held by the critic after two rounds (a tilted paper over a
  name tag), so nothing posted: a held story now gets one more fresh draft. The first news reel (Jensen Huang leaving Nvidia) was made by hand
  and posted at 18:06 UTC on 12 November. The same day "memebucks" got its spoken form ("meembucks") in
  `src/pronounce.json`.

### The numbers

| | Now (12 Nov) | 7 Dec | 4 Jan | 1 Feb |
|---|---|---|---|---|
| Median views a reel | about 115 (every reel lands between 100 and 250) | 150 | 300 | 600 |
| Skipped in the first 3 seconds | 52% (best format 24 to 32%, worst 70 to 77%) | 60% | 55% | 50% |
| Visits a day, bots excluded | about 3, none from Instagram's browser | 30 | 100 | 200 |
| Visitors finishing a Daily, a day | not counted yet | 10 | 30 | 60 |
| New accounts a week | not counted yet | 10 | 30 | 70 |
| People active in the week | about 14 | 15 | 50 | 120 |

The targets are tripwires for decisions, not forecasts (section 8). 600 views is about what accounts of this size
average. Reel targets beyond these: 65% still watching at 3 seconds (32% on 11 Nov), half of a short reel watched,
likes at 5% of reach, sends at 1%, a first reel past 300 views.

### What we learned (why the order below is what it is)

1. **Hardly anyone arrives, and reels are the only way in.** In 29 days 3,751 accounts saw the posts, 51 opened the
   profile and 2 tapped the link. Ten new accounts a day needs about 200 visits a day; from reels alone that is
   10,000 to 20,000 views a day. Reels cannot carry it alone, so other ways in are needed.
2. **Instagram gives every reel the same small test, and none passes it.** About 100 strangers see each reel. One that
   lost 24% of them in 3 seconds got 143 views; one that lost 72% got 124. Passing needs watch time, likes and sends:
   ours get 7 to 19 seconds, likes from 1 to 3%, no sends on 40 of the last 45 reels and 2 comments in all.
3. **The opening picture decides who stays.** Reels that open on a person or an odd object already in trouble, and
   say "your", keep 52 to 76%. Reels that open on a bare chart, a list or a definition keep 25 to 30%.
4. **More spectacle is not the lever.** The director look took the hold from 30% to 52% and views did not move. A
   reason to send or comment, and a length people finish, are what is missing.
5. **The account is clean but hollow.** Account Status shows a tick on every line (you, 11 Nov). The 439 followers
   are fake and follow nothing; reach is 99.9% non-followers; the account follows nobody and never comments.
6. **The sign-up wall was a leak** (five fields and an emailed code; fixed 10 Nov), and the bio link went to the home
   page, not the Daily (your profile edit, section 4).
7. **Money waits.** No price tests and no new paywalls until about 100 people play each week; nothing paid is pushed
   at a new player before a first win.

---

## 3. The plan in order

**Reach first** (your call, 12 Nov): reels and distribution, then reasons to come back and bring a friend, then money,
then depth.

### Now, to 26 November

| # | Item | What | Size | Who |
|---|---|---|---|---|
| 1 | RL1 | **The parked reel changes go live** (your yes, 12 Nov: no test render, the scoreboard judges them). A2 to A5 and A8 to A10 are merged into the server's writer beside the 12 November work, the reel folder is committed, and from then on the server is deployed from the repo. **Started 12 Nov:** committed, and the swap on the server is queued between two reels. Next: watch the first reels the merged writer makes (its rules are stricter: a 16-word hook, a 10-word sign-off, a question first in the caption, 60 seconds). | M | Me |
| 2 | RL2 | **All eight slots post.** A slot the critic held twice stayed empty (four of eight posted on 11 Nov). **12 Nov:** a held slot gets a third try with a format that has passed before, and the check before rendering now catches what the critic held 7 of the last 12 reels for: text over other text, and a figure's head over a label or a speech bubble over a face. Still open: figures standing on a chart's candles, the HUD running ahead of the voice (the writer is told; nothing checks it), and the voice pausing inside a phrase (3 of 12). The old reels waiting in the slots of 14 and 15 November are replaced as their slots come up. | S | Me |
| 3 | RL4 | **The first in-depth reels**: the Strategy test (RSI under 30, 83 trades) passed the critic on 12 Nov at 9, 8, 9, 9 and posts on 13 Nov at 03:00; the Technical lesson (09:00) is being made. Fix what holds the next ones. | S | Me |
| 4 | W1 | **The facts sweep.** **Done 12 Nov:** 114 lessons in 20 units in the reel writer's `SITE_FACTS` and in HOW_IT_WORKS (`/about` and `seo/context.md` by the SEO run of the same day); the README no longer says lessons award MB; the RULEBOOK names the Kokoro voice; "Free to play" is out of `growth/directories.md`. | S | Me |
| 5 | RL8 | **One sign-off line** on every reel and in the bio (decision, section 6). Done 12 Nov: how many played is out of the Daily reel's facts and its caption (a small number is no advertisement, and it counted the house bots). | S | Me, after your word |
| 6 | M13 | **Count the funnel**: shop views, buy-box opens, checkout starts, Dailies finished to accounts made; and `growth/weekly.md` filled every Monday (it has one row). | S | Me; you read me the admin page |
| 7 | Section 4 | **Instagram, 15 minutes a day**: remove fake followers, the profile edit, a daily Story, comments. | | You |
| 8 | RC2, RC3 | **The first sends**: your own result to 10 to 20 people; the directories; one challenge link pasted into a chat app to see its preview. | An afternoon | You |
| 9 | RC4, RC6 | **Show HN and the write-up**, after your three answers (section 4). | | You post; the drafts are ready |
| 10 | A11 | **A YouTube channel and its keys**: the same reels on Shorts automatically, and the retention curve Instagram never gives (the control for A1). **13 Nov:** posting is on (6 a day, one of them always the Daily; public); the channel description and its link `memestreet.net/yt` are in `growth/social.md` (yours to paste); the admin page counts clicks from YouTube beside Instagram's. | S | You, then me |
| 11 | RL3 | **Reel reviews on 19 and 26 November**: the scoreboard's first verdicts; A2 to A5 judged on medians of ten or more reels at 24 and 72 hours; `python3 src/learn.py show` on the reel server is the table to read (RL12). | | Me |
| 12 | RL12 | **The learning loop** (the owner, 13 Nov: "figure out why [the best did better and the worst did badly]... collate that knowledge into better reels"). **Done 13 Nov:** `src/learn.py` keeps a ledger of every posted reel (what it was beside what Instagram measured), and once a day, when three new reels are scored, Claude explains the five best and five worst against the medians and rewrites `state/learned.md`, the rules every writer prompt now ends with. First run: 45 reels, 7 rules (odd picturable openers for company stories, a feeling plus one dial for Hard truths, 9+ scenes, no jargon or bare-label openers). Watch: do the rules move the median hold (34) by the 26 Nov review? | M | Me |

### Next, to the end of December

| Item | What | Size | Who |
|---|---|---|---|
| A7 | The picture fills the frame: no bordered panel, the brand row and progress bar lifted above the scene. A dry render for you first. | M | Me, after your look |
| RL5 | A **Market lesson** format for the 45 lessons the Technical lesson does not use (basics, fundamentals, macro, psychology, real markets). | S | Me |
| RL6 | More reasons to send or comment: "which one are you" endings, a call to make before the reveal; a keyword answered by DM if you add Instagram's messaging permission (decision). | M | Me |
| TA-D6 | Past Daily charts: an archive and a practice replay. | S | Me |
| TA-D3, B10 | Share cards: a chart picture for every lesson link (SEO backlog 9), stock and Daily result; share a chart with drawings by link. | M | Me |
| TA-D8, TA-D7 | Streak and result badges (prizes: decision); friends' results beside yours, then group boards with a join code. | S, then M | Me |
| U1 | The phone: a pull-up trade ticket, a compact market list (decision), a check on real phones. | M | Me |
| U2 | A service worker: browser notifications for the Daily, fills and alerts; the installed app works offline enough to open. | S to M | Me |
| B6, B5 | Email that brings people back (a welcome, "your streak is waiting" after 7 days, a weekly review); a capped MB reward for both sides after an invited friend's first finished Daily. | M | Me |
| M11 | A Pro trial: seven days, started from a locked tool. | S to M | Me |
| LP | The Learn loop's eight failing checks, then power-ups (section 5). | L | Me |
| R7, R8, O8, E11 | Download and delete your own account; "How this market works"; a status page; a restore drill. | S each | Me |
| SEO | Backlog 4 (numbered steps as lists), 10 (glossary pages), 12 (more calculators): the daily routine works through them. | | The routine |
| RC7 to RC10 | Portals, the lesson plan and schools, societies, small creators, communities by hand. | 30 min a day | You; I list and draft |
| RC12 | A New Year "7-day chart challenge" from 1 January: seven Dailies, a badge. Built in mid-December. | M | Both |

### Later (2027)

- **Real markets:** RM1 to RM6 (waits for the data source and its cost).
- **Trading depth:** T14 options writing and spreads, T15 bots and backtests, TA-B7 alerts, TA-B5 trade from the chart,
  TA-B8 a screener, TA-B10, TA-B11, TA-B12 the chart as the home screen.
- **The market:** P15 about 60 more companies, P10, P8, P9, P12, P13, the MARKET_REALISM list, TA-E4.
- **Money, once about 100 people play each week:** M12 things MB can buy, M4, M8, M9, price tests.
- **Community and classes:** S1 classrooms (with B8), S2, S3, S4, TA-D2 leagues.
- **Running it:** E2, E5, E6, E7, E9, E10, E14, O4, O11.
- **Reach, later bets:** a Telegram bot game, the Microsoft Store, a Discord Activity, a Reddit Devvit version,
  Pinterest video pins, press, date hooks (section 5, RC13).

---

## 4. Your list (only you can do these)

| # | What | Time | Why | The text is in |
|---|---|---|---|---|
| | **The news watch, once** | | | |
| 0 | Switch the news timer on with one command (my safety check does not let me install a timer on the server): `ssh root@65.109.233.145 "cd /opt/memestreet-daily-reel && for x in service timer; do sed 's#__DIR__#/opt/memestreet-daily-reel#g; s#__USER__#root#g' systemd/memestreet-reel-news.\$x > /etc/systemd/system/memestreet-reel-news.\$x; done && systemctl daemon-reload && systemctl enable --now memestreet-reel-news.timer"` | 1 min | Until then nothing scans the news. | `tools/memestreet_daily_reel/news_watch.sh` |
| | **Instagram, every day** | | | |
| 1 | Remove the fake followers by hand, a few a day (439 left). Never in bulk and never through a tool that logs in. | 3 min a day | They are who Instagram thinks the reels are for. | |
| 2 | The profile: name "Meme Street: Stock Market Game", the new bio, the link `memestreet.net/daily?ref=ig_bio`, three reels pinned, four highlights (Play, How it works, Daily Chart, Lessons). | 15 min, once | 51 profile visits gave 2 link taps. | `growth/instagram.md` |
| 3 | A daily Story with a poll and a link sticker. | 3 min a day | Stories carry a link people can tap. | `growth/instagram.md` |
| 4 | Comment on bigger trading pages; reply to every comment on ours. | 10 min a day | The account follows nobody and never speaks. I draft comments on request. | |
| 5 | Delete the three trial reels and the older Daily #8 versions in the app (the API cannot delete). | 2 min | | |
| 6 | Optional: the in-app retention graph of three best and three worst reels, as screenshots. | 5 min | The API has no retention curve. | |
| | **Sends, once each** | | | |
| 7 | Your own Daily result and challenge link to 10 to 20 people, one by one. | 20 min | Most games get their first players this way. | The Daily's share button |
| 8 | Ten daily-game directories, AlternativeTo, SaaSHub, Finder. | An afternoon | Their visitors play a daily game every morning. | `growth/directories.md`, `seo/directories.md` |
| 9 | Show HN, on a weekday morning US time. First answer three questions: was AI used, are the bots labelled, is it open source. | 1 hour | | `growth/launch.md` |
| 10 | Product Hunt (a personal account), Launching Next, SideProjectors, Peerlist, Uneed. | 1 hour | | `growth/launch.md` |
| 11 | The technical write-up, under your name: dev.to, Hashnode, Medium, Indie Hackers, r/Python, r/webdev, r/gamedev, LinkedIn. | 1 hour | | `growth/writeup.md` |
| 12 | The lesson plan: pick its licence line, then Tes, Share My Lesson, OER Commons, Jump$tart, and the teacher and society emails. | 2 hours | A class is 30 players at once. | `growth/schools.md`, `growth/lesson_plan.pdf` |
| 13 | Portal uploads: itch.io (the frame is live), CrazyGames, Coolmath Games, Playgama, Y8. | 2 hours | | `growth/portals/README.md` |
| 14 | Paste one challenge link into a chat app and look at the preview. | 1 min | The preview title is built; nobody has seen it. | |
| 15 | The same reels by hand on TikTok, X and Reddit; communities by hand, nine helpful posts for each mention. | 30 min a day | X's API costs about $0.20 a post, TikTok's refuses upload tools. | `growth/social.md`; `tools/fetch_reels.ps1` fills `D:\memestreet_reels` |
| 16 | A personal welcome to each of the first 100 new players: two lines and one question ("what nearly stopped you?"). | 2 min each | Their words are the best copy we will get. | |
| | **Accounts and keys** (you put each key into the server's `config.env` yourself) | | | |
| 17 | ~~YouTube~~, ~~Bluesky~~, ~~Mastodon~~ (all on 13 Nov); still open: a Facebook Page, Threads, a Telegram channel; a TikTok Business account. | 20 min each | Each one switches on automatic cross-posting (A11). | `growth/cross_posting.md` |
| 18 | Bing Webmaster Tools: import the site from Search Console. | 5 min | | |
| 19 | Allow `memestreet.net` in the SEO routine's network settings. | 2 min | Its runs cannot fetch the live site. | |
| 20 | Look at Search Console's Performance page about 1 December and tell me what it shows. | 5 min | The routine has no ranking data to aim with. | |
| | **The site and the law** | | | |
| 21 | G2: sign up on a phone inside Instagram's browser; check the Daily reminder arrives; the count of code emails Resend has sent since 31 October. | 10 min | Nobody has tested the path a reel viewer takes. | |
| 22 | G4, R9: the name and contact address the site gives as its operator (also the footer of every email). | Decide | Consumer law, and teachers will ask. | |
| 23 | G3, O11: the old 10,000-MB accounts: reset or keep. | Decide | | |
| 24 | G6 phone alerts (UptimeRobot); G7 chat moderators; G8 watch disputes and the spending limit (R5). | | | |
| 25 | R4 a lawyer's read, and G5 the ad wording: only before any ads. | | Nothing else waits on it. | |
| 26 | O4: a Cloudflare account and the name servers. | 20 min | The server is ready. | |
| 27 | Watch the market live now and then: does it look like a market a trader would recognise? | | The last check no tool does. | `docs/MARKET_REALISM.md` |

---

## 5. Tracks: everything open

### RL and A. The reels

| # | Change | State | Size |
|---|---|---|---|
| RL1 | One copy of the reel code (see A2 to A5, A8 to A10 below); the reel folder committed; the crowded level-line tags, also only in the repo, go with it. | Your yes 12 Nov. Committed 12 Nov; the server swap is queued between two reels. If Instagram refuses a post's container because of the AI label (A8), the poster asks once more without it (`container()` in `src/post_instagram.py`), so the label can never cost a slot | M |
| A1 | Is it the account or the content? | Answered: the account is clean. Still to do: the YouTube control (after A11) and a benchmark of five similar accounts through Business Discovery. Stop rule in section 8. | S |
| A2 | The first 3 seconds: the hook stands whole on frame 0 at 72 to 90 px, the brand row and progress bar hidden until 3 seconds, no label, format promise or definition as the opener, a sound on the first frame. | In the repo, not on the server (RL1) | |
| A3 | The middle: a second hook where scene 0 hands over, the answer kept for the last scene, a beat at least every 4 seconds of speech. | In the repo, not on the server (RL1) | |
| A4 | The short loop: a format `Loop` of 7 to 12 seconds, one scene, no sign-off, that replays at once; half of the 13:00 reels. | In the repo, not on the server (RL1) | |
| A5 | The ending: the question moves into the hook or the middle and is the caption's first line; the sign-off is 10 words at most; the end card comes in over 0.4 seconds. | In the repo, not on the server (RL1) | |
| A6 | The format mix. | Live, and widened on 12 Nov (19 formats, the scoreboard) | |
| A7 | The picture fills the frame. | A scratch test passes the dry render; you look at the before and after first | M |
| A8 | The "AI info" label on every post (Meta asks for it for synthetic voices). | In the repo, not on the server (RL1) | |
| A9 | Captions checked by the writer: the question first, under 125 characters, one searched word, at most five hashtags. | In the repo, not on the server (RL1) | |
| A10 | The writer is shown our own five best and five worst openings every day (`src/own_reels.py`). | In the repo; on the server the file is only a library for the scoreboard (RL1) | |
| A11 | The same reels elsewhere (`src/post_elsewhere.py`): YouTube Shorts, a Facebook Page, Threads and Telegram; one text post a day with the Daily's link to Threads, Telegram, Bluesky and Mastodon. | On since 13 Nov for YouTube (6 a day, one always the Daily; public) and for the daily text post on Bluesky and Mastodon (first post 13 Nov 14:56 UTC, links tagged `bsky` and `masto`). Facebook, Threads and Telegram wait for their keys | S a platform |
| RL2 | All eight slots post. | 12 Nov: a third try for a held slot; the dry run (`qa(t, 1)` in `src/reel.html`) rejects text over text and a figure's head over any text. Open: figures on candles, the HUD ahead of the voice, pauses inside a phrase | S |
| RL3 | The scoreboard decides which formats stay; reviews on 19 and 26 Nov. | Running; no format has three scored reels yet | |
| RL4 | The in-depth formats. Next for the tests: more candles a stock (the game's `/api/reel/stock` gives 120; a length parameter would give every rule more trades) and short-selling rules. | Live 12 Nov; the first two reels are being made | S |
| RL5 | Market lesson: the other 45 lessons. | Open | S |
| RL6 | Reasons to send or comment beyond A5. | Open; the DM part is a decision | M |
| RL7 | The reel's facts stay true: `SITE_FACTS` and `DAILY_FACTS` change when the site does. | Corrected 12 Nov (W1); a standing duty | S |
| RL8 | One sign-off line. (The players count left the Daily's facts on 12 Nov.) | Decision | S |
| RL9 | Dead weight out of the reel folder: `src/recap.html` (still the renderer's default page), `src/voice.py`, `src/queue_reels.py`, `test_three.sh`, `post_reel.sh`; and the lab (`lab/evolve.py`, `lab/winners.py`, `trial_pair.sh`, `src/reel_v2.html`) if the evolve timer is retired. | Decision | S |
| RL10 | The Instagram token expires on 1 January 2027: renew it in December. | Open | S |
| RL11 | The audience panel's weights are uncalibrated (`lab/audience.py`): calibrate on real insights or drop it from the dry run. | Open; `state/reel_ledger.json` (RL12) is now the data to calibrate on | S |
| RL12 | The learning loop: Instagram's numbers explain each reel; the lessons go to the writer (`src/learn.py`, `state/learned.md`). | Running since 13 Nov. Later: read Instagram once a day for all three (`own_reels`, `format_scores`, `learn`); YouTube numbers in the ledger once its key can read | M |

Done: director reels and posting without approval (9 Nov); the Daily as a director reel with retries, captions on
every scene, covers, the explainer every third day (10 Nov); the format mix, reels at 35 to 60 seconds (11 Nov); one
format a day, seven new formats, the scoreboard, the first-3-seconds checklist, the in-depth formats, every chart
test in turn (12 Nov). Dropped: the fixed shot library as a requirement, Trial Reels, the trial winners step, footage
video, the neon 3D look, the props asked for the library (a kraken, a moat, a sick dragon, a recall).

### RC. Reach and distribution

| # | Channel | What | Who | State |
|---|---|---|---|---|
| RC1 | Challenge links | A link's own preview title ("Sam got +3.1% on Daily Chart #9. Can you beat it?"). | Me | Live 11 Nov (reach plan P1); the chat-app check is yours |
| RC2 | Your own circle | Your result to 10 to 20 people. | You | Open |
| RC3 | Directories | Dle Hunt, Playlin, The DLES, the `dles` list, DLES.gg, Dailydle, Wordles of the World, Dailies.games, The Daily Game Index, browsergames.top; AlternativeTo, SaaSHub, Finder. Later: pull requests to wordleweb and awesome-wordle. | You send | Texts ready |
| RC4 | Show HN | "A stock market that never closes, with 72 bots and no free money", playable with no sign-up. The draft's rank claim must name the profit boards (risk 11). | You post | Draft ready; the load check passed |
| RC5 | Launch lists | Product Hunt, Launching Next, SideProjectors, Peerlist, Uneed. | You send | Drafts ready |
| RC6 | The write-up | "How I built a stock market that never closes", then Python Weekly and PyCoder's Weekly. | You post | Draft ready |
| RC7 | Schools and students | The one-page lesson plan; UK university investing societies (20 personal emails a week: a private board for a meeting or a term league); economics and business teachers. One address may start only three visitor games a day (`daily_visits_per_ip`), so a class needs accounts or a higher number (decision). | I list and draft, you send | Plan and texts ready |
| RC8 | Game portals | itch.io, CrazyGames, Coolmath Games, Playgama, Y8: the Daily as one self-contained file (`tools/portal_build.py`). | You submit | Builds ready |
| RC9 | Communities by hand | r/WebGames, r/playmygame, r/InternetIsBeautiful, r/SideProject, learn-to-trade threads, The Student Room, daily-game Discords, Quora. Each one's rules first. | You | Open |
| RC10 | Small creators | 1,000 to 20,000 followers in finance education and student money: an Expert account, their own board, a tagged link; five messages a week. | I draft, you send | Not started |
| RC11 | Search | The daily routine; outreach to "best simulators" and "Wordle alternatives" lists; journalist-request services. | Me | Running |
| RC12 | New Year | A 7-day chart challenge from 1 January. | Both | Not started |
| RC13 | Later bets | A Telegram bot game (cheap: it opens our own address); the Microsoft Store through PWABuilder; a Reddit Devvit version; a Discord Activity; Pinterest video pins; a weekly long YouTube compilation; press ("Wordle for trading") once there are players to quote; 28 January (the GameStop anniversary), Global Money Week in March, Financial Literacy Month in April; an own Discord at 20 to 50 regulars. | | Later |

Ruled out: Google Play ($25), Apple ($99 a year), the X API (paid), BetaList (paid), Teachers Pay Teachers ($29), Poki
and Yandex Games, Snapchat Spotlight (it stopped recommending wholly AI-made videos), paid ads, any tool that posts
through browser cookies. Counting: every link carries its own `ref` tag; `tools/visits.py` reads the visit log.

### SEO

The daily cloud routine keeps its own state in `seo/` (`backlog.md`, `log.md`, `keyword-map.csv`); `seo-ship.yml`
merges and deploys its SEO-only pull requests. Open in its backlog: **1** Bing (yours), **4** numbered steps as
lists, **8** stock pages (low), **9** a picture per lesson link, **10** glossary pages, **12** more calculators
(**13**, the course size on `/about`, was done by the run of 12 Nov). Missing: a Search Console connector, so runs
have no ranking data.

### TA-D. Playing for fun, and the Daily Chart

| # | Change | How | Size |
|---|---|---|---|
| TA-D2 | Weekly competitions and leagues | Weekly events ranked on return on money put in and risk-adjusted return, small capped MB prizes. | M |
| TA-D3 | Share a chart | A chart with drawings, in chat or by link. | M |
| TA-D6 | Past charts | Every finished chart kept in `daily_game["archive"]` (stored, not regenerated); a practice replay apart from plays and stats; a list page with each day's winner. | S |
| TA-D7 | Friends and groups | Today's results of the people you follow beside yours; later a group code (a class, a group chat) with its own board. | S, then M |
| TA-D8 | Streak and result badges | 3, 7, 30 and 100-day streaks, a first place, beating the stock five days running; a Daily row on the profile. Prizes: decision. | S |
| TA-D9 | Browser notifications | The email is done; a notification needs the service worker (U2). | S |
| TA-D12 | A Real Daily | Once RM1 exists: an unnamed real ticker and period, revealed at the end; its own board. | M |

Done: TA-D1, TA-D4 the Daily Chart, TA-D5 play without an account, TA-D9 the reminder email, TA-D10 the result card's
next step, TA-D11 the Daily in the menu and on the profile; the front door of 10 November (`/play`, the result before
the save box, *beat my score* links, guest boards); the embed (B11).

### LP. The learning path

No MB is paid for learning: XP only.

| # | Change | How | Size |
|---|---|---|---|
| LP16 | The Learn loop, to the end | `docs/learn-loop/LEDGER.md` stands at 11 of 19 checks. Failing: 55 lessons with three exercises (four wanted), runs of teach cards in 35 lessons, the right answer's position biased in 8 units, 73 throwaway wrong options, 114 of 130 lessons written, praise beyond the basics, the placement test's early stop, the persona scoring for rubric v2. Restart with `/loop Follow docs/learn-loop/LOOP.md`. | L |
| LP17 | Power-ups (asked for on 8 Nov, nothing built) | In the ledger's order: the table and the inventory, then the Learning, Protection (a streak freeze), Insight and Flair kinds. *See the future* is large (the engine must commit to the path it previews) and its user cannot trade options afterwards: the one sanctioned exception to rule 2. | L |
| LP15 | Better exercises, the rest | The hand rewrite of the six core units, the which-chart and place-the-stop formats, Bollinger and VWAP overlays. | M |

Done: LP1 to LP14 (the path, exercises, XP, the streak, review, leagues, the placement test, the free tier of two
lessons a day, three Expert units), LP16's first two runs. Before the path: TA-C1 to TA-C4 (the course, the chart
tests, the glossary) and L10; folded into LP: TA-C5, TA-C7, L8, L11; dropped: L3 challenges (off since 23 October),
L4, L5, TA-C6. Small findings left in the ledger: the review re-asks questions seen minutes ago; task buttons for
limit, option and trail orders open the wrong page.

### TA-B and U. Charts, trading tools and the interface

| # | Change | How | Size |
|---|---|---|---|
| TA-B5 | Trade from the chart | Drag lines for entry, stop and target; the ratio and the size update as you drag; one click places the order and its bracket. | M |
| TA-B7 | Alerts | When the price crosses a drawn line or a bot rule is true; in the page and by email. Shared with RM6. | M |
| TA-B8 | A setup screener | Stocks near strong levels, breakouts on volume, squeezes, RSI extremes, gaps, new highs and lows, named patterns. | M |
| TA-B10 | Multi-chart layouts | Two or four charts, linked timeframes, an index or sector overlay. | M |
| TA-B11 | Replay mode | Step through a past period and trade it in a practice account (needs E5). | L |
| TA-B12 | The chart as the home screen | The chart in the middle, a watchlist, the ticket and positions; the table stays as "all stocks". | M |
| U1 | Phone, second step | A pull-up trade ticket; a compact market list (the first price is about 1,000 px down; the compact version drops Buy and Short from phone rows: decision); the chat dot is hidden on phones; a check on real phones. The manifest is live. | M |
| U2 | Notifications | A list, sounds, a service worker with browser notifications for fills, alerts and the Daily. | S |
| U3 | "While you were away" | Equity change, fills, news on holdings. | S |
| U5 | Accessibility and a light theme | Arrows beside colours, keyboard shortcuts, a light theme, translations. | M |
| U6 | Market overview | A heatmap. | M |
| U7 | Low-data mode | Pausing when the tab is hidden is partly there; send only what is visible. | S |
| U13 | One password box | A "show" switch instead of the second box (`pw2` is still in `web/index.html`). | S |

Done: U10 the cut, U11 beginner fixes, U12 the seven-tab menu, TA-B1 to TA-B4, TA-B6, TA-B9, TA-A10; T1 to T9 (done
or moved into the TA-B items), T10 options for everyone, T11 leverage, T12 bots, T13 backtests; S5, U8, U9.

### T. Options, bots and backtests

| # | Change | How | Size |
|---|---|---|---|
| T14 | Writing options and spreads (Pro) | Sell to open: a covered call, a cash-secured put, a naked option with margin; cash settlement at expiry; verticals, straddles, strangles and iron condors as one order; a strategy builder. `option_check.py` gains the written strategies (risk 9). | L |
| T15 | Bots and backtests, next | Sharpe, Sortino, CAGR, time in market and a benchmark line; a walk-forward split; a parameter sweep; a portfolio backtest; a stop and target per rule; share a bot by link; an "alert" action; export bot JSON. No Python bots. | S to M each |

Options later, if wanted: limit orders on options, implied-volatility history, options on the MSI 50 and the ETFs.

### RM. The bridge to real markets

The market stays fictional (rule 3). Real data enters as **delayed real charts to practise on**, never as something
to trade for money, and every real-chart page says "delayed, practice money, not advice".

| # | Change | How | Size |
|---|---|---|---|
| RM1 | Real candles | A licensed source for about 100 real tickers, daily and hourly, delayed (Twelve Data, EODHD, Alpha Vantage, Tiingo or Polygon: Stooq and Yahoo forbid redistribution). `tools/real_import.py` writes `data/real.db`. **Decision: the source and its monthly cost.** | S once decided |
| RM2 | Real charts page | The same chart, indicators, drawings and chart tests on real candles. | M |
| RM3 | Backtests on real candles | `run_backtest` with real rows. | S |
| RM4 | The Real Daily | See TA-D12. | M |
| RM5 | "Ready for real money?" | A readiness checklist from the player's own record, what carries over, how to choose a broker. No broker links before R10. | S to M |
| RM6 | Export your tools | Download bot JSON and alert rules; a script evaluates them on the player's own computer. | S |

### P and TA-A. The market

| # | Change | How | Size |
|---|---|---|---|
| P15 | More companies and industries | A pack of about 60 companies: two-member sectors filled to four and eight new industries; `max_companies` raised from 200 to 260; the tick measured before and after. | L |
| P10 | Asset classes that behave like themselves | Bonds fall when rates rise, gold reacts to real rates and fear, defensives hold up in bear phases. | M |
| P8 | Market psychology | Overreactions that partly retrace, "buy the rumour, sell the news", short squeezes, stop runs; each at a measured rate, checked for free money. | L |
| P9 | Factors and correlations | Risk-on and risk-off; correlations that rise in sell-offs. | L |
| P12 | Retire what conflicts | The hidden mood, two-outcome catalysts and distress bets, kept only where they fit. | M |
| P13 | A gentler market for beginners | A calmer market for the first units, or a difficulty setting. | M |
| P16 | The MARKET_REALISM list | Calibrate the equity risk premium on the engine; thinner tails and lag-1 autocorrelation; round-number clustering; reversal and momentum; a bid-ask spread (M8); triangles and cups. | S to M each |

Done: P1 to P7, P11 the realism and no-free-money suite, P14 IPOs and takeovers, TA-A1 to TA-A9; TA-A11 game-time
candles (built, then taken out on request).

### TA-E and N. News and the economy

| # | Change | How | Size |
|---|---|---|---|
| TA-E4 | "Why it moved", technical first | Each stock page says what happened in chart terms, with a headline only when there was one. | M |
| N8-N10 | Parked | Better company stories, a daily wrap written around the chart, LLM headlines. | M |

Done: TA-E1 to TA-E3, N1 to N6 (N7 became TA-E4).

### M and B. Money and growth

| # | Change | How | Size |
|---|---|---|---|
| M11 | A Pro trial | Seven days of Pro, started at sign-up or the first time a Pro tool is tapped; once per account. | S to M |
| M12 | Things MB can buy | Name colours and a title, chart themes, a custom Daily share card, an extra practice go of the Daily, gifting MB. All through the ledger. | M |
| M13 | The funnel | Shop views, buy-box opens, checkout starts; buyers per 1,000 sign-ups, spend per buyer, cohorts by week on the admin page. | S |
| M4 | When an account runs out | A page that shows what happened, with the options. | S |
| M8 | Trading costs that teach | Keep 0.1% a side, or a commission and a spread that widens in thin and fast markets. Decision. | M |
| M9 | Simplify the house | Retire the capital rule, reserve floors, top-ups and alarms. | S |
| B5 | Referral rewards | A capped MB reward for both once the friend has finished a first Daily. | S |
| B6 | Email that brings people back | A welcome, "your streak is waiting" after 7 days, a weekly review, a "send me tomorrow's chart" box for visitors. The reminder is done. | M |
| B7 | Community | A Discord or an Instagram broadcast channel with the daily winners, once 20 to 50 regulars exist. | S |
| B8 | Teachers and creators | Classrooms (S1) with a free trial; a creator programme (RC10). | M |
| B9 | Name and brand | Keep "Meme Street" or rename for a teaching audience. Your decision. | S |
| B10 | Pages people can find | Share cards for lessons, stocks and results (with TA-D3). | S |
| M14 | The shop's launch-deal pop-up | Its auto-open was removed in the interface pass of 8 Nov: restore it or leave it. Decision. | S |

Done: M1 to M3, M5 to M7, M10 shop fixes, B1 to B4, B11 the Daily in a frame, B12 `/llms.txt` and IndexNow (Bing is
yours), B13 the load check, the installable part of U1, the six `/vs` pages, the three calculators.

### S. Community

| # | Change | How | Size |
|---|---|---|---|
| S1 | Classrooms | A teacher account, a class with a join code, assigned units, a class board; the shop hidden. | L |
| S2 | Boards that reward skill | A risk-adjusted or consistency board; leverage counted or capped (risk 4). Decision. | S |
| S3 | Challenge weeks | Weekly themed events with the same starting balance and a skill objective. | M |
| S4 | Sharing ideas | A trade idea (a chart with levels and a plan) shared with followers, delayed. | M |

### E and O. Engineering and running the site

| # | Change | How | Size |
|---|---|---|---|
| E2 | Split `engine.py` | Modules for prices, news, orders, accounts, indices. | L |
| E5 | Determinism and replay | A seeded random stream per market and a tool that replays any period. | M |
| E6 | Observability | Structured logs, metrics, alerts for late ticks and errors. | M |
| E7 | Content tooling | A validator and a preview for content packs. | S |
| E9 | Rough edges | Sparklines reset on restart, the news wire is not saved, content files are checked every tick, the sector-shock line in HOW_IT_WORKS; the R value in `game/learning.py` uses the closing trade against the first stop's risk. | S |
| E10 | Scale the game server | Only when thousands play at once. | L |
| E11 | Ledger housekeeping and a restore drill | Rotation, a restore from the PC copy, a snapshot-against-ledger check. | S |
| E14 | A fast local test run | The suite in parallel across the cores (about 40 minutes in one process today). | S |
| O4 | Cloudflare in front | The server is ready; the account and name servers are yours. | S |
| O8 | Status and capacity | A status page. | S |
| O11 | The old accounts | Announce, back up, reset, or decide to keep them. | S |

Done: TA-F1 to TA-F3, E1, E8, E12, E13, O1 to O3 (O1 is real email, the launch list's G1), O5 to O7.

### R and X. Rules, and what is left of the old plan

| # | Change | How | Size |
|---|---|---|---|
| R4 | A lawyer's read | The terms and privacy pages; what ads may say. Before any ads. | S |
| R5 | Responsible spending | A lower default than US$500 in 30 days, a cool-off, a note that buying MB makes nobody a better trader. | S |
| R7 | Data rights | A player downloads their data and deletes their own account (the privacy page says "email us" today). | M |
| R8 | "How this market works" | What drives prices, what is random, that player trades never move prices. | S |
| R9 | Who runs the site | A business name and a contact address in the terms and in email footers. | S |
| R10 | Real-market rules | The data licence allows display; broker links, if any, follow UK and EU financial-promotion rules. | S |
| X2 | Moonshots and two-outcome catalysts | Switched off; remove the code or keep as an opt-in section. | M |
| X7 | 3x products | Kept; warnings or an unlock by unit later. | S |
| X9 | Admin "withdraw" | Keep only as an admin correction, renamed. | S |

Done or decided: R1 to R3, R6, X1, X3 to X6, X8.

---

## 6. Decisions

**Open (yours).** The default is what happens if you say nothing.

| Question | Default | Options |
|---|---|---|
| The reel sign-off (RL8) | "Join free at memestreet.net." (the RULEBOOK's line) | "Play today's chart free. Link in bio."; "Play free at memestreet.net/play". |
| A Market lesson format (RL5) | Build it | Leave the other 45 lessons out of the reels. |
| A keyword answered by DM (RL6) | Not built | Add Instagram's messaging permission to your Meta app (free). |
| The evolve timer and the lab (RL9) | Stay paused | Retire the lab and delete its code; switch it back on. |
| X at about $0.20 a post with a link | By hand, free | Pay. |
| A class behind one school address (RC7) | Three visitor games a day per address | Raise `daily_visits_per_ip`; class accounts (S1). |
| The phone market list (U1) | Leave it | The compact list, without Buy and Short on phone rows. |
| The shop pop-up's auto-open (M14) | Stays off | Restore it. |
| Daily Chart prizes (TA-D8) | Badges only | A small MB prize for the day's top three. |
| The real-data source (RM1) | Not chosen | Twelve Data, EODHD, Alpha Vantage, Tiingo or Polygon; which tier; daily only or hourly too. |
| Broker links (RM5, R10) | None | Through an approved firm; affiliate links after legal advice. |
| The old accounts (G3, O11) | Keep them | Reset to 1,000 MB. |
| The default spending limit (R5) | US$500 in 30 days | Lower it. |
| The operator's name and address (R9) | Not given | A business name and an address; a registered agent. |
| The name (B9) | Keep "Meme Street" | Rename for a teaching audience. |
| Moonshots (X2) | Off, code kept | Remove the code; an opt-in section. |
| Costs (M8) | 0.1% a side | A commission and a spread. |
| The boards and leverage (S2) | Leverage counts as it is | Cap it on the boards; a separate board. |

**Decided.**

- Before 7 Nov: Stripe through Managed Payments; package prices; Pro and Expert, monthly or yearly; real-time chart
  timeframes only; 13 or older to sign up; four leaderboards; a free restart when nearly out; the Daily on the site
  and open to visitors.
- 7 Nov: daily quests, the quest ladder, the daily contest and medals removed (U10); 3x products, the bank rating
  and chat kept; the full learning path; options writing Pro only (T14); all three real-market bridges; no Python bots.
- 8 Nov: rubric v2 for Learn (placement first, cards, wrong answers earn nothing, a free tier of two lessons a day,
  full lessons with Pro and Expert, very advanced units); **no MB for learning, XP only**; exercises in every lesson.
- 9 Nov: director reels, each with its own look, posted without approval; no 3D, no AI video.
- 10 Nov: the posting schedule stays; **no visible bot tag**; Trial Reels off; the Daily reel in the director style;
  an explainer every third day; an account without the emailed code; every link lands on the Daily; the visit log;
  no spending.
- 11 Nov: the reach plan with its defaults; reels of 35 to 60 seconds; the Daily in a frame for itch.io; the
  followers are fake and are removed by hand; five formats out (Explained like you're 5, Speed cheat sheet, One
  trick, Myth or fact; Technical lesson, which came back on 12 Nov in a new form).
- 12 Nov: one reel of each format a day; Instagram's skip rate cuts and boosts formats; Technical lesson in depth and
  Strategy test, both up to 100 seconds; **reach first**; **the parked reel changes go live with no test render**;
  this file is the single plan and the two older plans are deleted.
- Settled from the old open list: the rank claim now says "the return boards" (the profit boards stay: risk 11);
  "Session" replaced "Day" (U10); the house bots stay on the boards, flagged in the data only.

---

## 7. Risks

| # | Risk | Why it matters | Where |
|---|---|---|---|
| 1 | **The market must be realistic without free money.** | It is the product: too random teaches nothing, too regular is exploited in a day. | P8 to P16, `realism.py` |
| 2 | **Revenue from losses.** MB packages sell best when people lose. | It works against teaching and draws scrutiny with young users. | M4, M12, R5 |
| 3 | **Minors buying.** | Parents' disputes and refunds; Managed Payments needs a low dispute rate. | G8, R5 |
| 4 | **Leverage and the boards.** A 10x player tops a day's board, or loses everything, by luck. | The boards promise that skill wins. | S2 |
| 5 | **One server.** | A restore has never been rehearsed. | E11, O8 |
| 6 | **The name.** | Cheap to change now, expensive later. | B9 |
| 7 | **Real data licence and cost.** | A monthly bill before the feature earns. | RM1, R10 |
| 8 | **Financial promotions.** Broker links from a UK-run site may need an approved firm. | Fines, and the trust the site runs on. | RM5, R10 |
| 9 | **Selling volatility as free money.** | T14 must be checked like every market change. | T14 |
| 11 | **The profit boards.** A big account tops them with a small return. | "Paying never buys a rank" is false there; the Show HN draft must say so. | S2, RC4 |
| 12 | **Few MB sinks.** | Until M12, MB only buy capital. | M12 |
| 13 | **The reach ceiling may be the account, not the reels.** | Three weeks of changes with a clean status and no reel past 300 views makes the account the suspect. | A1, section 8 |
| 14 | **One Instagram account, one token.** | The token expires on 1 January 2027; a flag on the account stops everything. | RL10, A11 |
| 15 | **Code edited on the reel server by hand.** | It brings back two copies, and the next `./deploy.sh` silently undoes the edit. | RL1 |
| 16 | **The reel budget is the Claude plan.** | Each reel is a long writer call and up to two critic rounds; a held reel costs the same as a posted one. | RL2 |
| 17 | **Long reels against a 7-second audience.** | The in-depth formats run to 100 seconds; the scoreboard cuts them if viewers leave. | RL3, RL4 |
| 18 | **A reel that states a wrong number.** | A strategy test's verdict is worded by code and the writer may say only the facts; the critic checks them. | RL4 |
| 19 | **Several chats in one checkout.** | A `git commit -a` or a whole-file overwrite takes another chat's work with it. | Rule 14 |

(Risk 10, the learning path growing the save, is solved: attempts are capped at 300.)

---

## 8. Review dates, targets and stop rules

**The number that matters:** people, bots excluded, who finished a Daily or made a trade this week.

| When | What |
|---|---|
| Every Monday | `growth/weekly.md`, per source: visits, Dailies finished, accounts made, back within 7 days, invited someone. |
| 19 and 26 Nov | The reels: the scoreboard's verdicts; A2 to A5 on medians of ten or more reels of a format, at 24 and 72 hours, never on one reel (at 110 views a reel's skip rate is good to about 5 points). |
| About 1 Dec | Search Console's Performance page, three weeks after indexing. |
| 7 Dec, 4 Jan, 1 Feb | The checkpoints in section 2, reset after two weeks of real counts. On 1 Feb: double the two best sources and drop the weakest; decide on money (M11, M12) if about 100 people play each week. |
| December | Renew the Instagram token (RL10). |

**Stop rules**

- **Reels:** three weeks under 100 median views with skips above 65% means a change of format. Three weeks of changes
  with a clean Account Status and no reel past 300 views makes the account the suspect: a fresh-account test is your
  call. Under 10 visits a day from Instagram on 4 Jan means your own time goes to the best other source first.
- **Any other source:** under 5 finished Dailies a week after 4 weeks of trying, stop it.
- **Sign-up:** more than 1 attempt in 5 failing means the form is still the leak: take out another field.
- **Email:** any spam complaint, or more than 1 in 200 leaving after a send, stop and rethink.
- **Cross-posted video:** under 200 median views after 4 weeks on a platform, stop that platform.

---

## 9. Checking a change

**A market change**

1. The tests relevant to the change (`python -m unittest test_<module>` in `tests/`); the whole suite
   (`python -m unittest discover tests`, about 40 minutes) only for sweeping changes. They guard money conservation,
   the ledger and the rule that player trades never move prices.
2. `python tools/chart_check.py 12 <seed>` on two or three seeds: the charts against the facts of real prices
   (MARKET_REALISM.md has the targets and the last results).
3. `python tools/realism.py`: stylised facts, pattern rates within their target bands, and the no-free-money strategy
   comparison against holding the index, costs included, on markets never used for tuning; `tools/option_check.py`
   for options (extended by T14 to written options and spreads).
4. A look at the charts by a person: does it look like a market a trader would recognise?
5. Update `HOW_IT_WORKS.md` and this file.

**A site change:** only the tests for what changed; staging first (`deploy/upload.ps1 -Staging`); a page's inline
script is checked in a real browser, not only with `node --check`.

**A reel change**

1. `python src/make_spec.py selftest`, `python src/backtest.py demo`, `python src/format_scores.py demo`,
   `python src/learn.py demo`.
2. A dry run (`lab/silent.py`, then `DRY=1 PAGE=reel.html src/render.py`) and a look at frame 0 and the frame at 1 s.
3. Send it with `./deploy.sh` from the reel folder (whole files, between two reels, automatic roll-back); never
   edit code on the server. A local dry run of a seed fixture deletes its tracked `dry/` frames: use a copy, or
   `DRY_KEEP=1`, or `git checkout` them back.
4. Queued reels are re-rendered with `./rerender.sh <slot>` when the template changes.
5. Your feedback goes into `RULEBOOK.md` (the writer and the critic both read it), then `HOW_IT_WORKS.md`.

---

## 10. Where the detail lives

| What | Where |
|---|---|
| What the code does today | `docs/HOW_IT_WORKS.md` |
| The market's targets and last results | `docs/MARKET_REALISM.md` |
| The reel rules and your feedback | `tools/memestreet_daily_reel/RULEBOOK.md`; reference reels in `exemplar/NOTES.md` |
| The Learn loop | `docs/learn-loop/` (the rubric, the prompt, the ledger) |
| SEO state | `seo/` (the routine's backlog, log, keyword map, reports) |
| Every draft you send | `growth/` (`launch.md`, `directories.md`, `writeup.md`, `schools.md`, `lesson_plan.pdf`, `portals/`, `social.md`, `cross_posting.md`, `instagram.md`) |
| The weekly counts | `growth/weekly.md` |
| The Instagram ranking research of 7 Nov | `tools/memestreet_daily_reel/lab/research/instagram_ranking_2026.md` |
| The two plans this file replaced | git history: `docs/REACH_PLAN.md` and `docs/GROWTH_PLAN.md` at commit 2cc9309 |
