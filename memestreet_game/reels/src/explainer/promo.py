"""The two promo reels a day about the Daily (the owner, 2026-11-24: "post the 9am and 4pm posts ... then follow the schedule from
tomorrow"): at 09:00 UTC the TEASER of the day's mystery chart (only the months before the game, never what it does next; its
thumbnail always the gold DAILY #N badge, so the series is found on the grid), at 16:00 UTC a PROMO for the game, its theme
turning day by day (how to play, the streak, real charts, the same chart as your friends). Short (20 to 25 s), the daily reel's
look and voice, calm acts ("don't over do the animations"). Scripts are templates filled from the day's data: no writer, no
research, about 600 ElevenLabs characters a day.

  python3 src/explainer/promo.py day [YYYY-MM-DD]     make and queue the day's missing promo reels (<date>T0900, <date>T1600)
  python3 src/explainer/promo.py spec <date> <0900|1600> [theme]   print the script (no voice, no render)
  python3 src/explainer/promo.py demo                 self-check
"""
import datetime, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import make as M

SLOTS = {"0900": "teaser", "1600": "promo"}
THEMES = ["howto", "streak", "real", "friends"]
MUSIC = {"teaser": "Sneaking Around", "howto": "Informative Pizzicato", "streak": "Bumbling in the Dark", "real": "Sneaky Pizzicato Cartoon", "friends": "Well This is Awkward"}
BRAND = [{"name": "Meme Street", "color": "#ffc83d"}]
TAGS = "#stocks #trading #daytrading #stockmarket #MemeStreet"
GAME = "You get two minutes and $100,000 of practice money to buy, sell or short it as it prints, then the name comes up. No account, no app, no real money."


def money(v):
    return f"${v:.0f}" if v >= 20 else f"${v:.2f}".replace(".00", "")


def span(a, b):
    m = round((b - a).days / 30.4)
    return "a month" if m <= 1 else f"{m} months"


