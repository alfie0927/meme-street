"""Write one auto reel's script: the facts come from the game, the words from Claude, and both are checked.

  python3 src/make_spec.py <slot YYYY-MM-DDTHHMM> <work dir> [--category NAME] [--remake <november folder entry json>]

Facts are never invented: a quiz uses real game charts with the answer the chart actually gave (/api/learn/test), a
stock story uses a real game company and its real chart (/api/reel/stock), a lesson uses a real chart that shows the
idea. Claude writes the narration, the on-screen words, the hook and the caption around those facts, in the voice in
voice.md, and the result is checked (hook score, length, words per line, no emoji, the disclaimer) and sent back to
Claude to fix at most twice. Output: <work>/spec.json and <work>/caption.txt.
"""
import json, os, random, re, subprocess, sys, time, urllib.error, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "ig"))
import hookscore, detect
from pronounce import LEX

SITE = os.environ.get("MS_BASE_LOCAL", "http://127.0.0.1:8000")
MODEL = os.environ.get("REEL_MODEL", "claude-sonnet-5-5")
DISCLAIMER = "Fictional market. Not investment advice."
HISTORY = os.path.join(ROOT, "state", "auto_history.json")
PACK = os.environ.get("CONTENT_PACK", "/opt/memestreet/content/pack_fiction.json")

CATEGORIES = {
    "Chart quiz": "Three questions on three real game charts. Each: a question scene (options shown, a short countdown), "
                  "then an answer scene (the rest of the chart plays out, the right option lights up, one or two lines on why).",
    "Stock story": "Introduce one fictional company from the game: the hook, what it does, how it makes money, what moves "
                   "its stock (good news and bad news), its real recent chart, and an invitation to trade it. Show what "
                   "the company does as an animated \"scene\" (its business acted out: dragons flying over the ranch, "
                   "metal pouring from a furnace), and act out its good and bad news the same way where you can.",
    "Technical lesson": "Teach one chart idea (an indicator, a level, a pattern) on a real chart that shows it: what it is, "
                        "how to read it, the trap, and the one rule to remember.",
    "Trading mistake": "One common beginner mistake, shown on a real chart: what people do, what it costs, what to do instead.",
    "Guess the move": "A viral, interactive reel: a real chart stops at a big moment, the viewer guesses what came next "
                      "(a short countdown), then the reveal and why. One or two charts.",
    "Myth or fact": "A viral reel: three common trading beliefs, each called myth or fact with one line of why, ending on "
                    "the most surprising one. Cards and big text, one real chart to prove the last point.",
    "Daily recap": "Tonight's Daily Chart recap, the same chart every player had today: what the stock did, the realistic "
                   "trades a careful reader could have taken (only those in the facts, at their candles), today's best "
                   "player's return, and the invitation to play tomorrow's chart. Charts scenes with reveal cues through "
                   "the day, marks at the trade candles, a cards scene for the scorecard. The outro ends: \"Tomorrow's "
                   "Daily Chart drops at midnight. Beat it at memestreet.net.\" When the facts say plan_beat_holding is false, "
                   "say briefly in the first or second scene that just buying at the open and holding did better today.",
    # the viral formats from the research of 2026-11-04 (swipe.md: 169 shorts and TikToks, 11 accounts, ranked by how far
    # each beat its own account's median). The formula is copied, never a script.
    "Chart twist": "VIRAL (top format, 37x its account's median): a real chart that looks one way ('it still looked bearish'), "
                   "then the candles tell a different story. Hook names what it looked like; the middle builds the case "
                   "for it; the turn ('but then...') reveals what the chart really did and the clue that showed it early.",
    "One trick": "VIRAL (43x): one concrete, actionable rule shown on a real chart, said as an instruction in the first "
                 "line ('Don't buy the breakout. Put an order at the retest.'). Then the chart proves it, then the one-line rule again.",
    "Big players": "VIRAL (11x): how a move traps beginners: the push past a level that grabs everyone's stops, then the "
                   "reversal. Calm, not conspiratorial: 'this is where the stops sat, this is what price did to them'.",
    # stick figures (research 2026-11-05: 632 videos from 19 stick-figure and animated finance accounts)
    "Trader levels": "VIRAL STICK FIGURES (538x its account's median): 'Your life at every level of a trader'. Four or five "
                     "levels, each a stick scene (head 'Level 1'...) with Rookie or Pro acting it out with a pose and a short "
                     "bubble, from the gambler who buys whatever went up to the one who sets the stop first. Every level "
                     "that mentions candles or price stands beside the real chart and acts out what that chart did. Funny, true, kind.",
    "Explained like you're 5": "VIRAL STICK FIGURES (548x and 165x): one market idea explained like you're five by stick "
                               "figures acting it out (a shop, a queue, a seesaw), then the same idea on the real chart. "
                               "Big simple words; the stick figure is the teacher.",
    "Stick skit": "VIRAL STICK FIGURES (75x on TikTok): a 20 to 30 second skit with two stick figures and one punchline, "
                  "about a real beginner habit (buying the top, selling the bottom, ignoring the stop), played out on the "
                  "real chart. The last beat lands the lesson in one line.",
    # from accounts like the owner's examples (research 2026-11-05: 479 videos, 16 trading short-form accounts)
    "Truth list": "VIRAL LOOP (261x its account's median): a 6 to 10 second reel made to be replayed while the caption is "
                  "read. Scenes: a hook (on-screen text, max 6 words, like 'Trading truths nobody tells you') over a real "
                  "chart moving, then one big scene, no outro. The spoken line is the hook and 'read the caption'. The "
                  "caption carries the value: 7 to 12 numbered, original, plain trading truths (risk, stops, patience, "
                  "overtrading, revenge trading), one line each, then the usual ending.",
    "Hard truth": "VIRAL (6 to 10x): one hard truth about trading psychology in 10 to 20 seconds, shown on the real chart "
                  "moment that proves it (for example one loss, then the urge to win it back). One stick figure may act it "
                  "out. Short lines, a pause-free build, the truth said plainly in the last scene before a short outro.",
    "Speed cheat sheet": "VIRAL (14x): rapid fire, three candles or patterns in under 30 seconds, each named, shown on a "
                         "real chart, and given one line on what it means. The hook promises the speed.",
}
ROTATION = {"0600": ["Technical lesson", "Trading mistake"], "1200": ["Chart quiz"], "1800": ["Stock story", "Guess the move"],
            "2100": ["Chart twist", "One trick", "Big players", "Speed cheat sheet", "Guess the move"],
            "0300": ["Chart twist", "One trick", "Big players", "Speed cheat sheet", "Myth or fact"]}
