"""The new trading tools in a real browser: the Options tab on a stock page (the chain, buying, the position, selling it
back from the holdings page), leverage on the stock page (refused without Pro, then a 5x position with its liquidation
price), and the Bots page (the Expert pitch, then a bot from a template, saved, backtested and switched on)."""
import asyncio
import json
import unittest

from _cdp import find_browser, open_page
from _helpers import IsolatedServer
from test_server import http


def grant(srv, name, tier):
    status, text, _ = http(srv, "/api/admin/pro", "POST", {"name": name, "days": 30, "tier": tier},
                           headers={"X-Admin-Key": "testkey"})
    assert status == 200 and json.loads(text)["ok"], text


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class TradingToolsBrowser(unittest.TestCase):
    def test_options_leverage_and_bots(self):
        with IsolatedServer() as srv:
            d, errors = asyncio.run(self._run(srv))
        d.verdict(self, errors)

    async def _run(self, srv):
        from test_browser import Driver
        base = srv.url
        proc, pg, _ = await open_page(debug_port=9471)
        d = Driver(pg)
        try:
            await pg.goto(base + "/")
            await pg.js("document.getElementById('nm').value='toolsy';document.getElementById('joinbtn').click()")
            await asyncio.sleep(3)
            # options
            await pg.goto(base + "/stock/NVXA", 4)
            await pg.js("document.querySelector('[data-dtab=options]').click()")
            await d.check("the Options tab shows the chain", "document.querySelectorAll('.opt-chain tbody tr').length", lambda n: n == 13, wait=8)
            await d.check("and hides the chart", "getComputedStyle(document.getElementById('chart-box')).display", "none")
            await d.check("the quotes change with the stock", "(async()=>{const a=()=>[...document.querySelectorAll('.opt-chain .c-ask button')].map(b=>b.textContent).join();const x=a();await new Promise(r=>setTimeout(r,6000));return x!==a()})()", True, wait=10)
            await pg.js("document.querySelectorAll('.opt-chain .c-bid')[12].click()")       # a far-out call: one contract is affordable
            await d.check("clicking a contract shows all its Greeks", "document.getElementById('opt-ticket').innerText",
                          lambda t: all(g in t for g in ("Delta", "Gamma", "Theta", "Vega", "Rho")) and "A contract" in t, wait=3)
            await pg.js("document.getElementById('opt-n').value='1';document.getElementById('opt-go').click()")
            await d.check("buying it adds an option position", "(S.opts||[]).length", 1, wait=6)
            await d.check("which is listed under the chain", "document.getElementById('opt-mine').innerText", lambda t: "NVXA" in t and "call" in t, wait=4)
            await pg.goto(base + "/holdings", 4)
            await d.check("the holdings page lists it", "document.getElementById('hold-opts').innerText", lambda t: "call" in t, wait=6)
            await pg.js("document.querySelector('[data-opt-sell][data-f=\"1\"]').click()")
            await d.check("and sells it back", "(S.opts||[]).length", 0, wait=6)
            # leverage
            await pg.goto(base + "/stock/NVXA", 4)
            await pg.js("document.getElementById('d-lev').value='5';document.getElementById('d-buy').click()")
            await d.check("leverage without Pro is refused", "document.getElementById('toast').innerText", lambda t: "Pro" in t, wait=3)
            await d.check("and nothing was bought", "S.holdings.length", 0)
            grant(srv, "toolsy", "pro")
            await asyncio.sleep(2)
            await pg.js("document.getElementById('d-lev').value='5';document.getElementById('d-buy').click()")
            await d.check("with Pro a 5x position opens", "(S.holdings.find(h=>h.ticker==='NVXA')||{}).lev", 5, wait=6)
            await d.check("the position line shows the leverage and where it closes", "document.getElementById('d-pos').innerText",
                          lambda t: "Leverage" in t and "5x" in t and "Closes by itself" in t, wait=4)
            # bots
            await pg.goto(base + "/bots", 4)
            await d.check("without Expert the Bots page explains Expert", "document.getElementById('bots-body').innerText", lambda t: "Expert" in t, wait=6)
            grant(srv, "toolsy", "expert")
            await pg.goto(base + "/bots", 4)
            await d.check("with Expert there is a New bot button", "!!document.getElementById('bot-new')", True, wait=6)
            await pg.js("document.querySelector('[data-bot-tpl=ema]').click()")
            await d.check("a template fills the editor", "document.querySelectorAll('#be-rules tr').length", 2, wait=3)
            await pg.js("document.getElementById('be-tk').value='NVXA';document.getElementById('be-save').click()")
            await d.check("saving lists the bot", "document.querySelectorAll('.bot-card').length", 1, wait=6)
            await pg.js("document.querySelector('[data-bot-edit]').click()")
            await pg.js("document.getElementById('bt-tf').value='1m';document.getElementById('bt-bars').value='300';document.getElementById('bt-go').click()")
            await d.check("a backtest reports its return and the stock's", "document.getElementById('bt-out').innerText",
                          lambda t: "Return" in t and "Just holding" in t or "Not enough candles" in t, wait=15)
            await pg.js("document.getElementById('be-cancel').click()")
            await asyncio.sleep(1.5)
            await pg.js("document.querySelector('[data-bot-toggle]').click()")
            await d.check("the bot switches on", "document.querySelector('[data-bot-toggle]').innerText", "Switch off", wait=6)
            return d, pg.errors
        finally:
            proc.terminate()


if __name__ == "__main__":
    unittest.main()
