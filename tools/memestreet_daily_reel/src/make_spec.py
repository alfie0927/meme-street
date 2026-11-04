"""Write one auto reel's script: the facts come from the game, the words from Claude, and both are checked.

  python3 src/make_spec.py <slot YYYY-MM-DDTHHMM> <work dir> [--category NAME] [--remake <november folder entry json>]

Facts are never invented: a quiz uses real game charts with the answer the chart actually gave (/api/learn/test), a
stock story uses a real game company and its real chart (/api/reel/stock), a lesson uses a real chart that shows the
idea. Claude writes the narration, the on-screen words, the hook and the caption around those facts, in the voice in
voice.md, and the result is checked (hook score, length, words per line, no emoji, the disclaimer) and sent back to
Claude to fix at most twice. Output: <work>/spec.json and <work>/caption.txt.
"""
import json, os, random, re, sys, time, urllib.error, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "ig"))
import hookscore

SITE = os.environ.get("MS_BASE_LOCAL", "http://127.0.0.1:8000")
MODEL = os.environ.get("REEL_MODEL", "claude-sonnet-5-5")
DISCLAIMER = "Fictional market. Not investment advice."
HISTORY = os.path.join(ROOT, "state", "auto_history.json")
PACK = os.environ.get("CONTENT_PACK", "/opt/memestreet/content/pack_fiction.json")

CATEGORIES = {
    "Chart quiz": "Three questions on three real game charts. Each: a question scene (options shown, a short countdown), "
                  "then an answer scene (the rest of the chart plays out, the right option lights up, one or two lines on why).",
    "Stock story": "Introduce one fictional company from the game: the hook, what it does, how it makes money, what moves "
                   "its stock (good news and bad news), its real recent chart, and an invitation to trade it.",
    "Technical lesson": "Teach one chart idea (an indicator, a level, a pattern) on a real chart that shows it: what it is, "
                        "how to read it, the trap, and the one rule to remember.",
    "Trading mistake": "One common beginner mistake, shown on a real chart: what people do, what it costs, what to do instead.",
    "Guess the move": "A viral, interactive reel: a real chart stops at a big moment, the viewer guesses what came next "
                      "(a short countdown), then the reveal and why. One or two charts.",
    "Myth or fact": "A viral reel: three common trading beliefs, each called myth or fact with one line of why, ending on "
                    "the most surprising one. Cards and big text, one real chart to prove the last point.",
}
ROTATION = {"0600": ["Technical lesson", "Trading mistake"], "1200": ["Chart quiz"], "1800": ["Stock story", "Guess the move"],
            "2100": ["Guess the move", "Myth or fact"], "0900": ["Myth or fact"], "1300": ["Guess the move"]}
KINDS = {"Chart quiz": ["pattern", "candle", "breakout", "level", "trend", "stop", "rr", "fib"],
         "Technical lesson": ["rsi", "ma", "fib", "level", "pattern", "breakout", "candle", "trend"],
         "Trading mistake": ["stop", "rr", "breakout", "level", "next"],
         "Guess the move": ["breakout", "level", "next", "pattern"], "Myth or fact": ["next", "breakout", "level"]}


