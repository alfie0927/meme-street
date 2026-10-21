"""What 1,000 sign-ups might bring in (ROADMAP M7): a model of MB package and Pro sales.

    python tools/pricing_model.py [assumptions.json]

The site earns from selling MB (never cashed out) and the Pro pass, not from trading fees. How players behave is not
known yet (the shop has not opened), so every behaviour below is an ASSUMPTION, written in one table and replaceable
from a JSON file with the same keys. The packages, prices, the starting balance, the free restart and the challenge cap
are read from the game's own settings (content/base.json), so the model follows any change to them.

How it works, week by week for one cohort of sign-ups over `weeks` weeks:

* Players leave: `retention` is the share still active after 1, 4 and 13 weeks (in between it is interpolated in log).
* Some active accounts run out each week (`bust_rate`: below the free-restart line of 50 MB). Of those, some buy
  (`buy_after_bust`), some take the free restart if it is theirs to take (`restart_take`, at most once every
  `restart_days`), and the rest stop playing.
* Some active players buy without having run out, to trade bigger (`buy_rate`), and a share of every buyer buys again
  later (`repeat_share`).
* A share of active players hold the Pro pass (`pro_share`), monthly or yearly (`pro_yearly_share`).
* Purchases are spread over the packages by `package_mix`. Payment costs (`fee_pct` + `fee_fixed` a payment) and
  refunds (`refund_rate`) come off; with a merchant of record the fee covers sales tax and VAT.
* Challenges pay MB (up to the weekly cap) to active players (`challenge_mb_week`); they lower the share that runs out
  (`challenge_bust_relief` per 1,000 MB earned a week).

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

ASSUMPTIONS = {
    "signups": 1000,
    "weeks": 26,
    "retention": {"1": 0.30, "4": 0.12, "13": 0.05},  # share still playing after 1, 4 and 13 weeks (typical for a free game)
    "bust_rate": 0.04,              # share of active accounts that fall below the restart line in a week
    "buy_after_bust": 0.06,         # of those, the share who buy MB
    "restart_take": 0.6,            # of the rest, the share who take the free restart (if theirs to take)
    "buy_rate": 0.004,              # share of active players who buy in a week without having run out
    "repeat_share": 0.3,            # share of buyers who buy once more within the period
    "pro_share": 0.01,              # share of active players with the Pro pass
    "pro_yearly_share": 0.25,       # of those, the share on the yearly plan
    "package_mix": {"mb1000": 0.35, "mb5000": 0.30, "mb10000": 0.20, "mb50000": 0.10, "mb100000": 0.05},
    "fee_pct": 0.05, "fee_fixed": 0.50,   # a merchant of record's fee (it also handles VAT and sales tax)
    "refund_rate": 0.02,
    "challenge_mb_week": 150,       # MB an active player earns from challenges in a week (the cap is the game's)
    "challenge_bust_relief": 0.3,   # how much 1,000 MB a week of challenge pay lowers the share that runs out
}


def game_settings():
    with open(os.path.join(paths.CONTENT, "base.json"), encoding="utf-8") as fh:
        st = json.load(fh)["settings"]
    return {"packages": {p["sku"]: (p["mb"], p["price_cents"] / 100) for p in st.get("shop_packages", [])},
            "pro": {p["sku"]: (p["days"], p["price_cents"] / 100) for p in st.get("shop_pro", [])},
            "start": float(st.get("signup_bonus", 1000)), "restart_days": float(st.get("restart_days", 7)),
            "challenge_cap": float(st.get("challenge_week_cap", 500))}


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
    mix = {k: v for k, v in a["package_mix"].items() if k in g["packages"]}
    total_mix = sum(mix.values()) or 1.0
    avg_price = sum(g["packages"][k][1] * v for k, v in mix.items()) / total_mix
    avg_mb = sum(g["packages"][k][0] * v for k, v in mix.items()) / total_mix
    pro = g["pro"]
    monthly = next((v[1] for k, v in pro.items() if v[0] <= 31), 0.0)
    yearly = next((v[1] for k, v in pro.items() if v[0] >= 365), 0.0)
    pro_week = ((1 - a["pro_yearly_share"]) * monthly / (30 / 7) + a["pro_yearly_share"] * yearly / 52)
    challenge = min(a["challenge_mb_week"], g["challenge_cap"])
    bust = a["bust_rate"] * max(0.0, 1 - a["challenge_bust_relief"] * challenge / 1000)
    restart_ok = min(1.0, 7.0 / max(g["restart_days"], 1e-9))      # (once every `restart_days` days at most)
    rows, tot = [], {"purchases": 0.0, "buyers": 0.0, "gross": 0.0, "pro": 0.0, "mb_grant": a["signups"] * g["start"],
                     "mb_bought": 0.0, "mb_challenge": 0.0, "mb_restart": 0.0, "busts": 0.0}
    for w in range(a["weeks"]):
        active = a["signups"] * retention_at(a, w + 0.5)
        busts = active * bust
        buyers = busts * a["buy_after_bust"] + active * a["buy_rate"]
        purchases = buyers * (1 + a["repeat_share"])
        restarts = busts * (1 - a["buy_after_bust"]) * a["restart_take"] * restart_ok
        gross = purchases * avg_price
        pro_rev = active * a["pro_share"] * pro_week
        tot["purchases"] += purchases
        tot["buyers"] += buyers
        tot["gross"] += gross
        tot["pro"] += pro_rev
        tot["busts"] += busts
        tot["mb_bought"] += purchases * avg_mb
        tot["mb_challenge"] += active * challenge
        tot["mb_restart"] += restarts * g["start"]
        rows.append({"week": w + 1, "active": active, "busts": busts, "buyers": buyers, "gross": gross + pro_rev})
    revenue = tot["gross"] + tot["pro"]
    payments = tot["purchases"] + tot["pro"] / max(monthly, 1e-9)          # (about one payment a Pro month)
    net = revenue * (1 - a["fee_pct"] - a["refund_rate"]) - payments * a["fee_fixed"]
    tot.update(revenue=revenue, net=net, per_signup=net / a["signups"], avg_price=avg_price, avg_mb=avg_mb,
               paying_share=min(1.0, tot["buyers"] / a["signups"]))
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
    print(f"  average package bought: {tot['avg_mb']:,.0f} MB for US${tot['avg_price']:.2f}")
    print(f"  accounts that ran out: {tot['busts']:,.0f}; buyers: {tot['buyers']:,.0f} ({tot['paying_share']:.1%} of sign-ups); "
          f"purchases: {tot['purchases']:,.0f}")
    print(f"  revenue: MB US${tot['gross']:,.0f}, Pro US${tot['pro']:,.0f}; after payment costs and refunds US${tot['net']:,.0f} "
          f"(US${tot['per_signup']:.2f} a sign-up)")
    print(f"  MB put into the game: starting {tot['mb_grant']:,.0f}, bought {tot['mb_bought']:,.0f}, challenges "
          f"{tot['mb_challenge']:,.0f}, free restarts {tot['mb_restart']:,.0f}")
    print("\n  week  active  ran out  buyers  revenue")
    for r in rows:
        if r["week"] in (1, 2, 4, 8, 13, 26) or r["week"] == len(rows):
            print(f"  {r['week']:>4} {r['active']:>7.0f} {r['busts']:>8.1f} {r['buyers']:>7.1f}  US${r['gross']:>7.0f}")
    base, sens = sensitivity(a)
    print(f"\n  Sensitivity (net US${base:,.0f}): the change when an assumption is half / one and a half times as big")
    for k, lo, hi in sens:
        print(f"  {k:<24} {lo:>+9,.0f} {hi:>+9,.0f}")


if __name__ == "__main__":
    main()
