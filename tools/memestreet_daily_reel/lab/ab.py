"""Lab: the whole A/B for one brief, on this machine (no voice credits, nothing on the reel server).

  python3 lab/ab.py <slot> <category> <name>
1. lab/write.py: one brief, a v1 script (current rules) and a v2 script (RULES_V2.md)   (skipped if both exist)
2. lab/silent.py: each timed at the human pace
3. lab/frames.py --sheet: v1 drawn with src/reel.html, v2 with src/reel_v2.html
4. lab/audience.py: each scored alone, then the pair asked both ways round
Needs PYTHONPATH with playwright and FFMPEG (see lab/frames.py).
"""
import json, os, subprocess, sys

LAB = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(LAB)
sys.path.insert(0, LAB)
import audience


def run(*a):
    subprocess.run([sys.executable, *a], check=True, cwd=ROOT)


def main(slot, category, name):
    works = {v: os.path.join(LAB, "work", f"{name}-{v}") for v in ("v1", "v2")}
    if not all(os.path.exists(os.path.join(w, "spec.json")) for w in works.values()):
        run(os.path.join(LAB, "write.py"), slot, category, name)
    packs = {}
    for v, page in (("v1", os.path.join(ROOT, "src", "reel.html")), ("v2", os.path.join(ROOT, "src", "reel_v2.html"))):
        w = works[v]; d = packs[v] = os.path.join(LAB, "data", "ab", f"{name}-{v}")
        run(os.path.join(LAB, "silent.py"), w)
        run(os.path.join(LAB, "frames.py"), os.path.join(w, "timeline.json"), page, d + os.sep, "--sheet")
        run(os.path.join(LAB, "audience.py"), "packtl", os.path.join(w, "timeline.json"), d, os.path.join(w, "caption.txt"))
        r = audience.watch(d); print(v, json.dumps(r["predicted"]))
    print("pair (share of the panel preferring v1):", audience.both(packs["v1"], packs["v2"]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
