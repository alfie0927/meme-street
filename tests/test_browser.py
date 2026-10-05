"""Browser smoke test: drives the real page in headless Edge/Chrome through the DevTools protocol.

Skipped automatically when no Edge or Chrome is installed. Checks that the page loads without JavaScript
errors, that buttons survive the once-a-second re-render, and that the main flows work: the amount box,
shorting and covering, the holdings page, the limits line and quarterly earnings headlines.
"""
import asyncio
import os
import random
import tempfile
import time
import unittest
from unittest import mock

from _cdp import find_browser, open_page
from _helpers import IsolatedServer, advance, engine


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class BrowserSmoke(unittest.TestCase):
    def test_main_flows(self):
        # a 0.01-game-day quarter (18 s) so the first earnings headlines appear during the test
        with IsolatedServer(settings={"earnings_quarter_days": 0.01}) as srv:
            result = asyncio.run(self._flows(srv.url))
        self.assertEqual(result["errors"], [], "JavaScript errors on the page")
        for name, ok in result["checks"].items():
            self.assertTrue(ok, f"check failed: {name} -> {result['detail'].get(name)}")

    async def _flows(self, base):
        proc, pg, _ = await open_page()
        checks, detail = {}, {}

        async def check(name, expr, expect=True, wait=0.0):
            """Evaluate the expression; with `wait`, keep polling for up to that many seconds until it passes."""
            end = time.time() + wait
            while True:
                value = await pg.js(expr)
                passed = (value == expect) if not callable(expect) else bool(expect(value))
                if passed or time.time() >= end:
                    break
                await asyncio.sleep(0.5)
            detail[name] = value
            checks[name] = passed

        try:
            await pg.goto(base + "/")
            await pg.js("document.getElementById('nm').value='smoke'+Math.floor(Math.random()*9999)")
            await pg.js("document.getElementById('joinbtn').click()")
            await asyncio.sleep(3)
            await check("market table has rows", "document.querySelectorAll('#rows tr').length", lambda n: n > 30)
            await check("no mood element in the header", "!!document.getElementById('mood')", False)
            await check("the market tab's leaderboard has no Score column",
                        "[...document.querySelectorAll('#board th')].map(t=>t.textContent).join('|')", "#|Trader|Return", wait=8)
            await check("the company name sits next to the ticker on the same line",
                        "(()=>{const t=document.querySelector('#rows tr[data-k=NVXA] .tick-main'),k=t.querySelector('.tk'),n=t.querySelector('.nm');return [k.textContent,n.textContent.length,Math.abs(k.getBoundingClientRect().top-n.getBoundingClientRect().top)<8]})()",
                        lambda v: v[0] == "NVXA" and v[1] > 3 and v[2] is True)
            await check("the main page has no company descriptions",
                        "document.querySelectorAll('#rows .company-desc, #rows .company-cell').length", 0)
            await check("the main page has no volatility tag", "document.body.innerText.toUpperCase().includes('VOLATILE')", False)
            await check("sell button says Short with no position",
                        "document.querySelector('#rows tr[data-k=NVXA] .sell').textContent", "Short")
            # rows and buttons are the same elements after several re-renders (clicks are never lost)
            await check("buttons persist across re-renders", """(async()=>{const a=document.querySelector('#rows tr[data-k=NVXA] button');
                await new Promise(r=>setTimeout(r,2500));return a===document.querySelector('#rows tr[data-k=NVXA] button')})()""")
            # typed amount, short
            await pg.js("(()=>{const i=document.querySelector('.amt-input');i.value='150';i.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await pg.js("document.querySelector('#rows tr[data-k=NVXA] button[data-act=sell]').click()")
            await asyncio.sleep(1.5)
            await check("short opened with the typed amount", "document.getElementById('toast').textContent",
                        lambda t: t.startswith("Shorted") and "collateral" in t)
            await check("held cell shows the short", "document.querySelector('#rows tr[data-k=NVXA] .held').textContent",
                        lambda t: "(short)" in t)
            await check("buy button becomes Cover", "document.querySelector('#rows tr[data-k=NVXA] .buy').textContent", "Cover")
            await pg.js("document.querySelector('[data-chip=b][data-v=\"0.5\"]').click()")
            await check("a chip clears the amount box", "document.querySelector('.amt-input').value", "")
            await pg.js("(()=>{const i=document.querySelector('.amt-input');i.value='60';i.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await pg.js("document.querySelector('#rows tr[data-k=GOLD] button[data-act=buy]').click()")
            await asyncio.sleep(1.5)
            await check("typed buy", "document.getElementById('toast').textContent",
                        lambda t: t.startswith("Bought") and "60.00 MB" in t)
            # holdings page
            await pg.goto(base + "/holdings", 3)
            await check("holdings page lists the short and the long",
                        "[...document.querySelectorAll('#hold-rows tr')].map(r=>r.innerText.replace(/\\s+/g,' ')).join('|')",
                        lambda t: "SHORT" in t and "NVXA" in t and "GOLD" in t and "Long" in t)
            # buying and selling straight from the holdings page
            await pg.js("(()=>{const i=document.querySelector('#holdings-card .amt-input');i.value='25';i.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await pg.js("document.querySelector('#hold-rows tr[data-k=GOLD] button[data-act=buy]').click()")
            await asyncio.sleep(1.5)
            await check("buy more from the holdings page", "document.getElementById('toast').textContent",
                        lambda t: t.startswith("Bought") and "25.00 MB" in t)
            await asyncio.sleep(1.2)
            await pg.js("document.querySelector('#hold-rows tr[data-k=GOLD] button[data-act=sell]').click()")
            await asyncio.sleep(1.5)
            await check("sell from the holdings page", "document.getElementById('toast').textContent",
                        lambda t: t.startswith("Sold") and "25.00 MB" in t)
            await check("the holdings buttons say Cover and Short for a short",
                        "document.querySelector('#hold-rows tr[data-k=NVXA] .buy').textContent+'/'+document.querySelector('#hold-rows tr[data-k=NVXA] .sell').textContent",
                        "Cover/Short")
            # stock page
            await pg.goto(base + "/stock/NVXA", 4)
            await check("stock buttons are Cover and Short",
                        "document.getElementById('d-buy').textContent+'/'+document.getElementById('d-sell').textContent", "Cover/Short")
            await check("position box says short", "document.getElementById('d-pos').innerText",
                        lambda t: "short" in t.lower() and "Average entry price" in t)
            await check("the costs line is shown (and there is no position limit)", "document.getElementById('d-limits').textContent",
                        lambda t: "borrow fee" in t and "Position limit" not in t, wait=10)
            await check("chart is drawn with the average line",
                        "!!document.querySelector('#chart-wrap svg') && !!document.querySelector('line[stroke-dasharray=\"2 4\"]')",
                        wait=10)
            for period in ("1m", "5m", "1d", "30s"):
                await pg.js(f"document.querySelector('.periods button[data-p=\"{period}\"]').click()")
                await asyncio.sleep(0.8)
            for _ in range(6):
                await pg.js("document.getElementById('z-out').click()")
            await check("chart survives zooming out far past the data", "!!document.querySelector('#chart-wrap svg')",
                        wait=10)
            await pg.js("document.getElementById('d-buy').click()")
            await asyncio.sleep(1.5)
            await check("cover works", "document.getElementById('toast').textContent", lambda t: t.startswith("Covered"))
            # quarterly earnings (an 18-second quarter in this test) show up on the news wire
            await pg.goto(base + "/", 21)
            await check("an earnings headline appeared", "document.getElementById('news').innerText",
                        lambda t: "EARNINGS:" in t)
            # the admin dashboard: locked until the key is entered, then cards, charts and a player's trades
            await pg.goto(base + "/admin", 1.5)
            await check("admin page is locked first", "document.getElementById('app').style.display", "none")
            await pg.js("document.getElementById('key').value='wrong-key'")
            await pg.js("document.getElementById('go').click()")
            await check("a wrong key is refused", "document.getElementById('err').textContent",
                        lambda t: "not accepted" in t, wait=8)
            await pg.js("document.getElementById('key').value='testkey'")
            await pg.js("document.getElementById('go').click()")
            await check("admin cards render", "document.querySelectorAll('#cards .card').length", lambda n: n >= 9, wait=10)
            await check("alerts line is shown", "document.getElementById('alerts').innerText", lambda t: len(t) > 10)
            await check("charts are drawn after a few samples", "document.querySelectorAll('#ch1 svg, #ch2 svg').length",
                        lambda n: n >= 1, wait=25)
            await check("the smoke player is listed with a trade count",
                        "document.getElementById('winners').innerText", lambda t: "smoke" in t, wait=10)
            await pg.js("document.querySelector('#winners tr[data-n]').click()")
            await check("player detail shows the trade log", "document.getElementById('detail').innerText.toLowerCase()",
                        lambda t: "trades (newest first)" in t and "short" in t, wait=8)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return {"checks": checks, "errors": errors, "detail": detail}


class Driver:
    """A page plus the `check` helper, so each browser test reads as a list of checks."""

    def __init__(self, pg):
        self.pg, self.checks, self.detail = pg, {}, {}

    async def check(self, name, expr, expect=True, wait=0.0):
        end = time.time() + wait
        while True:
            value = await self.pg.js(expr)
            passed = (value == expect) if not callable(expect) else bool(expect(value))
            if passed or time.time() >= end:
                break
            await asyncio.sleep(0.5)
        self.detail[name] = value
        self.checks[name] = passed

    async def join(self, base, prefix):
        await self.pg.goto(base + "/")
        await self.pg.js(f"document.getElementById('nm').value='{prefix}'+Math.floor(Math.random()*9999)")
        await self.pg.js("document.getElementById('joinbtn').click()")
        await asyncio.sleep(3)

    def verdict(self, test, errors):
        test.assertEqual(errors, [], "JavaScript errors on the page")
        for name, ok in self.checks.items():
            test.assertTrue(ok, f"check failed: {name} -> {self.detail.get(name)}")


VISIBLE_ROWS = "[...document.querySelectorAll('#rows tr')].filter(r=>r.style.display!=='none')"


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class BrowserPages(unittest.TestCase):
    """The market table's search, sort and watchlist, and the portfolio, history, leaders, profile, social and
    player pages, driven in a real browser."""

    def test_market_search_sort_and_watchlist(self):
        with IsolatedServer() as srv:
            d, errors = asyncio.run(self._market(srv.url))
        d.verdict(self, errors)

    async def _market(self, base):
        proc, pg, _ = await open_page(debug_port=9334)
        d = Driver(pg)
        try:
            await d.join(base, "mkt")
            await d.check("table is full", "document.querySelectorAll('#rows tr').length", lambda n: n > 100)
            await d.check("the 2x and 3x products sit at the bottom of the table",
                          "[...document.querySelectorAll('#rows tr')].slice(-4).map(r=>r.dataset.k).sort().join()", "2LMSI,2SMSI,3LMSI,3SMSI", wait=8)
            await d.check("only the first row of industries is shown",
                          "document.getElementById('secs').getBoundingClientRect().height", lambda h: 20 < h < 45)
            await d.check("the toggle is there and folded",
                          "document.getElementById('secs-toggle').getAttribute('aria-expanded')+'|'+document.getElementById('secs-toggle').textContent",
                          lambda t: t.startswith("false|") and "industries" in t)
            await pg.js("document.getElementById('secs-toggle').click()")
            await d.check("the arrow reveals every industry",
                          "document.getElementById('secs').getBoundingClientRect().height", lambda h: h > 90)
            await d.check("and offers to show less", "document.getElementById('secs-toggle').textContent", lambda t: "less" in t)
            await pg.js("document.getElementById('secs-toggle').click()")
            await d.check("it folds up again", "document.getElementById('secs').getBoundingClientRect().height", lambda h: h < 45)
            await pg.js("document.querySelector('#secs [data-sec=creatures]').click()")
            await d.check("an industry picked from the hidden rows stays visible while folded",
                          "(()=>{const s=document.getElementById('secs').getBoundingClientRect(),c=document.querySelector('#secs .chip.on:not([data-sec=all])').getBoundingClientRect();return c.top-s.top<40&&c.bottom<=s.bottom+2})()")
            await d.check("the fictional industry lists its companies",
                          VISIBLE_ROWS + ".map(r=>r.dataset.k).join()", lambda t: "EMBR" in t and "NVXA" not in t)
            await pg.js("document.querySelector('#secs [data-sec=all]').click()")
            await d.check("count line shows all", "document.getElementById('count').textContent",
                          lambda t: t.endswith(" shown") and t.split(" of ")[0] == t.split(" of ")[1].split(" ")[0])
            await pg.js("(()=>{const q=document.getElementById('q');q.value='nvx';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await d.check("search narrows the table", VISIBLE_ROWS + ".map(r=>r.dataset.k).join()",
                          lambda t: "NVXA" in t and t.count(",") < 5)
            await pg.js("(()=>{const q=document.getElementById('q');q.value='zzzzqqq';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await d.check("no-match message", "getComputedStyle(document.getElementById('no-match')).display", "block")
            await pg.js("(()=>{const q=document.getElementById('q');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await pg.js("document.querySelector('#market-card th[data-sort=price]').click()")
            await asyncio.sleep(1.2)
            await d.check("sorted by price descending",
                          "(()=>{const v=" + VISIBLE_ROWS + ".filter(r=>!/^\d[LS]MSI$/.test(r.dataset.k)).map(r=>parseFloat(r.querySelector('.px').textContent.replace(/,/g,'')));"
                          "let ok=v.length>50;for(let i=1;i<v.length;i++)if(v[i]>v[i-1]*1.2+0.5)ok=false;return ok})()")
            await d.check("header shows the sort arrow", "document.querySelector('#market-card th[data-sort=price]').className",
                          lambda t: "sorted" in t and "desc" in t)
            await pg.js("document.querySelector('#market-card th[data-sort=ticker]').click()")
            await asyncio.sleep(1.2)
            await d.check("sorted by ticker",
                          "(()=>{const v=" + VISIBLE_ROWS + ".map(r=>r.dataset.k).filter(k=>!/^\d[LS]MSI$/.test(k));return v.length>50&&v.every((x,i)=>i===0||v[i-1]<=x)})()")
            await pg.js("document.querySelector('#secs [data-sec=index]').click()")
            await d.check("index chip shows only indices and ETFs", VISIBLE_ROWS + ".map(r=>r.dataset.k).join()",
                          lambda t: "MSI" in t and "2LMSI" in t and "3SMSI" in t and "BEAR1" not in t and "NVXA" not in t)
            await pg.js("document.querySelector('#secs [data-sec=all]').click()")
            await pg.js("document.querySelector('#rows tr[data-k=NVXA] [data-star]').click()")
            await pg.js("document.querySelector('#rows tr[data-k=GOLD] [data-star]').click()")
            await d.check("stars are filled", "document.querySelector('#rows tr[data-k=NVXA] .star').textContent", "★")
            await pg.js("document.querySelector('#secs [data-sec=watch]').click()")
            await d.check("watchlist filter shows only the two", VISIBLE_ROWS + ".map(r=>r.dataset.k).sort().join()", "GOLD,NVXA")
            await pg.goto(base + "/", 3)
            await d.check("watchlist and filter persist across a reload", VISIBLE_ROWS + ".map(r=>r.dataset.k).sort().join()",
                          "GOLD,NVXA", wait=8)
            await pg.js("document.querySelector('#secs [data-sec=watch]').click()")
            await pg.js("document.querySelector('#rows tr[data-k=NVXA] [data-star]').click()")
            await d.check("a star can be removed", "document.querySelector('#rows tr[data-k=NVXA] .star').textContent", "☆")
            await d.check("market is open and the banner hidden",
                          "getComputedStyle(document.getElementById('session-banner')).display+'|'+document.getElementById('mkt').textContent",
                          lambda t: t.startswith("none|Market open"))
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors

    def test_premarket_and_afterhours_are_shown_and_trading_still_works(self):
        # almost-always pre-market, almost-always after-hours, and the real 5 / 20 / 5 minute cycle
        for pre, post, name, word, port in ((1790, 0, "pre", "Pre-market", 9335), (0, 1790, "post", "After-hours", 9338),
                                            (300, 300, "real", None, 9341)):
            with IsolatedServer(settings={"premarket_seconds": pre, "aftermarket_seconds": post}) as srv:
                d, errors = asyncio.run(self._session(srv.url, name, word, port, pre, post))
            d.verdict(self, errors)

    async def _session(self, base, name, word, port, pre, post):
        proc, pg, _ = await open_page(debug_port=port)
        d = Driver(pg)
        try:
            await d.join(base, name)
            if word:
                # (the engine always leaves one minute of regular session in the cycle, so a run that lands in
                # that minute legitimately sees "Market open")
                await d.check("the status chip names the session", "document.getElementById('mkt').textContent",
                              lambda t: t.startswith((word, "Market open")), wait=10)
                chip = await pg.js("document.getElementById('mkt').textContent")
                if chip.startswith(word):
                    await d.check("the banner explains thin trading",
                                  "getComputedStyle(document.getElementById('session-banner')).display+'|'+document.getElementById('session-banner').textContent",
                                  lambda t: t.startswith("block|") and "thin" in t)
            else:
                await d.check("the chip names one of the three sessions", "document.getElementById('mkt').textContent",
                              lambda t: t.startswith(("Pre-market", "Market open", "After-hours")), wait=10)
            await d.check("there is no activity chart in the header", "!document.getElementById('cycle')&&!document.getElementById('bars')")
            await d.check("the chip explains the cycle in local time", "document.getElementById('mkt').title",
                          lambda t: "Pre-market" in t and "Market open" in t and "After-hours" in t)
            await d.check("buttons are not disabled in extended hours",
                          "[...document.querySelectorAll('#rows tr')].slice(0,5).every(r=>!r.querySelector('.buy').disabled&&!r.querySelector('.sell').disabled)")
            await pg.js("document.querySelector('#rows tr[data-k=GOLD] button[data-act=buy]').click()")
            await asyncio.sleep(1.5)
            await d.check("a trade goes through", "document.getElementById('toast').textContent", lambda t: t.startswith("Bought"))
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors

    def test_portfolio_history_leaders_profile_social_player(self):
        with IsolatedServer() as srv:
            d, errors = asyncio.run(self._pages(srv.url))
        d.verdict(self, errors)

    async def _pages(self, base):
        proc, pg, _ = await open_page(debug_port=9336)
        d = Driver(pg)
        try:
            await d.join(base, "pages")
            await pg.js("document.querySelector('#rows tr[data-k=GOLD] button[data-act=buy]').click()")
            await asyncio.sleep(2.5)
            await pg.js("document.querySelector('#rows tr[data-k=NVXA] button[data-act=sell]').click()")
            await asyncio.sleep(1.5)
            await d.check("an achievement notice appears in the corner", "document.getElementById('notes').innerText",
                          lambda t: "First steps" in t or "Achievement" in t, wait=4)
            # portfolio
            await pg.goto(base + "/portfolio", 3)
            await d.check("portfolio summary", "document.getElementById('pf-sum').innerText",
                          lambda t: "Equity" in t and "Realised profit" in t and "Fees paid" in t, wait=10)
            await d.check("portfolio lists the long and the short", "document.getElementById('pf-pos').innerText",
                          lambda t: "GOLD" in t and "NVXA" in t and "SHORT" in t, wait=8)
            await d.check("allocation bar has cash and positions", "document.querySelectorAll('#pf-alloc .alloc i').length",
                          lambda n: n >= 2)
            await d.check("equity curve area is filled", "document.getElementById('pf-curve').innerHTML.length", lambda n: n > 20)
            await d.check("portfolio is the only visible card",
                          "[...document.querySelectorAll('section>.card')].filter(c=>getComputedStyle(c).display!=='none').map(c=>c.id).join()",
                          "portfolio-card")
            # history
            await pg.goto(base + "/history", 3)
            await d.check("history lists the trades", "document.getElementById('hist-rows').innerText",
                          lambda t: "Buy" in t and "Short" in t and "GOLD" in t, wait=10)
            await d.check("history has a deposit row", "document.getElementById('hist-rows').innerText", lambda t: "Deposit" in t)
            await pg.js("document.querySelector('#hist-filters [data-k=\"buy,cover\"]').click()")
            await d.check("filter keeps only buys and covers",
                          "[...document.querySelectorAll('#hist-rows tr')].every(r=>/Buy|Cover/.test(r.cells[1].textContent))&&document.querySelectorAll('#hist-rows tr').length>0",
                          wait=6)
            await pg.js("window.__blob=null;URL.createObjectURL=b=>{window.__blob=b;return 'blob:test'}")
            await pg.js("document.getElementById('hist-csv').click()")
            await d.check("CSV download produces a file",
                          "(async()=>{for(let i=0;i<20&&!window.__blob;i++)await new Promise(r=>setTimeout(r,200));return window.__blob?(await window.__blob.text()).split('\\n')[0]:''})()",
                          lambda t: t.startswith("time_utc,type,ticker"))
            # leaders
            await pg.goto(base + "/leaders", 3)
            await d.check("the day board lists me (I have traded today)", "document.getElementById('board-table').innerText",
                          lambda t: "pages" in t, wait=10)
            await d.check("and says where I am", "document.getElementById('board-me').innerText",
                          lambda t: "You are #" in t and "on this board" in t, wait=8)
            await d.check("there is no risk-adjusted board", "document.querySelectorAll('#board-tabs [data-b=risk]').length", 0)
            await d.check("the board tabs are Day return and All-time P&L", "document.querySelectorAll('#board-tabs .chip').length", 2)
            await pg.js("document.querySelector('#board-tabs [data-b=pnl]').click()")
            await d.check("all-time board", "document.getElementById('board-table').innerText", lambda t: "profit" in t.lower())
            await d.check("my row is highlighted", "document.querySelectorAll('#board-table tr.me').length", 1)
            # profile
            await pg.goto(base + "/profile", 3)
            await d.check("three quests", "document.querySelectorAll('#quests .quest').length", 3, wait=10)
            await d.check("achievement grid is full", "document.querySelectorAll('#achs .ach').length", lambda n: n >= 20)
            await d.check("first steps is unlocked", "document.querySelectorAll('#achs .ach:not(.locked)').length", lambda n: n >= 1)
            await d.check("the daily contest is listed", "document.getElementById('tours').innerText",
                          lambda t: "Daily Marathon" in t and "Hourly Sprint" not in t and "paper money" in t)
            await d.check("the paper trading panel is hidden until I join", "document.getElementById('contest-play').style.display", "none")
            await pg.js("document.querySelector('#tours [data-join]').click()")
            await d.check("joining shows my rank", "document.getElementById('tours').innerText",
                          lambda t: "rank 1 of 1" in t, wait=10)
            await d.check("the paper panel opens with the full balance", "document.getElementById('cp-summary').innerText",
                          lambda t: "10,000.00" in t, wait=10)
            await pg.js("(()=>{const s=document.getElementById('cp-ticker');s.value='GOLD';document.getElementById('cp-pct').value='0.5';document.getElementById('cp-buy').click()})()")
            await d.check("a paper buy shows as a paper position", "document.getElementById('cp-pos').innerText",
                          lambda t: "GOLD" in t, wait=10)
            await asyncio.sleep(1.4)                                   # (one second between trades in the same stock)
            await pg.js("document.querySelector('#cp-pos [data-cclose]').click()")
            await d.check("closing the paper position empties the table", "document.getElementById('cp-pos').innerText",
                          lambda t: "No paper positions yet" in t, wait=10)
            await pg.js("(()=>{const c=document.getElementById('pub-toggle');c.checked=true;c.dispatchEvent(new Event('change',{bubbles:true}))})()")
            await asyncio.sleep(1.5)
            await pg.goto(base + "/profile", 3)
            await d.check("public setting is remembered by the server", "document.getElementById('pub-toggle').checked", True, wait=8)
            # social: chat, following
            await pg.goto(base + "/social", 3)
            await pg.js("(()=>{const i=document.getElementById('chat-in');i.value='hello from the browser test';document.getElementById('chat-send').click()})()")
            await d.check("my chat message appears", "document.getElementById('chat-log').innerText",
                          lambda t: "hello from the browser test" in t, wait=8)
            await d.check("there are no clubs on the social page", "!document.getElementById('tab-clubs')&&!document.querySelector('#soc-tabs [data-tab=clubs]')")
            await pg.js("document.querySelector('#soc-tabs [data-tab=follow]').click()")
            await pg.js("(()=>{document.getElementById('follow-name').value='nobody_here';document.getElementById('follow-add').click()})()")
            await asyncio.sleep(1.5)
            await d.check("following nobody shows a message", "document.getElementById('toast').textContent",
                          lambda t: "No such player" in t)
            # another player's page, here my own
            await pg.goto(base + "/leaders", 3)
            await d.check("my name is a link", "!!document.querySelector('#board-table tr.me a')", wait=8)
            await pg.js("document.querySelector('#board-table tr.me a').click()")
            await asyncio.sleep(3)
            await d.check("player page shows who it is", "document.getElementById('player-body').innerText",
                          lambda t: "This is you" in t and "Day return" in t, wait=8)
            await d.check("player page shows achievements", "document.getElementById('player-body').innerText",
                          lambda t: "achievements" in t.lower() and "First steps" in t)
            await pg.goto(base + "/player/nobody_at_all", 3)
            await d.check("unknown player is handled", "document.getElementById('player-body').innerText",
                          lambda t: "No trader" in t, wait=8)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors

    def test_a_delisted_stock_can_still_be_opened_and_the_history_has_no_fees_tab(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(5)
            e = engine.Engine(state_file=path)
            advance(e, 150)                                    # some candles to show
            s = e.stocks["OILX"]
            s.fair = s.initial_price * 0.1
            with mock.patch.object(random, "random", return_value=0.0):
                e._check_distress()
            self.assertIn("OILX", e.archive)
            e.save()
            with IsolatedServer(state_file=path) as srv:
                d, errors = asyncio.run(self._delisted(srv.url))
            d.verdict(self, errors)

    async def _delisted(self, base):
        proc, pg, _ = await open_page(debug_port=9347)
        d = Driver(pg)
        try:
            await d.join(base, "ghost")
            await pg.goto(base + "/stock/OILX", 3)
            await d.check("the page says it is delisted", "document.getElementById('d-badges').textContent",
                          lambda t: "DELISTED" in t, wait=10)
            await d.check("it names the company", "document.getElementById('d-name').textContent",
                          lambda t: "Ostrava Oil" in t, wait=5)
            await d.check("it explains the bankruptcy", "document.getElementById('d-note').textContent",
                          lambda t: "bankrupt" in t, wait=5)
            await d.check("the chart is drawn from the saved candles", "document.getElementById('chart-info').textContent",
                          lambda t: "candles" in t and not t.startswith("0 candles"), wait=8)
            await d.check("there is a chart", "document.querySelectorAll('#chart-wrap svg rect, #chart-wrap svg line').length", lambda n: n > 5)
            await d.check("there are no trade buttons", "getComputedStyle(document.querySelector('.detail-actions')).display", "none")
            await d.check("its facts and news are shown", "document.getElementById('d-facts').textContent.includes('Last price')&&document.getElementById('d-log').textContent.includes('bankruptcy')")
            await pg.goto(base + "/stock/NOSUCH", 3)
            await d.check("a stock that never existed says so", "document.getElementById('detail-content').innerText",
                          lambda t: "not currently traded" in t, wait=8)
            await pg.goto(base + "/history", 3)
            await d.check("the history filters have no fees tab", "document.getElementById('hist-filters').innerText",
                          lambda t: "Dividends" in t and "fee" not in t.lower() and "Trades" in t, wait=8)
            await pg.goto(base + "/stock/BULL2", 3)
            await d.check("an old product link goes to the renamed product", "location.pathname", "/stock/2LMSI", wait=8)
            await d.check("and that page is the 2x long product", "document.getElementById('d-name').textContent",
                          lambda t: "2x Long MSI" in t, wait=8)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors

    def test_orders_can_be_placed_listed_bracketed_and_cancelled_from_the_page(self):
        with IsolatedServer() as srv:
            d, errors = asyncio.run(self._orders(srv.url))
        d.verdict(self, errors)

    async def _orders(self, base):
        proc, pg, _ = await open_page(debug_port=9349)
        d = Driver(pg)
        try:
            await d.join(base, "orderer")
            await pg.goto(base + "/stock/GOLD", 3)
            await d.check("the order panel is on the stock page", "!!document.getElementById('d-orders')", wait=10)
            await d.check("stops are not offered without a position", "document.querySelector('#o-kind option[value=stop_loss]').disabled")
            await pg.js("document.getElementById('d-orders').open=true")
            await pg.js("(()=>{const p=S.byT.GOLD.price;document.getElementById('o-kind').value='limit_buy';document.getElementById('o-trigger').value=(p*0.9).toFixed(4);document.getElementById('o-place').click()})()")
            await d.check("the order is listed", "document.querySelectorAll('#o-list tbody tr').length", 1, wait=8)
            await d.check("it says what it waits for", "document.getElementById('o-list').innerText", lambda t: "Limit buy" in t and "at or below" in t)
            await d.check("a toast confirms it", "document.getElementById('toast').textContent", lambda t: "placed" in t, wait=3)
            await pg.js("(()=>{document.getElementById('o-kind').value='limit_buy';document.getElementById('o-trigger').value='999999';document.getElementById('o-place').click()})()")
            await asyncio.sleep(1.2)
            await d.check("an order that would trigger now is refused", "document.getElementById('toast').textContent", lambda t: "fall" in t or "lower" in t)
            await pg.goto(base + "/holdings", 3)
            await d.check("the holdings page lists open orders", "document.getElementById('hold-orders').innerText", lambda t: "open orders" in t.lower() and "GOLD" in t and "Limit buy" in t, wait=8)
            await pg.goto(base + "/stock/GOLD", 3)
            await pg.js("document.getElementById('d-orders').open=true")
            await pg.js("document.getElementById('d-buy').click()")
            await asyncio.sleep(2)
            await d.check("with a position the stop-loss is offered", "!document.querySelector('#o-kind option[value=stop_loss]').disabled", wait=8)
            await pg.js("(()=>{const p=S.byT.GOLD.price;document.getElementById('b-tp').value=(p*1.1).toFixed(4);document.getElementById('b-sl').value=(p*0.9).toFixed(4);document.getElementById('b-place').click()})()")
            await d.check("a bracket adds two orders", "document.querySelectorAll('#o-list tbody tr').length", 3, wait=8)
            await pg.js("document.querySelector('#o-list [data-cancel]').click()")           # the limit buy, placed first
            await d.check("cancelling an order removes it", "document.querySelectorAll('#o-list tbody tr').length", 2, wait=8)
            await pg.js("document.querySelector('#o-list [data-cancel]').click()")           # one leg of the bracket
            await d.check("cancelling a bracket leg removes the pair", "document.getElementById('o-list').innerText", lambda t: "No open orders" in t, wait=8)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors

    def test_reconnect_resyncs_the_page(self):
        with IsolatedServer() as srv:
            d, errors = asyncio.run(self._reconnect(srv.url))
        d.verdict(self, errors)

    async def _reconnect(self, base):
        proc, pg, _ = await open_page(debug_port=9337)
        d = Driver(pg)
        try:
            await d.join(base, "recon")
            await d.check("prices are flowing", "document.querySelector('#rows tr[data-k=NVXA] .px').textContent", lambda t: len(t) > 3)
            await pg.js("ws.close()")
            await d.check("it recovers and keeps updating",
                          "(async()=>{await new Promise(r=>setTimeout(r,3000));const a=document.getElementById('cash').textContent;return a.endsWith('MB')&&document.getElementById('conn').textContent===''})()",
                          wait=15)
            await pg.js("syncAt=0;requestSync()")
            await d.check("a sync request gives a fresh init",
                          "(async()=>{await new Promise(r=>setTimeout(r,1500));return S&&S.stocks.length>100&&S.seq>0})()")
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors

    def test_sign_in_with_a_password_register_log_out_log_in_and_change_it(self):
        with IsolatedServer(settings={"require_password": True}) as srv:
            d, errors = asyncio.run(self._passwords(srv.url))
        d.verdict(self, errors)

    async def _passwords(self, base):
        proc, pg, _ = await open_page(debug_port=9351)
        d = Driver(pg)
        name = "pw" + str(random.randint(1000, 9999))
        fill = ("(()=>{const set=(i,v)=>{document.getElementById(i).value=v};set('nm','%s');set('pw','%s');set('pw2','%s')})()")
        try:
            await pg.goto(base + "/", 3)
            await d.check("the box offers Log in and Create account", "document.getElementById('auth-tabs').style.display", "block", wait=8)
            await d.check("a first visit opens on Create account",
                          "document.querySelector('#auth-tabs .on').dataset.mode", "register")
            await pg.js(fill % (name, "correct-horse-battery", "something-else-entirely"))
            await pg.js("document.getElementById('joinbtn').click()")
            await d.check("mismatched passwords are caught on the page", "document.getElementById('lerr').textContent",
                          lambda t: "not the same" in t, wait=5)
            await pg.js(fill % (name, "short", "short"))
            await pg.js("document.getElementById('joinbtn').click()")
            await d.check("a weak password is refused by the server", "document.getElementById('lerr').textContent",
                          lambda t: "at least 8" in t, wait=8)
            await pg.js(fill % (name, "correct-horse-battery", "correct-horse-battery"))
            await pg.js("document.getElementById('joinbtn').click()")
            await d.check("registering enters the market", "document.getElementById('login').style.display", "none", wait=10)
            await d.check("the page is live", "document.querySelectorAll('#rows tr').length", lambda n: n > 100, wait=10)
            await pg.goto(base + "/profile", 3)
            await d.check("the profile says the account is protected", "document.getElementById('acct-note').innerText",
                          lambda t: "protected by a password" in t, wait=10)
            await pg.js("document.getElementById('acct-out').click()")
            await asyncio.sleep(2.5)
            await d.check("logging out shows the sign-in box again", "document.getElementById('login').style.display", "flex", wait=8)
            await d.check("and forgets the token", "localStorage.getItem('ms_token')", None)
            await d.check("a returning visitor opens on Log in", "document.querySelector('#auth-tabs .on').dataset.mode", "login")
            await pg.js("document.querySelector('#auth-tabs [data-mode=login]').click()")
            await pg.js(fill % (name, "wrong-password-1", ""))
            await pg.js("document.getElementById('joinbtn').click()")
            await d.check("a wrong password is refused", "document.getElementById('lerr').textContent",
                          lambda t: "Wrong name or password" in t, wait=8)
            await pg.js(fill % (name, "correct-horse-battery", ""))
            await pg.js("document.getElementById('joinbtn').click()")
            await d.check("the right password logs in", "document.getElementById('login').style.display", "none", wait=10)
            await pg.goto(base + "/profile", 3)
            await d.check("the current-password box shows once there is a password", "document.getElementById('acct-cur').style.display",
                          "inline-block", wait=10)
            await pg.js("(()=>{document.getElementById('acct-cur').value='correct-horse-battery';document.getElementById('acct-new').value='a-different-secret-1';document.getElementById('acct-save').click()})()")
            await d.check("changing the password is confirmed", "document.getElementById('toast').textContent",
                          lambda t: "Password saved" in t, wait=10)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors

    def test_email_sign_up_verify_and_recover_a_forgotten_password(self):
        with IsolatedServer(settings={"require_password": True, "email_mode": "required", "signups_per_ip_hour": 100}) as srv:
            d, errors = asyncio.run(self._email(srv.url))
        d.verdict(self, errors)

    @staticmethod
    def _latest_code(base, to):
        import json as _json
        import re as _re
        import urllib.request as _rq
        req = _rq.Request(base + "/api/admin/mail", headers={"X-Admin-Key": "testkey"})
        with _rq.urlopen(req, timeout=10) as r:
            for row in _json.loads(r.read())["recent"]:
                if row["to"] == to:
                    return _re.search(r"\n\s+([0-9A-Z]{6,8})\n", row["body"]).group(1)
        return ""

    async def _email(self, base):
        proc, pg, _ = await open_page(debug_port=9352)
        d = Driver(pg)
        name = "em" + str(random.randint(1000, 9999))
        addr = name + "@example.com"
        fill = ("(()=>{const set=(i,v)=>{document.getElementById(i).value=v};set('nm','%s');set('pw','%s');set('pw2','%s');set('em','%s')})()")
        try:
            await pg.goto(base + "/", 3)
            await d.check("the sign-up form asks for an email address", "document.getElementById('em').style.display", "block", wait=8)
            await d.check("and says it is needed", "document.getElementById('em').placeholder", lambda t: "needed" in t)
            await pg.js(fill % (name, "correct-horse-battery", "correct-horse-battery", "not-an-address"))
            await pg.js("document.getElementById('joinbtn').click()")
            await d.check("a bad address is refused", "document.getElementById('lerr').textContent",
                          lambda t: "email" in t.lower(), wait=8)
            await pg.js(fill % (name, "correct-horse-battery", "correct-horse-battery", addr))
            await pg.js("document.getElementById('joinbtn').click()")
            await d.check("registering takes you to the code box on the profile page", "location.pathname + location.hash",
                          "/profile#verify", wait=12)
            await d.check("the page says it is waiting for the code", "document.getElementById('email-note').innerText",
                          lambda t: "Waiting for the code" in t, wait=10)
            await d.check("the code box is showing", "document.getElementById('email-code-bar').style.display", "flex")
            code = self._latest_code(base, addr)
            await pg.js("(()=>{document.getElementById('email-code').value='%s';document.getElementById('email-confirm').click()})()" % code)
            await d.check("the right code verifies the address", "document.getElementById('email-note').innerText",
                          lambda t: "Email verified" in t, wait=10)
            await pg.js("document.getElementById('acct-out').click()")
            await asyncio.sleep(2.5)
            await d.check("logged out", "document.getElementById('login').style.display", "flex", wait=8)
            await pg.js("document.querySelector('#auth-tabs [data-mode=login]').click()")
            await d.check("the login tab offers a way back in", "document.getElementById('forgot-link').style.display", "block")
            await pg.js("(()=>{document.getElementById('nm').value='%s';document.getElementById('forgot').click()})()" % name)
            await d.check("the recovery form opens", "document.getElementById('recover').style.display", "block")
            await pg.js("document.getElementById('rec-send').click()")
            await d.check("it says the code was sent without saying whether the name exists", "document.getElementById('rec-msg').textContent",
                          lambda t: "If that account" in t, wait=8)
            await asyncio.sleep(0.5)
            reset = self._latest_code(base, addr)
            await pg.js("(()=>{document.getElementById('rec-code').value='%s';document.getElementById('rec-pw').value='a-fresh-password-9';document.getElementById('rec-go').click()})()" % reset)
            await d.check("the code and a new password log you in", "document.getElementById('login').style.display", "none", wait=10)
            await d.check("and the market is live", "document.querySelectorAll('#rows tr').length", lambda n: n > 100, wait=10)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors


if __name__ == "__main__":
    unittest.main()
