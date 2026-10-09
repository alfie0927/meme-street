"""What is a player worth? A small, honest model of the fee income.

Usage:  python revenue_model.py [fee=0.001] [balance=10000] [signups=1000] [mb_value=0] [assumptions.json] [--md]

The game earns the fee on every trade (0.1% per side), and nothing else is built in. In a fair market a player's money
is only ever used up by fees (the other side of their trades averages zero), so what a player is worth to the game is
bounded by their balance. The model follows that:

    r         = fee x trades per day x size              the share of their balance the fees take each day
    fees paid = balance x (1 - (1 - r) ** days active)   (a player who leaves keeps what is left; it is not income)

Everything about HOW people play is an ASSUMPTION (the table ARCHETYPES below), not a measurement: there are no real
players yet. Change them in a JSON file (a list of [name, share, trades_per_day, size, days_active]) and replace them with
real numbers from the closed test (the admin page's players-and-fees panel and `fees_paid` per player). The simulator's
bots are far more active than people (a bracket-trading bot trades 15 times its balance in two game hours), so their
turnover is printed only to show the scale, never used.

`mb_value` is what 1 MB is worth in your currency when real money is involved (0 = print MB only). It is an open
question in ROADMAP.md.
"""
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# name, share of sign-ups, trades per day, size of a trade as a share of the balance, days they keep playing
ARCHETYPES = [
    ("Looker", 0.40, 1, 0.10, 3),         # signs up, looks around, makes a trade or two, drifts away
    ("Casual", 0.30, 4, 0.25, 14),        # a few trades a day for a couple of weeks
    ("Regular", 0.20, 15, 0.25, 30),      # trades most of the day for a month
    ("Active", 0.08, 60, 0.25, 30),       # watches the wire, trades often
    ("Grinder", 0.02, 300, 0.25, 21),     # trades constantly (a bot-like human), burns through the balance
]
FEES = (0.0005, 0.001, 0.002, 0.003)


def fees_paid(balance, fee, trades_per_day, size, days):
    """Fees one player pays before they stop. Never more than their balance."""
    r = min(1.0, fee * trades_per_day * size)
    return balance * (1.0 - (1.0 - r) ** days)


def model(archetypes=ARCHETYPES, fee=0.001, balance=10000.0, signups=1000):
    """Rows per archetype and the totals, for `signups` new players."""
    total_share = sum(a[1] for a in archetypes)
    rows = []
    for name, share, tpd, size, days in archetypes:
        n = signups * share / total_share
        per = fees_paid(balance, fee, tpd, size, days)
        r = min(1.0, fee * tpd * size)
        rows.append({"name": name, "players": n, "trades_per_day": tpd, "size": size, "days": days,
                     "daily_cost": r, "fees_each": per, "fees_total": per * n, "left": balance - per})
    total = sum(x["fees_total"] for x in rows)
    for x in rows:
        x["share_of_fees"] = x["fees_total"] / total if total else 0.0
    return rows, total


def top_decile_share(rows):
    """The share of all fees paid by the heaviest-paying 10% of players."""
    n = sum(x["players"] for x in rows)
    need, got, total = 0.1 * n, 0.0, sum(x["fees_total"] for x in rows)
    for x in sorted(rows, key=lambda x: -x["fees_each"]):
        take = min(need, x["players"])
        got += take * x["fees_each"]
        need -= take
        if need <= 1e-9:
            break
    return got / total if total else 0.0


def study_turnover():
    """For scale only: how much of its balance each simulated strategy traded in two game hours (from a saved study)."""
    out = {}
    files = sorted(glob.glob(os.path.join(HERE, "sim_results", "bots_all_*.json")))
    if not files:
        return out
    runs = json.load(open(files[0]))
    for k in ("hodl", "retail", "bracket_trader", "news_chaser"):
        vals = [r["turnover"][k] for r in runs if k in r.get("turnover", {})]
        if vals:
            out[k] = sum(vals) / len(vals)
    return out


def report(archetypes=ARCHETYPES, fee=0.001, balance=10000.0, signups=1000, mb_value=0.0):
    rows, total = model(archetypes, fee, balance, signups)
    money = (lambda mb: f" ({mb * mb_value:,.0f})") if mb_value else (lambda mb: "")
    lines = [f"What is a player worth?  fee {fee:.3%} per trade, {balance:,.0f} MB each, {signups:,} sign-ups",
             "(ASSUMPTIONS about how people play, not measurements; see the top of revenue_model.py)", "",
             f"{'player type':10} {'share':>6} {'trades/day':>10} {'size':>5} {'days':>5} {'fees take/day':>13} {'fees each':>10} {'left each':>10} {'% of fees':>9}"]
    for x in rows:
        lines.append(f"{x['name']:10} {x['players'] / signups:6.0%} {x['trades_per_day']:10.0f} {x['size']:5.0%} {x['days']:5.0f} "
                     f"{x['daily_cost']:13.2%} {x['fees_each']:10,.0f} {x['left']:10,.0f} {x['share_of_fees']:9.0%}")
    lines += ["", f"Fees from {signups:,} sign-ups: {total:,.0f} MB{money(total)}, {total / signups:,.0f} MB per sign-up "
                  f"({total / signups / balance:.1%} of the starting balance).",
              f"The heaviest-paying 10% of players pay {top_decile_share(rows):.0%} of the fees."]
    lines += ["", "The fee level (the same players):", f"{'fee':>7} {'fees per sign-up':>17} {'as % of balance':>16}"]
    for f in FEES:
        _, t = model(archetypes, f, balance, signups)
        lines.append(f"{f:7.3%} {t / signups:17,.0f} {t / signups / balance:16.1%}")
    ref = study_turnover()
    if ref:
        lines += ["", "For scale: in two simulated game hours the buy-and-hold bots traded "
                  f"{ref.get('hodl', 0):.1f}x their balance, the random 'retail' bots {ref.get('retail', 0):.1f}x, "
                  f"a bracket-order bot {ref.get('bracket_trader', 0):.0f}x and a news-chasing bot {ref.get('news_chaser', 0):.0f}x. "
                  "People trade far less than bots, so these are not used."]
    lines += ["", "Reading it: income depends on how much people trade and how much money they put in, not on how many sign up. "
                  "A few heavy traders pay most of the fees, and a looker pays almost nothing."]
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    kw = {a.split("=", 1)[0]: a.split("=", 1)[1] for a in args if "=" in a}
    arche = ARCHETYPES
    for a in args:
        if a.endswith(".json"):
            arche = [tuple(x) for x in json.load(open(a))]
    text = report(arche, float(kw.get("fee", 0.001)), float(kw.get("balance", 10000)), int(kw.get("signups", 1000)),
                  float(kw.get("mb_value", 0)))
    print(text)
    if "--md" in sys.argv:
        os.makedirs(os.path.join(HERE, "sim_results"), exist_ok=True)
        with open(os.path.join(HERE, "sim_results", "revenue_model.txt"), "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
