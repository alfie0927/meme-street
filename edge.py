"""Many-seed edge check: does any simulated strategy beat the house?

Usage:  python edge.py [seeds=20] [hours=2] [first_seed=100] [name=value ...]

Runs sim.py on many independent seeds in parallel and reports, for every strategy, the mean return per
seed, its standard error and a t-statistic. With no price impact, any strategy whose mean return is
positive by more than two standard errors is being paid by the house: that is a failure.

Settings overrides can be given as name=value (JSON values), e.g.  mean_reversion_halflife_days=730
Use _strategies='["value","hodl"]' to run only some strategies.
Exit code is 1 if the token invariant drifts or any strategy shows an edge.
"""
import json, math, os, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim  # noqa: E402

# Public state and the leaderboard aren't used by the strategies and are slow to build: skipping them makes runs
# about ten times faster.
sim.engine_mod.Engine._public = lambda self: None
sim.engine_mod.Engine._board = lambda self: None


def workers():
    """Parallel processes: 8 by default (each uses about 150 MB). Set EDGE_WORKERS to change it."""
    return int(os.environ.get("EDGE_WORKERS", min(8, os.cpu_count() or 1)))


def one(args):
    seed, hours, settings = args
    settings = dict(settings)
    if "_strategies" in settings:  # e.g. _strategies='["value","hodl"]' to run only those traders (faster)
        sim.STRATEGIES = settings.pop("_strategies")
    return sim.run(hours, seed, settings, quiet=True)


def check(seeds=20, hours=2.0, first=100, settings=None, label="", quiet=False):
    jobs = [(first + i, hours, settings or {}) for i in range(seeds)]
    with ProcessPoolExecutor(max_workers=workers()) as ex:
        runs = list(ex.map(one, jobs))
    rows, failed = [], False
    for strat in sim.STRATEGIES:
        xs = [r["strategies"][strat] for r in runs if strat in r["strategies"]]
        if not xs:
            continue
        mean = sum(xs) / len(xs)
        sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / max(1, len(xs) - 1))
        se = sd / math.sqrt(len(xs))
        t = mean / se if se > 0 else 0.0
        flag = "EDGE" if t > 2 and mean > 0 else ""
        failed |= bool(flag)
        rows.append((strat, mean, se, t, flag))
    drift = max(r["drift"] for r in runs)
    fees = sum(r["fees"] for r in runs) / len(runs)
    house = sum(r["house_pnl"] for r in runs) / len(runs)
    if not quiet:
        print(f"== {label or 'default settings'}: {seeds} seeds x {hours:g}h, first seed {first}")
        print(f"{'strategy':16} {'mean ret':>9} {'std err':>8} {'t':>6}")
        for strat, mean, se, t, flag in rows:
            print(f"{strat:16} {mean:+9.2%} {se:8.2%} {t:+6.1f}  {flag}")
        print(f"avg fees {fees:.0f} MB, avg house P&L {house:+.0f} MB, max token drift {drift:.1e}")
    return rows, drift > 1e-6 or failed


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if "=" not in a]
    overrides = {k: json.loads(v) for k, v in (a.split("=", 1) for a in sys.argv[1:] if "=" in a)}
    seeds = int(args[0]) if args else 20
    hours = float(args[1]) if len(args) > 1 else 2.0
    first = int(args[2]) if len(args) > 2 else 100
    t0 = time.time()
    _, bad = check(seeds, hours, first, overrides, ", ".join(f"{k}={v}" for k, v in overrides.items()))
    print(f"({time.time() - t0:.0f}s)")
    sys.exit(1 if bad else 0)
