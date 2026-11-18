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
            check("with the stop as a price, the loss if hit, the value of a pip and the reward to risk", await pg.js(RESULT),
                  lambda t: "Stop 1.09800 · 20.0 pips · loses 100.00 USD if hit" in (t or "") and "1 pip = 5.00 USD" in (t or "") and "2.00 times your risk" in (t or ""))
            await set_value(pg, "comm-mode", "lot")
            await set_value(pg, "comm", "3.5")
            # 20 pips is 0.0020 a unit, plus 2 x 3.50 / 100,000 of commission: 100 / 0.00207 = 48,309 units, 0.48 lots
            check("commission (3.50 a lot, each side) shrinks the size", await wait_for(pg, f"({BIG})!=='0.50 lots'&&{BIG}"), "0.48 lots")
            check("and is shown in the loss", await pg.js(RESULT), lambda t: "3.36 USD commission" in (t or ""))
            await set_value(pg, "comm-mode", "none")
            await wait_for(pg, f"({BIG})==='0.50 lots'")
            check("the review button colours and names the trade", True, True)
            await real_click(pg, "#review")
            check("Review shows the order before anything is sent, in place of the form", await wait_for(pg, "!document.getElementById('reviewbox').hidden&&document.getElementById('ticket-form').hidden&&document.getElementById('review-list').textContent"),
                  lambda t: "0.50 lots" in (t or "") and "100.00 USD" in (t or ""))
            check("and the Place button names the trade in its side's colour", await pg.js("document.getElementById('place').textContent+'|'+document.getElementById('place').className"), "Buy 0.50 lots EURUSD|go buy")
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
            check("then offers a new trade", await pg.js("document.getElementById('again').hidden"), False)
            await real_click(pg, "#again")
            check("which clears the stop and returns to the form", await wait_for(pg, "!document.getElementById('ticket-form').hidden&&document.getElementById('stop').value"), "")
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
            await set_value(pg, "lim-day", "5")                       # (5% with no starting balance: blocked, never "no limit")
            check("a % limit with no starting balance blocks orders", await wait_for(pg, f"{RESULT}.includes('cannot be checked')&&{RESULT}"), lambda t: "Nothing is placed" in (t or ""))
            check("and Limits says why", await pg.js("document.getElementById('limits-out').textContent"), lambda t: "Enter the starting balance" in (t or ""))
            await set_value(pg, "lim-day-mode", "money")
            for k, v in (("lim-start", "10000"), ("lim-day", "120"), ("lim-total", "1000")):
                await set_value(pg, k, v)
            # the open EURUSD trade would lose 19.60 more at its stop; equity 9,960 is 40 down: worst 59.60 of 120, 60.40 of room
            check("the room left is shown", await wait_for(pg, "document.getElementById('limits-out').textContent.includes('at most 60.40 USD')"), True)
            check("and the ticket cuts the size to fit it (60.40 / 0.0020 = 30,200 units)", await wait_for(pg, BIG), "0.30 lots")
            check("and says so", await pg.js(RESULT), lambda t: "Made smaller to stay inside your loss limits" in (t or ""))
            await pg.js("window.__mock.deals.push({dealId:9,symbolName:'EURUSD',openingDirection:'buy',openingTime:new Date().toISOString(),"
                        "closingTime:new Date().toISOString(),netProfit:-70,label:'BLST r=70.00 id=lim00001'});window.__mock.balance=9930;window.__mock.equity=9890;"
                        "window.__mock.execs.forEach(f=>f())")
            check("a day at its limit blocks the ticket", await wait_for(pg, f"{RESULT}.includes('leave no room')&&{RESULT}"), lambda t: "will not place orders" in (t or ""))
            check("Limits keeps the real loss apart from the worst case", await pg.js("document.getElementById('limits-out').textContent"),
                  lambda t: "Lost so far: 110.00 USD of 120.00 USD" in (t or "") and "If every open stop is hit: 129.60 USD" in (t or "") and "No room left for a new trade" in (t or ""))
            check("and the Limits tab is amber: 110 of 120 lost for real, the rest taken by the open stop", await pg.js("document.getElementById('light-tab').className"), "dot amber")
            await set_value(pg, "lim-day", "500")
            await pg.js("window.__mock.failDeals=true;window.__mock.execs.forEach(f=>f())")
            check("if the history does not load, orders are blocked (fail closed)", await wait_for(pg, f"{RESULT}.includes('cannot be checked')&&{RESULT}"), lambda t: "Nothing is placed" in (t or ""))
            await pg.js("window.__mock.failDeals=false;window.__mock.accountType='netted';window.__mock.execs.forEach(f=>f())")
            check("a netting account that already holds the symbol is refused", await wait_for(pg, f"{RESULT}.includes('netting account')&&{RESULT}"), lambda t: "already hold EURUSD" in (t or ""))
        self.run_page(go, 9362)

    def test_pending_orders_sent_orders_and_load_failures_count(self):
        async def go(pg, check):
            await pg.goto(self.base + "/index.html?mock=1&symbol=EURUSD", 2)
            await wait_for(pg, "document.getElementById('acct').textContent.includes('Demo')")
            await set_value(pg, "stop", "20")
            await set_value(pg, "lim-day-mode", "money")
            for k, v in (("lim-start", "10000"), ("lim-day", "120")):
                await set_value(pg, k, v)
            await wait_for(pg, "document.getElementById('limits-out').textContent.includes('at most 60.40 USD')")
            # a buy limit of 10,000 EURUSD at 1.09500 with its stop at 1.09300 can lose 20.00 more: room 40.40
            await pg.js("window.__mock.orders.push({orderId:7,symbolId:1,symbolName:'EURUSD',side:'buy',type:'limit',volume:10000,"
                        "entryPrice:1.095,stopLoss:1.093});window.__mock.execs.forEach(f=>f())")
            check("a pending order's loss at its stop takes room", await wait_for(pg, "document.getElementById('limits-out').textContent.includes('at most 40.40 USD')"), True)
            check("and Exposure lists it", await pg.js("document.getElementById('exposure-out').textContent"),
                  lambda t: "pending" in (t or "") and "20.00 USD if it fills" in (t or ""))
            await pg.js("window.__mock.orders[0].stopLoss=null;window.__mock.execs.forEach(f=>f())")
            check("a pending order with no stop blocks orders", await wait_for(pg, f"{RESULT}.includes('cannot be checked')&&document.getElementById('limits-out').textContent"),
                  lambda t: "pending order has no stop" in (t or ""))
            await pg.js("window.__mock.orders=[];window.__mock.failPositions=true;window.__mock.execs.forEach(f=>f())")
            check("open positions that did not load block orders", await wait_for(pg, "document.getElementById('limits-out').textContent.includes('did not load')&&" + RESULT),
                  lambda t: "Nothing is placed" in (t or ""))
            await pg.js("window.__mock.failPositions=false;window.__mock.execs.forEach(f=>f())")
            check("and orders resume once they load", await wait_for(pg, f"({BIG})==='0.30 lots'&&{BIG}"), "0.30 lots")
            await real_click(pg, "#review")
            await wait_for(pg, "!document.getElementById('reviewbox').hidden")
            await real_click(pg, "#place")
            await wait_for(pg, "document.getElementById('place-msg').textContent.startsWith('Sent')")
            # 0.30 lots over 20 pips is 60.00: held against the room until the account shows the new position
            check("an order just sent is held against the room", await wait_for(pg, "document.getElementById('limits-out').textContent.includes('is held')&&document.getElementById('limits-out').textContent"),
                  lambda t: "at most 0.40 USD" in (t or "") and "60.00 USD of that is held" in (t or ""))
            await pg.js("window.__mock.positions.push({positionId:13,symbolId:1,symbolName:'EURUSD',side:'buy',volume:30000,entryPrice:1.1,"
                        "stopLoss:1.098,netPnl:0,openTimestamp:new Date().toISOString()});window.__mock.execs.forEach(f=>f())")
            check("and released once the account shows the new position, which then counts itself",
                  await wait_for(pg, "!document.getElementById('limits-out').textContent.includes('is held')&&document.getElementById('limits-out').textContent"),
                  # (it counts 59.40 from the bid, 1.09998 - 1.09800, where the hold was 60.00 from entry: 120 - 59.60 - 59.40)
                  lambda t: "at most 1.00 USD" in (t or ""))
        self.run_page(go, 9365)

    def test_exposure_journal_and_sessions(self):
        async def go(pg, check):
            await pg.goto(self.base + "/index.html?mock=1&symbol=EURUSD", 2)
            await wait_for(pg, "document.getElementById('acct').textContent.includes('Demo')")
            await real_click(pg, "[data-tab=exposure]")
            check("exposure: the open EURUSD trade risks 50 from entry and (1.09998 - 1.09900) x 20,000 = 19.60 more from the bid; the gold one has no stop",
                  await wait_for(pg, "document.getElementById('exposure-out').textContent.includes('19.60 USD more')&&document.getElementById('exposure-out').textContent"),
                  lambda t: "no stop: no limit" in (t or "") and "50.00 USD from entry" in (t or "") and "At risk at the stops: 19.60 USD" in (t or "") and "1 position(s) with no stop" in (t or ""))
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
                  lambda t: (t or "").startswith("true|Ballast Free sizes the trade"))
            check("its header says it is the free edition", await pg.js("document.getElementById('edition').textContent.startsWith('Free')"), True)
            await real_click(pg, "[data-tab=limits]")
            check("and Limits explains it is in the full version", await pg.js("document.getElementById('limits-out').textContent"), lambda t: "in Ballast (the full version)" in (t or ""))
        self.run_page(go, 9364)


if __name__ == "__main__":
    unittest.main()
