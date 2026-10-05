"""The social side of the game: achievements, daily quests, risk-adjusted rankings, tournaments, public profiles,
following and a moderated chat.

It is a mixin for the Engine: the engine owns the players and the money, this file owns everything built on top of
them. Nothing here ever changes anyone's cash or any price, and every reward is cosmetic (badges, streaks), so none
of it can create an edge or break the token books.
"""
import math
import random
import re
import sys
import unicodedata
from collections import deque

from accounts import mask_email
from contest import Sandbox, dump_account, load_account

# ---------------------------------------------------------------------------------------------- achievements
# (id, name, description). They are checked after every trade and every few seconds.
ACHIEVEMENTS = [
    ("first_trade", "First steps", "Make your first trade."),
    ("first_short", "Bear in the woods", "Open your first short."),
    ("winning_short", "Sold high, bought low", "Close a short at a profit."),
    ("margin_called", "Trial by fire", "Get margin-called (and keep playing)."),
    ("dividend", "Dividend collector", "Receive a dividend."),
    ("diversified", "Not all eggs", "Hold five different positions at once."),
    ("sector_spread", "Wide net", "Hold stocks in four different sectors at once."),
    ("index_trader", "Whole market", "Trade an index, ETF or leveraged product."),
    ("safe_haven", "Safe harbour", "Trade a safe-haven asset such as bonds or gold."),
    ("hedger", "Belt and braces", "Hold a safe haven or an inverse product alongside two or more stocks."),
    ("busy_10", "Getting active", "Make 10 trades."),
    ("busy_100", "Market regular", "Make 100 trades."),
    ("busy_500", "Floor trader", "Make 500 trades."),
    ("green_100", "In the green", "Book 100 MB of realised profit in total."),
    ("big_win", "Big win", "Close a single trade for at least 100 MB of profit."),
    ("diamond_hands", "Diamond hands", "Close a position at a profit after holding it for at least an hour."),
    ("caught_reversal", "Caught the reversal",
     "Hold a stock through a REVERSAL headline and close it at a profit within ten minutes."),
    ("up_10", "Up ten", "Reach a day return of +10%."),
    ("up_25", "Up twenty-five", "Reach a day return of +25%."),
    ("podium", "On the podium", "Finish in the top three of a daily contest."),
    ("quest_day", "Daily grind", "Complete all of a day's quests."),
]
ACH_NAMES = {a[0]: a[1] for a in ACHIEVEMENTS}

# ---------------------------------------------------------------------------------------------- daily quests
# (id, text, metric, lowest goal, highest goal, multiplier). Each day's three quests are drawn from this list with a
# generator seeded by the date, so everyone gets the same ones and they reset at midnight UTC.
QUESTS = [
    ("trades", "Make {goal} trades", "trades", 4, 12, 1),
    ("sectors", "Trade stocks in {goal} different sectors", "sectors", 2, 4, 1),
    ("profit_close", "Close {goal} position(s) at a profit", "profit_closes", 1, 3, 1),
    ("short", "Open a short", "shorts", 1, 1, 1),
    ("positions", "Hold {goal} different positions at once", "max_positions", 3, 6, 1),
    ("index", "Trade an index, ETF or leveraged product", "index_trades", 1, 1, 1),
    ("dividend", "Receive a dividend", "dividends", 1, 1, 1),
    ("volume", "Trade {goal} MB in total", "volume", 2, 8, 100),
]

# ---------------------------------------------------------------------------------------------- contests
# kind -> (name, length in seconds, seconds during which you can still join)
CONTESTS = {
    "marathon": ("Daily Marathon", 86400, 43200),
}
TOURNAMENTS = CONTESTS                               # (the old name, still used by saves and some callers)
CONTEST_BALANCE = 10000.0                            # every entrant starts with the same paper balance (MB)


# ---------------------------------------------------------------------------------------------- chat rules
BAD_WORDS = ["fuck", "shit", "bitch", "asshole", "cunt", "nigger", "faggot", "slut", "whore", "bastard"]   # also match "fucking", "shitty"
# Words that are also the start of ordinary ones (retardant, putative) only count as a whole word, plural or "-ed".
BAD_WORDS_EXACT = ["retard", "puta", "puto", "mierda", "cabron", "pendejo", "joder", "merde", "putain", "salope", "connard",
                   "encule", "scheisse", "arschloch", "hurensohn", "wichser", "porra", "caralho", "cazzo", "stronzo", "vaffanculo"]
# Players dodge a word list with look-alike characters (sh!t, f u c k, fuuuck). Each letter of a word is matched as
# itself or its usual look-alikes, repeated, with up to three separators between letters. A match must start at the
# beginning of a word, so "class hit" and "assume" are left alone.
_LOOKALIKE = {"a": "[a@4]", "e": "[e3]", "i": "[i1!|]", "o": "[o0]", "s": "[s5$]", "t": "[t7+]", "l": "[l1|]", "b": "[b8]"}


def _word_pattern(word, exact=False):
    letters = [(_LOOKALIKE.get(ch) or re.escape(ch)) + "+" for ch in word]
    tail = r"(?:s|ed)?(?![a-z0-9])" if exact else r"[a-z]*"
    return r"(?<![a-z0-9])" + r"[\W_]{0,3}".join(letters) + tail


