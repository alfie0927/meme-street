"""Many-bot, many-seed strategy study.

Usage:
    python bots.py all  [seeds=48] [hours=2] [first_seed=2000]   every strategy; the ones that make random choices get 100 bots
    python bots.py moon [seeds=48] [hours=6] [first_seed=1000]   the moonshot study: moon_sniper (100 bots, targets 1.5x to 20x),
                                                                 moon_hodl, moon_short, and random traders for comparison
    python bots.py moondense [seeds=54] [hours=2] [first_seed=3000]   the same, in a market where a new moonshot lists every 45 seconds
                                                                 (up to 30 at once) instead of every 15 minutes: about 16 times
                                                                 as many listings per run, so the fairness of moonshots can be
                                                                 measured much more precisely
    python bots.py report moon|moondense|all file.json [file.json ...]     print the report again, or for several saved studies together
Set EDGE_WORKERS to the number of parallel processes (default 14). Results are also written to sim_results/bots_<mode>_<first seed>.json (a subfolder, because every .json file in the project folder itself is
read by the game as a content pack).

What the numbers mean. Each seed is a separate simulated market. Players' trades never move a price, so every bot that
follows a fixed rule makes exactly the same trades as its copies; only the strategies that make random choices (retail,
hodl, gap_long, gap_short, bracket_trader and moon_sniper, whose bots each have their own target and stake) get 100 bots.
The standard error is taken across seeds (each seed's average over its bots is one observation), because bots in the same
market share its luck. "turnover" is how much a bot traded as a multiple of its starting money; "per turnover" is its
profit or loss divided by that, which for a fair market is minus the fee rate: it is what the house earns on what players
trade."""
import json, math, os, sys, time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim  # noqa: E402

HUNDRED = {s: 100 for s in sim.RANDOM_STRATEGIES}


def one(args):
    seed, hours, strategies, copies, settings = args
    sim.engine_mod.Engine._public = lambda self: None      # (not used by the strategies, and slow; done here, in the worker,
    sim.engine_mod.Engine._board = lambda self: None       # so that importing this module changes nothing)
    sim.STRATEGIES = list(strategies)
    try:
        return sim.run(hours, seed, settings, quiet=True, copies=copies, detail=True)
    except Exception as e:                       # one bad seed must not throw away the others
        return {"error": f"seed {seed}: {type(e).__name__}: {e}"}


def mean_se(xs):
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    m = sum(xs) / n
    if n < 2:
        return m, 0.0
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, sd / math.sqrt(n)


def pct(xs, f):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else 0.0


def run_all(runs, strategies):
    print(f"{'strategy':16} {'bots':>5} {'mean ret':>9} {'std err':>8} {'t':>6} {'profit%':>8} {'turnover':>9} {'ret/turnover':>13}")
    for strat in strategies:
        per_seed = [r["strategies"][strat] for r in runs if strat in r["strategies"]]
        if not per_seed:
            continue
        m, se = mean_se(per_seed)
        t = m / se if se > 0 else 0.0
        bots = [b for r in runs for b in r.get("bots", []) if b["s"] == strat]
        profit = f"{100 * sum(1 for b in bots if b['ret'] > 0) / len(bots):7.1f}%" if bots else "     n/a"
        turn = sum(r["turnover"][strat] for r in runs if strat in r["turnover"]) / len(per_seed)
        per_turn = m / turn if turn > 0 else 0.0
        flag = "EDGE" if t > 2 and m > 0 else ""
        print(f"{strat:16} {len(bots) // len(runs) if bots else 1:5d} {m:+9.2%} {se:8.2%} {t:+6.1f} {profit:>8} {turn:9.2f} {per_turn:+13.3%}  {flag}")
    fees = sum(r["fees"] for r in runs) / len(runs)
    house = sum(r["house_pnl"] for r in runs) / len(runs)
    print(f"house over {len(runs)} seeds: avg fees {fees:.0f} MB, avg house P&L {house:+.0f} MB; max token drift {max(r['drift'] for r in runs):.1e}")


