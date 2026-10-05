"""Limit, stop-loss and take-profit orders: held by the server, carried out as ordinary market trades when the price
reaches the trigger. They must never move a price, never fill at a better price than the market, and never open a
position the player did not ask for."""
import json
import math
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, fixed_engine, join, make_engine, quiet

TK = "CLDR"


def setup(seed):
    e = make_engine(seed)
    p = join(e, f"orders{seed}")
    return e, p, e.stocks[TK]


def step(e, n=2):
    """Advance past the one-second trade cooldown and run the tick (which carries out due orders)."""
    for _ in range(n):
        e.tick(now=e.now + 1)


class PlacingTests(unittest.TestCase):
    def test_each_kind_can_be_placed_on_the_right_side_of_the_price(self):
        e, p, s = setup(1)
        self.assertTrue(e.place_order(p, TK, "limit_buy", s.price * 0.95, pct=0.2)[0])
        self.assertTrue(e.place_order(p, TK, "limit_sell", s.price * 1.05, pct=0.2)[0])
        e.trade(p, TK, "buy", 0.3)
        self.assertTrue(e.place_order(p, TK, "stop_loss", s.price * 0.9)[0])
        self.assertTrue(e.place_order(p, TK, "take_profit", s.price * 1.1)[0])
        self.assertEqual({o["kind"] for o in p.orders}, {"limit_buy", "limit_sell", "stop_loss", "take_profit"})

    def test_an_order_that_would_trigger_immediately_is_refused(self):
        e, p, s = setup(2)
        ok, msg = e.place_order(p, TK, "limit_buy", s.price * 1.01, pct=0.1)
        self.assertFalse(ok)
        self.assertIn("lower", msg)
        ok, msg = e.place_order(p, TK, "limit_sell", s.price * 0.99, pct=0.1)
        self.assertFalse(ok)
        self.assertIn("higher", msg)
        e.trade(p, TK, "buy", 0.3)
        self.assertFalse(e.place_order(p, TK, "stop_loss", s.price * 1.05)[0])       # a long's stop is below
        self.assertFalse(e.place_order(p, TK, "take_profit", s.price * 0.95)[0])     # a long's target is above
        self.assertEqual(p.orders, [])

    def test_stops_and_targets_need_a_position_and_point_the_right_way_for_a_short(self):
        e, p, s = setup(3)
        ok, msg = e.place_order(p, TK, "stop_loss", s.price * 0.9)
        self.assertFalse(ok)
        self.assertIn("needs a position", msg)
        e.trade(p, TK, "sell", 0.3)                                                   # a short
        self.assertLess(p.hold[TK], 0)
        self.assertFalse(e.place_order(p, TK, "stop_loss", s.price * 0.9)[0])         # a short's stop is above
        self.assertTrue(e.place_order(p, TK, "stop_loss", s.price * 1.1)[0])
        self.assertTrue(e.place_order(p, TK, "take_profit", s.price * 0.9)[0])
        stop, tp = p.orders
        self.assertEqual((stop["side"], stop["cond"]), ("buy", "ge"))
        self.assertEqual((tp["side"], tp["cond"]), ("buy", "le"))

    def test_bad_input_is_refused(self):
        e, p, s = setup(4)
        bad = [("nope", s.price, 0.1, None), ("limit_buy", float("nan"), 0.1, None), ("limit_buy", float("inf"), 0.1, None),
               ("limit_buy", -1.0, 0.1, None), ("limit_buy", 0.0, 0.1, None), ("limit_buy", True, 0.1, None),
               ("limit_buy", s.price * 0.9, 0.0, None), ("limit_buy", s.price * 0.9, 1.5, None),
               ("limit_buy", s.price * 0.9, None, -5), ("limit_buy", s.price * 0.9, None, float("nan")),
               ("limit_buy", s.price * 0.9, None, None), ("limit_buy", "x", 0.1, None)]
        for kind, trig, pct, amount in bad:
            self.assertFalse(e.place_order(p, TK, kind, trig, pct, amount)[0], (kind, trig, pct, amount))
        self.assertFalse(e.place_order(p, "NOPE", "limit_buy", 1.0, 0.1)[0])
        self.assertEqual(p.orders, [])

    def test_there_is_a_cap_on_open_orders_but_not_on_their_size(self):
        e, p, s = setup(5)
        for i, tk in enumerate(("CLDR", "NVXA", "OILX", "GOLD")):
            for j in range(5):
                if len(p.orders) < 20:
                    st = e.stocks[tk]
                    self.assertTrue(e.place_order(p, tk, "limit_buy", st.price * (0.9 - j * 0.01), pct=1.0)[0])
        self.assertEqual(len(p.orders), 20)
        ok, msg = e.place_order(p, "MUNC", "limit_buy", e.stocks["MUNC"].price * 0.9, pct=0.1)
        self.assertFalse(ok)
        self.assertIn("at most 20", msg)
        e2, p2, s2 = setup(6)
        for j in range(6):
            self.assertTrue(e2.place_order(p2, TK, "limit_buy", s2.price * (0.9 - j * 0.01), amount=1e9)[0])      # any size
        ok, msg = e2.place_order(p2, TK, "limit_buy", s2.price * 0.5, pct=0.1)
        self.assertFalse(ok)
        self.assertIn("6 open orders", msg)

    def test_bots_cannot_place_orders(self):
        e = make_engine(7)
        bot = engine.Player("robot", bot=True)
        self.assertFalse(e.place_order(bot, TK, "limit_buy", e.stocks[TK].price * 0.9, pct=0.1)[0])


