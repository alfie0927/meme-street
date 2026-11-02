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

## 3. (Only for IG_LOGIN=instagram) Let Instagram fetch the video from your site

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

## 4. Connect Instagram (once, about 15 minutes)

Uses Meta's **API setup with Unified login**: no Facebook Page needed, the video is uploaded straight to Meta, and the token usually never expires. (Section 3 is not needed in this mode.)

1. **Instagram account:** Instagram app → Settings → *Account type and tools* → switch to **Business** or **Creator**, and make sure it is public.
2. **Meta app:** developers.facebook.com/apps → your app (it must have the **Manage messaging & content on Instagram** use case and be owned by a business portfolio).
3. **Open the setup:** *Use cases* → *Manage messaging & content on Instagram* → **Customize** → **API setup with Unified login**.
4. **Configure your app:** **Create new configuration** (the default includes `instagram_content_publish`) → **Use this configuration** → under *Redirect URL* enter `https://memestreet.net/` → **Save**. You don't need the Login URL.
5. **Generate access tokens:** **Add account** → invite your Instagram account as an **Instagram Tester**. Accept it on instagram.com: *Settings → Website permissions → Apps and websites → Tester invites*. Back in the dashboard, **Generate token**, complete the login, and **copy the token: it's shown only once** (starts with `EAA`).
6. **Skip** "Configure webhooks", the login button and App Review. They're for apps other people log into.
7. In `config.env`:
   ```
   IG_LOGIN=unified
   IG_ACCESS_TOKEN=EAA...
   GRAPH_VERSION=v26.0
   ```
8. **Test:** `./post_reel.sh --check` should print `connected (unified login) as @your_account` and when the token expires (usually "never").

### If you can't create a business portfolio: Facebook login (no portfolio needed)

1. Create a free **Facebook Page** (facebook.com/pages/create), e.g. "Meme Street".
2. **Link Instagram to the Page:** in the Page's settings → *Linked accounts* → Instagram → connect your (Business/Creator) account.
3. In your Meta app: *Use cases* → *Customize* → **API setup with Facebook login** → **Add required content permissions**.
4. Open **developers.facebook.com/tools/explorer** (Graph API Explorer). Top right: pick your app, *User or Page* → **Get User Access Token**, tick `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management` → **Generate Access Token** and approve (choose your Page + Instagram account).
5. Make it permanent: open **developers.facebook.com/tools/debug/accesstoken**, paste the token → **Debug** → **Extend Access Token** → copy the new (60-day) token. Back in the Explorer, paste it in the token box and run `me/accounts?fields=name,access_token`. Copy your Page's `access_token`: a Page token made from an extended token **does not expire**.
6. In `config.env`: `IG_LOGIN=facebook` and `IG_ACCESS_TOKEN=` that Page token. The video uploads straight to Meta (no section 3).
7. Test: `./post_reel.sh --check`.

Other modes: `IG_LOGIN=instagram` (Instagram Login; needs section 3) or `IG_LOGIN=facebook` (needs a Facebook Page).

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
