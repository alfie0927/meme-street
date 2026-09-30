"""Headless economy check for Meme Street.

Runs the engine on a fake clock with "human" traders that play adversarial strategies using only
public information (news wire, prices, reference prices). The house wants two things to be true:
  1. Tokens are conserved exactly (nothing is created or destroyed by price moves).
  2. No public-information strategy earns a reliable edge, so player profits come from other
     players and the house keeps its fees.

Usage:  python sim.py [hours=6] [seed=1]
Exit code is non-zero if the token invariant breaks.
"""
import os, random, sys, time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("ENGINE_DIR", HERE))
os.chdir(HERE)
import engine as engine_mod  # noqa: E402

STRATEGIES = ["news_chaser", "rumor_trader", "value", "dip_buyer", "retail", "hodl"]
COPIES = 3


class Trader:
    def __init__(self, p, strategy):
        self.p, self.strategy = p, strategy
        self.opened = {}
        self.last_news = 0
        self.last_price = {}


def act(e, tr):
    p, now = tr.p, e.now
    fresh = [n for n in e.news_log if n["id"] > tr.last_news]
    if e.news_log:
        tr.last_news = e.news_log[-1]["id"]

    def buy(tk, pct):
        ok, _ = e.trade(p, tk, "buy", pct)
        if ok:
            tr.opened[tk] = now

    def sell(tk):
        if tk in p.hold and e.trade(p, tk, "sell", 1)[0]:
            tr.opened.pop(tk, None)

    if tr.strategy in ("news_chaser", "rumor_trader"):
        kinds = {"news_chaser": ("breaking", "confirm", "correction", "bailout"),
                 "rumor_trader": ("rumor",)}[tr.strategy]
        for n in fresh:
            if n["kind"] not in kinds:
                continue
            for tk in n["tickers"][:2]:
                if tk not in e.stocks:
                    continue
                if n["dir"] > 0 and p.cash > 20:
                    buy(tk, 0.3)
                elif n["dir"] < 0:
                    sell(tk)
        hold_for = 120 if tr.strategy == "rumor_trader" else 90
        for tk, t in list(tr.opened.items()):
            if now - t > hold_for:
                sell(tk)
    elif tr.strategy == "value":
        for tk, s in e.stocks.items():
            ratio = s.price / s.initial_price
            if ratio < 0.9 and tk not in p.hold and p.cash > 20:
                buy(tk, 0.2)
            elif ratio > 0.99 and tk in p.hold:
                sell(tk)
    elif tr.strategy == "dip_buyer":
        # buys a stock the tick after it drops sharply, sells a minute later
        for tk, s in e.stocks.items():
            prev = tr.last_price.get(tk, s.price)
            if s.price / prev - 1 < -0.01 and p.cash > 20:
                buy(tk, 0.2)
            tr.last_price[tk] = s.price
        for tk, t in list(tr.opened.items()):
            if now - t > 60:
                sell(tk)
    elif tr.strategy == "retail":
        if random.random() < 0.02:
            tk = random.choice(list(e.stocks))
            if random.random() < 0.55:
                buy(tk, random.choice([0.1, 0.25, 0.5]))
            else:
                sell(tk)
    elif tr.strategy == "hodl":
        if not p.hold and p.cash > 900:
            for tk in random.sample(list(e.stocks), 8):
                buy(tk, 0.12)


def run(hours=6.0, seed=1):
    random.seed(seed)
    e = engine_mod.Engine(state_file=None)
    t0 = time.time()
    e.season_end = float("inf")  # isolate the market economics from season resets
    e.settings["season_seconds"] = 10 ** 9
    traders = []
    for strat in STRATEGIES:
        for i in range(COPIES):
            p, err = e.join(f"{strat[:10]}{i}")
            assert p, err
            traders.append(Trader(p, strat))
    start = {tr.p.token: e.equity(tr.p) for tr in traders}
    fees_before = getattr(e, "fees", None)
    drift = 0.0
    ticks = int(hours * 3600)
    for i in range(ticks):
        e.tick(now=t0 + i)
        for tr in traders:
            act(e, tr)
        drift = max(drift, abs(e.total_tokens() - e.minted))

    by = defaultdict(list)
    for tr in traders:
        by[tr.strategy].append(e.equity(tr.p) / start[tr.p.token] - 1)
    print("engine:", os.path.basename(os.path.dirname(engine_mod.__file__)))
    print(f"{hours:g}h simulated, seed {seed}, {len(e.stocks)} listings, delisted {e.delisted}")
    print(f"token invariant max drift: {drift:.2e}")
    print("strategy        mean ret   best     worst    trades")
    for strat in STRATEGIES:
        rs = by[strat]
        trades = sum(tr.p.trades for tr in traders if tr.strategy == strat) / COPIES
        print(f"{strat:14} {sum(rs) / len(rs):+8.2%} {max(rs):+8.2%} {min(rs):+8.2%} {trades:8.0f}")
    if hasattr(e, "house_stats"):
        st = e.house_stats()
        print("house:", {k: round(v, 2) if isinstance(v, float) else v for k, v in st.items()})
    moves = sorted(s.price / s.initial_price - 1 for s in e.stocks.values())
    print(f"price vs reference: min {moves[0]:+.1%}  median {moves[len(moves) // 2]:+.1%}  max {moves[-1]:+.1%}")
    return drift


if __name__ == "__main__":
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    sys.exit(1 if run(hours, seed) > 1e-6 else 0)
