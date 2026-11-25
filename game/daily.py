"""The Daily Chart, called Meme Street on the page: a two-minute trading game on one real stock whose name stays
hidden until the end, the same chart for everyone that day, with a board of the day's returns. Since 2026-11-18 it is
the whole of memestreet.net (the owner: "route the daily to memestreet.net. that's ALL there should be").

* **A real chart** (the owner: "make it so it takes REAL charts and shows the stock name at the end of the 2 minutes"):
  180 trading days of a real US stock (2016 to 2021), one day a candle, from `content/daily_real.json`
  (`tools/daily_bank.py` builds it from public-domain prices). The day picks one by the save's salt (`real_chart`), so
  nobody can tell which comes next, and a year passes before one repeats. While it plays the prices are the stock's
  real ones (since 2026-11-23; before, rebased so the last lead-in close was 100) and the candles carry no dates; once the game is over the result names the stock, its
  dates, its real prices and what happened in those months (`real`). Without the bank the model's chart below is used.
* **Streaks without an account** (the owner: "implementing streaks (without signing up), extra stuff for signing up"):
  a visitor's games count under their browser's id (`v:<id>`): stats, streak and history, carried into the account
  when they sign up or log in (`_daily_merge`). **Members** also get their name on the board, the same streak on
  every device, a **streak freeze** (`FREEZE_EVERY` games earn one, at most `FREEZES`; a single missed day uses one
  instead of ending the streak), their **history** (`daily_history`) and the **archive** of past charts to replay
  (`daily_archive`, `daily_past`).

* **The chart** of the day is made once, by the game's own price model (`market_model.py`: trends in legs, ranges and
  breakouts, support and resistance, chart patterns, volatility clustering) driving one made-up stock, with the engine's
  kind of noise on top. Each one-second candle is `MODEL_SECONDS` seconds of the model, so the two minutes hold a few
  game hours: legs, tests of levels, breakouts. The volatility changes from day to day and is mostly high (about 120% a
  game year, from 40% to 350%): the price usually swings 10% to 20% inside the two minutes, and some days far more.
  It is seeded from the day and a salt kept in the save (so it cannot be worked out in advance), and the chart itself
  is saved too, so a restart or a new version of the code changes nothing on the day.
* **A game**: 100,000 MB of paper money. Start shows `HISTORY` candles at once (the lead-in, to read the levels from), then
  one new candle a second for `LIVE` seconds, at the close of the last candle shown, with no fees:
  - **Buy** 25, 50, 75 or 100% of the cash; while short, Buy **covers** that share of the short.
  - **Sell** 25, 50, 75 or 100% of the shares; with none, Sell opens a **short** of that share of what the account is
    worth (a short already open counts against it, so the most you can be short is the account's worth: 1x).
  At the end what is held (or owed) is valued at the last close; the score is the return (never below -100%). One game a
  day for each account. When it ends the player gets the summary: their return, their place, every player's return as
  a distribution, and what the stock itself did.
* **Fair**: the candles still to come never leave the server; the page asks for the ones shown so far, and a trade is
  priced on the server at the candle showing when it arrives.
* **The board**: today's finished games, best return first (ties: who finished first); the last 7 days' top three are
  kept.
* **Like the daily word games** (since 2026-10-24): each day has a number (Daily #1 is 24 October 2026); each player
  keeps stats (games played, the current and best streak of days in a row, the average and best return, how often they
  beat just holding the stock); and a finished game has a grid of `SQUARES` squares, one per stretch of the two minutes,
  up, down or flat, for the shared result.

Paper money only: nothing here touches MB, the ledger or the market.
"""
import datetime
import hashlib
import json
import math
import os
import random
import secrets
import types

import market_model as mm

HISTORY = 60                 # lead-in candles shown at the start
LIVE = 120                   # candles that appear one a second: the game
MODEL_SECONDS = 30           # model seconds in a candle
STEP = 5                     # model seconds a step
START_CASH = 100000.0
OLD_START = 1000.0     # what games started before 2026-11-15 had (a game keeps its own `start`)
CHIPS = (0.25, 0.5, 0.75, 1.0)
DAY_SECONDS = 86400          # a real day, as the game's days (UTC)
BOARD = 20
REMIND_PER_DAY = 70          # reminder emails a day at most: the free mail plan sends 100, and sign-up codes need room (2026-11-10)
# The Daily Chart is a game for reading charts, so its price model leans a little further into technical structure than
# the market's (2026-10-26, on request: "more emphasis, not crazy"): levels come from swings and fair value gaps a player
# can see on the one-second candles (a model bar is two candles), are tested more often, hold somewhat more often and
# bounce visibly; breakouts run further; patterns form at the chart's scale and a little more often. Fakeouts and failed
# levels stay common. (The market keeps its own settings: there a reliable edge would be free money.)
TECHNICAL = {"bar_seconds": 60, "pivot_k": 3, "fvg_levels": 1,
             "hold_base": 0.46, "hold_per_touch": 0.10, "hold_strong_aligned": 0.08,
             "test_gap_seconds": 300, "bounce_sigmas": 0.18, "bounce_reach": 1.6, "follow_sigmas": 0.6,
             "pattern_days": 0.8, "pattern_flag_chance": 0.12, "pattern_end_chance": 0.3, "pattern_triangle_chance": 0.35}
CLOSE_RAMP = 30             # the last seconds of a game, where volume builds as at a real close
LEVELS_SHOWN = 6             # levels drawn on the finished chart
SQUARES = 8                  # the result grid: one square per 15 seconds of the two minutes
EPOCH_DAY = (datetime.date(2026, 10, 24) - datetime.date(1970, 1, 1)).days    # Daily #1
FREEZES, FREEZE_EVERY = 2, 7  # a member holds at most two streak freezes and earns one every seven games
HIST_KEEP, ARCH_KEEP = 400, 400   # days of history a player keeps, past charts the archive keeps
EVENTS = ("view", "share", "picture", "challenge", "signup_open", "archive_play", "help")   # ("view": the page opened, once a day a browser, 2026-11-25)   # what the page reports (daily_event)
REAL_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "daily_real.json")
_bank = {}


