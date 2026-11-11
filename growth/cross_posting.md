# The same reels on other platforms: what you set up

For the reach plan, A11 and the daily text post (`docs/REACH_PLAN.md`). The script is
`tools/memestreet_daily_reel/src/post_elsewhere.py`. It does nothing for a platform until that platform's keys are in
`config.env` on the reel server, so **putting a platform's keys in is your yes for that platform**: the next reel
Instagram takes goes there too. Everything below is free. Sign-up pages change; where a step no longer matches,
look for the thing named in bold.

| Platform | Gets | Keys in `config.env` | Link tag on the admin page |
|---|---|---|---|
| YouTube Shorts | up to 3 reels a day | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | `yt` |
| Facebook Page | up to 3 reels a day | `FB_PAGE_ID`, `FB_PAGE_TOKEN` | `fb` |
| Threads | up to 3 reels a day, and the text post | `THREADS_TOKEN` | `threads` |
| Telegram channel | up to 3 reels a day, and the text post | `TG_BOT_TOKEN`, `TG_CHAT` | `tg` |
| Bluesky | the text post | `BSKY_HANDLE`, `BSKY_APP_PASSWORD` | `bsky` |
| Mastodon | the text post | `MASTO_HOST`, `MASTO_TOKEN` | `masto` |

The text post goes out once a day from 12:00 UTC: "Daily Chart #9 fell 38%. Chart #10 is open now: one made-up
stock, two minutes, the same chart for everyone. Can you beat just holding it? Practice money, no cash value." and
the link. Only reels on Instagram's grid are sent, never a Trial Reel.

Optional lines: `ELSEWHERE_PER_DAY=3` (reels a day per platform; the day's first ones are taken), `TEXT_HOUR=12`,
`YT_PRIVACY=public`.

## After adding keys

You add the lines to `/opt/memestreet-daily-reel/config.env` yourself; I never open that file. Then, on the server:

```
cd /opt/memestreet-daily-reel && set -a; . ./config.env; set +a
python3 src/post_elsewhere.py --check                      # which platforms are on; sends nothing
python3 src/post_elsewhere.py queue/2026-11-11T0300        # send one reel now (a slot posted in the last 3 days)
TEXT_HOUR=0 python3 src/post_elsewhere.py --daily          # send today's text post now
tail logs/elsewhere.log
```

Each reel folder gets a `posted_elsewhere.json` with the post's id or the error per platform. A platform named in
it is not tried again for that reel; delete its entry to retry.

## YouTube (first)

1. Make the channel (a Brand Account named Meme Street is best) and put `https://memestreet.net/daily?ref=yt` in
   the channel's **links**. Links in a Short's description cannot be tapped; channel links can.
2. In Google Cloud Console make a project, enable **YouTube Data API v3**, and set up the **OAuth consent screen**
   as External. Then press **Publish app** so it is "In production". In "Testing" the token dies after 7 days.
3. Under Credentials make an **OAuth client ID** of type **Desktop app**. Copy its client ID and secret.
4. On your own computer, in `D:\stock_market_sim\tools\memestreet_daily_reel`:
   `..\..\.venv\Scripts\python.exe src\post_elsewhere.py yt-login`. Paste the two values, pick the channel in the
   browser, and allow it. Google shows an "unverified app" warning for your own app; choose Advanced, then continue.
5. The script prints three lines. Add them to `config.env` on the server.
6. Uploads are **unlisted** until you add `YT_PRIVACY=public`. Watch the first one in YouTube Studio. If Studio
   shows it locked as private, Google has not yet audited the API project. The free form is **YouTube API Services:
   Audit and Quota Extension**. Until it is approved, uploads through the script stay private.

## Facebook Page

The Instagram account is already linked to a Page (the server uses the Facebook login). You need a Page token that
may publish:

1. In **Graph API Explorer** pick the Meme Street app, add `pages_show_list`, `pages_read_engagement` and
   `pages_manage_posts`, and generate a user token.
2. Make it long-lived in the **Access Token Debugger** (Extend Access Token).
3. With the long-lived token, open `me/accounts` in the Explorer. The Page's `id` is `FB_PAGE_ID` and its
   `access_token` is `FB_PAGE_TOKEN`. A Page token made this way does not expire.

A Page Reel is 90 seconds at most.

## Threads

1. Open a Threads profile from the Instagram account.
2. In the Meta app dashboard add the use case **Access the Threads API** with `threads_basic` and
   `threads_content_publish`, and add the Threads account as a **Threads tester**. Accept the invite in the Threads
   app under Settings, Account, Website permissions.
3. In the use case's settings, the **User Token Generator** gives a token for the tester. That is `THREADS_TOKEN`.
   The script renews it every week; a token left unused for 60 days dies.

## Telegram

1. Make a public channel, for example `@memestreet_daily`.
2. Message **@BotFather**, send `/newbot`, and copy the token it gives: `TG_BOT_TOKEN`.
3. Add the bot to the channel as an admin with only **Post messages**. `TG_CHAT=@memestreet_daily`.

## Bluesky

Make the account, then Settings, Privacy and security, **App passwords**, add one. `BSKY_HANDLE=memestreet.bsky.social`
(your handle), `BSKY_APP_PASSWORD=` the app password. Never the account's main password.

## Mastodon

Pick a server that allows brand accounts, for example mastodon.social, and tick **This is an automated account**
in the profile settings. Under Preferences, **Development**, make a new application with only `write:statuses`,
and copy **Your access token**. `MASTO_HOST=mastodon.social`, `MASTO_TOKEN=` that token.

## Not tested against the real platforms

No account or key existed when this was built (2026-11-11). The self-check (`python3 src/post_elsewhere.py demo`)
proves the flow, the once-only rule, the daily limit and that keys never reach a log, with the network faked. The
first real post on each platform is the test of that platform's own rules, so look at each first post.
