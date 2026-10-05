import bisect, glob, itertools, json, logging, math, os, random, shutil, time, uuid
from collections import deque
from time import sleep as _sleep               # (a name of its own: the tests replace `time` with a fake clock)

import newsgen
import relations
import social
from ledger import Ledger
from social import SocialMixin
from accounts import AccountsMixin, name_problem

START_CASH = 1000.0          # default signup bonus (test credits)
FEE = 0.001                  # per side (0.1%; a round trip costs about 0.2%), collected as house revenue
COOLDOWN = 1.0
MAX_POOL_FRAC = 0.05
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
# Leveraged products that were renamed (old saves and ledgers still use the old tickers) or withdrawn
from netutil import TICKER_RENAMES  # noqa: E402  (a product that was renamed: old links and old saves still work)
WITHDRAWN_PRODUCTS = {"BEAR1": "Market Bear 1x"}
ARCHIVE_MAX = 60                               # how many delisted stocks keep their page and chart
BANKS = [("Halvorsen & Co", 0.02), ("Meridian Securities", -0.03), ("Quill Capital", 0.0),
         ("Bellwether Partners", 0.03), ("Northgate Research", -0.02), ("Sable Harbour Bank", 0.01)]
# Company-specific stories. Each is announced in the news first; the effect on the financials only
# lands at the next earnings report, which then cites it. (sign, headline, margin, revenue, debt)


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
        self.split_factor = 1.0   # product of the stock splits that happened in older games (there are no new ones)
        self.share_adj = 1.0      # product of all buybacks and offerings (1.02 means 2% more shares)
        self.offering = None      # a declared share offering waiting to settle: {"t", "pct"}
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
        self.earn_slot = None                      # the nominal report time before it is snapped to pre-market or after-hours
        self.events = []                           # scheduled events between reports: [{"t": time, "kind": "guidance"|...}]
        self.next_rating_review = None
        self.distress_checked = False
        self.safety = random.uniform(0.3, 0.85)   # hidden: banks "know" it, players must infer it
        self.pending = []                          # announced issues not yet reflected in financials
        self.log = deque(maxlen=60)                # news that named this stock, for players to look back on
        self.reports = deque(maxlen=12)            # past earnings reports
        self.spec = None                           # set for indices, ETFs and leveraged products
        self.persona = None                        # CEO, CFO, product, city and related companies (see newsgen.py)
        self.trend = 0.0
        self.mood = 0.0                            # narrative momentum for this company
        self.volm = 1.0                            # volatility multiplier: rises after big moves, decays back to 1
        self.boost_until = 0.0                     # a very strong event lifts the daily limit until this time
        self.listed_at = 0.0                       # when it was listed, if that was after the game began (0 = from the start)

    def update(self, cfg):
        self.name = cfg["name"]
        self.sector = cfg["sector"]
        self.beta = float(cfg.get("beta", 1.0))
        self.vol = float(cfg.get("vol", 0.30))
        self.sens = float(cfg.get("sens", 1.0))
        self._raw_price = max(0.01, float(cfg.get("initial_price", 1.0)))
        self.market_cap_base = float(cfg.get("market_cap", 0.0))
        configured_shares = float(cfg.get("shares_outstanding", 0.0))
        self._raw_shares = (self.market_cap_base / self._raw_price if self.market_cap_base > 0 else configured_shares)
        self.rescale()
        self.dividend_yield = float(cfg.get("dividend_yield", 0.0))
        if not hasattr(self, "base_dps"):  # dividends are paid per earnings report ("quarter"): a quarter of the yield
            self.base_dps = self.dividend_yield * self.initial_price / 4
            self.dps = self.base_dps
            self.div = None                # a declared dividend waiting for its ex-date: {"t", "amt"}
        self.price_unit = cfg.get("price_unit", "MB/share")
        self.asset_type = cfg.get("asset_type", "equity")
        self.rating = cfg.get("rating", "BBB")
        self.dependencies = dict(cfg.get("dependencies", {}))
        self.traits = list(cfg.get("traits", []))
        self.cfg = dict(cfg)                       # kept so a generated company can be saved and recreated
        self.moonshot = "moonshot" in self.traits  # tiny, pre-revenue and extremely volatile (see MOONSHOTS in docs)
        self.limit_mult = float(cfg.get("limit_mult", 3.0 if self.moonshot else 1.0))   # looser daily limit
        self.desc = cfg.get("desc", "")
        self.haven = float(cfg.get("haven", 0.0))
        if not hasattr(self, "revenue"):  # financials evolve with earnings, so content reloads must not reset them
            self.margin = float(cfg.get("margin", 0.12))
            self.base_margin = self.margin
            self.revenue = float(cfg.get("revenue", 0.0))
            self.cash = float(cfg.get("cash", 0.0))
            self.debt = float(cfg.get("debt", 0.0))

    def rescale(self):
        """The reference price and share count as the content pack says, adjusted for every split, buyback and
        offering since listing (so a content reload never undoes them)."""
        self.initial_price = self._raw_price / self.split_factor
        self.shares_outstanding = self._raw_shares * self.split_factor * self.share_adj

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
    def __init__(self, name):
        self.name = name
        self.token = uuid.uuid4().hex
        self.cash = 0.0
        self.deposited = 0.0     # net tokens credited to this account (signup, deposits - withdrawals)
        self.season_base = 0.0   # equity at season start plus deposits during the season
        self.divs = {}           # dividends received (paid, for shorts) per ticker
        self.borrow = {}         # borrow fees paid per shorted ticker
        self.log = deque(maxlen=100)   # this player's last trades (for the admin page)
        self.entry_fee = {}      # fees paid opening each open position (so realised P&L is net of all fees)
        self.realized = {}       # realised profit or loss per ticker, net of fees
        self.fees_paid = 0.0
        self.curve = deque(maxlen=1440)   # [time, equity, cash] sampled once a minute (a day of history)
        self.margin_calls = 0
        self.hold = {}           # shares; negative means a short position
        self.notices = []        # one-off messages for the client (margin calls)
        self.cost = {}           # total entry cost of the open position per ticker (for average price)
        self.last_trade = {}
        self.orders = []         # open limit, stop-loss and take-profit orders (see Engine.place_order)
        self.orders_dirty = False   # the list changed since the page last saw it
        self.pw = None           # the password record (see accounts.py); None for accounts from before passwords
        self.ips = []            # salted tags of the addresses this account signed up or logged in from (last five)
        self.email = None        # the email address on the account (see accounts.py); only trusted once verified
        self.email_verified = False
        self.email_pending = None   # an address waiting for its code to be typed in
        self.created = 0.0       # when the account was made
        self.trades = 0
        social.init_player(self)   # achievements, quests, following, chat limits (see social.py)


