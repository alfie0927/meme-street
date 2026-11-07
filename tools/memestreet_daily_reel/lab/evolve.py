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
    ask = ("You improve the rules for Meme Street's version-2 Instagram Reels by A/B testing. Each pair is the same facts made as "
           "the current reel (v1) and as version 2 (v2), both posted as Trial Reels to non-followers. Lower skip rate (% leaving in "
           "the first 3 s) and longer average watch are better.\n\nScoreboard by version of the rules (skip %, watch seconds):\n"
           + json.dumps(S, indent=1) + f"\n\nThe current rules (version {n}):\n" + text +
           "\n\nChange exactly ONE thing in the rules, the one most likely to cut skips and lengthen watching given these results "
           "(if a past version did better, you may bring back what it had). Do not touch the '## The template' section, and keep "
           "every rule the owner decided. Reply with JSON only: {\"change\": \"one sentence\", \"why\": \"one sentence, from the "
           "numbers\", \"rules\": \"the whole new rules file\"}")
    r = subprocess.run(["claude", "-p", "--output-format", "text", "--model", "sonnet", "--disallowedTools",
                        "Bash,Edit,Write,Read,WebFetch,WebSearch,Glob,Grep,Task,NotebookEdit"],
                       input=ask, capture_output=True, text=True, timeout=900, cwd="/tmp",
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})
    res = json.loads(re.search(r"\{.*\}", r.stdout, re.S).group(0))
    new = res["rules"]
    if "## The template" not in new or len(new) < 0.6 * len(text):
        return print("the proposed rules dropped too much; version", n, "stays")
    new = re.sub(r"^Version: \d+", f"Version: {n + 1}", new, count=1, flags=re.M)
    if f"Version: {n + 1}" not in new: new = new.replace("\n", f"\n\nVersion: {n + 1}\n", 1)
    new = new.rstrip("\n") + f"\n- {n + 1} ({time.strftime('%F')}): {res['change']} ({res['why']})\n"
    os.makedirs(os.path.join(LAB, "data", "rules"), exist_ok=True)
    shutil.copy(RULES, os.path.join(LAB, "data", "rules", f"v{n}.md"))
    open(RULES, "w", encoding="utf-8").write(new)
    print(f"version {n + 1}: {res['change']}")


def demo():
    rows = [{"winner": "v2", "version": 1, "category": "Chart quiz", "v1": {"reels_skip_rate": 70, "ig_reels_avg_watch_time": 5000},
             "v2": {"reels_skip_rate": 60, "ig_reels_avg_watch_time": 7000}}, {"winner": None, "version": 1}]
    s = summary(rows)[1]
    assert s["pairs"] == 1 and s["v2_wins"] == 1 and s["skip_v2"] == 60.0 and s["watch_v1"] == 5.0, s
    assert version("x\nVersion: 3\n") == 3 and version("none") == 1
    print("ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["demo"] else main()
