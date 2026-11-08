"""Learning (ROADMAP.md tracks TA-C and L): the Learn page's curriculum and its chart tests, and the challenges
(switched off).

* **The curriculum** lives in `content/learn-*.md`, one file per track, read in file-name order (`parse_learn` below
  has the format). Since 2026-11-07 (ROADMAP LP1-LP4) the course is a **path**: every lesson ends with **exercises**
  (questions `Q:`, chart tests `[test]` and tasks `[task]` checked on the live market), a lesson is **passed** when every
  exercise has been done (`passed`; a question counts once it is answered, right or wrong, and the answer is explained),
  exercises and passes earn **XP** (`xp`, by day in `xp_days` for the daily goal and the learning streak), and the Learn
  page points at the next lesson. A lesson a player opens still counts as read (`lessons_passed`). **Nothing on the
  Learn page pays MB** (since 2026-10-23). Visitors can read, answer and test too; only a player's progress is kept.
* **Chart tests** (`drills.py`): a real chart from the game's own history, stopped at a moment worth asking about
  (a level test, a breakout, a pattern...), and then the candles that came next. The right answer is kept here until
  the player answers (`_drill_q`, in memory only: a restart forgets a test still open), and a player's score per kind
  is kept (`drills`).
* **Challenges** reward the habits the lessons teach (protecting a trade with a stop, closing positions that had one),
  never volume or luck. They are switched off (the `challenges` setting); when on, every MB they pay counts as
  `challenge` MB, at most `challenge_week_cap` in a week (Monday to Sunday, UTC).

Nothing here changes prices or trading. (A trading journal lived here until 2026-10-20; it was removed, and old saves'
entries are dropped on load. The lesson rewards and the challenges for passing lessons went on 2026-10-27.)
"""
import collections
import datetime
import glob
import math
import os
import random
import re
import secrets

import drills
import paths

LEARN_FILES = os.path.join(paths.CONTENT, "learn-*.md")
CHALLENGES = [          # this week's habits (LP11, 2026-11-07): the old challenges, paid in XP, always on
    {"id": "week_stops", "title": "Every trade protected", "how": "Put a stop-loss on 5 positions this week.",
     "period": "week", "target": 5, "reward": 30, "counter": "stops"},
    {"id": "week_planned", "title": "Plan the trade, trade the plan",
     "how": "Close 3 positions this week that had a stop-loss while they were open, win or lose.", "period": "week",
     "target": 3, "reward": 30, "counter": "planned"},
    {"id": "week_targets", "title": "Every trade has a target", "how": "Put a take-profit on 5 positions this week.",
     "period": "week", "target": 5, "reward": 30, "counter": "targets"},
    {"id": "week_sized", "title": "Sized by the stop", "how": "Place 3 stops this week that risk under 2% of your account.",
     "period": "week", "target": 3, "reward": 30, "counter": "sized"},
]
PLAYER_FIELDS = ("lessons_passed", "chal", "stop_seen", "drills", "passed", "ex", "xp", "xp_days", "goal", "tasks", "placed", "attempts", "xp_weeks", "stop_px", "r_log")
COIN_KINDS = {"next"}        # chart tests built to score 50%: never a weak spot (LP9)
LEVELS = [(0, "Trainee"), (200, "Apprentice"), (600, "Trader"), (1500, "Analyst"), (3000, "Strategist"), (6000, "Master")]   # XP levels (LP14)
GOALS = (20, 50, 100)        # the daily XP goals a player can pick
CALC_KINDS = ("sizing", "r", "drawdown", "expectancy")   # generated number questions (LP15), fresh numbers each day


def level_of(xp):
    """The level an XP total has reached: its name, its floor and the next floor (None at the top)."""
    k = max(i for i, (floor, _) in enumerate(LEVELS) if xp >= floor)
    return {"name": LEVELS[k][1], "floor": LEVELS[k][0], "next": LEVELS[k + 1][0] if k + 1 < len(LEVELS) else None, "n": k + 1}
ATTEMPTS_MAX, WEAK_MIN, WEAK_BELOW, XP_REVIEW, LEAGUE = 300, 3, 0.7, 5, 20   # the review (LP5) and the weekly league (LP7)
PLACEMENT_UNITS = 12         # the placement test asks one question from each of this many units after Start here (LP6)
TASK_KINDS = {"trade": "Make a trade", "stop": "Put a stop-loss on a position", "target": "Put a take-profit on a position",
              "bracket": "Place a bracket", "planned": "Close a position that had a stop", "short": "Open a short",
              "limit": "Place a limit order", "trail": "Place a trailing stop", "option": "Buy an option",
              "note": "Write a note on a trade", "short_stop": "Put a stop-loss above a short"}
XP_RIGHT, XP_WRONG, XP_PASS, XP_TASK, GOAL = 10, 2, 20, 30, 50       # XP per exercise right or wrong, per lesson passed, per task; the daily goal (50: one lesson, not two answers)
TEST_TIMEFRAMES = {"1m": "1-minute", "5m": "5-minute", "15m": "15-minute", "1h": "1-hour"}
TEST_PENDING = 3000          # chart tests waiting for an answer, at most (the oldest go first)
TEST_KEEP = 3 * 3600         # and for at most this long
EXAMPLE_KEEP = 900           # a lesson's example chart is found again after this long


def init_player(p):
    p.lessons_passed = {}      # lesson id -> when it was first read
    p.chal = {}                # challenge id -> {"n": progress, "key": period key, "done": [period keys won]}
    p.stop_seen = []           # tickers whose open position has had a stop-loss (for "planned" trades)
    p.drills = {}              # chart test kind -> [right, answered]
    p.passed = {}              # lesson id -> when every exercise of it was done (LP1)
    p.ex = {}                  # lesson id -> [exercise indexes done] (questions and chart tests; tasks are in `tasks`)
    p.xp = 0                   # experience points, all time (LP3)
    p.xp_days = {}             # UTC day number (str) -> XP earned that day (the daily goal and the learning streak)
    p.goal = GOAL              # the daily XP goal
    p.tasks = []               # task kinds done on the live market (LP4)
    p.placed = None            # the placement test's result: the id of the unit the path starts at (LP6); None until taken
    p.attempts = []            # [day, skill, right] per exercise answered: a unit id or a chart-test kind (LP5, the newest 300)
    p.xp_weeks = {}            # ISO week -> XP earned that week (LP7, the weekly league; 8 weeks kept)
    p.stop_px = {}             # ticker -> {stop, entry, sh, risk} from the first stop on an open position: R at the close (LP9)
    p.r_log = []               # R multiples of closed positions that had a stop (the newest 100)


