"""Trading bots and backtests (Expert).

A bot trades on its owner's account by rules the owner writes. It watches a few stocks on one candle size (1m to 1h);
when a candle closes it works out each rule's condition on the candles so far, and the first rule that is true and makes
sense for the position (no buying when already long, no covering when not short, ...) is carried out through the same
trading code a player's own clicks use (fees, leverage, cooldowns and all). Stops and targets are checked every second.

**The rule language** is small and safe: it is parsed here (never `eval`), and can only read the market and the
account, never anything else. A condition is an expression like

    cross_above(close, ema(20)) and rsi(14) < 70
    price >= ema(200) or pnl_pct <= -5
    news_score > 2 and change(12) > 0

* numbers, `+ - * / %`, comparisons `< <= > >= == !=`, `and`, `or`, `not`, brackets;
* the candles: `open high low close volume` (the last finished candle; `prev(x, n)` looks n candles back), and `price`
  (the price now);
* indicators (the lengths are numbers): `sma(n) ema(n) wma(n) rsi(n) macd(fast, slow) macd_signal(fast, slow, signal)
  macd_hist(fast, slow, signal) atr(n) bb_upper(n, k) bb_mid(n) bb_lower(n, k) stoch_k(n) stoch_d(n, d) highest(n)
  lowest(n) change(n) volume_sma(n) vwap()`; `highest(n)` and `lowest(n)` are of the n candles before this one, so a
  breakout reads `close > highest(20)`;
* `cross_above(a, b)` and `cross_below(a, b)`: a crossed b on this candle;
* the account: `position` (shares held, negative when short), `long`, `short`, `flat`, `entry` (the average entry
  price), `pnl_pct` (the open position's move from its entry, in %, its way), `cash`, `equity`, `calls`, `puts` (option
  positions held on the stock);
* the news: `news_score` (this stock's headlines) and `market_news` (headlines about no single company), each headline
  scored with the bot's own words and weights and fading with its half-life;
* `abs(x) min(a, b) max(a, b)`.

**Actions:** `buy` (open a long), `sell` (close a long), `short` (open a short), `cover` (close a short), `close`
(close either), `buy_call`, `buy_put` (at a strike a given % out of the money and one of the five expiries) and
`sell_options` (sell back the options held on the stock). Sizes are a % of the free cash or an amount of MB (options:
as many whole 100-share contracts as that buys); buys and shorts can be leveraged (Pro, which Expert includes).

**Backtests** run a bot over the candles kept for a stock (up to 500 of each size, and three real days of one-minute
candles), in the same way: rules at each candle's close, orders filled at the next candle's open, the same fee, leverage
with its interest and its margin, stops and targets on the candles' highs and lows, options priced as the game prices
them (Black-Scholes on the stock's recent volatility plus the premium and the spread). The news score uses the headlines
the stock has kept. The result is the trades, the equity curve and how it did against simply holding the stock.
"""
import functools
import math
import re
import time
import uuid

import options

TIMEFRAMES = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600}
ACTIONS = ("buy", "sell", "short", "cover", "close", "buy_call", "buy_put", "sell_options")
MAX_BOTS = 5
TRANSIENT = ("last", "_scored")     # a bot's keys that are never saved or sent: candles seen, headlines scored
MAX_TICKERS = 10
MAX_RULES = 10
MAX_EXPR = 300
MAX_NODES = 120
FEE = 0.001
DEFAULT_WORDS = {
    "beat*": 2, "raise*": 1.5, "record": 1, "surge*": 1.5, "soar*": 2, "jump*": 1, "win*": 1.5, "upgrade*": 2,
    "approv*": 2, "expand*": 1, "strong": 1, "buyback": 1.5, "partnership": 1, "contract": 1, "rebound*": 1,
    "rall*": 1.5, "rescue*": 1.5, "above the forecast": 1,
    "miss*": -2, "cut*": -1.5, "downgrade*": -2, "recall*": -2, "lawsuit*": -1.5, "probe*": -1.5,
    "investigation": -1.5, "warn*": -1.5, "delay*": -1, "fall*": -1, "plunge*": -2, "slump*": -1.5, "weak*": -1,
    "loss*": -1, "layoff*": -1, "fraud": -3, "bankrupt*": -3, "default*": -2, "resign*": -1, "shortage*": -1,
    "offering": -1, "dilut*": -1.5, "below the forecast": -1,
}

# ------------------------------------------------------------------------------------------------ the rule language
SERIES = ("open", "high", "low", "close", "volume")
SCALARS = ("price", "position", "long", "short", "flat", "entry", "pnl_pct", "cash", "equity", "calls", "puts",
           "news_score", "market_news")
# name: (fewest arguments, most arguments, the defaults for missing ones, are the arguments lengths?)
FUNCS = {
    "sma": (1, 1, (), True), "ema": (1, 1, (), True), "wma": (1, 1, (), True), "rsi": (0, 1, (14,), True),
    "macd": (0, 2, (12, 26), True), "macd_signal": (0, 3, (12, 26, 9), True), "macd_hist": (0, 3, (12, 26, 9), True),
    "atr": (0, 1, (14,), True), "bb_upper": (0, 2, (20, 2), True), "bb_mid": (0, 1, (20,), True),
    "bb_lower": (0, 2, (20, 2), True), "stoch_k": (0, 1, (14,), True), "stoch_d": (0, 2, (14, 3), True),
    "highest": (1, 1, (), True), "lowest": (1, 1, (), True), "change": (1, 1, (), True),
    "volume_sma": (1, 1, (), True), "vwap": (0, 0, (), True),
    "cross_above": (2, 2, (), False), "cross_below": (2, 2, (), False), "prev": (2, 2, (), False),
    "abs": (1, 1, (), False), "min": (2, 2, (), False), "max": (2, 2, (), False),
}
_TOK = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|([A-Za-z_][A-Za-z0-9_]*)|(<=|>=|==|!=|[-+*/%<>(),]))")


