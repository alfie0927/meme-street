"""Achievements, daily quests, the day and all-time boards, tournaments, public profiles, following and chat.
None of it may touch money or prices, so most tests also check that the token books still balance."""
import os
import random
import tempfile
import unittest
from collections import deque

from _helpers import advance, drift, engine, fixed_engine, join, make_engine

import social

DAY = 86400


def fresh(seed=1, **settings):
    e = make_engine(seed, **settings)
    e.now = (int(e.now // DAY) + 1) * DAY + 100        # early in a UTC day, so quest resets don't interfere
    e.tick(now=e.now)
    return e


def step(e, seconds=2):
    e.now += seconds


def unlocked(p):
    return set(p.achievements)


class AchievementTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(11)
        self.p = join(self.e, "achiever")

    def test_nothing_is_unlocked_before_playing(self):
        self.assertEqual(unlocked(self.p), set())

    def test_first_trade_and_notice(self):
        self.e.trade(self.p, "CLDR", "buy", 0.1)
        self.assertIn("first_trade", unlocked(self.p))
        self.assertTrue(any("First steps" in n for n in self.p.notices))

    def test_unlocking_twice_does_not_repeat_the_notice(self):
        self.e.trade(self.p, "CLDR", "buy", 0.1)
        n = len(self.p.notices)
        step(self.e)
        self.e.trade(self.p, "CLDR", "buy", 0.1)
        self.assertEqual(sum("First steps" in x for x in self.p.notices), 1)
        self.assertGreaterEqual(len(self.p.notices), n)

    def test_first_short_and_winning_short(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "sell", 0.2)
        self.assertIn("first_short", unlocked(p))
        self.assertNotIn("winning_short", unlocked(p))
        step(e)
        e.stocks["NVXA"].fair *= 0.8
        e.trade(p, "NVXA", "buy", 1.0)
        self.assertIn("winning_short", unlocked(p))

    def test_a_losing_short_does_not_earn_winning_short(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "sell", 0.2)
        step(e)
        e.stocks["NVXA"].fair *= 1.1
        e.trade(p, "NVXA", "buy", 1.0)
        self.assertNotIn("winning_short", unlocked(p))

    def test_big_win_needs_100_mb_profit_on_one_trade(self):
        e, p = self.e, self.p
        e.credit(p, 9000)
        e.trade(p, "CLDR", "buy", 0.9, amount=1500)
        step(e)
        e.stocks["CLDR"].fair *= 1.3
        e.trade(p, "CLDR", "sell", 1.0)
        self.assertIn("big_win", unlocked(p))
        self.assertIn("green_100", unlocked(p))

    def test_small_win_does_not_earn_big_win(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.2)
        step(e)
        e.stocks["CLDR"].fair *= 1.1
        e.trade(p, "CLDR", "sell", 1.0)
        self.assertNotIn("big_win", unlocked(p))

    def test_index_and_safe_haven_trades(self):
        e, p = self.e, self.p
        e.trade(p, "MSI", "buy", 0.1)
        self.assertIn("index_trader", unlocked(p))
        step(e)
        e.trade(p, "BOND", "buy", 0.1)
        self.assertIn("safe_haven", unlocked(p))

    def test_diversified_and_sector_spread_and_hedger(self):
        e, p = self.e, self.p
        e.credit(p, 9000)
        by_sector = {}
        for tk, s in e.stocks.items():
            if s.asset_type == "equity" and s.sector != "safe":
                by_sector.setdefault(s.sector, tk)
        picks = list(by_sector.values())[:4]
        for tk in picks:
            step(e)
            e.trade(p, tk, "buy", 0.1, amount=200)
        self.assertIn("sector_spread", unlocked(p))
        self.assertNotIn("diversified", unlocked(p))
        step(e)
        e.trade(p, "BOND", "buy", 0.1, amount=200)
        self.assertIn("hedger", unlocked(p))
        self.assertIn("diversified", unlocked(p))

    def test_trade_count_achievements_use_a_lifetime_counter_that_survives_a_season_rollover(self):
        e, p = self.e, self.p
        e.credit(p, 9000)
        for i in range(6):
            step(e)
            e.trade(p, "GOLD", "buy" if i % 2 == 0 else "sell", 0.1, amount=50)
        e._end_season()                                     # resets the season's trade count, not the lifetime one
        self.assertEqual(p.trades, 0)
        for i in range(6):
            step(e)
            e.trade(p, "GOLD", "buy" if i % 2 == 0 else "sell", 0.1, amount=50)
        self.assertGreaterEqual(p.counters["trades"], 10)
        self.assertIn("busy_10", unlocked(p))
        self.assertNotIn("busy_100", unlocked(p))

    def test_dividend_achievement(self):
        e, p = self.e, self.p
        e.trade(p, "OILX", "buy", 0.2)
        s = e.stocks["OILX"]
        s.div = {"t": e.now, "amt": 0.01}
        e._dividends()
        self.assertIn("dividend", unlocked(p))

    def test_margin_call_achievement(self):
        e, p = self.e, self.p
        e.trade(p, "DOGO", "sell", 1.0)
        step(e)
        e.stocks["DOGO"].fair *= 30
        e._margin_calls()
        self.assertEqual(p.margin_calls, 1)
        e._social_t = 0
        e._social_tick()
        self.assertIn("margin_called", unlocked(p))

    def test_season_return_achievements(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 1.0)
        step(e)
        e.stocks["CLDR"].fair *= 1.6
        e._social_t = 0
        e._social_tick()
        self.assertIn("up_10", unlocked(p))

    def test_diamond_hands_needs_an_hour(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.2)
        e.now += 3700
        e.stocks["CLDR"].fair *= 1.1
        e.trade(p, "CLDR", "sell", 1.0)
        self.assertIn("diamond_hands", unlocked(p))

    def test_short_holding_is_not_diamond_hands(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.2)
        e.now += 600
        e.stocks["CLDR"].fair *= 1.1
        e.trade(p, "CLDR", "sell", 1.0)
        self.assertNotIn("diamond_hands", unlocked(p))

    def test_partial_closes_keep_the_original_open_time(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.3)
        opened = p.opened["CLDR"]
        e.now += 4000
        e.stocks["CLDR"].fair *= 1.1
        e.trade(p, "CLDR", "sell", 0.5)
        self.assertEqual(p.opened["CLDR"], opened)
        step(e)
        e.trade(p, "CLDR", "sell", 1.0)
        self.assertNotIn("CLDR", p.opened)
        self.assertIn("diamond_hands", unlocked(p))

    def test_caught_the_reversal(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.2)
        e.now += 30
        e.last_reversal["CLDR"] = e.now
        e.now += 60
        e.stocks["CLDR"].fair *= 1.1
        e.trade(p, "CLDR", "sell", 1.0)
        self.assertIn("caught_reversal", unlocked(p))

    def test_a_reversal_before_you_opened_does_not_count(self):
        e, p = self.e, self.p
        e.last_reversal["CLDR"] = e.now
        e.now += 30
        e.trade(p, "CLDR", "buy", 0.2)
        e.now += 60
        e.stocks["CLDR"].fair *= 1.1
        e.trade(p, "CLDR", "sell", 1.0)
        self.assertNotIn("caught_reversal", unlocked(p))

    def test_a_late_close_after_the_reversal_does_not_count(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.2)
        e.now += 30
        e.last_reversal["CLDR"] = e.now
        e.now += 700
        e.stocks["CLDR"].fair *= 1.1
        e.trade(p, "CLDR", "sell", 1.0)
        self.assertNotIn("caught_reversal", unlocked(p))

    def test_followups_record_company_reversals(self):
        e = fresh(5)
        found = False
        for seed in range(60):
            random.seed(seed)
            e.threads = [{"t": e.now, "tpl": {"scope": "company", "betas": {}, "ticker": "CLDR", "sector": "tech"},
                          "target": "CLDR", "label": "x", "ref": "a story", "sign": 1, "strength": "bystander",
                          "stage": 2, "issue": None}]
            e.last_reversal.clear()
            e._followups()
            if "CLDR" in e.last_reversal:
                found = True
                break
        self.assertTrue(found)

    def test_every_achievement_has_a_name_and_description(self):
        for ach_id, name, desc in social.ACHIEVEMENTS:
            self.assertTrue(name and desc)
        self.assertEqual(len({a[0] for a in social.ACHIEVEMENTS}), len(social.ACHIEVEMENTS))

    def test_unlocking_never_touches_money(self):
        e, p = self.e, self.p
        cash = p.cash
        e._unlock(p, "up_25")
        self.assertEqual(p.cash, cash)
        self.assertLess(abs(drift(e)), 1e-6)

    def test_notices_are_capped_for_offline_players(self):
        p = self.p
        for i in range(100):
            self.e._notify(p, f"n{i}")
        self.assertEqual(len(p.notices), 20)
        self.assertEqual(p.notices[-1], "n99")


class QuestTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(12)
        self.p = join(self.e, "quester")

    def test_everyone_gets_the_same_three_quests_each_day_and_they_change_daily(self):
        day = int(self.e.now // DAY)
        a = self.e.quests_for_day(day)
        self.assertEqual(a, self.e.quests_for_day(day))
        self.assertEqual(len(a), 3)
        self.assertEqual(len({q["id"] for q in a}), 3)
        others = [tuple(q["id"] for q in self.e.quests_for_day(day + i)) for i in range(1, 12)]
        self.assertGreater(len(set(others)), 1)

    def test_quest_goals_are_within_range_and_text_is_filled_in(self):
        for day in range(200):
            for q in self.e.quests_for_day(day):
                self.assertNotIn("{", q["text"])
                self.assertGreater(q["goal"], 0)

    def force(self, ids):
        """Pin today's quests to a given set so tests don't depend on the date."""
        day = int(self.e.now // DAY)
        table = {q[0]: q for q in social.QUESTS}
        quests = []
        for qid in ids:
            _, text, metric, lo, hi, mult = table[qid]
            goal = lo * mult
            quests.append({"id": qid, "text": text.format(goal=goal), "metric": metric, "goal": goal})
        self.e.quests_for_day = lambda d, _q=quests: _q
        return quests

    def test_progress_counts_trades_and_completes_the_quest_with_a_notice(self):
        e, p = self.e, self.p
        self.force(["trades", "short", "index"])
        for i in range(4):
            step(e)
            e.trade(p, "GOLD", "buy" if i % 2 == 0 else "sell", 0.1, amount=30)
        info = e.quests_for(p)
        trades = next(q for q in info["quests"] if q["id"] == "trades")
        self.assertTrue(trades["done"])
        self.assertTrue(any("Quest complete" in n for n in p.notices))

    def test_all_three_unlock_the_streak_and_achievement(self):
        e, p = self.e, self.p
        e.credit(p, 2000)
        self.force(["short", "index", "trades"])
        step(e)
        e.trade(p, "NVXA", "sell", 0.1, amount=100)
        step(e)
        e.trade(p, "MSI", "buy", 0.1, amount=100)
        for i in range(2):
            step(e)
            e.trade(p, "GOLD", "buy", 0.1, amount=30)
        info = e.quests_for(p)
        self.assertTrue(all(q["done"] for q in info["quests"]), info)
        self.assertEqual(info["streak"], 1)
        self.assertIn("quest_day", unlocked(p))

    def test_streak_continues_on_consecutive_days_and_resets_after_a_gap(self):
        e, p = self.e, self.p
        p.quest_last_full = int(e.now // DAY) - 1
        p.quest_streak = 3
        self.force(["short"])
        e.quests_for_day = lambda d: [{"id": "short", "text": "x", "metric": "shorts", "goal": 1}]
        e.trade(p, "NVXA", "sell", 0.1, amount=100)
        self.assertEqual(p.quest_streak, 4)
        self.assertEqual(e.quests_for(p)["streak"], 4)
        # a missed day breaks it
        e.now += 2 * DAY
        self.assertEqual(e.quests_for(p)["streak"], 0)

    def test_progress_resets_at_midnight_utc(self):
        e, p = self.e, self.p
        step(e)
        e.trade(p, "GOLD", "buy", 0.1, amount=30)
        self.assertEqual(e._daily(p)["trades"], 1)
        e.now += DAY
        self.assertEqual(e._daily(p)["trades"], 0)

    def test_sector_quest_counts_distinct_sectors_only(self):
        e, p = self.e, self.p
        e.credit(p, 3000)
        tickers = {}
        for tk, s in e.stocks.items():
            if s.asset_type == "equity":
                tickers.setdefault(s.sector, []).append(tk)
        sectors = list(tickers)[:2]
        for sec in sectors:
            step(e)
            e.trade(p, tickers[sec][0], "buy", 0.1, amount=100)
            step(e)
            e.trade(p, tickers[sec][1], "buy", 0.1, amount=100)
        self.assertEqual(len(e._daily(p)["sectors"]), 2)

    def test_old_days_are_forgotten(self):
        e, p = self.e, self.p
        p.quests_done["1"] = ["x"]
        e._check_quests(p)
        self.assertNotIn("1", p.quests_done)

    def test_quests_have_no_money_reward(self):
        e, p = self.e, self.p
        cash = p.cash
        self.force(["short"])
        e.quests_for_day = lambda d: [{"id": "short", "text": "x", "metric": "shorts", "goal": 1}]
        e.trade(p, "NVXA", "sell", 0.1, amount=100)
        self.assertEqual(sum(1 for n in p.notices if "Quest" in n or "quest" in n) >= 1, True)
        self.assertLess(abs(drift(e)), 1e-6)
        self.assertLessEqual(p.cash, cash + 100 * (1 - engine.FEE) + 1e-9)       # only the short's own proceeds


class DrawdownAndBoardTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(13)
        self.p = join(self.e, "dd_player")
        self.q = join(self.e, "dd_other")

    def test_drawdown_measures_the_fall_from_the_peak(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.5)
        e._board()
        e.stocks["CLDR"].fair *= 1.4
        e._board()
        peak = p.peak
        self.assertGreater(peak, 1.0)
        e.stocks["CLDR"].fair /= 1.4 * 1.2
        e._board()
        self.assertGreater(p.maxdd, 0.1)
        dd = p.maxdd
        e.stocks["CLDR"].fair *= 1.5
        e._board()
        self.assertEqual(p.maxdd, dd)                        # recovering does not erase the drawdown

    def test_drawdown_resets_each_season(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.5)
        e.stocks["CLDR"].fair *= 0.7
        e._board()
        self.assertGreater(p.maxdd, 0.05)
        e._end_season()
        self.assertEqual(p.maxdd, 0.0)
        self.assertIsNone(p.peak)
        e._board()
        self.assertAlmostEqual(p.peak, 1.0)

    def test_a_deposit_is_not_a_gain_and_a_withdrawal_is_not_a_drawdown(self):
        e, p = self.e, self.p
        e._board()
        e.credit(p, 1000)
        e._board()
        self.assertAlmostEqual(p.peak, 1.0, places=9)
        self.assertEqual(p.maxdd, 0.0)
        e.debit(p, 500)
        e._board()
        self.assertEqual(p.maxdd, 0.0)

    def test_there_is_no_risk_adjusted_board_and_no_score_anywhere(self):
        e, p, q = self.e, self.p, self.q
        e.trade(p, "CLDR", "buy", 0.3)
        q.maxdd = 0.3
        e._board()
        self.assertEqual(set(e.boards), {"pnl"})
        self.assertFalse(hasattr(e, "rank_risk"))
        for row in e.board:
            self.assertNotIn("score", row)
        for row in e.board_view():
            self.assertNotIn("score", row)
        self.assertEqual(set(e.me_for(p)["rank"]), {"season", "pnl"})
        self.assertNotIn("risk_rank", repr(e.public_profile(q.name, p)))
        self.assertEqual(e.boards_for(p)["mine"]["dd"], p.maxdd)                 # the drawdown itself is still tracked and shown

    # ---- the boards list only people who have traded in the period they cover
    def test_nobody_is_on_any_board_until_they_trade(self):
        e, p, q = self.e, self.p, self.q
        e._board()
        self.assertEqual(e.board, [])
        self.assertEqual(e.boards["pnl"], [])
        self.assertEqual(e.board_view(), [])
        self.assertIsNone(e.rank.get(p.token))
        self.assertEqual(e.boards_for(p)["counts"], {"season": 0, "pnl": 0})
        self.assertIsNone(e.me_state(p)["rank"])
        self.assertIsNone(e.me_for(p)["rank"]["season"])
        self.assertIsNone(e.me_for(p)["rank"]["pnl"])
        e.trade(p, "CLDR", "buy", 0.2)
        e._board()
        self.assertEqual([r["name"] for r in e.board], ["dd_player"])
        self.assertEqual([r["name"] for r in e.boards["pnl"]], ["dd_player"])
        self.assertEqual(e.rank[p.token], 1)
        self.assertEqual(e.rank_pnl[p.token], 1)
        self.assertNotIn(q.token, e.rank)                     # the one who only watched is on neither board
        self.assertNotIn(q.token, e.rank_pnl)
        self.assertEqual(e.boards_for(q)["mine"]["season"], None)
        self.assertEqual(e.boards_for(p)["counts"], {"season": 1, "pnl": 1})
        self.assertEqual(len(e.board_view()), 1)
        self.assertTrue(all(r["name"] != "dd_other" for r in e.boards_for(p)["season"] + e.boards_for(p)["pnl"]))

    def test_a_player_who_holds_nothing_changed_and_traded_nothing_stays_off_even_with_a_deposit(self):
        e, q = self.e, self.q
        e.credit(q, 500)
        e._board()
        self.assertNotIn(q.token, e.rank)
        self.assertNotIn(q.token, e.rank_pnl)

    def test_the_day_board_empties_when_a_day_ends_but_the_all_time_board_keeps_everyone_who_ever_traded(self):
        e, p, q = self.e, self.p, self.q
        e.trade(p, "CLDR", "buy", 0.2)
        e._board()
        self.assertIn(p.token, e.rank)
        e.season_end = e.now - 1                              # the day is over
        e.tick(now=e.now + 1)
        e.tick(now=e.now + 1)
        self.assertNotIn(p.token, e.rank)                     # nobody has traded in the new day yet
        self.assertEqual(e.board, [])
        self.assertIn(p.token, e.rank_pnl)                    # but p has traded at some time
        e.now += 2
        e.trade(q, "CLDR", "buy", 0.1)
        e._board()
        self.assertEqual([r["name"] for r in e.board], ["dd_other"])
        self.assertEqual({r["name"] for r in e.boards["pnl"]}, {"dd_player", "dd_other"})

    def test_margin_calls_and_paper_contest_trades_do_not_put_anyone_on_a_board(self):
        e, p = self.e, self.p
        e._board()
        e.tick(now=e.now + 1)
        t = next((t for t in e.tournaments if t["kind"] == "marathon"), None)
        if t is not None:
            e.tournament_join(p, t["id"])
            e.contest_trade(p, t["id"], "CLDR", "buy", 0.2)
        e._board()
        self.assertNotIn(p.token, e.rank)
        self.assertNotIn(p.token, e.rank_pnl)

    def test_a_trade_made_before_a_restart_still_counts_afterwards(self):
        import tempfile
        import os as _os
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path = _os.path.join(d, "state.json")
            e = engine.Engine(state_file=path, bots=False)
            p = join(e, "keeps_trading")
            e.trade(p, "CLDR", "buy", 0.2)
            e._board()
            e.save()
            e2 = engine.Engine(state_file=path, bots=False)
            e2._board()
            self.assertEqual([r["name"] for r in e2.board], ["keeps_trading"])
            self.assertEqual([r["name"] for r in e2.boards["pnl"]], ["keeps_trading"])

    def test_alltime_board_is_sorted_by_profit_and_ranks_are_consistent(self):
        e, p, q = self.e, self.p, self.q
        e.trade(p, "CLDR", "buy", 0.4)
        e.trade(q, "CLDR", "buy", 0.02)                       # (a board lists only people who have traded)
        e.stocks["CLDR"].fair *= 1.3
        e._board()
        pnl = e.boards["pnl"]
        self.assertEqual([r["pnl"] for r in pnl], sorted((r["pnl"] for r in pnl), reverse=True))
        self.assertEqual(e.rank_pnl[p.token], 1)
        self.assertEqual(e.rank_pnl[q.token], 2)

    def test_boards_for_marks_the_viewer_and_hides_tokens(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.1)                         # (only people who have traded are on a board)
        e._board()
        boards = e.boards_for(p)
        self.assertEqual({"season", "pnl", "mine", "counts", "players"}, set(boards))
        flat = repr(boards)
        for pl in e.players.values():
            self.assertNotIn(pl.token, flat)
        self.assertTrue(any(r["me"] for r in boards["season"]))
        self.assertEqual(boards["mine"]["season"], e.rank[p.token])

    def test_boards_do_not_move_money(self):
        e = self.e
        e._board()
        self.assertLess(abs(drift(e)), 1e-6)


# (the daily contest tests live in test_contests.py)


class ProfileAndFollowTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(15)
        self.p = join(self.e, "visible")
        self.q = join(self.e, "viewer")

    def test_private_by_default_shows_no_results_or_holdings(self):
        prof = self.e.public_profile("visible", self.q)
        self.assertFalse(prof["public"])
        for key in ("holdings", "season_ret", "alltime_ret", "rank", "trades"):
            self.assertNotIn(key, prof)

    def test_public_shows_results_but_holdings_only_after_the_delay(self):
        e, p, q = self.e, self.p, self.q
        e.trade(p, "CLDR", "buy", 0.3)
        e.set_public(p, True)
        e._holdsnap_t = 0
        e._snapshot_holdings()                                # a snapshot taken now...
        prof = e.public_profile("visible", q)
        self.assertIn("season_ret", prof)
        self.assertIsNone(prof["holdings"])                   # ...is not shown yet
        step(e, 200)
        self.assertIsNone(e.public_profile("visible", q)["holdings"])
        step(e, 150)
        shown = e.public_profile("visible", q)["holdings"]
        self.assertEqual([x["ticker"] for x in shown["positions"]], ["CLDR"])
        self.assertEqual(shown["positions"][0]["side"], "long")
        self.assertGreater(shown["positions"][0]["weight"], 0.2)

    def test_the_delayed_view_never_shows_a_newer_position(self):
        e, p, q = self.e, self.p, self.q
        e.set_public(p, True)
        e._holdsnap_t = 0
        e._snapshot_holdings()                                # empty portfolio at t0
        step(e, 40)
        e.trade(p, "CLDR", "buy", 0.3)
        e._holdsnap_t = 0
        e._snapshot_holdings()                                # CLDR at t0+40
        step(e, 270)                                          # t0+310: only the first snapshot is 300s old
        shown = e.public_profile("visible", q)["holdings"]
        self.assertEqual(shown["positions"], [])
        step(e, 40)
        shown = e.public_profile("visible", q)["holdings"]
        self.assertEqual([x["ticker"] for x in shown["positions"]], ["CLDR"])

    def test_holdings_show_weights_not_sizes(self):
        e, p, q = self.e, self.p, self.q
        e.credit(p, 5000)
        e.trade(p, "CLDR", "buy", 0.1, amount=500)
        e.set_public(p, True)
        e._holdsnap_t = 0
        e._snapshot_holdings()
        step(e, 400)
        text = repr(e.public_profile("visible", q))
        self.assertNotIn("shares", text)
        self.assertNotIn("cash", text)
        self.assertNotIn(p.token, text)

    def test_you_always_see_your_own_results_even_when_private(self):
        prof = self.e.public_profile("visible", self.p)
        self.assertIn("season_ret", prof)
        self.assertTrue(prof["me"])

    def test_profile_names_are_case_insensitive_and_unknown_is_none(self):
        self.assertIsNotNone(self.e.public_profile("VISIBLE", self.q))
        self.assertIsNone(self.e.public_profile("nobody_here", self.q))

    def test_profile_lists_achievements_and_badges(self):
        e, p = self.e, self.p
        e.trade(p, "CLDR", "buy", 0.1)
        p.badges.append({"tournament": "Daily Marathon", "tier": "Gold", "place": 1, "t": e.now, "ret": 0.1})
        prof = e.public_profile("visible", self.q)
        self.assertIn("first_trade", [a["id"] for a in prof["achievements"]])
        self.assertEqual(len(prof["badges"]), 1)

    def test_follow_unfollow_and_limits(self):
        e, p, q = self.e, self.p, self.q
        self.assertTrue(e.follow(q, "visible")[0])
        self.assertFalse(e.follow(q, "visible")[0])
        self.assertFalse(e.follow(q, "viewer")[0])
        self.assertFalse(e.follow(q, "ghost")[0])
        self.assertEqual(e.public_profile("visible", q)["followers"], 1)
        self.assertTrue(e.public_profile("visible", q)["following_them"])
        self.assertTrue(e.unfollow(q, "VISIBLE")[0])
        self.assertFalse(e.unfollow(q, "visible")[0])
        self.assertEqual(e.public_profile("visible", q)["followers"], 0)

    def test_cannot_follow_a_bot_and_follow_list_is_capped(self):
        e, q = self.e, self.q
        bot = engine.Player("robot1", bot=True)
        e._register(bot)
        self.assertFalse(e.follow(q, "robot1")[0])
        for i in range(social.FOLLOW_MAX):
            join(e, f"fol{i}")
            self.assertTrue(e.follow(q, f"fol{i}")[0])
        join(e, "onetoomany")
        ok, msg = e.follow(q, "onetoomany")
        self.assertFalse(ok)
        self.assertIn("at most", msg)

    def test_following_for_returns_profiles(self):
        e, p, q = self.e, self.p, self.q
        e.follow(q, "visible")
        rows = e.following_for(q)
        self.assertEqual([r["name"] for r in rows], ["visible"])



class ChatTests(unittest.TestCase):
    def setUp(self):
        self.e = fresh(17)
        self.a = join(self.e, "chatty")
        self.b = join(self.e, "listener")

    def say(self, p, text, **kw):
        step(self.e, 2)
        return self.e.post_chat(p, text, **kw)

    def test_a_message_is_stored_and_returned_in_history(self):
        ok, msg, m = self.say(self.a, "hello market")
        self.assertTrue(ok)
        self.assertEqual(m["text"], "hello market")
        self.assertEqual([x["text"] for x in self.e.chat_history(self.b)], ["hello market"])

    def test_cleaning_strips_links_control_chars_bad_words_and_caps_length(self):
        self.assertEqual(social.clean_chat("check https://evil.example/x now"), "check [link] now")
        self.assertEqual(social.clean_chat("go to www.scam.net or evil.com/path"), "go to [link] or [link]")
        self.assertEqual(social.clean_chat("a\x00b‮c​d"), "a b c d")
        self.assertEqual(social.clean_chat("this is shit"), "this is ****")
        self.assertEqual(social.clean_chat("SHITTY take"), "****** take")
        self.assertEqual(social.clean_chat("assume   spaces"), "assume spaces")
        self.assertEqual(len(social.clean_chat("x" * 1000)), social.CHAT_MAX)

    def test_html_is_stored_verbatim_for_the_client_to_escape(self):
        ok, _, m = self.say(self.a, "<script>alert(1)</script>")
        self.assertTrue(ok)
        self.assertIn("<script>", m["text"])         # the page uses textContent, so this is harmless; documented

    def test_empty_and_whitespace_messages_are_rejected(self):
        self.assertFalse(self.say(self.a, "   \x00  ")[0])
        self.assertFalse(self.say(self.a, "")[0])

    def test_rate_limits(self):
        e, a = self.e, self.a
        self.assertTrue(e.post_chat(a, "one")[0])
        ok, msg, _ = e.post_chat(a, "two")                  # same instant
        self.assertFalse(ok)
        self.assertIn("Slow down", msg)
        sent = 1
        for i in range(30):
            step(e, 2)
            if e.post_chat(a, f"msg {i}")[0]:
                sent += 1
        self.assertLessEqual(sent, social.CHAT_PER_MINUTE + 15)       # within one minute at most 15

    def test_per_minute_cap(self):
        e, a = self.e, self.a
        ok_count = 0
        for i in range(40):
            e.now += 1.6
            if e.post_chat(a, f"m{i}")[0]:
                ok_count += 1
            if e.now - (e.chat[0]["t"] if e.chat else e.now) > 55:
                break
        self.assertLessEqual(ok_count, social.CHAT_PER_MINUTE)

    def test_repeating_the_same_message_is_blocked_briefly(self):
        self.assertTrue(self.say(self.a, "buy gold")[0])
        ok, msg, _ = self.say(self.a, "buy gold")
        self.assertFalse(ok)
        self.assertIn("just said", msg)
        self.e.now += 20
        self.assertTrue(self.e.post_chat(self.a, "buy gold")[0])

    def test_mute_blocks_and_expires_and_unmute_works(self):
        e, a = self.e, self.a
        self.assertTrue(e.mute("chatty", 600)[0])
        ok, msg, _ = self.say(a, "hi")
        self.assertFalse(ok)
        self.assertIn("muted", msg)
        e.now += 601
        self.assertTrue(e.post_chat(a, "hi")[0])
        e.mute("chatty", 600)
        self.assertTrue(e.mute("chatty", 0)[0])
        self.assertTrue(self.say(a, "back again")[0])
        self.assertFalse(e.mute("ghost", 10)[0])

    def test_chat_can_be_switched_off(self):
        self.e.settings["chat_enabled"] = False
        ok, msg, _ = self.say(self.a, "hello")
        self.assertFalse(ok)
        self.assertIn("off", msg)

    def test_bots_cannot_chat(self):
        bot = engine.Player("robo", bot=True)
        self.e._register(bot)
        self.assertFalse(self.e.post_chat(bot, "beep")[0])

    def test_global_messages_reach_everyone(self):
        _, _, m = self.say(self.a, "hi all")
        self.assertIsNone(self.e.chat_audience(m))

    def test_share_a_trade_uses_the_server_side_record(self):
        e, a = self.e, self.a
        e.trade(a, "CLDR", "buy", 0.2)
        t = a.log[-1]["t"]
        ok, _, m = self.say(a, "nice entry", share_t=t)
        self.assertTrue(ok)
        self.assertEqual(m["share"]["ticker"], "CLDR")
        self.assertEqual(m["share"]["kind"], "buy")
        self.assertGreater(m["share"]["shares"], 0)

    def test_sharing_a_trade_you_did_not_make_or_a_bad_reference_fails(self):
        e, a, b = self.e, self.a, self.b
        e.trade(a, "CLDR", "buy", 0.2)
        t = a.log[-1]["t"]
        self.assertFalse(self.say(b, "stolen", share_t=t)[0])
        self.assertFalse(self.say(a, "x", share_t="abc")[0])
        self.assertFalse(self.say(a, "x2", share_t=12345.0)[0])

    def test_report_delete_and_admin_view(self):
        e, a, b = self.e, self.a, self.b
        _, _, m = self.say(a, "rude-ish message")
        self.assertFalse(e.report_chat(a, m["id"])[0])           # not your own
        self.assertTrue(e.report_chat(b, m["id"])[0])
        self.assertFalse(e.report_chat(b, m["id"])[0])           # only once
        self.assertFalse(e.report_chat(b, 99999)[0])
        view = e.admin_social()
        self.assertEqual(view["reports"][0]["name"], "chatty")
        self.assertEqual(view["messages"][0]["id"], m["id"])
        self.assertEqual(e.delete_chat(m["id"]), 1)
        self.assertEqual(e.chat_history(b), [])
        self.assertEqual(e.delete_chat(m["id"]), 0)

    def test_chat_never_touches_money(self):
        for i in range(10):
            self.say(self.a, f"line {i}")
        self.assertLess(abs(drift(self.e)), 1e-6)


class PersistenceTests(unittest.TestCase):
    def test_social_state_survives_a_save_and_load(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            state = os.path.join(tmp, "state.json")
            random.seed(21)
            e = engine.Engine(state_file=state, bots=False)
            e.now = (int(e.now // DAY) + 1) * DAY + 100
            e.tick(now=e.now)
            a, b = join(e, "keeper"), join(e, "friend")
            e.trade(a, "CLDR", "buy", 0.2)
            step(e)
            e.follow(b, "keeper")
            e.set_public(a, True)
            e.post_chat(a, "remember me")
            step(e)
            e._social_t = 0
            e._social_tick()
            tid = next(t["id"] for t in e.tournaments if t["kind"] == "marathon")
            e.tournament_join(a, tid)
            a.badges.append({"tournament": "Daily Marathon", "tier": "Gold", "place": 2, "t": e.now, "ret": 0.01})
            e.mute("friend", 900)
            before = (dict(a.achievements), dict(a.counters), a.maxdd, a.peak, list(a.opened))
            e.save()
            random.seed(22)
            f = engine.Engine(state_file=state, bots=False)
            a2 = next(p for p in f.players.values() if p.name == "keeper")
            b2 = next(p for p in f.players.values() if p.name == "friend")
            self.assertEqual((dict(a2.achievements), dict(a2.counters), a2.maxdd, a2.peak, list(a2.opened)), before)
            self.assertTrue(a2.public)
            self.assertEqual(b2.following, ["keeper"])
            self.assertEqual(len(a2.badges), 1)
            self.assertEqual([m["text"] for m in f.chat], ["remember me"])
            self.assertEqual(f.chat_seq, e.chat_seq)
            self.assertIn(a2.token, next(t for t in f.tournaments if t["id"] == tid)["entrants"])
            self.assertGreater(f.muted[b2.token], f.now - 1)

    def test_an_old_save_without_social_data_loads_cleanly(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            import json
            state = os.path.join(tmp, "state.json")
            random.seed(23)
            e = engine.Engine(state_file=state, bots=False)
            e.tick(now=e.now)
            join(e, "oldtimer")
            e.save()
            d = json.load(open(state, encoding="utf-8"))
            d.pop("social")
            for x in d["players"]:
                x.pop("social")
            json.dump(d, open(state, "w", encoding="utf-8"))
            f = engine.Engine(state_file=state, bots=False)
            p = next(x for x in f.players.values() if x.name == "oldtimer")
            self.assertEqual(p.achievements, {})
            f.tick(now=f.now + 1)



class NoEdgeAndStressTests(unittest.TestCase):
    def test_social_features_do_not_change_prices_or_the_token_books(self):
        """Run two identical markets; one gets lots of social activity. Prices must match tick for tick."""
        def run(active):
            # a private random stream, so nothing else in the process (other tests, library threads) can disturb it
            saved, engine.random = engine.random, random.Random(77)
            try:
                return play(active)
            finally:
                engine.random = saved

        def play(active):
            # No jump to a fixed time of day: the engine schedules earnings and other events relative to its own
            # start, so two markets created a few seconds apart are only identical if each runs from its own start.
            e = engine.Engine(state_file=None, bots=False)
            e.tick(now=e.now)
            ps = [join(e, f"u{i}") for i in range(4)]
            prices = []
            for k in range(120):
                if active:
                    p = ps[k % 4]
                    if k % 5 == 0:
                        e.post_chat(p, f"talk {k}")
                    e.follow(p, ps[(k + 1) % 4].name)
                    e.set_public(p, k % 2 == 0)
                    for t in e.tournaments:
                        e.tournament_join(p, t["id"])
                    e.public_profile(ps[(k + 2) % 4].name, p)
                    e.boards_for(p)
                    e.me_for(p)
                e.tick(now=e.now + 1)
                prices.append(round(e.stocks["CLDR"].price, 12))
            play.news = [(n["t"], n["text"]) for n in e.news_log]
            play.state = (e.now, e.next_event, e.mkt_volm, e.regime, round(e.mood, 9))
            return prices, drift(e)
        quiet_prices, d1 = run(False)
        first_news, first_state = play.news, play.state
        again, _ = run(False)
        if quiet_prices != again:                       # find where two identical markets part ways
            k = next(i for i, (a, b) in enumerate(zip(quiet_prices, again)) if a != b)
            self.fail(f"the market itself is not repeatable: first difference at tick {k}; "
                      f"news run1 {first_news[-3:]} vs run2 {play.news[-3:]}; state {first_state} vs {play.state}")
        busy_prices, d2 = run(True)
        self.assertEqual(quiet_prices, busy_prices)
        self.assertLess(abs(d1), 1e-6)
        self.assertLess(abs(d2), 1e-6)

    def test_many_players_social_tick_stays_fast(self):
        import time
        e = fresh(31)
        for i in range(300):
            join(e, f"load{i:03d}")
        e._social_t = 0
        t0 = time.perf_counter()
        e._social_tick()
        e._board()
        self.assertLess(time.perf_counter() - t0, 1.5)

    def test_me_for_shape(self):
        e = fresh(32)
        p = join(e, "shape1")
        e._board()
        me = e.me_for(p)
        self.assertEqual(me["total"], len(social.ACHIEVEMENTS))
        self.assertEqual(len(me["achievements"]), me["total"])
        self.assertEqual(len(me["quests"]["quests"]), 3)
        self.assertEqual({t["kind"] for t in me["tournaments"]["active"]}, {"marathon"} if me["tournaments"]["active"] else set())


if __name__ == "__main__":
    unittest.main()
