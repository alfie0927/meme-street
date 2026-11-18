"""Exact Risk Ticket (tradertools/ctrader-risk): the panel against its stand-in for cTrader (?mock=1), in a real
browser. The maths has its own tests (`node --test` in that folder); this checks the page: the size shown, the review
step, that an order goes out once and only from a real click, the loss limit's lock, and the trial's missing button."""
import asyncio
import functools
import http.server
import os
import threading
import time
import unittest

from _cdp import find_browser, open_page

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tradertools", "ctrader-risk", "site")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class _Server(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass                                   # (the browser is killed at the end of a test, mid-connection)


def serve():
    srv = _Server(("127.0.0.1", 0), functools.partial(_Quiet, directory=SITE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


async def wait_for(pg, expr, wait=8.0):
    end = time.time() + wait
    while True:
        value = await pg.js(expr)
        if value or time.time() > end:
            return value
        await asyncio.sleep(0.25)


async def real_click(pg, selector):
    """A click the page sees as the user's own (isTrusted), through the browser's input, not element.click()."""
    box = await pg.js(f"(()=>{{const r=document.querySelector('{selector}').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()")
    for kind in ("mousePressed", "mouseReleased"):
        await pg.cmd("Input.dispatchMouseEvent", type=kind, x=box[0], y=box[1], button="left", clickCount=1)


async def type_into(pg, element_id, value):
    await pg.js(f"(()=>{{const e=document.getElementById('{element_id}');e.value='{value}';e.dispatchEvent(new Event('input'));e.dispatchEvent(new Event('change'))}})()")


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class RiskTicketPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = serve()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_the_full_panel_sizes_reviews_and_sends_once_and_the_limit_locks_it(self):
        checks, errors = asyncio.run(self._full())
        self.assertEqual(errors, [], "JavaScript errors on the page")
        for name, (ok, got) in checks.items():
            self.assertTrue(ok, f"{name} -> {got}")

    async def _full(self):
        proc, pg, _ = await open_page(width=480, height=1100, debug_port=9361)
        checks = {}

        def check(name, got, want):
            checks[name] = ((want(got) if callable(want) else got == want), got)
        try:
            await pg.goto(self.base + "/index.html?mock=1&symbol=EURUSD", 1.5)
            check("the account shows as a demo with its balance", await wait_for(pg, "document.getElementById('acct').textContent.includes('10,000.00')&&document.getElementById('acct').textContent"),
                  lambda t: (t or "").startswith("Demo"))
            await type_into(pg, "stop", "20")                                   # 20 pips, target 2 x risk, 1% (the defaults)
            await type_into(pg, "target", "2")
            check("1% of 10,000 over 20 pips is 0.50 lots", await wait_for(pg, "document.querySelector('#result .big')&&document.querySelector('#result .big').textContent"), "0.50 lots")
            check("with the target's reward to risk", await pg.js("document.getElementById('result').textContent"), lambda t: "2.00 times the risk" in (t or ""))
            await real_click(pg, "#review")
            check("Review shows the order before anything is sent", await wait_for(pg, "!document.getElementById('reviewbox').hidden&&document.getElementById('review-list').textContent"),
                  lambda t: "0.50 lots" in (t or "") and "100.00 USD" in (t or ""))
            check("nothing has been sent by reviewing", await pg.js("window.__mock.sent.length"), 0)
            await pg.js("document.getElementById('place').click()")             # a script's click is not the user's
            await asyncio.sleep(0.5)
            check("a scripted click sends nothing", await pg.js("window.__mock.sent.length"), 0)
            await real_click(pg, "#place")
            await real_click(pg, "#place")                                       # a double tap
            await wait_for(pg, "document.getElementById('place-msg').textContent.startsWith('Sent')")
            check("a real click sends exactly one order, double tap or not", await pg.js("window.__mock.sent.length"), 1)
            check("the order carries the size, the stop and target in pips and the planned risk",
                  await pg.js("JSON.stringify(window.__mock.sent[0])"),
                  '{"symbolId":1,"orderType":"market","side":"buy","volume":50000,"label":"ERT r=100.00","stopLossPips":20,"takeProfitPips":40}')
            check("and says it was sent", await pg.js("document.getElementById('place-msg').textContent"), lambda t: (t or "").startswith("Sent. cTrader order #"))
            await real_click(pg, "#back")
            await type_into(pg, "lim-day", "100")
            await pg.js("window.__mock.deals.push({dealId:9,symbolName:'EURUSD',openingDirection:'buy',openingTime:new Date().toISOString(),"
                        "closingTime:new Date().toISOString(),netProfit:-100,label:'ERT r=100.00'});window.__mock.execs.forEach(f=>f())")
            check("a day's loss at the limit turns the light red", await wait_for(pg, "document.getElementById('light-day').className.includes('red')&&document.getElementById('light-day').className"), "light red")
            check("and the panel refuses to build an order", await pg.js("document.getElementById('result').textContent"), lambda t: "loss limit for today is reached" in (t or ""))
            check("the review button is off", await pg.js("document.getElementById('review').disabled"), True)
            check("the log shows the closed trade at -1 R", await wait_for(pg, "document.getElementById('log').textContent"), lambda t: "-1.00 R" in (t or ""))
            await type_into(pg, "lim-day", "")
            await pg.js("document.getElementById('sym').value='BTCUSD';document.getElementById('sym').dispatchEvent(new Event('change'))")
            await type_into(pg, "risk-mode", "money")
            await type_into(pg, "risk", "1")
            await type_into(pg, "stop", "1200")
            check("when the smallest size risks too much, it says so and sizes nothing",
                  await wait_for(pg, "(document.getElementById('result').textContent.includes('Nothing is placed')||'')&&document.getElementById('result').textContent"),
                  lambda t: "Nothing is placed" in (t or ""))
            await pg.goto(self.base + "/index.html?mock=1&symbol=EURUSD", 1.5)
            check("settings are remembered", await wait_for(pg, "document.getElementById('risk-mode').value"), "money")
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return checks, errors

    def test_the_trial_sizes_but_has_no_place_button(self):
        checks, errors = asyncio.run(self._trial())
        self.assertEqual(errors, [], "JavaScript errors on the page")
        for name, (ok, got) in checks.items():
            self.assertTrue(ok, f"{name} -> {got}")

    async def _trial(self):
        proc, pg, _ = await open_page(width=480, height=1000, debug_port=9362)
        checks = {}
        try:
            await pg.goto(self.base + "/trial/index.html?mock=1&symbol=USDJPY", 1.5)
            await wait_for(pg, "document.getElementById('acct').textContent.includes('Demo')")
            await type_into(pg, "stop", "30")
            got = await wait_for(pg, "document.querySelector('#result .big')&&document.querySelector('#result .big').textContent")
            # 1% of 10,000 over 30 pips: the yen are turned into dollars at 1/bid (149.998), the side that makes the risk
            # larger, so 0.50 lots would risk a few cents over 100 and the size rounds down to 0.49
            checks["the trial sizes the trade, rounding down"] = (got == "0.49 lots", got)
            await real_click(pg, "#review")
            got = await wait_for(pg, "!document.getElementById('reviewbox').hidden&&[document.getElementById('place').hidden,document.getElementById('review-note').textContent].join('|')")
            checks["but shows no Place button, and says why"] = ((got or "").startswith("true|The trial calculates"), got)
            checks["and the footer says it is the trial"] = (await pg.js("document.getElementById('edition').textContent.startsWith('Trial')"), None)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return checks, errors


if __name__ == "__main__":
    unittest.main()
