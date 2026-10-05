"""The append-only ledger and crash recovery: every money event is recorded, and after a crash the engine loads the
last snapshot and replays the events recorded after it, so no trade, deposit, fee or dividend is lost."""
import collections
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, quiet

from ledger import Ledger

FEE = engine.FEE


def new_engine(tmp, seed=1, **settings):
    random.seed(seed)
    e = engine.Engine(state_file=os.path.join(tmp, "state.json"),
                      ledger_path=os.path.join(tmp, "ledger.db"))
    e.settings.update(settings)
    e.tick(now=e.now)
    quiet(e)
    return e


class LedgerUnitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.led = Ledger(os.path.join(self.tmp.name, "l.db"))

    def tearDown(self):
        self.led.close()
        self.tmp.cleanup()

    def test_events_are_buffered_until_flush(self):
        self.led.add(t=1.0, kind="buy", token="a", ticker="X", shares=2, price=3, cash_delta=-6, house_delta=5.97, fee=0.03)
        self.assertEqual(self.led.count(), 0)
        self.assertEqual(self.led.flush(), 1)
        self.assertEqual(self.led.count(), 1)
        self.assertEqual(self.led.flush(), 0, "an empty flush writes nothing")

    def test_sequence_numbers_only_grow_and_events_after_returns_the_tail(self):
        for i in range(5):
            self.led.add(t=float(i), kind="buy", token="a", ticker="X", cash_delta=-i)
            self.led.flush()
        self.assertEqual(self.led.last_seq(), 5)
        tail = self.led.events_after(3)
        self.assertEqual([e["seq"] for e in tail], [4, 5])
        self.assertEqual(self.led.events_after(5), [])

    def test_history_is_newest_first_pages_and_filters(self):
        for i in range(10):
            self.led.add(t=float(i), kind="buy" if i % 2 == 0 else "sell", token="a", ticker="X", cash_delta=-i)
            self.led.add(t=float(i), kind="buy", token="b", ticker="Y")
        self.led.flush()
        page1 = self.led.history("a", limit=4)
        self.assertEqual([e["t"] for e in page1], [9.0, 8.0, 7.0, 6.0])
        page2 = self.led.history("a", limit=4, before=page1[-1]["seq"])
        self.assertEqual([e["t"] for e in page2], [5.0, 4.0, 3.0, 2.0])
        self.assertEqual({e["kind"] for e in self.led.history("a", kinds=["sell"])}, {"sell"})
        self.assertEqual({e["token"] for e in self.led.history("a", limit=100)}, {"a"})
        self.assertEqual([e["t"] for e in self.led.all_history("a")], [float(i) for i in range(10)])

    def test_best_and_worst_trades(self):
        for i, pnl in enumerate([5.0, -3.0, 12.0, -9.0, 1.0]):
            self.led.add(t=float(i), kind="sell", token="a", ticker="X", pnl=pnl)
        self.led.add(t=9.0, kind="buy", token="a", ticker="X")            # no pnl: never listed
        self.led.flush()
        best, worst = self.led.best_worst("a", 2)
        self.assertEqual([b["pnl"] for b in best], [12.0, 5.0])
        self.assertEqual([w["pnl"] for w in worst], [-9.0, -3.0])

    def test_extra_data_round_trips(self):
        self.led.add(t=1.0, kind="margin", token="a", extra={"tickers": ["X", "Y"], "shortfall": 4.5})
        self.led.flush()
        ev = self.led.events_after(0)[0]
        self.assertEqual(ev["extra"], {"tickers": ["X", "Y"], "shortfall": 4.5})

    def test_curve_points_are_stored_per_player_in_time_order(self):
        for t in (3.0, 1.0, 2.0):
            self.led.add_curve("a", t, 100 + t, 50.0)
        self.led.add_curve("b", 1.0, 5.0, 5.0)
        self.led.flush()
        self.assertEqual([p[0] for p in self.led.curve("a")], [1.0, 2.0, 3.0])
        self.assertEqual(len(self.led.curve("a", limit=2)), 2)

    def test_the_ledger_survives_being_reopened(self):
        self.led.add(t=1.0, kind="credit", token="a", cash_delta=1000.0)
        self.led.flush()
        path = self.led.path
        self.led.db.close()
        again = Ledger(path)
        try:
            self.assertEqual(again.count(), 1)
            self.assertEqual(again.last_seq(), 1)
        finally:
            again.close()
        self.led = Ledger(path)       # so tearDown has something to close


class EventRecordingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.e = new_engine(self.tmp.name, seed=11)

    def tearDown(self):
        self.e.ledger.close()
        self.tmp.cleanup()

    def events(self, token=None):
        self.e._flush_borrow()
        self.e.ledger.flush()
        return self.e.ledger.events_after(0) if token is None else self.e.ledger.all_history(token)

    def test_a_join_and_signup_credit_are_recorded(self):
        p = join(self.e, "recorded")
        kinds = [x["kind"] for x in self.events(p.token)]
        self.assertEqual(kinds, ["join", "credit"])

    def test_each_trade_kind_records_its_deltas(self):
        e = self.e
        p = join(e, "deltas")
        e.trade(p, "GOLD", "buy", 0.2)
        e.now += 2
        e.stocks["GOLD"].fair *= 1.1
        e.trade(p, "GOLD", "sell", 1.0)
        e.now += 2
        e.trade(p, "NVXA", "sell", 0.3)       # short
        e.now += 2
        e.stocks["NVXA"].fair *= 0.9
        e.trade(p, "NVXA", "buy", 1.0)        # cover
        evs = {x["kind"]: x for x in self.events(p.token) if x["kind"] in ("buy", "sell", "short", "cover")}
        self.assertEqual(set(evs), {"buy", "sell", "short", "cover"})
        buy = evs["buy"]
        self.assertAlmostEqual(buy["cash_delta"], -200.0, places=6)
        self.assertAlmostEqual(buy["house_delta"], 200.0 * (1 - FEE), places=6)
        self.assertAlmostEqual(buy["fee"], 200.0 * FEE, places=6)
        self.assertGreater(buy["shares"], 0)
        self.assertLess(evs["sell"]["shares"], 0)
        self.assertLess(evs["short"]["shares"], 0)
        self.assertGreater(evs["cover"]["shares"], 0)
        for kind in ("sell", "cover"):
            self.assertIsNotNone(evs[kind]["pnl"], kind)
        self.assertIsNone(evs["buy"]["pnl"])
        self.assertGreater(evs["sell"]["pnl"], 0)      # the price rose 10% (minus fees)
        self.assertGreater(evs["cover"]["pnl"], 0)     # the price fell 10% on a short

    def test_every_players_cash_equals_the_sum_of_their_ledger_deltas(self):
        """The core guarantee: replaying a player's events from nothing reproduces their cash exactly."""
        e = self.e
        players = [join(e, f"acct{i}") for i in range(5)]
        rng = random.Random(4)
        for i in range(400):
            e.tick(now=e.now + 1)
            if i % 2 == 0:
                p = rng.choice(players)
                e.trade(p, rng.choice(["CLDR", "OILX", "GOLD", "HLXB", "MSI", "3SMSI"]),
                        rng.choice(["buy", "buy", "sell", "sell"]), rng.choice([0.1, 0.5, 1.0]))
            if i == 100:
                e.credit(players[0], 300)
            if i == 150:
                e.debit(players[1], 40)
            if i == 200:
                e.stocks["OILX"].div = {"t": e.now - 1, "amt": 0.2}
            if i == 250:
                e.stocks["CLDR"].fair = e.stocks["CLDR"].initial_price * 3
        e._flush_borrow()
        e.ledger.flush()
        for p in players:
            total = sum(x["cash_delta"] for x in e.ledger.all_history(p.token))
            self.assertAlmostEqual(total, p.cash, places=6, msg=p.name)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_house_and_fee_totals_equal_the_sum_of_ledger_deltas(self):
        e = self.e
        start_house, start_fees = e.house, e.fees
        players = [join(e, f"house{i}") for i in range(3)]
        rng = random.Random(5)
        for i in range(300):
            e.tick(now=e.now + 1)
            e.trade(rng.choice(players), rng.choice(["CLDR", "GOLD", "HLXB"]), rng.choice(["buy", "sell"]), 0.3)
        evs = self.events()
        self.assertAlmostEqual(e.house - start_house, sum(x["house_delta"] for x in evs), places=6)
        self.assertAlmostEqual(e.fees - start_fees, sum(x["fee"] for x in evs), places=6)

    def test_realised_pnl_is_net_of_all_fees_and_adds_up(self):
        e = self.e
        p = join(e, "realised")
        s = e.stocks["CLDR"]
        e.trade(p, "CLDR", "buy", 0.2)                     # 200 MB
        cost = p.cost["CLDR"]
        entry_fee = p.entry_fee["CLDR"]
        self.assertAlmostEqual(entry_fee, 200 * FEE, places=9)
        e.now += 2
        s.fair *= 1.2
        e.trade(p, "CLDR", "sell", 0.5)                    # sell half
        half = e.ledger and None
        evs = [x for x in self.events(p.token) if x["kind"] == "sell"]
        proceeds = evs[0]["cash_delta"]
        self.assertAlmostEqual(evs[0]["pnl"], proceeds - cost * 0.5 - entry_fee * 0.5, places=6)
        self.assertAlmostEqual(p.entry_fee["CLDR"], entry_fee * 0.5, places=9)
        e.now += 2
        e.trade(p, "CLDR", "sell", 1.0)                    # and the rest
        self.assertNotIn("CLDR", p.entry_fee)
        total = sum(x["pnl"] for x in self.events(p.token) if x["pnl"] is not None)
        self.assertAlmostEqual(p.realized["CLDR"], total, places=9)
        # the total realised result equals the change in cash
        self.assertAlmostEqual(p.realized["CLDR"], p.cash - 1000, places=6)

    def test_short_realised_pnl(self):
        e = self.e
        p = join(e, "shortpnl")
        e.trade(p, "NVXA", "sell", 0.2)
        e.now += 2
        e.stocks["NVXA"].fair *= 0.8
        e.trade(p, "NVXA", "buy", 1.0)
        self.assertAlmostEqual(p.realized["NVXA"], p.cash - 1000, places=6)
        self.assertGreater(p.realized["NVXA"], 0)

    def test_dividends_borrow_fees_and_margin_calls_are_recorded(self):
        e = self.e
        long_p, short_p, gap_p = join(e, "divlong"), join(e, "divshort"), join(e, "gapped2")
        e.trade(long_p, "OILX", "buy", 0.3)
        e.now += 2
        e.trade(short_p, "OILX", "sell", 0.3)
        e.trade(gap_p, "HLXB", "sell", 1.0)
        e.stocks["OILX"].div = {"t": e.now - 1, "amt": 0.4}
        advance(e, 25)                                      # a dividend, some borrow fees
        e.stocks["HLXB"].fair *= 9
        e.tick(now=e.now + 1)                               # margin call
        kinds = collections.Counter(x["kind"] for x in self.events())
        for kind in ("dividend", "borrow", "margin", "margin_call"):
            self.assertGreaterEqual(kinds[kind], 1, kind)
        self.assertEqual(kinds["dividend"], 2)
        margin = [x for x in self.events() if x["kind"] == "margin"][0]
        self.assertEqual(margin["extra"]["tickers"], ["HLXB"])
        self.assertGreater(margin["extra"]["shortfall"], 0)

    def test_bankruptcy_payouts_and_the_delisting_are_recorded(self):
        e = self.e
        long_p, short_p = join(e, "bklong"), join(e, "bkshort")
        e.trade(long_p, "MOON", "buy", 0.1)
        e.now += 2
        e.trade(short_p, "MOON", "sell", 0.1)
        s = e.stocks["MOON"]
        s.fair = s.initial_price * 0.2
        random.seed(0)
        for seed in range(50):                       # find a seed where the distress check goes bankrupt, not bailout
            if "MOON" not in e.stocks:
                break
            e.stocks["MOON"].distress_checked = False
            e.stocks["MOON"].fair = e.stocks["MOON"].initial_price * 0.2
            random.seed(seed)
            e._check_distress()
        kinds = [x["kind"] for x in self.events()]
        self.assertIn("delist", kinds)
        self.assertEqual(kinds.count("delist_payout"), 2)

    def test_equity_curve_is_sampled_each_minute(self):
        e = new_engine(self.tmp.name, seed=13)
        p = join(e, "curved")
        advance(e, 185)
        self.assertGreaterEqual(len(p.curve), 3)
        self.assertLessEqual(len(p.curve), 4)
        self.assertTrue(all(len(point) == 3 for point in p.curve))
        e.ledger.flush()
        self.assertEqual(len(e.ledger.curve(p.token)), len(p.curve))
        e.ledger.close()

    def test_without_a_ledger_nothing_breaks(self):
        random.seed(14)
        e = engine.Engine(state_file=None)
        e.tick(now=e.now)
        quiet(e)
        p = join(e, "noledger")
        self.assertTrue(e.trade(p, "GOLD", "buy", 0.2)[0])
        advance(e, 70)
        self.assertLess(abs(drift(e)), 1e-6)
        self.assertEqual(len(p.curve), 1)


class CrashRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)

    def tearDown(self):
        self.tmp.cleanup()

    def busy_run(self, e, players, base_ticks, rng, with_events=False):
        for i in range(base_ticks):
            e.tick(now=e.now + 1)
            if i % 3 == 0:
                e.trade(rng.choice(players), rng.choice(["NVXA", "CLDR", "GOLD", "OILX", "HLXB", "MSI", "2LMSI", "DOGO"]),
                        rng.choice(["buy", "buy", "sell"]), rng.choice([0.1, 0.3, 1.0]))
            if with_events and i == 20:
                e.credit(players[0], 250)
            if with_events and i == 40:
                e.debit(players[1], 30)
            if with_events and i == 60:
                e.stocks["OILX"].div = {"t": e.now - 1, "amt": 0.3}
            if with_events and i == 80:
                e.stocks["CLDR"].fair = e.stocks["CLDR"].initial_price * 2.5

    def compare(self, a, b, cash_tol=1e-6):
        for token, p in a.by_token.items():
            q = b.by_token.get(token)
            self.assertIsNotNone(q, f"player {p.name} was lost")
            self.assertEqual(p.name, q.name)
            self.assertAlmostEqual(p.cash, q.cash, delta=cash_tol, msg=f"{p.name} cash")
            self.assertAlmostEqual(p.deposited, q.deposited, places=6, msg=f"{p.name} deposited")
            self.assertEqual(p.trades, q.trades, f"{p.name} trade count")
            self.assertEqual(p.margin_calls, q.margin_calls, f"{p.name} margin calls")
            for tk in set(p.hold) | set(q.hold):
                self.assertAlmostEqual(p.hold.get(tk, 0), q.hold.get(tk, 0), places=6, msg=f"{p.name} {tk} shares")
                self.assertAlmostEqual(p.cost.get(tk, 0), q.cost.get(tk, 0), places=6, msg=f"{p.name} {tk} cost")
            for tk in set(p.realized) | set(q.realized):
                self.assertAlmostEqual(p.realized.get(tk, 0), q.realized.get(tk, 0), places=6, msg=f"{p.name} {tk} realised")
            for tk in set(p.divs) | set(q.divs):
                self.assertAlmostEqual(p.divs.get(tk, 0), q.divs.get(tk, 0), places=6, msg=f"{p.name} {tk} dividends")
        self.assertEqual(set(a.by_token), set(b.by_token))
        for attr in ("house", "minted", "trades_total"):
            self.assertAlmostEqual(getattr(a, attr), getattr(b, attr), places=6, msg=attr)
        self.assertAlmostEqual(a.fees, b.fees, delta=cash_tol * 20)
        self.assertEqual(a.margin_calls, b.margin_calls)

    def test_a_crash_loses_no_trades(self):
        a = new_engine(self.tmp.name, seed=21)
        players = [join(a, f"crash{i}") for i in range(6)]
        rng = random.Random(8)
        self.busy_run(a, players, 120, rng)
        a.save()                                           # the last snapshot
        self.busy_run(a, players, 200, rng, with_events=True)    # 200 more seconds, then the process dies
        a._flush_borrow()
        a.ledger.flush()
        b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
        quiet(b)
        self.assertGreater(b.recovered_events, 50)
        self.compare(a, b)
        self.assertLess(abs(drift(b)), 1e-6)
        b.ledger.close()
        a.ledger.close()

    def test_borrow_fees_in_the_last_seconds_are_the_only_thing_that_can_be_lost(self):
        a = new_engine(self.tmp.name, seed=22)
        p = join(a, "shortlong")
        a.trade(p, "NVXA", "sell", 0.3)
        a.save()
        advance(a, 8)                                      # fees accrue but are not yet written (written every 10 s)
        a.ledger.flush()
        lost = sum(a._borrow_acc.values())
        self.assertGreater(lost, 0)
        b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
        quiet(b)
        self.assertAlmostEqual(a.by_token[p.token].cash, b.by_token[p.token].cash, delta=lost + 1e-9)
        self.assertLess(lost, 0.05)
        self.assertLess(abs(drift(b)), 1e-6)
        a.ledger.close()
        b.ledger.close()

    def test_a_player_who_joined_after_the_snapshot_is_recovered(self):
        a = new_engine(self.tmp.name, seed=23)
        join(a, "early")
        a.save()
        late = join(a, "latecomer")
        a.trade(late, "GOLD", "buy", 0.4)
        a.ledger.flush()
        b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
        quiet(b)
        q = b.by_token[late.token]
        self.assertEqual(q.name, "latecomer")
        self.assertAlmostEqual(q.cash, late.cash, places=6)
        self.assertAlmostEqual(q.hold["GOLD"], late.hold["GOLD"], places=9)
        a.ledger.close()
        b.ledger.close()

    def test_recovery_checkpoints_so_a_second_restart_replays_nothing(self):
        a = new_engine(self.tmp.name, seed=24)
        p = join(a, "twice")
        a.save()
        a.trade(p, "GOLD", "buy", 0.3)
        a.ledger.flush()
        b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
        self.assertGreater(b.recovered_events, 0)
        b.ledger.close()
        c = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
        self.assertEqual(c.recovered_events, 0, "events must not be applied twice")
        self.assertAlmostEqual(c.by_token[p.token].cash, a.by_token[p.token].cash, places=6)
        self.assertAlmostEqual(c.by_token[p.token].hold["GOLD"], a.by_token[p.token].hold["GOLD"], places=9)
        c.ledger.close()
        a.ledger.close()

    def test_a_clean_shutdown_replays_nothing(self):
        a = new_engine(self.tmp.name, seed=25)
        p = join(a, "clean1")
        a.trade(p, "GOLD", "buy", 0.3)
        a.save()
        b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
        self.assertEqual(b.recovered_events, 0)
        a.ledger.close()
        b.ledger.close()

    def test_a_snapshot_without_a_ledger_position_does_not_double_count_old_events(self):
        a = new_engine(self.tmp.name, seed=26)
        p = join(a, "legacy1")
        a.trade(p, "GOLD", "buy", 0.3)
        a.save()
        import json
        state = json.load(open(a.state_file, encoding="utf-8"))
        state.pop("ledger_seq")
        json.dump(state, open(a.state_file, "w", encoding="utf-8"))
        b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
        self.assertEqual(b.recovered_events, 0)
        self.assertAlmostEqual(b.by_token[p.token].cash, p.cash, places=6)
        a.ledger.close()
        b.ledger.close()

    def test_curve_and_trade_log_come_back_after_a_restart(self):
        a = new_engine(self.tmp.name, seed=27)
        p = join(a, "memory1")
        a.trade(p, "GOLD", "buy", 0.3)
        advance(a, 125)
        a.save()
        b = engine.Engine(state_file=a.state_file, ledger_path=a.ledger.path)
        q = b.by_token[p.token]
        self.assertEqual(len(q.curve), len(p.curve))
        self.assertEqual([x["k"] for x in q.log], [x["k"] for x in p.log])
        self.assertEqual(q.entry_fee.keys(), p.entry_fee.keys())
        a.ledger.close()
        b.ledger.close()


if __name__ == "__main__":
    unittest.main()
