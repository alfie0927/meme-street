"""Trading bots and backtests (Expert, bots.py): the rule language (parsed, never eval'd, with clear errors), the
indicators against hand calculations, crosses, the news score from the bot's own words, checking a bot's settings, only
Expert running them, a running bot trading on its rules through the real trading code (stocks, leverage, options,
stops and targets), and backtests that fill at the next open and compare with holding."""
import json
import unittest

from _helpers import IsolatedServer, advance, drift, engine, join, make_engine, quiet
import bots
from test_server import http


def candles(closes, t0=0, step=60):
    out = []
    prev = closes[0]
    for i, c in enumerate(closes):
        o = prev
        out.append([t0 + i * step, o, max(o, c) + 0.1, min(o, c) - 0.1, c, 100.0 + i])
        prev = c
    return out


class LanguageTests(unittest.TestCase):
    def test_parses_and_refuses_with_a_reason(self):
        for good in ("cross_above(close, ema(20))", "price >= ema(200) or pnl_pct <= -5", "not flat and rsi() < 30",
                     "news_score > 2 and change(12) > 0", "macd_hist(12, 26, 9) > 0", "close > highest(20)",
                     "prev(close, 3) < close", "abs(pnl_pct) > 2 and (long or short)", "bb_lower(20, 2) > price"):
            bots.parse(good)
        for bad, why in (("ema(close)", "plain numbers"), ("foo > 1", "no 'foo'"), ("rsi(14) <", "Expected"),
                         ("ema(600) > 1", "between 1 and 500"), ("__import__('os')", "can't read"),
                         ("x" * 400, "at most"), ("sma() > 1", "takes 1")):
            with self.assertRaises(bots.RuleError) as cm:
                bots.parse(bad)
            self.assertIn(why, str(cm.exception), bad)

    def test_indicators_match_hand_calculations(self):
        closes = [10, 11, 12, 11, 13, 14, 13, 15, 16, 15, 17, 18]
        ser = bots.Series(candles(closes))
        self.assertAlmostEqual(ser.ind("sma", (3,))[-1], (15 + 17 + 18) / 3)
        ema = ser.ind("ema", (3,))
        e = sum(closes[:3]) / 3
        for c in closes[3:]:
            e = c * 0.5 + e * 0.5
        self.assertAlmostEqual(ema[-1], e)
        self.assertEqual(ser.ind("highest", (3,))[-1], max(ser.h[-4:-1]))   # (the 3 candles before this one)
        self.assertAlmostEqual(ser.ind("change", (2,))[-1], (18 / 15 - 1) * 100)
        rsi = ser.ind("rsi", (5,))[-1]
        self.assertTrue(50 < rsi < 100)
        self.assertIsNone(ser.ind("sma", (20,))[-1])                          # not enough candles yet

    def test_evaluation_and_crosses(self):
        closes = [10] * 25 + [9, 9, 12]
        ser = bots.Series(candles(closes))
        i = len(ser) - 1
        acct = {"position": 0.0, "flat": 1.0}
        self.assertEqual(bots.evaluate(bots.parse("cross_above(close, sma(5))"), ser, i, acct), 1.0)
        self.assertEqual(bots.evaluate(bots.parse("cross_above(close, sma(5))"), ser, i - 1, acct), 0.0)
        self.assertEqual(bots.evaluate(bots.parse("flat and close - prev(close, 1) == 3"), ser, i, acct), 1.0)
        self.assertEqual(bots.evaluate(bots.parse("close > sma(50)"), ser, i, acct), 0.0)          # (no value: false)

    def test_the_news_score_uses_the_bots_own_words(self):
        words = {"beat*": 2, "recall": -3, "above the forecast": 1}
        self.assertEqual(bots.word_score("NovaChips beats estimates, above the forecast", words), 3)
        self.assertEqual(bots.word_score("A recall at NovaChips", words), -3)
        items = [{"t": 0, "text": "NVXA beats", "tickers": ["NVXA"]}, {"t": 0, "text": "Growth beats forecasts", "tickers": []},
                 {"t": 0, "text": "CLDR recall", "tickers": ["CLDR"]}]
        mine, market = bots.news_scores(items, "NVXA", words, 30, 30 * 60)
        self.assertAlmostEqual(mine, 1.0)                                       # one half-life old: half of 2
        self.assertAlmostEqual(market, 1.0)


