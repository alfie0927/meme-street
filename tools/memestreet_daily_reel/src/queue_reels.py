"""Load a folder of made reels into the posting queue, each with a thumbnail.
Usage: python3 src/queue_reels.py <folder with schedule.json> [ORIGINAL_UTC=NEW_UTC ...]
  e.g. 2026-11-03T1200=2026-11-04T0000 moves one post. Already-queued posts are left as they are.
"""
import asyncio, datetime, html, json, os, shutil, subprocess, sys
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); QUEUE = os.path.join(HERE, "..", "queue")
LOGO = "file://" + os.path.join(HERE, "..", "assets", "logo.png")

COVER = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:1080px;height:1920px;overflow:hidden;background:#07090c;font-family:'Cascadia Mono',monospace;color:#e6e9ec}
.hdr{position:absolute;left:70px;right:70px;top:300px;display:flex;align-items:center;justify-content:space-between}
.hdr .l{display:flex;align-items:center;gap:22px;font:700 50px/1 'Cascadia Mono'}.hdr img{width:96px;height:96px;border-radius:20px}
.tag{padding:16px 28px;border-radius:999px;background:#4fc6c8;color:#07121a;font:700 30px/1 'Cascadia Mono';letter-spacing:1px;text-transform:uppercase}
.shot{position:absolute;left:62px;right:62px;top:450px;height:820px;border-radius:26px;border:3px solid #23272d;background:#0b0f13 center/cover no-repeat;overflow:hidden}
.shot:after{content:'';position:absolute;inset:0;background:linear-gradient(#07090c 0,#07090c00 16%,#07090c00 84%,#07090c 100%)}
.title{position:absolute;left:60px;right:60px;top:1340px;text-align:center;font:800 96px/1.1 'Cascadia Mono';letter-spacing:-2px}
.url{position:absolute;left:0;right:0;top:1700px;text-align:center;font:700 40px/1 'Cascadia Mono';color:#8b96a3}
</style></head><body>
<div class="hdr"><div class="l"><img src="LOGO">Meme Street</div><div class="tag">TAG</div></div>
<div class="shot" style="background-image:url('SHOT')"></div><div class="title" id="t">TITLE</div><div class="url">memestreet.net</div>
<script>const t=document.getElementById('t');let s=96;while(t.scrollHeight>330&&s>48){s-=4;t.style.fontSize=s+'px'}</script></body></html>"""

def utc_key(iso):
    t = datetime.datetime.fromisoformat(iso).astimezone(datetime.timezone.utc)
    return t.strftime("%Y-%m-%dT%H%M")

async def covers(jobs):
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        for e, d in jobs:
            shot = os.path.join(d, "frame.jpg")
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(d, "reel.mp4")],
                                       capture_output=True, text=True).stdout or 10)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(dur * 0.4), "-i", os.path.join(d, "reel.mp4"), "-frames:v", "1", "-q:v", "3", shot], check=True)
            page = COVER.replace("LOGO", LOGO).replace("SHOT", "file://" + os.path.abspath(shot)).replace(
                "TAG", html.escape(e.get("type", ""))).replace("TITLE", html.escape(e.get("title", "")))
            f = os.path.join(d, "cover.html"); open(f, "w").write(page)
            await pg.goto("file://" + os.path.abspath(f)); await pg.evaluate("document.fonts.ready")
            await pg.screenshot(path=os.path.join(d, "cover.jpg"), type="jpeg", quality=92)
            os.remove(f); os.remove(shot)
        await b.close()

def main(src, moves):
    jobs = []
    for e in json.load(open(os.path.join(src, "schedule.json"))):
        key = utc_key(e["post_at"]); key = moves.get(key, key)
        d = os.path.join(QUEUE, ".staging", key)               # (moved into the queue once complete)
        if os.path.exists(os.path.join(QUEUE, key)) or e.get("ready") != "yes":
            print("skip", key, e["video"], "(queued already)" if e.get("ready") == "yes" else "(not ready)"); continue
        os.makedirs(d, exist_ok=True)
        shutil.copy(os.path.join(src, e["video"]), os.path.join(d, "reel.mp4"))
        shutil.copy(os.path.join(src, e["caption_file"]), os.path.join(d, "caption.txt"))
        jobs.append((e, d))
    asyncio.run(covers(jobs))
    for e, d in jobs:
        os.rename(d, os.path.join(QUEUE, os.path.basename(d)))
        print("queued", os.path.basename(d), e["video"])

if __name__ == "__main__":
    main(sys.argv[1], dict(a.split("=") for a in sys.argv[2:]))
