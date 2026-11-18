"""Ballast (tradertools/ballast): the trader's toolkit for cTrader, against its stand-in for cTrader (?mock=1), in a real
browser. The maths has its own tests (`node --test` in that folder); this checks the page: the size shown, the review
step, one order per real click, the loss limits cutting the size and then blocking, failing closed when the history
does not load, netting accounts, the other four tabs, settings kept per account, and the trial edition."""
import asyncio
import functools
import http.server
import os
import threading
import time
import unittest

from _cdp import find_browser, open_page

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tradertools", "ballast", "site")


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


async def set_value(pg, element_id, value):
    await pg.js(f"(()=>{{const e=document.getElementById('{element_id}');e.value='{value}';e.dispatchEvent(new Event('input'));e.dispatchEvent(new Event('change'))}})()")


RESULT = "document.getElementById('result').textContent"
BIG = "(document.querySelector('#result .big')||{}).textContent"


class Checks:
    def __init__(self):
        self.items = {}

    def __call__(self, name, got, want):
        self.items[name] = ((want(got) if callable(want) else got == want), got)


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class BallastPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = serve()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def run_page(self, fn, port):
        checks, errors = asyncio.run(self._run(fn, port))
        self.assertEqual(errors, [], "JavaScript errors on the page")
        for name, (ok, got) in checks.items.items():
            self.assertTrue(ok, f"{name} -> {got}")

    async def _run(self, fn, port):
        proc, pg, _ = await open_page(width=420, height=1200, debug_port=port)
        check = Checks()
        try:
            await fn(pg, check)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return check, errors

    def test_ticket_sizes_reviews_and_sends_once(self):
        async def go(pg, check):
            await pg.goto(self.base + "/index.html?mock=1&symbol=EURUSD", 2)
            check("the account shows as a demo", await wait_for(pg, "document.getElementById('acct').textContent.includes('10,000.00')&&document.getElementById('acct').textContent"),
                  lambda t: (t or "").startswith("Demo"))
            await set_value(pg, "stop", "20")
            await set_value(pg, "target", "2")
            check("1% of 10,000 over 20 pips is 0.50 lots", await wait_for(pg, BIG), "0.50 lots")
            check("with the loss at the stop and the reward to risk", await pg.js(RESULT), lambda t: "Loses 100.00 USD at the stop" in (t or "") and "2.00 times the risk" in (t or ""))
            await set_value(pg, "comm-mode", "lot")
            await set_value(pg, "comm", "3.5")
            # 20 pips is 0.0020 a unit, plus 2 x 3.50 / 100,000 of commission: 100 / 0.00207 = 48,309 units, 0.48 lots
            check("commission (3.50 a lot, each side) shrinks the size", await wait_for(pg, f"({BIG})!=='0.50 lots'&&{BIG}"), "0.48 lots")
            check("and is shown in the loss", await pg.js(RESULT), lambda t: "commission)" in (t or ""))
            await set_value(pg, "comm-mode", "none")
            await wait_for(pg, f"({BIG})==='0.50 lots'")
            await real_click(pg, "#review")
            check("Review shows the order before anything is sent", await wait_for(pg, "!document.getElementById('reviewbox').hidden&&document.getElementById('review-list').textContent"),
                  lambda t: "0.50 lots" in (t or "") and "100.00 USD" in (t or ""))
            await pg.js("document.getElementById('place').click()")             # a script's click is not the user's
            await asyncio.sleep(0.4)
            check("a scripted click sends nothing", await pg.js("window.__mock.sent.length"), 0)
            await real_click(pg, "#place")
            await real_click(pg, "#place")                                       # a double tap
            await wait_for(pg, "document.getElementById('place-msg').textContent.startsWith('Sent')")
            check("a real click sends exactly one order", await pg.js("window.__mock.sent.length"), 1)
            check("with the stop triggered on the closing price and the trade's id in the label",
                  await pg.js("(()=>{const r=window.__mock.sent[0];return [r.volume,r.stopLossPips,r.takeProfitPips,r.stopLossTriggerMethod,/^BLST r=100\\.00 id=[a-z0-9]{8}$/.test(r.label)].join('|')})()"),
                  "50000|20|40|trade|true")
            await real_click(pg, "#back")
            await set_value(pg, "stop", "0.5")
            check("a stop inside the spread is refused", await wait_for(pg, f"{RESULT}.includes('too close')&&{RESULT}"), lambda t: "at least 1 pip beyond the bid" in (t or ""))
            await set_value(pg, "stop", "20")
            await pg.goto(self.base + "/index.html?mock=1&symbol=EURUSD", 2)
            check("settings are kept for the account", await wait_for(pg, "document.getElementById('target').value===''&&document.getElementById('comm-mode').value"), "none")
        self.run_page(go, 9361)

    def test_limits_cut_the_size_then_block_and_fail_closed(self):
        async def go(pg, check):
            await pg.goto(self.base + "/index.html?mock=1&symbol=EURUSD", 2)
            await wait_for(pg, "document.getElementById('acct').textContent.includes('Demo')")
            await set_value(pg, "stop", "20")
            for k, v in (("lim-start", "10000"), ("lim-day", "120"), ("lim-total", "1000")):
                await set_value(pg, k, v)
            # the open EURUSD trade risks 50 at its stop (the gold one has no stop): 50 of 120 used, 70 of room
            check("the room left is shown", await wait_for(pg, "document.getElementById('limits-out').textContent.includes('at most 70.00')"), True)
            check("and the ticket cuts the size to fit it", await wait_for(pg, BIG), "0.35 lots")
            check("and says so", await pg.js(RESULT), lambda t: "Cut to fit your loss limits" in (t or ""))
            await pg.js("window.__mock.deals.push({dealId:9,symbolName:'EURUSD',openingDirection:'buy',openingTime:new Date().toISOString(),"
                        "closingTime:new Date().toISOString(),netProfit:-70,label:'BLST r=70.00 id=lim00001'});window.__mock.balance=9930;window.__mock.equity=9890;"
                        "window.__mock.execs.forEach(f=>f())")
            check("a day at its limit blocks the ticket", await wait_for(pg, f"{RESULT}.includes('no room left')&&{RESULT}"), lambda t: "will not place orders" in (t or ""))
            check("and the Limits tab is red", await pg.js("document.getElementById('light-tab').className"), "dot red")
            await set_value(pg, "lim-day", "500")
            await pg.js("window.__mock.failDeals=true;window.__mock.execs.forEach(f=>f())")
            check("if the history does not load, orders are blocked (fail closed)", await wait_for(pg, f"{RESULT}.includes('could not be checked')&&{RESULT}"), lambda t: "Nothing is placed" in (t or ""))
            await pg.js("window.__mock.failDeals=false;window.__mock.accountType='netted';window.__mock.execs.forEach(f=>f())")
            check("a netting account that already holds the symbol is refused", await wait_for(pg, f"{RESULT}.includes('netting account')&&{RESULT}"), lambda t: "already hold EURUSD" in (t or ""))
        self.run_page(go, 9362)

    def test_exposure_journal_and_sessions(self):
        async def go(pg, check):
            await pg.goto(self.base + "/index.html?mock=1&symbol=EURUSD", 2)
            await wait_for(pg, "document.getElementById('acct').textContent.includes('Demo')")
            await real_click(pg, "[data-tab=exposure]")
            check("exposure: the open EURUSD trade risks 50 at its stop, the gold one has none",
                  await wait_for(pg, "document.getElementById('exposure-out').textContent.includes('50.00 USD')&&document.getElementById('exposure-out').textContent"),
                  lambda t: "no stop: no limit" in (t or "") and "At risk at the stops: 50.00 USD" in (t or ""))
            await real_click(pg, "[data-tab=journal]")
            check("journal: a position closed in two parts is one trade; three trades, average 0.84 R",
                  await wait_for(pg, "document.getElementById('journal-sum').textContent"), lambda t: "3" in (t or "") and "0.84 R per trade" in (t or "") and "3.63" in (t or ""))
            check("journal by symbol", await pg.js("document.querySelectorAll('#journal-sym tbody tr').length"), 3)
            await real_click(pg, "[data-tab=sessions]")
            check("sessions: four cities, each open or closed", await pg.js("document.querySelectorAll('#sessions-out .row').length"), 4)
            check("the tab stays on show", await pg.js("document.getElementById('tab-sessions').hidden"), False)
        self.run_page(go, 9363)

    def test_the_trial_sizes_but_has_no_place_button(self):
        async def go(pg, check):
            await pg.goto(self.base + "/trial/index.html?mock=1&symbol=USDJPY", 2)
            await wait_for(pg, "document.getElementById('acct').textContent.includes('Demo')")
            await set_value(pg, "stop", "30")
            # 1% of 10,000 over 30 yen pips: the yen are valued at 1/bid (149.998), so 0.50 lots would risk a few cents
            # over 100 and the size rounds down
            check("the trial sizes the trade, rounding down", await wait_for(pg, BIG), "0.49 lots")
            await real_click(pg, "#review")
            check("but shows no Place button, and says why",
                  await wait_for(pg, "!document.getElementById('reviewbox').hidden&&[document.getElementById('place').hidden,document.getElementById('review-note').textContent].join('|')"),
                  lambda t: (t or "").startswith("true|The trial sizes"))
            check("its footer says it is the trial", await pg.js("document.getElementById('edition').textContent.startsWith('Trial')"), True)
        self.run_page(go, 9364)


if __name__ == "__main__":
    unittest.main()
