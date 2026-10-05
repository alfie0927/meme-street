"""Builds the 'testers wanted' X post graphics as editable HTML files in brand/, then screenshots them."""
import asyncio, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # the project folder (this file lives in brand/)
BRAND = ROOT + "/brand"
sys.path.insert(0, ROOT + "/tests")
os.chdir(ROOT + "/tests")
from _cdp import open_page

MARK = """<svg class="mark" viewBox="0 0 100 100" aria-hidden="true">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#55a4ee"/><stop offset="1" stop-color="#3cc994"/></linearGradient></defs>
  <rect width="100" height="100" rx="22" fill="url(#g)"/>
  <path d="M23 37.5q0-2.5 2.3-2.5q1.2 0 2.2 1.4l21.8 32.4q1.4 2.2-.9 2.2H25q-2 0-2-2z" fill="#050f1d"/>
  <path d="M77 26q0-2 -1.6-2q-1.2 0-2 1.8L52.5 71.5q-1.2 2.5.9 2.5H75q2 0 2-2z" fill="#050f1d"/>
</svg>"""

CSS = """
:root{--bg:#0a0d14;--card:#111826;--line:#1f2a3d;--ink:#f3f6fa;--mut:#8ea0b8;--up:#2fd47c;--dn:#ff5f6d;--acc:#55a4ee;--teal:#3cc994}
*{box-sizing:border-box;margin:0}
html,body{width:@W@px;height:@H@px;background:var(--bg);overflow:hidden}
body{font-family:'Poppins','Segoe UI',system-ui,sans-serif;color:var(--ink);position:relative}
.bg{position:absolute;inset:0;opacity:.42}
.grid{position:absolute;inset:0;background-image:linear-gradient(#ffffff08 1px,transparent 1px),linear-gradient(90deg,#ffffff08 1px,transparent 1px);background-size:60px 60px}
.glow{position:absolute;width:900px;height:900px;border-radius:50%;filter:blur(120px);opacity:.28;pointer-events:none}
.glow.a{background:#55a4ee;left:-300px;top:-380px}.glow.b{background:#3cc994;right:-320px;bottom:-460px}
.wrap{position:absolute;inset:@PAD@px;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:16px}.mark{width:@MARK@px;height:@MARK@px}
.word{font-weight:700;font-size:@WORD@px;letter-spacing:-.01em}
h1{font-weight:800;line-height:.95;letter-spacing:-.02em;font-size:@H1@px;margin-top:@H1TOP@px}
h1 span{background:linear-gradient(90deg,#55a4ee,#3cc994);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--mut);font-weight:500;font-size:@SUB@px;margin-top:14px}
.cards{display:flex;gap:@GAP@px;margin-top:@CARDTOP@px;@CARDDIR@}
.card{flex:1;background:linear-gradient(180deg,#131c2cdd,#0e1522dd);border:1px solid var(--line);border-radius:18px;padding:@CPAD@px;backdrop-filter:blur(4px)}
.card b{display:block;font-size:@CB@px;line-height:1.05;font-weight:800;background:linear-gradient(90deg,#55a4ee,#3cc994);-webkit-background-clip:text;background-clip:text;color:transparent}
.card p{font-size:@CP@px;line-height:1.3;font-weight:500;margin-top:8px;color:#dbe4f0}
.cta{margin-top:auto;color:var(--acc);font-weight:700;font-size:@CTA@px;letter-spacing:.01em}
.tags{position:absolute;right:@PAD@px;@TAGPOS@:@PAD@px;display:flex;flex-direction:column;gap:12px;align-items:flex-end}
.tag{font-weight:700;font-size:@TAG@px;border-radius:12px;padding:8px 16px;border:1px solid;font-variant-numeric:tabular-nums}
.tag small{font-weight:600;opacity:.8;margin-right:10px;font-size:.62em;letter-spacing:.06em}
.tag.up{color:var(--up);background:#2fd47c1c;border-color:#2fd47c66;transform:rotate(-3deg)}
.tag.dn{color:var(--dn);background:#ff5f6d1c;border-color:#ff5f6d66;transform:rotate(2.5deg)}
"""

