"""Learning (learning.py, lessons.json): lessons and quizzes, challenges that pay MB within a weekly cap, and the trading
journal that links entries to positions and fills in the result. Quizzes ship switched off (`quizzes: false`); the quiz
tests switch them on, and QuizzesOffTests check what players get today."""
import asyncio
import json
import unittest

from _cdp import find_browser, open_page
from _helpers import IsolatedServer, drift, join, make_engine
import learning  # noqa: E402  (after _helpers, which puts the project on the path)
from test_gateway import join as http_join
from test_browser import Driver
from test_server import http


def right_answers(e, lesson_id):
    return [q["answer"] for q in e._lesson_by_id[lesson_id]["quiz"]]


class LessonTests(unittest.TestCase):
    """The quizzes themselves, switched on (they are kept for later)."""

    def setUp(self):
        self.e = make_engine(21, quizzes=True)
        self.p = join(self.e, "student")

    def test_the_lessons_load_and_every_quiz_is_well_formed(self):
        e = self.e
        self.assertGreaterEqual(len(e.lessons), 10)
        ids = [x["id"] for x in e.lessons]
        self.assertEqual(len(ids), len(set(ids)))
        for x in e.lessons:
            self.assertTrue(x["body"] and x["quiz"], x["id"])
            for q in x["quiz"]:
                self.assertTrue(0 <= q["answer"] < len(q["options"]), (x["id"], q["q"]))
                self.assertTrue(q.get("why"), (x["id"], q["q"]))

    def test_the_page_never_gets_the_answers_before_marking(self):
        les = self.e.lesson("levels")
        self.assertNotIn("answer", json.dumps(les["quiz"]))
        self.assertNotIn("why", json.dumps(les["quiz"]))
        self.assertIsNone(self.e.lesson("nope"))

    def test_passing_a_quiz_pays_once_and_a_wrong_answer_fails(self):
        e, p = self.e, self.p
        wrong = [(a + 1) % 2 for a in right_answers(e, "basics")]
        r = e.answer_quiz(p, "basics", wrong)
        self.assertFalse(r["passed"])
        self.assertEqual(p.cash, 1000.0)
        r = e.answer_quiz(p, "basics", right_answers(e, "basics"))
        self.assertTrue(r["passed"] and r["first"])
        reward = e.settings.get("lesson_reward", 20) + 25           # the lesson, and the "First lesson" challenge
        self.assertAlmostEqual(p.cash, 1000.0 + reward)
        self.assertAlmostEqual(p.mb_by_source["challenge"], reward)
        r = e.answer_quiz(p, "basics", right_answers(e, "basics"))
        self.assertTrue(r["passed"] and not r["first"])
        self.assertAlmostEqual(p.cash, 1000.0 + reward)              # no second payment
        self.assertFalse(e.answer_quiz(p, "basics", [0])["ok"])        # every question needs an answer
        self.assertLess(abs(drift(e)), 1e-6)

    def test_the_basics_and_graduate_challenges(self):
        e, p = self.e, self.p
        start = [x["id"] for x in e.lessons if x.get("level") == "Start here"]
        for lid in start:
            e.answer_quiz(p, lid, right_answers(e, lid))
        view = {c["id"]: c for c in e.lessons_view(p)["challenges"]}
        self.assertTrue(view["basics"]["done"])
        self.assertFalse(view["graduate"]["done"])
        for x in e.lessons:
            e.answer_quiz(p, x["id"], right_answers(e, x["id"]))
        view = {c["id"]: c for c in e.lessons_view(p)["challenges"]}
        self.assertTrue(view["graduate"]["done"])

    def test_rewards_stop_at_the_weekly_cap(self):
        e, p = self.e, self.p
        e.settings["challenge_week_cap"] = 60
        for x in e.lessons:
            e.answer_quiz(p, x["id"], right_answers(e, x["id"]))
        self.assertAlmostEqual(p.mb_by_source["challenge"], 60.0)
        self.assertEqual(e.challenge_week_status(p)["left"], 0)


