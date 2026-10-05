"""Saving the game: the chart candles live in their own file that the periodic save rewrites only now and then, so a save
on a long-running game stays fast, and nothing is lost by restarting."""
import json
import os
import random
import tempfile
import time
import unittest

from _helpers import advance, engine, join

import accounts


def new_engine(path, seed=1):
    random.seed(seed)
    e = engine.Engine(state_file=path)
    e.settings.update(premarket_seconds=0, aftermarket_seconds=0)
    return e


class ContentFilesTests(unittest.TestCase):
    """Every .json file in the project folder is a content pack, except the save and its chart file. (The chart file is
    tens of MB and is rewritten while the game runs; reading it as a pack made each chart save look like a content change
    and could fail while the file was being replaced.)"""

    def files_for(self, state_name):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            for name in ("base.json", "pack.json", "state.json", "state.charts.json", "my.json", "my.charts.json"):
                with open(os.path.join(d, name), "w") as fh:
                    fh.write("{}")
            e = engine.Engine.__new__(engine.Engine)
            e.content_glob = os.path.join(d, "*.json")
            e.state_file = None if state_name is None else os.path.join(d, state_name)
            cwd = os.getcwd()
            os.chdir(d)                                   # (the default save name is read relative to the folder)
            try:
                return sorted(os.path.basename(f) for f in e._content_files())
            finally:
                os.chdir(cwd)

    def test_the_default_save_and_its_charts_are_not_content(self):
        self.assertEqual(self.files_for("state.json"), ["base.json", "my.charts.json", "my.json", "pack.json"])

    def test_with_no_save_file_the_default_names_are_still_skipped(self):
        self.assertEqual(self.files_for(None), ["base.json", "my.charts.json", "my.json", "pack.json"])

    def test_a_save_with_another_name_is_skipped_with_its_charts(self):
        self.assertEqual(self.files_for("my.json"), ["base.json", "pack.json"])

    def test_rewriting_the_chart_file_does_not_change_the_content_signature(self):
        e = engine.Engine(state_file=None)
        before = e._sig()
        charts = os.path.abspath("state.charts.json")
        self.assertNotIn(charts, [os.path.abspath(f) for f, _ in before])


class ChartFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = os.path.join(self.tmp.name, "state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_full_save_writes_the_core_and_the_charts_separately(self):
        e = new_engine(self.path)
        advance(e, 200)
        e.save()
        core = json.load(open(self.path, encoding="utf-8"))
        charts = json.load(open(e._charts_path(), encoding="utf-8"))
        self.assertTrue(all("tf" not in v for v in core["stocks"].values()))
        self.assertTrue(all("candles" in v for v in core["stocks"].values()))          # the minute candles stay in the core
        self.assertEqual(set(charts["tf"]), set(core["stocks"]))
        self.assertEqual(set(charts["tf"]["NVXA"]), set(engine.TIMEFRAMES))

    def test_the_periodic_save_only_rewrites_the_charts_when_they_are_due(self):
        e = new_engine(self.path)
        advance(e, 60)
        e.save()
        stamp = os.path.getmtime(e._charts_path())
        saved = e._charts_saved
        advance(e, 60)
        e.save(full=False)
        self.assertEqual(e._charts_saved, saved)                                      # not due yet
        self.assertEqual(os.path.getmtime(e._charts_path()), stamp)
        e.now += 301
        e.save(full=False)
        self.assertGreater(e._charts_saved, saved)                                    # now it is

    def test_charts_survive_a_restart_exactly(self):
        e = new_engine(self.path)
        advance(e, 400)
        e.save()
        before = {t: {k: [list(c) for c in v] for k, v in s.tf.items()} for t, s in e.stocks.items()}
        f = new_engine(self.path)
        # (the test clock ran ahead of the real clock, so the restarted game adds one candle at the real "now": ignore it)
        for t, frames in before.items():
            for k, rows in frames.items():
                self.assertEqual([list(c) for c in f.stocks[t].tf[k]][:len(rows)], rows, (t, k))

    def test_a_stale_chart_file_is_brought_up_to_date_from_the_minute_candles(self):
        e = new_engine(self.path)
        advance(e, 130)
        e.save()                                                                      # charts as of now
        advance(e, 300)
        e.save(full=False)                                                            # the core moves on, the charts do not
        live = {t: [list(c) for c in s.tf["1m"]] for t, s in e.stocks.items()}
        f = new_engine(self.path)
        for t, rows in live.items():
            got = [list(c) for c in f.stocks[t].tf["1m"]]
            self.assertEqual(got[:len(rows)], rows, t)                                # every recent candle is there
        self.assertIn(e.stocks["NVXA"].tf["5m"][-1][0], {c[0] for c in f.stocks["NVXA"].tf["5m"]})

    def test_a_missing_or_broken_chart_file_does_not_stop_the_game_loading(self):
        e = new_engine(self.path)
        advance(e, 200)
        e.save()
        with open(e._charts_path(), "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        f = new_engine(self.path)
        self.assertGreater(len(f.stocks["NVXA"].tf["1m"]), 0)                         # rebuilt from the minute candles
        os.remove(e._charts_path())
        g = new_engine(self.path)
        self.assertGreater(len(g.stocks["NVXA"].tf["5m"]), 0)

    def test_a_save_from_before_the_chart_file_still_loads_its_inline_charts(self):
        e = new_engine(self.path)
        advance(e, 200)
        e.save()
        core = json.load(open(self.path, encoding="utf-8"))
        charts = json.load(open(e._charts_path(), encoding="utf-8"))["tf"]
        for t, v in core["stocks"].items():
            v["tf"] = charts[t]
        json.dump(core, open(self.path, "w", encoding="utf-8"))
        os.remove(e._charts_path())
        f = new_engine(self.path)
        want = [list(c) for c in e.stocks["NVXA"].tf["30s"]]
        self.assertEqual([list(c) for c in f.stocks["NVXA"].tf["30s"]][:len(want)], want)

    def test_players_and_money_round_trip_with_the_core_file_alone(self):
        e = new_engine(self.path)
        p = join(e, "saver")
        e.trade(p, "CLDR", "buy", 0.5)
        e.save(full=False)
        f = new_engine(self.path)
        p2 = next(x for x in f.players.values() if x.name == "saver")
        self.assertAlmostEqual(p2.hold["CLDR"], p.hold["CLDR"])

    def test_the_core_save_is_much_smaller_and_faster_than_the_charts(self):
        e = new_engine(self.path)
        advance(e, 600)
        t0 = time.perf_counter()
        e.save(full=False)
        quick = time.perf_counter() - t0
        e.save()
        self.assertLess(os.path.getsize(self.path), os.path.getsize(e._charts_path()))
        self.assertLess(quick, 5.0)


class LockedFileTests(unittest.TestCase):
    """Windows can refuse to replace a file that OneDrive or a scanner has open for a moment ("Access is denied")."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = os.path.join(self.tmp.name, "state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_briefly_locked_file_is_retried_and_the_save_succeeds(self):
        from unittest import mock
        e = new_engine(self.path)
        real = os.replace
        calls = {"n": 0}

        def flaky(src, dst):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise PermissionError(5, "Access is denied")
            return real(src, dst)
        with mock.patch("engine.os.replace", flaky), mock.patch("engine._sleep", lambda s: None):
            e.save()
        self.assertGreater(calls["n"], 2)
        self.assertTrue(os.path.exists(self.path))
        self.assertTrue(os.path.exists(e._charts_path()))

    def test_a_file_that_stays_locked_does_not_crash_the_tick_and_the_charts_retry_soon(self):
        from unittest import mock
        e = new_engine(self.path)
        advance(e, 5)
        e.save()
        e.now += 400
        with mock.patch("engine.os.replace", side_effect=PermissionError(5, "Access is denied")),                 mock.patch("engine._sleep", lambda s: None):
            e.save(full=False)                                   # must not raise
        self.assertGreaterEqual(e.now - e._charts_saved, 300 - 30 - 1)   # due again within half a minute
        e.now += 31
        e.save(full=False)
        self.assertLess(e.now - e._charts_saved, 5)


if __name__ == "__main__":
    unittest.main()
