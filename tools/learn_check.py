"""The Learn loop's automated rubric (docs/learn-loop/RUBRIC.md, section B, v2): is the course the shape a Duolingo-style
path should be? Pure Python over the lesson files; no server.

    python tools/learn_check.py            prints a table, exits 1 when any check fails
    python tools/learn_check.py --json     the same as JSON (the loop's ledger reads it)

Checks: every lesson parses and has a goal line; at least 4 exercises per lesson (the glossary is a reference); no
lesson over 500 prose words; no teach card over 70 words and never more than two in a row; the right answer is the
longest option in under 45% of questions in every unit; no two questions nearly the same; no throwaway wrong options;
every chart-reading lesson has a chart or a chart test; every [try] link resolves; every [task] kind is exercised by a
test; in every unit most questions sit under the section they test; every unit carries a tier; the course is big
enough (130 lessons, 20 units, 3 Expert units of 5); the placement covers every unit; every Expert lesson applies;
the power-ups are defined and tested. Thresholds are the constants below. The rows marked v2 fail until the loop
builds what they measure.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "game"))
import learning  # noqa: E402

MIN_EXERCISES = 4
MAX_WORDS = 500
CARD_WORDS = 70                # a teach card (one paragraph, list, table or box)
CARDS_IN_A_ROW = 2             # teach cards without an exercise, chart, task or try-it between them
LONGEST_SHARE = 0.45           # the right answer may be the longest option in at most this share of a unit's questions
DUPLICATE_JACCARD = 0.85
THROWAWAY_WORDS = 2            # a wrong option of this many words or fewer, with no number in it, gives the answer away
CHART_UNITS = ("charts", "indicators")
CHART_LESSONS = ("trailing-scaling", "trend-following", "mean-reversion", "breakout-trading")   # chart-reading lessons in other units
INTERLEAVED_SHARE = 0.8        # questions placed before the lesson's last heading, in every unit
REFERENCE_LESSONS = {"glossary"}
TIERS = ("free", "pro", "expert")
MIN_LESSONS, MIN_UNITS, MIN_EXPERT_UNITS, MIN_EXPERT_LESSONS = 130, 20, 3, 5
POWERUP_KEYS = ("name", "kind", "effect", "earned", "limit")
ROUTES = ("/", "/learn", "/holdings", "/portfolio", "/history", "/leaders", "/social", "/profile", "/shop", "/calendar",
          "/bots", "/bots/guide", "/daily", "/lessons")
TEACH = ("p", "list", "table", "tip", "here", "warn")
INTERACTIVE = ("q", "calc", "test", "chart", "task", "try", "mine")


def _words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def card_words(b):
    """Words on one teach card (a paragraph, a list, a table or a box); 0 for anything else."""
    n = 0
    for k in ("p", "tip", "here", "warn"):
        if k in b:
            n += len(_words(b[k]))
    if "list" in b:
        n += sum(len(_words(x)) for x in b["list"])
    if "table" in b:
        n += sum(len(_words(c)) for r in b["table"] for c in r)
    return n


def prose_words(lesson):
    return sum(card_words(b) + (len(_words(b["h"])) if "h" in b else 0) + (len(_words(b["try"])) if "try" in b else 0)
               for b in lesson["body"])


def chart_ids():
    """Indicator ids and candle sizes the stock page knows (web/chart.js), for the [try] links."""
    try:
        with open(os.path.join(ROOT, "web", "chart.js"), encoding="utf-8") as f:
            js = f.read()
    except OSError:
        return set(), set()
    ids = set(re.findall(r"\n \['([a-z0-9_]+)','", js))
    for m in re.finditer(r"\[([0-9,]+)\]\.map\(\(?n(?:,j)?\)?=>\['(sma|ema)'\+n", js):
        ids.update(m.group(2) + n for n in m.group(1).split(","))
    tfs = set(re.findall(r"\['([0-9a-z]+)','[^']*',[0-9]+\]", js.split("const PERIODS=")[1].split("\n")[0])) if "const PERIODS=" in js else set()
    return ids, tfs


def applies(x):
    """An Expert lesson applies: a calculation, a number answer, a chart test or a chart."""
    return any("calc" in b or "num" in b or "test" in b or "chart" in b for b in x["body"])


def run(pattern=learning.LEARN_FILES, tests_text=None):
    """Every check as a row: (name, ok, detail). `tests_text` is tests/test_learning.py (read when None)."""
    rows = []
    try:
        tracks, lessons = learning.load_content(pattern)
    except ValueError as e:
        return [("parses", False, str(e))]
    rows.append(("parses", True, f"{len(tracks)} units, {len(lessons)} lessons"))
    steps = [x for x in lessons if x["id"] not in REFERENCE_LESSONS]
    tier = {t["id"]: t.get("tier") for t in tracks}

    nogoal = [x["id"] for x in lessons if not x.get("summary")]
    rows.append(("every lesson has a goal line", not nogoal, ", ".join(nogoal[:8]) or "all"))

    thin = [f"{x['id']} ({len(learning.exercises(x))})" for x in steps if len(learning.exercises(x)) < MIN_EXERCISES]
    rows.append((f"at least {MIN_EXERCISES} exercises a lesson", not thin, ", ".join(thin[:8]) + (f" (+{len(thin) - 8})" if len(thin) > 8 else "") or "all"))

    long_ = [f"{x['id']} ({prose_words(x)})" for x in steps if prose_words(x) > MAX_WORDS]
    rows.append((f"no lesson over {MAX_WORDS} prose words", not long_, ", ".join(long_[:8]) or "all short enough"))

    fat = [f"{x['id']}:{k} ({card_words(b)})" for x in steps for k, b in enumerate(x["body"]) if card_words(b) > CARD_WORDS]
    rows.append((f"no teach card over {CARD_WORDS} words (v2)", not fat, f"{len(fat)} cards: " + ", ".join(fat[:6]) if fat else "all"))

    runs = []
    for x in steps:
        n = 0
        for b in x["body"]:
            if any(k in b for k in TEACH):
                n += 1
                if n == CARDS_IN_A_ROW + 1:
                    runs.append(x["id"])
            elif any(k in b for k in INTERACTIVE):
                n = 0
    rows.append((f"at most {CARDS_IN_A_ROW} teach cards in a row (v2)", not runs, f"{len(runs)} lessons: " + ", ".join(runs[:8]) if runs else "all"))

    qs = [(x, b) for x in lessons for b in x["body"] if "q" in b and "options" in b]
    by_unit = {}
    for x, b in qs:
        longest = len(b["options"][b["answer"]]) > max(len(o) for k, o in enumerate(b["options"]) if k != b["answer"])
        u = by_unit.setdefault(x["track"], [0, 0])
        u[0] += longest
        u[1] += 1
    over = [f"{u} {a / n:.0%}" for u, (a, n) in by_unit.items() if n and a / n >= LONGEST_SHARE]
    share = sum(a for a, _ in by_unit.values()) / len(qs) if qs else 0.0
    rows.append((f"right answer the longest option in under {LONGEST_SHARE:.0%}", not over, f"{share:.0%} of {len(qs)} questions overall" + (f"; over in {', '.join(over)}" if over else ", every unit under")))

    dups = []
    sets = [(x["id"], set(_words(b["q"]))) for x, b in qs]
    for a in range(len(sets)):
        for c in range(a + 1, len(sets)):
            sa, sc = sets[a][1], sets[c][1]
            if sa and sc and len(sa & sc) / len(sa | sc) > DUPLICATE_JACCARD:
                dups.append(f"{sets[a][0]} ~ {sets[c][0]}")
    rows.append(("no near-duplicate questions", not dups, ", ".join(dups[:8]) or "none"))

    throw = [f"{x['id']}: {o!r}" for x, b in qs for k, o in enumerate(b["options"]) if k != b["answer"] and len(_words(o)) <= THROWAWAY_WORDS and not re.search(r"\d", o)]   # a number is a real option
    rows.append(("no throwaway wrong options (v2)", not throw, f"{len(throw)}: " + ", ".join(throw[:6]) if throw else "none"))

    missing = [x["id"] for x in lessons if (x["track"] in CHART_UNITS or x["id"] in CHART_LESSONS or tier.get(x["track"]) == "expert")
               and not any("chart" in b or "test" in b for b in x["body"])]
    rows.append(("every chart lesson has a chart or a test", not missing, ", ".join(missing) or "all"))

    ids, tfs = chart_ids()
    bad = []
    for x in lessons:
        for b in x["body"]:
            if "try" not in b:
                continue
            path, _, query = b["href"].partition("?")
            if not (path in ROUTES or path.startswith("/stock/")):
                bad.append(f"{x['id']}: {b['href']}")
                continue
            for part in [p for p in query.split("&") if p]:
                k, _, v = part.partition("=")
                if k == "ind" and ids and not all(i in ids for i in v.split(",")):
                    bad.append(f"{x['id']}: unknown indicator in {b['href']}")
                if k == "tf" and tfs and v not in tfs:
                    bad.append(f"{x['id']}: unknown candle size in {b['href']}")
    rows.append(("every [try] link resolves", not bad, ", ".join(bad[:6]) or "all"))

    if tests_text is None:
        try:
            with open(os.path.join(ROOT, "tests", "test_learning.py"), encoding="utf-8") as f:
                tests_text = f.read()
        except OSError:
            tests_text = ""
    kinds = {b["task"] for x in lessons for b in x["body"] if "task" in b}
    untested = sorted(k for k in kinds if f'"{k}"' not in tests_text)
    rows.append(("every task kind is exercised by a test", not untested, ", ".join(untested) or f"{len(kinds)} kinds"))

    before, total, late = 0, 0, {}
    for x in steps:
        prose = [k for k, b in enumerate(x["body"]) if any(t in b for t in ("p", "h", "list", "table"))]
        last_prose = max(prose, default=-1)
        for k, b in enumerate(x["body"]):
            if "q" in b or "calc" in b:
                total += 1
                ok = k <= last_prose + 1                       # under a section: reading follows it, or it is the one right after the last paragraph
                before += ok
                if not ok:
                    late[x["track"]] = late.get(x["track"], 0) + 1
    share = before / total if total else 1.0
    rows.append((f"every unit: {INTERLEAVED_SHARE:.0%} of questions under their section", share >= INTERLEAVED_SHARE,
                 f"{share:.0%} of {total} questions" + (f"; at the end in {', '.join(f'{u} ({n})' for u, n in sorted(late.items()))}" if late else "")))

    untiered = [t["id"] for t in tracks if t.get("tier") not in TIERS]
    rows.append(("every unit carries a tier (v2)", not untiered, ", ".join(untiered) or f"{sum(1 for t in tracks if t.get('tier') == 'expert')} Expert of {len(tracks)}"))

    expert_units = [t for t in tracks if t.get("tier") == "expert"]
    big = [t for t in expert_units if sum(1 for x in lessons if x["track"] == t["id"]) >= MIN_EXPERT_LESSONS]
    ok = len(lessons) >= MIN_LESSONS and len(tracks) >= MIN_UNITS and len(big) >= MIN_EXPERT_UNITS
    rows.append((f"{MIN_LESSONS} lessons, {MIN_UNITS} units, {MIN_EXPERT_UNITS} Expert units of {MIN_EXPERT_LESSONS} (v2)", ok,
                 f"{len(lessons)} lessons, {len(tracks)} units, {len(big)} Expert units of {MIN_EXPERT_LESSONS}+"))

    want = len(tracks) - 1
    rows.append(("placement covers every unit (v2)", learning.PLACEMENT_UNITS >= want, f"PLACEMENT_UNITS {learning.PLACEMENT_UNITS} of {want} units after Start"))

    noapply = [x["id"] for x in lessons if tier.get(x["track"]) == "expert" and not applies(x)]
    rows.append(("every Expert lesson applies (v2)", not noapply, ", ".join(noapply[:8]) or (f"{sum(1 for x in lessons if tier.get(x['track']) == 'expert')} Expert lessons" if expert_units else "no Expert unit yet")))

    pw = getattr(learning, "POWERUPS", None) or {}
    badpw = [k for k, v in pw.items() if not all(v.get(f) for f in POWERUP_KEYS)] if isinstance(pw, dict) else ["not a table"]
    rewards = {b["reward"] for x in lessons for b in x["body"] if "reward" in b}
    unknown = sorted(r for r in rewards if r not in pw)
    rows.append(("power-ups defined, every reward names one (v2)", bool(pw) and not badpw and not unknown,
                 (f"{len(pw)} power-ups" if pw else "no learning.POWERUPS") + (f"; incomplete: {', '.join(badpw)}" if badpw else "") + (f"; unknown rewards: {', '.join(unknown)}" if unknown else "")))

    untested_pw = sorted(k for k in pw if f'"{k}"' not in tests_text) if isinstance(pw, dict) else []
    allowance = "FREE_LESSONS_A_DAY" in tests_text
    rows.append(("daily allowance and power-ups tested (v2)", bool(pw) and allowance and not untested_pw,
                 ("the free day is tested" if allowance else "no test names FREE_LESSONS_A_DAY") + (f"; untested power-ups: {', '.join(untested_pw)}" if untested_pw else "")))
    return rows


def main(argv):
    rows = run()
    if "--json" in argv:
        print(json.dumps([{"check": n, "ok": ok, "detail": d} for n, ok, d in rows], indent=1))
    else:
        width = max(len(n) for n, _, _ in rows)
        for n, ok, d in rows:
            print(f"{'PASS' if ok else 'FAIL'}  {n.ljust(width)}  {d}")
        print(f"\n{sum(1 for _, ok, _ in rows if ok)} of {len(rows)} checks pass")
    return 0 if all(ok for _, ok, _ in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
