"""Catalyst probe: after a stock jumps (or falls) 25% or more in two minutes, what does it do in the next five?

Usage:  python catalyst_probe.py [seeds=150] [hours=2] [first_seed=60000] [name=value ...]

This is the thing the `catalyst_follow` / `catalyst_fade` strategies of sim.py bet on, measured directly: the engine runs
alone (no traders), and every time an equity (moonshots separately) is 25% above (or below) its price two minutes
earlier, the probe notes its price and, five minutes later, the return since. A stock is not counted again for five
minutes after an event, the way a position is held for five minutes. A stock that goes bankrupt in the window is
valued at the price holders were paid (so it is not dropped from the average, and the loss counts).

In a fair market the average forward return after a jump is zero, whatever the jump looked like. The standard error is
taken across seeds (each seed's events are one cluster), because events within one market are not independent.
Fees (0.1% each way) are not included: the number is the gross move.
"""
import json
import math
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine  # noqa: E402

engine.Engine._public = lambda self: None   # not needed here, and slow to build
engine.Engine._board = lambda self: None

HOLD = 300          # seconds a position would be held
LOOK = 120          # seconds the jump is measured over
JUMP = 0.25


def workers():
    return int(os.environ.get("EDGE_WORKERS", min(6, os.cpu_count() or 1)))


def run(args):
    seed, hours, settings = args
    random.seed(seed)
    e = engine.Engine(state_file=None)
    e.settings.update(settings)
    t0 = time.time()
    last = {}                    # ticker -> last known price
    cooldown = {}                # ticker -> time before which it is not counted again
    pending = []                 # [due time, ticker, entry price, kind, size]
    out = []
    for i in range(int(hours * 3600) + 1):
        now = t0 + i
        e.tick(now)
        for tk, s in e.stocks.items():
            last[tk] = s.price
        for ev in [x for x in pending if x[0] <= now]:
            pending.remove(ev)
            _, tk, entry, kind, size = ev
            if tk in e.stocks:
                price = e.stocks[tk].price
            else:                                      # delisted: holders were paid the final price (the last move is not in `last`)
                price = e.archive.get(tk, {}).get("final_price", last.get(tk, entry))
            out.append((kind, size, price / entry - 1))
        for tk, s in e.stocks.items():
            if s.asset_type != "equity" or cooldown.get(tk, 0) > now:
                continue
            r = e._ret(s, LOOK)
            if abs(r) > JUMP:
                cooldown[tk] = now + HOLD
                kind = ("moon" if s.moonshot else "ordinary") + (" up" if r > 0 else " down")
                pending.append([now + HOLD, tk, s.price, kind, abs(r)])
    return seed, out


def summarize(results):
    groups = {}
    for seed, rows in results:
        for kind, size, fwd in rows:
            groups.setdefault(kind, {}).setdefault(seed, []).append(fwd)
            big = "big " + kind if size >= 0.40 else None
            if big:
                groups.setdefault(big, {}).setdefault(seed, []).append(fwd)
    print(f"{'after a 25%+ move in 2 min':28} {'events':>7} {'seeds':>6} {'next 5 min':>11} {'std err':>8} {'t':>6}")
    for kind in sorted(groups):
        by = groups[kind]
        n = sum(len(v) for v in by.values())
        tot = sum(sum(v) for v in by.values())
        m = tot / n
        resid = sum((sum(v) - m * len(v)) ** 2 for v in by.values())
        se = math.sqrt(resid) / n if len(by) > 1 else 0.0
        t = m / se if se else 0.0
        print(f"{kind:28} {n:7d} {len(by):6d} {m:+11.3%} {se:8.3%} {t:+6.1f}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if "=" not in a]
    overrides = {k: json.loads(v) for k, v in (a.split("=", 1) for a in sys.argv[1:] if "=" in a)}
    seeds = int(args[0]) if args else 150
    hours = float(args[1]) if len(args) > 1 else 2.0
    first = int(args[2]) if len(args) > 2 else 60000
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers()) as ex:
        results = list(ex.map(run, [(first + i, hours, overrides) for i in range(seeds)]))
    print(f"{seeds} seeds x {hours:g} h, {workers()} processes, {time.time() - t0:.0f} s")
    summarize(results)
