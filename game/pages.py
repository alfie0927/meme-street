"""The pages of the site (the game, the admin page, the logo). Served by the game server, and by every gateway in a
multi-process set-up, so both look the same."""
import html
import json
import os
import re
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote

from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

import lessonpages
import vspages
import paths
from netutil import TICKER_RENAMES
from social import clean_chat

BRAND_FILES = {"memestreet_logo_peaks.png", "memestreet_header_peaks.png", "favicon.ico", "icon-48.png", "icon-192.png",
               "icon-512.png", "apple-touch-icon.png"}   # (the small icons: browser tabs, phones and search results)
DAILY_TEXT = ("A free daily stock market game: one new chart a day, the same for everyone. Two minutes to buy, sell and "
              "short as the candles print, then see how your return ranks against every other player. Like Wordle, "
              "for trading.")
DAILY_BODY = ("<main style=\"max-width:620px;margin:0 auto;padding:24px 16px;font:16px/1.55 system-ui,sans-serif\">"
              "<h1>The Daily Chart: a daily stock market game</h1>"
              "<p>Every day there is one new chart, and everyone gets the same one. You start with 1,000 MB of practice "
              "money and have two minutes: the candles print one a second, and you buy, sell or short as they come. "
              "When the time is up you see your return, your place, and how every other player did.</p>"
              "<p>It is like Wordle, but for reading charts: one go a day, a streak to keep, and a result to share. The "
              "chart comes from a made-up stock, so nobody can look it up, and the next one starts at midnight UTC.</p>"
              "<p>Turn on JavaScript to play. New to charts? Start with the <a href=\"/lessons\">free lessons</a> or read "
              "<a href=\"/about\">about Meme Street</a>.</p></main>")
HOME_TEXT = ("Meme Street is a made-up stock market that runs around the clock. Learn to trade with 1,000 MB of practice "
             "money (memebucks, no cash value) and no real cash at risk, with free lessons and a new chart game every day.")
HOME_BODY = ("<main><h1>Meme Street: a stock market game with play money</h1>"
             "<p>Meme Street is a made-up stock market that never closes, with 180+ companies, indices and funds, news that "
             "moves prices and a daily leaderboard. Everyone starts with 1,000 MB (memebucks), practice money with no cash "
             "value, so you can learn to trade without risking real cash.</p>"
             "<p>Turn on JavaScript to watch the market live and trade. New to trading? Start with the "
             "<a href=\"/lessons\">free lessons</a>, try the <a href=\"/daily\">Daily Chart</a>, or read "
             "<a href=\"/about\">how Meme Street works</a>.</p></main>")
SCRIPTS = {"chart.js", "bots.js", "daily.js", "learn.js"}   # the page's own scripts in web/ (the chart, TA-F2; the Bots page; the Daily Chart; the Learn page)
VS = re.compile(r"([\w. -]{0,16})~(-?[0-9]{1,7})~([0-9]{1,6})")   # a challenge link's name~return~number, as web/daily.js reads it
INDEXNOW_KEY = "9174e4823a4a87abdea3109b5df145c4"   # (not a secret: Bing reads it back from /<key>.txt to see that tools/indexnow.py speaks for this site)
MANIFEST = json.dumps({   # (an installable web app: roadmap U1, REACH_PLAN P3; ?ref=app shows an installed copy's visits in the visit log)
    "name": "Meme Street", "short_name": "Meme Street", "description": HOME_TEXT, "start_url": "/?ref=app", "scope": "/",
    "display": "standalone", "background_color": "#08090b", "theme_color": "#08090b", "categories": ["games", "education", "finance"],
    "icons": [{"src": f"/brand/icon-{n}.png", "sizes": f"{n}x{n}", "type": "image/png"} for n in (192, 512)]})


def vs_title(vs):
    """The preview title of a challenge link (`/daily?vs=name~return~number`, written by web/daily.js), or "" for a
    link without one, a malformed one, or a name the chat would mask (a link, a bad word). The name is letters, digits
    and `_. -` only, so it cannot leave the tag it is put in."""
    m = VS.fullmatch(vs)
    name = m[1].strip() if m else ""
    if not m or clean_chat(name) != name:
        return ""
    r = Decimal(int(m[2]) / 10000 * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)   # (as pc() in index.html: 0.25 is +0.3%)
    ret = ("+" if r > 0 else "-" if r < 0 else "") + f"{abs(r)}%"
    n = int(m[3])
    return f"{name} got {ret} on Daily Chart #{n}. Can you beat it?" if name else f"Can you beat {ret} on Daily Chart #{n}?"


