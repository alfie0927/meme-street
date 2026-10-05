"""One-day seasons, the 2x and 3x products, the migration of old saves, share offerings (only the share count changes),
no stock splits, and delisted stocks that stay viewable."""
import json
import os
import random
import tempfile
import unittest
from unittest import mock

from _helpers import advance, drift, engine, join, make_engine, quiet

DAY = engine.MARKET_DAY_SECONDS


class SeasonTests(unittest.TestCase):
    def test_a_season_is_one_real_day_ending_at_midnight_utc(self):
        e = make_engine(1)
        self.assertEqual(e.settings["season_seconds"], 86400)
        self.assertEqual(e.season_end % 86400, 0)
        self.assertGreater(e.season_end, e.now)
        self.assertLessEqual(e.season_end - e.now, 86400)

    def test_the_next_season_also_ends_at_midnight_and_balances_carry_over(self):
        e = make_engine(2)
        p = join(e, "daily1")
        e.trade(p, "GOLD", "buy", 0.3)
        end = e.season_end
        e.now = end + 1
        e.tick(now=end + 1)
        self.assertEqual(e.season_no, 2)
        self.assertEqual(e.season_end, end + 86400)
        self.assertAlmostEqual(p.season_base, e.equity(p), delta=1e-6)

    def test_a_day_in_a_save_that_does_not_end_at_midnight_is_realigned_when_it_loads(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(4)
            e = engine.Engine(state_file=path, bots=False)
            e.season_end = e.now + 1.9 * 86400                              # (a day that started at an odd moment)
            e.save()
            f = engine.Engine(state_file=path, bots=False)
            self.assertEqual(f.season_end % 86400, 0)
            self.assertLessEqual(f.season_end - f.now, 86400)
            e.season_end = e.now + 600                                      # an old one-hour season is left alone
            e.save()
            g = engine.Engine(state_file=path, bots=False)
            self.assertAlmostEqual(g.season_end - e.now, 600, delta=1)

    def test_old_runaway_splits_are_undone_when_a_save_loads(self):
        """The old split code could split a stock again and again until its price was 1e-22 (shown as 0.0000 MB)."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(9)
            e = engine.Engine(state_file=path, bots=False)
            p = join(e, "splitholder")
            e.trade(p, "CLDR", "buy", 0.5)
            advance(e, 130)
            price, equity, shares = e.stocks["CLDR"].price, e.equity(p), p.hold["CLDR"]
            e.save()
            f = 1e12
            d = json.load(open(path, encoding="utf-8"))
            v = d["stocks"]["CLDR"]
            for key in ("fair", "fair_open", "day_open", "day_high", "day_low", "dps", "base_dps"):
                v[key] = v[key] / f
            v["candles"] = [[c[0]] + [x / f for x in c[1:]] for c in v["candles"]]
            v["split_factor"] = f
            x = next(q for q in d["players"] if q["name"] == "splitholder")
            x["hold"]["CLDR"] *= f
            json.dump(d, open(path, "w", encoding="utf-8"))
            ch = os.path.splitext(path)[0] + ".charts.json"
            charts = json.load(open(ch, encoding="utf-8"))
            charts["tf"]["CLDR"] = {k: [[c[0]] + [y / f for y in c[1:]] for c in rows] for k, rows in charts["tf"]["CLDR"].items()}
            json.dump(charts, open(ch, "w", encoding="utf-8"))
            g = engine.Engine(state_file=path, bots=False)
            s = g.stocks["CLDR"]
            self.assertEqual(s.split_factor, 1.0)
            self.assertAlmostEqual(s.price / price, 1.0, places=6)
            self.assertAlmostEqual(s.tf["1m"][0][1] / e.stocks["CLDR"].tf["1m"][0][1], 1.0, places=6)
            p2 = next(q for q in g.players.values() if q.name == "splitholder")
            self.assertAlmostEqual(p2.hold["CLDR"] / shares, 1.0, places=6)
            self.assertAlmostEqual(g.equity(p2) / equity, 1.0, places=5)
            self.assertLess(abs(drift(g)), 1e-6)

    def test_the_daily_tournament_and_the_season_share_their_boundaries(self):
        e = make_engine(3)
        e._social_t = 0
        e._social_tick()
        marathon = next(t for t in e.tournaments if t["kind"] == "marathon")
        self.assertEqual(marathon["end"], e.season_end)

    def test_the_length_can_be_changed(self):
        e = make_engine(4, season_seconds=3600)
        e.now = 3600 * 1000 + 5
        self.assertEqual(e._season_boundary(), 3600 * 1001)


class LeveragedProductTests(unittest.TestCase):
    def test_the_products_are_2x_and_3x_long_and_short_and_the_1x_bear_is_gone(self):
        e = make_engine(5)
        for tk, lev in (("2LMSI", 2.0), ("2SMSI", -2.0), ("3LMSI", 3.0), ("3SMSI", -3.0)):
            s = e.stocks[tk]
            self.assertEqual(s.spec["kind"], "leveraged")
            self.assertEqual(s.spec["leverage"], lev)
            self.assertEqual(s.spec["of"], "MSI")
        self.assertEqual([s.name for s in (e.stocks["2LMSI"], e.stocks["2SMSI"], e.stocks["3LMSI"], e.stocks["3SMSI"])],
                         ["2x Long MSI", "2x Short MSI", "3x Long MSI", "3x Short MSI"])
        for gone in ("BULL2", "BEAR1", "BEAR2"):
            self.assertNotIn(gone, e.stocks)

    def test_a_3x_product_moves_three_times_the_index_each_second(self):
        e = make_engine(6)
        before = {tk: e.stocks[tk].price for tk in ("MSI", "3LMSI", "3SMSI")}
        e.tick(now=e.now + 1)
        r = e.stocks["MSI"].price / before["MSI"] - 1
        self.assertAlmostEqual(e.stocks["3LMSI"].price / before["3LMSI"] - 1, 3 * r, places=6)
        self.assertAlmostEqual(e.stocks["3SMSI"].price / before["3SMSI"] - 1, -3 * r, places=6)

    def test_a_3x_product_is_riskier_so_it_needs_more_margin_to_short(self):
        e = make_engine(7)
        self.assertGreater(e.margin_req(e.stocks["3LMSI"]), e.margin_req(e.stocks["2LMSI"]))
        self.assertGreater(e.stocks["3LMSI"].vol, e.stocks["2LMSI"].vol)

    def test_they_trade_and_conserve_money(self):
        e = make_engine(8)
        p = join(e, "lev3")
        for tk in ("3LMSI", "3SMSI", "2LMSI", "2SMSI"):
            e.now += 2
            self.assertTrue(e.trade(p, tk, "buy", 0.2)[0], tk)
        advance(e, 120)
        self.assertLess(abs(drift(e)), 1e-6)


class MigrationTests(unittest.TestCase):
    def old_save(self, tmp):
        """A saved game as the old code wrote it: BULL2, BEAR1 and BEAR2 held by two players."""
        path = os.path.join(tmp, "state.json")
        random.seed(11)
        e = engine.Engine(state_file=path, bots=False)
        a, b = join(e, "longer"), join(e, "shorter")
        for tk, new in (("2LMSI", "BULL2"), ("2SMSI", "BEAR2")):
            e.trade(a, tk, "buy", 0.2)
            e.now += 2
        e.trade(b, "2SMSI", "sell", 0.3)                       # b is short the inverse product
        e.now += 2
        e.tick(now=e.now + 1)
        e.save()
        d = json.load(open(path, encoding="utf-8"))
        # rewrite the save the way the old code would have: old tickers, and BEAR1 held by both players
        bear1_price = d["stocks"]["2SMSI"]["fair"] / 2
        d["stocks"]["BEAR1"] = dict(d["stocks"]["2SMSI"], fair=bear1_price)
        for x in d["players"]:
            if x["name"] == "longer":
                x["hold"]["BEAR1"], x["cost"]["BEAR1"] = 10.0, 10.0 * bear1_price
                x["cash"] -= 10.0 * bear1_price
                d["house"] += 10.0 * bear1_price
            if x["name"] == "shorter":
                x["hold"]["BEAR1"], x["cost"]["BEAR1"] = -5.0, 5.0 * bear1_price
                x["cash"] += 5.0 * bear1_price
                d["house"] -= 5.0 * bear1_price
        for old, new in (("BULL2", "2LMSI"), ("BEAR2", "2SMSI")):
            d["stocks"][old] = d["stocks"].pop(new)
            for x in d["players"]:
                for key in ("hold", "cost", "entry_fee", "realized", "divs", "borrow"):
                    if new in x.get(key, {}):
                        x[key][old] = x[key].pop(new)
                for entry in x.get("log", []):
                    if entry["tk"] == new:
                        entry["tk"] = old
        json.dump(d, open(path, "w", encoding="utf-8"))
        return path, d

    def test_an_old_save_gets_the_new_tickers_and_a_withdrawn_product_is_paid_out(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path, d = self.old_save(tmp)
            long_before = next(x for x in d["players"] if x["name"] == "longer")
            cash_before = long_before["cash"]
            random.seed(12)
            e = engine.Engine(state_file=path, bots=False)
            quiet(e)
            a = next(p for p in e.players.values() if p.name == "longer")
            b = next(p for p in e.players.values() if p.name == "shorter")
            self.assertIn("2LMSI", a.hold)
            self.assertIn("2SMSI", a.hold)
            self.assertLess(b.hold["2SMSI"], 0)                                   # the short moved across too
            self.assertNotIn("BULL2", a.hold)
            self.assertNotIn("BEAR1", a.hold)
            self.assertNotIn("BEAR1", b.hold)
            self.assertGreater(a.cash, cash_before)                               # BEAR1 was paid out in cash
            self.assertTrue(any(l["tk"] == "2LMSI" for l in a.log))
            self.assertLess(abs(drift(e)), 1e-6)
            self.assertIn("BEAR1", e.archive)                                      # and its page can still be opened
            self.assertEqual(e.company_for("BEAR1")["delisted"]["reason"], "withdrawn")
            e.save()
            again = engine.Engine(state_file=path, bots=False)                     # a second start changes nothing
            self.assertLess(abs(drift(again)), 1e-6)
            self.assertIn("BEAR1", again.archive)

    def test_old_ledger_events_with_old_tickers_are_replayed_under_the_new_ones(self):
        e = make_engine(13)
        p = join(e, "replay1")
        before = p.cash
        ev = {"kind": "buy", "ticker": "BULL2", "extra": {}, "token": p.token, "cash_delta": -50.0, "house_delta": 49.75,
              "fee": 0.25, "shares": 1.0, "cost_delta": 49.75, "pnl": None, "t": e.now, "price": 49.75, "notional": 50.0}
        e._apply_event(ev)
        self.assertAlmostEqual(p.cash, before - 50.0)
        self.assertIn("2LMSI", p.hold)
        self.assertNotIn("BULL2", p.hold)
        before = dict(p.hold)
        e._apply_event(dict(ev, ticker="BEAR1"))                                   # a withdrawn product's event is ignored
        self.assertEqual(p.hold, before)

    def test_old_links_to_a_renamed_product_redirect(self):
        # (the server's /stock/{ticker} route redirects using this table; the server module itself is never imported
        # by a test, because importing it builds an engine on the real save file)
        self.assertEqual(engine.TICKER_RENAMES, {"BULL2": "2LMSI", "BEAR2": "2SMSI"})


class OfferingTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(21)
        self.s = self.e.stocks["CLDR"]

    def fire(self):
        """Announce an offering by CLDR now."""
        e = self.e
        e.next_offering = e.now
        with mock.patch.object(engine.random, "choice", return_value=self.s):
            e._offerings()

    def test_it_is_announced_in_the_news_and_settles_a_few_minutes_later(self):
        e, s = self.e, self.s
        n0 = len(e.news_log)
        self.fire()
        self.assertIsNotNone(s.offering)
        item = e.news_log[-1]
        self.assertEqual(item["kind"], "offering")
        self.assertIn("announces a public offering", item["text"])
        self.assertIn(s.name, item["text"])
        self.assertEqual(item["tickers"], ["CLDR"])
        shares = s.shares_outstanding
        e.now += 100
        e._offerings()
        self.assertEqual(s.shares_outstanding, shares)                             # not yet
        e.now += 400
        e._offerings()
        self.assertGreater(s.shares_outstanding, shares)                           # now it has settled
        self.assertIsNone(s.offering)
        done = next(n for n in reversed(e.news_log) if "completes its share offering" in n["text"])
        self.assertEqual(done["tickers"], ["CLDR"])
        self.assertGreaterEqual(len(e.news_log), n0 + 2)

    def test_only_the_number_of_shares_changes(self):
        e, s = self.e, self.s
        before = (s.fair, s.revenue, s.margin, s.cash, s.debt, s.dps, s.initial_price, dict(e._pending),
                  e.stocks["MSI"].price, list(s.pending))
        shares = s.shares_outstanding
        self.fire()
        e.now += 400
        e._offerings()
        after = (s.fair, s.revenue, s.margin, s.cash, s.debt, s.dps, s.initial_price, dict(e._pending),
                 e.stocks["MSI"].price, list(s.pending))
        self.assertEqual(before, after)                                           # no price move, no cash, no news effect
        self.assertGreater(s.shares_outstanding, shares * 1.0099)
        self.assertLess(s.shares_outstanding, shares * 1.0401)                    # 1% to 4% new shares
        self.assertAlmostEqual(s.shares_outstanding, s._raw_shares * s.split_factor * s.share_adj, delta=1e-12)

    def test_market_cap_rises_and_earnings_per_share_falls(self):
        e, s = self.e, self.s
        e._public()
        row = next(r for r in e.pub_stocks if r["ticker"] == "CLDR")
        cap0, eps0 = row["financials"]["market_cap"], row["financials"]["eps"]
        self.fire()
        e.now += 400
        e._offerings()
        e._public()
        row = next(r for r in e.pub_stocks if r["ticker"] == "CLDR")
        self.assertGreater(row["financials"]["market_cap"], cap0)
        self.assertLess(row["financials"]["eps"], eps0)
        self.assertEqual(row["price"], round(s.price, 4))

    def test_positions_dividends_and_money_are_untouched(self):
        e, s = self.e, self.s
        p = join(e, "holder1")
        e.trade(p, "CLDR", "buy", 0.3)
        held, cash, value = p.hold["CLDR"], p.cash, e.equity(p)
        self.fire()
        e.now += 400
        e._offerings()
        self.assertEqual(p.hold["CLDR"], held)
        self.assertEqual(p.cash, cash)
        self.assertAlmostEqual(e.equity(p), value, places=9)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_pending_offering_survives_a_restart_and_a_reload(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(22)
            e = engine.Engine(state_file=path, bots=False)
            s = e.stocks["CLDR"]
            s.offering = {"t": e.now + 600, "pct": 0.02}
            e.save()
            f = engine.Engine(state_file=path, bots=False)
            self.assertEqual(f.stocks["CLDR"].offering, {"t": s.offering["t"], "pct": 0.02})
            f.now = s.offering["t"] + 1
            shares = f.stocks["CLDR"].shares_outstanding
            f._offerings()
            self.assertAlmostEqual(f.stocks["CLDR"].shares_outstanding, shares * 1.02, delta=shares * 1e-9)
            f.content_sig = None
            f.tick(now=f.now + 1)                                                   # a content reload keeps the new count
            self.assertAlmostEqual(f.stocks["CLDR"].shares_outstanding, shares * 1.02, delta=shares * 1e-9)

    def test_they_arrive_over_time_one_at_a_time_and_only_for_reporting_companies(self):
        e = make_engine(23, offering_mean_seconds=5)
        e.next_offering = e.now
        seen = set()
        for _ in range(400):
            e.tick(now=e.now + 1)
            for s in e.stocks.values():
                if s.offering:
                    seen.add(s.ticker)
                    self.assertGreater(s.revenue, 0)
                    self.assertEqual(s.asset_type, "equity")
        self.assertGreater(len(seen), 10)
        announcements = [n for n in e.news_log if n["kind"] == "offering" and "announces" in n["text"]]
        self.assertGreater(len(announcements), 10)

    def test_an_offering_is_no_longer_a_price_moving_company_story(self):
        import newsgen
        self.assertNotIn("offering", {k["key"] for k in newsgen.ISSUE_KINDS})

    def test_the_price_is_the_same_with_or_without_offerings(self):
        """Offerings draw random numbers, so compare their effect directly: a settled offering leaves every price alone."""
        e = self.e
        prices = {tk: s.fair for tk, s in e.stocks.items()}
        for tk in ("CLDR", "NVXA", "OILX"):
            e.stocks[tk].offering = {"t": e.now - 1, "pct": 0.03}
        e._offerings()
        self.assertEqual(prices, {tk: s.fair for tk, s in e.stocks.items()})


class NoSplitTests(unittest.TestCase):
    def test_stock_splits_do_not_exist(self):
        for name in ("_check_splits", "_apply_split", "_split_ratio_for"):
            self.assertFalse(hasattr(engine.Engine, name), name)

    def test_a_stock_that_has_run_up_a_long_way_does_not_split(self):
        e = make_engine(31)
        s = e.stocks["NVXA"]
        s.fair = s.initial_price * 8
        shares = s.shares_outstanding
        for _ in range(5):
            e.tick(now=e.now + 1)
        self.assertEqual(s.shares_outstanding, shares)
        self.assertGreater(s.price, s.initial_price * 5)
        self.assertFalse(any(n["kind"] == "split" for n in e.news_log))

    def test_the_wire_has_no_split_fields(self):
        e = make_engine(32)
        p = join(e, "nosplit")
        e._public()
        row = next(r for r in e.state_for(p)["stocks"] if r["ticker"] == "NVXA")
        self.assertNotIn("split_factor", row)
        self.assertNotIn("split_pending", row)

    def test_an_old_pending_split_is_dropped_on_load(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(33)
            e = engine.Engine(state_file=path, bots=False)
            e.save()
            d = json.load(open(path, encoding="utf-8"))
            d["stocks"]["NVXA"]["split"] = {"t": e.now - 1, "ratio": 2}
            json.dump(d, open(path, "w", encoding="utf-8"))
            f = engine.Engine(state_file=path, bots=False)
            shares = f.stocks["NVXA"].shares_outstanding
            f.tick(now=f.now + 5)
            self.assertEqual(f.stocks["NVXA"].shares_outstanding, shares)


class DelistedStockTests(unittest.TestCase):
    def bankrupt(self, e, tk):
        s = e.stocks[tk]
        s.fair = s.initial_price * 0.1
        s.distress_checked = False
        with mock.patch.object(engine.random, "random", return_value=0.0):
            e._check_distress()

    def test_a_bankrupt_company_keeps_its_page_and_chart(self):
        e = make_engine(41)
        advance(e, 90)
        self.bankrupt(e, "NVXA")
        self.assertNotIn("NVXA", e.stocks)
        self.assertIn("NVXA", e.archive)
        c = e.company_for("NVXA")
        d = c["delisted"]
        self.assertEqual(d["reason"], "bankruptcy")
        self.assertEqual(d["name"], "Novaxis Chips")
        self.assertGreater(d["final_price"], 0)
        self.assertTrue(c["persona"]["ceo"])
        self.assertTrue(c["log"])                                                  # its news is kept
        h = e.chart_for("NVXA", "1m")
        self.assertTrue(h["delisted"])
        self.assertGreater(len(h["candles"]), 1)
        self.assertEqual(set(h["candles"][0]), {"t", "o", "h", "l", "c"})
        other = e.chart_for("NVXA", "15m")                                         # a timeframe that was not kept falls back
        self.assertGreater(len(other["candles"]), 1)

    def test_an_unknown_ticker_is_still_unknown_and_an_old_delisting_says_so(self):
        e = make_engine(42)
        self.assertFalse(e.company_for("NOPE")["delisted"])
        e.delisted.append("OLDONE")                                                # delisted before the archive existed
        self.assertIs(e.company_for("OLDONE")["delisted"], True)
        self.assertIn("error", e.chart_for("OLDONE", "1m"))

    def test_the_archive_is_saved_loaded_and_capped(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = os.path.join(tmp, "state.json")
            random.seed(43)
            e = engine.Engine(state_file=path, bots=False)
            advance(e, 130)                                                       # (over a minute, so more than one candle)
            self.bankrupt(e, "OILX")
            e.save()
            f = engine.Engine(state_file=path, bots=False)
            self.assertIn("OILX", f.archive)
            self.assertNotIn("OILX", f.stocks)
            self.assertEqual(f.company_for("OILX")["delisted"]["name"], "Ostrava Oil")
            self.assertGreater(len(f.chart_for("OILX", "1m")["candles"]), 1)
            for i in range(engine.ARCHIVE_MAX + 5):
                f.archive[f"X{i}"] = dict(f.archive["OILX"], ticker=f"X{i}", delisted_at=i)
            f._archive_stock(e.stocks["CLDR"], "bankruptcy", 10.0)
            self.assertLessEqual(len(f.archive), engine.ARCHIVE_MAX)
            self.assertIn("CLDR", f.archive)                                      # the newest is kept, the oldest dropped

    def test_holders_were_paid_and_money_is_conserved(self):
        e = make_engine(44)
        p = join(e, "holder2")
        e.trade(p, "NVXA", "buy", 0.3)
        self.bankrupt(e, "NVXA")
        self.assertNotIn("NVXA", p.hold)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_moonshot_that_fails_is_archived_too(self):
        from test_wild import real_engine
        e = real_engine(45)
        moon = next(s for s in e.stocks.values() if s.moonshot)
        self.bankrupt(e, moon.ticker)
        self.assertIn(moon.ticker, e.archive)
        self.assertEqual(e.company_for(moon.ticker)["delisted"]["name"], moon.name)


if __name__ == "__main__":
    unittest.main()
