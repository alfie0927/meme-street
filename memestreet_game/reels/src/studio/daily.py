"""The 23:30 daily reel, made by the studio (since 2026-11-27, the owner on the remade TSMC reel: "ok amazing, keep this style for
each daily reel. but make every day more imaginative and creative").

The style is fixed: the viewer's own $100,000 (the game's real starting cash) put into the day's mystery stock, a live "YOUR MONEY"
counter riding the real prices, one fast but smooth beat a sentence, numbers spoken as words, the vote, the midnight line
(engines/hf/daily). What changes every day is the IDEA: the writer picks a new angle on the story, a new mix of beats (text
messages, a receipt, a face-off, a pull quote, a timeline, a gauge, notifications, a clipping, the chart, the product...) and a new
look (background motif and colours), and is shown the last seven days' choices so it never repeats them.

  python3 src/studio/daily.py <YYYY-MM-DD>            write, check, voice, film, mix, check every frame, queue for <date>T2330
  python3 src/studio/daily.py <date> --dir <d>        the same into <d>, not queued
  python3 src/studio/daily.py demo                    self-check (no Claude, no voice, no render)
Every number the writer uses must be in the day's research or follow from the real prices; a script that breaks a rule is sent
back (six tries). A reel whose frame check fails is not queued.
"""
import datetime, json, math, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.dirname(HERE); ROOT = os.path.dirname(SRC); EXPL = os.path.join(SRC, "explainer")
sys.path.insert(0, HERE); sys.path.insert(0, EXPL); sys.path.insert(0, SRC)
import studio as ST
BASE = 100000
STATE = os.path.join(ROOT, "state", "studio_daily.json")
KINDS = {
 "hook": 'frame 0: the viewer\'s $100,000 in huge type under two lines of contrast. Fields: "top", "bottom" (each at most 20 letters), "sub" (at most 34 letters), "crashOn"/"crashI" (optional: the word of the snapback where the money drops to where the window ended; omit if it rose)',
 "name": 'the reveal: the company name slammed in, its product turning in 3D below. Fields: "text" (the name), "kicker" ("IT WAS"), "sub" (what it does, at most 34 letters)',
 "chart": 'the real price line drawing itself between two points of the window. Fields: "from", "to" (0 to 1, or "peak", "low", "end"), optional "stamp"',
 "big": 'one number counting up and landing as it is said. Fields: "to", "from" (optional), "prefix", "suffix", "dec", "label" (at most 26 letters), "color", "on" (the word it lands on, as written in the sentence), optional "vs" + "vsLabel" + "label2" for a before/after bar',
 "notify": 'phone notifications dropping in. Fields: "items": [{"app", "icon" (one character), "color", "title" (at most 40 letters), "body" (optional, at most 44), "on"}] (1 or 2 items)',
 "clip": 'a taped newspaper or filing clipping. Fields: "paper", "date", "head" (at most 46 letters), "dek" (optional)',
 "chat": 'a text-message thread. Fields: "msgs": [{"who" (optional), "text" (at most 60 letters), "me": true|false, "on" (optional)}] (2 to 4 bubbles)',
 "receipt": 'a receipt printing line by line. Fields: "title" (its heading), "lines": [[label, amount]] (2 to 5), "total": [label, amount], "totalColor"',
 "versus": 'two numbers face off. Fields: "a": [value, label], "b": [value, label], "aColor", "bColor", "on" (the word b lands on)',
 "quote": 'words someone really said, from the research only, word for word. Fields: "text" (at most 90 letters), "by"',
 "timeline": 'dated moments down a line. Fields: "items": [[when, what]] (2 to 4; what at most 30 letters)',
 "meter": 'a gauge needle swinging to a value. Fields: "to", "from", "max", "prefix", "suffix", "label"',
 "product": 'the company\'s product turning in 3D, big. Fields: "text" (optional caption under it)',
 "blank": 'nothing but the caption (the vote and the midnight line sit on this)',
}
COMMON = 'Every beat may also carry "f" (where the YOUR MONEY counter stands when the beat ends: 0 to 1 or "peak"/"low"/"end"), "move" (slam, up, whipL, whipR, flip, drop), "head" (a 1 or 2 line headline, "LINE ONE|LINE TWO") and "stamp": {"text", "on", "color", "y"}.'
MOTIFS = ["blobs", "grid", "rays", "stripes", "dots", "tape"]
PRODUCTS = ["camera", "chip", "phone", "laptop", "car", "van", "bottle", "pill", "shoe", "shirt", "game", "food", "box"]
say = lambda *a: print(datetime.datetime.utcnow().strftime("%H:%M:%S"), *a, flush=True)


