"""The social side of the game: badges (achievements), the day and all-time boards, public profiles, following and a
moderated chat. (The daily quests, the quest ladder and the daily contest were removed on 2026-11-07: ROADMAP U10.)

It is a mixin for the Engine: the engine owns the players and the money, this file owns everything built on top of
them. Nothing here ever changes anyone's cash or any price, and every reward is cosmetic (badges, streaks), so none
of it can create an edge or break the token books.
"""
import math
import re
import unicodedata
from collections import deque

from accounts import mask_email

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
]
ACH_NAMES = {a[0]: a[1] for a in ACHIEVEMENTS}

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

PLAYER_FIELDS = ("achievements", "counters", "maxdd", "peak", "public", "following", "opened", "strikes")


def init_player(p):
    """Give a Player every field the social features use."""
    p.achievements = {}          # achievement id -> time unlocked
    p.counters = {}              # lifetime counts: trades, shorts, profitable closes, ...
    p.opened = {}                # ticker -> when the position currently held was opened
    p.peak = None                # best season return index so far (for the drawdown)
    p.maxdd = 0.0                # worst fall from that peak this season, as a share of the peak
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
        self.last_reversal = {}                    # ticker -> time of its latest REVERSAL headline
        self._social_t = 0.0
        self._holdsnap_t = 0.0
        self.boards = {"pnl": [], "ret": []}
        self.rank_pnl = {}
        self.rank_ret = {}
        self.board_day_pnl = []                    # the day board by profit in MB (self.board is by return)
        self.rank_day_pnl = {}

    def social_dump(self):
        return {"chat_seq": self.chat_seq, "chat": list(self.chat), "muted": self.muted,
                "reports": list(self.chat_reports), "mod_log": list(self.mod_log), "appeals": self.appeals[-100:],
                "appeal_seq": self.appeal_seq}

    def social_load(self, d):
        self.chat_seq = int(d.get("chat_seq", 0))
        self.chat.extend(m for m in d.get("chat", []) if m.get("channel", "global") == "global")
        self.muted = {k: float(v) for k, v in dict(d.get("muted", {})).items()}
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
        if s.asset_type == "index":
            c["index_trades"] = c.get("index_trades", 0) + 1
        if self._is_haven(s):
            c["haven_trades"] = c.get("haven_trades", 0) + 1
        close_pnl = pnl if kind in ("sell", "cover") else None
        if close_pnl is not None and close_pnl > 0:
            c["profit_closes"] = c.get("profit_closes", 0) + 1
        self._check_achievements(p, close=(kind, s.ticker, close_pnl, held_since) if close_pnl is not None else None)
        self._learn_close(p, s.ticker, close_pnl, closed)                    # closes, stops and R for the path (learning.py)

    def _on_dividend(self, p, amount):
        if amount > 0:
            p.counters["dividends"] = p.counters.get("dividends", 0) + 1
            self._check_achievements(p)

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
            pnl.append({"name": r["name"], "token": r["token"], "pnl": gain, "bot": bool(p.hb),
                        "ret": gain / p.deposited if p.deposited > 0 else 0.0})
        pnl.sort(key=lambda x: -x["pnl"])
        ret = sorted(pnl, key=lambda x: -x["ret"])
        self.boards = {"pnl": pnl, "ret": ret}
        self.rank_pnl = {x["token"]: i + 1 for i, x in enumerate(pnl)}
        self.rank_ret = {x["token"]: i + 1 for i, x in enumerate(ret)}

    def boards_for(self, p, top=20):
        """The boards as player `p` sees them; `p` None is a visitor without an account, who sees them with no place of
        their own (growth plan, 2026-11-10). `bot` marks a house bot."""
        me = p.token if p is not None else None
        def trim(rows, keys):
            return [{"rank": i + 1, "me": r["token"] == me, **{k: r.get(k) for k in keys}}
                    for i, r in enumerate(rows[:top])]
        def day(rows):
            return [{"rank": i + 1, "me": r["token"] == me, "name": r["name"], "bot": r.get("bot", False),
                     "ret": r["ret"], "gain": r.get("gain", 0.0), "equity": r["equity"]} for i, r in enumerate(rows[:top])]
        # four boards: today and all time, each by return (%) and by profit (MB)
        return {"season": day(self.board), "day_pnl": day(self.board_day_pnl),
                "pnl": trim(self.boards["pnl"], ("name", "pnl", "ret", "bot")),
                "ret": trim(self.boards.get("ret", []), ("name", "pnl", "ret", "bot")),
                "mine": {} if p is None else
                        {"season": self.rank.get(p.token), "day_pnl": self.rank_day_pnl.get(p.token),
                         "pnl": self.rank_pnl.get(p.token), "ret": self.rank_ret.get(p.token), "dd": p.maxdd},
                "counts": {"season": len(self.board), "day_pnl": len(self.board_day_pnl), "pnl": len(self.boards["pnl"]),
                           "ret": len(self.boards.get("ret", []))},
                "players": len(self.players)}

    # ------------------------------------------------------------------------------------------ public profiles
    def _snapshot_holdings(self):
        if self.now - self._holdsnap_t < SNAP_EVERY:
            return
        self._holdsnap_t = self.now
        for p in self.players.values():
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
        out = {"name": p.name, "public": p.public, "bot": bool(p.hb),
               "achievements": [{"id": a, "name": ACH_NAMES[a], "t": t}
                                for a, t in sorted(p.achievements.items(), key=lambda kv: kv[1])],
               "followers": sum(1 for x in self.players.values() if p.name in x.following),
               "following_them": viewer is not None and p.name in viewer.following, "me": mine,
               "daily": self.daily_stats_for(p), "learning": self.learning_summary(p)}
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
        if target is None:
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
        gate = self._chat_gate(p)
        if gate:
            return False, gate, None
        if self.muted.get(p.token, 0) > self.now:
            mins = math.ceil((self.muted[p.token] - self.now) / 60)
            return False, f"You are muted for another {mins} minute{'' if mins == 1 else 's'}", None
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
        gate = self._chat_gate(p)
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
        if author is None:
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
                "appeals": self.appeals_for_admin(), "mod_log": list(self.mod_log)[-40:][::-1]}

    # ------------------------------------------------------------------------------------------ the periodic work
    def _social_tick(self):
        """Every 5 seconds: time-based achievements and holdings snapshots."""
        if self.now - self._social_t < 5:
            return
        self._social_t = self.now
        for p in self.players.values():
            self._check_achievements(p)
        self._snapshot_holdings()

    def _end_season_social(self):
        for p in self.players.values():
            p.peak, p.maxdd = None, 0.0

    # ------------------------------------------------------------------------------------------ what a player sees about themselves
    def me_for(self, p):
        return {"name": p.name,
                "achievements": [{"id": a[0], "name": a[1], "description": a[2], "t": p.achievements.get(a[0])}
                                 for a in ACHIEVEMENTS],
                "unlocked": len(p.achievements), "total": len(ACHIEVEMENTS),
                "following": list(p.following),
                "public": p.public, "muted": max(0, int(self.muted.get(p.token, 0) - self.now)), "strikes": p.strikes,
                "appeal": next((a["status"] for a in reversed(self.appeals) if a["token"] == p.token), None),
                "account": {"has_password": p.pw is not None,
                            "sessions": sum(1 for v in self.sessions.values() if v["p"] == p.token),
                            "email": mask_email(p.email), "email_verified": bool(p.email_verified),
                            "email_pending": mask_email(p.email_pending), "email_mode": self.email_mode()},
                "chat_ready": self._chat_gate(p) is None, "chat_gate": self._chat_gate(p),
                "chat_trades_left": max(0, int(self.settings.get("chat_min_trades", 3)) - int(p.counters.get("trades", 0))),
                "counters": dict(p.counters), "dd": p.maxdd, "daily": self.daily_stats_for(p), "learning": self.learning_summary(p),
                "invite": self.invite_code(p), "invited": self.invited_count(p),
                "rank": {"season": self.rank.get(p.token), "pnl": self.rank_pnl.get(p.token)}}
