# Instagram: audit, profile and daily routine (@memestreetgame)

Pulled 10 Nov 2026 through the Graph API (`lab/insights.py` plus account insights), read-only. Part of
[docs/GROWTH_PLAN.md](../docs/GROWTH_PLAN.md), Parts 1 and 3. Built with the `ig-audit` and `ig-profile` skills.

## 1. Audit

```
AUDIT  ·  38 reels  ·  30 Oct to 9 Nov  ·  median views 61  ·  median hold at 3 s 32%

LAST 29 DAYS (account)
  3,751 accounts reached   3,745 of them non-followers, 5 followers
  5,072 views              33 of them by followers
     51 profile visits     1.4% of the accounts reached
      2 link taps          4% of profile visits
      0 new real followers (448 on 7 Nov, 448 on 10 Nov)

TOP 5 BY OUTLIER MULTIPLE (views / 61)
  2.4x  148 views  hold@3s 56%  watch  6.6s  Stock story    One bed maker now sells dreams you choose yourself.
  2.3x  142 views  hold@3s 56%  watch 17.0s  Trader levels  Which level of trader are you right now?  (3 saves)
  2.3x  139 views  hold@3s 28%  watch  6.1s  Chart quiz     3 charts. Can you call what happens next?
  2.1x  131 views  hold@3s 70%  watch  9.4s  Stock story    A bed maker that lets you pick your dream? Meet SleepNation Beds.
  2.1x  129 views  hold@3s 62%  watch  8.0s  Stock story    One escaped dragon shut a motorway for a day.

BOTTOM 5
  0.3x   18 views  hold@3s 11%  watch  5.8s  Chart twist    It climbed 9% in 70 minutes. Would you have called it higher?
  0.3x   18 views  hold@3s 46%  watch 20.3s  Daily recap    Daily Chart #2 recap
  0.3x   16 views  hold@3s 18%  watch  6.9s  Chart quiz     Chart quiz #2. Lock in your answers before the reveal.
  0.2x   13 views  hold@3s 27%  watch  3.9s  Tech lesson    Why does price keep stopping at the same spot?
  0.2x   10 views  hold@3s 20%  watch  3.6s  Chart twist    It looked bullish, until the candles said otherwise.

BY FORMAT              n   hold@3s   views    watch
  Stock story          5     56%     2.1x     8.0s
  Trader levels        1     56%     2.3x    17.0s
  Hard truth           5     39%     1.1x     6.3s
  Chart quiz           4     35%     2.0x     6.9s
  Chart twist          8     33%     0.6x     5.9s
  Technical lesson     5     27%     0.9x     3.9s
  Daily recap          7     27%     0.7x     7.4s
  (22 formats from the pipeline's own records, the rest read from the caption)

ALL 38 REELS: 0 comments, 7 sends (3 per 1,000 reached), 10 saves, 48 likes.
```

**What the data says**

1. **The first three seconds decide the views.** The top five kept 54% of viewers past 3 seconds and the bottom five
   kept 24%. Length shows nothing (reels over 60 seconds did as well as 30-second ones), so the openings are the
   problem, not the director reels' length. Fairly confident: 38 reels and a consistent gap.
2. **An odd fact about a made-up company holds people.** Stock stories kept 56% (n=5) against 32% for the account.
   "Which level of trader are you" (n=1) held people 17 seconds and earned 3 of the 10 saves. Moderately confident.
3. **Labels and definitions lose people at once.** "Daily Chart #6 recap", "Chart quiz #2", "Price tells you what
   happened. Volume tells you how much conviction…": 27% hold for recaps (n=7) and lessons (n=5). The Daily recap
   at 23:00 to 01:00 UTC is the weakest slot of the day. Moderately confident.
4. **More posts did not mean more views.** 30 reels from 3 to 9 Nov, 6 to 8 a day from 7 Nov; the median fell
   from 67 to 55 views.
5. **The reels do reach strangers, then nothing happens.** 99.9% of reach is non-followers, so Instagram is
   showing the work to new people. Of 3,751 reached, 51 opened the profile and 2 tapped the link. By the skill's
   rule, views with no follows is a profile problem, and here it is also a hook problem. Both get fixed.
6. **The 448 followers are not real readers.** Instagram cannot tell the gender of 438 of the 440 it profiles,
   it shows none of them online in the last two days, and only 5 saw anything in 29 days. The 100 and 97 likes on
   the two posts of 25 Oct came on a reach of 4 and 6, from an engaged audience mostly in Ukraine (91) and Thailand
   (21), while the followers are listed as mostly US. They cost nothing visible now, because reach goes to
   non-followers anyway. Removing them is optional and low priority: a few dozen a day with Instagram's own "Remove"
   button if you want a clean account.
7. **Posting hour: no conclusion.** 21:00 to 22:00 UTC looks best (hold 56%), but those slots were mostly stock
   stories and the 23:00 to 01:00 slots mostly recaps, so the format explains it.

**STOP:** recap and label openers, definition openers (the 23:00 UTC recap keeps its slot with a new opening; the
posting schedule stays as it is, your decision of 10 Nov).
**DO MORE:** stock stories, trader levels, and quizzes whose first line is the stake ("Most people get this wrong"),
not the name of the format. The reel changes are in [reel-brief.md](reel-brief.md).

