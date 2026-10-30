"""The pages of the site (the game, the admin page, the logo). Served by the game server, and by every gateway in a
multi-process set-up, so both look the same."""
import os

from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

import paths
from netutil import TICKER_RENAMES

BRAND_FILES = {"memestreet_logo_peaks.png", "memestreet_header_peaks.png", "favicon.ico", "icon-48.png", "icon-192.png",
               "icon-512.png", "apple-touch-icon.png"}   # (the small icons: browser tabs, phones and search results)
SCRIPTS = {"chart.js", "bots.js", "daily.js", "learn.js"}   # the page's own scripts in web/ (the chart, TA-F2; the Bots page; the Daily Chart; the Learn page)


def add_pages(app):
    """The pages are in web/ and the logo in brand/ (paths.py)."""
    web = paths.WEB

    def page():
        return FileResponse(os.path.join(web, "index.html"), headers={"Cache-Control": "no-store"})

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

    for route in ("holdings", "portfolio", "history", "profile", "social", "leaders", "shop", "learn", "calendar", "bots", "daily"):
        app.add_api_route("/" + route, lambda: page(), methods=["GET"], include_in_schema=False)
