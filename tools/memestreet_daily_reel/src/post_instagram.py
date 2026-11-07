"""Publish out/<date>/reel.mp4 as an Instagram Reel (official Instagram API).

Ways to connect (set IG_LOGIN in config.env):
  unified (recommended)   - "API setup with Unified login": no Facebook Page, token usually never expires,
                            video uploaded straight to Meta (no public hosting needed).
  instagram               - "Instagram API with Instagram Login": no Facebook Page needed.
                            Instagram fetches the video from a public URL on your site
                            (PUBLIC_VIDEO_DIR + PUBLIC_VIDEO_URL). The token is refreshed automatically.
  facebook                - "Instagram API with Facebook Login": needs a linked Facebook Page,
                            uploads the video straight to Meta (no hosting needed).
Usage:
  python3 src/post_instagram.py out/<date>             publish
  python3 src/post_instagram.py out/<date> --dry-run   show what would be posted
  python3 src/post_instagram.py --check                test the connection, post nothing
"""
import glob, json, os, shutil, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODE = os.environ.get("IG_LOGIN", "unified").strip().lower()
V = os.environ.get("GRAPH_VERSION", "v26.0")
HOST = "https://graph.instagram.com" if MODE == "instagram" else "https://graph.facebook.com"
STATE = os.path.join(ROOT, "state"); TOKFILE = os.path.join(STATE, "ig_token.json")

def http(method, url, params=None, data=None, headers=None):
    if params: url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=300).read() or b"{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {url.split('?')[0]} -> HTTP {e.code}: {e.read()[:600].decode(errors='ignore')}")

def token():
    """Current token: the auto-refreshed one in state/ if present, else the one in config.env."""
    if os.path.exists(TOKFILE):
        return json.load(open(TOKFILE))["access_token"]
    t = os.environ.get("IG_ACCESS_TOKEN", "")
    if not t: raise SystemExit("IG_ACCESS_TOKEN missing in config.env")
    return t

def refresh_token():
    """Instagram-Login tokens last 60 days; refreshing daily keeps them alive indefinitely."""
    if MODE != "instagram": return
    try:
        r = http("GET", "https://graph.instagram.com/refresh_access_token", {"grant_type": "ig_refresh_token", "access_token": token()})
        os.makedirs(STATE, exist_ok=True)
        json.dump({"access_token": r["access_token"], "expires_in": r.get("expires_in"), "refreshed": time.strftime("%F %T UTC", time.gmtime())}, open(TOKFILE, "w"))
        os.chmod(TOKFILE, 0o600)
    except SystemExit as e:
        print("token refresh skipped:", str(e)[:200])     # tokens under 24h old can't be refreshed yet; that's fine

def ig_id(tok):
    if os.environ.get("IG_USER_ID"): return os.environ["IG_USER_ID"]
    if MODE == "unified":                      # system-user token: the Instagram account is an assigned asset
        r = http("GET", f"{HOST}/{V}/me/assigned_instagram_accounts", {"fields": "id,username", "access_token": tok})
        if not r.get("data"): raise SystemExit("token has no Instagram account assigned (re-check Generate access tokens)")
        return r["data"][0]["id"]
    if MODE == "facebook":                     # the Instagram account linked to your Facebook Page
        me = http("GET", f"{HOST}/{V}/me", {"fields": "instagram_business_account", "access_token": tok})
        if me.get("instagram_business_account"): return me["instagram_business_account"]["id"]      # Page token
        pages = http("GET", f"{HOST}/{V}/me/accounts", {"fields": "name,instagram_business_account", "access_token": tok}).get("data", [])
        for pg in pages:                                                                              # User token
            if pg.get("instagram_business_account"): return pg["instagram_business_account"]["id"]
        raise SystemExit("no Instagram account linked to your Facebook Page (link it in the Page's settings)")
    me = http("GET", f"{HOST}/{V}/me", {"fields": "user_id,username", "access_token": tok})
    return me.get("user_id") or me.get("id")

