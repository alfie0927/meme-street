"""Where everything is, so that no file depends on the folder the game was started from.

    game/      the Python code (this file is here)
    web/       the pages the site serves (the game, the admin page, the about page, the test checkout)
    content/   the content packs (.json): companies, sectors, news templates, settings, lessons
    brand/     the logo
    tools/     scripts run by hand (launch.py, reset_game.py, share.py, chart_check.py, realism.py)
    data/      what the running game writes: the save, the chart file, the ledger, backups (never in git)"""
import os

GAME = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(GAME)
WEB = os.path.join(ROOT, "web")
CONTENT = os.path.join(ROOT, "content")
BRAND = os.path.join(ROOT, "brand")
TOOLS = os.path.join(ROOT, "tools")
DATA = os.path.join(ROOT, "data")
BACKUPS = os.path.join(DATA, "backups")
STATE_FILE = os.path.join(DATA, "state.json")
LEDGER_FILE = os.path.join(DATA, "ledger.db")
CONTENT_GLOB = os.path.join(CONTENT, "*.json")
