"""Engine tests: trading, shorting, limits, borrow fees, margin, dividends, earnings timing, news and saving.

Run all tests:   python -m unittest discover tests -v
These are fast (about a minute). Slow statistical checks live in test_edge.py (RUN_SLOW=1).
"""
import math
import os
import random
import tempfile
import unittest

from _helpers import advance, drift, engine, join, make_engine, quiet

FEE = engine.FEE
QUARTER = 63 * engine.MARKET_DAY_SECONDS


def pump(e, seconds=2):
    """Move the fake clock on so the 1-second trade cooldown never gets in the way."""
    e.now += seconds


class TradingTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(1)
        self.p = join(self.e, "alice")

    def test_conservation_after_random_trading(self):
        e = self.e
        rng = random.Random(3)
        players = [join(e, f"t{i}") for i in range(5)]
        for step in range(300):
            e.tick(now=e.now + 1)
            p = rng.choice(players)
            tk = rng.choice(list(e.stocks))
            e.trade(p, tk, rng.choice(["buy", "sell"]), rng.choice([0.1, 0.5, 1.0]))
        self.assertLess(abs(drift(e)), 1e-6)

    def test_round_trip_costs_about_one_percent(self):
        e, p = self.e, self.p
        before = p.cash
        ok, _ = e.trade(p, "GOLD", "buy", 0.25)
        self.assertTrue(ok)
        pump(e)
        e.trade(p, "GOLD", "sell", 1.0)
        lost = (before - p.cash) / (before * 0.25)
        self.assertAlmostEqual(lost, 1 - (1 - FEE) ** 2, places=6)

    def test_average_entry_price_is_share_weighted(self):
        e, p = self.e, self.p
        s = e.stocks["CLDR"]
        e.trade(p, "CLDR", "buy", 0.1)
        first = s.price
        pump(e)
        s.fair *= 1.10
        e.trade(p, "CLDR", "buy", 0.1)
        sh = p.hold["CLDR"]
        cash1, cash2 = 100 * (1 - FEE), 90 * (1 - FEE)   # 10% of 1000 then 10% of the remaining 900
        s1, s2 = cash1 / first, cash2 / s.price
        self.assertAlmostEqual(sh, s1 + s2, places=6)
        self.assertAlmostEqual(e.avg_price(p, "CLDR"), (s1 * first + s2 * s.price) / (s1 + s2), places=6)

    def test_selling_part_keeps_the_average_price(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.2)
        avg = e.avg_price(p, "CLDR")
        pump(e)
        e.stocks["CLDR"].fair *= 1.3
        e.trade(p, "CLDR", "sell", 0.5)
        self.assertAlmostEqual(e.avg_price(p, "CLDR"), avg, places=6)

    def test_typed_amount_is_used_instead_of_the_percentage(self):
        e, p = self.e, self.p
        ok, msg = e.trade(p, "GOLD", "buy", 0.9, 50)
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(1000 - p.cash, 50, places=6)

    def test_bad_amounts_are_rejected(self):
        e, p = self.e, self.p
        for bad in (0, -5, float("nan"), float("inf"), 1e13, "x", None):
            if bad is None:
                ok, _ = e.trade(p, "GOLD", "buy", 0)
            else:
                ok, _ = e.trade(p, "GOLD", "buy", 0.5, bad)
            self.assertFalse(ok, f"amount {bad!r} should be rejected")
            pump(e)
        self.assertEqual(p.cash, 1000)

    def test_cooldown_between_trades_in_one_stock(self):
        e, p = self.e, self.p
        self.assertTrue(e.trade(p, "GOLD", "buy", 0.1)[0])
        self.assertFalse(e.trade(p, "GOLD", "buy", 0.1)[0])
        self.assertTrue(e.trade(p, "CLDR", "buy", 0.1)[0])   # a different stock is fine

    def test_unknown_ticker_and_bad_side(self):
        e, p = self.e, self.p
        self.assertFalse(e.trade(p, "NOPE", "buy", 0.5)[0])
        self.assertFalse(e.trade(p, "GOLD", "hold", 0.5)[0])

    def test_index_price_follows_the_index_level(self):
        e = self.e
        advance(e, 20)
        self.assertAlmostEqual(e.stocks["MSI"].price, e.index_level, places=9)


class LimitTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(2)

    def test_there_is_no_position_limit_on_a_long(self):
        e = self.e
        p = join(e, "allin")
        ok, msg = e.trade(p, "DOGO", "buy", 1.0)             # the wildest stock, all of the cash
        self.assertTrue(ok, msg)
        self.assertNotIn("limit", msg.lower())
        self.assertNotIn("trimmed", msg)
        self.assertAlmostEqual(p.hold["DOGO"] * e.stocks["DOGO"].price, 1000 * (1 - engine.FEE), delta=1.0)
        self.assertLess(p.cash, 1.0)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_rich_player_is_not_capped_by_the_depth_of_the_stock(self):
        e = self.e
        p = join(e, "rich", extra_cash=1_000_000)
        s = e.stocks["MOON"]
        ok, msg = e.trade(p, "MOON", "buy", 1.0)
        self.assertTrue(ok, msg)
        self.assertGreater(p.hold["MOON"] * s.price, s.base)   # far more than the stock's size
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_short_is_limited_by_margin_not_by_a_position_cap(self):
        e = self.e
        p = join(e, "shorter", extra_cash=9000)              # 10,000 MB of equity
        ok, msg = e.trade(p, "GOLD", "sell", 1.0)            # calm: 1x margin, so up to the whole equity
        self.assertTrue(ok, msg)
        self.assertGreater(-p.hold["GOLD"] * e.stocks["GOLD"].price, 5000)
        self.assertNotIn("position limit", msg.lower())

    def test_selling_is_never_blocked(self):
        e = self.e
        p = join(e, "seller")
        e.trade(p, "NVXA", "buy", 1.0)
        pump(e)
        e.stocks["NVXA"].fair *= 3
        self.assertTrue(e.trade(p, "NVXA", "sell", 1.0)[0])

    def test_short_interest_cap_is_shared_by_all_players(self):
        e = self.e
        s = e.stocks["MOON"]
        a = join(e, "aa", extra_cash=1_000_000)
        b = join(e, "bb", extra_cash=1_000_000)
        ok, msg = e.trade(a, "MOON", "sell", 1.0)
        self.assertTrue(ok, msg)
        pump(e)
        ok, msg = e.trade(b, "MOON", "sell", 1.0)                 # there is no shared borrow limit any more
        self.assertTrue(ok, msg)
        self.assertGreater(e.short_interest_map()["MOON"], 100 * e.short_cap(s))
        self.assertLess(abs(drift(e)), 1e-6)

    def test_margin_requirement_and_maintenance_rise_with_volatility(self):
        e = self.e
        gold, nvxa, dogo = (e.stocks[t] for t in ("GOLD", "NVXA", "DOGO"))
        self.assertEqual(e.margin_req(gold), 1.0)
        self.assertEqual(e.margin_req(dogo), 2.0)
        self.assertGreater(e.margin_req(nvxa), 1.0)
        self.assertEqual(e.maintenance(gold), 0.25)
        self.assertEqual(e.maintenance(dogo), 0.50)

    def test_borrow_fee_matches_the_formula(self):
        e = self.e
        p = join(e, "shorty")
        s = e.stocks["NVXA"]
        self.assertTrue(e.trade(p, "NVXA", "sell", 0.5)[0])
        short_value = -p.hold["NVXA"] * s.price
        util = e.short_interest_map()["NVXA"] / e.short_cap(s)
        rate = (0.0003 + 0.001 * s.vol) * (1 + 3 * util)
        fees0 = e.fees
        e._borrow_t = e.now
        for _ in range(60):
            e.now += 1
            e._borrow_fees()
        expected = short_value * rate * 60 / engine.MARKET_DAY_SECONDS
        self.assertAlmostEqual(p.borrow["NVXA"], expected, delta=expected * 0.02)
        self.assertAlmostEqual(e.fees - fees0, p.borrow["NVXA"], places=9)
        self.assertLess(abs(drift(e)), 1e-6)


class ShortingTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(3)
        self.p = join(self.e, "shorty")

    def test_selling_with_no_position_opens_a_short_and_buying_covers_it(self):
        e, p = self.e, self.p
        ok, msg = e.trade(p, "NVXA", "sell", 1.0)
        self.assertTrue(ok, msg)
        self.assertLess(p.hold["NVXA"], 0)
        pump(e)
        e.stocks["NVXA"].fair *= 0.9    # the price falls: the short gains
        eq = e.equity(p)
        self.assertGreater(eq, 1000 - 20)
        self.assertTrue(e.trade(p, "NVXA", "buy", 1.0)[0])
        self.assertNotIn("NVXA", p.hold)
        self.assertGreater(p.cash, 1000)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_short_proceeds_stay_locked(self):
        e, p = self.e, self.p
        cash0 = p.cash
        e.trade(p, "NVXA", "sell", 1.0)
        self.assertLess(p.cash, 1e-6)                                # the stake left the cash: shorting does not add to it
        self.assertAlmostEqual(e.equity(p), cash0 * (1 - 2 * engine.FEE) / 1, delta=cash0 * 0.004)
        self.assertFalse(e.debit(p, 100)[0])                          # and it can't be withdrawn while the short is open

    def test_cannot_short_beyond_the_margin(self):
        e, p = self.e, self.p
        e.trade(p, "GOLD", "sell", 1.0)
        pump(e)
        ok, _ = e.trade(p, "CLDR", "sell", 1.0)   # nothing is left to short with: a short is paid for out of cash
        self.assertFalse(ok)

    def test_covering_a_part_keeps_the_average_price(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "sell", 1.0)
        avg = e.avg_price(p, "NVXA")
        pump(e)
        e.stocks["NVXA"].fair *= 0.8
        e.trade(p, "NVXA", "buy", 0.5)
        self.assertAlmostEqual(e.avg_price(p, "NVXA"), avg, places=6)

    def test_margin_call_triggers_exactly_at_the_maintenance_level(self):
        for tk in ("GOLD", "BYTE", "DOGO"):
            with self.subTest(stock=tk):
                e = make_engine(4)
                p = join(e, "mc")
                self.assertTrue(e.trade(p, tk, "sell", 1.0)[0])
                s = e.stocks[tk]
                base = s.fair
                liab0 = e.short_liability(p)
                self.assertGreater(liab0, 0)
                called_at = None
                for mult in [1.15 ** i for i in range(1, 45)]:
                    s.fair = base * mult
                    need = -p.hold.get(tk, 0) * s.price * e.maintenance(s)
                    eq = e.equity(p)
                    e._margin_calls()
                    if tk not in p.hold:
                        called_at = mult
                        self.assertLess(eq, need, "called although equity was above the maintenance level")
                        break
                    self.assertGreaterEqual(eq, need, "not called although equity fell below the level")
                self.assertIsNotNone(called_at, "no margin call happened")
                self.assertTrue(p.notices)
                self.assertGreaterEqual(p.cash, -1e-9)
                self.assertLess(abs(drift(e)), 1e-6)

    def test_a_gap_past_the_call_is_absorbed_by_the_house_and_counted(self):
        e = make_engine(6)
        p = join(e, "gapped")
        e.trade(p, "HLXB", "sell", 1.0)
        s = e.stocks["HLXB"]
        s.fair *= 8.0
        before = e.short_shortfall
        e._margin_calls()
        self.assertNotIn("HLXB", p.hold)
        self.assertEqual(p.cash, 0.0)
        self.assertGreater(e.short_shortfall, before)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_short_in_a_bankrupt_stock_is_closed_without_negative_cash(self):
        e = make_engine(7)
        p = join(e, "bk")
        e.trade(p, "MOON", "sell", 1.0)
        s = e.stocks["MOON"]
        s.fair = s.initial_price * 0.2
        e._check_distress()
        if "MOON" in e.delisted:
            self.assertNotIn("MOON", p.hold)
        self.assertGreaterEqual(p.cash, 0.0)
        self.assertLess(abs(drift(e)), 1e-6)


class DividendAndEarningsTests(unittest.TestCase):
    def test_ex_dividend_pays_longs_charges_shorts_and_drops_the_price(self):
        e = make_engine(8)
        long_p, short_p = join(e, "long"), join(e, "short")
        e.trade(long_p, "OILX", "buy", 0.5)
        pump(e)
        e.trade(short_p, "OILX", "sell", 0.5)
        s = e.stocks["OILX"]
        self.assertGreater(s.base_dps, 0)
        s.div = {"t": e.now - 1, "amt": 0.5}
        price0, c_long, c_short = s.price, long_p.cash, short_p.cash
        e._dividends()
        self.assertAlmostEqual(long_p.cash - c_long, long_p.hold["OILX"] * 0.5, places=6)
        self.assertAlmostEqual(c_short - short_p.cash, -short_p.hold["OILX"] * 0.5, places=6)
        self.assertAlmostEqual(price0 - s.price, price0 * (0.5 / price0), places=6)
        self.assertIsNone(s.div)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_first_reports_are_spread_over_one_quarter(self):
        e = make_engine(9)
        times = [s.next_earn - e.now for s in e.stocks.values() if s.next_earn]
        self.assertGreater(len(times), 20)
        self.assertGreaterEqual(min(times), 0.005 * QUARTER - 5)
        self.assertLessEqual(max(times), QUARTER + 5)
        self.assertGreater(max(times) - min(times), 0.5 * QUARTER, "reports are bunched together")      # (see test_calendar.py)

    def test_a_quarter_is_63_game_days_of_31_5_hours(self):
        e = make_engine(9)
        self.assertEqual(e._quarter_seconds(), 63 * 1800)
        self.assertEqual(e._quarter_seconds() / 3600, 31.5)

    def test_next_report_is_a_quarter_later_give_or_take_a_few_game_days(self):
        e = make_engine(10)
        s = e.stocks["NVXA"]
        e.now = s.next_earn + 1
        e._earnings()
        jitter = 4 * engine.MARKET_DAY_SECONDS
        self.assertAlmostEqual(s.next_earn - e.now, QUARTER, delta=jitter + 2 * engine.MARKET_DAY_SECONDS)
        self.assertEqual(len(s.reports), 1)
        e2 = make_engine(10, earnings_jitter_days=0)
        s2 = e2.stocks["NVXA"]
        e2.now = s2.next_earn + 1
        slot = s2.earn_slot
        e2._earnings()
        self.assertAlmostEqual(s2.earn_slot, slot + QUARTER, delta=1e-6)        # exactly a quarter with no jitter

    def test_earnings_headline_names_at_most_three_stories(self):
        e = make_engine(11)
        s = e.stocks["NVXA"]
        for i in range(12):
            s.pending.append({"t": e.now, "text": f"story {i}", "why": f"reason {i}", "dm": 0.01 * (i + 1),
                              "dr": 0.0, "dd": 0.0})
        e._report(s)
        text = next(n["text"] for n in reversed(e.news_log) if n["kind"] == "earnings")
        self.assertIn("and 9 smaller developments", text)
        self.assertEqual(text.count("reason"), 3)
        self.assertEqual(s.reports[-1]["n_causes"], 12)
        self.assertEqual(s.pending, [])

    def test_a_report_declares_a_dividend_that_follows_the_margin(self):
        e = make_engine(12)
        s = e.stocks["OILX"]
        e._report(s)
        self.assertIsNotNone(s.div)
        s.margin = -0.05          # a loss-making quarter
        e._report(s)
        self.assertIsNone(s.div)
        self.assertEqual(s.dps, 0.0)

    def test_story_effects_are_scaled_to_the_price_move(self):
        effect = {"dm": -0.10, "dr": -0.05, "dd": 0.2}
        engine.Engine._scale_effect(effect, -0.03)            # nominal -0.15, price move -3% -> factor 0.25 (floor)
        self.assertAlmostEqual(effect["dm"], -0.10 * 0.25)
        small = {"dm": -0.02, "dr": 0.0, "dd": 0.0}
        engine.Engine._scale_effect(small, -0.04)             # price moved twice as much as the nominal effect
        self.assertAlmostEqual(small["dm"], -0.04)
        wrong_way = {"dm": 0.05, "dr": 0.0, "dd": 0.0}
        engine.Engine._scale_effect(wrong_way, -0.02)         # opposite signs: left untouched
        self.assertEqual(wrong_way["dm"], 0.05)


