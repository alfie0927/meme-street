"""A gateway: a process that holds players' websockets and passes everything else on to the game server.

Why. One Python process can run the game and also serve a few hundred players, but sending a page's worth of prices to
every player every second is the expensive part, and one process can only use one core. A gateway takes that part over:
the game server (server.py, the "core") does the thinking once a second and sends each gateway one compact message,
and the gateway turns it into one update per player and sends it out. Run several gateways and the sending is spread
over as many cores. The core stays a single process because the market is one shared thing: one set of prices, one lock.

    browsers --websocket--> gateway --one link--> core (the game: prices, trades, accounts, saves)

What a gateway does:
  * serves the pages (the game, the admin page, the logo);
  * holds each browser's websocket, applies the once-a-second update, and forwards the browser's messages (trades,
    chat, chart requests) to the core, which answers through the same link;
  * passes ordinary requests (`/api/...`: sign-in, portfolio, admin) to the core, adding the caller's real address;
  * rate-limits each browser's messages, so one noisy page cannot flood the core.
It holds no game state at all, so a gateway can be restarted at any moment (its pages reconnect through it or through
another gateway), and if the core restarts every gateway reconnects by itself.

Settings (environment variables): CORE_URL (default ws://127.0.0.1:8001/internal/gateway), CORE_KEY (the shared secret;
the core must have the same), TRUST_PROXY=1 (believe X-Forwarded-For from a proxy on another machine).
Start them with `python launch.py --gateways 4` rather than by hand. Never imports the game server (that builds a game).
"""
import asyncio
import itertools
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from websockets.asyncio.client import connect

from netutil import caller_address
from pages import add_pages
from wsconn import Conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s gateway: %(message)s")
logger = logging.getLogger("gateway")

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
CORE_URL = os.environ.get("CORE_URL", "ws://127.0.0.1:8001/internal/gateway")
CORE_KEY = os.environ.get("CORE_KEY", "")
TRUST_PROXY = os.environ.get("TRUST_PROXY", "") == "1"
FORWARD_HEADERS = ("x-token", "x-admin-key", "content-type", "accept", "user-agent")
MAX_BODY = 64 * 1024
MESSAGES_PER_SECOND = 20.0         # what one page may send, on average ...
MESSAGE_BURST = 40                 # ... with this much saved up
HTTP_TIMEOUT = 30.0


class Page(Conn):
    """One browser's websocket on this gateway."""

    def __init__(self, ws, cid, pages):
        super().__init__(ws, "")
        self.cid, self.pages = cid, pages
        self.pk = None                  # the player's key, known once the core has opened the page
        self.ready = False              # the core has sent this page its first full picture; updates may follow
        self.allowance, self.stamp, self.dropped = float(MESSAGE_BURST), time.monotonic(), 0

    def _forget(self):
        self.pages.pop(self.cid, None)

    async def finish(self):
        """Hang up on the page, but only after what is already queued for it has gone out (an error message, say): the
        game server sends the message and the hang-up together, and closing at once would lose the message."""
        for _ in range(100):
            if not self.outbox and self.tick is None:
                break
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.05)                       # (the last message may still be on its way out)
        self.close(hang_up=True)

    def allow(self):
        """A token bucket: True if the page may send another message now."""
        now = time.monotonic()
        self.allowance = min(float(MESSAGE_BURST), self.allowance + (now - self.stamp) * MESSAGES_PER_SECOND)
        self.stamp = now
        if self.allowance >= 1.0:
            self.allowance -= 1.0
            return True
        self.dropped += 1
        return False


class Core:
    """The link to the game server."""

    def __init__(self):
        self.ws = None
        self.ready = False
        self.pages = {}                   # connection id -> Page
        self.waiting = {}                 # request id -> future of its answer
        self.ids = itertools.count(1)
        self.connected_at = 0.0

    async def send(self, obj):
        ws = self.ws
        if ws is None or not self.ready:
            raise ConnectionError("the game server is not connected")
        await ws.send(json.dumps(obj, separators=(",", ":")))

    # ---- what arrives from the core
    def on_frame(self, text):
        if text.startswith("T\n"):
            self.on_tick(text)
            return
        m = json.loads(text)
        kind = m.get("t")
        if kind == "to":
            page = self.pages.get(m["c"])
            if page is not None:
                page.push(m["x"])
        elif kind == "opened":
            page = self.pages.get(m["c"])
            if page is not None:
                page.pk, page.ready = m.get("pk"), True
        elif kind == "bc":
            wanted = None if m.get("aud") is None else set(m["aud"])
            for page in list(self.pages.values()):
                if (wanted is None or page.pk in wanted) and not (m.get("mo") and page.pk == "guest"):
                    page.push(m["x"])
        elif kind == "hangup":
            page = self.pages.get(m["c"])
            if page is not None:
                asyncio.get_running_loop().create_task(page.finish())
        elif kind == "http_res":
            fut = self.waiting.pop(m.get("id"), None)
            if fut is not None and not fut.done():
                fut.set_result(m)

    def on_tick(self, text):
        """`T`, the part every player gets, then one `player-key <tab> that player's own part` line each. Each page gets
        the shared part with its player's own part spliced in at the end."""
        _, base, *rows = text.split("\n")
        mine = {}
        for row in rows:
            pk, _, me = row.partition("\t")
            mine[pk] = me
        head = base[:-1] + ',"me":'
        for page in self.pages.values():
            if page.ready:
                me = mine.get(page.pk)
                if me:
                    page.push_tick(head + me + "}")

    # ---- the link coming and going
    def attach(self, ws):
        self.ws, self.ready, self.connected_at = ws, True, time.time()
        logger.info("connected to the game server")

    def detach(self):
        """The core is gone: close every page (they reconnect and get a fresh picture) and fail waiting requests."""
        self.ready, self.ws = False, None
        for page in list(self.pages.values()):
            page.close(hang_up=True)
        for fut in self.waiting.values():
            if not fut.done():
                fut.set_exception(ConnectionError("the game server went away"))
        self.waiting.clear()


