"""Numbers as a person says them, for the voice (the captions keep the digits). The owner, 2026-11-27: "the audio is bad, like
say 'one thousand and fifty two' etc for numbers": the voice was handed "$1,052" and read it its own way.

  say("$1,052")          -> "one thousand and fifty-two dollars"
  say("$2.51")           -> "two dollars fifty-one"          say("55 cents") -> "fifty-five cents"
  say("$9.21 billion")   -> "nine point two one billion dollars"
  say("78%")             -> "seventy-eight percent"          say("1,170 points") -> "one thousand, one hundred and seventy points"
  a year (1900 to 2099 standing alone) is left for the voice, which says years right.
"""
import re

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def under1000(n):
    h, r = divmod(n, 100); out = []
    if h: out.append(ONES[h] + " hundred")
    if r:
        w = ONES[r] if r < 20 else TENS[r // 10] + ("-" + ONES[r % 10] if r % 10 else "")
        out.append(("and " if h else "") + w)
    return " ".join(out)


def num(n):
    """An integer in British English: 1,052 -> 'one thousand and fifty-two'."""
    if n == 0: return "zero"
    parts, scale = [], ["", " thousand", " million", " billion", " trillion"]; k = 0; groups = []
    while n: n, g = divmod(n, 1000); groups.append(g)
    for k in range(len(groups) - 1, -1, -1):
        g = groups[k]
        if not g: continue
        w = under1000(g)
        if k == 0 and len(groups) > 1 and g < 100: w = "and " + w          # (one thousand AND fifty-two)
        parts.append(w + scale[k])
    return ", ".join(p for p in parts[:-1]) + (", " if len(parts) > 1 and not parts[-1].startswith("and") else " " if len(parts) > 1 else "") + parts[-1] if len(parts) > 1 else parts[0]


def dec(s):
    """'9.21' -> 'nine point two one'."""
    a, b = s.split(".") if "." in s else (s, "")
    return num(int(a.replace(",", ""))) + (" point " + " ".join(ONES[int(c)] for c in b) if b else "")


def say(text):
    t = text
    t = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)\s+(thousand|million|billion|trillion)\b", lambda m: f"{dec(m[1])} {m[2]} dollars", t)
    t = re.sub(r"\$(\d[\d,]*)\.(\d\d)\b", lambda m: f"{num(int(m[1].replace(',', '')))} dollar{'s' if m[1] != '1' else ''} {num(int(m[2]))}" if m[2] != "00" else f"{num(int(m[1].replace(',', '')))} dollars", t)
    t = re.sub(r"\$(\d[\d,]*)\b", lambda m: f"{num(int(m[1].replace(',', '')))} dollar{'s' if m[1] != '1' else ''}", t)
    t = re.sub(r"(\d[\d,]*(?:\.\d+)?)%", lambda m: f"{dec(m[1])} percent", t)
    t = re.sub(r"\b(\d+\.\d+)\b", lambda m: dec(m[1]), t)
    t = re.sub(r"\b(\d{1,3}(?:,\d{3})+|\d+)\b", lambda m: m[1] if re.fullmatch(r"(19|20)\d\d", m[1]) else num(int(m[1].replace(",", ""))), t)
    return t


def demo():
    assert num(1052) == "one thousand and fifty-two", num(1052)
    assert num(1170) == "one thousand, one hundred and seventy", num(1170)
    assert num(100000) == "one hundred thousand" and num(21912) == "twenty-one thousand, nine hundred and twelve", num(21912)
    assert num(1029221) == "one million, twenty-nine thousand, two hundred and twenty-one", num(1029221)
    assert say("$1,052") == "one thousand and fifty-two dollars", say("$1,052")
    assert say("It hit $3.35.") == "It hit three dollars thirty-five.", say("It hit $3.35.")
    assert say("$9.21 billion") == "nine point two one billion dollars" and say("55 cents") == "fifty-five cents"
    assert say("lost 78% in 2018") == "lost seventy-eight percent in 2018", say("lost 78% in 2018")
    assert say("$100,000") == "one hundred thousand dollars"
    print("ok")


if __name__ == "__main__":
    demo()
