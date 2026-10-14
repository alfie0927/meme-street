"""The chart's tools, in a real browser: the indicator maths (checked against plain Python versions of the textbook
formulas), the searchable Indicators box (free indicators switch on, Pro ones say they are Pro until the admin gives
the player Pro), the floating drawing toolbar (draw, select, move and delete a trend line, the position and Fibonacci
tools, hiding drawings, dragging the toolbar), and making the chart taller and full screen."""
import asyncio
import json
import math
import unittest

from _cdp import find_browser, open_page
from _helpers import IsolatedServer
from test_browser import Driver
from test_server import http

# 40 made-up candles: a rise, a fall and a rise again, with volume
CANDLES = []
for i in range(40):
    base = 100 + 8 * math.sin(i / 5) + i * 0.3
    o, c = base, base + 1.5 * math.sin(i * 1.7)
    CANDLES.append({"t": 1000 + 60 * i, "o": round(o, 4), "c": round(c, 4), "h": round(max(o, c) + 0.8 + 0.3 * (i % 3), 4),
                    "l": round(min(o, c) - 0.7 - 0.2 * (i % 4), 4), "v": 1000 + 37 * ((i * 7) % 11)})


def sma(v, n):
    return [None if i < n - 1 else sum(v[i - n + 1:i + 1]) / n for i in range(len(v))]


def ema(v, n):
    out, e, a = [], None, 2 / (n + 1)
    for i, x in enumerate(v):
        e = x if e is None else x * a + e * (1 - a)
        out.append(e if i >= n - 1 else None)
    return out


def wma(v, n):
    return [None if i < n - 1 else sum((n - j) * v[i - j] for j in range(n)) / (n * (n + 1) / 2) for i in range(len(v))]


def rma(v, n):                      # Wilder's smoothing, started with a simple average
    out, a = [], None
    for i, x in enumerate(v):
        if i < n - 1:
            out.append(None)
        elif i == n - 1:
            a = sum(v[:n]) / n
            out.append(a)
        else:
            a = (a * (n - 1) + x) / n
            out.append(a)
    return out


def rsi(v, n):
    out, g, l = [None], 0.0, 0.0
    for i in range(1, len(v)):
        d = v[i] - v[i - 1]
        up, dn = max(d, 0), max(-d, 0)
        if i <= n:
            g += up / n
            l += dn / n
            out.append((100 - 100 / (1 + g / l) if l else 100) if i == n else None)
        else:
            g, l = (g * (n - 1) + up) / n, (l * (n - 1) + dn) / n
            out.append(100 - 100 / (1 + g / l) if l else 100)
    return out


def reference(c):
    o, h, l, cl, v = ([x[k] for x in c] for k in "ohlcv")
    n = len(c)
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - cl[i - 1]), abs(l[i] - cl[i - 1])) for i in range(1, n)]
    hh = [None if i < 4 else max(h[i - 4:i + 1]) for i in range(n)]
    ll = [None if i < 4 else min(l[i - 4:i + 1]) for i in range(n)]
    tp = [(h[i] + l[i] + cl[i]) / 3 for i in range(n)]
    tps = sma(tp, 5)
    cci = [None if tps[i] is None else (tp[i] - tps[i]) / (0.015 * (sum(abs(tp[j] - tps[i]) for j in range(i - 4, i + 1)) / 5))
           for i in range(n)]
    obv = [0.0]
    for i in range(1, n):
        obv.append(obv[-1] + (v[i] if cl[i] > cl[i - 1] else -v[i] if cl[i] < cl[i - 1] else 0))
    mfv = [((cl[i] - l[i]) - (h[i] - cl[i])) / (h[i] - l[i]) * v[i] for i in range(n)]
    cmf = [None if i < 4 else sum(mfv[i - 4:i + 1]) / sum(v[i - 4:i + 1]) for i in range(n)]
    pos = [0] + [tp[i] * v[i] if tp[i] > tp[i - 1] else 0 for i in range(1, n)]
    neg = [0] + [tp[i] * v[i] if tp[i] < tp[i - 1] else 0 for i in range(1, n)]
    mfi = [None if i < 5 else (100 - 100 / (1 + sum(pos[i - 4:i + 1]) / sum(neg[i - 4:i + 1])) if sum(neg[i - 4:i + 1]) else 100)
           for i in range(n)]
    return {"sma": sma(cl, 5), "ema": ema(cl, 5), "wma": wma(cl, 5), "rsi": rsi(cl, 5), "atr": rma(tr, 5),
            "stoch": [None if hh[i] is None else 100 * (cl[i] - ll[i]) / (hh[i] - ll[i]) for i in range(n)],
            "willr": [None if hh[i] is None else -100 * (hh[i] - cl[i]) / (hh[i] - ll[i]) for i in range(n)],
            "cci": cci, "obv": obv, "cmf": cmf, "mfi": mfi,
            "roc": [None if i < 3 else 100 * (cl[i] / cl[i - 3] - 1) for i in range(n)],
            "bbu": [None if i < 4 else sum(cl[i - 4:i + 1]) / 5 + 2 * math.sqrt(sum((x - sum(cl[i - 4:i + 1]) / 5) ** 2 for x in cl[i - 4:i + 1]) / 5) for i in range(n)]}