def get(path):
    for attempt in range(5):
        time.sleep(0.5 + attempt)                         # (the game's per-address limit on these)
        try:
            with urllib.request.urlopen(SITE + path, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4: raise


def drill(kind):
    d = get(f"/api/learn/test?kind={kind}&example=1")
    if "candles" not in d:
        raise RuntimeError(f"no chart test for {kind}: {d}")
    return d


def swings(C, a, b, k=4):
    """The clearest highs and lows between candles a and b (index, price), for Claude to point at."""
    out = []
    for i in range(max(a, k), min(b, len(C) - k)):
        if C[i][1] == max(c[1] for c in C[i - k:i + k + 1]): out.append(["high", i, round(C[i][1], 2)])
        if C[i][2] == min(c[2] for c in C[i - k:i + k + 1]): out.append(["low", i, round(C[i][2], 2)])
    return out[-10:]


def chart_from_drill(d):
    up, C = d["upto"], d["candles"]
    end = min(len(C) - 1, up + 25)
    return {"candles": C, "label": f"{d['where']['name']} · {d['where']['tf']}", "upto": up, "end": end,
            "win": [max(0, up - 70), end], "drill": d}


def chart_summary(i, ch):
    d, C = ch.get("drill"), ch["candles"]
    s = {"chart": i, "candles": len(C), "label": ch["label"], "first_shown": ch["win"][0], "last": ch["end"],
         "swings": swings(C, ch["win"][0], ch["end"] + 1), "close_first": round(C[ch["win"][0]][3], 2),
         "close_last": round(C[ch["end"]][3], 2)}
    if d:
        s.update(question=d["q"], options=d["options"], right_answer=d["options"][d["answer"]], stops_at=d["upto"],
                 what_happened=d["result"], why=d["explain"], drawn_with_answer=[x["label"] for x in d["lines"] if x.get("label")])
    return s


def gather(category, rng, history):
    """The facts for this reel, and the charts the renderer draws."""
    facts, charts = {}, []
    if category == "Stock story":
        pack = json.load(open(PACK)) if os.path.exists(PACK) else {"companies": [], "templates": []}
        done = set(history.get("tickers", [])[-30:])
        cos = [c for c in pack["companies"] if c["ticker"] not in done] or pack["companies"]
        co = rng.choice(cos)
        st = get(f"/api/reel/stock/{co['ticker']}?tf=1h")
        news = [t for t in pack["templates"] if t.get("sector") == co["sector"]][:2]
        facts = {"company": st["name"], "ticker": st["ticker"], "what_it_does": st["desc"], "sector": co["sector"],
                 "price_now": round(st["price"], 2), "good_news_examples": sum((t["up"] for t in news), [])[:3],
                 "bad_news_examples": sum((t["down"] for t in news), [])[:3]}
        C = st["candles"]
        charts.append({"candles": C, "label": f"{st['name']} ({st['ticker']}) · {st['tf']}", "upto": len(C) - 1,
                       "end": len(C) - 1, "win": [0, len(C) - 1]})
        history.setdefault("tickers", []).append(co["ticker"])
    else:
        kinds = KINDS[category][:]; rng.shuffle(kinds)
        for k in kinds[:3 if category == "Chart quiz" else (2 if category == "Guess the move" else 1)]:
            charts.append(chart_from_drill(drill(k)))
    facts["charts"] = [chart_summary(i, c) for i, c in enumerate(charts)]
    return facts, charts


SCHEMA = """Reply with JSON only, no prose, in this shape:
{"title": "cover title, 2 to 5 words", "type": "%s",
 "hooks": ["three different spoken hook lines, best first"],
 "scenes": [ ...in order... ],
 "caption": "the Instagram caption"}
Scene kinds (each has "vo": the spoken line, plain words, max 26 words, contractions welcome):
 {"kind":"hook","vo":"the first hook line","text":"on-screen hook, max 6 words","chart":N or null}
 {"kind":"chart","chart":N,"head":"on-screen title, max 5 words","vo":"...","show":candle index shown at the start (optional),
   "cues":[{"say":"exact phrase from vo","do":"reveal","to":index} | {"say":"..","do":"mark","i":index,"label":"A","side":"high"|"low","tone":"amber|green|red|teal"}
          | {"say":"..","do":"line","price":number,"label":"max 3 words","tone":"amber|green|red|teal"} | {"say":"..","do":"shade","from":index,"to":index,"tone":"green|red|amber"}
          | {"say":"..","do":"zoom","from":index,"to":index}]}
 {"kind":"question","chart":N,"badge":"Q1","head":"max 5 words","vo":"asks it and reads the options"}   (options and answer are added from the facts)
 {"kind":"answer","chart":N,"head":"the right answer, max 5 words","vo":"says the answer first, then why, max 26 words","cues":[...]}
 {"kind":"cards","head":"max 5 words","vo":"...","items":[{"text":"max 4 words","sub":"max 7 words","icon":"up|down|warn|check|cross|coin|clock|bolt|chart|shield|people|idea"}],
   "cues":[{"say":"exact phrase","do":"item","i":0}, ...one per item]}
 {"kind":"big","text":"max 7 words, shown huge","vo":"..."}
 {"kind":"outro","text":"max 6 words","vo":"one ask, ending with memestreet.net"}
"""

RULES = """Rules:
- Total spoken words 75 to 140 (about 25 to 50 seconds). No greeting, no "in this video". Start at the hook.
- The first scene is a hook; the last is the outro. Change what is on screen every scene.
- Every number, name and outcome must come from the facts. Never invent results, prices, people or history.
- Candle indices in cues must be between a chart's first_shown and last. "say" must be words that appear in that scene's vo.
- The caption: first line is a hook that survives the "... more" cut (under 125 characters), then 2 to 5 short lines,
  one ask (comment, save or follow), "Practise at memestreet.net", then exactly "Fictional market. Not investment advice.",
  then 3 to 5 hashtags including #MemeStreet. No emoji anywhere. British spelling.
- Sound like the voice profile: calm, clear, short sentences, never hype.
"""


def claude(messages, system):
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is not set (run set_claude_key.ps1)")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST",
                                 data=json.dumps({"model": MODEL, "max_tokens": 6000, "system": system, "messages": messages}).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return "".join(b.get("text", "") for b in json.loads(r.read())["content"])


EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")


def check(spec, facts, charts):
    """What is wrong with the script, in words Claude can fix."""
    errs = []
    sc = spec.get("scenes") or []
    if not sc or sc[0].get("kind") != "hook": errs.append("the first scene must be a hook")
    if not sc or sc[-1].get("kind") != "outro": errs.append("the last scene must be an outro")
    words = sum(len(s.get("vo", "").split()) for s in sc)
    if not 75 <= words <= 140: errs.append(f"the narration is {words} words; it must be 75 to 140")
    for k, s in enumerate(sc):
        if len(s.get("vo", "").split()) > 30: errs.append(f"scene {k}'s line is too long ({len(s['vo'].split())} words, max 26)")
        ch = s.get("chart")
        if ch is not None and not (isinstance(ch, int) and 0 <= ch < len(charts)): errs.append(f"scene {k} uses chart {ch}, which does not exist")
        for c in s.get("cues", []):
            if c.get("say") and c["say"].lower() not in s.get("vo", "").lower(): errs.append(f"scene {k}: cue phrase {c['say']!r} is not in its line")
            for f in ("to", "i", "from"):
                if f in c and isinstance(ch, int) and 0 <= ch < len(charts) and not 0 <= c[f] < len(charts[ch]["candles"]):
                    errs.append(f"scene {k}: candle {c[f]} is outside chart {ch}")
    hs = [h for h in spec.get("hooks", []) if isinstance(h, str)]
    if hs:
        best = max(hs, key=lambda h: hookscore.run(h)[1])
        score = hookscore.run(best)[1]
        if score < 50: errs.append(f"the best hook scores {score:.0f}/100 (needs 50+): make it shorter, concrete and with something at stake")
        if sc and sc[0].get("kind") == "hook": sc[0]["vo"] = best if sc[0].get("vo") in hs else sc[0]["vo"]
    cap = spec.get("caption", "")
    if DISCLAIMER not in cap: errs.append(f"the caption must contain exactly: {DISCLAIMER}")
    if EMOJI.search(cap + json.dumps(sc)): errs.append("no emoji anywhere")
    if "#MemeStreet" not in cap: errs.append("the caption needs #MemeStreet")
    return errs


def finish(spec, charts, category):
    """Add what comes from the facts, not from Claude: the options and answers, the answer's lines, the windows."""
    for s in spec["scenes"]:
        ch = charts[s["chart"]] if isinstance(s.get("chart"), int) else None
        if not ch:
            s["chart"] = None; continue
        s.setdefault("win", ch["win"])
        d = ch.get("drill")
        if s["kind"] == "question" and d:
            s["options"], s["answer"], s["show"] = d["options"], d["answer"], ch["upto"]
            s["win"] = [ch["win"][0], ch["end"]]
            s.setdefault("cues", []).append({"say": "", "do": "options"})
        elif s["kind"] == "answer" and d:
            s["reveal_to"], s["carry"] = ch["end"], True
            s.setdefault("cues", [])
            s["cues"] += [{"say": "", "do": "line", "price": x["price"], "label": x.get("label", "")[:22], "tone": x.get("tone", "level")}
                          for x in d["lines"]][:3]
            s["cues"] += [{"say": "", "do": "mark", "i": m["i"], "label": m.get("label", "")[:2], "side": "high"} for m in d["marks"] if m.get("label")][:3]
        elif s["kind"] in ("hook", "chart") and s.get("show") is None and d:
            s["show"] = ch["upto"]
    spec["type"] = category
    spec["charts"] = [{"candles": c["candles"], "label": c["label"]} for c in charts]
    return spec


def main(slot, work, category=None, remake=None):
    rng = random.Random(slot)
    history = json.load(open(HISTORY)) if os.path.exists(HISTORY) else {}
    if remake:
        category = {"Chart quiz": "Chart quiz", "Stock story": "Stock story", "Technicals": "Technical lesson",
                    "New-trader challenge": "Trading mistake"}.get(remake.get("type"), "Technical lesson")
    category = category or rng.choice(ROTATION.get(slot[-4:], ["Technical lesson"]))
    facts, charts = gather(category, rng, history)
    voice = open(os.path.join(ROOT, "voice.md"), encoding="utf-8").read()      # (a copy of ~/.claude/instagram/voice.md)
    hooks = json.load(open(os.path.join(HERE, "ig", "hooks.json")))["hooks"]
    system = ("You write Instagram Reels for Meme Street, a free stock market game with fictional companies "
              "(memestreet.net). Voice profile:\n" + voice + "\n\nHook formulas you may use:\n" +
              "\n".join(f"- {h['name']}: {h['template']}" for h in hooks) + "\n\n" + RULES + "\n" + SCHEMA % category)
    ask = {"category": category, "what_this_reel_is": CATEGORIES[category], "facts": facts,
           "recent_titles_to_avoid": history.get("titles", [])[-20:]}
    if remake:
        ask["remake_of"] = {"note": "Make this reel again on the same topic, with the same teaching points and similar "
                                    "explanations, but tighter: no long pauses, every line earns its place. Use the new "
                                    "charts in the facts instead of the old ones.",
                            "title": remake.get("title"), "old_narration": remake.get("narration"), "old_caption": remake.get("caption")}
    msgs = [{"role": "user", "content": json.dumps(ask, indent=1)}]
    for attempt in range(3):
        raw = claude(msgs, system)
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            spec = json.loads(m.group(0)) if m else {}
        except ValueError as e:
            spec, errs = {}, [f"not valid JSON: {e}"]
        else:
            errs = check(spec, facts, charts)
        if not errs:
            break
        print(f"attempt {attempt + 1}: " + "; ".join(errs[:8]))
        msgs += [{"role": "assistant", "content": raw}, {"role": "user", "content": "Fix these and reply with the whole JSON again: " + "; ".join(errs)}]
    else:
        raise SystemExit("the script did not pass its checks: " + "; ".join(errs))
    spec = finish(spec, charts, category)
    os.makedirs(work, exist_ok=True)
    json.dump(spec, open(os.path.join(work, "spec.json"), "w"))
    open(os.path.join(work, "caption.txt"), "w").write(spec["caption"].strip() + "\n")
    history.setdefault("titles", []).append(spec["title"])
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    json.dump(history, open(HISTORY, "w"))
    print(f"{category}: {spec['title']} ({sum(len(s['vo'].split()) for s in spec['scenes'])} words, {len(spec['scenes'])} scenes)")


if __name__ == "__main__":
    a = sys.argv[1:]
    cat = a[a.index("--category") + 1] if "--category" in a else None
    rem = json.load(open(a[a.index("--remake") + 1])) if "--remake" in a else None
    main(a[0], a[1], cat, rem)
