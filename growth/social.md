# Posting by hand on other platforms

For the owner, 11 Nov 2026. You post these yourself, from your own accounts. Instagram keeps its eight reels a day; this
adds the same videos elsewhere. Once a platform's keys are in the server's `config.env`, the server can post there for
you instead (`growth/cross_posting.md`). TikTok has no automatic route, so it stays by hand.

## 1. Get the videos

Do not save them from Instagram: a downloaded reel carries Instagram's marks, and TikTok and YouTube show such videos
to fewer people. Copy the clean files from the server instead:

```
powershell -ExecutionPolicy Bypass -File tools\fetch_reels.ps1
```

This puts the last 2 days of posted reels in `D:\memestreet_reels`, one folder each with `reel.mp4` and
`caption.txt`. Add `-Days 7` for a week. It only reads from the server.

**Which ones.** Not all eight. Post the two or three a day that did best on Instagram the day before. On Instagram so
far, stock stories (the made-up companies) and the trader levels reels kept viewers best; chart twists and technical
lessons kept them worst.

## 2. Set up each profile once

Use the same name everywhere: **Meme Street**, handle **memestreetgame** (as on Instagram), and
`brand/icon-512.png` as the picture.

Bio (78 characters, fits TikTok's 80):

```
Learn to trade on a made-up market. Practice money, no cash value. Play daily:
```

Link: `https://memestreet.net/daily`

## 3. Each platform

| Platform | What to post | How often | Notes |
|---|---|---|---|
| TikTok | The reel video | 2 or 3 a day | Caption: the first line of `caption.txt` plus 3 to 5 hashtags. Turn on "AI-generated content" in the post settings: the voice is synthetic, and Instagram's posts carry the same label. |
| YouTube Shorts | The reel video | 1 or 2 a day | Title: the first line of `caption.txt`, under 100 characters. Description: the rest of the caption. Answer "No" to "made for kids". |
| X | One text post a day about the Daily Chart | Daily | Posting in the app is free. Paying is only for posting through X's API. Example below. |
| Threads | The same text post as X, or a reel | Daily | Threads is linked to the Instagram account, so setup takes a minute. |
| Reddit | A plain post about the Daily Chart as a game | Once a week at most | Only in places that allow it, such as r/WebGames and r/playmygame. Never in stock or investing subreddits: they ban self-promotion, and an account gets banned fast. |

Daily text post for X and Threads (fill in the number and the result from that day's Daily reel caption):

```
Daily Chart #10: one made-up chart, two minutes, the same for everyone.
Today's best: +1.7%. Can you beat it?
memestreet.net/daily
```

## 4. Rules that apply everywhere

- Always "practice money, no cash value". Never say anyone can make money, never name a real stock.
- Never buy followers or use follow-for-follow apps. The fake followers on Instagram already hold its reels back.
- Answer comments in the first hour after a post: the platforms show a video to more people when it gets replies.
- Note where visitors come from: each platform's link can carry a tag such as `memestreet.net/daily?ref=tiktok`, and the
  admin page's visit log counts it.
