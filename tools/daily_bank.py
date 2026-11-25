"""Builds the Daily's real charts: content/daily_real.json (the game's, one a day for a year: game/daily.py) and
memestreet_game/reels/src/daily_reel_charts.json (the reels': other stretches, so a reel never shows a chart the
game will play).

    python tools/daily_bank.py <dataset_43497.pq>     writes both (needs pyarrow)
    python tools/daily_bank.py demo                    self-check on made-up rows (no file, no pyarrow)

The source is OpenML dataset 43497, "5-years-historical-stock-quotes" (https://www.openml.org/d/43497), released as
"CC0: Public Domain": daily open, high, low, close and volume, split-adjusted, for every US stock that traded from
16 February 2016 to 12 February 2021. (Stooq and Yahoo forbid redistribution; this set does not.) Download it from
https://data.openml.org/datasets/0004/43497/dataset_43497.pq (123 MB).

A chart is HISTORY + LIVE trading days of one well-known stock (NAMES): the lead-in, then the two minutes, one day a
second. Only windows whose two minutes move a lot are kept (hi/lo of the closes >= 1.25), at most PER_TICKER a stock
and never two of one stock that overlap, at most COVID_SHARE covering the March 2020 crash, a third from each band of
BANDS (moderate, big, wild), drawn in a fixed shuffled order so every kind of stock comes up, and the famous moments
(MUST) always. N charts in all: a year before one repeats.

A chart holds its real candles, its stock and dates and what happened in those months; the game rebases the prices
while it plays (daily.rebased). The reels' charts are picked the same way from the windows that overlap none of the
game's (REEL_N of them, no famous moments forced: those belong to the game).
"""
import json
import math
import os
import random
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "content", "daily_real.json")
REEL_OUT = os.path.join(ROOT, "memestreet_game", "reels", "src", "daily_reel_charts.json")   # (the Daily's reel pipeline, 2026-11-18)
REEL_N = 300
STORY_OUT = os.path.join(ROOT, "memestreet_game", "reels", "src", "daily_story_charts.json")
# The crazy stories of real stocks (the owner, 2026-11-19: "you can tell crazy stories of crazy stocks etc, to make people
# engaged"): each is a stock, the day its story peaks, a one-line seed the researcher starts from (src/stock_story.py) and the
# idea an explainer reel teaches through it. Never a story about deaths, a disaster, health or an election (news_reel.EXCLUDE).
STORIES = [
    ("GME", "2021-01-27", "GameStop's short squeeze in January 2021, when retail traders on Reddit sent the stock from under 20 dollars to over 300 in weeks", "a short squeeze"),
    ("AMC", "2021-01-27", "AMC Entertainment's meme-stock rally in January 2021, while the cinema chain was fighting to avoid bankruptcy", "a meme stock"),
    ("KOSS", "2021-01-27", "Koss, a small headphone maker whose stock jumped more than 1,000 percent in a few days of January 2021", "a meme stock"),
    ("BB", "2021-01-27", "BlackBerry's meme rally in January 2021, years after its phones disappeared from shops", "a meme stock"),
    ("KODK", "2020-07-29", "Kodak's stock jump in July 2020 after a planned 765 million dollar US government loan to make drug ingredients, which was later put on hold", "a news spike"),
    ("NKLA", "2020-06-09", "Nikola's surge in June 2020 to a value above Ford's after listing through a SPAC, before it had sold a single truck", "a SPAC"),
    ("TSLA", "2020-08-31", "Tesla's 2020 run and its five-for-one stock split in August 2020", "a stock split"),
    ("TLRY", "2018-09-19", "Tilray's cannabis-stock frenzy in September 2018, when the shares briefly traded near 300 dollars in one day", "a bubble"),
    ("FB", "2018-07-26", "Facebook's record one-day loss of about 120 billion dollars in market value on 26 July 2018 after its earnings", "an earnings gap"),
    ("OSTK", "2020-08-01", "Overstock's 2020 rally of more than 1,000 percent, from under 3 dollars to over 100", "momentum"),
    ("NIO", "2020-07-01", "NIO's 2020 comeback from near-bankruptcy to a stock market darling", "a turnaround"),
    ("SPCE", "2020-02-20", "Virgin Galactic's rally in early 2020, when retail traders piled into the space-tourism stock", "hype"),
    ("PLUG", "2020-12-01", "Plug Power's 2020 hydrogen rally", "a theme rally"),
    ("MARA", "2021-01-08", "Marathon's surge as bitcoin topped 40,000 dollars in January 2021", "a crypto proxy"),
    ("RIOT", "2017-12-19", "Riot Blockchain's 2017 surge after a small biotech company renamed itself for the blockchain craze", "a name-change hype"),
    ("AMD", "2016-07-22", "AMD's 2016 comeback from under 2 dollars a share", "a turnaround"),
    ("NVDA", "2018-11-16", "Nvidia's late-2018 slump as the crypto-mining boom ended and unsold graphics chips piled up", "boom and bust"),
    ("OXY", "2020-04-20", "Oil stocks in April 2020, the month US oil futures went below zero", "negative oil prices"),
    ("WFC", "2016-09-08", "Wells Fargo's fake-accounts scandal in September 2016", "a scandal"),
    ("SNAP", "2017-03-02", "Snap's stock market debut in March 2017 and the slide that followed", "an IPO"),
    ("UBER", "2019-05-10", "Uber's stock market debut in May 2019, one of the biggest ever, and its fall", "an IPO"),
    ("BYND", "2019-07-26", "Beyond Meat's 2019 debut, when the shares rose more than 700 percent above the IPO price", "an IPO pop"),
    ("GE", "2018-06-19", "General Electric being dropped from the Dow Jones index in June 2018 after more than a hundred years", "an index exit"),
    ("CCL", "2020-03-16", "Carnival's share collapse in March 2020 when the cruise industry shut down", "a crash"),
    ("MSTR", "2020-12-01", "MicroStrategy using its company cash to buy bitcoin in 2020", "a bitcoin treasury"),
    ("PTON", "2020-09-11", "Peloton's 2020 boom as people bought exercise bikes for home", "a boom"),
]
HISTORY, LIVE = 60, 120
SPAN = HISTORY + LIVE
N, PER_TICKER, MIN_RANGE, COVID_SHARE, STEP = 366, 4, 1.25, 0.15, 5
BANDS = ((1.25, 1.5), (1.5, 2.0), (2.0, float("inf")))   # the two minutes' hi/lo: a third of the charts from each
# The timeframe of a candle, and the share of the bank in each (the owner, 2026-11-18: "the daily chart can be any time frame
# of trading"). The source has daily prices only, so the shortest candle is one day (the two minutes then cover about six
# months); intraday timeframes (1 day, 1 week, 14 days in two minutes) need a licensed intraday source: ROADMAP RM1.
TFS = {"1 day": 0.6, "2 days": 0.25, "1 week": 0.15}
GAP = {"1 day": 7, "2 days": 9, "1 week": 14}               # (days between two candles' starts beyond which a window is broken)
SEED = 43497                                               # the order of the charts and of the days

