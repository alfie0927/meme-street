# Meme Street

A stock-market game for learning to trade, or just trading for fun, with play money (memebucks, MB). Everyone starts
with 1,000 MB; more can be bought in packages and is never cashed out, and lessons and challenges award it for free.
The market is simulated: prices drift, trend, range and break out, react to an economic calendar and to earnings, and
move with the statistics of real charts, so technical analysis on it is worth learning. Live at
[memestreet.net](https://memestreet.net).

## Where things are

| Folder | What is in it |
|---|---|
| `game/` | The Python code: the game engine (`engine.py`), the price model (`market_model.py`), the web server (`server.py`), the shop, lessons, accounts, chat... |
| `web/` | The pages: the player site (`index.html`), the admin dashboard (`admin.html`), the about page, the test checkout |
| `content/` | The content packs (`.json`): settings, sectors, companies, news templates, lessons. Hot-reloaded while the game runs |
| `tools/` | Scripts run by hand: start with gateways, reset the game, share it from your PC, check the charts' realism |
| `data/` | What the running game writes: the save, the ledger, backups, the local admin key. Never in git |
| `docs/` | `HOW_IT_WORKS.md` (the full guide), `ROADMAP.md` (the plan), `MARKET_REALISM.md` (the research behind the charts) |
| `deploy/` | Putting it on a server: the guide (`DEPLOY.md`), upload, setup, services, backups |
| `tests/` | The test suite |
| `brand/` | The logo and promotional media |

## Run it on Windows

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
powershell -File start_game.ps1
```

Then open http://127.0.0.1:8000 (the admin page is at `/admin`; its key is in `data\admin_key.txt`). `start_game.ps1
-Fresh` starts a new game and keeps the old one in `data\backups\`. Without the script:
`.venv\Scripts\python.exe -m uvicorn server:app --app-dir game --port 8000`.

Tests: `.venv\Scripts\python.exe -m unittest discover tests` (about ten minutes).

## More

- How everything works, every setting and every endpoint: `docs/HOW_IT_WORKS.md` (start with section 1).
- What is planned and why: `docs/ROADMAP.md`.
- Updating the live site: `powershell -File deploy\upload.ps1 -Server root@<server> -Restart` (`deploy/DEPLOY.md`).