def add_pages(app):
    """The pages are in web/ and the logo in brand/ (paths.py)."""
    web = paths.WEB

    def page():
        return FileResponse(os.path.join(web, "index.html"), headers={"Cache-Control": "no-store"})

    cache = {}

    def page_as(path, title, description, extra="", body=""):
        """index.html with its own title, description, preview and address for a page search engines should list on
        its own (the Daily Chart): the same file, so nothing else changes. `body` is plain text for visitors and crawlers
        without JavaScript (put in a noscript block, so players never see it twice)."""
        f = os.path.join(web, "index.html")
        key = (path, os.path.getmtime(f))
        if key not in cache:
            s = open(f, encoding="utf-8").read()
            t, d = html.escape(title), html.escape(description)
            head = (f'<title>{t}</title><meta name="description" content="{d}"><link rel="canonical" href="{site}{path}">'
                    f'<meta property="og:title" content="{t}"><meta property="og:description" content="{d}">'
                    f'<meta property="og:url" content="{site}{path}"><meta name="twitter:card" content="summary_large_image">' + extra)
            s = s.replace("<title>Meme Street</title>", head, 1)
            for tag in ('<meta name="description"', '<meta property="og:title"', '<meta property="og:description"'):
                i = s.index(tag)                               # the home page's own copies go
                s = s[:i] + s[s.index(">", i) + 1:]
            if body:
                s = s.replace('<body class="page-market">', '<body class="page-market"><noscript>' + body + "</noscript>", 1)
            for k in [k for k in cache if k[1] != key[1]]:   # (a page of an older index.html)
                del cache[k]
            cache[key] = s
        return HTMLResponse(cache[key], headers={"Cache-Control": "no-store"})

    def daily_page(vs=""):
        """The Daily Chart, for searches such as "daily stock market game" (2026-10-31). A challenge link (`vs`) gets
        its own preview title (2026-11-11), swapped into the cached page's text: the cache still holds one page."""
        data = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Daily Chart by Meme Street",
                "url": site + "/daily", "applicationCategory": "GameApplication", "operatingSystem": "Any",
                "description": DAILY_TEXT, "image": site + "/brand/memestreet_logo_peaks.png",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
        title = "Daily Chart: the daily stock market game | Meme Street"
        r = page_as("/daily", title, DAILY_TEXT,
                    '<script type="application/ld+json">' + json.dumps(data) + "</script>", DAILY_BODY)
        t = vs_title(vs)
        if not t:
            return r
        tag, url = '<meta property="og:title" content="%s">', '<meta property="og:url" content="%s">'
        s = r.body.decode("utf-8").replace(tag % html.escape(title), tag % html.escape(t), 1)
        # (Facebook and Instagram take a preview from the page og:url names, so a challenge link names itself there;
        # the canonical link, which search engines read, stays /daily)
        s = s.replace(url % (site + "/daily"), url % html.escape(site + "/daily?vs=" + quote(vs, safe="")), 1)
        return HTMLResponse(s, headers={"Cache-Control": "no-store"})

    @app.get("/brand/{name}")
    async def brand_file(name: str):
        """The logo and the site icons (only the named brand images are served)."""
        if name not in BRAND_FILES:
            return JSONResponse({"error": "not found"}, status_code=404)
        path = os.path.join(paths.BRAND, name)
        if os.path.exists(path):
            return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})
        return JSONResponse({"error": "not found"}, status_code=404)

    @app.get("/favicon.ico")
    async def favicon():
        """Where browsers and search engines look for a site's icon first."""
        return await brand_file("favicon.ico")

    site = os.environ.get("SITE_URL", "https://memestreet.net").rstrip("/")
    lessons = lessonpages.Lessons(site)
    # (pages with their own content; not /learn or /leaders, which are the game's page and empty without JavaScript,
    # nor /terms and /privacy, which are noindex)
    public = ["/daily", "/", "/about", "/bots/guide", lessonpages.CALC_PATH, lessonpages.RR_PATH, lessonpages.SL_PATH] + lessons.paths() + vspages.paths()

    @app.get("/robots.txt")
    async def robots():
        """For search engines: everything but the admin page and the API, and where the sitemap is."""
        return PlainTextResponse(f"User-agent: *\nDisallow: /admin\nDisallow: /api/\nSitemap: {site}/sitemap.xml\n")

    @app.get("/manifest.json")
    async def manifest():
        """Lets a phone, a desktop browser or the Microsoft Store install the site as an app."""
        return Response(MANIFEST, media_type="application/manifest+json", headers={"Cache-Control": "public, max-age=86400"})

    llms = "\n".join(
        [f"# Meme Street\n\n> {HOME_TEXT}\n\nThe market, its companies and its news are made up. Memebucks (MB) are practice money: "
         "they have no cash value and are never paid out. Nothing on the site is investment advice.\n\n## Play\n",
         f"- [The Daily Chart]({site}/daily): {DAILY_TEXT}",
         f"- [The live market]({site}/): 180+ made-up companies, indices and funds, news that moves prices, and return boards.",
         f"- [About Meme Street]({site}/about): how the market, the practice money and the boards work.",
         f"- [Trading bots: the guide]({site}/bots/guide): setting up a rule-based bot, the rules it follows, and backtests.",
         "\n## Tools\n", f"- [Position size calculator]({site}{lessonpages.CALC_PATH}): {lessonpages.CALC_DESC}",
         f"- [Risk reward ratio calculator]({site}{lessonpages.RR_PATH}): {lessonpages.RR_DESC}",
         f"\n## Lessons\n\n{lessons.hub_text} [All lessons]({site}/lessons)\n"]
        + [f"- [{x['title']}]({site}/lessons/{x['id']}): {x['summary']}" for x in lessons.lessons]
        + [f"\n## Compare\n\n{vspages.HUB_DESC} [All comparisons]({site}/vs)\n"]
        + [f"- [{v['h1']}]({site}/vs/{s}): {v['desc']}" for s, v in vspages.VS.items()]) + "\n"

    @app.get("/llms.txt")
    async def llms_txt():
        """The site in plain words for AI search engines (llmstxt.org; REACH_PLAN P4)."""
        return PlainTextResponse(llms, headers={"Cache-Control": "public, max-age=3600"})

    @app.get(f"/{INDEXNOW_KEY}.txt")
    async def indexnow_key():
        """IndexNow (Bing, Yandex and others) reads the key back here before it believes a list of our addresses."""
        return PlainTextResponse(INDEXNOW_KEY)

    @app.get("/sitemap.xml")
    async def sitemap():
        """The public pages, so search engines find them all."""
        urls = "".join(f"<url><loc>{site}{u}</loc></url>" for u in public)
        return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                        + urls + "</urlset>", media_type="application/xml")

    @app.get("/js/{name}")
    async def script_file(name: str):
        """The page's scripts. Checked against the browser's copy on every load (no-cache), so a new version is picked
        up at once and an unchanged one costs a 304."""
        if name not in SCRIPTS:
            return JSONResponse({"error": "not found"}, status_code=404)
        return FileResponse(os.path.join(web, name), media_type="text/javascript", headers={"Cache-Control": "no-cache"})

    @app.get("/admin")
    async def admin_page():
        """The page is public but shows nothing until the admin key is entered; the data endpoints check the key."""
        return FileResponse(os.path.join(web, "admin.html"), headers={"Cache-Control": "no-store"})

    @app.get("/")
    async def index():
        return page_as("/", "Meme Street: a stock market game with play money", HOME_TEXT, "", HOME_BODY)

    @app.get("/daily")
    async def daily(vs: str = ""):
        return daily_page(vs)

    @app.get("/embed/daily")
    async def embed_daily():
        """The Daily Chart inside another site's frame (itch.io, a blog, a class page; REACH_PLAN P2). The same page as
        /daily, so search engines still see one address (the canonical link). The page's script reads the address and
        opens every link in a new tab; deploy/Caddyfile lets this one address be framed, and only by the hosts it names."""
        return daily_page()

    @app.get("/play")
    async def play():
        """The short address the reels say: today's Daily Chart, tagged as coming from a reel (growth plan, 2026-11-10).
        Not in the sitemap: it only forwards."""
        return RedirectResponse("/daily?ref=reel", status_code=307)

    @app.get("/lessons")
    async def lessons_hub():
        """Every Learn lesson, listed by track (lessonpages.py)."""
        return HTMLResponse(lessons.hub(), headers={"Cache-Control": "public, max-age=300"})

    @app.get(lessonpages.CALC_PATH)
    async def position_size_calculator():
        """A free position size calculator (lessonpages.py), for searches such as "position size calculator"."""
        return HTMLResponse(lessons.calculator(), headers={"Cache-Control": "public, max-age=300"})

    @app.get(lessonpages.RR_PATH)
    async def risk_reward_calculator():
        """A free risk reward ratio calculator (lessonpages.py), for searches such as "risk reward ratio calculator"."""
        return HTMLResponse(lessons.risk_reward(), headers={"Cache-Control": "public, max-age=300"})

    @app.get(lessonpages.SL_PATH)
    async def stop_loss_calculator():
        """A free stop loss calculator (lessonpages.py), for searches such as "stop loss calculator"."""
        return HTMLResponse(lessons.stop_loss(), headers={"Cache-Control": "public, max-age=300"})

    @app.get("/vs")
    async def compare_hub():
        """Meme Street beside the simulators people search for, and the Daily beside Wordle (vspages.py)."""
        return HTMLResponse(vspages.hub(site), headers={"Cache-Control": "public, max-age=300"})

    @app.get("/vs/{slug}")
    async def compare_page(slug: str):
        s = vspages.page(site, slug, len(lessons.lessons), len(lessons.tracks))
        if s is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return HTMLResponse(s, headers={"Cache-Control": "public, max-age=300"})

    @app.get("/lessons/{lesson_id}")
    async def lesson_page(lesson_id: str):
        s = lessons.page(lesson_id)
        if s is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return HTMLResponse(s, headers={"Cache-Control": "public, max-age=300"})

    @app.get("/learn")
    async def learn_page():
        return page_as("/learn", "Learn to trade: lessons and chart tests | Meme Street", lessons.hub_text)

    @app.get("/leaders")
    async def leaders_page():
        return page_as("/leaders", "Leaderboards: today and all time | Meme Street",
                       "Who is up the most on Meme Street today and of all time, by return and by profit. The return boards "
                       "count returns on money put in, so buying MB cannot buy a better place on them.")

    @app.get("/about")
    async def about_page():
        """What Meme Street is, for people who have not signed up yet (a plain page: no game connection)."""
        return FileResponse(os.path.join(web, "about.html"), headers={"Cache-Control": "public, max-age=300"})

    @app.get("/bots/guide")
    async def bots_guide_page():
        """How the trading bots work: setting one up, every word a rule can use, news scores, backtests."""
        return FileResponse(os.path.join(web, "bots-guide.html"), headers={"Cache-Control": "public, max-age=300"})

    @app.get("/terms")
    async def terms_page():
        return FileResponse(os.path.join(web, "terms.html"), headers={"Cache-Control": "public, max-age=300"})

    @app.get("/privacy")
    async def privacy_page():
        return FileResponse(os.path.join(web, "privacy.html"), headers={"Cache-Control": "public, max-age=300"})

    @app.get("/stock/{ticker}")
    async def stock_page(ticker: str):
        if ticker in TICKER_RENAMES:                  # an old link to a renamed product (BULL2 is now 2LMSI)
            return RedirectResponse("/stock/" + TICKER_RENAMES[ticker], status_code=307)
        return page()

    @app.get("/player/{name}")
    async def player_page(name: str):
        return page()

    @app.get("/shop/pay")
    async def shop_pay_page():
        """The pretend checkout used while the shop is in test mode (payments.py); the page itself asks the server for
        the order and refuses if the shop is not in test mode."""
        return FileResponse(os.path.join(web, "shop_pay.html"), headers={"Cache-Control": "no-store"})

    for route in ("holdings", "portfolio", "history", "profile", "social", "shop", "calendar", "bots"):
        app.add_api_route("/" + route, lambda: page(), methods=["GET"], include_in_schema=False)
