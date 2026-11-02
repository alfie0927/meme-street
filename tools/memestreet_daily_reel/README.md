# Meme Street · Daily Chart recap reel (automatic)

Every night at **23:30 UTC** this makes a recap reel of that day's Daily Chart, and at **00:00 UTC** (as the new chart goes live) posts it to Instagram.

It finds where support/resistance held, broke or faked out, works out the best trades someone could realistically have taken (entries/exits only at candle closes, after the signal), narrates it in the Meme Street voice (Kokoro *af_heart*) and renders a 60 fps, 1080×1920 reel. House rules are built in: no fees, no stop-loss placement ("watch for a fake breakout" instead), ends with memestreet.net/daily.

---

## 1. Put it in your repo

Create this folder in the **root of your Meme Street repo** and paste everything from the zip's `memestreet_daily_reel/` folder into it:

```
your-memestreet-repo/
├── ... your existing app (unchanged)
└── tools/
    └── daily-reel/
        ├── .gitignore            keeps secrets + generated files out of git
        ├── README.md             this file
        ├── config.example.env    template for your settings
        ├── setup.sh              one-time server install
        ├── make_reel.sh          23:30 job
        ├── post_reel.sh          00:00 job
        ├── assets/logo.png
        ├── src/                  analyze.py, fetch.py, voice.py, render.py, recap.html, post_instagram.py
        └── systemd/              the two UTC timers
```

Then commit it (from the repo root):

```bash
git add tools/daily-reel
git commit -m "Add Daily Chart recap reel bot"
git push
```

Never commit `config.env`. The included `.gitignore` already excludes it, along with `state/` (the refreshed Instagram token), `models/`, `data/`, `work/`, `out/` and `logs/`.

## 2. Install on the server (once)

On the server that runs memestreet.net (Ubuntu/Debian):

```bash
cd /path/to/your-memestreet-repo && git pull
cd tools/daily-reel
sudo ./setup.sh
```

This installs ffmpeg, Python packages, headless Chromium, the chart font and the voice model (~350 MB), creates `config.env`, and installs the two timers (switched off until step 6).

> If your deploy process deletes and re-creates the repo folder, `config.env`, `state/` and `models/` would be wiped. In that case keep this folder outside the deploy directory (for example `/opt/memestreet-daily-reel`), and update it with `git pull` from there.

No Meme Street account is needed. The bot reads each day's chart by playing it as a **guest visitor** (it never trades), and guests don't appear on the leaderboard.

## 3. Let Instagram fetch the video from your site

Instagram Login posting works by giving Instagram a public link to the video. The bot copies each night's reel into a folder your website serves (keeping 3 days).

```bash
sudo mkdir -p /var/www/memestreet-reels
sudo chown $USER /var/www/memestreet-reels
```

**If memestreet.net runs behind nginx**, add this inside its `server { ... }` block, then `sudo nginx -t && sudo systemctl reload nginx`:

```nginx
location /reels/ {
    alias /var/www/memestreet-reels/;
    types { video/mp4 mp4; }
}
```

**Other setups:** any folder that ends up public works. Put its path in `PUBLIC_VIDEO_DIR` and its URL in `PUBLIC_VIDEO_URL`. Check it by copying a test file in and opening `https://memestreet.net/reels/<file>` in a browser.

## 4. Connect Instagram (once, about 10 minutes)

1. **Make the Instagram account professional.** Instagram app → Settings → *Account type and tools* → switch to **Business** or **Creator**.
2. **Create a Meta app.** Go to **developers.facebook.com** → *My Apps* → **Create app**. Pick the Instagram use case (the one for managing content on Instagram; app type *Business*).
3. **Add Instagram with Instagram Login.** In the app dashboard: *Instagram* → **API setup with Instagram login**.
4. **Permissions.** Make sure **instagram_business_basic** and **instagram_business_content_publish** are listed.
5. **Generate the token.** Under *Generate access tokens* click **Add account**, log in to the Meme Street Instagram account, approve (keep "content publishing" ticked), then **Generate token** and copy it.
6. **Paste it** into `config.env`:
   ```
   IG_LOGIN=instagram
   IG_ACCESS_TOKEN=IGAA...
   ```
7. **Test:** `./post_reel.sh --check` should print `connected (instagram login) as @your_account`.

Because you're posting to your own account (which has a role on your app), the app can stay in Development mode. No App Review is needed. The token normally lasts 60 days, but the bot refreshes it every night (saved in `state/ig_token.json`), so it keeps working as long as it runs.

**Alternative (Facebook Login):** if the Instagram account is linked to a Facebook Page, set `IG_LOGIN=facebook` and use a Page-connected token with `instagram_basic`, `instagram_content_publish`, `pages_show_list` and `pages_read_engagement`. A Meta Business Suite *System user* token never expires. This mode uploads the video directly, so section 3 isn't needed.

## 5. Test the whole thing

```bash
./make_reel.sh                                   # makes today's reel (~10-20 min incl. the 2-min game)
ls out/$(date -u +%F)/                           # reel.mp4 + caption.txt: watch it
DATE=$(date -u +%F) ./post_reel.sh --dry-run     # shows what would be posted
DATE=$(date -u +%F) ./post_reel.sh               # optional: really post this one now
```

## 6. Go live

```bash
sudo systemctl enable --now memestreet-reel-make.timer memestreet-reel-post.timer
systemctl list-timers | grep memestreet          # next run times (23:30 and 00:00 UTC)
```

## Day to day

- **Logs:** `logs/<date>.log`, or `journalctl -u memestreet-reel-make -u memestreet-reel-post`.
- **No double posts:** a reel is never posted twice (`out/<date>/posted.json`). If the 23:30 job fails, nothing is posted.
- **Re-make a day:** `./make_reel.sh 2026-11-02` (reuses saved data).
- **Pause posting:** `sudo systemctl disable --now memestreet-reel-post.timer` (reels are still made).
- **Slow server:** if rendering gets close to midnight, set `FPS=30` in `config.env` (twice as fast).
- **Instagram limit:** 50 posts per 24 h. One a day is nowhere near it.

For the first week, watch each reel when it appears (around 23:45 UTC). The script is generated automatically. It's reliable, but check it before trusting it fully.
