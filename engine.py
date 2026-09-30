import glob, json, logging, math, os, random, time, uuid
from collections import deque

START_CASH = 1000.0          # default signup bonus and bot bankroll (test credits)
FEE = 0.005                  # per side, collected as house revenue
COOLDOWN = 1.0
MAX_POOL_FRAC = 0.05
SNAP_EVERY = 5.0
MARKET_DAY_SECONDS = 1800
TRADING_DAYS_PER_YEAR = 252
INTRADAY_CANDLE_SECONDS = 60
MAX_TICK_MOVE = 0.15

logger = logging.getLogger(__name__)

# Economics
# ---------
# Every token sits in exactly one place: a player's cash, a stock pool (T), the house reserve,
# or collected fees. Only trades move tokens, and only deposits/withdrawals and house capital
# injections change the total (`minted`). News, noise and mean reversion move prices by
# changing a pool's share count (S) instead of its tokens, so they never create money. Player
# gains are paid by other players (or by the house's pool liquidity when the house is on the
# other side), and the house earns FEE on every trade.


class Stock:
    def __init__(self, cfg, tokens):
        self.ticker = cfg["ticker"]
        self.update(cfg)
        self.T = float(tokens)
        self.S = float(tokens) / self.initial_price
        self.base = float(tokens)
        self.fair = self.fair_open = self.initial_price  # exogenous value path, excludes trade impact
        self.hist = deque(maxlen=MARKET_DAY_SECONDS + 1)
        self.candles = deque(maxlen=2 * MARKET_DAY_SECONDS // INTRADAY_CANDLE_SECONDS)
        self.daily_hist = deque(maxlen=366)
        self.day_open = self.day_high = self.day_low = self.price
        self.next_earn = None
        self.next_rating_review = None
        self.distress_checked = False

    def update(self, cfg):
        self.name = cfg["name"]
        self.sector = cfg["sector"]
        self.beta = float(cfg.get("beta", 1.0))
        self.vol = float(cfg.get("vol", 0.30))
        self.sens = float(cfg.get("sens", 1.0))
        self.initial_price = max(0.01, float(cfg.get("initial_price", 1.0)))
        self.market_cap_base = float(cfg.get("market_cap", 0.0))
        configured_shares = float(cfg.get("shares_outstanding", 0.0))
        self.shares_outstanding = (self.market_cap_base / self.initial_price
                       if self.market_cap_base > 0 else configured_shares)
        self.dividend_yield = float(cfg.get("dividend_yield", 0.0))
        self.price_unit = cfg.get("price_unit", "MB/share")
        self.asset_type = cfg.get("asset_type", "equity")
        self.rating = cfg.get("rating", "BBB")
        self.margin = float(cfg.get("margin", 0.12))
        self.dependencies = dict(cfg.get("dependencies", {}))
        self.revenue = float(cfg.get("revenue", 0.0))
        self.cash = float(cfg.get("cash", 0.0))
        self.debt = float(cfg.get("debt", 0.0))
        self.traits = list(cfg.get("traits", []))
        self.desc = cfg.get("desc", "")

    @property
    def price(self):
        return self.T / self.S

    def quote_buy(self, cash):
        fee = cash * FEE
        t = cash - fee
        new_S = self.T * self.S / (self.T + t)
        return self.S - new_S, fee

    def quote_sell(self, shares):
        new_T = self.T * self.S / (self.S + shares)
        gross = self.T - new_T
        fee = gross * FEE
        return gross - fee, fee

    def move(self, r):
        """Exogenous price move: token-neutral, only the pool's share count changes."""
        self.S /= 1 + r
        self.fair *= 1 + r


class Player:
    def __init__(self, name, bot=False, strategy=None):
        self.name = name
        self.token = uuid.uuid4().hex
        self.cash = 0.0
        self.deposited = 0.0     # net tokens credited to this account (signup, deposits - withdrawals)
        self.season_base = 0.0   # equity at season start plus deposits during the season
        self.hold = {}
        self.last_trade = {}
        self.bot = bot
        self.strategy = strategy
        self.snaps = deque(maxlen=240)
        self.trades = 0
        self.seen = set()


class Engine:
    def __init__(self, content_glob="*.json", state_file="state.json", bots=True):
        self.content_glob = content_glob
        self.state_file = state_file
        self.now = time.time()
        self.sectors, self.templates, self.settings = {}, {}, {}
        self.market_profiles = {}
        self.stocks = {}
        self.delisted = []
        self.players = {}
        self.by_token = {}
        self.events = []
        self.news_log = deque(maxlen=200)
        self.hints = deque(maxlen=20)
        self.history = []
        self.house = 0.0          # house reserve: funds new listings, receives delisted pools
        self.fees = 0.0           # fee revenue
        self.house_capital = 0.0  # tokens the house has put in (pool seeds, reserve, bot bankrolls)
        self.minted = 0.0
        self.season_no = 1
        self.last_snap = 0.0
        self.board = []
        self.rank = {}
        self.pub_stocks = []
        self.index_level = 100.0
        self.index_hist = deque(maxlen=MARKET_DAY_SECONDS + 1)
        self.market_day = int(self.now // MARKET_DAY_SECONDS)
        self._pending = {}
        self.regime = "Expansion"
        regime_window = self.settings.get("regime_days", [7, 14])
        self.next_regime_change = self.now + random.uniform(*regime_window) * MARKET_DAY_SECONDS
        self.sector_indices = {}
        self.content_sig = None
        self._reload(initial=True)
        seed = float(self.settings.get("house_seed", self.settings.get("treasury_seed", 50000)))
        self._mint_house(seed)
        self.house += seed
        self.season_end = self.now + float(self.settings.get("season_seconds", 3600))
        event_mean = float(self.settings.get("event_mean_seconds", 120))
        self.next_event = self.now + random.expovariate(1 / event_mean)
        self._load_state()
        self.index_prev = {tk: s.price for tk, s in self.stocks.items()}
        self.index_hist.clear()
        self.index_hist.append(self.index_level)
        if bots and not self.by_token_bots():
            self._add_bots(int(self.settings.get("bots", 8)))

    def by_token_bots(self):
        return [p for p in self.players.values() if p.bot]

    # ---------- content ----------
    def _content_files(self):
        state_path = os.path.abspath(self.state_file) if self.state_file else None
        return [f for f in glob.glob(self.content_glob) if os.path.abspath(f) != state_path]

    def _sig(self):
        return tuple((f, os.path.getmtime(f)) for f in sorted(self._content_files()))

    def _read(self):
        sectors, companies, templates, settings, profiles = {}, {}, {}, {}, {}
        for f in sorted(self._content_files()):
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            settings.update(d.get("settings", {}))
            profiles.update(d.get("profiles", {}))
            for x in d.get("sectors", []):
                sectors[x["id"]] = x
            for x in d.get("companies", []):
                companies[x["ticker"]] = x
            for x in d.get("templates", []):
                templates[x["id"]] = x
        return sectors, companies, templates, settings, profiles

    def _reload(self, initial=False):
        try:
            sectors, companies, templates, settings, profiles = self._read()
        except Exception as e:
            logger.exception("content reload failed")
            self.news("system", f"Content reload failed: {e}")
            return
        self.content_sig = self._sig()
        self.sectors, self.templates = sectors, templates
        self.settings.update(settings)
        self.market_profiles.update(profiles)
        for tk, cfg in companies.items():
            if cfg["sector"] not in sectors:
                continue
            if tk in self.delisted:
                continue
            cfg = {**cfg, **self.market_profiles.get(tk, {})}
            if tk in self.stocks:
                self.stocks[tk].update(cfg)
            else:
                self._list(cfg, initial)

    def _mint_house(self, amount):
        self.minted += amount
        self.house_capital += amount

    def _list(self, cfg, initial):
        depth = float(cfg.get("depth", 20000))
        take = 0.0 if initial else min(max(self.house, 0.0), depth)
        self.house -= take
        if depth > take:
            self._mint_house(depth - take)
        s = Stock(cfg, depth)
        first_earn = self.settings.get("earnings_initial_seconds", [1800, 5400])
        s.next_earn = self.now + random.uniform(*first_earn) if "earnings" in s.traits else None
        s.next_rating_review = (self.now + random.uniform(*self._review_days()) * MARKET_DAY_SECONDS
                                if s.asset_type == "equity" else None)
        s.hist.append(s.price)
        s.day_open = s.day_high = s.day_low = s.price
        self.stocks[s.ticker] = s
        self._record(s)
        if not initial:
            sec = self.sectors[s.sector]["name"]
            self.news("ipo", f"NEW LISTING: {s.name} ({s.ticker}) debuts in {sec}. {s.desc}", [s.ticker])

    def _review_days(self):
        return self.settings.get("rating_review_days", [7, 14])

    # ---------- news ----------
    def news(self, kind, text, tickers=(), dirn=0, strength="bystander"):
        self.news_log.append({"id": len(self.news_log) and self.news_log[-1]["id"] + 1 or 1,
                              "t": self.now, "kind": kind, "text": text,
                              "tickers": list(tickers)[:4], "dir": dirn})

    # ---------- players / money in and out ----------
    def join(self, name):
        name = "".join(c for c in name if c.isalnum() or c in "_-. ")[:16].strip()
        if len(name) < 2:
            return None, "Name must be 2-16 letters/numbers"
        if any(p.name.lower() == name.lower() for p in self.players.values()):
            return None, "Name taken"
        p = Player(name)
        self._register(p)
        bonus = float(self.settings.get("signup_bonus", START_CASH))
        if bonus > 0:
            self.credit(p, bonus)
        return p, ""

    def _register(self, p):
        self.players[p.token] = p
        self.by_token[p.token] = p

    def credit(self, p, amount):
        """Tokens enter the game (purchase of memebucks, signup credit)."""
        amount = float(amount)
        if amount <= 0:
            return False, "Amount must be positive"
        p.cash += amount
        p.deposited += amount
        p.season_base += amount
        self.minted += amount
        return True, f"Credited {amount:.2f} MB"

    def debit(self, p, amount):
        """Tokens leave the game (withdrawal). Only free cash can be withdrawn."""
        amount = float(amount)
        if amount <= 0:
            return False, "Amount must be positive"
        if amount > p.cash + 1e-9:
            return False, "Not enough cash; sell positions first"
        amount = min(amount, p.cash)
        p.cash -= amount
        p.deposited -= amount
        p.season_base = max(0.0, p.season_base - amount)
        self.minted -= amount
        return True, f"Withdrew {amount:.2f} MB"

    def _add_bots(self, n):
        strategies = ["random", "momentum", "contrarian", "news"]
        bankroll = float(self.settings.get("bot_cash", START_CASH))
        for i in range(n):
            st = strategies[i % 4]
            p = Player(f"bot_{st}_{i // 4 + 1}", bot=True, strategy=st)
            self._register(p)
            p.cash = p.deposited = p.season_base = bankroll
            self._mint_house(bankroll)

    def equity(self, p):
        v = p.cash
        for tk, sh in p.hold.items():
            s = self.stocks.get(tk)
            if s:
                v += s.quote_sell(sh)[0]
        return v

    # ---------- trading ----------
    def _do_buy(self, p, s, cash):
        shares, fee = s.quote_buy(cash)
        s.T += cash - fee
        s.S -= shares
        self.fees += fee
        p.cash -= cash
        p.hold[s.ticker] = p.hold.get(s.ticker, 0.0) + shares
        self._record(s)
        return shares

    def _do_sell(self, p, s, shares):
        proceeds, fee = s.quote_sell(shares)
        s.T -= proceeds + fee
        s.S += shares
        self.fees += fee
        p.cash += proceeds
        left = p.hold.get(s.ticker, 0.0) - shares
        if left < 1e-9:
            p.hold.pop(s.ticker, None)
        else:
            p.hold[s.ticker] = left
        self._record(s)
        return proceeds

    def trade(self, p, ticker, side, pct):
        s = self.stocks.get(ticker)
        if not s:
            return False, "Unknown ticker"
        if not (0 < pct <= 1):
            return False, "Bad size"
        if self.now - p.last_trade.get(ticker, 0) < COOLDOWN:
            return False, "Cooldown: 1s between trades in the same stock"
        note = ""
        if side == "buy":
            cash = p.cash * pct
            cap = MAX_POOL_FRAC * s.T / (1 - FEE)
            if cash > cap:
                cash, note = cap, " (capped by pool depth)"
            if cash < 1:
                return False, "Not enough cash (min 1)"
            sh = self._do_buy(p, s, cash)
            msg = f"Bought {sh:.2f} {ticker} for {cash:.2f} MB{note}"
        elif side == "sell":
            held = p.hold.get(ticker, 0.0)
            if held <= 0:
                return False, f"You hold no {ticker}"
            sh = held * pct if pct < 1 else held
            if sh > 0.25 * s.S:
                sh, note = 0.25 * s.S, " (capped by pool depth)"
            got = self._do_sell(p, s, sh)
            msg = f"Sold {sh:.2f} {ticker} for {got:.2f} MB{note}"
        else:
            return False, "Bad side"
        p.last_trade[ticker] = self.now
        p.trades += 1
        return True, msg

    # ---------- price history ----------
    def _record(self, s):
        price = s.price
        minute = int(self.now // INTRADAY_CANDLE_SECONDS) * INTRADAY_CANDLE_SECONDS
        c = s.candles[-1] if s.candles else None
        if c and c[0] == minute:
            c[2], c[3], c[4] = max(c[2], price), min(c[3], price), price
        else:
            s.candles.append([minute, price, price, price, price])
        s.day_high = max(s.day_high, price)
        s.day_low = min(s.day_low, price)

    # ---------- market dynamics ----------
    # Exogenous moves are queued into self._pending during a tick and applied together in
    # _flush_moves, so knock-on effects land in the same tick as their cause and cannot be
    # front-run from the previous state.
    def _queue(self, returns):
        for tk, r in returns.items():
            if tk in self.stocks and r:
                self._pending[tk] = (1 + self._pending.get(tk, 0.0)) * (1 + r) - 1

    def _random_market_moves(self):
        annual_scale = math.sqrt(TRADING_DAYS_PER_YEAR * MARKET_DAY_SECONDS)
        market_shock = random.gauss(0.0, 1.0)
        sector_shocks = {sector: random.gauss(0.0, 1.0) for sector in self.sectors}
        returns = {}
        for stock in self.stocks.values():
            market_sigma = stock.beta * 0.18
            sector_sigma = 0.08
            idio_sigma = math.sqrt(max(stock.vol ** 2 - market_sigma ** 2 - sector_sigma ** 2, 0.005 ** 2))
            shock = (market_sigma * market_shock + sector_sigma * sector_shocks.get(stock.sector, 0.0)
                     + idio_sigma * random.gauss(0.0, 1.0)) / annual_scale
            returns[stock.ticker] = max(-0.01, min(0.01, shock))
        self._queue(returns)

    def _mean_revert(self):
        # Pulls the exogenous fair value back toward the reference price. Player price impact is
        # not reverted, so buying and later selling costs only fees and slippage.
        halflife_days = float(self.settings.get("mean_reversion_halflife_days", 7.0))
        if halflife_days <= 0:
            return
        rate = 1 - 0.5 ** (1.0 / (halflife_days * MARKET_DAY_SECONDS))
        self._queue({tk: rate * (s.initial_price / s.fair - 1)
                     for tk, s in self.stocks.items() if s.fair > 0})

    def _event_returns(self, betas, index_move, impact, strength):
        """Full move per ticker for a positive event; a negative event is the mirror image."""
        strength_limits = {"bystander": 0.1, "weak": 0.35, "strong": 0.65, "very strong": 1.0}
        out = {}
        for tk, s in self.stocks.items():
            crowd = min(2.0, max(0.5, s.T / s.base))
            vol_scale = min(1.8, max(0.5, math.sqrt(s.vol / 0.30)))
            market_return = s.beta * index_move * vol_scale
            catalyst_return = impact * betas.get(tk, 0.0) * s.sens * crowd * vol_scale
            daily_limit = (s.vol / math.sqrt(TRADING_DAYS_PER_YEAR)
                           * strength_limits.get(strength, 0.35)
                           * max(0.5, min(2.0, abs(s.beta))))
            r = max(-daily_limit, min(daily_limit, market_return + catalyst_return))
            if r:
                out[tk] = r
        return out

    def _spawn_event(self, tpl=None, target=None, direction=None, strength=None):
        if tpl is None:
            pool = [t for t in self.templates.values() if t.get("weight", 1) > 0]
            if not pool:
                return
            tpl = random.choices(pool, weights=[t.get("weight", 1) for t in pool])[0]
        scope = tpl.get("scope", "market")
        tgt_sector, label = None, "the market"
        if scope == "company":
            target = target or tpl.get("ticker")
            if target is None:
                c = [s for s in self.stocks.values() if tpl.get("sector") in (None, s.sector)]
                if not c:
                    return
                target = random.choice(c).ticker
            if target not in self.stocks:
                return
            label = self.stocks[target].name
        elif scope == "sector":
            tgt_sector = tpl.get("sector") or random.choice(list(self.sectors))
            if tgt_sector not in self.sectors:
                return
            label = self.sectors[tgt_sector]["name"]
        b = tpl.get("betas", {})
        betas = {}
        for s in self.stocks.values():
            v = b.get(s.ticker, 0) + b.get(s.sector, 0) + b.get("*", 0)
            if scope == "company" and s.ticker == target:
                v += b.get("self", 0)
            if scope == "sector" and s.sector == tgt_sector:
                v += b.get("self", 0)
            if v:
                betas[s.ticker] = v
        if not betas:
            return
        # Direction is a fair coin: news must not be predictable from recent price action.
        sign = direction if direction in (-1, 1) else random.choice([-1, 1])
        strength_weights = self.settings.get("news_strength_weights", {
            "bystander": 0.25, "weak": 0.4, "strong": 0.25, "very strong": 0.1})
        strength = strength or tpl.get("strength") or random.choices(
            list(strength_weights), weights=list(strength_weights.values()))[0]
        ranges = self.settings.get("news_move_ranges", {})
        impact = random.uniform(*ranges.get(strength, [0.0, 0.005]))
        index_move = float(tpl.get("index_bias", 1.0)) * impact if scope == "market" else 0.0
        up_moves = self._event_returns(betas, index_move, impact, strength)
        final = {tk: sign * r for tk, r in up_moves.items()}
        fmt = lambda arr: random.choice(arr).format(name=label, sector=label)
        text = fmt(tpl["up"] if sign > 0 else tpl["down"])
        top = sorted(betas, key=lambda k: -abs(betas[k]))[:4]
        shown = sign
        if tpl.get("rumor") and random.random() < float(self.settings.get("rumor_prob", 0.6)):
            # The rumor moves the price by its expected value now; the confirmation or correction
            # moves it the rest of the way. Expected profit from trading on the rumor is zero.
            cred = float(self.settings.get("rumor_credibility", 0.75))
            shown = sign if random.random() < cred else -sign
            pre = {tk: shown * (2 * cred - 1) * r for tk, r in up_moves.items()}
            rest = {tk: (1 + final[tk]) / (1 + pre[tk]) - 1 for tk in final}
            rumor_delay = self.settings.get("rumor_delay_seconds", [45, 90])
            self.events.append({"start": self.now + random.uniform(*rumor_delay), "rest": rest,
                                "sign": sign, "shown": shown, "text": text, "top": top,
                                "strength": strength})
            self.news("rumor", "RUMOR: " + fmt(tpl["up"] if shown > 0 else tpl["down"]), top, shown, strength)
            self._queue(pre)
        else:
            self.news("breaking", "BREAKING: " + text, top, sign, strength)
            self._queue(final)
        self.hints.append({"id": uuid.uuid4().hex, "t": self.now, "dir": shown, "betas": betas})

    def _events(self):
        if self.now >= self.next_event:
            self._spawn_event()
            self.next_event = self.now + random.expovariate(1 / float(self.settings.get("event_mean_seconds", 120)))
        for ev in list(self.events):
            if self.now < ev["start"]:
                continue
            tag = "CONFIRMED" if ev["shown"] == ev["sign"] else "CORRECTION"
            self.news("confirm" if tag == "CONFIRMED" else "correction", f"{tag}: {ev['text']}",
                      ev["top"], ev["sign"], ev["strength"])
            self._queue(ev["rest"])
            self.events.remove(ev)

    def _earnings(self):
        tpl = self.templates.get("earnings")
        if not tpl:
            return
        for s in self.stocks.values():
            if s.next_earn and self.now >= s.next_earn:
                interval = self.settings.get("earnings_interval_seconds", [3600, 10800])
                s.next_earn = self.now + random.uniform(*interval)
                self._spawn_event(tpl, s.ticker)

    def _credit_reviews(self):
        ratings = ["D", "C", "CC", "CCC", "B", "BB", "BBB", "A", "AA", "AAA"]
        for stock in list(self.stocks.values()):
            if not stock.next_rating_review or self.now < stock.next_rating_review:
                continue
            stock.next_rating_review = self.now + random.uniform(*self._review_days()) * MARKET_DAY_SECONDS
            index = ratings.index(stock.rating) if stock.rating in ratings else ratings.index("BBB")
            probability = random.random()
            direction = -1 if stock.margin < 0 and probability < 0.65 else (
                1 if probability < 0.2 else -1 if probability < 0.3 else 0)
            next_index = max(0, min(len(ratings) - 1, index + direction))
            if next_index == index:
                self.news("rating", f"Bank analysts maintain {stock.name} at {stock.rating}.",
                          [stock.ticker], 0, "bystander")
                continue
            stock.rating = ratings[next_index]
            template = {
                "scope": "company", "ticker": stock.ticker,
                "up": [f"Bank analysts upgrade {stock.name} to {stock.rating}"],
                "down": [f"Bank analysts downgrade {stock.name} to {stock.rating}"],
                "betas": {"self": 1.0}, "strength": "weak", "rumor": False,
            }
            self._spawn_event(template, stock.ticker, direction, "weak")

    def _advance_regime(self):
        if self.now < self.next_regime_change:
            return
        previous = self.regime
        if previous == "Bubble":
            self.regime = "Recession"
        else:
            self.regime = random.choices(
                ["Expansion", "Boom", "Bubble", "Recession"], weights=[0.42, 0.25, 0.12, 0.21])[0]
        window = self.settings.get("regime_days", [7, 14])
        self.next_regime_change = self.now + random.uniform(*window) * MARKET_DAY_SECONDS
        if self.regime == "Boom":
            direction, strength = 1, "strong"
        elif self.regime == "Bubble":
            direction, strength = 1, "very strong"
        elif self.regime == "Recession":
            direction, strength = -1, "very strong" if previous == "Bubble" else "strong"
        else:
            direction, strength = random.choice([-1, 1]), "weak"
        impact = random.uniform(*self.settings.get("news_move_ranges", {}).get(strength, [0.01, 0.03]))
        moves = self._event_returns({}, impact, 0.0, strength)
        self._queue({tk: direction * r for tk, r in moves.items()})
        self.news("macro", f"Market regime: {previous} to {self.regime}.", (), direction, strength)

    def _dependency_returns(self, source_returns):
        sector_returns = {}
        for sector_id in self.sectors:
            members = [s for s in self.stocks.values() if s.sector == sector_id]
            weight = sum(s.base for s in members)
            if weight:
                sector_returns[sector_id] = sum(
                    s.base * source_returns.get(s.ticker, 0.0) for s in members
                ) / weight
        linked = {}
        for tk, stock in self.stocks.items():
            r = sum(source_returns.get(src, 0.0) * float(k) for src, k in stock.dependencies.items())
            for source_sector, targets in self.settings.get("sector_links", {}).items():
                r += sector_returns.get(source_sector, 0.0) * float(targets.get(stock.sector, 0.0))
            if r:
                linked[tk] = r
        return linked

    def _flush_moves(self):
        pending, self._pending = self._pending, {}
        self._queue(pending)
        self._queue(self._dependency_returns(pending))
        pending, self._pending = self._pending, {}
        for tk, r in pending.items():
            s = self.stocks[tk]
            # daily move envelope on the exogenous fair value (player trades are not clamped)
            daily_sigma = s.vol / math.sqrt(TRADING_DAYS_PER_YEAR)
            limit = min(0.15, daily_sigma * (1.5 + 0.75 * min(abs(s.beta), 2.0)))
            target = s.fair * (1 + max(-MAX_TICK_MOVE, min(MAX_TICK_MOVE, r)))
            target = max(s.fair_open * (1 - limit), min(s.fair_open * (1 + limit), target))
            s.move(target / s.fair - 1)

    def _check_distress(self):
        threshold = float(self.settings.get("distress_price_ratio", 0.25))
        bailout_chance = float(self.settings.get("bailout_chance", 0.25))
        for ticker, stock in list(self.stocks.items()):
            ratio = stock.fair / stock.initial_price
            if stock.distress_checked:
                if ratio > 2 * threshold:
                    stock.distress_checked = False
                continue
            if ratio > threshold:
                continue
            stock.distress_checked = True
            if random.random() < bailout_chance:
                stock.move(float(self.settings.get("bailout_return", 0.25)))
                stock.rating = "B" if stock.rating not in ("D", "C", "CC", "CCC") else stock.rating
                self.news("bailout", f"Emergency bank facility rescues {stock.name}.",
                          [ticker], 1, "very strong")
                continue
            # Bankruptcy: holders are cashed out at the pool's current price (no fee), the
            # remaining pool liquidity returns to the house reserve.
            for player in self.players.values():
                sh = player.hold.pop(ticker, 0.0)
                if sh > 0:
                    new_T = stock.T * stock.S / (stock.S + sh)
                    player.cash += stock.T - new_T
                    stock.T, stock.S = new_T, stock.S + sh
            self.house += stock.T
            self.delisted.append(ticker)
            self.stocks.pop(ticker)
            self.index_prev.pop(ticker, None)
            self.news("bankruptcy", f"{stock.name} files for bankruptcy and is delisted; holders are paid out at the last price.",
                      [ticker], -1, "very strong")

    # ---------- bots ----------
    def _ret(self, s, n=60):
        h = s.hist
        return h[-1] / h[-n] - 1 if len(h) >= n else 0.0

    def _bot_act(self, p):
        stocks = list(self.stocks.values())
        strat = p.strategy
        if strat == "random":
            s = random.choice(stocks)
            if random.random() < 0.6:
                self.trade(p, s.ticker, "buy", random.uniform(0.05, 0.2))
            elif s.ticker in p.hold:
                self.trade(p, s.ticker, "sell", random.choice([0.5, 1]))
        elif strat in ("momentum", "contrarian"):
            ranked = sorted(stocks, key=lambda s: self._ret(s))
            best, worst = ranked[-1], ranked[0]
            if strat == "contrarian":
                best, worst = worst, best
            if worst.ticker in p.hold:
                self.trade(p, worst.ticker, "sell", 1)
            if p.cash > 20:
                self.trade(p, best.ticker, "buy", 0.25)
        elif strat == "news":
            for h in list(self.hints):
                if h["id"] in p.seen or self.now - h["t"] > 8:
                    continue
                p.seen.add(h["id"])
                eff = {tk: h["dir"] * b for tk, b in h["betas"].items()}
                for tk, v in eff.items():
                    if v < -0.3 and tk in p.hold:
                        self.trade(p, tk, "sell", 1)
                pos = sorted([tk for tk, v in eff.items() if v > 0.3], key=lambda k: -eff[k])[:2]
                for tk in pos:
                    if p.cash > 20:
                        self.trade(p, tk, "buy", 0.3)
                break
            if len(p.seen) > 200:
                p.seen = {h["id"] for h in self.hints}

    def _bots(self):
        for p in self.players.values():
            if p.bot and random.random() < float(self.settings.get("bot_action_probability", 0.01)):
                self._bot_act(p)

    # ---------- season / scoring ----------
    # Seasons are leaderboard periods only. Balances are real and are never reset.
    def _snapshot(self):
        for p in self.players.values():
            p.snaps.append(self.equity(p))

    @staticmethod
    def _score(p):
        s = list(p.snaps)
        if len(s) < 5:
            return 0.0
        r = [b / a - 1 for a, b in zip(s, s[1:]) if a > 0]
        if not r:
            return 0.0
        m = sum(r) / len(r)
        sd = math.sqrt(sum((x - m) ** 2 for x in r) / len(r))
        return m / sd if sd > 1e-9 else 0.0

    def season_return(self, p, equity=None):
        e = self.equity(p) if equity is None else equity
        return e / p.season_base - 1 if p.season_base > 1e-9 else 0.0

    def _board(self):
        rows = []
        for p in self.players.values():
            e = self.equity(p)
            rows.append({"name": p.name, "equity": e, "ret": self.season_return(p, e),
                         "score": self._score(p), "bot": p.bot, "token": p.token})
        rows.sort(key=lambda r: -r["ret"])
        self.board = rows
        self.rank = {r["token"]: i + 1 for i, r in enumerate(rows)}

    def _end_season(self):
        self._board()
        top = [(r["name"], round(r["ret"] * 100, 1)) for r in self.board[:5]]
        self.history.append({"season": self.season_no, "top": top})
        self.history = self.history[-10:]
        for p in self.players.values():
            p.season_base = self.equity(p)
            p.snaps.clear()
            p.trades = 0
        winner = top[0] if top else ("nobody", 0)
        self.news("season", f"SEASON {self.season_no} OVER. Winner: {winner[0]} ({winner[1]:+}%). "
                            "Balances carry over; a new leaderboard starts now.")
        self.season_no += 1
        self.season_end = self.now + float(self.settings.get("season_seconds", 3600))

    # ---------- main tick ----------
    def tick(self, now=None):
        self.now = now if now is not None else time.time()
        if self._sig() != self.content_sig:
            self._reload()
        self._pending = {}
        self._mean_revert()
        self._random_market_moves()
        self._advance_regime()
        self._credit_reviews()
        self._events()
        self._earnings()
        self._flush_moves()
        self._check_distress()
        self._bots()
        self._update_index()
        for s in self.stocks.values():
            s.hist.append(s.price)
            self._record(s)
        self._update_index_level()
        if self.now - self.last_snap >= SNAP_EVERY:
            self.last_snap = self.now
            self._snapshot()
        if self.now >= self.season_end:
            self._end_season()
        self._board()
        self._public()

    def _update_index(self):
        """Roll the daily candle when the game day changes."""
        current_day = int(self.now // MARKET_DAY_SECONDS)
        if current_day <= self.market_day:
            return
        for stock in self.stocks.values():
            stock.daily_hist.append((self.market_day, stock.day_open, stock.day_high, stock.day_low, stock.price))
            stock.day_open = stock.day_high = stock.day_low = stock.price
            stock.fair_open = stock.fair
        self.market_day = current_day

    def _update_index_level(self):
        total_weight = sum(s.base for s in self.stocks.values())
        if total_weight:
            weighted_return = sum(
                s.base * (s.price / self.index_prev.get(tk, s.price) - 1)
                for tk, s in self.stocks.items()
            ) / total_weight
            self.index_level *= max(0.001, 1 + weighted_return)
        self.index_prev = {tk: s.price for tk, s in self.stocks.items()}
        self.index_hist.append(self.index_level)

    def _day_ref(self, s):
        """Price one game day ago, from the minute candles."""
        cutoff = self.now - MARKET_DAY_SECONDS
        for c in s.candles:
            if c[0] >= cutoff:
                return c[1]
        return s.hist[0] if s.hist else s.price

    def _public(self):
        out = []
        for s in self.stocks.values():
            h = list(s.hist)
            ref = self._day_ref(s)
            display_price = round(s.price, 4)
            display_shares = round(s.shares_outstanding, 9)
            market_cap = display_shares * display_price
            earnings = s.revenue * s.margin
            out.append({"ticker": s.ticker, "name": s.name, "desc": s.desc,
                        "sector": s.sector, "asset_type": s.asset_type,
                        "beta": s.beta, "rating": s.rating,
                        "price_unit": s.price_unit,
                        "price": display_price, "chg": round(s.price / ref - 1, 4),
                        "spark": [round(x, 4) for x in h[-60:]], "vol": s.vol,
                        "traits": s.traits, "pool": round(s.T),
                        "financials": {"market_cap": round(market_cap, 9), "revenue": round(s.revenue, 6),
                                       "net_income": round(earnings, 6), "cash": round(s.cash, 6),
                                       "debt": round(s.debt, 6), "margin": round(s.margin, 6),
                                       "shares_outstanding": display_shares,
                                       "eps": round(earnings / s.shares_outstanding, 9)
                                       if s.shares_outstanding > 0 else None,
                                       "dividend_yield": round(s.dividend_yield * s.initial_price / s.price, 4)
                                       if s.price > 0 else 0.0,
                                       "pe": round(market_cap / earnings, 6)
                                       if s.asset_type == "equity" and earnings > 0 else None}})
        self.pub_stocks = out
        index_ref = self.index_hist[0]
        self.pub_index = {"value": round(self.index_level, 3),
                          "chg": round(self.index_level / index_ref - 1, 4),
                          "spark": [round(x, 3) for x in self.index_hist]}
        self.sector_indices = {}
        for sector_id, sector in self.sectors.items():
            members = [s for s in self.stocks.values() if s.sector == sector_id]
            weight = sum(s.base for s in members)
            level = 100 * sum(s.base * s.price / s.initial_price for s in members) / weight if weight else 100.0
            self.sector_indices[sector_id] = {"value": round(level, 2), "chg": round(level / 100 - 1, 4)}

    def history_for(self, ticker, period):
        stock = self.stocks.get(ticker)
        if not stock:
            return {"type": "history", "error": "Unknown or delisted stock"}
        if period == "day":
            cutoff = self.now - MARKET_DAY_SECONDS
            candles = [{"t": t, "o": o, "h": h, "l": l, "c": c}
                       for t, o, h, l, c in stock.candles if t >= cutoff]
        else:
            history = list(stock.daily_hist)
            live = (self.market_day, stock.day_open, stock.day_high, stock.day_low, stock.price)
            if history and history[-1][0] == self.market_day:
                history[-1] = live
            else:
                history.append(live)
            if period == "week":
                window = history[-7:]
            elif period == "month":
                window = history[-30:]
            else:
                daily = history[-365:]
                window = []
                for i in range(0, len(daily), 7):
                    chunk = daily[i:i + 7]
                    window.append((chunk[0][0], chunk[0][1],
                                   max(x[2] for x in chunk), min(x[3] for x in chunk), chunk[-1][4]))
            candles = [{"t": d * MARKET_DAY_SECONDS, "o": o, "h": h, "l": l, "c": c} for d, o, h, l, c in window]
        for candle in candles:
            for k in "ohlc":
                candle[k] = round(candle[k], 5)
        return {"type": "history", "ticker": ticker, "period": period, "candles": candles,
                "day_seconds": MARKET_DAY_SECONDS, "now": self.now}

    def _upcoming_events(self):
        events = []
        for stock in self.stocks.values():
            if stock.next_earn:
                events.append({"ticker": stock.ticker, "name": stock.name, "kind": "Earnings",
                               "at": stock.next_earn, "in_seconds": max(0, int(stock.next_earn - self.now))})
            if stock.next_rating_review:
                events.append({"ticker": stock.ticker, "name": stock.name, "kind": "Bank rating review",
                               "at": stock.next_rating_review,
                               "in_seconds": max(0, int(stock.next_rating_review - self.now))})
        return sorted(events, key=lambda event: event["at"])[:20]

    def state_for(self, p):
        e = self.equity(p)
        px = {s["ticker"]: s["price"] for s in self.pub_stocks}
        hold = [{"ticker": tk, "shares": round(sh, 4), "value": round(sh * px.get(tk, 0), 2)}
                for tk, sh in p.hold.items()]
        return {"type": "state", "season": self.season_no,
                "season_left": max(0, int(self.season_end - self.now)),
                "index": self.pub_index,
                "upcoming": self._upcoming_events(),
                "cash": round(p.cash, 2), "equity": round(e, 2), "ret": round(self.season_return(p, e), 4),
                "pnl": round(e - p.deposited, 2),
                "holdings": hold,
                "sectors": [{"id": k, "name": v["name"], "icon": v.get("icon", ""),
                             **self.sector_indices.get(k, {})} for k, v in self.sectors.items()],
                "stocks": self.pub_stocks,
                "news": [n for n in list(self.news_log)[-30:]][::-1],
                "board": [{"name": r["name"], "equity": round(r["equity"], 2), "ret": round(r["ret"], 4),
                           "score": round(r["score"], 2), "bot": r["bot"]} for r in self.board[:10]],
                "rank": self.rank.get(p.token), "players": len(self.players)}

    # ---------- accounting / persistence ----------
    def total_tokens(self):
        return (self.house + self.fees + sum(s.T for s in self.stocks.values())
                + sum(p.cash for p in self.players.values()))

    def house_stats(self):
        """House P&L. Players' combined P&L is the mirror image of the house's (zero-sum)."""
        humans = [p for p in self.players.values() if not p.bot]
        bots = [p for p in self.players.values() if p.bot]
        human_equity = sum(self.equity(p) for p in humans)
        human_in = sum(p.deposited for p in humans)
        bots_pnl = sum(self.equity(p) - p.deposited for p in bots)
        players_pnl = human_equity - human_in
        house_pnl = -players_pnl
        return {"fees": self.fees, "house_pnl": house_pnl, "bots_pnl": bots_pnl,
                "liquidity_pnl": house_pnl - self.fees - bots_pnl,
                "players_pnl": players_pnl, "player_deposits": human_in, "player_equity": human_equity,
                "player_cash": sum(p.cash for p in humans), "house_capital": self.house_capital,
                "house_reserve": self.house, "pool_tokens": sum(s.T for s in self.stocks.values()),
                "minted": self.minted, "invariant_drift": self.total_tokens() - self.minted,
                "humans": len(humans)}

    def save(self):
        d = {"schema": 6, "house": self.house, "fees": self.fees, "house_capital": self.house_capital,
             "minted": self.minted, "index_level": self.index_level,
             "index_hist": list(self.index_hist), "market_day": self.market_day,
             "regime": self.regime, "next_regime_change": self.next_regime_change,
             "delisted": self.delisted, "season_no": self.season_no,
             "season_end": self.season_end, "history": self.history,
             "stocks": {t: {"T": s.T, "S": s.S, "base": s.base, "fair": s.fair, "fair_open": s.fair_open,
                            "daily_hist": list(s.daily_hist), "candles": list(s.candles), "rating": s.rating,
                            "day_open": s.day_open, "day_high": s.day_high, "day_low": s.day_low,
                            "next_earn": s.next_earn,
                            "next_rating_review": s.next_rating_review,
                            "distress_checked": s.distress_checked}
                        for t, s in self.stocks.items()},
             "players": [{"name": p.name, "token": p.token, "cash": p.cash, "hold": p.hold,
                          "deposited": p.deposited, "season_base": p.season_base,
                          "bot": p.bot, "strategy": p.strategy} for p in self.players.values()]}
        tmp = self.state_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f)
        os.replace(tmp, self.state_file)

    def _load_state(self):
        if not self.state_file or not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, encoding="utf-8") as fh:
                d = json.load(fh)
            schema = int(d.get("schema", 1))
            share_scales = {}
            saved_stocks = d["stocks"]
            self.delisted = list(d.get("delisted", []))
            for ticker in self.delisted:
                self.stocks.pop(ticker, None)
            house = float(d.get("house", d.get("treasury", 0.0)))
            for t, v in saved_stocks.items():
                if t not in self.stocks:
                    house += float(v.get("T", 0.0))  # listing removed from content: liquidity returns
                    continue
                s = self.stocks[t]
                s.T, s.S, s.base = v["T"], v["S"], v["base"]
                history_scale = 1.0
                if schema < 2:
                    old_price = s.price
                    history_scale = s.initial_price / old_price if old_price > 0 else 1.0
                    share_scales[t] = old_price / s.initial_price
                    s.S = s.T / s.initial_price
                elif schema < 5 and s.initial_price > 0:
                    old_price = s.price
                    target_ratio = max(0.5, min(1.5, old_price / s.initial_price))
                    target_price = s.initial_price * target_ratio
                    if old_price > 0 and abs(target_price / old_price - 1) > 1e-9:
                        history_scale = target_price / old_price
                        share_scales[t] = old_price / target_price
                        s.S = s.T / target_price
                s.fair = float(v.get("fair", s.price))
                s.fair_open = float(v.get("fair_open", s.fair))
                s.hist.clear()
                s.hist.append(s.price)
                s.candles.clear()
                s.candles.extend([list(c) for c in v.get("candles", [])])
                s.daily_hist.clear()
                raw_daily = v.get("daily_hist", [])
                if schema < 3:
                    for day, price in raw_daily:
                        scaled = price * history_scale
                        s.daily_hist.append((day, scaled, scaled, scaled, scaled))
                else:
                    # schema < 6 labelled each closed day with the following day's number
                    shift = 1 if schema < 6 else 0
                    for day, o, h, l, c in raw_daily:
                        if s.daily_hist and s.daily_hist[-1][0] >= day - shift:
                            s.daily_hist.pop()
                        s.daily_hist.append((day - shift, o * history_scale, h * history_scale,
                                             l * history_scale, c * history_scale))
                if "day_open" in v:
                    s.day_open = v["day_open"] * history_scale
                    s.day_high = v["day_high"] * history_scale
                    s.day_low = v["day_low"] * history_scale
                else:
                    s.day_open = s.day_high = s.day_low = s.price
                s.rating = v.get("rating", s.rating)
                s.next_earn = v.get("next_earn", s.next_earn)
                s.next_rating_review = v.get("next_rating_review", s.next_rating_review)
                s.distress_checked = v.get("distress_checked", False)
                # events that fell due while the server was down are rescheduled instead of all firing at once
                if s.next_earn and s.next_earn < self.now:
                    s.next_earn = self.now + random.uniform(*self.settings.get("earnings_initial_seconds", [1800, 5400]))
                if s.next_rating_review and s.next_rating_review < self.now:
                    s.next_rating_review = self.now + random.uniform(*self._review_days()) * MARKET_DAY_SECONDS
                self._record(s)
            self.minted = float(d["minted"])
            self.fees = float(d.get("fees", 0.0))
            # listings added to content since the save are funded from the house reserve
            new_reserves = sum(s.T for t, s in self.stocks.items() if t not in saved_stocks)
            take = min(max(house, 0.0), new_reserves)
            self.house = house - take
            self.minted += new_reserves - take
            self.players.clear()
            self.by_token.clear()
            for x in d["players"]:
                p = Player(x["name"], x["bot"], x["strategy"])
                p.token, p.cash = x["token"], x["cash"]
                p.hold = {ticker: shares * share_scales.get(ticker, 1.0)
                          for ticker, shares in x["hold"].items()}
                p.deposited = float(x.get("deposited", START_CASH))
                p.season_base = float(x.get("season_base", self.equity(p)))
                self.players[p.token] = p
                self.by_token[p.token] = p
            human_in = sum(p.deposited for p in self.players.values() if not p.bot)
            self.house_capital = float(d.get("house_capital", self.minted - human_in)) + new_reserves - take
            self.index_level = float(d.get("index_level", 100.0))
            self.index_hist.clear()
            self.index_hist.extend(d.get("index_hist", [self.index_level]))
            self.market_day = int(d.get("market_day", self.market_day))
            self.regime = d.get("regime", self.regime)
            self.next_regime_change = float(d.get("next_regime_change", self.next_regime_change))
            self.season_no, self.season_end, self.history = d["season_no"], d["season_end"], d["history"]
            drift = self.total_tokens() - self.minted
            if abs(drift) > 1e-6:
                logger.warning("token invariant off by %.6f after loading state", drift)
                if schema < 6:
                    # pre-v6 saves could leak tokens through the old treasury; book the gap as house capital
                    self.minted += drift
                    self.house_capital += drift
        except Exception:
            logger.exception("state load failed, starting fresh")