def day_data(date):
    """The day's Daily -> the little a promo needs: its number, the months before the game (prices) and their span."""
    p = os.path.join(M.ROOT, "data", f"{date}.json")
    if not os.path.exists(p): subprocess.run([sys.executable, os.path.join(M.SRC, "fetch.py"), p], cwd=M.ROOT, check=True)
    d = json.load(open(p, encoding="utf-8")); g = d["game"]; rv = g.get("real")
    if not rv: raise SystemExit(f"not made: the Daily of {date} is a model chart")
    H = g.get("history", 60); hist = [round(c[3] * rv["k"], 2) for c in g["candles"][:H]]
    start = datetime.date.fromisoformat(rv["start"]); frm = datetime.date.fromisoformat(rv["from"]) if rv.get("from") else start - datetime.timedelta(days=H * 7 // 5)
    y = os.path.join(M.ROOT, "data", f"{datetime.date.fromisoformat(date) - datetime.timedelta(days=1)}.json")
    try: yname = ((json.load(open(y, encoding="utf-8"))["game"].get("real") or {}).get("name"))
    except (OSError, ValueError, KeyError): yname = None
    return {"number": d.get("number"), "day": "Today's", "stock": {}, "chart": hist, "history": hist, "span": span(frm, start), "yesterday": yname}


def S(say, bg, *items):
    return {"say": say, "scene": {"bg": bg, "label": None, "items": list(items)}}


def teaser(st):
    """09:00: the day's chart up to the game, and the question. Three openings in turn by the Daily's number."""
    n, P, sp = st["number"], st["history"], st["span"]; lo, hi = min(P), max(P)
    ch = P[-1] / P[0] - 1; chart = {"kind": "chart", "from": 0, "to": 1, "title": "???"}      # (the opening says what the chart did, by its shape)
    if ch <= -.5: first = S(f"This stock crashed {round(-ch * 100)}% in {sp}, from {money(P[0])} to {money(P[-1])}.", "trading", chart, {"kind": "title", "text": "BUY THE CRASH?"})
    elif ch >= 1: first = S(f"This stock went up {ch + 1:.0f} times in {sp}.", "trading", chart, {"kind": "title", "text": "TOO LATE TO BUY?"})
    elif ch <= -.2: first = S(f"This stock fell from {money(P[0])} to {money(P[-1])} in {sp}.", "trading", chart, {"kind": "title", "text": "BOTTOM OR TRAP?"})
    elif ch >= .25: first = S(f"This stock went from {money(P[0])} to {money(P[-1])} in {sp}.", "trading", chart, {"kind": "title", "text": "BUY OR SELL?"})
    else: first = S(f"This stock drifted between {money(lo)} and {money(hi)} for {sp}.", "trading", chart, {"kind": "title", "text": "WHAT HAPPENS NEXT?"})
    lines = [first,
             S("What it did next is today's mystery chart on Meme Street.", "night", {"kind": "question", "act": "spin"}),
             S("You get two minutes and $100,000 of practice money.", "studio", {"kind": "money", "text": "$100K", "rain": True}),
             S("Buy it, sell it, or short it while it prints.", "home", {"kind": "person", "who": "you", "pose": "point"}, {"kind": "phone", "brand": "Meme Street", "title": f"DAILY #{n}", "lines": ["BUY", "SELL", "SHORT"], "tap": True, "on": "Buy"}),
             S("Then the name comes up, and you see how you did.", "stage", {"kind": "podium", "first": "you", "second": None, "third": None}),
             S("The real story behind it goes up tonight.", "city", {"kind": "news", "lines": ["TONIGHT", "23:30 UTC"], "act": "launch"}),
             S("Play it free, right now, at Meme Street dot net.", "home", {"kind": "phone", "brand": "Meme Street", "title": "MEME STREET", "lines": ["PLAY NOW"], "tap": True})]
    return {"title": f"Daily #{n}: What Does This Stock Do Next? You Have Two Minutes", "mystery": True, "prices": "history",
            "cover": {"style": "top", "color": "#ff5d6c", "lines": M.hook_lines({"title": "", "sentences": [first]})},      # (no DAILY badge: only the 23:30 story reel carries it, the owner 2026-11-25)
            "choice": {"kicker": f"DAILY #{n} · LIVE NOW", "a": "It goes up", "b": "It goes down", "cta": "Play free at memestreet.net"},
            "caption": f"Daily #{n} is live. {first['say']} What it did next is today's mystery chart on Meme Street. {GAME} Comment A or B, then play it free at memestreet.net. The story behind it goes up at 23:30 UTC.",
            "tags": TAGS, "brands": BRAND, "cast": [{"id": "you", "tag": "YOU", "look": "hoodie", "color": "#7fc4ff"}], "sentences": lines}


def promo(st, theme):
    """16:00: the game itself, one theme a day."""
    sam = [{"id": "sam", "tag": "SAM", "look": "hoodie", "color": "#7fc4ff"}]
    end = S("Today's chart is live right now, at Meme Street dot net.", "trading", {"kind": "chart", "from": 0, "to": 1, "title": "???"})
    if theme == "howto":
        return {"title": "Wordle, But For Stocks: One Mystery Chart A Day, Two Minutes To Trade It", "badge": ("How to play", "#7fc4ff"), "lines": ["Wordle", "for stocks"],
                "choice": ("Buy the dip", "Short it"), "cast": sam,
                "caption": "Wordle, but for stocks. Every midnight UTC one real stock chart goes live on Meme Street, its name hidden, the same chart for everyone. " + GAME + " Keep your streak and send your score to a friend. Play today's chart: memestreet.net",
                "sentences": [S("This is Wordle, but for stocks.", "night", {"kind": "chart", "from": 0, "to": 1, "title": "???"}, {"kind": "title", "text": "WORDLE FOR STOCKS"}),
                              S("Every midnight, one real stock chart goes live on Meme Street, its name hidden.", "city", {"kind": "question", "act": "spin"}),
                              S("You get two minutes and $100,000 of practice money.", "studio", {"kind": "money", "text": "$100K", "rain": True}),
                              S("Sam bought the first big dip.", "home", {"kind": "person", "who": "sam", "pose": "point"}, {"kind": "arrow", "dir": "down", "text": "DIP", "act": "drop", "on": "dip."}),
                              S("With seconds left, it turned around.", "studio", {"kind": "person", "who": "sam", "pose": "shock"}),
                              S("Sam sold near the top, and finished in the green.", "home", {"kind": "person", "who": "sam", "pose": "cheer"}, {"kind": "arrow", "dir": "up", "text": "GREEN", "act": "launch", "on": "green."}),
                              S("Then the name came up, and Sam's score hit the board.", "stage", {"kind": "podium", "first": "sam", "second": None, "third": None}),
                              S("No account, no app, and no real money.", "studio", {"kind": "phone", "brand": "Meme Street", "title": "FREE", "lines": ["NO ACCOUNT", "NO DOWNLOAD"], "act": "spin"}), end]}
    if theme == "streak":
        return {"title": "Miss One Day And Your Meme Street Streak Starts Again From Zero", "badge": ("Your streak", "#2bd47d"), "lines": ["Don't break", "the streak"],
                "choice": ("I'm on a streak", "Starting today"), "cast": sam,
                "caption": "One new stock chart a day on Meme Street, the same for everyone. Play every day and your streak counts up; miss one and it starts again from zero. " + GAME + " Start your streak today: memestreet.net",
                "sentences": [S("Miss one day, and your streak starts again from zero.", "night", {"kind": "calendar", "month": "STREAK", "day": "0", "act": "drop"}, {"kind": "title", "text": "DON'T BREAK THE STREAK"}),
                              S("Meme Street puts up one real stock chart every day.", "trading", {"kind": "chart", "from": 0, "to": 1, "title": "???"}),
                              S("Sam plays it every morning over coffee.", "home", {"kind": "person", "who": "sam", "pose": "hold"}, {"kind": "phone", "brand": "Meme Street", "title": "THE DAILY", "lines": ["PLAY"], "tap": True}),
                              S("Two minutes to buy, sell, or short it.", "studio", {"kind": "phone", "brand": "Meme Street", "title": "2:00", "lines": ["BUY", "SELL", "SHORT"], "act": "pulse"}),
                              S("Day after day, the streak keeps counting.", "office", {"kind": "calendar", "month": "STREAK", "day": "12", "act": "launch"}, {"kind": "person", "who": "sam", "pose": "cheer"}),
                              S("One morning Sam forgot, and it went back to zero.", "night", {"kind": "person", "who": "sam", "pose": "sad"}),
                              S("So Sam started again the very next day.", "city", {"kind": "person", "who": "sam", "pose": "walk"}), end]}
    if theme == "real":
        y = st.get("yesterday"); said = f"Yesterday's was {y}." if y else "Yesterday's was a name you know."
        return {"title": "Every Chart In This Game Is A Real Stock With Its Name Hidden", "badge": ("Real charts", "#b98cff"), "lines": ["Real stocks.", "No names."],
                "choice": ("I'd guess it", "No idea"), "cast": sam,
                "caption": "Every chart in the Meme Street Daily is a real stock's real prices, its name hidden until you have traded it. " + (f"Yesterday's was {y}. " if y else "") + GAME + " Can you guess today's? memestreet.net",
                "sentences": [S("Every chart in this game is a real stock, with its name hidden.", "trading", {"kind": "chart", "from": 0, "to": 1, "title": "???"}, {"kind": "title", "text": "REAL STOCKS. NO NAMES."}),
                              S(said, "city", {"kind": "question", "act": "spin"}),
                              S("You trade it blind for two minutes.", "home", {"kind": "person", "who": "sam", "pose": "point"}, {"kind": "phone", "brand": "Meme Street", "title": "???", "lines": ["BUY", "SELL"], "tap": True}),
                              S("Real prices, real crashes, real rallies.", "studio", {"kind": "arrow", "dir": "up", "text": "REAL", "act": "launch"}),
                              S("Then the name comes up, and you see if you read it right.", "stage", {"kind": "person", "who": "sam", "pose": "shock"}),
                              S("It's practice money, so the lessons are free.", "studio", {"kind": "money", "text": "$100K", "rain": True}), end]}
    return {"title": "The Same Stock Chart For Everyone Today: Can You Beat Your Friends?", "badge": ("Challenge", "#ff5d8f"), "lines": ["Beat your", "friends"],
            "choice": ("I'd win", "They'd win"), "cast": sam + [{"id": "jo", "tag": "JO", "look": "woman", "color": "#ff5d8f"}],
            "caption": "Everyone gets the same mystery stock chart on Meme Street today. Two minutes, $100,000 of practice money, buy, sell or short. Then compare your score with your friends'. No account, no app, no real money. Send this to the friend you'd beat: memestreet.net",
            "sentences": [S("Everyone gets the same stock chart today.", "trading", {"kind": "chart", "from": 0, "to": 1, "title": "???"}, {"kind": "title", "text": "SAME CHART. WHO WINS?"}),
                          S("Sam and Jo played it on the bus.", "city", {"kind": "person", "who": "sam", "pose": "point"}, {"kind": "person", "who": "jo", "pose": "hold"}),
                          S("Sam bought early, and held on.", "home", {"kind": "person", "who": "sam", "pose": "hold"}, {"kind": "arrow", "dir": "up", "text": "BUY", "act": "launch"}),
                          S("Jo shorted the spike, right at the top.", "office", {"kind": "person", "who": "jo", "pose": "point"}, {"kind": "arrow", "dir": "down", "text": "SHORT", "act": "drop"}),
                          S("Then the name came up, and the scores went side by side.", "stage", {"kind": "podium", "first": "jo", "second": "sam", "third": None}),
                          S("Jo won, and Sam wants a rematch tomorrow.", "home", {"kind": "person", "who": "sam", "pose": "sad"}),
                          S("Send this to the friend you'd beat.", "studio", {"kind": "phone", "brand": "Meme Street", "title": "SHARE", "lines": ["MY SCORE"], "tap": True, "act": "spin"}), end]}


def spec(date, slot, theme=None):
    st = day_data(date)
    if SLOTS[slot] == "teaser": return teaser(st), st, "teaser"
    theme = theme or THEMES[datetime.date.fromisoformat(date).toordinal() % len(THEMES)]
    p = promo(st, theme)
    return ({"title": p["title"], "mystery": True, "hud": False, "prices": "history", "cover": {"style": "top" if theme in ("howto", "real") else "bottom", "lines": p["lines"], "color": p["badge"][1]},
             "choice": {"kicker": "TODAY'S CHART IS LIVE", "a": p["choice"][0], "b": p["choice"][1], "cta": "Play free at memestreet.net"},
             "caption": p["caption"], "tags": TAGS, "brands": BRAND, "cast": p["cast"], "sentences": p["sentences"]}, st, theme)


def make(date, slot):
    """One promo reel made and queued for <date>T<slot>. -> the queue folder, or None if it was already there."""
    import news_reel as N
    q = os.path.join(M.ROOT, "queue", f"{date}T{slot}")
    if any(os.path.exists(os.path.join(q, f)) for f in (".auto", "posted.json")): return None
    import glob
    if glob.glob(os.path.join(M.ROOT, "queue-originals", f"{date}T{slot}*")): return None      # (a slot whose reel was taken out by hand stays the owner's: never re-made, 2026-11-25)
    tries = os.path.join(M.ROOT, "state", f"promo-{date}T{slot}.tries"); n = int(open(tries).read()) if os.path.exists(tries) else 0
    if n >= 3: M.say(f"{date}T{slot}: tried three times, not made"); return None
    os.makedirs(os.path.dirname(tries), exist_ok=True); open(tries, "w").write(str(n + 1))
    sp, st, kind = spec(date, slot, THEMES[(datetime.date.fromisoformat(date).toordinal() + n) % len(THEMES)] if slot == "1600" else None)   # (a retry takes the next theme)
    os.environ["EXPLAINER_TRACK"] = MUSIC.get(kind, "")
    work, out = (os.path.join(M.ROOT, x, f"promo-{date}T{slot}") for x in ("work", "out"))
    for d in (work, out): subprocess.run(["rm", "-rf", d]); os.makedirs(d)
    json.dump(sp, open(os.path.join(work, "spec.json"), "w", encoding="utf-8"), indent=1)
    R, wav = M.cut(sp, work, st); M.render(R, wav, work, out)
    open(os.path.join(out, "caption.txt"), "w", encoding="utf-8").write(M.caption_text(sp, st))
    json.dump({"by": "promo", "kind": kind, "note": "the owner, 2026-11-24: a 9am and a 4pm reel about the Daily every day"}, open(os.path.join(out, "approved.json"), "w"))
    return N.queue_out(out, f"{date}T{slot}", sp["title"])


def day(date):
    """The day's promo slots still ahead of us, the earlier first; a slot already past is skipped (never posted late)."""
    now = datetime.datetime.now(datetime.UTC)
    for slot in SLOTS:
        due = datetime.datetime.fromisoformat(f"{date}T{slot[:2]}:{slot[2:]}:00+00:00")
        if due < now: continue
        try: r = make(date, slot); M.say(f"{date}T{slot}:", r or "already queued")
        except (SystemExit, Exception) as e: M.say(f"{date}T{slot} not made: {e}")


def demo():
    st = {"number": 22, "day": "Today's", "stock": {}, "chart": [8.5, 9.9, 8.3, 9.4], "history": [8.5, 9.9, 8.3, 9.4], "span": "3 months", "yesterday": "Express"}
    t = teaser(st); assert t["sentences"][0]["say"].startswith("This stock went from $8.50 to $9.40") is False and "drifted" in t["sentences"][0]["say"] and "badge" not in t["cover"], t["sentences"][0]
    assert "crashed 90%" in teaser(dict(st, history=[30, 20, 3]))["sentences"][0]["say"] and "up 3 times" in teaser(dict(st, history=[3, 5, 9]))["sentences"][0]["say"]
    for th in THEMES:
        p = promo(st, th); assert 6 <= len(p["sentences"]) <= 10 and p["sentences"][-1]["say"].startswith("Today's chart is live"), th
        ids = {c["id"] for c in p["cast"]}
        for s in p["sentences"]:
            for it in s["scene"]["items"]:
                assert it["kind"] in M.KINDS or it["kind"] in M.FLAT, it
                assert not it.get("act") or it["act"] in M.ACTS, it
                assert it["kind"] != "person" or it["who"] in ids, it
                assert s["scene"]["bg"] in M.BGS
        assert sum(len(s["say"].split()) for s in p["sentences"]) <= 85, th
    assert "Express" in promo(st, "real")["sentences"][1]["say"] and money(9.0) == "$9" and money(25.4) == "$25" and span(datetime.date(2016, 4, 6), datetime.date(2016, 6, 30)) == "3 months"
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:] or ["demo"]
    if a[0] == "demo": demo()
    elif a[0] == "day": day(a[1] if len(a) > 1 else datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d"))
    elif a[0] == "spec": print(json.dumps(spec(a[1], a[2], a[3] if len(a) > 3 else None)[0], indent=1))
