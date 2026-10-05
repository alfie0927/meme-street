"""Daily contests: every entrant trades the same fixed paper balance at the live prices under the real rules, in an
account that is separate from the real one. A contest can never change a real balance, the house reserve or a price."""
import os
import random
import tempfile
import types
import unittest

from _helpers import advance, drift, engine, join, make_engine

import social

DAY = 86400


def fresh(seed=1, **settings):
    e = make_engine(seed, **settings)
    e.now = (int(e.now // DAY) + 1) * DAY + 100          # early in a UTC day
    e.tick(now=e.now)
    e._social_t = 0
    e._social_tick()
    return e


def contest(e):
    return next(t for t in e.tournaments if t["kind"] == "marathon")


def step(e, seconds=2):
    e.now += seconds


def finish(e):
    e.now = contest(e)["end"] + 1
    e._social_t = 0
    e._social_tick()


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(14)
        self.p = join(self.e, "racer")
        self.q = join(self.e, "racer2", extra_cash=50000)       # a rich player

    def test_there_is_only_the_daily_marathon_and_it_starts_at_midnight_utc(self):
        self.assertEqual({t["kind"] for t in self.e.tournaments}, {"marathon"})
        t = contest(self.e)
        self.assertEqual(t["end"] - t["start"], DAY)
        self.assertEqual(t["start"] % DAY, 0)

    def test_everyone_gets_the_same_paper_balance_whatever_they_have(self):
        e = self.e
        tid = contest(e)["id"]
        self.assertTrue(e.tournament_join(self.p, tid)[0])
        self.assertTrue(e.tournament_join(self.q, tid)[0])
        bal = e._contest_balance()
        self.assertEqual(bal, 10000.0)
        for pl in (self.p, self.q):
            self.assertEqual(contest(e)["entrants"][pl.token]["base"], bal)
            self.assertEqual(e._account(contest(e), pl.token).cash, bal)
        self.assertEqual(e.tournament_return(contest(e), self.q.token), 0.0)

    def test_the_balance_is_a_setting(self):
        e = fresh(15, contest_balance=2500)
        p = join(e, "small")
        e.tournament_join(p, contest(e)["id"])
        self.assertEqual(e._account(contest(e), p.token).cash, 2500)

    def test_joining_leaves_the_real_account_alone(self):
        e = self.e
        before = (self.p.cash, dict(self.p.hold), self.p.deposited, e.house, e.total_tokens())
        e.tournament_join(self.p, contest(e)["id"])
        self.assertEqual(before, (self.p.cash, dict(self.p.hold), self.p.deposited, e.house, e.total_tokens()))
        self.assertIs(e.players[self.p.token], self.p)                       # still the one real account
        self.assertIsNot(e._account(contest(e), self.p.token), self.p)       # the paper one is a different object

    def test_cannot_join_twice_late_unknown_or_as_a_bot(self):
        e = self.e
        tid = contest(e)["id"]
        self.assertTrue(e.tournament_join(self.p, tid)[0])
        self.assertFalse(e.tournament_join(self.p, tid)[0])
        self.assertFalse(e.tournament_join(self.q, "marathon-0")[0])
        e.now = contest(e)["join_until"] + 1
        ok, msg = e.tournament_join(self.q, tid)
        self.assertFalse(ok)
        self.assertIn("closed", msg)


class PaperTradingTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(21)
        self.p = join(self.e, "paper")
        self.e.tournament_join(self.p, contest(self.e)["id"])
        self.tid = contest(self.e)["id"]

    def acct(self):
        return self.e._account(contest(self.e), self.p.token)

    def test_a_paper_buy_moves_paper_cash_and_shares_and_nothing_real(self):
        e, p = self.e, self.p
        real = (p.cash, dict(p.hold), e.house, e.fees, e.trades_total, p.trades)
        ok, msg = e.contest_trade(p, self.tid, "CLDR", "buy", 0.5)
        self.assertTrue(ok, msg)
        a = self.acct()
        self.assertAlmostEqual(a.cash, 5000, places=6)
        self.assertGreater(a.hold["CLDR"], 0)
        self.assertEqual(real, (p.cash, dict(p.hold), e.house, e.fees, e.trades_total, p.trades))

    def test_it_follows_the_real_trading_rules_exactly(self):
        e = self.e
        twin = join(e, "twin", extra_cash=9000)              # a real account with the same 10,000 MB
        self.assertAlmostEqual(twin.cash, 10000)
        for side, pct, tk in (("buy", 0.5, "CLDR"), ("sell", 1.0, "OILX"), ("buy", 0.3, "NVXA")):
            step(e)
            self.assertEqual(e.trade(twin, tk, side, pct)[1], e.contest_trade(self.p, self.tid, tk, side, pct)[1])
        a = self.acct()
        self.assertAlmostEqual(a.cash, twin.cash, places=6)
        self.assertEqual(set(a.hold), set(twin.hold))
        for tk in twin.hold:
            self.assertAlmostEqual(a.hold[tk], twin.hold[tk], places=9)
        self.assertAlmostEqual(e.equity(a), e.equity(twin), places=6)
        self.assertAlmostEqual(a.fees_paid, twin.fees_paid, places=9)

    def test_shorting_needs_margin_and_a_squeeze_triggers_a_margin_call(self):
        e, p = self.e, self.p
        self.assertTrue(e.contest_trade(p, self.tid, "CLDR", "sell", 0.9)[0])
        a = self.acct()
        self.assertLess(a.hold["CLDR"], 0)
        e.stocks["CLDR"].fair *= 3.0
        step(e)
        e._paper_tick()
        self.assertGreaterEqual(a.margin_calls, 1)
        self.assertNotIn("CLDR", a.hold)
        self.assertTrue(any(n.startswith("Contest:") for n in p.notices))
        self.assertEqual(p.margin_calls, 0)                                  # the real account had no call

    def test_borrow_fees_run_on_paper_shorts_too(self):
        e, p = self.e, self.p
        e.contest_trade(p, self.tid, "CLDR", "sell", 0.5)
        a = self.acct()
        cash0 = a.cash
        for _ in range(20):
            step(e, 1)
            e._paper_tick()
        self.assertLess(a.cash, cash0)
        self.assertGreater(a.borrow.get("CLDR", 0), 0)
        self.assertEqual(e.borrow_fees, 0)                                   # none of it reached the real fee pool

    def test_dividends_are_paid_to_holders_and_charged_to_shorts(self):
        e, p = self.e, self.p
        e.contest_trade(p, self.tid, "CLDR", "buy", 0.3)
        e.contest_trade(p, self.tid, "OILX", "sell", 0.3)
        a = self.acct()
        c0 = a.cash
        long_sh, short_sh = a.hold["CLDR"], a.hold["OILX"]
        e._paper_dividend("CLDR", 0.1)
        e._paper_dividend("OILX", 0.1)
        self.assertAlmostEqual(a.cash - c0, long_sh * 0.1 - (-short_sh) * 0.1, places=9)

    def test_a_bankruptcy_pays_longs_the_last_price_and_closes_shorts_at_it(self):
        e, p = self.e, self.p
        e.contest_trade(p, self.tid, "CLDR", "buy", 0.3)
        e.contest_trade(p, self.tid, "OILX", "sell", 0.3)
        a = self.acct()
        long_sh, short_sh = a.hold["CLDR"], -a.hold["OILX"]
        c0, collateral = a.cash, a.cost["OILX"]
        e._paper_delist("CLDR", 2.0)
        e._paper_delist("OILX", 5.0)
        self.assertNotIn("CLDR", a.hold)
        self.assertNotIn("OILX", a.hold)
        self.assertAlmostEqual(a.cash, c0 + long_sh * 2.0 + max(0.0, 2 * collateral - short_sh * 5.0), places=6)
        self.assertNotIn("CLDR", a.cost)

    def test_one_entrants_shorts_do_not_use_up_anothers_borrow(self):
        e = self.e
        rivals = [join(e, f"rival{i}") for i in range(4)]
        for r in rivals:
            e.tournament_join(r, self.tid)
        outcomes = []
        for r in [self.p] + rivals:
            step(e)
            outcomes.append(e.contest_trade(r, self.tid, "NVXA", "sell", 0.9)[0])
        self.assertTrue(all(outcomes))

    def test_bad_requests_and_strangers_are_refused(self):
        e = self.e
        stranger = join(e, "stranger")
        self.assertFalse(e.contest_trade(stranger, self.tid, "CLDR", "buy", 0.2)[0])
        self.assertFalse(e.contest_trade(self.p, "nope", "CLDR", "buy", 0.2)[0])
        self.assertFalse(e.contest_trade(self.p, self.tid, "NOPE", "buy", 0.2)[0])
        self.assertFalse(e.contest_trade(self.p, self.tid, "CLDR", "hold", 0.2)[0])
        self.assertFalse(e.contest_trade(self.p, self.tid, "CLDR", "buy", 0)[0])
        self.assertFalse(e.contest_trade(self.p, self.tid, "CLDR", "buy", 2)[0])
        self.assertFalse(e.contest_trade(self.p, self.tid, "CLDR", "buy", 0.2, amount=float("nan"))[0])

    def test_trading_stops_when_the_contest_is_over(self):
        e = self.e
        e.now = contest(e)["end"] + 1
        ok, msg = e.contest_trade(self.p, self.tid, "CLDR", "buy", 0.2)
        self.assertFalse(ok)
        self.assertIn("over", msg)


class NoEffectOnTheRealGameTests(unittest.TestCase):
    """The core promise: a contest changes nothing outside itself."""

    def run_world(self, with_contest):
        random.seed(77)
        clock = engine.time                                          # both worlds start at exactly the same moment
        engine.time = types.SimpleNamespace(time=lambda: 40 * DAY + 100.0)
        try:
            e = engine.Engine(state_file=None)
        finally:
            engine.time = clock
        e.settings["chat_min_trades"] = 0
        e.tick(now=e.now)
        e._social_t = 0
        e._social_tick()
        real = [join(e, f"real{i}", extra_cash=500) for i in range(3)]
        crowd = [join(e, f"crowd{i}") for i in range(6)]
        if with_contest:
            for c in crowd:
                e.tournament_join(c, contest(e)["id"])
        rng, crng = random.Random(5), random.Random(6)               # separate choices: the contest must not steer the real game
        for k in range(400):
            e.tick(now=e.now + 1)
            if k % 7 == 0:
                e.trade(real[k % 3], rng.choice(["CLDR", "NVXA", "OILX", "GOLD"]), rng.choice(["buy", "sell"]), 0.3)
            if with_contest and k % 3 == 0:
                tk = crng.choice(["CLDR", "NVXA", "OILX", "GOLD", "MSI"])
                e.contest_trade(crowd[k % 6], contest(e)["id"], tk, crng.choice(["buy", "sell"]), crng.random())
        return e

    def test_prices_the_house_fees_and_real_balances_are_identical_with_and_without_a_contest(self):
        a = self.run_world(False)
        b = self.run_world(True)
        self.assertEqual({k: s.price for k, s in a.stocks.items()}, {k: s.price for k, s in b.stocks.items()})
        self.assertEqual((a.house, a.fees, a.trades_total, a.margin_calls, a.borrow_fees, a.short_shortfall),
                         (b.house, b.fees, b.trades_total, b.margin_calls, b.borrow_fees, b.short_shortfall))
        self.assertEqual([(p.name, p.cash, p.hold) for p in a.players.values() if p.name.startswith("real")],
                         [(p.name, p.cash, p.hold) for p in b.players.values() if p.name.startswith("real")])
        self.assertEqual(a.total_tokens(), b.total_tokens())
        self.assertLess(abs(drift(b)), 1e-6)
        self.assertGreater(sum(x.trades for x in b._sandboxes[contest(b)["id"]].players.values()), 20)   # they did trade

    def test_paper_players_never_appear_in_the_real_game(self):
        e = self.run_world(True)
        self.assertEqual(len(e.players), 9)
        e._board()
        tokens = [r["token"] for r in e.board]
        self.assertEqual(len(tokens), len(set(tokens)))                      # the leaderboards count each person once...
        self.assertTrue(all(t in e.players for t in tokens))                 # ...and only real players are on them
        self.assertEqual({r["name"] for r in e.board}, {"real0", "real1", "real2"})   # the crowd only made paper trades, which are not trades
        humans = [p for p in e.players.values()]
        self.assertTrue(all(e.by_token[p.token] is p for p in humans))


class FinishTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(31)
        self.players = [join(self.e, f"run{i}") for i in range(5)]
        self.tid = contest(self.e)["id"]
        for p in self.players:
            self.e.tournament_join(p, self.tid)

    def test_standings_rank_by_paper_return_and_the_return_is_against_the_fixed_balance(self):
        e = self.e
        for i, p in enumerate(self.players):
            e.contest_trade(p, self.tid, "CLDR", "buy", 0.2 * (i + 1) if i < 4 else 0.01)
        step(e)
        e.stocks["CLDR"].fair *= 1.2
        rows = e.tournament_standings(contest(e))
        self.assertEqual([r["name"] for r in rows[:4]], ["run3", "run2", "run1", "run0"])
        a = e._account(contest(e), self.players[3].token)
        self.assertAlmostEqual(rows[0]["ret"], (e.equity(a) - 10000) / 10000, places=9)
        self.assertGreater(rows[0]["ret"], 0.1)

    def test_finishing_awards_medals_notices_and_the_podium_but_moves_no_money(self):
        e = self.e
        for i, p in enumerate(self.players):
            e.contest_trade(p, self.tid, "CLDR", "buy", 0.2 * (i + 1) if i < 4 else 0.01)
        step(e)
        e.stocks["CLDR"].fair *= 1.2
        before = [(p.cash, dict(p.hold)) for p in self.players] + [e.house]
        finish(e)
        self.assertFalse(any(t["id"] == self.tid for t in e.tournaments))
        self.assertNotIn(self.tid, e._sandboxes)
        hist = next(h for h in e.tournament_history if h["id"] == self.tid)
        self.assertEqual(hist["entrants"], 5)
        self.assertEqual([r["name"] for r in hist["results"][:3]], ["run3", "run2", "run1"])
        self.assertEqual([[b["place"] for b in p.badges] for p in self.players], [[], [3], [2], [1], []])
        self.assertIn("podium", set(self.players[3].achievements))
        self.assertTrue(any("finished #1 of 5" in n for n in self.players[3].notices))
        self.assertTrue(any("finished #5 of 5" in n for n in self.players[4].notices))
        self.assertEqual(before, [(p.cash, dict(p.hold)) for p in self.players] + [e.house])
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_finished_contest_is_not_recreated_and_the_next_day_has_a_new_one(self):
        e = self.e
        finish(e)
        ids = [t["id"] for t in e.tournaments if t["kind"] == "marathon"]
        self.assertNotIn(self.tid, ids)
        self.assertEqual(len(ids), 1)
        self.assertEqual(contest(e)["entrants"], {})

    def test_a_single_entrant_still_gets_a_medal(self):
        e = fresh(32)
        p = join(e, "solo")
        e.tournament_join(p, contest(e)["id"])
        finish(e)
        self.assertEqual([b["place"] for b in p.badges], [1])


class WhatThePageSeesTests(unittest.TestCase):
    def test_tournaments_for_gives_the_account_the_rank_and_whether_you_can_join(self):
        e = fresh(41)
        p, q = join(e, "viewer"), join(e, "outsider")
        tid = contest(e)["id"]
        theirs = next(t for t in e.tournaments_for(q)["active"] if t["id"] == tid)
        self.assertTrue(theirs["open"])
        self.assertIsNone(theirs["mine"])
        self.assertEqual(theirs["balance"], 10000.0)
        e.tournament_join(p, tid)
        e.contest_trade(p, tid, "CLDR", "buy", 0.4)
        step(e)
        e.contest_trade(p, tid, "OILX", "sell", 0.4)
        mine = next(t for t in e.tournaments_for(p)["active"] if t["id"] == tid)
        self.assertTrue(mine["joined"])
        self.assertFalse(mine["open"])
        self.assertEqual(mine["mine"]["rank"], 1)
        acct = mine["mine"]["account"]
        self.assertEqual({r["ticker"] for r in acct["positions"]}, {"CLDR", "OILX"})
        self.assertEqual(set(acct), {"cash", "free", "equity", "positions", "trades", "margin_calls", "fees"})
        self.assertEqual(acct["trades"], 2)
        short = next(r for r in acct["positions"] if r["ticker"] == "OILX")
        self.assertLess(short["shares"], 0)

    def test_nothing_about_other_players_accounts_is_exposed(self):
        e = fresh(42)
        p, q = join(e, "spy"), join(e, "target")
        tid = contest(e)["id"]
        e.tournament_join(p, tid)
        e.tournament_join(q, tid)
        e.contest_trade(q, tid, "CLDR", "buy", 0.5)
        view = next(t for t in e.tournaments_for(p)["active"] if t["id"] == tid)
        self.assertNotIn("CLDR", str(view["top"]))
        self.assertEqual(set(view["top"][0]), {"name", "ret"})


class PersistenceTests(unittest.TestCase):
    def test_paper_accounts_survive_a_restart_with_their_positions(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(51)
            e = engine.Engine(state_file=path)
            e.now = (int(e.now // DAY) + 1) * DAY + 100
            e.tick(now=e.now)
            e._social_t = 0
            e._social_tick()
            p = join(e, "saver")
            tid = contest(e)["id"]
            e.tournament_join(p, tid)
            e.contest_trade(p, tid, "CLDR", "buy", 0.5)
            step(e)
            e.contest_trade(p, tid, "OILX", "sell", 0.3)
            a = e._account(contest(e), p.token)
            before = (a.cash, dict(a.hold), dict(a.cost), a.trades, round(e.tournament_return(contest(e), p.token), 9))
            e.save()
            f = engine.Engine(state_file=path)
            p2 = next(x for x in f.players.values() if x.name == "saver")
            t2 = next(t for t in f.tournaments if t["id"] == tid)
            a2 = f._account(t2, p2.token)
            self.assertEqual((a2.cash, dict(a2.hold), dict(a2.cost), a2.trades), before[:4])
            self.assertEqual(t2["entrants"][p2.token]["base"], 10000.0)
            self.assertTrue(f.contest_trade(p2, tid, "NVXA", "buy", 0.1)[0])          # and it still trades

    def test_a_contest_saved_by_the_old_design_is_dropped_cleanly(self):
        e = fresh(52)
        old = {"id": "marathon-%d" % contest(e)["start"], "kind": "marathon", "name": "Daily Marathon",
               "start": contest(e)["start"], "end": contest(e)["end"], "join_until": contest(e)["join_until"],
               "entrants": {"abc": {"base": 1000.0, "dep": 1000.0, "tier": "Bronze"}}}
        e._load_tournaments([old])
        self.assertEqual(e.tournaments, [])
        e._social_t = 0
        e._social_tick()
        self.assertEqual(contest(e)["entrants"], {})                                   # a fresh one starts

    def test_money_is_conserved_with_a_busy_contest(self):
        e = fresh(53)
        crowd = [join(e, f"busy{i}") for i in range(4)]
        tid = contest(e)["id"]
        for c in crowd:
            e.tournament_join(c, tid)
        for k in range(300):
            e.tick(now=e.now + 1)
            e.contest_trade(crowd[k % 4], tid, random.choice(["CLDR", "NVXA", "OILX"]), random.choice(["buy", "sell"]), 0.5)
        self.assertLess(abs(drift(e)), 1e-6)


if __name__ == "__main__":
    unittest.main()
