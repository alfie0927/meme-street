"""The wire protocol's engine side: one `init`, then a small `tick` every second. The key property is that a
client which applies the ticks to its init ends up with exactly the picture a full state would give."""
import json
import random
import unittest

from _helpers import engine, join

PRICE_KEYS = ("price", "chg")


def apply_tick(view, tick):
    """What the page does with a tick (kept deliberately tiny, as in index.html)."""
    for row in view["stocks"]:
        px = tick["px"].get(row["ticker"])
        if px:
            row["price"], row["chg"] = px
            row["spark"].append(px[0])
            del row["spark"][:-60]
    for tk, sl in tick.get("slow", {}).items():
        for row in view["stocks"]:
            if row["ticker"] == tk:
                row.update(sl)
    for item in tick["news"]:
        if item["id"] not in {n["id"] for n in view["news"]}:
            view["news"].insert(0, item)
    if "upcoming" in tick:
        view["upcoming"] = tick["upcoming"]
    if "board" in tick:
        view["board"] = tick["board"]
    view.update(tick["me"])
    view["market"] = tick["market"]
    view["season_left"] = tick["season_left"]


def run(e, n):
    """Tick the engine n times and return the wire messages, round-tripped through JSON like a real connection."""
    out = []
    for _ in range(n):
        e.tick(now=e.now + 1)
        out.append(json.loads(json.dumps(e.build_wire())))
    return out


