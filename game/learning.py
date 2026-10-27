"""Learning (ROADMAP.md tracks TA-C and L): the Learn page's curriculum and its chart tests, and the challenges
(switched off).

* **The curriculum** lives in `content/learn-*.md`, one file per track, read in file-name order (`parse_learn` below
  has the format). A lesson a player opens counts as read (`lessons_passed`, the name from when lessons had quizzes;
  the quizzes were taken out on 2026-10-27, on request). **Nothing on the Learn page pays MB** (since 2026-10-23).
  Visitors can read and take the tests too; only a player's progress is kept.
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
import os
import random
import re
import secrets

import drills
import paths

LEARN_FILES = os.path.join(paths.CONTENT, "learn-*.md")
CHALLENGES = [
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
PLAYER_FIELDS = ("lessons_passed", "chal", "stop_seen", "drills")
TEST_TIMEFRAMES = {"1m": "1-minute", "5m": "5-minute", "15m": "15-minute", "1h": "1-hour"}
TEST_PENDING = 3000          # chart tests waiting for an answer, at most (the oldest go first)
TEST_KEEP = 3 * 3600         # and for at most this long
EXAMPLE_KEEP = 900           # a lesson's example chart is found again after this long


def init_player(p):
    p.lessons_passed = {}      # lesson id -> when it was first read
    p.chal = {}                # challenge id -> {"n": progress, "key": period key, "done": [period keys won]}
    p.stop_seen = []           # tickers whose open position has had a stop-loss (for "planned" trades)
    p.drills = {}              # chart test kind -> [right, answered]


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
    Raises ValueError on anything it does not understand, with the line number."""
    tracks, lessons = ([] if tracks is None else tracks), ([] if lessons is None else lessons)
    track = lesson = None
    para = []

    def flush():
        if para:
            lesson["body"].append({"p": " ".join(para)})
            para.clear()

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
        if not line:
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
        elif re.fullmatch(r"\[(chart|test) [a-z]+\]", line):
            flush()
            k, kind = line[1:-1].split()
            if kind not in drills.KINDS and not (k == "test" and kind == "any"):
                raise ValueError(f"line {n}: no chart test called {kind!r}")
            body.append({k: kind})
        elif line.startswith("[try "):
            flush()
            m = re.fullmatch(r"\[try (/\S*)\]\s*(.+)", line)
            if not m:
                raise ValueError(f"line {n}: want '[try /path] text'")
            body.append({"try": m.group(2), "href": m.group(1)})
        else:
            para.append(line)
    if lesson:
        flush()
    return tracks, lessons


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
        self._drill_q = collections.OrderedDict()       # test id -> (kind, answer, the reveal, when asked)
        self._drill_ex = {}                              # kind -> (when found, a lesson's example chart)

    def _challenges(self):
        """The challenges on offer: none while they are switched off (the `challenges` setting, off since 2026-10-23)."""
        return CHALLENGES if self.settings.get("challenges", False) else []

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
                self._reward(p, c["reward"], f"Challenge complete: {c['title']}")

    # ------------------------------------------------------------------ lessons
    def lessons_view(self, p=None):
        """The Learn page: every track with its lessons (and which ones `p` has read), the chart tests (with `p`'s
        score), and the challenges when they are on. `p` is None for a visitor."""
        done = p.lessons_passed if p else {}
        by_track = {}
        for x in self.lessons:
            by_track.setdefault(x["track"], []).append(
                {"id": x["id"], "title": x["title"], "minutes": x.get("minutes", 5), "summary": x.get("summary", ""),
                 "read": x["id"] in done})
        tracks = [{"id": t["id"], "title": t["title"], "blurb": t.get("blurb", ""), "lessons": by_track.get(t["id"], [])}
                  for t in self.tracks]
        score = p.drills if p else {}
        tests = [{"kind": k, "title": drills.TITLES[k], "about": drills.ABOUT[k], "right": score.get(k, [0, 0])[0],
                  "n": score.get(k, [0, 0])[1]} for k in drills.KINDS]
        out = {"tracks": tracks, "read": sum(1 for x in self.lessons if x["id"] in done), "total": len(self.lessons),
               "tests": tests, "challenges": []}
        if p is not None:
            week = self._week_key()
            for c in self._challenges():
                st = p.chal.get(c["id"], {})
                key = week if c["period"] == "week" else "once"
                n = st.get("n", 0) if st.get("key") == key else 0
                out["challenges"].append({"id": c["id"], "title": c["title"], "how": c["how"], "period": c["period"],
                                          "target": c["target"], "n": min(n, c["target"]),
                                          "done": key in st.get("done", []), "reward": c["reward"]})
            out["week"] = self.challenge_week_status(p)
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
        return {"id": x["id"], "title": x["title"], "track": x["track"], "track_title": track["title"],
                "minutes": x.get("minutes", 5), "summary": x.get("summary", ""), "body": x.get("body", []),
                "prev": near(k - 1), "next": near(k + 1)}

    # ------------------------------------------------------------------ chart tests (drills.py)
    def _drill_find(self, kind, rng):
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
            t = drills.make(kind, cs, rng)
            if t:
                return t, cs, {"ticker": s.ticker, "name": s.name, "tf": TEST_TIMEFRAMES[tf], "end": rows[t["upto"]][0]}
        import daily                                     # (only for a new game: the model's own chart)
        for _ in range(6):
            cs = [list(c) for c in daily.make_chart(rng.getrandbits(48))["candles"]]
            t = drills.make(kind, cs, rng)
            if t:
                return t, cs, {"ticker": None, "name": "A chart from the market model", "tf": "short", "end": None}
        return None, None, None

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

    def drill_new(self, kind):
        """A new chart test of `kind` (one of drills.KINDS, or "any"): the question, with an id to answer it by."""
        rng = random.Random(secrets.randbits(64))
        if kind == "any":
            kind = rng.choice(drills.KINDS)
        if kind not in drills.KINDS:
            return {"error": "Unknown kind of test"}
        t, cs, where = self._drill_find(kind, rng)
        if not t:
            return {"error": "No chart has one of these right now: try another kind"}
        q, a = self._drill_pack(t, cs)
        tid = secrets.token_urlsafe(9)
        self._drill_q[tid] = (kind, t["answer"], dict(a, where=where), self.now)
        while len(self._drill_q) > TEST_PENDING:
            self._drill_q.popitem(last=False)
        return dict(q, id=tid, tf=where["tf"])

    def drill_answer(self, p, tid, choice):
        """Mark a chart test and show what happened next. A player's score for the kind is kept."""
        got = self._drill_q.pop(tid, None) if isinstance(tid, str) else None
        if not got or self.now - got[3] > TEST_KEEP:
            return {"error": "This test has expired: here is a new one", "expired": True}
        kind, answer, reveal, _ = got
        right = isinstance(choice, int) and not isinstance(choice, bool) and choice == answer
        out = dict(reveal, right=right)
        if p is not None:
            sc = p.drills.setdefault(kind, [0, 0])
            sc[0] += int(right)
            sc[1] += 1
            out["score"] = list(sc)
        return out

    def drill_example(self, kind):
        """A lesson's example: a test of `kind` with its answer, all at once (the same one for everyone for a quarter
        of an hour, then a fresh one)."""
        if kind not in drills.KINDS:
            return {"error": "Unknown kind of chart"}
        got = self._drill_ex.get(kind)
        if got and self.now - got[0] < EXAMPLE_KEEP:
            return got[1]
        rng = random.Random(secrets.randbits(64))
        t, cs, where = self._drill_find(kind, rng)
        if not t:
            return {"error": "No example right now"}
        q, a = self._drill_pack(t, cs)
        ex = dict(q, tf=where["tf"], upto=len(q["candles"]) - 1, candles=q["candles"] + a["candles"], lines=a["lines"],
                  marks=a["marks"], answer=a["answer"], result=a["result"], explain=a["explain"], where=where)
        self._drill_ex[kind] = (self.now, ex)
        return ex

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