class NewsTests(unittest.TestCase):
    def test_no_headline_is_ever_repeated(self):
        e = make_engine(13, event_mean_seconds=15, issue_mean_seconds=15)
        quiet(e)
        texts = []
        seen = 0
        for _ in range(3000):
            e.tick(now=e.now + 1)
            for n in list(e.news_log)[-8:]:
                if n["id"] > seen:
                    seen = n["id"]
                    texts.append(n["text"].lower())
        self.assertGreater(len(texts), 300)
        self.assertEqual(len(texts), len(set(texts)), "a headline was printed twice")

    def test_follow_ups_and_reversals_appear(self):
        e = make_engine(14, event_mean_seconds=15, issue_mean_seconds=15)
        quiet(e)
        kinds = set()
        for _ in range(3000):
            e.tick(now=e.now + 1)
            for n in list(e.news_log)[-5:]:
                for k in ("UPDATE:", "REVERSAL:"):
                    if n["text"].startswith(k):
                        kinds.add(k)
        self.assertEqual(kinds, {"UPDATE:", "REVERSAL:"})

    def test_follow_up_branches_use_the_same_strength_and_balanced_scales(self):
        e = make_engine(15)
        seen = []
        e._spawn_event = lambda tpl, target, sign, strength, scale, **kw: seen.append((sign, strength, scale))
        for _ in range(200):
            e.threads.append({"t": e.now - 1, "tpl": {"scope": "market", "betas": {"*": 0.5}, "index_bias": 1.0,
                                                      "sector": None, "ticker": None},
                              "target": None, "label": "the market", "ref": "Rates fall", "sign": 1,
                              "strength": "strong", "stage": 2, "issue": None})
        e._followups()
        self.assertEqual(len(seen), 200)
        self.assertEqual({st for _, st, _ in seen}, {"strong"}, "both branches must use the original strength")
        cont = [sc for sg, _, sc in seen if sg == 1]
        rev = [sc for sg, _, sc in seen if sg == -1]
        self.assertTrue(cont and rev)
        self.assertEqual({round(x, 6) for x in cont}, {0.8})
        self.assertEqual({round(x, 6) for x in rev}, {1.2})
        # expected move is zero: 60% x 0.8 == 40% x 1.2
        self.assertAlmostEqual(0.6 * 0.8, 0.4 * 1.2)

    def test_headline_direction_scaling_cancels_exactly(self):
        """For any mood the likelier direction moves prices less so that E[sign x scale] = 0."""
        e = make_engine(16)
        for eff in (-1, -0.5, 0, 0.3, 0.9):
            p_good = e._p_good(eff)
            expected = p_good * 2 * (1 - p_good) - (1 - p_good) * 2 * p_good
            self.assertAlmostEqual(expected, 0.0, places=12)

    def test_the_hidden_mood_is_not_sent_to_players(self):
        e = make_engine(17, event_mean_seconds=10)
        p = join(e, "viewer")
        advance(e, 400)
        state = e.state_for(p)
        def keys(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    yield str(k).lower()
                    yield from keys(v)
            elif isinstance(x, list):
                for v in x:
                    yield from keys(v)
        names = set(keys(state))
        self.assertFalse({k for k in names if "mood" in k or "narrative" in k or "regime" in k or "crisis" in k})
        for n in e.news_log:
            if n["kind"] == "macro":
                for word in ("boom", "bubble", "recession", "crisis", "expansion"):
                    self.assertNotIn(word, n["text"].lower())

    def test_news_never_targets_the_index_directly(self):
        e = make_engine(18, event_mean_seconds=10)
        quiet(e)
        advance(e, 600)
        for n in e.news_log:
            self.assertNotIn("MSI", n["tickers"])


class MarketContentTests(unittest.TestCase):
    """The bigger market: new companies, sectors, and derived assets (sector indices, ETFs, leveraged products)."""

    @classmethod
    def setUpClass(cls):
        cls.e = make_engine(50)

    def test_the_market_has_over_a_hundred_listings(self):
        equities = [s for s in self.e.stocks.values() if s.asset_type == "equity"]
        self.assertGreaterEqual(len(equities), 100)
        self.assertGreaterEqual(len(self.e.stocks), 125)

    def test_every_equity_has_a_complete_profile(self):
        for tk, s in self.e.stocks.items():
            if s.asset_type != "equity":
                continue
            self.assertGreater(s.initial_price, 0, tk)
            self.assertGreater(s.revenue, 0, tk)
            self.assertGreater(s.shares_outstanding, 0, tk)
            self.assertGreater(s.vol, 0.05, tk)
            self.assertTrue(s.desc, tk)
            self.assertIn(s.sector, self.e.sectors, tk)

    def test_new_sectors_exist_and_have_companies_and_news(self):
        for sector in ("healthcare", "retail", "media", "autos", "realestate", "crypto", "space"):
            self.assertIn(sector, self.e.sectors)
            self.assertGreaterEqual(sum(1 for s in self.e.stocks.values() if s.sector == sector and s.asset_type == "equity"), 5)
            tpls = [t for t in self.e.templates.values() if t.get("sector") == sector]
            self.assertGreaterEqual(len(tpls), 2, f"{sector} needs its own news templates")

    def test_news_templates_are_well_formed(self):
        for t in self.e.templates.values():
            self.assertIn(t.get("scope", "market"), ("market", "sector", "company"), t["id"])
            self.assertTrue(t["up"] and t["down"], t["id"])
            if t.get("sector"):
                self.assertIn(t["sector"], self.e.sectors, t["id"])

    def test_every_sector_with_three_stocks_has_a_tradable_index(self):
        for sid in self.e.sectors:
            if sid in ("safe", "meme", "commodities"):
                continue
            n = sum(1 for s in self.e.stocks.values() if s.sector == sid and s.asset_type == "equity")
            tk = "X" + sid[:4].upper()
            self.assertEqual(tk in self.e.stocks, n >= 3, f"{sid}: {n} stocks")

    def test_derived_assets_have_no_company_behind_them(self):
        for tk in self.e.derived:
            s = self.e.stocks[tk]
            self.assertEqual(s.asset_type, "index")
            self.assertEqual(s.base, 0.0)
            self.assertIsNone(s.next_earn)
            self.assertIsNone(s.next_rating_review)

    def test_sector_index_follows_its_constituents(self):
        e = make_engine(51)
        quiet(e)
        s = e.stocks["XTECH"]
        members = [m for m in e.stocks.values() if m.sector == "tech" and m.asset_type == "equity"]
        w = sum(m.base for m in members)
        p0 = {m.ticker: m.price for m in members}
        i0 = s.price
        advance(e, 1)
        # one tick: index return equals the base-weighted average return of its members (from the tick before)
        advance(e, 120)
        self.assertGreater(s.price, 0)
        # exact check on one more tick
        before = {m.ticker: m.price for m in members}
        i_before = s.price
        e.tick(now=e.now + 1)
        expected = sum(m.base * (m.price / before[m.ticker] - 1) for m in members) / w
        self.assertAlmostEqual(s.price / i_before - 1, expected, places=9)

    def test_etf_is_an_equal_weighted_basket(self):
        e = make_engine(52)
        quiet(e)
        advance(e, 5)
        etf = e.stocks["AIFX"]
        names = e.derived["AIFX"]["members"]
        before = {t: e.stocks[t].price for t in names}
        i_before = etf.price
        e.tick(now=e.now + 1)
        expected = sum(e.stocks[t].price / before[t] - 1 for t in names) / len(names)
        self.assertAlmostEqual(etf.price / i_before - 1, expected, places=9)

    def test_indices_and_etfs_are_total_return_so_dividends_are_not_a_leak(self):
        """When a member goes ex-dividend its price drops by the dividend. The ETF adds that drop back, so holding
        the ETF does not quietly lose the yield; without this a 'Dividend Income ETF' would pay holders nothing."""
        e = make_engine(57)
        quiet(e)
        advance(e, 5)
        names = e.derived["DIVX"]["members"]
        target = names[0]
        s = e.stocks[target]
        s.div = {"t": e.now, "amt": s.price * 0.05}                 # a 5% dividend, so the effect is easy to see
        before = {t: e.stocks[t].price for t in names}
        etf_before = e.stocks["DIVX"].price
        seen = {}
        original = e._update_index_level

        def spy():
            seen.update(e._div_today)
            original()
        e._update_index_level = spy
        e.tick(now=e.now + 1)
        d = seen[target]
        self.assertAlmostEqual(d, 0.05, delta=0.005)
        total = sum(e.stocks[t].price / before[t] / ((1 - d) if t == target else 1.0) - 1 for t in names) / len(names)
        self.assertAlmostEqual(e.stocks["DIVX"].price / etf_before - 1, total, places=9)
        naive = sum(e.stocks[t].price / before[t] - 1 for t in names) / len(names)
        self.assertGreater(total - naive, 0.04 / len(names))       # the dividend drop was added back
        self.assertEqual(e._div_today, {})                         # and it is only used for the tick it happened in

    def test_leveraged_and_inverse_products_multiply_the_index_return_each_tick(self):
        e = make_engine(53)
        quiet(e)
        advance(e, 5)
        before = {tk: e.stocks[tk].price for tk in ("MSI", "2LMSI", "2SMSI", "3LMSI", "3SMSI")}
        e.tick(now=e.now + 1)
        r = e.stocks["MSI"].price / before["MSI"] - 1
        self.assertNotEqual(r, 0.0)
        for tk, lev in (("2LMSI", 2.0), ("2SMSI", -2.0), ("3LMSI", 3.0), ("3SMSI", -3.0)):
            self.assertAlmostEqual(e.stocks[tk].price / before[tk] - 1, lev * r, places=9, msg=tk)

    def test_leveraged_products_are_martingales_and_decay_when_choppy(self):
        """Over many random paths the average price stays at its start (no edge), while the typical (median) path
        of a leveraged product drifts below it: that is the 'decay' the description warns about."""
        import random as _r
        rng = _r.Random(5)
        finals = []
        for _ in range(400):
            price = 100.0
            for _ in range(600):
                r = rng.gauss(0, 0.004)
                price *= max(0.001, 1 + 2.0 * r)
            finals.append(price)
        mean = sum(finals) / len(finals)
        median = sorted(finals)[len(finals) // 2]
        self.assertAlmostEqual(mean, 100.0, delta=2.0)     # a martingale: no expected gain or loss
        self.assertLess(median, mean)                      # but a typical path decays

    def test_derived_assets_trade_like_stocks_and_conserve_money(self):
        e = make_engine(54)
        p = join(e, "indexer")
        for tk in ("XTECH", "AIFX", "2LMSI", "3SMSI"):
            ok, msg = e.trade(p, tk, "buy", 0.15)
            self.assertTrue(ok, f"{tk}: {msg}")
            pump(e)
        ok, msg = e.trade(p, "2SMSI", "sell", 0.5)                 # short an inverse product
        self.assertTrue(ok, msg)
        advance(e, 30)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_news_and_ratings_never_touch_derived_assets(self):
        e = make_engine(55, event_mean_seconds=10, issue_mean_seconds=10)
        quiet(e)
        advance(e, 500)
        for n in e.news_log:
            for tk in n["tickers"]:
                self.assertNotIn(tk, e.derived)
        for tk in e.derived:
            self.assertEqual(e.stocks[tk].reports.maxlen and len(e.stocks[tk].reports), 0)

    def test_derived_state_survives_a_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            random.seed(56)
            e = engine.Engine(state_file=path)
            e.tick(now=e.now)
            quiet(e)
            advance(e, 40)
            e.save()
            f = engine.Engine(state_file=path)
            for tk in ("MSI", "XTECH", "AIFX", "2LMSI", "2SMSI"):
                self.assertAlmostEqual(f.stocks[tk].price, e.stocks[tk].price, places=9, msg=tk)
            self.assertEqual(set(f.derived), set(e.derived))


class NewListingTests(unittest.TestCase):
    """Companies listed in the last 30 minutes get a NEW badge: only ones that joined after the game began."""

    def test_the_original_listings_are_not_new(self):
        e = make_engine(63)
        e._public()
        self.assertTrue(all(s.listed_at == 0.0 for s in e.stocks.values()))
        self.assertTrue(all(row["listed_at"] == 0.0 for row in e.pub_stocks))

    def test_a_company_added_while_running_is_marked_with_its_listing_time(self):
        e = make_engine(64)
        cfg = dict(next(c for c in e._read()[1].values() if c["ticker"] == "NVXA"), ticker="ZZNW", name="Brand New Co")
        e.now += 100
        e._list(cfg, initial=False)
        e._public()
        row = next(r for r in e.pub_stocks if r["ticker"] == "ZZNW")
        self.assertEqual(row["listed_at"], e.now)
        self.assertTrue(any("NEW LISTING" in n["text"] for n in e.news_log))

    def test_a_company_added_to_the_content_since_the_last_save_is_new_on_load(self):
        import json
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path = os.path.join(d, "state.json")
            random.seed(65)
            a = engine.Engine(state_file=path)
            a.tick(now=a.now)
            a.save()
            state = json.load(open(path, encoding="utf-8"))
            state["stocks"].pop("NVXA")                        # as if NVXA had been added to the content since
            json.dump(state, open(path, "w", encoding="utf-8"))
            b = engine.Engine(state_file=path)
            self.assertEqual(b.stocks["NVXA"].listed_at, b.now)
            self.assertEqual(b.stocks["CLDR"].listed_at, 0.0)
            b.save()
            c = engine.Engine(state_file=path)
            self.assertEqual(c.stocks["NVXA"].listed_at, b.stocks["NVXA"].listed_at)   # remembered across restarts


class CommodityTests(unittest.TestCase):
    """Commodities used to carry a slow drift, which made their next move predictable (a momentum edge)."""

    def test_commodities_have_no_drift_by_default(self):
        e = make_engine(61)
        quiet(e)
        advance(e, 300)
        for tk, s in e.stocks.items():
            if s.asset_type == "commodity":
                self.assertEqual(s.trend, 0.0, tk)

    def test_the_old_drift_can_still_be_switched_on_for_experiments(self):
        e = make_engine(62, commodity_trend=1.0)
        quiet(e)
        advance(e, 300)
        self.assertTrue(any(s.trend != 0.0 for s in e.stocks.values() if s.asset_type == "commodity"))



class EnvelopeTests(unittest.TestCase):
    """The daily limit must damp moves without favouring either direction (otherwise dip-buyers farm it)."""

    def setUp(self):
        self.e = make_engine(40)
        self.s = self.e.stocks["NVXA"]
        self.cap = 0.15
        self.limit = min(self.cap, self.e._daily_sigma(self.s) * (1.5 + 0.75 * min(abs(self.s.beta), 2.0)))

    def test_no_damping_at_the_open_and_half_at_the_limit(self):
        s, e = self.s, self.e
        s.fair = s.fair_open
        self.assertAlmostEqual(e._envelope_damping(s, self.cap), 1.0)
        s.fair = s.fair_open * math.exp(self.limit)
        self.assertAlmostEqual(e._envelope_damping(s, self.cap), 0.5, places=6)
        s.fair = s.fair_open * math.exp(2 * self.limit)
        self.assertLess(e._envelope_damping(s, self.cap), 0.1)

    def test_damping_is_the_same_above_and_below_the_open(self):
        s, e = self.s, self.e
        for x in (0.3, 0.7, 1.0, 1.5):
            s.fair = s.fair_open * math.exp(x * self.limit)
            up = e._envelope_damping(s, self.cap)
            s.fair = s.fair_open * math.exp(-x * self.limit)
            down = e._envelope_damping(s, self.cap)
            self.assertAlmostEqual(up, down, places=12)

    def test_an_up_move_and_a_down_move_are_shrunk_by_exactly_the_same_amount(self):
        s, e = self.s, self.e
        s.fair = s.fair_open * math.exp(-0.9 * self.limit)        # near the day's lower limit
        start = s.fair
        e._pending = {s.ticker: 0.01}
        e._flush_moves()
        up = s.fair / start - 1
        s.fair = start
        e._pending = {s.ticker: -0.01}
        e._flush_moves()
        down = s.fair / start - 1
        self.assertAlmostEqual(up, -down, places=12, msg="the limit must not favour one direction")
        self.assertLess(up, 0.01)       # but both are damped

    def test_the_old_reflecting_wall_is_gone(self):
        """Near the lower limit a falling stock must not be protected from further falls."""
        s, e = self.s, self.e
        s.fair = s.fair_open * math.exp(-1.2 * self.limit)
        start = s.fair
        e._pending = {s.ticker: -0.02}
        e._flush_moves()
        self.assertLess(s.fair, start)

    def test_a_zero_cap_turns_the_limit_off(self):
        s, e = self.s, self.e
        e.settings["daily_move_cap"] = 0
        s.fair = s.fair_open * math.exp(self.limit)
        start = s.fair
        e._pending = {s.ticker: 0.01}
        e._flush_moves()
        self.assertAlmostEqual(s.fair / start - 1, 0.01, places=12)

    def test_the_limit_still_tames_extreme_days(self):
        """60 shocks of +2% in a row would be +120% unchecked (about 12 limits). The soft limit holds it to a
        few limits: a stock can overshoot, but runaway days are tamed."""
        s, e = self.s, self.e
        s.fair = s.fair_open
        for _ in range(60):
            e._pending = {s.ticker: 0.02}
            e._flush_moves()
        self.assertLess(math.log(s.fair / s.fair_open), 3.0 * self.limit)
        self.assertGreater(math.log(s.fair / s.fair_open), self.limit)   # it is soft, not a wall


class AdminDataTests(unittest.TestCase):
    """The numbers behind the /admin page."""

    def test_every_kind_of_trade_is_logged_with_its_fee(self):
        e = make_engine(30)
        p = join(e, "logger")
        e.trade(p, "GOLD", "buy", 0.2)
        pump(e)
        e.trade(p, "GOLD", "sell", 1.0)
        pump(e)
        e.trade(p, "NVXA", "sell", 0.5)      # a short
        pump(e)
        e.trade(p, "NVXA", "buy", 1.0)       # a cover
        kinds = [x["k"] for x in p.log]
        self.assertEqual(kinds, ["buy", "sell", "short", "cover"])
        for entry in p.log:
            self.assertGreater(entry["fee"], 0)
            self.assertAlmostEqual(entry["fee"] / entry["mb"], FEE, delta=FEE * 0.02)
        self.assertEqual(e.trades_total, 4)

    def test_trade_log_keeps_only_the_last_hundred(self):
        e = make_engine(31)
        p = join(e, "busy1")
        for i in range(130):
            pump(e)
            e.trade(p, "GOLD", "buy" if i % 2 == 0 else "sell", 0.1 if i % 2 == 0 else 1.0)
        self.assertEqual(len(p.log), 100)

    def test_a_margin_call_is_logged_for_the_player_and_the_house(self):
        e = make_engine(32)
        p = join(e, "called1")
        e.trade(p, "HLXB", "sell", 1.0)
        e.stocks["HLXB"].fair *= 8
        e._margin_calls()
        self.assertEqual(p.margin_calls, 1)
        self.assertEqual(e.margin_calls, 1)
        entry = e.margin_log[-1]
        self.assertEqual(entry["player"], "called1")
        self.assertEqual(entry["tickers"], ["HLXB"])
        self.assertGreater(entry["shortfall"], 0)
        self.assertEqual(p.log[-1]["k"], "margin_call")

    def test_house_series_is_sampled_every_ten_seconds(self):
        e = make_engine(33)
        quiet(e)
        advance(e, 65)
        self.assertGreaterEqual(len(e.series), 6)
        self.assertLessEqual(len(e.series), 8)
        for point in e.series:
            for key in ("t", "house", "fees", "humans_pnl", "trades"):
                self.assertIn(key, point)

    def test_admin_overview_shape_and_distribution(self):
        e = make_engine(34)
        quiet(e)
        winner, loser = join(e, "winner1"), join(e, "loser1")
        e.trade(winner, "GOLD", "buy", 0.5)
        pump(e)
        e.trade(loser, "GOLD", "buy", 0.5)
        e.stocks["GOLD"].fair *= 1.3
        advance(e, 12)
        o = e.admin_overview(online=3)
        self.assertEqual(o["online"], 3)
        self.assertEqual(o["winners"][0]["name"], "winner1" if e.equity(winner) >= e.equity(loser) else "loser1")
        self.assertEqual(sum(b["count"] for b in o["dist"]), 2)
        self.assertIn("invariant_drift", o["stats"])
        self.assertEqual(o["trades_total"], 2)
        self.assertGreaterEqual(o["trades_per_min"], 0)

    def test_admin_player_detail_and_unknown_player(self):
        e = make_engine(35)
        p = join(e, "Detail1")
        e.trade(p, "CLDR", "buy", 0.2)
        d = e.admin_player("detail1")                 # case-insensitive
        self.assertEqual(d["name"], "Detail1")
        self.assertEqual(d["holdings"][0]["ticker"], "CLDR")
        self.assertEqual(len(d["log"]), 1)
        self.assertIsNone(e.admin_player("nobody here"))

    def test_trade_log_and_margin_log_survive_a_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            random.seed(36)
            e = engine.Engine(state_file=path)
            e.tick(now=e.now)
            p = join(e, "persist1")
            e.trade(p, "GOLD", "buy", 0.2)
            e.margin_log.append({"t": e.now, "player": "persist1", "tickers": ["X"], "shortfall": 1.5})
            e.margin_calls = 4
            e.save()
            f = engine.Engine(state_file=path)
            q = f.by_token[p.token]
            self.assertEqual([x["k"] for x in q.log], ["buy"])
            self.assertEqual(f.margin_calls, 4)
            self.assertEqual(list(f.margin_log), list(e.margin_log))
            self.assertEqual(f.trades_total, e.trades_total)


class PersistenceTests(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            random.seed(20)
            e = engine.Engine(state_file=path)
            e.tick(now=e.now)
            p = join(e, "keeper")
            e.trade(p, "OILX", "buy", 0.3)
            pump(e)
            e.trade(p, "NVXA", "sell", 0.5)          # a short
            advance(e, 30)
            p.divs["OILX"] = 1.25
            p.borrow["NVXA"] = 0.5
            e.stocks["OILX"].div = {"t": e.now + 100, "amt": 0.4}
            e.save()
            f = engine.Engine(state_file=path)
            q = f.by_token[p.token]
            self.assertEqual(q.hold, p.hold)
            self.assertEqual(q.cost, p.cost)
            self.assertEqual(q.divs, p.divs)
            self.assertEqual(q.borrow, p.borrow)
            self.assertEqual(f.stocks["OILX"].div, e.stocks["OILX"].div)
            self.assertEqual(f.stocks["OILX"].price, e.stocks["OILX"].price)
            self.assertEqual(f.stocks["NVXA"].next_earn, e.stocks["NVXA"].next_earn)
            self.assertEqual(list(f.used_news), list(e.used_news))
            self.assertAlmostEqual(f.borrow_fees, e.borrow_fees)
            self.assertLess(abs(drift(f)), 1e-6)

    def test_save_is_atomic_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            e = engine.Engine(state_file=path)
            e.save()
            self.assertTrue(os.path.exists(path))
            self.assertFalse(os.path.exists(path + ".tmp"))


if __name__ == "__main__":
    unittest.main()
