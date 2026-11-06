"""Realistic video shots for the reels (Higgsfield API, pay as you go). One shot = a 9:16 still from the image model in
the house style, animated by the video model (5 or 10 s). Shots are cached by their description, so a critic round
remakes only a shot whose description changed, and a monthly cap stops all spending (the reel then goes without video).

  python3 src/footage.py demo                     self-check with a stubbed API (no spend)
  python3 src/footage.py try "<shot>" [seconds]    one real shot -> state/footage_try/<key>.mp4
Needs HF_API_KEY in config.env: the key exactly as console.higgsfield.ai shows it.
  python3 src/footage.py check                     is the key accepted? (a free status call, nothing generated)
"""
import datetime, hashlib, json, os, sys, tempfile, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.higgsfield.ai"
IMAGE = os.environ.get("HF_IMAGE_MODEL", "/higgsfield-ai/soul/standard")
VIDEO = os.environ.get("HF_VIDEO_MODEL", "/kling-video/v2.5-turbo/pro/image-to-video")
CAP = float(os.environ.get("HF_MONTHLY_CAP", "60"))                       # (US dollars a month)
PRICE = {"image": float(os.environ.get("HF_PRICE_IMAGE", "0.03")), "video_s": float(os.environ.get("HF_PRICE_VIDEO_S", "0.08"))}
SPEND = os.path.join(ROOT, "state", "footage_spend.json")
POLL, WAIT = 5, 420
STYLE = (", photoreal cinematic shot in the Meme Street look: dark moody low-key lighting at dusk or night, deep "
         "near-black shadows, cool teal highlights with warm amber accents, soft volumetric haze, 35mm lens, shallow depth "
         "of field, clean uncluttered composition, vertical frame, no text, no letters, no logos, no watermark, no real "
         "people")                                         # (the house look: near-black, teal and amber, like the charts)
MOTION = ", smooth natural motion, slow cinematic camera move, realistic physics"
NEG = "text, letters, captions, watermark, logo, warped hands, extra limbs, melted face, morphing, flicker, distorted, blurry, low quality"


def key():
    """The credential: HF_API_KEY as the console shows it (one string, usually 'id:secret'), or HF_API_KEY_ID and
    HF_API_KEY_SECRET; '' when there is none."""
    one = os.environ.get("HF_API_KEY", "").strip()
    if one: return one
    i, s = os.environ.get("HF_API_KEY_ID", "").strip(), os.environ.get("HF_API_KEY_SECRET", "").strip()
    return f"{i}:{s}" if i and s else ""


def http(method, url, body=None):
    req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": f"Key {key()}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def fetch(url, path):
    with urllib.request.urlopen(url, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())


def month():
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m")


def spent():
    return (json.load(open(SPEND)) if os.path.exists(SPEND) else {}).get(month(), 0.0)


def charge(x):
    S = json.load(open(SPEND)) if os.path.exists(SPEND) else {}
    S[month()] = round(S.get(month(), 0.0) + x, 4)
    os.makedirs(os.path.dirname(SPEND), exist_ok=True); json.dump(S, open(SPEND, "w"))


def cost(seconds):
    return PRICE["image"] + PRICE["video_s"] * seconds


def remaining():
    return CAP - spent()


def run(path, body):
    """Submit, then poll its status URL until it is done; returns the last status (completed, failed, nsfw...)."""
    r = http("POST", API + path, body)
    url, t = r.get("status_url") or f"{API}/requests/{r['request_id']}/status", time.time()
    while r.get("status") not in ("completed", "failed", "nsfw", "canceled"):
        if time.time() - t > WAIT:
            raise TimeoutError(f"{path} still {r.get('status')} after {WAIT}s")
        time.sleep(POLL); r = http("GET", url)
    return r


