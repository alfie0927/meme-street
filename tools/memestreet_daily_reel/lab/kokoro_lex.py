"""Lab: teach Kokoro the words it says wrongly. Every word our reels use (scripts in work/*/spec.json, the game's
company names, the lexicon's own terms) is said by Kokoro in a carrier sentence and heard back by Whisper (small.en,
the critic's ear); a word heard as something else is a suspect. For each suspect Claude proposes respellings, Kokoro
says each and the first one Whisper hears as the real word is kept. Nothing changes until `apply`.

  python3 lab/kokoro_lex.py test [N]     -> lab/data/lex_test.json (suspects; N caps the words, for a quick run)
  python3 lab/kokoro_lex.py fix          -> lab/data/lex_fix.json (a respelling per suspect, or none that worked)
  python3 lab/kokoro_lex.py apply        adds the working respellings to src/pronounce.json
  python3 lab/kokoro_lex.py demo         self-check
Run on the reel server under the reel lock (Kokoro and Whisper are there):  flock queue/.auto.lock python3 lab/kokoro_lex.py test
"""
import glob, json, os, re, subprocess, sys

LAB = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(LAB); DATA = os.path.join(LAB, "data")
sys.path.insert(0, os.path.join(ROOT, "src"))
CARRIER = "The next word is {}."
STOP = set("the and that this with from have will your what when then than they them their there were been into just "
           "more most some only also over very about which would could should because while where after before every".split())
key = lambda w: re.sub(r"[^a-z]", "", w.lower())


def vocabulary(limit=None):
    """Every distinct word our reels say, longest-lived first: script words of 4+ letters, company names, lexicon terms."""
    from pronounce import LEX
    seen = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "work", "*", "spec.json"))):
        for s in json.load(open(f, encoding="utf-8")).get("scenes", []):
            for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", s.get("vo", "")):
                w = w.strip("'-")
                if len(w) >= 4 and w.lower() not in STOP and not w.lower().endswith("'s"): seen.setdefault(w.lower(), w)
    pack = os.environ.get("CONTENT_PACK", "/opt/memestreet/content/pack_fiction.json")
    if os.path.exists(pack):
        for c in json.load(open(pack, encoding="utf-8")).get("companies", []):
            for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", c.get("name", "")):
                if len(w) >= 3: seen.setdefault(w.lower(), w)
    for k in LEX:                                         # (the lexicon's terms: check its respellings still land)
        if re.fullmatch(r"[A-Za-z][A-Za-z ]+", k): seen.setdefault(k.lower(), k)
    ws = sorted(seen.values(), key=str.lower)
    return ws[:limit] if limit else ws


class Ear:
    """Kokoro's mouth and Whisper's ear, loaded once."""
    def __init__(self):
        import numpy as np
        from kokoro_onnx import Kokoro
        from faster_whisper import WhisperModel
        from voice import MODEL
        self.np = np
        self.K = Kokoro(os.path.join(MODEL, "kokoro-v1.0.onnx"), os.path.join(MODEL, "voices-v1.0.bin"))
        self.A = WhisperModel(os.environ.get("CRITIC_ASR", "small.en"), device="cpu", compute_type="int8")

    def hear(self, spoken):
        """What Whisper hears when Kokoro says CARRIER with `spoken` in it (the word after the carrier's words)."""
        np = self.np
        a, sr = self.K.create(CARRIER.format(spoken), voice="af_heart", speed=1.0, lang="en-us")
        a16 = np.interp(np.arange(0, len(a), sr / 16000), np.arange(len(a)), a).astype(np.float32)
        segs, _ = self.A.transcribe(a16, language="en", beam_size=5)
        text = " ".join(s.text for s in segs).strip()
        return re.sub(r"(?i)^\W*the next word is\W*", "", text).strip(" .,")


def ok(word, heard):
    """Heard as the word: same letters, ignoring spaces, case and punctuation ('Stone Sage' is StoneSage)."""
    return key(heard) == key(word) or key(heard).rstrip("s") == key(word).rstrip("s")


