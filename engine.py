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
# real-time candle sizes in seconds, keyed by the labels the chart offers
TIMEFRAMES = {"30s": 30, "1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "2h": 7200,
              "4h": 14400, "1d": 86400, "1mo": 30 * 86400, "1y": 365 * 86400}
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


RATINGS = ["D", "C", "CC", "CCC", "B", "BB", "BBB", "A", "AA", "AAA"]
BANKS = [("Halvorsen & Co", 0.02), ("Meridian Securities", -0.03), ("Quill Capital", 0.0),
         ("Bellwether Partners", 0.03), ("Northgate Research", -0.02), ("Sable Harbour Bank", 0.01)]
# Company-specific stories. Each is announced in the news first; the effect on the financials only
# lands at the next earnings report, which then cites it. (sign, headline, margin, revenue, debt)
ISSUES = [
    (-1, "{name}'s CEO faces board pressure over strategy and missed targets", -0.22, -0.01, 0.0, "management turmoil"),
    (-1, "{name} warns of supply-chain disruption at a key supplier", -0.18, -0.04, 0.0, "a supply-chain disruption"),
    (-1, "{name} faces a regulatory probe and a product recall", -0.15, -0.03, 0.06, "a recall and regulatory probe"),
    (-1, "{name} loses a major customer to a rival", -0.08, -0.09, 0.0, "the loss of a major customer"),
    (-1, "{name} takes on new debt to fund an aggressive expansion", -0.04, 0.0, 0.18, "higher debt from its expansion"),
    (-1, "{name} reports a data breach, customers review contracts", -0.10, -0.05, 0.0, "a data breach"),
    (1, "{name} wins a major multi-year contract", 0.10, 0.08, 0.0, "a major contract win"),
    (1, "{name} appoints a respected new CEO and unveils a turnaround plan", 0.18, 0.01, 0.0, "new management"),
    (1, "{name}'s latest product sees strong early demand", 0.08, 0.06, 0.0, "strong product demand"),
    (1, "{name} launches a cost-cutting programme and lifts its outlook", 0.20, 0.0, 0.0, "cost savings"),
    (1, "{name} pays down debt ahead of schedule", 0.03, 0.0, -0.18, "lower debt"),
]


# Narrative: the market has a mood (regime plus an optional crisis overlay), sectors and companies have
# their own moods, and headlines lean the same way. Every headline is also dressed with a lead-in and a
# tail so no two read alike; `Engine._unique` guarantees it.
REGIME_MOOD = {"Recession": -0.6, "Expansion": 0.15, "Boom": 0.55, "Bubble": 0.75}
LEADS = ["Developing: ", "Desk note: ", "Wire flash: ", "Market watch: ", "Analyst brief: ", "Overnight: ",
         "Pre-bell: ", "Flash: ", "Midday: ", "Street talk: "]
TAILS = [" - traders react", " (heavy volume)", ", desks report", ", per industry sources",
         ", say people familiar", " - details to follow", " as volumes spike", " ahead of the close",
         "; watch the follow-through", " - screens flash red and green", ", according to a note to clients",
         " in thin trading", " as the open nears", " - the tape is busy"]
TAILS_GOOD = [" as optimism builds", " as the rally broadens", " as dip-buyers step in",
              " as risk appetite returns", " amid upbeat sentiment", " as buyers pile in"]
TAILS_BAD = [" as nerves fray", " as selling pressure builds", " amid fresh worries",
             " as risk appetite fades", " as the gloom deepens", " as traders head for the exits"]
# Follow-ups refer back to an earlier headline ({ref}). "Continue" keeps the original direction, "reverse"
# is a switch-up. Keyed by (kind, tone of the *original* news).
FOLLOWUPS = {
    ("continue", -1): ['The damage deepens: new details emerge after "{ref}"',
                       'Analysts warn the fallout from "{ref}" may last longer than expected',
                       '"{ref}" - officials now admit the problem is wider than first reported',
                       'More pain after "{ref}" as second-round effects spread',
                       'Fresh worries: "{ref}" turns out to be only the start'],
    ("continue", 1): ['Momentum builds after "{ref}" as new details impress',
                      'Analysts lift estimates following "{ref}"',
                      '"{ref}" - follow-up reports suggest the gains could be larger than first thought',
                      'The good news keeps coming after "{ref}"',
                      'Upside surprise: "{ref}" looks even better on closer inspection'],
    ("reverse", -1): ['Relief: new details soften the blow from "{ref}"',
                      'Rebound: "{ref}" looks overdone, analysts say',
                      '"{ref}" - officials now say the fallout is more contained than feared',
                      'Silver lining emerges after "{ref}"',
                      'U-turn: the worst of "{ref}" may already be behind us'],
    ("reverse", 1): ['Reality check: new details cast doubt on "{ref}"',
                     'Not so fast: "{ref}" runs into complications',
                     '"{ref}" - follow-up reports reveal a catch',
                     'Cold water thrown on "{ref}" as new details emerge',
                     'Switch-up: "{ref}" unravels under scrutiny'],
}
# Regime shifts are announced by tone only. The regime itself, and the market's mood, are never named.
REGIME_NEWS = {
    1: ["Risk appetite surges as investors turn bolder", "A wave of buying sweeps trading floors",
        "Confidence returns across the market", "Investors pile back in as caution fades"],
    -1: ["Selling sweeps the market as confidence cracks", "Investors rush to cut risk across the board",
         "Sentiment sours as traders step back", "Caution spreads as buyers vanish"],
}


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