class TriggerTests(unittest.TestCase):
    def test_a_limit_buy_fills_at_the_market_price_when_the_price_falls_to_the_trigger(self):
        e, p, s = setup(11)
        trigger = s.price * 0.95
        self.assertTrue(e.place_order(p, TK, "limit_buy", trigger, pct=0.5)[0])
        step(e, 3)
        self.assertEqual(len(p.orders), 1)                                              # not triggered yet
        s.fair = trigger * 0.999
        cash = p.cash
        e.tick(now=e.now + 1)
        self.assertEqual(p.orders, [])
        self.assertGreater(p.hold[TK], 0)
        self.assertLess(p.cash, cash)                                                    # it spent cash
        self.assertTrue(any("Limit buy carried out" in n for n in p.notices))
        self.assertAlmostEqual(p.log[-1]["px"], s.price, delta=s.price * 1e-3)           # at the market, not the trigger

    def test_a_gap_through_the_trigger_fills_at_the_new_price_not_the_trigger(self):
        e, p, s = setup(12)
        e.trade(p, TK, "buy", 0.5)
        step(e, 2)
        trigger = s.price * 0.97
        self.assertTrue(e.place_order(p, TK, "stop_loss", trigger)[0])
        s.fair = trigger * 0.80                                                        # a gap far below the stop
        e.tick(now=e.now + 1)
        self.assertNotIn(TK, p.hold)
        sold_at = p.log[-1]["px"]
        self.assertLess(sold_at, trigger * 0.85)                                       # filled at the bad price, not at the stop

    def test_stop_loss_and_take_profit_for_a_long(self):
        for kind, mult in (("stop_loss", 0.95), ("take_profit", 1.05)):
            e, p, s = setup(13)
            e.trade(p, TK, "buy", 0.4)
            step(e, 2)
            held = p.hold[TK]
            self.assertTrue(e.place_order(p, TK, kind, s.price * mult)[0])
            s.fair = s.price * mult * (0.999 if mult < 1 else 1.001)
            e.tick(now=e.now + 1)
            self.assertNotIn(TK, p.hold, kind)
            self.assertEqual(p.orders, [])

    def test_stop_loss_and_take_profit_for_a_short(self):
        for kind, mult in (("stop_loss", 1.05), ("take_profit", 0.95)):
            e, p, s = setup(14)
            e.trade(p, TK, "sell", 0.3)
            step(e, 2)
            self.assertLess(p.hold[TK], 0)
            self.assertTrue(e.place_order(p, TK, kind, s.price * mult)[0])
            s.fair = s.price * mult * (0.999 if mult < 1 else 1.001)
            e.tick(now=e.now + 1)
            self.assertNotIn(TK, p.hold, kind)

    def test_a_limit_sell_sells_a_long_or_opens_a_short(self):
        e, p, s = setup(15)
        e.trade(p, TK, "buy", 0.3)
        step(e, 2)
        e.place_order(p, TK, "limit_sell", s.price * 1.05, pct=1.0)
        s.fair *= 1.06
        e.tick(now=e.now + 1)
        self.assertNotIn(TK, p.hold)
        step(e, 2)
        e.place_order(p, TK, "limit_sell", s.price * 1.05, pct=0.2)                     # now flat: it opens a short
        s.fair *= 1.06
        e.tick(now=e.now + 1)
        self.assertLess(p.hold.get(TK, 0), 0)

    def test_partial_and_amount_sizes(self):
        e, p, s = setup(16)
        e.trade(p, TK, "buy", 0.6)
        step(e, 2)
        held = p.hold[TK]
        e.place_order(p, TK, "take_profit", s.price * 1.05, pct=0.5)
        s.fair *= 1.06
        e.tick(now=e.now + 1)
        self.assertAlmostEqual(p.hold[TK], held * 0.5, delta=held * 1e-6)
        step(e, 2)
        e.place_order(p, TK, "limit_buy", s.price * 0.9, amount=25.0)
        cash = p.cash
        s.fair *= 0.88
        e.tick(now=e.now + 1)
        self.assertAlmostEqual(cash - p.cash, 25.0, delta=0.01)

    def test_orders_wait_through_the_cooldown_and_a_busy_account_loses_nothing(self):
        e, p, s = setup(17)
        e.place_order(p, TK, "limit_buy", s.price * 0.95, pct=0.1)
        e.trade(p, TK, "buy", 0.1)                                                     # a trade a moment ago
        s.fair *= 0.9
        e.tick(now=e.now + 0.2)
        self.assertEqual(len(p.orders), 1)                                             # still waiting: cooldown
        e.tick(now=e.now + 1.2)
        self.assertEqual(p.orders, [])

    def test_a_stop_never_opens_a_position_you_closed_yourself(self):
        e, p, s = setup(18)
        e.trade(p, TK, "buy", 0.3)
        step(e, 2)
        e.place_order(p, TK, "stop_loss", s.price * 0.95)
        e.trade(p, TK, "sell", 1.0)                                                    # you got out by hand
        step(e, 2)
        s.fair *= 0.9
        e.tick(now=e.now + 1)
        self.assertEqual(p.hold.get(TK, 0), 0)                                         # no short was opened
        self.assertEqual(p.orders, [])
        self.assertTrue(any("no longer hold" in n for n in p.notices))

    def test_a_failed_order_is_cancelled_with_the_reason(self):
        e, p, s = setup(19)
        e.place_order(p, TK, "limit_buy", s.price * 0.95, amount=50.0)
        p.cash = 5.0
        s.fair *= 0.9
        e.tick(now=e.now + 2)
        self.assertEqual(p.orders, [])
        self.assertTrue(any("could not be carried out" in n and "Not enough" in n for n in p.notices), p.notices)

    def test_orders_expire(self):
        e, p, s = setup(20)
        e.settings["order_expiry_seconds"] = 100
        e.place_order(p, TK, "limit_buy", s.price * 0.5, pct=0.1)
        e.tick(now=e.now + 50)
        self.assertEqual(len(p.orders), 1)
        e.tick(now=e.now + 60)
        self.assertEqual(p.orders, [])
        self.assertTrue(any("expired" in n for n in p.notices))

    def test_an_order_in_a_stock_that_is_delisted_is_cancelled(self):
        e, p, s = setup(21)
        e.place_order(p, TK, "limit_buy", s.price * 0.5, pct=0.1)
        e.stocks.pop(TK)
        e.tick(now=e.now + 1)
        self.assertEqual(p.orders, [])
        self.assertTrue(any("no longer traded" in n for n in p.notices))

    def test_nothing_triggers_while_the_price_is_still_on_the_safe_side(self):
        e, p, s = setup(22)
        e.place_order(p, TK, "limit_buy", s.price * 0.5, pct=0.1)
        e.place_order(p, TK, "limit_sell", s.price * 2.0, pct=0.1)
        advance(e, 30)
        self.assertEqual(len(p.orders), 2)
        self.assertEqual(p.hold, {})