class SettingsTests(unittest.TestCase):
    def test_a_bot_is_checked(self):
        ok = bots.clean_bot({"name": "x", "tickers": ["nvxa"], "timeframe": "5m",
                             "rules": [{"when": "rsi(14) < 30", "do": "buy", "size": 20}]})
        self.assertEqual(ok["tickers"], ["NVXA"])
        self.assertEqual(ok["rules"][0]["unit"], "pct")
        for bad in ({"tickers": [], "rules": [{"when": "true", "do": "buy"}]},
                    {"tickers": ["A"], "rules": [{"when": "true", "do": "explode"}]},
                    {"tickers": ["A"], "rules": [{"when": "rsi( <", "do": "buy"}]},
                    {"tickers": ["A"], "timeframe": "2m", "rules": [{"when": "true", "do": "buy"}]},
                    {"tickers": ["A"], "rules": [{"when": "true", "do": "buy", "size": 150}]}):
            with self.assertRaises(bots.RuleError):
                bots.clean_bot(bad)


class RunningTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(71)
        quiet(self.e)
        self.p = join(self.e, "botter")

    def bot(self, rules, **kw):
        return dict({"name": "t", "tickers": ["NVXA"], "timeframe": "1m", "rules": rules}, **kw)

    def until(self, test, seconds=400):
        """Tick until test() is true (a fresh game needs two finished candles before a rule can be worked out)."""
        for _ in range(seconds):
            if test():
                return True
            self.e.tick(now=self.e.now + 1)
        return test()

    def test_only_expert(self):
        e, p = self.e, self.p
        ok, msg, _ = e.save_bot(p, self.bot([{"when": "true", "do": "buy", "size": 10}]))
        self.assertFalse(ok)
        self.assertIn("Expert", msg)
        e.admin_pro(p, 30)                                                    # Pro is not enough
        self.assertFalse(e.save_bot(p, self.bot([{"when": "true", "do": "buy", "size": 10}]))[0])
        self.assertIn("error", e.backtest(p, self.bot([{"when": "true", "do": "buy"}]), "NVXA"))

    def test_a_bot_buys_then_sells_on_its_rules(self):
        e, p = self.e, self.p
        e.admin_pro(p, 30, tier="expert")
        self.assertTrue(e.is_pro(p))                                          # Expert includes Pro
        ok, msg, bid = e.save_bot(p, self.bot([{"when": "flat", "do": "buy", "size": 20},
                                               {"when": "long", "do": "sell"}]))
        self.assertTrue(ok, msg)
        self.assertTrue(e.toggle_bot(p, bid, True)[0])
        cash = p.cash
        b = p.bots[0]
        done = lambda: [x["do"] for x in b["log"] if x["ok"] and x["do"] in ("buy", "sell")]
        self.until(lambda: len(done()) >= 2)
        acts = done()
        self.assertGreaterEqual(len(acts), 2, b["log"])
        self.assertEqual(acts[:2], ["buy", "sell"])
        self.assertNotEqual(p.cash, cash)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_stops_leverage_and_options(self):
        e, p = self.e, self.p
        e.admin_pro(p, 30, tier="expert")
        ok, msg, bid = e.save_bot(p, self.bot([{"when": "calls == 0", "do": "buy_call", "size": 5, "strike_pct": 2, "expiry": 1},
                                               {"when": "flat", "do": "buy", "size": 10, "lev": 3}],     # (one action a candle: the first rule that is true)
                                              stop_pct=0.0001))
        self.assertTrue(ok, msg)
        e.toggle_bot(p, bid, True)
        b = p.bots[0]
        self.until(lambda: any(x["do"] == "buy" and x["ok"] for x in b["log"]))
        self.assertTrue(any(x["do"] == "buy" and x["ok"] and "3x" in x["msg"] for x in b["log"]), b["log"])
        self.until(lambda: any(x["do"].startswith("close (") for x in b["log"]))
        self.assertTrue(any(x["do"].startswith("close (") for x in b["log"]), b["log"])     # the tiny stop fired
        self.until(lambda: any(x["do"] == "buy_call" for x in b["log"]))
        self.assertTrue(any(x["do"] == "buy_call" and x["ok"] for x in b["log"]), b["log"])
        self.assertLess(abs(drift(e)), 1e-6)

    def test_bots_stop_when_expert_ends(self):
        e, p = self.e, self.p
        e.admin_pro(p, 30, tier="expert")
        _, _, bid = e.save_bot(p, self.bot([{"when": "false", "do": "buy", "size": 10}]))
        e.toggle_bot(p, bid, True)
        e.admin_pro(p, remove=True, tier="expert")
        advance(e, 2)
        self.assertFalse(p.bots[0]["on"])

    def test_bots_survive_a_save(self):
        import tempfile, os
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            a = engine.Engine(state_file=os.path.join(tmp, "s.json"))
            p = join(a, "keepbot")
            a.admin_pro(p, 30, tier="expert")
            a.save_bot(p, self.bot([{"when": "rsi() < 30", "do": "buy", "size": 10}]))
            a.save()
            b = engine.Engine(state_file=a.state_file)
            q = b.by_token[p.token]
            self.assertEqual(q.bots[0]["rules"][0]["when"], "rsi() < 30")
            self.assertGreater(q.expert_until, b.now)