def dump_player(p):
    return {k: getattr(p, k) for k in PLAYER_FIELDS}


def load_player(p, x):
    for k in PLAYER_FIELDS:
        if k in x:
            setattr(p, k, x[k])
    p.lessons_passed = dict(p.lessons_passed or {})
    p.chal = dict(p.chal or {})
    p.stop_seen = list(p.stop_seen or [])
    p.drills = {k: list(v) for k, v in (getattr(p, "drills", None) or {}).items()}
    p.passed = {str(k): float(v) for k, v in dict(getattr(p, "passed", None) or {}).items()}
    p.ex = {str(k): sorted({int(i) for i in v}) for k, v in dict(getattr(p, "ex", None) or {}).items()}
    p.xp = int(getattr(p, "xp", 0) or 0)
    p.xp_days = {str(k): int(v) for k, v in dict(getattr(p, "xp_days", None) or {}).items()}
    p.goal = int(getattr(p, "goal", GOAL) or GOAL)
    p.tasks = [t for t in list(getattr(p, "tasks", None) or []) if t in TASK_KINDS]
    p.placed = str(p.placed) if getattr(p, "placed", None) else None
    p.attempts = [[int(a[0]), str(a[1]), bool(a[2])] + ([str(a[3])] if len(a) > 3 and a[3] else []) for a in list(getattr(p, "attempts", None) or []) if len(a) in (3, 4)][-ATTEMPTS_MAX:]
    p.stop_px = {str(k): v for k, v in dict(getattr(p, "stop_px", None) or {}).items() if isinstance(v, dict)}
    p.r_log = [float(r) for r in list(getattr(p, "r_log", None) or [])][-100:]
    p.xp_weeks = {str(k): int(v) for k, v in dict(getattr(p, "xp_weeks", None) or {}).items()}


BOXES = {"TIP": "tip", "HERE": "here", "WARN": "warn"}


def parse_learn(text, tracks=None, lessons=None):
    """A track file of the curriculum. Line by line:

        # Track title {id}                 a track; the lines up to its first lesson are its blurb
        ## Lesson title {id} [6]           a lesson (and how many minutes it takes to read)
        SUMMARY: one line                  what the lesson covers (on the track list)
        ### Heading                        a heading in the lesson
        plain lines                        a paragraph (a blank line ends it); **bold** and [text](/path) are allowed
        - item                             a bulleted list
        TIP: / HERE: / WARN: text          a tip, how Meme Street does it, a warning
        | cell | cell |                    a table row (the first row is the header)
        [chart kind] / [test kind]         a real game chart with its answer / a chart test (drills.KINDS; a test
                                           can also be "any")
        [try /path] text                   a practice box with a link
        [task kind] text                   a task checked on the live market (TASK_KINDS), an exercise
        [mine]                             the player's own trading numbers, with the lesson's slant (LP10)
        Q: question / + right / - wrong    a question with one right answer and some wrong ones, an exercise,
        WHY: text                          closed by the explanation (shown after answering)
        Q: question / = 400 ±2%            a question answered with a number (the tolerance absolute or in %)
        [calc sizing|r|drawdown|expectancy] a generated number question with fresh numbers each day, an exercise
        [test kind opt]                    a chart test narrowed to the lesson ("level support", "pattern flag")
    Raises ValueError on anything it does not understand, with the line number."""
    tracks, lessons = ([] if tracks is None else tracks), ([] if lessons is None else lessons)
    track = lesson = None
    para = []
    q = [None]                       # the question being read: {"q", "options", "answer", "why"} until its WHY line

    def flush():
        if para:
            lesson["body"].append({"p": " ".join(para)})
            para.clear()

    def close_q(n):
        if q[0] is not None:
            raise ValueError(f"line {n}: a question needs a WHY: line after its answers")

    def head(rest, n):
        m = re.fullmatch(r"(.+?)\s*\{([a-z0-9-]+)\}\s*(?:\[(\d+)\])?", rest)
        if not m:
            raise ValueError(f"line {n}: want 'Title {{id}}', got {rest!r}")
        return m.group(1), m.group(2), int(m.group(3) or 5)

    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("# "):
            title, tid, _ = head(line[2:], n)
            track, lesson = {"id": tid, "title": title, "blurb": ""}, None
            tracks.append(track)
            continue
        if track is None:
            if line:
                raise ValueError(f"line {n}: text before the first track")
            continue
        if line.startswith("## "):
            if lesson:
                flush()
            title, lid, minutes = head(line[3:], n)
            lesson = {"id": lid, "track": track["id"], "title": title, "minutes": minutes, "summary": "", "body": []}
            lessons.append(lesson)
            continue
        if lesson is None:
            track["blurb"] = (track["blurb"] + " " + line).strip()
            continue
        body = lesson["body"]
        if q[0] is not None:                                     # inside a question: its answers, then WHY
            if line.startswith("+ ") or line.startswith("- "):
                if line.startswith("+ "):
                    if q[0]["answer"] is not None:
                        raise ValueError(f"line {n}: a question has two right answers")
                    q[0]["answer"] = len(q[0]["options"])
                q[0]["options"].append(line[2:])
            elif line.startswith("= "):
                m = re.fullmatch(r"= (-?[\d.]+)(?: ±(-?[\d.]+)(%?))?", line)
                if not m or q[0]["options"]:
                    raise ValueError(f"line {n}: want '= number ±tolerance' (and no + or - answers with it)")
                v = float(m.group(1))
                tol = float(m.group(2) or 0)
                q[0]["num"], q[0]["tol"] = v, (abs(v) * tol / 100 if m.group(3) else tol)
            elif line.startswith("WHY: "):
                if "num" not in q[0] and (q[0]["answer"] is None or len(q[0]["options"]) < 2):
                    raise ValueError(f"line {n}: a question needs a + answer and at least one - answer, or a = number")
                q[0]["why"] = line[5:]
                if "num" in q[0]:
                    body.append({"q": q[0]["q"], "num": q[0]["num"], "tol": q[0]["tol"], "why": q[0]["why"]})
                else:
                    body.append({"q": q[0]["q"], "options": q[0]["options"], "answer": q[0]["answer"], "why": q[0]["why"]})
                q[0] = None
            else:
                raise ValueError(f"line {n}: inside a question only + answers, - answers and WHY: may follow")
        elif line.startswith("Q: "):
            flush()
            q[0] = {"q": line[3:], "options": [], "answer": None, "why": ""}
        elif not line:
            flush()
        elif line.startswith("SUMMARY: "):
            lesson["summary"] = line[9:]
        elif line.startswith("### "):
            flush()
            body.append({"h": line[4:]})
        elif line.startswith("- "):
            flush()
            if body and "list" in body[-1]:
                body[-1]["list"].append(line[2:])
            else:
                body.append({"list": [line[2:]]})
        elif line.split(":")[0] in BOXES and ": " in line:
            flush()
            k, _, txt = line.partition(": ")
            body.append({BOXES[k]: txt})
        elif line.startswith("|"):
            flush()
            cells = [c.strip() for c in line.strip("|").split("|")]
            if body and "table" in body[-1]:
                body[-1]["table"].append(cells)
            else:
                body.append({"table": [cells]})
        elif re.fullmatch(r"\[(chart|test) [a-z]+(?: [a-z_]+)?\]", line):
            flush()
            parts = line[1:-1].split()
            k, kind, opt = parts[0], parts[1], (parts[2] if len(parts) > 2 else None)
            if kind not in drills.KINDS and not (k == "test" and kind == "any"):
                raise ValueError(f"line {n}: no chart test called {kind!r}")
            if opt and kind not in ("level", "pattern", "candle"):
                raise ValueError(f"line {n}: only level, pattern and candle tests take an option")
            body.append({k: kind, **({"opt": opt} if opt else {})})
        elif line.startswith("[calc "):
            flush()
            m = re.fullmatch(r"\[calc ([a-z]+)\]", line)
            if not m or m.group(1) not in CALC_KINDS:
                raise ValueError(f"line {n}: want '[calc kind]' with a kind in {list(CALC_KINDS)}")
            body.append({"calc": m.group(1)})
        elif line.startswith("[try "):
            flush()
            m = re.fullmatch(r"\[try (/\S*)\]\s*(.+)", line)
            if not m:
                raise ValueError(f"line {n}: want '[try /path] text'")
            body.append({"try": m.group(2), "href": m.group(1)})
        elif line == "[mine]":                                   # the player's own trading, in the lesson (LP10)
            flush()
            body.append({"mine": True})
        elif line.startswith("[task "):
            flush()
            m = re.fullmatch(r"\[task ([a-z_]+)\]\s*(.+)", line)
            if not m or m.group(1) not in TASK_KINDS:
                raise ValueError(f"line {n}: want '[task kind] text' with a kind in {sorted(TASK_KINDS)}")
            body.append({"task": m.group(1), "text": m.group(2)})
        else:
            para.append(line)
    close_q(len(text.splitlines()))
    if lesson:
        flush()
    return tracks, lessons