def check():
    refresh_token(); tok = token(); uid = ig_id(tok)
    fields = "username,account_type" if MODE == "instagram" else "username"
    me = http("GET", f"{HOST}/{V}/{uid}", {"fields": fields, "access_token": tok})
    lim = http("GET", f"{HOST}/{V}/{uid}/content_publishing_limit", {"fields": "quota_usage,config", "access_token": tok})
    print(f"connected ({MODE} login) as @{me.get('username')} (id {uid}); publishing limit: {json.dumps(lim.get('data', lim))}")
    if MODE == "unified":
        try:
            dbg = http("GET", f"{HOST}/{V}/debug_token", {"input_token": tok, "access_token": tok}).get("data", {})
            exp = dbg.get("expires_at", 0)
            print("token expires:", "never" if not exp else time.strftime("%Y-%m-%d", time.gmtime(exp)))
        except SystemExit: pass
    if MODE == "instagram" and not (os.environ.get("PUBLIC_VIDEO_DIR") and os.environ.get("PUBLIC_VIDEO_URL")):  # only instagram mode needs hosting
        print("WARNING: PUBLIC_VIDEO_DIR / PUBLIC_VIDEO_URL are not set; instagram mode needs them")

def main(folder, dry=False):
    mp4, cap, flag = (os.path.join(folder, f) for f in ("reel.mp4", "caption.txt", "posted.json"))
    if os.path.exists(flag): print("already posted:", open(flag).read()); return
    if not os.path.exists(mp4): raise SystemExit(f"no reel at {mp4} (did the 23:30 job run?)")
    caption = open(cap).read() if os.path.exists(cap) else ""
    if dry:
        print(f"[dry run] {MODE} login - would post {mp4} ({os.path.getsize(mp4)//1024} KB) with caption:\n{caption}"); return
    refresh_token(); tok = token(); uid = ig_id(tok)
    base = {"media_type": "REELS", "caption": caption, "share_to_feed": "true", "access_token": tok}
    trial = json.load(open(os.path.join(folder, "trial.json"))) if os.path.exists(os.path.join(folder, "trial.json")) else None
    if trial:                                              # a Trial Reel: non-followers only, off the grid; Instagram shares it with
        base["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"}); base.pop("share_to_feed")   # followers if it performs
    pub_dir, pub_url = os.environ.get("PUBLIC_VIDEO_DIR"), os.environ.get("PUBLIC_VIDEO_URL")
    if MODE == "instagram" or (pub_dir and pub_url):
        if not (pub_dir and pub_url): raise SystemExit("set PUBLIC_VIDEO_DIR and PUBLIC_VIDEO_URL in config.env (see README)")
        os.makedirs(pub_dir, exist_ok=True)
        for old in glob.glob(os.path.join(pub_dir, "daily-*")):           # tidy: keep 3 days of public files
            if time.time() - os.path.getmtime(old) > 3 * 86400: os.remove(old)
        name = f"daily-{os.path.basename(os.path.normpath(folder))}-{int(time.time())}.mp4"   # (a new address each post: Cloudflare caches the old one)
        shutil.copy(mp4, os.path.join(pub_dir, name)); os.chmod(os.path.join(pub_dir, name), 0o644)
        cover = os.path.join(folder, "cover.jpg")                             # the day's cover photo (render.py)
        if os.path.exists(cover):
            shutil.copy(cover, os.path.join(pub_dir, name[:-4] + ".jpg")); os.chmod(os.path.join(pub_dir, name[:-4] + ".jpg"), 0o644)
            base["cover_url"] = pub_url.rstrip("/") + "/" + name[:-4] + ".jpg"
        c = http("POST", f"{HOST}/{V}/{uid}/media", {**base, "video_url": pub_url.rstrip("/") + "/" + name})
    else:
        c = http("POST", f"{HOST}/{V}/{uid}/media", {**base, "upload_type": "resumable"})
        up = http("POST", c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{V}/{c['id']}", data=open(mp4, "rb").read(),
                  headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(os.path.getsize(mp4))})
        if not up.get("success", True): raise SystemExit(f"upload failed: {up}")
    cid = c["id"]; print("container", cid, "- waiting for Instagram to process the video...")
    for _ in range(90):
        st = http("GET", f"{HOST}/{V}/{cid}", {"fields": "status_code,status", "access_token": tok})
        if st.get("status_code") == "FINISHED": break
        if st.get("status_code") in ("ERROR", "EXPIRED"): raise SystemExit(f"Instagram could not process the video: {st}")
        time.sleep(10)
    else:
        raise SystemExit("timed out waiting for Instagram to process the video")
    r = http("POST", f"{HOST}/{V}/{uid}/media_publish", {"creation_id": cid, "access_token": tok})
    json.dump({"media_id": r.get("id"), "posted_at": time.strftime("%F %T UTC", time.gmtime()), **({"trial": trial} if trial else {})}, open(flag, "w"))
    print("published reel, media id", r.get("id"))

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--check" in sys.argv: check()
    elif args: main(args[0], "--dry-run" in sys.argv)
    else: raise SystemExit(__doc__)
