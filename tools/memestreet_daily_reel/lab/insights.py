"""Lab (on the side: the pipeline never reads this): every post on the account with its Instagram insights.

  python3 lab/insights.py            -> lab/data/insights.json
  python3 lab/insights.py --metrics  -> the reel metrics this API version accepts
"""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from post_instagram import http, token, ig_id, HOST, V

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "insights.json")
M = ["views", "reach", "likes", "comments", "shares", "saved", "reposts", "total_interactions",   # (the REELS metrics Meta lists, 2026)
     "ig_reels_avg_watch_time", "ig_reels_video_view_total_time", "reels_skip_rate"]


def insights(mid, tok):
    """Ask for every metric; one the API refuses is dropped and the rest asked again."""
    want = list(M)
    while want:
        try:
            r = http("GET", f"{HOST}/{V}/{mid}/insights", {"metric": ",".join(want), "access_token": tok})
            return {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value")) for d in r.get("data", [])}
        except SystemExit as e:
            bad = [m for m in want if m in str(e)]
            if not bad or len(bad) == len(want): return {"error": str(e)[:300]}
            want = [m for m in want if m not in bad[:1]]
    return {}


def main():
    tok = token(); uid = ig_id(tok)
    if "--metrics" in sys.argv:
        try: http("GET", f"{HOST}/{V}/{uid}/media", {"fields": "id", "limit": 1, "access_token": tok})
        except SystemExit as e: print(e)
        mid = http("GET", f"{HOST}/{V}/{uid}/media", {"fields": "id", "limit": 1, "access_token": tok})["data"][0]["id"]
        try: http("GET", f"{HOST}/{V}/{mid}/insights", {"metric": "nonsense_metric", "access_token": tok})
        except SystemExit as e: print(e)
        return
    me = http("GET", f"{HOST}/{V}/{uid}", {"fields": "username,followers_count,media_count", "access_token": tok})
    posts, url, params = [], f"{HOST}/{V}/{uid}/media", {"fields": "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count", "limit": 50, "access_token": tok}
    while url:
        r = http("GET", url, params); params = None
        posts += r.get("data", []); url = r.get("paging", {}).get("next")
    for p in posts:
        p["insights"] = insights(p["id"], tok); time.sleep(0.3)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"account": me, "pulled": time.strftime("%F %T UTC", time.gmtime()), "posts": posts}, open(OUT, "w"), indent=1)
    print(f"@{me.get('username')}: {me.get('followers_count')} followers, {len(posts)} posts -> {OUT}")


if __name__ == "__main__":
    main()
