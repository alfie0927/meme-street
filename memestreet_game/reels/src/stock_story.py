"""Crazy true stock stories and stock explainers (the owner, 2026-11-19: "you can tell crazy stories of crazy stocks etc, to make
people engaged, you can use sometimes the roblox esque animation to display everything. see how that does and if it does well
use it indefinitely"; then "use [open-higgsfield] to make the reels into a UNIQUE style of reels, with stock explainers, crazy
stock stories").

  python3 src/stock_story.py slot <SLOT> story|explainer   auto_reel.sh: this slot's reel, or exit 1 (the slot then gets a game reel)
  python3 src/stock_story.py now story|explainer [2d|3d]   make one and queue it to post at once
  python3 src/stock_story.py decide                        the 2D / 3D trial's verdict from Instagram's numbers (also run by `slot`)
  python3 src/stock_story.py demo                          self-check: no Claude, no network, no spend

A story is one of the famous moments in src/daily_story_charts.json (tools/daily_bank.py: the stock, its day, a seed, the idea
an explainer teaches through it, and its real daily prices), the one out longest ago. The researcher (news_reel.research: three
major outlets, every claim with its status) turns the seed into a fact pack; nothing that pack does not support is said
(news_reel.fact_check, before the voice and after the critic's rewrite).

Two looks, tried against each other on stories (the owner's "see how that does"): "2d", a director reel over the real chart with up
to two cinematic shots from Higgsfield (footage.py; the newer models open-higgsfield lists; the monthly cap in footage.py holds),
and "3d", the story acted out in the serial's toy-block town (world3d.js). They take turns by day until each has MIN_EACH scored
reels; then `decide` keeps the winner (median views at least WIN_BY better, hold not worse by more than HOLD_SLACK points), in
state/story_style.json, for every story from then on. Explainers are always 2d.
"""
import datetime, json, os, re, statistics, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_spec as M
import news_reel as N

BANK = os.path.join(HERE, "daily_story_charts.json")
STYLE_FILE = os.path.join(ROOT, "state", "story_style.json")
LEDGER = os.path.join(ROOT, "state", "reel_ledger.json")
STORY, EXPLAIN, STORY3D = "Crazy stock story", "Stock explainer", "Crazy stock story 3D"
MIN_EACH, WIN_BY, HOLD_SLACK = 5, 1.15, 3.0
SKILLS = (" HOW IT IS BUILT (the virality and ig-reel skills, as this account's rules already apply them): frame 0 is already moving "
          "and shows something a stranger recognises (the wildest candle, the company's world, the number that makes no sense); the "
          "claim builds word by word in the first 1.5 seconds; every line is shown, never only said; one question to the viewer in "
          "the middle (a decision: 'would you have sold here?'), never in the outro; the outro: \"Today's stock is live. Play it at "
          "memestreet.net.\" The caption follows the ig-caption skill: the hook under 125 characters, the story in short lines that "
          "keep each fact's status words, the question, 'Play today's stock at memestreet.net', 'Sources: <outlets>. "
          + M.DISCLAIMER + "', 3 to 5 hashtags.")
FACT_RULES = (" ONLY what facts.news says may be said, shown or put in the caption: every claim, number, date and name comes from it and "
              "keeps its status ('confirmed', 'admitted', or 'reported' said with its outlet: 'Reuters reported'); what is only alleged is "
              "not told. Prices and percentages on screen come from facts.chart (real dollars, closes) or facts.news. Name the company; "
              "name only the people in facts.news.people. No advice on the stock today, no prediction, no view on guilt.")
M.CATEGORIES[STORY] = (
    "NEW, A CRAZY TRUE STOCK STORY (the owner, 2026-11-19): facts.news is the researched story of a real stock and chart 0 is its "
    "real price chart in dollars (facts.chart: the story's day is candle facts.chart.story_candle). Tell it like a thriller: the "
    "hook is the craziest true number or moment, said in the first sentence over the chart's wildest candle (or the opening "
    "cinematic shot); then what happened, in order, one beat a line, each beat shown (the chart revealed up to that day on its "
    "words, a counter racing, your device's characters acting it); the turn; how it ended (the chart's last candles); then one "
    "line linking it to Meme Street's daily game (only what facts.meme_street says)." + FACT_RULES + SKILLS)
