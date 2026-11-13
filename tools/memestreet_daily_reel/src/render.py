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
        pg.set_default_timeout(180000)                    # (a frame late in a long render can take a while)
        await pg.add_init_script(f"window.__R={json.dumps(R)};")
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(f"file://{HERE}/{os.environ.get('PAGE', 'recap.html')}"); await pg.evaluate("document.fonts.ready")   # (PAGE=reel.html: the auto reels)
        for i in range(n):
            await pg.evaluate("t=>render(t)", i / FPS)
            await pg.screenshot(path=f"{fdir}/f{i:05d}.jpg", type="jpeg", quality=92)
        if os.environ.get("PAGE", "").startswith("reel"):           # no text may touch other text, anywhere in the reel
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

async def dry(R, fdir, fps=2):
    """DRY=1: a director reel's scene function (make_spec.py scene_js) is run through the whole reel at 2 fps before any
    voice is made: a JavaScript error, text on text, text under 26 px, three seconds in which nothing on screen changes,
    or a frame that takes too long to draw, and the writer gets the reason back. Returns the list of faults."""
    import time
    os.makedirs(fdir, exist_ok=True); n = int(round(R["T"] * fps)); faults = []; took = []; small = {}; bad = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        pg.set_default_timeout(180000)
        await pg.add_init_script(f"window.__R={json.dumps(R)};")
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(f"file://{HERE}/{os.environ.get('PAGE', 'reel.html')}"); await pg.evaluate("document.fonts.ready")
        if errs: await b.close(); return [f"the scene function does not load: {errs[0][:300]}"]
        for i in range(n):
            t = i / fps; t0 = time.time()
            try:
                await pg.evaluate("t=>render(t)", t)
            except Exception as e:                       # (a throw inside the scene function at this t)
                await b.close(); return [f"the scene function threw at t={t:.1f}s: {str(e).splitlines()[0][:300]}"]
            took.append(time.time() - t0)
            await pg.screenshot(path=f"{fdir}/f{i:05d}.jpg", type="jpeg", quality=70)
            for pair in await pg.evaluate("t=>qa(t,1)", t):   # (1: also what the scene function draws)
                bad.setdefault(tuple(pair), t)
            m = await pg.evaluate("minFont()")
            if m is not None and m < 26: small.setdefault(round(m), t)
            if i == 0 and R.get("scene_js") and await pg.evaluate("hook0()") < 72:   # (the first frame is the hook: whole, large, readable with the sound off)
                faults.append("frame 0 has no large hook: scene 0 is a free scene whose punch 'text' is 2 to 5 short words (the template draws it whole at the top, 72 px or more, in two lines at most)")
        await b.close()
    for (a, c), t in list(bad.items())[:5]: faults.append(f"covered at {t:.1f}s: {a} and {c} overlap; move one of them so both read clean (a label is never under a figure, a ring or another label)")
    for m, t in list(small.items())[:3]: faults.append(f"text {m} px at {t:.1f}s: nothing the scene draws may be under 26 px (unreadable on a phone)")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-framerate", str(fps), "-i", f"{fdir}/f%05d.jpg", "-vf", "scale=135:240,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    F = memoryview(raw); px = 135 * 240; still = 0; last = None
    kind = lambda t: next((q["kind"] for q in reversed(R["scenes"]) if t >= q["t0"] - 1e-3), "free")   # (the big line and the end card are the template's: they may hold)
    for i in range(1, len(raw) // px):
        a, c = F[(i - 1) * px:i * px], F[i * px:(i + 1) * px]
        d = sum(abs(x - y) for x, y in zip(a.tobytes(), c.tobytes())) / px   # ponytail: pure-python frame diff (no numpy here), ~10 ms a frame
        still = still + 1 if d < 0.25 and kind(i / fps) not in ("big", "outro") else 0
        if still >= 3 * fps and last != i // (3 * fps): faults.append(f"nothing visibly changes from {(i / fps - 3):.0f}s to {i / fps:.0f}s: something must move or appear every 2 to 3 seconds"); last = i // (3 * fps)
    budget = float(os.environ.get("DRY_FRAME_MS", "250")) / 1000
    if took and sum(took) / len(took) > budget: faults.append(f"a frame takes {1000 * sum(took) / len(took):.0f} ms to draw (budget {1000 * budget:.0f} ms): simplify the drawing (fewer particles, no filters on big groups)")
    return faults[:8]


def main(work, out):
    R = json.load(open(os.path.join(work, "timeline.json")))
    if os.environ.get("DRY") == "1":
        fdir = os.path.join(work, "dry"); shutil.rmtree(fdir, ignore_errors=True)
        faults = asyncio.run(dry(R, fdir))
        if os.environ.get("DRY_KEEP") != "1": shutil.rmtree(fdir, ignore_errors=True)   # (DRY_KEEP=1: look at the frames)
        if faults: raise SystemExit("DRY: " + "; ".join(faults))
        print(f"dry run ok ({R['T']:.1f}s)"); return
    fdir = os.path.join(work, "frames"); shutil.rmtree(fdir, ignore_errors=True)
    os.makedirs(out, exist_ok=True)
    n = asyncio.run(frames(R, fdir, os.path.join(out, "cover.jpg"), os.path.basename(os.path.normpath(out))))
    T = R["T"]; ins = []; flt = []
    for i, (f, a) in enumerate(R["vo"]):
        ins += ["-i", f]; flt.append(f"[{i}:a]adelay={int(a*1000)}[v{i}]")
    music = os.path.join(os.path.dirname(HERE), "assets", "music.wav")
    if os.environ.get("PAGE", "").startswith("reel") and os.path.exists(music):
        # the house music under everything, ducked while the voice speaks (sounds.py makes it)
        m = len(R["vo"]); ins += ["-stream_loop", "-1", "-i", music]
        flt.append("".join(f"[v{i}]" for i in range(m)) + f"amix=inputs={m}:normalize=0,apad=whole_dur={T},asplit=2[mx][sc]")
        flt.append(f"[{m}:a]atrim=0:{T},volume=0.22,afade=t=out:st={max(0, T - 1.2)}:d=1.2[mu]")
        flt.append("[mu][sc]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=350[du]")
        flt.append("[mx][du]amix=inputs=2:normalize=0,loudnorm=I=-15:TP=-1.5[o]")
    else:
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
