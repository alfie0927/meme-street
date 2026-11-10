"""The pages of the site (the game, the admin page, the logo). Served by the game server, and by every gateway in a
multi-process set-up, so both look the same."""
import html
import json
import os

from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

import lessonpages
import paths
from netutil import TICKER_RENAMES

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

    def daily_page():
        """The Daily Chart, for searches such as "daily stock market game" (2026-10-31)."""
        data = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Daily Chart by Meme Street",
                "url": site + "/daily", "applicationCategory": "GameApplication", "operatingSystem": "Any",
                "description": DAILY_TEXT, "image": site + "/brand/memestreet_logo_peaks.png",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
        return page_as("/daily", "Daily Chart: the daily stock market game | Meme Street", DAILY_TEXT,
                       '<script type="application/ld+json">' + json.dumps(data) + "</script>", DAILY_BODY)

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
    public = ["/daily", "/", "/about", "/bots/guide", lessonpages.CALC_PATH] + lessons.paths()

    @app.get("/robots.txt")
    async def robots():
        """For search engines: everything but the admin page and the API, and where the sitemap is."""
        return PlainTextResponse(f"User-agent: *\nDisallow: /admin\nDisallow: /api/\nSitemap: {site}/sitemap.xml\n")

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
    async def daily():
        return daily_page()

    @app.get("/lessons")
    async def lessons_hub():
        """Every Learn lesson, listed by track (lessonpages.py)."""
        return HTMLResponse(lessons.hub(), headers={"Cache-Control": "public, max-age=300"})

    @app.get(lessonpages.CALC_PATH)
    async def position_size_calculator():
        """A free position size calculator (lessonpages.py), for searches such as "position size calculator"."""
        return HTMLResponse(lessons.calculator(), headers={"Cache-Control": "public, max-age=300"})

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