NAMES = {   # the stocks people have heard of (US listings that traded 2016-2021), ticker: the name shown at the end
    "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon", "GOOGL": "Alphabet", "FB": "Facebook",
    "NFLX": "Netflix", "NVDA": "Nvidia", "AMD": "AMD", "INTC": "Intel", "TSLA": "Tesla", "ZM": "Zoom",
    "SHOP": "Shopify", "SQ": "Square", "PYPL": "PayPal", "TWTR": "Twitter", "SNAP": "Snap", "UBER": "Uber",
    "LYFT": "Lyft", "SPOT": "Spotify", "ROKU": "Roku", "PTON": "Peloton", "ETSY": "Etsy", "DOCU": "DocuSign",
    "CRM": "Salesforce", "ADBE": "Adobe", "ORCL": "Oracle", "IBM": "IBM", "CSCO": "Cisco", "QCOM": "Qualcomm",
    "MU": "Micron", "BABA": "Alibaba", "JD": "JD.com", "NIO": "NIO", "BIDU": "Baidu", "PINS": "Pinterest",
    "TWLO": "Twilio", "OKTA": "Okta", "CRWD": "CrowdStrike", "NET": "Cloudflare", "DBX": "Dropbox", "GPRO": "GoPro",
    "BB": "BlackBerry", "NOK": "Nokia", "EA": "Electronic Arts", "ATVI": "Activision Blizzard",
    "TTWO": "Take-Two Interactive", "TDOC": "Teladoc", "CHWY": "Chewy", "W": "Wayfair", "OSTK": "Overstock",
    "GME": "GameStop", "AMC": "AMC Entertainment", "BBBY": "Bed Bath & Beyond", "KOSS": "Koss", "EXPR": "Express",
    "NKLA": "Nikola", "KODK": "Kodak", "SPCE": "Virgin Galactic", "BYND": "Beyond Meat", "PLUG": "Plug Power",
    "FCEL": "FuelCell Energy", "TLRY": "Tilray", "CGC": "Canopy Growth", "ACB": "Aurora Cannabis",
    "MARA": "Marathon", "RIOT": "Riot", "MSTR": "MicroStrategy",
    "WKHS": "Workhorse", "SNDL": "Sundial Growers", "FUBO": "fuboTV", "MRNA": "Moderna", "NVAX": "Novavax",
    "PFE": "Pfizer", "BNTX": "BioNTech", "JNJ": "Johnson & Johnson", "GILD": "Gilead", "INO": "Inovio",
    "VXRT": "Vaxart", "REGN": "Regeneron", "ABBV": "AbbVie", "LLY": "Eli Lilly", "MRK": "Merck", "CCL": "Carnival",
    "RCL": "Royal Caribbean", "NCLH": "Norwegian Cruise Line", "AAL": "American Airlines", "DAL": "Delta Air Lines",
    "UAL": "United Airlines", "LUV": "Southwest Airlines", "BA": "Boeing", "MAR": "Marriott", "EXPE": "Expedia",
    "BKNG": "Booking Holdings", "DIS": "Disney", "NKE": "Nike", "SBUX": "Starbucks", "MCD": "McDonald's",
    "KO": "Coca-Cola", "PEP": "PepsiCo", "WMT": "Walmart", "TGT": "Target", "COST": "Costco", "HD": "Home Depot",
    "CMG": "Chipotle", "DPZ": "Domino's", "LULU": "Lululemon", "UAA": "Under Armour", "GPS": "Gap", "M": "Macy's",
    "JWN": "Nordstrom", "KSS": "Kohl's", "JPM": "JPMorgan Chase", "BAC": "Bank of America", "GS": "Goldman Sachs",
    "MS": "Morgan Stanley", "WFC": "Wells Fargo", "C": "Citigroup", "V": "Visa", "MA": "Mastercard",
    "AXP": "American Express", "XOM": "ExxonMobil", "CVX": "Chevron", "OXY": "Occidental Petroleum",
    "SLB": "Schlumberger", "HAL": "Halliburton", "ENPH": "Enphase Energy", "FSLR": "First Solar",
    "SEDG": "SolarEdge", "GE": "General Electric", "CAT": "Caterpillar", "F": "Ford", "GM": "General Motors",
    "LMT": "Lockheed Martin", "MMM": "3M", "T": "AT&T", "VZ": "Verizon", "TMUS": "T-Mobile", "CHGG": "Chegg",
    "SPWR": "SunPower", "BLNK": "Blink Charging", "NNDM": "Nano Dimension",
    "TSM": "TSMC", "ASML": "ASML", "AVGO": "Broadcom", "TXN": "Texas Instruments", "PG": "Procter & Gamble",
    "MO": "Altria", "UNH": "UnitedHealth", "CVS": "CVS Health", "WBA": "Walgreens", "DKNG": "DraftKings",
    "PENN": "Penn National Gaming", "WYNN": "Wynn Resorts", "MGM": "MGM Resorts", "LVS": "Las Vegas Sands",
}
EVENTS = [   # (day, what happened[, only these stocks]): named at the end when it falls inside the two minutes
    ("2016-06-24", "the day after the UK voted to leave the EU"), ("2016-11-09", "the day after the US election"),
    ("2018-02-05", "the volatility crash of February 2018"), ("2018-12-24", "the Christmas Eve low of the 2018 sell-off"),
    ("2020-03-16", "the COVID crash of March 2020"),
    ("2020-04-20", "the day oil futures went below zero", ("XOM", "CVX", "OXY", "SLB", "HAL")),
    ("2020-11-09", "the first vaccine results (9 November 2020)"),
    ("2021-01-27", "the GameStop short squeeze", ("GME", "AMC", "BB", "NOK", "KOSS", "EXPR", "BBBY", "SNDL")),
    ("2018-07-26", "Facebook's record one-day fall (26 July 2018)", ("FB",)),
    ("2019-03-11", "the 737 MAX crash and grounding (March 2019)", ("BA",)),
    ("2020-05-18", "Moderna's first vaccine trial results (18 May 2020)", ("MRNA",)),
    ("2020-06-08", "Nikola's June 2020 spike", ("NKLA",)),
    ("2020-07-29", "Kodak's government loan news (July 2020)", ("KODK",)),
]
MUST = {"GME": "2021-01-27", "AMC": "2021-01-27", "TSLA": "2020-08-31", "ZM": "2020-03-23", "KODK": "2020-07-29", "NKLA": "2020-06-08",
        "CCL": "2020-03-16", "MRNA": "2020-05-18", "FB": "2018-07-26", "BA": "2019-03-11"}   # the famous moments, always in
