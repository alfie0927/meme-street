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

# The first six are the original long-only strategies. The rest probe the newer mechanics:
#   short_seller    fades bullish headlines by shorting, covers after 90 s
#   squeeze_hunter  shorts anything that jumped over 3% in a minute (a momentum/mean-reversion fade)
#   big_size        trades the news with 100% of cash or spare margin, closes after 60 s
#   mood_oracle     cheats: reads the engine's hidden mood and trades the index with it. If even this
#                   can't earn an edge, the hidden narrative can't be farmed by anyone who reads it.
# And these probe the mechanics added with the bigger market:
#   gap_long/short  hold three stocks across the opening jump (long, or short): buy just before the regular
#                   session opens, sell a few seconds after, to see if the jump pays
#   open_follow     buys what jumped up at the open and shorts what jumped down (momentum after the open)
#   open_fade       the opposite: fades the opening jump
#   reversal_chaser trades in the direction a REVERSAL headline points; update_chaser does the same for UPDATE
#   partner_chaser  trades the second company named in a two-company story, in the headline's direction
#   etf_hodl, bull2_hodl, bear2_hodl, bull3_hodl, bear3_hodl   buy and hold a basket ETF, the 2x long and short
#                   products (2LMSI, 2SMSI) and the 3x long and short products (3LMSI, 3SMSI)
#   vol_chaser      buys stocks flagged as volatile (volatility clusters, but must not predict direction)
#   earnings_runup  buys 30 s before a company's earnings report and sells 30 s after
#   moon_hodl       buys each brand-new moonshot at its listing and holds it for 20 minutes
#   moon_short      shorts every moonshot (as far as the small borrow pool allows) for 10 minutes
#   moon_sniper     buys every brand-new moonshot within five seconds of its listing and then waits, with no stop-loss and
#                   no time limit, until it is worth `target` times what it paid (1.5x to 20x, a different target for each
#                   of its bots) or goes bankrupt. Moonshots are fair bets, so it should lose only its fees on average; the
#                   point of it is the spread: how many bots win big, how many lose, and what the house pays out.
#   distress_buyer  buys stocks that are just above the distress line (a rescue could be coming)
#   distress_short  shorts them (a bankruptcy could be coming); the rescue/bankruptcy bet is built to be fair
#   catalyst_follow buys anything that jumped 25% in the last two minutes; catalyst_fade shorts it
#   relation_oracle CHEATS by reading the hidden supplier / customer / rival graph: when a company jumps 4% in 30
#                   seconds it buys its customers and shorts its rivals (or the reverse after a fall), for two
#                   minutes. The spillover lands in the same second as the move, so it should earn nothing.
#   bracket_trader  buys a random stock and sets a take-profit and a stop-loss 1% either side (an order bracket),
#                   then does it again: orders are a convenience, so it should earn only minus its fees
#   industry_follow buys three companies of any industry that has just moved 6% or more as a group, in the
#                   direction it moved (shorting them if it fell); industry_fade does the opposite
#   trend_follower  buys commodities whose last 10 minutes were up, shorts those that were down (commodities
#                   have a slow trend, which would be a momentum edge if it were predictable)
STRATEGIES = ["news_chaser", "rumor_trader", "value", "dip_buyer", "retail", "hodl",
              "short_seller", "squeeze_hunter", "big_size", "mood_oracle",
              "gap_long", "gap_short", "open_follow", "open_fade", "reversal_chaser", "update_chaser", "partner_chaser",
              "etf_hodl", "bull2_hodl", "bear2_hodl", "bull3_hodl", "bear3_hodl", "vol_chaser", "earnings_runup", "trend_follower",
              "moon_hodl", "moon_short", "moon_sniper", "distress_buyer", "distress_short", "catalyst_follow", "catalyst_fade",
              "industry_follow", "industry_fade", "relation_oracle", "bracket_trader"]
COPIES = 3
# Only these strategies make random choices, so only their copies differ. Every other strategy is a fixed rule applied to
# public information, and since a player's trades never move a price, all its copies make exactly the same trades and end
# with exactly the same money (checked: the spread across copies is 0.000000 for the other 29). More copies of those add
# nothing; more seeds (more markets) are what give a bigger sample.
NEWS_STRATEGIES = {"news_chaser", "rumor_trader", "short_seller", "big_size", "reversal_chaser", "update_chaser", "partner_chaser"}
RANDOM_STRATEGIES = {"retail", "hodl", "gap_long", "gap_short", "bracket_trader", "moon_sniper"}
MOON_TARGETS = [1.5, 2, 3, 5, 10, 20]       # moon_sniper: sell when the price is this many times what it paid
MOON_STAKES = [0.1, 0.25, 0.5]              # moon_sniper: the share of free cash put into each new moonshot