CANDLES_JS = """
(function(){var s=document.getElementById('bg'),W=@W@,H=@H@,n=@N@,x=0,step=W/n,y=H*.78,seed=7,out='';
function r(){seed=(seed*16807)%2147483647;return seed/2147483647}
for(var i=0;i<n;i++){var drift=-(H*.5)/n*1.0, move=(r()-.46)*H*.075+drift*.9, o=y, c=y+move, hi=Math.min(o,c)-r()*H*.03, lo=Math.max(o,c)+r()*H*.03;
 y=Math.max(H*.12,Math.min(H*.9,c)); var up=c<o, col=up?'#2fd47c':'#ff5f6d', cx=x+step/2, bw=step*.52;
 out+='<line x1="'+cx+'" x2="'+cx+'" y1="'+hi+'" y2="'+lo+'" stroke="'+col+'" stroke-width="2"/><rect x="'+(cx-bw/2)+'" y="'+Math.min(o,c)+'" width="'+bw+'" height="'+Math.max(4,Math.abs(c-o))+'" fill="'+col+'" rx="2"/>';x+=step}
s.innerHTML=out})();
"""

def page(w, h, wide):
    cfg = dict(W=w, H=h)
    if wide:
        cfg.update(PAD=64, MARK=72, WORD=44, H1=148, H1TOP=34, SUB=34, GAP=22, CARDTOP=38, CARDDIR="flex-direction:row", CPAD=24,
                   CB=30, CP=20, CTA=28, TAG=34, N=48, TAGPOS='bottom')
    else:
        cfg.update(PAD=64, MARK=72, WORD=44, H1=136, H1TOP=44, SUB=34, GAP=16, CARDTOP=36, CARDDIR="flex-direction:column", CPAD=20,
                   CB=30, CP=21, CTA=30, TAG=32, N=40, TAGPOS='top')
    css = CSS
    for k, v in cfg.items():
        css = css.replace(f"@{k}@", str(v))
    js = CANDLES_JS
    for k, v in cfg.items():
        js = js.replace(f"@{k}@", str(v))
    h1 = "TESTERS<br><span>WANTED</span>" if not wide else "TESTERS <span>WANTED</span>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Meme Street - testers wanted ({w}x{h})</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700;800&display=swap" rel="stylesheet">
<style>{css}</style></head><body>
<!-- Edit this file and open it in a browser at {w}x{h} to preview, then screenshot it. Note: python brand/make_x_post.py rebuilds this file from its own template and overwrites hand edits, so change the template there instead if you use the script. -->
<div class="glow a"></div><div class="glow b"></div><div class="grid"></div>
<svg id="bg" class="bg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"></svg>
<div class="tags"><div class="tag up"><small>MOON</small>&#9650; +412%</div><div class="tag dn"><small>NVXA</small>&#9660; &minus;8.7%</div></div>
<div class="wrap">
  <div class="brand">{MARK}<div class="word">Meme Street</div></div>
  <h1>{h1}</h1>
  <div class="sub">A stock market for companies that don&rsquo;t exist.</div>
  <div class="cards">
    <div class="card"><b>150+</b><p>invented companies in 30 industries</p></div>
    <div class="card"><b>Moonshots</b><p>Stocks that can 5&times; or go bust</p></div>
    <div class="card"><b>Daily contest</b><p>Everyone trades the same paper balance</p></div>
  </div>
  <div class="cta">Play money only &middot; Free &middot; Reply or DM to join</div>
</div>
<script>{js}</script>
</body></html>
"""


def screenshot_page(w, h, wide):
    html = page(w, h, wide)
    name = f"x_testers_{w}x{h}"
    with open(f"{BRAND}/{name}.html", "w", encoding="utf-8") as f:
        f.write(html)
    return name


async def shoot(name, w, h, port):
    proc, pg, _ = await open_page(width=w, height=h, debug_port=port)
    try:
        await pg.goto("file:///" + BRAND.replace("\\", "/") + f"/{name}.html", 3)
        await pg.js("document.fonts.ready.then(()=>1)")
        await asyncio.sleep(1.5)
        await pg.shot(f"{BRAND}/{name}.png")
    finally:
        proc.terminate()


async def main():
    for i, (w, h, wide) in enumerate(((1600, 900, True), (1080, 1080, False))):
        name = screenshot_page(w, h, wide)
        await shoot(name, w, h, 9371 + i)
        print("made", name)

asyncio.run(main())