class Engine(SocialMixin, AccountsMixin):
    def __init__(self, content_glob="*.json", state_file="state.json", ledger_path=None):
        self._init_social()
        self._init_accounts()
        self.content_glob = content_glob
        self.state_file = state_file
        self.ledger = Ledger(ledger_path) if ledger_path else None   # append-only money log (see ledger.py)
        self.index_prev = {}                       # every stock's price at the previous tick (for index returns)
        self._div_today = {}                       # ticker -> dividend as a share of price, for this tick's index returns
        self._borrow_acc = {}                      # borrow fees waiting to be written to the ledger
        self._borrow_flush_t = 0.0
        self._charts_saved = 0.0                   # when the chart file was last written
        self._reserve_t = 0.0                      # when the house reserve was last checked against its floor
        self.recapitalized = 0.0                   # what the house reserve has been topped up by (see _reserve_check)
        self._curve_t = 0.0
        self.recovered_events = 0
        self._retired_bots = 0                      # how many house-funded bots a save from an older version had (they are removed on load)
        self.now = time.time()
        self.sectors, self.templates, self.settings = {}, {}, {}
        self.derived_specs = {}                    # indices, ETFs and leveraged products from the content packs
        self.derived = {}                          # every derived asset that exists: ticker -> spec
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
        self.series = deque(maxlen=720)            # house and player money sampled every 10 s (admin charts; not saved)
        self.margin_log = deque(maxlen=50)         # recent margin calls
        self.margin_calls = 0
        self.trades_total = 0
        self._series_t = 0.0
        self.archive = {}                          # delisted stocks, kept so their page and chart can still be opened
        self.order_seq = 0                         # numbers the orders players place
        self._last_final = {}                      # per-stock moves of the most recent event (for stories that touch two companies)
        self.mkt_volm = 1.0                        # market-wide volatility multiplier (crises and recessions raise it)
        self._phase = "open"                       # pre, open or after: where we are in the 30-minute trading cycle
        self._prev_phase = None
        self._open = True                          # is the regular session under way?
        self._norm_cache = {}                      # session volatility normalisation, by settings
        self.gaps_total = 0                        # opening auctions so far
        self.borrow_fees = 0.0                     # total borrow fees collected from shorts (part of `fees`)
        self.short_shortfall = 0.0                 # losses the house absorbed when a short could not be paid for
        self._borrow_t = self.now
        self.history = []
        self.house = 0.0          # house reserve: funds new listings, receives delisted pools
        self.fees = 0.0           # fee revenue
        self.house_capital = 0.0  # tokens the house has put in (pool seeds and the reserve)
        self.minted = 0.0
        self.season_no = 1
        self.board = []
        self.rank = {}
        self.pub_stocks = []
        self.pub_fast, self.pub_slow, self.pub_static, self.pub_px = {}, {}, {}, {}
        self.pub_index = {}
        self.wire_seq = 0                          # counts the per-tick updates sent to clients
        self._wire_slow_sent = {}                  # slow numbers as last sent, so only changes go out
        self._wire_upcoming_sig = None
        self._static_sig = None
        self.static_v = 0                          # bumps when the list of listings or their facts changes
        self.news_seq = 0
        self.index_level = 100.0
        self.index_hist = deque(maxlen=MARKET_DAY_SECONDS + 1)
        self.market_day = int(self.now // MARKET_DAY_SECONDS)
        self._pending = {}
        self.regime = "Expansion"
        regime_window = self.settings.get("regime_days", [7, 14])
        self.next_regime_change = self.now + random.uniform(*regime_window) * MARKET_DAY_SECONDS
        self.sector_indices = {}
        self.relations = relations.Relations()     # who supplies whom and who competes (internal, never shown)
        self.content_sig = None
        self._reload(initial=True)
        seed = float(self.settings.get("house_seed", self.settings.get("treasury_seed", 50000)))
        self._mint_house(seed)
        self.house += seed
        self.season_end = self._season_boundary()
        event_mean = float(self.settings.get("event_mean_seconds", 120))
        self.next_event = self.now + random.expovariate(1 / event_mean)
        self.next_issue = self.now + random.expovariate(1 / float(self.settings.get('issue_mean_seconds', 100)))
        self.next_cross = self.now + random.expovariate(1 / float(self.settings.get('cross_mean_seconds', 240)))
        self.next_catalyst = self.now + random.expovariate(1 / float(self.settings.get('catalyst_mean_seconds', 480)))
        self.next_sector_shock = self.now + random.expovariate(1 / float(self.settings.get('sector_shock_mean_seconds', 600)))
        self.next_moonshot = self.now + random.expovariate(1 / float(self.settings.get('moonshot_mean_seconds', 900)))
        self.next_offering = self.now + random.expovariate(1 / float(self.settings.get('offering_mean_seconds', 1200)))
        had_state = bool(self.state_file and os.path.exists(self.state_file))
        self._pre_moonshot_save = False
        self._assign_personas()
        self._add_derived_assets()
        self._load_state()
        self._sync_relations()
        if not had_state or self._pre_moonshot_save:   # a new game (or a save from before moonshots) starts with a few listed
            for _ in range(int(self.settings.get("moonshot_initial", 4))):
                self._list_moonshot(initial=True)
            self._assign_personas()
        if self.recovered_events or self._retired_bots:
            self.save()                            # checkpoint straight away so the replayed events are not replayed again
        self._sync_index_asset()
        self.index_prev = {tk: s.price for tk, s in self.stocks.items()}
        self.index_hist.clear()
        self.index_hist.append(self.index_level)

    def _assign_personas(self):
        """Every listed company gets a CEO, CFO, flagship product, home city and a supplier, customer and rival
        (other listed companies). They are deterministic per ticker, saved, and recur in later stories."""
        others = [(tk, st.sector) for tk, st in self.stocks.items() if st.asset_type == "equity"]
        for st in self.stocks.values():
            if st.asset_type == "equity" and st.persona is None:
                st.persona = newsgen.make_persona(st.ticker, st.sector, others)

    def _persona_ctx(self, st):
        p = st.persona or {}
        return {"name": st.name, "ceo": p.get("ceo"), "cfo": p.get("cfo"), "product": p.get("product"),
                "product2": p.get("product2"), "city": p.get("city"), "supplier": self._related_name(st, "supplier"),
                "customer": self._related_name(st, "customer"), "rival": self._related_name(st, "rival"),
                "ex_ceo": p["ex_ceos"][-1] if p.get("ex_ceos") else None}

    def _change_ceo(self, st, new_ceo):
        p = st.persona
        if p and new_ceo:
            p["ex_ceos"] = (p.get("ex_ceos", []) + [p["ceo"]])[-3:]
            p["ceo"] = new_ceo

    def _add_derived_assets(self):
        """The market index, a tradable index for each big sector, themed ETFs and leveraged/inverse products.
        They have no company behind them: their price is computed from their constituents' returns every tick
        (see `_update_index_level`), so nothing can move them directly and they carry no news, ratings or dividends."""
        if "MSI" not in self.stocks:
            cfg = {"ticker": "MSI", "name": "Meme Street Index", "sector": "index", "asset_type": "index",
                   "beta": 1.0, "vol": 0.2, "initial_price": 100.0,
                   "desc": "Tracks the weighted basket of every stock on Meme Street, so you can trade the whole market in one position."}
            self.stocks["MSI"] = Stock(cfg, 0.0)
            self.stocks["MSI"].spec = {"kind": "market"}
        self.derived["MSI"] = {"kind": "market"}
        specs = dict(self.derived_specs)
        min_members = int(self.settings.get("sector_index_min_members", 3))
        if self.settings.get("auto_sector_indices", True):
            for sid, sec in self.sectors.items():
                if sid in ("safe", "meme", "commodities", "index"):
                    continue
                members = [x for x in self.stocks.values() if x.sector == sid and x.asset_type == "equity"]
                tk = "X" + sid[:4].upper()
                if len(members) >= min_members and tk not in self.stocks and tk not in specs:
                    specs[tk] = {"ticker": tk, "name": f"{sec['name']} Index", "kind": "sector", "sector": sid,
                                 "desc": f"Tracks every {sec['name']} stock, weighted by company size, so you can trade the whole sector."}
        for pass_kinds in (("sector", "basket"), ("leveraged",)):   # leveraged products need their underlying first
            for tk, spec in specs.items():
                if tk in self.stocks or spec.get("kind") not in pass_kinds:
                    continue
                kind = spec["kind"]
                if kind == "sector":
                    members = [x for x in self.stocks.values() if x.sector == spec["sector"] and x.asset_type == "equity"]
                    sector = spec["sector"]
                elif kind == "basket":
                    members = [self.stocks[m] for m in spec.get("members", []) if m in self.stocks and self.stocks[m].asset_type == "equity"]
                    sector = "index"
                else:
                    under = self.stocks.get(spec.get("of"))
                    if not under:
                        continue
                    members, sector = [], "index"
                if kind != "leveraged":
                    if not members:
                        continue
                    vol = max(0.1, 0.8 * sum(m.vol for m in members) / len(members))
                    beta = sum(m.beta for m in members) / len(members)
                else:
                    lev = float(spec.get("leverage", 1.0))
                    vol, beta = max(0.05, abs(lev) * under.vol), lev * under.beta
                cfg = {"ticker": tk, "name": spec["name"], "sector": sector, "asset_type": "index", "beta": beta,
                       "vol": vol, "initial_price": 100.0, "desc": spec.get("desc", "")}
                stock = Stock(cfg, 0.0)
                stock.spec = dict(spec)
                self.stocks[tk] = stock
                self.derived[tk] = dict(spec)

    def _sync_index_asset(self):
        s = self.stocks.get("MSI")
        if s:
            s.fair = self.index_level

    # ---------- content ----------
    def _content_files(self):
        """The content packs: every .json file in the folder except the save and its chart file (which are big, are
        rewritten while the game runs and are not content: reading them as packs made every chart save look like a
        content change, and a read could fail while the file was being replaced)."""
        skip = set()
        for name in (self.state_file or "state.json", "state.json"):
            skip.add(os.path.abspath(name))
            skip.add(os.path.abspath(os.path.splitext(name)[0] + ".charts.json"))
        return [f for f in glob.glob(self.content_glob) if os.path.abspath(f) not in skip]

    def _sig(self):
        return tuple((f, os.path.getmtime(f)) for f in sorted(self._content_files()))

    def _read(self):
        sectors, companies, templates, settings, profiles, derived = {}, {}, {}, {}, {}, {}
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
            for x in d.get("derived", []):
                derived[x["ticker"]] = x
        return sectors, companies, templates, settings, profiles, derived

    def _reload(self, initial=False):
        try:
            sectors, companies, templates, settings, profiles, derived = self._read()
        except Exception as e:
            logger.exception("content reload failed")
            self.news("system", f"Content reload failed: {e}")
            return
        self.content_sig = self._sig()
        self.sectors, self.templates = sectors, templates
        self.derived_specs = derived
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
        if not initial:
            self._add_derived_assets()   # a pack that was added while running may bring new indices or ETFs
            self._assign_personas()
            self._sync_relations()

    def _mint_house(self, amount):
        self.minted += amount
        self.house_capital += amount

    # ---------- the house reserve and its risk ----------
    def _reserve_floor(self):
        """The least the house reserve should hold: the larger of a share (`reserve_floor_frac`, 10%) of what human
        players have in total and a share (`reserve_stress_frac`, 50%) of the stress loss (see `house_risk`), and never
        less than `reserve_floor_min`. Players may put as much as they like into one stock, and a fair bet can still be
        a big one; the floor keeps the reserve in proportion to the money that can win from it."""
        frac = float(self.settings.get("reserve_floor_frac", 0.10))
        stress = float(self.settings.get("reserve_stress_frac", 0.5))
        if frac <= 0 and stress <= 0:
            return 0.0
        equity = sum(self.equity(p) for p in self.players.values())
        return max(float(self.settings.get("reserve_floor_min", 0.0)), frac * equity, stress * self._exposure()[1])

    def _reserve_check(self):
        """Every five seconds: if the reserve has fallen below its floor, top it up. This changes nothing a player
        sees or receives (every payout is made in full either way) and moves no price; it only means the house's
        capital grows when players are collectively winning, and `recapitalized` records how much that has been."""
        if self.now - self._reserve_t < 5.0 or not self.settings.get("reserve_recap", True):
            return
        self._reserve_t = self.now
        floor = self._reserve_floor()
        if self.house < floor:
            amount = floor - self.house
            self.house += amount
            self._mint_house(amount)
            self.recapitalized += amount
            self._emit("recap", None, house=amount)

    def house_risk(self):
        """What the house stands to lose to its players, for the admin page. The house is the other side of every
        position, so a stock players hold net long hurts the house when it rises and one they hold net short hurts it
        when it falls. `stress_loss` is the loss if every stock moved three of its own daily sigmas against the house
        at once (deliberately pessimistic: the stocks are not all driven by the same thing)."""
        rows, stress = self._exposure()
        return {"reserve": self.house, "floor": self._reserve_floor(), "recapitalized": self.recapitalized,
                "stress_loss": stress, "exposure": rows[:8]}

    def _exposure(self):
        """(per-stock rows sorted by what they could cost the house, the total stress loss)."""
        net = {}
        for p in self.players.values():
            for tk, sh in p.hold.items():
                s = self.stocks.get(tk)
                if s:
                    net[tk] = net.get(tk, 0.0) + sh * s.price
        rows, stress = [], 0.0
        for tk, v in net.items():
            s = self.stocks[tk]
            move = 3 * self._daily_sigma(s)
            loss = abs(v) * (move if v > 0 else min(move, 1.0))
            stress += loss
            rows.append({"ticker": tk, "name": s.name, "net": v, "move": move, "loss": loss})
        rows.sort(key=lambda r: -r["loss"])
        return rows, stress

    def _list(self, cfg, initial):
        depth = float(cfg.get("depth", 20000))
        take = 0.0 if initial else min(max(self.house, 0.0), depth)
        self.house -= take
        if depth > take:
            self._mint_house(depth - take)
        s = Stock(cfg, depth)
        reports = s.asset_type == "equity" and s.revenue > 0
        if reports:
            s.earn_slot = self._pick_earnings_slot()
            s.next_earn = self._snap_to_window(s.earn_slot)
            s.events = self._new_company_events(s)
        s.next_rating_review = self._next_review() if s.asset_type == "equity" else None
        if s.asset_type == "equity":
            s.rating = self._rating_for(s)
        s.hist.append(s.price)
        s.day_open = s.day_high = s.day_low = s.price
        self.stocks[s.ticker] = s
        self._record(s)
        if not initial:
            s.listed_at = self.now
            sec = self.sectors[s.sector]["name"]
            self.news("ipo", f"NEW LISTING: {s.name} ({s.ticker}) debuts in {sec}. {s.desc}", [s.ticker])
            self._sync_relations()                 # its suppliers, customers and rivals, and theirs in turn

    def _quarter_seconds(self):
        """One fiscal quarter in real seconds: a quarter is a quarter of a 252-day game year (63 game days)."""
        return float(self.settings.get("earnings_quarter_days", TRADING_DAYS_PER_YEAR / 4)) * MARKET_DAY_SECONDS

    def _pick_earnings_slot(self):
        """When a company first reports. Companies are spread over the quarter so that there are always a few
        reports per game day and one is always coming up: of a dozen random candidate times the one farthest from
        every report already on the calendar is taken. (Reports are not bunched into a few weeks the way they are
        in real life.)"""
        q = self._quarter_seconds()
        taken = sorted(s.earn_slot for s in self.stocks.values() if s.earn_slot)
        best, best_gap = None, -1.0
        for _ in range(12):
            c = self.now + random.uniform(0.005, 1.0) * q
            i = bisect.bisect(taken, c)
            gap = min((abs(c - taken[j]) for j in (i - 1, i) if 0 <= j < len(taken)), default=q)
            if gap > best_gap:
                best, best_gap = c, gap
        return best

    def _snap_to_window(self, t):
        """Reports only come out before the open (pre-market) or after the close (after-hours): the time is moved
        into the pre-market or after-hours window of the 30-minute cycle it falls in, chosen at random and at a
        random second. With no sessions, or a quarter shorter than a game day (a demo or a test), it is left alone."""
        pre, post = self._session_lengths()
        if (pre <= 0 and post <= 0) or self._quarter_seconds() < MARKET_DAY_SECONDS:
            return t
        cycle = math.floor(t / MARKET_DAY_SECONDS) * MARKET_DAY_SECONDS
        windows = ([(cycle, cycle + pre)] if pre > 0 else []) + (
            [(cycle + MARKET_DAY_SECONDS - post, cycle + MARKET_DAY_SECONDS)] if post > 0 else [])
        lo, hi = random.choice(windows)
        when = random.uniform(lo, hi)
        if when < self.now + 1:                                  # that window has passed: take the next cycle's
            when = random.uniform(lo, hi) + MARKET_DAY_SECONDS
        return when

    def _reschedule_earnings(self, s):
        """The next report is a quarter after this one's nominal time, give or take a few game days, then snapped
        to pre-market or after-hours. The slots drift a little each quarter but stay spread out."""
        q = self._quarter_seconds()
        jitter = min(float(self.settings.get("earnings_jitter_days", 4)) * MARKET_DAY_SECONDS, 0.15 * q)
        base = s.earn_slot if s.earn_slot and s.earn_slot > self.now - q else self.now
        s.earn_slot = max(base + q + random.uniform(-jitter, jitter), self.now + 0.5 * q)
        s.next_earn = self._snap_to_window(s.earn_slot)

    def _sync_relations(self):
        """Keep the supplier, customer and rival links in step with the listed companies: link in any equity that is
        new (the companies already there get the matching link on their side) and drop the ones that are gone."""
        live = {tk for tk, s in self.stocks.items() if s.asset_type == "equity" and not s.moonshot}
        for tk in [t for t in self.relations.sector if t not in live]:
            self.relations.remove(tk)
        self.relations.add([(tk, s.sector, f"{s.name} {s.desc}") for tk, s in self.stocks.items()
                            if tk in live and tk not in self.relations])

    def _related_name(self, st, kind):
        """The name of one of a company's suppliers, customers or rivals, if it has any, for a story."""
        pool = [self.stocks[t] for t in self.relations.partners(st.ticker, kind)
                if t in self.stocks and self.stocks[t].asset_type == "equity"]
        return random.choice(pool).name if pool else None

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
        tilt = float(self.settings.get("mood_tilt", 1.0))  # 0 turns the narrative bias off (for experiments)
        return _clamp(0.5 + 0.3 * eff * tilt, 0.15, 0.85)

    def _dress(self, text, tone):
        """Lead-in and tail for variety. Tone-only: nothing here reveals the hidden mood."""
        lead = ""
        if random.random() < 0.45:
            lead = f"{random.choice(newsgen.SOURCES)} reports: " if random.random() < 0.3 else random.choice(LEADS)
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
        vol_target = 1.5 if crisis else {"Recession": 1.2, "Bubble": 1.15, "Boom": 0.95}.get(self.regime, 1.0)
        self.mkt_volm += (vol_target - self.mkt_volm) * (1 - math.exp(-dt / 150))
        for k in list(self.sector_mood):
            self.sector_mood[k] *= math.exp(-dt / 400)
        for st in self.stocks.values():
            st.mood *= math.exp(-dt / 600)

    def news(self, kind, text, tickers=(), dirn=0, strength="bystander"):
        text = self._unique(text)
        self.news_seq += 1
        self.news_log.append({"id": self.news_seq,
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
        bad = name_problem(name)
        if bad:
            return None, bad
        if any(p.name.lower() == name.lower() for p in self.players.values()):
            return None, "Name taken"
        p = Player(name)
        p.created = self.now
        self._register(p)
        self._emit("join", p)
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
        ratio = self._ratio(p)
        p.cash += amount
        p.deposited += amount
        p.season_base += amount
        self.minted += amount
        self._rebase_peak(p, ratio)     # paying in is not performance: keep the drawdown tracker honest
        self._emit("credit", p, cash=amount, notional=amount)
        return True, f"Credited {amount:.2f} MB"

    def debit(self, p, amount):
        """Tokens leave the game (withdrawal). Only free cash (not locked as short collateral) can leave."""
        amount = float(amount)
        if amount <= 0:
            return False, "Amount must be positive"
        if amount > self.free_cash(p) + 1e-9:
            return False, "Not enough free cash; close positions first"
        ratio = self._ratio(p)
        p.cash -= amount
        p.deposited -= amount
        p.season_base = max(0.0, p.season_base - amount)
        self.minted -= amount
        self._rebase_peak(p, ratio)
        self._emit("debit", p, cash=-amount, notional=amount)
        return True, f"Withdrew {amount:.2f} MB"

    # ---------- risk limits (borrowing and margin; there is no cap on the size of a position) ----------
    def short_cap(self, s):
        """Most shares-worth (MB) that all players together may have borrowed to short this stock."""
        base = s.base if s.base > 0 else float(self.settings.get("short_cap_index", 16000))
        return float(self.settings.get("short_cap_frac", 0.25)) * base

    def short_interest_map(self):
        out = {}
        for p in self.players.values():
            for tk, sh in p.hold.items():
                if sh < 0 and tk in self.stocks:
                    out[tk] = out.get(tk, 0.0) + -sh * self.stocks[tk].price
        return out

    def borrow_rate_day(self, s, util=0.0):
        """Borrow fee per game day (30 real minutes) as a share of the short's value. Volatile and heavily
        shorted stocks cost more: (0.03% + 0.1% x volatility) x (1 + 3 x share of the borrow limit in use)."""
        base = float(self.settings.get("borrow_base_day", 0.0003))
        coeff = float(self.settings.get("borrow_vol_day", 0.001))
        return (base + coeff * s.vol) * (1 + 3 * _clamp(util, 0.0, 1.0))

    def margin_req(self, s):
        """Initial margin multiple for shorting: 1x up to 35% volatility, rising to 2x at 80% and above."""
        return 1 + _clamp((s.vol - 0.35) / 0.45, 0, 1) + _clamp((s.vol - 1.2) / 1.8, 0, 1)   # up to 3x for moonshots

    def maintenance(self, s):
        """Margin-call level as a share of the short's value: 25% up to 30% volatility, rising to 50% at 90%+."""
        return 0.25 + 0.25 * _clamp((s.vol - 0.30) / 0.60, 0, 1) + 0.25 * _clamp((s.vol - 1.2) / 1.8, 0, 1)

    def margin_used(self, p):
        total = 0.0
        for tk, sh in p.hold.items():
            s = self.stocks.get(tk)
            if s and sh < 0:
                total += -sh * s.price * self.margin_req(s)
        return total

    def short_liability(self, p):
        """What it would cost, before fees, to buy back every short."""
        total = 0.0
        for tk, sh in p.hold.items():
            s = self.stocks.get(tk)
            if s and sh < 0:
                total += -sh * s.price
        return total

    def free_cash(self, p):
        """Cash you can spend. A short does not add to it: the amount you short is taken out of your cash as collateral
        (see `_do_short`), so cash is simply cash."""
        return max(0.0, p.cash)

    def equity(self, p):
        v = p.cash
        for tk, sh in p.hold.items():
            s = self.stocks.get(tk)
            if not s:
                continue
            if sh > 0:
                v += s.quote_sell(sh)[0]
            else:                                    # a short: the collateral posted, plus what the price has done for you
                v += 2 * p.cost.get(tk, -sh * s.price) - (-sh) * s.price * (1 + FEE)
        return v

    # ---------- trading ----------
    def _emit(self, kind, p=None, ticker=None, shares=0.0, price=0.0, cash=0.0, house=0.0, fee=0.0, cost=0.0,
              notional=0.0, pnl=None, **extra):
        """Record a money event in the ledger (if there is one). The numbers are deltas: what this event added to
        the player's cash, to the house reserve, to fees, to the position's shares and to its cost basis."""
        if self.ledger is None:
            return
        self.ledger.add(t=self.now, kind=kind, token=p.token if p else None, name=p.name if p else None,
                        ticker=ticker, shares=shares, price=price, cash_delta=cash, house_delta=house, fee=fee,
                        cost_delta=cost, notional=notional, pnl=pnl, extra=extra or None)

    def _log(self, p, kind, s, shares, notional, fee):
        p.log.append({"t": self.now, "k": kind, "tk": s.ticker, "sh": shares, "px": s.price, "mb": notional,
                      "fee": fee})

    def _do_buy(self, p, s, cash):
        """Trades execute at the market price against the house, so they never move the price."""
        shares, fee = s.quote_buy(cash)
        self.house += cash - fee
        self.fees += fee
        p.cash -= cash
        if abs(p.hold.get(s.ticker, 0.0)) < 1e-9:
            self._on_open(p, s.ticker)
        p.hold[s.ticker] = p.hold.get(s.ticker, 0.0) + shares
        p.cost[s.ticker] = p.cost.get(s.ticker, 0.0) + shares * s.price
        p.entry_fee[s.ticker] = p.entry_fee.get(s.ticker, 0.0) + fee
        p.fees_paid += fee
        self._log(p, "buy", s, shares, cash, fee)
        self._emit("buy", p, s.ticker, shares=shares, price=s.price, cash=-cash, house=cash - fee, fee=fee,
                   cost=shares * s.price, notional=cash)
        self._on_trade(p, "buy", s, cash)
        return shares

    def _close_basis(self, p, ticker, fraction):
        """Take `fraction` of a position's cost basis and entry fees out of the books. Returns (cost, entry fee)."""
        cost_before = p.cost.get(ticker, 0.0)
        fee_before = p.entry_fee.get(ticker, 0.0)
        if fraction >= 1 - 1e-12:
            p.cost.pop(ticker, None)
            p.entry_fee.pop(ticker, None)
            return cost_before, fee_before
        p.cost[ticker] = cost_before * (1 - fraction)          # the average entry price is unchanged
        p.entry_fee[ticker] = fee_before * (1 - fraction)
        return cost_before * fraction, fee_before * fraction

    def _do_sell(self, p, s, shares):
        proceeds, fee = s.quote_sell(shares)
        self.house -= proceeds + fee
        self.fees += fee
        p.cash += proceeds
        p.fees_paid += fee
        self._log(p, "sell", s, shares, proceeds + fee, fee)
        held = p.hold.get(s.ticker, 0.0)
        left = held - shares
        fraction = shares / held if held > 0 else 1.0
        if left < 1e-9:
            p.hold.pop(s.ticker, None)
            fraction = 1.0
        else:
            p.hold[s.ticker] = left
        cost_removed, fee_removed = self._close_basis(p, s.ticker, fraction)
        pnl = proceeds - cost_removed - fee_removed
        p.realized[s.ticker] = p.realized.get(s.ticker, 0.0) + pnl
        self._emit("sell", p, s.ticker, shares=-shares, price=s.price, cash=proceeds, house=-(proceeds + fee), fee=fee,
                   cost=-cost_removed, notional=proceeds + fee, pnl=pnl, efee=fee_removed)
        self._on_trade(p, "sell", s, proceeds + fee, pnl, closed=fraction >= 1.0)
        return proceeds

    def _do_short(self, p, s, shares):
        """Sell shares you don't own. What you short is taken out of your cash and held by the house as collateral
        (it does not increase your cash). Closing the short gives the collateral back, plus the gain or minus the loss."""
        gross = shares * s.price
        fee = gross * FEE
        self.house += gross
        self.fees += fee
        p.cash -= gross + fee
        if -1e-9 < p.cash < 0:
            p.cash = 0.0                                # (rounding when the whole stake is shorted)
        if abs(p.hold.get(s.ticker, 0.0)) < 1e-9:
            self._on_open(p, s.ticker)
        p.hold[s.ticker] = p.hold.get(s.ticker, 0.0) - shares
        p.cost[s.ticker] = p.cost.get(s.ticker, 0.0) + gross
        p.entry_fee[s.ticker] = p.entry_fee.get(s.ticker, 0.0) + fee
        p.fees_paid += fee
        self._log(p, "short", s, shares, gross, fee)
        self._emit("short", p, s.ticker, shares=-shares, price=s.price, cash=-(gross + fee), house=gross, fee=fee,
                   cost=gross, notional=gross)
        self._on_trade(p, "short", s, gross)
        return gross

    def _short_payout(self, p, cost_part, value, fee):
        """(cash change, shortfall) when a short with `cost_part` of collateral is bought back at `value`: the
        collateral plus the gain, less the fee. If the loss is bigger than the collateral the player pays what they
        have and the house absorbs the rest."""
        got = 2 * cost_part - value - fee
        if got >= 0:
            return got, 0.0
        pay = min(-got, max(p.cash, 0.0))
        return -pay, -got - pay

    def _do_cover(self, p, s, shares, pay_all=False):
        """Buy back shorted shares. If the loss is more than the collateral and cash can't cover it, it is refused
        (unless it is a margin call, when the player pays what they have)."""
        held = p.hold.get(s.ticker, 0.0)
        shares = min(shares, -held)
        fraction = shares / -held if held < 0 else 1.0
        cost_part = p.cost.get(s.ticker, 0.0) * fraction
        value = shares * s.price
        fee = value * FEE
        cd, short = self._short_payout(p, cost_part, value, fee)
        if short > 0:
            if not pay_all:
                return None
            self.short_shortfall += short
        p.cash += cd
        self.house -= cd + fee
        self.fees += fee
        p.fees_paid += fee
        kind = "margin_call" if pay_all else "cover"
        self._log(p, kind, s, shares, value, fee)
        left = held + shares
        if left > -1e-9:
            p.hold.pop(s.ticker, None)
            fraction = 1.0
        else:
            p.hold[s.ticker] = left
        cost_removed, fee_removed = self._close_basis(p, s.ticker, fraction)
        pnl = cost_removed - fee_removed - value - fee
        p.realized[s.ticker] = p.realized.get(s.ticker, 0.0) + pnl
        self._emit(kind, p, s.ticker, shares=shares, price=s.price, cash=cd, house=-(cd + fee), fee=fee,
                   cost=-cost_removed, notional=value, pnl=pnl, efee=fee_removed)
        self._on_trade(p, kind, s, value, pnl, closed=fraction >= 1.0)
        return value

    def avg_price(self, p, ticker):
        sh = abs(p.hold.get(ticker, 0.0))
        return p.cost.get(ticker, 0.0) / sh if sh > 0 else 0.0

    def trade(self, p, ticker, side, pct, amount=None):
        """pct is a fraction (of free cash / position / spare margin); amount, when given, is MB and wins."""
        s = self.stocks.get(ticker)
        if not s:
            return False, "Unknown ticker"
        gate = self.email_gate(p)
        if gate:
            return False, gate
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
                shares = min(shares, -held)
                if shares * price < 1 and shares < -held - 1e-9:
                    return False, "Too small to cover (min 1)"
                cost = self._do_cover(p, s, shares)
                if cost is None:
                    return False, "Not enough cash to cover the loss on this short"
                msg = f"Covered {shares:.2f} {ticker} short, buying back {cost:.2f} MB worth"
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
            else:  # nothing to sell: open or add to a short, paid for out of your cash (there is no other limit)
                free = self.free_cash(p)
                outlay = amount if amount is not None else free * pct
                if outlay > free + 1e-9:
                    return False, f"Not enough free cash to short ({free:.2f} MB available)"
                if outlay < 1:
                    return False, "Not enough cash (min 1)"
                gross = outlay / (1 + FEE)
                sh = gross / price
                self._do_short(p, s, sh)
                msg = f"Shorted {sh:.2f} {ticker} for {gross:.2f} MB (taken out of your cash as collateral)"
        else:
            return False, "Bad side"
        p.last_trade[ticker] = self.now
        p.trades += 1
        self.trades_total += 1
        return True, msg

    def _margin_calls(self):
        """Shorts must stay covered. A short in a calm stock is called when equity falls below 25% of what
        closing it would cost; in a volatile stock the level rises to 50%. When any call triggers, every
        short is closed at the market price (the player pays what they have; see `short_shortfall`)."""
        for p in self.players.values():
            if not any(sh < 0 for sh in p.hold.values()):
                continue
            need = 0.0
            for tk, sh in p.hold.items():
                st = self.stocks.get(tk)
                if st and sh < 0:
                    need += -sh * st.price * self.maintenance(st)
            if need <= 0 or self.equity(p) >= need:
                continue
            closed = []
            shortfall0 = self.short_shortfall
            for tk, sh in list(p.hold.items()):
                if sh < 0 and tk in self.stocks:
                    self._do_cover(p, self.stocks[tk], -sh, pay_all=True)
                    closed.append(tk)
            p.margin_calls += 1
            self.margin_calls += 1
            self.margin_log.append({"t": self.now, "player": p.name, "tickers": closed,
                                    "shortfall": self.short_shortfall - shortfall0})
            self._emit("margin", p, tickers=closed, shortfall=self.short_shortfall - shortfall0)
            p.notices.append("Margin call: your short in " + ", ".join(closed) + " was closed at the market price.")

    def _flush_borrow(self):
        """Write the borrow fees collected since the last flush as one ledger event per player and stock."""
        for (token, tk), fee in self._borrow_acc.items():
            p = self.by_token.get(token)
            if p:
                self._emit("borrow", p, tk, cash=-fee, fee=fee, notional=fee)
        self._borrow_acc = {}
        self._borrow_flush_t = self.now

    def _borrow_fees(self):
        """Every tick, shorts pay a borrow fee: a share of their value that depends on the stock's volatility
        and on how much of its borrow limit is already used. The fee goes to the house."""
        dt = max(0.0, min(5.0, self.now - self._borrow_t))
        self._borrow_t = self.now
        if dt <= 0:
            return
        interest = None
        for p in self.players.values():
            if not any(sh < 0 for sh in p.hold.values()):
                continue
            if interest is None:
                interest = self.short_interest_map()
            for tk, sh in p.hold.items():
                st = self.stocks.get(tk)
                if not st or sh >= 0:
                    continue
                util = interest.get(tk, 0.0) / max(self.short_cap(st), 1e-9)
                fee = min(-sh * st.price * self.borrow_rate_day(st, util) * dt / MARKET_DAY_SECONDS, p.cash)
                if fee > 0:
                    p.cash -= fee
                    self.fees += fee
                    self.borrow_fees += fee
                    p.fees_paid += fee
                    p.borrow[tk] = p.borrow.get(tk, 0.0) + fee
                    if self.ledger is not None:
                        key = (p.token, tk)
                        self._borrow_acc[key] = self._borrow_acc.get(key, 0.0) + fee

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

    def _vol_multiplier(self, stock):
        return _clamp(stock.volm * self.mkt_volm, 0.5, 3.0)

    def _update_volatility(self, stock, applied_return, scale=1.0):
        """GARCH-style clustering. A move bigger than the current noise level raises the stock's volatility
        multiplier; a smaller one lowers it; it always decays back toward 1 (half-life `vol_cluster_decay_days`
        game days). The multiplier scales *future* moves only and is known in advance, so it changes how wild the
        market is without making any direction more likely: the expected move stays zero.

        `scale` is how big a normal second is right now (the session factor, §6.8). The move is measured against
        it, so the thin pre-market and after-hours are not mistaken for a calm spell, and the burst at the open is
        not mistaken for a storm: the multiplier follows real surprises, not the known shape of the day."""
        k = float(self.settings.get("vol_cluster_k", 0.01))
        if k <= 0:
            return
        sigma_tick = self._daily_sigma(stock) / math.sqrt(MARKET_DAY_SECONDS) * scale
        m = self._vol_multiplier(stock)
        stock.volm += k * (abs(applied_return) / sigma_tick - 0.8 * m)   # 0.8 = E|Z| for a standard normal shock
        half_life = float(self.settings.get("vol_cluster_decay_days", 1.0)) * MARKET_DAY_SECONDS
        stock.volm = _clamp(1.0 + 0.5 ** (1.0 / half_life) * (stock.volm - 1.0), 0.5, 3.0)

    def _vol_scale(self):
        return float(self.settings.get("volatility_scale", 1.0))

    def _daily_sigma(self, s):
        return s.vol * self._vol_scale() / math.sqrt(TRADING_DAYS_PER_YEAR)

    def _random_market_moves(self):
        annual_scale = math.sqrt(TRADING_DAYS_PER_YEAR * MARKET_DAY_SECONDS) / self._vol_scale()
        commodity_trend = float(self.settings.get("commodity_trend", 0.0))
        session = self._session_mult()
        jump_ticks = self._open_jump_ticks() if self._opening_tick() else 0.0
        market_shock = random.gauss(0.0, 1.0)
        sector_shocks = {sector: random.gauss(0.0, 1.0) for sector in self.sectors}
        if jump_ticks:                 # the opening auction: a fresh, independent shock for every stock
            self.gaps_total += 1
            jump_market = random.gauss(0.0, 1.0)
            jump_sectors = {sector: random.gauss(0.0, 1.0) for sector in self.sectors}
        returns = {}
        for stock in self.stocks.values():
            if stock.asset_type == "index":
                continue
            market_sigma = stock.beta * 0.18
            sector_sigma = 0.08
            idio_sigma = math.sqrt(max(stock.vol ** 2 - market_sigma ** 2 - sector_sigma ** 2, 0.005 ** 2))
            vm = self._vol_multiplier(stock)
            shock = (market_sigma * market_shock + sector_sigma * sector_shocks.get(stock.sector, 0.0)
                     + idio_sigma * random.gauss(0.0, 1.0)) / annual_scale
            shock *= vm * session                    # known before the shock is drawn, so the mean stays zero
            if stock.asset_type == "commodity" and commodity_trend > 0:
                # OFF by default. A slow drift makes returns predictable: following the last 10 minutes earned
                # +0.15% per 20 minutes before fees in the edge probe, a momentum edge, so commodities are
                # pure noise now. Kept as an experiment: `commodity_trend` scales the old drift.
                stock.trend = stock.trend * 0.998 + random.gauss(0.0, commodity_trend * 0.0015 * stock.vol / annual_scale)
                shock += stock.trend
            sig = stock.vol / annual_scale * max(vm * session, 1.0)        # one typical second of this stock's noise
            lim = max(0.01, 5.0 * sig)                                     # 1% for ordinary stocks, more for wild ones
            shock = max(-lim, min(lim, shock))
            if jump_ticks:
                jump = (market_sigma * jump_market + sector_sigma * jump_sectors.get(stock.sector, 0.0)
                        + idio_sigma * random.gauss(0.0, 1.0)) / annual_scale * math.sqrt(jump_ticks) * vm
                cap = max(0.08, 6.0 * sig)
                shock += max(-cap, min(cap, jump))
            returns[stock.ticker] = shock
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
                     for tk, s in self.stocks.items() if s.fair > 0 and not s.moonshot})   # moonshots are free to run

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
        self._last_final = final
        if strength == "very strong":
            until = self.now + float(self.settings.get("major_event_boost_seconds", 600))
            for tk in final:
                self.stocks[tk].boost_until = max(self.stocks[tk].boost_until, until)
        def raw_for(sgn):
            text = random.choice(tpl["up"] if sgn > 0 else tpl["down"]).format(name=label, sector=label)
            return newsgen.paraphrase(text, random) if tpl.get("paraphrase", True) else text

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
            deferred = (scope, 1 if sign == good_dir else -1, strength, tgt_sector, target if scope == "company" else None)
            self.events.append({"start": self.now + random.uniform(*rumor_delay), "rest": rest,
                                "sign": sign, "shown": shown, "text": text, "top": top,
                                "strength": strength, "after": deferred})
            self.news("rumor", "RUMOR: " + (text if shown == sign else fmt(shown, raw_for(shown))), top, shown, strength)
            self._queue(pre)
        else:
            deferred = None
            self.news("breaking", prefix + text, top, sign, strength)
            self._queue(final)
        if deferred is None:
            self._after_event(scope, 1 if sign == good_dir else -1, strength, tgt_sector, tgt_stock)
        if follow:
            self._remember(tpl, scope, target, tgt_sector, label, core, sign, strength, issue)
        return final.get(target) if scope == "company" else None

    def _after_event(self, scope, tone, strength, sector, stock):
        """The narrative reacts to news once its truth is public: the hidden mood moves with the headline's tone, and a
        very strong bad market story can start a crisis (never announced; it just makes bad headlines likelier for a
        while). A rumor waits for its confirmation or correction before it does this: the mood would otherwise carry the
        rumor's true direction, which the price has not yet fully moved to, and anyone reading the mood would know
        where the rest of the move goes."""
        self._nudge(scope, tone, strength, sector, stock)
        if scope == "market" and tone < 0 and strength == "very strong" and self.now >= self.crisis_until:
            self.crisis_until = self.now + random.uniform(480, 900)

    @staticmethod
    def _scale_effect(effect, move):
        """Make a story's effect on the financials match how far the market moved the price when it broke,
        so earnings later confirm the price instead of contradicting it (the P/E stays steady)."""
        nominal = effect["dr"] + effect["dm"]
        if move is None or abs(nominal) < 1e-6 or move * nominal <= 0:
            return
        f = _clamp(abs(move / nominal), 0.25, 2.5)
        effect["dm"] *= f
        effect["dr"] *= f
        effect["dd"] *= _clamp(f, 0.5, 1.5)

    # ---------- story memory: follow-ups and switch-ups ----------
    def _remember(self, tpl, scope, target, sector, label, core, sign, strength, issue, stage=0):
        if not self.settings.get("news_followups", True):  # switch for experiments
            return
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
            tpl2 = {**tpl, "rumor": False, "up": [headline], "down": [headline], "paraphrase": False}
            # same strength for both branches: only the 0.8x / 1.2x scale differs, so the expected move is zero
            strength = th["strength"]
            move = self._spawn_event(tpl2, target, sign, strength, scale,
                                     prefix="UPDATE: " if cont else "REVERSAL: ", follow=False)
            if not cont and tpl.get("scope") == "company":
                self.last_reversal[target] = self.now      # for the "caught the reversal" achievement
            issue = th.get("issue")
            stock = self.stocks.get(target)
            if issue and stock is not None:
                k = 0.5 if cont else -0.7  # the follow-up also changes what the next earnings report will show
                why = (f"further developments in {issue['why']}" if cont else f"a reversal after {issue['why']}")
                effect = {"t": self.now, "text": headline, "why": why, "dm": issue["dm"] * k,
                          "dr": issue["dr"] * k, "dd": issue["dd"] * k}
                self._scale_effect(effect, move)
                stock.pending.append(effect)
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
            if ev.get("after"):
                scope, tone, strength, sector, ticker = ev["after"]
                self._after_event(scope, tone, strength, sector, self.stocks.get(ticker) if ticker else None)
            self.events.remove(ev)

    @staticmethod
    def _money(v):
        return f"{v:.1f}B MB" if abs(v) >= 1 else f"{v * 1000:.0f}M MB"

    def _issues(self):
        """Company stories are announced first; earnings later show their effect on the financials. Each story is
        written from slot templates (see newsgen.py) using the company's CEO, CFO, product, city and its supplier,
        customer and rival, so the same kind of story reads differently for every company."""
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
        strength = random.choices(["weak", "strong"], weights=[0.7, 0.3])[0]
        ctx = self._persona_ctx(s)
        taken = {ctx["ceo"], ctx["cfo"]}
        ctx["new_ceo"] = newsgen.person(random, avoid=taken)
        pct = random.uniform(1.0, 2.5) if strength == "weak" else random.uniform(3.0, 5.5)
        ctx["pct"] = f"{pct:.1f}"
        kinds = list(newsgen.KINDS_BY_SIGN[sign])
        random.shuffle(kinds)
        kind = headline = None
        for k in kinds:
            options = [t for t in (newsgen.fill(x, ctx) for x in k["texts"]) if t]
            if options:
                kind, headline = k, random.choice(options)
                break
        if kind is None:
            return
        scale_k = random.uniform(0.7, 1.3)
        effect = {"t": self.now, "text": headline, "why": kind["why"], "dm": kind["dm"] * scale_k,
                  "dr": kind["dr"] * scale_k, "dd": kind["dd"] * scale_k}
        if kind.get("ds"):
            effect["ds"] = (-pct if sign > 0 else pct) / 100      # a buyback retires shares, an offering issues them
        tpl = {"scope": "company", "ticker": s.ticker, "rumor": False, "betas": {"self": 1.0},
               "up": [headline], "down": [headline], "paraphrase": False}
        s.pending.append(effect)
        move = self._spawn_event(tpl, s.ticker, sign, strength, scale, issue=effect)
        self._scale_effect(effect, move)
        if kind.get("new_ceo"):
            self._change_ceo(s, ctx["new_ceo"])

    def _cross_stories(self):
        """A story that involves two named companies and moves both: a supplier outage that also hurts its
        customer, a rival winning a contract, a partnership, a takeover bid. One text pair covers both directions,
        and the likelier direction moves prices less so the expected move stays zero (as for every other story)."""
        if self.now < self.next_cross:
            return
        self.next_cross = self.now + random.expovariate(1 / float(self.settings.get("cross_mean_seconds", 240)))
        pool = [s for s in self.stocks.values() if s.asset_type == "equity" and s.revenue > 0 and s.persona]
        if not pool:
            return
        s = random.choice(pool)
        kind = random.choice(newsgen.CROSS_KINDS)
        partners = [self.stocks[t] for t in self.relations.partners(s.ticker, kind["relation"])
                    if t in self.stocks and self.stocks[t].asset_type == "equity" and self.stocks[t].revenue > 0]
        if not partners:                           # not every company has a customer or a rival
            return
        partner = random.choice(partners)
        eff = self._eff_mood("company", s.sector, s)
        p_pos = _clamp(0.5 + 0.25 * (s.safety - 0.5) + 0.25 * eff, 0.15, 0.85)
        sign = 1 if random.random() < p_pos else -1
        scale = 2 * (1 - (p_pos if sign > 0 else 1 - p_pos))
        ctx = self._persona_ctx(s)
        ctx["other"] = partner.name
        pool_text = kind["texts_up"] if sign > 0 else kind["texts_down"]
        options = [t for t in (newsgen.fill(x, ctx) for x in pool_text) if t]
        if not options:
            return
        headline = random.choice(options)
        tpl = {"scope": "company", "ticker": s.ticker, "rumor": False,
               "betas": {"self": 1.0, partner.ticker: kind["other_weight"]}, "up": [headline], "down": [headline],
               "paraphrase": False}
        strength = random.choices(["weak", "strong"], weights=[0.65, 0.35])[0]
        mine = {"t": self.now, "text": headline, "why": kind["why"], "dm": 0.08 * sign, "dr": 0.05 * sign, "dd": 0.0}
        w = kind["other_weight"]
        theirs = {"t": self.now, "text": headline, "why": kind["why"], "dm": 0.08 * abs(w) * sign * (1 if w > 0 else -1),
                  "dr": 0.05 * abs(w) * sign * (1 if w > 0 else -1), "dd": 0.0}
        s.pending.append(mine)
        partner.pending.append(theirs)
        self._spawn_event(tpl, s.ticker, sign, strength, scale)
        final = self._last_final or {}
        self._scale_effect(mine, final.get(s.ticker))
        self._scale_effect(theirs, final.get(partner.ticker))

    # ---------- scheduled events between earnings reports ----------
    def _new_company_events(self, s):
        """Plan a company's next quarter of events (about 1.5 on average, `company_events_per_quarter`): a guidance
        update, an investor day, an analyst call or a product event, each at a quiet moment of the public calendar and
        well away from the company's own earnings report. Only what and when is public, never how it will go."""
        mean = float(self.settings.get("company_events_per_quarter", 1.5))
        if mean <= 0:
            return []
        q = self._quarter_seconds()
        count = int(mean) + (1 if random.random() < mean - int(mean) else 0)
        taken = sorted(ev["t"] for x in self.stocks.values() for ev in x.events)
        away = min(0.03 * q, MARKET_DAY_SECONDS)                       # keep clear of the company's own report
        kinds = random.sample(newsgen.COMPANY_EVENTS, min(count, len(newsgen.COMPANY_EVENTS)))
        events = []
        for kind in kinds:
            best, best_gap = None, -1.0
            for _ in range(12):
                c = self.now + random.uniform(0.005, 0.97) * q
                if s.next_earn and abs(c - s.next_earn) < away:
                    continue
                i = bisect.bisect(taken, c)
                gap = min((abs(c - taken[j]) for j in (i - 1, i) if 0 <= j < len(taken)), default=q)
                if gap > best_gap:
                    best, best_gap = c, gap
            if best is not None:
                bisect.insort(taken, best)
                events.append({"t": best, "kind": kind["key"]})
        return sorted(events, key=lambda ev: ev["t"])

    def _company_events(self):
        for s in list(self.stocks.values()):
            if not s.events or self.now < s.events[0]["t"]:
                continue
            ev = s.events.pop(0)
            self._fire_company_event(s, ev["kind"])
            if not s.events and s.next_earn:
                s.events = self._new_company_events(s)                 # plan the next quarter once this one is used up

    def _fire_company_event(self, s, key):
        kind = newsgen.COMPANY_EVENT_KEYS[key]
        eff = self._eff_mood("company", s.sector, s)
        p_pos = _clamp(0.5 + 0.25 * (s.safety - 0.5) + 0.25 * eff, 0.15, 0.85)
        sign = 1 if random.random() < p_pos else -1
        scale = 2 * (1 - (p_pos if sign > 0 else 1 - p_pos))           # the likelier outcome moves the price less
        ctx = self._persona_ctx(s)
        options = [t for t in (newsgen.fill(x, ctx) for x in (kind["texts_up"] if sign > 0 else kind["texts_down"])) if t]
        if not options:
            return
        headline = random.choice(options)
        k = random.uniform(0.7, 1.3)
        effect = {"t": self.now, "text": headline, "why": kind["why"], "dm": kind["dm"] * sign * k,
                  "dr": kind["dr"] * sign * k, "dd": 0.0}
        strength = random.choices(["weak", "strong"], weights=[0.7, 0.3])[0]
        tpl = {"scope": "company", "ticker": s.ticker, "rumor": False, "betas": {"self": 1.0},
               "up": [headline], "down": [headline], "paraphrase": False}
        s.pending.append(effect)
        move = self._spawn_event(tpl, s.ticker, sign, strength, scale, issue=effect)
        self._scale_effect(effect, move)

    def _earnings(self):
        for s in self.stocks.values():
            if s.next_earn and self.now >= s.next_earn:
                self._reschedule_earnings(s)                       # the next quarter
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
        # Only announced stories and zero-mean noise change the numbers. There is no built-in growth or
        # margin reversion: those would be predictable earnings changes the price does not already contain.
        margin_before = s.margin
        s.margin += dm * max(abs(s.margin), 0.06) + noise_m
        s.revenue *= 1 + dr + noise_r
        s.debt *= 1 + dd
        ds = sum(e.get("ds", 0.0) for e in causes)              # buybacks and offerings change the share count
        if ds:
            market_cap = s.shares_outstanding * s.price
            s.share_adj *= 1 + ds
            s.rescale()
            s.cash += ds * market_cap                            # an offering brings cash in, a buyback pays it out
        s.cash += s.revenue * s.margin * 0.12
        if s.cash < 0:
            s.debt += -s.cash
            s.cash = 0.0
        # the price reacts to the unannounced change in net income, so the P/E stays steady
        surprise = _clamp(noise_m / max(abs(margin_before), 0.06) + noise_r, -0.06, 0.06)
        rev_chg = s.revenue / old_rev - 1 if old_rev else 0.0
        earnings = s.revenue * s.margin
        eps = earnings / s.shares_outstanding if s.shares_outstanding > 0 else None
        # a quarter holds many stories: name the biggest three and say how many more there were
        causes.sort(key=lambda c: -(abs(c["dm"]) + abs(c["dr"]) + 0.3 * abs(c["dd"])))
        named = []
        for c in causes:
            if c["why"] not in named:
                named.append(c["why"])
            if len(named) == 3:
                break
        extra = len(causes) - len(named)
        driver = ("Driven by " + "; ".join(named) + (f" and {extra} smaller developments" if extra > 0 else "") + "."
                  if causes else "")
        tone = 1 if surprise > 0.004 else -1 if surprise < -0.004 else 0
        quote = newsgen.fill(random.choice(newsgen.EARNINGS_QUOTES[tone]), self._persona_ctx(s))
        text = (f"EARNINGS: {s.name} reports revenue of {self._money(s.revenue)} ({rev_chg * 100:+.1f}%) "
                f"and a net margin of {s.margin * 100:.1f}%." + (f" {driver}" if driver else "")
                + (f" {quote}." if quote else ""))
        if s.base_dps > 0 and self.settings.get("dividends_enabled", True):   # the switch is for experiments
            old_dps = s.dps
            new_dps = round(s.base_dps * _clamp(s.margin / s.base_margin, 0, 1.5), 4) \
                if s.margin > 0 and s.base_margin > 0 else 0.0
            if new_dps > 0:
                s.div = {"t": self.now + 300, "amt": new_dps}
                verb = "raises" if new_dps > old_dps * 1.02 else "cuts" if new_dps < old_dps * 0.98 else "maintains"
                when = "in 5 minutes" if self._open or self._phase == "pre" else "when the market next opens"
                text += f" It {verb} its dividend to {new_dps:.4f} MB per share, going ex-dividend {when}."
            else:
                s.div = None
                text += " It suspends its dividend."
            s.dps = new_dps
        self.news("earnings", text, [s.ticker], 1 if surprise > 0 else -1 if surprise < 0 else 0, "weak")
        self._queue({s.ticker: surprise})
        s.reports.append({"t": self.now, "revenue": s.revenue, "rev_chg": rev_chg, "margin": s.margin,
                          "margin_chg": s.margin - old_margin, "net_income": earnings, "eps": eps,
                          "beat": surprise >= 0, "causes": [{"t": c["t"], "text": c["text"]} for c in causes[:6]],
                          "n_causes": len(causes)})

    def _dividends(self):
        """On the ex-date holders receive the dividend from the house (shorts pay it) and the price drops by
        the same amount, so owning a stock through an ex-date has no expected gain or loss."""
        for s in self.stocks.values():
            if not s.div or self.now < s.div["t"]:
                continue
            price = s.price
            amt = min(s.div["amt"], price * 0.2)
            s.div = None
            if amt <= 0 or price <= 0:
                continue
            for p in self.players.values():
                sh = p.hold.get(s.ticker, 0.0)
                if sh > 0:
                    pay = sh * amt
                    p.cash += pay
                    self.house -= pay
                    p.divs[s.ticker] = p.divs.get(s.ticker, 0.0) + pay
                    self._emit("dividend", p, s.ticker, shares=0.0, price=amt, cash=pay, house=-pay, notional=pay)
                    self._on_dividend(p, pay)
                elif sh < 0:
                    owed = min(p.cash, -sh * amt)
                    p.cash -= owed
                    self.house += owed
                    p.divs[s.ticker] = p.divs.get(s.ticker, 0.0) - owed
                    self._emit("dividend", p, s.ticker, shares=0.0, price=amt, cash=-owed, house=owed, notional=owed)
            self._paper_dividend(s.ticker, amt)
            factor = 1 - amt / price
            s.fair *= factor
            s.fair_open *= factor
            self._div_today[s.ticker] = amt / price      # indices and ETFs add this back (see _update_index_level)
            self.news("dividend", f"{s.name} goes ex-dividend: {amt:.4f} MB per share is paid to holders and the "
                                  f"price adjusts.", [s.ticker], 0, "bystander")

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
            if random.random() < 0.4:               # a reason, about two notes in five
                why = self._review_reason(stock, direction < 0)
                headline = f"{bank} {word} price target on {stock.name} to {pt:.2f} MB, citing {why}"
            else:
                headline = random.choice([f"{bank} {word} price target on {stock.name} to {pt:.2f} MB",
                                          f"{bank} {word} its price target for {stock.name} to {pt:.2f} MB"])
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
            members = [s for s in self.stocks.values() if s.sector == sector_id and s.asset_type != "index"]
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
        scale = float(self.settings.get("relation_spillover", 1.0))
        if scale > 0:                              # suppliers, customers and rivals move each other a little
            for tk, r in self.relations.spill(source_returns, scale).items():
                if tk in self.stocks:
                    linked[tk] = linked.get(tk, 0.0) + r
        return linked

    def _sample_curves(self):
        """Once a minute, note each human player's equity (for the portfolio chart). Kept for a day in memory and
        in the ledger, so it survives restarts."""
        if self.now - self._curve_t < 60:
            return
        self._curve_t = self.now
        for p in self.players.values():
            eq = self.equity(p)
            p.curve.append([self.now, eq, p.cash])
            if self.ledger is not None:
                self.ledger.add_curve(p.token, self.now, eq, p.cash)

    def _tick_ledger(self):
        if self.ledger is None:
            return
        if self.now - self._borrow_flush_t >= 10:
            self._flush_borrow()
        self.ledger.flush()

    # ---------- trading sessions: pre-market, open, after-hours ----------
    def _session_lengths(self):
        pre = max(0.0, float(self.settings.get("premarket_seconds", 300)))
        post = max(0.0, float(self.settings.get("aftermarket_seconds", 300)))
        if pre + post > MARKET_DAY_SECONDS - 60:       # always leave at least a minute of regular trading
            scale = (MARKET_DAY_SECONDS - 60) / (pre + post)
            pre, post = pre * scale, post * scale
        return pre, post

    def market_phase(self, now=None):
        """Where we are in the 30-minute cycle, on the real clock (so it is the same for everyone):
        pre-market in the first `premarket_seconds` (5 minutes: 00:00-00:05), the regular session next
        (00:05-00:25) and after-hours in the last `aftermarket_seconds` (00:25-00:30). With both set to 0 there
        are no sessions and the market is simply always open."""
        now = self.now if now is None else now
        pre, post = self._session_lengths()
        if pre <= 0 and post <= 0:
            return "open"
        phase = now % MARKET_DAY_SECONDS
        if phase < pre:
            return "pre"
        if phase >= MARKET_DAY_SECONDS - post:
            return "after"
        return "open"

    def _update_session(self):
        self._prev_phase = self._phase
        self._phase = self.market_phase()
        self._open = self._phase == "open"

    def session(self):
        """For the page: the phase, whether the regular session is on, and the time until the next phase."""
        pre, post = self._session_lengths()
        if pre <= 0 and post <= 0:
            return {"phase": "open", "open": True, "next": None, "changes_in": None, "pre": 0, "after": 0,
                    "cycle": MARKET_DAY_SECONDS}
        phase = self.now % MARKET_DAY_SECONDS
        name = self.market_phase()
        if name == "pre":
            nxt, left = "open", pre - phase
        elif name == "open":
            nxt, left = ("after", MARKET_DAY_SECONDS - post - phase) if post > 0 else ("pre", MARKET_DAY_SECONDS - phase)
        else:
            nxt, left = ("pre", MARKET_DAY_SECONDS - phase) if pre > 0 else ("open", MARKET_DAY_SECONDS - phase)
        out = {"phase": name, "open": name == "open", "next": nxt, "changes_in": int(left) + 1,
               "pre": int(pre), "after": int(post), "cycle": MARKET_DAY_SECONDS}
        return out

    def _session_norm(self):
        """The regular session's volume profile spends the day's volatility budget unevenly (a burst at the open,
        a smaller one into the close, calmer in between), but the day as a whole must keep the stock's annual
        volatility. This constant scales the regular-session profile so that, over a whole 30-minute cycle, the
        variance (pre-market + regular session + after-hours + the opening jump) adds up to exactly one normal day."""
        pre, post = self._session_lengths()
        k = (pre, post, self._extended_noise(), self._open_burst(), self._close_burst(), self._open_jump_ticks(),
             self.settings.get("open_burst_seconds", 150), self.settings.get("close_burst_seconds", 120))
        if k not in self._norm_cache:
            n = int(MARKET_DAY_SECONDS - pre - post)
            shape = sum(self._shape(t, n) ** 2 for t in range(n))
            target = MARKET_DAY_SECONDS - (pre + post) * self._extended_noise() ** 2 - self._open_jump_ticks()
            self._norm_cache[k] = math.sqrt(max(target, 0.25 * n) / shape) if shape > 0 else 1.0
        return self._norm_cache[k]

    def _extended_noise(self):
        return float(self.settings.get("extended_noise", 0.35))

    def _open_burst(self):
        return float(self.settings.get("open_burst", 2.5))

    def _close_burst(self):
        return float(self.settings.get("close_burst", 1.5))

    def _open_jump_ticks(self):
        """Size of the opening jump, in seconds' worth of normal noise (90 means a jump about as big as a minute
        and a half of ordinary trading)."""
        return float(self.settings.get("open_jump_seconds", 90))

    def _shape(self, t, n):
        """Raw volume profile of the regular session, t seconds in (of n): a burst at the open that fades, and a
        smaller one into the close. 1.0 is a normal stretch."""
        o = float(self.settings.get("open_burst_seconds", 150))
        c = float(self.settings.get("close_burst_seconds", 120))
        return (1.0 + (self._open_burst() - 1.0) * math.exp(-t / max(o, 1e-9))
                + (self._close_burst() - 1.0) * math.exp(-(n - t) / max(c, 1e-9)))

    def _mult_at(self, phase):
        """The noise multiplier `phase` seconds into the 30-minute cycle."""
        pre, post = self._session_lengths()
        if pre <= 0 and post <= 0:
            return 1.0
        if phase < pre or phase >= MARKET_DAY_SECONDS - post:
            return self._extended_noise()           # thin trading before and after the regular session
        n = int(MARKET_DAY_SECONDS - pre - post)
        t = max(0.0, min(n - 1.0, phase - pre))
        return self._shape(t, n) * self._session_norm()

    def _session_mult(self):
        """How big this second's ordinary noise is, compared with a normal second. Known in advance and the same
        for up and down, so it changes how much prices move, never which way."""
        return self._mult_at(self.now % MARKET_DAY_SECONDS)

    def _opening_tick(self):
        pre, post = self._session_lengths()
        return (pre > 0 or post > 0) and self._phase == "open" and self._prev_phase not in (None, "open")

    def _flush_moves(self):
        pending, self._pending = self._pending, {}
        own = dict(pending)                            # each company's own moves, before the spillovers below
        self._queue(pending)
        self._queue(self._dependency_returns(pending))
        pending, self._pending = self._pending, {}
        cap = float(self.settings.get("daily_move_cap", 0.15))
        scale = self._noise_scale()
        for tk, r in pending.items():
            s = self.stocks[tk]
            r = max(-MAX_TICK_MOVE, min(MAX_TICK_MOVE, r))
            if cap > 0:
                r *= self._envelope_damping(s, cap)
            s.move(r)
            # The surprise is measured on the company's own move, before the daily brake and before the spillovers
            # from its partners and rivals. Measured after the brake, its 5% or so of shrinkage looked like calm and
            # the multiplier slid to its floor (ordinary stocks ran at about 0.6 of their stated volatility); and
            # the spillovers add a little more than the noise the multiplier is measured against.
            self._update_volatility(s, max(-MAX_TICK_MOVE, min(MAX_TICK_MOVE, own.get(tk, 0.0))), scale)

    def _anchor_volatility(self):
        """Keeps the average volatility multiplier of ordinary stocks at 1, so a stock's stated volatility is its
        real one. The multiplier is very sensitive: news adds a little more than the noise it is measured against,
        and with a half-life of a game day that small excess lifted the average to about 1.3 (before the daily brake's
        shrinkage was taken out of the measure it sank to about 0.6). One common factor, the same for every stock and
        known in advance, pulls the average back by 0.2% of the gap each second (a time constant of about eight minutes):
        slow enough that a market-wide storm still lasts several minutes, fast enough to cancel the bias, and
        individual storms and calms stay. Moonshots are left alone: their catalysts are meant to leave them jumpy."""
        if float(self.settings.get("vol_cluster_k", 0.01)) <= 0:
            return
        ordinary = [s for s in self.stocks.values() if s.asset_type != "index" and not s.moonshot]
        if not ordinary:
            return
        mean = sum(s.volm for s in ordinary) / len(ordinary)
        if mean <= 0:
            return
        factor = mean ** -0.002
        for s in ordinary:
            s.volm = _clamp(s.volm * factor, 0.5, 3.0)

    def _noise_scale(self):
        """How big this second's moves are expected to be, in units of a normal second: the session factor, and on
        the first second of the regular session the opening jump on top of it. Used to measure surprises (§6.7)."""
        scale = self._session_mult()
        if self._opening_tick():
            scale = math.sqrt(scale * scale + self._open_jump_ticks())
        return max(scale, 0.05)

    def _envelope_damping(self, s, cap):
        """Soft daily limit: every move is scaled by 1 / (1 + (x / L)^4), where x is how far the stock has already
        moved today and L is its daily limit (about 2.5 daily sigmas, at most `daily_move_cap`).

        The factor looks only at where the price is now, never at the direction of the move, so up and down moves
        are shrunk equally and the expected move stays exactly zero. (The hard clamp this replaced stopped
        further falls near the day's lower limit but not further rises: a reflecting wall that made dips bounce,
        which a dip-buying strategy farmed for about +2.7% over two hours.)"""
        limit = self._daily_sigma(s) * (1.5 + 0.75 * min(abs(s.beta), 2.0))
        if not s.moonshot:
            limit = min(cap, limit)
        limit *= s.limit_mult                    # moonshots may move hundreds of per cent in a day
        if self.now < s.boost_until:     # a major event is under way: the brake is much looser for a few minutes
            limit *= float(self.settings.get("major_event_limit_boost", 2.5))
        if limit <= 0 or s.fair <= 0 or s.fair_open <= 0:
            return 1.0
        x = abs(math.log(s.fair / s.fair_open))
        return 1.0 / (1.0 + (x / limit) ** 4)

    def _archive_stock(self, stock, reason, price):
        """Remember a stock that is leaving the market, so its page and chart can still be opened from the history
        page: what it was, its last numbers, its news and its candles (the most recent of each timeframe)."""
        keep = {k: [[round(x, 5) if i else x for i, x in enumerate(c)] for c in list(stock.tf[k])[-240:]]
                for k in ("1m", "5m", "30m", "1h", "1d") if k in stock.tf}
        p = stock.persona or {}
        self.archive[stock.ticker] = {
            "ticker": stock.ticker, "name": stock.name, "desc": stock.desc, "sector": stock.sector,
            "asset_type": stock.asset_type, "reason": reason, "delisted_at": self.now, "final_price": round(price, 6),
            "beta": stock.beta, "vol": stock.vol, "rating": stock.rating,
            "financials": {"revenue": stock.revenue, "margin": stock.margin, "cash": stock.cash, "debt": stock.debt,
                           "shares_outstanding": stock.shares_outstanding},
            "persona": {"ceo": p.get("ceo"), "cfo": p.get("cfo"), "product": p.get("product"), "city": p.get("city"),
                        "former_ceos": list(p.get("ex_ceos", []))},
            "log": list(stock.log)[-40:], "reports": [dict(r, causes=list(r.get("causes", []))) for r in list(stock.reports)[-6:]],
            "tf": keep}
        while len(self.archive) > ARCHIVE_MAX:
            self.archive.pop(min(self.archive, key=lambda k: self.archive[k]["delisted_at"]))

    def _distress_terms(self, stock):
        """(chance of bankruptcy, share of the price holders get back if it happens, price jump if it is rescued).
        The three are tied together so the bet is fair: q * payout + (1 - q) * (1 + jump) = 1. Holders and shorts
        then have no expected gain or loss from the event, so nobody can profit by buying or shorting a stock that
        is about to be resolved one way or the other."""
        if stock.moonshot:
            q = float(self.settings.get("moonshot_bankruptcy_chance", 0.6))
            b = float(self.settings.get("moonshot_bankruptcy_payout", 0.03))
        else:
            q = float(self.settings.get("bankruptcy_chance", 0.5))
            b = float(self.settings.get("bankruptcy_payout", 0.25))
        q = _clamp(q, 0.0, 0.99)
        return q, b, (1 - q * b) / (1 - q) - 1

    def _check_distress(self):
        """A company whose price falls below `distress_price_ratio` (25%) of its reference is resolved once: it is
        either rescued (the price jumps) or goes bankrupt (holders are paid a fraction of the price and it is
        delisted). See `_distress_terms`: the two outcomes are balanced so the event is a fair bet."""
        threshold = float(self.settings.get("distress_price_ratio", 0.25))
        for ticker, stock in list(self.stocks.items()):
            if stock.asset_type == "index":
                continue
            ratio = stock.fair / stock.initial_price
            if stock.distress_checked:
                if ratio > 1.25 * threshold:                 # it climbed clear of the line: the next fall is a new episode
                    stock.distress_checked = False
                    continue
                if ratio >= threshold / 4:
                    continue
                # A rescue that left it far below the line and it then kept falling (a rescue is a doubling now, not a
                # ten-fold jump, so this can happen): it is resolved again instead of sliding towards zero for good.
            elif ratio > threshold:
                continue
            stock.distress_checked = True
            q, payout, rescue = self._distress_terms(stock)
            if ratio < 1e-3:
                q = 1.0                                       # worth next to nothing: it simply fails (no rescue to speak of)
            if random.random() >= q:
                stock.move(rescue)
                stock.rating = "B" if stock.rating not in ("D", "C", "CC", "CCC") else stock.rating
                self.news("bailout", random.choice([
                    f"A surprise investor rescues {stock.name}: shares soar.",
                    f"Emergency financing saves {stock.name} from collapse; the shares rocket.",
                    f"{stock.name} strikes a last-minute lifeline deal and the stock rebounds."]),
                    [ticker], 1, "very strong")
                continue
            # Bankruptcy: holders are cashed out at a fraction of the price (no fee), shorts close at that price,
            # the remaining pool liquidity returns to the house reserve and the ticker is delisted for good.
            stock.move(-(1 - payout))
            for player in self.players.values():
                sh = player.hold.pop(ticker, 0.0)
                short_cost = player.cost.pop(ticker, 0.0)
                player.entry_fee.pop(ticker, None)
                if sh > 0:
                    pay = sh * stock.price
                    player.cash += pay
                    self.house -= pay
                    self._emit("delist_payout", player, ticker, shares=-sh, price=stock.price, cash=pay,
                               house=-pay, notional=pay)
                elif sh < 0:  # a short closes at the bankruptcy price: collateral back, less what the price did
                    cd, short = self._short_payout(player, short_cost, -sh * stock.price, 0.0)
                    self.short_shortfall += short
                    player.cash += cd
                    self.house -= cd
                    self._emit("delist_payout", player, ticker, shares=-sh, price=stock.price, cash=cd, house=-cd,
                               notional=abs(cd), shortfall=short)
            self._paper_delist(ticker, stock.price)
            self.house += stock.T
            self._emit("delist", None, ticker, house=stock.T)
            self._archive_stock(stock, "bankruptcy", stock.price)
            self.delisted.append(ticker)
            self.stocks.pop(ticker)
            self.relations.remove(ticker)
            self.index_prev.pop(ticker, None)
            headline = f"{stock.name} files for bankruptcy and is delisted; holders are paid out at the last price."
            self.news("bankruptcy", headline, [ticker], -1, "very strong")
            self.archive[ticker]["log"].append({"t": self.now, "kind": "bankruptcy", "text": headline})

    # ---------- rare news that moves a stock a lot ----------
    def _catalysts(self):
        """About every 8 minutes one company gets a catalyst: a trial result, an approval, a buyout offer, an audit,
        a test flight. It moves the price a lot, whatever the stock's beta. Every catalyst is a fair bet: the good
        outcome's chance times its gain equals the bad outcomes' chances times their losses, so the expected move is
        exactly zero and there is nothing to gain by guessing. A moonshot gets a two-outcome bet (newsgen.CATALYSTS), an
        ordinary company a three-outcome one in which a big fall is rare (newsgen.CATALYST_TIERS)."""
        if self.now < self.next_catalyst:
            return
        self.next_catalyst = self.now + random.expovariate(1 / float(self.settings.get("catalyst_mean_seconds", 480)))
        pool = [x for x in self.stocks.values() if x.asset_type == "equity" and x.persona]
        if not pool:
            return
        moon_w = float(self.settings.get("catalyst_moonshot_weight", 10.0))
        s = random.choices(pool, weights=[moon_w if x.moonshot else 1.0 for x in pool])[0]
        kinds = [k for k in newsgen.CATALYSTS if k["sectors"] is None or s.sector in k["sectors"]]
        kind = random.choices(kinds, weights=[k["weight"] for k in kinds])[0]
        ctx = self._persona_ctx(s)
        if s.moonshot:                                             # a lottery ticket: a good outcome or a collapse
            p = kind["p"]
            lo, hi = kind["up_moon"]
            shrink = float(self.settings.get("catalyst_moonshot_scale", 0.7))   # (a moonshot's upside is trimmed: see the tail notes)
            lo, hi = lo * shrink, hi * shrink
            up = min(random.uniform(lo, hi), 0.95 * (1 - p) / p)   # the loss may never take more than 95%
            down = -p * up / (1 - p)
            good = random.random() < p
            texts = kind["texts_up"] if good else kind["texts_down"]
            r = up if good else down
        else:
            r, good, texts = self._ordinary_catalyst(kind)
        options = [t for t in (newsgen.fill(x, ctx) for x in texts) if t]
        if not options:
            return
        s.move(r)
        self._update_volatility(s, r)                              # a huge move makes the stock jumpier for a while
        self._queue(self._dependency_returns({s.ticker: r}))       # its suppliers, customers and rivals feel it a little
        self.news("breaking", "BREAKING: " + random.choice(options), [s.ticker], 1 if good else -1, "very strong")

    def _ordinary_catalyst(self, kind):
        """The outcome of a catalyst for an ordinary company: (move, was it good news, the headlines to pick from). Three
        outcomes (newsgen.CATALYST_TIERS): the good news, a small setback, and, rarely, a disaster. The disaster and the
        setback are drawn first and the gain is then worked out so that the expected move is exactly zero."""
        t = newsgen.CATALYST_TIERS[kind["key"]]
        bad = random.uniform(*t["bad"])
        dis = random.uniform(*t["dis"])
        up = (t["p_bad"] * bad + t["p_dis"] * dis) / t["p_good"]
        roll = random.random()
        if roll < t["p_good"]:
            return up, True, kind["texts_up"]
        if roll < t["p_good"] + t["p_bad"]:
            return -bad, False, t["texts_bad"]
        return -dis, False, t["texts_dis"]

    # ---------- industry-wide shocks ----------
    def _sector_shocks(self):
        """About every 10 minutes a whole industry gets news that moves every company in it the same way: a ban, a
        collapse in demand, a probe, a disruptive technology (or the good version of each). It has no market
        component, so a sector can crash while the market rises."""
        if self.now < self.next_sector_shock:
            return
        self.next_sector_shock = self.now + random.expovariate(1 / float(self.settings.get("sector_shock_mean_seconds", 600)))
        self._sector_shock()

    def _sector_shock(self, sector=None, kind=None, good=None):
        """One industry-wide shock (the arguments let a test pick the sector, the kind and the outcome).

        A fair two-outcome bet (see newsgen.INDUSTRY_SHOCKS): the failure has probability 1 - p and size `bad`, the
        good outcome has probability p and size (1 - p) * bad / p, so the expected move is exactly zero. Each company
        moves by that size times its own exposure, 0.7 to 1.3, drawn without regard to the direction, so the average
        stays zero for every company too. Like a catalyst it is applied straight to the price; the usual spillovers
        (company and sector links) follow through the normal flush."""
        by_sector = {}
        for s in self.stocks.values():
            if s.asset_type == "equity" and s.sector in self.sectors:
                by_sector.setdefault(s.sector, []).append(s)
        if sector is None:
            pool = [sid for sid, m in by_sector.items() if len(m) >= 2]
            if not pool:
                return None
            sector = random.choice(pool)
        members = by_sector.get(sector, [])
        if not members:
            return None
        spec = kind if isinstance(kind, dict) else None
        if spec is None:
            spec = (next((k for k in newsgen.INDUSTRY_SHOCKS if k["key"] == kind), None) if kind
                    else random.choices(newsgen.INDUSTRY_SHOCKS, weights=[k["weight"] for k in newsgen.INDUSTRY_SHOCKS])[0])
        p = spec["p"]
        bad = random.uniform(*spec["bad"]) * float(self.settings.get("sector_shock_size", 1.0))
        up = (1 - p) * bad / p
        if good is None:
            good = random.random() < p
        size = up if good else -bad
        moves = {}
        for s in members:
            r = max(-0.95, random.uniform(0.7, 1.3) * size)
            moves[s.ticker] = r
            s.move(r)
            self._update_volatility(s, r)
        self._queue(self._dependency_returns(moves))
        name = self.sectors[sector]["name"]
        text = random.choice(spec["texts_up"] if good else spec["texts_down"]).format(sector=name)
        ranked = [s.ticker for s in sorted(members, key=lambda x: -x.base)]
        self.news("industry", "INDUSTRY ALERT: " + text, ranked, 1 if good else -1, "very strong")
        logged = self.news_log[-1]
        for tk in ranked[4:]:                    # every company in the sector keeps the headline in its own log
            self.stocks[tk].log.append({"t": self.now, "kind": "industry", "text": logged["text"]})
        return sector, size

    # ---------- share offerings ----------
    @staticmethod
    def _shares_text(billions):
        """A share count (held in billions) as people write it: '12.3 million' or '1.27 billion'."""
        return f"{billions:.2f} billion" if billions >= 1.0 else f"{billions * 1000:.1f} million"

    def _offerings(self):
        """About every 20 minutes a company announces a public offering of new shares, and a few minutes later the
        shares are issued. The only thing that changes is the number of shares outstanding in the stock's info (and
        so its market cap and earnings per share): no price move, no cash, no change in the financials. A stock's
        price is a fair bet and an offering is not news about the business, so there is nothing to trade on."""
        for s in self.stocks.values():
            o = s.offering
            if o and self.now >= o["t"]:
                s.offering = None
                s.share_adj *= 1 + o["pct"]
                s.rescale()
                self.news("offering", f"{s.name} completes its share offering: shares outstanding rise to "
                                      f"{self._shares_text(s.shares_outstanding)}.", [s.ticker])
        if self.now < self.next_offering:
            return
        self.next_offering = self.now + random.expovariate(1 / float(self.settings.get("offering_mean_seconds", 1200)))
        pool = [s for s in self.stocks.values() if s.asset_type == "equity" and s.revenue > 0 and not s.offering]
        if not pool:
            return
        s = random.choice(pool)
        pct = random.uniform(0.01, 0.04)
        delay = float(self.settings.get("offering_delay_seconds", 300))
        s.offering = {"t": self.now + delay, "pct": pct}
        self.news("offering", f"{s.name} announces a public offering of {self._shares_text(pct * s.shares_outstanding)} "
                              f"new shares ({pct * 100:.1f}% of its shares outstanding), to settle in about "
                              f"{max(1, round(delay / 60))} minutes.", [s.ticker])

    # ---------- moonshots: tiny, wild companies that keep joining the market ----------
    def _list_moonshot(self, initial):
        taken = set(self.stocks) | set(self.delisted) | set(self.derived)
        cfg = newsgen.make_moonshot(random, taken, set(self.sectors))
        self._list(cfg, initial)

    def _moonshot_ipos(self):
        """A new moonshot lists every ~15 minutes while fewer than `moonshot_max` are trading, so the bankrupt ones
        are replaced. Nothing about an IPO is predictable: it lists at its reference price with no first-day pop."""
        if self.now < self.next_moonshot:
            return
        self.next_moonshot = self.now + random.expovariate(1 / float(self.settings.get("moonshot_mean_seconds", 900)))
        if sum(1 for x in self.stocks.values() if x.moonshot) < int(self.settings.get("moonshot_max", 8)):
            self._list_moonshot(initial=False)
            self._assign_personas()

    # ---------- orders: limit, stop-loss and take-profit ----------
    ORDER_KINDS = {"limit_buy": "Limit buy", "limit_sell": "Limit sell", "stop_loss": "Stop-loss",
                   "take_profit": "Take-profit"}

    def _order_view(self, o):
        return {"id": o["id"], "ticker": o["ticker"], "kind": o["kind"], "label": self.ORDER_KINDS[o["kind"]],
                "side": o["side"], "cond": o["cond"], "trigger": o["trigger"], "pct": o.get("pct"),
                "amount": o.get("amount"), "created": o["created"], "expires": o["expires"], "oco": o.get("oco")}

    def place_order(self, p, ticker, kind, trigger, pct=None, amount=None, oco=None):
        """Leave an order that the server carries out for you. It is checked every second against the live price and,
        when the price crosses the trigger, it becomes an ordinary market trade at the price of that moment (not at the
        trigger, so a price that gaps through it fills at the new price). Orders never move a price and never change
        what a trade costs, so they are no more than a way of not having to watch the screen.

        limit_buy   buys when the price falls to the trigger or below (a bargain)
        limit_sell  sells (or shorts) when the price rises to the trigger or above
        stop_loss   closes your position when it moves against you to the trigger (needs a position)
        take_profit closes your position when it moves in your favour to the trigger (needs a position)"""
        gate = self.email_gate(p)
        if gate:
            return False, gate
        if kind not in self.ORDER_KINDS:
            return False, "Unknown order type"
        s = self.stocks.get(ticker)
        if s is None:
            return False, "Unknown ticker"
        if not (isinstance(trigger, (int, float)) and not isinstance(trigger, bool) and math.isfinite(trigger)
                and 0 < trigger < 1e9):
            return False, "Bad trigger price"
        close_only = kind in ("stop_loss", "take_profit")
        if amount is not None:
            if not (isinstance(amount, (int, float)) and not isinstance(amount, bool) and math.isfinite(amount)
                    and 0 < amount < 1e12):
                return False, "Bad amount"
            pct = None
        else:
            pct = 1.0 if pct is None and close_only else pct
            if not (isinstance(pct, (int, float)) and not isinstance(pct, bool) and math.isfinite(pct) and 0 < pct <= 1):
                return False, "Bad size"
        limit = int(self.settings.get("max_orders", 20))
        if len(p.orders) >= limit:
            return False, f"You can have at most {limit} open orders"
        if sum(1 for o in p.orders if o["ticker"] == ticker) >= 6:
            return False, f"You already have 6 open orders in {ticker}"
        price = s.price
        held = p.hold.get(ticker, 0.0)
        pos = 0
        if kind == "limit_buy":
            side, cond = "buy", "le"
            if trigger >= price:
                return False, f"A limit buy waits for the price to fall: {ticker} is at {price:.4g}, so the trigger must be lower (or just buy now)"
        elif kind == "limit_sell":
            side, cond = "sell", "ge"
            if trigger <= price:
                return False, f"A limit sell waits for the price to rise: {ticker} is at {price:.4g}, so the trigger must be higher (or just sell now)"
        else:
            if abs(held) < 1e-9:
                return False, f"A {self.ORDER_KINDS[kind].lower()} needs a position in {ticker}"
            pos = 1 if held > 0 else -1
            against = kind == "stop_loss"
            # a long loses when the price falls and gains when it rises; a short the other way round
            goes_down = (pos > 0) == against
            side = "sell" if pos > 0 else "buy"
            cond = "le" if goes_down else "ge"
            if (cond == "le" and trigger >= price) or (cond == "ge" and trigger <= price):
                way = "below" if cond == "le" else "above"
                return False, (f"For your {'long' if pos > 0 else 'short'} in {ticker} a {self.ORDER_KINDS[kind].lower()} "
                               f"must be {way} the current price of {price:.4g}")
        self.order_seq += 1
        order = {"id": self.order_seq, "ticker": ticker, "kind": kind, "side": side, "cond": cond,
                 "trigger": round(float(trigger), 8), "close_only": close_only, "pos": pos, "created": self.now,
                 "expires": self.now + float(self.settings.get("order_expiry_seconds", 7 * 86400)), "oco": oco}
        if pct is not None:
            order["pct"] = float(pct)
        else:
            order["amount"] = float(amount)
        p.orders.append(order)
        p.orders_dirty = True
        return True, f"{self.ORDER_KINDS[kind]} placed: {ticker} {'at or below' if cond == 'le' else 'at or above'} {trigger:.4g}"

    def place_bracket(self, p, ticker, take_profit, stop_loss):
        """A take-profit and a stop-loss on one position that cancel each other: whichever the price reaches first
        closes the position and removes the other."""
        held = p.hold.get(ticker, 0.0)
        if abs(held) < 1e-9:
            return False, f"You have no position in {ticker} to protect"
        self.order_seq += 1
        group = f"b{self.order_seq}"
        ok1, m1 = self.place_order(p, ticker, "take_profit", take_profit, pct=1.0, oco=group)
        if not ok1:
            return False, m1
        ok2, m2 = self.place_order(p, ticker, "stop_loss", stop_loss, pct=1.0, oco=group)
        if not ok2:
            p.orders = [o for o in p.orders if o.get("oco") != group]
            p.orders_dirty = True
            return False, m2
        return True, f"Bracket placed on {ticker}: take profit at {take_profit:.4g}, stop-loss at {stop_loss:.4g}"

    def cancel_order(self, p, order_id):
        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            return False, "No such order"
        order = next((o for o in p.orders if o["id"] == order_id), None)
        if order is None:
            return False, "No such order"
        self._drop_order(p, order)
        return True, f"Cancelled your {self.ORDER_KINDS[order['kind']].lower()} in {order['ticker']}"

    def _drop_order(self, p, order, why=None, filled=False):
        """Remove an order (and its bracket partner). `why` is told to the player unless they asked for it."""
        group = order.get("oco")
        p.orders = [o for o in p.orders if o is not order and not (group and o.get("oco") == group)]
        p.orders_dirty = True
        if why:
            self._notify(p, why)

    def _orders_tick(self):
        """Every second: carry out the orders whose trigger the price has reached."""
        for p in self.players.values():
            if not p.orders:
                continue
            for o in list(p.orders):
                if o not in p.orders:                     # a bracket partner that was just carried out
                    continue
                label = self.ORDER_KINDS[o["kind"]]
                s = self.stocks.get(o["ticker"])
                if s is None:
                    self._drop_order(p, o, f"{label} in {o['ticker']} cancelled: it is no longer traded.")
                    continue
                if self.now >= o["expires"]:
                    self._drop_order(p, o, f"{label} in {o['ticker']} expired without being triggered.")
                    continue
                hit = s.price <= o["trigger"] if o["cond"] == "le" else s.price >= o["trigger"]
                if not hit:
                    continue
                held = p.hold.get(o["ticker"], 0.0)
                if o["close_only"] and ((o["pos"] > 0 and held <= 1e-9) or (o["pos"] < 0 and held >= -1e-9)):
                    self._drop_order(p, o, f"{label} in {o['ticker']} cancelled: you no longer hold that position.")
                    continue
                ok, msg = self.trade(p, o["ticker"], o["side"], o.get("pct", 1.0), o.get("amount"))
                if not ok and msg.startswith("Cooldown"):
                    continue                              # you traded it a moment ago: try again next second
                if ok:
                    self._drop_order(p, o, f"{label} carried out: {msg}", filled=True)
                else:
                    self._drop_order(p, o, f"{label} in {o['ticker']} could not be carried out and was cancelled: {msg}")

    # ---------- helpers ----------
    def _ret(self, s, n=60):
        h = s.hist
        return h[-1] / h[-n] - 1 if len(h) >= n else 0.0

    # ---------- season / scoring ----------
    # Seasons are leaderboard periods only. Balances are real and are never reset.
    def season_return(self, p, equity=None):
        e = self.equity(p) if equity is None else equity
        return e / p.season_base - 1 if p.season_base > 1e-9 else 0.0

    @staticmethod
    def traded_today(p):
        """Has this player made a trade in the current day? (`trades` counts voluntary trades and is zeroed when a day
        ends; a margin call is not a trade.)"""
        return p.trades > 0

    @staticmethod
    def ever_traded(p):
        """Has this player ever made a trade? Someone who only joined and looked around has not."""
        return bool(p.trades > 0 or p.counters.get("trades", 0) > 0 or p.hold or p.realized)

    def _board(self):
        """The leaderboards list only people who have traded in the period the board covers: the day board those who
        traded today, the all-time board those who have ever traded. Joining and watching does not put you on a board,
        and a player who is on no board has no rank (`rank` is None)."""
        everyone, rows = [], []
        for p in self.players.values():
            e = self.equity(p)
            self._track_drawdown(p, e)
            row = {"name": p.name, "equity": e, "ret": self.season_return(p, e), "token": p.token}
            everyone.append(row)
            if self.traded_today(p):
                rows.append(row)
        rows.sort(key=lambda r: -r["ret"])
        self.board = rows
        self.rank = {r["token"]: i + 1 for i, r in enumerate(rows)}
        self._social_board(everyone)

    def _season_boundary(self):
        """When the current season ends. A season is one real day (`season_seconds`, 86400) and ends at midnight UTC,
        so it coincides with the daily tournament and the daily quests."""
        length = float(self.settings.get("season_seconds", 86400))
        return (math.floor(self.now / length) + 1) * length

    def _close_positions_at_market(self, p):
        """Close every position of a player at the market price, without fees, settling with the house (a long is
        paid out, a short gets its collateral back plus or minus what the price did). Used by a game reset and when
        the old house-funded bots are removed."""
        for tk, sh in list(p.hold.items()):
            s = self.stocks.get(tk)
            if s is None:
                continue
            if sh > 0:
                pay = sh * s.price
                p.cash += pay
                self.house -= pay
            else:
                cd, short = self._short_payout(p, p.cost.get(tk, 0.0), -sh * s.price, 0.0)
                self.short_shortfall += short
                p.cash += cd
                self.house -= cd
        p.hold, p.cost, p.entry_fee, p.last_trade = {}, {}, {}, {}

    def _retire_bots(self, bots):
        """A save from an older version has house-funded bots. They are removed: each one's positions are closed at the
        market price and everything it holds goes back to the house reserve, so no token is created or lost (the bots
        were funded by the house in the first place). Runs once, after the ledger has been replayed."""
        returned = 0.0
        for p in bots:
            p.orders = []
            self._close_positions_at_market(p)
            returned += p.cash
            self.house += p.cash
            p.cash = 0.0
            self.players.pop(p.token, None)
            self.by_token.pop(p.token, None)
        self._retired_bots = len(bots)
        logger.info("removed %d bots; %.2f MB went back to the house reserve", len(bots), returned)

    def reset_to_day_one(self):
        """Start the game over (admin only; the server backs everything up first). Every player goes
        back to the starting balance (`signup_bonus`) and Day 1: positions are closed at
        the market price without fees, orders are cancelled, the trade history, medals, achievements and the day
        history are cleared, and the money ledger starts again from the new balances. What stays: the market (prices,
        charts, listings, news), accounts (names, passwords, who follows whom, privacy) and the chat moderation record.

        The tokens balance the way they always do: closing a position settles it with the house, and setting a balance
        mints or burns the difference (`minted` moves with it), so nothing is created without being counted."""
        bonus = float(self.settings.get("signup_bonus", START_CASH))
        for p in self.players.values():
            self._close_positions_at_market(p)
            target = bonus
            delta = target - p.cash
            p.cash = target
            self.minted += delta
            p.deposited = p.season_base = target
            p.realized, p.divs, p.borrow = {}, {}, {}
            p.fees_paid, p.trades, p.margin_calls = 0.0, 0, 0
            p.log.clear()
            p.curve.clear()
            p.orders, p.orders_dirty = [], True
            p.notices.clear()
            social.reset_progress(p)
            self._notify(p, f"The game was reset: it is Day 1 again and everyone starts with {target:,.0f} MB.")
        self.season_no = 1
        self.history = []
        self.season_end = self._season_boundary()
        self.tournaments, self._sandboxes = [], {}
        self.tournament_history.clear()
        self.margin_log.clear()
        self.margin_calls = 0
        self.trades_total = 0
        self.chat_reports.clear()
        self._borrow_acc = {}                           # (borrow fees waiting for the ledger belong to the old game)
        if self.ledger is not None:
            self.ledger.clear()
            for p in self.players.values():
                self._emit("join", p)
                self._emit("credit", p, cash=p.cash, notional=p.cash)
        self._board()
        self._social_t = 0
        self.news("season", f"DAY 1 BEGINS. Everyone starts again with {bonus:,.0f} MB. Good luck.")
        self.save()

    def reset_with_backup(self, folder):
        """`reset_to_day_one`, after copying the save, the chart file and the ledger into `folder`."""
        os.makedirs(folder, exist_ok=True)
        self.save()                                      # so the copy holds the game exactly as it is now
        for path in (self.state_file, self._charts_path()):
            if path and os.path.exists(path):
                shutil.copy(path, folder)
        if self.ledger is not None:
            self.ledger.backup(os.path.join(folder, "ledger.db"))
        self.reset_to_day_one()
        return folder

    def _end_season(self):
        self._board()
        top = [(r["name"], round(r["ret"] * 100, 1)) for r in self.board[:5]]
        self.history.append({"season": self.season_no, "top": top})
        self.history = self.history[-10:]
        for p in self.players.values():
            p.season_base = self.equity(p)
            p.trades = 0
        self._end_season_social()
        winner = top[0] if top else ("nobody", 0)
        self.news("season", f"DAY {self.season_no} OVER. Winner: {winner[0]} ({winner[1]:+}%). "
                            "Balances carry over; a new leaderboard starts now.")
        self.season_no += 1
        self.season_end = self._season_boundary()

    # ---------- main tick ----------
    def tick(self, now=None):
        self.now = now if now is not None else time.time()
        if self._sig() != self.content_sig:
            self._reload()
        self._pending = {}
        self._update_session()
        self._mean_revert()
        self._random_market_moves()
        self._advance_regime()
        self._credit_reviews()
        self._mood_step()
        self._events()
        self._followups()
        self._issues()
        self._cross_stories()
        self._company_events()
        self._catalysts()
        self._sector_shocks()
        self._moonshot_ipos()
        self._offerings()
        self._earnings()
        self._flush_moves()
        self._anchor_volatility()
        if self._open:                          # ex-dividend dates and failures take effect at the open
            self._check_distress()
            self._dividends()
        self._borrow_fees()
        self._margin_calls()
        self._paper_tick()
        self._reserve_check()
        self._orders_tick()
        self._update_index()
        for s in self.stocks.values():
            if s.asset_type != "index":
                s.hist.append(s.price)
                self._record(s)
        self._update_index_level()
        for tk in self.derived:
            asset = self.stocks.get(tk)
            if asset:
                asset.hist.append(asset.price)
                self._record(asset)
        if self.now >= self.season_end:
            self._end_season()
        self._board()
        self._sample_series()
        self._sample_curves()
        self._public()
        self._social_tick()
        self._tick_ledger()

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
        """Move the market index and every derived asset by the returns of their constituents this tick."""
        equities = [(tk, st) for tk, st in self.stocks.items() if st.asset_type != "index"]
        # A dividend drops the stock's price by exactly the dividend. Indices and ETFs add that drop back, so they
        # track the *total* return of their constituents (like an accumulating fund); otherwise holding a "Dividend
        # Income ETF" would quietly lose the yield every time a member went ex-dividend.
        rets = {tk: st.price / self.index_prev.get(tk, st.price) / (1 - self._div_today.get(tk, 0.0)) - 1
                for tk, st in equities}
        self._div_today = {}
        total_weight = sum(st.base for _, st in equities)
        market = 0.0
        if total_weight:
            market = sum(st.base * rets[tk] for tk, st in equities) / total_weight
            self.index_level *= max(0.001, 1 + market)
        dret = {"MSI": market}
        for tk, spec in self.derived.items():
            st = self.stocks.get(tk)
            if not st or spec["kind"] in ("market", "leveraged"):
                continue
            if spec["kind"] == "sector":
                members = [(k, x) for k, x in equities if x.sector == spec["sector"]]
                weight = sum(x.base for _, x in members)
                r = sum(x.base * rets[k] for k, x in members) / weight if weight else 0.0
            else:
                members = [(k, x) for k, x in equities if k in spec.get("members", [])]
                r = sum(rets[k] for k, _ in members) / len(members) if members else 0.0
            dret[tk] = r
            st.fair = max(1e-6, st.fair * (1 + r))
        for tk, spec in self.derived.items():
            st = self.stocks.get(tk)
            if st and spec["kind"] == "leveraged":
                # a fixed multiple of the underlying's return every tick: a martingale like the underlying, but its
                # price decays in choppy markets because the multiple is reset each second
                r = float(spec.get("leverage", 1.0)) * dret.get(spec.get("of"), 0.0)
                dret[tk] = r
                st.fair = max(1e-6, st.fair * max(0.001, 1 + r))
        self._sync_index_asset()
        self.index_prev = {tk: st.price for tk, st in self.stocks.items()}
        self.index_hist.append(self.index_level)

    def _day_ref(self, s):
        """Price one game day ago, from the minute candles."""
        cutoff = self.now - MARKET_DAY_SECONDS
        for c in s.candles:
            if c[0] >= cutoff:
                return c[1]
        return s.hist[0] if s.hist else s.price

    def _public(self):
        """The public view of every asset, rebuilt once per tick. It is kept in three pieces so the wire protocol
        can send each at its own pace: static facts (name, sector, description) rarely change, slow numbers
        (financials, limits, rating) change now and then, and the fast numbers (price, change, sparkline) change
        every tick. `pub_stocks` is all three merged."""
        out, fast, slow, static = [], {}, {}, {}
        interest = self.short_interest_map()
        for s in self.stocks.values():
            ref = self._day_ref(s)
            display_price = round(s.price, 4)
            display_shares = round(s.shares_outstanding, 9)
            market_cap = display_shares * display_price
            earnings = s.revenue * s.margin
            st = {"ticker": s.ticker, "name": s.name, "desc": s.desc, "sector": s.sector,
                  "asset_type": s.asset_type, "beta": s.beta, "price_unit": s.price_unit,
                  "tracks": self._tracks(s), "vol": s.vol, "traits": s.traits, "listed_at": s.listed_at}
            util = interest.get(s.ticker, 0.0) / max(self.short_cap(s), 1e-9)
            fin = {} if s.asset_type == "index" else {
                "revenue": round(s.revenue, 6), "net_income": round(earnings, 6), "cash": round(s.cash, 6),
                "debt": round(s.debt, 6), "margin": round(s.margin, 6), "shares_outstanding": display_shares,
                "eps": round(earnings / s.shares_outstanding, 9) if s.shares_outstanding > 0 else None,
                "annual_dps": round(4 * s.dps, 9)}
            sl = {"rating": s.rating,
                  "margin_req": round(self.margin_req(s), 2),
                  "borrow_hour": round(2 * self.borrow_rate_day(s, util), 5),
                  "borrow_util": round(min(1.0, util), 3), "financials": fin}
            # the numbers that depend on the price are worked out here for the full picture; the page recomputes
            # them from the live price, so they never need to travel in the per-tick updates
            live_fin = {} if s.asset_type == "index" else {
                **fin, "market_cap": round(market_cap, 9),
                "dividend_yield": round(4 * s.dps / s.price, 4) if s.price > 0 else 0.0,
                "pe": round(market_cap / earnings, 6) if s.asset_type == "equity" and earnings > 0 else None}
            chg = round(s.price / ref - 1, 4)
            fast[s.ticker] = [display_price, chg]
            slow[s.ticker] = sl
            static[s.ticker] = st
            out.append({**st, **sl, "financials": live_fin,
                        "price": display_price, "chg": chg,
                        "spark": [round(x, 4) for x in itertools.islice(reversed(s.hist), 60)][::-1]})
        self.pub_fast, self.pub_slow, self.pub_static = fast, slow, static
        self.pub_px = {tk: v[0] for tk, v in fast.items()}
        self.pub_stocks = out
        index_ref = self.index_hist[0]
        self.pub_index = {"value": round(self.index_level, 3),
                          "chg": round(self.index_level / index_ref - 1, 4),
                          "spark": [round(x, 3) for x in self.index_hist]}
        self.sector_indices = {}
        for sector_id, sector in self.sectors.items():
            members = [s for s in self.stocks.values() if s.sector == sector_id and s.asset_type != "index"]
            weight = sum(s.base for s in members)
            level = 100 * sum(s.base * s.price / s.initial_price for s in members) / weight if weight else 100.0
            self.sector_indices[sector_id] = {"value": round(level, 2), "chg": round(level / 100 - 1, 4)}

    def chart_for(self, ticker, period):
        stock = self.stocks.get(ticker)
        if not stock and ticker in self.archive:
            tf = self.archive[ticker]["tf"]
            key = period if period in tf else next((k for k in ("1m", "5m", "30m", "1h", "1d") if k in tf), None)
            candles = [{"t": c[0], "o": c[1], "h": c[2], "l": c[3], "c": c[4]} for c in tf.get(key, [])]
            return {"type": "history", "ticker": ticker, "period": period, "candles": candles, "now": self.now,
                    "delisted": True}
        if not stock:
            return {"type": "history", "error": "Unknown or delisted stock"}
        key = period if period in TIMEFRAMES else "30s"  # legacy clients may still ask for day/week/...
        candles = [{"t": t, "o": o, "h": h, "l": l, "c": c} for t, o, h, l, c in stock.tf[key]]
        for candle in candles:
            for k in "ohlc":
                candle[k] = round(candle[k], 5)
        return {"type": "history", "ticker": ticker, "period": period, "candles": candles,
                "now": self.now}

    def _tracks(self, s):
        """What a derived asset follows, in words, for the stock page."""
        spec = getattr(s, "spec", None)
        if not spec:
            return None
        if spec["kind"] == "market":
            return "Every listed stock, weighted by company size"
        if spec["kind"] == "sector":
            return "All " + self.sectors.get(spec["sector"], {}).get("name", spec["sector"]) + " stocks, weighted by company size"
        if spec["kind"] == "basket":
            return "Equal weights in " + ", ".join(m for m in spec.get("members", []) if m in self.stocks)
        lev = float(spec.get("leverage", 1.0))
        return f"{lev:+g}x the daily moves of {spec.get('of')}, reset every second"

    def company_for(self, ticker):
        stock = self.stocks.get(ticker)
        if not stock and ticker in self.archive:
            a = self.archive[ticker]
            return {"type": "company", "ticker": ticker, "delisted": {k: a[k] for k in (
                "name", "desc", "sector", "asset_type", "reason", "delisted_at", "final_price", "beta", "vol", "rating",
                "financials")}, "persona": a["persona"], "log": list(a["log"])[::-1],
                "reports": [{**r, "causes": list(r["causes"])} for r in a["reports"][::-1]]}
        if not stock:
            return {"type": "company", "ticker": ticker, "error": "Unknown or delisted stock",
                    "delisted": ticker in self.delisted or ticker in WITHDRAWN_PRODUCTS}
        persona = None
        if stock.persona:
            p = stock.persona
            persona = {"ceo": p.get("ceo"), "cfo": p.get("cfo"), "product": p.get("product"), "city": p.get("city"),
                       "former_ceos": list(p.get("ex_ceos", []))}
        return {"type": "company", "ticker": ticker, "persona": persona, "log": list(stock.log)[::-1],
                "reports": [{**r, "causes": list(r["causes"])} for r in list(stock.reports)[::-1]]}

    def _upcoming_events(self):
        events = []
        for stock in self.stocks.values():
            if stock.next_earn:
                events.append({"ticker": stock.ticker, "name": stock.name, "kind": "Earnings",
                               "at": stock.next_earn, "in_seconds": max(0, int(stock.next_earn - self.now))})
        for stock in self.stocks.values():
            for ev in stock.events:
                events.append({"ticker": stock.ticker, "name": stock.name, "kind": newsgen.COMPANY_EVENT_KEYS[ev["kind"]]["label"],
                               "at": ev["t"], "in_seconds": max(0, int(ev["t"] - self.now))})
        return sorted(events, key=lambda event: event["at"])[:20]

    def me_state(self, p, notices=True):
        """What one player sees about themselves every tick: cash, equity, rank and their positions."""
        e = self.equity(p)
        px = self.pub_px
        hold = []
        for tk, sh in p.hold.items():
            price = px.get(tk, 0)
            cost = p.cost.get(tk, 0.0)
            n = abs(sh)
            value = n * price
            pnl = value - cost if sh > 0 else cost - value
            hold.append({"ticker": tk, "side": "long" if sh > 0 else "short", "shares": round(n, 6),
                         "avg": round(cost / n, 6) if n > 0 else 0, "price": price, "cost": round(cost, 2),
                         "value": round(value, 2), "pnl": round(pnl, 2), "div": round(p.divs.get(tk, 0.0), 2),
                         "borrow": round(p.borrow.get(tk, 0.0), 2),
                         "pct": round(pnl / cost, 4) if cost > 0 else 0})
        out = {"cash": round(p.cash, 2), "equity": round(e, 2), "ret": round(self.season_return(p, e), 4),
               "pnl": round(e - p.deposited, 2), "holdings": hold, "rank": self.rank.get(p.token)}
        if p.orders or p.orders_dirty:          # sent while there are orders, and once more when the last one goes
            out["orders"] = [self._order_view(o) for o in p.orders]
            p.orders_dirty = False
        if notices:
            out["notices"], p.notices = p.notices, []
        return out

    def take_notices(self, p):
        notes, p.notices = p.notices, []
        return notes

    def board_view(self):
        return [{"name": r["name"], "equity": round(r["equity"], 2), "ret": round(r["ret"], 4),
                 } for r in self.board[:10]]

    def sector_view(self):
        return ([{"id": k, "name": v["name"], "icon": v.get("icon", ""), **self.sector_indices.get(k, {})}
                 for k, v in self.sectors.items()] + [{"id": "index", "name": "Indices & ETFs", "icon": "📊"}])

    def state_for(self, p):
        """The whole picture in one message (the shape the page used before the delta protocol; the `init`
        message is this plus a few fields). Tests and tools still use it."""
        return {"type": "state", "season": self.season_no,
                "season_left": max(0, int(self.season_end - self.now)),
                "index": self.pub_index,
                "market": self.session(),
                "upcoming": self._upcoming_events(),
                **self.me_state(p),
                "sectors": self.sector_view(),
                "stocks": self.pub_stocks,
                "news": [n for n in list(self.news_log)[-30:]][::-1],
                "board": self.board_view(),
                "players": len(self.players)}

    # ---------- the wire protocol: one `init`, then a small `tick` every second ----------
    def init_for(self, p):
        """Sent once when a page connects (and again if it falls behind): everything, including the facts that
        never change, so that the per-tick updates can be small."""
        d = self.state_for(p)
        d.update({"type": "init", "t": self.now, "seq": self.wire_seq, "static_v": self.static_v,
                  "chat": self.chat_history(p)})
        return d

    NEWS_WINDOW = 5    # seconds of headlines repeated in each tick, so a skipped tick loses nothing

    def build_wire(self):
        """The part of the per-tick update that is identical for every player. Built (and serialised) once per
        tick, then each player's own numbers are added to the end. Prices go out every tick; the heavier,
        slower-changing things (ratings, limits, financials, leaderboard, calendar) every fifth tick, and only
        when they changed."""
        self.wire_seq += 1
        n = self.wire_seq
        sig = (tuple(self.stocks), self.content_sig)
        if sig != self._static_sig:
            self._static_sig = sig
            self.static_v += 1
        idx = self.pub_index
        msg = {"type": "tick", "seq": n, "t": self.now, "px": self.pub_fast,
               "idx": [idx.get("value"), idx.get("chg")],
               "sec": {k: [v["value"], v["chg"]] for k, v in self.sector_indices.items()},
               "market": self.session(), "season": self.season_no,
               "season_left": max(0, int(self.season_end - self.now)), "players": len(self.players),
               "news": [x for x in list(self.news_log)[-12:] if x["t"] > self.now - self.NEWS_WINDOW],
               "static_v": self.static_v}
        if not self._wire_slow_sent:       # the first client's init already carries the current numbers
            self._wire_slow_sent = dict(self.pub_slow)
        if n % 5 == 0:
            everything = n % 60 == 0       # once a minute resend all, so a client that missed a change catches up
            changed = {tk: sl for tk, sl in self.pub_slow.items()
                       if everything or self._wire_slow_sent.get(tk) != sl}
            self._wire_slow_sent = dict(self.pub_slow)
            if changed:
                msg["slow"] = changed
            msg["board"] = self.board_view()
            upcoming = self._upcoming_events()
            sig = [(x["ticker"], x["at"]) for x in upcoming]
            if everything or sig != self._wire_upcoming_sig:     # the page counts down from `at` by itself
                self._wire_upcoming_sig = sig
                msg["upcoming"] = upcoming
        return msg

    # ---------- accounting / persistence ----------
    def total_tokens(self):
        return (self.house + self.fees + sum(s.T for s in self.stocks.values())
                + sum(p.cash for p in self.players.values()))

    def _sample_series(self):
        """Every 10 seconds, note house and player money so the admin page can draw charts."""
        if self.now - self._series_t < 10:
            return
        self._series_t = self.now
        humans = sum(self.equity(p) - p.deposited for p in self.players.values())
        self.series.append({"t": self.now, "house": self.house, "fees": self.fees, "humans_pnl": humans,
                            "trades": self.trades_total})

    def admin_overview(self, online=0):
        """Everything the admin page shows, in one call."""
        humans = list(self.players.values())
        rows = []
        for p in humans:
            eq = self.equity(p)
            pnl = eq - p.deposited
            rows.append({"name": p.name, "equity": eq, "pnl": pnl, "ret": pnl / p.deposited if p.deposited > 0 else 0.0,
                         "trades": p.trades, "positions": len(p.hold), "margin_calls": p.margin_calls})
        rows.sort(key=lambda r: -r["pnl"])
        edges = [(-1e9, -0.5, "< -50%"), (-0.5, -0.25, "-50..-25"), (-0.25, -0.1, "-25..-10"), (-0.1, 0.0, "-10..0"),
                 (0.0, 0.1, "0..10"), (0.1, 0.25, "10..25"), (0.25, 0.5, "25..50"), (0.5, 1e9, "> 50%")]
        dist = [{"label": lab, "lo": lo, "hi": hi, "count": sum(1 for r in rows if lo <= r["ret"] < hi)}
                for lo, hi, lab in edges]
        series = list(self.series)
        per_min = 0.0
        if series:
            last = series[-1]
            old = next((x for x in series if x["t"] >= last["t"] - 300), series[0])
            span = max(last["t"] - old["t"], 1.0)
            per_min = (last["trades"] - old["trades"]) / span * 60
        return {"stats": self.house_stats(), "series": series, "online": online, "trades_total": self.trades_total,
                "trades_per_min": per_min, "margin_calls": self.margin_calls,
                "margin_log": list(self.margin_log)[::-1][:20], "dist": dist, "winners": rows[:10]}

    # ---------- a player's own portfolio and history ----------
    def portfolio_for(self, p):
        """Everything the portfolio page shows: the equity curve, what the player holds and how it is split, realised
        and unrealised profit, fees, dividends, and their best and worst closed trades."""
        eq = self.equity(p)
        positions, longs, shorts, unrealized = [], 0.0, 0.0, 0.0
        for tk, sh in p.hold.items():
            st = self.stocks.get(tk)
            if not st:
                continue
            n = abs(sh)
            value = n * st.price
            cost = p.cost.get(tk, 0.0)
            pnl = (value - cost) if sh > 0 else (cost - value)
            unrealized += pnl
            if sh > 0:
                longs += value
            else:
                shorts += value
            positions.append({"ticker": tk, "name": st.name, "side": "long" if sh > 0 else "short", "shares": n,
                              "avg": cost / n if n else 0.0, "price": st.price, "value": value, "cost": cost,
                              "pnl": pnl, "pct": pnl / cost if cost > 0 else 0.0,
                              "realized": p.realized.get(tk, 0.0)})
        positions.sort(key=lambda x: -x["value"])
        gross = longs + shorts + max(p.cash, 0.0)
        allocation = [{"label": "Cash", "kind": "cash", "value": max(p.cash, 0.0)}]
        allocation += [{"label": x["ticker"], "kind": x["side"], "value": x["value"]} for x in positions]
        for a in allocation:
            a["pct"] = a["value"] / gross if gross > 0 else 0.0
        if self.ledger is not None:
            self.ledger.flush()
            best, worst = self.ledger.best_worst(p.token, 5)
        else:
            by = sorted(p.realized.items(), key=lambda kv: -kv[1])
            best = [{"ticker": k, "pnl": v} for k, v in by[:5] if v > 0]
            worst = [{"ticker": k, "pnl": v} for k, v in by[::-1][:5] if v < 0]
        realized = sum(p.realized.values())
        curve = [list(point) for point in p.curve] + [[self.now, eq, p.cash]]
        return {"equity": eq, "cash": p.cash, "deposited": p.deposited, "pnl": eq - p.deposited,
                "ret": (eq - p.deposited) / p.deposited if p.deposited > 0 else 0.0,
                "unrealized": unrealized, "realized": realized, "fees": p.fees_paid,
                "dividends": sum(p.divs.values()), "borrow": sum(p.borrow.values()),
                "trades": p.trades, "positions": positions, "allocation": allocation, "curve": curve,
                "best": best, "worst": worst, "realized_by_ticker": dict(p.realized)}

    HISTORY_KINDS = ("buy", "sell", "short", "cover", "margin_call", "dividend", "borrow", "credit", "debit",
                     "delist_payout")

    def history_for(self, p, limit=100, before=None, kinds=None):
        """A player's ledger entries, newest first, with paging (`before` is the `seq` of the last one seen)."""
        limit = max(1, min(int(limit), 500))
        kinds = [k for k in (kinds or ()) if k in self.HISTORY_KINDS] or list(self.HISTORY_KINDS)
        if self.ledger is not None:
            self.ledger.flush()
            rows = self.ledger.history(p.token, limit + 1, before, kinds)
            more = len(rows) > limit
            rows = rows[:limit]
            events = [{"seq": r["seq"], "t": r["t"], "kind": r["kind"], "ticker": r["ticker"],
                       "shares": abs(r["shares"]), "price": r["price"], "mb": r["notional"], "fee": r["fee"],
                       "pnl": r["pnl"], "cash": r["cash_delta"]} for r in rows]
            return {"events": events, "more": more, "next_before": events[-1]["seq"] if events and more else None,
                    "source": "ledger"}
        events = [{"seq": None, "t": x["t"], "kind": x["k"], "ticker": x["tk"], "shares": x["sh"], "price": x["px"],
                   "mb": x["mb"], "fee": x["fee"], "pnl": None, "cash": None}
                  for x in reversed(p.log) if x["k"] in kinds][:limit]
        return {"events": events, "more": False, "next_before": None, "source": "memory"}

    def history_csv(self, p):
        """The whole history as CSV text (oldest first), for download."""
        import datetime
        out = ["time_utc,type,ticker,shares,price_mb,amount_mb,fee_mb,realised_pnl_mb,cash_change_mb"]
        if self.ledger is not None:
            self.ledger.flush()
            rows = [r for r in self.ledger.all_history(p.token) if r["kind"] in self.HISTORY_KINDS]
        else:
            rows = [{"t": x["t"], "kind": x["k"], "ticker": x["tk"], "shares": x["sh"], "price": x["px"],
                     "notional": x["mb"], "fee": x["fee"], "pnl": None, "cash_delta": None} for x in p.log]
        for r in rows:
            when = datetime.datetime.fromtimestamp(r["t"], datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            cells = [when, r["kind"], r["ticker"] or "", f"{abs(r['shares']):.6f}", f"{r['price']:.6f}",
                     f"{r['notional']:.4f}", f"{r['fee']:.4f}", "" if r["pnl"] is None else f"{r['pnl']:.4f}",
                     "" if r["cash_delta"] is None else f"{r['cash_delta']:.4f}"]
            out.append(",".join(cells))
        return "\n".join(out) + "\n"

    def admin_player(self, name):
        p = next((x for x in self.players.values() if x.name.lower() == name.lower()), None)
        if not p:
            return None
        eq = self.equity(p)
        holdings = []
        for tk, sh in p.hold.items():
            st = self.stocks.get(tk)
            if not st:
                continue
            n = abs(sh)
            value = n * st.price
            cost = p.cost.get(tk, 0.0)
            holdings.append({"ticker": tk, "side": "long" if sh > 0 else "short", "shares": n,
                             "avg": cost / n if n else 0.0, "price": st.price,
                             "pnl": (value - cost) if sh > 0 else (cost - value)})
        return {"name": p.name, "cash": p.cash, "equity": eq, "deposited": p.deposited,
                "pnl": eq - p.deposited, "divs": sum(p.divs.values()), "borrow": sum(p.borrow.values()),
                "trades": p.trades, "margin_calls": p.margin_calls, "holdings": holdings, "log": list(p.log)}

    def house_stats(self):
        """House P&L. Players' combined P&L is the mirror image of the house's (zero-sum)."""
        humans = list(self.players.values())
        human_equity = sum(self.equity(p) for p in humans)
        human_in = sum(p.deposited for p in humans)
        players_pnl = human_equity - human_in
        house_pnl = -players_pnl
        return {"fees": self.fees, "house_pnl": house_pnl,
                "liquidity_pnl": house_pnl - self.fees,
                "players_pnl": players_pnl, "player_deposits": human_in, "player_equity": human_equity,
                "player_cash": sum(p.cash for p in humans), "house_capital": self.house_capital,
                "house_reserve": self.house, "pool_tokens": sum(s.T for s in self.stocks.values()),
                "minted": self.minted, "invariant_drift": self.total_tokens() - self.minted,
                "borrow_fees": self.borrow_fees, "short_shortfall": self.short_shortfall,
                "short_interest": sum(self.short_interest_map().values()),
                "humans": len(humans), "recapitalized": self.recapitalized, "risk": self.house_risk()}

    def _charts_path(self):
        return os.path.splitext(self.state_file)[0] + ".charts.json"

    @staticmethod
    def _write_json(path, obj):
        """Serialise with the fast C encoder (json.dump to a file goes through a slow Python path: 4x slower on a big
        save) and swap the file in atomically."""
        text = json.dumps(obj, separators=(",", ":"))
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        # On Windows another program (OneDrive syncing the folder, a virus scanner, a backup) can hold the file open for
        # a moment, and os.replace then fails with "Access is denied". Try again a few times before giving up.
        for attempt in range(8):
            try:
                os.replace(tmp, path)
                return True
            except PermissionError:
                _sleep(0.1 * (attempt + 1))
        logger.warning("could not replace %s (something has it open); will try again at the next save", path)
        return False

    def save(self, full=True):
        """Write the game to disk. The chart candles are most of the file (23 of 27 MB on a long-running game) and
        change slowly, so they go to their own file, which the periodic save only rewrites every `charts_save_seconds`
        (five minutes). `full=True` (shutdown, tests) writes everything."""
        if not self.state_file:
            return
        seq = 0
        if self.ledger is not None:
            self._flush_borrow()
            self.ledger.flush()
            seq = self.ledger.last_seq()           # this snapshot already contains every event up to here
        d = {"schema": 7, "ledger_seq": seq, "house": self.house, "fees": self.fees, "house_capital": self.house_capital,
             "minted": self.minted, "index_level": self.index_level,
             "short_model": 2, "borrow_fees": self.borrow_fees, "short_shortfall": self.short_shortfall,
             "margin_calls": self.margin_calls, "trades_total": self.trades_total,
             "margin_log": list(self.margin_log), "mkt_volm": self.mkt_volm,
             "index_hist": list(self.index_hist), "market_day": self.market_day,
             "recapitalized": self.recapitalized, "regime": self.regime, "next_regime_change": self.next_regime_change,
             "mood": self.mood, "crisis_until": self.crisis_until, "sector_mood": self.sector_mood,
             "used_news": list(self.used_news), "threads": self.threads,
             "delisted": self.delisted, "season_no": self.season_no,
             "season_end": self.season_end, "history": self.history,
             "stocks": {t: {"T": s.T, "base": s.base, "fair": s.fair, "fair_open": s.fair_open,
                            "daily_hist": list(s.daily_hist), "candles": list(s.candles),
                            "safety": s.safety, "pending": s.pending, "log": list(s.log),
                            "reports": list(s.reports), "trend": s.trend, "mood": s.mood,
                            "dps": s.dps, "div": s.div, "base_margin": s.base_margin, "listed_at": s.listed_at,
                            "base_dps": s.base_dps, "volm": s.volm, "persona": s.persona, "split_factor": s.split_factor, "share_adj": s.share_adj,
                            "offering": s.offering,
                            "revenue": s.revenue, "margin": s.margin, "cash": s.cash, "debt": s.debt,
                            "rating": s.rating,
                            "day_open": s.day_open, "day_high": s.day_high, "day_low": s.day_low,
                            "next_earn": s.next_earn, "earn_slot": s.earn_slot, "events": s.events,
                            "next_rating_review": s.next_rating_review,
                            "distress_checked": s.distress_checked}
                        for t, s in self.stocks.items()},
             "players": [{"name": p.name, "token": p.token, "cash": p.cash, "hold": p.hold,
                          "deposited": p.deposited, "season_base": p.season_base, "cost": p.cost, "divs": p.divs, "borrow": p.borrow,
                          "orders": p.orders, "pw": p.pw, "ips": p.ips, "created": p.created,
                          "email": p.email, "email_verified": p.email_verified, "email_pending": p.email_pending,
                          "entry_fee": p.entry_fee, "realized": p.realized, "fees_paid": p.fees_paid, "trades": p.trades,
                          "log": list(p.log), "margin_calls": p.margin_calls,
                          "social": social.dump_player(p),
                          } for p in self.players.values()],
             "generated": [dict(x.cfg) for x in self.stocks.values() if x.cfg.get("generated")],
             "relations": self.relations.to_json(), "archive": self.archive,
             "social": self.social_dump(), "accounts": self.accounts_dump()}
        self._write_json(self.state_file, d)
        interval = float(self.settings.get("charts_save_seconds", 300))
        if full or self.now - self._charts_saved >= interval:
            ok = self._write_json(self._charts_path(), {"saved_at": self.now,
                                                        "tf": {t: {k: list(v) for k, v in s.tf.items()}
                                                               for t, s in self.stocks.items()}})
            # a failed write is tried again in half a minute (not every second: the file is big)
            self._charts_saved = self.now if ok else self.now - max(0.0, interval - 30.0)

    # ---------- crash recovery ----------
    def _replay(self, after_seq):
        """Re-apply every ledger event recorded after the snapshot we loaded, so a crash loses no trades,
        deposits, fees or dividends. Prices, news and other non-money state come back as of the snapshot."""
        events = self.ledger.events_after(after_seq)
        for ev in events:
            try:
                self._apply_event(ev)
            except Exception:
                logger.exception("could not replay ledger event %s", ev.get("seq"))
        if events:
            logger.warning("recovered %d ledger events recorded after the last snapshot", len(events))
        return len(events)

    def _apply_event(self, ev):
        kind, tk, extra = ev["kind"], ev["ticker"], ev["extra"]
        tk = TICKER_RENAMES.get(tk, tk)
        if kind == "split" or tk in WITHDRAWN_PRODUCTS:        # splits no longer exist; a withdrawn product is already paid out
            return
        if kind == "join":
            if ev["token"] not in self.by_token:
                p = Player(ev["name"])
                p.token = ev["token"]
                self._register(p)
            return
        if kind == "recap":
            self.house += ev["house_delta"]
            self._mint_house(ev["house_delta"])
            self.recapitalized += ev["house_delta"]
            return
        if kind == "delist":
            stock = self.stocks.pop(tk, None)
            if stock is not None:
                self.house += ev["house_delta"]
                self.delisted.append(tk)
                self.index_prev.pop(tk, None)
            return
        p = self.by_token.get(ev["token"])
        if p is None:
            return
        cash, house, fee = ev["cash_delta"], ev["house_delta"], ev["fee"]
        if kind in ("credit", "debit"):
            p.cash += cash
            p.deposited += cash
            p.season_base = max(0.0, p.season_base + cash)
            self.minted += cash
        elif kind in ("buy", "sell", "short", "cover", "margin_call"):
            p.cash += cash
            self.house += house
            self.fees += fee
            p.fees_paid += fee
            held = p.hold.get(tk, 0.0) + ev["shares"]
            if abs(held) < 1e-9:
                p.hold.pop(tk, None)
                p.cost.pop(tk, None)
                p.entry_fee.pop(tk, None)
            else:
                p.hold[tk] = held
                p.cost[tk] = p.cost.get(tk, 0.0) + ev["cost_delta"]
                if kind in ("buy", "short"):
                    p.entry_fee[tk] = p.entry_fee.get(tk, 0.0) + fee
                else:
                    p.entry_fee[tk] = max(0.0, p.entry_fee.get(tk, 0.0) - extra.get("efee", 0.0))
            if ev["pnl"] is not None:
                p.realized[tk] = p.realized.get(tk, 0.0) + ev["pnl"]
            if kind != "margin_call":
                p.trades += 1
                self.trades_total += 1
            p.log.append({"t": ev["t"], "k": kind, "tk": tk, "sh": abs(ev["shares"]), "px": ev["price"],
                          "mb": ev["notional"], "fee": fee})
        elif kind == "margin":
            p.margin_calls += 1
            self.margin_calls += 1
            self.short_shortfall += extra.get("shortfall", 0.0)
            self.margin_log.append({"t": ev["t"], "player": p.name, "tickers": extra.get("tickers", []),
                                    "shortfall": extra.get("shortfall", 0.0)})
        elif kind == "dividend":
            p.cash += cash
            self.house += house
            p.divs[tk] = p.divs.get(tk, 0.0) + cash
        elif kind == "borrow":
            p.cash += cash
            self.fees += fee
            self.borrow_fees += fee
            p.fees_paid += fee
            p.borrow[tk] = p.borrow.get(tk, 0.0) + fee
        elif kind == "delist_payout":
            p.cash += cash
            self.house += house
            p.hold.pop(tk, None)
            p.cost.pop(tk, None)
            p.entry_fee.pop(tk, None)
            self.short_shortfall += extra.get("shortfall", 0.0)

    def _migrate_short_model(self):
        """Saves from when a short ADDED its proceeds to your cash (locked as collateral). Now the amount you short is
        taken out of your cash and held as collateral. Each open short moves its collateral (twice its entry value: the
        proceeds that were added and the same amount held) out of the cash into the house, so equity does not change
        (a player whose cash had been spent elsewhere gives up what cash they have, never more)."""
        moved = 0.0
        for p in self.players.values():
            for tk, sh in p.hold.items():
                if sh < 0:
                    take = min(max(p.cash, 0.0), 2 * p.cost.get(tk, -sh * self.stocks[tk].price if tk in self.stocks else 0.0))
                    p.cash -= take
                    self.house += take
                    moved += take
        if moved:
            logger.warning("moved %.2f MB of short collateral out of players' cash (old short model)", moved)

    def _undo_old_splits(self, d, charts):
        """Saves from the time stock splits existed. A split divided the price (and every chart and reference) by its
        ratio and multiplied the shares; the old code could split a stock again and again (the price stayed above twice
        its own, shrinking reference), until a price was 1e-22 and showed as 0.0000 MB. There are no splits now, so each
        stock is put back on its original scale: prices, charts, dividends and trigger prices are multiplied by the split
        factor and shares divided by it. Every position keeps the same value, so nobody gains or loses anything."""
        factors = {tk: float(v.get("split_factor", 1.0)) for tk, v in d.get("stocks", {}).items()}
        factors = {tk: f for tk, f in factors.items() if f > 1.0000001 and f < 1e60}
        if not factors:
            return

        def candles(rows, f):
            return [[c[0]] + [x * f for x in c[1:]] for c in rows]
        for tk, f in factors.items():
            v = d["stocks"][tk]
            for key in ("fair", "fair_open", "day_open", "day_high", "day_low", "dps", "base_dps"):
                if v.get(key) is not None:
                    v[key] = float(v[key]) * f
            if isinstance(v.get("div"), dict) and v["div"].get("amt") is not None:
                v["div"]["amt"] = float(v["div"]["amt"]) * f
            v["candles"] = candles(v.get("candles", []), f)
            v["daily_hist"] = [[c[0]] + [x * f for x in c[1:]] for c in v.get("daily_hist", [])]
            for frames in (v.get("tf"), charts.get(tk)):
                if isinstance(frames, dict):
                    for key in list(frames):
                        frames[key] = candles(frames[key], f)
            v["split_factor"] = 1.0
        for x in d.get("players", []):
            for tk, f in factors.items():
                if tk in x.get("hold", {}):
                    x["hold"][tk] = x["hold"][tk] / f
                for o in x.get("orders", []):
                    if o.get("ticker") == tk and o.get("trigger"):
                        o["trigger"] = o["trigger"] * f
        logger.warning("undid old stock splits on %s", ", ".join(sorted(factors)))

    def _migrate_save(self, d):
        """Saves from before the leveraged products were renamed (BULL2 became 2LMSI, BEAR2 became 2SMSI) or one of
        them was withdrawn (BEAR1): rename the tickers everywhere, and pay out holders of a withdrawn product at its
        last price (a short is closed at that price), the way a delisting does, so nobody loses a position."""
        stocks = d.get("stocks", {})
        for old, new in TICKER_RENAMES.items():
            if old in stocks and new not in stocks:
                stocks[new] = stocks.pop(old)

        def renamed(m):
            return {TICKER_RENAMES.get(k, k): v for k, v in m.items()}
        for x in d.get("players", []):
            for key in ("hold", "cost", "divs", "borrow", "entry_fee", "realized"):
                if key in x:
                    x[key] = renamed(x[key])
            for entry in x.get("log", []):
                entry["tk"] = TICKER_RENAMES.get(entry.get("tk"), entry.get("tk"))
            soc = x.get("social", {})
            if "opened" in soc:
                soc["opened"] = renamed(soc["opened"])
        for tk, name in WITHDRAWN_PRODUCTS.items():
            v = stocks.pop(tk, None)
            if v is None:
                continue
            price = float(v.get("fair", 0.0))
            for x in d.get("players", []):
                sh = float(x.get("hold", {}).pop(tk, 0.0))
                for key in ("cost", "entry_fee"):
                    x.get(key, {}).pop(tk, None)
                if sh > 0:
                    x["cash"] += sh * price
                    d["house"] = float(d.get("house", 0.0)) - sh * price
                elif sh < 0:
                    owed = min(x["cash"], -sh * price)
                    x["cash"] -= owed
                    d["house"] = float(d.get("house", 0.0)) + owed
            d.setdefault("archive", {})[tk] = {
                "ticker": tk, "name": name, "desc": "A leveraged product that was withdrawn from the market.",
                "sector": "index", "asset_type": "index", "reason": "withdrawn", "delisted_at": d.get("saved_at", 0.0),
                "final_price": round(price, 6), "beta": 0.0, "vol": 0.0, "rating": None, "financials": {},
                "persona": {}, "log": [], "reports": [], "tf": {}}
            d.setdefault("delisted", []).append(tk)

    def _load_state(self):
        if not self.state_file or not os.path.exists(self.state_file):
            return
        try:
            with open(self.state_file, encoding="utf-8") as fh:
                d = json.load(fh)
            charts = {}
            if os.path.exists(self._charts_path()):
                try:
                    with open(self._charts_path(), encoding="utf-8") as fh:
                        charts = json.load(fh).get("tf", {})
                except (OSError, ValueError):
                    logger.warning("could not read the chart file; charts are rebuilt from the minute candles")
            self._undo_old_splits(d, charts)
            self._migrate_save(d)
            self.archive = dict(d.get("archive", {}))
            schema = int(d.get("schema", 1))
            saved_stocks = d["stocks"]
            self._pre_moonshot_save = "generated" not in d     # every newer save has the key, even with no moonshots
            if d.get("relations"):
                self.relations = relations.Relations.from_json(d["relations"])
            self.delisted = list(d.get("delisted", []))
            for cfg in d.get("generated", []):                 # companies that were generated while the game ran
                tk = cfg.get("ticker")
                if tk and tk not in self.stocks and tk not in self.delisted and tk in saved_stocks:
                    self.stocks[tk] = Stock(cfg, float(cfg.get("depth", 3000)))
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
                    saved_tf = charts.get(t, {}).get(key)
                    if saved_tf is None:
                        saved_tf = v.get("tf", {}).get(key)          # a save from before the chart file existed
                    if saved_tf is not None:
                        s.tf[key].extend([list(c) for c in saved_tf])
                        if s.tf[key] and secs >= INTRADAY_CANDLE_SECONDS:     # the chart file may be a few minutes behind
                            last = s.tf[key][-1][0]
                            for c in s.candles:
                                if c[0] >= last:
                                    self._merge(s.tf[key], int(c[0] // secs) * secs, *c[1:])
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
                if "dps" in v:
                    s.dps, s.div = float(v["dps"]), v.get("div")
                    s.base_dps = float(v.get("base_dps", s.base_dps))
                s.volm = float(v.get("volm", 1.0))
                s.listed_at = float(v.get("listed_at", 0.0))
                if v.get("persona"):
                    s.persona = v["persona"]
                s.split_factor = float(v.get("split_factor", 1.0))
                s.share_adj = float(v.get("share_adj", 1.0))
                s.offering = v.get("offering")             # (a split that was only announced in an older game is dropped)
                s.rescale()
                if "revenue" in v:
                    s.revenue, s.margin = float(v["revenue"]), float(v["margin"])
                    s.cash, s.debt = float(v["cash"]), float(v["debt"])
                    s.base_margin = float(v.get("base_margin", s.margin))
                if s.asset_type == "equity" and "safety" not in v:
                    s.rating = self._rating_for(s)
                s.next_earn = v.get("next_earn", s.next_earn)
                s.earn_slot = v.get("earn_slot")
                s.events = [ev for ev in v.get("events", []) if isinstance(ev, dict) and ev.get("kind") in newsgen.COMPANY_EVENT_KEYS
                            and ev.get("t", 0) > self.now]
                if s.next_earn and not s.events:                            # an old save, or every planned event is past
                    s.events = self._new_company_events(s)
                if s.next_earn and s.earn_slot is None:     # a save from before reports were moved to pre/after-hours
                    s.earn_slot = s.next_earn
                    if s.next_earn > self.now:
                        s.next_earn = self._snap_to_window(s.next_earn)
                s.next_rating_review = v.get("next_rating_review", s.next_rating_review)
                s.distress_checked = v.get("distress_checked", False)
                # events that fell due while the server was down are rescheduled instead of all firing at once
                if s.next_earn and s.next_earn < self.now:
                    s.earn_slot = self._pick_earnings_slot()
                    s.next_earn = self._snap_to_window(s.earn_slot)
                if s.next_rating_review and s.next_rating_review < self.now:
                    s.next_rating_review = self._next_review()
                self._record(s)
            self.minted = float(d["minted"])
            self.fees = float(d.get("fees", 0.0))
            self.borrow_fees = float(d.get("borrow_fees", 0.0))
            self.short_shortfall = float(d.get("short_shortfall", 0.0))
            self.margin_calls = int(d.get("margin_calls", 0))
            self.mkt_volm = float(d.get("mkt_volm", 1.0))
            self.trades_total = int(d.get("trades_total", 0))
            self.margin_log.extend(d.get("margin_log", []))
            # listings added to content since the save are funded from the house reserve
            for t, s in self.stocks.items():
                if t not in saved_stocks and t not in self.derived:
                    s.listed_at = self.now            # added to the content since the save: new to this game
            new_reserves = sum(s.T for t, s in self.stocks.items() if t not in saved_stocks)
            take = min(max(house, 0.0), new_reserves)
            self.house = house - take
            self.minted += new_reserves - take
            self.players.clear()
            self.by_token.clear()
            retiring = []                                  # house-funded bots from an older save: settled and removed below
            for x in d["players"]:
                p = Player(x["name"])
                if x.get("bot"):
                    retiring.append(p)
                p.token, p.cash = x["token"], x["cash"]
                p.hold = {ticker: shares for ticker, shares in x["hold"].items() if ticker in self.stocks}
                p.cost = {tk: float(c) for tk, c in x.get("cost", {}).items() if tk in p.hold}
                p.divs = {tk: float(c) for tk, c in x.get("divs", {}).items()}
                p.borrow = {tk: float(c) for tk, c in x.get("borrow", {}).items()}
                p.orders = [o for o in x.get("orders", []) if isinstance(o, dict) and o.get("kind") in self.ORDER_KINDS
                            and o.get("ticker") in self.stocks]
                self.order_seq = max([self.order_seq] + [int(o.get("id", 0)) for o in p.orders])
                p.entry_fee = {tk: float(c) for tk, c in x.get("entry_fee", {}).items() if tk in p.hold}
                p.realized = {tk: float(c) for tk, c in x.get("realized", {}).items()}
                p.fees_paid = float(x.get("fees_paid", 0.0))
                p.trades = int(x.get("trades", 0))
                p.pw = x.get("pw") if isinstance(x.get("pw"), dict) else None
                p.ips = [str(t) for t in x.get("ips", [])][-5:]
                p.email = str(x["email"]) if x.get("email") else None
                p.email_verified = bool(x.get("email_verified")) and p.email is not None
                p.email_pending = str(x["email_pending"]) if x.get("email_pending") else None
                p.created = float(x.get("created", 0.0))
                if self.ledger is not None and p not in retiring:
                    p.curve.extend(self.ledger.curve(p.token, 1440))
                p.log.extend(x.get("log", []))
                p.margin_calls = int(x.get("margin_calls", 0))
                for tk, shares in p.hold.items():  # saves from before cost tracking: entry = current price
                    p.cost.setdefault(tk, shares * self.stocks[tk].price)
                p.deposited = float(x.get("deposited", START_CASH))
                p.season_base = float(x.get("season_base", self.equity(p)))
                social.load_player(p, x.get("social", {}))
                self.players[p.token] = p
                self.by_token[p.token] = p
            human_in = sum(p.deposited for p in self.players.values() if p not in retiring)
            self.house_capital = float(d.get("house_capital", self.minted - human_in)) + new_reserves - take
            self.recapitalized = float(d.get("recapitalized", 0.0))
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
            self.season_end = min(float(self.season_end), self._season_boundary())   # days end at midnight UTC, even in a save made before that
            self.social_load(d.get("social", {}))
            self.accounts_load(d.get("accounts", {}))
            if self.ledger is not None:
                self.recovered_events = self._replay(int(d.get("ledger_seq", self.ledger.last_seq())))
            if d.get("short_model") != 2:
                self._migrate_short_model()
            if retiring:
                self._retire_bots(retiring)
            drift = self.total_tokens() - self.minted
            if abs(drift) > 1e-6:
                logger.warning("token invariant off by %.6f after loading state", drift)
                if schema < 6:
                    # pre-v6 saves could leak tokens through the old treasury; book the gap as house capital
                    self.minted += drift
                    self.house_capital += drift
        except Exception:
            logger.exception("state load failed, starting fresh")