class Trader:
    def __init__(self, p, strategy, params=None):
        self.p, self.strategy = p, strategy
        self.params = params or {}
        self.stats = {"buys": 0, "hits": 0, "busts": 0, "blocked": 0}     # moon_sniper: positions opened, sold at the target, lost to bankruptcy, ticks a sale was refused
        self.seen = set()
        self.opened = {}
        self.last_news = 0
        self.last_price = {}


def act(e, tr):
    p, now = tr.p, e.now
    fresh = []
    if tr.strategy in NEWS_STRATEGIES:             # (reading the wire costs 200 comparisons a tick: only those that use it do)
        fresh = [n for n in e.news_log if n["id"] > tr.last_news]
        if e.news_log:
            tr.last_news = e.news_log[-1]["id"]

    def buy(tk, pct):
        ok, _ = e.trade(p, tk, "buy", pct)
        if ok:
            tr.opened[tk] = now

    def sell(tk):
        if p.hold.get(tk, 0.0) > 0 and e.trade(p, tk, "sell", 1)[0]:
            tr.opened.pop(tk, None)

    def short(tk, pct):
        if p.hold.get(tk, 0.0) == 0:
            ok, _ = e.trade(p, tk, "sell", pct)
            if ok:
                tr.opened[tk] = now

    def cover(tk):
        if p.hold.get(tk, 0.0) < 0 and e.trade(p, tk, "buy", 1)[0]:
            tr.opened.pop(tk, None)

    def close(tk):
        if p.hold.get(tk, 0.0) > 0:
            sell(tk)
        else:
            cover(tk)

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
    elif tr.strategy == "short_seller":
        for n in fresh:
            if n["kind"] in ("breaking", "confirm", "correction") and n["dir"] > 0:
                for tk in n["tickers"][:2]:
                    if tk in e.stocks:
                        short(tk, 0.3)
        for tk, t in list(tr.opened.items()):
            if now - t > 90:
                close(tk)
    elif tr.strategy == "squeeze_hunter":
        for tk, s in e.stocks.items():
            if tk not in p.hold and e._ret(s, 60) > 0.03:
                short(tk, 0.25)
        for tk, t in list(tr.opened.items()):
            if tk not in p.hold:                                  # the short was refused (no cash left) or already closed
                tr.opened.pop(tk, None)
            elif tk in e.stocks and (now - t > 120 or e.stocks[tk].price / e.avg_price(p, tk) > 1.05):
                close(tk)
    elif tr.strategy == "big_size":
        for n in fresh:
            if n["kind"] not in ("breaking", "confirm", "correction"):
                continue
            for tk in n["tickers"][:1]:
                if tk not in e.stocks or p.hold.get(tk, 0.0) != 0:
                    continue
                if n["dir"] > 0:
                    buy(tk, 1.0)
                elif n["dir"] < 0:
                    short(tk, 1.0)
        for tk, t in list(tr.opened.items()):
            if now - t > 60:
                close(tk)
    elif tr.strategy == "mood_oracle":
        if int(now) % 60 == 0:
            want = 1 if e.mood > 0.25 else -1 if e.mood < -0.25 else 0
            have = (p.hold.get("MSI", 0.0) > 0) - (p.hold.get("MSI", 0.0) < 0)
            if have and have != want:
                close("MSI")
            if want == 1 and not have:
                buy("MSI", 0.5)
            elif want == -1 and not have:
                short("MSI", 0.5)
    elif tr.strategy == "hodl":
        if not p.hold and p.cash > 900:
            for tk in random.sample(list(e.stocks), 8):
                buy(tk, 0.12)
    elif tr.strategy in ("gap_long", "gap_short"):
        pre = float(e.settings.get("premarket_seconds", 300))
        phase = now % 1800
        if pre > 0:
            if pre - 8 <= phase < pre - 2 and not p.hold:
                for tk in random.sample([k for k, s in e.stocks.items() if s.asset_type == "equity"], 3):
                    (buy if tr.strategy == "gap_long" else short)(tk, 0.3)
            elif pre + 3 <= phase < pre + 30 and p.hold:
                for tk in list(p.hold):
                    close(tk)
    elif tr.strategy in ("open_follow", "open_fade"):
        pre = float(e.settings.get("premarket_seconds", 300))
        phase = now % 1800
        if pre > 0:
            if pre - 3 <= phase < pre - 1:
                tr.last_price = {tk: s.price for tk, s in e.stocks.items()}     # the last pre-market prices
            elif pre + 2 <= phase < pre + 4 and tr.last_price and not p.hold:
                for tk, s in e.stocks.items():
                    if s.asset_type != "equity" or tk not in tr.last_price:
                        continue
                    jump = s.price / tr.last_price[tk] - 1
                    if abs(jump) > 0.006:
                        up = (jump > 0) == (tr.strategy == "open_follow")
                        (buy if up else short)(tk, 0.15)
                tr.last_price = {}
            elif phase >= pre + 70 and p.hold:
                for tk in list(p.hold):
                    close(tk)
    elif tr.strategy in ("reversal_chaser", "update_chaser"):
        prefix = "REVERSAL:" if tr.strategy == "reversal_chaser" else "UPDATE:"
        for n in fresh:
            if n["kind"] == "breaking" and n["text"].startswith(prefix) and n["tickers"]:
                tk = n["tickers"][0]
                if tk in e.stocks and p.hold.get(tk, 0.0) == 0:
                    (buy if n["dir"] > 0 else short)(tk, 0.3)
        for tk, t in list(tr.opened.items()):
            if now - t > 90:
                close(tk)
    elif tr.strategy == "partner_chaser":
        for n in fresh:
            if n["kind"] == "breaking" and len(n["tickers"]) >= 2:
                tk = n["tickers"][1]
                if tk in e.stocks and p.hold.get(tk, 0.0) == 0:
                    (buy if n["dir"] > 0 else short)(tk, 0.3)
        for tk, t in list(tr.opened.items()):
            if now - t > 90:
                close(tk)
    elif tr.strategy in ("etf_hodl", "bull2_hodl", "bear2_hodl", "bull3_hodl", "bear3_hodl"):
        tk = {"etf_hodl": "AIFX", "bull2_hodl": "2LMSI", "bear2_hodl": "2SMSI", "bull3_hodl": "3LMSI",
              "bear3_hodl": "3SMSI"}[tr.strategy]
        if tk in e.stocks and not p.hold and p.cash > 900:
            buy(tk, 0.9)
    elif tr.strategy == "vol_chaser":
        for tk, s in e.stocks.items():
            if s.asset_type == "equity" and tk not in p.hold and e._vol_multiplier(s) > 1.5 and p.cash > 20:
                buy(tk, 0.2)
        for tk, t in list(tr.opened.items()):
            if now - t > 120:
                sell(tk)
    elif tr.strategy == "moon_hodl":
        for tk, s in e.stocks.items():
            if s.moonshot and tk not in p.hold and s.listed_at and now - s.listed_at < 60 and p.cash > 20:
                buy(tk, 0.25)
        for tk, t in list(tr.opened.items()):
            if now - t > 1200:
                sell(tk)
    elif tr.strategy == "moon_sniper":
        for tk in getattr(e, "_sim_new_moon", ()):
            if tk not in tr.seen and p.cash > 20:
                tr.seen.add(tk)                                   # one try per listing
                buy(tk, tr.params["stake"])
                if tk in p.hold:
                    tr.stats["buys"] += 1
        for tk in list(tr.opened):
            s = e.stocks.get(tk)
            if tk not in p.hold:                                  # the company went bankrupt and the engine closed the position
                tr.opened.pop(tk, None)
                tr.stats["busts"] += 1
            elif s is not None and s.price >= e.avg_price(p, tk) * tr.params["target"]:
                sell(tk)
                if tk not in p.hold:
                    tr.stats["hits"] += 1
                else:                                             # at the target but the sale was refused (the one-second cooldown)
                    tr.stats["blocked"] += 1
    elif tr.strategy == "moon_short":
        for tk, s in e.stocks.items():
            if s.moonshot and tk not in p.hold:
                short(tk, 0.2)
        for tk, t in list(tr.opened.items()):
            if tk in e.stocks and now - t > 600:
                close(tk)
    elif tr.strategy in ("distress_buyer", "distress_short"):
        for tk, s in e.stocks.items():
            ratio = s.fair / s.initial_price
            if s.asset_type == "equity" and tk not in p.hold and 0.25 < ratio < 0.33:
                (buy if tr.strategy == "distress_buyer" else short)(tk, 0.2)
        for tk, t in list(tr.opened.items()):
            if tk in e.stocks and now - t > 600:
                close(tk)
    elif tr.strategy in ("catalyst_follow", "catalyst_fade"):
        for tk, s in e.stocks.items():
            if s.asset_type == "equity" and tk not in p.hold and e._ret(s, 120) > 0.25:
                (buy if tr.strategy == "catalyst_follow" else short)(tk, 0.2)
        for tk, t in list(tr.opened.items()):
            if tk in e.stocks and now - t > 300:
                close(tk)
    elif tr.strategy in ("industry_follow", "industry_fade"):
        for sid in e.sectors:
            members = [s for s in e.stocks.values() if s.sector == sid and s.asset_type == "equity" and not s.moonshot]
            if len(members) < 2:
                continue
            avg = sum(e._ret(s, 120) for s in members) / len(members)
            if abs(avg) > 0.06:
                go_up = (avg > 0) == (tr.strategy == "industry_follow")
                for s in members[:3]:
                    if s.ticker not in p.hold:
                        (buy if go_up else short)(s.ticker, 0.1)
        for tk, t0 in list(tr.opened.items()):
            if tk in e.stocks and now - t0 > 300:
                close(tk)
    elif tr.strategy == "relation_oracle":
        for tk, s in e.stocks.items():
            if s.asset_type != "equity" or tk not in e.relations:
                continue
            r = e._ret(s, 30)
            if abs(r) > 0.04:
                for c in e.relations.customers(tk):
                    if c in e.stocks:
                        (buy if r > 0 else short)(c, 0.1)
                for v in e.relations.rivals(tk):
                    if v in e.stocks:
                        (short if r > 0 else buy)(v, 0.1)
        for tk, t0 in list(tr.opened.items()):
            if tk in e.stocks and now - t0 > 120:
                close(tk)
    elif tr.strategy == "bracket_trader":
        if not p.hold and not p.orders and p.cash > 100 and random.random() < 0.03:
            tk = random.choice([k for k, s in e.stocks.items() if s.asset_type == "equity" and not s.moonshot])
            buy(tk, 0.3)
            if tk in p.hold:
                px = e.stocks[tk].price
                e.place_bracket(p, tk, px * 1.01, px * 0.99)
    elif tr.strategy == "trend_follower":
        for tk, s in e.stocks.items():
            if s.asset_type != "commodity" or tk in p.hold:
                continue
            r = e._ret(s, 600)
            if r > 0.01:
                buy(tk, 0.2)
            elif r < -0.01:
                short(tk, 0.2)
        for tk, t in list(tr.opened.items()):
            if now - t > 1200:
                close(tk)
    elif tr.strategy == "earnings_runup":
        for tk, s in e.stocks.items():
            if s.next_earn and 0 < s.next_earn - now <= 30 and tk not in p.hold and p.cash > 20:
                buy(tk, 0.2)
        for tk, t in list(tr.opened.items()):
            s = e.stocks.get(tk)
            if s is None or (s.next_earn and s.next_earn - now > 60) or now - t > 90:
                sell(tk)