class QuizzesOffTests(unittest.TestCase):
    """What ships: lessons are plain reading, with no quiz, no lesson reward and no challenge that needs a quiz."""

    def setUp(self):
        self.e = make_engine(23)
        self.p = join(self.e, "reader")

    def test_the_game_ships_with_quizzes_off(self):
        self.assertFalse(self.e.settings["quizzes"])                                   # (from base.json)
        self.assertFalse(self.e.quizzes_on())

    def test_a_lesson_has_no_quiz_and_answers_are_refused_without_paying(self):
        e, p = self.e, self.p
        les = e.lesson("basics")
        self.assertTrue(les["body"])
        self.assertEqual(les["quiz"], [])
        r = e.answer_quiz(p, "basics", [q["answer"] for q in e._lesson_by_id["basics"]["quiz"]])
        self.assertFalse(r["ok"])
        self.assertEqual(p.cash, 1000.0)
        self.assertEqual(p.lessons_passed, {})

    def test_the_learn_page_offers_no_quiz_reward_or_quiz_challenge(self):
        view = self.e.lessons_view(self.p)
        self.assertFalse(view["quizzes"])
        self.assertEqual(view["lesson_reward"], 0)
        self.assertTrue(all(x["questions"] == 0 and not x["passed"] for x in view["lessons"]))
        ids = {c["id"] for c in view["challenges"]}
        self.assertTrue(ids)
        self.assertFalse(ids & {"first_lesson", "basics", "graduate"})
        self.assertIn("first_stop", ids)


class ChallengeAndJournalTests(unittest.TestCase):
    def setUp(self):
        self.e = make_engine(22)
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

    def test_a_journal_idea_becomes_a_trade_and_gets_its_result_in_mb_and_r(self):
        e, p = self.e, self.p
        price = e.stocks["NVXA"].price
        ok, msg = e.add_journal(p, "nvxa", "support", "bounce off the level", stop=price * 0.95, target=price * 1.1)
        self.assertTrue(ok, msg)
        entry = p.journal[-1]
        self.assertEqual(entry["status"], "idea")
        e.trade(p, "NVXA", "buy", 0.5)
        self.assertEqual(entry["status"], "open")
        self.assertEqual(entry["side"], "long")
        e.stocks["NVXA"].fair *= 1.05
        self.step()
        e.trade(p, "NVXA", "sell", 1.0)
        self.assertEqual(entry["status"], "closed")
        self.assertGreater(entry["result"], 0)
        self.assertAlmostEqual(entry["r"], entry["result"] / (price * 0.05 * entry["shares"]), places=1)
        self.assertTrue(e.review_journal(p, entry["id"], "Waited for the level and it worked")[0])
        self.assertEqual(p.chal["week_review"]["n"], 1)
        view = e.journal_view(p)
        self.assertEqual(view["summary"]["closed"], 1)
        self.assertNotIn("pro_stats", view)                          # the breakdown is a Pro tool
        p.pro_until = e.now + 3600
        self.assertEqual(e.journal_view(p)["pro_stats"]["by_setup"][0]["setup"], "support")

    def test_bad_journal_entries_are_refused(self):
        e, p = self.e, self.p
        self.assertFalse(e.add_journal(p, "NOPE", "support")[0])
        self.assertFalse(e.add_journal(p, "NVXA", "astrology")[0])
        self.assertFalse(e.add_journal(p, "NVXA", "support", stop="abc")[0])
        self.assertFalse(e.add_journal(p, "NVXA", "support", stop=-1)[0])
        self.assertTrue(e.add_journal(p, "NVXA", "support", plan="x" * 2000)[0])
        self.assertEqual(len(p.journal[-1]["plan"]), 400)

    def test_the_learning_state_survives_a_save(self):
        p = self.p
        p.lessons_passed["basics"] = 1.0
        p.journal.append({"id": "j1", "t": 1.0, "ticker": "NVXA", "setup": "other", "status": "idea"})
        q = type(p)("copy")
        learning.load_player(q, json.loads(json.dumps(learning.dump_player(p))))
        self.assertEqual(q.lessons_passed, {"basics": 1.0})
        self.assertEqual(q.journal[0]["id"], "j1")


