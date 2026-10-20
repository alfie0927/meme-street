"""The quest ladder: one-off quests in four tiers, Bronze, Silver, Gold and Diamond, each harder than the last and paying
more. They sit next to the daily quests (social.py) and the learning challenges (learning.py).

* **Rewards.** Every quest pays MB once (10, 25, 75 or 150 by tier), credited as `challenge` MB: money put in, so it never
  lifts a return or a rank. There is no weekly cap: each quest can only be done once, so the whole ladder is worth
  1,780 MB at most.
* **Diamond** quests also unlock a **title** (shown after the name, such as "Top Trader") and a **name colour**. The
  player picks which to wear on their profile page; it shows on the leaderboards, in chat and on their public profile.
  Colours come from a fixed palette, never from what a player types.
* **Progress** comes from counters the game already keeps (trades, profitable closes, shorts, dividends, realised
  profit) and from a few the ladder counts itself (different stocks and industries, stops, take-profits, planned
  trades, days traded, day-board finishes, patient wins). Counts made before
  the ladder existed still count, so an active player finds some quests already done.

Like the other rewards, nothing here moves a price or gives a trading advantage.
"""

TIERS = [("bronze", "Bronze"), ("silver", "Silver"), ("gold", "Gold"), ("diamond", "Diamond")]
REWARD = {"bronze": 10.0, "silver": 25.0, "gold": 75.0, "diamond": 150.0}
COLORS = {"gold": ("Gold", "#ffd166"), "cyan": ("Cyan", "#39c5cf"), "emerald": ("Emerald", "#3fdc8a"),
          "ruby": ("Ruby", "#ff6b81"), "violet": ("Violet", "#c49bff"), "diamond": ("Diamond", "#a5f3fc")}
TITLES = {"top_trader": "Top Trader", "veteran": "Market Veteran", "risk_master": "Risk Master",
          "money_maker": "Money Maker", "chart_master": "Chart Master", "legend": "Legend"}
# (id, tier, name, how, metric, target, (title, colour) unlocked by a Diamond quest)
LADDER = [
    ("b_trades", "bronze", "Warming up", "Make 5 trades.", "trades", 5, None),
    ("b_tickers", "bronze", "Window shopping", "Trade 5 different stocks.", "tickers", 5, None),
    ("b_wins", "bronze", "Small wins", "Close 3 positions at a profit.", "profit_closes", 3, None),
    ("b_stop", "bronze", "Safety net", "Put a stop-loss on a position.", "stops", 1, None),
    ("b_short", "bronze", "Going short", "Open a short.", "shorts", 1, None),
    ("b_target", "bronze", "Set a target", "Put a take-profit on a position.", "targets", 1, None),
    ("b_days", "bronze", "Coming back", "Trade on 3 different days.", "days", 3, None),
    ("b_dividend", "bronze", "Paid to wait", "Receive a dividend.", "dividends", 1, None),
    ("s_trades", "silver", "Getting busy", "Make 50 trades.", "trades", 50, None),
    ("s_sectors", "silver", "All over the map", "Trade stocks in 8 different industries.", "sectors", 8, None),
    ("s_wins", "silver", "Winning habit", "Close 20 positions at a profit.", "profit_closes", 20, None),
    ("s_planned", "silver", "Plan the trade", "Close 10 positions that had a stop-loss while they were open.", "planned", 10, None),
    ("s_short_wins", "silver", "Short seller", "Close 5 shorts at a profit.", "short_wins", 5, None),
    ("s_tickers", "silver", "Explorer", "Trade 25 different stocks.", "tickers", 25, None),
    ("s_days", "silver", "A week of trading", "Trade on 7 different days.", "days", 7, None),
    ("s_profit", "silver", "Paying off", "Book 250 MB of realised profit in total.", "realized", 250, None),
    ("g_trades", "gold", "Busy desk", "Make 250 trades.", "trades", 250, None),
    ("g_wins", "gold", "Consistent", "Close 75 positions at a profit.", "profit_closes", 75, None),
    ("g_planned", "gold", "Trade the plan", "Close 40 positions that had a stop-loss while they were open.", "planned", 40, None),
    ("g_short_wins", "gold", "Bear market pro", "Close 25 shorts at a profit.", "short_wins", 25, None),
    ("g_top10", "gold", "On the board", "Finish a day in the top 10 of the day board with a positive return.", "top10", 1, None),
    ("g_days", "gold", "A month of trading", "Trade on 20 different days.", "days", 20, None),
    ("g_profit", "gold", "Real money", "Book 1,000 MB of realised profit in total.", "realized", 1000, None),
    ("g_patient", "gold", "Patience pays", "Close 10 winning positions you held for at least an hour.", "long_wins", 10, None),
    ("d_top3", "diamond", "Top Trader", "Finish 3 days in the top 3 of the day board with a positive return.", "top3", 3, ("top_trader", "gold")),
    ("d_trades", "diamond", "Market Veteran", "Make 1,000 trades.", "trades", 1000, ("veteran", "cyan")),
    ("d_planned", "diamond", "Risk Master", "Close 150 positions that had a stop-loss while they were open.", "planned", 150, ("risk_master", "emerald")),
    ("d_profit", "diamond", "Money Maker", "Book 5,000 MB of realised profit in total.", "realized", 5000, ("money_maker", "ruby")),
    ("d_wins", "diamond", "Chart Master", "Close 300 positions at a profit.", "profit_closes", 300, ("chart_master", "violet")),
    ("d_legend", "diamond", "Legend", "Finish every other quest on the ladder.", "ladder", 29, ("legend", "diamond")),
]
LADDER_BY = {q[0]: q for q in LADDER}
PLAYER_FIELDS = ("ladder", "title", "name_color")