M.CATEGORIES[EXPLAIN] = (
    "NEW, A STOCK EXPLAINER (the owner, 2026-11-19): explain facts.idea (for example a short squeeze) through the real story in "
    "facts.news and its real chart (chart 0, dollars; facts.chart). The hook is the idea as a dare or a crazy true number ('This is "
    "how a stock goes up 1,000% in a week'); then how it works in plain words, each step shown on the chart or acted by your "
    "device (one definition sentence at most); the real example proves it, beat by beat; the one sign to watch for; then one line "
    "linking it to Meme Street's daily game (only what facts.meme_street says). Fun and fast, never a lecture." + FACT_RULES + SKILLS)
for _c in (STORY, EXPLAIN):
    M.LENGTH[_c] = (100, 145, True)
    M.KINDS[_c] = []
VIDEO_NOTE = (" CINEMATIC SHOTS (open-higgsfield's models through footage.py): facts.video.available is true, so open on ONE "
              "\"film\" scene (the story's world in one striking moving shot: a trading floor at night, a rocket on a pad, a crowd "
              "with phones lit; no real people, no logos, no text) and use at most one more later; every other scene is your own "
              "animation over the chart.")


def bank():
    return json.load(open(BANK, encoding="utf-8"))["charts"]


def pick(history):
    """The story out longest ago (one list for stories and explainers, so the same story is never both in one day)."""
    B = bank()
    i = M.lru(list(range(len(B))), history, "stock_stories")[0]
    return B[i]


def chart_of(x):
    """The story's chart (real dollars) and what the writer may say of it."""
    C = [list(c) for c in x["c"]]
    k = x["peak"]
    cl = [c[3] for c in C]
    facts = {"stock": x["n"], "ticker": x["t"], "from": x["d"][0], "to": x["d"][1], "story_day": x["day"], "story_candle": k,
             "first_close": cl[0], "close_on_story_day": cl[k], "last_close": cl[-1],
             "highest": {"close": max(cl), "candle": cl.index(max(cl))}, "lowest": {"close": min(cl), "candle": cl.index(min(cl))},
             "pct_first_to_peak": round((max(cl) / cl[0] - 1) * 100, 1), "pct_peak_to_last": round((cl[-1] / max(cl) - 1) * 100, 1),
             "candle_is": "one trading day"}
    ch = {"candles": C, "label": f"{x['n']} ({x['t']})", "upto": len(C) - 1, "end": len(C) - 1, "win": [0, len(C) - 1]}
    return facts, ch


def research(x, kind):
    seed = x["seed"] + (f". Explain {x['idea']} through it." if kind == "explainer" else "")
    pack = N.research(seed)
    errs = N.sound(pack)
    if errs:
        return None, errs
    left = [f["claim"] for f in pack["facts"] if f["status"] == "alleged"]
    return dict(pack, facts=[f for f in pack["facts"] if f["status"] != "alleged"], left_out_as_unproven=left), []


def video_ok():
    import footage
    return bool(footage.cred()) and footage.remaining() >= 2 * footage.cost(5)


# ---------------------------------------------------------------------------------------------------- the 2D / 3D trial
def style_for(slot, kind):
    if kind == "explainer":
        return "2d"
    try:
        w = json.load(open(STYLE_FILE, encoding="utf-8")).get("winner")
    except (OSError, ValueError):
        w = None
    if w in ("2d", "3d"):
        return w
    return "3d" if datetime.date.fromisoformat(slot[:10]).toordinal() % 2 else "2d"


