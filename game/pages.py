"""The pages of the site (the game, the admin page, the logo). Served by the game server, and by every gateway in a
multi-process set-up, so both look the same."""
import html
import json
import os

from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response

import paths
from netutil import TICKER_RENAMES

BRAND_FILES = {"memestreet_logo_peaks.png", "memestreet_header_peaks.png", "favicon.ico", "icon-48.png", "icon-192.png",
               "icon-512.png", "apple-touch-icon.png"}   # (the small icons: browser tabs, phones and search results)
DAILY_TEXT = ("A free daily stock market game: one new chart a day, the same for everyone. Two minutes to buy, sell and "
              "short as the candles print, then see how your return ranks against every other player. Like Wordle, "
              "for trading.")
SCRIPTS = {"chart.js", "bots.js", "daily.js", "learn.js"}   # the page's own scripts in web/ (the chart, TA-F2; the Bots page; the Daily Chart; the Learn page)


def add_pages(app):
    """The pages are in web/ and the logo in brand/ (paths.py)."""
    web = paths.WEB

    def page():
        return FileResponse(os.path.join(web, "index.html"), headers={"Cache-Control": "no-store"})

    cache = {}

    def page_as(path, title, description, extra=""):
        """index.html with its own title, description, preview and address for a page search engines should list on
        its own (the Daily Chart): the same file, so nothing else changes."""
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
            cache.clear()
            cache[key] = s
        return HTMLResponse(cache[key], headers={"Cache-Control": "no-store"})

    def daily_page():
        """The Daily Chart, for searches such as "daily stock market game" (2026-10-31)."""
        data = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Daily Chart by Meme Street",
                "url": site + "/daily", "applicationCategory": "GameApplication", "operatingSystem": "Any",
                "description": DAILY_TEXT, "image": site + "/brand/memestreet_logo_peaks.png",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
        return page_as("/daily", "Daily Chart: the daily stock market game | Meme Street", DAILY_TEXT,
                       '<script type="application/ld+json">' + json.dumps(data) + "</script>")

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
    public = ("/daily", "/", "/about", "/learn", "/daily", "/leaders", "/bots/guide", "/terms", "/privacy")

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
        return page()

    @app.get("/daily")
    async def daily():
        return daily_page()

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

    for route in ("holdings", "portfolio", "history", "profile", "social", "leaders", "shop", "learn", "calendar", "bots"):
        app.add_api_route("/" + route, lambda: page(), methods=["GET"], include_in_schema=False)
