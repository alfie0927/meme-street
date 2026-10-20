"""Learning (ROADMAP.md track L): lessons with quizzes, and challenges that award MB.

* **Lessons** live in `content/lessons.json`. A lesson's quiz is marked here: the right answers never reach the page
  before the player has answered. Passing a lesson (every answer right) for the first time is worth `lesson_reward` MB.
  **Quizzes are switched off for now** (`quizzes: false` in base.json): the lessons are plain reading, there is no
  quiz, no lesson reward, and the challenges that need quizzes (first lesson, the basics, graduate) are not offered.
  The questions stay in lessons.json, so `quizzes: true` brings it all back.
* **Challenges** reward the habits the lessons teach (protecting a trade with a stop, closing positions that had one),
  never volume or luck. Some can be won once, some once a week. Every MB from a lesson or a challenge counts
  as `challenge` MB, and at most `challenge_week_cap` of them are paid in one week (a week runs Monday to Sunday, UTC).

Nothing here changes prices or trading: challenges only ever credit MB (counted as money put in, so they never lift a
return). (A trading journal lived here until 2026-10-20; it was removed, and old saves' entries are dropped on load.)
"""
import datetime
import json
import os

import paths

LESSONS_FILE = os.path.join(paths.CONTENT, "lessons.json")
CHALLENGES = [
    {"id": "first_lesson", "title": "First lesson", "how": "Pass the quiz of any lesson.", "period": "once", "target": 1,
     "reward": 25, "counter": "lessons"},
    {"id": "basics", "title": "The basics", "how": "Pass the quizzes of the four Start here lessons.", "period": "once",
     "target": 4, "reward": 100, "counter": "basics"},
    {"id": "graduate", "title": "Graduate", "how": "Pass every lesson's quiz.", "period": "once", "target": 0,
     "reward": 250, "counter": "lessons"},
    {"id": "first_stop", "title": "Protect a trade", "how": "Put a stop-loss (or a bracket) on an open position.",
     "period": "once", "target": 1, "reward": 25, "counter": "stops"},
    {"id": "first_target", "title": "Set a target", "how": "Put a take-profit on an open position.",
     "period": "once", "target": 1, "reward": 25, "counter": "targets"},
    {"id": "week_stops", "title": "Every trade protected", "how": "Put a stop-loss on 5 positions this week.",
     "period": "week", "target": 5, "reward": 60, "counter": "stops"},
    {"id": "week_planned", "title": "Plan the trade, trade the plan",
     "how": "Close 3 positions this week that had a stop-loss while they were open, win or lose.", "period": "week",
     "target": 3, "reward": 75, "counter": "planned"},
    {"id": "week_targets", "title": "Every trade has a target", "how": "Put a take-profit on 5 positions this week.",
     "period": "week", "target": 5, "reward": 50, "counter": "targets"},
]
QUIZ_COUNTERS = ("lessons", "basics")      # challenges won by passing quizzes (not offered while quizzes are off)
PLAYER_FIELDS = ("lessons_passed", "chal", "stop_seen")


def init_player(p):
    p.lessons_passed = {}      # lesson id -> when it was passed
    p.chal = {}                # challenge id -> {"n": progress, "key": period key, "done": [period keys won]}
    p.stop_seen = []           # tickers whose open position has had a stop-loss (for "planned" trades)


def dump_player(p):
    return {k: getattr(p, k) for k in PLAYER_FIELDS}


def load_player(p, x):
    for k in PLAYER_FIELDS:
        if k in x:
            setattr(p, k, x[k])
    p.lessons_passed = dict(p.lessons_passed or {})
    p.chal = dict(p.chal or {})
    p.stop_seen = list(p.stop_seen or [])


def load_lessons(path=LESSONS_FILE):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("lessons", [])
    except (OSError, ValueError):
        return []


