"""Chart basics (ROADMAP step 3): the chart set-up and drawings kept per player on the server (chartprefs.py), checked
before they are kept; one stock's trades from the history (the chart's trade markers); and, in a real browser, the chart
types and the log scale, the crosshair's readout, an indicator's settings, the channel and Fibonacci extension tools,
your trades and orders on the chart, and drawings and settings following the player to a new browser."""
import asyncio
import json
import time
import unittest

from _cdp import find_browser, open_page
from _helpers import IsolatedServer, join, make_engine
import chartprefs  # noqa: E402  (after _helpers, which puts the game on the path)
from test_browser import Driver
from test_server import Client, http

GOOD = [{"id": "abc123", "type": "trend", "pts": [{"t": 1000.0, "p": 10.5}, {"t": 1060.0, "p": 11.0}]},
        {"id": "x9", "type": "text", "pts": [{"t": 1000, "p": 9}], "text": "breakout?", "c": "#AABBCC"},
        {"id": "ch1", "type": "channel", "pts": [{"t": 1, "p": 1}, {"t": 2, "p": 2}, {"t": 3, "p": 1.5}]}]


class StoreTests(unittest.TestCase):
    def test_settings_are_checked_and_kept(self):
        prefs, err = chartprefs.clean_prefs({"ind": ["sma20", "rsi", "sma20"], "set": {"sma20": {"n": 33, "c": "#FF0000", "src": "hl2"},
                                                                                 "bb": {"n": 20, "k": 2.5}},
                                             "ctype": "ha", "log": True, "trades": False})
        self.assertIsNone(err)
        self.assertEqual(prefs["ind"], ["sma20", "rsi"])                       # duplicates dropped
        self.assertEqual(prefs["set"]["sma20"], {"n": 33, "src": "hl2", "c": "#ff0000"})
        self.assertEqual(prefs["ctype"], "ha")
        for bad in ({"ind": ["<script>"]}, {"ind": "sma20"}, {"set": {"sma20": {"n": 0}}}, {"set": {"sma20": {"n": 2.5}}},
                    {"set": {"sma20": {"n": True}}}, {"set": {"sma20": {"c": "red"}}}, {"set": {"sma20": {"src": "x"}}},
                    {"set": {"bb": {"k": float("inf")}}}, {"ctype": "pie"}, {"log": "yes"}, [], {"ind": ["a"] * 61}):
            self.assertIsNone(chartprefs.clean_prefs(bad)[0], bad)

    def test_drawings_are_checked_and_kept(self):
        clean, err = chartprefs.clean_drawings(GOOD)
        self.assertIsNone(err)
        self.assertEqual(clean[1]["c"], "#aabbcc")
        self.assertEqual(clean[0]["pts"][1], {"t": 1060.0, "p": 11.0})
        for bad in ([{"id": "a", "type": "laser", "pts": [{"t": 1, "p": 1}]}], [{"id": "A B", "type": "hline", "pts": [{"t": 1, "p": 1}]}],
                    [{"id": "a", "type": "hline", "pts": []}], [{"id": "a", "type": "hline", "pts": [{"t": 1, "p": -1}]}],
                    [{"id": "a", "type": "hline", "pts": [{"t": 1, "p": float("nan")}]}],
                    [{"id": "a", "type": "text", "pts": [{"t": 1, "p": 1}], "text": "x" * 81}],
                    [{"id": "a", "type": "hline", "pts": [{"t": 1, "p": 1}]}] * 81, {"id": "a"}):
            self.assertIsNone(chartprefs.clean_drawings(bad)[0], bad)

    def test_the_engine_keeps_them_per_player_and_stock_and_saves_them(self):
        e = make_engine(1)
        p, q = join(e, "chartist"), join(e, "other")
        self.assertTrue(e.set_chart_prefs(p, {"ind": ["ema9"], "ctype": "bars"})[0])
        self.assertTrue(e.set_drawings(p, "NVXA", GOOD)[0])
        self.assertFalse(e.set_drawings(p, "nv xa", GOOD)[0])
        self.assertEqual(e.drawings(p, "NVXA")["drawings"][2]["type"], "channel")
        self.assertEqual(e.drawings(q, "NVXA"), {"ticker": "NVXA", "drawings": [], "saved": False})
        self.assertTrue(e.set_drawings(p, "NVXA", [])[0])                      # cleared: the stock is no longer kept
        self.assertEqual(e.drawings(p, "NVXA")["saved"], False)
        e.set_drawings(p, "CLDR", GOOD)
        restored = type(p)("copy")
        chartprefs.load_player(restored, json.loads(json.dumps(chartprefs.dump_player(p))))
        self.assertEqual(restored.chart["prefs"]["ctype"], "bars")
        self.assertEqual(restored.chart["draw"]["CLDR"][0]["id"], "abc123")

    def test_only_the_newest_stocks_keep_their_drawings(self):
        e = make_engine(2)
        p = join(e, "busy")
        for i in range(chartprefs.MAX_STOCKS + 5):
            e.set_drawings(p, f"T{i}", GOOD[:1])
        self.assertEqual(len(p.chart["draw"]), chartprefs.MAX_STOCKS)
        self.assertNotIn("T0", p.chart["draw"])
        self.assertIn(f"T{chartprefs.MAX_STOCKS + 4}", p.chart["draw"])


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = IsolatedServer().__enter__()
        cls.client = Client(cls.srv, "Drawer")
        cls.tok = cls.client.token
        cls.h = {"X-Token": cls.tok}

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.srv.__exit__(None, None, None)

    def test_settings_and_drawings_round_trip(self):
        st, text, _ = http(self.srv, "/api/chart", "POST", {"ind": ["rsi"], "set": {"rsi": {"n": 7}}, "log": True}, self.h)
        self.assertEqual((st, json.loads(text)["ok"]), (200, True), text)
        st, text, _ = http(self.srv, "/api/chart", headers=self.h)
        self.assertEqual(json.loads(text)["prefs"]["set"]["rsi"], {"n": 7})
        st, text, _ = http(self.srv, "/api/drawings/nvxa", "POST", GOOD, self.h)
        self.assertTrue(json.loads(text)["ok"], text)
        st, text, _ = http(self.srv, "/api/drawings/NVXA", headers=self.h)
        self.assertEqual(len(json.loads(text)["drawings"]), 3)
        time.sleep(0.6)                                                        # (one save every half second)
        st, text, _ = http(self.srv, "/api/drawings/NVXA", "POST", [{"id": "z", "type": "nope", "pts": []}], self.h)
        self.assertFalse(json.loads(text)["ok"])
        self.assertEqual(http(self.srv, "/api/chart")[0], 401)                 # a visitor keeps nothing on the server

    def test_the_history_can_be_one_stocks(self):
        c = self.client
        c.recv_until("state")
        for tk in ("NVXA", "CLDR"):
            c.send({"type": "trade", "ticker": tk, "side": "buy", "pct": 0.1})
            self.assertTrue(c.recv_until("result")["ok"])
            time.sleep(1.2)
        st, text, _ = http(self.srv, "/api/history?ticker=NVXA&kind=buy,sell", headers=self.h)
        ev = json.loads(text)["events"]
        self.assertTrue(ev)
        self.assertTrue(all(x["ticker"] == "NVXA" for x in ev), ev)


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class ChartBrowserTests(unittest.TestCase):
    def test_types_crosshair_settings_tools_markers_and_the_saved_set_up(self):
        with IsolatedServer(settings={"require_password": True}) as srv:
            d, errors = asyncio.run(self._run(srv))
        d.verdict(self, errors)

    async def _run(self, srv):
        base = srv.url
        st, text, _ = http(srv, "/api/register", "POST", {"name": "ChartFan", "password": "a fine long password", "birth_year": 1990})
        tok = json.loads(text)["token"]
        proc, pg, _ = await open_page(debug_port=9381)
        d = Driver(pg)
        try:
            await pg.goto(base + "/", 2)
            await pg.js(f"localStorage.ms_token='{tok}'")
            await pg.goto(base + "/stock/NVXA", 4)
            await d.check("the chart is drawn", "!!document.querySelector('#chart-wrap svg') && !!chartGeom", True, wait=15)
            # chart types and the log scale
            for kind, probe in (("bars", "document.querySelectorAll('#chart-wrap svg g path[fill=none][stroke]').length>0"),
                                ("hollow", "chartType==='hollow'"), ("line", "chartType==='line'"), ("ha", "chartGeom.drawn!==chartGeom.raw")):
                await pg.js(f"(()=>{{const s=document.getElementById('c-type');s.value='{kind}';s.dispatchEvent(new Event('change'))}})()")
                await d.check(f"the chart can be drawn as {kind}", probe, True, wait=4)
            await pg.js("document.getElementById('c-log').click()")
            await d.check("the log scale is on", "chartGeom.log", True, wait=4)
            # the crosshair: a mouse over the chart shows the candle in the readout and a price on the scale
            await pg.js("(()=>{const w=document.getElementById('chart-wrap'),r=w.querySelector('svg').getBoundingClientRect(),g=chartGeom;"
                        "w.dispatchEvent(new PointerEvent('pointermove',{clientX:r.left+(g.padL+g.pw*.9)*r.width/CH.w,clientY:r.top+(g.padT+g.PH*.5)*r.height/CH.h,bubbles:true,pointerType:'mouse'}))})()")
            await d.check("the crosshair shows", "!document.getElementById('xh').hidden&&document.querySelector('.xh-p').textContent.length>0", True, wait=3)
            await d.check("the readout shows open, high, low and close", "document.getElementById('xread').innerText", lambda t: all(k in t for k in ("O ", "H ", "L ", "C ", "Vol")), wait=3)
            # an indicator's settings
            await pg.js("document.querySelector('[data-ind-cfg=sma20]').click()")
            await d.check("the settings box opens", "!document.getElementById('ind-cfg').hidden", True, wait=3)
            await pg.js("(()=>{const i=document.querySelector('#ind-cfg [data-cfg=n]');i.value='9';i.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await d.check("a new length renames it", "document.getElementById('ind-bar').innerText", lambda t: "SMA 9" in t, wait=3)
            await d.check("and the chart uses it", "document.querySelector('#chart-wrap svg').textContent", lambda t: "SMA 9" in t, wait=3)
            # the two new drawing tools
            await pg.js("""(()=>{const w=document.getElementById('chart-wrap'),r=w.querySelector('svg').getBoundingClientRect(),g=chartGeom;
              window.__ev=(t,fx,fy)=>w.dispatchEvent(new PointerEvent(t,{clientX:r.left+(g.padL+fx*g.pw)*r.width/CH.w,clientY:r.top+(g.padT+fy*g.PH)*r.height/CH.h,bubbles:true,buttons:t==='pointerup'?0:1,pointerId:3,pointerType:'mouse'}));
              window.__pick=k=>{document.querySelector('#draw-tools [data-dt=menu]').click();document.querySelector('.dt-menu [data-tool='+k+']').click()};
              window.__click=(fx,fy)=>{__ev('pointerdown',fx,fy);__ev('pointerup',fx,fy)}})()""")
            await pg.js("__pick('channel');__click(.2,.7);__click(.6,.4);__click(.4,.75)")
            await d.check("the channel tool draws two parallel lines", "drawList.length===1&&drawList[0].type==='channel'&&drawList[0].pts.length===3", True, wait=3)
            await pg.js("__pick('fibext');__click(.1,.8);__click(.4,.3);__click(.55,.6)")
            await d.check("the Fibonacci extension draws its levels", "document.querySelector('#chart-wrap svg').textContent", lambda t: "1.618 (" in t and "2.618 (" in t, wait=3)
            # your trade and your stop on the chart
            await pg.js("send({type:'trade',ticker:'NVXA',side:'buy',pct:0.2})")
            await d.check("a trade shows as an arrow", "document.querySelectorAll('#chart-wrap .trade-mark').length", lambda n: n is not None and n >= 1, wait=8)
            await pg.js("send({type:'order',action:'exit',ticker:'NVXA',kind:'stop_loss',trigger:S.byT.NVXA.price*0.98})")
            await d.check("the stop shows on the price scale", "document.querySelector('#chart-wrap svg').textContent", lambda t: "SL " in t, wait=6)
            await asyncio.sleep(2)                       # (the set-up and the drawings are sent after a short pause)
            # a new browser: the drawings and the settings come from the server
            await pg.js("localStorage.clear();localStorage.ms_token=" + json.dumps(tok))
            await pg.goto(base + "/stock/NVXA", 5)
            await d.check("in a new browser the drawings come back", "drawList.map(x=>x.type).sort().join()", "channel,fibext", wait=10)
            await d.check("and so do the settings", "[chartType,logScale,JSON.stringify(indSet.sma20||{})]", ["ha", True, '{"n":9}'], wait=6)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors


if __name__ == "__main__":
    unittest.main()
