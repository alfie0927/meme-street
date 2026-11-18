"""Builds the game's real charts: charts/<k>.json, one per day of the year, and charts/meta.json.

    python build_charts.py <dataset_43497.pq>     writes charts/ (needs pyarrow)
    python build_charts.py demo                    self-check on made-up rows (no file, no pyarrow)

The source is OpenML dataset 43497, "5-years-historical-stock-quotes" (https://www.openml.org/d/43497), released as
"CC0: Public Domain": daily open, high, low, close and volume, split-adjusted, for every US stock that traded from
16 February 2016 to 12 February 2021. (Stooq and Yahoo forbid redistribution; this set does not.) Download it from
https://data.openml.org/datasets/0004/43497/dataset_43497.pq (123 MB).

A chart is HISTORY + LIVE trading days of one well-known stock (NAMES): the lead-in, then the two minutes, one day a
second. Only windows whose two minutes move a lot are kept (hi/lo of the closes >= 1.25), at most PER_TICKER a stock
and never two of one stock that overlap, at most COVID_SHARE covering the March 2020 crash, a third from each band of
BANDS (moderate, big, wild), drawn in a fixed shuffled order so every kind of stock comes up, and the famous moments
(MUST) always. N charts in all: a year before one repeats.

Each file holds the candles rebased so the last lead-in close is 100 (the price level gives nothing away; volume is
relative) and, base64-encoded so a glance at the file does not spoil it, what the end of the game reveals: the stock,
its dates, the factor back to real prices, its real first and last close, and what happened in those months.
"""
import base64
import json
import math
import os
import random
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "charts")
HISTORY, LIVE = 60, 120
SPAN = HISTORY + LIVE
N, PER_TICKER, MIN_RANGE, COVID_SHARE, STEP = 366, 4, 1.25, 0.15, 5
BANDS = ((1.25, 1.5), (1.5, 2.0), (2.0, float("inf")))   # the two minutes' hi/lo: a third of the charts from each
SEED = 43497                                               # the order of the charts and of the days

