"""Learning (learning.py, content/learn-*.md, drills.py): the course (tracks of lessons with quizzes), the chart tests on
real game charts, and the challenges (switched off). Nothing on the Learn page pays MB. (The trading journal was removed
on 2026-10-20; the lesson rewards and the lesson challenges on 2026-10-27.)"""
import asyncio
import json
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


def right_answers(e, lesson_id):
    return [q["answer"] for q in e._lesson_by_id[lesson_id]["quiz"]]


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
            self.assertGreaterEqual(len(x["quiz"]), 2, x["id"])
            for q in x["quiz"]:
                self.assertTrue(0 <= q["answer"] < len(q["options"]) and q["why"], (x["id"], q["q"]))
                self.assertEqual(len(set(q["options"])), len(q["options"]), (x["id"], q["q"]))

    def test_every_block_is_known_and_every_link_goes_somewhere(self):
        kinds = set(drills.KINDS)
        for x in self.lessons:
            for b in x["body"]:
                k = next(iter(b))
                self.assertIn(k, ("p", "h", "list", "tip", "here", "warn", "table", "chart", "test", "try"), x["id"])
                if k in ("chart", "test"):
                    self.assertTrue(b[k] in kinds or (k == "test" and b[k] == "any"), (x["id"], b))
                if k == "table":
                    self.assertTrue(all(len(r) == len(b["table"][0]) for r in b["table"]), (x["id"], b["table"][0]))
                if k == "try":
                    href = b["href"]
                    self.assertTrue(href in ROUTES or href.startswith("/stock/"), (x["id"], href))

    def test_the_right_answers_are_spread_over_the_places(self):
        places = [q["answer"] for x in self.lessons for q in x["quiz"]]
        for k in range(3):
            self.assertGreater(places.count(k), len(places) / 5, k)

    def test_a_bad_file_is_refused_with_its_line(self):
        for text in ("## A lesson {a}\n", "# T {t}\n## L {l}\nQ: q?\n- a\n- b\nWHY: no right answer\n",
                     "# T {t}\n## L {l}\n[test nope]\n", "# T {t}\n## L {l}\nQ: q?\n+ a\n+ b\nWHY: two\n"):
            with self.assertRaises(ValueError):
                learning.parse_learn(text)


class LessonTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(21)
        self.p = join(self.e, "student")

    def test_the_page_never_gets_the_answers_before_marking(self):
        les = self.e.lesson("support-resistance")
        self.assertTrue(les["quiz"])
        self.assertNotIn("answer", json.dumps(les["quiz"]))
        self.assertNotIn("why", json.dumps(les["quiz"]))
        self.assertEqual(les["track_title"], "Reading charts")
        self.assertIsNone(self.e.lesson("welcome")["prev"])
        self.assertEqual(self.e.lesson("welcome")["next"]["id"], "first-trade")
        self.assertIsNone(self.e.lesson("nope"))

    def test_passing_a_quiz_is_recorded_and_pays_nothing(self):
        e, p = self.e, self.p
        right = right_answers(e, "welcome")
        wrong = [(a + 1) % 3 for a in right]
        r = e.answer_quiz(p, "welcome", wrong)
        self.assertTrue(r["ok"] and not r["passed"])
        self.assertEqual(r["score"], 0)
        r = e.answer_quiz(p, "welcome", right)
        self.assertTrue(r["passed"] and r["first"])
        self.assertIn("welcome", p.lessons_passed)
        self.assertFalse(e.answer_quiz(p, "welcome", right)["first"])
        self.assertEqual(p.cash, 1000.0)
        self.assertEqual(p.mb_by_source.get("challenge", 0.0), 0.0)
        self.assertFalse(e.answer_quiz(p, "welcome", [0])["ok"])               # every question needs an answer
        self.assertFalse(e.answer_quiz(p, "welcome", [True] * len(right))["passed"])
        view = e.lessons_view(p)
        self.assertEqual(view["passed"], 1)
        self.assertTrue(view["tracks"][0]["lessons"][0]["passed"])
        self.assertLess(abs(drift(e)), 1e-6)

    def test_a_visitor_gets_marks_and_nothing_is_kept(self):
        e = self.e
        r = e.answer_quiz(None, "welcome", right_answers(e, "welcome"))
        self.assertTrue(r["passed"] and not r["first"])
        view = e.lessons_view(None)
        self.assertEqual(view["passed"], 0)
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