class Stock:
    def __init__(self, cfg, tokens):
        self.ticker = cfg["ticker"]
        self.update(cfg)
        self.T = float(tokens)    # liquidity the house seeded for this listing; trades never touch it
        self.base = float(tokens)
        self.fair = self.fair_open = self.initial_price  # the market price: trades never move it
        self.hist = deque(maxlen=MARKET_DAY_SECONDS + 1)
        self.candles = deque(maxlen=2 * MARKET_DAY_SECONDS // INTRADAY_CANDLE_SECONDS)
        self.daily_hist = deque(maxlen=366)
        self.tf = {k: deque(maxlen=500) for k in TIMEFRAMES}
        self.day_open = self.day_high = self.day_low = self.price
        self.next_earn = None
        self.next_rating_review = None
        self.distress_checked = False
        self.safety = random.uniform(0.3, 0.85)   # hidden: banks "know" it, players must infer it
        self.pending = []                          # announced issues not yet reflected in financials
        self.log = deque(maxlen=60)                # news that named this stock, for players to look back on
        self.reports = deque(maxlen=12)            # past earnings reports
        self.trend = 0.0
        self.mood = 0.0                            # narrative momentum for this company

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
        self.dependencies = dict(cfg.get("dependencies", {}))
        self.traits = list(cfg.get("traits", []))
        self.desc = cfg.get("desc", "")
        self.haven = float(cfg.get("haven", 0.0))
        if not hasattr(self, "revenue"):  # financials evolve with earnings, so content reloads must not reset them
            self.margin = float(cfg.get("margin", 0.12))
            self.base_margin = self.margin
            self.revenue = float(cfg.get("revenue", 0.0))
            self.cash = float(cfg.get("cash", 0.0))
            self.debt = float(cfg.get("debt", 0.0))

    @property
    def price(self):
        return self.fair

    def quote_buy(self, cash):
        fee = cash * FEE
        return (cash - fee) / self.fair, fee

    def quote_sell(self, shares):
        gross = shares * self.fair
        fee = gross * FEE
        return gross - fee, fee

    def move(self, r):
        """Exogenous price move. Player trades never call this."""
        self.fair *= 1 + r


class Player:
    def __init__(self, name, bot=False, strategy=None):
        self.name = name
        self.token = uuid.uuid4().hex
        self.cash = 0.0
        self.deposited = 0.0     # net tokens credited to this account (signup, deposits - withdrawals)
        self.season_base = 0.0   # equity at season start plus deposits during the season
        self.hold = {}           # shares; negative means a short position
        self.notices = []        # one-off messages for the client (margin calls)
        self.cost = {}           # total entry cost of the open position per ticker (for average price)
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
        self.used_news = deque(maxlen=6000)        # every headline ever printed, so none repeats
        self.used_set = set()
        self.mood = 0.15                           # market narrative: -1 gloom .. +1 euphoria
        self.sector_mood = {}
        self.crisis_until = 0.0
        self._mood_t = self.now
        self.threads = []                          # remembered stories that may get follow-ups or switch-ups
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
        self.next_issue = self.now + random.expovariate(1 / float(self.settings.get('issue_mean_seconds', 100)))
        self._add_index_asset()
        self._load_state()
        self._sync_index_asset()
        self.index_prev = {tk: s.price for tk, s in self.stocks.items()}
        self.index_hist.clear()
        self.index_hist.append(self.index_level)
        if bots and not self.by_token_bots():
            self._add_bots(int(self.settings.get("bots", 8)))

    def _add_index_asset(self):
        cfg = {"ticker": "MSI", "name": "Meme Street Index", "sector": "index", "asset_type": "index",
               "beta": 1.0, "vol": 0.2, "initial_price": 100.0,
               "desc": "Tracks the weighted basket of every stock on Meme Street, so you can trade the whole market in one position."}
        self.stocks["MSI"] = Stock(cfg, 0.0)

    def _sync_index_asset(self):
        s = self.stocks.get("MSI")
        if s:
            s.fair = self.index_level

    def by_token_bots(self):
        return [p for p in self.players.values() if p.bot]

    # ---------- content ----------
    def _content_files(self):
        state_path = os.path.abspath(self.state_file or "state.json")
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
        reports = s.asset_type == "equity" and s.revenue > 0
        s.next_earn = self.now + random.uniform(*first_earn) if reports else None
        s.next_rating_review = self._next_review() if s.asset_type == "equity" else None
        if s.asset_type == "equity":
            s.rating = self._rating_for(s)
        s.hist.append(s.price)
        s.day_open = s.day_high = s.day_low = s.price
        self.stocks[s.ticker] = s
        self._record(s)
        if not initial:
            sec = self.sectors[s.sector]["name"]
            self.news("ipo", f"NEW LISTING: {s.name} ({s.ticker}) debuts in {sec}. {s.desc}", [s.ticker])

    def _next_review(self):
        return self.now + random.uniform(*self.settings.get("rating_review_seconds", [600, 1500]))

    # ---------- news ----------
    def _unique(self, text):
        """No two headlines are ever identical: vary the tail, and as a last resort add a timestamp."""
        key = text.lower()
        for _ in range(40):
            if key not in self.used_set:
                break
            text = text.rstrip(".") + random.choice(TAILS)
            key = text.lower()
        else:
            n = 0
            base = text
            while key in self.used_set:
                n += 1
                text = f"{base} [{time.strftime('%H:%M:%S', time.localtime(self.now))}#{n}]"
                key = text.lower()
        if len(self.used_news) == self.used_news.maxlen:
            self.used_set.discard(self.used_news[0].lower())
        self.used_news.append(text)
        self.used_set.add(key)
        return text

    def _eff_mood(self, scope, sector=None, stock=None):
        sm = self.sector_mood.get(sector, 0.0) if sector else 0.0
        if scope == "company" and stock is not None:
            return 0.5 * stock.mood + 0.3 * self.sector_mood.get(stock.sector, 0.0) + 0.2 * self.mood
        if scope == "sector":
            return 0.6 * sm + 0.4 * self.mood
        return self.mood

    def _p_good(self, eff):
        return _clamp(0.5 + 0.3 * eff, 0.15, 0.85)

    def _dress(self, text, tone):
        """Lead-in and tail for variety. Tone-only: nothing here reveals the hidden mood."""
        lead = random.choice(LEADS) if random.random() < 0.45 else ""
        r = random.random()
        tail = ""
        if r < 0.45:
            tail = random.choice(TAILS_GOOD if tone > 0 else TAILS_BAD)
        elif r < 0.75:
            tail = random.choice(TAILS)
        return lead + text + tail

    def _nudge(self, scope, tone, strength, sector=None, stock=None):
        w = {"bystander": 0.02, "weak": 0.05, "strong": 0.10, "very strong": 0.20}.get(strength, 0.05)
        if scope == "market":
            self.mood = _clamp(self.mood + tone * w, -1, 1)
        elif scope == "sector" and sector:
            self.sector_mood[sector] = _clamp(self.sector_mood.get(sector, 0.0) + tone * w * 2, -1, 1)
        elif scope == "company" and stock is not None:
            stock.mood = _clamp(stock.mood + tone * w * 3, -1, 1)
            self.sector_mood[stock.sector] = _clamp(self.sector_mood.get(stock.sector, 0.0) + tone * w * 0.5, -1, 1)

    def _mood_step(self):
        """Hidden narrative state. It only tilts which kind of headline is likelier; players never see it."""
        dt = max(0.0, min(60.0, self.now - self._mood_t))
        self._mood_t = self.now
        crisis = self.now < self.crisis_until
        target = -0.9 if crisis else REGIME_MOOD.get(self.regime, 0.1)
        self.mood += (target - self.mood) * (1 - math.exp(-dt / 150))
        for k in list(self.sector_mood):
            self.sector_mood[k] *= math.exp(-dt / 400)
        for st in self.stocks.values():
            st.mood *= math.exp(-dt / 600)

    def news(self, kind, text, tickers=(), dirn=0, strength="bystander"):
        text = self._unique(text)
        self.news_log.append({"id": len(self.news_log) and self.news_log[-1]["id"] + 1 or 1,
                              "t": self.now, "kind": kind, "text": text,
                              "tickers": list(tickers)[:4], "dir": dirn})
        for tk in list(tickers)[:4]:
            if tk in self.stocks:
                self.stocks[tk].log.append({"t": self.now, "kind": kind, "text": text})

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
        """Tokens leave the game (withdrawal). Only free cash (not locked as short collateral) can leave."""
        amount = float(amount)
        if amount <= 0:
            return False, "Amount must be positive"
        if amount > self.free_cash(p) + 1e-9:
            return False, "Not enough free cash; close positions first"
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

    def short_liability(self, p):
        """What it would cost, before fees, to buy back every short."""
        total = 0.0
        for tk, sh in p.hold.items():
            s = self.stocks.get(tk)
            if s and sh < 0:
                total += -sh * s.price
        return total

    def free_cash(self, p):
        """Cash not locked as collateral for shorts: the sale proceeds of a short stay locked."""
        return max(0.0, p.cash - self.short_liability(p))

    def equity(self, p):
        v = p.cash
        for tk, sh in p.hold.items():
            s = self.stocks.get(tk)
            if not s:
                continue
            v += s.quote_sell(sh)[0] if sh > 0 else -(-sh) * s.price * (1 + FEE)
        return v

    # ---------- trading ----------
    def _do_buy(self, p, s, cash):
        """Trades execute at the market price against the house, so they never move the price."""
        shares, fee = s.quote_buy(cash)
        self.house += cash - fee
        self.fees += fee
        p.cash -= cash
        p.hold[s.ticker] = p.hold.get(s.ticker, 0.0) + shares
        p.cost[s.ticker] = p.cost.get(s.ticker, 0.0) + shares * s.price
        return shares

    def _do_sell(self, p, s, shares):
        proceeds, fee = s.quote_sell(shares)
        self.house -= proceeds + fee
        self.fees += fee
        p.cash += proceeds
        held = p.hold.get(s.ticker, 0.0)
        left = held - shares
        if left < 1e-9:
            p.hold.pop(s.ticker, None)
            p.cost.pop(s.ticker, None)
        else:
            p.hold[s.ticker] = left
            p.cost[s.ticker] = p.cost.get(s.ticker, 0.0) * left / held  # average entry price is unchanged
        return proceeds

    def _do_short(self, p, s, shares):
        """Sell shares you don't own. The proceeds are paid out but stay locked as collateral."""
        proceeds, fee = s.quote_sell(shares)
        self.house -= proceeds + fee
        self.fees += fee
        p.cash += proceeds
        p.hold[s.ticker] = p.hold.get(s.ticker, 0.0) - shares
        p.cost[s.ticker] = p.cost.get(s.ticker, 0.0) + shares * s.price
        return proceeds

    def _do_cover(self, p, s, shares, pay_all=False):
        """Buy back shorted shares. If cash can't cover it (margin call), the player pays what they have."""
        held = p.hold.get(s.ticker, 0.0)
        shares = min(shares, -held)
        value = shares * s.price
        cost = value * (1 + FEE)
        if cost > p.cash:
            if not pay_all:
                return None
            cost = p.cash
            value = cost / (1 + FEE)
        fee = cost - value
        p.cash -= cost
        self.house += value
        self.fees += fee
        left = held + shares
        if left > -1e-9:
            p.hold.pop(s.ticker, None)
            p.cost.pop(s.ticker, None)
        else:
            p.hold[s.ticker] = left
            p.cost[s.ticker] = p.cost.get(s.ticker, 0.0) * left / held
        return cost

    def avg_price(self, p, ticker):
        sh = abs(p.hold.get(ticker, 0.0))
        return p.cost.get(ticker, 0.0) / sh if sh > 0 else 0.0

    def trade(self, p, ticker, side, pct, amount=None):
        """pct is a fraction (of free cash / position / spare margin); amount, when given, is MB and wins."""
        s = self.stocks.get(ticker)
        if not s:
            return False, "Unknown ticker"
        if amount is not None:
            if not (isinstance(amount, (int, float)) and math.isfinite(amount) and 0 < amount < 1e12):
                return False, "Bad amount"
        elif not (0 < pct <= 1):
            return False, "Bad size"
        if self.now - p.last_trade.get(ticker, 0) < COOLDOWN:
            return False, "Cooldown: 1s between trades in the same stock"
        held = p.hold.get(ticker, 0.0)
        price = s.price
        if side == "buy":
            if held < -1e-9:  # buying while short covers the short
                if amount is not None:
                    shares = amount / (price * (1 + FEE))
                else:
                    shares = -held if pct >= 1 else -held * pct
                shares = min(shares, -held, p.cash / (price * (1 + FEE)))
                if shares * price < 1 and shares < -held - 1e-9:
                    return False, "Not enough cash to cover (min 1)"
                cost = self._do_cover(p, s, shares)
                if cost is None:
                    return False, "Not enough cash to cover"
                msg = f"Covered {shares:.2f} {ticker} short for {cost:.2f} MB"
            else:
                free = self.free_cash(p)
                cash = amount if amount is not None else free * pct
                if cash > free + 1e-9:
                    return False, f"Not enough free cash ({free:.2f} MB available)"
                if cash < 1:
                    return False, "Not enough cash (min 1)"
                sh = self._do_buy(p, s, cash)
                msg = f"Bought {sh:.2f} {ticker} for {cash:.2f} MB"
        elif side == "sell":
            if held > 1e-9:
                if amount is not None:
                    sh = min(held, amount / (price * (1 - FEE)))
                else:
                    sh = held * pct if pct < 1 else held
                got = self._do_sell(p, s, sh)
                msg = f"Sold {sh:.2f} {ticker} for {got:.2f} MB"
            else:  # nothing to sell: open or add to a short
                spare = max(0.0, self.equity(p) - self.short_liability(p))
                notional = amount if amount is not None else spare * pct
                if notional > spare + 1e-9:
                    return False, f"Not enough margin to short ({spare:.2f} MB available)"
                if notional < 1:
                    return False, "Not enough margin to short (min 1)"
                sh = notional / price
                self._do_short(p, s, sh)
                msg = f"Shorted {sh:.2f} {ticker} for {notional:.2f} MB"
        else:
            return False, "Bad side"
        p.last_trade[ticker] = self.now
        p.trades += 1
        return True, msg

    def _margin_calls(self):
        """Shorts must stay covered: if equity falls below 25% of what the shorts would cost to close,
        every short is closed at the market price."""
        for p in self.players.values():
            if not any(sh < 0 for sh in p.hold.values()):
                continue
            liab = self.short_liability(p)
            if liab <= 0 or self.equity(p) >= 0.25 * liab:
                continue
            closed = []
            for tk, sh in list(p.hold.items()):
                if sh < 0 and tk in self.stocks:
                    self._do_cover(p, self.stocks[tk], -sh, pay_all=True)
                    closed.append(tk)
            p.notices.append("Margin call: your short in " + ", ".join(closed) + " was closed at the market price.")

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
        for key, secs in TIMEFRAMES.items():
            self._merge(s.tf[key], int(self.now // secs) * secs, price, price, price, price)

    @staticmethod
    def _merge(dq, t, o, h, l, c):
        last = dq[-1] if dq else None
        if last and last[0] == t:
            last[2], last[3], last[4] = max(last[2], h), min(last[3], l), c
        else:
            dq.append([t, o, h, l, c])

    # ---------- market dynamics ----------
    # Exogenous moves are queued into self._pending during a tick and applied together in
    # _flush_moves, so knock-on effects land in the same tick as their cause and cannot be
    # front-run from the previous state.
    def _queue(self, returns):
        for tk, r in returns.items():
            if tk in self.stocks and r and self.stocks[tk].asset_type != "index":
                self._pending[tk] = (1 + self._pending.get(tk, 0.0)) * (1 + r) - 1

    def _vol_scale(self):
        return float(self.settings.get("volatility_scale", 1.0))

    def _daily_sigma(self, s):
        return s.vol * self._vol_scale() / math.sqrt(TRADING_DAYS_PER_YEAR)

    def _random_market_moves(self):
        annual_scale = math.sqrt(TRADING_DAYS_PER_YEAR * MARKET_DAY_SECONDS) / self._vol_scale()
        market_shock = random.gauss(0.0, 1.0)
        sector_shocks = {sector: random.gauss(0.0, 1.0) for sector in self.sectors}
        returns = {}
        for stock in self.stocks.values():
            if stock.asset_type == "index":
                continue
            market_sigma = stock.beta * 0.18
            sector_sigma = 0.08
            idio_sigma = math.sqrt(max(stock.vol ** 2 - market_sigma ** 2 - sector_sigma ** 2, 0.005 ** 2))
            shock = (market_sigma * market_shock + sector_sigma * sector_shocks.get(stock.sector, 0.0)
                     + idio_sigma * random.gauss(0.0, 1.0)) / annual_scale
            if stock.asset_type == "commodity":
                # supply/demand cycles: commodities trend for a while instead of being pure noise
                stock.trend = stock.trend * 0.998 + random.gauss(0.0, 0.0015 * stock.vol / annual_scale)
                shock += stock.trend
            returns[stock.ticker] = max(-0.01, min(0.01, shock))
        self._queue(returns)

    def _mean_revert(self):
        # Pulls the exogenous fair value back toward the reference price. Player price impact is
        # not reverted, so buying and later selling costs only fees and slippage.
        halflife_days = float(self.settings.get("mean_reversion_halflife_days", 90.0))
        if halflife_days <= 0:
            return
        rate = 1 - 0.5 ** (1.0 / (halflife_days * MARKET_DAY_SECONDS))
        # geometric pull, symmetric in log price: 0.8x and 1.25x the reference are pulled equally hard
        self._queue({tk: (s.initial_price / s.fair) ** rate - 1
                     for tk, s in self.stocks.items() if s.fair > 0})

    def _event_returns(self, betas, index_move, impact, strength):
        """Full move per ticker for a positive event; a negative event is the mirror image."""
        strength_limits = self.settings.get("event_strength_limits", {
            "bystander": 0.1, "weak": 0.35, "strong": 0.65, "very strong": 1.0})
        out = {}
        for tk, s in self.stocks.items():
            if s.asset_type == "index" or s.base <= 0:
                continue
            crowd = min(2.0, max(0.5, s.T / s.base))
            vol_scale = min(1.8, max(0.5, math.sqrt(s.vol / 0.30)))
            market_return = s.beta * index_move * vol_scale
            catalyst_return = impact * betas.get(tk, 0.0) * s.sens * crowd * vol_scale
            daily_limit = (self._daily_sigma(s) * strength_limits.get(strength, 0.35)
                           * max(0.5, min(2.0, abs(s.beta))))
            r = max(-daily_limit, min(daily_limit, market_return + catalyst_return))
            if r:
                out[tk] = r
        return out

    @staticmethod
    def _good_dir(tpl):
        """Which direction (+1 'up' text, -1 'down' text) is good news for the affected stocks."""
        if tpl.get("good") == "down" or float(tpl.get("index_bias", 0) or 0) < 0:
            return -1
        return 1

    def _spawn_event(self, tpl=None, target=None, direction=None, strength=None, scale=1.0,
                     prefix="BREAKING: ", follow=True, issue=None):
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
                c = [s for s in self.stocks.values()
                     if tpl.get("sector") in (None, s.sector) and s.asset_type != "index"]
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
            if s.asset_type == "index":
                continue
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
        good_dir = self._good_dir(tpl)
        tgt_stock = self.stocks.get(target) if scope == "company" else None
        eff = self._eff_mood(scope, tgt_sector, tgt_stock)
        if direction in (-1, 1):
            sign = direction
        else:
            # Headlines lean with the narrative. The likelier direction moves prices proportionally less
            # and the unlikelier one more, so the expected move of the news stays zero: it can't be farmed.
            p_good = self._p_good(eff)
            sign = good_dir if random.random() < p_good else -good_dir
            p_sign = p_good if sign == good_dir else 1 - p_good
            scale = 2 * (1 - p_sign)
        strength_weights = self.settings.get("news_strength_weights", {
            "bystander": 0.25, "weak": 0.4, "strong": 0.25, "very strong": 0.1})
        strength = strength or tpl.get("strength") or random.choices(
            list(strength_weights), weights=list(strength_weights.values()))[0]
        ranges = self.settings.get("news_move_ranges", {})
        impact = random.uniform(*ranges.get(strength, [0.0, 0.005]))
        index_move = float(tpl.get("index_bias", 1.0)) * impact if scope == "market" else 0.0
        up_moves = {tk: r * scale for tk, r in self._event_returns(betas, index_move, impact, strength).items()}
        final = {tk: sign * r for tk, r in up_moves.items()}
        def raw_for(sgn):
            return random.choice(tpl["up"] if sgn > 0 else tpl["down"]).format(name=label, sector=label)

        def fmt(sgn, raw):
            return self._dress(raw, 1 if sgn == good_dir else -1)
        core = raw_for(sign)
        text = fmt(sign, core)
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
            self.news("rumor", "RUMOR: " + (text if shown == sign else fmt(shown, raw_for(shown))), top, shown, strength)
            self._queue(pre)
        else:
            self.news("breaking", prefix + text, top, sign, strength)
            self._queue(final)
        self.hints.append({"id": uuid.uuid4().hex, "t": self.now, "dir": shown, "betas": betas})
        tone = 1 if sign == good_dir else -1
        self._nudge(scope, tone, strength, tgt_sector, tgt_stock)
        if scope == "market" and tone < 0 and strength == "very strong" and self.now >= self.crisis_until:
            # a crisis is never announced; it just makes bad headlines likelier for a while
            self.crisis_until = self.now + random.uniform(480, 900)
        if follow:
            self._remember(tpl, scope, target, tgt_sector, label, core, sign, strength, issue)

    # ---------- story memory: follow-ups and switch-ups ----------
    def _remember(self, tpl, scope, target, sector, label, core, sign, strength, issue, stage=0):
        q = {"market": 0.35, "sector": 0.3, "company": 0.35}.get(scope, 0.3)
        if issue is not None:
            q = 0.55
        if random.random() >= q:
            return
        keep = {k: tpl[k] for k in ("scope", "betas", "index_bias", "good") if k in tpl}
        keep["sector"] = sector
        keep["ticker"] = target if scope == "company" else None
        self.threads.append({"t": self.now + random.uniform(120, 480), "tpl": keep, "target": target,
                             "label": label, "ref": core, "sign": sign, "strength": strength,
                             "stage": stage, "issue": issue})
        self.threads = self.threads[-40:]

    def _followups(self):
        """A remembered story comes back later: either it continues, or it switches direction.
        The continuation is likelier (60%) but smaller, the reversal rarer (40%) but bigger, so a trader
        who reads the first headline has no expected profit from guessing which one comes next."""
        for th in list(self.threads):
            if self.now < th["t"]:
                continue
            self.threads.remove(th)
            tpl = th["tpl"]
            target = th["target"]
            if tpl.get("scope") == "company" and target not in self.stocks:
                continue
            cont = random.random() < 0.6
            sign = th["sign"] if cont else -th["sign"]
            scale = 2 * (1 - (0.6 if cont else 0.4))
            good_dir = self._good_dir(tpl)
            orig_tone = 1 if th["sign"] == good_dir else -1
            headline = random.choice(FOLLOWUPS[("continue" if cont else "reverse", orig_tone)]).format(ref=th["ref"])
            tpl2 = {**tpl, "rumor": False, "up": [headline], "down": [headline]}
            strength = th["strength"] if not cont or th["strength"] == "bystander" else (
                "strong" if th["strength"] == "very strong" else "weak" if th["strength"] == "strong" else th["strength"])
            self._spawn_event(tpl2, target, sign, strength, scale, prefix="UPDATE: " if cont else "REVERSAL: ",
                              follow=False)
            issue = th.get("issue")
            stock = self.stocks.get(target)
            if issue and stock is not None:
                k = 0.5 if cont else -0.7  # the follow-up also changes what the next earnings report will show
                why = (f"further developments in {issue['why']}" if cont else f"a reversal after {issue['why']}")
                stock.pending.append({"t": self.now, "text": headline, "why": why, "dm": issue["dm"] * k,
                                      "dr": issue["dr"] * k, "dd": issue["dd"] * k})
            if th["stage"] < 2 and random.random() < 0.3:
                self._remember(tpl2 | {"betas": tpl.get("betas", {})}, tpl.get("scope", "market"), target,
                               tpl.get("sector"), th["label"], th["ref"], sign, strength, issue, th["stage"] + 1)

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

    @staticmethod
    def _money(v):
        return f"{v:.1f}B MB" if abs(v) >= 1 else f"{v * 1000:.0f}M MB"

    def _issues(self):
        """Company stories are announced first; earnings later show their effect on the financials."""
        if self.now < self.next_issue:
            return
        self.next_issue = self.now + random.expovariate(1 / float(self.settings.get("issue_mean_seconds", 100)))
        pool = [s for s in self.stocks.values() if s.asset_type == "equity" and s.revenue > 0]
        if not pool:
            return
        s = random.choice(pool)
        # weaker companies attract bad news a little more often, but anyone can get either
        eff = self._eff_mood("company", s.sector, s)
        p_pos = _clamp(0.5 + 0.25 * (s.safety - 0.5) + 0.25 * eff, 0.15, 0.85)
        sign = 1 if random.random() < p_pos else -1
        scale = 2 * (1 - (p_pos if sign > 0 else 1 - p_pos))
        _, text, dm, dr, dd, why = random.choice([i for i in ISSUES if i[0] == sign])
        k = random.uniform(0.7, 1.3)
        headline = text.format(name=s.name)
        tpl = {"scope": "company", "ticker": s.ticker, "rumor": False, "betas": {"self": 1.0},
               "up": [headline], "down": [headline]}
        strength = random.choices(["weak", "strong"], weights=[0.7, 0.3])[0]
        effect = {"t": self.now, "text": headline, "why": why, "dm": dm * k, "dr": dr * k, "dd": dd * k}
        s.pending.append(effect)
        self._spawn_event(tpl, s.ticker, sign, strength, scale, issue=effect)

    def _earnings(self):
        for s in self.stocks.values():
            if s.next_earn and self.now >= s.next_earn:
                interval = self.settings.get("earnings_interval_seconds", [3600, 10800])
                s.next_earn = self.now + random.uniform(*interval)
                self._report(s)

    def _report(self, s):
        old_rev, old_margin = s.revenue, s.margin
        dm = sum(e["dm"] for e in s.pending)
        dr = sum(e["dr"] for e in s.pending)
        dd = sum(e["dd"] for e in s.pending)
        causes = list(s.pending)
        s.pending = []
        # unannounced noise is small: a big change in the numbers needs a story the news already told
        noise_m, noise_r = random.gauss(0.0, 0.008), random.gauss(0.0, 0.01)
        s.margin += dm * max(abs(s.margin), 0.06)
        s.margin += (s.base_margin - s.margin) * 0.15 + noise_m
        s.revenue *= 1 + 0.01 + dr + noise_r
        s.debt *= 1 + dd
        s.cash += s.revenue * s.margin * 0.12
        if s.cash < 0:
            s.debt += -s.cash
            s.cash = 0.0
        surprise = _clamp(noise_m * 5 + noise_r * 2, -0.06, 0.06)
        rev_chg = s.revenue / old_rev - 1 if old_rev else 0.0
        earnings = s.revenue * s.margin
        eps = earnings / s.shares_outstanding if s.shares_outstanding > 0 else None
        driver = ("Driven by " + "; ".join(c["why"] for c in causes) + ", as flagged in earlier news."
                  if causes else "No major changes were flagged beforehand.")
        text = (f"EARNINGS: {s.name} reports revenue of {self._money(s.revenue)} ({rev_chg * 100:+.1f}%) "
                f"and a net margin of {s.margin * 100:.1f}%. {driver}")
        self.news("earnings", text, [s.ticker], 1 if surprise > 0 else -1 if surprise < 0 else 0, "weak")
        self._queue({s.ticker: surprise})
        s.reports.append({"t": self.now, "revenue": s.revenue, "rev_chg": rev_chg, "margin": s.margin,
                          "margin_chg": s.margin - old_margin, "net_income": earnings, "eps": eps,
                          "beat": surprise >= 0, "causes": [{"t": c["t"], "text": c["text"]} for c in causes]})

    def _bank_score(self, s):
        """What the banks 'know': hidden safety plus volatility, beta and the balance sheet, in 0..1."""
        rev = s.revenue
        if rev > 0:
            fin = _clamp(0.45 + s.margin * 1.4 + _clamp((s.cash - s.debt) / rev, -1, 1) * 0.2
                         - min(s.debt / rev, 2.0) * 0.3, 0, 1)
        else:
            fin = _clamp(0.5 + s.margin, 0, 1)
        volp = 1 - _clamp((s.vol - 0.15) / 0.6, 0, 1)
        betap = 1 - _clamp((s.beta - 0.5) / 1.5, 0, 1)
        return 0.30 * s.safety + 0.25 * volp + 0.15 * betap + 0.30 * fin

    def _rating_for(self, s, bias=0.0):
        return RATINGS[int(_clamp(round(_clamp((self._bank_score(s) + bias - 0.28) / 0.5, 0, 1) * 9), 0, 9))]

    def _review_reason(self, s, down):
        rev = s.revenue or 1e-9
        options = []
        if down:
            if s.margin < s.base_margin * 0.8:
                options.append("thinner margins")
            if s.debt / rev > 0.5:
                options.append("leverage concerns")
            if s.margin < 0:
                options.append("continued cash burn")
            if s.vol > 0.5:
                options.append("elevated volatility")
            return random.choice(options or ["a more cautious outlook", "weaker earnings quality"])
        if s.margin > s.base_margin * 1.1:
            options.append("improving margins")
        if s.cash > s.debt:
            options.append("a stronger balance sheet")
        if s.vol < 0.3:
            options.append("a defensive profile")
        return random.choice(options or ["a better outlook", "steady execution"])

    def _credit_reviews(self):
        """Banks review stocks they cover. A rating change is published as a price-target move."""
        for stock in list(self.stocks.values()):
            if not stock.next_rating_review or self.now < stock.next_rating_review:
                continue
            stock.next_rating_review = self._next_review()
            bank, bias = random.choice(BANKS)
            stock.safety = _clamp(stock.safety + random.gauss(0.0, 0.02), 0.05, 0.98)
            index = RATINGS.index(stock.rating) if stock.rating in RATINGS else RATINGS.index("BBB")
            target = RATINGS.index(self._rating_for(stock, bias))
            direction = (target > index) - (target < index)
            if direction and random.random() < 0.7:
                stock.rating = RATINGS[index + direction]
            else:
                direction = 0
            pt = stock.price * (1 + 0.04 * (target - index) + random.gauss(0.0, 0.02))
            if direction == 0:
                if random.random() < 0.4:
                    self.news("rating", f"{bank} reiterates its view on {stock.name}, price target {pt:.2f} MB.",
                              [stock.ticker], 0, "bystander")
                continue
            word = "raises" if direction > 0 else "lowers"
            why = self._review_reason(stock, direction < 0)
            headline = f"{bank} {word} price target on {stock.name} to {pt:.2f} MB, citing {why}"
            tpl = {"scope": "company", "ticker": stock.ticker, "up": [headline], "down": [headline],
                   "betas": {"self": 1.0}, "rumor": False}
            self._spawn_event(tpl, stock.ticker, direction, "weak", follow=False)

    def _advance_regime(self):
        if self.now < self.next_regime_change:
            return
        previous = self.regime
        if previous == "Bubble":
            self.regime = "Recession"
        else:
            self.regime = random.choices(
                ["Expansion", "Boom", "Bubble", "Recession"], weights=[0.44, 0.22, 0.12, 0.22])[0]
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
        self.news("macro", random.choice(REGIME_NEWS[1 if direction > 0 else -1]), (), direction, strength)

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
        cap = float(self.settings.get("daily_move_cap", 0.15))
        for tk, r in pending.items():
            s = self.stocks[tk]
            # daily move envelope on the exogenous fair value (player trades are not clamped)
            target = s.fair * (1 + max(-MAX_TICK_MOVE, min(MAX_TICK_MOVE, r)))
            if cap > 0:
                limit = min(cap, self._daily_sigma(s) * (1.5 + 0.75 * min(abs(s.beta), 2.0)))
                target = max(s.fair_open * (1 - limit), min(s.fair_open * (1 + limit), target))
            s.move(target / s.fair - 1)

    def _check_distress(self):
        threshold = float(self.settings.get("distress_price_ratio", 0.25))
        bailout_chance = float(self.settings.get("bailout_chance", 0.25))
        for ticker, stock in list(self.stocks.items()):
            if stock.asset_type == "index":
                continue
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
            # Bankruptcy: the price is cut by the haircut, holders are cashed out at that price
            # (no fee) and the remaining pool liquidity returns to the house reserve. Without the
            # haircut, buying a distressed stock would be a free bet on the bailout.
            stock.move(-float(self.settings.get("bankruptcy_haircut", 0.5)))
            for player in self.players.values():
                sh = player.hold.pop(ticker, 0.0)
                player.cost.pop(ticker, None)
                if sh > 0:
                    payout = sh * stock.price
                    player.cash += payout
                    self.house -= payout
                elif sh < 0:  # a short closes at the haircut price
                    owed = min(player.cash, -sh * stock.price)
                    player.cash -= owed
                    self.house += owed
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
        self._mood_step()
        self._events()
        self._followups()
        self._issues()
        self._earnings()
        self._flush_moves()
        self._check_distress()
        self._margin_calls()
        self._bots()
        self._update_index()
        for s in self.stocks.values():
            if s.asset_type != "index":
                s.hist.append(s.price)
                self._record(s)
        self._update_index_level()
        index_asset = self.stocks.get("MSI")
        if index_asset:
            self._sync_index_asset()
            index_asset.hist.append(index_asset.price)
            self._record(index_asset)
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
        total_weight = sum(s.base for s in self.stocks.values() if s.asset_type != "index")
        if total_weight:
            weighted_return = sum(
                s.base * (s.price / self.index_prev.get(tk, s.price) - 1)
                for tk, s in self.stocks.items() if s.asset_type != "index"
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
                        "traits": s.traits,
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
            if s.asset_type == "index":
                out[-1]["financials"] = {}
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
        key = period if period in TIMEFRAMES else "30s"  # legacy clients may still ask for day/week/...
        candles = [{"t": t, "o": o, "h": h, "l": l, "c": c} for t, o, h, l, c in stock.tf[key]]
        for candle in candles:
            for k in "ohlc":
                candle[k] = round(candle[k], 5)
        return {"type": "history", "ticker": ticker, "period": period, "candles": candles,
                "now": self.now}

    def company_for(self, ticker):
        stock = self.stocks.get(ticker)
        if not stock:
            return {"type": "company", "error": "Unknown or delisted stock"}
        return {"type": "company", "ticker": ticker, "log": list(stock.log)[::-1],
                "reports": [{**r, "causes": list(r["causes"])} for r in list(stock.reports)[::-1]]}

    def _upcoming_events(self):
        events = []
        for stock in self.stocks.values():
            if stock.next_earn:
                events.append({"ticker": stock.ticker, "name": stock.name, "kind": "Earnings",
                               "at": stock.next_earn, "in_seconds": max(0, int(stock.next_earn - self.now))})
        return sorted(events, key=lambda event: event["at"])[:20]

    def state_for(self, p):
        e = self.equity(p)
        px = {s["ticker"]: s["price"] for s in self.pub_stocks}
        hold = []
        for tk, sh in p.hold.items():
            price = px.get(tk, 0)
            cost = p.cost.get(tk, 0.0)
            n = abs(sh)
            value = n * price
            pnl = value - cost if sh > 0 else cost - value
            hold.append({"ticker": tk, "side": "long" if sh > 0 else "short", "shares": round(n, 6),
                         "avg": round(cost / n, 6) if n > 0 else 0, "price": price, "cost": round(cost, 2),
                         "value": round(value, 2), "pnl": round(pnl, 2),
                         "pct": round(pnl / cost, 4) if cost > 0 else 0})
        notices, p.notices = p.notices, []
        return {"type": "state", "season": self.season_no,
                "season_left": max(0, int(self.season_end - self.now)),
                "index": self.pub_index,
                "upcoming": self._upcoming_events(),
                "cash": round(p.cash, 2), "equity": round(e, 2), "ret": round(self.season_return(p, e), 4),
                "pnl": round(e - p.deposited, 2),
                "holdings": hold, "notices": notices,
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
        d = {"schema": 7, "house": self.house, "fees": self.fees, "house_capital": self.house_capital,
             "minted": self.minted, "index_level": self.index_level,
             "index_hist": list(self.index_hist), "market_day": self.market_day,
             "regime": self.regime, "next_regime_change": self.next_regime_change,
             "mood": self.mood, "crisis_until": self.crisis_until, "sector_mood": self.sector_mood,
             "used_news": list(self.used_news), "threads": self.threads,
             "delisted": self.delisted, "season_no": self.season_no,
             "season_end": self.season_end, "history": self.history,
             "stocks": {t: {"T": s.T, "base": s.base, "fair": s.fair, "fair_open": s.fair_open,
                            "daily_hist": list(s.daily_hist), "candles": list(s.candles),
                            "safety": s.safety, "pending": s.pending, "log": list(s.log),
                            "reports": list(s.reports), "trend": s.trend, "mood": s.mood, "base_margin": s.base_margin,
                            "revenue": s.revenue, "margin": s.margin, "cash": s.cash, "debt": s.debt,
                            "tf": {k: list(v) for k, v in s.tf.items()}, "rating": s.rating,
                            "day_open": s.day_open, "day_high": s.day_high, "day_low": s.day_low,
                            "next_earn": s.next_earn,
                            "next_rating_review": s.next_rating_review,
                            "distress_checked": s.distress_checked}
                        for t, s in self.stocks.items()},
             "players": [{"name": p.name, "token": p.token, "cash": p.cash, "hold": p.hold,
                          "deposited": p.deposited, "season_base": p.season_base, "cost": p.cost,
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
                s.T, s.base = v["T"], v["base"]
                history_scale = 1.0
                if schema < 7 and v.get("S"):
                    s.fair = v["T"] / v["S"]  # before v7 the pool price was the market price
                    if "fair" in v:
                        history_scale = 1.0
                s.fair = float(v["fair"]) if schema >= 7 and "fair" in v else s.fair
                s.fair_open = float(v.get("fair_open", s.fair))
                s.hist.clear()
                s.hist.append(s.price)
                s.candles.clear()
                s.candles.extend([list(c) for c in v.get("candles", [])])
                for key, secs in TIMEFRAMES.items():
                    s.tf[key].clear()
                    saved_tf = v.get("tf", {}).get(key)
                    if saved_tf is not None:
                        s.tf[key].extend([list(c) for c in saved_tf])
                    else:  # state from before multi-timeframe candles: rebuild from the minute candles
                        for c in s.candles:
                            self._merge(s.tf[key], int(c[0] // secs) * secs, *c[1:])
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
                s.safety = float(v.get("safety", s.safety))
                s.pending = list(v.get("pending", []))
                s.log.clear()
                s.log.extend(v.get("log", []))
                s.reports.clear()
                s.reports.extend(v.get("reports", []))
                s.trend = float(v.get("trend", 0.0))
                s.mood = float(v.get("mood", 0.0))
                if "revenue" in v:
                    s.revenue, s.margin = float(v["revenue"]), float(v["margin"])
                    s.cash, s.debt = float(v["cash"]), float(v["debt"])
                    s.base_margin = float(v.get("base_margin", s.margin))
                if s.asset_type == "equity" and "safety" not in v:
                    s.rating = self._rating_for(s)
                s.next_earn = v.get("next_earn", s.next_earn)
                s.next_rating_review = v.get("next_rating_review", s.next_rating_review)
                s.distress_checked = v.get("distress_checked", False)
                # events that fell due while the server was down are rescheduled instead of all firing at once
                if s.next_earn and s.next_earn < self.now:
                    s.next_earn = self.now + random.uniform(*self.settings.get("earnings_initial_seconds", [1800, 5400]))
                if s.next_rating_review and s.next_rating_review < self.now:
                    s.next_rating_review = self._next_review()
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
                p.hold = {ticker: shares for ticker, shares in x["hold"].items() if ticker in self.stocks}
                p.cost = {tk: float(c) for tk, c in x.get("cost", {}).items() if tk in p.hold}
                for tk, shares in p.hold.items():  # saves from before cost tracking: entry = current price
                    p.cost.setdefault(tk, shares * self.stocks[tk].price)
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
            self.mood = float(d.get("mood", self.mood))
            self.crisis_until = float(d.get("crisis_until", 0.0))
            self.threads = list(d.get("threads", []))
            self.sector_mood = dict(d.get("sector_mood", {}))
            for line in d.get("used_news", []):
                if len(self.used_news) == self.used_news.maxlen:
                    self.used_set.discard(self.used_news[0].lower())
                self.used_news.append(line)
                self.used_set.add(line.lower())
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
