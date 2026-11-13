"""The same reel on other platforms, and one text post a day with a link (docs/ROADMAP.md A11 and the RC track; the owner, 2026-11-11).

  python3 src/post_elsewhere.py <folder>    the reel in <folder>, once Instagram took it (queue_post.sh, make_reel.sh)
  python3 src/post_elsewhere.py --daily     the day's text post, once a day from TEXT_HOUR (queue_post.sh)
  python3 src/post_elsewhere.py --check     which platforms are on (no network)
  python3 src/post_elsewhere.py yt-login    once, on your own computer: the YouTube refresh token for config.env
  python3 src/post_elsewhere.py demo        the self-check, no network

A platform is on only when all its keys are in config.env (KEYS below); with none set this script does nothing.
Reels go to YouTube Shorts (at most YT_PER_DAY, 6: the API's free upload quota), a Facebook Page, Threads and a Telegram
channel (at most ELSEWHERE_PER_DAY, 3, each), counted over YouTube's quota day (midnight to midnight Pacific time). One
of each day's uploads is always kept for the Daily (the owner, 2026-11-13): other reels stop one short of the cap;
the text post goes to Threads, Telegram, Bluesky and Mastodon. <folder>/posted_elsewhere.json says what went where, and
a platform named in it is never tried again for that reel (an entry is written before the upload starts, so a crash
cannot post twice; delete an entry to retry it). YouTube uploads are unlisted until YT_PRIVACY=public is set.
urllib only, like post_instagram.py. Every error text has the keys taken out before it is printed or saved.
"""
import datetime, glob, json, hashlib, os, re, secrets, sys, textwrap, time, urllib.parse, urllib.request, urllib.error
from post_instagram import http, V, ROOT, STATE

KEYS = {"youtube": ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"), "facebook": ("FB_PAGE_ID", "FB_PAGE_TOKEN"),
        "threads": ("THREADS_TOKEN",), "telegram": ("TG_BOT_TOKEN", "TG_CHAT"), "bluesky": ("BSKY_HANDLE", "BSKY_APP_PASSWORD"),
        "mastodon": ("MASTO_HOST", "MASTO_TOKEN")}
REF = {"youtube": "yt", "facebook": "fb", "threads": "threads", "telegram": "tg", "bluesky": "bsky", "mastodon": "masto"}   # (each link's own ref tag: the admin page counts sign-ups by it)
LINK = "https://memestreet.net/daily?ref="
SF = os.path.join(STATE, "elsewhere.json")              # {"day", "n": reels sent today per platform, "text_day", "text"}
E = os.environ.get
UA = {"User-Agent": "memestreet-reels/1.0 (+https://memestreet.net)"}
on = lambda p: all(E(k, "").strip() for k in KEYS[p])
stamp = lambda: time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
form = lambda d: urllib.parse.urlencode(d).encode()


def clean(text):
    """An error text with every key's value taken out (Telegram's token is part of its address)."""
    for k in sum(KEYS.values(), ()):
        if len(E(k, "")) > 5: text = text.replace(E(k), "***")
    return text[:300]


def attempt(fn):
    try: return {"id": fn(), "at": stamp()}
    except (Exception, SystemExit) as e: return {"error": clean(f"{type(e).__name__}: {e}"), "at": stamp()}


def state():
    try: st = json.load(open(SF))
    except (OSError, ValueError): st = {}
    if st.get("day") != stamp()[:10]: st.update(day=stamp()[:10])          # (the text post's day: UTC)
    if st.get("qday") != quota_day(): st.update(qday=quota_day(), n={})   # (the reels' count: YouTube's quota day)
    return st