def state():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"days": []}


def money_table(P):
    """What $100,000 became at each month of the window: the figures the writer may use for "your money"."""
    n = len(P) - 1; hi, lo = P.index(max(P)), P.index(min(P))
    pts = sorted({0, n, hi, lo} | {round(k * n / 12) for k in range(13)})
    return {"start": BASE, "peak": {"value": round(BASE * P[hi] / P[0]), "at": round(hi / n, 3)}, "low": {"value": round(BASE * P[lo] / P[0]), "at": round(lo / n, 3)},
            "end": round(BASE * P[-1] / P[0]), "change_pct": round((P[-1] / P[0] - 1) * 100), "path": [{"at": round(i / n, 3), "value": round(BASE * P[i] / P[0])} for i in pts]}


def system():
    return ("You write the script and the shot list of one 30 to 45 second vertical reel for Meme Street (memestreet.net), a free daily "
            "game where a visitor gets $100,000 of practice money and two minutes to trade a real stock's chart with its name hidden. "
            "Tonight's reel tells the true story behind today's chart, as if the VIEWER had put their $100,000 into it on the first day. "
            "The format is fixed; the idea must be new every day.\n\nTHE SERIES RULES:\n" + open(os.path.join(HERE, "BIBLE.md"), encoding="utf-8").read() +
            "\n\nTHE HOOK (follow it; the reel lives or dies in its first three seconds):\n" + open(os.path.join(HERE, "HOOKS.md"), encoding="utf-8").read())