def real_bank(path=REAL_FILE):
    """The real charts (tools/daily_bank.py), read once; [] when the file is missing or unreadable."""
    if path not in _bank:
        try:
            with open(path, encoding="utf-8") as f:
                b = json.load(f)
            _bank[path] = b["charts"] if b.get("history") == HISTORY and b.get("live") == LIVE else []
        except (OSError, ValueError, KeyError, AttributeError):
            _bank[path] = []
    return _bank[path]


def real_levels(cs, n=LEVELS_SHOWN, k=3):
    """Support and resistance read from a real chart's own swings: a swing high or low (the extreme of `k` candles either
    side), grouped with others within two candles' usual move, kept when the price turned there twice or more; then every
    test of it in the two minutes, labelled by what the candles did next (`_seen`: held, broke, fake break). The most
    tested first, `n` at most, in the shape the old model chart's levels had."""
    closes = [c[3] for c in cs]
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0 and b > 0]
    th = 2 * (sum(r * r for r in rets) / max(len(rets), 1)) ** 0.5
    piv = []
    for i in range(k, len(cs) - k):
        near = cs[i - k:i + k + 1]
        if cs[i][1] >= max(c[1] for c in near):
            piv.append((i, cs[i][1]))
        if cs[i][2] <= min(c[2] for c in near):
            piv.append((i, cs[i][2]))
    groups = []
    for i, price in sorted(piv, key=lambda x: x[1]):
        g = next((g for g in groups if abs(math.log(price / g["price"])) < th), None)
        if g is None:
            groups.append({"price": price, "pts": [i]})
        else:
            g["pts"].append(i)
            g["price"] += (price - g["price"]) / len(g["pts"])
    out = []
    for g in groups:
        if len(g["pts"]) < 2:
            continue
        lv, tests, away = g["price"], [], True
        for j in range(max(min(g["pts"]) + 1, HISTORY), len(cs) - 1):
            if abs(math.log(closes[j] / lv)) > 1.5 * th:                     # (a new test only after the price has left the level)
                away = True
            if away and cs[j][2] <= lv * (1 + th / 2) and cs[j][1] >= lv * (1 - th / 2):
                side = 1 if closes[j - 1] > lv else -1                       # (from above: a test of support)
                seen = _seen(closes, j, lv, side, th)
                if seen:
                    tests.append([j, seen])
                    away = False
        if tests:
            out.append({"price": round(lv, 4), "kind": "support" if closes[tests[0][0] - 1] > lv else "resistance", "tests": tests})
    out.sort(key=lambda g: (-len(g["tests"]), g["tests"][0][0]))
    return out[:n]