## 2. Profile

Score with the `ig-profile` rubric: **about 40/100** (38 of the 76 points I can see; pinned posts, highlights and
the contact button need a screenshot from you).

```
PROFILE SCORE  ~40/100

  name field        2/12   "Meme Street": the name alone, no word anyone searches
  bio first line    5/12   "The stock market, but made up." says what, not who it is for or what they get
  bio body          3/8    a fact, an honest disclaimer, then the biggest ask there is ("Sign up")
  link              3/8    http://memestreet.net: the home page, not the thing the bio promises
  pinned three      ?/10   not visible through the API
  highlights        ?/8    not visible through the API; there are no Stories to build them from
  grid legibility   6/8    consistent covers with a 4-word title; small at thumbnail size
  photo             5/6    the M mark, clean and high contrast (a logo is right for a product)
  handle            5/6    readable and sayable
  category/contact  ?/6    professional account; category and contact button not visible
  recent activity   9/10   posts daily; no comments to answer yet
  story presence    0/6    no Story live, and the pipeline never posts one
```

**The rewrites, in fix-first order.** You change each field on your phone; nothing here touches Instagram.

**1. Name field** (30 characters, the bold line; Instagram search matches it). Pick one:
```
Meme Street: Stock Market Game
```
```
Meme Street | Trading Game
```
```
Meme Street | Learn to Trade
```
The first is exactly 30 characters, and "stock market game" is what people type. (The plan's
"Meme Street | Stock Market Game" is 31 and would not fit.)

**2. Bio** (150 characters). Line one says who it is for and what they get; then the offer; then the honest line.
```
Learn to read charts on a made-up stock market.
Today's chart: 2 minutes, no sign-up 👇
Practice money only, no cash value.
```
Second option, keeping your 30-minute fact:
```
A made-up stock market for learning to trade.
A full day lasts 30 mins. Play today's chart, no sign-up 👇
Practice money, no cash value.
```

**3. Link:** one door that matches the bio:
```
https://memestreet.net/daily?ref=ig_bio
```
The `ref` tag means anyone who signs up from it shows in the admin panel's sign-ups by source.

**4. Pin three reels** (tap ⋯ on the reel, then "Pin to your profile"), each with a different job:
- The offer: "One chart. Two minutes. Can you beat it?" (30 Oct)
- The introduction: "Which level of trader are you right now?" (9 Nov, the best watch time and saves)
- The best hold: "A bed maker that lets you pick your dream? Meet SleepNation Beds." (7 Nov, 70% kept)

**5. Highlights**, once the daily Story below has run for a week: **Play** (how the Daily Chart works, three
Stories), **How it works** (made-up market, 1,000 MB of practice money, no cash value), **Daily Chart** (the daily
Stories), **Lessons**.

**6. Category and contact:** in Edit profile, set the category to "Video game" or "Education" and keep a contact
email you read.

**Re-score:** about 72/100 after steps 1 to 4 (ten minutes of edits); about 85 once the daily Story has run long
enough to fill highlights. The rest is not a rewrite: covers built to be read at thumbnail size, and comments that
get answered once there are comments.

## 3. The daily Story (2 minutes, by hand)

A Story is the only tappable link besides the bio, and the API cannot add link stickers or polls, so this is by
hand. Every day:

1. Play today's Daily Chart. About a minute in, take a screenshot of the chart (before the end, so the outcome is
   hidden).
2. Post it as a Story with a **poll sticker** ("Up or down from here?") and a **link sticker** to
   `https://memestreet.net/daily?ref=ig_story` with the sticker text "Play it".
3. Next morning, the answer: a screenshot of your result card, "Yesterday's chart went ___. Today's is live." plus
   the same link sticker.

**The first week** (one line of text each on top of the screenshot):

| Day | Story text | Sticker besides the link |
|---|---|---|
| Mon | Today's chart. Up or down from here? | Poll: Up / Down |
| Tue | I got +x% on today's chart. Beat it? | Emoji slider: how confident? |
| Wed | This candle shape has a name. Which? | Quiz: three pattern names |
| Thu | Today's chart is a made-up company. Guess what it sells. | Question box |
| Fri | Day x of my streak. Two minutes a day. | Poll: Do you keep a streak? |
| Sat | Which level of trader are you? (frame from the Trader levels reel) | Poll: four levels |
| Sun | Best score this week: +x%. New chart at midnight UTC. | Countdown to midnight UTC |

## 4. Comments and messages (15 minutes a day)

- **On your own reels:** answer every comment by hand within the first hour you see it. Then send the link by
  message (Instagram lets you reply privately to a comment):
  > Thanks for playing along! Today's chart is here, 2 minutes and no sign-up: memestreet.net/daily
- **On other accounts:** 10 real comments a day on recent posts in chart reading, trading education, finance memes
  and student money. Say something specific about their post; never the link, never "check out my page".
- **Never:** automated comments or follows, engagement pods, buying anything (see the plan's Spending section).
