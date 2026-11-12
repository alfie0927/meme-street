"""Builds the game-portal uploads (docs/ROADMAP.md, RC8) into growth/portals/:

  daily_standalone.html   tools/portal_daily.html with charts baked in: one file, no server, no outside address.
  daily_standalone.zip    The same file as index.html (CrazyGames, Coolmath Games, Playgama, Y8).
  daily_itch.zip          One page that frames the live Daily at /embed/daily?ref=itch (itch.io; needs P2 live).

  python tools/portal_build.py                 build
  python tools/portal_build.py --check [dir]   build, then play games in a headless browser against game/daily.py's
                                               rules (needs Playwright); screenshots go to dir if one is given
"""
import json, os, random, sys, types, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import daily     # noqa: E402  (the chart maker and the rules; never `import server`, which opens the real save)

OUT = os.path.join(ROOT, "growth", "portals")
SEEDS = range(7001, 7031)     # thirty charts. A live day's seed comes from the server's secret salt, so none of these is one.
ITCH = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Chart by Meme Street</title>
<style>html,body{height:100%;margin:0;background:#0a0d11}iframe{border:0;width:100%;height:100%;display:block}</style></head>
<body><iframe src="https://memestreet.net/embed/daily?ref=itch" title="Daily Chart: the two-minute trading game" allow="clipboard-write; web-share" allowfullscreen></iframe></body></html>
"""


def build():
    charts = [[c[:4] for c in daily.make_chart(s)["candles"]] for s in SEEDS]
    page = open(os.path.join(ROOT, "tools", "portal_daily.html"), encoding="utf-8").read()
    assert page.count("/*CHARTS*/[]") == 1, "the CHARTS marker is gone from tools/portal_daily.html"
    page = page.replace("/*CHARTS*/[]", json.dumps(charts, separators=(",", ":")))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "daily_standalone.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    for name, html in (("daily_standalone", page), ("daily_itch", ITCH)):
        with zipfile.ZipFile(os.path.join(OUT, name + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(zipfile.ZipInfo("index.html", (2026, 11, 11, 0, 0, 0)), html, zipfile.ZIP_DEFLATED)   # (a fixed date: the same build gives the same file)
    return charts


class _Ref(daily.DailyMixin):
    """game/daily.py's own rules with no engine round them: one play on one chart."""
    def __init__(self, candles):
        self.now, self.daily_game = 0, {"chart": {"candles": candles}}
        self.play = {"t0": 0, "cash": daily.START_CASH, "shares": 0.0, "trades": []}
    def _dchart(self): return self.daily_game
    def _dplays(self, p): return {None: self.play}
    def _daily_state(self, play, since=0): return {}
    def _daily_record(self, play): pass


def reference(candles, script):
    r, who, errs = _Ref(candles), types.SimpleNamespace(token=None), []
    for sec, side, pct in script:
        r.now = sec
        errs.append(r.daily_trade(who, side, pct).get("error", ""))
    r.now = daily.LIVE
    r._daily_finish(r.play)
    return {"cash": r.play["cash"], "shares": r.play["shares"], "ret": r.play["ret"], "errs": errs,
            "grid": daily.DailyMixin._daily_grid(r.play, candles), "trades": r.play["trades"]}


def check(charts, shots=None):
    from playwright.sync_api import sync_playwright
    rng, close = random.Random(1), lambda a, b: abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))
    scripts = [[[0, "buy", 1.0], [5, "buy", 1.0], [30, "sell", 0.5], [30, "sell", 1.0], [31, "sell", 1.0], [40, "sell", 1.0], [90, "buy", 0.25], [119, "buy", 1.0]]]
    scripts += [sorted([rng.randrange(daily.LIVE), rng.choice(("buy", "sell")), rng.choice(daily.CHIPS)] for _ in range(rng.randrange(0, 14))) for _ in range(len(charts) - 1)]
    url = "file:///" + os.path.join(OUT, "daily_standalone.html").replace("\\", "/")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 960, "height": 600})
        bad, asked = [], []
        pg.on("pageerror", lambda e: bad.append(str(e)))
        pg.on("console", lambda m: m.type == "error" and bad.append(m.text))
        pg.on("request", lambda r: asked.append(r.url))
        pg.goto(url)
        kinds = set()
        for ci, sc in enumerate(scripts):                      # the rules: every chart, a scripted game, both sides
            want, got = reference(charts[ci], sc), pg.evaluate("([ci, sc]) => replay(ci, sc)", [ci, sc])
            assert got["grid"] == want["grid"] and got["errs"] == want["errs"], (ci, sc, got, want)
            assert all(close(got[k], want[k]) for k in ("cash", "shares", "ret")), (ci, sc, got, want)
            assert len(got["trades"]) == len(want["trades"]) and all(a[:2] == b[:2] and close(a[2], b[2]) and close(a[3], b[3]) for a, b in zip(got["trades"], want["trades"])), (ci, sc)
            kinds |= {t[1] for t in want["trades"]} | {e for e in want["errs"] if e}
        assert len(kinds) == 6, kinds                           # buy, sell, short, cover and both refusals were all played
        shot = lambda name: shots and (pg.wait_for_timeout(300), pg.screenshot(path=os.path.join(shots, name)))   # (a tick first: the page redraws ten times a second)
        shot("portal_1_intro.png")
        pg.click("#play")                                       # the page: Play, a trade, the label that follows it, the end
        assert pg.get_attribute("#app", "class") == "s-game"
        pg.click("#chips button:nth-child(2)")
        pg.click("#buy")
        assert pg.inner_text("#sell-l") == "Sell" and pg.evaluate("g.trades.length") == 1 and close(pg.evaluate("g.cash"), 500.0)
        pg.evaluate("t0 -= 60000")
        pg.wait_for_function("shown() >= 120")
        pg.keyboard.press("s")
        shot("portal_2_game.png")
        pg.evaluate("t0 -= 61000")
        pg.wait_for_selector("#app.s-end")
        assert pg.locator("#grid i").count() == daily.SQUARES and "%" in pg.inner_text("#e-ret")
        shot("portal_3_end.png")
        pg.set_viewport_size({"width": 390, "height": 700})
        pg.click("#again")
        pg.keyboard.press("s")
        assert pg.inner_text("#buy-l") == "Cover"
        pg.evaluate("t0 -= 45000")
        pg.wait_for_function("shown() >= 105")
        shot("portal_4_phone.png")
        b.close()
    assert not bad, bad
    assert asked == [url], asked                                # the file asks the network for nothing
    print(f"check passed: {len(scripts)} games match game/daily.py; the page plays; no request left the file")


if __name__ == "__main__":
    cs = build()
    print("built", ", ".join(f"{n} ({os.path.getsize(os.path.join(OUT, n)) // 1024} KB)" for n in sorted(os.listdir(OUT)) if n.startswith("daily_")))
    if "--check" in sys.argv:
        check(cs, next((a for a in sys.argv[1:] if not a.startswith("--")), None))
