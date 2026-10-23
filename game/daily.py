"""The Daily Chart: a two-minute trading game on one stock with no name, the same chart for everyone that day, with a
board of the day's returns.

* **The chart** of the day is made once, by the game's own price model (`market_model.py`: trends in legs, ranges and
  breakouts, support and resistance, chart patterns, volatility clustering) driving one made-up stock, with the engine's
  kind of noise on top. Each one-second candle is `MODEL_SECONDS` seconds of the model, so the two minutes hold a few
  game hours: legs, tests of levels, breakouts. The volatility changes from day to day and is mostly high (about 120% a
  game year, from 40% to 350%): the price usually swings 10% to 20% inside the two minutes, and some days far more.
  It is seeded from the day and a salt kept in the save (so it cannot be worked out in advance), and the chart itself
  is saved too, so a restart or a new version of the code changes nothing on the day.
* **A game**: 1,000 MB of paper money. Start shows `HISTORY` candles at once (the lead-in, to read the levels from), then
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

Paper money only: nothing here touches MB, the ledger or the market.
"""
import hashlib
import math
import random
import secrets
import types

import market_model as mm

HISTORY = 60                 # lead-in candles shown at the start
LIVE = 120                   # candles that appear one a second: the game
MODEL_SECONDS = 30           # model seconds in a candle
STEP = 5                     # model seconds a step
START_CASH = 1000.0
CHIPS = (0.25, 0.5, 0.75, 1.0)
DAY_SECONDS = 86400          # a real day, as the game's days (UTC)
BOARD = 20


def make_chart(seed):
    """The day's candles: `HISTORY + LIVE` of [open, high, low, close, volume], and the volatility it was made with."""
    rng = random.Random(seed)
    vol = min(3.5, max(0.4, rng.lognormvariate(math.log(1.2), 0.45)))  # a game year: mostly around 120%
    price = round(rng.choice((rng.uniform(4, 30), rng.uniform(30, 150), rng.uniform(150, 600))), 2)
    x = types.SimpleNamespace(ticker="DAILY", price=price, vol=vol, beta=rng.uniform(0.6, 1.8), sector="daily",
                              asset_type="equity", moonshot=False)
    model = mm.MarketModel({"price_model": {}}, rng=random.Random(seed ^ 0x5DEECE66D), now=0.0)
    model.regime = rng.choice(sorted(mm.REGIMES))
    model.regime_until = mm.DAY * rng.uniform(1, 5)
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
    nd = 4 if min(c[2] for c in candles) < 1 else 2
    return {"vol": round(vol, 4), "candles": [[round(c[0], nd), round(c[1], nd), round(c[2], nd), round(c[3], nd),
                                               int(c[4] * 1000)] for c in candles]}


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
            seed = int(hashlib.sha256(f"{d['salt']}:{day}".encode()).hexdigest()[:15], 16)
            d.update(day=day, chart=make_chart(seed), plays={})
        return d

    def _daily_finish(self, play, final=False):
        """Ends a game whose two minutes are up (or every game, at the end of the day): what is held is valued at the
        last candle's close."""
        if play.get("done") or (not final and self.now - play["t0"] < LIVE):
            return
        last = self.daily_game["chart"]["candles"][-1][3]
        play["equity"] = max(0.0, play["cash"] + play["shares"] * last)     # (a short cannot lose more than everything)
        play["ret"] = play["equity"] / START_CASH - 1
        play["done"] = True
        play["end"] = play["t0"] + LIVE

    def _daily_board(self, d, final=False):
        for play in d["plays"].values():
            self._daily_finish(play, final)
        done = sorted((x for x in d["plays"].values() if x.get("done")), key=lambda x: (-x["ret"], x["end"]))
        return [{"name": x["name"], "ret": round(x["ret"], 6), "trades": len(x["trades"])} for x in done]

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
            out["rank"] = next((i + 1 for i, x in enumerate(board) if x["name"] == play["name"]), None)
            out["of"] = len(board)
            out["dist"] = sorted(x["ret"] for x in board)                  # everyone's return today (no names)
            out["hold"] = cs[-1][3] / cs[HISTORY - 1][3] - 1                # what the stock itself did in the two minutes
            out["hi"] = max(c[1] for c in cs[HISTORY:])
            out["lo"] = min(c[2] for c in cs[HISTORY:])
        return out

    def daily_view(self, p):
        d = self._dchart()
        board = self._daily_board(d)
        play = d["plays"].get(p.token)
        out = {"day": d["day"], "live": LIVE, "history": HISTORY, "cash": START_CASH, "chips": CHIPS,
               "board": board[:BOARD], "players": len(board), "past": d["past"], "guest": bool(getattr(p, "guest", False)),
               "status": "new" if play is None else "done" if play.get("done") or self.now - play["t0"] >= LIVE else "running",
               "next": (d["day"] + 1) * DAY_SECONDS}
        if play is not None:
            out["game"] = self._daily_state(play)
        return out

    def daily_start(self, p):
        if getattr(p, "guest", False):
            return {"error": "Create an account to play"}
        d = self._dchart()
        if p.token in d["plays"]:
            return {"error": "You have played today's chart: a new one comes at midnight (UTC)"}
        d["plays"][p.token] = {"name": p.name, "t0": self.now, "cash": START_CASH, "shares": 0.0, "trades": []}
        return self._daily_state(d["plays"][p.token])

    def daily_poll(self, p, since=0):
        d = self._dchart()
        play = d["plays"].get(p.token)
        if play is None:
            return {"error": "Press Start first"}
        try:
            since = int(since)
        except (TypeError, ValueError):
            since = 0
        return self._daily_state(play, since)

    def daily_trade(self, p, side, pct):
        d = self._dchart()
        play = d["plays"].get(p.token)
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