def quota_day():
    """The day YouTube's upload quota counts in: midnight to midnight Pacific time."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    except Exception:
        return time.strftime("%Y-%m-%d", time.gmtime(time.time() - 8 * 3600))


def per_day(p):
    return int(E("YT_PER_DAY", "6") if p == "youtube" else E("ELSEWHERE_PER_DAY", "3"))


def save(st):
    os.makedirs(os.path.dirname(SF), exist_ok=True); json.dump(st, open(SF, "w"), indent=1)


def public(folder):
    """The address of the copy post_instagram.py put on the site for this reel (kept 3 days), or None."""
    d, u = E("PUBLIC_VIDEO_DIR"), E("PUBLIC_VIDEO_URL")
    f = sorted(glob.glob(os.path.join(d, f"daily-{os.path.basename(folder)}-*.mp4"))) if d and u else []
    return u.rstrip("/") + "/" + os.path.basename(f[-1]) if f else None


def must(url):
    if not url: raise SystemExit("no public copy of the video on the site (PUBLIC_VIDEO_DIR keeps 3 days)")
    return url


def head(method, url, data, headers):
    """Like http(), for a call whose answer is in the response headers (YouTube's upload address)."""
    try: return urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=300).headers
    except urllib.error.HTTPError as e: raise SystemExit(f"{method} {url.split('?')[0]} -> HTTP {e.code}: {e.read()[:600].decode(errors='ignore')}")


