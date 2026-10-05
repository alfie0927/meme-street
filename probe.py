"""Drift probe: do stocks below their reference price beat the rest? (a hidden mean-reversion detector)

Usage:  python probe.py [seeds=60] [hours=3] [name=value ...]

Runs the engine alone (no traders) on many seeds. At every game-day boundary it compares the next 30-minute
return of stocks that are below 97% of their reference price with all other stocks (market move removed),
averages per seed, and reports the mean, standard error and t-statistic across seeds.

With no price impact, a persistent positive number means "buy the dips" is paid for by the house. Use it to
find *where* an edge comes from by switching mechanisms off with settings overrides, e.g.
  python probe.py 60 3 mood_tilt=0
  python probe.py 60 3 news_followups=false
  python probe.py 60 3 daily_move_cap=0
  python probe.py 60 3 event_mean_seconds=1e9 issue_mean_seconds=1e9
A single configuration has a standard error near 0.1% per 30 minutes, so only compare large differences.
"""
import json, math, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine  # noqa: E402

engine.Engine._public = lambda self: None   # public state isn't needed here and is slow to build
engine.Engine._board = lambda self: None


def workers():
    """Parallel processes: 8 by default (each uses about 150 MB). Set EDGE_WORKERS to change it."""
    return int(os.environ.get("EDGE_WORKERS", min(8, os.cpu_count() or 1)))


def run(args):
    seed, hours, settings = args
    random.seed(seed)
    e = engine.Engine(state_file=None, bots=False)
    e.settings.update(settings)
    t0 = time.time()
    init = {tk: s.initial_price for tk, s in e.stocks.items()}
    snaps = []
    for i in range(int(hours * 3600) + 1):
        e.tick(t0 + i)
        if i % 1800 == 0:
            snaps.append({tk: s.price for tk, s in e.stocks.items() if s.asset_type == "equity"})
    lows = []
    for a, b in zip(snaps, snaps[1:]):
        rets = {tk: b[tk] / a[tk] - 1 for tk in a if tk in b}
        market = sum(rets.values()) / len(rets)
        lows += [r - market for tk, r in rets.items() if a[tk] / init[tk] < 0.97]
    return sum(lows) / len(lows) if lows else None


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if "=" not in a]
    overrides = {k: json.loads(v) for k, v in (a.split("=", 1) for a in sys.argv[1:] if "=" in a)}
    seeds = int(args[0]) if args else 60
    hours = float(args[1]) if len(args) > 1 else 3.0
    with ProcessPoolExecutor(max_workers=workers()) as ex:
        res = [x for x in ex.map(run, [(s, hours, overrides) for s in range(1000, 1000 + seeds)]) if x is not None]
    m = sum(res) / len(res)
    se = math.sqrt(sum((x - m) ** 2 for x in res) / (len(res) - 1)) / math.sqrt(len(res))
    print(f"below-reference stocks beat the rest by {m:+.3%} per 30 min (se {se:.3%}, t {m / se:+.1f}, {len(res)} seeds)")
