"""Draw chosen moments of a one-shot reel as stills (the look test, and the frame sheets the checks read).
  python3 src/oneshot/shot.py <timeline.json> <outdir> <t> [<t> ...]
Writes <outdir>/t<sec>.jpg and prints the seconds each frame took."""
import asyncio, json, os, sys, time
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = ["--allow-file-access-from-files", "--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


async def main(tl, out, ts):
    R = json.load(open(tl)); os.makedirs(out, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=ARGS); pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        pg.set_default_timeout(300000); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        await pg.add_init_script(f"window.__R={json.dumps(R)};")
        await pg.goto(f"file://{HERE}/oneshot.html"); t0 = time.time()
        try: await pg.evaluate("window.ready")
        except Exception as e: raise SystemExit(f"load failed: {e}; {errs[:3]}")
        print(f"loaded in {time.time() - t0:.1f}s")
        for t in ts:
            t0 = time.time(); await pg.evaluate("t=>render(t)", t)
            await pg.screenshot(path=os.path.join(out, f"t{t:05.2f}.jpg"), type="jpeg", quality=88)
            print(f"t={t}: {time.time() - t0:.2f}s")
        await b.close()
        if errs: print("errors:", errs[:5])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3:]]))
