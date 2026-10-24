"""IPOs (engine._ipos, newsgen.make_company; since 2026-10-24): about 15 new companies a game year, from any industry and
of any size, announced a game day ahead and listed at the announced price; past `max_companies` each listing is matched
by a takeover of the smallest company outside the MSI 50, for cash at the market price; all of it saved."""
import os
import random
import statistics
import tempfile
import unittest

from _helpers import drift, engine, join, make_engine
import newsgen


class GeneratorTests(unittest.TestCase):
    def test_every_industry_makes_a_sound_company_like_its_peers(self):
        e = make_engine(2)
        rng = random.Random(4)
        sizes = set()
        for sector in e.sectors:
            if sector not in newsgen.IPO_SECTORS:
                continue
            peers = [s.cfg for s in e.stocks.values() if s.sector == sector and s.asset_type == "equity" and not s.moonshot]
            taken = set(e.stocks)
            for _ in range(5):
                c = newsgen.make_company(rng, taken, sector, peers)
                taken.add(c["ticker"])
                sizes.add(c["size"])
                self.assertEqual(len(c["ticker"]), 4)
                self.assertNotIn(c["ticker"], e.stocks)
                self.assertTrue(0.3 <= c["market_cap"] <= 120 and 6 <= c["initial_price"] <= 150, c)
                self.assertAlmostEqual(c["shares_outstanding"] * c["initial_price"], c["market_cap"], delta=c["market_cap"] * 1e-3)
                self.assertTrue(0.15 <= c["vol"] <= 1.5 and c["revenue"] >= 0 and c["cash"] > 0, c)
                self.assertEqual((c["sector"], c["generated"], c["kind"]), (sector, True, "ipo"))
        self.assertEqual(sizes, {"small", "mid", "large"})


class ListingTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(6)
        self.e.settings["ipo_per_year"] = 15

    def test_about_fifteen_a_game_year(self):
        e = self.e
        year = engine.TRADING_DAYS_PER_YEAR * engine.MARKET_DAY_SECONDS
        waits = [e._ipo_wait() - e.now for _ in range(4000)]
        self.assertAlmostEqual(year / statistics.fmean(waits), 15, delta=1.0)
        e.settings["ipo_per_year"] = 0
        self.assertGreater(e._ipo_wait() - e.now, 1e15)                    # switched off

    def test_announced_a_game_day_ahead_then_listed_at_that_price(self):
        e = self.e
        before = set(e.stocks)
        e.next_ipo = e.now
        e._ipos()
        cfg = e.pending_ipo["cfg"]
        self.assertNotIn(cfg["ticker"], e.stocks)
        self.assertTrue(any(n["text"].startswith("IPO ahead: " + cfg["name"]) for n in e.news_log))
        up = [u for u in e._upcoming_events() if u["kind"] == "IPO"]
        self.assertEqual(len(up), 1)
        self.assertEqual(up[0]["ticker"], "")                              # (no link until it trades)
        self.assertIn(cfg["ticker"], up[0]["name"])
        e.now += engine.MARKET_DAY_SECONDS - 5
        e._ipos()
        self.assertNotIn(cfg["ticker"], e.stocks)                          # not before its time
        e.now += 10
        e._ipos()
        s = e.stocks[cfg["ticker"]]
        self.assertEqual(set(e.stocks) - before, {cfg["ticker"]})
        self.assertAlmostEqual(s.price, cfg["initial_price"], places=6)    # no first-day pop
        self.assertEqual(s.listed_at, e.now)
        self.assertTrue(any(n["text"].startswith("NEW LISTING: " + s.name) for n in e.news_log))
        self.assertIsNone(e.pending_ipo)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_save_keeps_the_announced_ipo_and_the_new_company(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(3)
            a = engine.Engine(state_file=path)
            a.settings["ipo_per_year"] = 15
            a.tick(now=a.now)
            a.next_ipo = a.now
            a._ipos()
            first = a.pending_ipo["cfg"]["ticker"]
            a.save()
            b = engine.Engine(state_file=path)
            self.assertEqual(b.pending_ipo["cfg"]["ticker"], first)
            b.now = b.pending_ipo["at"] + 1
            b._ipos()
            self.assertIn(first, b.stocks)
            b.save()
            c = engine.Engine(state_file=path)
            self.assertIn(first, c.stocks)
            self.assertEqual(c.stocks[first].cfg.get("kind"), "ipo")


class TakeoverTests(unittest.TestCase):
    def test_past_the_limit_the_smallest_outside_the_index_is_bought_at_the_market_price(self):
        e = make_engine(8)
        e.settings["ipo_per_year"] = 15
        ordinary = [s for s in e.stocks.values() if s.asset_type == "equity" and not s.moonshot]
        e.settings["max_companies"] = len(ordinary)
        pool = [s for s in ordinary if s.ticker not in e.index_members]
        target = min(pool, key=lambda s: (s.shares_outstanding * s.price, s.ticker))
        p = join(e, "holder")
        ok, msg = e.trade(p, target.ticker, "buy", 0.5)
        self.assertTrue(ok, msg)
        shares, price_then = p.hold[target.ticker], None
        e.next_ipo = e.now
        e._ipos()
        e.now = e.pending_ipo["at"] + 1
        price_then = target.price
        cash_before = p.cash
        e._ipos()
        self.assertNotIn(target.ticker, e.stocks)
        self.assertIn(target.ticker, e.delisted)
        self.assertEqual(e.archive[target.ticker]["reason"], "takeover")
        self.assertAlmostEqual(p.cash - cash_before, shares * price_then, places=6)    # at the market price
        self.assertNotIn(target.ticker, p.hold)
        self.assertEqual(len([s for s in e.stocks.values() if s.asset_type == "equity" and not s.moonshot]), len(ordinary))
        self.assertTrue(any("buys " + target.name in n["text"] for n in e.news_log))
        self.assertLess(abs(drift(e)), 1e-6)


if __name__ == "__main__":
    unittest.main()
