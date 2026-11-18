"""How the Meme Street voice says things, the same in every reel (narrate.py; the Daily recap goes through narrate.py
too). A text line becomes the line the voice reads: words from pronounce.json ("MACD" -> "mack dee"), multipliers
("2.4x" -> "two point four times"), percents, and ticker symbols read as their company names.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
LEX = {k: v for k, v in json.load(open(os.path.join(HERE, "pronounce.json"), encoding="utf-8")).items() if not k.startswith("_")}
# longest first, so "memestreet.net/daily" wins over "memestreet.net"
_RULES = [(re.compile(r"(?<![\w.])" + re.escape(k) + r"(?![\w])", re.I), v) for k, v in sorted(LEX.items(), key=lambda kv: -len(kv[0]))]
_TICKERS = {}


def tickers(names):
    """Ticker symbols the voice should read as company names ({"CLSD": "CloudSeed Co"}), from the content pack."""
    _TICKERS.update(names)


def say_as(text):
    for rx, v in _RULES:
        text = rx.sub(v, text)
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*[x×](?=\W|$)", lambda m: m.group(1) + " times", text)        # 2.4x -> 2.4 times
    text = re.sub(r"(\d)\s*%", r"\1 percent", text)
    text = re.sub(r"\b([A-D]) or ([A-D])\b", r"\1, or \2", text)         # ("A or B" ran together, heard as "ORB")
    for t, name in _TICKERS.items():
        text = re.sub(r"\b" + re.escape(t) + r"\b", name, text)
    return text


_U = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                 "fifteen sixteen seventeen eighteen nineteen".split())}
_T = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
_S = {"hundred": 100, "thousand": 1000, "million": 1000000}
_P = ".,;:!?\"')"


def _num(ws):
    """Spoken number words -> digits. Price talk joins its parts: 'two oh three' 203, 'two thirty' 230; a cardinal reads
    as one: 'a hundred and four' 104."""
    out, cur, big, last = [], None, 0, None              # cur: the part under a thousand of the chunk being read
    def close():
        nonlocal cur, big
        if cur is not None or big: out.append(str(big + (cur or 0)))
        cur, big = None, 0
    for w in ws:
        if w == "and": continue
        if w == "oh": close(); out.append("0"); last = "oh"; continue
        if w in _S:
            v = _S[w]
            if v == 100: cur = (cur or 1) * 100
            else: big += (cur or 1) * v; cur = 0
            last = "s"; continue
        u = w in _U; t = w in _T; v = _U[w] if u else _T[w]
        joins = cur is not None and ((last == "t" and u and v < 10) or (last == "s" and (cur % 100 == 0)))
        if not joins and not (cur is None and big):
            close()
        cur = (cur or 0) + v; last = "t" if t else "u"
    close()
    return "".join(out)


def digits(words):
    """The caption form of a spoken line: number words become digits ('fifty-one.' -> '51.', 'twelve percent' -> '12%',
    'twenty-candle' -> '20-candle'). Returns (token, first word, last word) so each token takes the time it is said.
    A lone 'one' stays a word ('one candle'), unless it is a name ('level one')."""
    core = lambda w: w.lower().strip(_P)
    numw = lambda w: all(p in _U or p in _T or p in _S for p in core(w).split("-")) and core(w) != ""
    out, i, n = [], 0, len(words)
    while i < n:
        w = words[i]; c = core(w); parts = c.split("-")
        start = numw(w) or (c == "a" and i + 1 < n and core(words[i + 1]) in _S) or (re.fullmatch(r"\d+(\.\d+)?", c) is not None)
        if not start and len(parts) > 1 and parts[0] in _U | _T:                        # 'twenty-candle'
            k = max(j for j in range(len(parts)) if all(p in _U or p in _T for p in parts[:j + 1]))
            out.append((w[:len(w) - len(w.lstrip(_P))] + _num(parts[:k + 1]) + "-" + "-".join(w.lstrip(_P).split("-")[k + 1:]), i, i)); i += 1; continue
        if not start:
            out.append((w, i, i)); i += 1; continue
        j, ws, tail = i, [], ""
        while j < n:
            c = core(words[j])
            if j > i and words[j - 1][-1:] in _P: break                                # punctuation ends a number
            if numw(words[j]): ws += c.split("-")
            elif re.fullmatch(r"\d+(\.\d+)?", c) and j == i: ws.append(c)
            elif c == "a" and j == i: pass
            elif c == "and" and ws and ws[-1] in _S and j + 1 < n and numw(words[j + 1]): pass
            elif c == "oh" and ws and j + 1 < n and numw(words[j + 1]): ws.append("oh")
            elif c == "point" and ws and j + 1 < n and numw(words[j + 1]) and "." not in tail:
                d = []; j += 1
                while j < n and core(words[j]) in _U and _U[core(words[j])] < 10 and (len(d) == 0 or words[j - 1][-1:] not in _P):
                    d.append(str(_U[core(words[j])])); j += 1
                tail = "." + "".join(d); j -= 1
            else: break
            j += 1
        if ws == ["one"] and (i == 0 or core(words[i - 1]) not in ("level", "number", "chart", "day", "week")):
            out.append((w, i, i)); i += 1; continue
        v = ws[0] if re.fullmatch(r"\d+(\.\d+)?", ws[0]) else _num(ws)
        v += tail
        if j < n and core(words[j]) == "percent" and words[j - 1][-1:] not in _P: v += "%"; j += 1
        last = words[j - 1]; v += last[len(last.rstrip(_P)):]
        out.append((v, i, j - 1)); i = j
    joined = []                                          # a spelt ticker reads as one word: 'E M B R' -> 'EMBR'
    for t in out:
        if joined and re.fullmatch(r"[A-Z]+", joined[-1][0]) and joined[-1][2] - joined[-1][1] + 1 == len(joined[-1][0]) \
                and re.fullmatch(r"[A-Z][^\w\s]*", t[0]):
            joined[-1] = (joined[-1][0] + t[0], joined[-1][1], t[2])
        else:
            joined.append(t)
    return joined


def demo():
    cap = lambda s: " ".join(t for t, _, _ in digits(s.split()))
    for said, shown in [("about two oh three, then", "about 203, then"), ("a hundred and four.", "104."),
                        ("near fifty-one.", "near 51."), ("sold at two thirty", "sold at 230"),
                        ("That's your twelve percent.", "That's your 12%."), ("That's your 12 percent.", "That's your 12%."),
                        ("two point four times the volume", "2.4 times the volume"), ("one idea, one candle", "one idea, one candle"),
                        ("at level one.", "at level 1."), ("the twenty-candle high", "the 20-candle high"),
                        ("three thirty-four, and", "334, and"), ("ninety-one now", "91 now"), ("a clue", "a clue"),
                        ("one thousand two hundred shares", "1200 shares"), ("twenty three", "23"), ("seventy-four to fifty-one", "74 to 51")]:
        assert cap(said) == shown, (said, cap(said), shown)
    assert digits("near sixty-nine, under".split())[1] == ("69,", 1, 1)
    assert cap("Trade E M B R free.") == "Trade EMBR free." and cap("A, or B") == "A, or B" and cap("RSI stays") == "RSI stays"


if __name__ == "__main__":
    for s in ["MACD crossed while RSI hit 70%.", "Volume was 2.4x normal.", "Play at memestreet.net/daily or memestreet.net.",
              "Meme Street gives you 1,000 MB.", "FOMO is real. The doji says wait."]:
        out = say_as(s); print(f"{s!r} -> {out!r}")
    assert say_as("MACD") == "mack dee" and "Meem Street dot net slash daily" in say_as("memestreet.net/daily")
    assert "two" not in say_as("2.4x") and "2.4 times" == say_as("2.4x")
    demo(); print("ok")
