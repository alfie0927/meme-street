"""The Learn loop's automated rubric (docs/learn-loop/RUBRIC.md, section B): is the course the shape a Duolingo-style
path should be? Pure Python over the lesson files; no server.

    python tools/learn_check.py            prints a table, exits 1 when any check fails
    python tools/learn_check.py --json     the same as JSON (the loop's ledger reads it)

Checks: every lesson parses; at least 3 exercises per lesson (the glossary is a reference); no lesson over 600 prose
words; the right answer is the longest option in under 45% of questions; no two questions nearly the same; every
chart-reading lesson has a chart or a chart test; every [try] link resolves (routes, /stock/, known indicator ids and
candle sizes); every [task] kind is exercised by a test; in the core units most questions sit under the section they
test (interleaved), not all at the end. Thresholds are the constants below.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "game"))
import learning  # noqa: E402

MIN_EXERCISES = 3
MAX_WORDS = 600
LONGEST_SHARE = 0.45           # the right answer may be the longest option in at most this share of questions
DUPLICATE_JACCARD = 0.85
CORE_UNITS = ("start", "basics", "charts", "indicators", "orders", "risk")
CHART_UNITS = ("charts", "indicators")
CHART_LESSONS = ("trailing-scaling", "trend-following", "mean-reversion", "breakout-trading")   # chart-reading lessons in other units
INTERLEAVED_SHARE = 0.8        # in the core units, questions placed before the lesson's last heading
REFERENCE_LESSONS = {"glossary"}
ROUTES = ("/", "/learn", "/holdings", "/portfolio", "/history", "/leaders", "/social", "/profile", "/shop", "/calendar",
          "/bots", "/bots/guide", "/daily", "/lessons")


def _words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def prose_words(lesson):
    n = 0
    for b in lesson["body"]:
        for k in ("p", "h", "tip", "here", "warn", "try"):
            if k in b:
                n += len(_words(b[k]))
        if "list" in b:
            n += sum(len(_words(x)) for x in b["list"])
        if "table" in b:
            n += sum(len(_words(c)) for r in b["table"] for c in r)
    return n


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


def run(pattern=learning.LEARN_FILES, tests_text=None):
    """Every check as a row: (name, ok, detail). `tests_text` is tests/test_learning.py (read when None)."""
    rows = []
    try:
        tracks, lessons = learning.load_content(pattern)
    except ValueError as e:
        return [("parses", False, str(e))]
    rows.append(("parses", True, f"{len(tracks)} units, {len(lessons)} lessons"))

    thin = [f"{x['id']} ({len(learning.exercises(x))})" for x in lessons if x["id"] not in REFERENCE_LESSONS and len(learning.exercises(x)) < MIN_EXERCISES]
    rows.append((f"at least {MIN_EXERCISES} exercises a lesson", not thin, ", ".join(thin) or "all"))

    long_ = [f"{x['id']} ({prose_words(x)})" for x in lessons if x["id"] not in REFERENCE_LESSONS and prose_words(x) > MAX_WORDS]
    rows.append((f"no lesson over {MAX_WORDS} prose words", not long_, ", ".join(long_) or "all short enough"))

    qs = [(x, b) for x in lessons for b in x["body"] if "q" in b and "options" in b]
    longest = [1 for _, b in qs if len(b["options"][b["answer"]]) > max(len(o) for k, o in enumerate(b["options"]) if k != b["answer"])]
    share = len(longest) / len(qs) if qs else 0.0
    rows.append((f"right answer the longest option in under {LONGEST_SHARE:.0%}", share < LONGEST_SHARE, f"{share:.0%} of {len(qs)} questions"))

    dups = []
    sets = [(x["id"], set(_words(b["q"]))) for x, b in qs]
    for a in range(len(sets)):
        for c in range(a + 1, len(sets)):
            sa, sc = sets[a][1], sets[c][1]
            if sa and sc and len(sa & sc) / len(sa | sc) > DUPLICATE_JACCARD:
                dups.append(f"{sets[a][0]} ~ {sets[c][0]}")
    rows.append(("no near-duplicate questions", not dups, ", ".join(dups[:8]) or "none"))

    missing = [x["id"] for x in lessons if (x["track"] in CHART_UNITS or x["id"] in CHART_LESSONS)
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

    before, total = 0, 0
    for x in lessons:
        if x["track"] not in CORE_UNITS:
            continue
        prose = [k for k, b in enumerate(x["body"]) if any(t in b for t in ("p", "h", "list", "table"))]
        last_prose = max(prose, default=-1)
        for k, b in enumerate(x["body"]):
            if "q" in b or "calc" in b:
                total += 1
                before += k <= last_prose + 1                  # under a section: reading follows it, or it is the one right after the last paragraph
    share = before / total if total else 1.0
    rows.append((f"core units: {INTERLEAVED_SHARE:.0%} of questions under their section", share >= INTERLEAVED_SHARE, f"{share:.0%} of {total} questions"))
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