class BacktestTests(unittest.TestCase):
    def test_fills_at_the_next_open_and_compares_with_holding(self):
        closes = [100 + 0.5 * i for i in range(60)]                          # a steady rise
        bot = bots.clean_bot({"tickers": ["X"], "timeframe": "1m", "rules": [{"when": "flat", "do": "buy", "size": 100}]})
        r = bots.run_backtest(bot, candles(closes), 60, [], cash=1000.0)
        self.assertEqual(r["log"][0]["do"], "buy")
        self.assertEqual(r["log"][0]["price"], candles(closes)[21][1])        # decided at the 20th close, filled at the next open
        self.assertGreater(r["return"], 0)
        self.assertAlmostEqual(r["buy_hold"], closes[-1] / candles(closes)[20][1] - 1)
        self.assertLessEqual(r["max_drawdown"], 0.01)

    def test_stops_and_a_margin_call_on_the_candles_range(self):
        closes = [100.0] * 25 + [99, 97, 90, 80, 85]
        bot = bots.clean_bot({"tickers": ["X"], "timeframe": "1m", "stop_pct": 5,
                              "rules": [{"when": "flat", "do": "buy", "size": 50}]})
        r = bots.run_backtest(bot, candles(closes), 60, [], cash=1000.0)
        stop = [x for x in r["log"] if x["do"] == "stop"]
        self.assertTrue(stop)
        self.assertLess(stop[0]["pnl"], 0)
        lev = bots.clean_bot({"tickers": ["X"], "timeframe": "1m", "rules": [{"when": "flat", "do": "buy", "size": 50, "lev": 10}]})
        r = bots.run_backtest(lev, candles(closes), 60, [], cash=1000.0)
        self.assertTrue(any(x["do"] == "margin call" for x in r["log"]))
        self.assertGreaterEqual(r["end"], 0)

    def test_news_and_options_in_a_backtest(self):
        closes = [100.0] * 25 + [101, 103, 106, 110, 115, 116, 117, 118]
        cs = candles(closes)
        news = [{"t": cs[24][0], "text": "NovaChips beats estimates", "tickers": ["X"]}]
        bot = bots.clean_bot({"tickers": ["X"], "timeframe": "1m",
                              "rules": [{"when": "news_score > 1 and calls == 0", "do": "buy_call", "size": 10, "expiry": 0}]})
        r = bots.run_backtest(bot, cs, 60, news, cash=1000.0, ticker="X")
        self.assertTrue(any(x["do"] == "buy_call" for x in r["log"]), r["log"])

    def test_backtest_over_http(self):
        with IsolatedServer() as srv:
            status, text, _ = http(srv, "/api/join", "POST", {"name": "bt"})
            token = json.loads(text)["token"]
            h = {"X-Token": token}
            bot = {"name": "x", "tickers": ["NVXA"], "timeframe": "1m", "rules": [{"when": "flat", "do": "buy", "size": 10}]}
            d = json.loads(http(srv, "/api/bots/backtest", "POST", {"bot": bot, "ticker": "NVXA"}, headers=h)[1])
            self.assertIn("Expert", d.get("error", ""))
            d = json.loads(http(srv, "/api/bots", headers=h)[1])
            self.assertFalse(d["expert"])
            self.assertIn("ema", d["funcs"])


if __name__ == "__main__":
    unittest.main()
