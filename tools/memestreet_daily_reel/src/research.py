"""Weekly: which short finance videos are beating their own channel's usual views right now (YouTube Shorts only:
public, no login; Instagram needs a login and TikTok forbids automated collection, so those stay manual research).

For each channel in CHANNELS: its newest 30 Shorts, the median views, and every Short above 4x that median. The top
openings (titles) go to state/evidence.json, which make_spec.py gives the writer of the viral reels as shapes to
follow, never words to copy. Usage: python3 src/research.py
"""
import json, os, re, statistics, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), "state", "evidence.json")
CHANNELS = {   # trading education and stick-figure finance accounts found in the research of 2026-11-04 and -05
    "TradingLab": "UCCbv0qixG-cyokxEY3kELtg", "JeaFx": "UC1Jp-8YnEz3pjPkhCC555gA", "Trading Chart": "UCiGFPi9pZFjYPCoUGzEVy3Q",
    "Tom Crown": "UCiuD3eNaZ95eSXImp_eSIww", "The Moving Average": "UCYFQzaZyTUzY-Tiytyv3HhA", "Brad Goh": "UC2I5dxN4qhaV1dw55u31JWw",
    "Words of Rizdom": "UCHvMu0C0vfg9oBQpihN5X4Q", "Stock Learners": "UCg3LNMpW2sgZc3nthsbsfzQ", "UKspreadbetting": "UCnKPQUoCRb1Vu-qWwWituGQ",
    "Trader Drysdale": "UCxGX_A0NZ-NP06072FcF4sw", "Casual Finance": "UCrNfRFWnLC3tCy1TnyhVQ7g", "Qxir": "UCGHDQtN_vzFYJaq_Fx1eikg",
    "Sticky Academy": "UCrWuA3fVjz1Ej9qe8QhQ0yA", "Stickman Invests": "UC1rRUMyO51O5cLoY1Z0rRkA", "Stick Trader Mind": "UCago6VV8oz_M4vMKrQSIjsw",
    "CMC Aureon": "UCENW0ZwwrW6NG52OJnRxNLg", "DuraMarkets": "@duramarkets", "Data Trader": "UCwIsRM8qBXobpAnzVJ0c4IQ",
}


def shorts(cid):
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "--flat-playlist", "--playlist-end", "30", "-J",
                        (f"https://www.youtube.com/{cid}/shorts" if cid.startswith("@") else f"https://www.youtube.com/channel/{cid}/shorts")], capture_output=True, text=True, timeout=180)
    try:
        return [e for e in (json.loads(r.stdout or "{}").get("entries") or []) if e and e.get("view_count")]
    except ValueError:
        return []


def main():
    rows = []
    for name, cid in CHANNELS.items():
        es = shorts(cid); time.sleep(3)                      # (a few requests a minute: reading, not crawling)
        if len(es) < 8:
            continue
        med = statistics.median(e["view_count"] for e in es)
        for e in es:
            t = re.sub(r"#\S+|[^\x00-\x7F]", "", e.get("title") or "").strip()
            if med and e["view_count"] >= 4 * med and t and len(t.split()) >= 3:
                rows.append([f"{e['view_count'] / med:.0f}x", t[:100], name])
    rows.sort(key=lambda r: -float(r[0][:-1]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"updated": time.strftime("%F", time.gmtime()), "examples": rows[:12]}, open(OUT, "w"))
    print(f"{len(rows)} outliers; top: " + " | ".join(f"{a} {b}" for a, b, _ in rows[:5]))


if __name__ == "__main__":
    main()