def ask(story, recent, example):
    st = story["stock"]; mt = money_table(story["chart"])
    kinds = "\n".join(f"  {k}: {v}" for k, v in KINDS.items())
    rec = "\n".join(f"  {d['date']}: angle \"{d.get('angle')}\", beats {d.get('kinds')}, motif {d.get('motif')}, hook \"{d.get('hook')}\"" for d in recent[-7:]) or "  (none yet)"
    return ("THE TRUE STORY. Every figure, date, name and claim must come from here, nothing else:\n" + json.dumps({k: story[k] for k in ("stock", "window", "prices", "research")}, indent=1) +
            "\n\nWHAT THE VIEWER'S $100,000 BECAME (use these figures for 'your money', exactly, with commas: $127,628):\n" + json.dumps(mt) +
            f"\n\nTHE LAST SEVEN DAILY REELS (do something DIFFERENT: another angle, another opening line shape, another mix of beats, another motif):\n{rec}"
            "\n\nBEFORE WRITING, pick tonight's ANGLE: one imaginative way into this story that a stranger has not seen (for example: the group chat "
            "where your friend told you to buy; the receipt of everything that went wrong; a face-off between the hype and the result; the "
            "day-by-day diary of your money; the one quote that aged badly; the countdown to the moment it turned; a weather report for your "
            "portfolio...). Invent your own; never one the last seven used. Build every beat to serve it."
            "\n\nTHE BEATS you can use, one a sentence (in order: sentence i is scene i):\n" + kinds + "\n" + COMMON +
            "\n\nWRITE JSON only:\n"
            '{"angle": a few words, "title": the post title (8 to 14 words, the company named), "brand_color": "#rrggbb" (the company\'s own colour, readable on near-black),\n'
            ' "product": one of ' + ", ".join(PRODUCTS) + ' (what it makes, nearest), "label": what is printed on the product (at most 12 letters),\n'
            ' "theme": {"motif": one of ' + ", ".join(MOTIFS) + ', "ink": a near-black background "#rrggbb", "glow": "#rrggbb55", "glow2": "rgba(...)"},\n'
            ' "hook": {"context", "lean", "snapback" (the first three sentences, word for word), "text": "LINE ONE|LINE TWO" (the words on frame 0, at most six words, 30 letters), "visual"},\n'
            ' "say": [11 to 14 sentences], "scenes": [one beat per sentence],\n'
            ' "choice": {"q": the closing question, "a", "b" (each at most 26 letters, different first words)},\n'
            ' "caption": 2 or 3 lines for the post (the hook, then the dates), "music": one of "Shock and Awe", "Secret Garden", "The Snail", "Fun and Games", "Kidding Around", "Fun Jazz", "Playful"}\n'
            "THE RULES OF THE FORM:\n"
            "- Sentence 1 begins \"You put $100,000 into\" and names what the stock is in plain words (never its name). Sentences 1 to 3 are the hook's context, lean and snapback.\n"
            f"- Sentence 4 is the reveal and begins \"{story.get('day') or 'Today' + chr(39) + 's'} mystery chart on Meme Street was {st['name'].split(' (')[0]}\"; its beat is \"name\".\n"
            "- The second to last sentence is the vote, a question; its beat is \"blank\". The last sentence is, word for word: \"A new mystery chart goes live at midnight.\" (beat \"blank\").\n"
            "- Scene 0 is \"hook\". Use at least five different kinds of beat, \"chart\" at least once, and no kind more than twice (\"blank\" and \"chart\" excepted).\n"
            "- Sentences of 6 to 16 words, said by one narrator to the viewer (\"you\", \"your money\"). 95 to 120 words in all. Plain words a 12-year-old gets.\n"
            "- Money as written: $100,000 / $127,628 / $2.51 / $9.21 billion. No invented numbers, quotes, people or events. A quote beat only with words the research quotes.\n"
            "- Every \"on\" is a word of its own sentence, written exactly as in the sentence.\n\n"
            "THE SHAPE OF A GOOD ONE (another day's reel; its idea is used, never copy it):\n" + json.dumps(example, indent=1))


def numbers_ok(spec, story):
    """Every figure in what is said and shown is in the research or follows from the real prices. -> [faults]"""
    txt = json.dumps({k: story[k] for k in ("window", "prices", "research", "stock")}); allowed = set()
    for m in re.findall(r"\d[\d,]*(?:\.\d+)?", txt): m = m.rstrip(","); allowed.add(m.replace(",", "").rstrip("0").rstrip(".") if "." in m else m.replace(",", ""))
    for a, u in re.findall(r"(\d+(?:\.\d+)?)\s*(thousand|million|billion)", txt): allowed.add(str(round(float(a) * {"thousand": 1e3, "million": 1e6, "billion": 1e9}[u])))      # ("$3.1 million" may be written 3100000)
    P = story["chart"]; vals = [BASE * p / P[0] for p in P]
    def fine(x):
        v = x.rstrip(",").replace(",", ""); vn = v.rstrip("0").rstrip(".") if "." in v else v
        if vn in allowed or v in allowed: return True
        f = float(v)
        if f <= 12 or 1990 <= f <= 2035 or f == BASE: return True
        if any(abs(f - a) <= max(2, a * .004) for a in vals): return True                                  # (what $100,000 was worth on some day)
        if any(abs(f - abs(round((a / BASE - 1) * 100))) < 1.01 for a in vals): return True                # (a percent change of it)
        return False
    seen = []
    for s in spec.get("say", []): seen += re.findall(r"\d[\d,]*(?:\.\d+)?", s)
    for sc in spec.get("scenes", []): seen += re.findall(r"\d[\d,]*(?:\.\d+)?", re.sub(r"#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)", "", json.dumps({k: v for k, v in sc.items() if k not in ("f", "from", "to", "y", "max", "crashI", "dec")}, ensure_ascii=False)))      # (colours are not figures)
    bad = sorted({x for x in seen if not fine(x)})
    return [f"these figures are not in the research or the prices: {', '.join(bad[:8])} (use only real figures; your money's values are in the table)"] if bad else []