COVID = "2020-03-16"


def bars(rows, tf):
    """Daily rows (date, o, h, l, c, v) as candles of the timeframe: (first day, o, h, l, c, v, last day)."""
    if tf == "1 day":
        return [r + (r[0],) for r in rows]
    groups = []
    for r in rows:
        key = date.fromisoformat(r[0]).isocalendar()[:2] if tf == "1 week" else None
        if groups and ((tf == "1 week" and groups[-1][0] == key) or (tf == "2 days" and len(groups[-1][1]) < 2)):
            groups[-1][1].append(r)
        else:
            groups.append((key, [r]))
    return [(g[0][0], g[0][1], max(x[2] for x in g), min(x[3] for x in g), g[-1][4], sum(x[5] for x in g), g[-1][0]) for _, g in groups]


def windows(sym, rows, tf="1 day"):
    """Every candidate window of one stock in one timeframe: rows are daily (date, o, h, l, c, v), oldest first. A window may
    not cross a gap (a halt or missing data) or hold a broken candle."""
    out = []
    rows = bars(rows, tf)
    step = STEP if tf == "1 day" else 2
    for s in range(0, len(rows) - SPAN + 1, step):
        w = rows[s:s + SPAN]
        if any((date.fromisoformat(b[0]) - date.fromisoformat(a[0])).days > GAP[tf] for a, b in zip(w, w[1:])):
            continue
        if any(not (r[3] > 0 and r[3] <= min(r[1], r[4]) and r[2] >= max(r[1], r[4])) for r in w):
            continue
        game = [r[4] for r in w[HISTORY:]]
        rng = max(game) / min(game)
        if rng >= 1.25:
            out.append({"t": sym, "tf": tf, "rng": rng, "a": w[HISTORY][0], "b": w[-1][6], "w": w})
    return out


