"""Lab: render chosen moments of a reel from its timeline.json with a template, as one strip (no voice, no video).

  python3 lab/frames.py <timeline.json> <page.html> <out.jpg> [t1 t2 ...]   (default: the first 3 s, then every 4 s)
  python3 lab/frames.py <timeline.json> <page.html> <dir>/ --sheet          the first 3 s and the whole reel, as the
                                                                             audience's feed pack reads them
Used to compare template versions (src/reel.html against src/reel_v2.html) without touching the reel pipeline.
"""
import asyncio, json, math, os, subprocess, sys
from playwright.async_api import async_playwright

HOOK_T = [0, 0.5, 1, 1.5, 2, 3]


async def shoot(R, page, times, w=360):
    shots = []
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.add_init_script(f"window.__R={json.dumps(R)};")
        await pg.goto("file:///" + os.path.abspath(page).replace("\\", "/")); await pg.evaluate("document.fonts.ready")
        for t in times:
            await pg.evaluate("t=>render(t)", t)
            shots.append(await pg.screenshot(type="jpeg", quality=88, scale="css", clip={"x": 0, "y": 0, "width": 1080, "height": 1920}))
        await b.close()
    if errs: raise SystemExit("page errors: " + "; ".join(errs[:3]))
    return shots


def strip(shots, out, w=360, cols=None):
    """Side by side (cols=None) or a grid of `cols` columns, each frame w px wide."""
    ff = os.environ.get("FFMPEG", "ffmpeg"); tmp = out + "_parts"; os.makedirs(tmp, exist_ok=True)
    for i, s in enumerate(shots): open(os.path.join(tmp, f"{i:03d}.jpg"), "wb").write(s)
    cols = cols or len(shots); rows = math.ceil(len(shots) / cols)
    subprocess.run([ff, "-v", "error", "-y", "-i", os.path.join(tmp, "%03d.jpg"), "-vf", f"scale={w}:-1,tile={cols}x{rows}",
                    "-frames:v", "1", out], check=True)
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


def main(a):
    R = json.load(open(a[0], encoding="utf-8")); page, out = a[1], a[2]
    if "--sheet" in a:
        os.makedirs(out, exist_ok=True); whole = [i * 1.5 for i in range(int(R["T"] / 1.5) + 1)]
        shots = asyncio.run(shoot(R, page, HOOK_T + whole))
        strip(shots[:len(HOOK_T)], os.path.join(out, "first_3s.jpg"), 360)
        strip(shots[len(HOOK_T):], os.path.join(out, "whole_reel.jpg"), 180, 8)
        return
    times = [float(x) for x in a[3:]] or HOOK_T + [4 + 4 * i for i in range(int((R["T"] - 4) / 4) + 1)]
    strip(asyncio.run(shoot(R, page, times)), out)


if __name__ == "__main__":
    main(sys.argv[1:])