def shot(desc, seconds, out_dir):
    """The mp4 of one shot (5 s, or 10 s for a scene over 7 s), or None: no key, over the cap, or refused twice."""
    seconds = 10 if seconds > 7 else 5
    key = hashlib.sha1(json.dumps([desc, seconds, IMAGE, VIDEO, STYLE]).encode()).hexdigest()[:16]
    out = os.path.join(out_dir, key + ".mp4")
    if os.path.exists(out):
        return out
    if not key():
        print("footage: no Higgsfield key (config.env), no video"); return None
    if remaining() < cost(seconds):
        print(f"footage: the monthly cap (${CAP:.0f}) is reached, no video"); return None
    os.makedirs(out_dir, exist_ok=True)
    for d in (desc, desc + ", calm and family friendly"):          # (a refusal gets one gentler try; failed requests are free)
        try:
            im = run(IMAGE, {"prompt": d + STYLE, "aspect_ratio": "9:16", "resolution": "2K"})
            if im.get("status") != "completed":
                print(f"footage: still {im.get('status')}: {im.get('error') or ''}"); continue
            charge(PRICE["image"])
            v = run(VIDEO, {"prompt": d + MOTION, "image_url": im["images"][0]["url"], "duration": seconds, "negative_prompt": NEG})
            if v.get("status") != "completed":
                print(f"footage: video {v.get('status')}: {v.get('error') or ''}"); continue
            charge(PRICE["video_s"] * seconds)
            fetch(v["video"]["url"], out)
            return out
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as e:
            print(f"footage: {type(e).__name__}: {str(e)[:200]}")
    return None


def demo():
    global http, fetch, SPEND, POLL, CAP
    calls, real = [], (http, fetch, SPEND, POLL, CAP)
    def fake(method, url, body=None):
        calls.append((method, url))
        if method == "POST": return {"status": "queued", "request_id": "r1", "status_url": API + "/requests/r1/status"}
        img = any("soul" in u for _, u in calls[-2:])
        return {"status": "completed", "request_id": "r1", **({"images": [{"url": "https://x/i.png"}]} if img else {"video": {"url": "https://x/v.mp4"}})}
    d = tempfile.mkdtemp(); http, fetch, SPEND, POLL = fake, (lambda u, p: open(p, "wb").write(b"mp4")), os.path.join(d, "s.json"), 0
    os.environ.setdefault("HF_API_KEY", "id:secret")
    p = shot("a dragon over a ranch", 6, d)
    assert p and open(p, "rb").read() == b"mp4" and abs(spent() - cost(5)) < 1e-9, spent()
    n = len(calls); assert shot("a dragon over a ranch", 6, d) == p and len(calls) == n          # (cached: no call, no spend)
    assert shot("a dragon over a ranch", 9, d) != p and abs(spent() - cost(5) - cost(10)) < 1e-9  # (10 s is another shot)
    CAP = spent() + 0.01; assert shot("a foundry", 5, d) is None                                   # (over the cap: nothing sent)
    CAP = 99; http = lambda m, u, b=None: {"status": "failed", "request_id": "r", "error": "x"}
    s0 = spent(); assert shot("refused", 5, d) is None and spent() == s0                          # (failed: free, no clip)
    http, fetch, SPEND, POLL, CAP = real
    print("footage ok")


if __name__ == "__main__":
    if sys.argv[1] == "demo":
        demo()
    elif sys.argv[1] == "check":                         # a status call for a request that does not exist: 404 = key accepted
        try:
            http("GET", API + "/requests/00000000-0000-0000-0000-000000000000/status"); print("key accepted")
        except urllib.error.HTTPError as e:
            print({401: "key rejected (401): check HF_API_KEY", 403: "key rejected (403)"}.get(e.code, f"key accepted (HTTP {e.code} for a made-up request)"))
    elif sys.argv[1] == "try":
        p = shot(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 5, os.path.join(ROOT, "state", "footage_try"))
        print(p, f"spent this month ${spent():.2f} of ${CAP:.0f}")
