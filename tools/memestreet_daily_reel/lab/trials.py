"""Lab: the Trial Reels scoreboard. Every posted pair (queue/*/posted.json with "trial"), its real insights side by side,
which version won, and whether the simulated verdict (lab/data/trial/<pair>-v1/-v2) called it.

  python3 lab/trials.py          (on the reel server, config.env loaded)  -> lab/data/trials.json and a table
A pair is scored once both reels are 24 hours old; the winner is the lower skip rate, ties broken by watch time.
"""
import glob, json, os, sys, time

LAB = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(LAB)
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, LAB)
M = ["views", "reach", "reels_skip_rate", "ig_reels_avg_watch_time", "likes", "comments", "shares", "saved"]


def winner(a, b):
    """'v1', 'v2' or None: the lower skip rate wins; within 3 points, the longer average watch."""
    if a.get("reels_skip_rate") is None or b.get("reels_skip_rate") is None: return None
    if abs(a["reels_skip_rate"] - b["reels_skip_rate"]) >= 3: return "v1" if a["reels_skip_rate"] < b["reels_skip_rate"] else "v2"
    return "v1" if (a.get("ig_reels_avg_watch_time") or 0) >= (b.get("ig_reels_avg_watch_time") or 0) else "v2"


def main():
    from post_instagram import http, token, HOST, V
    import insights
    tok = token(); pairs = {}
    for f in glob.glob(os.path.join(ROOT, "queue", "*", "posted.json")):
        p = json.load(open(f))
        if not p.get("trial"): continue
        t = p["trial"]; age = time.time() - time.mktime(time.strptime(p["posted_at"], "%Y-%m-%d %H:%M:%S UTC"))
        i = insights.insights(p["media_id"], tok) if age > 86400 else {}
        pairs.setdefault(t["pair"], {"category": t.get("category"), "version": t.get("version", 1)})[t["variant"]] = {"media_id": p["media_id"], "age_h": round(age / 3600), **i}
    rows = []
    for k in sorted(pairs):
        P = pairs[k]; a, b = P.get("v1", {}), P.get("v2", {})
        sim = None
        sf = os.path.join(LAB, "data", "trial", f"{k}-sim.json")
        if os.path.exists(sf): sim = json.load(open(sf))
        w = winner(a, b) if a and b else None
        rows.append({"pair": k, "category": P["category"], "version": P["version"], "v1": a, "v2": b, "winner": w,
                     "simulated": sim, "sim_right": (sim["pick"] == w) if sim and w else None})
    json.dump(rows, open(os.path.join(LAB, "data", "trials.json"), "w"), indent=1)
    f = lambda r, v, m: r[v].get(m, "-") if r[v] else "-"
    print(f"{'pair':16} {'format':16} {'skip v1/v2':>13} {'watch s v1/v2':>14} {'views v1/v2':>12} {'shares':>7}  winner  sim")
    for r in rows:
        ws = lambda v: round((r[v].get("ig_reels_avg_watch_time") or 0) / 1000, 1) if r[v] and "ig_reels_avg_watch_time" in r[v] else "-"
        print(f"{r['pair']:16} {str(r['category'])[:16]:16} {str(f(r,'v1','reels_skip_rate')):>6}/{str(f(r,'v2','reels_skip_rate')):<6} {str(ws('v1')):>6}/{str(ws('v2')):<7} "
              f"{str(f(r,'v1','views')):>5}/{str(f(r,'v2','views')):<6} {str(f(r,'v1','shares'))}/{str(f(r,'v2','shares')):<4}  {str(r['winner'] or 'wait'):6}  "
              f"{(r['simulated'] or {}).get('pick', '-')}{'' if r['sim_right'] is None else (' right' if r['sim_right'] else ' wrong')}")
    import evolve
    for v, x in sorted(evolve.summary(rows).items()):
        print(f"rules version {v}: {x['pairs']} pairs scored, version 2 won {x['v2_wins']}; skip {x['skip_v1']}% -> {x['skip_v2']}%, watch {x['watch_v1']}s -> {x['watch_v2']}s")
    done = [r for r in rows if r["winner"]]
    if done:
        print(f"version 2 won {sum(r['winner'] == 'v2' for r in done)} of {len(done)} scored pairs; "
              f"the simulation called {sum(bool(r['sim_right']) for r in done if r['sim_right'] is not None)} of {sum(r['sim_right'] is not None for r in done)}")


if __name__ == "__main__":
    main()
