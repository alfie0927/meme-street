"""Which reel formats Instagram's viewers stay for (the owner, 2026-11-12: "see which reels do the best and try to make more
of those / get rid of ones with high skip rates").

  python3 src/format_scores.py         -> state/format_scores.json, and the board on stdout (auto_reel.sh runs it twice a day)
  python3 src/format_scores.py demo    the self-check, no network

Counted: every director reel that is at least 24 hours old (a younger one is still being shown) and was shown at least 20
times. Per format: how many, and the median skip rate (who left in the first 3 seconds), views and seconds watched. A format
with 3 or more such reels gets a verdict against the median of all of them:
  cut    its skip rate is 8 points or more above: make_spec.py brief() stops making it
  boost  8 points or more below: it joins every turn and is made every day (the best 2 at most)
  keep   in between;   new: under 3 reels, it keeps its turn;   scheduled: the Daily and the explainers, never cut or boosted
At least 9 rotation formats always stay (7 slots a day, one reel of each format a day). A reel's numbers are read again for a
week after it posts, then kept as they are, so a format's count grows past the 60 posts the API lists.
"""
import json, os, statistics, sys, time
from own_reels import insights, made, age, load
from post_instagram import http, token, ig_id, HOST, V, ROOT

OUT = os.path.join(ROOT, "state", "format_scores.json")
DAY, SHOWN, MIN_N, MARGIN, MAX_BOOST, FLOOR = 86400, 20, 3, 8, 2, 9
SCHEDULED = ("Daily recap", "Daily Chart explained", "Meme Street explained")


def board(rows, rotation):
    """rows: [{format, skip, views, watch_s}], rotation: the formats that take turns -> the median skip and each format's line."""
    rows = [r for r in rows if r.get("format")]
    if not rows: return {"median_skip": None, "formats": {}}
    med = statistics.median(r["skip"] for r in rows); F = {}
    for r in rows: F.setdefault(r["format"], []).append(r)
    out = {f: {"reels": len(rs), **{k: round(statistics.median(r[k] for r in rs), 1) for k in ("skip", "views", "watch_s")}} for f, rs in F.items()}
    for f, x in out.items():
        x["verdict"] = "scheduled" if f in SCHEDULED else "new" if x["reels"] < MIN_N else \
                       "cut" if x["skip"] >= med + MARGIN else "boost" if x["skip"] <= med - MARGIN else "keep"
    worst = lambda v, sign: sorted((f for f, x in out.items() if x["verdict"] == v), key=lambda f: sign * out[f]["skip"])
    for f in worst("boost", 1)[MAX_BOOST:]: out[f]["verdict"] = "keep"                       # (the two best only)
    cut = [f for f in worst("cut", -1) if f in rotation]                                    # (the worst first)
    for f in cut[max(0, len(rotation) - FLOOR):]: out[f]["verdict"] = "keep"                # (enough formats always stay)
    return {"median_skip": round(med, 1), "formats": out}


def show(b):
    lines = [f"{'format':24}{'reels':>6}{'skip %':>8}{'views':>7}{'watch s':>9}  verdict", f"(median skip of all reels: {b['median_skip']})"]
    for f, x in sorted(b["formats"].items(), key=lambda kv: kv[1]["skip"]):
        lines.append(f"{f[:23]:24}{x['reels']:>6}{x['skip']:>8}{x['views']:>7}{x['watch_s']:>9}  {x['verdict']}")
    return "\n".join(lines)


def main():
    from make_spec import ROTATION
    tok = token(); uid = ig_id(tok); now = time.time()
    rows = (load(OUT) if os.path.exists(OUT) else {}).get("rows", {}); mk = made()
    posts = http("GET", f"{HOST}/{V}/{uid}/media", {"fields": "id,media_product_type,timestamp", "limit": 60, "access_token": tok}).get("data", [])
    for p in posts:
        mid = str(p["id"]); a = age(p, now); tl, cat = mk.get(mid, (None, None))
        if p.get("media_product_type") != "REELS" or a < DAY or (mid in rows and a > 7 * DAY): continue
        if mid not in rows and not (cat and (tl or {}).get("scene_js")): continue     # (director reels with their script still here)
        i = insights(mid, tok); time.sleep(0.3)
        if i.get("reels_skip_rate") is None or (i.get("views") or 0) < SHOWN: continue
        rows[mid] = {"format": cat or rows[mid]["format"], "posted": p["timestamp"][:16], "title": (tl or {}).get("title") or rows.get(mid, {}).get("title"),
                     "skip": round(i["reels_skip_rate"], 1), "views": i["views"], "watch_s": round((i.get("ig_reels_avg_watch_time") or 0) / 1000, 1)}
    b = board(list(rows.values()), {c for cs in ROTATION.values() for c in cs})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"pulled": time.strftime("%F %T UTC", time.gmtime()), **b, "rows": rows}, open(OUT + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    os.replace(OUT + ".tmp", OUT)                           # (whole or not at all: brief() reads it)
    print(time.strftime("%F %T UTC", time.gmtime()), f"{len(rows)} reels"); print(show(b))


def demo():
    R = lambda f, *skips: [{"format": f, "skip": k, "views": 100, "watch_s": 7} for k in skips]
    rot = {"Best", "Good", "Mid", "Bad", "Worse", "Few"} | {f"x{k}" for k in range(5)}       # (11 take turns: two may go)
    rows = R("Best", 30, 32, 34) + R("Good", 36, 38, 40) + R("Mid", 50, 50, 50) + R("Bad", 60, 62, 64) + R("Worse", 70, 72, 74) + \
           R("Few", 90, 90) + R("Daily recap", 90, 90, 90) + R("Also best", 20, 20, 20) + R(None, 1)
    b = board(rows, rot); v = {f: x["verdict"] for f, x in b["formats"].items()}
    assert b["median_skip"] == 50 and b["formats"]["Best"] == {"reels": 3, "skip": 32, "views": 100, "watch_s": 7, "verdict": "boost"}, b
    assert v == {"Best": "boost", "Good": "keep", "Mid": "keep", "Bad": "cut", "Worse": "cut", "Few": "new", "Daily recap": "scheduled", "Also best": "boost"}, v
    v = {f: x["verdict"] for f, x in board(rows, rot - {"x0"})["formats"].items()}            # (10 take turns: only the worst goes)
    assert v["Worse"] == "cut" and v["Bad"] == "keep", v
    assert board([], rot) == {"median_skip": None, "formats": {}} and "Best" in show(b)
    print("ok")


if __name__ == "__main__":
    demo() if "demo" in sys.argv[1:] else main()
