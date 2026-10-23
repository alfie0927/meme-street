"""No free money with options, on the real engine (HOW_IT_WORKS §4 and §17.11). Runs one game for a number of game days
with nobody trading; every 10 minutes, for every stock with options and the first four expiries, buys on paper (at the
ask, plus the fee) calls and puts at the money, 5% and 10% out and 10% in the money, and straddles and 5% and 10%
strangles; each is either held to expiry (a delisted stock pays as if at 0) or sold at the bid halfway there. Prints the
average return per MB spent in every group that could hide an edge: kind and moneyness, expiry, calm or stormy spell,
tame or wild stock, a new game's first 15 game days. Every straddle and strangle group should lose; single calls and
puts follow the market's direction. Run several seeds side by side (about 15 minutes each for 60 game days):

    python tools/option_check.py SEED GAME_DAYS
"""
import os
import random
import statistics
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))   # the game's code
import engine  # noqa: E402
import options  # noqa: E402

MNY = {"atm": 0.0, "otm5": 0.05, "otm10": 0.10, "itm10": -0.10}


def main(seed, days):
    random.seed(seed)
    e = engine.Engine(state_file=None)
    e._public = lambda: None                 # (no page state or leaderboard: nobody is looking)
    e._board = lambda: None
    e.tick(now=e.now)
    book = []                                # [expiry, sell time, ticker, kind, strike(s), cost, groups, sold]
    res = defaultdict(list)
    start, end, step, t0 = e.now, e.now + days * 1800, 0, time.time()
    while e.now < end:
        e.tick(now=e.now + 1)
        step += 1
        if step % 600 == 0:
            exps = e.option_expiries()
            for s in list(e.stocks.values()):
                if not e.option_ok(s):
                    continue
                wild = "wild" if s.vol * e._vol_scale() >= 0.6 else "tame"
                m = e._vol_multiplier(s)
                spell = "calm" if m < 0.85 else "storm" if m > 1.2 else "normal"
                phase = "early" if e.now - start < 15 * 1800 else "late"
                for j, exp in enumerate(exps[:4]):
                    ks = e.listed_strikes(s, exp)
                    near = lambda want: min(ks, key=lambda k: abs(k - want))   # noqa: E731
                    for name, off in (("straddle", 0.0), ("strangle5", 0.05), ("strangle10", 0.10)):
                        Kc, Kp = near(s.price * (1 + off)), near(s.price * (1 - off))
                        cost = (e.option_quote(s, "call", Kc, exp)["ask"] + e.option_quote(s, "put", Kp, exp)["ask"]) * 1.001
                        groups = {"pair": f"{name}-{wild}", "expiry": f"{name}-{j}", "spell": f"{name}-{spell}",
                                  "phase": f"{name}-{phase}"}
                        book.append([exp, e.now + (exp - e.now) / 2, s.ticker, "pair", (Kc, Kp), cost, groups, False])
                    for kind in ("call", "put"):
                        for mn, off in MNY.items():
                            if mn == "itm10" and kind == "put":
                                continue
                            K = near(s.price * (1 + off if kind == "call" else 1 - off))
                            ask = e.option_quote(s, kind, K, exp)["ask"]
                            if ask > 0:
                                groups = {"single": f"{wild}-{kind}-{mn}", "all-expiry": str(j), "all-spell": spell}
                                book.append([exp, e.now + (exp - e.now) / 2, s.ticker, kind, K, ask * 1.001, groups, False])
        if step % 60 == 0:
            keep = []
            for x in book:
                exp, sell_t, tk, kind, K, cost, groups, sold = x
                s = e.stocks.get(tk)
                if not sold and e.now >= sell_t and s is not None:
                    bid = (e.option_quote(s, "call", K[0], exp)["bid"] + e.option_quote(s, "put", K[1], exp)["bid"]
                           if kind == "pair" else e.option_quote(s, kind, K, exp)["bid"]) * 0.999
                    for g, v in groups.items():
                        res[("halfway", g, v)].append(bid / cost - 1)
                    x[7] = True
                if e.now >= exp:
                    S = s.price if s else 0.0
                    pay = (options.payoff("call", K[0], S) + options.payoff("put", K[1], S) if kind == "pair"
                           else options.payoff(kind, K, S))
                    for g, v in groups.items():
                        res[("held", g, v)].append(pay / cost - 1)
                else:
                    keep.append(x)
            book = keep
    print(f"seed {seed}, {days} game days, {time.time() - t0:.0f} s")
    for key in sorted(res):
        print(f"{key[0]:8} {key[1]:10} {key[2]:20} n={len(res[key]):7} mean {statistics.mean(res[key]):+.3f}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 21, float(sys.argv[2]) if len(sys.argv) > 2 else 60)
