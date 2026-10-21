"""The long price history (history.py, ROADMAP TA-A10) and the game-time candles built from it (TA-A11): game-day candles
cover the regular session only, so the overnight move shows as a gap; they are kept in history.db across restarts, a game
from before the file existed gets them rebuilt from its intraday candles, and the 1m chart reaches back into minutes.db."""
import os
import tempfile
import types
import unittest

import _helpers  # noqa: F401  (puts the game on sys.path)
from _helpers import advance, engine
import history

D = engine.MARKET_DAY_SECONDS


class StoreTests(unittest.TestCase):
    def test_candles_are_written_read_back_in_order_and_trimmed(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            st = history.CandleStore(os.path.join(tmp, "h.db"))
            for i in range(5):
                st.add("AAA", [i * 60, 1 + i, 2 + i, 0.5 + i, 1.5 + i, 10 * i])
            st.add("BBB", [0, 1, 1, 1, 1, 0])
            self.assertEqual(st.flush(), 6)
            self.assertEqual([c[0] for c in st.last("AAA", 3)], [120, 180, 240])          # the newest three, oldest first
            self.assertEqual([c[0] for c in st.last("AAA", 10, before=120)], [0, 60])
            st.add("AAA", [240, 9, 9, 9, 9, 9])                                             # the same start replaces it
            st.flush()
            self.assertEqual(st.last("AAA", 1)[0][1], 9)
            self.assertEqual(st.tickers(), {"AAA", "BBB"})
            st.prune(120)
            self.assertEqual([c[0] for c in st.last("AAA", 10)], [120, 180, 240])
            st.close()

    def test_aggregate_and_regular_session_days(self):
        rows = [[0, 1, 2, 0.5, 1.5, 1], [60, 1.5, 3, 1, 2, 2], [120, 2, 2.5, 0.2, 0.4, 3]]
        self.assertEqual(history.aggregate(rows, lambda t: 0), [[0, 1, 3, 0.2, 0.4, 6]])
        # five-minute candles of two game days: only the regular session (300 to 1499 s into the day) counts
        five = [[d * D + k * 300, 10 + k, 11 + k, 9 + k, 10.5 + k, 1] for d in (0, 1) for k in range(6)]
        days = history.days_from_intraday(five, D, 300, 300)
        self.assertEqual([c[0] for c in days], [0, D])
        self.assertEqual(days[0][1:], [11, 15, 10, 14.5, 4])          # open of 300 s, close of the 1200 s candle


class GameDayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, state=True, now=None):
        clock = engine.time
        if now is not None:                                # (a restart later in the game: the engine starts at `now`)
            engine.time = types.SimpleNamespace(time=lambda: now)
        try:
            e = engine.Engine(state_file=os.path.join(self.dir, "state.json") if state else None,
                              history_path=os.path.join(self.dir, "history.db"),
                              minutes_path=os.path.join(self.dir, "minutes.db"))
        finally:
            engine.time = clock
        e.settings.update(premarket_seconds=300, aftermarket_seconds=300)
        return e

    def test_a_game_day_candle_is_the_regular_session_and_the_overnight_move_is_a_gap(self):
        e = self.make()
        start = (int(e.now // D) + 1) * D                  # the next game day, from its pre-market
        e.tick(now=start - 1)
        seen = {}
        for i in range(3 * D + 400):
            now = start + i
            e.tick(now=now)
            phase = (now % D)
            if phase == 300:                               # the first second of the regular session
                seen.setdefault(now // D, {})["open"] = e.stocks["NVXA"].price
            if phase == 1499:
                seen.setdefault(now // D, {})["close"] = e.stocks["NVXA"].price
        s = e.stocks["NVXA"]
        self.assertEqual([c[0] for c in s.days], [start, start + D, start + 2 * D])
        for c in s.days:
            day = c[0] // D
            self.assertAlmostEqual(c[1], seen[day]["open"], places=6)
            self.assertAlmostEqual(c[4], seen[day]["close"], places=6)
            self.assertGreaterEqual(c[2], max(c[1], c[4]))
            self.assertLessEqual(c[3], min(c[1], c[4]))
            self.assertGreater(c[5], 0)
        self.assertIsNotNone(s.reg)                       # day four's session is under way
        gaps = [abs(b[1] / a[4] - 1) for a, b in zip(s.days, list(s.days)[1:])]
        self.assertTrue(all(g > 0 for g in gaps))          # the next open is not the last close
        # the chart: days (with today's session last), weeks and months of the game calendar
        ch = e.chart_for("NVXA", "gd")
        self.assertEqual([c["t"] for c in ch["candles"]], [start, start + D, start + 2 * D, start + 3 * D])
        self.assertEqual(ch["game_day0"], engine.GAME_DAY0)
        for period, step in (("gw", 7), ("gm", 28)):
            agg = e.chart_for("NVXA", period)["candles"]
            self.assertTrue(1 <= len(agg) <= 2)
            first = agg[0]["t"] // D
            if period == "gw":
                self.assertEqual(engine.game_date(first).weekday(), 0)        # a game week starts on a Monday
            else:
                self.assertEqual(engine.game_date(first).day, 1)              # a game month on the 1st
            self.assertEqual(agg[-1]["c"], ch["candles"][-1]["c"])
        # the file keeps them: a restart reads them back, and today's session goes on
        e.save(full=True)
        e.close_stores()
        e2 = self.make(now=e.now + 5)
        s2 = e2.stocks["NVXA"]
        self.assertEqual([c[0] for c in s2.days], [start, start + D, start + 2 * D])
        self.assertEqual(s2.reg[0], start + 3 * D)
        # a restart in the after-hours: today's finished candle comes back from the file
        e2.tick(now=e.now + 6)
        for i in range(7, 1300):
            e2.tick(now=e.now + i)
        self.assertIsNone(s2.reg)
        e2.save(full=True)
        e2.close_stores()
        e3 = self.make(now=e2.now + 1)
        self.assertEqual([c[0] for c in e3.stocks["NVXA"].days][-2:], [start + 2 * D, start + 3 * D])
        e3.close_stores()

    def test_the_one_minute_chart_reaches_back_into_the_minute_file(self):
        e = self.make(state=False)
        e.settings.update(premarket_seconds=0, aftermarket_seconds=0)
        for k in e.stocks.values():
            k.tf["1m"] = type(k.tf["1m"])(maxlen=20)       # (a short in-memory window, so the file has to fill the rest)
        advance(e, 60 * 45)
        rows = e.chart_for("NVXA", "1m")["candles"]
        self.assertGreaterEqual(len(rows), 44)
        ts = [c["t"] for c in rows]
        self.assertEqual(ts, sorted(set(ts)))              # no minute twice, oldest first
        self.assertTrue(all(b - a == 60 for a, b in zip(ts, ts[1:])))
        e.close_stores()

    def test_a_game_from_before_the_history_file_gets_its_days_rebuilt(self):
        e = engine.Engine(state_file=None)
        e.settings.update(premarket_seconds=300, aftermarket_seconds=300)
        s = e.stocks["NVXA"]
        base = (int(e.now // D) - 3) * D
        for k in ("5m", "30m"):
            s.tf[k].clear()
        for d in range(3):
            s.tf["30m"].append([base + d * D, 10, 12, 8, 11, 100])
            for k in range(6):
                s.tf["5m"].append([base + d * D + k * 300, 10 + k, 10.5 + k, 9.5 + k, 10 + k, 5])
        e._load_days()
        self.assertEqual([c[0] for c in s.days], [base, base + D, base + 2 * D])
        self.assertEqual(s.days[0][1], 11)                 # from the 5-minute candles: the regular session's open


if __name__ == "__main__":
    unittest.main()
