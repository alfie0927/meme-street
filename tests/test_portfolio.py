"""The portfolio page's data (equity curve, allocation, realised vs unrealised profit, best and worst trades) and the
trade history (paging, filters, CSV export)."""
import csv
import io
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, quiet

FEE = engine.FEE


def make(tmp, seed=1, ledger=True):
    random.seed(seed)
    e = engine.Engine(state_file=os.path.join(tmp, "state.json"), bots=False,
                      ledger_path=os.path.join(tmp, "ledger.db") if ledger else None)
    e.tick(now=e.now)
    quiet(e)
    return e


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.e = make(self.tmp.name, 31)
        self.p = join(self.e, "folio1")

    def tearDown(self):
        if self.e.ledger:
            self.e.ledger.close()
        self.tmp.cleanup()

    def trade_story(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.3)                        # a winner
        e.now += 2
        e.trade(p, "GOLD", "buy", 0.2)                        # a loser
        e.now += 2
        e.trade(p, "NVXA", "sell", 0.2)                       # a short that wins
        e.now += 2
        e.stocks["CLDR"].fair *= 1.25
        e.stocks["GOLD"].fair *= 0.9
        e.stocks["NVXA"].fair *= 0.9
        e.trade(p, "CLDR", "sell", 0.5)
        e.now += 2
        e.trade(p, "GOLD", "sell", 1.0)
        e.now += 2
        e.trade(p, "NVXA", "buy", 0.5)

    def test_realised_plus_unrealised_equals_total_profit_before_costs_not_in_positions(self):
        e, p = self.e, self.p
        self.trade_story()
        pf = e.portfolio_for(p)
        # equity - deposited = realised + unrealised - fees still owed on the open positions' exit
        exit_fees = sum(x["value"] for x in pf["positions"]) * FEE
        self.assertAlmostEqual(pf["pnl"], pf["realized"] + pf["unrealized"] - exit_fees
                               - sum(0 for _ in ()), delta=2.0)
        self.assertGreater(pf["realized"], -50)
        self.assertEqual(set(pf["realized_by_ticker"]), {"CLDR", "GOLD", "NVXA"})

    def test_positions_carry_average_price_value_and_pnl(self):
        self.trade_story()
        pf = self.e.portfolio_for(self.p)
        sides = {x["ticker"]: x for x in pf["positions"]}
        self.assertEqual(set(sides), {"CLDR", "NVXA"})
        self.assertEqual(sides["CLDR"]["side"], "long")
        self.assertEqual(sides["NVXA"]["side"], "short")
        cldr = sides["CLDR"]
        self.assertAlmostEqual(cldr["pnl"], cldr["value"] - cldr["cost"], places=9)
        self.assertGreater(cldr["pnl"], 0)
        self.assertGreater(sides["NVXA"]["pnl"], 0)            # the short gained
        self.assertAlmostEqual(cldr["avg"], cldr["cost"] / cldr["shares"], places=9)

    def test_allocation_adds_up_to_one_and_names_cash_and_positions(self):
        self.trade_story()
        pf = self.e.portfolio_for(self.p)
        self.assertAlmostEqual(sum(a["pct"] for a in pf["allocation"]), 1.0, places=9)
        labels = {a["label"] for a in pf["allocation"]}
        self.assertEqual(labels, {"Cash", "CLDR", "NVXA"})
        self.assertEqual({a["kind"] for a in pf["allocation"]}, {"cash", "long", "short"})

    def test_fees_dividends_and_trade_count_are_totalled(self):
        e, p = self.e, self.p
        self.trade_story()
        p.divs["OILX"] = 2.5
        p.borrow["NVXA"] = 0.4
        pf = e.portfolio_for(p)
        self.assertEqual(pf["trades"], 6)
        self.assertAlmostEqual(pf["fees"], p.fees_paid)
        self.assertGreater(pf["fees"], 0)
        self.assertAlmostEqual(pf["dividends"], 2.5)
        self.assertAlmostEqual(pf["borrow"], 0.4)

    def test_best_and_worst_trades_come_from_the_ledger(self):
        self.trade_story()
        pf = self.e.portfolio_for(self.p)
        self.assertTrue(pf["best"] and pf["worst"])
        self.assertGreater(pf["best"][0]["pnl"], 0)
        self.assertLess(pf["worst"][0]["pnl"], 0)
        self.assertEqual(pf["worst"][0]["ticker"], "GOLD")
        pnls = [b["pnl"] for b in pf["best"]]
        self.assertEqual(pnls, sorted(pnls, reverse=True))

    def test_the_curve_grows_each_minute_and_ends_at_the_current_equity(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.3)
        advance(e, 190)
        pf = e.portfolio_for(p)
        self.assertGreaterEqual(len(pf["curve"]), 4)
        times = [pt[0] for pt in pf["curve"]]
        self.assertEqual(times, sorted(times))
        self.assertAlmostEqual(pf["curve"][-1][1], pf["equity"], places=9)

    def test_a_brand_new_player_has_an_empty_but_valid_portfolio(self):
        pf = self.e.portfolio_for(join(self.e, "fresh1"))
        self.assertEqual(pf["positions"], [])
        self.assertEqual(pf["realized"], 0)
        self.assertEqual(pf["best"], [])
        self.assertAlmostEqual(sum(a["pct"] for a in pf["allocation"]), 1.0)

    def test_it_works_without_a_ledger_too(self):
        e = make(self.tmp.name + "-no", 32, ledger=False) if False else None
        random.seed(33)
        e = engine.Engine(state_file=None, bots=False)
        e.tick(now=e.now)
        quiet(e)
        p = join(e, "noledger2")
        e.trade(p, "CLDR", "buy", 0.3)
        e.now += 2
        e.stocks["CLDR"].fair *= 1.1
        e.trade(p, "CLDR", "sell", 1.0)
        pf = e.portfolio_for(p)
        self.assertEqual(pf["best"][0]["ticker"], "CLDR")
        self.assertEqual(e.history_for(p)["source"], "memory")


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.e = make(self.tmp.name, 41)
        self.p = join(self.e, "hist1")
        for i in range(30):
            self.e.now += 2
            self.e.trade(self.p, "GOLD" if i % 2 == 0 else "CLDR", "buy" if i % 3 else "sell", 0.1)

    def tearDown(self):
        self.e.ledger.close()
        self.tmp.cleanup()

    def test_newest_first_with_all_the_columns(self):
        page = self.e.history_for(self.p, limit=10)
        self.assertEqual(len(page["events"]), 10)
        self.assertTrue(page["more"])
        times = [x["t"] for x in page["events"]]
        self.assertEqual(times, sorted(times, reverse=True))
        for key in ("seq", "t", "kind", "ticker", "shares", "price", "mb", "fee", "pnl", "cash"):
            self.assertIn(key, page["events"][0])
        self.assertEqual(page["source"], "ledger")

    def test_paging_walks_through_everything_without_gaps_or_repeats(self):
        seen, before = [], None
        for _ in range(20):
            page = self.e.history_for(self.p, limit=7, before=before)
            seen += [x["seq"] for x in page["events"]]
            if not page["more"]:
                break
            before = page["next_before"]
        self.assertEqual(seen, sorted(set(seen), reverse=True))
        everything = self.e.history_for(self.p, limit=500)["events"]
        self.assertEqual(seen, [x["seq"] for x in everything])
        self.assertGreaterEqual(len(everything), 20)         # most of the 30 trades succeed, plus the signup credit

    def test_filters_by_kind_and_ignores_unknown_kinds(self):
        sells = self.e.history_for(self.p, limit=500, kinds=["sell"])["events"]
        self.assertTrue(sells)
        self.assertEqual({x["kind"] for x in sells}, {"sell"})
        unknown = self.e.history_for(self.p, limit=500, kinds=["join", "margin"])["events"]
        default = self.e.history_for(self.p, limit=500)["events"]
        self.assertEqual([x["seq"] for x in unknown], [x["seq"] for x in default])
        self.assertNotIn("join", {x["kind"] for x in unknown})

    def test_limit_is_clamped(self):
        self.assertLessEqual(len(self.e.history_for(self.p, limit=10_000)["events"]), 500)
        self.assertEqual(len(self.e.history_for(self.p, limit=0)["events"]), 1)

    def test_a_player_only_sees_their_own_history(self):
        other = join(self.e, "other11")
        self.e.trade(other, "GOLD", "buy", 0.5)
        mine = self.e.history_for(self.p, limit=500)["events"]
        theirs = self.e.history_for(other, limit=500)["events"]
        self.assertFalse({x["seq"] for x in mine} & {x["seq"] for x in theirs})

    def test_csv_export_has_a_header_one_row_per_event_and_parses(self):
        text = self.e.history_csv(self.p)
        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(rows[0], ["time_utc", "type", "ticker", "shares", "price_mb", "amount_mb", "fee_mb",
                                   "realised_pnl_mb", "cash_change_mb"])
        events = self.e.history_for(self.p, limit=500)["events"]
        self.assertEqual(len(rows) - 1, len(events))
        for row in rows[1:]:
            self.assertEqual(len(row), 9)
            float(row[3]), float(row[4]), float(row[5]), float(row[6])
        cash = sum(float(r[8]) for r in rows[1:] if r[8])
        self.assertAlmostEqual(cash, self.p.cash, places=2)

    def test_realised_pnl_appears_only_on_closing_trades(self):
        events = self.e.history_for(self.p, limit=500)["events"]
        for x in events:
            if x["kind"] in ("sell", "cover", "margin_call"):
                self.assertIsNotNone(x["pnl"])
            else:
                self.assertIsNone(x["pnl"])

    def test_money_is_conserved(self):
        self.assertLess(abs(drift(self.e)), 1e-6)


if __name__ == "__main__":
    unittest.main()
