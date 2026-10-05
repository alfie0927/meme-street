"""The earnings calendar (reports only before the open or after the close, spread evenly through the cycle, a quarter
apart give or take a few game days), bank price-target notes that give a reason only some of the time, and headlines
that carry no hidden information."""
import json
import math
import os
import random
import re
import tempfile
import unittest

import _helpers
from _helpers import advance, drift, engine, join, make_engine, quiet

DAY = engine.MARKET_DAY_SECONDS
QUARTER = 63 * DAY


def build(seed, **settings):
    """An engine whose settings are in force from the very start (the first reports are scheduled while it is built)."""
    random.seed(seed)
    original = engine.Engine._read

    def read(self):
        sectors, companies, templates, base, profiles, derived = original(self)
        return sectors, companies, templates, {**base, **settings}, profiles, derived
    engine.Engine._read = read
    try:
        return engine.Engine(state_file=None, bots=False)
    finally:
        engine.Engine._read = original


def sessions(seed, **settings):
    """An engine with the real 5 / 20 / 5 minute cycle (the test world has it switched off)."""
    return build(seed, premarket_seconds=300, aftermarket_seconds=300, **settings)


def phase(t):
    return t % DAY


def in_window(t, pre=300, post=300):
    return phase(t) < pre or phase(t) >= DAY - post


class SpreadTests(unittest.TestCase):
    def test_reports_are_spread_so_that_one_is_always_coming_soon(self):
        e = make_engine(1)
        slots = sorted(s.earn_slot - e.now for s in e.stocks.values() if s.earn_slot)
        n = len(slots)
        self.assertGreater(n, 100)
        self.assertGreaterEqual(slots[0], 0.005 * QUARTER - 5)
        self.assertLessEqual(slots[-1], QUARTER + 5)
        gaps = [b - a for a, b in zip(slots, slots[1:])]
        mean_gap = QUARTER / n
        self.assertLess(max(gaps), 6 * mean_gap, "reports are bunched into a few weeks")      # no long dry stretch
        per_day = n / 63
        self.assertGreater(per_day, 1.5)                                                       # a few every game day
        # and the first report of the lot is not far off
        self.assertLess(slots[0], 6 * mean_gap)

    def test_a_better_spread_than_chance(self):
        """The best-of-a-dozen draw leaves smaller holes than independent random times would."""
        e = make_engine(2)
        n = len([s for s in e.stocks.values() if s.earn_slot])
        slots = sorted(s.earn_slot - e.now for s in e.stocks.values() if s.earn_slot)
        worst = max(b - a for a, b in zip(slots, slots[1:]))
        rng = random.Random(3)
        randoms = []
        for _ in range(50):
            t = sorted(rng.uniform(0.005, 1.0) * QUARTER for _ in range(n))
            randoms.append(max(b - a for a, b in zip(t, t[1:])))
        self.assertLess(worst, sum(randoms) / len(randoms))

    def test_a_new_company_takes_a_quiet_slot(self):
        e = make_engine(4)
        taken = sorted(s.earn_slot for s in e.stocks.values() if s.earn_slot)
        picks = [e._pick_earnings_slot() for _ in range(200)]
        near = [min(abs(p - t) for t in taken) for p in picks]
        rng = random.Random(5)
        chance = [min(abs(e.now + rng.uniform(0.005, 1.0) * QUARTER - t) for t in taken) for _ in range(200)]
        self.assertGreater(sum(near) / 200, 1.1 * sum(chance) / 200)
        self.assertGreater(sum(near) / 200, 0.4 * QUARTER / len(taken))   # it lands well inside one of the biggest gaps

    def test_a_company_listed_while_running_gets_a_slot_in_the_next_quarter(self):
        e = make_engine(6)
        cfg = dict(next(c for c in e._read()[1].values() if c["ticker"] == "NVXA"), ticker="ZZEA", name="Newly Listed Co")
        cfg = {**cfg, **e.market_profiles["NVXA"]}                      # (the profile is what gives it revenue to report)
        e.now += 10
        e._list(cfg, initial=False)
        s = e.stocks["ZZEA"]
        self.assertGreater(s.next_earn, e.now)
        self.assertLessEqual(s.next_earn - e.now, QUARTER + 5)


