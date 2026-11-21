"""The Daily's game reels, filmed in the 3D town (the owner, 2026-11-21: "they should be more 3d animation style"; the town's
reels have a median of 1,160 views against about 120 for the flat ones: state/reel_ledger.json).

The slot's own format and facts (make_spec.brief: Yesterday's stock, Guess the stock, Beat the chart) are written in the town's
shot grammar (story_reel.WHAT), with the REAL chart on the square's screen (world3d.js: "screen": {"real": 0, "from", "to"}),
then voiced, rendered, reviewed and queued like every reel.

  python3 src/town_daily.py slot <YYYY-MM-DDTHHMM> [category]   make and queue it (exit 1 when it is not made: auto_reel.sh then makes the flat one)
  python3 src/town_daily.py demo                               the self-check: no Claude, no voice
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import make_spec as M, story_reel as S, world as W

FORMATS = (M.YESTERDAY, M.GUESS, M.BEAT)                  # (Higher or lower needs a countdown on the board: not filmed in the town yet)
SUFFIX = " 3D"                                             # (the saved type, so the ledger tells the town's reels from the flat ones)
CAST = {"the narrator (I)": "grey-blue shirt #8a96ab, dark blue trousers #2e3a52, brown hair #6b4426, skin #f1c27d: the player the viewer follows",
        "the holder": "green hoodie #43b05c, cap: buys at the start and never sells",
        "the panic seller": "red jacket #e2504a, wide eyes: sells the moment it drops"}


def what(fmt):
    """The brief of one game reel in the town: the real screen, the players' chests, the serial's shot grammar, the format's own rules."""
    w = S.WHAT
    grammar = w[w.index("THE LOOK"):w.index("THE STORY:")]
    return ("THE DAILY'S GAME, FILMED IN THE BLOCKY TOWN (the owner, 2026-11-21: 'they should be more 3d animation style'): this is a '"
            + fmt + "' reel (its rules are under THE FORMAT below), acted out by townspeople in the town square. "
            "THE REAL CHART is on the square's big screen: \"screen\": {\"title\": \"MYSTERY STOCK\", \"real\": 0, \"from\": N, \"to\": M, "
            "\"pct\"?: \"+12%\", \"level\"?: a real price, \"buy\"?: a candle number, \"sell\"?: a candle number}, in a shot with \"place\": "
            "\"square\" (cam \"screen\" fills the frame with the board; a wide or mid shot shows the people under it). The board holds "
            "the 45 candles up to \"to\" and draws those from \"from\" to \"to\" as the shot runs, so each screen shot carries the chart "
            "on from the candle where the last one stopped (facts.charts gives the candle numbers; the game's two minutes start at "
            "candle facts.lead_in_candles, one candle a second). Candle numbers, prices and percentages come only from the facts. A "
            "real chart and a made-up \"chart\" never share a screen. "
            "THE PLAYERS are townspeople: the number on a chest is that player's practice account (it starts at facts.practice_money; "
            "facts.players says what each did and finished with), the same in every shot until the line moves it, and it counts up or "
            "crashes on the very word that says so. The crowd in the square gasps, cheers and groans with the chart. The stock's name "
            "stays off every screen until the reveal: then the board shows it, {\"text\": \"NAME|TICKER\", \"tone\": \"gold\"} (the "
            "serial's rule of made-up names does not apply: the reveal is the real stock, exactly as facts.reveal names it). A guess "
            "reel puts its options up as {\"title\": \"WHICH STOCK?\", \"lines\": [the three of facts.options]}. "
            + grammar +
            "THE FORMAT (what is told and where each fact comes from; ignore what it says about cards, tags, a HUD, a price tag or a "
            "scene function: here the town's shots are the picture): " + M.CATEGORIES[fmt] +
            " TOLD AS A STORY, never a commentary: one player the viewer can name and what they want, the chart in their way, a turn "
            "at a real candle, the payoff; a new shot about every 2 seconds, and the thing each line names is shown as it is said. "
            "\"type\" is \"Blocky story\". Every scene is of kind \"free\" but the outro, whose line is \"Today's stock is live. Play it "
            "at memestreet.net.\" The caption: line 1 is the hook as a question to the viewer, under 125 characters; two or three short "
            "lines that give away nothing before the reveal; 'Play today's stock at memestreet.net'; '" + M.DISCLAIMER + "'; 3 to 5 hashtags.")


