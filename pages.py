"""The pages of the site (the game, the admin page, the logo). Served by the game server, and by every gateway in a
multi-process set-up, so both look the same."""
import os

from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from netutil import TICKER_RENAMES

BRAND_FILES = {"memestreet_logo_peaks.png", "memestreet_header_peaks.png"}


def add_pages(app, base):
    def page():
        return FileResponse(os.path.join(base, "index.html"), headers={"Cache-Control": "no-store"})

    @app.get("/brand/{name}")
    async def brand_file(name: str):
        """The logo (only the two named brand images are served)."""
        if name not in BRAND_FILES:
            return JSONResponse({"error": "not found"}, status_code=404)
        for folder in (os.path.join(base, "brand"), base):
            path = os.path.join(folder, name)
            if os.path.exists(path):
                return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})
        return JSONResponse({"error": "not found"}, status_code=404)

    @app.get("/admin")
    async def admin_page():
        """The page is public but shows nothing until the admin key is entered; the data endpoints check the key."""
        return FileResponse(os.path.join(base, "admin.html"), headers={"Cache-Control": "no-store"})

    @app.get("/")
    async def index():
        return page()

    @app.get("/about")
    async def about_page():
        """What Meme Street is, for people who have not signed up yet (a plain page: no game connection)."""
        return FileResponse(os.path.join(base, "about.html"), headers={"Cache-Control": "public, max-age=300"})

    @app.get("/stock/{ticker}")
    async def stock_page(ticker: str):
        if ticker in TICKER_RENAMES:                  # an old link to a renamed product (BULL2 is now 2LMSI)
            return RedirectResponse("/stock/" + TICKER_RENAMES[ticker], status_code=307)
        return page()

    @app.get("/player/{name}")
    async def player_page(name: str):
        return page()

    for route in ("holdings", "portfolio", "history", "profile", "social", "leaders"):
        app.add_api_route("/" + route, lambda: page(), methods=["GET"], include_in_schema=False)
