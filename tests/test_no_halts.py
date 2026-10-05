"""There are no trading halts: however far a price or the whole market moves, trading and orders carry on."""
import unittest

from _helpers import advance, drift, engine, join, make_engine


class NoHaltTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(41)
        self.p = join(self.e, "trader", extra_cash=5000)

    def test_the_circuit_breaker_code_and_its_state_are_gone(self):
        e = self.e
        for name in ("halt_left", "_check_halts", "market_halt_until", "_market_halt_cool"):
            self.assertFalse(hasattr(e, name), name)
        for s in e.stocks.values():
            self.assertFalse(hasattr(s, "halted_until"))
            self.assertFalse(hasattr(s, "halt_cool_until"))

    def test_a_stock_can_be_traded_straight_after_an_extreme_move(self):
        e, p = self.e, self.p
        e.stocks["CLDR"].fair *= 0.5                              # a 50% crash in one go
        advance(e, 3)
        ok, msg = e.trade(p, "CLDR", "buy", 0.2)
        self.assertTrue(ok, msg)
        e.stocks["CLDR"].fair *= 1.8
        advance(e, 3)
        ok, msg = e.trade(p, "CLDR", "sell", 1.0)
        self.assertTrue(ok, msg)

    def test_the_whole_market_can_be_traded_after_a_market_wide_crash(self):
        e, p = self.e, self.p
        for s in e.stocks.values():
            if s.asset_type == "equity":
                s.fair *= 0.85
        advance(e, 60)
        for tk in ("CLDR", "NVXA", "MSI"):
            ok, msg = e.trade(p, tk, "buy", 0.05)
            self.assertTrue(ok, tk + ": " + msg)
            advance(e, 2)
        self.assertNotIn("halt", [n["kind"] for n in e.news_log])

    def test_no_halt_news_is_ever_printed_over_a_wild_hour(self):
        e = self.e
        e.settings.update(moonshot_initial=6, moonshot_mean_seconds=100, catalyst_mean_seconds=60, sector_shock_mean_seconds=90)
        for _ in range(3600):
            e.tick(now=e.now + 1)
        self.assertEqual([n for n in e.news_log if n["kind"] == "halt"], [])
        self.assertEqual([n for n in e.news_log if "halted" in n["text"].lower()], [])

    def test_a_stop_loss_fills_through_a_crash_without_waiting(self):
        e, p = self.e, self.p
        self.assertTrue(e.trade(p, "CLDR", "buy", 0.3)[0])
        px = e.stocks["CLDR"].price
        ok, msg = e.place_order(p, "CLDR", "stop_loss", px * 0.95, pct=1.0)
        self.assertTrue(ok, msg)
        e.stocks["CLDR"].fair = px * 0.7
        advance(e, 3)
        self.assertNotIn("CLDR", p.hold)                          # filled at once, at the new price
        self.assertEqual(p.orders, [])

    def test_the_page_data_has_no_halt_field(self):
        e, p = self.e, self.p
        advance(e, 2)
        init = e.init_for(p)
        self.assertTrue(all("halt_until" not in row for row in init["stocks"]))
        wire = e.build_wire()
        self.assertTrue(all("halt_until" not in sl for sl in wire.get("slow", {}).values()))
        self.assertTrue(all("halt_until" not in sl for sl in e.pub_slow.values()))

    def test_an_old_halt_setting_in_a_content_pack_does_nothing(self):
        e, p = self.e, self.p
        e.settings.update(halts_enabled=True, halt_move=0.01, halt_seconds=600, halt_market_move=0.001)
        e.stocks["CLDR"].fair *= 0.7
        advance(e, 3)
        self.assertTrue(e.trade(p, "CLDR", "buy", 0.1)[0])
        self.assertLess(abs(drift(e)), 1e-6)


if __name__ == "__main__":
    unittest.main()
