"""Index drift probe: does the market index (or an average stock) drift over a two-hour game?

Usage:  python index_probe.py [seeds=200] [hours=2] [first_seed=80000] [name=value ...]

The engine runs alone (no traders). For every seed it takes the simple return of the MSI 50, of the equal-weighted
average of all ordinary companies, of the themed ETF AIFX and of the leveraged products 2LMSI and 2SMSI over the whole run,
then reports the mean across seeds, its standard error and the t-statistic. In a fair market the expected return is zero
(the leveraged products lose a little to decay, which is not an edge). A standard error across seeds is the honest one:
every stock in a seed shares the same market moves.
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

engine.Engine._public = lambda self: None
engine.Engine._board = lambda self: None

SERIES = ("MSI", "average company", "AIFX", "2LMSI", "2SMSI")


def workers():
    return int(os.environ.get("EDGE_WORKERS", min(6, os.cpu_count() or 1)))


def run(args):
    seed, hours, settings = args
    random.seed(seed)
    e = engine.Engine(state_file=None)
    e.settings.update(settings)
    t0 = time.time()
    e.tick(t0)
    companies = [tk for tk, s in e.stocks.items() if s.asset_type == "equity" and not s.moonshot]
    start = {tk: e.stocks[tk].price for tk in e.stocks}
    for i in range(1, int(hours * 3600) + 1):
        e.tick(t0 + i)
    out = {k: e.stocks[k].price / start[k] - 1 for k in ("MSI", "AIFX", "2LMSI", "2SMSI")}
    rets = [e.stocks[tk].price / start[tk] - 1 for tk in companies if tk in e.stocks]
    out["average company"] = sum(rets) / len(rets)
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if "=" not in a]
    overrides = {k: json.loads(v) for k, v in (a.split("=", 1) for a in sys.argv[1:] if "=" in a)}
    seeds = int(args[0]) if args else 200
    hours = float(args[1]) if len(args) > 1 else 2.0
    first = int(args[2]) if len(args) > 2 else 80000
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers()) as ex:
        res = list(ex.map(run, [(first + i, hours, overrides) for i in range(seeds)]))
    print(f"{seeds} seeds x {hours:g} h, {workers()} processes, {time.time() - t0:.0f} s")
    print(f"{'series':18} {'mean return':>12} {'std err':>9} {'t':>6} {'median':>9}")
    for k in SERIES:
        xs = sorted(r[k] for r in res)
        m = sum(xs) / len(xs)
        se = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) / math.sqrt(len(xs))
        print(f"{k:18} {m:+12.3%} {se:9.3%} {m / se:+6.1f} {xs[len(xs) // 2]:+9.3%}")
