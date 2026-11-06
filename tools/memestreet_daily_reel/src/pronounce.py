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


if __name__ == "__main__":
    for s in ["MACD crossed while RSI hit 70%.", "Volume was 2.4x normal.", "Play at memestreet.net/daily or memestreet.net.",
              "Meme Street gives you 1,000 MB.", "FOMO is real. The doji says wait."]:
        out = say_as(s); print(f"{s!r} -> {out!r}")
    assert say_as("MACD") == "mack dee" and "Meem Street dot net slash daily" in say_as("memestreet.net/daily")
    assert "two" not in say_as("2.4x") and "2.4 times" == say_as("2.4x")
