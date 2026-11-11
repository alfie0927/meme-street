"""Tell Bing, Yandex and the other IndexNow search engines which pages to fetch (docs/REACH_PLAN.md P4, roadmap B12).

  python tools/indexnow.py               every address in the live sitemap (once, after the key route went live)
  python tools/indexnow.py before.xml    only the addresses that are not in that older copy of the sitemap
                                         (the SEO deploy, .github/workflows/seo-ship.yml: what the day's run added)
  python tools/indexnow.py demo          the self-check, no network

The key is INDEXNOW_KEY in game/pages.py, which the site serves at /<key>.txt: that is how the search engines know the
list comes from us. It is not a secret. Free, no account.
"""
import json
import os
import re
import sys
import urllib.request

SITE = "https://memestreet.net"
PAGES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game", "pages.py")


def locs(xml):
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def new(now, before):
    """The addresses of our own site in `now` that `before` does not have, in the sitemap's order."""
    old = set(locs(before))
    return [u for u in locs(now) if u.startswith(SITE + "/") and u not in old]


def main(before=None):
    key = re.search(r'INDEXNOW_KEY = "([0-9a-f]{32})"', open(PAGES, encoding="utf-8").read()).group(1)
    if urllib.request.urlopen(f"{SITE}/{key}.txt", timeout=20).read().decode().strip() != key:
        raise SystemExit("the site does not serve the key yet: nothing sent")
    now = urllib.request.urlopen(SITE + "/sitemap.xml", timeout=20).read().decode()
    urls = new(now, open(before, encoding="utf-8").read() if before else "")
    if not urls:
        return print("no new addresses: nothing sent")
    body = {"host": SITE.split("//")[1], "key": key, "keyLocation": f"{SITE}/{key}.txt", "urlList": urls}
    req = urllib.request.Request("https://api.indexnow.org/indexnow", json.dumps(body).encode(),
                                 {"Content-Type": "application/json; charset=utf-8"})
    print(len(urls), "addresses sent, HTTP", urllib.request.urlopen(req, timeout=20).status)


def demo():
    a = "<urlset><url><loc>%s/a</loc></url><url><loc>%s/b</loc></url><url><loc>https://other.test/c</loc></url></urlset>" % (SITE, SITE)
    assert new(a, "") == [SITE + "/a", SITE + "/b"]                       # everything of ours, nothing of another site's
    assert new(a, "<loc>%s/a</loc>" % SITE) == [SITE + "/b"]              # only what is new
    assert new(a, a) == []
    assert re.search(r'INDEXNOW_KEY = "([0-9a-f]{32})"', open(PAGES, encoding="utf-8").read())
    print("ok")


if __name__ == "__main__":
    demo() if sys.argv[1:] == ["demo"] else main(*sys.argv[1:2])