EXERCISE_KINDS = ("q", "test", "task", "calc")


def exercises(lesson):
    """The exercises of a lesson, in order: (index into its body, kind)."""
    return [(k, next(x for x in EXERCISE_KINDS if x in b)) for k, b in enumerate(lesson["body"]) if any(x in b for x in EXERCISE_KINDS)]


def load_content(pattern=LEARN_FILES):
    """The tracks and the lessons, in order, from every track file."""
    tracks, lessons = [], []
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8") as fh:
            try:
                parse_learn(fh.read(), tracks, lessons)
            except ValueError as e:
                raise ValueError(f"{os.path.basename(path)}: {e}") from None
    ids = [x["id"] for x in lessons] + [t["id"] for t in tracks]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"the same id twice: {sorted(dup)}")
    return tracks, lessons


class LearningMixin:
    """Mixed into the Engine. Uses `self.now`, `self.settings`, `self.credit`, `self._notify`, `self.stocks`, `self.is_pro`."""

    def _init_learning(self):
        self.tracks, self.lessons = load_content()
        self._lesson_by_id = {x["id"]: x for x in self.lessons}
        self.path_lessons = [x for x in self.lessons if exercises(x)]      # a lesson with nothing to do (the glossary) is a reference, not a step
        self._drill_q = collections.OrderedDict()       # test id -> (kind, answer, the reveal, when asked)
        self._drill_ex = {}                              # kind -> (when found, a lesson's example chart)

    def _challenges(self):
        """This week's habits: always on since 2026-11-07 (they pay XP, never MB; the `challenges` setting is ignored)."""
        return CHALLENGES

    # ------------------------------------------------------------------ periods and rewards
    def _week_key(self, t=None):
        y, w, _ = datetime.datetime.fromtimestamp(self.now if t is None else t, datetime.timezone.utc).isocalendar()
        return f"{y}-W{w:02d}"

    def challenge_week_status(self, p):
        cap = float(self.settings.get("challenge_week_cap", 500))
        got = float((p.challenge_mb or {}).get(self._week_key(), 0.0))
        return {"cap": cap, "earned": round(got, 2), "left": round(max(0.0, cap - got), 2), "week": self._week_key()}

    def _reward(self, p, amount, why):
        """A habit completed: XP (LP11; it paid MB until 2026-11-07)."""
        self._xp(p, int(amount))
        self._notify(p, f"{why} (+{int(amount)} XP)")
        return amount

    def _bump(self, p, counter, by=1):
        """Count progress on every challenge that uses this counter, and pay the ones that are now complete."""
        week = self._week_key()
        for c in self._challenges():
            if c["counter"] != counter:
                continue
            st = p.chal.setdefault(c["id"], {"n": 0, "key": None, "done": []})
            key = week if c["period"] == "week" else "once"
            if st["key"] != key:
                st["key"], st["n"] = key, 0
            if key in st["done"]:
                continue
            st["n"] += by
            if st["n"] >= c["target"]:
                st["done"] = (st["done"] + [key])[-12:]
                self._reward(p, c["reward"], f"Habit done: {c['title']}")

    # ------------------------------------------------------------------ the path: XP, passes, tasks (LP1-LP4)
    def _learn_day(self):
        return str(int(self.now // 86400))

    def _xp(self, p, n):
        """Earn XP, today (the daily goal and the learning streak count by UTC day; 60 days are kept)."""
        if p is None or n <= 0:
            return 0
        day = self._learn_day()
        before, today_before = p.xp, p.xp_days.get(day, 0)
        p.xp += n
        p.xp_days[day] = today_before + n
        for k in [k for k in p.xp_days if int(k) < int(day) - 60]:
            del p.xp_days[k]
        if today_before == 0:                                        # the first XP of the day: the streak (LP14b)
            streak = self.learn_streak(p)
            if streak >= 2:
                self._notify(p, f"Learning streak: {streak} days in a row")
        if today_before < p.goal <= today_before + n:
            self._notify(p, f"Daily goal reached: {p.goal} XP today")
        if level_of(before)["n"] < level_of(p.xp)["n"]:
            self._notify(p, f"Level up: you are now {level_of(p.xp)['name']} ({p.xp:,} XP)")
        week = self._week_key()
        p.xp_weeks[week] = p.xp_weeks.get(week, 0) + n
        for k in sorted(p.xp_weeks)[:-8]:
            del p.xp_weeks[k]
        return n

    def _attempt(self, p, skill, right, key=None):
        """Remember an exercise answer by skill (a unit id for a question, a chart-test kind for a test): the review
        (LP5) reads them. `key` names the question, so a review pays for it once a day."""
        if p is not None:
            p.attempts.append([int(self._learn_day()), skill, bool(right)] + ([key] if key else []))
            del p.attempts[:-ATTEMPTS_MAX]

    def _paid_today(self, p, key):
        day = int(self._learn_day())
        return any(a[0] == day and len(a) > 3 and a[3] == key for a in p.attempts)

    @staticmethod
    def _perm(p, lesson_id, i, n):
        """The order a question's options are shown in: shuffled, the same for one player (or all visitors) every time,
        so the right answer's slot gives nothing away (LP9). `shown[j] = options[perm[j]]`."""
        rng = random.Random(f"{p.token if p is not None else 'visitor'}:{lesson_id}:{i}")
        perm = list(range(n))
        rng.shuffle(perm)
        return perm

    def weak_skills(self, p):
        """The skills a player misses most: over the newest attempts, those answered at least WEAK_MIN times and right
        less than WEAK_BELOW of the time, the three lowest first."""
        by = {}
        for a in p.attempts[-200:]:
            skill, right = a[1], a[2]
            if skill in COIN_KINDS:
                continue
            st = by.setdefault(skill, [0, 0])
            st[0] += int(right)
            st[1] += 1
        names = {t["id"]: t["title"] for t in self.tracks}
        names.update(drills.TITLES)
        out = [{"skill": k, "name": names.get(k, k), "right": r, "n": n, "acc": round(r / n, 2)}
               for k, (r, n) in by.items() if n >= WEAK_MIN and r / n < WEAK_BELOW]
        return sorted(out, key=lambda w: (w["acc"], -w["n"]))[:3]

    def review_new(self, p):
        """A review session for the weak skills (LP5): up to three questions from each weak unit, and a chart test of
        each weak kind (the page fetches it). Answers go through learn_answer / drill_answer with `review` set, which
        records the attempt and pays a little XP but never passes a lesson."""
        if p is None:
            return {"error": "Sign in to review: the review is built from your own answers"}
        weak = self.weak_skills(p)
        if not weak:
            return {"error": "Nothing to review yet: answer more exercises first", "weak": []}
        rng = random.Random(secrets.randbits(64))
        items = []
        for w in weak:
            if w["skill"] in drills.KINDS:
                items.append({"test": w["skill"], "name": w["name"]})
                continue
            qs = [(x["id"], k) for x in self.lessons if x["track"] == w["skill"] and x["id"] in p.lessons_passed
                  for k, kind in exercises(x) if kind == "q" and "options" in x["body"][k]]                  # (only lessons the player has opened)
            for lid, k in rng.sample(qs, min(3, len(qs))):
                b = self._lesson_by_id[lid]["body"][k]
                perm = self._perm(p, lid, k, len(b["options"]))
                items.append({"lesson": lid, "i": k, "q": b["q"], "options": [b["options"][j] for j in perm], "name": w["name"]})
        if not items:
            return {"error": "Nothing to review yet: open the lessons of your weak units first", "weak": weak}
        return {"items": items, "weak": weak, "xp_review": XP_REVIEW}

    def league(self, p=None):
        """This week's learners (LP7): the LEAGUE players with the most XP this ISO week, and the viewer's own rank.
        No MB: XP is the only prize."""
        week = self._week_key()
        rows = sorted(((q.xp_weeks.get(week, 0), q.name, q.token) for q in self.players.values() if q.xp_weeks.get(week, 0) > 0),
                      key=lambda r: (-r[0], r[1]))
        mine = next((k + 1 for k, r in enumerate(rows) if p is not None and r[2] == p.token), None)
        return {"week": week, "rows": [{"name": n, "xp": x} for x, n, _ in rows[:LEAGUE]], "rank": mine,
                "xp": p.xp_weeks.get(week, 0) if p is not None else 0, "learners": len(rows)}

    def learn_streak(self, p):
        """Days in a row with XP, counting back from today (or from yesterday while today has none yet)."""
        day = int(self._learn_day())
        if not p.xp_days.get(str(day)):
            day -= 1
        n = 0
        while p.xp_days.get(str(day)):
            n, day = n + 1, day - 1
        return n

    def _ex_done(self, p, lesson):
        """Which exercises of a lesson `p` has done: questions and tests answered, tasks done anywhere."""
        done = set(p.ex.get(lesson["id"], ()))
        for k, kind in exercises(lesson):
            if kind == "task" and lesson["body"][k]["task"] in p.tasks:
                done.add(k)
        return done

    def _pass_check(self, p, lesson):
        """A lesson is passed when every exercise is done. Returns the XP just earned for passing (0 if not now)."""
        ex = exercises(lesson)
        if lesson["id"] in p.passed or not ex or len(self._ex_done(p, lesson)) < len(ex):
            return 0
        p.passed[lesson["id"]] = self.now
        self._xp(p, XP_PASS)
        self._notify(p, f"Lesson passed: {lesson['title']} (+{XP_PASS} XP)")
        unit = [x for x in self.path_lessons if x["track"] == lesson["track"]]
        if all(x["id"] in p.passed for x in unit):                  # the unit is finished (LP14c)
            title = next((t["title"] for t in self.tracks if t["id"] == lesson["track"]), lesson["track"])
            self._notify(p, f"Unit finished: {title}")
        return XP_PASS

    def set_goal(self, p, goal):
        """Pick the daily XP goal (LP14b)."""
        try:
            goal = int(goal)
        except (TypeError, ValueError):
            return False, "Pick a goal"
        if goal not in GOALS:
            return False, f"The goal is one of {', '.join(str(g) for g in GOALS)} XP a day"
        p.goal = goal
        return True, f"Your daily goal is {goal} XP"

    def _learn_task(self, p, kind):
        """A task was done on the live market (the hooks below): the first time earns XP and may pass lessons."""
        if p is None or kind not in TASK_KINDS or kind in p.tasks:
            return
        p.tasks.append(kind)
        self._xp(p, XP_TASK)
        self._notify(p, f"Done on the market: {TASK_KINDS[kind].lower()} (+{XP_TASK} XP)")
        for x in self.lessons:
            if any(b.get("task") == kind for b in x["body"]):
                self._pass_check(p, x)

    def _calc(self, p, lesson_id, i, kind):
        """A generated number question (LP15): fresh numbers for each player and day, the same between the view and the
        answer (seeded), graded within a tolerance."""
        rng = random.Random(f"{p.token if p is not None else 'visitor'}:{lesson_id}:{i}:{self._learn_day()}")
        if kind == "sizing":
            acct, risk, dist = rng.choice((1000, 2000, 5000, 10000)), rng.choice((0.5, 1, 2)), rng.choice((2, 4, 5, 8, 10))
            ans = acct * risk / dist
            return {"q": f"Your account is {acct:,} MB and you risk {risk:g}% a trade. The stop is {dist}% below your entry. How many MB can the position be?",
                    "num": ans, "tol": ans * 0.02, "unit": "MB",
                    "why": f"{risk:g}% of {acct:,} MB is {acct * risk / 100:g} MB of risk; {acct * risk / 100:g} ÷ {dist}% = {ans:,.0f} MB."}
        if kind == "r":
            risk, mult = rng.choice((10, 15, 20, 25, 40)), rng.choice((0.5, 1.5, 2, 3, -1, -0.5))
            made = risk * mult
            return {"q": f"You risked {risk} MB on a trade and it closed at {made:+g} MB. What is the result in R?",
                    "num": mult, "tol": 0.05, "unit": "R", "why": f"{made:+g} ÷ {risk} = {mult:+g}R: the result measured in units of the risk taken."}
        if kind == "drawdown":
            fall = rng.choice((10, 20, 25, 33, 50))
            ans = (1 / (1 - fall / 100) - 1) * 100
            return {"q": f"An account falls {fall}% from its peak. What gain, in %, gets it back to the peak?", "num": ans, "tol": ans * 0.03, "unit": "%",
                    "why": f"After a {fall}% fall, {100 - fall}% is left; it must grow by 100 ÷ {100 - fall} − 1 = {ans:.0f}%."}
        win, avg = rng.choice((30, 40, 50, 60)), rng.choice((1.5, 2, 3))
        ans = win / 100 * avg - (1 - win / 100)
        return {"q": f"A strategy wins {win}% of the time at +{avg:g}R and loses the rest at −1R. What is its expectancy, in R per trade?",
                "num": ans, "tol": 0.05, "unit": "R", "why": f"{win / 100:g} × {avg:g} − {1 - win / 100:g} × 1 = {ans:+.2f}R per trade, before costs."}

    def learn_answer(self, p, lesson_id, i, choice, review=False):
        """Answer question `i` (an index into the lesson's body) of a lesson: right or wrong, the right answer and why.
        A player's first answer to a question is kept and earns XP; a visitor's is marked and forgotten. In a review
        (LP5) the answer is remembered as an attempt and a right one pays XP_REVIEW, but nothing passes."""
        x = self._lesson_by_id.get(lesson_id)
        b = x["body"][i] if x and isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(x["body"]) else None
        if not b or not ("q" in b or "calc" in b):
            return {"error": "No such question"}
        if "calc" in b or "num" in b:                                       # a number answer (LP15)
            spec = self._calc(p, lesson_id, i, b["calc"]) if "calc" in b else b
            try:
                val = float(choice)
            except (TypeError, ValueError):
                val = None
            right = val is not None and math.isfinite(val) and abs(val - spec["num"]) <= spec["tol"] + 1e-9
            out = {"right": right, "answer": round(spec["num"], 4), "why": spec["why"]}
        else:
            perm = self._perm(p, lesson_id, i, len(b["options"]))
            picked = perm[choice] if isinstance(choice, int) and not isinstance(choice, bool) and 0 <= choice < len(perm) else None
            right = picked == b["answer"]
            out = {"right": right, "answer": perm.index(b["answer"]), "why": b["why"]}      # (the answer as a shown slot)
        key = f"{lesson_id}:{i}"
        paid = p is not None and review and self._paid_today(p, key)
        self._attempt(p, x["track"], right, key)
        if p is not None and review:
            out["xp"] = self._xp(p, XP_REVIEW) if right and not paid else 0
            out["weak"] = self.weak_skills(p)
            return out
        if p is not None:
            done = p.ex.setdefault(lesson_id, [])
            if i not in done:
                done.append(i)
                out["xp"] = self._xp(p, XP_RIGHT if right else XP_WRONG) + self._pass_check(p, x)
            out.update(self._lesson_progress(p, x))
        return out

    def _lesson_progress(self, p, x):
        ex = exercises(x)
        return {"done": sorted(self._ex_done(p, x)), "total": len(ex), "passed": x["id"] in p.passed,
                "xp_total": p.xp, "today": p.xp_days.get(self._learn_day(), 0), "goal": p.goal,
                "answers": {str(k): ({"answer": round(x["body"][k]["num"], 4), "why": x["body"][k]["why"]} if "num" in x["body"][k]
                                     else {"answer": round(self._calc(p, x["id"], k, x["body"][k]["calc"])["num"], 4), "why": self._calc(p, x["id"], k, x["body"][k]["calc"])["why"]} if "calc" in x["body"][k]
                                     else {"answer": self._perm(p, x["id"], k, len(x["body"][k]["options"])).index(x["body"][k]["answer"]), "why": x["body"][k]["why"]})
                            for k in p.ex.get(x["id"], ()) if "q" in x["body"][k] or "calc" in x["body"][k]}}

    # ------------------------------------------------------------------ the placement test (LP6)
    def placement_new(self, p=None):
        """A fresh placement test: one question from each of the first PLACEMENT_UNITS units after Start here, in the
        order of the path, without their answers (options in the player's shuffled order). Stateless: the answers come
        back with the lesson and block index."""
        rng = random.Random(secrets.randbits(64))
        out = []
        for t in self.tracks[1:1 + PLACEMENT_UNITS]:
            qs = [(x["id"], k) for x in self.lessons if x["track"] == t["id"] for k, kind in exercises(x) if kind == "q" and "options" in x["body"][k]]
            if not qs:
                continue
            lid, k = rng.choice(qs)
            b = self._lesson_by_id[lid]["body"][k]
            perm = self._perm(p, lid, k, len(b["options"]))
            out.append({"track": t["id"], "title": t["title"], "lesson": lid, "i": k, "q": b["q"], "options": [b["options"][j] for j in perm]})
        return {"questions": out}

    def placement_grade(self, p, answers):
        """Grade a placement test. Units answered right in a row from the first are known: for a player their lessons
        are marked passed (no XP) and the path starts at the first unit missed. Returns each answer marked and the
        start of the path."""
        results, known, stop = [], [], False
        for a in list(answers or [])[:PLACEMENT_UNITS]:
            x = self._lesson_by_id.get(a.get("lesson")) if isinstance(a, dict) else None
            i = a.get("i") if x else None
            b = x["body"][i] if x and isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(x["body"]) and "q" in x["body"][i] else None
            if b is None:
                return {"error": "Bad answer"}
            perm = self._perm(p, x["id"], i, len(b["options"]))
            c = a.get("choice")
            right = isinstance(c, int) and not isinstance(c, bool) and 0 <= c < len(perm) and perm[c] == b["answer"]
            results.append({"track": x["track"], "lesson": x["id"], "i": i, "right": right, "answer": perm.index(b["answer"]), "why": b["why"]})
            if right and not stop:
                known.append(x["track"])
            else:
                stop = True
        if not results:
            return {"error": "No answers"}
        start = next((t for t in self.tracks[1:] if t["id"] not in known), None)      # None: every unit asked is known
        unit_ids = set(known) | ({"start"} if known else set())
        first = next((x for x in self.lessons if x["track"] not in unit_ids), None)
        out = {"results": results, "known": [t["title"] for t in self.tracks if t["id"] in known],
               "start": {"track": start["title"] if start else None, "lesson": {"id": first["id"], "title": first["title"]} if first else None}}
        if p is not None:
            for x in self.lessons:
                if x["track"] in unit_ids:
                    p.passed.setdefault(x["id"], self.now)
                    p.ex[x["id"]] = [k for k, kind in exercises(x) if kind != "task"]
            p.placed = start["id"] if start else "all"
            out["passed"] = len(p.passed)
        return out

    def trading_summary(self, p):
        """The player's own trading, for the path and the risk lessons (LP10): the last seven days of closes from the
        ledger, the stop and exit counts and the R the hooks keep, and the lesson that fixes each weakness."""
        since = self.now - 7 * 86400
        ev = [e for e in self.history_for(p, 500)["events"] if e["t"] >= since and e["kind"] in ("buy", "sell", "short", "cover")]
        closes = [e for e in ev if e["kind"] in ("sell", "cover")]
        known = [e for e in closes if e.get("pnl") is not None]                 # (the ledger knows each close's P&L; a memory-only game does not)
        wins = [e["pnl"] for e in known if e["pnl"] > 0]
        losses = [e["pnl"] for e in known if e["pnl"] <= 0]
        gross = sum(abs(e.get("mb") or 0.0) for e in ev)
        fees = sum(e.get("fee") or 0.0 for e in ev)
        c = p.counters
        out = {"closes": len(closes), "wins": len(wins), "win_rate": len(wins) / len(known) if known else None,
               "avg_win": sum(wins) / len(wins) if wins else None, "avg_loss": sum(losses) / len(losses) if losses else None,
               "profit_factor": (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else None,
               "fees": fees, "fee_share": fees / gross if gross > 0 else None, "maxdd": p.maxdd,
               "all_closes": c.get("closes", 0), "with_stop": c.get("closes_with_stop", 0),
               "exits": {"stop": c.get("exit_stop", 0), "target": c.get("exit_target", 0), "trail": c.get("exit_trail", 0)},
               "avg_r": sum(p.r_log) / len(p.r_log) if p.r_log else None, "r_n": len(p.r_log), "tips": []}
        tips = out["tips"]
        if out["all_closes"] >= 3 and out["with_stop"] / out["all_closes"] < 0.7:
            tips.append({"text": f"Only {out['with_stop']} of your {out['all_closes']} closed positions had a stop-loss.", "lesson": "stop-placement", "title": "Where stops go"})
        if out["avg_r"] is not None and out["r_n"] >= 3 and out["avg_r"] < 0:
            tips.append({"text": f"Your average trade with a stop came out at {out['avg_r']:+.2f}R.", "lesson": "expectancy", "title": "Win rate, payoff and expectancy"})
        if out["avg_win"] is not None and out["avg_loss"] is not None and -out["avg_loss"] > 1.5 * out["avg_win"]:
            tips.append({"text": "Your average loss is more than one and a half times your average win.", "lesson": "r-multiples", "title": "R-multiples and reward to risk"})
        if out["fee_share"] is not None and out["fee_share"] > 0.02:
            tips.append({"text": f"Fees took {out['fee_share'] * 100:.1f}% of what you traded this week.", "lesson": "costs", "title": "Slippage, gaps through stops, and fees"})
        if p.maxdd > 0.1:
            tips.append({"text": f"Your worst fall today was {p.maxdd * 100:.0f}% from the top.", "lesson": "drawdown", "title": "Drawdown maths"})
        return out

    def learning_summary(self, p):
        """The learning record for the profile pages (LP8)."""
        return {"xp": p.xp, "level": level_of(p.xp), "streak": self.learn_streak(p), "passed": len(p.passed), "total": len(self.path_lessons), "tasks_total": len(TASK_KINDS),
                "today": p.xp_days.get(self._learn_day(), 0), "goal": p.goal, "tasks": len(p.tasks), "weak": self.weak_skills(p),
                "week_xp": p.xp_weeks.get(self._week_key(), 0)}

    # ------------------------------------------------------------------ lessons
    def lessons_view(self, p=None):
        """The Learn page as a path: every track (a unit) with its lessons and their state (passed, exercises done, the
        next one to do), the player's XP, streak and daily goal, the chart tests (with `p`'s score), and the challenges
        when they are on. `p` is None for a visitor."""
        done = p.lessons_passed if p else {}
        by_track, next_id = {}, None
        for x in self.lessons:
            ex = exercises(x)
            ex_done = len(self._ex_done(p, x)) if p else 0
            passed = bool(p and x["id"] in p.passed)
            if next_id is None and not passed and ex:
                next_id = x["id"]
            by_track.setdefault(x["track"], []).append(
                {"id": x["id"], "title": x["title"], "minutes": x.get("minutes", 5), "summary": x.get("summary", ""),
                 "read": x["id"] in done, "passed": passed, "ex_done": ex_done, "ex_total": len(ex), "next": x["id"] == next_id})
        tracks = [{"id": t["id"], "title": t["title"], "blurb": t.get("blurb", ""), "lessons": by_track.get(t["id"], [])}
                  for t in self.tracks]
        score = p.drills if p else {}
        tests = [{"kind": k, "title": drills.TITLES[k], "about": drills.ABOUT[k], "right": score.get(k, [0, 0])[0],
                  "n": score.get(k, [0, 0])[1]} for k in drills.KINDS]
        out = {"tracks": tracks, "read": sum(1 for x in self.lessons if x["id"] in done), "total": len(self.path_lessons),
               "passed": len(p.passed) if p else 0, "next": next_id, "tests": tests, "challenges": [],
               "xp": p.xp if p else 0, "level": level_of(p.xp if p else 0), "goals": list(GOALS), "streak": self.learn_streak(p) if p else 0, "placed": p.placed if p else None,
               "xp_rules": {"right": XP_RIGHT, "wrong": XP_WRONG, "pass": XP_PASS, "task": XP_TASK},
               "weak": self.weak_skills(p) if p else [], "league": self.league(p),
               "today": p.xp_days.get(self._learn_day(), 0) if p else 0, "goal": p.goal if p else GOAL}
        if p is not None:
            week = self._week_key()
            for c in self._challenges():
                st = p.chal.get(c["id"], {})
                key = week if c["period"] == "week" else "once"
                n = st.get("n", 0) if st.get("key") == key else 0
                out["challenges"].append({"id": c["id"], "title": c["title"], "how": c["how"], "period": c["period"],
                                          "target": c["target"], "n": min(n, c["target"]),
                                          "done": key in st.get("done", []), "xp": c["reward"]})
            out["mine"] = self.trading_summary(p)
        return out

    def lesson(self, lesson_id, p=None):
        """One lesson to read: its blocks, its track, and the lessons before and after it in the curriculum. A player
        who opens it has read it."""
        x = self._lesson_by_id.get(lesson_id)
        if not x:
            return None
        if p is not None and lesson_id not in p.lessons_passed:
            p.lessons_passed[lesson_id] = self.now
        k = self.lessons.index(x)
        track = next((t for t in self.tracks if t["id"] == x["track"]), {"title": ""})

        def near(j):
            return {"id": self.lessons[j]["id"], "title": self.lessons[j]["title"]} if 0 <= j < len(self.lessons) else None
        body = []
        for i, b in enumerate(x.get("body", [])):
            if "q" in b and "num" in b:                        # a number question (LP15)
                body.append({"q": b["q"], "num": True, "i": i})
            elif "calc" in b:                                      # generated: fresh numbers each day
                c = self._calc(p, x["id"], i, b["calc"])
                body.append({"q": c["q"], "num": True, "unit": c["unit"], "i": i})
            elif "q" in b:                                       # the answer stays here until it is given (learn_answer)
                perm = self._perm(p, x["id"], i, len(b["options"]))
                body.append({"q": b["q"], "options": [b["options"][j] for j in perm], "i": i})
            elif "task" in b:
                body.append({"task": b["task"], "text": b["text"], "i": i, "how": TASK_KINDS[b["task"]]})
            elif "test" in b:
                body.append({"test": b["test"], "i": i, **({"opt": b["opt"]} if b.get("opt") else {})})
            elif "mine" in b:
                body.append({"mine": True})
            else:
                body.append(b)
        out = {"id": x["id"], "title": x["title"], "track": x["track"], "track_title": track["title"],
               "minutes": x.get("minutes", 5), "summary": x.get("summary", ""), "body": body,
               "prev": near(k - 1), "next": near(k + 1), "total": len(exercises(x))}
        if p is not None:
            out.update(self._lesson_progress(p, x))
            if any("mine" in b for b in body):
                out["mine"] = self.trading_summary(p)
        return out

    # ------------------------------------------------------------------ chart tests (drills.py)
    def _drill_find(self, kind, rng, opt=None):
        """A test of `kind` on a real chart: a company or commodity and a candle size picked at random, up to 40 tries,
        from the candles in memory (the newest 500 of each size; the one still forming is left out). A game too new to
        have enough candles gets a chart from the price model instead (the Daily Chart's maker)."""
        pool = [s for s in self.stocks.values() if s.asset_type in ("equity", "commodity")]
        for _ in range(40 if pool else 0):
            s, tf = rng.choice(pool), rng.choice(list(TEST_TIMEFRAMES))
            rows = list(s.tf.get(tf, ()))[-401:-1]
            if len(rows) < 150:
                continue
            cs = [[r[1], r[2], r[3], r[4], r[5] if len(r) > 5 else 0.0] for r in rows]
            t = drills.make(kind, cs, rng, opt)
            if t:
                return t, cs, {"ticker": s.ticker, "name": s.name, "tf": TEST_TIMEFRAMES[tf], "end": rows[t["upto"]][0]}
        import daily                                     # (only for a new game: the model's own chart)
        for _ in range(6):
            cs = [list(c) for c in daily.make_chart(rng.getrandbits(48))["candles"]]
            t = drills.make(kind, cs, rng, opt)
            if t:
                return t, cs, {"ticker": None, "name": "A chart from the market model", "tf": "short", "end": None}
        return None, None, None

    def reel_stock(self, ticker, tf="1h", n=120):
        """A company for the Instagram reels (tools/memestreet_daily_reel): what it does and its newest candles (the one
        still forming left out). Public facts only, the same as the stock page shows (2026-11-04)."""
        s = self.stocks.get(ticker)
        if s is None or s.asset_type not in ("equity", "commodity") or tf not in TEST_TIMEFRAMES:
            return None
        rows = list(s.tf.get(tf, ()))[-(n + 1):-1]
        return {"ticker": s.ticker, "name": s.name, "sector": s.sector, "desc": s.desc, "tf": TEST_TIMEFRAMES[tf],
                "price": s.price, "candles": [[r[1], r[2], r[3], r[4], r[5] if len(r) > 5 else 0.0] for r in rows]}

    @staticmethod
    def _drill_pack(t, cs):
        """The question (the candles up to the moment) and the answer (the candles after it), on a window of the chart
        that starts early enough for a 50-candle average and every line and mark."""
        up = t["upto"]
        first = min([up - 90] + [x["from"] - 10 for x in t["lines"]] + [m["i"] - 10 for m in t["marks"]])
        start, end = max(0, first, up - 160), min(len(cs), up + 1 + t["show"])
        nd = 4 if min(x[2] for x in cs[start:end]) < 1 else 2

        def candle(x):
            return [round(x[0], nd), round(x[1], nd), round(x[2], nd), round(x[3], nd), int(x[4])]
        lines = [{"price": round(x["price"], nd), "label": x["label"], "tone": x["tone"], "from": max(0, x["from"] - start),
                  "after": x["after"]} for x in t["lines"]]
        marks = [{"i": m["i"] - start, "price": round(m["price"], nd), "label": m["label"], "after": m["after"]}
                 for m in t["marks"] if m["i"] >= start]
        q = {"kind": t["kind"], "title": t["title"], "q": t["q"], "options": t["options"], "overlay": t["overlay"],
             "panel": t["panel"], "candles": [candle(x) for x in cs[start:up + 1]],
             "lines": [x for x in lines if not x["after"]], "marks": [m for m in marks if not m["after"]]}
        a = {"answer": t["answer"], "result": t["result"], "explain": t["explain"],
             "candles": [candle(x) for x in cs[up + 1:end]], "lines": lines, "marks": marks}
        return q, a

    def drill_new(self, kind, opt=None):
        """A new chart test of `kind` (one of drills.KINDS, or "any"): the question, with an id to answer it by."""
        rng = random.Random(secrets.randbits(64))
        if kind == "any":
            kind = rng.choice(drills.KINDS)
        if kind not in drills.KINDS:
            return {"error": "Unknown kind of test"}
        t, cs, where = self._drill_find(kind, rng, opt)
        if not t:
            return {"error": "No chart has one of these right now: try another kind"}
        q, a = self._drill_pack(t, cs)
        tid = secrets.token_urlsafe(9)
        self._drill_q[tid] = (kind, t["answer"], dict(a, where=where), self.now)
        while len(self._drill_q) > TEST_PENDING:
            self._drill_q.popitem(last=False)
        return dict(q, id=tid, tf=where["tf"])

    def drill_answer(self, p, tid, choice, lesson_id=None, i=None, review=False):
        """Mark a chart test and show what happened next. A player's score for the kind is kept; a test taken inside a
        lesson (`lesson_id`, `i`: the index of its block) is one of that lesson's exercises and earns XP."""
        got = self._drill_q.pop(tid, None) if isinstance(tid, str) else None
        if not got or self.now - got[3] > TEST_KEEP:
            return {"error": "This test has expired: here is a new one", "expired": True}
        kind, answer, reveal, _ = got
        right = isinstance(choice, int) and not isinstance(choice, bool) and choice == answer
        out = dict(reveal, right=right)
        self._attempt(p, kind, right)
        if p is not None:
            sc = p.drills.setdefault(kind, [0, 0])
            sc[0] += int(right)
            sc[1] += 1
            out["score"] = list(sc)
            if review:
                out["xp"] = self._xp(p, XP_REVIEW) if right else 0
                out["weak"] = self.weak_skills(p)
                return out
            x = self._lesson_by_id.get(lesson_id) if lesson_id else None
            if x and isinstance(i, int) and 0 <= i < len(x["body"]) and "test" in x["body"][i]:
                done = p.ex.setdefault(lesson_id, [])
                if i not in done:
                    done.append(i)
                    out["xp"] = self._xp(p, XP_RIGHT if right else XP_WRONG) + self._pass_check(p, x)
                out.update(self._lesson_progress(p, x))
        return out

    def drill_example(self, kind, opt=None):
        """A lesson's example: a test of `kind` with its answer, all at once (the same one for everyone for a quarter
        of an hour, then a fresh one)."""
        if kind not in drills.KINDS:
            return {"error": "Unknown kind of chart"}
        got = self._drill_ex.get((kind, opt))
        if got and self.now - got[0] < EXAMPLE_KEEP:
            return got[1]
        rng = random.Random(secrets.randbits(64))
        t, cs, where = self._drill_find(kind, rng, opt)
        if not t:
            return {"error": "No example right now"}
        q, a = self._drill_pack(t, cs)
        ex = dict(q, tf=where["tf"], upto=len(q["candles"]) - 1, candles=q["candles"] + a["candles"], lines=a["lines"],
                  marks=a["marks"], answer=a["answer"], result=a["result"], explain=a["explain"], where=where)
        self._drill_ex[(kind, opt)] = (self.now, ex)
        return ex

    # ------------------------------------------------------------------ hooks from trading
    def _learn_order(self, p, ticker, kind, trigger=None, raw=None):
        """An order was placed (`raw` is its real kind; `kind` folds a trailing stop into a stop-loss). The first stop on
        a position fixes the risk the trade was taken with (entry, stop, shares), so its close can be measured in R
        (LP9), and a stop risking under 2% of the account counts for the "sized by the stop" habit (LP11)."""
        if raw in ("limit_buy", "limit_sell"):
            self._learn_task(p, "limit")
        if raw == "trailing_stop":
            self._learn_task(p, "trail")
        if kind == "take_profit":
            self._bump(p, "targets")
            self._learn_task(p, "target")
        if kind != "stop_loss" or ticker in p.stop_seen:
            return
        p.stop_seen.append(ticker)
        held = p.hold.get(ticker, 0.0)
        sh = abs(held)
        if trigger and sh > 1e-9:
            entry = abs(p.cost.get(ticker, 0.0)) / sh
            risk = abs(entry - float(trigger)) * sh
            p.stop_px[ticker] = {"stop": float(trigger), "entry": entry, "sh": sh, "risk": risk}
            eq = self.equity(p)
            if eq > 0 and risk <= 0.02 * eq:
                self._bump(p, "sized")
        if held < 0:
            self._learn_task(p, "short_stop")
        self._bump(p, "stops")
        self._learn_task(p, "stop")

    def _learn_close(self, p, ticker, pnl, closed):
        """A position was closed (social's trade hook, before `_learn_after_trade`): count it, whether it had a stop,
        and its R when the first stop fixed the risk (ponytail: R uses the closing trade's P&L against the risk at the
        first stop; partial closes are approximate)."""
        if not closed or pnl is None:
            return
        c = p.counters
        c["closes"] = c.get("closes", 0) + 1
        st = p.stop_px.pop(ticker, None)
        if ticker in p.stop_seen or st:
            c["closes_with_stop"] = c.get("closes_with_stop", 0) + 1
        if st and st.get("risk", 0) > 1e-9:
            p.r_log.append(round(float(pnl) / st["risk"], 3))
            del p.r_log[:-100]

    def _learn_after_trade(self, p, ticker, kind="trade"):
        """Every trade: the first is a task; a short is one; a position that had a stop-loss and was closed is a
        planned trade, win or lose."""
        self._learn_task(p, "trade")
        if kind == "short":
            self._learn_task(p, "short")
        if abs(p.hold.get(ticker, 0.0)) > 1e-9 or ticker not in p.stop_seen:
            return
        p.stop_seen.remove(ticker)
        self._bump(p, "planned")
        self._learn_task(p, "planned")
