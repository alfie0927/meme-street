"""House bots: 72 computer players with ordinary usernames that trade the market and play the Daily Chart the way
people do (since 2026-10-27, on request). They are switched on by the `house_bots` setting or `HOUSE_BOTS=1` in the
environment (the live server sets it in /etc/memestreet.env); tests and new games have none.

Each bot is an ordinary account (it starts with the usual 1,000 MB and trades through `Engine.trade`, `set_exit` and the
Daily Chart's own calls, under the same rules, fees and prices as anyone) with a persona kept in `p.hb`:

* **style**: what it looks for: `trend` (price above rising averages), `dip` (a sharp fall into oversold), `breakout`
  (a close above the last 20 candles' high), `levels` (a bounce near a recent swing low), `rsi` (oversold buys,
  overbought shorts), `shorter` (shorts downtrends), `holder` (buys and sits), `scalper` (small, quick trades) or
  `random` (gut feeling);
* **skill** (0 to 1): a skilled bot sizes by risk and always sets a stop-loss and a take-profit; an unskilled one bets a
  random share of its cash, takes small profits early and holds losers until it panics;
* **when**: its hours of the day (UTC), how often it looks, how likely it is to play the Daily Chart, and spells of being
  active (1 to 12 days) and **dormant** (1 to 14 days, more often for some), like people who drop off and come back.

Bots never read anything a player cannot see: the market candles and, in the Daily Chart, only the candles already
shown at the moment of each decision (the plan is made from the past candles one by one, and carried out a second or
few later at the price then). Players' trades never move prices, so bots cannot either. They have no email, never
chat, and are left out of the admin page's player lists (the Overview counts them); their MB count everywhere else.
"""
import os
import random

import daily
import drills

NAMES = ["jake_trades", "ThetaGang99", "bearmarketbecky", "MrStopLoss", "noah.b", "dannyboy_7", "priya_s", "freddie_m",
         "mia.k", "Rayan07", "lukeyp", "Marco.R", "chloe2k4", "Ines_V", "Dave M", "kofi_k", "sunnyside_em", "otterly_owen",
         "theo.w", "NovaSkye", "jakub_p", "Lina88", "maxwellh", "bluefinch", "samokay", "hazel.x", "mattw_", "rubyy_",
         "Kenji_T", "frostbyte", "aisha.m", "pipsqueak_",
         # 40 more (2026-10-27, on request); "luna<3" became "luna3" (names allow letters, digits, _ - . and spaces)
         "sleepytoad", "Benji_77", "moonpiefan", "kx_ellie", "ToastLord", "j4yden", "waffle.nina", "Riko_02",
         "gremlin_matt", "peachy.kai", "Nova_2k9", "lilypadz", "ollie.exe", "Miko_V", "sourapple_sam", "jj_2008",
         "cloudboy_", "Tia.Mx", "rocketraccoon7", "ezra.wtf", "honeydew_hana", "Kieran99", "mochi_milo", "vxne",
         "bubbly.bee", "Dario_04", "froggo_finn", "luna3", "pixel_pip", "Jules_2k7", "saltycrisp", "amara_xo",
         "noodle_nate", "Rhea.88", "sleepy_sora", "kobe_2", "minty.mae", "Ziggy_V", "crumbcat", "eli_not_elias"]
STYLES = ["trend", "dip", "breakout", "levels", "rsi", "holder", "scalper", "random", "shorter"]
FIXED = {"jake_trades": ("scalper", 0.45), "ThetaGang99": ("trend", 0.7), "bearmarketbecky": ("shorter", 0.55),
         "MrStopLoss": ("trend", 0.92)}
HOUR = 3600
DAY = 86400


def init_player(p):
    p.hb = None                # a house bot's persona and state (see the module doc); None for a person


def dump_player(p):
    return p.hb


def load_player(p, x):
    p.hb = x if isinstance(x, dict) else None


