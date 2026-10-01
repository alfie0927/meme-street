import asyncio, json, logging, os, secrets, time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from engine import Engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
engine = Engine()
clients = {}
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")


sending = set()


async def _send(ws, text):
    """Send with a deadline; runs as its own task so a stuck client can never stall the game loop."""
    try:
        await asyncio.wait_for(ws.send_text(text), timeout=3)
    except Exception:
        clients.pop(ws, None)
    finally:
        sending.discard(ws)


async def game_loop():
    n = 0
    while True:
        t0 = time.time()
        try:
            engine.tick()
            n += 1
            if n % 30 == 0:
                engine.save()
            for ws, tok in list(clients.items()):
                p = engine.by_token.get(tok)
                if p and ws not in sending:  # a client still receiving the last update just skips this one
                    sending.add(ws)
                    asyncio.create_task(_send(ws, json.dumps(engine.state_for(p))))
        except Exception:
            logger.exception("tick error")
        await asyncio.sleep(max(0.05, 1.0 - (time.time() - t0)))


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(game_loop())
    yield
    task.cancel()
    engine.save()


app = FastAPI(lifespan=lifespan)


class Join(BaseModel):
    name: str


@app.post("/api/join")
async def join(j: Join):
    p, err = engine.join(j.name)
    if not p:
        return JSONResponse({"error": err}, status_code=400)
    return {"token": p.token, "name": p.name}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str = ""):
    await ws.accept()
    p = engine.by_token.get(token)
    if not p:
        await ws.send_text(json.dumps({"type": "error", "msg": "bad token"}))
        await ws.close()
        return
    clients[ws] = token
    last_query = 0.0
    try:
        while True:
            raw = await ws.receive_text()
            try:
                if len(raw) > 2000:
                    continue
                m = json.loads(raw)
                if not isinstance(m, dict):
                    continue
                kind = m.get("type")
                if kind == "trade":
                    try:
                        raw_amount = m.get("amount")
                        amount = None if raw_amount in (None, "") else float(raw_amount)
                        ok, msg = engine.trade(p, str(m.get("ticker")), str(m.get("side")),
                                               float(m.get("pct") or 0), amount)
                    except (ValueError, TypeError):
                        ok, msg = False, "Bad trade request"
                    except Exception:
                        logger.exception("trade failed")
                        ok, msg = False, "Trade error"
                    await ws.send_text(json.dumps({"type": "result", "ok": ok, "msg": msg}))
                elif kind in ("history", "company"):
                    now = time.time()
                    if now - last_query < 0.2:  # history/company lookups are heavier than trades
                        continue
                    last_query = now
                    ticker = str(m.get("ticker", ""))
                    result = (engine.history_for(ticker, str(m.get("period", "30s"))) if kind == "history"
                              else engine.company_for(ticker))
                    await ws.send_text(json.dumps(result))
            except WebSocketDisconnect:
                raise
            except RuntimeError:
                raise
            except (ValueError, TypeError, AttributeError) as e:
                logger.debug("ignored malformed websocket message: %r", e)
            except Exception:
                logger.exception("websocket message failed")
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        clients.pop(ws, None)


class Transfer(BaseModel):
    name: str
    amount: float


def admin_ok(key):
    return bool(ADMIN_KEY) and secrets.compare_digest(key or "", ADMIN_KEY)


def find_player(name):
    return next((p for p in engine.players.values() if p.name.lower() == name.lower()), None)


@app.get("/api/admin/stats")
async def admin_stats(x_admin_key: str = Header("")):
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return engine.house_stats()


@app.post("/api/admin/credit")
async def admin_credit(t: Transfer, x_admin_key: str = Header("")):
    """Stand-in for a confirmed memebuck purchase until the crypto payment flow exists."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    p = find_player(t.name)
    if not p:
        return JSONResponse({"error": "unknown player"}, status_code=404)
    ok, msg = engine.credit(p, t.amount)
    logger.info("admin credit %s %.2f: %s", p.name, t.amount, msg)
    return {"ok": ok, "msg": msg, "cash": p.cash}


@app.post("/api/admin/withdraw")
async def admin_withdraw(t: Transfer, x_admin_key: str = Header("")):
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    p = find_player(t.name)
    if not p:
        return JSONResponse({"error": "unknown player"}, status_code=404)
    ok, msg = engine.debit(p, t.amount)
    logger.info("admin withdraw %s %.2f: %s", p.name, t.amount, msg)
    return {"ok": ok, "msg": msg, "cash": p.cash}


@app.get("/")
async def index():
    return FileResponse(os.path.join(BASE, "index.html"), headers={"Cache-Control": "no-store"})


@app.get("/holdings")
async def holdings_page():
    return FileResponse(os.path.join(BASE, "index.html"), headers={"Cache-Control": "no-store"})


@app.get("/stock/{ticker}")
async def stock_page(ticker: str):
    return FileResponse(os.path.join(BASE, "index.html"), headers={"Cache-Control": "no-store"})


