"""Industry-wide shocks (a ban, a collapse in demand, a probe, a disruptive technology that hits a whole sector at
once) and the fair-bet rules that keep them balanced, plus the volatility multiplier staying centred on 1 through
the trading sessions."""
import math
import random
import unittest

import _helpers
from _helpers import drift, engine, join, make_engine, quiet

import newsgen
from test_wild import real_engine


def fire(e, n, sector="tech", good=None, kind=None):
    """Fire n shocks on one sector, undoing each price move afterwards. Returns {ticker: [moves]} and the sizes."""
    moves, sizes = {}, []
    for _ in range(n):
        before = {tk: s.fair for tk, s in e.stocks.items()}
        out = e._sector_shock(sector=sector, good=good, kind=kind)
        sizes.append(out[1])
        for tk, f in before.items():
            moves.setdefault(tk, []).append(e.stocks[tk].fair / f - 1)
            e.stocks[tk].fair = f
        e._pending = {}
    return moves, sizes


def dependents(e, sector):
    """Tickers (outside the sector) whose company links point at a company in it: they may move a little with it."""
    members = {s.ticker for s in e.stocks.values() if s.sector == sector}
    return {tk for tk, s in e.stocks.items() if s.sector != sector and any(src in members for src in s.dependencies)}


class IndustryShockFairnessTests(unittest.TestCase):
    def test_every_kind_is_a_fair_two_outcome_bet(self):
        for k in newsgen.INDUSTRY_SHOCKS:
            p = k["p"]
            self.assertTrue(0.3 < p < 0.7, k["key"])
            for bad in (k["bad"][0], sum(k["bad"]) / 2, k["bad"][1]):
                up = (1 - p) * bad / p
                self.assertAlmostEqual(p * up + (1 - p) * (-bad), 0.0, places=12, msg=k["key"])
                self.assertLess(1.4 * bad, 0.95, k["key"])           # no company can lose more than 95%
            self.assertTrue(k["texts_up"] and k["texts_down"])
            for t in k["texts_up"] + k["texts_down"]:
                self.assertIn("{sector}", t)

    def test_failures_are_bigger_than_the_rallies_that_balance_them_only_when_they_are_rarer(self):
        for k in newsgen.INDUSTRY_SHOCKS:
            p = k["p"]
            up, bad = (1 - p) / p, 1.0
            self.assertEqual(up > bad, p < 0.5, k["key"])             # the rarer outcome is the bigger one

    def test_the_expected_move_of_every_company_is_zero(self):
        e = real_engine(31)
        moves, sizes = fire(e, 2500, sector="tech")
        members = [s.ticker for s in e.stocks.values() if s.sector == "tech" and s.asset_type == "equity"]
        self.assertGreaterEqual(len(members), 5)
        for tk in members:
            rs = moves[tk]
            mean = sum(rs) / len(rs)
            sd = math.sqrt(sum((r - mean) ** 2 for r in rs) / len(rs))
            self.assertLess(abs(mean), 4 * sd / math.sqrt(len(rs)), (tk, mean, sd))
        mean = sum(sizes) / len(sizes)
        sd = math.sqrt(sum((x - mean) ** 2 for x in sizes) / len(sizes))
        self.assertLess(abs(mean), 4 * sd / math.sqrt(len(sizes)), (mean, sd))

    def test_failures_and_rallies_both_happen_and_a_failure_is_a_real_but_modest_move(self):
        e = real_engine(32)
        _, sizes = fire(e, 1500, sector="energy")
        downs = [x for x in sizes if x < 0]
        ups = [x for x in sizes if x > 0]
        self.assertGreater(len(downs) / len(sizes), 0.4)
        self.assertGreater(len(ups) / len(sizes), 0.4)
        self.assertGreater(sum(1 for x in downs if x < -0.06) / len(downs), 0.4)    # a whole industry down 6%+
        self.assertGreaterEqual(min(sizes), -0.13 - 1e-9)                          # and never more than 13% (before exposure)

    def test_no_company_ever_moves_20_percent_in_one_industry_shock_and_the_typical_move_is_small(self):
        """An earlier version moved whole sectors 20-30% (49% at the extreme), which was far too much."""
        e = real_engine(34)
        moves, _ = fire(e, 1500, sector="tech")
        every = [abs(r) for tk, v in moves.items() if e.stocks[tk].sector == "tech" and e.stocks[tk].asset_type == "equity" for r in v]
        self.assertLess(max(every), 0.2)
        every.sort()
        median = every[len(every) // 2]
        self.assertTrue(0.04 < median < 0.10, median)                              # typically 5-10%
        self.assertLess(sum(1 for x in every if x > 0.15) / len(every), 0.05)      # moves over 15% are rare

    def test_the_size_setting_scales_every_shock(self):
        big = real_engine(35, sector_shock_size=1.0)
        small = real_engine(35, sector_shock_size=0.5)
        _, a = fire(big, 600, sector="energy")
        _, b = fire(small, 600, sector="energy")
        self.assertAlmostEqual(sum(abs(x) for x in b) / sum(abs(x) for x in a), 0.5, delta=0.08)

    def test_no_company_ever_loses_more_than_95_percent(self):
        e = real_engine(33)
        moves, _ = fire(e, 800, sector="pharma", good=False)
        self.assertGreater(min(min(v) for tk, v in moves.items() if e.stocks[tk].sector == "pharma"), -0.8)


class IndustryShockEffectTests(unittest.TestCase):
    def setUp(self):
        self.e = real_engine(40, sector_links={}, relation_spillover=0)    # no spillovers, so only the shocked sector moves

    def sector_of(self, tk):
        return self.e.stocks[tk].sector

    def test_a_failure_moves_every_company_in_the_sector_down_and_nothing_else(self):
        e = self.e
        before = {tk: s.fair for tk, s in e.stocks.items()}
        linked = dependents(e, "finance")
        sector, size = e._sector_shock(sector="finance", good=False)
        e._flush_moves()
        self.assertLess(size, 0)
        for tk, s in e.stocks.items():
            if s.asset_type == "index":
                continue
            if s.sector == "finance" and s.asset_type == "equity":
                self.assertLess(s.fair / before[tk] - 1, -0.02, tk)
                self.assertGreater(s.fair / before[tk] - 1, -0.2, tk)
            elif tk not in linked:
                self.assertAlmostEqual(s.fair / before[tk], 1.0, places=9, msg=tk)

    def test_a_good_outcome_lifts_the_whole_sector(self):
        e = self.e
        before = {tk: s.fair for tk, s in e.stocks.items() if s.sector == "retail" and s.asset_type == "equity"}
        e._sector_shock(sector="retail", good=True)
        for tk, f in before.items():
            self.assertGreater(e.stocks[tk].fair, f, tk)

    def test_the_sector_can_fall_while_the_market_rises(self):
        """The shock has no market component: shocking one sector leaves every other stock unchanged, so a rising
        market (here, every other stock up 3%) and a collapsing sector can happen at the same time."""
        e = self.e
        linked = dependents(e, "tech")
        others = [s for s in e.stocks.values() if s.asset_type == "equity" and s.sector != "tech" and s.ticker not in linked]
        for s in others:
            s.move(0.03)
        after_rally = {s.ticker: s.fair for s in others}
        before = {s.ticker: s.fair for s in e.stocks.values() if s.sector == "tech" and s.asset_type == "equity"}
        e._sector_shock(sector="tech", good=False)
        tech = [e.stocks[tk].fair / f - 1 for tk, f in before.items()]
        self.assertTrue(all(r < -0.02 for r in tech))                     # the sector fell...
        for s in others:
            self.assertAlmostEqual(s.fair, after_rally[s.ticker], places=9, msg=s.ticker)   # ...the rest still +3%

    def test_the_sector_index_follows_the_sector_down(self):
        e = self.e
        e.tick(now=e.now + 1)
        level = e.stocks["XTECH"].fair
        e._sector_shock(sector="tech", good=False)
        e.tick(now=e.now + 1)
        self.assertLess(e.stocks["XTECH"].fair, 0.985 * level)

    def test_moonshots_in_the_sector_are_hit_too(self):
        e = self.e
        moon = next(s for s in e.stocks.values() if s.moonshot)
        before = moon.fair
        e._sector_shock(sector=moon.sector, good=False)
        self.assertLess(moon.fair, before)

    def test_it_makes_the_whole_sector_jumpier(self):
        e = self.e
        before = {s.ticker: s.volm for s in e.stocks.values() if s.sector == "energy"}
        e._sector_shock(sector="energy", good=False)
        self.assertTrue(all(e.stocks[tk].volm > v for tk, v in before.items() if e.stocks[tk].asset_type == "equity"))

    def test_spillovers_follow_the_usual_links_and_have_no_expected_move(self):
        e = real_engine(41)            # the real sector links: energy hurts airlines and utilities a little
        e.settings["daily_move_cap"] = 0
        rs = []
        for _ in range(400):
            e._pending = {}
            before = {s.ticker: s.fair for s in e.stocks.values() if s.sector == "airlines"}
            e._sector_shock(sector="energy")
            e._flush_moves()
            rs.append(sum(s.fair / before[s.ticker] - 1 for s in e.stocks.values() if s.sector == "airlines"))
            for tk, f in before.items():
                e.stocks[tk].fair = f
            for s in e.stocks.values():
                if s.sector == "energy":
                    s.fair = s.initial_price
        mean = sum(rs) / len(rs)
        sd = math.sqrt(sum((x - mean) ** 2 for x in rs) / len(rs))
        self.assertTrue(any(abs(x) > 1e-4 for x in rs))                  # there is a spillover...
        self.assertLess(abs(mean), 4 * sd / math.sqrt(len(rs)))           # ...and it has no direction


class IndustryShockNewsTests(unittest.TestCase):
    def test_the_headline_names_the_sector_and_every_company_keeps_it_in_its_log(self):
        e = real_engine(50)
        n = len(e.news_log)
        e._sector_shock(sector="tech", good=False)
        self.assertEqual(len(e.news_log), n + 1)
        item = e.news_log[-1]
        self.assertTrue(item["text"].startswith("INDUSTRY ALERT: "))
        self.assertIn("Technology", item["text"])
        self.assertEqual(item["kind"], "industry")
        self.assertEqual(item["dir"], -1)
        members = [s for s in e.stocks.values() if s.sector == "tech" and s.asset_type == "equity"]
        for s in members:
            self.assertTrue(any(x["text"] == item["text"] for x in s.log), s.ticker)
        self.assertEqual(len(item["tickers"]), 4)
        biggest = sorted(members, key=lambda x: -x.base)[:4]
        self.assertEqual(item["tickers"], [s.ticker for s in biggest])

    def test_the_headlines_are_never_repeated(self):
        e = real_engine(51)
        for i in range(60):
            e._sector_shock(sector="energy")
        texts = [x["text"] for x in e.news_log if x["kind"] == "industry"]
        self.assertEqual(len(texts), len(set(texts)))

    def test_every_sector_with_companies_can_be_hit_and_havens_and_commodities_are_not(self):
        e = real_engine(52)
        seen = set()
        for _ in range(400):
            out = e._sector_shock()
            seen.add(out[0])
        self.assertNotIn("safe", seen)
        self.assertNotIn("commodities", seen)
        self.assertGreater(len(seen), 20)
        self.assertIn("portals", seen)                       # the imaginary industries count too

    def test_shocks_arrive_over_time_and_can_be_switched_off(self):
        e = real_engine(53, sector_shock_mean_seconds=20)
        for _ in range(1200):
            e.tick(now=e.now + 1)
        hits = [x for x in e.news_log if x["kind"] == "industry"]
        self.assertGreater(len(hits), 10)                       # (about 19 in practice, fewer than the mean gap suggests)
        off = real_engine(54, sector_shock_mean_seconds=1e12)
        off.next_sector_shock = off.now + 1e12                 # (the first one was scheduled with the default gap)
        for _ in range(1200):
            off.tick(now=off.now + 1)
        self.assertFalse([x for x in off.news_log if x["kind"] == "industry"])

    def test_money_is_conserved_with_industry_shocks_running(self):
        e = real_engine(55, sector_shock_mean_seconds=15, catalyst_mean_seconds=30)
        players = [join(e, f"ind{i}") for i in range(3)]
        e.tick(now=e.now)
        for k in range(1200):
            e.tick(now=e.now + 1)
            if k % 11 == 0:
                tk = random.choice(["NVXA", "CLDR", "GOLD", "XTECH", "XENER", "EMBR"])
                e.trade(players[k % 3], tk, random.choice(["buy", "sell"]), 0.3)
        self.assertLess(abs(drift(e)), 1e-6)


class VolatilityStaysCentredTests(unittest.TestCase):
    """The volatility multiplier must follow real surprises, not the known shape of the day: the thin pre-market
    must not read as calm (the multiplier used to sink to its floor of 0.5 every cycle), and the average over
    ordinary stocks stays at 1, so a stock's stated volatility is its real one."""

    marks = None

    @classmethod
    def setUpClass(cls):
        e = real_engine(61)
        # No market-wide headlines, industry shocks or catalysts: a macro headline lifts every stock's multiplier at
        # once, which is meant to last a few minutes and would make this check depend on luck. What is tested here
        # is that the known shape of the trading day does not move it.
        e.next_event = e.next_sector_shock = e.next_catalyst = e.now + 1e12
        day = engine.MARKET_DAY_SECONDS
        start = (int(e.now // day) + 1) * day
        ordinary = [s for s in e.stocks.values() if s.asset_type == "equity" and not s.moonshot]
        cls.marks = {}
        for i in range(3 * day):
            e.tick(now=start + i)
            if i % day in (299, 1499, 1799):
                cls.marks[(i // day, i % day)] = sum(s.volm for s in ordinary) / len(ordinary)

    def test_the_average_multiplier_stays_near_one_through_every_session(self):
        self.assertEqual(len(self.marks), 9)
        for key, m in self.marks.items():
            self.assertTrue(0.8 < m < 1.35, (key, m))

    def test_the_thin_pre_market_does_not_collapse_the_multiplier(self):
        for (cycle, phase), m in self.marks.items():
            if phase == 299:                                    # the end of pre-market
                self.assertGreater(m, 0.8, (cycle, m))


if __name__ == "__main__":
    unittest.main()