def pick(cands, n=N, must=True):
    """The charts: a third from each band of BANDS, each band in a fixed shuffled order, the famous moments first, at
    most PER_TICKER a stock, never two of one stock overlapping, at most COVID_SHARE covering the March 2020 crash."""
    rng = random.Random(SEED)
    order = []
    for tf in TFS:
        for k, (lo, hi) in enumerate(BANDS):
            band = sorted((x for x in cands if x.get("tf", "1 day") == tf and lo <= x["rng"] < hi), key=lambda x: (x["t"], x["a"]))
            rng.shuffle(band)
            order += [((tf, k), x) for x in band]
    rng.shuffle(order)                               # (the timeframes and bands mixed, each drawn up to its quota)
    for t, day in (MUST.items() if must else ()):     # (each famous moment first, a daily chart, the day about three quarters into the two minutes)
        mine = [(k, x) for k, x in order if x["t"] == t and x.get("tf", "1 day") == "1 day" and x["a"] <= day <= x["b"]]
        at = lambda x: next(i for i, r in enumerate(x["w"]) if r[0] >= day) - HISTORY
        if mine:
            order.insert(0, order.pop(order.index(min(mine, key=lambda kx: abs(at(kx[1]) - 0.75 * LIVE)))))
    got, per, covid = [], {}, 0
    quota = {(tf, k): round(n * share / len(BANDS)) for tf, share in TFS.items() for k in range(len(BANDS))}
    for k, x in order + [(None, x) for _, x in order]:   # (a second pass fills what a short timeframe or band left over)
        if len(got) >= n:
            break
        if k is not None and quota[k] <= 0:
            continue
        if k is None and any(x is y for y in got):
            continue
        mine = per.setdefault(x["t"], [])
        if len(mine) >= PER_TICKER or any(not (x["w"][-1][6] < y["w"][0][0] or y["w"][-1][6] < x["w"][0][0]) for y in mine):
            continue
        hit = x["a"] <= COVID <= x["b"]
        if hit and covid >= COVID_SHARE * n:
            continue
        covid += hit
        if k is not None:
            quota[k] -= 1
        mine.append(x)
        got.append(x)
    return got