core = Core()


async def link_loop():
    delay = 1.0
    while True:
        try:
            async with connect(f"{CORE_URL}?key={quote(CORE_KEY)}", max_size=None, ping_interval=20, ping_timeout=40) as ws:
                core.attach(ws)
                delay = 1.0
                async for frame in ws:
                    try:
                        core.on_frame(frame)
                    except Exception:
                        logger.exception("bad frame from the game server")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("no link to the game server (%s: %s); trying again in %.0f s", type(e).__name__, e, delay)
        finally:
            core.detach()
        await asyncio.sleep(delay)
        delay = min(delay * 2, 5.0)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(link_loop())
    yield
    task.cancel()
    try:
        await task
    except BaseException:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/gateway/health")
async def health():
    """For a launcher or a monitor: is this gateway linked to the game?"""
    return {"ok": core.ready, "pages": len(core.pages), "linked_for": round(time.time() - core.connected_at, 1) if core.ready else 0}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str = ""):
    await ws.accept()
    if not core.ready:
        await ws.close(code=1013)                       # try again later: the page reconnects by itself
        return
    cid = next(core.ids)
    page = Page(ws, cid, core.pages)
    core.pages[cid] = page
    page.task = asyncio.create_task(page.writer())
    try:
        await core.send({"t": "open", "c": cid, "token": token[:200]})
        while page.alive:
            raw = await ws.receive_text()
            if len(raw) > 2000:
                continue
            if not page.allow():
                if page.dropped > 400:                  # not slowing down: hang up
                    break
                continue
            await core.send({"t": "msg", "c": cid, "raw": raw})
    except (WebSocketDisconnect, RuntimeError, ConnectionError):
        pass
    finally:
        page.close()
        if page.task:
            page.task.cancel()
        if core.ready:
            try:
                await core.send({"t": "close", "c": cid})
            except Exception:
                pass


@app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def api(request: Request, rest: str):
    """Every ordinary request goes to the core, which answers it exactly as if it had arrived there directly."""
    if not core.ready:
        return JSONResponse({"error": "The game is restarting. Try again in a moment."}, status_code=503, headers={"Retry-After": "3"})
    declared = request.headers.get("content-length", "0")
    if declared.isdigit() and int(declared) > MAX_BODY:
        return JSONResponse({"error": "request too large"}, status_code=413)
    body = await request.body()
    if len(body) > MAX_BODY:
        return JSONResponse({"error": "request too large"}, status_code=413)
    headers = {k: v for k, v in ((k.lower(), v) for k, v in request.headers.items()) if k in FORWARD_HEADERS}
    peer = request.client.host if request.client else "unknown"
    headers["x-forwarded-for"] = caller_address(peer, request.headers, TRUST_PROXY)   # (the core believes this one)
    rid = next(core.ids)
    fut = asyncio.get_running_loop().create_future()
    core.waiting[rid] = fut
    try:
        await core.send({"t": "http", "id": rid, "method": request.method, "path": "/api/" + rest, "qs": request.url.query,
                         "headers": headers, "body": body.decode("utf-8", "replace")})
        res = await asyncio.wait_for(fut, HTTP_TIMEOUT)
    except asyncio.TimeoutError:
        return JSONResponse({"error": "The game took too long to answer"}, status_code=504)
    except ConnectionError:
        return JSONResponse({"error": "The game is restarting. Try again in a moment."}, status_code=503, headers={"Retry-After": "3"})
    finally:
        core.waiting.pop(rid, None)
    return Response(content=res["body"].encode("utf-8"), status_code=int(res["status"]),
                    headers={k: v for k, v in res["headers"]})


add_pages(app, BASE)