def moon_report(runs):
    bots = [b for r in runs for b in r["bots"] if b["s"] == "moon_sniper"]
    listed = sum(r["moonshots_listed"] for r in runs) / len(runs)
    print(f"\nmoon_sniper: {len(bots) // len(runs)} bots x {len(runs)} seeds = {len(bots)} bot-runs; "
          f"{listed:.1f} new moonshots listed per run\n")
    good = [r for r in runs if r.get("stats_v") == 2]            # (the first version of the counters counted refused sales as hits)
    gb = [b for r in good for b in r["bots"] if b["s"] == "moon_sniper"]
    opened = sum(b["buys"] for b in gb)
    hits = sum(b["hits"] for b in gb)
    busts = sum(b["busts"] for b in gb)
    blocked = sum(b["blocked"] for b in gb)
    if opened:
        print(f"positions opened {opened} (in {len(good)} of the {len(runs)} runs, the ones with correct counters): hit their target {hits} ({hits / opened:.1%}), "
              f"went bankrupt {busts} ({busts / opened:.1%}), still open at the end {opened - hits - busts} ({(opened - hits - busts) / opened:.1%}); "
              f"a sale was refused (the one-second cooldown) on {blocked} bot-ticks")
    rets = [b["ret"] for b in bots]
    print(f"return per bot-run: mean {sum(rets) / len(rets):+.2%}  median {pct(rets, .5):+.2%}  5th pct {pct(rets, .05):+.2%}  "
          f"95th pct {pct(rets, .95):+.2%}  best {max(rets):+.1%}  worst {min(rets):+.1%}  profitable {100 * sum(1 for x in rets if x > 0) / len(rets):.1f}%\n")
    print(f"{'target':>7} {'stake':>6} {'bots':>5} {'mean ret':>9} {'std err':>8} {'t':>6} {'median':>8} {'profit%':>8} {'hit%':>6} {'bust%':>6}")
    for kind in ("target", "stake"):
        keys = sorted({b["params"][kind] for b in bots})
        for k in keys:
            sel = [b for b in bots if b["params"][kind] == k]
            by_seed = defaultdict(list)
            for i, r in enumerate(runs):
                by_seed[i] = [b["ret"] for b in r["bots"] if b["s"] == "moon_sniper" and b["params"][kind] == k]
            seed_means = [sum(v) / len(v) for v in by_seed.values() if v]
            m, se = mean_se(seed_means)
            t = m / se if se > 0 else 0.0
            selg = [b for b in gb if b["params"][kind] == k]
            op = sum(b["buys"] for b in selg)
            h = sum(b["hits"] for b in selg)
            bu = sum(b["busts"] for b in selg)
            label_t = f"{k}x" if kind == "target" else "all"
            label_s = f"{k:.0%}" if kind == "stake" else "all"
            print(f"{label_t:>7} {label_s:>6} {len(sel):5d} {m:+9.2%} {se:8.2%} {t:+6.1f} {pct([b['ret'] for b in sel], .5):+8.2%} "
                  f"{100 * sum(1 for b in sel if b['ret'] > 0) / len(sel):7.1f}% {100 * h / max(op, 1):5.1f}% {100 * bu / max(op, 1):5.1f}%")
        print()


def save(mode, runs, first):
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_results")     # (not the project folder itself: every .json there is read as a content pack)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, f"bots_{mode}_{first}.json"), "w") as fh:
        json.dump(runs, fh)


def report(args):
    mode = args[0]
    runs = []
    for path in args[1:]:
        with open(path) as fh:
            runs += json.load(fh)
    strategies = list(runs[0]["strategies"])
    print(f"== {mode}: {len(runs)} seeds from {len(args) - 1} file(s)")
    run_all(runs, strategies)
    if mode.startswith("moon"):
        moon_report(runs)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "report":
        return report(sys.argv[2:])
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    hours = float(sys.argv[3]) if len(sys.argv) > 3 else (6.0 if mode == "moon" else 2.0)
    first = int(sys.argv[4]) if len(sys.argv) > 4 else {"moon": 1000, "moondense": 3000}.get(mode, 2000)
    settings = {}
    if mode == "moon":
        strategies = ["moon_sniper", "moon_hodl", "moon_short", "retail", "hodl"]
        copies = {"moon_sniper": 100, "retail": 100, "hodl": 100}
    elif mode == "moondense":
        strategies = ["moon_sniper", "moon_hodl"]
        copies = {"moon_sniper": 100}
        settings = {"moonshot_mean_seconds": 45, "moonshot_max": 30}
    else:
        strategies = list(sim.STRATEGIES)
        copies = HUNDRED
    jobs = [(first + i, hours, strategies, copies, settings) for i in range(seeds)]
    workers = int(os.environ.get("EDGE_WORKERS", 14))
    t0 = time.time()
    print(f"{mode}: {seeds} seeds x {hours:g} h, seeds {first}..{first + seeds - 1}, {workers} processes", flush=True)
    runs = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(one, jobs)):
            if "error" in r:
                print(f"  {r['error']} (left out)", flush=True)
                continue
            runs.append(r)
            print(f"  seed {first + i} done ({time.time() - t0:.0f} s)", flush=True)
            save(mode, runs, first)               # (so a long study that is interrupted keeps what it has)
    if not runs:
        sys.exit("every seed failed")
    print(f"\n== {mode}: {seeds} seeds x {hours:g} h ({time.time() - t0:.0f} s)")
    run_all(runs, strategies)
    if mode.startswith("moon"):
        moon_report(runs)


if __name__ == "__main__":
    main()