class BracketTests(unittest.TestCase):
    def test_a_bracket_places_two_orders_and_the_first_to_trigger_cancels_the_other(self):
        e, p, s = setup(31)
        e.trade(p, TK, "buy", 0.4)
        step(e, 2)
        ok, msg = e.place_bracket(p, TK, s.price * 1.08, s.price * 0.94)
        self.assertTrue(ok, msg)
        self.assertEqual(len(p.orders), 2)
        self.assertEqual(len({o["oco"] for o in p.orders}), 1)
        s.fair *= 0.9                                                                  # the stop is hit
        e.tick(now=e.now + 1)
        self.assertNotIn(TK, p.hold)
        self.assertEqual(p.orders, [])                                                 # the target went with it
        self.assertEqual(sum(1 for n in p.notices if "carried out" in n), 1)

    def test_a_bracket_needs_a_position_and_valid_prices_and_leaves_nothing_behind_on_failure(self):
        e, p, s = setup(32)
        self.assertFalse(e.place_bracket(p, TK, s.price * 1.1, s.price * 0.9)[0])
        e.trade(p, TK, "buy", 0.4)
        step(e, 2)
        ok, msg = e.place_bracket(p, TK, s.price * 1.1, s.price * 1.05)                # a stop above the price
        self.assertFalse(ok)
        self.assertEqual(p.orders, [])
        ok, msg = e.place_bracket(p, TK, s.price * 0.9, s.price * 0.8)                 # a target below the price
        self.assertFalse(ok)
        self.assertEqual(p.orders, [])

    def test_cancelling_one_leg_cancels_the_bracket(self):
        e, p, s = setup(33)
        e.trade(p, TK, "buy", 0.4)
        step(e, 2)
        e.place_bracket(p, TK, s.price * 1.08, s.price * 0.94)
        ok, msg = e.cancel_order(p, p.orders[0]["id"])
        self.assertTrue(ok)
        self.assertEqual(p.orders, [])


