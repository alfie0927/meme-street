"""Render the reel: chart frames (headless Chromium) + narration -> 1080x1920 MP4.
Usage: python3 src/render.py work/<date> out/<date>
"""
import asyncio, json, os, shutil, subprocess, sys
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = int(os.environ.get("FPS", "60"))   # 60 = smoothest; 30 renders twice as fast

async def frames(R, fdir, cover=None, date=""):
    os.makedirs(fdir, exist_ok=True)
    n = int(round(R["T"] * FPS))
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        await pg.add_init_script(f"window.__R={json.dumps(R)};")
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(f"file://{HERE}/{os.environ.get('PAGE', 'recap.html')}"); await pg.evaluate("document.fonts.ready")   # (PAGE=reel.html: the auto reels)
        for i in range(n):
            await pg.evaluate("t=>render(t)", i / FPS)
            await pg.screenshot(path=f"{fdir}/f{i:05d}.jpg", type="jpeg", quality=92)
        if os.environ.get("PAGE") == "reel.html":           # no text may touch other text, anywhere in the reel
            bad = {}
            for q in range(int(R["T"] * 4)):
                for pair in await pg.evaluate("t=>qa(t)", q / 4):
                    bad.setdefault(tuple(pair), q / 4)
            if bad:
                raise SystemExit("overlapping text: " + "; ".join(f"{a} / {b} at {t:.2f}s" for (a, b), t in list(bad.items())[:6]))
        if cover:
            await pg.evaluate("d=>cover(d)", date)
            await pg.screenshot(path=cover, type="jpeg", quality=92)
        await b.close()
        if errs: raise SystemExit("render errors: " + "; ".join(errs[:3]))
    return n

def main(work, out):
    R = json.load(open(os.path.join(work, "timeline.json")))
    fdir = os.path.join(work, "frames"); shutil.rmtree(fdir, ignore_errors=True)
    os.makedirs(out, exist_ok=True)
    n = asyncio.run(frames(R, fdir, os.path.join(out, "cover.jpg"), os.path.basename(os.path.normpath(out))))
    T = R["T"]; ins = []; flt = []
    for i, (f, a) in enumerate(R["vo"]):
        ins += ["-i", f]; flt.append(f"[{i}:a]adelay={int(a*1000)}[v{i}]")
    flt.append("".join(f"[v{i}]" for i in range(len(R["vo"]))) + f"amix=inputs={len(R['vo'])}:normalize=0,apad=whole_dur={T},loudnorm=I=-16:TP=-1.5[o]")
    vo = os.path.join(work, "voice.m4a")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(flt), "-map", "[o]", "-ar", "48000", "-ac", "1", "-c:a", "aac", "-b:a", "160k", vo], check=True)
    mp4 = os.path.join(out, "reel.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{fdir}/f%05d.jpg", "-i", vo, "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
                    "-c:a", "copy", "-movflags", "+faststart", "-t", str(T), mp4], check=True)
    shutil.copy(os.path.join(work, "caption.txt"), os.path.join(out, "caption.txt"))
    shutil.rmtree(fdir, ignore_errors=True)
    print(f"rendered {mp4} ({n} frames, {T:.1f}s)")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