def brief(slot, category=None):
    """The slot's own brief (its format, facts and real chart), turned to the town. -> (B, the format) or (None, the format)."""
    os.environ["REEL_SLOT"] = slot                         # (Yesterday's stock reads the Daily of the day before this slot: as auto_reel.sh sets it)
    B0 = M.brief(slot, category)
    fmt = B0["category"]
    if fmt not in FORMATS: return None, fmt
    facts = dict(B0["ask"]["facts"], story={"cast": CAST}, example=W.example(), video={"available": False})
    ask = dict(B0["ask"], category=S.CATEGORY, what_this_reel_is=what(fmt), facts=facts)
    return {"slot": slot, "category": S.CATEGORY, "system": M.system_prompt(S.CATEGORY), "ask": ask, "charts": B0["charts"]}, fmt


def make(slot, category=None):
    """One game reel in the town: written, voiced, rendered, reviewed, queued in its slot. -> the slot, or None."""
    import news_reel as N
    B, fmt = brief(slot, category)
    if not B:
        print(f"{fmt} is not filmed in the town: the flat reel is made", flush=True); return None
    work, out = os.path.join(ROOT, "work", "auto-" + slot), os.path.join(ROOT, "out", "auto-" + slot)
    subprocess.run(["rm", "-rf", work, out], check=True)
    spec = M.write(B, work=work)
    spec.update({k: v for k, v in S.STYLE.items() if not k.startswith("voice")}, scene_js=W.JS, part=None, series="")   # (the town and its tune; the house voice)
    M.save(spec, B, work)
    r = subprocess.run([sys.executable, os.path.join(HERE, "critic.py"), "loop", work, out], cwd=ROOT,
                       env=dict(os.environ, STEP_TIMEOUT=os.environ.get("STORY_STEP_TIMEOUT", "6000")))   # (a 3D render of 40 s took 39 minutes on the server)
    if r.returncode or not os.path.exists(os.path.join(out, "approved.json")):
        print("the town's reel was not finished: the flat reel is made", flush=True); return None
    p = os.path.join(work, "spec.json"); final = json.load(open(p, encoding="utf-8")); final["type"] = fmt + SUFFIX
    json.dump(final, open(p, "w", encoding="utf-8"))
    return N.queue_out(out, slot, final.get("title", ""))


def demo():
    for f in FORMATS:
        t = what(f)
        assert "\"real\": 0" in t and "THE LOOK" in t and "THE FORMAT" in t and M.CATEGORIES[f][:60] in t and "%(" not in t and M.DISCLAIMER in t
    assert M.HILO not in FORMATS and S.CATEGORY in M.CATEGORIES and M.LENGTH[S.CATEGORY][2]
    C = [{"candles": [[1, 2, 1, 2, 0]] * 180, "label": "Mystery stock", "live_from": 60}]
    spec = {"title": "T", "type": S.CATEGORY, "device": {"metaphor": "chest labels"}, "caption": "c", "scenes": [
        {"kind": "free", "text": "It fell hard", "vo": "It fell hard in the first ten days.", "shots": [
            {"place": "square", "cam": "screen", "screen": {"title": "MYSTERY STOCK", "real": 0, "from": 60, "to": 70}},
            {"say": "ten days", "place": "square", "cam": "close:narrator", "actors": [{"who": "narrator", "at": [0, 0], "chest": [100000, 91000]}]}]}]}
    assert W.check(spec, C) == [] and W.check(spec) != []            # (the real screen needs the reel's chart)
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:] or ["demo"]
    if a[0] == "demo": demo()
    elif a[0] == "slot" and len(a) > 1: sys.exit(0 if make(a[1], a[2] if len(a) > 2 else None) else 1)
    else: raise SystemExit(__doc__)
