"""The MSI 50: the market index follows the 50 largest companies, weighted by market value."""
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, make_engine


def cap(s):
    return s.shares_outstanding * s.price


class MemberTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(3)

    def test_it_is_called_the_msi_50_everywhere(self):
        s = self.e.stocks["MSI"]
        self.assertEqual(s.name, "MSI 50")
        self.assertIn("50 largest", s.desc)
        self.assertNotIn("Meme Street Index", s.desc)
        for tk, name in (("2LMSI", "2x Long MSI 50"), ("2SMSI", "2x Short MSI 50"),
                         ("3LMSI", "3x Long MSI 50"), ("3SMSI", "3x Short MSI 50")):
            self.assertEqual(self.e.stocks[tk].name, name)
            self.assertIn("MSI 50", self.e.stocks[tk].desc)
        tracks = next(x for x in self.e.pub_stocks if x["ticker"] == "MSI")["tracks"]
        self.assertIn("50 largest", tracks)

    def test_the_members_are_the_fifty_biggest_companies_and_nothing_else(self):
        e = self.e
        self.assertEqual(len(e.index_members), 50)
        members = [e.stocks[t] for t in e.index_members]
        self.assertTrue(all(s.asset_type == "equity" and not s.moonshot for s in members))
        eligible = [s for s in e.stocks.values() if s.asset_type == "equity" and not s.moonshot]
        weakest_in = min(cap(s) for s in members)
        self.assertTrue(all(cap(s) <= weakest_in + 1e-9 for s in eligible if s.ticker not in e.index_members))
        self.assertEqual(e.index_members, sorted(e.index_members, key=lambda t: (-cap(e.stocks[t]), t)))

    def test_funds_commodities_moonshots_and_other_indices_are_never_in(self):
        e = self.e
        e.settings["index_size"] = 10_000                               # even with room for everyone
        e._list_moonshot(initial=False)
        e._rank_index_members()
        kinds = {e.stocks[t].asset_type for t in e.index_members}
        self.assertEqual(kinds, {"equity"})
        self.assertFalse(any(e.stocks[t].moonshot for t in e.index_members))
        self.assertNotIn("MSI", e.index_members)


class ReturnTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(4)
        self.e.index_prev = {tk: s.price for tk, s in self.e.stocks.items()}

    def test_the_index_moves_by_the_market_value_weighted_return_of_its_members(self):
        e = self.e
        before = e.index_level
        weights = {t: cap(e.stocks[t]) for t in e.index_members}
        moves = {t: random.Random(t).uniform(-0.03, 0.03) for t in e.index_members}
        for t, r in moves.items():
            e.stocks[t].move(r)
        e._update_index_level()
        expected = sum(weights[t] * moves[t] for t in weights) / sum(weights.values())
        self.assertAlmostEqual(e.index_level / before - 1, expected, places=9)

    def test_a_bigger_company_moves_it_more_than_a_smaller_one(self):
        e = self.e
        big, small = e.index_members[0], e.index_members[-1]
        self.assertGreater(cap(e.stocks[big]), cap(e.stocks[small]))
        before = e.index_level
        e.stocks[big].move(0.10)
        e._update_index_level()
        up_big = e.index_level / before - 1
        e.index_prev = {tk: s.price for tk, s in e.stocks.items()}
        before = e.index_level
        e.stocks[small].move(0.10)
        e._update_index_level()
        up_small = e.index_level / before - 1
        self.assertGreater(up_big, up_small)
        self.assertGreater(up_small, 0)

    def test_companies_outside_the_fifty_do_not_move_it_at_all(self):
        e = self.e
        outside = [t for t, s in e.stocks.items() if s.asset_type != "index" and t not in e.index_members]
        self.assertGreater(len(outside), 50)
        before = e.index_level
        for t in outside:
            e.stocks[t].move(0.25)
        e._update_index_level()
        self.assertEqual(e.index_level, before)

    def test_the_leveraged_products_still_follow_the_new_index(self):
        e = self.e
        up, lev = e.stocks["MSI"].price, e.stocks["2LMSI"].price
        for t in e.index_members:
            e.stocks[t].move(0.02)
        e._update_index_level()
        r = e.stocks["MSI"].price / up - 1
        self.assertAlmostEqual(r, 0.02, places=9)
        self.assertAlmostEqual(e.stocks["2LMSI"].price / lev - 1, 2 * r, places=9)


class MembershipChangeTests(unittest.TestCase):
    def test_it_is_re_ranked_when_a_new_game_day_starts(self):
        e = make_engine(5)
        outsider = next(t for t, s in e.stocks.items() if s.asset_type == "equity" and not s.moonshot
                        and t not in e.index_members)
        e.stocks[outsider].fair *= 1000                                   # now the biggest company by far
        self.assertNotIn(outsider, e.index_members)                       # (not until the next day starts)
        e.market_day -= 1
        e.tick(now=e.now + 1)
        self.assertIn(outsider, e.index_members)
        self.assertEqual(e.index_members[0], outsider)
        self.assertEqual(len(e.index_members), 50)

    def test_a_delisted_member_is_replaced_at_once_and_the_index_does_not_jump(self):
        e = make_engine(6)
        gone = e.index_members[10]
        before = e.index_level
        e.stocks.pop(gone)
        e.index_prev.pop(gone, None)
        e.tick(now=e.now + 1)
        self.assertNotIn(gone, e.index_members)
        self.assertEqual(len(e.index_members), 50)
        self.assertLess(abs(e.index_level / before - 1), 0.02)

    def test_fewer_than_fifty_companies_means_all_of_them(self):
        e = make_engine(7, index_size=7)
        e._rank_index_members()
        self.assertEqual(len(e.index_members), 7)

    def test_the_members_survive_a_restart(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(8)
            a = engine.Engine(state_file=path)
            a.tick(now=a.now)
            advance(a, 20)
            a.save()
            b = engine.Engine(state_file=path)
            self.assertEqual(b.index_members, a.index_members)
            self.assertAlmostEqual(b.index_level, a.index_level, places=9)

    def test_a_save_without_members_picks_them_on_load(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(9)
            a = engine.Engine(state_file=path)
            a.tick(now=a.now)
            a.save()
            import json
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            data.pop("index_members")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            b = engine.Engine(state_file=path)
            self.assertEqual(len(b.index_members), 50)
            advance(b, 5)

    def test_trading_the_index_never_moves_it_and_money_balances(self):
        e = make_engine(10)
        p = join(e, "trader")
        level = e.index_level
        e.trade(p, "MSI", "buy", 1.0)
        self.assertEqual(e.index_level, level)
        advance(e, 120)
        e.trade(p, "MSI", "sell", 1.0)
        self.assertLess(abs(drift(e)), 1e-6)


if __name__ == "__main__":
    unittest.main()
