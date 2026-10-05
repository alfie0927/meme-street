"""Paired comparison: how much does one setting change a strategy's result?

Usage:  python paired.py [seeds=16] [hours=2] [first_seed=1000] strategies=value,hodl  name=setting[,setting] ...

Every configuration runs on the *same* seeds, so the market paths are identical except for what the setting
changes. The difference per seed between a configuration and the first (the baseline) is far less noisy than
comparing two separate runs: a +0.5% effect that is invisible in `edge.py` (noise of about 1%) shows up here.

Each configuration is written  label:setting=value,setting=value  (JSON values). The first is the baseline.
Example:
  python paired.py 16 2 1000 strategies=value,hodl  base:  no_reversion:mean_reversion_halflife_days=0 \\
      no_envelope:daily_move_cap=0 no_notes:'rating_review_seconds=[1e9,1e9]'

Prints, per configuration and strategy: the mean return, and the mean difference from the baseline with its
standard error and t-statistic. A clearly positive difference for a profitable strategy means the setting
that was switched off was paying that strategy.
The engine's public-state building is skipped (it isn't needed here), which makes runs about twice as fast.
Set EDGE_WORKERS to change the number of parallel processes (default 8; each uses about 150 MB).
"""
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim  # noqa: E402

sim.engine_mod.Engine._public = lambda self: None
sim.engine_mod.Engine._board = lambda self: None


def workers():
    return int(os.environ.get("EDGE_WORKERS", min(8, os.cpu_count() or 1)))


def one(args):
    label, seed, hours, settings, strategies = args
    sim.STRATEGIES = list(strategies)
    return label, seed, sim.run(hours, seed, dict(settings), quiet=True)["strategies"]


def parse_config(text):
    label, _, rest = text.partition(":")
    settings = {}
    for part in [p for p in rest.split(",") if p] if "[" not in rest else [rest]:
        k, _, v = part.partition("=")
        settings[k] = json.loads(v)
    return label, settings


def compare(configs, strategies, seeds=16, hours=2.0, first=1000):
    jobs = [(label, first + i, hours, settings, strategies) for label, settings in configs for i in range(seeds)]
    results = {}
    with ProcessPoolExecutor(max_workers=workers()) as ex:
        for label, seed, strat in ex.map(one, jobs):
            results[(label, seed)] = strat
    base = configs[0][0]
    out = []
    for label, _ in configs:
        for strat in strategies:
            xs = [results[(label, first + i)].get(strat, 0.0) for i in range(seeds)]
            diffs = [results[(label, first + i)].get(strat, 0.0) - results[(base, first + i)].get(strat, 0.0)
                     for i in range(seeds)]
            mean = sum(xs) / len(xs)
            dmean = sum(diffs) / len(diffs)
            se = math.sqrt(sum((x - dmean) ** 2 for x in diffs) / max(1, len(diffs) - 1)) / math.sqrt(len(diffs))
            out.append((label, strat, mean, dmean, se, (dmean / se) if se > 0 else 0.0))
    return out


if __name__ == "__main__":
    pos = [a for a in sys.argv[1:] if ":" not in a and not a.startswith("strategies=")]
    seeds = int(pos[0]) if pos else 16
    hours = float(pos[1]) if len(pos) > 1 else 2.0
    first = int(pos[2]) if len(pos) > 2 else 1000
    strategies = next((a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("strategies=")),
                      ["value", "hodl"])
    configs = [parse_config(a) for a in sys.argv[1:] if ":" in a]
    if not configs:
        sys.exit(__doc__)
    t0 = time.time()
    rows = compare(configs, strategies, seeds, hours, first)
    print(f"== paired comparison: {seeds} seeds x {hours:g}h, first seed {first}; baseline = {configs[0][0]}")
    print(f"{'config':22} {'strategy':14} {'mean ret':>9} {'vs baseline':>12} {'std err':>8} {'t':>6}")
    for label, strat, mean, dmean, se, t in rows:
        diff = "" if label == configs[0][0] else f"{dmean:+12.2%}"
        print(f"{label:22} {strat:14} {mean:+9.2%} {diff:>12} {'' if label == configs[0][0] else f'{se:8.2%}'} "
              f"{'' if label == configs[0][0] else f'{t:+6.1f}'}")
    print(f"({time.time() - t0:.0f}s)")