class CancelAndPersistTests(unittest.TestCase):
    def test_cancel_and_the_view_the_page_gets(self):
        e, p, s = setup(41)
        e.place_order(p, TK, "limit_buy", s.price * 0.9, pct=0.25)
        e._public()
        me = e.me_state(p)
        self.assertEqual(len(me["orders"]), 1)
        view = me["orders"][0]
        self.assertEqual((view["ticker"], view["kind"], view["label"], view["cond"]), (TK, "limit_buy", "Limit buy", "le"))
        ok, msg = e.cancel_order(p, view["id"])
        self.assertTrue(ok)
        self.assertEqual(e.me_state(p)["orders"], [])                                  # the empty list is sent once...
        self.assertNotIn("orders", e.me_state(p))                                      # ...and then nothing more
        self.assertFalse(e.cancel_order(p, view["id"])[0])
        self.assertFalse(e.cancel_order(p, "abc")[0])
        self.assertFalse(e.cancel_order(p, None)[0])

    def test_one_player_cannot_cancel_anothers_order(self):
        e, p, s = setup(42)
        q = join(e, "other42")
        e.place_order(p, TK, "limit_buy", s.price * 0.9, pct=0.25)
        self.assertFalse(e.cancel_order(q, p.orders[0]["id"])[0])
        self.assertEqual(len(p.orders), 1)

    def test_orders_survive_a_save_and_load_and_the_numbering_continues(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(43)
            e = engine.Engine(state_file=path, bots=False)
            p = join(e, "saver")
            s = e.stocks[TK]
            e.place_order(p, TK, "limit_buy", s.price * 0.9, pct=0.25)
            e.trade(p, "NVXA", "buy", 0.2)
            e.now += 2
            e.place_bracket(p, "NVXA", e.stocks["NVXA"].price * 1.1, e.stocks["NVXA"].price * 0.9)
            ids = [o["id"] for o in p.orders]
            e.save()
            f = engine.Engine(state_file=path, bots=False)
            q = next(x for x in f.players.values() if x.name == "saver")
            self.assertEqual([o["id"] for o in q.orders], ids)
            self.assertEqual(q.orders[0]["trigger"], p.orders[0]["trigger"])
            ok, _ = f.place_order(q, "OILX", "limit_buy", f.stocks["OILX"].price * 0.9, pct=0.1)
            self.assertTrue(ok)
            self.assertGreater(q.orders[-1]["id"], max(ids))

    def test_old_saves_without_orders_load(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(44)
            e = engine.Engine(state_file=path, bots=False)
            join(e, "old44")
            e.save()
            d = json.load(open(path, encoding="utf-8"))
            for x in d["players"]:
                x.pop("orders", None)
            json.dump(d, open(path, "w", encoding="utf-8"))
            f = engine.Engine(state_file=path, bots=False)
            self.assertTrue(all(p.orders == [] for p in f.players.values()))


class NoEdgeTests(unittest.TestCase):
    def test_orders_never_move_a_price_or_change_the_random_numbers(self):
        def run(with_orders):
            e = fixed_engine(51)
            quiet(e)
            p = join(e, "orderer")
            if with_orders:
                for tk in ("CLDR", "NVXA", "OILX"):
                    s = e.stocks[tk]
                    e.place_order(p, tk, "limit_buy", s.price * 0.999, pct=0.3)
                    e.place_order(p, tk, "limit_sell", s.price * 1.001, pct=0.3)
            prices = []
            for _ in range(300):
                e.tick(now=e.now + 1)
                prices.append(round(e.stocks["CLDR"].price, 12))
            return prices, e, p
        quiet_prices, _, _ = run(False)
        busy_prices, e, p = run(True)
        self.assertEqual(quiet_prices, busy_prices)
        self.assertLess(abs(drift(e)), 1e-6)
        self.assertGreater(p.trades, 0)                                               # and they did trade

    def test_a_bracket_round_trip_costs_only_fees_on_average(self):
        """The price is a fair bet, so a take-profit and stop-loss around a position win and lose in equal measure:
        what is left is the fees."""
        rng = random.Random(7)
        gains = []
        for k in range(120):
            random.seed(1000 + k)
            e = engine.Engine(state_file=None, bots=False)
            quiet(e)
            p = join(e, "bracket")
            s = e.stocks["CLDR"]
            e.trade(p, "CLDR", "buy", 0.5)
            start = e.equity(p)
            e.now += 2
            e.place_bracket(p, "CLDR", s.price * 1.004, s.price * 0.996)
            for _ in range(900):
                e.tick(now=e.now + 1)
                if not p.orders:
                    break
            gains.append(e.equity(p) / start - 1)
        mean = sum(gains) / len(gains)
        sd = math.sqrt(sum((g - mean) ** 2 for g in gains) / len(gains))
        self.assertLess(mean, 4 * sd / math.sqrt(len(gains)) + 0.0005)                 # no profit beyond noise
        self.assertGreater(mean, -0.02)

    def test_money_is_conserved_with_many_orders_firing(self):
        e = make_engine(52)
        players = [join(e, f"busy{i}") for i in range(4)]
        e.tick(now=e.now)
        rng = random.Random(3)
        for k in range(500):
            e.tick(now=e.now + 1)
            if k % 7 == 0:
                p = players[k % 4]
                tk = rng.choice(["CLDR", "NVXA", "OILX", "GOLD"])
                s = e.stocks[tk]
                kind = rng.choice(["limit_buy", "limit_sell"])
                mult = rng.uniform(0.985, 0.997) if kind == "limit_buy" else rng.uniform(1.003, 1.015)
                e.place_order(p, tk, kind, s.price * mult, pct=rng.choice([0.1, 0.5, 1.0]))
                if p.hold.get(tk):
                    e.place_bracket(p, tk, s.price * 1.01, s.price * 0.99)
        self.assertLess(abs(drift(e)), 1e-6)
        self.assertGreater(sum(p.trades for p in players), 5)


if __name__ == "__main__":
    unittest.main()
