"""Compare setting overrides across seeds using sim.py.

Usage:  python tune.py configs.json [hours=6] [seeds=6] [first_seed=1]

Use a fresh first_seed to confirm a result: configs run on the same seeds share market paths.

configs.json maps a name to settings overrides, for example:
  {"current": {}, "calmer": {"volatility_scale": 0.8}}
A config may set "_strategies" to a list of sim.py strategies to run only those traders.

Columns: winner / median = average season return of the best / median simulated player;
1h med / p90 = typical and large one-hour stock moves; liqPnL = house result from pool liquidity
(should stay well below fees); value / hodl = mean return of those strategies (near zero means
no free edge); refdev = 90th percentile distance of prices from their reference.
"""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim  # noqa: E402


def one(args):
    name, settings, seed, hours = args
    settings = dict(settings)
    if "_strategies" in settings:
        sim.STRATEGIES = settings.pop("_strategies")
    return name, seed, sim.run(hours, seed, settings, quiet=True)


def grid(configs, seeds=range(1, 7), hours=6.0):
    jobs = [(n, c, s, hours) for n, c in configs.items() for s in seeds]
    out = {}
    with ProcessPoolExecutor() as ex:
        for name, seed, m in ex.map(one, jobs):
            out.setdefault(name, []).append(m)
    print(f"{'config':22} {'winner':>8} {'median':>8} {'1h med':>7} {'1h p90':>7} {'fees':>7} {'liqPnL':>8} "
          f"{'house':>8} {'value':>7} {'hodl':>7} {'drift':>8} {'refdev':>7}")
    for name, ms in out.items():
        avg = lambda k: sum(m[k] for m in ms) / len(ms)
        strat = lambda k: sum(m["strategies"].get(k, 0.0) for m in ms) / len(ms)
        print(f"{name:22} {avg('season_top'):+8.1%} {avg('season_median'):+8.1%} {avg('move_1h_median'):7.1%} "
              f"{avg('move_1h_p90'):7.1%} {avg('fees'):7.0f} {avg('liquidity_pnl'):+8.0f} {avg('house_pnl'):+8.0f} "
              f"{strat('value'):+7.1%} {strat('hodl'):+7.1%} {max(m['drift'] for m in ms):8.1e} {avg('ref_dev_p90'):7.1%}")


if __name__ == "__main__":
    configs = json.load(open(sys.argv[1], encoding="utf-8"))
    hours = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    seeds = range(first, first + n)
    t = time.time()
    grid(configs, seeds, hours)
    print(f"({time.time() - t:.0f}s)")