def run(hours=6.0, seed=1, settings=None, quiet=False, copies=None, detail=False):
    """Simulate `hours` of play. Seasons run as configured, so season winners can be measured.

    `copies` is the number of traders per strategy: a number (every strategy), or a dict {strategy: number} (others
    keep COPIES). `detail=True` adds `bots` to the result: one row per trader of a random strategy (strategy,
    parameters, return, turnover, positions opened, hit and bust counts)."""
    random.seed(seed)
    e = engine_mod.Engine(state_file=None)
    e.settings.update(settings or {})
    t0 = time.time()
    e.season_end = t0 + 3600           # (the simulator measures season winners over its own hour-long seasons)
    traders = []
    combos = [(t, st) for t in MOON_TARGETS for st in MOON_STAKES]
    for strat in STRATEGIES:
        n = copies.get(strat, COPIES) if isinstance(copies, dict) else (copies or COPIES)
        for i in range(n):
            p, err = e.join(f"{strat[:11]}{i}")
            assert p, err
            params = {"target": combos[i % len(combos)][0], "stake": combos[i % len(combos)][1]} if strat == "moon_sniper" else None
            traders.append(Trader(p, strat, params))
    start = {tr.p.token: e.equity(tr.p) for tr in traders}
    drift = 0.0
    moons_seen = set()    # every moonshot that was listed during the run (not counting the ones the game starts with)
    seasons = []          # per season: sorted human season returns
    hourly_moves = []     # |1h price change| per stock
    last_hour = {tk: s.price for tk, s in e.stocks.items()}
    ticks = int(hours * 3600)
    for i in range(ticks):
        now = t0 + i
        if now >= e.season_end:
            seasons.append(sorted(e.season_return(tr.p) for tr in traders))
        e.tick(now=now)
        e._sim_new_moon = [tk for tk, s in e.stocks.items() if s.moonshot and s.listed_at and now - s.listed_at < 5]
        moons_seen.update(e._sim_new_moon)
        for tr in traders:
            act(e, tr)
        drift = max(drift, abs(e.total_tokens() - e.minted))
        if i and i % 3600 == 0:
            hourly_moves += [abs(s.price / last_hour[tk] - 1) for tk, s in e.stocks.items() if tk in last_hour]
            last_hour = {tk: s.price for tk, s in e.stocks.items()}

    by = defaultdict(list)
    turnover = defaultdict(list)
    for tr in traders:
        by[tr.strategy].append(e.equity(tr.p) / start[tr.p.token] - 1)
        turnover[tr.strategy].append(tr.p.fees_paid / engine_mod.FEE / start[tr.p.token])   # money traded, as a multiple of starting money
    st = e.house_stats()
    hourly_moves.sort()
    q = lambda arr, f: arr[min(len(arr) - 1, int(f * len(arr)))] if arr else 0.0
    m = {"drift": drift, "fees": st["fees"], "house_pnl": st["house_pnl"],
         "liquidity_pnl": st["liquidity_pnl"],
         "season_top": sum(r[-1] for r in seasons) / len(seasons) if seasons else 0.0,
         "season_median": sum(r[len(r) // 2] for r in seasons) / len(seasons) if seasons else 0.0,
         "move_1h_median": q(hourly_moves, 0.5), "move_1h_p90": q(hourly_moves, 0.9),
         "strategies": {k: sum(v) / len(v) for k, v in by.items()},
         "turnover": {k: sum(v) / len(v) for k, v in turnover.items()},
         "delisted": len(e.delisted),
         "ref_dev_p90": q(sorted(abs(s.price / s.initial_price - 1) for s in e.stocks.values()), 0.9)}
    if detail:
        m["bots"] = [{"s": tr.strategy, "params": tr.params, "ret": e.equity(tr.p) / start[tr.p.token] - 1,
                      "turnover": tr.p.fees_paid / engine_mod.FEE / start[tr.p.token], "trades": tr.p.trades, **tr.stats}
                     for tr in traders if tr.strategy in RANDOM_STRATEGIES]
        m["moonshots_listed"] = len(moons_seen)
        m["stats_v"] = 2                                          # (version 1 counted a refused sale as a hit)
    if quiet:
        return m
    print("engine:", os.path.basename(os.path.dirname(engine_mod.__file__)))
    print(f"{hours:g}h simulated, seed {seed}, {len(e.stocks)} listings, delisted {e.delisted}")
    print(f"token invariant max drift: {drift:.2e}")
    print("strategy        mean ret   best     worst    trades")
    for strat in STRATEGIES:
        rs = by[strat]
        trades = sum(tr.p.trades for tr in traders if tr.strategy == strat) / COPIES
        print(f"{strat:14} {sum(rs) / len(rs):+8.2%} {max(rs):+8.2%} {min(rs):+8.2%} {trades:8.0f}")
    print(f"seasons: {len(seasons)}, avg winner {m['season_top']:+.1%}, avg median player {m['season_median']:+.1%}")
    print(f"1h stock moves: median {m['move_1h_median']:.1%}, 90th pct {m['move_1h_p90']:.1%}")
    print("house:", {k: round(v, 2) if isinstance(v, float) else v for k, v in st.items()})
    moves = sorted(s.price / s.initial_price - 1 for s in e.stocks.values())
    print(f"price vs reference: min {moves[0]:+.1%}  median {moves[len(moves) // 2]:+.1%}  max {moves[-1]:+.1%}")
    return m


if __name__ == "__main__":
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    sys.exit(1 if run(hours, seed)["drift"] > 1e-6 else 0)