class WireTests(unittest.TestCase):
    def setUp(self):
        random.seed(41)
        self.e = engine.Engine(state_file=None)
        self.e.tick(now=self.e.now)
        self.p = join(self.e, "wired1")

    def test_ticks_are_numbered_and_carry_every_price(self):
        msgs = run(self.e, 3)
        self.assertEqual([m["seq"] for m in msgs], [1, 2, 3])
        for m in msgs:
            self.assertEqual(m["type"], "tick")
            self.assertEqual(set(m["px"]), set(self.e.stocks))
            for price, chg in m["px"].values():
                self.assertGreater(price, 0)
                self.assertTrue(-1 < chg < 5)

    def test_tick_messages_are_small(self):
        msgs = run(self.e, 12)
        for m in msgs:
            if "slow" not in m:
                self.assertLess(len(json.dumps(m)), 9000)
        init = json.dumps(self.e.init_for(self.p))
        self.assertGreater(len(init), 8 * len(json.dumps(msgs[0])))

    def test_slow_numbers_are_sent_only_every_fifth_tick_and_only_what_changed(self):
        e = self.e
        msgs = run(e, 4)
        self.assertTrue(all("slow" not in m for m in msgs))
        e.stocks["NVXA"].rating = "AA" if e.stocks["NVXA"].rating != "AA" else "A"
        m5 = run(e, 1)[0]
        self.assertEqual(m5["seq"], 5)
        self.assertIn("NVXA", m5["slow"])
        self.assertLess(len(m5["slow"]), len(e.stocks) // 2)       # only what changed, not everything
        self.assertEqual(m5["slow"]["NVXA"]["rating"], e.stocks["NVXA"].rating)
        m6to9 = run(e, 4)
        self.assertTrue(all("slow" not in m for m in m6to9))
        m10 = run(e, 1)[0]
        self.assertNotIn("NVXA", m10.get("slow", {}))         # NVXA's rating was already sent

    def test_price_derived_numbers_do_not_travel_in_slow_updates(self):
        """Market cap, P/E and dividend yield move with the price, so sending them would defeat the deltas; the page
        recomputes them from the live price and these fields."""
        msgs = run(self.e, 60)
        full = msgs[-1]["slow"]
        row = full["NVXA"]["financials"]
        for key in ("market_cap", "pe", "dividend_yield"):
            self.assertNotIn(key, row)
        for key in ("shares_outstanding", "net_income", "annual_dps", "revenue", "eps"):
            self.assertIn(key, row)
        changed = [len(m.get("slow", {})) for m in msgs[:-1]]
        self.assertLess(max(changed), len(self.e.stocks) // 3)

    def test_the_full_picture_still_has_market_cap_pe_and_yield(self):
        run(self.e, 2)
        row = next(r for r in self.e.init_for(self.p)["stocks"] if r["ticker"] == "NVXA")
        fin = row["financials"]
        self.assertAlmostEqual(fin["market_cap"], fin["shares_outstanding"] * row["price"], delta=1e-6)
        for key in ("pe", "dividend_yield", "eps", "annual_dps"):
            self.assertIn(key, fin)

    def test_everything_is_resent_once_a_minute(self):
        msgs = run(self.e, 60)
        full = msgs[-1]
        self.assertEqual(full["seq"], 60)
        self.assertEqual(set(full["slow"]), set(self.e.stocks))

    def test_board_comes_every_fifth_tick(self):
        msgs = run(self.e, 10)
        self.assertEqual([m["seq"] for m in msgs if "board" in m], [5, 10])

    def test_the_calendar_is_sent_only_when_it_changes(self):
        e = self.e
        msgs = run(e, 12)
        self.assertEqual(sum(1 for m in msgs if "upcoming" in m), 1)
        e.stocks["CLDR"].next_earn = e.now + 90
        later = run(e, 5)
        self.assertEqual(sum(1 for m in later if "upcoming" in m), 1)

    def test_recent_headlines_are_repeated_for_a_few_ticks_so_a_skipped_tick_loses_nothing(self):
        e = self.e
        e.news("breaking", "A test headline", ["NVXA"], 1)
        item_id = e.news_log[-1]["id"]
        carried = [m for m in run(e, 8) if item_id in [n["id"] for n in m["news"]]]
        self.assertGreaterEqual(len(carried), 4)
        self.assertLessEqual(len(carried), 7)
        later = run(e, 1)[0]
        self.assertNotIn(item_id, [n["id"] for n in later["news"]])

    def test_news_ids_never_repeat_or_go_backwards(self):
        e = self.e
        for i in range(30):
            e.news("breaking", f"headline number {i}", [], 0)
        ids = [n["id"] for n in e.news_log]
        self.assertEqual(ids, sorted(set(ids)))

    def test_static_version_changes_when_the_listing_changes(self):
        e = self.e
        v0 = run(e, 1)[0]["static_v"]
        self.assertEqual(run(e, 1)[0]["static_v"], v0)
        e.stocks.pop("DOGO")
        self.assertEqual(run(e, 1)[0]["static_v"], v0 + 1)

    def test_no_hidden_state_reaches_the_wire(self):
        e = self.e
        for m in run(e, 6):
            flat = json.dumps(m).lower()
            for bad in ("mood", "narrative", "safety", "token", "persona"):
                self.assertNotIn(bad, flat)
        flat = json.dumps(e.init_for(self.p)).lower()
        for bad in ('"mood"', '"narrative"', '"safety"', e.by_token and self.p.token):
            self.assertNotIn(bad, flat)

    def test_the_session_is_in_every_tick_and_the_init(self):
        e = self.e
        e.settings.update(premarket_seconds=300, aftermarket_seconds=300)
        run(e, 2)
        self.assertIn(e.init_for(self.p)["market"]["phase"], ("pre", "open", "after"))
        self.assertNotIn("profile", e.init_for(self.p)["market"])        # there is no activity chart any more
        for m in run(e, 6):
            self.assertIn(m["market"]["phase"], ("pre", "open", "after"))
            self.assertNotIn("profile", m["market"])

    def test_init_is_the_full_picture_plus_the_protocol_fields(self):
        e = self.e
        run(e, 3)
        init = e.init_for(self.p)
        self.assertEqual(init["type"], "init")
        self.assertEqual(init["seq"], e.wire_seq)
        self.assertEqual(init["static_v"], e.static_v)
        for key in ("stocks", "sectors", "index", "news", "board", "upcoming", "market", "cash", "equity", "holdings",
                    "notices", "chat", "season_left", "players"):
            self.assertIn(key, init)
        self.assertEqual(len(init["stocks"]), len(e.stocks))
        row = init["stocks"][0]
        for key in ("ticker", "name", "desc", "sector", "price", "chg", "spark", "rating", "financials",
                    "margin_req", "borrow_hour"):
            self.assertIn(key, row)

    def test_me_state_does_not_flush_notices_unless_asked(self):
        e, p = self.e, self.p
        p.notices.append("hello")
        self.assertNotIn("notices", e.me_state(p, notices=False))
        self.assertEqual(p.notices, ["hello"])
        self.assertEqual(e.me_state(p)["notices"], ["hello"])
        self.assertEqual(p.notices, [])
        p.notices.append("again")
        self.assertEqual(e.take_notices(p), ["again"])
        self.assertEqual(p.notices, [])

    def test_me_state_reflects_positions(self):
        e, p = self.e, self.p
        run(e, 2)
        e.trade(p, "CLDR", "buy", 0.3)
        run(e, 2)
        me = e.me_state(p)
        self.assertEqual([h["ticker"] for h in me["holdings"]], ["CLDR"])
        self.assertAlmostEqual(me["cash"] + me["holdings"][0]["value"], me["equity"], delta=3.0)

    def test_a_client_that_applies_every_tick_matches_a_full_state(self):
        """The core guarantee: init + deltas == full state, through trades, news, earnings and rating changes."""
        e, p = self.e, self.p
        run(e, 2)
        view = json.loads(json.dumps(e.init_for(self.p)))
        rng = random.Random(5)
        tickers = [t for t, s in e.stocks.items() if s.asset_type == "equity"]
        for i in range(200):
            if i % 7 == 0:
                e.trade(p, rng.choice(tickers), rng.choice(["buy", "sell"]), 0.05)
            if i == 60:
                e.stocks["NVXA"].rating = "CCC"
                e.stocks["NVXA"].revenue *= 1.3
            if i == 90:
                e.stocks["CLDR"].boost_until = e.now + 30
            tick = run(e, 1)[0]
            tick["me"] = json.loads(json.dumps(e.me_state(p, notices=False)))
            apply_tick(view, tick)
        # slow fields can lag by up to four ticks; compare on a fifth-tick boundary
        while True:
            e.tick(now=e.now + 1)
            tick = json.loads(json.dumps(e.build_wire()))
            tick["me"] = json.loads(json.dumps(e.me_state(p, notices=False)))
            apply_tick(view, tick)
            if e.wire_seq % 5 == 0:
                break
        full = json.loads(json.dumps(e.state_for(p)))
        by_view = {r["ticker"]: r for r in view["stocks"]}
        for row in full["stocks"]:
            mine = by_view[row["ticker"]]
            for key in ("price", "chg", "rating", "margin_req",
                        "borrow_hour", "borrow_util"):
                self.assertEqual(mine[key], row[key], (row["ticker"], key))
            for key, value in mine["financials"].items():          # price-derived numbers are worked out by the page
                self.assertEqual(value, row["financials"][key], (row["ticker"], "financials", key))
            self.assertEqual(mine["spark"][-30:], row["spark"][-30:], row["ticker"])
        self.assertEqual(view["cash"], full["cash"])
        self.assertEqual(view["holdings"], full["holdings"])
        self.assertEqual(view["rank"], full["rank"])
        self.assertEqual([n["id"] for n in view["news"]][:5], [n["id"] for n in full["news"]][:5])
        self.assertEqual(view["board"], full["board"])


if __name__ == "__main__":
    unittest.main()