class LearningServerTests(unittest.TestCase):
    def test_lessons_and_journal_over_http_with_quizzes_off(self):
        with IsolatedServer() as srv:
            a = http_join(srv.url, "HttpStudent")
            h = {"X-Token": a["token"]}
            d = json.loads(http(srv, "/api/learn", headers=h)[1])
            self.assertTrue(d["lessons"] and d["challenges"])
            self.assertFalse(d["quizzes"])
            les = json.loads(http(srv, "/api/learn/lesson/basics")[1])            # public
            self.assertTrue(les["body"])
            self.assertEqual(les["quiz"], [])
            self.assertNotIn("answer", json.dumps(les))
            with open(learning.LESSONS_FILE, encoding="utf-8") as fh:
                ans = [q["answer"] for q in next(x for x in json.load(fh)["lessons"] if x["id"] == "basics")["quiz"]]
            r = json.loads(http(srv, "/api/learn/quiz", "POST", {"lesson": "basics", "answers": ans}, headers=h)[1])
            self.assertFalse(r["ok"])
            status, text, _ = http(srv, "/api/journal", "POST", {"ticker": "NVXA", "setup": "breakout", "stop": 1.0}, headers=h)
            self.assertTrue(json.loads(text)["ok"], text)
            j = json.loads(http(srv, "/api/journal", headers=h)[1])
            self.assertEqual(j["entries"][0]["setup"], "breakout")
            self.assertEqual(http(srv, "/api/learn")[0], 401)


@unittest.skipUnless(find_browser(), "no Edge/Chrome installed")
class LearningBrowserTests(unittest.TestCase):
    """The Learn, Journal and Calendar pages and the chart tools, in a real browser."""

    def test_the_new_pages_and_chart_tools(self):
        with IsolatedServer() as srv:
            d, errors = asyncio.run(self._pages(srv.url))
        d.verdict(self, errors)

    async def _pages(self, base):
        proc, pg, _ = await open_page(debug_port=9362)
        d = Driver(pg)
        try:
            await d.join(base, "learner")
            await d.check("a new player is pointed at the first lesson", "document.getElementById('learn-banner').innerText",
                          lambda t: "first lesson" in t, wait=8)
            await pg.goto(base + "/learn", 3)
            await d.check("the lessons are listed", "document.querySelectorAll('.lesson-item').length", lambda n: n >= 10, wait=10)
            await d.check("and the challenges", "document.querySelectorAll('.chal').length", lambda n: n >= 5)
            await d.check("with no quiz mentioned (quizzes are off)", "document.getElementById('learn-body').innerText",
                          lambda t: "quiz" not in t.lower() and "questions" not in t)
            await pg.goto(base + "/learn?l=basics", 3)
            await d.check("a lesson opens to read", "document.querySelector('.lesson-body') && document.querySelector('.lesson-body').innerText.length",
                          lambda n: bool(n) and n > 200, wait=10)
            await d.check("without a quiz", "document.querySelectorAll('.quiz-q').length + (document.getElementById('quiz-go') ? 1 : 0)", 0)
            await pg.goto(base + "/journal", 3)
            await d.check("the journal has the setups", "document.getElementById('j-setup').options.length", lambda n: n > 5, wait=10)
            await pg.js("(()=>{document.getElementById('j-ticker').value='NVXA';document.getElementById('j-setup').value='support';"
                        "document.getElementById('j-stop').value='1';document.getElementById('j-plan').value='test plan';"
                        "document.getElementById('j-save').click()})()")
            await d.check("an entry is saved and listed", "document.getElementById('j-rows').innerText",
                          lambda t: "NVXA" in t and "Bounce at support" in t, wait=10)
            await pg.goto(base + "/calendar", 3)
            await d.check("the calendar lists releases with forecasts", "document.getElementById('cal-up').innerText",
                          lambda t: "forecast" in t.lower() and "Weekly jobless claims" in t, wait=10)   # (weekly: always within the next 12 days)
            await pg.goto(base + "/stock/NVXA", 4)
            await d.check("the chart has volume bars", "document.querySelector('#chart-wrap svg') && document.querySelector('#chart-wrap svg').textContent",
                          lambda t: bool(t) and "Volume" in t, wait=15)
            await pg.js("document.querySelector('[data-ind=rsi]').click()")
            await d.check("RSI adds a panel", "document.querySelector('#chart-wrap svg').textContent", lambda t: "RSI 14" in t, wait=5)
            await pg.js("document.querySelector('[data-ind=bb]').click()")
            await d.check("a Pro indicator says it is Pro", "document.getElementById('toast').textContent", lambda t: "Pro" in t, wait=3)
            await pg.js("document.getElementById('draw-toggle').click()")
            await pg.js("(()=>{const w=document.getElementById('chart-wrap'),r=w.querySelector('svg').getBoundingClientRect();"
                        "w.dispatchEvent(new PointerEvent('pointerdown',{clientX:r.left+r.width/3,clientY:r.top+r.height*0.25,bubbles:true}))})()")
            await d.check("a level can be drawn", "document.querySelectorAll('[data-unline]').length", 1, wait=4)
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