def entry(x):
    """One chart as the bank keeps it: ticker, name, [first day, first day of the two minutes, last day], the events
    inside the two minutes, and the real candles [open, high, low, close, volume]."""
    p = lambda v: round(v, 2 if v >= 10 else 4)
    return {"t": x["t"], "n": NAMES[x["t"]], "tf": x.get("tf", "1 day"), "d": [x["w"][0][0], x["a"], x["b"]],
            "e": [e[1] for e in EVENTS if x["a"] <= e[0] <= x["b"] and (len(e) < 3 or x["t"] in e[2])],
            "c": [[p(r[1]), p(r[2]), p(r[3]), p(r[4]), int(r[5])] for r in x["w"]]}


def write(got, path, what):
    got = sorted(got, key=lambda x: (x["t"], x["a"]))           # (the game's order of days comes from its own salt)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"source": "OpenML dataset 43497, '5-years-historical-stock-quotes' (https://www.openml.org/d/43497), CC0: Public Domain. "
                             "Daily prices, split-adjusted, 2016-02-16 to 2021-02-12. Built by tools/daily_bank.py.",
                   "for": what, "history": HISTORY, "live": LIVE, "charts": [entry(x) for x in got]}, f, separators=(",", ":"))


def apart(cands, got):
    """The windows that share no day with a chart of the same stock in `got`."""
    taken = {}
    for y in got:
        taken.setdefault(y["t"], []).append((y["w"][0][0], y["w"][-1][6]))
    return [x for x in cands if all(x["w"][-1][6] < a or b < x["w"][0][0] for a, b in taken.get(x["t"], []))]


def stories(by):
    """The story charts: about 100 trading days before each story's day and 40 after (fewer when the data ends), real prices."""
    out = []
    for t, day, seed, idea in STORIES:
        rows = sorted(by.get(t, []))
        k = next((i for i, r in enumerate(rows) if r[0] >= day), None)
        if k is None:
            print("story without data:", t, day); continue
        w = rows[max(0, k - 100):k + 40]
        if len(w) < 60:
            print("story too short:", t, day, len(w)); continue
        p = lambda v: round(v, 2 if v >= 10 else 4)
        out.append({"t": t, "n": NAMES[t], "day": day, "seed": seed, "idea": idea, "d": [w[0][0], w[-1][0]],
                    "peak": next(i for i, r in enumerate(w) if r[0] >= day),
                    "c": [[p(r[1]), p(r[2]), p(r[3]), p(r[4]), int(r[5])] for r in w]})
    with open(STORY_OUT, "w", encoding="utf-8") as f:
        json.dump({"source": "OpenML dataset 43497 (CC0: Public Domain), daily split-adjusted prices. Built by tools/daily_bank.py.",
                   "for": "the reels' crazy stock stories and explainers (src/stock_story.py)", "charts": out}, f, separators=(",", ":"))
    print(f"{len(out)} story charts -> {STORY_OUT}")


