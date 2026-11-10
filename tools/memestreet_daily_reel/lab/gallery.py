"""Lab: the owner's rating gallery (2026-11-08). Short silent clips of every library shot (3 castings each), the story
layouts as real stock stories drew them, and design A/B pairs (glow, push-in, breath, tag style), with an items.json the
rating page reads.  python3 lab/gallery.py <out dir>   (on the reel server: Playwright and ffmpeg; no Claude, no voice)
"""
import asyncio, glob, json, os, subprocess, sys

LAB = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(LAB)
sys.path.insert(0, LAB); sys.path.insert(0, os.path.join(ROOT, "src"))
from frames import shoot
import shots
from make_spec import WORLD_PROPS

FPS = 30
CASTS = {   # (round 2, 2026-11-08: recast from the owner's notes; shot: three castings, each a line, its cast, its moments and options)
    "rise_fall": [("It went up like crazy, then crashed.", {"hero": {"p": "rocket", "color": "amber"}}, {"up": "went up", "down": "then crashed"}, {}),
                  ("The hype launched it, then it came back down.", {"hero": {"p": "plane", "label": "The hype"}}, {"up": "launched it", "down": "came back down"}, {}),
                  ("One dragon soared, then dropped out of the sky.", {"hero": {"p": "dragon", "color": "purple"}}, {"up": "soared", "down": "dropped"}, {})],
    "clash": [("A rival ship rammed their freighter.", {"a": {"p": "ship", "color": "red", "label": "Rival"}, "b": {"p": "sub", "label": "Freighter"}}, {"hit": "rammed"}, {}),
              ("A runaway truck smashed into the depot.", {"a": {"p": "truck", "color": "red"}, "b": {"p": "warehouse", "label": "Depot"}}, {"hit": "smashed into"}, {}),
              ("A rogue drone flew straight into the turbine.", {"a": {"p": "drone", "color": "red"}, "b": {"p": "turbine"}}, {"hit": "flew straight into"}, {})],
    "crash_landing": [("One escaped dragon landed on the motorway as a truck drove in.", {"a": {"p": "truck"}, "b": {"p": "dragon", "color": "amber"}}, {"land": "landed on the motorway"}, {}),
                      ("A crate fell off a plane, right in front of the van.", {"a": {"p": "truck", "label": "Van"}, "b": {"p": "crate", "color": "amber"}}, {"land": "fell off a plane"}, {}),
                      ("A drone dropped onto the road as the train came through.", {"a": {"p": "train"}, "b": {"p": "drone", "color": "red"}}, {"land": "dropped onto the road"}, {})],
    "pour": [("Every rental pays it.", {"source": {"p": "dragon", "color": "amber"}, "pile": {"p": "coins", "color": "amber"}}, {"pour": "pays it"}, {"what": "coins"}),
             ("Fans pour money into the brand.", {"source": {"p": "person", "color": "purple"}, "pile": {"p": "coins", "color": "amber"}}, {"pour": "pour money"}, {"what": "coins"}),
             ("Every flight pays out.", {"source": {"p": "plane"}, "pile": {"p": "coins", "color": "amber"}}, {"pour": "pays out"}, {"what": "coins"})],
    "rally_drop": [("It rises all morning, then it drops in one hour.", {}, {"up": "rises all morning", "down": "drops in one hour"}, {}),
                   ("Buyers pushed it up, then sellers dumped it.", {}, {"up": "pushed it up", "down": "dumped it"}, {}),
                   ("The hype lifted it, then the news sank it.", {}, {"up": "lifted it", "down": "sank it"}, {})],
    "fill": [("Rain on demand fills the reservoir.", {"cloud": {"p": "cloud"}, "pile": {"p": "lake", "label": "Reservoir"}}, {"rain": "fills the reservoir"}, {}),
             ("Its clouds water the farms in a drought.", {"cloud": {"p": "cloud"}, "pile": {"p": "tree", "color": "green", "label": "Farms"}}, {"rain": "water the farms"}, {}),
             ("Seeded storms refill the lake.", {"cloud": {"p": "cloud", "color": "purple"}, "pile": {"p": "lake"}}, {"rain": "refill the lake"}, {})],
    "shield": [("Support held when sellers hit it.", {"guard": {"p": "shield", "color": "amber", "label": "Support"}, "threat": {"p": "person", "color": "red", "label": "Sellers"}}, {"strike": "sellers hit it"}, {}),
               ("A stop-loss saves you when the crash comes.", {"guard": {"p": "shield", "label": "Stop-loss"}, "threat": {"p": "warning", "color": "red", "label": "Crash"}}, {"strike": "the crash comes"}, {}),
               ("Insurance protects the ranch when a storm hits.", {"guard": {"p": "shield", "color": "green", "label": "Insurance"}, "threat": {"p": "cloud", "color": "red", "label": "Storm"}}, {"strike": "a storm hits"}, {})],
    "three_up": [("Three charts, three questions: how many can you get?", {"item1": {"p": "chart"}, "item2": {"p": "chart"}, "item3": {"p": "chart"}, "topper": {"p": "question", "color": "amber"}}, {"items": "Three charts", "topper": "three questions"}, {}),
                 ("Three candles, one question.", {"item1": {"p": "candle", "color": "green"}, "item2": {"p": "candle", "color": "red"}, "item3": {"p": "candle", "color": "green"}, "topper": {"p": "question", "color": "amber"}}, {"items": "Three candles", "topper": "one question"}, {}),
                 ("Three jobs, one payday.", {"item1": {"p": "truck"}, "item2": {"p": "crate"}, "item3": {"p": "plane"}, "topper": {"p": "coin", "color": "amber"}}, {"items": "Three jobs", "topper": "one payday"}, {})],
    "versus": [("Patience beat rushing, every time.", {"left": {"p": "hourglass", "color": "green", "label": "Patience"}, "right": {"p": "rocket", "color": "red", "label": "Rushing"}}, {"win": "beat rushing"}, {"winner": "left"}),
               ("Teleport freight beat the trucks.", {"left": {"p": "truck", "label": "Trucks"}, "right": {"p": "portal", "color": "purple", "label": "Teleport"}}, {"win": "beat the trucks"}, {"winner": "right"}),
               ("Buyers won the fight with sellers.", {"left": {"p": "person", "color": "green", "label": "Buyers"}, "right": {"p": "person", "color": "red", "label": "Sellers"}}, {"win": "won the fight"}, {"winner": "left"})],
    "count": [("Two charts, two guesses: can you call the move?", {"hero": {"p": "question", "color": "amber", "label": "Your call"}}, {"count": "call the move"}, {}),
("Support held 24 times.", {"hero": {"p": "shield", "color": "amber", "label": "Support"}}, {"count": "24 times"}, {}),
              ("It earns three ways.", {"hero": {"p": "coins", "color": "amber"}}, {"count": "three ways"}, {}),
              ("The motorway shut for one whole day.", {"hero": {"p": "clock", "color": "amber"}}, {"count": "one whole day"}, {})],
    "arrive": [("A new drone lands and buyers love it.", {"hero": {"p": "drone"}, "left": {"p": "person"}, "right": {"p": "person", "color": "amber"}}, {"arrive": "lands", "cheer": "buyers love it"}, {}),
               ("The rocket touched down and the money rolled in.", {"hero": {"p": "rocket", "color": "amber"}, "left": {"p": "person", "color": "green"}, "right": {"p": "person", "color": "green"}}, {"arrive": "touched down", "cheer": "money rolled in"}, {"what": "coins"}),
               ("A new ship docked and the fans fell in love.", {"hero": {"p": "ship"}, "left": {"p": "person"}, "right": {"p": "person"}}, {"arrive": "docked", "cheer": "fell in love"}, {})],
    "reveal": [("A record hatching season: the eggs hatched baby dragons.", {"shell": {"p": "egg", "color": "amber"}, "inside": {"p": "dragon", "color": "amber"}}, {"open": "hatched"}, {}),
               ("One dragon broke out of its cage.", {"shell": {"p": "cage"}, "inside": {"p": "dragon", "color": "red", "label": "Escaped"}}, {"open": "broke out"}, {}),
               ("The crate opened and a new drone flew out.", {"shell": {"p": "crate", "color": "amber"}, "inside": {"p": "drone"}}, {"open": "opened"}, {})],
}
PAIRS_R1 = [("glow", "Glow: soft or strong?", {"glow": 2}, {"glow": 8}),
         ("push", "Camera: slow push-in or still?", {"push": .04}, {"push": 0}),
         ("breath", "Props: breathing or still?", {"breath": .03}, {"breath": 0}),
         ("tags", "Tags: dark box or bare text?", {}, {"css": ".slab{background:none;border:none;text-shadow:0 2px 10px #000;font-size:40px}"})]


