"""What 1,000 sign-ups might bring in (ROADMAP M7): a model of Pro and Expert pass sales.

    python tools/pricing_model.py [assumptions.json]

The site earns from the Pro and Expert passes only: MB have no cash value and are not sold (since 2026-11-15), and
there is no trading fee income. How players behave is not known yet, so every behaviour below is an ASSUMPTION,
written in one table and replaceable from a JSON file with the same keys. The passes and their prices are read from
the game's own settings (content/base.json `shop_pro` and `shop_expert`), so the model follows any change to them.

How it works, week by week for one cohort of sign-ups over `weeks` weeks:

* Players leave: `retention` is the share still active after 1, 4 and 13 weeks (in between it is interpolated in log).
* A share of active players hold Pro (`pro_share`) and a share hold Expert (`expert_share`), on the monthly or the
  yearly plan (`yearly_share`).
* A monthly pass's first month is half price (the New Launch Deal, once per pass); a pass is kept `months_kept`
  months on average, so the deal is spread over those months.
* Payment costs (`fee_pct` + `fee_fixed` a payment) and refunds (`refund_rate`) come off; with a merchant of record
  the fee covers sales tax and VAT.

It prints the totals for the cohort, a week-by-week table, and how much the revenue moves when each assumption is half
or one and a half times as big (the sensitivity), so it is clear which numbers matter most once real ones come in.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "game"))
import paths  # noqa: E402

TIERS = ("pro", "expert")

ASSUMPTIONS = {
    "signups": 1000,
    "weeks": 26,
    "retention": {"1": 0.30, "4": 0.12, "13": 0.05},  # share still playing after 1, 4 and 13 weeks (typical for a free game)
    "pro_share": 0.01,              # share of active players with the Pro pass
    "expert_share": 0.003,          # share of active players with the Expert pass
    "yearly_share": 0.25,           # of pass holders, the share on the yearly plan
    "months_kept": 4,               # how many months a monthly pass is kept on average (the first one is half price)
    "fee_pct": 0.05, "fee_fixed": 0.50,   # a merchant of record's fee (it also handles VAT and sales tax)
    "refund_rate": 0.02,
}


def game_settings():
    with open(os.path.join(paths.CONTENT, "base.json"), encoding="utf-8") as fh:
        st = json.load(fh)["settings"]
    return {t: {p["sku"]: (p["days"], p["price_cents"] / 100) for p in st.get(f"shop_{t}", [])} for t in TIERS}


def plan_prices(plans):
    """A tier's (monthly, yearly) price in dollars; 0 for a plan the shop does not have."""
    monthly = next((v[1] for v in plans.values() if v[0] <= 31), 0.0)
    yearly = next((v[1] for v in plans.values() if v[0] >= 365), 0.0)
    return monthly, yearly


def retention_at(a, week):
    """Share of the cohort active in `week` (week 0 is everyone), log-interpolated between the given points."""
    pts = sorted((float(k), float(v)) for k, v in a["retention"].items())
    pts = [(0.0, 1.0)] + pts
    if week >= pts[-1][0]:
        (w0, r0), (w1, r1) = pts[-2], pts[-1]
    else:
        (w0, r0), (w1, r1) = next((p, q) for p, q in zip(pts, pts[1:]) if p[0] <= week <= q[0])
    k = (math.log(r1) - math.log(r0)) / (w1 - w0)
    return max(0.0, min(1.0, r0 * math.exp(k * (week - w0))))


def run(a=None, g=None):
    """The cohort, week by week. Returns the totals and the weekly rows."""
    a = dict(ASSUMPTIONS, **(a or {}))
    g = g or game_settings()
    y = a["yearly_share"]
    deal = 1 - 0.5 / max(a["months_kept"], 1.0)            # the half-price first month, spread over the months kept
    prices = {t: plan_prices(g.get(t, {})) for t in TIERS}
    rows, tot = [], {"pro": 0.0, "expert": 0.0, "payments": 0.0}
    for w in range(a["weeks"]):
        active = a["signups"] * retention_at(a, w + 0.5)
        row = {"week": w + 1, "active": active, "holders": 0.0, "revenue": 0.0}
        for t in TIERS:
            monthly, yearly = prices[t]
            holders = active * a[f"{t}_share"]
            rev = holders * ((1 - y) * monthly * deal / (30 / 7) + y * yearly / 52)
            tot[t] += rev
            tot["payments"] += holders * ((1 - y) / (30 / 7) + y / 52)   # (one payment a month, or one a year)
            row["holders"] += holders
            row["revenue"] += rev
        rows.append(row)
    revenue = tot["pro"] + tot["expert"]
    net = revenue * (1 - a["fee_pct"] - a["refund_rate"]) - tot["payments"] * a["fee_fixed"]
    tot.update(revenue=revenue, net=net, per_signup=net / a["signups"])
    return tot, rows


def sensitivity(a=None):
    """The net revenue when each assumption is halved and when it is one and a half times as big."""
    a = dict(ASSUMPTIONS, **(a or {}))
    g = game_settings()
    base = run(a, g)[0]["net"]
    out = []
    scaled = lambda f: {w: min(1.0, r * f) for w, r in a["retention"].items()}
    out.append(("retention (every point)", run(dict(a, retention=scaled(0.5)), g)[0]["net"] - base,
                run(dict(a, retention=scaled(1.5)), g)[0]["net"] - base))
    for k, v in a.items():
        if k in ("signups", "weeks") or not isinstance(v, (int, float)):
            continue
        lo = run(dict(a, **{k: v * 0.5}), g)[0]["net"]
        hi = run(dict(a, **{k: min(v * 1.5, 1.0) if v <= 1 else v * 1.5}), g)[0]["net"]
        out.append((k, lo - base, hi - base))
    out.sort(key=lambda r: -max(abs(r[1]), abs(r[2])))
    return base, out


def main():
    a = {}
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as fh:
            a = json.load(fh)
    tot, rows = run(a)
    full = dict(ASSUMPTIONS, **a)
    print(f"A cohort of {full['signups']:,} sign-ups over {full['weeks']} weeks (every behaviour is an assumption: see the file)")
    print(f"  revenue: Pro US${tot['pro']:,.0f}, Expert US${tot['expert']:,.0f}; after payment costs and refunds "
          f"US${tot['net']:,.0f} (US${tot['per_signup']:.2f} a sign-up)")
    print("\n  week  active  pass holders  revenue")
    for r in rows:
        if r["week"] in (1, 2, 4, 8, 13, 26) or r["week"] == len(rows):
            print(f"  {r['week']:>4} {r['active']:>7.0f} {r['holders']:>13.1f}  US${r['revenue']:>7.0f}")
    base, sens = sensitivity(a)
    print(f"\n  Sensitivity (net US${base:,.0f}): the change when an assumption is half / one and a half times as big")
    for k, lo, hi in sens:
        print(f"  {k:<24} {lo:>+9,.0f} {hi:>+9,.0f}")


if __name__ == "__main__":
    main()