def errors(spec, story, recent):
    F = []; S = spec.get("say") or []; C = spec.get("scenes") or []; st = story["stock"]; name = st["name"].split(" (")[0]
    for k in ("angle", "title", "hook", "say", "scenes", "choice", "theme", "product"):
        if not spec.get(k): F.append(f"no {k}")
    if F: return F
    if len(S) != len(C): F.append(f"{len(S)} sentences but {len(C)} scenes: one beat a sentence")
    if not 11 <= len(S) <= 14: F.append(f"{len(S)} sentences: write 11 to 14")
    n = sum(len(s.split()) for s in S)
    if not 95 <= n <= 120: F.append(f"{n} words: write 95 to 120 (about 45 seconds at this pace)")
    if not S[0].startswith("You put $100,000 into"): F.append('sentence 1 begins "You put $100,000 into"')
    if name.lower() in " ".join(S[:3]).lower(): F.append("the name is not said before sentence 4")
    if len(S) > 3 and not S[3].lower().startswith(("today's mystery chart on meme street was", "yesterday's mystery chart on meme street was")) : F.append(f'sentence 4 begins "{story.get("day") or "Today" + chr(39) + "s"} mystery chart on Meme Street was {name}"')
    if S and S[-1].strip() != "A new mystery chart goes live at midnight.": F.append('the last sentence is "A new mystery chart goes live at midnight."')
    if len(S) > 1 and not S[-2].strip().endswith("?"): F.append("the second to last sentence is the vote: a question")
    kinds = [c.get("kind") for c in C]
    for i, k in enumerate(kinds):
        if k not in KINDS: F.append(f"scene {i + 1}: no beat called {k}")
    if kinds and kinds[0] != "hook": F.append("scene 1 is the hook beat")
    if len(kinds) > 3 and kinds[3] != "name": F.append("scene 4 is the name beat")
    if len(kinds) > 1 and (kinds[-1] != "blank" or kinds[-2] != "blank"): F.append("the last two scenes are blank (the vote and the midnight line sit on them)")
    if "chart" not in kinds: F.append("no chart beat: the real chart is shown at least once")
    from collections import Counter
    many = [k for k, c in Counter(kinds).items() if c > 2 and k not in ("blank", "chart")]
    if many: F.append(f"{', '.join(many)} used more than twice")
    if len(set(kinds) - {"blank"}) < 5: F.append("use at least five different kinds of beat")
    for i, c in enumerate(C):
        if i < len(S):
            for on in [c.get("on")] + [x.get("on") for x in c.get("items", []) + c.get("msgs", []) if isinstance(x, dict)] + [(c.get("stamp") or {}).get("on")]:
                if on and on not in S[i]: F.append(f"scene {i + 1}: \"on\": \"{on}\" is not a word of its sentence")
    if spec.get("product") not in PRODUCTS: F.append("product is one of " + ", ".join(PRODUCTS))
    if (spec.get("theme") or {}).get("motif") not in MOTIFS: F.append("theme.motif is one of " + ", ".join(MOTIFS))
    last = recent[-7:]
    if any(d.get("angle", "").lower() == str(spec.get("angle")).lower() for d in last): F.append("this angle was used in the last seven days: find a new one")
    if last and last[-1].get("motif") == (spec.get("theme") or {}).get("motif"): F.append("yesterday used the same motif: pick another")
    h = spec["hook"]; reel = to_reel(spec, story, "x")
    F += [f for f in ST.lint(reel)[0] if "seconds" not in f]
    F += numbers_ok(spec, story)
    return F