class RuleError(ValueError):
    pass


def _tokens(text):
    out, pos = [], 0
    text = text.rstrip()
    while pos < len(text):
        m = _TOK.match(text, pos)
        if not m or m.end() == pos:
            raise RuleError(f"I can't read '{text[pos:pos + 12].strip()}'")
        num, name, op = m.groups()
        out.append(("num", float(num)) if num else ("name", name.lower()) if name else ("op", op))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, tokens):
        self.t, self.i, self.nodes = tokens, 0, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, kind=None, value=None):
        tok = self.peek()
        if tok[0] is None or (kind and tok[0] != kind) or (value is not None and tok[1] != value):
            want = value or kind or "more"
            raise RuleError(f"Expected {want!r}" + (f" but found {tok[1]!r}" if tok[0] else " at the end"))
        self.i += 1
        return tok

    def node(self, *n):
        self.nodes += 1
        if self.nodes > MAX_NODES:
            raise RuleError("That rule is too long")
        return n

    def expr(self):
        a = self.and_()
        while self.peek() == ("name", "or"):
            self.take()
            a = self.node("or", a, self.and_())
        return a

    def and_(self):
        a = self.not_()
        while self.peek() == ("name", "and"):
            self.take()
            a = self.node("and", a, self.not_())
        return a

    def not_(self):
        if self.peek() == ("name", "not"):
            self.take()
            return self.node("not", self.not_())
        return self.cmp()

    def cmp(self):
        a = self.add()
        tok = self.peek()
        if tok[0] == "op" and tok[1] in ("<", "<=", ">", ">=", "==", "!="):
            self.take()
            return self.node("cmp", tok[1], a, self.add())
        return a

    def add(self):
        a = self.mul()
        while self.peek()[0] == "op" and self.peek()[1] in "+-":
            op = self.take()[1]
            a = self.node("bin", op, a, self.mul())
        return a

    def mul(self):
        a = self.unary()
        while self.peek()[0] == "op" and self.peek()[1] in "*/%":
            op = self.take()[1]
            a = self.node("bin", op, a, self.unary())
        return a

    def unary(self):
        if self.peek() == ("op", "-"):
            self.take()
            return self.node("neg", self.unary())
        return self.atom()

    def atom(self):
        tok = self.peek()
        if tok[0] == "num":
            self.take()
            return self.node("num", tok[1])
        if tok == ("op", "("):
            self.take()
            a = self.expr()
            self.take("op", ")")
            return a
        if tok[0] == "name":
            self.take()
            name = tok[1]
            if name in ("true", "false"):
                return self.node("num", 1.0 if name == "true" else 0.0)
            if self.peek() == ("op", "("):
                self.take()
                args = []
                if self.peek() != ("op", ")"):
                    args.append(self.expr())
                    while self.peek() == ("op", ","):
                        self.take()
                        args.append(self.expr())
                self.take("op", ")")
                return self._call(name, args)
            if name in SERIES or name in SCALARS:
                return self.node("var", name)
            raise RuleError(f"There is no '{name}' (see the list of words a rule can use)")
        raise RuleError("Expected a number, a word or a bracket" + (f", not {tok[1]!r}" if tok[0] else " at the end"))

    def _call(self, name, args):
        if name not in FUNCS:
            raise RuleError(f"There is no function '{name}'")
        lo, hi, defaults, lengths = FUNCS[name]
        if not lo <= len(args) <= hi:
            raise RuleError(f"{name}() takes {lo if lo == hi else f'{lo} to {hi}'} number{'s' if hi != 1 else ''}")
        if lengths:
            vals = []
            for a in args:
                if a[0] != "num":
                    raise RuleError(f"{name}() needs plain numbers, like {name}(20)")
                vals.append(a[1])
            vals += list(defaults[len(vals):])
            if any(not (0 < v <= 500) for v in vals):
                raise RuleError(f"{name}(): lengths are between 1 and 500")
            return self.node("ind", name, tuple(vals))
        if name == "prev" and not (args[1][0] == "num" and 1 <= args[1][1] <= 200):
            raise RuleError("prev(x, n) needs a number of candles n from 1 to 200")
        return self.node("call", name, tuple(args))


@functools.lru_cache(maxsize=1024)
def parse(text):
    """The rule as a tree, or RuleError with what is wrong (a rule is parsed once, then remembered)."""
    text = str(text or "").strip()
    if not text:
        raise RuleError("The rule is empty")
    if len(text) > MAX_EXPR:
        raise RuleError(f"A rule is at most {MAX_EXPR} characters")
    p = _Parser(_tokens(text))
    tree = p.expr()
    if p.i != len(p.t):
        raise RuleError(f"I don't understand what follows '{p.t[p.i - 1][1] if p.i else ''}'")
    return tree