def persona(name, k):
    """A bot's character, the same every time for the same name."""
    r = random.Random("hb:" + name)
    style, skill = FIXED.get(name, (STYLES[k % len(STYLES)], round(r.uniform(0.15, 0.9), 2)))
    return {"style": style, "skill": skill,
            "look": r.choice([300, 600, 900, 1800]),                 # seconds between looks at the market while on
            "hours": [r.randrange(24), r.randint(4, 14)],              # UTC hour it starts, and for how long
            "daily": round(r.uniform(0.35, 0.97), 2),                  # chance of playing the Daily Chart on an active day
            "flaky": round(r.uniform(0.0, 1.0), 2),                    # how much it drops off for days
            "max_pos": r.randint(1, 6), "shorts": style in ("rsi", "shorter", "random") or r.random() < 0.2,
            "hold_h": {"scalper": 0.5, "holder": 120}.get(style, r.choice([2, 6, 12, 24, 48])),
            "state": "active", "until": 0.0, "next": 0.0, "watch": [], "opened": {}, "dday": None, "dat": None,
            "dplan": [], "made": True}


class HouseBotsMixin:
    """Mixed into the Engine: `self.players`, `self.stocks`, `self.trade`, `self.set_exit`, the Daily Chart's calls."""

    def _house_on(self):
        return bool(self.settings.get("house_bots")) or os.environ.get("HOUSE_BOTS") == "1"

    def house_bots(self):
        return [p for p in self.players.values() if p.hb]

    def humans(self):
        return [p for p in self.players.values() if not p.hb]

    def _house_make(self):
        have = {p.name.lower() for p in self.players.values()}
        for k, name in enumerate(NAMES):
            if name.lower() in have:
                continue
            p, _ = self.join(name)
            if p is not None:
                p.hb = persona(name, k)
                p.hb["next"] = self.now + random.uniform(5, 600)
                p.email_verified = True                    # (nothing is sent: the address check never applies to a bot)

    def _house_tick(self):
        if not self._house_on():
            return
        if not getattr(self, "_house_made", False):
            self._house_make()
            self._house_made = True
        for p in self.house_bots():
            hb = p.hb
            if hb["dplan"]:
                self._house_daily_step(p)
            if self.now >= hb["next"]:
                hb["next"] = self.now + hb["look"] * random.uniform(0.6, 1.4)
                try:
                    self._house_look(p)
                except Exception:                          # a bot must never stop the game
                    hb["next"] = self.now + HOUR

    # ------------------------------------------------------------------ the rhythm of a person
    def _house_awake(self, p):
        hb = p.hb
        if self.now >= hb["until"]:                        # a spell ends: active, or off for a while
            off = hb["state"] == "active" and random.random() < 0.15 + 0.6 * hb["flaky"]
            hb["state"] = "dormant" if off else "active"
            hb["until"] = self.now + (random.uniform(1, 14) if off else random.uniform(1, 12)) * DAY
        if hb["state"] != "active":
            return False
        start, length = hb["hours"]
        return (int(self.now // HOUR) - start) % 24 < length

    def _house_look(self, p):
        hb = p.hb
        if not self._house_awake(p):
            hb["next"] = self.now + HOUR
            return
        today = int(self.now // DAY)
        if hb["dday"] != today:                            # once a day: will it play the Daily Chart, and when
            hb["dday"] = today
            hb["dat"] = self.now + random.uniform(0, hb["hours"][1] * HOUR) if random.random() < hb["daily"] else None
        if hb["dat"] is not None and self.now >= hb["dat"]:
            hb["dat"] = None
            self._house_daily_start(p)
        self._house_market(p)

    # ------------------------------------------------------------------ the market
    def _house_candles(self, tk):
        s = self.stocks.get(tk)
        rows = list(s.tf.get("5m", ()))[-121:-1] if s else []
        return [[r[1], r[2], r[3], r[4], r[5] if len(r) > 5 else 0.0] for r in rows]

    def _house_market(self, p):
        hb = p.hb
        if not hb["watch"] or random.random() < 0.05:      # a few favourites, now and then a new one
            pool = sorted((s for s in self.stocks.values() if s.asset_type == "equity" and not s.moonshot),
                          key=lambda s: -s.shares_outstanding * s.price)
            pick = random.sample(pool[:60], min(8, len(pool[:60]))) if pool else []
            hb["watch"] = [s.ticker for s in pick[:random.randint(3, 8)]]
        eq = self.equity(p)
        if eq < 60 and not p.hold:                         # broke: the free restart, or a break first
            ok, _ = self.claim_restart(p)
            if not ok:
                hb["state"], hb["until"] = "dormant", self.now + random.uniform(2, 6) * DAY
            return
        for tk in list(p.hold):                            # what it holds
            self._house_manage(p, tk)
        if len(p.hold) >= hb["max_pos"] or random.random() > 0.35 + 0.4 * (hb["style"] == "scalper"):
            return
        tk = random.choice(hb["watch"]) if hb["watch"] else None
        if not tk or tk in p.hold or tk not in self.stocks:
            return
        cs = self._house_candles(tk)
        if len(cs) < 60:
            return
        side = self._house_signal(hb, cs)
        if side == "sell" and not hb["shorts"]:
            return
        if side:
            self._house_enter(p, tk, side, cs)

    def _house_signal(self, hb, cs):
        """"buy", "sell" (a short) or None, from the candles alone."""
        cl = [c[3] for c in cs]
        s20, s50 = drills.sma(cl, 20)[-1], drills.sma(cl, 50)[-1]
        r = drills.rsi(cl)[-1] or 50
        atr = drills.atr_series(cs)[-1]
        last, style = cl[-1], hb["style"]
        hi20, lo20 = max(c[1] for c in cs[-21:-1]), min(c[2] for c in cs[-21:-1])
        if style == "trend":
            return "buy" if last > s20 > s50 else "sell" if hb["shorts"] and last < s20 < s50 else None
        if style == "shorter":
            return "sell" if last < s20 < s50 else None
        if style == "dip":
            return "buy" if r < 35 and last < hi20 - 1.5 * atr else None
        if style == "breakout":
            return "buy" if last > hi20 else "sell" if hb["shorts"] and last < lo20 else None
        if style == "levels":
            return "buy" if abs(last - lo20) < 0.5 * atr and cl[-1] > cl[-2] else None
        if style == "rsi":
            return "buy" if r < 30 else "sell" if r > 70 else None
        if style == "holder":
            return "buy" if random.random() < 0.5 else None
        if style == "scalper":
            return random.choice(["buy", "buy", "sell"])
        return random.choice(["buy", "buy", "sell", None])

    def _house_enter(self, p, tk, side, cs):
        hb, price = p.hb, cs[-1][3]
        atr = max(drills.atr_series(cs)[-1], price * 0.002)
        stop_d = atr * (1.0 if hb["style"] == "scalper" else 2.0)
        eq = self.equity(p)
        if random.random() < hb["skill"]:                  # sized so the stop loses about 1-2% of the account
            amount = eq * random.uniform(0.01, 0.02) * price / stop_d
            amount = min(amount, p.cash * 0.6, eq * 0.35)
        else:                                              # a gut-feel share of the cash
            amount = p.cash * random.uniform(0.1, 0.6)
        if amount < 5:
            return
        ok, _ = self.trade(p, tk, side, None, amount=round(amount, 2))
        if not ok:
            return
        hb["opened"][tk] = self.now
        if random.random() < 0.3 + 0.7 * hb["skill"]:      # the careful ones protect the trade
            d = 1 if side == "buy" else -1
            self.set_exit(p, tk, "stop_loss", round(price - d * stop_d, 4))
            self.set_exit(p, tk, "take_profit", round(price + d * stop_d * random.uniform(1.5, 3.0), 4))

    def _house_manage(self, p, tk):
        hb, s = p.hb, self.stocks.get(tk)
        sh = p.hold.get(tk, 0.0)
        if not s or abs(sh) < 1e-12:
            hb["opened"].pop(tk, None)
            return
        cost = p.cost.get(tk, 0.0)
        gain = ((abs(sh) * s.price - cost) if sh > 0 else (cost - abs(sh) * s.price)) / cost if cost > 0 else 0.0
        held_h = (self.now - hb["opened"].get(tk, self.now)) / HOUR
        close = held_h > hb["hold_h"] * random.uniform(0.7, 1.5)
        if hb["skill"] < 0.4:                              # takes small wins fast, sits on losses until it panics
            close = close and gain > -0.1 or gain > 0.03 or gain < -0.25
        if close:
            if self.trade(p, tk, "sell" if sh > 0 else "buy", 1.0)[0]:
                hb["opened"].pop(tk, None)

    # ------------------------------------------------------------------ the Daily Chart
    def _house_daily_start(self, p):
        r = self.daily_start(p)
        if "error" in r:
            return
        hb = p.hb
        cs = self._dchart()["chart"]["candles"]
        hb["dplan"] = self._house_daily_plan(hb, cs, f"{p.name}:{self._dchart()['day']}")

    def _house_daily_plan(self, hb, cs, seed=None):
        """The trades of a game, decided candle by candle from the candles shown so far (never a later one), each carried
        out a few seconds after its candle: [candle index, side, size]."""
        H, L = daily.HISTORY, daily.LIVE
        cl = [c[3] for c in cs]
        rng = random.Random(seed)
        every = max(1, int(2 + 6 * (1 - hb["skill"]) + rng.random() * 3))     # how often it looks
        size = rng.choice(daily.CHIPS[1:]) if hb["skill"] > 0.5 else rng.choice(daily.CHIPS)
        pos, entry, plan = 0, 0.0, []

        def act(i, want):
            nonlocal pos, entry
            delay = rng.randint(0, 1 if hb["skill"] > 0.6 else 3)
            at = min(H + L - 1, i + delay)
            if pos > 0 and want <= 0:
                plan.append([at, "sell", 1.0])
            if pos < 0 and want >= 0:
                plan.append([at, "buy", 1.0])
            if want > 0 and pos <= 0:
                plan.append([at, "buy", size])
            if want < 0 and pos >= 0:
                plan.append([at, "sell", size])
            pos, entry = want, cl[i]

        style = hb["style"]
        for i in range(H - 1, H + L - 2, every):
            past = cl[:i + 1]
            fast = sum(past[-8:]) / 8
            slow = sum(past[-21:]) / 21
            hi, lo = max(c[1] for c in cs[i - 20:i]), min(c[2] for c in cs[i - 20:i])
            want = pos
            if style in ("trend", "scalper", "holder") or (style == "random" and rng.random() < 0.5):
                want = 1 if fast > slow else (-1 if hb["shorts"] else 0)
                if style == "holder" and pos == 0 and i == H - 1:
                    want = 1
                elif style == "holder":
                    want = pos
            elif style == "shorter":
                want = -1 if fast < slow else 0
            elif style == "breakout":
                want = 1 if cl[i] > hi else -1 if hb["shorts"] and cl[i] < lo else pos
            elif style in ("dip", "levels", "rsi"):
                if pos == 0 and cl[i] <= lo * 1.001:
                    want = 1
                elif pos > 0 and cl[i] >= slow:
                    want = 0
            elif style == "random" and rng.random() < 0.2:
                want = rng.choice([-1, 0, 1])
            if pos and hb["skill"] > 0.5 and (cl[i] / entry - 1) * pos < -0.015:      # a stop
                want = 0
            if want != pos:
                act(i, want)
        if pos and rng.random() < hb["skill"]:             # most careful players are flat at the end
            act(H + L - 3, 0)
        return plan

    def _house_daily_step(self, p):
        d = self._dchart()
        play = d["plays"].get(p.token)
        hb = p.hb
        if play is None or play.get("done") or self.now - play["t0"] >= daily.LIVE:
            hb["dplan"] = []
            return
        shown = self._daily_shown(play) - 1
        while hb["dplan"] and hb["dplan"][0][0] <= shown:
            _, side, pct = hb["dplan"].pop(0)
            self.daily_trade(p, side, pct)