def test(limit=None):
    from pronounce import say_as
    ear = Ear(); out = []
    ws = vocabulary(limit)
    for n, w in enumerate(ws):
        h = ear.hear(say_as(w))
        if not ok(w, h): out.append({"word": w, "said_as": say_as(w), "heard": h})
        if n % 50 == 0: print(f"{n}/{len(ws)} words, {len(out)} suspects", flush=True)
    os.makedirs(DATA, exist_ok=True)
    json.dump({"words": len(ws), "suspects": out}, open(os.path.join(DATA, "lex_test.json"), "w"), indent=1)
    print(f"{len(ws)} words, {len(out)} heard wrongly -> lab/data/lex_test.json")


def respellings(words):
    """Claude's phonetic respellings, three per word, plain letters (how a reader would say it aloud)."""
    ask = ("A text-to-speech voice (Kokoro, American English) mispronounces these words. For each, give 3 respellings in "
           "plain letters that the voice would read correctly (e.g. 'Meme' -> 'Meem', 'doji' -> 'doh jee', 'GameStop' "
           "-> 'Game Stop'). Keep words split only where a listener hears a break. Reply with JSON only: "
           '{"word": ["respelling", "respelling", "respelling"], ...}\n\n' + "\n".join(words))
    r = subprocess.run(["claude", "-p", "--output-format", "text", "--model", "sonnet", "--disallowedTools",
                        "Bash,Edit,Write,Read,WebFetch,WebSearch,Glob,Grep,Task,NotebookEdit"],
                       input=ask, capture_output=True, text=True, encoding="utf-8", timeout=600, cwd=LAB,
                       env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})
    return json.loads(re.search(r"\{.*\}", r.stdout, re.S).group(0))


HOMOPHONES = {("herd", "heard"), ("meet", "meat"), ("sell", "cell"), ("sells", "cells"), ("know", "no"), ("knew", "new"),
              ("piece", "peace"), ("read", "red"), ("four", "for"), ("practise", "practice"), ("you're", "your"), ("hire", "higher"),
              ("queuing", "cueing")}   # (said right; alone, Whisper can only guess the spelling)


def real(s):
    """A suspect worth fixing: not a number Whisper wrote in digits, not a word with a sound-alike, not a lexicon term
    that is meant to change (BOS -> break of structure)."""
    w, h = s["word"].lower(), s["heard"].lower().strip(" .,")
    from pronounce import digits
    if re.fullmatch(r"[\d.%-]+( candle)?", h) or "".join(c for c, _, _ in digits(s["word"].split())).lower().replace("-", " ") == h: return False
    if (w, h) in HOMOPHONES: return False
    return key(s["said_as"]) != key(h)


def fix():
    """For each suspect: a respelling Kokoro says so Whisper hears the real word. A suspect heard wrongly only because
    Whisper does not know the word (an invented name) passes once a respelling lands; one with no respelling that works
    is reported, not changed."""
    T = [s for s in json.load(open(os.path.join(DATA, "lex_test.json"), encoding="utf-8"))["suspects"] if real(s)]
    ear = Ear(); R = respellings([s["word"] for s in T]); out = []
    for s in T:
        tried = []
        for c in R.get(s["word"], [])[:3]:
            h = ear.hear(c); tried.append({"as": c, "heard": h})
            if ok(s["word"], h): out.append({**s, "fix": c, "tried": tried}); break
        else:
            out.append({**s, "fix": None, "tried": tried})
    json.dump(out, open(os.path.join(DATA, "lex_fix.json"), "w"), indent=1)
    print(f"{sum(1 for x in out if x['fix'])} of {len(out)} suspects fixed -> lab/data/lex_fix.json")


def apply():
    p = os.path.join(ROOT, "src", "pronounce.json"); L = json.load(open(p, encoding="utf-8"))
    F = [x for x in json.load(open(os.path.join(DATA, "lex_fix.json"), encoding="utf-8")) if x["fix"]]
    for x in F: L.setdefault(x["word"], x["fix"])           # (never overwrite a respelling someone chose)
    json.dump(L, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{len(F)} respellings added to src/pronounce.json")


def demo():
    assert ok("StoneSage", "Stone Sage.") and ok("candles", "candle") and not ok("Ember", "number")
    assert key("Meem-Street") == "meemstreet"
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    {"test": lambda: test(int(a[1]) if len(a) > 1 else None), "fix": fix, "apply": apply}.get(a[0] if a else "demo", demo)()