def to_reel(spec, story, name):
    st = story["stock"]; P = story["chart"]; nm = st["name"].split(" (")[0]; c = spec.get("choice") or {}
    vote = len(spec["say"]) - 2
    return {"name": name, "slot": "2330", "engine": "hf", "entry": "daily/index.html", "style": "your money: " + str(spec.get("angle")), "title": spec["title"],
            "brands": [{"name": nm, "color": spec.get("brand_color", "#2f7cf6")}], "hook": spec["hook"], "say": spec["say"], "choice": c,
            "music": spec.get("music") or "Shock and Awe", "tail": 1.0, "cover": {"t": 1.2}, "tags": f"#stocks #investing #stockmarket #{re.sub(r'[^A-Za-z0-9]', '', st['ticker'])} #MemeStreet",
            "caption": (spec.get("caption") or spec["title"]) + f"\n{story.get('day') or 'Today' + chr(39) + 's'} mystery chart was {nm} ({st['ticker']}), {st['start']} to {st['end']}." + ("\nSources: " + ", ".join(sorted({o for f in story['research'].get('facts', []) for o in (f.get('by') or [])})[:5]) if story['research'].get('facts') else ""),
            "props": {"prices": P, "dates": [st["start"], st["end"]], "name": nm, "color": spec.get("brand_color", "#2f7cf6"), "number": story.get("number"), "product": spec.get("product"),
                      "label": spec.get("label") or nm.upper()[:12], "tag": f"{(story.get('day') or 'Today' + chr(39) + 's').upper()} MYSTERY CHART", "vote": vote, "base": BASE, "theme": spec.get("theme") or {}, "scenes": spec["scenes"]}}


def write(story, recent):
    import make_spec as MS
    ex = json.load(open(os.path.join(HERE, "reels", "d26-tsmc", "reel.json"), encoding="utf-8")); ex = {"say": ex["say"], "hook": ex["hook"], "scenes": ex["props"]["scenes"], "choice": ex["choice"]}
    msgs = [{"role": "user", "content": ask(story, recent, ex)}]; sysp = system(); fix = []
    for k in range(6):
        reply = MS.claude_cli(msgs, sysp, model=os.environ.get("STUDIO_MODEL", "opus"))
        try: m = re.search(r"\{[\s\S]*\}", reply); spec = json.loads(m.group(0)); fix = errors(spec, story, recent)
        except Exception as e: spec, fix = None, [f"the reply was not valid JSON ({str(e)[:80]})"]
        if not fix: return spec
        say("sent back:", "; ".join(fix)[:500])
        msgs += [{"role": "assistant", "content": reply}, {"role": "user", "content": "Sent back. Fix only these, keep the rest, reply with the whole JSON again: " + "; ".join(fix)}]
    raise SystemExit("not made: the script failed its checks six times: " + "; ".join(fix))


def make(date, where=None):
    import make as M
    data = os.path.join(ROOT, "data", f"{date}.json")
    if not os.path.exists(data): subprocess.run([sys.executable, os.path.join(SRC, "fetch.py"), data], cwd=ROOT, check=True)
    story = M.day_story(date, data); st = state(); recent = st["days"]
    spec = json.load(open(os.environ["STUDIO_SPEC"], encoding="utf-8")) if os.environ.get("STUDIO_SPEC") else write(story, recent); d = where or os.path.join(ROOT, "work", f"studio-daily-{date}"); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    reel = to_reel(spec, story, f"daily-{date}"); json.dump(reel, open(os.path.join(d, "reel.json"), "w", encoding="utf-8"), indent=1)
    say("written:", spec["angle"], "|", " ".join(spec["say"][:3]))
    os.environ["DAILY_DATA"] = data; os.environ.setdefault("EXPLAINER_EL_SPEED", "0.96")
    ST.voice(d); ST.render(d)
    import sound as SN
    SN.mix(d); ST.pack(d); res = ST.check(d)
    if not res["ok"]: raise SystemExit("not queued: the frame check failed: " + "; ".join(res["faults"] + res["script"]["faults"]))
    if where: return d
    out = os.path.join(d, "out"); shutil.copy(os.path.join(d, "out", "cover.jpg"), out) if False else None
    json.dump({"by": "studio", "note": "the owner, 2026-11-27: keep this style for each daily reel, more imaginative every day", "check": {k: res[k] for k in ("faults", "warns")}}, open(os.path.join(out, "approved.json"), "w"))
    import news_reel as N
    slot = N.queue_out(out, f"{date}T2330", spec["title"])
    st["days"].append({"date": date, "angle": spec["angle"], "kinds": [c["kind"] for c in spec["scenes"]], "motif": spec["theme"].get("motif"), "hook": spec["say"][0]}); st["days"] = st["days"][-30:]
    os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(st, open(STATE, "w", encoding="utf-8"), indent=1)
    return slot