NAMES = {   # the stocks people have heard of (US listings that traded 2016-2021), ticker: the name shown at the end
    "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon", "GOOGL": "Alphabet (Google)", "FB": "Facebook",
    "NFLX": "Netflix", "NVDA": "Nvidia", "AMD": "AMD", "INTC": "Intel", "TSLA": "Tesla", "ZM": "Zoom",
    "SHOP": "Shopify", "SQ": "Square", "PYPL": "PayPal", "TWTR": "Twitter", "SNAP": "Snap (Snapchat)", "UBER": "Uber",
    "LYFT": "Lyft", "SPOT": "Spotify", "ROKU": "Roku", "PTON": "Peloton", "ETSY": "Etsy", "DOCU": "DocuSign",
    "CRM": "Salesforce", "ADBE": "Adobe", "ORCL": "Oracle", "IBM": "IBM", "CSCO": "Cisco", "QCOM": "Qualcomm",
    "MU": "Micron", "BABA": "Alibaba", "JD": "JD.com", "NIO": "NIO", "BIDU": "Baidu", "PINS": "Pinterest",
    "TWLO": "Twilio", "OKTA": "Okta", "CRWD": "CrowdStrike", "NET": "Cloudflare", "DBX": "Dropbox", "GPRO": "GoPro",
    "BB": "BlackBerry", "NOK": "Nokia", "EA": "Electronic Arts", "ATVI": "Activision Blizzard",
    "TTWO": "Take-Two Interactive", "TDOC": "Teladoc", "CHWY": "Chewy", "W": "Wayfair", "OSTK": "Overstock",
    "GME": "GameStop", "AMC": "AMC Entertainment", "BBBY": "Bed Bath & Beyond", "KOSS": "Koss", "EXPR": "Express",
    "NKLA": "Nikola", "KODK": "Kodak", "SPCE": "Virgin Galactic", "BYND": "Beyond Meat", "PLUG": "Plug Power",
    "FCEL": "FuelCell Energy", "TLRY": "Tilray", "CGC": "Canopy Growth", "ACB": "Aurora Cannabis",
    "MARA": "Marathon (bitcoin miner)", "RIOT": "Riot (bitcoin miner)", "MSTR": "MicroStrategy",
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


def windows(sym, rows):
    """Every candidate window of one stock: rows are (date, o, h, l, c, v), oldest first. A window may not cross a gap of
    more than a week (a halt or missing data) or hold a broken candle."""
    out = []
    for s in range(0, len(rows) - SPAN + 1, STEP):
        w = rows[s:s + SPAN]
        if any((date.fromisoformat(b[0]) - date.fromisoformat(a[0])).days > 7 for a, b in zip(w, w[1:])):
            continue
        if any(not (r[3] > 0 and r[3] <= min(r[1], r[4]) and r[2] >= max(r[1], r[4])) for r in w):
            continue
        game = [r[4] for r in w[HISTORY:]]
        rng = max(game) / min(game)
        if rng >= 1.25:
            out.append({"t": sym, "rng": rng, "a": w[HISTORY][0], "b": w[-1][0], "w": w})
    return out


def pick(cands, n=N):
    """The charts: a third from each band of BANDS, each band in a fixed shuffled order, the famous moments first, at
    most PER_TICKER a stock, never two of one stock overlapping, at most COVID_SHARE covering the March 2020 crash."""
    rng = random.Random(SEED)
    order = []
    for k, (lo, hi) in enumerate(BANDS):
        band = sorted((x for x in cands if lo <= x["rng"] < hi), key=lambda x: (x["t"], x["a"]))
        rng.shuffle(band)
        order += [(k, x) for x in band]
    for t, day in MUST.items():                      # (each famous moment first, the day about three quarters into the two minutes)
        mine = [(k, x) for k, x in order if x["t"] == t and x["a"] <= day <= x["b"]]
        at = lambda x: next(i for i, r in enumerate(x["w"]) if r[0] >= day) - HISTORY
        if mine:
            order.insert(0, order.pop(order.index(min(mine, key=lambda kx: abs(at(kx[1]) - 0.75 * LIVE)))))
    got, per, covid = [], {}, 0
    quota = [n // len(BANDS) + (k < n % len(BANDS)) for k in range(len(BANDS))]
    for k, x in order:
        if len(got) >= n:
            break
        if quota[k] <= 0:
            continue
        mine = per.setdefault(x["t"], [])
        if len(mine) >= PER_TICKER or any(not (x["w"][-1][0] < y["w"][0][0] or y["w"][-1][0] < x["w"][0][0]) for y in mine):
            continue
        hit = x["a"] <= COVID <= x["b"]
        if hit and covid >= COVID_SHARE * n:
            continue
        covid += hit
        quota[k] -= 1
        mine.append(x)
        got.append(x)
    return got


def chart(x):
    """One day's file: the rebased candles and the encoded reveal."""
    w = x["w"]
    k = w[HISTORY - 1][4] / 100.0
    vols = sorted(r[5] for r in w)
    vm = max(vols[len(vols) // 2], 1)
    reveal = {"ticker": x["t"], "name": NAMES[x["t"]], "from": w[0][0], "start": x["a"], "end": x["b"], "k": k,
              "first": w[HISTORY - 1][4], "last": w[-1][4],
              "events": [e[1] for e in EVENTS if x["a"] <= e[0] <= x["b"] and (len(e) < 3 or x["t"] in e[2])]}
    return {"c": [[round(r[1] / k, 2), round(r[2] / k, 2), round(r[3] / k, 2), round(r[4] / k, 2), int(r[5] / vm * 100)] for r in w],
            "r": base64.b64encode(json.dumps(reveal, separators=(",", ":")).encode("utf-8")).decode("ascii")}


def write(got, out=OUT):
    """charts/<k>.json for day k of the cycle (the page takes day number - 1 modulo n), in an order the seed shuffles."""
    got = sorted(got, key=lambda x: (x["t"], x["a"]))
    random.Random(SEED + 1).shuffle(got)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith(".json"):
            os.remove(os.path.join(out, f))
    for k, x in enumerate(got):
        with open(os.path.join(out, f"{k}.json"), "w", encoding="utf-8") as fh:
            json.dump(chart(x), fh, separators=(",", ":"))
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"n": len(got), "history": HISTORY, "live": LIVE,
                   "source": "OpenML dataset 43497 (https://www.openml.org/d/43497), CC0: Public Domain"}, fh)


def build(path):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    T = pq.read_table(path, columns=["datetime", "open_price", "high_price", "low_price", "close_price", "volume", "symbol"])
    T = T.filter(pc.is_in(T.column("symbol"), value_set=pa.array(sorted(NAMES))))
    by = {}
    for r in T.to_pylist():
        by.setdefault(r["symbol"], []).append((r["datetime"][:10], r["open_price"], r["high_price"], r["low_price"], r["close_price"], r["volume"] or 0))
    print("not in the data:", sorted(set(NAMES) - set(by)))
    got = pick([w for s, rows in by.items() for w in windows(s, sorted(rows))])
    print("famous moments missing:", sorted(t for t, day in MUST.items() if not any(x["t"] == t and x["a"] <= day <= x["b"] for x in got)))
    write(got)
    print(f"{len(got)} charts from {len({x['t'] for x in got})} stocks, {sum(x['a'] <= COVID <= x['b'] for x in got)} over the "
          f"COVID crash, median move {sorted(x['rng'] for x in got)[len(got) // 2]:.2f}x hi/lo -> {OUT}")


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
    assert all(not (w["w"][0][0] <= wave[99][0] < w["w"][-1][0]) for w in wild)               # never across a gap
    got = pick(wild + windows("NVDA", rows(lambda i: 100 * math.exp(math.cos(i / 15)))), n=50)
    for t in ("TSLA", "NVDA"):
        mine = sorted((x for x in got if x["t"] == t), key=lambda x: x["w"][0][0])
        assert 0 < len(mine) <= PER_TICKER and all(a["w"][-1][0] < b["w"][0][0] for a, b in zip(mine, mine[1:]))   # no overlaps
    c = chart(got[0])
    r = json.loads(base64.b64decode(c["r"]))
    assert len(c["c"]) == SPAN and c["c"][HISTORY - 1][3] == 100.0 and r["name"] in NAMES.values()
    assert abs(c["c"][-1][3] * r["k"] - r["last"]) < 0.01 * r["k"] and r["from"] < r["start"] < r["end"]
    with tempfile.TemporaryDirectory() as td:
        write(got, td)
        assert sorted(os.listdir(td)) == sorted([f"{k}.json" for k in range(len(got))] + ["meta.json"])
    print("ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["demo"] else build(sys.argv[1])