def youtube(mp4, cap):
    """A vertical video of 3 minutes or less is a Short. A refresh token of an OAuth app still in "Testing" dies after 7 days."""
    tok = http("POST", "https://oauth2.googleapis.com/token", data=form({"client_id": E("YT_CLIENT_ID"), "client_secret": E("YT_CLIENT_SECRET"),
               "refresh_token": E("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}))["access_token"]
    title = textwrap.shorten(re.sub(r"[<>]", "", cap.split("\n")[0]), 100, placeholder="...") or "Meme Street"
    meta = {"snippet": {"title": title, "description": cap + "\n\nPlay today's chart free: memestreet.net/yt", "categoryId": "27"},   # (27: Education)
            "status": {"privacyStatus": E("YT_PRIVACY", "unlisted"), "selfDeclaredMadeForKids": False}}
    A = {"Authorization": "Bearer " + tok}
    up = head("POST", "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", json.dumps(meta).encode(),
              {**A, "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(os.path.getsize(mp4))})["Location"]
    return http("PUT", up, data=open(mp4, "rb").read(), headers={**A, "Content-Type": "video/mp4"})["id"]


def facebook(url, text):
    """A Page Reel (90 s at most), fetched by Meta from the site. The Page token needs pages_manage_posts."""
    pg, tok, G = E("FB_PAGE_ID"), E("FB_PAGE_TOKEN"), "https://graph.facebook.com/" + V
    vid = http("POST", f"{G}/{pg}/video_reels", {"upload_phase": "start", "access_token": tok})["video_id"]
    http("POST", f"https://rupload.facebook.com/video-upload/{V}/{vid}", data=b"", headers={"Authorization": "OAuth " + tok, "file_url": url})
    http("POST", f"{G}/{pg}/video_reels", {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": text, "access_token": tok})
    return vid


def th_token():
    """The Threads token lasts 60 days; a weekly refresh keeps it alive (the pattern of refresh_token() in post_instagram.py)."""
    f, t = os.path.join(STATE, "threads_token.json"), E("THREADS_TOKEN"); seed = hashlib.sha256(t.encode()).hexdigest()[:12]
    try: old = json.load(open(f))
    except (OSError, ValueError): old = {}
    if old.get("seed") == seed: t = old["access_token"]   # (a new token in config.env wins over the saved one)
    if old.get("seed") != seed or time.time() - os.path.getmtime(f) > 7 * 86400:
        try:
            t = http("GET", "https://graph.threads.net/refresh_access_token", {"grant_type": "th_refresh_token", "access_token": t})["access_token"]
            os.makedirs(STATE, exist_ok=True); json.dump({"seed": seed, "access_token": t}, open(f, "w")); os.chmod(f, 0o600)
        except (SystemExit, KeyError): pass                # (a token under a day old cannot be refreshed yet)
    return t


def threads(text, url=None):
    """A video post (Meta fetches it from the site) or, with no url, a text post."""
    tok, G = th_token(), "https://graph.threads.net/v1.0/"
    c = http("POST", G + "me/threads", {**({"media_type": "VIDEO", "video_url": url} if url else {"media_type": "TEXT"}), "text": text[:500], "access_token": tok})["id"]
    for _ in range(30 if url else 0):                      # (a video is processed first)
        st = http("GET", G + c, {"fields": "status", "access_token": tok}).get("status")
        if st == "FINISHED": break
        if st in ("ERROR", "EXPIRED"): raise SystemExit(f"Threads could not process the video: {st}")
        time.sleep(10)
    return http("POST", G + "me/threads_publish", {"creation_id": c, "access_token": tok})["id"]


def telegram(text, url=None):
    """To a channel the bot is an admin of. Telegram fetches a video by address up to 20 MB (the reels are under 12)."""
    r = http("POST", f"https://api.telegram.org/bot{E('TG_BOT_TOKEN')}/" + ("sendVideo" if url else "sendMessage"),
             {"chat_id": E("TG_CHAT"), **({"video": url, "caption": text[:1024]} if url else {"text": text})})
    return r["result"]["message_id"]


def facets(text):
    """Bluesky does not find links itself: each one is marked by its byte range."""
    return [{"index": {"byteStart": len(text[:m.start()].encode()), "byteEnd": len(text[:m.end()].encode())},
             "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group()}]} for m in re.finditer(r"https://\S+", text)]


def bluesky(text):
    # ponytail: text posts only. A video needs Bluesky's upload-job service; add it when this account shows life.
    B, J = "https://bsky.social/xrpc/", {**UA, "Content-Type": "application/json"}
    s = http("POST", B + "com.atproto.server.createSession", data=json.dumps({"identifier": E("BSKY_HANDLE"), "password": E("BSKY_APP_PASSWORD")}).encode(), headers=J)
    rec = {"$type": "app.bsky.feed.post", "text": text[:300], "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "facets": facets(text[:300])}
    return http("POST", B + "com.atproto.repo.createRecord", data=json.dumps({"repo": s["did"], "collection": "app.bsky.feed.post", "record": rec}).encode(),
                headers={**J, "Authorization": "Bearer " + s["accessJwt"]})["uri"]


def mastodon(text):
    return http("POST", f"https://{E('MASTO_HOST')}/api/v1/statuses", data=form({"status": text[:500]}), headers={**UA, "Authorization": "Bearer " + E("MASTO_TOKEN")})["id"]


TEXT = {"threads": threads, "telegram": telegram, "bluesky": bluesky, "mastodon": mastodon}


def daily_text(p, d):
    """Yesterday's Daily Chart in one line and today's link, from the data make_reel.sh saved (no result of today's is given away)."""
    g = d["game"]; C = g["candles"]; h = g.get("hold", C[-1][3] / C[g.get("history", 60)][3] - 1); n = d["number"]   # (the hold of analyze.py)
    did = "ended flat" if abs(h) < .005 else f"{'rose' if h > 0 else 'fell'} {abs(h) * 100:.0f}%"
    return (f"Daily Chart #{n} {did}. Chart #{n + 1} is open now: one made-up stock, two minutes, the same chart for everyone. "
            f"Can you beat just holding it? Practice money, no cash value.\n{LINK}{REF[p]}")


def daily():
    st = state(); today = st["day"]
    if st.get("text_day") == today or time.gmtime().tm_hour < int(E("TEXT_HOUR", "12")) or not any(on(p) for p in TEXT): return
    f = os.path.join(ROOT, "data", time.strftime("%Y-%m-%d", time.gmtime(time.time() - 86400)) + ".json")
    if not os.path.exists(f): return                       # (no Daily data for yesterday: no post today)
    st["text_day"] = today; save(st)                       # (marked first: a crash never posts it twice)
    d = json.load(open(f, encoding="utf-8")); text = {p: attempt(lambda: fn(daily_text(p, d))) for p, fn in TEXT.items() if on(p)}
    st = state(); st["text"] = text; save(st); print("the daily text post", stamp(), json.dumps(st["text"]))


def main(folder):
    n = os.path.normpath(folder); mp4, flag, capf = (os.path.join(n, x) for x in ("reel.mp4", "posted_elsewhere.json", "caption.txt"))
    if not os.path.exists(os.path.join(n, "posted.json")) or os.path.exists(os.path.join(n, "trial.json")): return print("not a reel on Instagram's grid: nothing sent")
    done = json.load(open(flag)) if os.path.exists(flag) else {}; url = public(n)
    cap = open(capf, encoding="utf-8").read().strip() if os.path.exists(capf) else ""; line = cap.split("\n")[0]
    send = {"youtube": lambda: youtube(mp4, cap), "facebook": lambda: facebook(must(url), cap + "\n\n" + LINK + REF["facebook"]),
            "threads": lambda: threads(line + "\n" + LINK + REF["threads"], must(url)), "telegram": lambda: telegram(line + "\n" + LINK + REF["telegram"], must(url))}
    daily = os.path.basename(os.path.dirname(n)) == "out" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", os.path.basename(n))   # (make_reel.sh posts the Daily from out/<date>)
    for p, fn in send.items():
        if not on(p) or p in done or state()["n"].get(p, 0) >= per_day(p) - (0 if daily else 1): continue   # (one upload a day stays free for the Daily)
        done[p] = {"started": stamp()}; json.dump(done, open(flag, "w"))   # (marked first: a crash mid-upload never posts twice)
        done[p] = attempt(fn); json.dump(done, open(flag, "w"))
        if "id" in done[p]: st = state(); st["n"][p] = st["n"].get(p, 0) + 1; save(st)   # (read again: the Daily's run may have written meanwhile)
        print(os.path.basename(n), p, json.dumps(done[p]))


def check():
    for p in KEYS: print(f"{p:9} {'on' if on(p) else 'off: needs ' + ', '.join(k for k in KEYS[p] if not E(k, '').strip())}")
    print(f"reels a day: YouTube {per_day('youtube')}, the others {per_day('facebook')} (one kept for the Daily); sent today {state()['n']}; YouTube privacy: {E('YT_PRIVACY', 'unlisted')}; text post from {E('TEXT_HOUR', '12')}:00 UTC")


def yt_login():
    """Once, on your own computer (it needs a browser): prints the three YouTube lines for the server's config.env."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import webbrowser
    cid = E("YT_CLIENT_ID") or input("Client ID: ").strip(); sec = E("YT_CLIENT_SECRET") or input("Client secret: ").strip(); got = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            got.update(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))
            self.send_response(200); self.end_headers(); self.wfile.write(b"Done. Go back to the terminal.")
        log_message = lambda *a: None

    srv = HTTPServer(("127.0.0.1", 0), H); back = f"http://127.0.0.1:{srv.server_port}"; st = secrets.token_urlsafe(16)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({"client_id": cid, "redirect_uri": back, "response_type": "code",
          "scope": "https://www.googleapis.com/auth/youtube.upload", "access_type": "offline", "prompt": "consent", "state": st})
    print("Opening Google's consent page. If no browser opens, paste this address into one:\n" + url); webbrowser.open(url)
    while not ({"code", "error"} & set(got)): srv.handle_request()
    if got.get("state") != st or "code" not in got: raise SystemExit(f"Google did not give a code: {got.get('error', 'the state value did not match')}")
    r = http("POST", "https://oauth2.googleapis.com/token", data=form({"code": got["code"], "client_id": cid, "client_secret": sec, "redirect_uri": back, "grant_type": "authorization_code"}))
    lines = f"YT_CLIENT_ID={cid}\nYT_CLIENT_SECRET={sec}\nYT_REFRESH_TOKEN={r['refresh_token']}\n"
    keep = os.path.join(os.path.expanduser("~"), "yt_keys.env")      # (outside the repo; appended to the server's config.env, then deleted)
    with open(keep, "w", encoding="utf-8", newline="\n") as f: f.write(lines)
    print(f"\nAdd these three lines to config.env on the server:\n{lines}\nThey are also saved in {keep}. To add them in one go (PowerShell):\n"
          f'  Get-Content "{keep}" | ssh root@65.109.233.145 "tr -d \'\\r\' >> /opt/memestreet-daily-reel/config.env"\nthen delete that file.')


def demo():
    import tempfile
    G, calls, T = globals(), [], tempfile.mkdtemp()
    ans = {"access_token": "tok", "id": "X1", "video_id": "V1", "status": "FINISHED", "result": {"message_id": 7}, "did": "did:x", "accessJwt": "j", "uri": "at://x"}
    G.update(http=lambda m, url, params=None, data=None, headers=None: (calls.append(url.split("?")[0]), ans)[1],
             head=lambda *a: {"Location": "https://upload.example/1"}, STATE=T, SF=os.path.join(T, "elsewhere.json"), ROOT=T)
    for k in sum(KEYS.values(), ()): os.environ.pop(k, None)
    pub = os.path.join(T, "pub"); os.makedirs(pub); os.environ.update(PUBLIC_VIDEO_DIR=pub, PUBLIC_VIDEO_URL="https://x.test/v/", TEXT_HOUR="0", ELSEWHERE_PER_DAY="2", YT_PER_DAY="2")

    def reel(name, where="queue", **extra):
        d = os.path.join(T, where, name); os.makedirs(d)
        for f, body in {"reel.mp4": "mp4", "caption.txt": "A stop is a plan.\n\n#trading", "posted.json": "{}", **extra}.items(): open(os.path.join(d, f), "w").write(body)
        for t in (1, 2): open(os.path.join(pub, f"daily-{name}-{t}.mp4"), "w").write("x")
        return d
    a = reel("2026-11-11T0300"); flag = os.path.join(a, "posted_elsewhere.json")
    assert public(a) == "https://x.test/v/daily-2026-11-11T0300-2.mp4"                    # the newest copy
    main(a); daily(); assert not calls and not os.path.exists(flag)                       # no keys: nothing leaves
    os.environ.update({k: "secret-" + k for k in sum(KEYS.values(), ())})
    main(a); done = json.load(open(flag)); n = len(calls)
    assert set(done) == {"youtube", "facebook", "threads", "telegram"} and all("id" in v for v in done.values()), done
    main(a); assert len(calls) == n                                                       # a second run sends nothing
    b = reel("2026-11-11T0600"); main(b); assert len(calls) == n and not os.path.exists(os.path.join(b, "posted_elsewhere.json"))   # the day's cap, less the Daily's
    dd = reel("2026-11-11", where="out"); main(dd); assert set(json.load(open(os.path.join(dd, "posted_elsewhere.json")))) == set(done)   # the Daily takes the kept one
    assert state()["n"] == {p: 2 for p in done} and per_day("youtube") == 2; os.environ.pop("YT_PER_DAY"); assert per_day("youtube") == 6 and per_day("threads") == 2
    os.environ["ELSEWHERE_PER_DAY"] = "5"; os.environ["YT_PER_DAY"] = "5"; n = len(calls)
    for bad in (reel("t", **{"trial.json": "{}"}), os.path.join(T, "none")): main(bad)
    assert len(calls) == n                                                                # a Trial Reel, or a reel Instagram did not take
    def boom(*a, **k): raise SystemExit("POST https://api.telegram.org/botsecret-TG_BOT_TOKEN/sendVideo -> HTTP 400")
    G["http"] = boom; main(b); err = json.load(open(os.path.join(b, "posted_elsewhere.json")))
    assert all("error" in v and "secret-" not in v["error"] for v in err.values()) and "bot***" in err["telegram"]["error"], err   # keys never reach a log
    G["http"] = lambda m, url, params=None, data=None, headers=None: (calls.append(url.split("?")[0]), ans)[1]
    C = [[1, 1, 1, 100.0]] * 61 + [[1, 1, 1, 112.0]]; d = {"number": 9, "game": {"candles": C, "history": 60}}
    txt = daily_text("bluesky", d); assert "Daily Chart #9 rose 12%" in txt and "Chart #10" in txt and txt.endswith("?ref=bsky") and len(txt) <= 300, txt
    assert "ended flat" in daily_text("threads", {"number": 1, "game": {"candles": C[:61], "history": 60}})
    f = facets("é " + LINK + "bsky")[0]["index"]; assert (f["byteStart"], f["byteEnd"]) == (3, 3 + len(LINK + "bsky")), f   # bytes, not characters
    os.makedirs(os.path.join(T, "data")); json.dump(d, open(os.path.join(T, "data", time.strftime("%Y-%m-%d", time.gmtime(time.time() - 86400)) + ".json"), "w"))
    n = len(calls); daily(); m = len(calls); assert m > n and set(state()["text"]) == set(TEXT); daily(); assert len(calls) == m   # once a day
    import shutil; shutil.rmtree(T, ignore_errors=True); print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: raise SystemExit(__doc__)
    {"demo": demo, "--check": check, "--daily": daily, "yt-login": yt_login}.get(a[0], lambda: main(a[0]))()