class WindowTests(unittest.TestCase):
    def test_every_scheduled_report_is_before_the_open_or_after_the_close(self):
        e = sessions(7)
        times = [s.next_earn for s in e.stocks.values() if s.next_earn]
        self.assertGreater(len(times), 100)
        self.assertTrue(all(in_window(t) for t in times), [phase(t) for t in times if not in_window(t)][:5])
        # both windows are used, about equally
        pre = sum(1 for t in times if phase(t) < 300)
        self.assertGreater(pre / len(times), 0.3)
        self.assertLess(pre / len(times), 0.7)

    def test_reports_that_actually_happen_are_in_the_windows_and_a_quarter_apart(self):
        e = sessions(8)
        s = e.stocks["NVXA"]
        times = []
        for _ in range(14):
            e.now = s.next_earn + 1
            e._earnings()
            times.append(e.now)
        self.assertGreaterEqual(len(s.reports), 10)
        self.assertTrue(all(in_window(t - 1) for t in times))
        gaps = [b - a for a, b in zip(times, times[1:])]
        jitter = 4 * DAY
        for g in gaps:
            self.assertGreater(g, QUARTER - jitter - 2 * DAY)
            self.assertLess(g, QUARTER + jitter + 2 * DAY)
        self.assertGreater(max(gaps) - min(gaps), DAY)                    # but not exactly a quarter every time

    def test_no_report_ever_comes_out_in_the_regular_session(self):
        e = sessions(9, earnings_quarter_days=5)                           # short quarters so there are many reports
        seen = 0
        for _ in range(3000):
            nxt = min(s.next_earn for s in e.stocks.values() if s.next_earn)
            e.now = nxt + 0.5
            before = sum(len(s.reports) for s in e.stocks.values())
            e._earnings()
            after = sum(len(s.reports) for s in e.stocks.values())
            for _ in range(after - before):
                seen += 1
                self.assertTrue(in_window(nxt), phase(nxt))
        self.assertGreater(seen, 1500)

    def test_a_flat_market_or_a_short_demo_quarter_has_no_windows(self):
        flat = build(10, premarket_seconds=0, aftermarket_seconds=0)       # sessions off
        times = [s.next_earn for s in flat.stocks.values() if s.next_earn]
        self.assertFalse(all(in_window(t) for t in times))
        demo = sessions(11, earnings_quarter_days=0.01)                    # an 18-second quarter
        t = demo._snap_to_window(demo.now + 7)
        self.assertEqual(t, demo.now + 7)

    def test_only_pre_market_or_only_after_hours_still_works(self):
        e = build(12, premarket_seconds=300, aftermarket_seconds=0)
        for _ in range(200):
            self.assertLess(phase(e._snap_to_window(e.now + QUARTER * random.random())), 300)
        e = build(13, premarket_seconds=0, aftermarket_seconds=300)
        for _ in range(200):
            self.assertGreaterEqual(phase(e._snap_to_window(e.now + QUARTER * random.random())), DAY - 300)

    def test_a_snapped_time_is_never_in_the_past(self):
        e = sessions(14)
        e.now = (int(e.now // DAY) + 1) * DAY + 1000                      # mid-session
        for _ in range(300):
            self.assertGreater(e._snap_to_window(e.now - 600), e.now)


class SaveTests(unittest.TestCase):
    def test_the_slots_survive_a_restart_and_old_saves_are_moved_into_windows(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path = os.path.join(d, "state.json")
            random.seed(15)
            _helpers.engine.Engine._read = _helpers._real_read
            try:
                a = engine.Engine(state_file=path, bots=False)
                a.settings.update(premarket_seconds=300, aftermarket_seconds=300)
                a.tick(now=a.now)
                a.save()
                b = engine.Engine(state_file=path, bots=False)
                self.assertEqual({k: s.earn_slot for k, s in a.stocks.items()}, {k: s.earn_slot for k, s in b.stocks.items()})
                state = json.load(open(path, encoding="utf-8"))
                for v in state["stocks"].values():
                    v.pop("earn_slot", None)                                 # a save from before the calendar changed
                    if v.get("next_earn"):
                        v["next_earn"] = a.now + 5000 + random.random() * 40000
                json.dump(state, open(path, "w", encoding="utf-8"))
                c = engine.Engine(state_file=path, bots=False)
            finally:
                _helpers.engine.Engine._read = _helpers._flat_read
            times = [s.next_earn for s in c.stocks.values() if s.next_earn]
            self.assertGreater(len(times), 100)
            self.assertTrue(all(s.earn_slot for s in c.stocks.values() if s.next_earn))
            self.assertTrue(all(in_window(t) for t in times))


class ReportTextTests(unittest.TestCase):
    def test_the_earnings_headline_carries_no_hidden_information(self):
        e = make_engine(16)
        s = e.stocks["NVXA"]
        s.pending.append({"t": e.now, "text": "story", "why": "a supply-chain disruption", "dm": -0.05, "dr": 0.0, "dd": 0.0})
        e._report(s)
        text = next(n["text"] for n in reversed(e.news_log) if n["kind"] == "earnings")
        self.assertIn("Driven by a supply-chain disruption.", text)
        for bad in ("flagged", "earlier news", "beforehand", "pending"):
            self.assertNotIn(bad, text)
        s2 = e.stocks["OILX"]
        e._report(s2)                                                       # no stories behind it: it just says nothing
        text2 = next(n["text"] for n in reversed(e.news_log) if n["kind"] == "earnings")
        self.assertNotIn("Driven by", text2)
        for bad in ("flagged", "earlier news", "beforehand", "No major"):
            self.assertNotIn(bad, text2)
        self.assertNotIn("  ", text2)

    def test_the_dividend_date_is_honest_about_when_the_market_opens(self):
        e = sessions(17)
        s = e.stocks["OILX"]
        e.now = (int(e.now // DAY) + 1) * DAY + 100                           # pre-market: the open is 5 minutes later
        e._update_session()
        e._report(s)
        self.assertIn("going ex-dividend in 5 minutes", next(n["text"] for n in reversed(e.news_log) if n["kind"] == "earnings"))
        e.now = (int(e.now // DAY) + 1) * DAY + 1700                          # after-hours: it waits for the next open
        e._update_session()
        e._report(s)
        self.assertIn("when the market next opens", next(n["text"] for n in reversed(e.news_log) if n["kind"] == "earnings"))

    def test_nothing_in_a_long_run_of_news_mentions_how_the_game_works(self):
        e = make_engine(18, event_mean_seconds=3, issue_mean_seconds=3, cross_mean_seconds=5)
        advance(e, 1500)
        for s in list(e.stocks.values())[:30]:
            e._report(s)
        texts = [n["text"] for n in e.news_log]
        self.assertGreater(len(texts), 100)
        banned = re.compile(r"flagged|earlier news|beforehand|hidden|safety score|mood|regime", re.I)
        self.assertEqual([t for t in texts if banned.search(t)], [])


class BankNoteTests(unittest.TestCase):
    def test_about_two_notes_in_five_give_a_reason(self):
        random.seed(20)
        e = make_engine(20)
        notes = []
        for _ in range(40):
            for s in e.stocks.values():
                if s.asset_type == "equity":
                    s.next_rating_review = e.now - 1
                    s.rating = random.choice(engine.RATINGS)
            e._credit_reviews()
            notes += [x["text"] for x in e.news_log]
            e.news_log.clear()
        notes = [t for t in notes if re.search(r"(raises|lowers)( its)? price target", t)]
        self.assertGreater(len(notes), 800)
        share = sum(1 for t in notes if "citing" in t) / len(notes)
        self.assertGreater(share, 0.34)
        self.assertLess(share, 0.46)

    def test_a_reason_is_a_real_one_and_the_note_without_one_still_has_the_target(self):
        random.seed(21)
        e = make_engine(21)
        e.now += 1
        s = e.stocks["NVXA"]
        s.margin = s.base_margin * 0.5                                         # thin margins: a downgrade says why
        for _ in range(200):
            self.assertIn(e._review_reason(s, True), ("thinner margins", "leverage concerns", "continued cash burn",
                                                      "elevated volatility", "a more cautious outlook", "weaker earnings quality"))
        for _ in range(300):
            for st in e.stocks.values():
                if st.asset_type == "equity":
                    st.next_rating_review = e.now - 1
                    st.rating = "BBB"
            e._credit_reviews()
        plain = [n["text"] for n in e.news_log if re.search(r"price target (on|for) .* to \d+\.\d\d MB$", n["text"])]
        self.assertTrue(plain)


class CompanyPageTests(unittest.TestCase):
    def test_the_company_message_has_no_supplier_customer_or_rival(self):
        e = make_engine(22)
        msg = e.company_for("MRHS")
        self.assertEqual(set(msg["persona"]), {"ceo", "cfo", "product", "city", "former_ceos"})
        self.assertNotIn("Flagged", json.dumps(msg))


if __name__ == "__main__":
    unittest.main()