ROTATION["0900"] = ["Hard truth"]
ROTATION["1300"] = ["Truth list"]
ROTATION["2100"] += ["Trader levels", "Explained like you're 5", "Stick skit"]
ROTATION["0300"] += ["Trader levels", "Explained like you're 5", "Stick skit"]
KINDS = {"Chart quiz": ["pattern", "candle", "breakout", "level", "trend", "stop", "rr", "fib"],
         "Technical lesson": ["rsi", "ma", "fib", "level", "pattern", "breakout", "candle", "trend"],
         "Trading mistake": ["stop", "rr", "breakout", "level", "next"],
         "Guess the move": ["breakout", "level", "next", "pattern"], "Myth or fact": ["next", "breakout", "level"],
         "Chart twist": ["breakout", "pattern", "level", "next"], "One trick": ["breakout", "stop", "level", "rr"],
         "Big players": ["breakout", "level"], "Speed cheat sheet": ["candle", "pattern", "trend"],
         "Trader levels": ["breakout", "level", "stop"], "Explained like you're 5": ["trend", "level", "candle", "rr"],
         "Stick skit": ["breakout", "level", "next"], "Truth list": ["trend", "breakout", "level"],
         "Hard truth": ["stop", "next", "breakout", "level"]}
LENGTH = {"Truth list": (8, 30, False), "Hard truth": (25, 60, True)}     # spoken words min, max, and whether it ends on the outro
VIRAL_EVIDENCE = [
    ["37x", "It still looked bearish... but the candles told a different story."],
    ["6x", "It looked bullish, until the second test changed everything."],
    ["43x", "Don't buy it, but put an order in."],
    ["7x", "This one candle can predict where price is going."],
    ["11x", "The big players can move price, but they leave a footprint."],
    ["14x", "Candlestick patterns explained in less than a minute."],
    ["0.2x (what flops)", "Here are my top three chart settings."], ["0.2x (what flops)", "Markets went crazy today, here's why."]]
STICK_EVIDENCE = [
    ["538x", "Your life at every level of a day trader."], ["548x", "Stocks explained for those who want to be rich."],
    ["165x", "Stock market terms explained, for beginners."], ["152x", "How to actually quit it, explained by a stick figure."],
    ["75x", "Bro forgot his job. (a 15-second stick-figure skit)"], ["80x", "Every scam tactic explained in eight minutes."]]
SHORT_EVIDENCE = [
    ["261x", "15 trading truths you need to hear. (6-second loop, the list in the caption)"],
    ["68x", "'More trades = more money' and other beliefs that cost traders. (6-second loop)"],
    ["10x", "The harsh reality of trading."], ["2x on a small account", "One loss. That's all it takes for emotion to grab the wheel."]]
CHART_COUNT = {"Chart quiz": 3, "Guess the move": 2, "Speed cheat sheet": 3}


def get(path, body=None):
    for attempt in range(5):
        time.sleep(0.5 + attempt)                         # (the game's per-address limit on these)
        try:
            req = urllib.request.Request(SITE + path, data=json.dumps(body).encode() if body else None,
                                         headers={"content-type": "application/json"}, method="POST" if body else "GET")
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4: raise


