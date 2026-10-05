"""Rebuilds the X post graphics in this folder (run from the project folder: python brand/make_x_screenshot.py). It needs Edge or Chrome."""
import asyncio, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # the project folder (this file lives in brand/)
BRAND = ROOT + "/brand"
sys.path.insert(0, ROOT + "/tests")
os.chdir(ROOT + "/tests")
from _cdp import open_page
from _helpers import IsolatedServer


async def main(base):
    proc, pg, _ = await open_page(width=1600, height=900, debug_port=9381)
    try:
        await pg.goto(base + "/", 3)
        await pg.js("(()=>{document.getElementById('nm').value='tester'+Math.floor(Math.random()*900+100);document.getElementById('joinbtn').click()})()")
        await asyncio.sleep(6)
        await pg.shot(BRAND + "/market_page_screenshot.png")
    finally:
        proc.terminate()

with IsolatedServer(settings={"signup_bonus": 10000}) as srv:
    asyncio.run(main(srv.url))

html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Meme Street - now testing (1600x900)</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&display=swap" rel="stylesheet">
<style>
html,body{margin:0;width:1600px;height:900px;overflow:hidden;background:#0a0d14;font-family:'Poppins','Segoe UI',sans-serif}
img{position:absolute;inset:0;width:1600px;height:900px}
.shade{position:absolute;inset:0;background:linear-gradient(180deg,#0a0d1400 40%,#0a0d14f2 100%)}
.label{position:absolute;left:48px;bottom:44px;display:flex;align-items:center;gap:18px}
.pill{background:linear-gradient(90deg,#55a4ee,#3cc994);color:#050f1d;font-weight:800;font-size:34px;letter-spacing:.06em;padding:10px 26px;border-radius:14px;box-shadow:0 8px 30px #0008}
.txt{color:#f3f6fa;font-weight:700;font-size:34px;text-shadow:0 2px 14px #000c}
.txt small{display:block;color:#55a4ee;font-size:24px;font-weight:700;margin-top:2px}
</style></head><body>
<!-- Edit the words below. The picture is market_page_screenshot.png in this folder. -->
<img src="market_page_screenshot.png" alt="Meme Street market page">
<div class="shade"></div>
<div class="label"><div class="pill">NOW TESTING</div><div class="txt">Meme Street<small>Play money only &middot; Free &middot; Reply or DM to join</small></div></div>
</body></html>
"""
with open(BRAND + "/x_now_testing_1600x900.html", "w", encoding="utf-8") as f:
    f.write(html)


async def shoot():
    proc, pg, _ = await open_page(width=1600, height=900, debug_port=9382)
    try:
        await pg.goto("file:///" + BRAND + "/x_now_testing_1600x900.html", 3)
        await asyncio.sleep(1.5)
        await pg.shot(BRAND + "/x_now_testing_1600x900.png")
    finally:
        proc.terminate()

asyncio.run(shoot())
print("done")