def init_player(p):
    p.ladder = {"done": {}, "n": {}, "tickers": [], "sectors": [], "day": None}
    p.title = ""          # the title the player wears (a TITLES id, or "")
    p.name_color = ""     # the name colour the player wears (a COLORS id, or "")


def dump_player(p):
    return {k: getattr(p, k) for k in PLAYER_FIELDS}


def load_player(p, x):
    for k in PLAYER_FIELDS:
        if k in x:
            setattr(p, k, x[k])
    lad = p.ladder if isinstance(p.ladder, dict) else {}
    p.ladder = {"done": {k: float(v) for k, v in dict(lad.get("done", {})).items() if k in LADDER_BY},
                "n": {k: int(v) for k, v in dict(lad.get("n", {})).items()},
                "tickers": [str(t) for t in lad.get("tickers", [])][:300], "sectors": [str(s) for s in lad.get("sectors", [])][:60],
                "day": lad.get("day")}
    p.title = str(p.title or "") if p.title in TITLES else ""
    p.name_color = str(p.name_color or "") if p.name_color in COLORS else ""


class LadderMixin:
    """Mixed into the Engine. Uses `self.now`, `self.credit`, `self._notify`, `self.stocks`, `self.board`, `self.by_token`."""

    # ------------------------------------------------------------------ counting
    def _ladder_count(self, p, key, by=1):
        n = p.ladder["n"]
        n[key] = n.get(key, 0) + by
        self._ladder_check(p)

    def _ladder_on_trade(self, p, kind, s, close_pnl, held_since):
        """Every executed trade (social.py's hook): stocks and industries traded, days traded, short and patient wins."""
        lad = p.ladder
        if s.ticker not in lad["tickers"] and len(lad["tickers"]) < 300:
            lad["tickers"].append(s.ticker)
        if s.asset_type == "equity" and s.sector not in lad["sectors"] and len(lad["sectors"]) < 60:
            lad["sectors"].append(s.sector)
        day = int(self.now // 86400)
        if lad.get("day") != day:
            lad["day"] = day
            lad["n"]["days"] = lad["n"].get("days", 0) + 1
        if close_pnl is not None and close_pnl > 0:
            if kind == "cover":
                lad["n"]["short_wins"] = lad["n"].get("short_wins", 0) + 1
            if self.now - held_since >= 3600:
                lad["n"]["long_wins"] = lad["n"].get("long_wins", 0) + 1
        self._ladder_check(p)

    def _ladder_day_end(self):
        """The day board is final (engine._end_season): count top-10 and top-3 finishes with a positive return."""
        for i, row in enumerate(self.board[:10]):
            p = self.by_token.get(row.get("token"))
            if p is None or row.get("ret", 0.0) <= 0:
                continue
            n = p.ladder["n"]
            n["top10"] = n.get("top10", 0) + 1
            if i < 3:
                n["top3"] = n.get("top3", 0) + 1
            self._ladder_check(p)

    def _ladder_metric(self, p, metric):
        c, n = p.counters, p.ladder["n"]
        if metric == "trades":
            return int(c.get("trades", 0))
        if metric == "profit_closes":
            return int(c.get("profit_closes", 0))
        if metric == "shorts":
            return int(c.get("short", 0))
        if metric == "dividends":
            return int(c.get("dividends", 0)) or (1 if any(v > 0 for v in p.divs.values()) else 0)
        if metric == "tickers":
            return len(p.ladder["tickers"])
        if metric == "sectors":
            return len(p.ladder["sectors"])
        if metric == "realized":
            return int(sum(p.realized.values()))
        if metric == "ladder":
            return sum(1 for k in p.ladder["done"] if k != "d_legend")
        return int(n.get(metric, 0))

    # ------------------------------------------------------------------ completing quests
    def _ladder_check(self, p):
        if not self.settings.get("quest_ladder", True):          # (switched off: nothing completes or pays)
            return
        for qid, tier, name, how, metric, target, unlock in LADDER:
            if qid in p.ladder["done"] or self._ladder_metric(p, metric) < target:
                continue
            p.ladder["done"][qid] = self.now
            blocked = self.reward_block(p)
            reward = 0 if blocked else REWARD[tier]
            if reward:
                self.credit(p, reward, source="challenge")
            extra = ""
            if unlock:
                extra = f" You can now wear the title “{TITLES[unlock[0]]}” and a {COLORS[unlock[1]][0].lower()} name (on your profile page)."
            paid = f"+{reward:,.0f} MB" if reward else f"no MB: {blocked}"
            self._notify(p, f"{dict(TIERS)[tier]} quest complete: {name}! {paid}.{extra}")

    def ladder_unlocked(self, p):
        titles, colors = [], []
        for qid in p.ladder["done"]:
            unlock = LADDER_BY[qid][6]
            if unlock:
                titles.append(unlock[0])
                colors.append(unlock[1])
        return titles, colors

    # ------------------------------------------------------------------ what the page sees
    def ladder_view(self, p):
        self._ladder_check(p)                      # (counts made before the ladder existed are paid here too)
        tiers = []
        for tid, tname in TIERS:
            quests = []
            for qid, tier, name, how, metric, target, unlock in LADDER:
                if tier != tid:
                    continue
                quests.append({"id": qid, "name": name, "how": how, "n": min(self._ladder_metric(p, metric), target),
                               "target": target, "done": qid in p.ladder["done"], "reward": REWARD[tier],
                               "unlocks": {"title": TITLES[unlock[0]], "color": COLORS[unlock[1]][1], "color_name": COLORS[unlock[1]][0]} if unlock else None})
            tiers.append({"id": tid, "name": tname, "reward": REWARD[tid], "quests": quests,
                          "done": sum(1 for q in quests if q["done"])})
        titles, colors = self.ladder_unlocked(p)
        return {"tiers": tiers, "done": len(p.ladder["done"]), "total": len(LADDER), "on": bool(self.settings.get("quest_ladder", True)),
                "titles": [{"id": t, "name": TITLES[t]} for t in titles],
                "colors": [{"id": c, "name": COLORS[c][0], "hex": COLORS[c][1]} for c in colors],
                "wear": {"title": p.title, "color": p.name_color}, "style": self.style_of(p)}

    def set_style(self, p, title, color):
        """Wear an unlocked title and name colour ("" for none)."""
        titles, colors = self.ladder_unlocked(p)
        title, color = str(title or ""), str(color or "")
        if title and title not in titles:
            return False, "You have not unlocked that title yet"
        if color and color not in colors:
            return False, "You have not unlocked that colour yet"
        p.title, p.name_color = title, color
        return True, "Saved: this is how your name looks on the boards and in chat"

    def style_of(self, p):
        """How a name is shown: {"c": colour, "t": title}, or None for a plain name."""
        if p is None or not (p.title or p.name_color):
            return None
        out = {}
        if p.name_color in COLORS:
            out["c"] = COLORS[p.name_color][1]
        if p.title in TITLES:
            out["t"] = TITLES[p.title]
        return out or None