def base():
    """A real stock story's spec as the frame for a one-scene clip (its type, title, company)."""
    for f in sorted(glob.glob(os.path.join(ROOT, "work", "auto-*", "spec.json")), reverse=True):
        S = json.load(open(f))
        if any(s.get("kind") == "story" for s in S.get("scenes", [])): return S
    raise SystemExit("no stock story spec in work/")


def clip(R, t0, t1, out, tok=None):
    R = dict(R, tok=tok or {})
    fr = asyncio.run(shoot(R, os.path.join(ROOT, "src", "reel.html"), [t0 + k / FPS for k in range(int((t1 - t0) * FPS))]))
    d = out + "_f"; os.makedirs(d, exist_ok=True)
    for k, b in enumerate(fr): open(os.path.join(d, f"{k:04d}.jpg"), "wb").write(b)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(d, "%04d.jpg"), "-vf", "scale=540:-2",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
    for f in os.listdir(d): os.remove(os.path.join(d, f))
    os.rmdir(d)


def timeline(B, scene, work):
    """One acted scene and the outro, timed without a voice (lab/silent.py)."""
    os.makedirs(work, exist_ok=True)
    S = dict(B, title="", scenes=[dict(scene, kind="hook", text=""), B["scenes"][-1]])
    assert not shots.expand_all(S, WORLD_PROPS), shots.expand_all(S, WORLD_PROPS)
    json.dump(S, open(os.path.join(work, "spec.json"), "w"))
    subprocess.run([sys.executable, os.path.join(LAB, "silent.py"), work], check=True, stdout=subprocess.DEVNULL)
    return json.load(open(os.path.join(work, "timeline.json")))