def rebased(x, i):
    """Bank chart `x` (number `i`) as the game shows it: the stock's real prices (since 2026-11-23, the owner; before,
    rebased so the last lead-in close was 100), volume relative to the chart's median; `real` holds what the end of the
    game reveals (`k`, now always 1, turns a shown price into the real one; kept for old archived days)."""
    cs = x["c"]
    k = 1.0
    vols = sorted(c[4] for c in cs)
    vm = max(vols[len(vols) // 2], 1)
    candles = [[round(o, 4), round(h, 4), round(lo, 4), round(c, 4), int(v / vm * 1000)] for o, h, lo, c, v in cs]
    return {"candles": candles,
            "levels": real_levels(candles),
            "real": {"i": i, "ticker": x["t"], "name": x["n"], "tf": x.get("tf", "1 day"), "from": x["d"][0], "start": x["d"][1], "end": x["d"][2], "k": k,
                     "first": cs[HISTORY - 1][3], "last": cs[-1][3], "events": x.get("e", [])}}


def real_chart(salt, day, resets=0, bank=None):
    """The day's real chart, or None without a bank: the bank in an order only the salt knows, one chart a day, so a
    year goes by before one repeats; an admin reset takes one from the far side of the year."""
    bank = real_bank() if bank is None else bank
    if not bank:
        return None
    order = sorted(range(len(bank)), key=lambda i: hashlib.sha256(f"{salt}:real:{i}".encode()).digest())
    i = order[(day - EPOCH_DAY + (len(bank) // 2 + resets if resets else 0)) % len(bank)]
    return rebased(bank[i], i)


def is_visitor(key):
    return str(key or "").startswith("v:")


def clean_ref(ref):
    """A tracking link's name as the server keeps it (letters, digits, - and _), or None."""
    ref = str(ref or "").strip().lower()[:40]
    return ref if ref and all(c.isalnum() or c in "-_" for c in ref) else None


def make_chart(seed):
    """The day's candles: `HISTORY + LIVE` of [open, high, low, close, volume], and the volatility it was made with."""
    rng = random.Random(seed)
    vol = min(3.5, max(0.4, rng.lognormvariate(math.log(1.2), 0.45)))  # a game year: mostly around 120%
    price = round(rng.choice((rng.uniform(4, 30), rng.uniform(30, 150), rng.uniform(150, 600))), 2)
    x = types.SimpleNamespace(ticker="DAILY", price=price, vol=vol, beta=rng.uniform(0.6, 1.8), sector="daily",
                              asset_type="equity", moonshot=False)
    model = mm.MarketModel({"price_model": dict(TECHNICAL)}, rng=random.Random(seed ^ 0x5DEECE66D), now=0.0)
    model.regime = rng.choice(sorted(mm.REGIMES))
    model.regime_until = mm.DAY * rng.uniform(1, 5)
    model.trace = []                                                    # (its level tests, for the after-game breakdown)
    annual = math.sqrt(mm.YEAR)
    sig = vol / annual * math.sqrt(STEP)                               # one step's ordinary move
    volm, t = 1.0, 0.0
    candles = []
    per = MODEL_SECONDS // STEP
    warm = 3 * mm.DAY // STEP                                           # three game days first: swings, levels, a phase
    for i in range(warm + (HISTORY + LIVE) * per):
        t += STEP
        rets, noise, vmul = model.step(t, STEP, [x])
        vm = volm * model.market_vol(t) * noise.get(x.ticker, 1.0)
        shock = max(-8 * sig * max(vm, 1.0), min(8 * sig * max(vm, 1.0), sig * vm * rng.gauss(0, 1)))
        r = (1 + rets.get(x.ticker, 0.0)) * (1 + shock) - 1
        w = 1.25 if r < 0 else 0.75                                     # the engine's clustering: falls raise it more
        volm += 0.01 * STEP * (w * abs(shock) / (sig * max(vm / volm, 0.05)) - 0.8 * volm)
        volm = max(0.5, min(3.0, 1 + 0.5 ** (STEP / mm.DAY) * (volm - 1)))
        x.price = max(0.01, x.price * (1 + r))
        if i < warm:
            continue
        k = (i - warm) % per
        v = vmul.get(x.ticker, 1.0) * (0.4 + 0.6 * min(abs(shock) / sig, 6.0))
        if k == 0:
            candles.append([x.price, x.price, x.price, x.price, v])
        else:
            c = candles[-1]
            c[1], c[2], c[3], c[4] = max(c[1], x.price), min(c[2], x.price), x.price, c[4] + v
    # Like a real close, the last `CLOSE_RAMP` seconds get busier (2026-10-26, on request: a game could fade out in a
    # calm patch): at least 80% of the chart's usual volume (its mean without the top tenth, so a climax does not set
    # the bar), rising by up to 60% towards the final candle. Quiet stretches elsewhere stay: volume drying up before a
    # breakout is one of the things the game teaches.
    vols = sorted(c[4] for c in candles)
    usual = sum(vols[:len(vols) * 9 // 10]) / (len(vols) * 9 // 10)
    for j, c in enumerate(candles[-CLOSE_RAMP:]):
        c[4] = max(c[4], 0.8 * usual * (0.9 + 0.2 * rng.random())) * (1 + 0.6 * j / (CLOSE_RAMP - 1))
    low = min(c[2] for c in candles)
    nd = 4 if low < 1 else 3 if low < 50 else 2         # (a cheap stock's small moves would round away to a flat line in cents)
    return {"vol": round(vol, 4), "candles": [[round(c[0], nd), round(c[1], nd), round(c[2], nd), round(c[3], nd),
                                               int(c[4] * 1000)] for c in candles],
            "levels": _levels(model.trace, warm * STEP, candles, nd)}


def _seen(closes, k, level, side, th):
    """How a level test at candle `k` looks on the candles that follow: "held" (the price moved `th` away on its own
    side first), "broke" (it closed `th` through and stayed), "fake break" (through, then back on its side within 8
    candles), or None (neither within 15 candles: not shown). Read from the candles, not from what the model meant,
    so the after-game breakdown never contradicts the chart."""
    lv = math.log(level)
    start = max(0.0, (math.log(closes[k]) - lv) * side)
    for j in range(k + 1, min(len(closes), k + 16)):
        rel = (math.log(closes[j]) - lv) * side          # > 0: on the level's own side
        if rel > th + start:
            return "held"
        if rel < -th:
            back = any((math.log(c) - lv) * side > th / 2 for c in closes[j + 1:j + 9])
            return "fake break" if back else "broke"
    return None


def _levels(trace, start, candles, nd):
    """The levels the chart tested (shown only after the game): each one's price, kind (support, resistance or a fair
    value gap), and every test of it that shows on the candles as [candle, outcome] (`_seen`). Tests of the same level
    are grouped; at most `LEVELS_SHOWN`, the most tested first."""
    closes = [c[3] for c in candles]
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:]) if a > 0 and b > 0]
    th = 2 * (sum(r * r for r in rets) / max(len(rets), 1)) ** 0.5   # two candles' usual move
    groups = []
    for t, _, what, d in trace:
        k = int((t - start) // MODEL_SECONDS)
        if what != "level" or not 0 <= k < len(candles) - 1:
            continue
        seen = _seen(closes, k, d["level"], d["side"], th)
        if seen is None:
            continue
        g = next((g for g in groups if abs(g["price"] / d["level"] - 1) < mm.LEVEL_TOL), None)
        if g is None:
            g = {"price": d["level"], "kind": "fvg" if d["kind"] == "fvg" else "support" if d["side"] > 0 else "resistance",
                 "tests": []}
            groups.append(g)
        g["tests"].append([k, seen])
    groups.sort(key=lambda g: (-len(g["tests"]), g["tests"][0][0]))
    return [dict(g, price=round(g["price"], nd)) for g in groups[:LEVELS_SHOWN]]


class DailyMixin:
    """Mixed into the Engine: `self.now`, `self.players`. The state is `self.daily_game` (saved)."""

    def _dchart(self):
        d = self.__dict__.get("daily_game")
        if not isinstance(d, dict) or "salt" not in d:
            d = self.daily_game = {"salt": secrets.token_hex(16), "day": None, "chart": None, "plays": {}, "past": []}
        day = int(self.now // DAY_SECONDS)
        if d["day"] != day:
            if d["day"] is not None and d["plays"]:
                board = self._daily_board(d, final=True)
                d["past"] = ([{"day": d["day"], "players": len(board), "top": board[:3]}] + d["past"])[:7]
            if d["day"] is not None and d.get("chart"):
                d["log"] = ([self._daily_summary(d)] + d.get("log", []))[:400]     # (the admin page's day by day)
                if d["chart"].get("real"):                                      # (the archive: a past day's chart, replayable)
                    d["arch"] = ([{"day": d["day"], "number": self._dnum(d), "real": d["chart"]["real"],
                                   "hold": d["chart"]["candles"][-1][3] / d["chart"]["candles"][HISTORY - 1][3] - 1}]
                                 + d.get("arch", []))[:ARCH_KEEP]
            seed = int(hashlib.sha256(f"{d['salt']}:{day}".encode()).hexdigest()[:15], 16)
            d.update(day=day, chart=real_chart(d["salt"], day) or make_chart(seed), plays={}, visits={}, resets=0, ev={})
        d.setdefault("visits", {})
        d.setdefault("stats", {})
        d.setdefault("hist", {})
        d.setdefault("ev", {})
        return d

    def _dplays(self, p):
        """Where `p`'s game is: an account's in `plays` (on the board), a visitor's in `visits` (not on it) until they
        sign up (`daily_claim`)."""
        d = self._dchart()
        return d["visits"] if getattr(p, "visitor", False) else d["plays"]

    def daily_claim(self, p, visitor):
        """A visitor who has just made an account, or logged in, brings what they played without one: today's game
        goes on the board (unless the account has played today), and their stats, streak and history join the
        account's (`_daily_merge`; 2026-11-01, 2026-11-18)."""
        d = self._dchart()
        vkey = "v:" + str(visitor or "")
        play = d["visits"].get(vkey)
        if play is not None and play.get("done") is not True:
            self._daily_finish(play)
        self._daily_merge(d, vkey, p.token)
        play = d["visits"].pop(vkey, None)
        if play is None or p.token in d["plays"]:
            return False
        play.update(name=p.name, token=p.token, claimed=True)
        play.pop("visitor", None)
        d["plays"][p.token] = play
        return True

    @staticmethod
    def _daily_merge(d, vkey, token):
        """A visitor's stats and history moved into an account's. A day both played counts once (the account's game
        stands); the streak is the longest that still runs on the joint days; freezes are a member's only."""
        S, H = d.setdefault("stats", {}), d.setdefault("hist", {})
        vs, vh = S.pop(vkey, None), H.pop(vkey, None) or []
        if vs is None:
            return
        mine, ah = S.get(token), H.get(token, [])
        days = {h[0] for h in ah}
        dup = [h for h in vh if h[0] in days]
        H[token] = sorted(ah + [h for h in vh if h[0] not in days])[-HIST_KEEP:]
        if not mine:
            S[token] = dict(vs, freezes=1)
            return
        mine["played"] += vs["played"] - len(dup)
        mine["sum"] += vs["sum"] - sum(h[1] for h in dup)
        mine["beat"] += vs["beat"] - sum(1 for h in dup if h[1] > h[2] + 1e-9)
        mine["best"] = max(x for x in (mine["best"], vs["best"]) if x is not None) if (mine["best"] is not None or vs["best"] is not None) else None
        mine["first"] = min(mine.get("first", vs.get("first", 0)), vs.get("first", mine.get("first", 0)))
        run, last = 0, None                                        # (the run of days in a row that ends on the latest day played)
        for day in sorted({h[0] for h in H[token]}, reverse=True):
            if last is not None and day != last - 1:
                break
            run, last = run + 1, day
        if (vs["last"] or -1) > (mine["last"] or -1):
            mine["streak"], mine["last"] = max(vs["streak"], run), vs["last"]
        elif vs["last"] == mine["last"]:
            mine["streak"] = max(mine["streak"], vs["streak"], run)
        mine["max_streak"] = max(mine["max_streak"], vs["max_streak"], mine["streak"])

    def _daily_finish(self, play, final=False):
        """Ends a game whose two minutes are up (or every game, at the end of the day): what is held is valued at the
        last candle's close."""
        if play.get("done") or (not final and self.now - play["t0"] < LIVE):
            return
        last = self.daily_game["chart"]["candles"][-1][3]
        play["equity"] = max(0.0, play["cash"] + play["shares"] * last)     # (a short cannot lose more than everything)
        play["ret"] = play["equity"] / play.get("start", OLD_START) - 1
        play["done"] = True
        play["end"] = play["t0"] + LIVE
        self._daily_record(play)

    def _daily_record(self, play):
        """A finished game counts towards its player's stats and history, once: an account's, or a visitor's under
        their browser's id (since 2026-11-18). A member who missed exactly one day spends a streak freeze on it and the
        streak goes on; every FREEZE_EVERY games earn a freeze, FREEZES at most."""
        d, token = self.daily_game, play.get("token")
        if not token:
            return
        member = not is_visitor(token)
        st = d.setdefault("stats", {}).setdefault(token, {"played": 0, "streak": 0, "max_streak": 0, "last": None,
                                                          "sum": 0.0, "best": None, "beat": 0, "first": d["day"]})
        if st["last"] == d["day"]:
            return
        st.setdefault("first", d["day"])
        if member:
            st.setdefault("freezes", 1)
        cs = d["chart"]["candles"]
        hold = cs[-1][3] / cs[HISTORY - 1][3] - 1
        if st["last"] == d["day"] - 1:
            st["streak"] += 1
        elif member and st["last"] == d["day"] - 2 and st["streak"] and st.get("freezes", 0) > 0:
            st["freezes"] -= 1                                            # (a missed day, covered)
            st["froze"] = st.get("froze", 0) + 1
            st["streak"] += 1
        else:
            st["streak"] = 1
        st["max_streak"] = max(st["max_streak"], st["streak"])
        st["last"], st["played"], st["sum"] = d["day"], st["played"] + 1, st["sum"] + play["ret"]
        st["best"] = play["ret"] if st["best"] is None else max(st["best"], play["ret"])
        st["beat"] += play["ret"] > hold + 1e-9
        if member and st["played"] % FREEZE_EVERY == 0:
            st["freezes"] = min(FREEZES, st.get("freezes", 0) + 1)
        real = d["chart"].get("real") or {}
        h = d.setdefault("hist", {}).setdefault(token, [])
        h.append([d["day"], round(play["ret"], 6), round(hold, 6), real.get("ticker"), len(play["trades"])])
        del h[:-HIST_KEEP]

    def _daily_alive(self, st, member):
        """Whether a streak still runs today: played yesterday or today, or (a member) missed one day with a freeze
        in hand, which the next game will spend."""
        day = self.daily_game["day"]
        if st["last"] is None:
            return False
        return st["last"] >= day - 1 or (member and st["last"] == day - 2 and st.get("freezes", 0) > 0)

    def _daily_stats(self, p):
        st = (self.daily_game.get("stats") or {}).get(p.token)
        member = not getattr(p, "visitor", False)
        if not st:
            return {"played": 0, "streak": 0, "max_streak": 0, "avg": None, "best": None, "beat": 0,
                    "freezes": 1 if member else 0, "needs_freeze": False}
        alive = self._daily_alive(st, member)
        return {"played": st["played"], "streak": st["streak"] if alive else 0, "max_streak": st["max_streak"],
                "avg": st["sum"] / st["played"] if st["played"] else None, "best": st["best"], "beat": st["beat"],
                "freezes": st.get("freezes", 1) if member else 0,
                "needs_freeze": bool(alive and st["last"] == self.daily_game["day"] - 2)}

    @staticmethod
    def _daily_best(cs):
        """The best single trade the two minutes offered, long or short: in at one close, out at a later one (TA-D10,
        2026-11-07). `from` and `to` are candle indexes; the result card turns them into seconds into the game."""
        closes = [c[3] for c in cs[HISTORY - 1:]]
        lo = hi = 0
        best = {"side": "long", "ret": 0.0, "from": 0, "to": 0}
        for j in range(1, len(closes)):
            up, down = closes[j] / closes[lo] - 1, 1 - closes[j] / closes[hi]   # (a short's gain is the fall over the price it was sold at: 2026-11-18, was high/low - 1)
            if up > best["ret"]:
                best = {"side": "long", "ret": up, "from": lo, "to": j}
            if down > best["ret"]:
                best = {"side": "short", "ret": down, "from": hi, "to": j}
            if closes[j] < closes[lo]:
                lo = j
            if closes[j] > closes[hi]:
                hi = j
        best["from"] += HISTORY - 1
        best["to"] += HISTORY - 1
        best["ret"] = round(best["ret"], 6)
        return best

    def daily_stats_for(self, p):
        """A player's Daily Chart stats for the profile pages (TA-D11), or None before the first chart was ever made."""
        return self._daily_stats(p) if self.__dict__.get("daily_game") else None

    @staticmethod
    def _daily_grid(play, cs):
        """One square per stretch of the two minutes: +1 if the account's worth rose over it, -1 if it fell, 0 if flat."""
        trades = sorted(play["trades"], key=lambda t: t[0])
        cash, shares, j, worth = play.get("start", OLD_START), 0.0, 0, []
        step = LIVE // SQUARES
        for k in range(SQUARES + 1):
            i = HISTORY - 1 + k * step
            while j < len(trades) and trades[j][0] <= i:
                _, kind, price, sh = trades[j]
                sh = sh if kind in ("buy", "cover") else -sh
                shares, cash, j = shares + sh, cash - sh * price, j + 1
            worth.append(max(0.0, cash + shares * cs[i][3]))
        return [0 if abs(b - a) <= 0.0005 * max(a, 1.0) else (1 if b > a else -1) for a, b in zip(worth, worth[1:])]

    def _daily_board(self, d, final=False):
        for play in d["plays"].values():
            self._daily_finish(play, final)
        done = sorted((x for x in d["plays"].values() if x.get("done")), key=lambda x: (-x["ret"], x["end"]))
        bots = {b.token for b in self.house_bots()} if hasattr(self, "house_bots") else set()
        return [dict({"name": x["name"], "ret": round(x["ret"], 6), "trades": len(x["trades"])}, **({"house": True} if x.get("token") in bots else {}))
                for x in done]

    def _daily_summary(self, d):
        """One day of the Daily Chart in numbers, for the admin page: people (house bots apart), visitors who played
        without an account and how many of them signed up after, and how the games went (2026-11-01)."""
        bots = {b.token for b in self.house_bots()}
        cs = d["chart"]["candles"]
        hold = cs[-1][3] / cs[HISTORY - 1][3] - 1
        over = lambda x: x.get("done") or self.now - x["t0"] >= LIVE
        people = [x for x in d["plays"].values() if x.get("token") not in bots]
        visits = [x for k, x in d.get("visits", {}).items() if not self._daily_robot(k)]
        claimed = [x for x in people if x.get("claimed")]
        done = [x for x in people if x.get("done")]
        rets = sorted(x["ret"] for x in done)
        for x in visits:
            self._daily_finish(x)                                          # (a visitor's game is finished like any other; it records nothing)
        every = rets + [x["ret"] for x in visits if x.get("done")]
        stats = d.get("stats") or {}
        firsts = [stats.get(x.get("token") or "", {}).get("first") for x in people + visits]
        refs = {}
        for x in people + visits:
            if x.get("ref"):
                refs[x["ref"]] = refs.get(x["ref"], 0) + 1
        return {"day": d["day"], "number": self._dnum(d), "stock": (d["chart"].get("real") or {}).get("ticker"),
                "new": sum(1 for f in firsts if f == d["day"]), "returning": sum(1 for f in firsts if f is not None and f < d["day"]),
                "refs": refs, "ev": dict(d.get("ev") or {}),
                "people": len(people), "finished": len(done),
                "bots": len(d["plays"]) - len(people), "visitors": len(visits) + len(claimed),
                "visitors_finished": sum(1 for x in visits if over(x)) + sum(1 for x in claimed if over(x)),
                "signed_up": len(claimed), "hold": hold,
                "avg": sum(rets) / len(rets) if rets else None, "avg_all": sum(every) / len(every) if every else None, "median": rets[len(rets) // 2] if rets else None,
                "best": rets[-1] if rets else None, "worst": rets[0] if rets else None,
                "beat": sum(1 for r in rets if r > hold + 1e-9), "sat_out": sum(1 for x in done if not x["trades"]),
                "trades": sum(len(x["trades"]) for x in done) / len(done) if done else None,
                "started": len(people) + len(visits),
                "hours": [sum(1 for x in people + visits if int(x["t0"] // 3600) % 24 == h) for h in range(24)]}

    @staticmethod
    def _daily_robot(key):
        """A visitor id the reel pipeline plays and reads under (src/fetch.py, narrate.py): never counted as a person."""
        return str(key).startswith(("v:reelbot", "v:reelendcard"))

    def _dnum(self, d):
        """The chart's number: #1 on the epoch day (EPOCH_DAY, or the day an admin restarted the numbering)."""
        return d["day"] - d.get("epoch", EPOCH_DAY) + 1

    def daily_reset(self, restart=False):
        """Admin: a new chart for today, in place of the one out now (one that came out wrong). Today's board and games
        start again; the old chart's numbers go into the day-by-day log marked as replaced. A game already finished on
        it keeps its place in the player's stats (played, streak), and a replay today adds nothing to them."""
        d = self._dchart()
        self._daily_board(d, final=True)
        d["log"] = ([dict(self._daily_summary(d), replaced=True)] + d.get("log", []))[:90]
        d["resets"] = d.get("resets", 0) + 1
        seed = int(hashlib.sha256(f"{d['salt']}:{d['day']}:{d['resets']}".encode()).hexdigest()[:15], 16)
        d.update(chart=real_chart(d["salt"], d["day"], d["resets"]) or make_chart(seed), plays={}, visits={})
        if restart:                                                        # (the new chart is Daily Chart #1, no winners before it)
            d["epoch"], d["past"] = d["day"], []
        return True, f"Meme Street #{self._dnum(d)} is a new chart now: today's board starts again"

    def daily_admin(self):
        """Everything the Daily-only admin page shows (web/admin.html, 2026-11-18): today, the days before, the players
        (members and visitors apart, house traders and the reel pipeline left out), streaks, coming back (by the day a
        player first played), the stocks, where players came from, sharing and the way to an account."""
        d = self._dchart()
        self._daily_board(d)                                               # (games whose two minutes are up are finished)
        for x in d.get("visits", {}).values():
            self._daily_finish(x)
        bots = {b.token for b in self.house_bots()}
        stats = {t: s for t, s in (d.get("stats") or {}).items() if t not in bots and not self._daily_robot(t)
                 and (is_visitor(t) or t in self.by_token)}
        hist = {t: {h[0] for h in d.get("hist", {}).get(t, [])} for t in stats}
        member = lambda t: not is_visitor(t)
        alive = lambda t, s: self._daily_alive(s, member(t))
        name = lambda t: self.by_token[t].name if member(t) else "visitor " + t[2:8]
        def group(pick):
            S = {t: s for t, s in stats.items() if pick(t)}
            return {"players": len(S), "games": sum(s["played"] for s in S.values()),
                    "returning": sum(1 for s in S.values() if s["played"] >= 2), "regulars": sum(1 for s in S.values() if s["played"] >= 5),
                    "on_streak": sum(1 for t, s in S.items() if alive(t, s) and s["streak"] > 1),
                    "best_streak": max((s["max_streak"] for s in S.values()), default=0),
                    "avg_return": (sum(s["sum"] for s in S.values()) / max(1, sum(s["played"] for s in S.values()))) if S else None,
                    "freezes_used": sum(s.get("froze", 0) for s in S.values())}
        lengths = {}
        for t, s in stats.items():
            if alive(t, s) and s["streak"]:
                b = "1" if s["streak"] == 1 else "2-3" if s["streak"] <= 3 else "4-7" if s["streak"] <= 7 else "8-30" if s["streak"] <= 30 else "31+"
                lengths[b] = lengths.get(b, 0) + 1
        cohorts = {}                                                         # (by first day: how many came back)
        for t, s in stats.items():
            f = s.get("first")
            if f is None or f < d["day"] - 30:
                continue
            c = cohorts.setdefault(f, {"day": f, "number": f - d.get("epoch", EPOCH_DAY) + 1, "new": 0, "members": 0, "d1": 0, "d7": 0, "again": 0})
            c["new"] += 1
            c["members"] += member(t)
            days = hist.get(t, set())
            c["d1"] += (f + 1) in days
            c["d7"] += any(f < x <= f + 7 for x in days)
            c["again"] += s["played"] >= 2
        log = d.get("log", [])
        stocks = [{"number": x.get("number"), "day": x["day"], "stock": x.get("stock"), "hold": x.get("hold"), "avg": x.get("avg_all", x.get("avg")),
                   "median": x.get("median"), "beat": x.get("beat"), "finished": (x.get("finished") or 0) + (x.get("visitors_finished") or 0)}
                  for x in log if x.get("stock")]
        refs = {}
        for x in [self._daily_summary(d)] + log[:30]:
            for k, v in (x.get("refs") or {}).items():
                refs[k] = refs.get(k, 0) + v
        top = lambda key, n=15: sorted(((name(t), s["streak"] if key == "streak" else s[key], s["max_streak"], s["played"], member(t))
                                        for t, s in stats.items() if (key != "streak" or (alive(t, s) and s["streak"] > 1))),
                                       key=lambda x: (-x[1], -x[3]))[:n]
        # the numbers for coming back (2026-11-25, the owner: "only useful stats"), all from each player's own history
        today = d["day"]
        played = lambda t, day: day in hist.get(t, ())
        series = [{"day": x, "players": sum(1 for t in stats if played(t, x)),
                   "new": sum(1 for t, s in stats.items() if s.get("first") == x)} for x in range(today - 59, today + 1)]
        uniq = lambda n: sum(1 for t in stats if any(today - n < x <= today for x in hist.get(t, ())))
        def keep(k):                                                       # (of players old enough to tell: back on day k after their first)
            old = [t for t, s in stats.items() if s.get("first") is not None and s["first"] + k <= today]
            return {"k": k, "of": len(old), "back": sum(1 for t in old if played(t, stats[t]["first"] + k))}
        def within(k):                                                     # (back on any day within k days of their first)
            old = [t for t, s in stats.items() if s.get("first") is not None and s["first"] + k <= today]
            return {"of": len(old), "back": sum(1 for t in old if any(stats[t]["first"] < x <= stats[t]["first"] + k for x in hist.get(t, ())))}
        buckets = {"1": 0, "2": 0, "3-4": 0, "5-9": 0, "10+": 0}
        for s in stats.values():
            n = s["played"]
            buckets["1" if n <= 1 else "2" if n == 2 else "3-4" if n <= 4 else "5-9" if n <= 9 else "10+"] += 1
        last = {t: max(hist.get(t) or [s.get("last") or 0]) for t, s in stats.items()}
        hours = [0] * 24
        for x in [self._daily_summary(d)] + log[:29]:
            for h, v in enumerate(x.get("hours") or []):
                hours[h] += v
        habit = {"dau": uniq(1), "wau": uniq(7), "mau": uniq(30), "series": series, "curve": [keep(k) for k in range(1, 15)],
                 "d1": within(1), "d7": within(7), "d30": within(30), "games": buckets, "hours": hours,
                 "at_risk": sum(1 for t, s in stats.items() if alive(t, s) and s["streak"] > 1 and not played(t, today)),
                 "lapsing": sum(1 for t in stats if 2 <= today - last[t] <= 7), "gone": sum(1 for t in stats if today - last[t] > 7)}
        return {"today": self._daily_summary(d), "days": log[:90], "habit": habit, "streaks": top("streak"), "most_played": top("played"),
                "all_time": group(lambda t: True), "members": group(member), "visitors": group(is_visitor),
                "streak_lengths": lengths, "cohorts": sorted(cohorts.values(), key=lambda c: -c["day"]), "stocks": stocks,
                "refs": sorted(refs.items(), key=lambda kv: -kv[1]), "chart": {k: v for k, v in (d["chart"].get("real") or {}).items()},
                "bank": len(real_bank()), "archive": len(d.get("arch", [])),
                "next": (d["day"] + 1) * DAY_SECONDS, "log_since": log[-1]["day"] if log else d["day"]}

    def _daily_shown(self, play):
        """How many candles the player has seen: the lead-in, and one more each second."""
        return HISTORY + max(0, min(LIVE, int(self.now - play["t0"])))

    def _daily_state(self, play, since=0):
        d = self.daily_game
        self._daily_finish(play)
        cs = d["chart"]["candles"]
        n = len(cs) if play.get("done") else self._daily_shown(play)
        since = max(0, min(int(since or 0), n))
        last = cs[n - 1][3]
        out = {"candles": cs[since:n], "from": since, "shown": n, "history": HISTORY, "live": LIVE, "cash": play["cash"],
               "shares": play["shares"], "price": last, "equity": play["cash"] + play["shares"] * last,
               "trades": play["trades"], "left": 0 if play.get("done") else max(0.0, play["t0"] + LIVE - self.now),
               "done": bool(play.get("done"))}
        if play.get("done"):
            out["ret"] = play["ret"]
            out["equity"] = play["equity"]
            board = self._daily_board(d)
            if play.get("visitor"):                                        # (not on the board: where it would be)
                out["rank"] = 1 + sum(x["ret"] > play["ret"] for x in board)
                out["of"] = len(board) + 1
                out["dist"] = sorted([x["ret"] for x in board] + [round(play["ret"], 6)])
            else:
                out["rank"] = next((i + 1 for i, x in enumerate(board) if x["name"] == play["name"]), None)
                out["of"] = len(board)
                out["dist"] = sorted(x["ret"] for x in board)              # everyone's return today (no names)
            out["hold"] = cs[-1][3] / cs[HISTORY - 1][3] - 1                # what the stock itself did in the two minutes
            out["hi"] = max(c[1] for c in cs[HISTORY:])
            out["lo"] = min(c[2] for c in cs[HISTORY:])
            out["grid"] = self._daily_grid(play, cs)
            out["levels"] = d["chart"].get("levels", [])                 # (only once the game is over: they tell the future)
            out["best"] = self._daily_best(cs)                          # what you could have done (TA-D10)
            if d["chart"].get("real"):
                out["real"] = {k: v for k, v in d["chart"]["real"].items() if k != "i"}   # (the stock's name, dates, real prices: only now)
        return out

    def daily_view(self, p):
        d = self._dchart()
        board = self._daily_board(d)
        play = self._dplays(p).get(p.token)
        if play is not None:
            self._daily_finish(play)                                       # (a visitor's game too, before its stats are read)
        out = {"visitor": bool(getattr(p, "visitor", False)), "day": d["day"], "number": self._dnum(d), "live": LIVE, "history": HISTORY, "cash": START_CASH,
               "chips": CHIPS, "stats": self._daily_stats(p),
               "board": board[:BOARD], "players": len(board), "past": d["past"], "guest": bool(getattr(p, "guest", False)),
               "status": "new" if play is None else "done" if play.get("done") or self.now - play["t0"] >= LIVE else "running",
               "next": (d["day"] + 1) * DAY_SECONDS, "remind": bool(getattr(p, "remind", False)), "real": bool(d["chart"].get("real")),
               "people": sum(1 for x in board if not x.get("house")), "house": sum(1 for x in board if x.get("house")),
               "tomorrow": self._daily_tomorrow(d)}
        if play is not None:
            out["game"] = self._daily_state(play)
        if not out["visitor"] and not out["guest"]:                         # (the account panel: who is signed in)
            out["me"] = {"name": p.name, "email": getattr(p, "email", None), "verified": bool(getattr(p, "email_verified", False))}
        return out

    # ---- the reminder email (TA-D9, growth plan 2026-11-10): opt-in, a confirmed address only, one a day when the new
    # chart starts, at most REMIND_PER_DAY a day so sign-up codes always fit in the free mail plan, one-click unsubscribe
    def daily_remind_set(self, p, on):
        if on and not (p.email and p.email_verified):
            return {"ok": False, "error": "Confirm your email address first: the code is on your Profile page."}
        p.remind = bool(on)
        if p.remind and not p.unsub:
            p.unsub = secrets.token_urlsafe(16)
        return {"ok": True, "remind": p.remind,
                "msg": "We'll email you when each new chart starts." if p.remind else "No more Daily Chart emails."}

    def daily_unsubscribe(self, t):
        """The link in every reminder: True if it matched an account (which is now off the list)."""
        for p in self.players.values():
            if t and p.unsub and secrets.compare_digest(p.unsub, str(t)):
                p.remind = False
                return True
        return False

    def daily_reminders(self, site, cap=REMIND_PER_DAY):
        """Today's reminders still to send, as (address, subject, body, unsubscribe link); each player is marked sent."""
        d = self._dchart()
        num, today = self._dnum(d), d["day"]
        left = cap - sum(1 for p in self.players.values() if getattr(p, "remind_day", -1) == today)
        out = []
        for p in self.players.values():
            if left <= 0:
                break
            if not (getattr(p, "remind", False) and p.email and p.email_verified and not p.hb and p.remind_day != today):
                continue
            p.remind_day, left = today, left - 1
            streak = self._daily_stats(p).get("streak") or 0
            link = f"{site}/api/unsub?t={p.unsub}"
            body = (f"Meme Street #{num} is live: two minutes on today's mystery stock, a real chart, the same one for everyone. Its name shows at the end.\n"
                    + (f"Your streak: {streak} day{'s' if streak != 1 else ''}. Play today to keep it.\n" if streak else "")
                    + f"\nPlay: {site}/daily?ref=mail_daily\n\n"
                    f"You get this because you asked for it on Meme Street. Stop it with one click: {link}\n"
                    "Meme Street Game · memestreet.game@gmail.com · practice money only, no cash value\n")
            out.append((p.email, f"Meme Street #{num} is live", body, link))
        return out

    def daily_start(self, p, ref=None):
        if getattr(p, "guest", False):
            return {"error": "Create an account to play"}
        plays = self._dplays(p)
        if p.token in plays:
            return {"error": "You have played today's stock: a new one comes at midnight (UTC)"}
        if getattr(p, "visitor", False):
            if len(plays) >= 50000:                                        # (a ceiling on what visitors can make the save hold)
                return {"error": "Create a free account to play"}
            plays[p.token] = {"name": "You", "visitor": True, "token": p.token, "t0": self.now, "cash": START_CASH, "start": START_CASH, "shares": 0.0, "trades": []}
        else:
            plays[p.token] = {"name": p.name, "token": p.token, "t0": self.now, "cash": START_CASH, "start": START_CASH, "shares": 0.0, "trades": []}
        if clean_ref(ref):
            plays[p.token]["ref"] = clean_ref(ref)
        return self._daily_state(plays[p.token])

    def _daily_tomorrow(self, d):
        """Tomorrow's timeframe (never its stock): the teaser on today's result. Worked out once a day."""
        if d.get("next_tf", [None])[0] != d["day"]:
            nxt = real_chart(d["salt"], d["day"] + 1)
            d["next_tf"] = [d["day"], nxt["real"]["tf"] if nxt else None]
        return {"tf": d["next_tf"][1]}

    def daily_event(self, p, kind):
        """The page reports a share, a story picture, a challenge link, the sign-up box opened, an archive replay or the
        help: counted for the day (the admin page's Sharing tab), nothing about who."""
        if kind not in EVENTS:
            return {"ok": False}
        ev = self._dchart()["ev"]
        ev[kind] = ev.get(kind, 0) + 1
        return {"ok": True}

    def daily_history(self, p):
        """A member's every game (the history panel): day number, date, the stock, their return and the stock's."""
        d = self._dchart()
        if getattr(p, "visitor", False):
            return {"error": "Make a free account to keep your history", "need_account": True}
        names = {a["day"]: a["real"] for a in d.get("arch", [])}
        if d["chart"].get("real"):
            names[d["day"]] = d["chart"]["real"]
        rows = []
        for day, ret, hold, ticker, *rest in reversed(d.get("hist", {}).get(p.token, [])):
            r = names.get(day) or {}
            rows.append({"day": day, "number": day - d.get("epoch", EPOCH_DAY) + 1, "ret": ret, "hold": hold,
                         "ticker": ticker, "name": r.get("name") if r.get("ticker") == ticker else None, "trades": rest[0] if rest else None})
        return {"rows": rows, "stats": self._daily_stats(p)}

    def daily_archive(self, p):
        """The past charts a member can replay (not today's): number, date, the stock and what it did."""
        d = self._dchart()
        if getattr(p, "visitor", False):
            return {"error": "Make a free account to open the archive", "need_account": True}
        mine = {h[0]: h[1] for h in d.get("hist", {}).get(p.token, [])}
        return {"days": [{"day": a["day"], "number": a["number"], "ticker": a["real"]["ticker"], "name": a["real"]["name"],
                          "start": a["real"]["start"], "end": a["real"]["end"], "hold": a["hold"], "mine": mine.get(a["day"])}
                         for a in d.get("arch", []) if a["day"] < d["day"]]}

    def daily_past(self, p, number):
        """A past day's whole chart and its reveal, for a member's practice replay (unranked; played in the page)."""
        d = self._dchart()
        if getattr(p, "visitor", False):
            return {"error": "Make a free account to open the archive", "need_account": True}
        try:
            number = int(number)
        except (TypeError, ValueError):
            return {"error": "No such day"}
        a = next((a for a in d.get("arch", []) if a["number"] == number and a["day"] < d["day"]), None)
        bank = real_bank()
        if a is None or not 0 <= a["real"].get("i", -1) < len(bank) or bank[a["real"]["i"]]["t"] != a["real"]["ticker"]:
            return {"error": "That day's chart is not in the archive"}
        ch = rebased(bank[a["real"]["i"]], a["real"]["i"])
        return {"number": number, "day": a["day"], "candles": ch["candles"], "history": HISTORY, "live": LIVE, "cash": START_CASH,
                "real": {k: v for k, v in ch["real"].items() if k != "i"}}

    def daily_poll(self, p, since=0):
        play = self._dplays(p).get(p.token)
        if play is None:
            return {"error": "Press Start first"}
        try:
            since = int(since)
        except (TypeError, ValueError):
            since = 0
        return self._daily_state(play, since)

    def daily_trade(self, p, side, pct):
        d = self._dchart()
        play = self._dplays(p).get(p.token)
        if play is None:
            return {"error": "Press Start first"}
        self._daily_finish(play)
        if play.get("done"):
            return {"error": "Time is up", **self._daily_state(play)}
        try:
            pct = float(pct)
        except (TypeError, ValueError):
            return {"error": "Bad size"}
        if side not in ("buy", "sell") or not any(abs(pct - c) < 1e-9 for c in CHIPS):
            return {"error": "Buy or sell 25, 50, 75 or 100%"}
        n = self._daily_shown(play)
        price = d["chart"]["candles"][n - 1][3]
        held = play["shares"]
        if side == "buy" and held < -1e-12:                # buying while short covers that share of the short
            sh = -held * pct
            play["shares"] += sh
            play["cash"] -= sh * price
            kind = "cover"
        elif side == "buy":
            spend = play["cash"] * pct
            if spend < 0.01:
                return {"error": "No cash left to buy with", **self._daily_state(play)}
            sh = spend / price
            play["cash"] -= spend
            play["shares"] += sh
            kind = "buy"
        elif held > 1e-12:                                 # selling what is held
            sh = held * pct
            play["shares"] -= sh
            play["cash"] += sh * price
            kind = "sell"
        else:                                              # nothing held: a short, of that share of the account's worth
            room = max(0.0, play["cash"] + held * price - (-held) * price)
            if room * pct < 0.01:
                return {"error": "You are already short as much as your account allows", **self._daily_state(play)}
            sh = room * pct / price
            play["shares"] -= sh
            play["cash"] += sh * price
            kind = "short"
        play["trades"].append([n - 1, kind, price, sh])
        if abs(play["shares"]) * price < 1e-9:
            play["shares"] = 0.0
        return self._daily_state(play)