def daily(date):
    """The auto timer's entry: does nothing once the slot has its reel; three tries a day; -> 0 when the slot is filled."""
    q = os.path.join(ROOT, "queue", f"{date}T2330")
    if os.path.exists(os.path.join(q, ".auto")) or os.path.exists(os.path.join(q, "posted.json")): say(f"{date}T2330 already has its reel"); return 0
    tries = os.path.join(ROOT, "state", f"studio-{date}.tries"); n = int(open(tries).read()) if os.path.exists(tries) else 0
    if n >= 3: say(f"{date}: tried three times, not made"); return 1
    os.makedirs(os.path.dirname(tries), exist_ok=True); open(tries, "w").write(str(n + 1))
    make(date); return 0


def demo():
    P = [10 + i * .1 for i in range(121)]
    story = {"stock": {"name": "Acme (widgets)", "ticker": "ACM", "start": "2020-01-01", "end": "2020-06-01"}, "day": "Today's", "number": 1, "chart": P,
             "window": {"first_price": "$10.00"}, "prices": {}, "research": {"facts": [{"claim": "sales hit $9.21 billion", "by": ["X"]}]}}
    mt = money_table(P); assert mt["end"] == 220000 and mt["peak"]["value"] == 220000, mt
    ex = json.load(open(os.path.join(HERE, "reels", "d26-tsmc", "reel.json"), encoding="utf-8"))
    spec = {"angle": "a", "title": "t t t t t t t t", "hook": dict(ex["hook"], context="You put $100,000 into a widget maker.", lean="It turned into $220,000.", snapback="But nobody saw it coming at all."),
            "say": ["You put $100,000 into a widget maker.", "It turned into $220,000.", "But nobody saw it coming at all."] + ex["say"][3:], "scenes": ex["props"]["scenes"], "choice": ex["choice"], "theme": {"motif": "grid"}, "product": "box"}
    spec["say"][3] = "Today's mystery chart on Meme Street was Acme."
    F = numbers_ok(spec, story); assert any("figures" in f for f in F), F                    # (TSMC's figures are not Acme's)
    spec2 = dict(spec, say=spec["say"][:3] + ["Today's mystery chart on Meme Street was Acme.", "Sales hit $9.21 billion that year in the end.", "Your money ended at $220,000 by June."], scenes=[{"kind": "hook"}, {"kind": "big", "to": 220000, "on": "$220,000"}, {"kind": "clip", "head": "Sales hit $9.21 billion"}, {"kind": "name"}, {"kind": "chart"}, {"kind": "blank"}])
    assert numbers_ok(spec2, story) == [], numbers_ok(spec2, story)
    E = errors(spec, story, [{"angle": "a", "motif": "grid"}]); assert any("angle" in e for e in E) and any("motif" in e for e in E), E
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "demo": demo()
    elif "--dir" in a: print(make(a[0], a[a.index("--dir") + 1]))
    else: sys.exit(daily(a[0]))