def drill(kind):
    """A fresh chart test of `kind` with its answer: the question, then the game's marking of it (the candles that came
    next, the right answer and why). A new real chart every time, unlike a lesson's example."""
    q = get(f"/api/learn/test?kind={kind}")
    if "candles" not in q:
        raise RuntimeError(f"no chart test for {kind}: {q}")
    a = get("/api/learn/test", {"id": q["id"], "choice": 0})
    return dict(q, upto=len(q["candles"]) - 1, candles=q["candles"] + a["candles"], lines=a["lines"], marks=a["marks"],
                answer=a["answer"], result=a["result"], explain=a["explain"], where=a["where"])


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
    if re.search(r"fake|back inside|fail", d["result"], re.I) and d["lines"]:
        # a fake or failed move: the reveal stops just after the close back across the level, so the payoff shows the
        # failure (25 candles on, the price can be anywhere, e.g. +40% after a "fake" breakout)
        lv = d["lines"][0]["price"]; side = C[up][3] > lv
        back = next((k for k in range(up + 1, end + 1) if (C[k][3] > lv) != side), None)
        if back is not None: end = min(end, max(up + 6, back + 3))
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
        up, e = d["upto"], ch["end"]; c0 = C[up][3]; after = C[up + 1:e + 1]
        s["after_the_question"] = {                       # what the answer scene really shows: the script may say only this
            "note": "The candles revealed after the question, as numbers. Say only what these show; if what_happened seems to "
                    "say more, these numbers win.",
            "close_at_question": round(c0, 2),
            "closes_after": [[up + j + 1, round(c[3], 2)] for j, c in enumerate(after)][::max(1, len(after) // 8)],
            "pct_to_last": round((C[e][3] / c0 - 1) * 100, 1),
            "highest_after": round(max(c[1] for c in after), 2) if after else None,
            "lowest_after": round(min(c[2] for c in after), 2) if after else None,
            "levels": [{"label": x.get("label", ""), "price": round(x["price"], 2),
                        "closes_above": sum(c[3] > x["price"] for c in after), "closes_below": sum(c[3] < x["price"] for c in after)}
                       for x in d["lines"]]}
    return s


def gather(category, rng, history, company=None):
    """The facts for this reel, and the charts the renderer draws. `company`: a remake's company, by name."""
    facts, charts = {}, []
    if category == "Daily recap":                          # tonight's chart and its analysis (analyze.py), from fetch.py's file
        import analyze
        d = json.load(open(os.environ["DAILY_DATA"], encoding="utf-8"))
        A = analyze.analyse(d, os.environ.get("MS_USER", ""))
        C, H = A["C"], A["H"]
        facts = {"chart_number": A["number"], "stock_change_pct": round(A["hold"] * 100, 2), "clock_starts_at_candle": H,
                 "trades": [{"dir": t["dir"], "entry_candle": t["entry"], "exit_candle": t["exit"], "return_pct": round(t["r"] * 100, 2),
                             "why": f"{t['ev']['outcome']} at {t['ev']['price']}"} for t in A["trades"]],
                 "plan_total_pct": round(A["total"] * 100, 2), "plan_beat_holding": bool(A["total"] >= A["hold"]),
                 "best_player_pct": None if A["best_player"] is None else round(A["best_player"] * 100, 2),
                 "players": A["players"]}
        charts.append({"candles": C, "label": f"Daily Chart #{A['number']}", "upto": len(C) - 1, "end": len(C) - 1, "win": [0, len(C) - 1]})
        facts["charts"] = [chart_summary(0, charts[0])]
        return facts, charts
    if category == "Stock story":
        pack = json.load(open(PACK, encoding="utf-8")) if os.path.exists(PACK) else {"companies": [], "templates": []}
        if company:                                      # (the same company as the reel it remakes, or no remake)
            want = company.lower()
            cos = [c for c in pack["companies"] if c["name"].lower() == want or c["name"].lower().startswith(want + " ")]
            if not cos:
                raise SystemExit(f"no game company called {company!r}: the original reel stays")
        else:
            done = set(history.get("tickers", [])[-30:])
            cos = [c for c in pack["companies"] if c["ticker"] not in done] or pack["companies"]
        rng.shuffle(cos)
        for co in cos[:8]:                               # (the content pack has companies the live game may not list)
            try:
                st = get(f"/api/reel/stock/{co['ticker']}?tf=1h"); break
            except urllib.error.HTTPError as e:
                if e.code != 404: raise
        else:
            raise SystemExit("no listed company found: the original reel stays")
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
        for k in kinds[:CHART_COUNT.get(category, 1)]:
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
   "cues":[{"say":"exact phrase from vo","do":"reveal","to":index} | {"say":"..","do":"mark","i":index,"label":"max 12 characters","side":"high"|"low"|"vol" (vol: rings that candle's volume bar against the 20-candle average),"tone":"amber|green|red|teal"}
          | {"say":"..","do":"line","price":number,"label":"max 3 words","tone":"amber|green|red|teal"} | {"say":"..","do":"shade","from":index,"to":index,"tone":"green|red|amber"}
          | {"say":"..","do":"zoom","from":index,"to":index}]}
 {"kind":"question","chart":N,"badge":"Q1","head":"max 5 words","vo":"asks it and reads the options"}   (options and answer are added from the facts)
 {"kind":"answer","chart":N,"head":"the right answer, max 5 words","vo":"says the answer first, then why, max 26 words","cues":[...]}
 {"kind":"cards","head":"max 5 words","vo":"...","items":[{"text":"max 4 words","sub":"max 7 words","icon":"up|down|warn|check|cross|coin|clock|bolt|chart|shield|people|idea"}],
   "cues":[{"say":"exact phrase","do":"item","i":0}, ...one per item]}
 {"kind":"big","text":"max 7 words, shown huge","vo":"..."}
 {"kind":"stick","head":"max 5 words","vo":"...","chart":N or null (with a chart: one presenter figure beside it),
   "figures":[{"pose":"stand|think|panic|happy|point|pointl|sad|shrug|walk","label":"max 2 words","color":"white|teal|amber"}] (1 to 3 figures; none with a chart beyond the first),
   "cues":[{"say":"exact phrase","do":"pose","fig":0,"pose":"panic"} | {"say":"..","do":"bubble","fig":0,"text":"max 5 words"} | chart cues as above]}
 {"kind":"scene","head":"max 5 words","vo":"...","set":"farm|city|factory|lab|sea|sky|mine|shop|night|desert",
   "sprites":[{"e":"one emoji","x":0-100 (left to right),"y":0-100 (0 high in the sky, 100 standing on the ground),
               "size":"s|m|l","move":"fly|walk|bob|pulse|shake|drop|spin|float|still","to":[x,y] (optional: travels there
               during the scene),"flip":true (optional: mirrors it to face right),"say":"exact phrase from vo: it pops in then"}]}
   (3 to 8 sprites: an animated picture that acts out what the line says, e.g. a dragon-rental company: a farm set,
    🐉 flying from left to right, 🏠 the barn, 🌳 trees, 🧑‍🌾 the rancher; a sick herd: 🤒 bobbing over the dragons)
 {"kind":"outro","text":"max 6 words","vo":"one ask, ending with memestreet.net"}
"""

RULES = """Rules:
- Total spoken words 75 to 140 (about 25 to 50 seconds), unless the reel's description says otherwise. No greeting, no "in this video". Start at the hook.
- The first scene is a hook; the last is the outro. Change what is on screen every scene.
- Every number, name and outcome must come from the facts. Never invent results, prices, people or history.
- Candle indices in cues must be between a chart's first_shown and last. "say" must be words that appear in that scene's vo.
- Show what you say: a scene that talks about candles, the chart, a breakout, volume or wicks has that chart on screen
  (stick scenes too: give them the chart). Talking about volume? Mark the candle with side "vol".
- A mark, shade or zoom only points at candles already on screen at that moment: at or before the scene's "show"
  (or where the scene before it on the same chart ended), or revealed earlier in the same scene.
- On-screen text (hook text, big text, outro text) is words of that scene's line, word for word, in order.
- A figure's label is its name ("Rookie", "Pro") or role, never a copy of the scene's head.
- The caption: first line is a hook that survives the "... more" cut (under 125 characters), then 2 to 5 short lines,
  one ask (comment, save or follow), "Practise at memestreet.net", then exactly "Fictional market. Not investment advice.",
  then 3 to 5 hashtags including #MemeStreet. No emoji anywhere. British spelling.
- Talk the way the best finance narrators do (measured on 16 top Shorts): full, flowing sentences of 10 to 20 words,
  joined the way people join them ("so", "and", "but", "because", "which means", "now"), pointing at the chart with
  "here" and "right here". One short punchy fragment ("But then, crash.") at most once in a reel; never stack
  fragments ("Clean. Strong." / "Calm. Boring. Lovely." read like an advert, not a person).
- Sound like a person talking to ONE viewer: "you", contractions, short punchy lines, one surprising real number,
  a question to the viewer now and then. Never read a list aloud. No stiff phrases ("in today's video", "let's dive in",
  "it's important to note", "in conclusion", "delve"). Calm, clear, never hype.
- Write prices the way people say them ("about two ten", "a hundred and twelve"), never with decimals in the spoken line.
- Stick scenes use the two recurring characters: label "Rookie" (white) for the beginner and "Pro" (teal) for the one
  who knows. Same names in every reel.
- The last line echoes a word from the hook, so the replay loops cleanly, and the outro always ends with:
  "Today's Daily Chart is live. Beat it at memestreet.net."
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


def check(spec, facts, charts, category=None):
    """What is wrong with the script, in words Claude can fix."""
    errs = []
    sc = spec.get("scenes") or []
    if not sc or sc[0].get("kind") != "hook": errs.append("the first scene must be a hook")
    lo_w, hi_w, outro = LENGTH.get(category or spec.get("type"), (75, 140, True))
    if outro and (not sc or sc[-1].get("kind") != "outro"): errs.append("the last scene must be an outro")
    if category == "Stock story" and not any(s.get("kind") == "scene" for s in sc):
        errs.append("a stock story shows what the company does as an animated \"scene\" (its business acted out with sprites)")
    words = sum(len(s.get("vo", "").split()) for s in sc)
    if not lo_w <= words <= hi_w: errs.append(f"the narration is {words} words; it must be {lo_w} to {hi_w}")
    for k, s in enumerate(sc):
        if len(s.get("vo", "").split()) > 26: errs.append(f"scene {k}'s line is too long ({len(s['vo'].split())} words, max 26)")
        ch = s.get("chart")
        if ch is not None and not (isinstance(ch, int) and 0 <= ch < len(charts)): errs.append(f"scene {k} uses chart {ch}, which does not exist")
        for c in s.get("cues", []):
            if c.get("say") and c["say"].lower() not in s.get("vo", "").lower(): errs.append(f"scene {k}: cue phrase {c['say']!r} is not in its line")
            for f in ("to", "i", "from"):
                if f in c and isinstance(ch, int) and 0 <= ch < len(charts) and not 0 <= c[f] < len(charts[ch]["candles"]):
                    errs.append(f"scene {k}: candle {c[f]} is outside chart {ch}")
    errs += shown_check(sc, charts) + speech_check(sc)
    if sc and sc[0].get("kind") == "hook":                 # the hook as spoken (the screen and the caption follow it, never swapped)
        res, score, _, flags = hookscore.run(sc[0].get("vo", ""))
        if score < 50:
            weak = "; ".join(f"{k.lower()} {v[0]:.0f}: {v[1]}" for k, v in sorted(res.items(), key=lambda x: x[1][0])[:3])
            errs.append(f"the spoken hook scores {score:.0f}/100 (needs 50+); its weakest parts: {weak}" + (f"; {'; '.join(flags)}" if flags else "") +
                        ". A hook that scores: 5-12 words, a number or a named thing up front, something lost or won, said to 'you' "
                        "(e.g. 'This one candle cost you fifteen percent.' scores 84); keep the on-screen text and the caption's first line saying the same thing")
    if sc and sc[0].get("kind") == "hook" and sc[0].get("chart") is None and sc[0].get("text"):
        k = lambda x: [re.sub(r"[^a-z0-9']", "", w.lower()) for w in x.split()]
        tx, vx = k(sc[0]["text"]), k(sc[0].get("vo", ""))
        if tx != vx[:len(tx)]: errs.append("the hook's on-screen text must be the first words of the spoken hook, word for word, so it appears as it is said from the first frame")
    spoken = " ".join(x.get("vo", "") for x in sc)
    acr = sorted({a for a in re.findall(r"[A-Z][A-Z0-9&]{1,5}", spoken) if a not in LEX and a not in ("I", "OK", "UK", "US")})
    if acr: errs.append("write these out or as people say them (the voice reads capitals as letters): " + ", ".join(acr))
    if re.search(r"[0-9]+[.][0-9]{2}", spoken): errs.append("say prices the way people say them, no decimals in a spoken line ('about two ten')")
    # (numbers are written out for the voice, but the detector counts only digits as concrete: score them as digits)
    NW = r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|half|point)"
    hs = detect.run(re.sub(rf"\b{NW}(?:[\s-]+(?:and\s+)?{NW})*\b", "9", spoken, flags=re.I), json.load(open(os.path.join(HERE, "ig", "slop.json"), encoding="utf-8")))
    if hs[2] == "FLAGGED":
        weak = "; ".join(f"{n.lower()} {v[0]:.0f}: {v[1]}" for n, v in sorted(hs[0].items(), key=lambda kv: kv[1][0])[:2])
        errs.append(f"the narration reads machine-written (human score {hs[1]:.0f}; weakest: {weak}): vary sentence length, be concrete, talk to 'you', drop stock phrases")
    if sc and sc[-1].get("kind") == "outro" and "daily chart" not in sc[-1].get("vo", "").lower():
        errs.append("the outro must end: \"Today's Daily Chart is live. Beat it at memestreet.net.\"")
    if sc and "memestreet.net" not in sc[-1].get("vo", "").lower():
        errs.append("the last scene's line must end by saying memestreet.net (spoken as 'Meem Street dot net')")
    if facts.get("plan_beat_holding") is False and not re.search(r"\bhold", " ".join(x.get("vo", "") for x in sc[:2]).lower()):
        errs.append("buying at the open and holding beat today's trades: say so briefly in the first or second scene (use the word 'holding')")
    cap = spec.get("caption", "")
    if DISCLAIMER not in cap: errs.append(f"the caption must contain exactly: {DISCLAIMER}")
    if EMOJI.search(cap + json.dumps(sc)): errs.append("no emoji anywhere")
    if "#MemeStreet" not in cap: errs.append("the caption needs #MemeStreet")
    return errs


def speech_check(sc):
    """Sentences like a person's (the human Shorts average 16 words a sentence; ours were 5 to 7): flowing on average,
    and never two fragments in a row."""
    errs, frag = [], []
    sents = [x for s in sc for x in re.split(r"(?<=[.?!])\s+", s.get("vo", "").strip()) if x]
    n = sum(len(x.split()) for x in sents)
    if n >= 40 and n / max(1, len(sents)) < 9:
        errs.append(f"the sentences average {n / len(sents):.0f} words: people speak in flowing sentences of 10 to 20 words, joined with so, and, but, because")
    for a, b in zip(sents, sents[1:]):
        if len(a.split()) < 4 and len(b.split()) < 4: frag.append(f"{a} {b}")
    if frag: errs.append("stacked fragments read like an advert, join them into a sentence: " + " | ".join(frag[:4]))
    return errs


CHART_TALK = re.compile(r"\b(candles?|chart|breakout|volume|wicks?)\b", re.I)


def shown_check(sc, charts):
    """The screen shows what the voice says: chart talk has a chart, on-screen text is spoken word for word, a figure is
    not labelled with the title, and marks, shades and zooms land on candles that are already drawn (renderer rules)."""
    errs, end = [], {}
    kw = lambda x: [re.sub(r"[^a-z0-9']", "", w.lower()) for w in x.split() if re.sub(r"[^a-z0-9']", "", w.lower())]
    for k, s in enumerate(sc):
        ch, kind, vo = s.get("chart"), s.get("kind"), s.get("vo", "")
        if kind == "scene":                                # an animated picture: sprites that act out the line
            sp = s.get("sprites") or []
            if not 3 <= len(sp) <= 8: errs.append(f"scene {k} (an animated scene) needs 3 to 8 sprites, it has {len(sp)}")
            for p in sp:
                if not isinstance(p.get("e"), str) or not p["e"] or len(p["e"]) > 8 or p["e"].isascii():
                    errs.append(f"scene {k}: sprite {p.get('e')!r} must be one emoji")
                if not all(isinstance(p.get(q), (int, float)) and 0 <= p[q] <= 100 for q in ("x", "y")):
                    errs.append(f"scene {k}: sprite {p.get('e')!r} needs x and y from 0 to 100")
                if p.get("say") and not re.search(re.escape(p["say"].lower()), vo.lower()):
                    errs.append(f"scene {k}: sprite {p.get('e')!r} says {p['say']!r}, which is not in its line")
        if ch is None and kind in ("stick", "cards", "big", "scene") and CHART_TALK.search(vo):
            errs.append(f"scene {k} talks about {CHART_TALK.search(vo).group(0)!r} but shows no chart: give it the chart, or say only what it shows")
        if s.get("text") and kind in ("hook", "big", "outro"):
            t, v = kw(s["text"]), kw(vo)
            if not any(v[j:j + len(t)] == t for j in range(len(v) - len(t) + 1)):
                errs.append(f"scene {k}'s on-screen text {s['text']!r} must be words of its line, word for word, in order")
        for f in s.get("figures") or []:
            if f.get("label") and s.get("head") and f["label"].strip().lower() == s["head"].strip().lower():
                errs.append(f"scene {k}: the figure's label repeats the title {s['head']!r}; label it with its name (Rookie, Pro)")
        if not (isinstance(ch, int) and 0 <= ch < len(charts)):
            continue
        C = charts[ch]; n = len(C["candles"]); drill = C.get("drill")
        if kind == "question" and drill: r = C["upto"]                    # (as the renderer will draw it: see finish())
        elif s.get("show") is not None: r = s["show"]
        elif k and sc[k - 1].get("chart") == ch: r = end[k - 1]
        elif kind in ("hook", "chart") and drill: r = C["upto"]
        else: r = n - 1
        if kind == "answer" and drill: r = max(r, C["end"])
        for c in s.get("cues", []):
            if c.get("do") == "reveal" and isinstance(c.get("to"), int): r = max(r, c["to"])
            far = c.get("i") if c.get("do") == "mark" else c.get("to") if c.get("do") in ("shade", "zoom") else None
            if isinstance(far, int) and far > r:
                errs.append(f"scene {k}: the {c['do']} on candle {far} points at a candle not drawn yet (only up to {r} is on screen): reveal it first or use an earlier candle")
        end[k] = r
    seen = {}
    for k, s in enumerate(sc):
        for c in s.get("cues", []):
            if c.get("do") != "line" or not c.get("label") or not isinstance(c.get("price"), (int, float)): continue
            for (ch, lab), p in seen.items():
                same = abs(p - c["price"]) <= 0.005 * max(abs(p), 1e-9)
                if ch == s.get("chart") and (lab == c["label"]) != same:
                    errs.append(f"scene {k}: the line {c['label']!r} at {c['price']} " + (f"is the level already called {lab!r}: one level keeps one name in every scene" if same else f"reuses the name of the line at {p}: one name means one level"))
            seen[(s.get("chart"), c["label"])] = c["price"]
    return errs


def finish(spec, charts, category):
    """Add what comes from the facts, not from Claude: the options and answers, the drawn lines, the windows."""
    named = [(s.get("chart"), c["price"], c["label"]) for s in spec["scenes"] for c in s.get("cues", [])
             if c.get("do") == "line" and c.get("label") and isinstance(c.get("price"), (int, float))]
    def name(k, x):                                       # the writer's name for this level, if it drew it: one level, one name
        return next((lab for ck, p, lab in named if ck == k and abs(p - x["price"]) <= 0.005 * abs(p)), x.get("label", ""))[:22]
    for s in spec["scenes"]:
        ch = charts[s["chart"]] if isinstance(s.get("chart"), int) else None
        if not ch:
            s["chart"] = None; continue
        s.setdefault("win", ch["win"])
        d = ch.get("drill")
        tone = lambda x: x.get("tone", "level")
        if s["kind"] == "question" and d:
            s["options"], s["answer"], s["show"] = d["options"], d["answer"], ch["upto"]
            s["win"] = [ch["win"][0], ch["end"]]
            s.setdefault("cues", []).append({"say": "", "do": "options"})
            s["cues"] += [{"say": "", "do": "line", "price": x["price"], "label": name(s["chart"], x), "tone": tone(x)}
                          for x in d["lines"] if not x.get("after")][:2]
        elif s["kind"] == "answer" and d:
            s["reveal_to"], s["carry"] = ch["end"], True
            s.setdefault("cues", [])
            s["cues"] += [{"say": "", "do": "line", "price": x["price"], "label": name(s["chart"], x), "tone": tone(x)}
                          for x in d["lines"] if x.get("after")][:3]
            s["cues"] += [{"say": "", "do": "mark", "i": m["i"], "label": m.get("label", "")[:2], "side": "high"} for m in d["marks"] if m.get("label")][:3]
        elif s["kind"] in ("hook", "chart") and s.get("show") is None and d:
            s["show"] = ch["upto"]
    spec["type"] = category
    spec["charts"] = [{"candles": c["candles"], "label": c["label"]} for c in charts]
    return spec


def brief(slot, category=None, remake=None):
    """Everything the writer needs for one reel: the system prompt, the request (facts included) and the charts."""
    rng = random.Random(slot)
    history = json.load(open(HISTORY)) if os.path.exists(HISTORY) else {}
    if remake:
        category = {"Chart quiz": "Chart quiz", "Stock story": "Stock story", "Technicals": "Technical lesson",
                    "New-trader challenge": "Trading mistake"}.get(remake.get("type"), "Technical lesson")
    category = category or rng.choice(ROTATION.get(slot[-4:], ["Technical lesson"]))
    try:
        facts, charts = gather(category, rng, history, remake.get("title") if remake and category == "Stock story" else None)
    except SystemExit:
        if not (remake and category == "Stock story"): raise
        category = "Explained like you're 5"               # (gold, oil, an ETF: not a game company, so an explainer on the topic)
        facts, charts = gather(category, rng, history)
    voice = open(os.path.join(ROOT, "voice.md"), encoding="utf-8").read()      # (a copy of ~/.claude/instagram/voice.md)
    hooks = json.load(open(os.path.join(HERE, "ig", "hooks.json"), encoding="utf-8"))["hooks"]
    system = ("You write Instagram Reels for Meme Street, a free stock market game with fictional companies "
              "(memestreet.net). Voice profile:\n" + voice + "\n\nHook formulas you may use:\n" +
              "\n".join(f"- {h['name']}: {h['template']}" for h in hooks) + "\n\n" + RULES + "\n" + SCHEMA % category)
    ask = {"category": category, "what_this_reel_is": CATEGORIES[category], "facts": facts,
           "recent_titles_to_avoid": history.get("titles", [])[-20:]}
    if CATEGORIES[category].startswith("VIRAL"):
        ask["what_works_now"] = {"note": "Openings of short trading videos that beat their own account's usual views "
                                         "(research 2026-11-04). Use the SHAPE, never the words: write an original line "
                                         "about this reel's own chart.",
                                 "examples": STICK_EVIDENCE if "STICK" in CATEGORIES[category] else
                                 SHORT_EVIDENCE if category in LENGTH else VIRAL_EVIDENCE}
        ev = os.path.join(ROOT, "state", "evidence.json")      # this week's outliers (src/research.py), shapes only
        if os.path.exists(ev):
            ask["what_works_now"]["this_week"] = json.load(open(ev, encoding="utf-8")).get("examples", [])[:8]
    if remake:
        ask["remake_of"] = {"note": "Make this reel again on the same topic, with the same teaching points and similar "
                                    "explanations, but tighter: no long pauses, every line earns its place. Use the new "
                                    "charts in the facts instead of the old ones. If the topic is something the chart cannot "
                                    "draw (MACD, Bollinger Bands, VWAP, ATR, moving averages, position sizing, an ETF, a "
                                    "commodity), explain it with cards, big text and Rookie and Pro, and use the chart only "
                                    "for what it really shows; never claim the chart shows the indicator.",
                            "title": remake.get("title"), "old_narration": remake.get("narration"), "old_caption": remake.get("caption")}
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    json.dump(history, open(HISTORY, "w"))                  # (the stock just used, so the next story picks another)
    return {"slot": slot, "category": category, "system": system, "ask": ask, "charts": charts}


def parse(raw, B, base=None):
    """The script in Claude's reply (a patch of `base` when one is given), and what is wrong with it."""
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        spec = json.loads(m.group(0)) if m else {}
    except ValueError as e:
        return {}, [f"not valid JSON: {e}"]
    if base is not None:
        spec = merge(base, spec)
    return spec, check(spec, B["ask"]["facts"], B["charts"], B["category"])


def merge(base, patch):
    """A rewrite after the critic sends only what changes: {"scenes": {"3": scene, ...}, "title": ...}. The scenes not
    named stay exactly as they were (a whole script, with a list of scenes, replaces the draft)."""
    if isinstance(patch.get("scenes"), list):
        return patch
    s = json.loads(json.dumps(base))
    for k, v in (patch.get("scenes") or {}).items():
        i = int(k)
        if 0 <= i < len(s["scenes"]): s["scenes"][i] = v
        elif i == len(s["scenes"]): s["scenes"].append(v)
    s.update({k: v for k, v in patch.items() if k != "scenes"})
    return s


def claude_cli(messages, system):
    """The writer through Claude Code on this server, logged in to the owner's plan (CLAUDE_CODE_OAUTH_TOKEN from
    `claude setup-token`): the plan's usage, no API bill. No tools: it only writes."""
    convo = "\n\n".join(("REQUEST:\n" if m["role"] == "user" else "YOUR EARLIER REPLY:\n") + m["content"] for m in messages)
    r = subprocess.run(["claude", "-p", "--output-format", "text", "--model", os.environ.get("REEL_CLI_MODEL", "sonnet"),
                        "--append-system-prompt", system,
                        "--disallowedTools", "Bash,Edit,Write,Read,WebFetch,WebSearch,Glob,Grep,Task,NotebookEdit"],
                       input=convo, capture_output=True, text=True, timeout=600, cwd="/tmp",
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})   # (an API key would be billed instead)
    if r.returncode:
        raise SystemExit("claude -p failed: " + (r.stderr or r.stdout)[-400:])
    return r.stdout


def lessons():
    """What the film critic (critic.py) sent earlier reels back for, most often first: the writer reads these before
    every reel, so the next one passes first time."""
    f = os.path.join(ROOT, "state", "lessons.json")
    L = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else []
    L = sorted((x for x in L if x.get("owner") != "renderer"),     # (the renderer's notes are fixed in reel.html, not by the writer)
               key=lambda x: (x.get("count", 1), x.get("last", "")), reverse=True)[:30]
    return ("\n\nThe film critic who reviews every finished reel sent earlier reels back for these. Never repeat them:\n" +
            "\n".join(f"- {x['lesson']}" for x in L)) if L else ""


def write(B, msgs=None, base=None):
    """Have Claude write the script (or, with `base`, a patch of it), checked and sent back at most four times."""
    ask = claude_cli if os.environ.get("REEL_WRITER", "cli") == "cli" else claude
    msgs = msgs or [{"role": "user", "content": json.dumps(B["ask"], indent=1)}]
    B = dict(B, system=B["system"] + lessons())
    for attempt in range(5):
        raw = ask(msgs, B["system"])
        spec, errs = parse(raw, B, base)
        if not errs:
            return spec
        print(f"attempt {attempt + 1}: " + "; ".join(errs[:8]))
        msgs += [{"role": "assistant", "content": raw}, {"role": "user", "content": ("Fix these and reply with only the scenes you change, in the same form: " if base else "Fix these and reply with the whole JSON again: ") + "; ".join(errs)}]
    raise SystemExit("the script did not pass its checks: " + "; ".join(errs))


def revise(work, review):
    """The critic sent the finished reel back: the writer gets its own script and his checked script notes, and rewrites
    only the scenes they name (a patch; the rest is approved and stays as it is, so it is not voiced or reviewed again)."""
    B = json.load(open(os.path.join(work, "brief.json"), encoding="utf-8"))
    draft = open(os.path.join(work, "draft.json"), encoding="utf-8").read()
    sn = lambda x: int((re.findall(r"scene (\d+)", x.get("where", "")) or [999])[0])
    notes = "\n".join(f"- [{x.get('severity', '')}] {x.get('where', '')}: {x.get('what', '')} FIX: {x.get('fix', '')}"
                      for x in sorted((x for x in review.get("issues", []) if x.get("owner", "script") != "renderer"), key=sn))
    msgs = [{"role": "user", "content": json.dumps(B["ask"], indent=1)}, {"role": "assistant", "content": draft},
            {"role": "user", "content": "A film critic watched the finished reel made from your script and sent it back.\n"
                                        f"His notes (scenes count from 0):\n{notes}\n"
                                        "Fix every note. Everything he did not mention is approved: leave it exactly as it is. "
                                        'Reply with JSON holding only what you change: {"scenes": {"<scene number>": <the whole '
                                        'new scene>, ...}}, plus "title" or "caption" only if a note is about them. To add, '
                                        "remove or reorder scenes, reply with the whole JSON instead."}]
    save(write(B, msgs, json.loads(draft)), B, work, again=True)


def save(spec, B, work, again=False):
    os.makedirs(work, exist_ok=True)
    json.dump(B, open(os.path.join(work, "brief.json"), "w"))          # (for a rewrite after the critic: revise())
    json.dump(spec, open(os.path.join(work, "draft.json"), "w"))
    spec = finish(spec, B["charts"], B["category"])
    json.dump(spec, open(os.path.join(work, "spec.json"), "w"))
    open(os.path.join(work, "caption.txt"), "w", encoding="utf-8").write(spec["caption"].strip() + "\n")
    history = json.load(open(HISTORY)) if os.path.exists(HISTORY) else {}
    if not again: history.setdefault("titles", []).append(spec["title"])
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    json.dump(history, open(HISTORY, "w"))
    print(f"{B['category']}: {spec['title']} ({sum(len(s['vo'].split()) for s in spec['scenes'])} words, {len(spec['scenes'])} scenes)")


if __name__ == "__main__":
    a = sys.argv[1:]
    rem = json.load(open(a[a.index("--remake") + 1], encoding="utf-8")) if "--remake" in a else None
    cat = a[a.index("--category") + 1] if "--category" in a else None
    if a[0] == "revise":                                 # <work> <review.json>: rewrite after the film critic's notes
        revise(a[1], json.load(open(a[2], encoding="utf-8")))
    elif a[0] == "brief":                                  # for a writer elsewhere (a cloud session): <dir>/brief.json
        B = brief(a[1], cat, rem); os.makedirs(a[2], exist_ok=True)
        json.dump(B, open(os.path.join(a[2], "brief.json"), "w"))
        print(f"{a[2]}/brief.json: {B['category']}")
    elif a[0] == "assemble":                             # <dir>/brief.json + <dir>/script.json (the writer's reply) -> spec.json
        B = json.load(open(os.path.join(a[1], "brief.json")))
        spec, errs = parse(open(os.path.join(a[1], "script.json"), encoding="utf-8").read(), B)
        if errs:
            raise SystemExit("fix: " + "; ".join(errs))
        save(spec, B, a[1])
    else:                                                # <slot> <work>: brief, write, save
        B = brief(a[0], cat, rem)
        save(write(B), B, a[1])
