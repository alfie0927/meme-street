"""Learning (ROADMAP.md track L): lessons with quizzes, challenges that award MB, and the trading journal.

* **Lessons** live in `lessons.json`. A lesson's quiz is marked here: the right answers never reach the page before the
  player has answered. Passing a lesson (every answer right) for the first time is worth `lesson_reward` MB.
* **Challenges** reward the habits the lessons teach (protecting a trade with a stop, keeping a journal, reviewing
  trades), never volume or luck. Some can be won once, some once a week. Every MB from a lesson or a challenge counts
  as `challenge` MB, and at most `challenge_week_cap` of them are paid in one week (a week runs Monday to Sunday, UTC).
* **The journal** is a player's own notes on their trades: the setup, the plan (stop and target) and, afterwards, what
  they learned. An entry is linked to the player's position in that stock: when the position is closed the result is
  filled in, in MB and in R (the result divided by the risk the plan took). Everyone sees their win rate and average
  result; Pro adds the breakdown by setup and the R statistics.

Nothing here changes prices or trading: challenges only ever credit MB (counted as money put in, so they never lift a
return), and the journal is notes.
"""
import datetime
import json
import os
import uuid

LESSONS_FILE = "lessons.json"
SETUPS = {"support": "Bounce at support", "resistance": "Rejected at resistance", "breakout": "Breakout",
          "pullback": "Trend pullback", "range": "Range trade", "macro": "Macro release", "earnings": "Earnings",
          "other": "Other"}
CHALLENGES = [
    {"id": "first_lesson", "title": "First lesson", "how": "Pass the quiz of any lesson.", "period": "once", "target": 1,
     "reward": 25, "counter": "lessons"},
    {"id": "basics", "title": "The basics", "how": "Pass the quizzes of the four Start here lessons.", "period": "once",
     "target": 4, "reward": 100, "counter": "basics"},
    {"id": "graduate", "title": "Graduate", "how": "Pass every lesson's quiz.", "period": "once", "target": 0,
     "reward": 250, "counter": "lessons"},
    {"id": "first_stop", "title": "Protect a trade", "how": "Put a stop-loss (or a bracket) on an open position.",
     "period": "once", "target": 1, "reward": 25, "counter": "stops"},
    {"id": "first_journal", "title": "Dear diary", "how": "Write your first journal entry with a setup and a stop.",
     "period": "once", "target": 1, "reward": 25, "counter": "journal"},
    {"id": "week_stops", "title": "Every trade protected", "how": "Put a stop-loss on 5 positions this week.",
     "period": "week", "target": 5, "reward": 60, "counter": "stops"},
    {"id": "week_planned", "title": "Plan the trade, trade the plan",
     "how": "Close 3 positions this week that had a stop-loss while they were open, win or lose.", "period": "week",
     "target": 3, "reward": 75, "counter": "planned"},
    {"id": "week_journal", "title": "Keep a journal", "how": "Write 5 journal entries with a setup and a stop this week.",
     "period": "week", "target": 5, "reward": 50, "counter": "journal"},
    {"id": "week_review", "title": "Learn from it", "how": "Write what you learned on 3 closed journal entries this week.",
     "period": "week", "target": 3, "reward": 40, "counter": "reviews"},
]
PLAYER_FIELDS = ("lessons_passed", "chal", "journal", "stop_seen")
JOURNAL_MAX = 300


def init_player(p):
    p.lessons_passed = {}      # lesson id -> when it was passed
    p.chal = {}                # challenge id -> {"n": progress, "key": period key, "done": [period keys won]}
    p.journal = []             # journal entries, oldest first (see add_journal)
    p.stop_seen = []           # tickers whose open position has had a stop-loss (for "planned" trades)


def dump_player(p):
    return {k: getattr(p, k) for k in PLAYER_FIELDS}


