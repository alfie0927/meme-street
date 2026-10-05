"""The strategy simulator's moonshot sniper and its many-bot runs (sim.py, bots.py)."""
import unittest
from unittest import mock

from _helpers import engine, join, make_engine

import bots
import sim


def sniper(e, name="snipe", target=2, stake=0.25):
    p = join(e, name)
    return sim.Trader(p, "moon_sniper", {"target": target, "stake": stake})


def list_moon(e, tk="CLDR"):
    """Pretend `tk` has just been listed as a moonshot."""
    s = e.stocks[tk]
    s.moonshot, s.listed_at = True, e.now
    e._sim_new_moon = [tk]
    return s


class SniperTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(5)
        self.s = list_moon(self.e)

    def test_it_buys_a_new_listing_with_its_stake_and_only_once(self):
        e = self.e
        tr = sniper(e)
        cash = tr.p.cash
        sim.act(e, tr)
        self.assertGreater(tr.p.hold.get("CLDR", 0), 0)
        self.assertAlmostEqual(cash - tr.p.cash, cash * 0.25, delta=cash * 0.005)
        self.assertEqual(tr.stats["buys"], 1)
        before = dict(tr.p.hold)
        sim.act(e, tr)                                           # still listed as new: it does not buy again
        self.assertEqual(tr.p.hold, before)

    def test_it_ignores_anything_that_is_not_a_new_moonshot(self):
        e = self.e
        tr = sniper(e)
        e._sim_new_moon = []
        sim.act(e, tr)
        self.assertEqual(tr.p.hold, {})
        self.assertEqual(tr.stats["buys"], 0)

    def test_it_waits_until_the_price_reaches_its_target_and_then_sells_everything(self):
        e, s = self.e, self.s
        tr = sniper(e, target=3)
        sim.act(e, tr)
        e._sim_new_moon = []
        entry = e.avg_price(tr.p, "CLDR")
        s.fair = entry * 2.9                                    # not there yet
        sim.act(e, tr)
        self.assertIn("CLDR", tr.p.hold)
        self.assertEqual(tr.stats["hits"], 0)
        e.now += 2
        s.fair = entry * 3.01
        sim.act(e, tr)
        self.assertNotIn("CLDR", tr.p.hold)
        self.assertEqual(tr.stats["hits"], 1)
        self.assertGreater(tr.p.cash, 1000)                      # a 3x on a quarter of the money is a big gain

    def test_a_sale_the_game_refuses_at_the_target_is_not_counted_as_a_hit_until_it_goes_through(self):
        e, s = self.e, self.s
        tr = sniper(e, target=2)
        sim.act(e, tr)
        e._sim_new_moon = []
        entry = e.avg_price(tr.p, "CLDR")
        s.fair = entry * 2.5
        tr.p.last_trade["CLDR"] = e.now                          # the one-second cooldown: a second trade in it is refused
        sim.act(e, tr)
        self.assertIn("CLDR", tr.p.hold)
        self.assertEqual(tr.stats["hits"], 0)
        self.assertEqual(tr.stats["blocked"], 1)
        e.now += 2
        sim.act(e, tr)
        self.assertNotIn("CLDR", tr.p.hold)
        self.assertEqual(tr.stats["hits"], 1)

    def test_it_never_sells_at_a_loss_it_holds_on_with_no_stop(self):
        e, s = self.e, self.s
        tr = sniper(e, target=2)
        sim.act(e, tr)
        e._sim_new_moon = []
        entry = e.avg_price(tr.p, "CLDR")
        for factor in (0.9, 0.5, 0.1):
            s.fair = entry * factor
            e.now += 2
            sim.act(e, tr)
        self.assertIn("CLDR", tr.p.hold)

    def test_a_bankruptcy_that_closes_the_position_is_counted(self):
        e = self.e
        tr = sniper(e)
        sim.act(e, tr)
        e._sim_new_moon = []
        tr.p.hold.pop("CLDR")                                    # what the engine does to holders of a bankrupt company
        tr.p.cost.pop("CLDR", None)
        sim.act(e, tr)
        self.assertEqual(tr.stats["busts"], 1)
        self.assertEqual(tr.opened, {})

    def test_it_stops_when_it_is_out_of_cash(self):
        e = self.e
        tr = sniper(e, stake=1.0)
        sim.act(e, tr)
        e._sim_new_moon = ["NVXA"]
        e.stocks["NVXA"].moonshot, e.stocks["NVXA"].listed_at = True, e.now
        sim.act(e, tr)
        self.assertEqual(tr.stats["buys"], 1)

    def test_every_strategy_with_random_choices_is_known_and_the_sniper_is_in_the_list(self):
        self.assertIn("moon_sniper", sim.STRATEGIES)
        self.assertTrue(sim.RANDOM_STRATEGIES <= set(sim.STRATEGIES))
        self.assertEqual(len(sim.STRATEGIES), len(set(sim.STRATEGIES)))


class ManyBotRunTests(unittest.TestCase):
    def run_sim(self, strategies, copies, hours=0.05, seed=3, random_set=None):
        patches = [mock.patch.object(engine.Engine, "_public", lambda self: None),
                   mock.patch.object(engine.Engine, "_board", lambda self: None),
                   mock.patch.object(sim, "STRATEGIES", list(strategies))]
        if random_set is not None:
            patches.append(mock.patch.object(sim, "RANDOM_STRATEGIES", set(random_set)))
        for p in patches:
            p.start()
        try:
            return sim.run(hours, seed, {}, quiet=True, copies=copies, detail=True)
        finally:
            for p in reversed(patches):
                p.stop()

    def test_the_number_of_bots_per_strategy_follows_the_copies_argument(self):
        m = self.run_sim(["retail", "hodl", "value"], {"retail": 7, "hodl": 4}, hours=0.01)
        rows = m["bots"]
        self.assertEqual(sum(1 for b in rows if b["s"] == "retail"), 7)
        self.assertEqual(sum(1 for b in rows if b["s"] == "hodl"), 4)
        self.assertFalse(any(b["s"] == "value" for b in rows))        # (value is a fixed rule: not reported per bot)
        m = self.run_sim(["retail"], 5, hours=0.01)
        self.assertEqual(len(m["bots"]), 5)

    def test_copies_of_a_fixed_rule_end_with_exactly_the_same_money_and_random_ones_do_not(self):
        m = self.run_sim(["value", "retail"], 3, hours=0.12, random_set={"value", "retail"})
        value = [b["ret"] for b in m["bots"] if b["s"] == "value"]
        retail = [b["ret"] for b in m["bots"] if b["s"] == "retail"]
        self.assertEqual(len(value), 3)
        self.assertEqual(len(set(value)), 1)                          # identical: a player's trades never move a price
        self.assertGreater(len(set(retail)), 1)                        # random traders differ

    def test_the_run_reports_how_much_each_strategy_traded(self):
        m = self.run_sim(["retail"], 4, hours=0.12)
        self.assertGreater(m["turnover"]["retail"], 0)
        self.assertTrue(all(b["turnover"] >= 0 for b in m["bots"]))

    def test_the_bots_report_helpers_summarise_correctly(self):
        self.assertEqual(bots.mean_se([1, 2, 3])[0], 2)
        self.assertAlmostEqual(bots.mean_se([1, 2, 3])[1], 0.5773502691896258)
        self.assertEqual(bots.mean_se([]), (0.0, 0.0))
        self.assertEqual(bots.pct([1, 2, 3, 4], 0.5), 3)
        self.assertEqual(bots.pct([], 0.5), 0.0)


if __name__ == "__main__":
    unittest.main()