def build(path):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    T = pq.read_table(path, columns=["datetime", "open_price", "high_price", "low_price", "close_price", "volume", "symbol"])
    T = T.filter(pc.is_in(T.column("symbol"), value_set=pa.array(sorted(NAMES))))
    assert all(t in NAMES for t, *_ in STORIES)
    by = {}
    for r in T.to_pylist():
        by.setdefault(r["symbol"], []).append((r["datetime"][:10], r["open_price"], r["high_price"], r["low_price"], r["close_price"], r["volume"] or 0))
    print("not in the data:", sorted(set(NAMES) - set(by)))
    cands = [w for s, rows in by.items() for tf in TFS for w in windows(s, sorted(rows), tf)]
    got = pick(cands)
    print("famous moments missing:", sorted(t for t, day in MUST.items() if not any(x["t"] == t and x["a"] <= day <= x["b"] for x in got)))
    write(got, OUT, "the game")
    reel = pick(apart(cands, got), REEL_N, must=False)
    write(reel, REEL_OUT, "the reels")
    stories(by)
    for g, f in ((got, OUT), (reel, REEL_OUT)):
        print({tf: sum(x.get("tf") == tf for x in g) for tf in TFS})
        print(f"{len(g)} charts from {len({x['t'] for x in g})} stocks, {sum(x['a'] <= COVID <= x['b'] for x in g)} over the "
              f"COVID crash, median move {sorted(x['rng'] for x in g)[len(g) // 2]:.2f}x hi/lo, {os.path.getsize(f) // 1024} KB -> {f}")


def demo():
    import tempfile
    days = [date.fromordinal(date(2016, 3, 1).toordinal() + k) for k in range(900)]
    days = [d.isoformat() for d in days if d.weekday() < 5]
    rows = lambda f: [(d, f(i), f(i) * 1.02, f(i) * 0.98, f(i) * 1.01, 1000) for i, d in enumerate(days)]
    assert not windows("AAPL", rows(lambda i: 100.0))                                          # a dull stock gives nothing
    wave = rows(lambda i: 100 * math.exp(math.sin(i / 20)))
    del wave[100:110]
    wild = windows("TSLA", wave)
    assert wild and all(len(w["w"]) == SPAN for w in wild)
    assert all(not (w["w"][0][0] <= wave[99][0] < w["w"][-1][6]) for w in wild)               # never across a gap
    wk = bars(rows(lambda i: 100.0 + i), "1 week")
    assert all(date.fromisoformat(c[0]).isocalendar()[:2] == date.fromisoformat(c[6]).isocalendar()[:2] for c in wk) and wk[1][4] > wk[0][4]
    two = bars(rows(lambda i: 100.0 + i), "2 days")
    assert len(two) == (len(days) + 1) // 2 and two[0][2] == max(100 * 1.02, 101 * 1.02) and two[0][5] == 2000   # (high of both, volume summed)
    long_days = [d.isoformat() for d in (date.fromordinal(date(2016, 3, 1).toordinal() + k) for k in range(1500)) if d.weekday() < 5]
    lw = [(d, 100 * math.exp(math.sin(i / 25)), 100 * math.exp(math.sin(i / 25)) * 1.02, 100 * math.exp(math.sin(i / 25)) * 0.98,
           100 * math.exp(math.sin(i / 25)) * 1.01, 1000) for i, d in enumerate(long_days)]
    assert windows("TSLA", lw, "1 week")[0]["tf"] == "1 week"
    got = pick(wild + windows("NVDA", rows(lambda i: 100 * math.exp(math.cos(i / 15)))), n=50)
    for t in ("TSLA", "NVDA"):
        mine = sorted((x for x in got if x["t"] == t), key=lambda x: x["w"][0][0])
        assert 0 < len(mine) <= PER_TICKER and all(a["w"][-1][6] < b["w"][0][0] for a, b in zip(mine, mine[1:]))   # no overlaps
    e = entry(got[0])
    assert len(e["c"]) == SPAN and e["n"] in NAMES.values() and e["d"] == [got[0]["w"][0][0], got[0]["a"], got[0]["b"]]
    t0 = next(x for x in got if x["t"] == "TSLA")
    other = apart(wild, [t0])
    assert other and len(other) < len(wild) and all(x["w"][-1][6] < t0["w"][0][0] or t0["w"][-1][6] < x["w"][0][0] for x in other)   # the reels' share no day
    with tempfile.TemporaryDirectory() as td:
        write(got, os.path.join(td, "b.json"), "test")
        b = json.load(open(os.path.join(td, "b.json")))
        assert b["history"] == HISTORY and len(b["charts"]) == len(got)
    print("ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["demo"] else build(sys.argv[1])
