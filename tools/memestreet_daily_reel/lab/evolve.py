"""Lab: the next version of the rules under test (RULES_V2.md), once a day (memestreet-reel-evolve.timer, 05:00 UTC).

The current version is judged on its Trial Reels pairs once at least 3 are scored (lab/trials.py: real skip rate and
watch time against the current reel). Claude gets the scoreboard by version and the current rules, and changes ONE
thing, the change most likely to cut skips and lengthen watching, keeping what the owner decided (the rulebook and the
template section are not its to change). The old version is kept in lab/data/rules/; the new one is used by the next pair.
  python3 lab/evolve.py          (on the reel server)
  python3 lab/evolve.py demo     self-check
"""
import json, os, re, shutil, subprocess, sys, time

LAB = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(LAB); RULES = os.path.join(ROOT, "RULES_V2.md")
MIN_PAIRS = 3
CHANGES = 3                                                      # (the owner, 2026-11-08: a few changes, so the two versions look different)
CHAMPION = os.path.join(ROOT, "CHAMPION.md")                     # (the promoted winner: every regular reel's rules)
HISTORY = os.path.join(LAB, "data", "rules", "history.md")       # (every round's verdict, so a dropped change is not tried again)


def version(text):
    m = re.search(r"^Version: (\d+)", text, re.M); return int(m.group(1)) if m else 1


def summary(rows):
    """Per version: pairs scored, how often version 2 won, and its average skip and watch against the current reel's."""
    out = {}
    for r in rows:
        if not r.get("winner"): continue
        v = out.setdefault(r.get("version") or 1, {"pairs": 0, "v2_wins": 0, "skip_v1": [], "skip_v2": [], "watch_v1": [], "watch_v2": [], "formats": []})
        v["pairs"] += 1; v["v2_wins"] += r["winner"] == "v2"; v["formats"].append(r.get("category"))
        for k in ("v1", "v2"):
            v["skip_" + k].append(r[k].get("reels_skip_rate")); v["watch_" + k].append((r[k].get("ig_reels_avg_watch_time") or 0) / 1000)
    avg = lambda xs: round(sum(x for x in xs if x is not None) / max(1, sum(x is not None for x in xs)), 1)
    return {k: {"pairs": v["pairs"], "v2_wins": v["v2_wins"], "skip_v1": avg(v["skip_v1"]), "skip_v2": avg(v["skip_v2"]),
                "watch_v1": avg(v["watch_v1"]), "watch_v2": avg(v["watch_v2"]), "formats": v["formats"]} for k, v in out.items()}


