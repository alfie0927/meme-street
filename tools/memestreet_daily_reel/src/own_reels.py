"""Our own best and worst openings, measured by Instagram, for the writer (docs/REACH_PLAN.md A10; the owner, 2026-11-11).

  python3 src/own_reels.py         -> state/own_reels.json   (auto_reel.sh runs it when that file is over a day old)
  python3 src/own_reels.py demo    the self-check, no network

The last 40 reels that are at least 24 hours old (a younger one is still being shown) and were shown at least 20 times.
Each one: its opening (the first spoken sentence, from the reel's own script while its work folder is still here, else
the caption's first line), its format, its hold (100 minus Instagram's skip rate: who is still there after 3 seconds)
and how much of its length was watched. make_spec.py brief() hands the five best and the five worst to the writer.
"""
import calendar, glob, json, os, re, sys, time
from post_instagram import http, token, ig_id, HOST, V, ROOT

OUT = os.path.join(ROOT, "state", "own_reels.json")
M = ["views", "reach", "shares", "ig_reels_avg_watch_time", "reels_skip_rate"]
LAST, OLD, SHOWN, EACH = 40, 86400, 20, 5
NOTE = ("Our own reels, measured by Instagram. hold = percent still watching after 3 seconds; watched = percent of the "
        "reel's length watched on average. The best openings kept people and the worst lost them: learn the shape of "
        "each (who or what is on screen, where the stake is, how soon), never reuse the words. One reel's hold is good "
        "to about 5 points at this size, so read the pattern across them, not one line.")
load = lambda p: json.load(open(p, encoding="utf-8"))
age = lambda p, now: now - calendar.timegm(time.strptime(p["timestamp"][:19], "%Y-%m-%dT%H:%M:%S"))


def insights(mid, tok):
    """Ask for every metric; one the API refuses is dropped and the rest asked again (the pattern of lab/insights.py)."""
    want = list(M)
    while want:
        try:
            r = http("GET", f"{HOST}/{V}/{mid}/insights", {"metric": ",".join(want), "access_token": tok})
            return {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value")) for d in r.get("data", [])}
        except SystemExit as e:
            bad = [m for m in want if m in str(e)]
            if not bad or len(bad) == len(want): return {}
            want = [m for m in want if m not in bad[:1]]
    return {}


def made():
    """media id -> (timeline, format) for the reels whose work folder is still on this machine."""
    out = {}
    for flag in glob.glob(os.path.join(ROOT, "queue", "*", "posted.json")) + glob.glob(os.path.join(ROOT, "out", "*", "posted.json")):
        d = os.path.dirname(flag); n = os.path.basename(d)
        w = os.path.join(ROOT, "work", n if os.path.basename(os.path.dirname(d)) == "out" else "auto-" + n)   # (the Daily posts from out/<date>)
        try: mid = str(load(flag)["media_id"]); tl = load(os.path.join(w, "timeline.json"))
        except (OSError, ValueError, KeyError): continue
        try: cat = load(os.path.join(w, "brief.json")).get("category")
        except (OSError, ValueError): cat = None
        out[mid] = (tl, cat)
    return out


def pick(posts, made, now):
    """posts newest first, each with its insights -> what the writer is shown."""
    rows = []
    for p in posts:
        i = p.get("insights") or {}; tl, cat = made.get(str(p["id"]), (None, None)); s0 = ((tl or {}).get("scenes") or [{}])[0]
        if p.get("media_product_type") != "REELS" or age(p, now) < OLD or (i.get("views") or 0) < SHOWN or i.get("reels_skip_rate") is None: continue
        said = (s0.get("vo") or (p.get("caption") or "").strip().split("\n")[0]).strip()
        r = {"opening": re.split(r"(?<=[.?!])\s+", said)[0][:160], "views": i["views"], "hold": round(100 - i["reels_skip_rate"])}
        if s0.get("text"): r["on_screen"] = s0["text"]
        if cat: r["format"] = cat
        if (tl or {}).get("T") and i.get("ig_reels_avg_watch_time"): r["watched"] = min(100, round(i["ig_reels_avg_watch_time"] / 10 / tl["T"]))   # (the time comes in ms)
        if i.get("reach"): r["sends_per_100_reached"] = round(100 * (i.get("shares") or 0) / i["reach"], 1)
        rows.append(r)
    rows = sorted(rows[:LAST], key=lambda r: (-r["hold"], -r["views"])); k = min(EACH, len(rows) // 2)
    return {"note": NOTE, "reels": len(rows), "median_hold": rows[len(rows) // 2]["hold"] if rows else None,
            "best": rows[:k], "worst": rows[len(rows) - k:][::-1] if k else []}


def main():
    tok = token(); uid = ig_id(tok); now = time.time()
    posts = http("GET", f"{HOST}/{V}/{uid}/media", {"fields": "id,caption,media_product_type,timestamp", "limit": 60, "access_token": tok}).get("data", [])
    for p in posts:
        if p.get("media_product_type") == "REELS" and age(p, now) >= OLD: p["insights"] = insights(p["id"], tok); time.sleep(0.3)
    out = {"pulled": time.strftime("%F %T UTC", time.gmtime()), **pick(posts, made(), now)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False); os.replace(OUT + ".tmp", OUT)   # (whole or not at all: brief() reads it)
    print(f"{out['reels']} reels, median hold {out['median_hold']}, {len(out['best'])} best and {len(out['worst'])} worst -> {OUT}")


def demo():
    now = calendar.timegm((2026, 11, 11, 0, 0, 0)); P = lambda n, day, v, skip, **k: {"id": n, "media_product_type": "REELS", "timestamp": f"2026-11-{day:02d}T06:00:00+0000",
        "caption": f"Line {n}? More.\nsecond", "insights": {"views": v, "reach": v, "shares": 1, "reels_skip_rate": skip, "ig_reels_avg_watch_time": 6000}, **k}
    posts = [P(1, 11, 500, 10), P(2, 9, 5, 10), P(3, 9, 100, 30), P(4, 8, 100, 70), P(5, 8, 100, 50), P(6, 7, 100, 40, media_product_type="FEED")]
    o = pick(posts, {"3": ({"T": 30, "scenes": [{"vo": "Your boat has holes. Each one is a fee.", "text": "Your boat has holes"}]}, "Stick skit")}, now)
    assert o["reels"] == 3 and o["median_hold"] == 50, o                      # (too young, too few views and a feed post are left out)
    assert o["best"] == [{"opening": "Your boat has holes.", "views": 100, "hold": 70, "on_screen": "Your boat has holes", "format": "Stick skit", "watched": 20, "sends_per_100_reached": 1.0}], o["best"]
    assert [r["opening"] for r in o["worst"]] == ["Line 4?"] and o["worst"][0]["hold"] == 30, o["worst"]
    assert pick([], {}, now)["best"] == []
    print("ok")


if __name__ == "__main__":
    demo() if "demo" in sys.argv[1:] else main()