def build_filter(extra=()):
    parts = [_word_pattern(w) for w in sorted(set(BAD_WORDS) | {str(w).lower() for w in extra if str(w).strip()})]
    parts += [_word_pattern(w, exact=True) for w in sorted(BAD_WORDS_EXACT)]
    return re.compile("|".join(parts), re.I)


def _fold(text):
    """Accents and full-width letters folded to plain ones, one character for one (so positions still line up)."""
    out = []
    for c in text:
        d = "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x))
        out.append(d if len(d) == 1 else c)
    return "".join(out)


_BAD_RE = build_filter()
_URL_RE = re.compile(r"(https?://\S+|www\.\S+|\b\S+\.(com|net|org|io|xyz|ru|cn|gg|ly)\b\S*)", re.I)
_CTRL_RE = re.compile("[\x00-\x1f\x7f​-‏‪-‮⁦-⁩﻿]")
CHAT_MAX = 200
CHAT_MIN_GAP = 1.5          # seconds between a player's messages
CHAT_PER_MINUTE = 15
FOLLOW_MAX = 20
SNAP_EVERY = 30             # seconds between holdings snapshots (shown to others after a delay)

PLAYER_FIELDS = ("achievements", "counters", "quests_done", "quest_streak", "quest_last_full", "maxdd", "peak",
                 "badges", "public", "following", "daily", "opened", "strikes")


def init_player(p):
    """Give a Player every field the social features use."""
    p.achievements = {}          # achievement id -> time unlocked
    p.counters = {}              # lifetime counts: trades, shorts, profitable closes, ...
    p.daily = {}                 # today's progress for the quests
    p.opened = {}                # ticker -> when the position currently held was opened
    p.quests_done = {}           # day number -> quest ids completed
    p.quest_streak = 0
    p.quest_last_full = -10      # the last day on which every quest was completed
    p.peak = None                # best season return index so far (for the drawdown)
    p.maxdd = 0.0                # worst fall from that peak this season, as a share of the peak
    p.badges = []                # tournament medals
    p.public = False             # share the (delayed) portfolio and results with other players?
    p.following = []
    p.strikes = 0                # automatic mutes so far (each is longer than the last)
    p.hold_snaps = deque(maxlen=40)   # (time, positions) taken every SNAP_EVERY seconds
    p.last_chat = 0.0
    p.last_chat_text = None
    p.chat_times = []


def reset_progress(p):
    """A fresh start (see Engine.reset_to_day_one): the competitive record goes, who you are stays."""
    keep = (p.public, list(p.following), p.strikes)
    init_player(p)
    p.public, p.following, p.strikes = keep


def dump_player(p):
    return {k: getattr(p, k) for k in PLAYER_FIELDS}


def load_player(p, x):
    for k in PLAYER_FIELDS:
        if k in x:
            setattr(p, k, x[k])
    p.achievements = {k: float(v) for k, v in dict(p.achievements).items() if k in ACH_NAMES}
    p.following = [str(n) for n in p.following][:FOLLOW_MAX]
    p.badges = list(p.badges)[-30:]
    p.maxdd = float(p.maxdd or 0.0)
    p.strikes = int(p.strikes or 0)
    p.opened = {k: float(v) for k, v in dict(p.opened).items() if k in p.hold}