class ChallengesOffTests(unittest.TestCase):
    def test_the_game_ships_with_challenges_off_and_they_pay_nothing(self):
        e = make_engine(24)
        self.assertFalse(e.settings["challenges"])                                     # (from base.json)
        p = join(e, "nochal")
        self.assertEqual(e.lessons_view(p)["challenges"], [])
        cash = p.cash
        e.trade(p, "NVXA", "buy", 0.2)
        e.now += 2
        e.set_exit(p, "NVXA", "stop_loss", e.stocks["NVXA"].price * 0.9)               # (a stop: "Protect a trade" when on)
        e.tick(now=e.now + 1)
        self.assertEqual(p.mb_by_source.get("challenge", 0.0), 0.0)
        self.assertLess(p.cash, cash)


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
        self.assertGreaterEqual(p.mb_by_source.get("challenge", 0), 25)
        e.place_order(p, "NVXA", "stop_loss", price * 0.8)          # a second stop on the same position counts once
        self.assertEqual(p.chal["week_stops"]["n"], 1)
        self.step()
        e.trade(p, "NVXA", "sell", 1.0)
        self.assertNotIn("NVXA", p.stop_seen)
        self.assertEqual(p.chal["week_planned"]["n"], 1)

    def test_a_take_profit_counts_for_the_ladder(self):
        e, p = self.e, self.p
        e.trade(p, "NVXA", "buy", 0.3)
        ok, msg = e.place_order(p, "NVXA", "take_profit", e.stocks["NVXA"].price * 1.1)
        self.assertTrue(ok, msg)
        self.assertEqual(p.ladder["n"].get("targets"), 1)
        self.assertIn("once", p.chal["first_target"]["done"])                  # the "Set a target" challenge
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


class LearningServerTests(unittest.TestCase):
    def test_the_learn_endpoints_for_a_visitor_and_a_player(self):
        with IsolatedServer() as srv:
            d = json.loads(http(srv, "/api/learn")[1])                              # public: a visitor sees the course
            self.assertGreaterEqual(d["total"], 90)
            self.assertEqual(d["challenges"], [])
            les = json.loads(http(srv, "/api/learn/lesson/welcome")[1])
            self.assertTrue(les["body"] and les["quiz"])
            self.assertNotIn("answer", json.dumps(les))
            ans = [q["answer"] for q in next(x for x in learning.load_content()[1] if x["id"] == "welcome")["quiz"]]
            r = json.loads(http(srv, "/api/learn/quiz", "POST", {"lesson": "welcome", "answers": ans})[1])
            self.assertTrue(r["passed"] and not r["first"])                        # a visitor: marked, not kept
            a = http_join(srv.url, "HttpStudent")
            h = {"X-Token": a["token"]}
            r = json.loads(http(srv, "/api/learn/quiz", "POST", {"lesson": "welcome", "answers": ans}, headers=h)[1])
            self.assertTrue(r["passed"] and r["first"])
            time.sleep(0.3)
            self.assertEqual(json.loads(http(srv, "/api/learn", headers=h)[1])["passed"], 1)
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
            await d.check("and a chart test to answer", "document.querySelectorAll('[data-lrn-test] [data-lrn-pick]').length",
                          lambda n: n >= 2, wait=10)
            await pg.js("document.querySelector('[data-lrn-test] [data-lrn-pick]').click()")
            await d.check("an answer shows what came next", "document.querySelector('[data-lrn-test] .lrn-out').innerText",
                          lambda t: "Another chart" in t and ("Right." in t or "Not this time." in t), wait=8)
            await d.check("and marks the right choice", "document.querySelectorAll('[data-lrn-test] .lrn-opts button.right').length", 1)
            await pg.js("document.querySelectorAll('.quiz-q').forEach(q=>q.querySelector('input').checked=true);document.getElementById('quiz-go').click()")
            await d.check("the quiz is marked", "document.getElementById('quiz-out').innerText",
                          lambda t: "right" in t, wait=6)
            await d.check("with a note under each question", "[...document.querySelectorAll('.quiz-q .why')].every(w=>w.innerText.length>10)", True)
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
