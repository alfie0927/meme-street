"""Learning (learning.py, content/learn-*.md, drills.py): the course (tracks of lessons), the chart tests on
real game charts, and the challenges (switched off). Nothing on the Learn page pays MB. (The trading journal was removed
on 2026-10-20; the lesson rewards, the lesson challenges and then the quizzes on 2026-10-27.)"""
import asyncio
import json
import tempfile
import time
import unittest

from _cdp import find_browser, open_page
from _helpers import IsolatedServer, drift, join, make_engine
import drills  # noqa: E402  (after _helpers, which puts the project on the path)
import learning  # noqa: E402
from test_gateway import join as http_join
from test_browser import Driver
from test_server import http

ROUTES = ("/", "/learn", "/holdings", "/portfolio", "/history", "/leaders", "/social", "/profile", "/shop", "/calendar",
          "/bots", "/bots/guide", "/daily")


class CourseTests(unittest.TestCase):
    """The course files themselves: every one parses, and every lesson is complete."""

    @classmethod
    def setUpClass(cls):
        cls.tracks, cls.lessons = learning.load_content()

    def test_the_course_is_complete(self):
        self.assertEqual(self.tracks[0]["id"], "start")
        self.assertEqual(self.lessons[0]["id"], "welcome")                    # (the new player's banner links to it)
        self.assertGreaterEqual(len(self.tracks), 17)
        self.assertGreaterEqual(len(self.lessons), 90)
        track_ids = {t["id"] for t in self.tracks}
        for t in self.tracks:
            self.assertTrue(t["blurb"], t["id"])
            self.assertTrue(any(x["track"] == t["id"] for x in self.lessons), t["id"])
        for x in self.lessons:
            self.assertIn(x["track"], track_ids)
            self.assertTrue(x["summary"] and len(x["body"]) >= 3, x["id"])
            self.assertTrue(learning.exercises(x) or x["id"] == "glossary", x["id"])   # every lesson ends with exercises (LP2); the glossary is a reference
        self.assertGreaterEqual(sum(len(learning.exercises(x)) for x in self.lessons), 250)

    def test_every_block_is_known_and_every_link_goes_somewhere(self):
        kinds = set(drills.KINDS)
        for x in self.lessons:
            for b in x["body"]:
                k = next(iter(b))
                self.assertIn(k, ("p", "h", "list", "tip", "here", "warn", "table", "chart", "test", "try", "q", "task", "mine", "calc"), x["id"])
                if k == "q" and "num" not in b:
                    self.assertTrue(len(b["options"]) >= 2 and b["answer"] in range(len(b["options"])) and b["why"], (x["id"], b["q"]))
                if k == "calc":
                    self.assertIn(b["calc"], learning.CALC_KINDS)
                if k == "task":
                    self.assertIn(b["task"], learning.TASK_KINDS)
                if k in ("chart", "test"):
                    self.assertTrue(b[k] in kinds or (k == "test" and b[k] == "any"), (x["id"], b))
                if k == "table":
                    self.assertTrue(all(len(r) == len(b["table"][0]) for r in b["table"]), (x["id"], b["table"][0]))
                if k == "try":
                    href = b["href"]
                    self.assertTrue(href in ROUTES or href.startswith("/stock/"), (x["id"], href))

    def test_a_bad_file_is_refused_with_its_line(self):
        for text in ("## A lesson {a}\n", "# T {t}\n## L {l}\n[test nope]\n", "# T {t}\n## L {l}\n[chart any]\n",
                     "# T {t}\n## L {l}\n[try nowhere] text\n", "# Track with no id\n", "# T {t}\n## L {l}\n[task nope] text\n",
                     "# T {t}\n## L {l}\nQ: q?\n+ a\n- b\n", "# T {t}\n## L {l}\nQ: q?\n+ a\n+ b\nWHY: w\n",
                     "# T {t}\n## L {l}\nQ: q?\n- a\n- b\nWHY: w\n", "# T {t}\n## L {l}\nQ: q?\nplain\nWHY: w\n",
                     "# T {t}\n## L {l}\n[calc nope]\n", "# T {t}\n## L {l}\n[test rsi support]\n", "# T {t}\n## L {l}\nQ: q?\n= abc\nWHY: w\n"):
            with self.assertRaises(ValueError):
                learning.parse_learn(text)


class LessonTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(21)
        self.p = join(self.e, "student")

    def test_a_question_is_parsed_and_its_answer_is_kept_from_the_page(self):
        tracks, lessons = learning.parse_learn("# T {t}\nblurb\n## L {l}\nSUMMARY: s\nText.\n[task stop] Protect it.\nQ: Two?\n- One\n+ Two\n- Three\nWHY: Because.\n")
        body = lessons[0]["body"]
        self.assertEqual(body[1], {"task": "stop", "text": "Protect it."})
        self.assertEqual(body[2], {"q": "Two?", "options": ["One", "Two", "Three"], "answer": 1, "why": "Because."})
        self.assertEqual(learning.exercises(lessons[0]), [(1, "task"), (2, "q")])
        les = self.e.lesson("welcome")
        qs = [b for b in les["body"] if "q" in b]
        self.assertTrue(qs and all("answer" not in b and "why" not in b and "i" in b for b in qs))
        self.assertEqual(les["total"], len([b for b in les["body"] if "q" in b or "task" in b or "test" in b]))

    def test_answering_earns_xp_and_passes_the_lesson_when_every_exercise_is_done(self):
        e, p = self.e, self.p
        les = e.lesson("stocks-shares", p)                                        # questions only
        qs = [b for b in les["body"] if "q" in b]
        self.assertFalse(les["passed"])
        first = e.learn_answer(p, "stocks-shares", qs[0]["i"], 99)               # wrong: explained, counts once, a little XP
        self.assertFalse(first["right"])
        self.assertTrue(first["why"] and first["answer"] in range(3))
        self.assertEqual(first["xp"], learning.XP_WRONG)
        self.assertEqual(p.xp, learning.XP_WRONG)
        again = e.learn_answer(p, "stocks-shares", qs[0]["i"], first["answer"])
        self.assertNotIn("xp", again)                                             # the second answer earns nothing
        for b in qs[1:]:
            e.learn_answer(p, "stocks-shares", b["i"], 0)
        self.assertIn("stocks-shares", p.passed)
        self.assertEqual(e.lesson("stocks-shares", p)["passed"], True)
        self.assertGreaterEqual(p.xp, learning.XP_WRONG + learning.XP_PASS)
        self.assertEqual(p.xp_days[e._learn_day()], p.xp)
        self.assertEqual(e.learn_streak(p), 1)
        view = e.lessons_view(p)
        self.assertEqual((view["passed"], view["xp"], view["streak"], view["today"]), (1, p.xp, 1, p.xp))
        self.assertEqual(view["next"], "welcome")                                 # the first unpassed lesson
        self.assertIn("error", e.learn_answer(p, "stocks-shares", 0, 0))          # not a question
        self.assertIn("error", e.learn_answer(p, "nope", 0, 0))
        self.assertEqual(p.cash, 1000.0)                                          # nothing here pays MB
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_visitor_can_answer_and_nothing_is_kept(self):
        e = self.e
        les = e.lesson("stocks-shares")
        q = next(b for b in les["body"] if "q" in b)
        a = e.learn_answer(None, "stocks-shares", q["i"], 0)
        self.assertIn("right", a)
        self.assertNotIn("xp", a)
        self.assertNotIn("done", a)

    def test_a_task_done_on_the_market_passes_the_lessons_that_ask_for_it(self):
        e, p = self.e, self.p
        les = e.lesson("first-trade", p)
        task = next(b for b in les["body"] if "task" in b)
        self.assertEqual(task["task"], "stop")
        for b in les["body"]:
            if "q" in b:
                e.learn_answer(p, "first-trade", b["i"], 0)
        self.assertNotIn("first-trade", p.passed)                                 # the task is still to do
        e.trade(p, "NVXA", "buy", 0.2)
        self.assertIn("trade", p.tasks)                                           # the first trade is the welcome lesson's task
        xp = p.xp
        e.place_order(p, "NVXA", "stop_loss", e.stocks["NVXA"].price * 0.9)
        self.assertIn("stop", p.tasks)
        self.assertEqual(p.xp, xp + learning.XP_TASK + learning.XP_PASS)
        self.assertIn("first-trade", p.passed)
        e.place_order(p, "NVXA", "stop_loss", e.stocks["NVXA"].price * 0.85)   # a second stop earns nothing more
        self.assertEqual(p.xp, xp + learning.XP_TASK + learning.XP_PASS)
        e.now += 2
        e.trade(p, "NVXA", "sell", 1.0)
        self.assertIn("planned", p.tasks)
        e.now += 2
        e.trade(p, "OILX", "sell", 0.2)
        self.assertIn("short", p.tasks)
        self.assertEqual(e.learning_summary(p)["tasks"], 4)

    def test_the_placement_test_marks_the_units_known_in_a_row_and_starts_the_path_after_them(self):
        e, p = self.e, self.p
        t = e.placement_new()
        qs = t["questions"]
        self.assertEqual(len(qs), learning.PLACEMENT_UNITS)
        self.assertEqual([q["track"] for q in qs], [tr["id"] for tr in e.tracks[1:1 + learning.PLACEMENT_UNITS]])
        self.assertTrue(all("answer" not in q and q["options"] for q in qs))
        def shown(who, q):                                                          # the right answer's slot as `who` sees it
            b = e._lesson_by_id[q["lesson"]]["body"][q["i"]]
            return e._perm(who, q["lesson"], q["i"], len(b["options"])).index(b["answer"])
        right = [shown(p, q) for q in qs]
        answers = [{"lesson": q["lesson"], "i": q["i"], "choice": right[n] if n < 3 else (right[n] + 1) % len(q["options"])}
                   for n, q in enumerate(qs)]                                      # the first three units known, the fourth missed
        vright = [shown(None, q) for q in qs]
        vanswers = [{"lesson": q["lesson"], "i": q["i"], "choice": vright[n] if n < 3 else (vright[n] + 1) % len(q["options"])}
                    for n, q in enumerate(qs)]
        v = e.placement_grade(None, vanswers)                                       # a visitor: graded, nothing kept
        self.assertEqual([r["right"] for r in v["results"]][:4], [True, True, True, False])
        self.assertEqual(v["start"]["track"], e.tracks[4]["title"])
        self.assertNotIn("passed", v)
        self.assertIsNone(p.placed)
        r = e.placement_grade(p, answers)
        known = {"start"} | {tr["id"] for tr in e.tracks[1:4]}
        self.assertEqual(set(r["known"]), {tr["title"] for tr in e.tracks[1:4]})
        self.assertTrue(all(x["id"] in p.passed for x in e.lessons if x["track"] in known))
        self.assertFalse(any(x["id"] in p.passed for x in e.lessons if x["track"] not in known))
        self.assertEqual(p.placed, e.tracks[4]["id"])
        self.assertEqual(p.xp, 0)                                                   # placing earns nothing
        view = e.lessons_view(p)
        self.assertEqual(view["next"], next(x["id"] for x in e.lessons if x["track"] == e.tracks[4]["id"]))
        self.assertEqual(view["placed"], p.placed)
        self.assertIn("error", e.placement_grade(p, [{"lesson": "nope", "i": 0, "choice": 0}]))
        self.assertIn("error", e.placement_grade(p, []))
        q2 = join(e, "expert")
        all_right = [{"lesson": q["lesson"], "i": q["i"], "choice": shown(q2, q)} for q in qs]
        r2 = e.placement_grade(q2, all_right)
        self.assertEqual((r2["start"]["track"], q2.placed), (e.tracks[1 + learning.PLACEMENT_UNITS]["title"], e.tracks[1 + learning.PLACEMENT_UNITS]["id"]))

    def test_wrong_answers_make_a_weak_skill_and_a_review_that_pays_a_little_and_passes_nothing(self):
        e, p = self.e, self.p
        self.assertEqual(e.weak_skills(p), [])
        self.assertIn("error", e.review_new(p))
        self.assertIn("error", e.review_new(None))
        les = e.lesson("stocks-shares", p)
        qs = [b for b in les["body"] if "q" in b]
        for b in qs[:3]:
            e.learn_answer(p, "stocks-shares", b["i"], 99)                        # three wrong in Market basics
        self.assertEqual(len(p.attempts), 3)
        self.assertEqual(p.attempts[-1][1:3], ["basics", False])
        weak = e.weak_skills(p)
        self.assertEqual((weak[0]["skill"], weak[0]["n"], weak[0]["acc"]), ("basics", 3, 0.0))
        self.assertEqual(e.lessons_view(p)["weak"][0]["skill"], "basics")
        r = e.review_new(p)
        self.assertTrue(r["items"] and all(x.get("lesson") and "answer" not in x for x in r["items"]))
        self.assertTrue(all(e._lesson_by_id[x["lesson"]]["track"] == "basics" for x in r["items"]))
        xp, passed, ex_before = p.xp, dict(p.passed), {k: list(v) for k, v in p.ex.items()}
        x = r["items"][0]
        b = e._lesson_by_id[x["lesson"]]["body"][x["i"]]
        right = e._perm(p, x["lesson"], x["i"], len(b["options"])).index(b["answer"])
        for at in p.attempts:
            at[0] -= 1                                                              # (yesterday's answers: today's review pays)
        a = e.learn_answer(p, x["lesson"], x["i"], right, review=True)
        self.assertTrue(a["right"])
        self.assertEqual(a["xp"], learning.XP_REVIEW)
        self.assertEqual(p.xp, xp + learning.XP_REVIEW)
        self.assertEqual(e.learn_answer(p, x["lesson"], x["i"], right, review=True)["xp"], 0)     # once a day per question
        self.assertEqual(p.passed, passed)                                        # a review never passes
        self.assertEqual(p.ex, ex_before)                                          # and adds nothing to a lesson's progress
        self.assertEqual(len(p.attempts), 5)                                      # three in the lesson, two in the review
        q = e.drill_new("rsi")
        d = e.drill_answer(p, q["id"], 0, review=True)
        self.assertEqual(p.attempts[-1][1], "rsi")
        self.assertIn("weak", d)
        q2 = e.drill_new("rsi")
        rsi_right = e._drill_q[q2["id"]][1]
        self.assertEqual(e.drill_answer(p, q2["id"], rsi_right, review=True)["xp"], 0)      # a kind pays once a day in review
        for _ in range(301):
            e._attempt(p, "basics", True)
        self.assertEqual(len(p.attempts), learning.ATTEMPTS_MAX)

    def test_the_weekly_league_ranks_this_weeks_xp(self):
        e, p = self.e, self.p
        q = join(e, "rival")
        self.assertEqual(e.league(p)["rows"], [])
        e._xp(p, 30)
        e._xp(q, 50)
        q.xp_weeks[e._week_key(e.now - 14 * 86400)] = 999                        # an old week counts for nothing
        lg = e.league(p)
        self.assertEqual([(r["name"], r["xp"]) for r in lg["rows"]], [("rival", 50), ("student", 30)])
        self.assertEqual((lg["rank"], lg["xp"], lg["learners"]), (2, 30, 2))
        self.assertIsNone(e.league(None)["rank"])
        bot = join(e, "housebot1")
        bot.hb = {"style": "scalper"}                                              # a house bot learns nothing (loop 9)
        self.assertEqual(e._xp(bot, 40), 0)
        self.assertEqual(bot.xp, 0)
        self.assertNotIn("housebot1", [r["name"] for r in e.league(p)["rows"]])
        self.assertEqual(e.learning_summary(p)["units_total"], len({x["track"] for x in e.path_lessons}))
        self.assertEqual(e.lessons_view(p)["league"]["rank"], 2)
        self.assertEqual(e.learning_summary(p)["week_xp"], 30)

    def test_options_are_shuffled_per_player_and_the_coin_flip_test_is_never_a_weak_spot(self):
        e, p = self.e, self.p
        q = join(e, "other")
        les_p, les_q, les_v = e.lesson("stocks-shares", p), e.lesson("stocks-shares", q), e.lesson("stocks-shares")
        qp = next(b for b in les_p["body"] if "q" in b)
        orig = e._lesson_by_id["stocks-shares"]["body"][qp["i"]]
        self.assertEqual(sorted(qp["options"]), sorted(orig["options"]))
        slots = set()
        for who, les in ((p, les_p), (q, les_q), (None, les_v)):
            b = next(x for x in les["body"] if x.get("i") == qp["i"])
            slot = b["options"].index(orig["options"][orig["answer"]])
            self.assertEqual(e.learn_answer(who, "stocks-shares", qp["i"], slot)["right"], True)
            slots.add(slot)
        self.assertEqual(e.lesson("stocks-shares", p)["body"][qp["i"]]["options"], qp["options"])   # stable for one player
        all_slots = set()
        for x in e.lessons[:30]:
            for k, kind in learning.exercises(x):
                if kind == "q":
                    b = x["body"][k]
                    all_slots.add(e._perm(p, x["id"], k, len(b["options"])).index(b["answer"]))
        self.assertEqual(all_slots, {0, 1, 2})                                     # the right answer lands in every slot
        for _ in range(6):
            e._attempt(p, "next", False)
        self.assertEqual([w["skill"] for w in e.weak_skills(p)], [])
        les = e.lesson("stocks-shares", p)
        self.assertIn(str(qp["i"]), les["answers"])                                 # an answered question shows its answer again
        self.assertEqual(les["answers"][str(qp["i"])]["why"], orig["why"])

    def test_closes_stops_exits_and_r_are_counted_for_the_trading_card(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "buy", 0.3)
        price = e.stocks["NVXA"].price
        e.place_order(p, "NVXA", "stop_loss", price * 0.9)
        st = p.stop_px["NVXA"]
        self.assertAlmostEqual(st["stop"], price * 0.9)
        self.assertGreater(st["risk"], 0)
        e.now += 2
        e.trade(p, "NVXA", "sell", 1.0)
        self.assertEqual((p.counters["closes"], p.counters["closes_with_stop"]), (1, 1))
        self.assertEqual(len(p.r_log), 1)
        self.assertNotIn("NVXA", p.stop_px)
        e.now += 2
        e.trade(p, "OILX", "buy", 0.2)
        e.now += 2
        e.trade(p, "OILX", "sell", 1.0)
        self.assertEqual((p.counters["closes"], p.counters["closes_with_stop"]), (2, 1))
        e.now += 2
        e.trade(p, "GOLD", "buy", 0.2)
        s = e.stocks["GOLD"]
        e.place_order(p, "GOLD", "take_profit", s.price * 1.05)
        s.fair = s.price * 1.06
        for _ in range(60):
            e.tick(now=e.now + 1)
            if "GOLD" not in p.hold:
                break
        self.assertEqual(p.counters.get("exit_target"), 1)

    def test_the_trading_card_reads_the_players_own_closes_and_points_at_lessons(self):
        e, p = self.e, self.p
        m = e.trading_summary(p)
        self.assertEqual((m["closes"], m["all_closes"], m["tips"]), (0, 0, []))
        for tk in ("NVXA", "CLDR", "OILX"):                                        # three closes, none with a stop
            e.trade(p, tk, "buy", 0.1)
            e.now += 2
            e.trade(p, tk, "sell", 1.0)
            e.now += 2
        m = e.trading_summary(p)
        self.assertEqual((m["closes"], m["all_closes"], m["with_stop"]), (3, 3, 0))
        self.assertIn(m["win_rate"], (None, 0.0, 1 / 3, 2 / 3, 1.0))              # (no ledger in the test worlds: no P&L per close)
        self.assertGreater(m["fees"], 0)
        self.assertEqual(m["tips"][0]["lesson"], "stop-placement")
        les = e.lesson("stop-placement", p)
        self.assertTrue(any("mine" in b for b in les["body"]))
        self.assertEqual(les["mine"]["all_closes"], 3)
        self.assertNotIn("mine", e.lesson("stop-placement"))                      # a visitor gets the block, no numbers
        self.assertEqual(e.lessons_view(p)["mine"]["closes"], 3)

    def test_the_new_tasks_fire_from_their_hooks(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "buy", 0.2)
        self.assertTrue(e.place_order(p, "NVXA", "limit_buy", e.stocks["NVXA"].price * 0.9, pct=0.1)[0])
        self.assertIn("limit", p.tasks)
        e.place_order(p, "NVXA", "trailing_stop", 5)
        self.assertIn("trail", p.tasks)
        self.assertIn("stop", p.tasks)
        e.set_note(p, p.log[-1]["t"], "my first note")
        self.assertIn("note", p.tasks)
        px = e.stocks["NVXA"].price
        self.assertTrue(e.place_bracket(p, "NVXA", px * 1.2, px * 0.8)[0])
        self.assertIn("bracket", p.tasks)
        e.now += 2
        e.trade(p, "OILX", "sell", 0.2)
        e.place_order(p, "OILX", "stop_loss", e.stocks["OILX"].price * 1.1)
        self.assertIn("short_stop", p.tasks)
        for kind in ("limit", "trail", "option", "note", "short_stop", "bracket", "trade", "stop", "planned"):   # (target and short: kinds kept for old saves)
            self.assertTrue(any(b.get("task") == kind for x in e.lessons for b in x["body"]), kind)

    def test_a_lesson_without_exercises_is_a_reference_and_not_a_step(self):
        e, p = self.e, self.p
        glossary = e._lesson_by_id["glossary"]
        self.assertEqual(learning.exercises(glossary), [])
        self.assertNotIn(glossary, e.path_lessons)
        self.assertEqual(e.lessons_view(p)["total"], len(e.path_lessons))
        self.assertEqual(e.learning_summary(p)["total"], len(e.path_lessons))
        for x in e.lessons:                                                         # the task comes after the questions
            ex = learning.exercises(x)
            tasks = [k for k, kind in ex if kind == "task"]
            qs = [k for k, kind in ex if kind == "q"]
            if tasks and qs:
                self.assertGreater(min(tasks), max(qs), x["id"])

    def test_levels_goals_and_the_celebrations(self):
        e, p = self.e, self.p
        self.assertEqual(learning.level_of(0)["name"], "Trainee")
        self.assertEqual((learning.level_of(199)["name"], learning.level_of(200)["name"], learning.level_of(6000)["next"]), ("Trainee", "Apprentice", None))
        self.assertFalse(e.set_goal(p, 33)[0])
        self.assertTrue(e.set_goal(p, 50)[0])
        self.assertEqual(p.goal, 50)
        day = int(e.now // 86400)
        p.xp_days = {str(day - 1): 5}
        e._xp(p, 10)
        self.assertTrue(any("streak: 2 days" in n for n in p.notices))
        self.assertFalse(any("goal reached" in n for n in p.notices))
        e._xp(p, 40)
        self.assertTrue(any("Daily goal reached: 50" in n for n in p.notices))
        e._xp(p, 200)
        self.assertTrue(any("Level up: you are now Apprentice" in n for n in p.notices))
        view = e.lessons_view(p)
        self.assertEqual((view["level"]["name"], view["goals"]), ("Apprentice", [20, 50, 100]))
        self.assertEqual(e.learning_summary(p)["level"]["name"], "Apprentice")
        # finishing a unit says so
        for x in e.lessons:
            if x["track"] == "start":
                for k, kind in learning.exercises(x):
                    if kind == "q":
                        e.learn_answer(p, x["id"], k, 0)
        for kind in ("trade", "stop"):
            e._learn_task(p, kind)
        self.assertTrue(all(x["id"] in p.passed for x in e.path_lessons if x["track"] == "start"))
        self.assertTrue(any("Unit finished: Start here" in n for n in p.notices))

    def test_number_questions_and_generated_calculations(self):
        e, p = self.e, self.p
        tracks, lessons = learning.parse_learn("# T {t}\nb\n## L {l}\nSUMMARY: s\nText.\nQ: Two plus two?\n= 4 ±0.5\nWHY: Maths.\nQ: Half?\n= 50 ±2%\nWHY: Half.\n[calc sizing]\n")
        body = lessons[0]["body"]
        self.assertEqual((body[1]["num"], body[1]["tol"], body[2]["tol"]), (4.0, 0.5, 1.0))
        self.assertEqual(learning.exercises(lessons[0]), [(1, "q"), (2, "q"), (3, "calc")])
        les = e.lesson("position-sizing", p)
        calc = next(b for b in les["body"] if b.get("num"))
        self.assertIn("MB", calc["q"])
        self.assertEqual(e.lesson("position-sizing", p)["body"][calc["i"]]["q"], calc["q"])      # the same numbers all day
        spec = e._calc(p, "position-sizing", calc["i"], "sizing")
        wrong = e.learn_answer(p, "position-sizing", calc["i"], spec["num"] * 2)
        self.assertFalse(wrong["right"])
        self.assertAlmostEqual(wrong["answer"], spec["num"], places=3)
        self.assertEqual(wrong["xp"], learning.XP_WRONG)
        again = e.learn_answer(p, "position-sizing", calc["i"], spec["num"] * 1.01)             # within 2%: right, but already answered
        self.assertTrue(again["right"])
        self.assertNotIn("xp", again)
        self.assertFalse(e.learn_answer(p, "position-sizing", calc["i"], "nope")["right"])
        for kind in learning.CALC_KINDS:
            c = e._calc(p, "x", 0, kind)
            self.assertTrue(c["q"] and c["why"] and c["tol"] > 0, kind)
        ok = e.learn_answer(None, "position-sizing", calc["i"], e._calc(None, "position-sizing", calc["i"], "sizing")["num"])
        self.assertTrue(ok["right"])
        self.assertTrue(all("options" in e._lesson_by_id[q["lesson"]]["body"][q["i"]] for q in e.placement_new(p)["questions"]))

    def test_a_chart_test_can_be_narrowed_to_the_lesson(self):
        e = self.e
        for _ in range(3):
            q = e.drill_new("level", "support")
            self.assertNotIn("error", q)
            self.assertIn("support", q["q"].lower() + " ".join(q["options"]).lower())
        q = e.drill_new("level", "resistance")
        self.assertIn("resistance", q["q"].lower() + " ".join(q["options"]).lower())
        q = e.drill_new("candle", "engulfing")
        self.assertTrue("error" in q or "ngulfing" in " ".join(q["options"]))
        self.assertNotIn("error", e.drill_new("rsi", "support"))                  # an option a kind ignores does no harm
        les = e.lesson("support-resistance")
        self.assertTrue(any(b.get("test") == "level" and b.get("opt") == "support" for b in les["body"]))

    def test_the_streak_counts_days_in_a_row(self):
        e, p = self.e, self.p
        day = int(e.now // 86400)
        p.xp_days = {str(day - 3): 5, str(day - 2): 5, str(day - 1): 5}
        self.assertEqual(e.learn_streak(p), 3)                                    # yesterday still counts today
        p.xp_days = {str(day - 3): 5, str(day - 1): 5}
        self.assertEqual(e.learn_streak(p), 1)
        p.xp_days = {str(day - 2): 5}
        self.assertEqual(e.learn_streak(p), 0)

    def test_a_lesson_comes_with_its_track_and_neighbours(self):
        les = self.e.lesson("support-resistance")
        self.assertTrue(les["body"])
        self.assertNotIn("quiz", les)
        self.assertEqual(les["track_title"], "Reading charts")
        self.assertIsNone(self.e.lesson("welcome")["prev"])
        self.assertEqual(self.e.lesson("welcome")["next"]["id"], "first-trade")
        self.assertIsNone(self.e.lesson("nope"))

    def test_opening_a_lesson_counts_it_as_read_and_pays_nothing(self):
        e, p = self.e, self.p
        e.lesson("welcome", p)
        first = p.lessons_passed["welcome"]
        e.now += 60
        e.lesson("welcome", p)
        self.assertEqual(p.lessons_passed, {"welcome": first})                    # the first read is kept
        self.assertIsNone(e.lesson("nope", p))
        self.assertEqual(p.cash, 1000.0)
        self.assertEqual(p.mb_by_source.get("challenge", 0.0), 0.0)
        view = e.lessons_view(p)
        self.assertEqual(view["read"], 1)
        self.assertTrue(view["tracks"][0]["lessons"][0]["read"])
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_visitor_reads_and_nothing_is_kept(self):
        e = self.e
        self.assertTrue(e.lesson("welcome")["body"])
        view = e.lessons_view(None)
        self.assertEqual(view["read"], 0)
        self.assertNotIn("week", view)
        self.assertEqual(len(view["tests"]), len(drills.KINDS))


class ChartTestTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(25)
        self.p = join(self.e, "chartist")

    def test_a_test_hides_its_answer_until_it_is_answered_and_counts_the_score(self):
        e, p = self.e, self.p
        q = e.drill_new("level")
        self.assertNotIn("error", q)
        self.assertNotIn("answer", q)
        self.assertNotIn("result", q)
        self.assertTrue(all(not x["after"] for x in q["lines"] + q["marks"]))
        a = e.drill_answer(p, q["id"], 0)
        self.assertIn(a["right"], (True, False))
        self.assertTrue(a["candles"] and a["result"] and a["explain"])
        self.assertEqual(p.drills["level"], [int(a["right"]), 1])
        self.assertEqual(a["score"], p.drills["level"])
        self.assertTrue(e.drill_answer(p, q["id"], 0)["expired"])              # one answer per test
        self.assertTrue(e.drill_answer(p, "made-up", 0)["expired"])

    def test_every_kind_and_a_mixed_one_can_be_asked_and_a_visitor_keeps_no_score(self):
        e = self.e
        for kind in drills.KINDS + ("any",):
            q = e.drill_new(kind)
            self.assertNotIn("error", q, kind)
            a = e.drill_answer(None, q["id"], 1)
            self.assertNotIn("score", a)
        self.assertIn("error", e.drill_new("nope"))

    def test_a_reel_gets_a_company_and_its_candles(self):
        e = self.e
        s = next(x for x in e.stocks.values() if x.asset_type == "equity")
        d = e.reel_stock(s.ticker, "1m")
        self.assertEqual((d["name"], d["desc"]), (s.name, s.desc))
        self.assertTrue(all(len(c) == 5 for c in d["candles"]))
        self.assertIsNone(e.reel_stock("NOPE"))

    def test_an_old_test_expires(self):
        e = self.e
        q = e.drill_new("trend")
        e.now += learning.TEST_KEEP + 1
        self.assertTrue(e.drill_answer(self.p, q["id"], 0)["expired"])

    def test_a_lessons_example_comes_with_its_answer_and_stays_for_a_while(self):
        e = self.e
        x = e.drill_example("pattern")
        self.assertIn(x["answer"], range(len(x["options"])))
        self.assertTrue(0 < x["upto"] < len(x["candles"]) - 1)
        self.assertIs(e.drill_example("pattern"), x)
        e.now += learning.EXAMPLE_KEEP + 1
        self.assertIsNot(e.drill_example("pattern"), x)
        self.assertIn("error", e.drill_example("any"))

    def test_real_candles_are_used_once_the_game_has_them(self):
        e = self.e
        s = e.stocks["NVXA"]
        rows = list(s.tf["1m"])
        price = s.price
        fake = [[k * 60.0, price, price * 1.002, price * 0.998, price * (1 + 0.001 * ((k % 7) - 3)), 100.0]
                for k in range(300)]
        s.tf["1m"].clear()
        s.tf["1m"].extend(fake)
        stocks, frames = e.stocks, learning.TEST_TIMEFRAMES
        e.stocks, learning.TEST_TIMEFRAMES = {"NVXA": s}, {"1m": "1-minute"}
        try:
            q = e.drill_new("next")
            self.assertEqual(q["tf"], "1-minute")
            a = e.drill_answer(self.p, q["id"], 0)
            self.assertEqual((a["where"]["ticker"], a["where"]["name"]), ("NVXA", s.name))
        finally:
            e.stocks, learning.TEST_TIMEFRAMES = stocks, frames
            s.tf["1m"].clear()
            s.tf["1m"].extend(rows)


class HabitsTests(unittest.TestCase):
    """This week's habits (LP11): the old challenges, always on, paid in XP and never in MB."""

    def test_habits_are_on_and_pay_xp_not_mb(self):
        e = make_engine(24)
        p = join(e, "habit")
        view = e.lessons_view(p)
        self.assertEqual([c["id"] for c in view["challenges"]], ["week_stops", "week_planned", "week_targets", "week_sized"])
        self.assertTrue(all("xp" in c and "reward" not in c for c in view["challenges"]))
        cash = p.cash
        for tk in ("NVXA", "CLDR", "OILX", "GOLD", "AIFX"):
            e.trade(p, tk, "buy", 0.1)
            e.now += 2
            e.set_exit(p, tk, "stop_loss", e.stocks[tk].price * 0.9)
        self.assertEqual(len(p.chal["week_stops"]["done"]), 1)
        self.assertGreaterEqual(p.xp, 30)
        self.assertEqual(p.mb_by_source.get("challenge", 0.0), 0.0)
        self.assertLess(p.cash, cash)                                              # only the trades moved cash
        self.assertEqual(p.chal["week_sized"]["n"], 3)                             # 10% positions with a 10% stop risk 1%: all count, capped at the target


class ChallengeTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(22, challenges=True)
        self.p = join(self.e, "trader")

    def step(self, n=2):
        for _ in range(n):
            self.e.tick(now=self.e.now + 1)

    def test_a_stop_on_a_position_completes_protect_a_trade_and_closing_it_counts_as_planned(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "buy", 0.3)
        price = e.stocks["NVXA"].price
        ok, msg = e.place_order(p, "NVXA", "stop_loss", price * 0.9)
        self.assertTrue(ok, msg)
        self.assertIn("NVXA", p.stop_seen)
        self.assertEqual(p.mb_by_source.get("challenge", 0), 0)
        e.place_order(p, "NVXA", "stop_loss", price * 0.8)          # a second stop on the same position counts once
        self.assertEqual(p.chal["week_stops"]["n"], 1)
        self.step()
        e.trade(p, "NVXA", "sell", 1.0)
        self.assertNotIn("NVXA", p.stop_seen)
        self.assertEqual(p.chal["week_planned"]["n"], 1)

    def test_a_take_profit_counts_for_the_habits(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "buy", 0.3)
        ok, msg = e.place_order(p, "NVXA", "take_profit", e.stocks["NVXA"].price * 1.1)
        self.assertTrue(ok, msg)
        self.assertEqual(p.chal["week_targets"]["n"], 1)

    def test_the_learning_state_survives_a_save(self):
        p = self.p
        p.lessons_passed["basics"] = 1.0
        p.stop_seen.append("NVXA")
        q = type(p)("copy")
        old = dict(learning.dump_player(p), journal=[{"id": "j1", "t": 1.0, "ticker": "NVXA", "setup": "other"}])
        learning.load_player(q, json.loads(json.dumps(old)))                  # a save from when the journal existed
        self.assertEqual(q.lessons_passed, {"basics": 1.0})
        self.assertEqual(q.stop_seen, ["NVXA"])
        self.assertNotIn("journal", learning.dump_player(q))
        p.passed["welcome"] = 2.0
        p.ex["welcome"] = [3, 5]
        p.xp, p.xp_days, p.tasks = 42, {"20000": 42}, ["stop", "nope"]
        r = type(p)("copy2")
        learning.load_player(r, json.loads(json.dumps(learning.dump_player(p))))
        self.assertEqual((r.passed, r.ex, r.xp, r.xp_days, r.tasks), ({"welcome": 2.0}, {"welcome": [3, 5]}, 42, {"20000": 42}, ["stop"]))
        s = type(p)("old")
        learning.load_player(s, {"lessons_passed": {}})                           # a save from before the path
        self.assertEqual((s.passed, s.ex, s.xp, s.tasks, s.goal, s.placed, s.attempts, s.xp_weeks), ({}, {}, 0, [], learning.GOAL, None, [], {}))


class LearnCheckTests(unittest.TestCase):
    """The Learn loop's automated rubric (tools/learn_check.py): a report over the real course, and a broken course fails."""

    def test_every_public_lesson_page_renders(self):
        """/lessons/{id} for every lesson, including the ones with [calc] and [mine] blocks, which once raised (loop 10)."""
        import lessonpages
        _, lessons = learning.load_content()
        for x in lessons:
            h = lessonpages.body_html(x)
            self.assertTrue(h, x["id"])
        sizing = next(x for x in lessons if x["id"] == "position-sizing")
        self.assertIn("Work it out", lessonpages.body_html(sizing))

    def test_the_check_reports_and_flags_a_broken_course(self):
        import importlib.util
        import os as _os
        spec = importlib.util.spec_from_file_location("learn_check", _os.path.join(_os.path.dirname(__file__), "..", "tools", "learn_check.py"))
        lc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lc)
        rows = lc.run()
        self.assertGreaterEqual(len(rows), 8)
        self.assertTrue(rows[0][1], rows[0])                                      # the real course parses
        self.assertTrue(all(len(r) == 3 for r in rows))
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            long_text = " ".join(["word"] * 700)
            lines = ["# Charts {charts}", "blurb", "## Long {long}", "SUMMARY: s", long_text, "### H", "Text.",
                     "Q: Same question here?", "+ A long right answer indeed", "- b", "- c", "WHY: w",
                     "Q: Same question here!", "+ A long right answer indeed", "- b", "- c", "WHY: w", "[try /nowhere] x"]
            with open(_os.path.join(tmp, "learn-00-x.md"), "w", encoding="utf-8") as f:
                f.write(chr(10).join(lines) + chr(10))
            bad = {n: ok for n, ok, _ in lc.run(_os.path.join(tmp, "learn-*.md"), tests_text="")}
            self.assertFalse(bad["no lesson over 600 prose words"])
            self.assertFalse(bad["no near-duplicate questions"])
            self.assertFalse(bad["every chart lesson has a chart or a test"])
            self.assertFalse(bad["every [try] link resolves"])
            self.assertFalse(bad["right answer the longest option in under 45%"])


class LearningServerTests(unittest.TestCase):
    def test_the_learn_endpoints_for_a_visitor_and_a_player(self):
        with IsolatedServer() as srv:
            d = json.loads(http(srv, "/api/learn")[1])                              # public: a visitor sees the course
            self.assertGreaterEqual(d["total"], 90)
            self.assertEqual(d["challenges"], [])
            les = json.loads(http(srv, "/api/learn/lesson/welcome")[1])            # a visitor reads it
            self.assertTrue(les["body"] and les["next"])
            self.assertEqual(http(srv, "/api/learn/lesson/nope")[0], 404)
            self.assertIn(http(srv, "/api/learn/quiz", "POST", {"lesson": "welcome", "answers": [0]})[0], (404, 405))
            a = http_join(srv.url, "HttpStudent")
            h = {"X-Token": a["token"]}
            http(srv, "/api/learn/lesson/welcome", headers=h)                       # a player reads it
            time.sleep(0.3)
            self.assertEqual(json.loads(http(srv, "/api/learn", headers=h)[1])["read"], 1)
            q = json.loads(http(srv, "/api/learn/test?kind=level", headers=h)[1])
            self.assertTrue(q["id"] and q["candles"] and q["options"])
            self.assertNotIn("answer", q)
            r = json.loads(http(srv, "/api/learn/test", "POST", {"id": q["id"], "choice": 0}, headers=h)[1])
            self.assertTrue(r["candles"] and r["result"])
            self.assertEqual(r["score"][1], 1)
            time.sleep(0.6)
            r = json.loads(http(srv, "/api/learn/test", "POST", {"id": q["id"], "choice": 0}, headers=h)[1])
            self.assertTrue(r["expired"])
            time.sleep(0.6)
            ex = json.loads(http(srv, "/api/learn/test?kind=pattern&example=1", headers=h)[1])
            self.assertIn("answer", ex)
            time.sleep(0.6)
            self.assertIn("error", json.loads(http(srv, "/api/learn/test?kind=nope", headers=h)[1]))
            self.assertIn(http(srv, "/api/journal", headers=h)[0], (404, 405))
            les = json.loads(http(srv, "/api/learn/lesson/stocks-shares", headers=h)[1])      # the path (LP1-LP3)
            qi = next(b["i"] for b in les["body"] if "q" in b)
            time.sleep(0.3)
            a = json.loads(http(srv, "/api/learn/answer", "POST", {"lesson": "stocks-shares", "i": qi, "choice": 0}, headers=h)[1])
            self.assertIn("why", a)
            self.assertIn(a["xp"], (learning.XP_RIGHT, learning.XP_WRONG))
            self.assertEqual(a["total"], les["total"])
            time.sleep(0.3)
            d = json.loads(http(srv, "/api/learn", headers=h)[1])
            self.assertEqual((d["xp"], d["streak"], d["today"]), (a["xp"], 1, a["xp"]))


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class LearningBrowserTests(unittest.TestCase):
    """The Learn and Calendar pages and the chart tools, in a real browser."""

    def test_the_new_pages_and_chart_tools(self):
        with IsolatedServer() as srv:
            d, errors = asyncio.run(self._pages(srv.url))
        d.verdict(self, errors)

    async def _pages(self, base):
        proc, pg, _ = await open_page(debug_port=9362)
        d = Driver(pg)
        try:
            await d.join(base, "learner")
            await d.check("a new player is pointed at the first lesson", "document.getElementById('learn-banner').innerHTML",
                          lambda t: "first lesson" in t and "l=welcome" in t, wait=8)
            await pg.goto(base + "/learn", 3)
            await d.check("every track is listed", "document.querySelectorAll('.lrn-track').length", lambda n: n >= 17, wait=10)
            await d.check("with all its lessons", "document.querySelectorAll('.lrn-ls li').length", lambda n: n >= 90)
            await d.check("and every kind of chart test", "document.querySelectorAll('.lrn-test').length",
                          lambda n: n >= len(drills.KINDS) + 1)
            await d.check("and no challenges or MB to earn (switched off)", "document.querySelectorAll('.chal').length+'|'+document.getElementById('learn-body').innerText",
                          lambda t: t.startswith("0|") and "Challenges" not in t and "MB a week" not in t)
            await pg.goto(base + "/learn?l=support-resistance", 3)
            await d.check("a lesson opens to read", "document.querySelector('.lesson-body') && document.querySelector('.lesson-body').innerText.length",
                          lambda n: bool(n) and n > 1500, wait=10)
            await d.check("with a real chart as an example", "document.querySelectorAll('[data-lrn-ex] svg').length", 1, wait=10)
            await pg.js("document.querySelector('[data-lrn-show]').click()")
            await d.check("whose answer can be shown", "document.querySelector('[data-lrn-ex] .lrn-out').innerText",
                          lambda t: "changes every quarter of an hour" in t, wait=5)
            await pg.js("while(document.querySelector('[data-lrn-later]'))lrnReveal()")   # exercises come one at a time; show them all
            await d.check("and a chart test to answer", "document.querySelectorAll('[data-lrn-test] [data-lrn-pick]').length",
                          lambda n: n >= 2, wait=10)
            await pg.js("document.querySelector('[data-lrn-test] [data-lrn-pick]').click()")
            await d.check("an answer shows what came next", "document.querySelector('[data-lrn-test] .lrn-out').innerText",
                          lambda t: "Another chart" in t and ("Right." in t or "Not this time." in t), wait=8)
            await d.check("and marks the right choice", "document.querySelectorAll('[data-lrn-test] .lrn-opts button.right').length", 1)
            await d.check("with questions to answer", "document.querySelectorAll('[data-lrn-q] [data-lrn-choice]').length", lambda n: n >= 4)
            await pg.js("document.querySelector('[data-lrn-q] [data-lrn-choice]').click()")
            await d.check("an answer is marked and explained", "document.querySelector('[data-lrn-q] .lrn-out').innerText",
                          lambda t: "Right." in t or "Not this one." in t, wait=8)
            await d.check("and the header counts it", "document.getElementById('lrn-head').innerText", lambda t: "of" in t and "done" in t, wait=5)
            await pg.goto(base + "/learn", 3)
            await d.check("and the path shows the XP earned", "document.querySelector('.lrn-prog').innerText",
                          lambda t: "XP" in t and "0 of" not in t.split("XP")[0], wait=10)
            await d.check("and points at the next lesson", "document.querySelector('.lrn-next').innerText", lambda t: "Start" in t or "Next" in t or "Continue" in t)
            await pg.goto(base + "/learn?test=rsi", 3)
            await d.check("a page of chart tests opens", "document.querySelectorAll('[data-lrn-test] svg').length", 1, wait=10)
            await d.check("there is no Journal in the menu", "!document.querySelector('#nav a[href=\"/journal\"]')", True)
            await pg.goto(base + "/calendar", 3)
            await d.check("the calendar grid lists releases", "[...document.querySelectorAll('#cal-grid .cal-chip')].some(c=>c.title.includes('Weekly jobless claims'))",
                          True, wait=10)   # (weekly: always in a month)
            await pg.goto(base + "/stock/NVXA", 4)
            await d.check("the chart has volume bars", "document.querySelector('#chart-wrap svg') && document.querySelector('#chart-wrap svg').textContent",
                          lambda t: bool(t) and "Volume" in t, wait=15)
            await d.check("the stock page says how big the company is", "document.getElementById('d-facts').innerText",
                          lambda t: "Large cap" in t, wait=5)
            await pg.js("document.getElementById('ind-open').click()")
            await pg.js("document.querySelector('#ind-list [data-ind=rsi]').click()")
            await d.check("RSI adds a panel", "document.querySelector('#chart-wrap svg').textContent", lambda t: "RSI 14" in t, wait=5)
            await pg.js("openIndCfg('rsi')")
            await d.check("an indicator's settings name its lesson", "document.getElementById('ind-cfg').innerText", lambda t: "Lesson:" in t and "Momentum" in t, wait=3)
            await pg.js("openIndCfg(null)")
            await d.check("the risk tool links to its lessons", "document.querySelectorAll('#d-risk .lrn-help').length", lambda n: n >= 3)
            await pg.js("document.querySelector('#ind-list [data-ind=bb]').click()")
            await d.check("a Pro indicator says it is Pro", "document.getElementById('toast').textContent", lambda t: "Pro" in t, wait=3)
            await pg.js("document.body.click();document.querySelector('#draw-tools [data-dt=menu]').click();document.querySelector('.dt-menu [data-tool=hline]').click()")
            await pg.js("(()=>{const w=document.getElementById('chart-wrap'),r=w.querySelector('svg').getBoundingClientRect();"
                        "w.dispatchEvent(new PointerEvent('pointerdown',{clientX:r.left+r.width/3,clientY:r.top+r.height*0.25,bubbles:true}))})()")
            await d.check("a level can be drawn", "document.querySelectorAll('#chart-wrap [data-dw]').length", 1, wait=4)
            await pg.js("(()=>{const d=document.getElementById('d-risk');d.open=true;const s=document.getElementById('r-stop');"
                        "s.value=String((S.byT.NVXA.price*0.95).toFixed(2));s.dispatchEvent(new Event('input',{bubbles:true}))})()")
            await d.check("the risk tool sizes the trade", "document.getElementById('r-out').innerText",
                          lambda t: "shares" in t and "1.0% of your equity" in t, wait=4)
        finally:
            errors = list(pg.errors)
            proc.terminate()
        return d, errors


if __name__ == "__main__":
    unittest.main()