def main(out):
    os.makedirs(out, exist_ok=True); B = base(); items = []; work = os.path.join(LAB, "work", "gallery")
    for name, casts in ((n, c) for n, c in CASTS.items() if n in ("rally_drop", "count")):
        for j, (vo, cast, on, opts) in enumerate(casts):
            R = timeline(B, dict({"vo": vo, "act": name, "cast": cast, "on": on}, **opts), work); s = R["scenes"][0]
            f = f"r6-shot-{name}-{j + 1}.mp4"
            if not os.path.exists(os.path.join(out, f)): clip(R, 0, s["t1"] + .4, os.path.join(out, f))
            items.append({"id": f[:-4], "kind": "shot", "group": name, "title": f"{name.replace('_', ' ')}: \"{vo}\"", "file": f}); print(f, flush=True)
    for f in sorted(glob.glob(os.path.join(ROOT, "work", "auto-*", "timeline.json")), reverse=True):   # (the layouts, as real stories drew them)
        R = json.load(open(f))
        for i, s in enumerate(R["scenes"]):
            lay = s.get("layout")
            if True or sum(x["group"] == lay for x in items) >= 2: continue
            g = f"r3-layout-{lay}-{sum(x['group'] == lay for x in items) + 1}.mp4"
            if not os.path.exists(os.path.join(out, g)): clip(R, s["t0"], s["t1"], os.path.join(out, g))
            items.append({"id": g[:-4], "kind": "layout", "group": lay, "title": f"{lay}: \"{s['vo']}\"", "file": g}); print(g, flush=True)
    seen = {}                                              # (the other reel types' scenes, as real reels drew them: two of each kind)
    for f in sorted(glob.glob(os.path.join(ROOT, "work", "auto-*", "timeline.json")), reverse=True):
        R = json.load(open(f)); typ = R.get("type") or "?"
        for i, s in enumerate(R["scenes"]):
            k = s.get("kind")
            if k not in ("stick",) or seen.get(k, 0) >= 2 or (k, typ) in seen: continue
            seen[k] = seen.get(k, 0) + 1; seen[(k, typ)] = 1
            g = f"r6-scene-{k}-{seen[k]}.mp4"
            if not os.path.exists(os.path.join(out, g)): clip(R, s["t0"], s["t1"], os.path.join(out, g))
            items.append({"id": g[:-4], "kind": "scene", "group": k, "title": f"{typ}, {k}: \"{s['vo']}\"", "file": g}); print(g, flush=True)
    R = timeline(B, {"vo": CASTS["clash"][0][0], "act": "clash", "cast": CASTS["clash"][0][1], "on": CASTS["clash"][0][2]}, work)
    for key, q, a, b in []:   # (round 1 settled the design pairs: all 'same', the defaults stay)
        fa, fb = f"pair-{key}-a.mp4", f"pair-{key}-b.mp4"
        for ff, tk in ((fa, a), (fb, b)):
            if not os.path.exists(os.path.join(out, ff)): clip(R, 0, R["scenes"][0]["t1"] + .4, os.path.join(out, ff), tk)
        items.append({"id": f"pair-{key}", "kind": "pair", "group": key, "title": q, "a": fa, "b": fb, "tok_a": a, "tok_b": b}); print(fa, fb, flush=True)
    json.dump(items, open(os.path.join(out, "items.json"), "w"), indent=1)
    print(len(items), "items")


if __name__ == "__main__":
    main(sys.argv[1])