def clean_chat(text, bad_re=None):
    """Strip control and invisible characters and accents, mask links and bad words (including disguised ones),
    collapse spaces, cap the length."""
    text = _CTRL_RE.sub(" ", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    text = _URL_RE.sub("[link]", text)
    chars = list(text)
    for m in (bad_re or _BAD_RE).finditer(_fold(text)):                  # find on the folded text, mask the original
        chars[m.start():m.end()] = "*" * (m.end() - m.start())
    return "".join(chars)[:CHAT_MAX]


class SocialMixin:
    # ------------------------------------------------------------------------------------------ setup
    def _init_social(self):
        self.chat = deque(maxlen=200)              # global chat, oldest first
        self.chat_seq = 0
        self.chat_reports = deque(maxlen=100)
        self.muted = {}                            # token -> time the mute ends
        self.mod_log = deque(maxlen=500)           # every moderation action: who, what, when, why
        self.appeals = []                          # appeals by muted players: {"id", "name", "token", "text", "t", "status"}
        self.appeal_seq = 0
        self.pending_deletes = []                  # messages the engine removed by itself, for the server to tell the pages
        self._bad_re, self._bad_key = _BAD_RE, ()
        self.tournaments = []                      # contests that have not finished yet
        self._sandboxes = {}                       # contest id -> its paper accounts (see contest.py)
        self.tournament_history = deque(maxlen=20)
        self.last_reversal = {}                    # ticker -> time of its latest REVERSAL headline
        self._social_t = 0.0
        self._holdsnap_t = 0.0
        self.boards = {"pnl": []}
        self.rank_pnl = {}

    def social_dump(self):
        return {"chat_seq": self.chat_seq, "chat": list(self.chat), "muted": self.muted,
                "tournaments": self._dump_tournaments(), "tournament_history": list(self.tournament_history),
                "reports": list(self.chat_reports), "mod_log": list(self.mod_log), "appeals": self.appeals[-100:],
                "appeal_seq": self.appeal_seq}

    def social_load(self, d):
        self.chat_seq = int(d.get("chat_seq", 0))
        self.chat.extend(m for m in d.get("chat", []) if m.get("channel", "global") == "global")
        self.muted = {k: float(v) for k, v in dict(d.get("muted", {})).items()}
        self._load_tournaments(d.get("tournaments", []))
        self.tournament_history.extend(d.get("tournament_history", []))
        self.chat_reports.extend(d.get("reports", []))
        self.mod_log.extend(d.get("mod_log", []))
        self.appeals = [a for a in d.get("appeals", []) if isinstance(a, dict) and a.get("token") in self.by_token]
        self.appeal_seq = int(d.get("appeal_seq", 0))

    # ------------------------------------------------------------------------------------------ small helpers
    def _notify(self, p, text):
        p.notices.append(text)
        del p.notices[:-20]                        # an offline player never piles up more than 20

    def _is_haven(self, s):
        spec = getattr(s, "spec", None)
        return s.sector == "safe" or bool(spec and float(spec.get("leverage", 1.0)) < 0)

    def _find(self, name):
        name = str(name).lower()
        return next((x for x in self.players.values() if x.name.lower() == name), None)

    def _daily(self, p):
        """This player's progress today (UTC day); it resets when the day changes."""
        day = int(self.now // 86400)
        if p.daily.get("day") != day:
            p.daily = {"day": day, "trades": 0, "sectors": [], "profit_closes": 0, "shorts": 0, "max_positions": 0,
                       "index_trades": 0, "dividends": 0, "volume": 0.0}
        return p.daily

    # ------------------------------------------------------------------------------------------ hooks from the engine
    def _on_open(self, p, ticker):
        """A position was just opened from nothing."""
        p.opened[ticker] = self.now

    def _on_trade(self, p, kind, s, notional, pnl=None, closed=False):
        """Called for every executed trade: buy, sell, short, cover and margin call."""
        held_since = p.opened.get(s.ticker, self.now)
        if closed:
            p.opened.pop(s.ticker, None)
        if kind == "margin_call":
            return
        c = p.counters
        c["trades"] = c.get("trades", 0) + 1
        c[kind] = c.get(kind, 0) + 1
        d = self._daily(p)
        d["trades"] += 1
        d["volume"] += notional
        if s.asset_type == "index":
            c["index_trades"] = c.get("index_trades", 0) + 1
            d["index_trades"] += 1
        if self._is_haven(s):
            c["haven_trades"] = c.get("haven_trades", 0) + 1
        if s.asset_type == "equity" and s.sector not in d["sectors"]:
            d["sectors"].append(s.sector)
        if kind == "short":
            d["shorts"] += 1
        d["max_positions"] = max(d["max_positions"], len(p.hold))
        close_pnl = pnl if kind in ("sell", "cover") else None
        if close_pnl is not None and close_pnl > 0:
            d["profit_closes"] += 1
            c["profit_closes"] = c.get("profit_closes", 0) + 1
        self._check_achievements(p, close=(kind, s.ticker, close_pnl, held_since) if close_pnl is not None else None)
        self._check_quests(p)

    def _on_dividend(self, p, amount):
        if amount > 0:
            p.counters["dividends"] = p.counters.get("dividends", 0) + 1
            self._daily(p)["dividends"] += 1
            self._check_achievements(p)
            self._check_quests(p)

    # ------------------------------------------------------------------------------------------ achievements
    def _unlock(self, p, ach_id):
        if ach_id in p.achievements:
            return
        p.achievements[ach_id] = self.now
        self._notify(p, f"Achievement unlocked: {ACH_NAMES[ach_id]}")

    def _check_achievements(self, p, close=None):
        c = p.counters
        if c.get("trades"):
            self._unlock(p, "first_trade")
        if c.get("short"):
            self._unlock(p, "first_short")
        if p.margin_calls >= 1:
            self._unlock(p, "margin_called")
        if c.get("dividends") or any(v > 0 for v in p.divs.values()):
            self._unlock(p, "dividend")
        holds = [t for t in p.hold if t in self.stocks]
        if len(holds) >= 5:
            self._unlock(p, "diversified")
        sectors = {self.stocks[t].sector for t in holds if self.stocks[t].asset_type == "equity"}
        if len(sectors) >= 4:
            self._unlock(p, "sector_spread")
        if c.get("index_trades"):
            self._unlock(p, "index_trader")
        if c.get("haven_trades"):
            self._unlock(p, "safe_haven")
        equities = [t for t in holds if self.stocks[t].asset_type == "equity" and not self._is_haven(self.stocks[t])]
        if len(equities) >= 2 and any(self._is_haven(self.stocks[t]) for t in holds):
            self._unlock(p, "hedger")
        for need, ach in ((10, "busy_10"), (100, "busy_100"), (500, "busy_500")):
            if c.get("trades", 0) >= need:
                self._unlock(p, ach)
        if sum(p.realized.values()) >= 100:
            self._unlock(p, "green_100")
        if close is not None:
            kind, tk, pnl, since = close
            if kind == "cover" and pnl > 0:
                self._unlock(p, "winning_short")
            if pnl >= 100:
                self._unlock(p, "big_win")
            if pnl > 0 and self.now - since >= 3600:
                self._unlock(p, "diamond_hands")
            rev = self.last_reversal.get(tk)
            if pnl > 0 and rev is not None and since < rev <= self.now and self.now - rev <= 600:
                self._unlock(p, "caught_reversal")
        ret = self.season_return(p)
        if ret >= 0.10:
            self._unlock(p, "up_10")
        if ret >= 0.25:
            self._unlock(p, "up_25")

    # ------------------------------------------------------------------------------------------ quests
    def quests_for_day(self, day):
        rng = random.Random(f"quests-{day}")
        out = []
        for qid, text, metric, lo, hi, mult in rng.sample(QUESTS, 3):
            goal = rng.randint(lo, hi) * mult
            out.append({"id": qid, "text": text.format(goal=goal), "metric": metric, "goal": goal})
        return out

    def _quest_progress(self, p, quest):
        d = self._daily(p)
        m = quest["metric"]
        if m == "sectors":
            return len(d["sectors"])
        if m == "max_positions":
            return max(d["max_positions"], len([t for t in p.hold if t in self.stocks]))
        return d.get(m, 0)

    def _check_quests(self, p):
        day = int(self.now // 86400)
        self._daily(p)
        quests = self.quests_for_day(day)
        done = p.quests_done.setdefault(str(day), [])
        for q in quests:
            if q["id"] not in done and self._quest_progress(p, q) >= q["goal"]:
                done.append(q["id"])
                self._notify(p, f"Quest complete: {q['text']}")
        if len(done) == len(quests) and p.quest_last_full != day:
            p.quest_streak = p.quest_streak + 1 if p.quest_last_full == day - 1 else 1
            p.quest_last_full = day
            self._unlock(p, "quest_day")
            self._notify(p, f"All of today's quests done! Streak: {p.quest_streak} day(s).")
        for key in [k for k in p.quests_done if int(k) < day - 7]:
            p.quests_done.pop(key)

    def quests_for(self, p):
        day = int(self.now // 86400)
        self._daily(p)
        done = set(p.quests_done.get(str(day), []))
        quests = [{**q, "progress": min(self._quest_progress(p, q), q["goal"]), "done": q["id"] in done}
                  for q in self.quests_for_day(day)]
        return {"day": day, "quests": quests, "streak": p.quest_streak if p.quest_last_full >= day - 1 else 0,
                "resets_in": int((day + 1) * 86400 - self.now)}

    # ------------------------------------------------------------------------------------------ rankings
    def _ratio(self, p, equity=None):
        """Equity relative to the season's base (which already includes deposits): 1.0 at the start of a season."""
        if p.season_base <= 1e-9:
            return None
        return (self.equity(p) if equity is None else equity) / p.season_base

    def _track_drawdown(self, p, equity):
        r = self._ratio(p, equity)
        if r is None:
            return
        if p.peak is None:
            p.peak = max(r, 1.0)
        elif r > p.peak:
            p.peak = r
        if p.peak > 0:
            p.maxdd = max(p.maxdd, (p.peak - r) / p.peak)

    def _rebase_peak(self, p, ratio_before):
        """A deposit or withdrawal changes the ratio without any trading; scale the peak by the same factor so it
        does not look like a gain or a drawdown."""
        after = self._ratio(p)
        if p.peak and ratio_before and after:
            p.peak *= after / ratio_before

    def _social_board(self, rows):
        """The all-time board, from every player's row (only people who have ever traded are on it)."""
        pnl = []
        for r in rows:
            p = self.by_token.get(r["token"])
            if not p or not self.ever_traded(p):
                continue
            gain = r["equity"] - p.deposited
            pnl.append({"name": r["name"], "token": r["token"], "bot": r["bot"], "pnl": gain,
                        "ret": gain / p.deposited if p.deposited > 0 else 0.0})
        pnl.sort(key=lambda x: -x["pnl"])
        self.boards = {"pnl": pnl}
        self.rank_pnl = {x["token"]: i + 1 for i, x in enumerate(pnl)}

    def boards_for(self, p, top=20):
        def trim(rows, keys):
            return [{"rank": i + 1, "me": r["token"] == p.token, **{k: r[k] for k in keys}}
                    for i, r in enumerate(rows[:top])]
        season = [{"rank": i + 1, "me": r["token"] == p.token, "name": r["name"], "bot": r["bot"],
                   "ret": r["ret"], "equity": r["equity"]} for i, r in enumerate(self.board[:top])]
        return {"season": season,
                "pnl": trim(self.boards["pnl"], ("name", "bot", "pnl", "ret")),
                "mine": {"season": self.rank.get(p.token), "pnl": self.rank_pnl.get(p.token), "dd": p.maxdd},
                "counts": {"season": len(self.board), "pnl": len(self.boards["pnl"])},
                "players": len(self.players)}

    # ------------------------------------------------------------------------------------------ contests
    # A contest is a fixed-balance paper-trading day: every entrant gets the same paper balance when they join and
    # trades it at the live prices under the real rules (see contest.py). The paper account is separate from the real
    # one, so a contest cannot change anyone's real balance, the house reserve or any price. Prizes are medals.
    def _player_class(self):
        return sys.modules[type(self).__module__].Player

    def _contest_balance(self):
        return float(self.settings.get("contest_balance", CONTEST_BALANCE))

    def _tournament_tick(self):
        for kind, (name, period, join_window) in CONTESTS.items():
            start = int(self.now // period) * period
            tid = f"{kind}-{start}"
            if not any(t["id"] == tid for t in self.tournaments) and \
                    not any(h["id"] == tid for h in self.tournament_history):
                self.tournaments.append({"id": tid, "kind": kind, "name": name, "start": start, "end": start + period,
                                         "join_until": start + float(self.settings.get("contest_join_seconds", join_window)),
                                         "entrants": {}, "v": 2})
        for t in list(self.tournaments):
            if self.now >= t["end"]:
                self.tournaments.remove(t)
                self._finish_tournament(t)

    def _sandbox(self, t):
        sb = self._sandboxes.get(t["id"])
        if sb is None:
            sb = self._sandboxes[t["id"]] = Sandbox(self)
        return sb

    def _paper_tick(self):
        for sb in self._sandboxes.values():
            sb.tick()
            for token, a in sb.players.items():
                if a.notices:
                    real = self.by_token.get(token)
                    if real:
                        for text in a.notices:
                            self._notify(real, "Contest: " + text)
                    a.notices.clear()

    def _paper_dividend(self, ticker, amt):
        for sb in self._sandboxes.values():
            sb.dividend(ticker, amt)

    def _paper_delist(self, ticker, price):
        for sb in self._sandboxes.values():
            sb.delist(ticker, price)

    def _account(self, t, token):
        sb = self._sandboxes.get(t["id"])
        return sb.players.get(token) if sb else None

    def tournament_return(self, t, token):
        a = self._account(t, token)
        ent = t["entrants"].get(token)
        if a is None or not ent or ent["base"] <= 0:
            return 0.0
        return (self.equity(a) - ent["base"]) / ent["base"]

    def tournament_standings(self, t):
        rows = []
        for token in t["entrants"]:
            p = self.by_token.get(token)
            if p:
                rows.append({"name": p.name, "ret": self.tournament_return(t, token), "token": token})
        rows.sort(key=lambda r: -r["ret"])
        return rows

    def _finish_tournament(self, t):
        rows = self.tournament_standings(t)
        for place, r in enumerate(rows[:3], 1):
            p = self.by_token.get(r["token"])
            if p:
                p.badges.append({"tournament": t["name"], "place": place, "t": self.now, "ret": r["ret"]})
                del p.badges[:-30]
                self._notify(p, f"{t['name']}: you finished #{place} of {len(rows)} with {r['ret'] * 100:+.1f}%!")
                self._unlock(p, "podium")
        for r in rows[3:]:
            p = self.by_token.get(r["token"])
            if p:
                self._notify(p, f"{t['name']} is over: you finished #{rows.index(r) + 1} of {len(rows)} "
                                f"with {r['ret'] * 100:+.1f}%.")
        self.tournament_history.append({"id": t["id"], "name": t["name"], "end": t["end"], "entrants": len(rows),
                                        "results": [{"name": r["name"], "ret": r["ret"]} for r in rows[:10]]})
        self._sandboxes.pop(t["id"], None)

    def tournament_join(self, p, tid):
        t = next((x for x in self.tournaments if x["id"] == tid), None)
        if t is None:
            return False, "No such contest"
        if p.bot:
            return False, "Bots cannot enter"
        gate = self.email_gate(p)
        if gate:
            return False, gate
        if p.token in t["entrants"]:
            return False, "You have already joined"
        if self.now >= t["join_until"]:
            return False, "Entries are closed for this contest"
        base = self._contest_balance()
        acct = self._player_class()(p.name)
        acct.token, acct.cash = p.token, base
        self._sandbox(t).players[p.token] = acct
        t["entrants"][p.token] = {"base": base, "at": self.now}
        return True, f"You joined the {t['name']} with {base:,.0f} MB of paper money. Trade it from the Contest tab."

    def contest_trade(self, p, tid, ticker, side, pct, amount=None):
        """A paper trade in a contest, under the same rules as a real one."""
        t = next((x for x in self.tournaments if x["id"] == tid), None)
        a = self._account(t, p.token) if t else None
        if a is None:
            return False, "You are not in that contest"
        if self.now >= t["end"]:
            return False, "That contest is over"
        return self._sandbox(t).trade(a, str(ticker), side, pct, amount)

    def _account_view(self, t, token):
        a = self._account(t, token)
        if a is None:
            return None
        rows = []
        for tk, sh in sorted(a.hold.items()):
            s = self.stocks.get(tk)
            if s:
                avg = a.cost.get(tk, 0.0) / abs(sh) if sh else 0.0
                rows.append({"ticker": tk, "name": s.name, "shares": sh, "price": s.price, "avg": avg,
                             "pnl": (s.price - avg) * sh})
        return {"cash": a.cash, "free": self.free_cash(a), "equity": self.equity(a), "positions": rows,
                "trades": a.trades, "margin_calls": a.margin_calls, "fees": a.fees_paid}

    def tournaments_for(self, p):
        out = []
        for t in self.tournaments:
            joined = p.token in t["entrants"]
            mine = None
            if joined:
                rows = self.tournament_standings(t)
                rank = next((i + 1 for i, r in enumerate(rows) if r["token"] == p.token), None)
                mine = {"ret": self.tournament_return(t, p.token), "rank": rank, "of": len(rows),
                        "account": self._account_view(t, p.token)}
            out.append({"id": t["id"], "name": t["name"], "kind": t["kind"], "start": t["start"], "end": t["end"],
                        "join_until": t["join_until"], "open": self.now < t["join_until"] and not joined,
                        "balance": self._contest_balance(), "entrants": len(t["entrants"]), "joined": joined,
                        "mine": mine,
                        "top": [{"name": r["name"], "ret": r["ret"]} for r in self.tournament_standings(t)[:5]]})
        return {"active": out, "finished": list(self.tournament_history)[::-1][:6]}

    def _dump_tournaments(self):
        out = []
        for t in self.tournaments:
            sb = self._sandboxes.get(t["id"])
            out.append({**t, "accounts": {tok: dump_account(a) for tok, a in sb.players.items()} if sb else {}})
        return out

    def _load_tournaments(self, rows):
        """Contests from before paper accounts existed are dropped: their entrants had no paper balance."""
        PlayerCls = self._player_class()
        self.tournaments, self._sandboxes = [], {}
        for t in rows:
            if t.get("kind") not in CONTESTS or t.get("v") != 2:
                continue
            accounts = t.pop("accounts", {})
            self.tournaments.append(t)
            sb = self._sandbox(t)
            for tok, x in accounts.items():
                if tok in t["entrants"]:
                    sb.players[tok] = load_account(PlayerCls, tok, x, self.stocks)
            t["entrants"] = {tok: e for tok, e in t["entrants"].items() if tok in sb.players}

    # ------------------------------------------------------------------------------------------ public profiles
    def _snapshot_holdings(self):
        if self.now - self._holdsnap_t < SNAP_EVERY:
            return
        self._holdsnap_t = self.now
        for p in self.players.values():
            if p.bot:
                continue
            eq = max(self.equity(p), 1e-9)
            rows = []
            for tk, sh in p.hold.items():
                st = self.stocks.get(tk)
                if st:
                    rows.append({"ticker": tk, "side": "long" if sh > 0 else "short",
                                 "weight": abs(sh) * st.price / eq})
            rows.sort(key=lambda r: -r["weight"])
            p.hold_snaps.append((self.now, rows))

    def _delayed_holdings(self, p):
        """The newest snapshot that is at least `public_delay_seconds` old, so nobody can copy a trade as it happens."""
        delay = float(self.settings.get("public_delay_seconds", 300))
        chosen = None
        for t, rows in p.hold_snaps:
            if self.now - t >= delay:
                chosen = (t, rows)
        return {"as_of": chosen[0], "positions": chosen[1]} if chosen else None

    def public_profile(self, name, viewer=None):
        p = self._find(name)
        if p is None:
            return None
        mine = viewer is not None and viewer.token == p.token
        out = {"name": p.name, "bot": p.bot, "public": p.public,
               "achievements": [{"id": a, "name": ACH_NAMES[a], "t": t}
                                for a, t in sorted(p.achievements.items(), key=lambda kv: kv[1])],
               "badges": list(p.badges),
               "followers": sum(1 for x in self.players.values() if p.name in x.following),
               "following_them": viewer is not None and p.name in viewer.following, "me": mine}
        if p.public or mine:     # results and holdings are only shown to others when the player opted in
            eq = self.equity(p)
            out.update({"trades": p.trades, "season_ret": self.season_return(p, eq),
                        "alltime_ret": (eq - p.deposited) / p.deposited if p.deposited > 0 else 0.0,
                        "rank": self.rank.get(p.token),
                        "holdings": self._delayed_holdings(p),
                        "holdings_delay": float(self.settings.get("public_delay_seconds", 300))})
        return out

    def set_public(self, p, public):
        p.public = bool(public)
        return True, "Your portfolio is now " + ("public (others see it after a delay)" if p.public else "private")

    # ------------------------------------------------------------------------------------------ following
    def follow(self, p, name):
        target = self._find(name)
        if target is None or target.bot:
            return False, "No such player"
        if target.token == p.token:
            return False, "You can't follow yourself"
        if target.name in p.following:
            return False, "Already following"
        if len(p.following) >= FOLLOW_MAX:
            return False, f"You can follow at most {FOLLOW_MAX} players"
        p.following.append(target.name)
        return True, f"Following {target.name}"

    def unfollow(self, p, name):
        for n in list(p.following):
            if n.lower() == str(name).lower():
                p.following.remove(n)
                return True, f"Unfollowed {n}"
        return False, "You weren't following them"

    def following_for(self, p):
        return [x for x in (self.public_profile(n, p) for n in p.following) if x]

    # ------------------------------------------------------------------------------------------ chat
    def post_chat(self, p, text, channel="global", share_t=None):
        """Returns (ok, message or error text, the message dict). Cleaned, rate limited and subject to mutes."""
        if not self.settings.get("chat_enabled", True):
            return False, "Chat is switched off", None
        if p.bot:
            return False, "Bots cannot chat", None
        gate = self._chat_gate(p)
        if gate:
            return False, gate, None
        if self.muted.get(p.token, 0) > self.now:
            return False, "You are muted for another %d minute(s)" % math.ceil((self.muted[p.token] - self.now) / 60), None
        body = clean_chat(text, self._filter())
        if not body:
            return False, "Say something first", None
        if channel != "global":
            return False, "There is only the global chat", None
        if self.now - p.last_chat < CHAT_MIN_GAP:
            return False, "Slow down a little", None
        p.chat_times = [t for t in p.chat_times if self.now - t < 60]
        if len(p.chat_times) >= CHAT_PER_MINUTE:
            return False, "Too many messages this minute", None
        if p.last_chat_text == (body, channel) and self.now - p.last_chat < 15:
            return False, "You just said that", None
        share = None
        if share_t not in (None, ""):
            try:
                want = float(share_t)
            except (TypeError, ValueError):
                return False, "Bad trade reference", None
            entry = next((x for x in p.log if abs(x["t"] - want) < 1e-6 and x["k"] != "margin_call"), None)
            if entry is None:
                return False, "That trade is too old to share", None
            share = {"kind": entry["k"], "ticker": entry["tk"], "shares": entry["sh"], "price": entry["px"]}
        self.chat_seq += 1
        msg = {"id": self.chat_seq, "t": self.now, "name": p.name, "text": body, "channel": channel, "share": share}
        p.last_chat, p.last_chat_text = self.now, (body, channel)
        p.chat_times.append(self.now)
        self.chat.append(msg)
        return True, "sent", msg

    def chat_history(self, p, limit=50):
        """The latest messages, oldest first."""
        return list(self.chat)[-limit:]

    def chat_audience(self, msg):
        """The tokens that should receive a message: None means everyone (there is only the global chat)."""
        return None

    def _all_chat(self):
        return [self.chat]

    def delete_chat(self, msg_id, actor=None):
        n = 0
        for dq in self._all_chat():
            for m in list(dq):
                if m["id"] == int(msg_id):
                    dq.remove(m)
                    n += 1
                    if actor:
                        self._log_mod(actor, "delete", m["name"], m["text"])
        return n

    def _filter(self):
        """The word filter, rebuilt if the content packs add words (`chat_bad_words`)."""
        extra = tuple(self.settings.get("chat_bad_words", ()))
        if extra != self._bad_key:
            self._bad_re, self._bad_key = (build_filter(extra) if extra else _BAD_RE), extra
        return self._bad_re

    def _chat_gate(self, p):
        """New accounts must have traded a little before they can chat or report (a throwaway account that has never
        played can't spam or mass-report)."""
        mail = self.email_gate(p)
        if mail:
            return mail
        need = int(self.settings.get("chat_min_trades", 3))
        have = int(p.counters.get("trades", 0))
        if have < need:
            return f"Make {need} trades before you chat or report (you have made {have})"
        return None

    def _log_mod(self, actor, action, name, detail=""):
        self.mod_log.append({"t": self.now, "actor": actor, "action": action, "name": name, "detail": str(detail)[:160]})

    def report_chat(self, p, msg_id):
        gate = self._chat_gate(p) if not p.bot else "Bots cannot report"
        if gate:
            return False, gate
        msg = next((m for dq in self._all_chat() for m in dq if m["id"] == int(msg_id)), None)
        if msg is None:
            return False, "That message is gone"
        if msg["name"] == p.name:
            return False, "You can't report your own message"
        if any(r["id"] == msg["id"] and r["by"] == p.name for r in self.chat_reports):
            return False, "You already reported that"
        self.chat_reports.append({"id": msg["id"], "by": p.name, "name": msg["name"], "text": msg["text"], "t": self.now})
        reporters = {r["by"] for r in self.chat_reports if r["id"] == msg["id"]}
        if len(reporters) >= int(self.settings.get("chat_report_threshold", 3)):
            self._auto_moderate(msg, len(reporters))
            return True, "Thanks, the message has been removed"
        return True, "Thanks, a moderator will take a look"

    MUTE_STEPS = (600, 3600, 86400)             # the first automatic mute is 10 minutes, then an hour, then a day

    def _auto_moderate(self, msg, n):
        """Enough different players reported a message: remove it and mute its author, for longer each time."""
        self.delete_chat(msg["id"])
        self.pending_deletes.append(msg["id"])
        author = self._find(msg["name"])
        if author is None or author.bot:
            return
        author.strikes += 1
        seconds = self.MUTE_STEPS[min(author.strikes - 1, len(self.MUTE_STEPS) - 1)]
        self.muted[author.token] = self.now + seconds
        self._notify(author, f"A message of yours was reported by {n} players and removed. You are muted for "
                             f"{seconds // 60} minutes. If that was a mistake you can appeal on the social page.")
        self._log_mod("auto", "mute", author.name, f"{n} reports on message {msg['id']}; strike {author.strikes}, {seconds // 60} min")

    def take_auto_deletes(self):
        out, self.pending_deletes = self.pending_deletes, []
        return out

    # ---- appeals
    def appeal(self, p, text):
        if self.muted.get(p.token, 0) <= self.now:
            return False, "You are not muted"
        if any(a["token"] == p.token and a["status"] == "open" for a in self.appeals):
            return False, "You already have an appeal waiting for a moderator"
        body = clean_chat(text, self._filter())[:300]
        if len(body) < 5:
            return False, "Tell the moderators why the mute was a mistake (at least a few words)"
        self.appeal_seq += 1
        self.appeals.append({"id": self.appeal_seq, "name": p.name, "token": p.token, "text": body, "t": self.now,
                             "status": "open"})
        del self.appeals[:-100]
        self._log_mod(p.name, "appeal", p.name, body)
        return True, "Your appeal was sent to the moderators"

    def appeals_for_admin(self):
        rows = sorted(self.appeals, key=lambda a: (a["status"] != "open", -a["t"]))[:50]
        return [{k: v for k, v in a.items() if k != "token"} for a in rows]        # a player's token never leaves the server

    def resolve_appeal(self, appeal_id, decision):
        a = next((x for x in self.appeals if x["id"] == int(appeal_id)), None)
        if a is None or a["status"] != "open":
            return False, "No such open appeal"
        p = self.by_token.get(a["token"])
        if decision == "lift":
            a["status"] = "lifted"
            if p:
                self.muted.pop(p.token, None)
                p.strikes = max(0, p.strikes - 1)                      # a mistake does not count against them
                self._notify(p, "A moderator lifted your chat mute. Sorry about that.")
            self._log_mod("admin", "appeal lifted", a["name"], a["text"])
            return True, f"Lifted the mute on {a['name']}"
        if decision == "deny":
            a["status"] = "denied"
            if p:
                self._notify(p, "A moderator looked at your appeal and kept the mute.")
            self._log_mod("admin", "appeal denied", a["name"], a["text"])
            return True, f"Kept the mute on {a['name']}"
        return False, "Decision must be lift or deny"

    def mute(self, name, seconds, actor=None):
        p = self._find(name)
        if p is None:
            return False, "Unknown player"
        seconds = max(0.0, float(seconds))
        if seconds <= 0:
            self.muted.pop(p.token, None)
            if actor:
                self._log_mod(actor, "unmute", p.name)
            return True, f"Unmuted {p.name}"
        self.muted[p.token] = self.now + seconds
        if actor:
            self._log_mod(actor, "mute", p.name, f"{int(seconds // 60)} minutes")
        return True, f"Muted {p.name} for {int(seconds // 60)} minutes"

    def admin_social(self):
        return {"messages": [m for dq in self._all_chat() for m in dq][-100:][::-1],
                "reports": list(self.chat_reports)[::-1],
                "muted": [{"name": self.by_token[t].name, "left": int(u - self.now)}
                          for t, u in self.muted.items() if u > self.now and t in self.by_token],
                "appeals": self.appeals_for_admin(), "mod_log": list(self.mod_log)[-40:][::-1],
                "tournaments": [{"id": t["id"], "entrants": len(t["entrants"])} for t in self.tournaments]}

    # ------------------------------------------------------------------------------------------ the periodic work
    def _social_tick(self):
        """Every 5 seconds: tournaments, time-based achievements and quests, holdings snapshots."""
        if self.now - self._social_t < 5:
            return
        self._social_t = self.now
        self._tournament_tick()
        for p in self.players.values():
            if not p.bot:
                self._check_achievements(p)
                self._check_quests(p)
        self._snapshot_holdings()

    def _end_season_social(self):
        for p in self.players.values():
            p.peak, p.maxdd = None, 0.0

    # ------------------------------------------------------------------------------------------ what a player sees about themselves
    def me_for(self, p):
        return {"name": p.name,
                "achievements": [{"id": a[0], "name": a[1], "description": a[2], "t": p.achievements.get(a[0])}
                                 for a in ACHIEVEMENTS],
                "unlocked": len(p.achievements), "total": len(ACHIEVEMENTS), "badges": list(p.badges),
                "quests": self.quests_for(p), "tournaments": self.tournaments_for(p),
                "following": list(p.following),
                "public": p.public, "muted": max(0, int(self.muted.get(p.token, 0) - self.now)), "strikes": p.strikes,
                "appeal": next((a["status"] for a in reversed(self.appeals) if a["token"] == p.token), None),
                "account": {"has_password": p.pw is not None,
                            "sessions": sum(1 for v in self.sessions.values() if v["p"] == p.token),
                            "email": mask_email(p.email), "email_verified": bool(p.email_verified),
                            "email_pending": mask_email(p.email_pending), "email_mode": self.email_mode()},
                "chat_ready": self._chat_gate(p) is None, "chat_gate": self._chat_gate(p),
                "chat_trades_left": max(0, int(self.settings.get("chat_min_trades", 3)) - int(p.counters.get("trades", 0))),
                "counters": dict(p.counters), "dd": p.maxdd,
                "rank": {"season": self.rank.get(p.token), "pnl": self.rank_pnl.get(p.token)}}