def decide(ledger=None, path=None, now=None):
    """The trial's verdict from the reel ledger (src/learn.py): 2D stories ("Crazy stock story") against 3D ("Crazy stock story
    3D"), on median views and hold. -> the winner, or None while it is still open. Kept in state/story_style.json."""
    path = path or STYLE_FILE
    try:
        L = ledger if ledger is not None else json.load(open(LEDGER, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    rows = [r for r in (L.values() if isinstance(L, dict) else L) if isinstance(r, dict) and r.get("views") is not None]
    g = {s: [r for r in rows if r.get("format") == f] for s, f in (("2d", STORY), ("3d", STORY3D))}
    if min(len(v) for v in g.values()) < MIN_EACH:
        return None
    med = {s: (statistics.median(r["views"] for r in v), statistics.median(r.get("hold") or 0 for r in v)) for s, v in g.items()}
    win = None
    for a, b in (("3d", "2d"), ("2d", "3d")):
        if med[a][0] >= WIN_BY * med[b][0] and med[a][1] >= med[b][1] - HOLD_SLACK:
            win = a
    if win is None and min(len(v) for v in g.values()) >= 2 * MIN_EACH:
        win = max(med, key=lambda s: med[s][0])           # (ten each and still close: the one more people watched)
    if win:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump({"winner": win, "decided": time.strftime("%Y-%m-%d", time.gmtime(now)), "medians": med,
                   "reels": {s: len(v) for s, v in g.items()}}, open(path, "w", encoding="utf-8"), indent=1)
    return win


# ---------------------------------------------------------------------------------------------------- the 3D story
def what_3d():
    import story_reel as S
    w = S.WHAT
    grammar = w[w.index("THE LOOK"):w.index("THE STORY:")]
    return ("A TRUE STOCK STORY IN THE BLOCKY TOWN (the owner, 2026-11-19: 'use sometimes the roblox esque animation to display "
            "everything'): facts.news is the researched story of a real stock and facts.chart its real prices. The town acts it out, "
            "told in the first person by a townsperson who watched it happen. The company is a building or a shop in the town with its "
            "name on a screen; traders are townspeople whose chest numbers show the stock's price or their money as the story moves "
            "(numbers only from facts.chart and facts.news); the big moments are crowds rushing in, a number crashing on a chest, the "
            "sky turning red. " + grammar +
            "THE STORY: every beat of facts.news, in order, one beat a scene, acted by the townspeople; the people in "
            "facts.news.people, and only they, are named, each a townsperson with one trademark feature; facts.story.cast gives the "
            "regulars' colours. Then one line linking it to Meme Street's daily game (only what facts.meme_street says), and the sign-off "
            "'Today's stock is live. Play it at memestreet.net.'" + FACT_RULES + " \"type\" is \"Blocky story\". The caption: the hook "
            "under 125 characters, the story in short lines with each fact's status words, 'Play today's stock at memestreet.net', "
            "'Sources: <outlets>. " + M.DISCLAIMER + "', 3 to 5 hashtags. The voice tells it in flowing sentences of 10 to 20 words, "
            "while the pictures cut every 2 seconds.") % {k: ", ".join(v) for k, v in __import__("world").VOC.items()} \
        if "%(poses)s" in grammar else (
            "A TRUE STOCK STORY IN THE BLOCKY TOWN: " + grammar + " THE STORY: every beat of facts.news, in order." + FACT_RULES)


CAST = {"the narrator (I)": "grey-blue shirt #8a96ab, dark blue trousers #2e3a52, brown hair #6b4426, skin #f1c27d: a small trader who watched it all",
        "a fund manager": "black suit #1f2433, white shirt, slicked black hair #1b1b1b, dark glasses: the big money on the other side",
        "a young trader": "green hoodie #43b05c, cap, phone in hand: the crowd buying in"}


def make_3d(x, pack, slot, post_at):
    """The 3D story: written in the town's grammar, fact-checked, voiced over the serial's tune, reviewed, queued. -> slot or None."""
    import story_reel as S, world as W
    facts_c, _ = chart_of(x)
    at = slot or datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H%M")
    facts = {"news": pack, "chart": facts_c, "story": {"cast": CAST}, "meme_street": M.GAME_FACTS, "example": W.example(),
             "recent_devices": [], "video": {"available": False}, "hook_shots_used_lately": []}
    what = what_3d()
    ask = {"category": S.CATEGORY, "what_this_reel_is": what, "facts": facts, "recent_titles_to_avoid": []}
    B = {"slot": at, "category": S.CATEGORY, "system": M.system_prompt(S.CATEGORY), "ask": ask, "charts": []}
    work, out = os.path.join(ROOT, "work", "auto-" + at), os.path.join(ROOT, "out", "auto-" + at)
    spec = M.write(B, work=work)
    bad = N.fact_check(pack, M.GAME_FACTS, spec)
    if bad:
        N.say("3D story: the fact check sent it back:", "; ".join(bad)[:400])
        draft = json.dumps(spec, indent=1)
        spec = M.write(B, msgs=[{"role": "user", "content": json.dumps(ask, indent=1)}, {"role": "assistant", "content": draft},
                                {"role": "user", "content": "A fact check found these. Fix every one, change nothing else, reply with the whole JSON: " + "; ".join(bad)}], work=work)
        if N.fact_check(pack, M.GAME_FACTS, spec):
            N.say("3D story HELD: the fact check failed twice"); return None
    spec.update({k: v for k, v in S.STYLE.items() if not k.startswith("voice")}, scene_js=W.JS, part=None, series="")   # (the town and its tune; the house voice)
    M.save(spec, B, work)
    json.dump(pack, open(os.path.join(work, "facts.json"), "w", encoding="utf-8"), indent=1)
    r = subprocess.run([sys.executable, os.path.join(HERE, "critic.py"), "loop", work, out], cwd=ROOT,
                       env=dict(os.environ, STEP_TIMEOUT=os.environ.get("STORY_STEP_TIMEOUT", "2700")))
    if r.returncode or not os.path.exists(os.path.join(out, "approved.json")):
        N.say("3D story HELD: the critic did not approve it"); return None
    final = json.load(open(os.path.join(work, "spec.json"), encoding="utf-8"))
    if N.fact_check(pack, M.GAME_FACTS, final):
        N.say("3D story HELD: the fact check failed after the critic's rewrite"); return None
    final["type"] = STORY3D                                # (the ledger tells the two looks apart by this)
    json.dump(final, open(os.path.join(work, "spec.json"), "w", encoding="utf-8"))
    return N.queue_out(out, post_at, pack.get("headline", ""))


# ---------------------------------------------------------------------------------------------------- one reel
def make(kind, slot=None, style=None):
    """One story or explainer: picked, researched, written, checked, made, queued (in `slot`, or to post now). -> slot or None."""
    hist = json.load(open(M.HISTORY)) if os.path.exists(M.HISTORY) else {}
    x = pick(hist)
    json.dump(hist, open(M.HISTORY, "w"))                  # (the pick is kept: a story that fails is not tried again at once)
    style = style or style_for(slot or time.strftime("%Y-%m-%dT%H%M", time.gmtime()), kind)
    N.say(f"{kind} ({style}): {x['n']} {x['day']} - researching")
    pack, errs = research(x, kind)
    if not pack:
        N.say(f"{kind} not made: the research did not stand up: " + "; ".join(errs)[:300]); return None
    if style == "3d":
        return make_3d(x, pack, slot, slot)
    facts_c, ch = chart_of(x)
    video = video_ok()
    cat = STORY if kind == "story" else EXPLAIN
    what = M.CATEGORIES[cat] + (VIDEO_NOTE if video else "")
    extra = {"chart": facts_c, "idea": x["idea"], "charts": [M.chart_summary(0, ch)]}
    return N.make(pack, [x["n"]], slot=slot, category=cat, what=what, charts=[ch], extra=extra, video=video, post_now=not slot)


def demo():
    import tempfile
    B = bank()
    assert len(B) >= 20 and all(len(x["c"]) >= 60 and 0 <= x["peak"] < len(x["c"]) for x in B)
    h = {}
    a, b = pick(h), pick(h)
    assert a["t"] + a["day"] != b["t"] + b["day"] and len(h["stock_stories"]) == 2
    f, ch = chart_of(a)
    assert f["close_on_story_day"] == ch["candles"][a["peak"]][3] and f["highest"]["close"] >= f["last_close"]
    assert style_for("2026-11-20T1300", "explainer") == "2d" and {style_for("2026-11-20T1300", "story"), style_for("2026-11-21T1300", "story")} == {"2d", "3d"}
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "s.json")
        L = {str(k): {"format": STORY, "views": 100, "hold": 50} for k in range(5)}
        assert decide(L, p) is None                        # (no 3D reels yet)
        L.update({f"x{k}": {"format": STORY3D, "views": 200, "hold": 49} for k in range(5)})
        assert decide(L, p) == "3d" and json.load(open(p))["winner"] == "3d"
        L2 = {**{str(k): {"format": STORY, "views": 100, "hold": 60} for k in range(5)}, **{f"x{k}": {"format": STORY3D, "views": 300, "hold": 40} for k in range(5)}}
        assert decide(L2, os.path.join(td, "t.json")) is None   # (more views but a far worse hold: not yet)
    assert "THE LOOK" in what_3d() and "THE STORY:" in what_3d() and "facts.news" in what_3d() and "%(" not in what_3d()
    assert STORY in M.CATEGORIES and EXPLAIN in M.CATEGORIES and M.DISCLAIMER in M.CATEGORIES[STORY]
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:] or ["demo"]
    if a[0] == "demo": demo()
    elif a[0] == "decide": print(decide() or "still open")
    elif a[0] == "slot" and len(a) > 2:
        decide()
        sys.exit(0 if make(a[2], slot=a[1]) else 1)
    elif a[0] == "now" and len(a) > 1:
        print(make(a[1], style=a[2] if len(a) > 2 else None) or "held or not made: see the lines above")
    else: raise SystemExit(__doc__)