# ------------------------------------------------------------------------------------------------ indicators
def _sma(v, n):
    n = int(n)
    out, s = [None] * len(v), 0.0
    for i, x in enumerate(v):
        s += x
        if i >= n:
            s -= v[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def _ema(v, n):
    n = int(n)
    out = [None] * len(v)
    k = 2 / (n + 1)
    e = None
    for i, x in enumerate(v):
        if x is None:
            continue
        if e is None:
            if i >= n - 1 and all(y is not None for y in v[i - n + 1:i + 1]):
                e = sum(v[i - n + 1:i + 1]) / n
                out[i] = e
            continue
        e = x * k + e * (1 - k)
        out[i] = e
    return out


def _wma(v, n):
    n = int(n)
    w = n * (n + 1) / 2
    return [None if i < n - 1 else sum(v[i - n + 1 + j] * (j + 1) for j in range(n)) / w for i in range(len(v))]


def _rma(v, n):
    n = int(n)
    out, r = [None] * len(v), None
    for i, x in enumerate(v):
        if x is None:
            continue
        if r is None:
            if i >= n and all(y is not None for y in v[i - n + 1:i + 1]):
                r = sum(v[i - n + 1:i + 1]) / n
                out[i] = r
            continue
        r = (r * (n - 1) + x) / n
        out[i] = r
    return out


def _rsi(c, n):
    gains = [None] + [max(c[i] - c[i - 1], 0.0) for i in range(1, len(c))]
    losses = [None] + [max(c[i - 1] - c[i], 0.0) for i in range(1, len(c))]
    g, lo = _rma(gains, n), _rma(losses, n)
    return [None if a is None or b is None else (100.0 if b == 0 else 100 - 100 / (1 + a / b)) for a, b in zip(g, lo)]


def _sub(a, b):
    return [None if x is None or y is None else x - y for x, y in zip(a, b)]


class Series:
    """A stock's candles (oldest first) and the indicators worked out on them, each a list as long as the candles. Every
    indicator at candle i depends only on candles up to i, so a backtest can work them out once."""

    def __init__(self, candles):
        self.t = [c[0] for c in candles]
        self.o = [c[1] for c in candles]
        self.h = [c[2] for c in candles]
        self.l = [c[3] for c in candles]
        self.c = [c[4] for c in candles]
        self.v = [c[5] if len(c) > 5 else 0.0 for c in candles]
        self.cache = {}

    def __len__(self):
        return len(self.c)

    def ind(self, name, args):
        key = (name, args)
        got = self.cache.get(key)
        if got is None:
            got = self.cache[key] = self._make(name, args)
        return got

    def _make(self, name, a):
        c, h, l, v = self.c, self.h, self.l, self.v
        if name == "sma":
            return _sma(c, a[0])
        if name == "ema":
            return _ema(c, a[0])
        if name == "wma":
            return _wma(c, a[0])
        if name == "rsi":
            return _rsi(c, a[0])
        if name in ("macd", "macd_signal", "macd_hist"):
            line = _sub(_ema(c, a[0]), _ema(c, a[1]))
            if name == "macd":
                return line
            sig = _ema(line, a[2])
            return sig if name == "macd_signal" else _sub(line, sig)
        if name == "atr":
            tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
            return _rma(tr, a[0])
        if name in ("bb_upper", "bb_mid", "bb_lower"):
            n = int(a[0])
            mid = _sma(c, n)
            if name == "bb_mid":
                return mid
            k = a[1] if len(a) > 1 else 2
            out = [None] * len(c)
            for i in range(n - 1, len(c)):
                seg = c[i - n + 1:i + 1]
                m = mid[i]
                sd = math.sqrt(sum((x - m) ** 2 for x in seg) / n)
                out[i] = m + (k if name == "bb_upper" else -k) * sd
            return out
        if name in ("stoch_k", "stoch_d"):
            n = int(a[0])
            k = [None] * len(c)
            for i in range(n - 1, len(c)):
                hi, lo = max(h[i - n + 1:i + 1]), min(l[i - n + 1:i + 1])
                k[i] = 50.0 if hi == lo else 100 * (c[i] - lo) / (hi - lo)
            if name == "stoch_k":
                return k
            return _sma_none(k, a[1] if len(a) > 1 else 3)
        if name in ("highest", "lowest"):
            n = int(a[0])
            src, f = (h, max) if name == "highest" else (l, min)
            return [None if i < n else f(src[i - n:i]) for i in range(len(c))]
        if name == "change":
            n = int(a[0])
            return [None if i < n or c[i - n] <= 0 else (c[i] / c[i - n] - 1) * 100 for i in range(len(c))]
        if name == "volume_sma":
            return _sma(v, a[0])
        if name == "vwap":
            out, pv, vv, day = [None] * len(c), 0.0, 0.0, None
            for i in range(len(c)):
                d = int(self.t[i] // 1800)
                if d != day:
                    day, pv, vv = d, 0.0, 0.0
                tp = (h[i] + l[i] + c[i]) / 3
                pv += tp * v[i]
                vv += v[i]
                out[i] = pv / vv if vv > 0 else tp
            return out
        raise RuleError(name)


def _sma_none(v, n):
    n = int(n)
    out = [None] * len(v)
    for i in range(n - 1, len(v)):
        seg = v[i - n + 1:i + 1]
        if all(x is not None for x in seg):
            out[i] = sum(seg) / n
    return out


def evaluate(tree, ser, i, acct, k=0):
    """The value of a rule on candle `i - k` (k candles back). `acct` holds the account and news values."""
    kind = tree[0]
    if kind == "num":
        return tree[1]
    j = i - k
    if j < 0:
        return None
    if kind == "var":
        name = tree[1]
        if name in SERIES:
            return {"open": ser.o, "high": ser.h, "low": ser.l, "close": ser.c, "volume": ser.v}[name][j]
        if name == "price" and k > 0:
            return ser.c[j]
        return acct.get(name)
    if kind == "ind":
        return ser.ind(tree[1], tree[2])[j]
    if kind == "and":
        return 1.0 if _true(evaluate(tree[1], ser, i, acct, k)) and _true(evaluate(tree[2], ser, i, acct, k)) else 0.0
    if kind == "or":
        return 1.0 if _true(evaluate(tree[1], ser, i, acct, k)) or _true(evaluate(tree[2], ser, i, acct, k)) else 0.0
    if kind == "not":
        return 0.0 if _true(evaluate(tree[1], ser, i, acct, k)) else 1.0
    if kind == "neg":
        x = evaluate(tree[1], ser, i, acct, k)
        return None if x is None else -x
    if kind == "cmp":
        a, b = evaluate(tree[2], ser, i, acct, k), evaluate(tree[3], ser, i, acct, k)
        if a is None or b is None:
            return 0.0
        op = tree[1]
        return 1.0 if (a < b if op == "<" else a <= b if op == "<=" else a > b if op == ">" else a >= b if op == ">="
                       else abs(a - b) < 1e-9 if op == "==" else abs(a - b) >= 1e-9) else 0.0
    if kind == "bin":
        a, b = evaluate(tree[2], ser, i, acct, k), evaluate(tree[3], ser, i, acct, k)
        if a is None or b is None:
            return None
        op = tree[1]
        if op in "/%" and b == 0:
            return None
        return a + b if op == "+" else a - b if op == "-" else a * b if op == "*" else a / b if op == "/" else a % b
    if kind == "call":
        name, args = tree[1], tree[2]
        if name in ("cross_above", "cross_below"):
            a0, b0 = evaluate(args[0], ser, i, acct, k), evaluate(args[1], ser, i, acct, k)
            a1, b1 = evaluate(args[0], ser, i, acct, k + 1), evaluate(args[1], ser, i, acct, k + 1)
            if None in (a0, b0, a1, b1):
                return 0.0
            return 1.0 if ((a0 > b0 and a1 <= b1) if name == "cross_above" else (a0 < b0 and a1 >= b1)) else 0.0
        if name == "prev":
            return evaluate(args[0], ser, i, acct, k + int(args[1][1]))
        vals = [evaluate(a, ser, i, acct, k) for a in args]
        if any(x is None for x in vals):
            return None
        return abs(vals[0]) if name == "abs" else min(vals) if name == "min" else max(vals)
    raise RuleError(kind)


def _true(x):
    return x is not None and x != 0


# ------------------------------------------------------------------------------------------------ the news score
def word_score(text, words):
    """How bullish (above 0) or bearish a headline reads with these words and weights. A word ending in * matches any
    word that starts with it ("upgrade*" matches "upgraded"); a phrase matches as a whole."""
    t = " " + re.sub(r"[^a-z0-9%]+", " ", str(text).lower()) + " "
    score = 0.0
    for w, weight in words.items():
        w = w.strip().lower()
        if not w:
            continue
        if w.endswith("*"):
            if re.search(r"\b" + re.escape(w[:-1]), t):
                score += weight
        elif (" " + w + " ") in t:
            score += weight
    return score


def news_scores(items, ticker, words, halflife_min, now, cache=None):
    """(this stock's score, the market's) from recent headlines, each fading with the half-life. `cache` (a dict kept
    across calls with the same words) scores each headline once: a backtest asks again at every candle."""
    hl = max(1.0, float(halflife_min)) * 60
    mine = market = 0.0
    for n in items:
        age = now - n["t"]
        tks = n.get("tickers") or []
        if age < 0 or age > 6 * hl or (tks and ticker not in tks):
            continue
        sc = cache.get(n["text"]) if cache is not None else None
        if sc is None:
            sc = word_score(n["text"], words)
            if cache is not None:
                cache[n["text"]] = sc
        if tks:
            mine += 0.5 ** (age / hl) * sc
        else:
            market += 0.5 ** (age / hl) * sc
    return mine, market


# ------------------------------------------------------------------------------------------------ a bot's set-up
def clean_bot(raw, old=None):
    """A bot's settings from the page, checked (RuleError with what is wrong)."""
    if not isinstance(raw, dict):
        raise RuleError("Bad bot")
    name = str(raw.get("name") or "My bot").strip()[:40] or "My bot"
    tickers = []
    for t in raw.get("tickers") or []:
        t = str(t).strip().upper()[:12]
        if t and t not in tickers:
            tickers.append(t)
    if not tickers:
        raise RuleError("Give the bot at least one stock to trade")
    if len(tickers) > MAX_TICKERS:
        raise RuleError(f"At most {MAX_TICKERS} stocks a bot")
    tf = str(raw.get("timeframe") or "5m")
    if tf not in TIMEFRAMES:
        raise RuleError("The candle size is one of " + ", ".join(TIMEFRAMES))
    rules = []
    for r in raw.get("rules") or []:
        if not isinstance(r, dict):
            continue
        when = str(r.get("when") or "").strip()
        do = str(r.get("do") or "")
        if not when and not do:
            continue
        if do not in ACTIONS:
            raise RuleError(f"'{do}' is not something a bot can do")
        try:
            parse(when)
        except RuleError as e:
            raise RuleError(f"Rule {len(rules) + 1}: {e}") from None
        size = _num(r.get("size"), 10.0, 0.0, 1e9)
        unit = "mb" if r.get("unit") == "mb" else "pct"
        if unit == "pct" and not 0 < size <= 100:
            raise RuleError(f"Rule {len(rules) + 1}: a size in % is between 0 and 100")
        rules.append({"when": when, "do": do, "size": size, "unit": unit,
                      "lev": _num(r.get("lev"), 1.0, 1.0, 10.0), "strike_pct": _num(r.get("strike_pct"), 0.0, 0.0, 15.0),
                      "expiry": int(_num(r.get("expiry"), 1, 0, len(options.EXPIRY_DAYS) - 1))})
    if not rules:
        raise RuleError("Give the bot at least one rule")
    if len(rules) > MAX_RULES:
        raise RuleError(f"At most {MAX_RULES} rules a bot")
    words = {}
    for w, v in (raw.get("words") if isinstance(raw.get("words"), dict) else DEFAULT_WORDS).items():
        w = str(w).strip().lower()[:40]
        if w and len(words) < 200:
            words[w] = _num(v, 0.0, -100.0, 100.0)
    bot = {"id": (old or {}).get("id") or uuid.uuid4().hex[:10], "name": name, "tickers": tickers, "timeframe": tf,
           "rules": rules, "stop_pct": _num(raw.get("stop_pct"), 0.0, 0.0, 90.0),
           "target_pct": _num(raw.get("target_pct"), 0.0, 0.0, 1000.0), "words": words,
           "halflife": _num(raw.get("halflife"), 30.0, 1.0, 1440.0),
           "max_trades": int(_num(raw.get("max_trades"), 30, 1, 500)),
           "on": bool((old or {}).get("on", False)), "log": list((old or {}).get("log", [])), "last": {},
           "day": (old or {}).get("day", [0, 0]), "created": (old or {}).get("created") or time.time()}
    return bot


def _num(x, default, lo, hi):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(v):
        return default
    return min(hi, max(lo, v))


def init_player(p):
    p.bots = []


def dump_player(p):
    return {"bots": [{k: v for k, v in b.items() if k not in TRANSIENT} for b in p.bots]}


def load_player(p, x):
    p.bots = []
    for b in (x or {}).get("bots", []):
        try:
            c = clean_bot(b, b)
        except RuleError:
            continue
        c["on"] = bool(b.get("on"))
        p.bots.append(c)


def applicable(do, pos, opts_here):
    """Does an action make sense for the position now (no buying when long, no covering when not short, ...)?"""
    if do in ("buy", "short"):
        return abs(pos) < 1e-12
    if do == "sell":
        return pos > 1e-12
    if do == "cover":
        return pos < -1e-12
    if do == "close":
        return abs(pos) > 1e-12
    if do == "buy_call":
        return not any(o == "call" for o in opts_here)
    if do == "buy_put":
        return not any(o == "put" for o in opts_here)
    if do == "sell_options":
        return bool(opts_here)
    return False


# ------------------------------------------------------------------------------------------------ running them
class BotsMixin:
    """Mixed into the Engine: saving bots, running them every second, and backtests."""

    def bots_view(self, p):
        return {"bots": [self._bot_view(b) for b in p.bots], "expert": self.is_expert(p), "pro": self.is_pro(p),
                "timeframes": list(TIMEFRAMES), "actions": list(ACTIONS), "default_words": DEFAULT_WORDS,
                "max_bots": MAX_BOTS, "series": list(SERIES), "scalars": list(SCALARS), "funcs": sorted(FUNCS)}

    def _bot_view(self, b):
        return {k: v for k, v in b.items() if k not in TRANSIENT}

    def save_bot(self, p, raw):
        if not self.is_expert(p):
            return False, "Bots are an Expert tool (see the Shop)", None
        old = next((b for b in p.bots if b["id"] == (raw or {}).get("id")), None) if isinstance(raw, dict) else None
        if old is None and len(p.bots) >= MAX_BOTS:
            return False, f"At most {MAX_BOTS} bots", None
        try:
            bot = clean_bot(raw, old)
        except RuleError as e:
            return False, str(e), None
        bad = [t for t in bot["tickers"] if t not in self.stocks]
        if bad:
            return False, "Unknown: " + ", ".join(bad), None
        if any(r["lev"] > 1 for r in bot["rules"]) and not self.is_pro(p):
            return False, "Leverage is a Pro tool", None
        if old is None:
            p.bots.append(bot)
        else:
            p.bots[p.bots.index(old)] = bot
        return True, "Saved", bot["id"]

    def toggle_bot(self, p, bot_id, on):
        b = next((x for x in p.bots if x["id"] == bot_id), None)
        if b is None:
            return False, "No such bot"
        if on and not self.is_expert(p):
            return False, "Bots are an Expert tool (see the Shop)"
        b["on"] = bool(on)
        b["last"] = {}
        self._bot_log(b, "", "on" if on else "off", True, "Switched on" if on else "Switched off")
        return True, "On" if on else "Off"

    def delete_bot(self, p, bot_id):
        b = next((x for x in p.bots if x["id"] == bot_id), None)
        if b is None:
            return False, "No such bot"
        p.bots.remove(b)
        return True, "Deleted"

    def _bots_off(self, p, why):
        for b in p.bots:
            if b["on"]:
                b["on"] = False
                self._bot_log(b, "", "off", False, why)

    def _bot_log(self, b, tk, action, ok, msg):
        b["log"].append({"t": self.now, "tk": tk, "do": action, "ok": ok, "msg": msg[:160]})
        del b["log"][:-40]

    def _bots_tick(self):
        """Every second: each running bot checks its stops and targets, and when one of its candles closes, its rules."""
        for p in list(self.players.values()):
            if not p.bots or not any(b["on"] for b in p.bots):
                continue
            if not self.is_expert(p):
                self._bots_off(p, "Expert ended: the bots are off")
                self._notify(p, "Your Expert pass has ended, so your bots were switched off.")
                continue
            for b in p.bots:
                if b["on"]:
                    self._run_bot(p, b)

    def _run_bot(self, p, b):
        secs = TIMEFRAMES[b["timeframe"]]
        bucket = int(self.now // secs)
        day = int(self.now // 1800)
        if b["day"][0] != day:
            b["day"] = [day, 0]
        for tk in b["tickers"]:
            s = self.stocks.get(tk)
            if s is None:
                continue
            pos = p.hold.get(tk, 0.0)
            if abs(pos) > 1e-12 and (b["stop_pct"] > 0 or b["target_pct"] > 0):     # stops and targets, every second
                avg = p.cost.get(tk, 0.0) / abs(pos)
                move = (s.price / avg - 1) * 100 * (1 if pos > 0 else -1) if avg > 0 else 0.0
                if (b["stop_pct"] > 0 and move <= -b["stop_pct"]) or (b["target_pct"] > 0 and move >= b["target_pct"]):
                    why = "stop" if move < 0 else "target"
                    ok, msg = self.trade(p, tk, "sell" if pos > 0 else "buy", 1.0)
                    self._bot_log(b, tk, "close (" + why + ")", ok, msg)
                    if ok:
                        b["day"][1] += 1
                    continue
            if b["last"].get(tk) == bucket:
                continue
            b["last"][tk] = bucket
            if b["day"][1] >= b["max_trades"]:
                continue
            candles = self._finished(s, b["timeframe"])
            if len(candles) < 2:
                continue
            ser = Series(candles[-300:])
            acct = self._bot_account(p, b, s)
            for r in b["rules"]:
                if not applicable(r["do"], acct["position"], acct["_opts"]):
                    continue
                try:
                    hit = _true(evaluate(parse(r["when"]), ser, len(ser) - 1, acct))
                except (RuleError, ZeroDivisionError, OverflowError, ValueError):
                    hit = False
                if not hit:
                    continue
                ok, msg = self._bot_act(p, b, s, r, acct)
                self._bot_log(b, tk, r["do"], ok, msg)
                if ok:
                    b["day"][1] += 1
                break

    def _bot_account(self, p, b, s):
        tk = s.ticker
        pos = p.hold.get(tk, 0.0)
        avg = p.cost.get(tk, 0.0) / abs(pos) if abs(pos) > 1e-12 else 0.0
        scored = b.setdefault("_scored", {})
        if len(scored) > 2000:
            scored.clear()
        mine, market = news_scores(list(self.news_log), tk, b["words"], b["halflife"], self.now, scored)
        opts_here = [o["kind"] for o in p.opts if o["tk"] == tk]
        return {"price": s.price, "position": pos, "long": 1.0 if pos > 1e-12 else 0.0, "short": 1.0 if pos < -1e-12 else 0.0,
                "flat": 1.0 if abs(pos) <= 1e-12 else 0.0, "entry": avg,
                "pnl_pct": ((s.price / avg - 1) * 100 * (1 if pos > 0 else -1)) if avg > 0 else 0.0,
                "cash": p.cash, "equity": self.equity(p), "calls": float(opts_here.count("call")),
                "puts": float(opts_here.count("put")), "news_score": mine, "market_news": market, "_opts": opts_here}

    def _bot_act(self, p, b, s, r, acct):
        tk, do = s.ticker, r["do"]
        size = r["size"]
        pct, amount = (size / 100.0, None) if r["unit"] == "pct" else (1.0, size)
        lev = r["lev"] if r["lev"] > 1 else None
        if do in ("buy", "short"):
            return self.trade(p, tk, "buy" if do == "buy" else "sell", pct, amount, lev)
        if do == "sell" or (do == "close" and acct["position"] > 0):
            return self.trade(p, tk, "sell", 1.0)
        if do in ("cover", "close"):
            return self.trade(p, tk, "buy", 1.0)
        if do in ("buy_call", "buy_put"):
            kind = "call" if do == "buy_call" else "put"
            want = s.price * (1 + (r["strike_pct"] / 100) * (1 if kind == "call" else -1))
            exp = self.option_expiries()[r["expiry"]]
            K = min(self.listed_strikes(s, exp), key=lambda k: abs(k - want))
            mb = amount if amount is not None else max(0.0, p.cash) * pct / 1.001
            return self.buy_option(p, tk, kind, K, exp, amount=mb)
        if do == "sell_options":
            done, sold = [], False
            for o in [o for o in p.opts if o["tk"] == tk]:
                p.last_trade.pop("opt:" + tk, None)          # (one action: every position on the stock goes at once)
                ok, msg = self.sell_option(p, o["id"], 1.0)
                done.append(msg)
                sold = sold or ok
            return sold, "; ".join(done) or "No options"
        return False, "Unknown action"

    # ------------------------------------------------------------------ backtests
    def backtest(self, p, raw, ticker, timeframe=None, bars=500, cash=10000.0):
        """Run a bot's rules over the candles kept for `ticker` (see the module's notes). Nothing real is traded."""
        got = self.backtest_inputs(p, raw, ticker, timeframe, bars, cash)
        return got if "error" in got else run_backtest(**got)

    def backtest_inputs(self, p, raw, ticker, timeframe=None, bars=500, cash=10000.0):
        """What a backtest needs, gathered quickly (the server then runs it without holding up the game)."""
        if not self.is_expert(p):
            return {"error": "Backtests are an Expert tool (see the Shop)"}
        try:
            bot = clean_bot(dict(raw or {}, tickers=[ticker]))
        except RuleError as e:
            return {"error": str(e)}
        s = self.stocks.get(ticker)
        if s is None:
            return {"error": "Unknown stock"}
        tf = timeframe if timeframe in TIMEFRAMES else bot["timeframe"]
        candles = self._history_candles(s, tf)
        bars = int(_num(bars, 500, 50, 5000))
        candles = candles[-bars:]
        if len(candles) < 30:
            return {"error": "Not enough candles of that size yet: try a smaller size"}
        news = [n for n in list(self.news_log) if ticker in (n.get("tickers") or []) or not n.get("tickers")]
        news += [{"t": x["t"], "text": x["text"], "tickers": [ticker]} for x in list(s.log)
                 if not any(abs(n["t"] - x["t"]) < 1e-6 and n["text"] == x["text"] for n in news)]
        news.sort(key=lambda n: n["t"])
        return {"bot": bot, "candles": candles, "tf_secs": TIMEFRAMES[tf], "news": news,
                "cash": float(_num(cash, 10000, 100, 1e7)), "vol": self._realised_vol(s), "rf": self._rf(), "allow_lev": self.is_pro(p),
                "spread": float(self.settings.get("option_spread", 0.06)),
                "vol_premium": float(self.settings.get("option_vol_premium", 0.15)), "ticker": ticker,
                "carry": self.option_carry(s), "skew": self.option_skew(s)}

    def _finished(self, s, tf):
        """The candles of that size whose time is over (the newest may still be under way)."""
        rows = list(s.tf.get(tf, ()))
        if rows and rows[-1][0] + TIMEFRAMES[tf] > self.now:
            rows = rows[:-1]
        return rows

    def _history_candles(self, s, tf):
        rows = self._finished(s, tf)
        if tf == "1m" and self.minute_store is not None:
            older = self.minute_store.last(s.ticker, 4320, before=rows[0][0] if rows else None)
            rows = older + rows
        return [list(c) + [0.0] * (6 - len(c)) for c in rows]


def run_backtest(bot, candles, tf_secs, news, cash=10000.0, vol=0.3, rf=0.015, allow_lev=True, spread=0.06,
                 vol_premium=0.15, ticker="", carry=None, skew=(0.0, 0.0)):
    """The simulation itself (pure: candles in, a report out), so tests and tools can run it without an engine."""
    ser = Series(candles)
    n = len(ser)
    year_bars = 365 * 1800 / tf_secs
    trees = [parse(r["when"]) for r in bot["rules"]]
    state = {"cash": cash, "pos": 0.0, "cost": 0.0, "fee_in": 0.0, "lev": 1.0, "loan": 0.0, "loan0": 0.0, "collat": 0.0}
    opts = []                    # {"kind", "K", "exp_bar", "qty", "cost"}
    trades, curve = [], []
    pending = None               # (rule, the bar it fires on)
    wins = losses = 0
    gross_win = gross_loss = 0.0
    fees = 0.0
    rate_bar = 0.0003 * tf_secs / 1800
    news_i = 0
    feed = []
    scored = {}                         # headline -> its score with these words (scored once)
    first_news = news[0]["t"] if news else None
    peak, max_dd = cash, 0.0
    exposed = 0

    def equity_at(px):
        e = state["cash"]
        if state["pos"] > 0:
            e += state["pos"] * px * (1 - FEE) - state["loan"]
        elif state["pos"] < 0:
            e += state["collat"] + state["cost"] - (-state["pos"]) * px * (1 + FEE)
        for o in opts:
            e += o["qty"] * _bt_quote(o["kind"], px, o["K"], max(0, o["exp_bar"] - i) / year_bars)["bid"]
        return e

    def realised_vol(j):
        seg = ser.c[max(0, j - 20):j + 1]
        r = [math.log(b / a) for a, b in zip(seg, seg[1:]) if a > 0 and b > 0]
        if len(r) < 5:
            return vol
        m = sum(r) / len(r)
        return max(vol, math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(year_bars))

    def _bt_quote(kind, S, K, T):
        return options.quote(S, K, T, sigma_now * (1 + vol_premium), kind, rf if carry is None else carry, 0.0, 0.0,
                             skew[0], skew[1], spread)

    def close_position(px, why, j):
        nonlocal wins, losses, gross_win, gross_loss, fees
        pos = state["pos"]
        if pos > 0:
            proceeds = pos * px * (1 - FEE)
            fee = pos * px * FEE
            state["cash"] += proceeds - state["loan"]
            pnl = proceeds - state["cost"] - state["fee_in"] - (state["loan"] - state["loan0"])
        else:
            value = -pos * px
            fee = value * FEE
            state["cash"] += state["collat"] + state["cost"] - value - fee
            pnl = state["cost"] - value - fee - state["fee_in"]
        fees += fee
        trades.append({"t": ser.t[j], "do": why, "price": px, "pnl": pnl})
        if pnl >= 0:
            wins += 1
            gross_win += pnl
        else:
            losses += 1
            gross_loss -= pnl
        state.update(pos=0.0, cost=0.0, fee_in=0.0, lev=1.0, loan=0.0, loan0=0.0, collat=0.0)
        state["cash"] = max(state["cash"], 0.0)

    sigma_now = vol
    for i in range(n):
        o, h, l, c = ser.o[i], ser.h[i], ser.l[i], ser.c[i]
        sigma_now = realised_vol(i)
        # 1. what was decided at the last close happens at this candle's open
        if pending is not None:
            r = pending
            pending = None
            pos = state["pos"]
            do = r["do"]
            if do in ("buy", "short") and abs(pos) < 1e-12:
                lev = r["lev"] if allow_lev else 1.0
                margin = r["size"] if r["unit"] == "mb" else state["cash"] * r["size"] / 100
                margin = min(margin, state["cash"])
                if margin >= 1:
                    if do == "buy":
                        notional = margin * lev
                        fee = notional * FEE
                        state.update(pos=(notional - fee) / o, cost=(notional - fee), fee_in=fee, lev=lev,
                                     loan=notional - margin, loan0=notional - margin)
                        state["cash"] -= margin
                    else:
                        gross = margin / (1 / lev + FEE)
                        fee = gross * FEE
                        state.update(pos=-gross / o, cost=gross, fee_in=fee, lev=lev, collat=gross / lev)
                        state["cash"] -= gross / lev + fee
                    fees += fee
                    trades.append({"t": ser.t[i], "do": do, "price": o, "lev": lev})
            elif do in ("sell", "cover", "close") and abs(pos) > 1e-12:
                if do == "close" or (do == "sell" and pos > 0) or (do == "cover" and pos < 0):
                    close_position(o, do, i)
            elif do in ("buy_call", "buy_put"):
                kind = "call" if do == "buy_call" else "put"
                if not any(x["kind"] == kind for x in opts):
                    want = o * (1 + (r["strike_pct"] / 100) * (1 if kind == "call" else -1))
                    K = min(options.strikes_for(o), key=lambda k: abs(k - want))
                    exp_bar = i + max(1, int(round(max(1, options.EXPIRY_DAYS[r["expiry"]]) * 1800 / tf_secs)))
                    q = _bt_quote(kind, o, K, (exp_bar - i) / year_bars)
                    mb = r["size"] if r["unit"] == "mb" else state["cash"] * r["size"] / 100
                    n = int(mb / (q["ask"] * options.MULTIPLIER * (1 + FEE)) + 1e-9) if q["ask"] > 0 else 0   # whole contracts
                    spend = n * options.MULTIPLIER * q["ask"]
                    if n >= 1 and spend * (1 + FEE) <= state["cash"] + 1e-9:
                        state["cash"] -= spend * (1 + FEE)
                        fees += spend * FEE
                        opts.append({"kind": kind, "K": K, "exp_bar": exp_bar, "qty": n * options.MULTIPLIER, "cost": spend * (1 + FEE)})
                        trades.append({"t": ser.t[i], "do": do, "price": q["ask"], "strike": K, "contracts": n})
            elif do == "sell_options" and opts:
                for x in list(opts):
                    q = _bt_quote(x["kind"], o, x["K"], max(0, x["exp_bar"] - i) / year_bars)
                    got = x["qty"] * q["bid"] * (1 - FEE)
                    fees += x["qty"] * q["bid"] * FEE
                    state["cash"] += got
                    pnl = got - x["cost"]
                    trades.append({"t": ser.t[i], "do": "sell_option", "price": q["bid"], "pnl": pnl})
                    wins, losses = (wins + 1, losses) if pnl >= 0 else (wins, losses + 1)
                    gross_win, gross_loss = (gross_win + pnl, gross_loss) if pnl >= 0 else (gross_win, gross_loss - pnl)
                    opts.remove(x)
        # 2. interest, stops, targets and the margin, on this candle's range
        pos = state["pos"]
        if abs(pos) > 1e-12:
            exposed += 1
            if pos > 0 and state["loan"] > 0:
                state["loan"] *= 1 + rate_bar
            avg = state["cost"] / abs(pos)
            side = 1 if pos > 0 else -1
            worst, best = (l, h) if side > 0 else (h, l)
            exit_px = None
            if bot["stop_pct"] > 0:
                stop = avg * (1 - side * bot["stop_pct"] / 100)
                if (worst - stop) * side <= 0:
                    exit_px, why = (o if (o - stop) * side <= 0 else stop), "stop"
            if exit_px is None and state["lev"] > 1:
                m = 0.5 / state["lev"]
                if pos > 0:
                    liq = state["loan"] / (pos * (1 - FEE - m))
                else:
                    liq = (state["collat"] + state["cost"]) / (-pos * (1 + FEE + m))
                if (worst - liq) * side <= 0:
                    exit_px, why = (o if (o - liq) * side <= 0 else liq), "margin call"
            if exit_px is None and bot["target_pct"] > 0:
                target = avg * (1 + side * bot["target_pct"] / 100)
                if (best - target) * side >= 0:
                    exit_px, why = (o if (o - target) * side >= 0 else target), "target"
            if exit_px is not None:
                close_position(exit_px, why, i)
        for x in list(opts):                              # options that expire on this candle settle at its close
            if i >= x["exp_bar"]:
                pay = x["qty"] * options.payoff(x["kind"], x["K"], c)
                state["cash"] += pay
                pnl = pay - x["cost"]
                trades.append({"t": ser.t[i], "do": "option expired", "price": c, "pnl": pnl})
                wins, losses = (wins + 1, losses) if pnl >= 0 else (wins, losses + 1)
                gross_win, gross_loss = (gross_win + pnl, gross_loss) if pnl >= 0 else (gross_win, gross_loss - pnl)
                opts.remove(x)
        # 3. the rules at this candle's close (from the 20th candle on, so the indicators have something to work on)
        while news_i < len(news) and news[news_i]["t"] <= ser.t[i] + tf_secs:
            feed.append(news[news_i])
            news_i += 1
        if i >= 20 and i < n - 1:
            pos = state["pos"]
            avg = state["cost"] / abs(pos) if abs(pos) > 1e-12 else 0.0
            mine, market = news_scores(feed[-200:], ticker, bot["words"], bot["halflife"], ser.t[i] + tf_secs, scored)
            kinds_held = [x["kind"] for x in opts]
            acct = {"price": c, "position": pos, "long": float(pos > 1e-12), "short": float(pos < -1e-12),
                    "flat": float(abs(pos) <= 1e-12), "entry": avg,
                    "pnl_pct": ((c / avg - 1) * 100 * (1 if pos > 0 else -1)) if avg > 0 else 0.0,
                    "cash": state["cash"], "equity": equity_at(c), "calls": float(kinds_held.count("call")),
                    "puts": float(kinds_held.count("put")), "news_score": mine, "market_news": market}
            for r, tree in zip(bot["rules"], trees):
                if applicable(r["do"], pos, kinds_held) and _true(evaluate(tree, ser, i, acct)):
                    pending = r
                    break
        eq = equity_at(c)
        peak = max(peak, eq)
        max_dd = max(max_dd, 1 - eq / peak if peak > 0 else 0.0)
        if n <= 300 or i % max(1, n // 300) == 0 or i == n - 1:
            curve.append([ser.t[i], round(eq, 2)])
    end = equity_at(ser.c[-1])
    done = [t for t in trades if "pnl" in t]
    return {"ticker": ticker, "timeframe_secs": tf_secs, "candles": n, "from": ser.t[0], "to": ser.t[-1],
            "start": cash, "end": round(end, 2), "return": end / cash - 1,
            "buy_hold": ser.c[-1] / ser.o[20 if n > 21 else 0] - 1,
            "trades": len(done), "wins": wins, "losses": losses,
            "win_rate": wins / (wins + losses) if wins + losses else None,
            "avg_win": gross_win / wins if wins else None, "avg_loss": -gross_loss / losses if losses else None,
            "profit_factor": gross_win / gross_loss if gross_loss > 0 else None, "max_drawdown": max_dd,
            "fees": round(fees, 2), "exposure": exposed / n, "curve": curve, "log": trades[-200:],
            "news_from": first_news,
            "note": ("Fills at the next candle's open, 0.1% fees, leverage interest, stops and targets on the candles' "
                     "highs and lows. The past is a guide, not a promise: a rule tuned to one stretch of history "
                     "often fails on the next.")}