INDICATOR_JS = """JSON.stringify((()=>{const c=%s,C=colsOf(c);return{sma:smaOf(C.c,5),ema:emaOf(C.c,5),wma:wmaOf(C.c,5),
rsi:rsiOf(C.c,5),atr:atrSeries(C,5),stoch:stochOf(C,5,1,1).K,willr:willrOf(C,5),cci:cciOf(C,5),obv:obvOf(C),cmf:cmfOf(C,5),
mfi:mfiOf(C,5),roc:rocOf(C.c,3),bbu:bbOf(C.c,5,2).u,count:IND.length,free:IND.filter(x=>!x[4]).length}})())"""

# viewBox point of a fraction of the price area, and pointer events there (the chart maps them back to time and price)
POINTER_JS = """(()=>{const w=document.getElementById('chart-wrap'),r=w.querySelector('svg').getBoundingClientRect(),g=chartGeom;
window.__at=(fx,fy)=>({x:r.left+(g.padL+fx*g.pw)*r.width/CH.w,y:r.top+(g.padT+fy*g.PH)*r.height/CH.h});
window.__ev=(type,fx,fy,target,buttons)=>{const p=__at(fx,fy);(target||w).dispatchEvent(new PointerEvent(type,{clientX:p.x,clientY:p.y,bubbles:true,buttons:buttons||0,pointerId:7}))};
window.__pick=k=>{document.querySelector('#draw-tools [data-dt=menu]').click();document.querySelector('.dt-menu [data-tool='+k+']').click()};
return true})()"""
DRAWN = "(JSON.parse(localStorage.getItem('ms_draw')||'{}').NVXA||[])"


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class ChartToolsBrowserTests(unittest.TestCase):
    def test_indicators_drawings_and_chart_size(self):
        with IsolatedServer() as srv:
            d, errors, extra = asyncio.run(self._run(srv))
        d.verdict(self, errors)
        got, want = extra["math"], reference(CANDLES)
        self.assertEqual(got["count"], 49)
        self.assertEqual(got["free"], 17)
        for key, ref in want.items():
            for i, (a, b) in enumerate(zip(got[key], ref)):
                if b is None:
                    self.assertIsNone(a, (key, i))
                else:
                    self.assertIsNotNone(a, (key, i))
                    self.assertAlmostEqual(a, b, places=6, msg=f"{key}[{i}]")

    async def _run(self, srv):
        base = srv.url
        proc, pg, _ = await open_page(debug_port=9371)
        d = Driver(pg)
        extra = {}
        try:
            name = "Charter1"
            await pg.goto(base + "/")
            await pg.js(f"document.getElementById('nm').value='{name}'")
            await pg.js("document.getElementById('joinbtn').click()")
            await asyncio.sleep(3)
            await pg.goto(base + "/stock/NVXA", 4)
            await d.check("the chart is drawn", "!!document.querySelector('#chart-wrap svg') && !!chartGeom", True, wait=15)
            extra["math"] = json.loads(await pg.js(INDICATOR_JS % json.dumps(CANDLES)))
            # dragging the chart up and down as well as sideways
            await pg.js(POINTER_JS)
            lo0 = await pg.js("chartGeom.lo")
            await pg.js("__ev('pointerdown',.5,.5,null,1);__ev('pointermove',.5,.75,null,1);__ev('pointerup',.5,.75)")
            await d.check("dragging down moves the chart down (higher prices come into view)", f"yMan!==null&&chartGeom.lo>{lo0!r}", True, wait=3)
            await d.check("and offers Fit prices", "!document.getElementById('z-fit').hidden", True, wait=3)
            await pg.js("document.getElementById('z-fit').click()")
            await d.check("Fit prices puts the price scale back on automatic", "yMan===null&&document.getElementById('z-fit').hidden", True, wait=3)
            # dragging on the price scale stretches or squeezes the price range; a double-click there makes it automatic
            span0 = await pg.js("chartGeom.span")
            drag_axis = ("(dy=>{const w=document.getElementById('chart-wrap'),[x,y]=%s,ev=(t,d)=>w.dispatchEvent(new PointerEvent(t,{clientX:x,clientY:y+d,bubbles:true,buttons:1,pointerId:5}));"
                         "ev('pointerdown',0);ev('pointermove',dy);ev('pointerup',dy)})" % "(()=>{const w=document.getElementById('chart-wrap'),r=w.querySelector('svg').getBoundingClientRect(),g=chartGeom,x=r.left+(g.axisX+20)*r.width/CH.w,y=r.top+(g.padT+g.PH/2)*r.height/CH.h;return [x,y]})()")
            await pg.js(drag_axis + "(120)")
            await d.check("dragging the price scale down shows a wider price range", f"yMan!==null&&chartGeom.span>{span0!r}*1.5", True, wait=3)
            await pg.js(drag_axis + "(-240)")
            await d.check("and dragging it up a narrower one", f"chartGeom.span<{span0!r}", True, wait=3)
            await pg.js("(()=>{const [x,y]=(()=>{const w=document.getElementById('chart-wrap'),r=w.querySelector('svg').getBoundingClientRect(),g=chartGeom,x=r.left+(g.axisX+20)*r.width/CH.w,y=r.top+(g.padT+g.PH/2)*r.height/CH.h;return [x,y]})();document.getElementById('chart-wrap').dispatchEvent(new MouseEvent('dblclick',{clientX:x,clientY:y,bubbles:true}))})()")
            await d.check("a double-click on the price scale makes it automatic again", "yMan===null", True, wait=3)
            # the toolbar: a small bar with a drop-down, and drawing a trend line
            await d.check("the toolbar is a small bar", "(()=>{const b=document.querySelector('#draw-tools .dt-bar').getBoundingClientRect();return b.width<170&&b.height<40&&!document.querySelector('.dt-menu')})()", True, wait=5)
            await pg.js("document.querySelector('#draw-tools [data-dt=menu]').click()")
            await d.check("its drop-down lists every tool", "document.querySelectorAll('.dt-menu [data-tool]').length", 14, wait=3)
            await pg.js("document.querySelector('.dt-menu [data-tool=trend]').click()")
            await d.check("picking a tool closes the drop-down", "!document.querySelector('.dt-menu')", True, wait=3)
            await d.check("a tool turns the crosshair on", "document.getElementById('chart-wrap').classList.contains('tool')")
            await pg.js("__ev('pointerdown',.3,.3,null,1);__ev('pointermove',.6,.6,null,1);__ev('pointerup',.6,.6)")
            await d.check("a dragged trend line is saved", f"(()=>{{const l={DRAWN};return l.length===1&&l[0].type==='trend'&&l[0].pts[0].p>l[0].pts[1].p}})()", wait=3)
            await d.check("and drawn, selected with its two handles", "document.querySelectorAll('#chart-wrap [data-dw]').length+':'+document.querySelectorAll('#chart-wrap [data-dh]').length", "1:2", wait=3)
            await d.check("the tool goes back to the arrow", "tool", "cursor")
            # move it by dragging its body
            p0 = await pg.js(f"{DRAWN}[0].pts[0].p")
            await pg.js("__ev('pointerdown',.45,.45,document.querySelector('#chart-wrap [data-dw] path'),1);__ev('pointermove',.45,.25,null,1);__ev('pointerup',.45,.25)")
            await d.check("dragging a drawing moves it up", f"{DRAWN}[0].pts[0].p", lambda p: p is not None and p > p0, wait=3)
            await pg.js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true}))")
            await d.check("Delete removes the selected drawing", f"{DRAWN}.length", 0, wait=3)
            # the position tool, the Fibonacci tool and hiding
            await pg.js("__pick('long')")
            await pg.js("__ev('pointerdown',.5,.5,null,1);__ev('pointerup',.5,.5)")
            await d.check("a long position shows its target, stop and reward to risk", "document.querySelector('#chart-wrap svg').textContent",
                          lambda t: "Target" in t and "Stop" in t and "2.00R" in t and "Long from" in t, wait=3)
            await pg.js("__pick('fib')")
            await pg.js("__ev('pointerdown',.2,.8,null,1);__ev('pointermove',.7,.2,null,1);__ev('pointerup',.7,.2)")
            await d.check("the Fibonacci tool draws its levels", "document.querySelector('#chart-wrap svg').textContent",
                          lambda t: "0.618 (" in t and "0.382 (" in t, wait=3)
            await pg.js("document.querySelector('#draw-tools [data-dt=menu]').click();document.querySelector('.dt-menu [data-dt=hide]').click()")
            await d.check("drawings can be hidden", "document.querySelectorAll('#chart-wrap [data-dw]').length", 0, wait=3)
            await pg.js("document.querySelector('#draw-tools [data-dt=menu]').click();document.querySelector('.dt-menu [data-dt=hide]').click()")
            await d.check("and shown again", "document.querySelectorAll('#chart-wrap [data-dw]').length", 2, wait=3)
            # the toolbar can be dragged around
            x0 = await pg.js("document.getElementById('draw-tools').offsetLeft")
            await pg.js("(()=>{const g=document.querySelector('.dt-grip'),r=g.getBoundingClientRect(),e=(t,dx)=>g.dispatchEvent(new PointerEvent(t,{clientX:r.left+5+dx,clientY:r.top+4+dx/3,bubbles:true,pointerId:9}));e('pointerdown',0);e('pointermove',120);e('pointerup',120)})()")
            await d.check("the toolbar can be dragged and remembers where", "JSON.parse(localStorage.getItem('ms_tb')).x", lambda x: x is not None and x >= x0 + 100, wait=3)
            # the Indicators box
            await pg.js("document.getElementById('ind-open').click()")
            await d.check("the Indicators box opens", "!document.getElementById('ind-pop').hidden", wait=3)
            await pg.js("(()=>{const q=document.getElementById('ind-q');q.value='fib';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await d.check("searching finds Fibonacci and hides the rest", "document.getElementById('ind-list').innerText",
                          lambda t: "Auto Fibonacci" in t and "RSI 14" not in t, wait=3)
            await pg.js("document.querySelector('#ind-list [data-ind=autofib]').click()")
            await d.check("a free indicator switches on", "document.querySelector('#chart-wrap svg').textContent", lambda t: "61.8%" in t, wait=4)
            await pg.js("(()=>{const q=document.getElementById('ind-q');q.value='stochastic';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await pg.js("document.querySelector('#ind-list [data-ind=stoch]').click()")
            await d.check("a free oscillator gets its own panel", "document.querySelector('#chart-wrap svg').textContent", lambda t: "Stochastic" in t, wait=4)
            await pg.js("(()=>{const q=document.getElementById('ind-q');q.value='ichimoku';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await pg.js("document.querySelector('#ind-list [data-ind=ichimoku]').click()")
            await d.check("a Pro indicator says it is Pro", "document.getElementById('toast').textContent", lambda t: "Pro" in t, wait=3)
            await d.check("and stays off", "JSON.parse(localStorage.getItem('ms_ind')).includes('ichimoku')", False)
            # the admin gives the player Pro: the Pro indicators work
            status, text, _ = http(srv, "/api/admin/pro", "POST", {"name": name, "days": 30, "note": "test"}, {"X-Admin-Key": "testkey"})
            extra["grant"] = (status, text)
            await d.check("with Pro from the admin the player is Pro", "!!(S&&S.pro)", True, wait=6)
            await pg.js("document.querySelector('#ind-list [data-ind=ichimoku]').click()")
            await d.check("and a Pro indicator draws", "document.querySelector('#chart-wrap svg').textContent", lambda t: "Ichimoku" in t, wait=4)
            await pg.js("document.body.click()")
            await d.check("a click elsewhere closes the box", "document.getElementById('ind-pop').hidden", True, wait=3)
            # the chart's size
            h0 = await pg.js("document.querySelector('#chart-wrap svg').getBoundingClientRect().height")
            await pg.js("(()=>{const b=document.getElementById('chart-resize'),r=b.getBoundingClientRect(),e=(t,dy)=>b.dispatchEvent(new PointerEvent(t,{clientX:r.left+r.width/2,clientY:r.top+5+dy,bubbles:true,pointerId:11}));e('pointerdown',0);e('pointermove',150);e('pointerup',150)})()")
            await d.check("dragging the bar under the chart makes it taller", "document.querySelector('#chart-wrap svg').getBoundingClientRect().height", lambda h: h is not None and h > h0 + 40, wait=3)
            await d.check("there are no Taller or Shorter buttons", "!document.getElementById('z-taller')&&!document.getElementById('z-shorter')", True)
            await pg.js("document.getElementById('z-full').click()")
            await d.check("full screen covers the window", "(()=>{const e=document.getElementById('chart-box'),b=e.getBoundingClientRect();return [e.classList.contains('chart-full'),Math.round(b.left),Math.round(b.top),Math.round(b.width),Math.round(b.height),document.documentElement.clientWidth,innerHeight,getComputedStyle(e).position]})()",
                          lambda v: v and v[0] and v[1] == 0 and v[2] == 0 and v[3] >= v[5] - 1 and v[4] >= v[6] - 1, wait=3)
            await pg.js("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
            await d.check("Escape leaves full screen", "document.getElementById('chart-box').classList.contains('chart-full')", False, wait=3)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        self.assertEqual(extra.get("grant", (200,))[0], 200, extra.get("grant"))
        return d, errors, extra


class AdminProTests(unittest.TestCase):
    def test_the_admin_can_give_and_take_away_pro(self):
        from test_gateway import join as http_join
        with IsolatedServer() as srv:
            a = http_join(srv.url, "ProGift")
            admin = {"X-Admin-Key": "testkey"}
            self.assertEqual(http(srv, "/api/admin/pro", "POST", {"name": "ProGift", "days": 30})[0], 403)
            self.assertEqual(http(srv, "/api/admin/pro", "POST", {"name": "Nobody", "days": 30}, admin)[0], 404)
            for bad in (0, -5, 5000, float("nan")):
                self.assertEqual(http(srv, "/api/admin/pro", "POST", {"name": "ProGift", "days": bad}, admin)[0], 400, bad)
            status, text, _ = http(srv, "/api/admin/pro", "POST", {"name": "ProGift", "days": 30, "note": "a thank-you"}, admin)
            self.assertEqual(status, 200, text)
            r = json.loads(text)
            self.assertTrue(r["ok"] and r["pro"])
            me = json.loads(http(srv, "/api/shop", headers={"X-Token": a["token"]})[1])
            self.assertTrue(me["pro"])
            first = r["pro_until"]
            r = json.loads(http(srv, "/api/admin/pro", "POST", {"name": "ProGift", "days": 10}, admin)[1])
            self.assertAlmostEqual(r["pro_until"] - first, 10 * 86400, delta=5)            # more days add on
            r = json.loads(http(srv, "/api/admin/pro", "POST", {"name": "ProGift", "remove": True}, admin)[1])
            self.assertTrue(r["ok"])
            self.assertFalse(r["pro"])
            player = json.loads(http(srv, "/api/admin/player/ProGift", headers=admin)[1])
            self.assertFalse(player["pro"])
            self.assertIsNone(player["pro_until"])


if __name__ == "__main__":
    unittest.main()