def load_player(p, x):
    for k in PLAYER_FIELDS:
        if k in x:
            setattr(p, k, x[k])
    p.lessons_passed = dict(p.lessons_passed or {})
    p.chal = dict(p.chal or {})
    p.journal = list(p.journal or [])[-JOURNAL_MAX:]
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
        self.lessons = load_lessons(os.path.join(os.getcwd(), LESSONS_FILE))
        self._lesson_by_id = {x["id"]: x for x in self.lessons}

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
        for c in CHALLENGES:
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
        for c in CHALLENGES:
            st = p.chal.get(c["id"], {})
            key = week if c["period"] == "week" else "once"
            done = key in st.get("done", [])
            n = st.get("n", 0) if st.get("key") == key else 0
            if c["counter"] in ("lessons", "basics"):
                n = self._lesson_progress(p, c)
            chal.append({"id": c["id"], "title": c["title"], "how": c["how"], "period": c["period"],
                         "target": self._target(c), "n": min(n, self._target(c)), "done": done, "reward": c["reward"]})
        return {"lessons": [{"id": x["id"], "title": x["title"], "level": x.get("level", ""), "minutes": x.get("minutes", 5),
                             "summary": x.get("summary", ""), "passed": x["id"] in p.lessons_passed,
                             "questions": len(x.get("quiz", []))} for x in self.lessons],
                "challenges": chal, "week": cw, "lesson_reward": float(self.settings.get("lesson_reward", 20))}

    def lesson(self, lesson_id):
        x = self._lesson_by_id.get(lesson_id)
        if not x:
            return None
        return {"id": x["id"], "title": x["title"], "level": x.get("level", ""), "minutes": x.get("minutes", 5),
                "body": x.get("body", []), "quiz": [{"q": q["q"], "options": q["options"]} for q in x.get("quiz", [])]}

    def answer_quiz(self, p, lesson_id, answers):
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
        """A stop-loss was placed on an open position."""
        if kind != "stop_loss" or ticker in p.stop_seen:
            return
        p.stop_seen.append(ticker)
        self._bump(p, "stops")

    def _learn_after_trade(self, p, ticker):
        """Link journal entries to positions: an idea becomes an open trade when a position is opened, and an open
        entry is closed with its result when the position is closed."""
        held = p.hold.get(ticker, 0.0)
        s = self.stocks.get(ticker)
        price = s.price if s else 0.0
        if abs(held) > 1e-9:
            for e in reversed(p.journal):
                if e["ticker"] == ticker and e["status"] == "idea" and self.now - e["t"] < 2 * 1800:
                    self._open_entry(p, e, held, price)
                    break
            return
        if ticker in p.stop_seen:                       # a position that had a stop was closed: a planned trade
            p.stop_seen.remove(ticker)
            self._bump(p, "planned")
        for e in p.journal:
            if e["ticker"] == ticker and e["status"] == "open":
                result = p.realized.get(ticker, 0.0) - e.get("realized0", 0.0)
                e.update(status="closed", closed_at=self.now, exit_price=round(price, 6), result=round(result, 4))
                risk = abs(e.get("entry_price", 0) - (e.get("stop") or 0)) * e.get("shares", 0) if e.get("stop") else 0
                e["r"] = round(result / risk, 2) if risk > 1e-9 else None

    def _open_entry(self, p, e, held, price):
        e.update(status="open", side="long" if held > 0 else "short", entry_price=round(price, 6),
                 shares=abs(held), realized0=p.realized.get(e["ticker"], 0.0), opened_at=self.now)

    # ------------------------------------------------------------------ the journal
    def add_journal(self, p, ticker, setup, plan="", stop=None, target=None, note=""):
        ticker = str(ticker or "").upper()
        if ticker not in self.stocks:
            return False, "Pick a stock you can trade"
        if setup not in SETUPS:
            return False, "Pick a setup"
        plan, note = str(plan or "")[:400].strip(), str(note or "")[:400].strip()
        try:
            stop = float(stop) if stop not in (None, "") else None
            target = float(target) if target not in (None, "") else None
        except (TypeError, ValueError):
            return False, "Stop and target must be prices"
        if (stop is not None and stop <= 0) or (target is not None and target <= 0):
            return False, "Stop and target must be above 0"
        recent = [e for e in p.journal if self.now - e["t"] < 60]
        if len(recent) >= 5:
            return False, "Slow down: at most 5 entries a minute"
        e = {"id": uuid.uuid4().hex[:10], "t": self.now, "ticker": ticker, "setup": setup, "plan": plan, "note": note,
             "stop": stop, "target": target, "status": "idea", "lesson": ""}
        held = p.hold.get(ticker, 0.0)
        if abs(held) > 1e-9:
            self._open_entry(p, e, held, self.stocks[ticker].price)
        p.journal.append(e)
        del p.journal[:-JOURNAL_MAX]
        if stop is not None:
            self._bump(p, "journal")
        return True, "Saved to your journal"

    def review_journal(self, p, entry_id, lesson):
        e = next((x for x in p.journal if x["id"] == entry_id), None)
        if e is None:
            return False, "Unknown entry"
        lesson = str(lesson or "")[:400].strip()
        if len(lesson) < 10:
            return False, "Write a sentence or two about what you learned"
        first = not e.get("lesson")
        e["lesson"] = lesson
        if first and e["status"] == "closed":
            self._bump(p, "reviews")
        return True, "Saved"

    def delete_journal(self, p, entry_id):
        n = len(p.journal)
        p.journal = [x for x in p.journal if x["id"] != entry_id]
        return (True, "Deleted") if len(p.journal) < n else (False, "Unknown entry")

    def journal_view(self, p):
        closed = [e for e in p.journal if e["status"] == "closed"]
        wins = [e for e in closed if e.get("result", 0) > 0]
        out = {"entries": list(reversed(p.journal[-150:])), "setups": SETUPS, "pro": self.is_pro(p),
               "summary": {"closed": len(closed), "open": sum(1 for e in p.journal if e["status"] == "open"),
                           "ideas": sum(1 for e in p.journal if e["status"] == "idea"),
                           "win_rate": round(len(wins) / len(closed), 3) if closed else None,
                           "avg_result": round(sum(e.get("result", 0) for e in closed) / len(closed), 2) if closed else None}}
        if self.is_pro(p):
            by = {}
            for e in closed:
                b = by.setdefault(e["setup"], {"setup": e["setup"], "name": SETUPS.get(e["setup"], e["setup"]), "n": 0,
                                               "wins": 0, "total": 0.0, "rs": []})
                b["n"] += 1
                b["wins"] += e.get("result", 0) > 0
                b["total"] += e.get("result", 0)
                if e.get("r") is not None:
                    b["rs"].append(e["r"])
            rows = []
            for b in by.values():
                rs = b.pop("rs")
                b.update(win_rate=round(b["wins"] / b["n"], 3), total=round(b["total"], 2),
                         avg_r=round(sum(rs) / len(rs), 2) if rs else None, with_stop=len(rs))
                rows.append(b)
            rows.sort(key=lambda b: -b["total"])
            rs = [e["r"] for e in closed if e.get("r") is not None]
            out["pro_stats"] = {"by_setup": rows, "avg_r": round(sum(rs) / len(rs), 2) if rs else None,
                                "best_r": max(rs) if rs else None, "worst_r": min(rs) if rs else None,
                                "planned_share": round(len(rs) / len(closed), 3) if closed else None}
        return out
