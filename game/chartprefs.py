"""A player's chart set-up, kept on the server so it follows them from one browser or phone to another (ROADMAP TA-B3
and TA-B4): which indicators are on and their settings (period, source, colour), the chart type and price scale, and the
drawings on each stock.

The page owns the meaning of all this (the indicator list and the drawing tools live in web/index.html); the server only
keeps it, and checks its shape and size first, because whatever a player sends is shown back to them: names are short
lower-case ids, colours are #rrggbb, numbers are finite and in range, text is short, and nothing is kept that is not
listed here. A player who is not signed in keeps it all in the browser only.
"""
import json
import math
import re

ID_RE = re.compile(r"^[a-z0-9_]{1,24}$")
TICKER_RE = re.compile(r"^[A-Z0-9]{1,8}$")
DRAW_ID_RE = re.compile(r"^[a-z0-9]{1,16}$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
CHART_TYPES = ("candles", "hollow", "bars", "line", "ha")
SOURCES = ("c", "o", "h", "l", "hl2", "hlc3", "ohlc4")
DRAW_TYPES = ("hline", "vline", "trend", "ray", "rect", "circle", "fib", "fibext", "channel", "brush", "path", "hs",
              "long", "short", "text")
MAX_INDICATORS = 60
MAX_DRAWINGS = 80             # per stock (the page keeps the newest 80 too)
MAX_STOCKS = 100              # stocks with drawings; beyond that the ones changed longest ago are dropped
MAX_POINTS = 400              # a brush stroke
MAX_TEXT = 80


def init_player(p):
    p.chart = {"prefs": {}, "draw": {}}


def dump_player(p):
    return p.chart


def load_player(p, x):
    prefs, _ = clean_prefs((x or {}).get("prefs", {}))
    draw = {}
    for tk, lst in dict((x or {}).get("draw", {})).items():
        ok, _ = clean_drawings(lst)
        if TICKER_RE.match(str(tk)) and ok is not None:
            draw[str(tk)] = ok
    p.chart = {"prefs": prefs or {}, "draw": draw}


def _num(v, lo, hi, integer=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        return None
    if integer and v != int(v):
        return None
    return int(v) if integer else float(v)


def clean_prefs(d):
    """(clean prefs, None) or (None, why)."""
    if not isinstance(d, dict):
        return None, "Chart settings must be an object"
    out = {}
    ind = d.get("ind", [])
    if not isinstance(ind, list) or len(ind) > MAX_INDICATORS or not all(isinstance(k, str) and ID_RE.match(k) for k in ind):
        return None, "Bad indicator list"
    out["ind"] = list(dict.fromkeys(ind))
    sets = d.get("set", {})
    if not isinstance(sets, dict) or len(sets) > MAX_INDICATORS:
        return None, "Bad indicator settings"
    out["set"] = {}
    for k, v in sets.items():
        if not (isinstance(k, str) and ID_RE.match(k) and isinstance(v, dict)):
            return None, "Bad indicator settings"
        one = {}
        for name in ("n", "m", "s"):
            if name in v:
                x = _num(v[name], 1, 500, integer=True)
                if x is None:
                    return None, f"{k}: {name} must be a whole number from 1 to 500"
                one[name] = x
        if "k" in v:
            x = _num(v["k"], 0.01, 20)
            if x is None:
                return None, f"{k}: k must be a number from 0.01 to 20"
            one["k"] = x
        if "src" in v:
            if v["src"] not in SOURCES:
                return None, f"{k}: unknown source"
            one["src"] = v["src"]
        if "c" in v:
            if not (isinstance(v["c"], str) and COLOR_RE.match(v["c"])):
                return None, f"{k}: colours are #rrggbb"
            one["c"] = v["c"].lower()
        if one:
            out["set"][k] = one
    if "ctype" in d:
        if d["ctype"] not in CHART_TYPES:
            return None, "Unknown chart type"
        out["ctype"] = d["ctype"]
    if "log" in d:
        if not isinstance(d["log"], bool):
            return None, "log must be true or false"
        out["log"] = d["log"]
    if "trades" in d:
        if not isinstance(d["trades"], bool):
            return None, "trades must be true or false"
        out["trades"] = d["trades"]
    return out, None


def clean_drawings(lst):
    """(clean list, None) or (None, why)."""
    if not isinstance(lst, list) or len(lst) > MAX_DRAWINGS:
        return None, f"At most {MAX_DRAWINGS} drawings on one stock"
    out = []
    for d in lst:
        if not isinstance(d, dict) or d.get("type") not in DRAW_TYPES:
            return None, "Unknown drawing"
        did = str(d.get("id", ""))
        pts = d.get("pts")
        if not DRAW_ID_RE.match(did) or not isinstance(pts, list) or not 1 <= len(pts) <= MAX_POINTS:
            return None, "Bad drawing"
        clean_pts = []
        for pt in pts:
            if not isinstance(pt, dict):
                return None, "Bad point"
            t, pr = _num(pt.get("t"), 0, 1e11), _num(pt.get("p"), 1e-9, 1e12)
            if t is None or pr is None:
                return None, "Bad point"
            clean_pts.append({"t": t, "p": pr})
        one = {"id": did, "type": d["type"], "pts": clean_pts}
        if "text" in d:
            if not isinstance(d["text"], str) or len(d["text"]) > MAX_TEXT:
                return None, f"A note is at most {MAX_TEXT} characters"
            one["text"] = d["text"]
        if "c" in d:
            if not (isinstance(d["c"], str) and COLOR_RE.match(d["c"])):
                return None, "Colours are #rrggbb"
            one["c"] = d["c"].lower()
        out.append(one)
    return out, None


class ChartsMixin:
    """Mixed into the Engine."""

    def chart_prefs(self, p):
        return {"prefs": p.chart.get("prefs", {})}

    def set_chart_prefs(self, p, d):
        prefs, err = clean_prefs(d)
        if err:
            return False, err
        if len(json.dumps(prefs)) > 16000:
            return False, "Too many settings"
        p.chart["prefs"] = prefs
        return True, "Saved"

    def drawings(self, p, ticker):
        if not TICKER_RE.match(ticker or ""):
            return {"error": "Unknown ticker"}
        return {"ticker": ticker, "drawings": p.chart["draw"].get(ticker, []), "saved": ticker in p.chart["draw"]}

    def set_drawings(self, p, ticker, lst):
        if not TICKER_RE.match(ticker or ""):
            return False, "Unknown ticker"
        clean, err = clean_drawings(lst)
        if err:
            return False, err
        draw = p.chart["draw"]
        draw.pop(ticker, None)                       # (re-inserted last: the dict keeps the most recently changed at the end)
        if clean:
            draw[ticker] = clean
        while len(draw) > MAX_STOCKS:
            draw.pop(next(iter(draw)))
        return True, "Saved"