class LearningMixin:
    """Mixed into the Engine. Uses `self.now`, `self.settings`, `self.credit`, `self._notify`, `self.stocks`, `self.is_pro`."""

    def _init_learning(self):
        self.lessons = load_lessons(LESSONS_FILE)
        self._lesson_by_id = {x["id"]: x for x in self.lessons}

    def quizzes_on(self):
        return bool(self.settings.get("quizzes", False))

    def _challenges(self):
        """The challenges on offer: without quizzes, the ones that are won by passing them are left out."""
        return CHALLENGES if self.quizzes_on() else [c for c in CHALLENGES if c["counter"] not in QUIZ_COUNTERS]

    # ------------------------------------------------------------------ periods and rewards
    def _week_key(self, t=None):
        y, w, _ = datetime.datetime.fromtimestamp(self.now if t is None else t, datetime.timezone.utc).isocalendar()
        return f"{y}-W{w:02d}"

    def challenge_week_status(self, p):
        cap = float(self.settings.get("challenge_week_cap", 500))
        got = float((p.challenge_mb or {}).get(self._week_key(), 0.0))
        return {"cap": cap, "earned": round(got, 2), "left": round(max(0.0, cap - got), 2), "week": self._week_key()}

    def _reward(self, p, amount, why):
        """Pay a challenge or lesson reward, within the weekly cap. Returns what was paid."""
        blocked = self.reward_block(p)
        if blocked:
            self._notify(p, f"{why}: done, but no MB: {blocked}.")
            return 0.0
        week = self._week_key()
        cap = float(self.settings.get("challenge_week_cap", 500))
        got = float(p.challenge_mb.get(week, 0.0))
        pay = max(0.0, min(float(amount), cap - got))
        if pay <= 0:
            self._notify(p, f"{why}: you have earned this week's maximum of {cap:,.0f} MB from challenges, so this one is for the glory.")
            return 0.0
        p.challenge_mb[week] = got + pay
        for k in [k for k in p.challenge_mb if k < self._week_key(self.now - 60 * 86400)]:
            del p.challenge_mb[k]                       # keep two months
        self.credit(p, pay, source="challenge")
        self._notify(p, f"{why}: +{pay:,.0f} MB")
        return pay

    def _bump(self, p, counter, by=1):
        """Count progress on every challenge that uses this counter, and pay the ones that are now complete."""
        week = self._week_key()
        for c in self._challenges():
            if c["counter"] != counter and not (counter == "lessons" and c["counter"] == "basics"):
                continue
            st = p.chal.setdefault(c["id"], {"n": 0, "key": None, "done": []})
            key = week if c["period"] == "week" else "once"
            if st["key"] != key:
                st["key"], st["n"] = key, 0
            if key in st["done"]:
                continue
            if c["counter"] in ("lessons", "basics"):
                st["n"] = self._lesson_progress(p, c)
            else:
                st["n"] += by
            if st["n"] >= self._target(c):
                st["done"] = (st["done"] + [key])[-12:]
                self._reward(p, c["reward"], f"Challenge complete: {c['title']}")

    def _target(self, c):
        return c["target"] or len(self.lessons)

    def _lesson_progress(self, p, c):
        if c["counter"] == "basics":
            return sum(1 for x in self.lessons if x.get("level") == "Start here" and x["id"] in p.lessons_passed)
        return sum(1 for x in self.lessons if x["id"] in p.lessons_passed)

    # ------------------------------------------------------------------ lessons
    def lessons_view(self, p):
        cw = self.challenge_week_status(p)
        week = self._week_key()
        chal = []
        for c in self._challenges():
            st = p.chal.get(c["id"], {})
            key = week if c["period"] == "week" else "once"
            done = key in st.get("done", [])
            n = st.get("n", 0) if st.get("key") == key else 0
            if c["counter"] in ("lessons", "basics"):
                n = self._lesson_progress(p, c)
            chal.append({"id": c["id"], "title": c["title"], "how": c["how"], "period": c["period"],
                         "target": self._target(c), "n": min(n, self._target(c)), "done": done, "reward": c["reward"]})
        quiz = self.quizzes_on()
        return {"lessons": [{"id": x["id"], "title": x["title"], "level": x.get("level", ""), "minutes": x.get("minutes", 5),
                             "summary": x.get("summary", ""), "passed": quiz and x["id"] in p.lessons_passed,
                             "questions": len(x.get("quiz", [])) if quiz else 0} for x in self.lessons],
                "challenges": chal, "week": cw, "quizzes": quiz,
                "lesson_reward": float(self.settings.get("lesson_reward", 20)) if quiz else 0.0}

    def lesson(self, lesson_id):
        x = self._lesson_by_id.get(lesson_id)
        if not x:
            return None
        quiz = x.get("quiz", []) if self.quizzes_on() else []
        return {"id": x["id"], "title": x["title"], "level": x.get("level", ""), "minutes": x.get("minutes", 5),
                "body": x.get("body", []), "quiz": [{"q": q["q"], "options": q["options"]} for q in quiz]}

    def answer_quiz(self, p, lesson_id, answers):
        if not self.quizzes_on():
            return {"ok": False, "error": "Quizzes are switched off for now"}
        x = self._lesson_by_id.get(lesson_id)
        if not x:
            return {"ok": False, "error": "Unknown lesson"}
        quiz = x.get("quiz", [])
        if not isinstance(answers, list) or len(answers) != len(quiz):
            return {"ok": False, "error": "Answer every question"}
        marks = []
        for q, a in zip(quiz, answers):
            right = isinstance(a, int) and not isinstance(a, bool) and a == q["answer"]
            marks.append({"right": right, "answer": q["answer"], "why": q.get("why", "")})
        passed = all(m["right"] for m in marks)
        first = passed and lesson_id not in p.lessons_passed
        paid = 0.0
        if first:
            p.lessons_passed[lesson_id] = self.now
            paid = self._reward(p, float(self.settings.get("lesson_reward", 20)), f"Lesson passed: {x['title']}")
            self._bump(p, "lessons", 0)
        return {"ok": True, "passed": passed, "first": first, "paid": paid, "marks": marks,
                "score": sum(m["right"] for m in marks), "of": len(quiz)}

    # ------------------------------------------------------------------ hooks from trading
    def _learn_order(self, p, ticker, kind):
        """A stop-loss or a take-profit was placed on an open position."""
        if kind == "take_profit":
            self._bump(p, "targets")
            self._ladder_count(p, "targets")
        if kind != "stop_loss" or ticker in p.stop_seen:
            return
        p.stop_seen.append(ticker)
        self._bump(p, "stops")
        self._ladder_count(p, "stops")

    def _learn_after_trade(self, p, ticker):
        """A position that had a stop-loss was closed: a planned trade, win or lose."""
        if abs(p.hold.get(ticker, 0.0)) > 1e-9 or ticker not in p.stop_seen:
            return
        p.stop_seen.remove(ticker)
        self._bump(p, "planned")
        self._ladder_count(p, "planned")
