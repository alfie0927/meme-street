"""The quest ladder (ladder.py): Bronze to Diamond quests paid once, Diamond titles and name colours shown on the boards,
in chat and on profiles; the holdings page's take-profit and stop-loss boxes (Engine.set_exit); and the calendar's
month grid of game days (Engine.calendar_month)."""
import asyncio
import json
import os
import random
import tempfile
import unittest

from _cdp import find_browser, open_page

from _helpers import IsolatedServer, drift, engine, join, make_engine, quiet
import ladder  # noqa: E402  (after _helpers, which puts the game on the path)
from test_server import http

TK = "CLDR"


def step(e, n=2):
    for _ in range(n):
        e.tick(now=e.now + 1)


class LadderTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(31, quest_ladder=True)                  # (the test worlds switch the ladder off)
        quiet(self.e)
        self.p = join(self.e, "climber")

    def test_the_ladder_has_four_tiers_that_pay_more_as_they_go_up(self):
        tiers = [t for t, _ in ladder.TIERS]
        self.assertEqual(tiers, ["bronze", "silver", "gold", "diamond"])
        rewards = [ladder.REWARD[t] for t in tiers]
        self.assertEqual(rewards, sorted(rewards))
        self.assertEqual(len(ladder.LADDER), 30)
        self.assertEqual(sum(ladder.REWARD[q[1]] for q in ladder.LADDER), 1780)
        for q in ladder.LADDER:                                      # only Diamond quests unlock a title and a colour
            self.assertEqual(q[6] is not None, q[1] == "diamond", q[0])
        legend = ladder.LADDER_BY["d_legend"]
        self.assertEqual(legend[5], len(ladder.LADDER) - 1)

    def test_trading_completes_bronze_quests_once_and_pays_them_as_money_put_in(self):
        e, p = self.e, self.p
        for i in range(5):
            self.assertTrue(e.trade(p, TK, "buy" if i % 2 == 0 else "sell", 0.1)[0])
            step(e)
        self.assertIn("b_trades", p.ladder["done"])
        paid = p.mb_by_source.get("challenge", 0.0)
        self.assertGreaterEqual(paid, 10.0)
        before = p.cash
        e._ladder_check(p)                                           # never twice
        self.assertEqual(p.cash, before)
        self.assertAlmostEqual(p.deposited, 1000.0 + paid, places=6)  # counted as money put in: no lift to the return
        self.assertLess(abs(drift(e)), 1e-6)
        view = e.ladder_view(p)
        bronze = view["tiers"][0]
        self.assertEqual(bronze["id"], "bronze")
        q = next(x for x in bronze["quests"] if x["id"] == "b_trades")
        self.assertTrue(q["done"])
        self.assertEqual(q["n"], 5)

    def test_a_stop_loss_and_a_short_count(self):
        e, p = self.e, self.p
        e.trade(p, TK, "buy", 0.3)
        self.assertTrue(e.place_order(p, TK, "stop_loss", e.stocks[TK].price * 0.9)[0])
        self.assertIn("b_stop", p.ladder["done"])
        step(e)
        self.assertTrue(e.trade(p, "NVXA", "sell", 0.1)[0])                     # selling what you do not hold is a short
        self.assertIn("b_short", p.ladder["done"])

    def test_diamond_unlocks_a_title_and_a_colour_that_show_everywhere(self):
        e, p = self.e, self.p
        self.assertEqual(e.set_style(p, "veteran", "")[0], False)            # locked
        p.counters["trades"] = 1000
        e._ladder_check(p)
        self.assertIn("d_trades", p.ladder["done"])
        view = e.ladder_view(p)
        self.assertEqual([t["id"] for t in view["titles"]], ["veteran"])
        self.assertEqual([c["id"] for c in view["colors"]], ["cyan"])
        self.assertFalse(e.set_style(p, "top_trader", "")[0])                # still locked
        self.assertFalse(e.set_style(p, "", "gold")[0])
        self.assertTrue(e.set_style(p, "veteran", "cyan")[0])
        self.assertEqual(e.style_of(p), {"c": ladder.COLORS["cyan"][1], "t": "Market Veteran"})
        e.trade(p, TK, "buy", 0.1)
        engine.Engine._board(e)                                              # (quiet() switched the board off)
        self.assertEqual(e.board_view()[0]["style"]["t"], "Market Veteran")
        self.assertEqual(e.boards_for(p)["season"][0]["style"]["c"], ladder.COLORS["cyan"][1])
        ok, _, msg = e.post_chat(p, "hello from the top")
        self.assertTrue(ok)
        self.assertEqual(msg["style"]["t"], "Market Veteran")
        self.assertEqual(e.public_profile("climber")["style"]["t"], "Market Veteran")
        self.assertTrue(e.set_style(p, "", "")[0])
        self.assertIsNone(e.style_of(p))

    def test_day_board_finishes_count_only_with_a_positive_return(self):
        e, p = self.e, self.p
        q = join(e, "second")
        e.board = [{"token": p.token, "ret": 0.05, "name": p.name}, {"token": q.token, "ret": -0.01, "name": q.name}]
        e._ladder_day_end()
        self.assertEqual(p.ladder["n"].get("top10"), 1)
        self.assertEqual(p.ladder["n"].get("top3"), 1)
        self.assertIn("g_top10", p.ladder["done"])
        self.assertIsNone(q.ladder["n"].get("top10"))

    def test_the_ladder_survives_a_save_and_a_reset_starts_it_again(self):
        e, p = self.e, self.p
        p.counters["trades"] = 1000
        e._ladder_check(p)
        e.set_style(p, "veteran", "cyan")
        q = type(p)("copy")
        ladder.load_player(q, json.loads(json.dumps(ladder.dump_player(p))))
        self.assertEqual(q.ladder["done"].keys(), p.ladder["done"].keys())
        self.assertEqual((q.title, q.name_color), ("veteran", "cyan"))
        bad = type(p)("bad")
        ladder.load_player(bad, {"title": "<script>", "name_color": "red; background:url(x)", "ladder": {"done": {"nope": 1}}})
        self.assertEqual((bad.title, bad.name_color, bad.ladder["done"]), ("", "", {}))
        e.reset_to_day_one()
        self.assertEqual(p.ladder["done"], {})
        self.assertEqual((p.title, p.name_color), ("", ""))


class ExitTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(32)
        quiet(self.e)
        self.p = join(self.e, "exiter")
        self.s = self.e.stocks[TK]

    def kinds(self):
        return {o["kind"]: o for o in self.p.orders if o["ticker"] == TK}

    def test_set_move_and_remove_a_take_profit_and_a_stop(self):
        e, p, s = self.e, self.p, self.s
        self.assertFalse(e.set_exit(p, TK, "take_profit", s.price * 1.1)[0])          # no position yet
        e.trade(p, TK, "buy", 0.3)
        ok, msg = e.set_exit(p, TK, "take_profit", s.price * 1.1)
        self.assertTrue(ok, msg)
        self.assertFalse(e.set_exit(p, TK, "stop_loss", s.price * 1.05)[0])           # a long's stop is below
        self.assertTrue(e.set_exit(p, TK, "stop_loss", s.price * 0.9)[0])
        k = self.kinds()
        self.assertEqual(k["take_profit"]["oco"], k["stop_loss"]["oco"])              # paired: one cancels the other
        self.assertIsNotNone(k["take_profit"]["oco"])
        self.assertTrue(e.set_exit(p, TK, "take_profit", s.price * 1.2)[0])          # moved, not added
        self.assertEqual(len(p.orders), 2)
        self.assertAlmostEqual(self.kinds()["take_profit"]["trigger"], round(s.price * 1.2, 8))
        self.assertFalse(e.set_exit(p, TK, "take_profit", s.price * 0.8)[0])         # a long's target is above
        self.assertTrue(e.set_exit(p, TK, "take_profit", None)[0])                   # removed: the stop stays alone
        k = self.kinds()
        self.assertEqual(list(k), ["stop_loss"])
        self.assertIsNone(k["stop_loss"]["oco"])
        self.assertFalse(e.set_exit(p, TK, "take_profit", None)[0])

    def test_a_short_has_its_target_below_and_its_stop_above(self):
        e, p, s = self.e, self.p, self.s
        self.assertTrue(e.trade(p, TK, "sell", 0.2)[0])                    # a short
        self.assertFalse(e.set_exit(p, TK, "take_profit", s.price * 1.1)[0])
        self.assertTrue(e.set_exit(p, TK, "take_profit", s.price * 0.9)[0])
        self.assertTrue(e.set_exit(p, TK, "stop_loss", s.price * 1.1)[0])
        self.assertFalse(e.set_exit(p, TK, "stop_loss", s.price * 0.95)[0])

    def test_a_paired_exit_closes_the_position_and_takes_the_other_with_it(self):
        e, p, s = self.e, self.p, self.s
        e.trade(p, TK, "buy", 0.3)
        step(e)
        e.set_exit(p, TK, "take_profit", s.price * 1.02)
        e.set_exit(p, TK, "stop_loss", s.price * 0.98)
        s.fair *= 1.05
        step(e, 3)
        self.assertNotIn(TK, p.hold)
        self.assertEqual(p.orders, [])
        self.assertLess(abs(drift(e)), 1e-6)


class CalendarMonthTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(33, market_model=2)
        quiet(self.e)
        step(self.e, 3)

    def test_a_month_of_game_days_in_weeks_with_today_marked(self):
        e = self.e
        c = e.calendar_month(0)
        self.assertTrue(c["on"])
        self.assertTrue(all(len(w) == 7 for w in c["weeks"]))
        cells = [x for w in c["weeks"] for x in w]
        self.assertEqual([x["n"] for x in cells], list(range(cells[0]["n"], cells[0]["n"] + len(cells))))   # one cell a day
        today = [x for x in cells if x["today"]]
        self.assertEqual(len(today), 1)
        self.assertEqual(today[0]["n"], int(e.now // engine.MARKET_DAY_SECONDS))
        self.assertTrue(28 <= sum(1 for x in cells if x["in"]) <= 31)
        self.assertEqual(engine.game_date(cells[0]["n"]).weekday(), 0)                # weeks start on Monday
        kinds = {m["kind"] for x in cells for m in x["macro"]}
        self.assertIn("claims", kinds)                                                # weekly, so always in a month
        claims = [x for x in cells if any(m["kind"] == "claims" for m in x["macro"])]
        self.assertTrue(all(engine.game_date(x["n"]).weekday() == engine.game_date(claims[0]["n"]).weekday() for x in claims))
        for x in cells:
            for m in x["macro"]:
                self.assertEqual(int(m["t"] // engine.MARKET_DAY_SECONDS), x["n"])
                self.assertTrue(m.get("out") or "forecast" in m)

    def test_cycling_months_and_released_results(self):
        e = self.e
        a, b, c = e.calendar_month(-1), e.calendar_month(0), e.calendar_month(1)
        self.assertNotEqual(a["title"], b["title"])
        self.assertNotEqual(b["title"], c["title"])
        self.assertFalse(any(x["today"] for w in c["weeks"] for x in w if x["in"]))
        self.assertEqual(e.calendar_month(99)["offset"], 24)                         # clamped
        t, kind = e.model.economy.upcoming(e.now, days=40)[0]
        e.model.economy.publish(t - 60)
        e.now = t - 2
        for _ in range(4):
            e.tick(now=e.now + 1)
        month = e.calendar_month(0)
        rec = next(m for w in month["weeks"] for x in w for m in x["macro"] if int(m["t"]) == int(t) and m["kind"] == kind)
        self.assertTrue(rec["out"])
        self.assertTrue(rec.get("text"))

    def test_the_month_over_http(self):
        with IsolatedServer(settings={"market_model": 2}) as srv:
            status, text, _ = http(srv, "/api/calendar/month?offset=1")
            self.assertEqual(status, 200, text)
            d = json.loads(text)
            self.assertTrue(d["on"])
            self.assertEqual(d["offset"], 1)


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class PagesBrowserTests(unittest.TestCase):
    """The three pages in a real browser: holdings' take-profit and stop-loss boxes, the profile's quest ladder, and the
    calendar's month grid."""

    def test_holdings_exits_ladder_and_calendar(self):
        from test_browser import Driver
        with IsolatedServer() as srv:
            d, errors = asyncio.run(self._run(srv.url))
        d.verdict(self, errors)

    async def _run(self, base):
        from test_browser import Driver
        proc, pg, _ = await open_page(debug_port=9391)
        d = Driver(pg)
        try:
            await d.join(base, "ladderer")
            await pg.js("send({type:'trade',ticker:'CLDR',side:'buy',pct:0.3})")
            await asyncio.sleep(1.5)
            await pg.goto(base + "/holdings", 3)
            cell = "document.querySelector('#hold-rows tr[data-k=CLDR] .c-%s').innerText.trim()"
            await d.check("a position shows - for no take profit and no stop", f"[{cell % 'tp'},{cell % 'sl'}].join('|')", "-|-", wait=8)
            await pg.js("document.querySelector('#hold-rows tr[data-k=CLDR] .c-tp [data-exit]').click()")
            await d.check("clicking it opens a box", "!!document.querySelector('#hold-rows .exit-edit input')", True, wait=3)
            await pg.js("(()=>{const i=document.querySelector('#hold-rows .exit-edit input');i.value=String((S.byT.CLDR.price*1.2).toFixed(2));document.querySelector('#hold-rows [data-exit-save]').click()})()")
            await d.check("setting a take profit places the order", "(S.orders||[]).some(o=>o.ticker==='CLDR'&&o.kind==='take_profit')", True, wait=5)
            await d.check("and the cell shows its price", cell % "tp", lambda t: t != "-" and "%" in t, wait=4)
            await pg.js("document.querySelector('#hold-rows tr[data-k=CLDR] .c-sl [data-exit]').click()")
            await pg.js("(()=>{const i=document.querySelector('#hold-rows .exit-edit input');i.value=String((S.byT.CLDR.price*0.8).toFixed(2));i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))})()")
            await d.check("Enter sets a stop-loss, paired with the take profit", "(()=>{const o=(S.orders||[]).filter(o=>o.ticker==='CLDR');return o.length===2&&!!o[0].oco&&o[0].oco===o[1].oco})()", True, wait=5)
            await pg.js("document.querySelector('#hold-rows tr[data-k=CLDR] .c-tp [data-exit]').click()")
            await pg.js("document.querySelector('#hold-rows [data-exit-clear]').click()")
            await d.check("Remove takes the take profit away", "(S.orders||[]).filter(o=>o.ticker==='CLDR').map(o=>o.kind).join()", "stop_loss", wait=5)
            await d.check("and its cell shows - again", cell % "tp", "-", wait=4)
            await pg.goto(base + "/profile", 3)
            await d.check("the ladder has four tiers", "document.querySelectorAll('#ladder details.lad-tier').length", 4, wait=8)
            await d.check("the first unfinished one is open", "[...document.querySelectorAll('#ladder details.lad-tier')].filter(x=>x.open).map(x=>x.dataset.tier).join()", "bronze")
            await d.check("Diamond promises a title", "document.querySelector('#ladder .lad-diamond').textContent", lambda t: "Top Trader" in t and "Legend" in t)
            await pg.js("document.querySelector('#ladder .lad-diamond summary').click()")
            await d.check("a tier opens with a click and is remembered", "JSON.parse(localStorage.getItem('ms_ladder_open')).includes('diamond')", True, wait=3)
            await pg.goto(base + "/calendar", 3)
            await d.check("the calendar is a grid of days", "document.querySelectorAll('#cal-grid .cal-cell').length", lambda n: n is not None and n >= 28 and n % 7 == 0, wait=10)
            await d.check("today is marked", "document.querySelectorAll('#cal-grid .cal-cell.today').length", 1)
            await d.check("releases are on it", "[...document.querySelectorAll('#cal-grid .cal-chip')].some(c=>c.title.includes('Weekly jobless claims'))", True)
            t0 = await pg.js("document.getElementById('cal-title').innerText")
            await pg.js("document.getElementById('cal-next').click()")
            await d.check("Next shows the next month", "document.getElementById('cal-title').innerText", lambda t: bool(t) and t != t0, wait=5)
            await d.check("without today in it", "document.querySelectorAll('#cal-grid .cal-cell.today:not(.other)').length", 0)
            await pg.js("document.getElementById('cal-today').click()")
            await d.check("Today comes back", "document.getElementById('cal-title').innerText", t0, wait=5)
            await pg.js("(()=>{const c=[...document.querySelectorAll('#cal-grid .cal-cell:not(.other)')].find(x=>x.querySelector('.cal-chip'));c.click()})()")
            await d.check("a day opens with its releases", "document.getElementById('cal-day').innerText", lambda t: bool(t) and ("forecast" in t.lower() or "stocks" in t or "released" in t or "little change" in t), wait=3)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors


if __name__ == "__main__":
    unittest.main()
