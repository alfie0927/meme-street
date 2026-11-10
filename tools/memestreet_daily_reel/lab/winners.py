"""Lab: Trial Reels winners onto the grid (the owner, 2026-11-08). A scored pair's winning reel takes the next regular slot
of its format (a Stock story winner is the next 18:00 Stock story), and the reels already scheduled at that hour move back
a day each. The loser stays a Trial Reel: non-followers only, never on the grid (the API cannot delete a post).

  python3 lab/winners.py          (auto_reel.sh runs it under the reel lock, config.env loaded)
  python3 lab/winners.py demo     self-check
"""
import datetime as dt, json, os, shutil, sys, tempfile

LAB = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(LAB)
sys.path.insert(0, os.path.join(ROOT, "src")); sys.path.insert(0, LAB)
DONE = os.path.join(LAB, "data", "winners.json")
FILES = ("reel.mp4", "caption.txt", "cover.jpg", "approved.json")
F = "%Y-%m-%dT%H%M"


def held(d):
    """A slot folder that holds something to post or to make (an approved reel, or a remake to do)."""
    return os.path.exists(os.path.join(d, "approved.json")) or os.path.exists(os.path.join(d, "remake.json"))


def place(q, src, cat, rotation, now):
    """Put the reel in folder `src` into the next slot of `cat` in queue `q` after `now`; push that hour's later reels back a
    day each. Returns the slot, or None when no hour takes the format."""
    hours = sorted(h for h, cats in rotation.items() if cat in cats)
    if not hours: return None
    day = now.date()
    while True:
        for h in hours:
            s = f"{day:%Y-%m-%d}T{h}"; t = dt.datetime.strptime(s, F)
            if t - now < dt.timedelta(minutes=10): continue
            d = os.path.join(q, s)
            if os.path.exists(os.path.join(d, "posted.json")) or os.path.exists(os.path.join(d, "winner.json")): continue
            chain = []                                     # (this hour's scheduled reels from here on, until a free day)
            while held(os.path.join(q, (t + dt.timedelta(days=len(chain))).strftime(F))): chain.append((t + dt.timedelta(days=len(chain))).strftime(F))
            for c in reversed(chain):                      # (the last first, so nothing is overwritten)
                nxt = os.path.join(q, (dt.datetime.strptime(c, F) + dt.timedelta(days=1)).strftime(F))
                if os.path.exists(nxt): shutil.rmtree(nxt)   # (a free day's folder holds only a held slot's try count)
                os.rename(os.path.join(q, c), nxt)
            if os.path.exists(d): shutil.rmtree(d)
            os.makedirs(d)
            for f in FILES:
                if os.path.exists(os.path.join(src, f)): shutil.copy(os.path.join(src, f), d)
            open(os.path.join(d, ".auto"), "w").close()
            return s
        day += dt.timedelta(days=1)


def main():
    import trials
    from make_spec import ROTATION
    trials.main()                                          # (scores every pair once both reels are 24 hours old)
    rows = json.load(open(os.path.join(LAB, "data", "trials.json")))
    done = json.load(open(DONE)) if os.path.exists(DONE) else {}
    q = os.path.join(ROOT, "queue"); now = dt.datetime.utcnow()
    for r in rows:
        if not r.get("winner") or r["pair"] in done: continue
        a = dt.datetime.strptime(r["pair"], F)
        src = os.path.join(q, (a if r["winner"] == "v1" else a + dt.timedelta(minutes=5)).strftime(F))
        if not os.path.exists(os.path.join(src, "reel.mp4")): done[r["pair"]] = {"slot": None, "why": "reel file gone"}; continue
        s = place(q, src, r["category"], ROTATION, now)
        if s: json.dump({"pair": r["pair"], "variant": r["winner"], "category": r["category"]}, open(os.path.join(q, s, "winner.json"), "w"))
        done[r["pair"]] = {"slot": s, "variant": r["winner"]}
        print(f"trial {r['pair']} ({r['category']}): {r['winner']} won; " + (f"posts at {s}" if s else "no slot takes this format"))
    os.makedirs(os.path.dirname(DONE), exist_ok=True); json.dump(done, open(DONE, "w"), indent=1)


def demo():
    q = tempfile.mkdtemp(); src = os.path.join(q, "src"); os.makedirs(src)
    for f in FILES: open(os.path.join(src, f), "w").write("winner")
    for s in ("2026-11-08T1800", "2026-11-09T1800"):       # (two stock stories already scheduled)
        os.makedirs(os.path.join(q, s)); open(os.path.join(q, s, "approved.json"), "w").write(s)
    os.makedirs(os.path.join(q, "2026-11-10T1800")); open(os.path.join(q, "2026-11-10T1800", ".tries"), "w").write("2")
    rot = {"1800": ["Stock story"], "1200": ["Chart quiz"]}
    s = place(q, src, "Stock story", rot, dt.datetime(2026, 11, 8, 12, 0))
    rd = lambda s: open(os.path.join(q, s, "approved.json")).read()
    assert s == "2026-11-08T1800" and rd(s) == "winner", s
    assert rd("2026-11-09T1800") == "2026-11-08T1800" and rd("2026-11-10T1800") == "2026-11-09T1800"   # (each a day back)
    assert place(q, src, "Myth or fact", rot, dt.datetime(2026, 11, 8, 12, 0)) is None
    open(os.path.join(q, s, "winner.json"), "w").write("{}")   # (a second winner goes after the first)
    assert place(q, src, "Stock story", rot, dt.datetime(2026, 11, 8, 12, 0)) == "2026-11-09T1800"
    assert rd("2026-11-11T1800") == "2026-11-09T1800"
    open(os.path.join(q, "2026-11-09T1800", "winner.json"), "w").write("{}")
    assert place(q, src, "Stock story", rot, dt.datetime(2026, 11, 8, 17, 55)) == "2026-11-10T1800"   # (too close: tomorrow's)
    shutil.rmtree(q); print("ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["demo"] else main()
