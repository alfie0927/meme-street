"""Paper-money contest accounts.

A contest gives every entrant the same fixed paper balance, so the ranking is about skill and not about who started
with more. The paper account trades at the live prices under the real rules (the same fee, the same margin and
maintenance levels for shorts, the same borrow fees, dividends and bankruptcy payouts), but it never touches the real
economy: no real token moves, the house reserve is untouched, and no price is affected.

It reuses the engine's own trading code. A `Sandbox` looks like the engine to that code, with its own throwaway house
and fee pool, and passes everything else (prices, settings, the clock) through to the real engine. Because the code is
the same, the contest cannot drift away from how the real game works."""
import inspect
import types
from collections import deque

ACCOUNT_FIELDS = ("cash", "hold", "cost", "entry_fee", "realized", "fees_paid", "divs", "borrow", "trades", "margin_calls")


class Sandbox:
    """An engine look-alike with a throwaway house. Methods of the engine run against it as if it were the engine."""

    def __init__(self, engine):
        self._engine = engine
        self.house = 0.0                       # what the paper accounts have lost to (or won from) the pretend house
        self.fees = 0.0
        self.borrow_fees = 0.0
        self.short_shortfall = 0.0
        self.trades_total = 0
        self.margin_calls = 0
        self.margin_log = deque(maxlen=20)
        self.ledger = None                     # paper trades are never written to the money ledger
        self.players = {}                      # token -> paper account (a Player object that is not in the real game)
        self.by_token = self.players
        self._borrow_acc = {}
        self._borrow_t = engine.now
        self._borrow_flush_t = engine.now

    def __getattr__(self, name):
        engine = self.__dict__["_engine"]
        found = inspect.getattr_static(type(engine), name, None)
        if isinstance(found, staticmethod):
            return found.__func__
        if inspect.isfunction(found):          # the engine's own methods, run against the sandbox
            return types.MethodType(found, self)
        return getattr(engine, name)           # prices, stocks, settings, the clock

    # Things that would reach the real game from a trade do nothing here.
    def _on_open(self, p, ticker):
        pass

    def _on_trade(self, p, kind, s, notional, pnl=None, closed=False):
        pass

    def _on_dividend(self, p, pay):
        pass

    def _emit(self, *a, **k):
        pass

    def email_gate(self, p):
        """A paper account is not the player: the player's own address was checked when they entered the contest."""
        return None

    def short_interest_map(self):
        """Every entrant borrows on their own: one entrant's shorts never use up another's shares to borrow."""
        return {}

    # ---- the engine hooks that settle paper accounts alongside real ones
    def tick(self):
        """Margin calls and borrow fees, every tick, exactly as for real accounts."""
        if not self.players:
            return
        self._borrow_fees()
        self._margin_calls()

    def dividend(self, ticker, amt):
        """The ex-dividend payment (holders receive it, shorts pay it), as for real accounts."""
        for p in self.players.values():
            sh = p.hold.get(ticker, 0.0)
            if sh > 0:
                pay = sh * amt
                p.cash += pay
                p.divs[ticker] = p.divs.get(ticker, 0.0) + pay
            elif sh < 0:
                owed = min(p.cash, -sh * amt)
                p.cash -= owed
                p.divs[ticker] = p.divs.get(ticker, 0.0) - owed

    def delist(self, ticker, price):
        """A bankrupt company: holders are paid out at the last price and shorts close at it."""
        for p in self.players.values():
            sh = p.hold.pop(ticker, 0.0)
            collateral = p.cost.pop(ticker, 0.0)
            p.entry_fee.pop(ticker, None)
            if sh > 0:
                p.cash += sh * price
            elif sh < 0:                                  # the collateral back, less what the price did (never below zero cash)
                p.cash += self._short_payout(p, collateral, -sh * price, 0.0)[0]


def dump_account(a):
    d = {k: getattr(a, k) for k in ACCOUNT_FIELDS}
    d["name"] = a.name
    d["log"] = list(a.log)[-30:]
    return d


def load_account(player_cls, token, x, stocks):
    a = player_cls(str(x.get("name", "?")))
    a.token = token
    a.cash = float(x.get("cash", 0.0))
    a.hold = {tk: float(sh) for tk, sh in dict(x.get("hold", {})).items() if tk in stocks}
    a.cost = {tk: float(c) for tk, c in dict(x.get("cost", {})).items() if tk in a.hold}
    a.entry_fee = {tk: float(c) for tk, c in dict(x.get("entry_fee", {})).items() if tk in a.hold}
    a.realized = {tk: float(c) for tk, c in dict(x.get("realized", {})).items()}
    a.divs = {tk: float(c) for tk, c in dict(x.get("divs", {})).items()}
    a.borrow = {tk: float(c) for tk, c in dict(x.get("borrow", {})).items()}
    a.fees_paid = float(x.get("fees_paid", 0.0))
    a.trades = int(x.get("trades", 0))
    a.margin_calls = int(x.get("margin_calls", 0))
    a.log.extend(x.get("log", []))
    return a
