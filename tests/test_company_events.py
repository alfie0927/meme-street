"""Scheduled company events between earnings reports (guidance updates, investor days, analyst calls, product events):
on the public calendar in advance, never in the news before they happen, and fair bets when they do."""
import json
import math
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, make_engine, quiet

import newsgen

QUARTER = 63 * engine.MARKET_DAY_SECONDS


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(1)

    def reporting(self):
        return [s for s in self.e.stocks.values() if s.next_earn]

    def test_every_reporting_company_has_one_or_two_events_of_different_kinds(self):
        for s in self.reporting():
            self.assertIn(len(s.events), (1, 2), s.ticker)
            self.assertEqual(len({ev["kind"] for ev in s.events}), len(s.events), s.ticker)
            for ev in s.events:
                self.assertIn(ev["kind"], newsgen.COMPANY_EVENT_KEYS)
                self.assertGreater(ev["t"], self.e.now)
                self.assertLess(ev["t"], self.e.now + QUARTER)

    def test_about_one_and_a_half_events_per_company_per_quarter(self):
        n = [len(s.events) for s in self.reporting()]
        self.assertAlmostEqual(sum(n) / len(n), 1.5, delta=0.2)

    def test_they_are_spread_out_and_keep_clear_of_the_companys_own_report(self):
        times = sorted(ev["t"] for s in self.reporting() for ev in s.events)
        gaps = [b - a for a, b in zip(times, times[1:])]
        self.assertLess(max(gaps), 6 * (QUARTER / len(times)))                  # no long dry stretch
        for s in self.reporting():
            for ev in s.events:
                self.assertGreater(abs(ev["t"] - s.next_earn), engine.MARKET_DAY_SECONDS - 1, s.ticker)   # at least a game day clear

    def test_the_first_is_not_far_off(self):
        first = min(ev["t"] for s in self.reporting() for ev in s.events)
        self.assertLess(first - self.e.now, 0.02 * QUARTER)

    def test_moonshots_and_funds_have_none_and_the_setting_switches_them_off(self):
        from test_wild import real_engine
        e = real_engine(2)
        self.assertTrue(all(not s.events for s in e.stocks.values() if s.moonshot or s.asset_type != "equity"))
        random.seed(3)
        original = engine.Engine._read

        def read(self):
            sectors, companies, templates, base, profiles, derived = original(self)
            return sectors, companies, templates, {**base, "company_events_per_quarter": 0}, profiles, derived
        engine.Engine._read = read
        try:
            off = engine.Engine(state_file=None)
        finally:
            engine.Engine._read = original
        self.assertTrue(all(not s.events for s in off.stocks.values()))

    def test_they_are_on_the_public_calendar_with_a_label_and_nothing_else(self):
        e = make_engine(4)
        s = next(x for x in e.stocks.values() if x.events)
        s.events[0]["t"] = e.now + 5
        s.events[0]["kind"] = "investor_day"
        cal = e._upcoming_events()
        row = next(c for c in cal if c["ticker"] == s.ticker and c["kind"] == "Investor day")
        self.assertEqual(set(row), {"ticker", "name", "kind", "at", "in_seconds"})   # no hint of how it will go
        self.assertEqual([c["at"] for c in cal], sorted(c["at"] for c in cal))

    def test_a_company_listed_later_gets_its_events(self):
        e = make_engine(5)
        cfg = dict(next(c for c in e._read()[1].values() if c["ticker"] == "NVXA"), ticker="ZZEV", name="Event Co")
        cfg = {**cfg, **e.market_profiles["NVXA"]}
        e.now += 10
        e._list(cfg, initial=False)
        self.assertTrue(e.stocks["ZZEV"].events)


class FiringTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(11)
        self.s = self.e.stocks["CLDR"]

    def test_an_event_that_is_due_prints_a_headline_names_the_company_and_queues_a_move(self):
        e, s = self.e, self.s
        s.events = [{"t": e.now + 5, "kind": "guidance"}]
        n0 = len(e.news_log)
        e.now += 6
        e._pending = {}
        e._company_events()
        self.assertEqual(len(e.news_log), n0 + 1)
        text = e.news_log[-1]["text"]
        self.assertIn(s.name, text)
        self.assertTrue(any(w in text.lower() for w in ("outlook", "forecast", "targets", "guidance")), text)
        self.assertIn("CLDR", e._pending)
        self.assertEqual(s.pending[-1]["why"], "updated guidance")                  # the next report will name it
        self.assertNotEqual(s.pending[-1]["dm"], 0)

    def test_the_next_quarters_events_are_planned_once_this_ones_are_used_up(self):
        e, s = self.e, self.s
        s.events = [{"t": e.now + 5, "kind": "analyst_call"}]
        e.now += 6
        e._company_events()
        self.assertGreaterEqual(len(s.events), 1)
        self.assertTrue(all(ev["t"] > e.now for ev in s.events))

    def test_nothing_is_announced_before_it_happens(self):
        e, s = self.e, self.s
        s.events = [{"t": e.now + 500, "kind": "investor_day"}]
        n0 = len(e.news_log)
        advance(e, 20)
        self.assertFalse(any("investor day" in n["text"].lower() and s.name in n["text"] for n in list(e.news_log)[n0:]))

    def test_the_report_names_the_event_among_what_drove_it(self):
        e, s = self.e, self.s
        s.events = [{"t": e.now + 1, "kind": "product_event"}]
        e.now += 2
        e._company_events()
        e._report(s)
        text = next(n["text"] for n in reversed(e.news_log) if n["kind"] == "earnings")
        self.assertIn("a product event", text)

    def test_each_kind_has_text_for_both_outcomes_and_only_uses_slots_a_company_has(self):
        for k in newsgen.COMPANY_EVENTS:
            self.assertTrue(k["texts_up"] and k["texts_down"], k["key"])
            for t in k["texts_up"] + k["texts_down"]:
                self.assertIn("{name}", t)
        ctx = self.e._persona_ctx(self.s)
        for k in newsgen.COMPANY_EVENTS:
            self.assertTrue([t for t in (newsgen.fill(x, ctx) for x in k["texts_up"] + k["texts_down"]) if t], k["key"])


class FairBetTests(unittest.TestCase):
    def fire_many(self, kind, n, seed):
        e = make_engine(seed)
        quiet(e)
        s = e.stocks["CLDR"]
        moves = []
        for _ in range(n):
            e._pending = {}
            e._fire_company_event(s, kind)
            moves.append(e._pending.get("CLDR", 0.0))
        return moves

    def test_the_expected_move_of_every_kind_is_zero(self):
        for i, kind in enumerate(newsgen.COMPANY_EVENT_KEYS):
            moves = self.fire_many(kind, 2500, 20 + i)
            mean = sum(moves) / len(moves)
            sd = math.sqrt(sum((m - mean) ** 2 for m in moves) / len(moves))
            self.assertGreater(sd, 0.002, kind)                                     # they do move the price
            self.assertLess(abs(mean), 4 * sd / math.sqrt(len(moves)), (kind, mean, sd))

    def test_both_outcomes_happen(self):
        moves = self.fire_many("guidance", 2500, 31)
        self.assertGreater(len([m for m in moves if m > 0]), 400)
        self.assertGreater(len([m for m in moves if m < 0]), 400)

    def test_money_is_conserved_with_events_running(self):
        e = make_engine(32, company_events_per_quarter=40)
        players = [join(e, f"ev{i}") for i in range(3)]
        for s in e.stocks.values():
            if s.next_earn:
                s.events = e._new_company_events(s)
        e.tick(now=e.now)
        for k in range(600):
            e.tick(now=e.now + 1)
            if k % 13 == 0:
                e.trade(players[k % 3], random.choice(["CLDR", "NVXA", "OILX"]), random.choice(["buy", "sell"]), 0.3)
        self.assertLess(abs(drift(e)), 1e-6)


class PersistenceTests(unittest.TestCase):
    def test_events_survive_a_restart_and_old_saves_get_some(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(41)
            e = engine.Engine(state_file=path)
            before = {k: [dict(ev) for ev in s.events] for k, s in e.stocks.items() if s.events}
            e.save()
            f = engine.Engine(state_file=path)
            self.assertEqual({k: s.events for k, s in f.stocks.items() if s.events}, before)
            d = json.load(open(path, encoding="utf-8"))
            for v in d["stocks"].values():
                v.pop("events", None)
            json.dump(d, open(path, "w", encoding="utf-8"))
            g = engine.Engine(state_file=path)
            self.assertGreater(sum(1 for s in g.stocks.values() if s.events), 100)


if __name__ == "__main__":
    unittest.main()