def main():
    subprocess.run([sys.executable, os.path.join(LAB, "trials.py")], check=True, cwd=ROOT)
    rows = json.load(open(os.path.join(LAB, "data", "trials.json")))
    text = open(RULES, encoding="utf-8").read(); n = version(text); S = summary(rows)
    if S.get(n, {}).get("pairs", 0) < MIN_PAIRS:
        return print(f"version {n} has {S.get(n, {}).get('pairs', 0)} scored pairs; it needs {MIN_PAIRS} before the next version")
    # the round's verdict (the owner, 2026-11-08): a version 2 that won most of its pairs becomes v1, the rules of every regular
    # reel (CHAMPION.md); one that lost is dropped. Either way the next version 2 is v1 plus one new change.
    x = S[n]; won = 2 * x["v2_wins"] > x["pairs"]
    if won: shutil.copy(RULES, CHAMPION)
    first = os.path.join(LAB, "data", "rules", "v1.md")
    text = text if won else open(CHAMPION, encoding="utf-8").read() if os.path.exists(CHAMPION) else \
        open(first, encoding="utf-8").read() if os.path.exists(first) else text
    os.makedirs(os.path.join(LAB, "data", "rules"), exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(f"- version {n}: v2 won {x['v2_wins']} of {x['pairs']} pairs ({'promoted to v1' if won else 'dropped'}); "
                f"skip {x['skip_v1']}% -> {x['skip_v2']}%, watch {x['watch_v1']}s -> {x['watch_v2']}s\n")
    print(f"version {n}: v2 won {x['v2_wins']} of {x['pairs']}: " + ("promoted, it is now v1" if won else "dropped; v1 stays"))
    tried = open(HISTORY, encoding="utf-8").read()
    ask = ("You improve the rules for Meme Street's version-2 Instagram Reels by A/B testing. Each pair is the same facts made as "
           "the current reel (v1) and as version 2 (v2), both posted as Trial Reels to non-followers. Lower skip rate (% leaving in "
           "the first 3 s) and longer average watch are better.\n\nScoreboard by version of the rules (skip %, watch seconds):\n"
           + json.dumps(S, indent=1) + "\n\nEach round's verdict (a version that lost was dropped; do not try its change again):\n" + tried +
           "\n\nThe rules to change (v1, the current winner):\n" + text +
           f"\n\nMake the next version 2: change {CHANGES} things in the rules, a package most likely to cut skips and lengthen "
           "watching given these results (if a past version did better, you may bring back what it had). At least 2 of them must be "
           "VISIBLE, so a viewer can tell the two reels apart with the sound off: what the hook's acted scene does, how many story "
           "scenes and how fast the screen changes, how the chart is framed and marked, the on-screen text, the order of the reveal. "
           "Do not touch the '## The template' section, and keep every rule the owner decided. Reply with JSON only: "
           "{\"changes\": [\"one sentence each\"], \"why\": \"one sentence, from the numbers\", \"rules\": \"the whole new rules file\"}")
    r = subprocess.run(["claude", "-p", "--output-format", "text", "--model", "sonnet", "--disallowedTools",
                        "Bash,Edit,Write,Read,WebFetch,WebSearch,Glob,Grep,Task,NotebookEdit"],
                       input=ask, capture_output=True, text=True, timeout=900, cwd="/tmp",
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})
    res = json.loads(re.search(r"\{.*\}", r.stdout, re.S).group(0))
    new = res["rules"]
    if "## The template" not in new or len(new) < 0.6 * len(text):
        return print("the proposed rules dropped too much; version", n, "stays")
    fixed = lambda t: t.split("## The template", 1)[1].split("\n## ", 1)[0].strip()   # (the owner's fixed rules: the cover, the acted hook)
    if fixed(new) != fixed(text):
        return print("the proposed rules changed the fixed template section; version", n, "stays")
    new = re.sub(r"^Version: \d+", f"Version: {n + 1}", new, count=1, flags=re.M)
    if f"Version: {n + 1}" not in new: new = new.replace("\n", f"\n\nVersion: {n + 1}\n", 1)
    ch = "; ".join(res.get("changes") or [res.get("change", "")])
    new = new.rstrip("\n") + f"\n- {n + 1} ({time.strftime('%F')}): {ch} ({res['why']})\n"
    with open(HISTORY, "a", encoding="utf-8") as f: f.write(f"- version {n + 1} tries: {ch}\n")
    os.makedirs(os.path.join(LAB, "data", "rules"), exist_ok=True)
    shutil.copy(RULES, os.path.join(LAB, "data", "rules", f"v{n}.md"))
    open(RULES, "w", encoding="utf-8").write(new)
    print(f"version {n + 1}: {ch}")


def demo():
    rows = [{"winner": "v2", "version": 1, "category": "Chart quiz", "v1": {"reels_skip_rate": 70, "ig_reels_avg_watch_time": 5000},
             "v2": {"reels_skip_rate": 60, "ig_reels_avg_watch_time": 7000}}, {"winner": None, "version": 1}]
    s = summary(rows)[1]
    assert s["pairs"] == 1 and s["v2_wins"] == 1 and s["skip_v2"] == 60.0 and s["watch_v1"] == 5.0, s
    assert version("x\nVersion: 3\n") == 3 and version("none") == 1
    print("ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["demo"] else main()
