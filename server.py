import asyncio, json, logging, os, secrets, shutil, threading, time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from engine import GUEST_KEY, Engine
from accounts import DUMMY_RECORD, Limiter, canonical_email, hash_password, password_problem, verify_password
from mailer import Mailer
from netutil import caller_address
from pages import add_pages
from wsconn import Conn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
engine = Engine(ledger_path=os.path.join(BASE, "ledger.db"))
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")

# The engine is not thread safe, so it is only ever touched while holding `lock`. The game tick, trades and every
# lookup run in worker threads (never on the event loop), so a slow tick can't freeze the websockets and a burst of
# requests can't delay the tick by more than the time one call holds the lock.
lock = threading.Lock()
pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="engine")
perf = {"tick_ms": 0.0, "tick_max_ms": 0.0, "send_ms": 0.0, "late_ticks": 0, "ticks": 0, "last_save_ms": 0.0,
        "recent": deque(maxlen=120)}


def locked(fn, *args, **kw):
    with lock:
        return fn(*args, **kw)


async def run(fn, *args, **kw):
    return await asyncio.get_running_loop().run_in_executor(pool, lambda: locked(fn, *args, **kw))


def dumps(obj):
    return json.dumps(obj, separators=(",", ":"))


clients = {}   # websocket -> Conn here, and (gateway id, connection id) -> RemoteConn for a client on a gateway
gateways = {}  # gateway id -> GatewayLink (see the end of the websocket section)
CORE_KEY = os.environ.get("CORE_KEY", "")   # the shared secret gateways must present; with none set, no gateway can connect


def tick_step(n, tokens):
    """Runs in a worker thread with the lock held: advance the game one second and prepare every update. `tokens` are
    the players that have a page open, here or on a gateway. Returns the part every player gets (serialised once,
    however many players are online), each player's own part, and any notices."""
    t0 = time.perf_counter()
    engine.tick()
    saved = 0.0
    if n % 30 == 0:
        s0 = time.perf_counter()
        engine.save(full=False)
        saved = (time.perf_counter() - s0) * 1000
    base = dumps(engine.build_wire())
    mes, notes = {}, {}
    for tok in tokens:
        p = engine.by_token.get(tok) or engine.guest_for(tok)
        if p is None:
            continue
        mes[tok] = dumps(engine.me_state(p, notices=False))
        if p.notices:
            notes[tok] = engine.take_notices(p)
    return base, mes, notes, (time.perf_counter() - t0) * 1000, saved


async def game_loop():
    n = 0
    loop = asyncio.get_running_loop()
    while True:
        t0 = time.time()
        try:
            tokens = {c.token for c in clients.values()}
            base, mes, notes, ms, saved = await loop.run_in_executor(pool, lambda: locked(tick_step, n, tokens))
            n += 1
            perf["ticks"] += 1
            perf["tick_ms"] = ms if perf["tick_ms"] == 0 else 0.9 * perf["tick_ms"] + 0.1 * ms
            perf["recent"].append(ms)
            perf["tick_max_ms"] = max(perf["recent"])
            if saved:
                perf["last_save_ms"] = saved
            s0 = time.perf_counter()
            for conn in list(clients.values()):
                if conn.remote:                          # (a client on a gateway is served by its gateway, below)
                    continue
                me = mes.get(conn.token)
                if me:
                    conn.push_tick(base[:-1] + ',"me":' + me + "}")
                if conn.token in notes:
                    conn.push(dumps({"type": "notice", "msgs": notes[conn.token]}))
            for link in list(gateways.values()):
                link.send_tick(base, mes, notes)
            perf["send_ms"] = 0.9 * perf["send_ms"] + 0.1 * (time.perf_counter() - s0) * 1000
        except Exception:
            logger.exception("tick error")
        spent = time.time() - t0
        if spent > 1.0:
            perf["late_ticks"] += 1
        await asyncio.sleep(max(0.05, 1.0 - spent))


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(game_loop())
    yield
    task.cancel()
    try:
        await task
    except BaseException:
        pass
    with lock:
        engine.save()
        if engine.ledger is not None:
            engine.ledger.close()
    pool.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)


class Join(BaseModel):
    name: str


@app.get("/api/auth_mode")
async def auth_mode():
    """The sign-in box asks this: are passwords required, or is this a name-only game? Is an email address asked for
    ("off", "optional" or "required") and can mail actually be sent (otherwise there is no password recovery)?"""
    return {"passwords": bool(engine.settings.get("require_password", True)), "email": engine.email_mode(),
            "mail_ready": mailer.configured}


class Register(BaseModel):
    name: str
    password: str
    email: str = ""


class EmailIn(BaseModel):
    email: str


class CodeIn(BaseModel):
    code: str


class Forgot(BaseModel):
    name: str


class Recover(BaseModel):
    name: str
    code: str
    password: str


class AdminEmail(BaseModel):
    name: str
    action: str


class PasswordChange(BaseModel):
    new: str
    current: str = ""


class ResetPassword(BaseModel):
    name: str


# ---- accounts: sign-up, login and the limits around them (see accounts.py)
limits = Limiter()
hash_slots = asyncio.Semaphore(4)              # at most four password hashes at once: each uses 16 MB and some CPU


def client_ip(request):
    """The caller's address (see netutil.caller_address for when a forwarding header is believed)."""
    peer = request.client.host if request.client else "unknown"
    return caller_address(peer, request.headers, bool(engine.settings.get("trust_proxy", False)))


async def hashed(password):
    async with hash_slots:
        return await asyncio.get_running_loop().run_in_executor(pool, hash_password, password)


async def verified(password, record):
    async with hash_slots:
        return await asyncio.get_running_loop().run_in_executor(pool, verify_password, password, record or DUMMY_RECORD)


def too_many(seconds):
    return JSONResponse({"error": f"Too many attempts. Try again in {seconds} s."}, status_code=429,
                        headers={"Retry-After": str(seconds)})


@app.post("/api/join")
async def join(j: Join):
    """Name-only sign-up. Only available while `require_password` is off (tests, a closed friends-only game)."""
    if engine.settings.get("require_password", True):
        return JSONResponse({"error": "Create an account with a password"}, status_code=400)
    p, err = await run(engine.join, j.name)
    if not p:
        return JSONResponse({"error": err}, status_code=400)
    return {"token": p.token, "name": p.name}


@app.post("/api/register")
async def register(j: Register, request: Request):
    ip = client_ip(request)
    now = time.time()
    cap = int(engine.settings.get("signups_per_ip_hour", 5))
    if cap > 0 and limits.count(("signup", ip), 3600, now) >= cap:
        return too_many(limits.retry_after(("signup", ip), 3600, now))
    problem = password_problem(j.password, j.name)
    if problem:
        return JSONResponse({"error": problem}, status_code=400)
    mode = engine.email_mode()
    addr = None
    if mode != "off" and (j.email.strip() or mode == "required"):     # check the address before the account exists
        addr, err = engine.email_check(j.email)
        if err:
            return JSONResponse({"error": err}, status_code=400)
        if canonical_email(addr) in engine.email_owner:
            return JSONResponse({"error": "That email address is already used by another account"}, status_code=400)
    record = await hashed(j.password)
    p, err = await run(engine.register, j.name, record, ip)
    if not p:
        return JSONResponse({"error": err}, status_code=400)
    limits.add(("signup", ip), now)
    token = await run(engine.new_session, p, ip)
    out = {"token": token, "name": p.name}
    if addr:
        out.update(await start_verification(p, addr))
    await run(engine.save, False)                # an account must survive a crash: it has a password nobody can recreate
    return out


# ---- email: verifying an address and recovering a password (see accounts.py and mailer.py)
mailer = Mailer.from_env()
if mailer.configured:                           # with real mail, asking for an address makes sense: optional unless a setting says otherwise
    engine.default_email_mode = "optional"


def mail_allowed(now):
    """A ceiling on all mail the game sends in an hour, so abuse can't run up the mail bill or get the sender
    blacklisted."""
    cap = int(engine.settings.get("mail_per_hour", 200))
    return cap <= 0 or limits.count(("mail",), 3600, now) < cap


def send_mail(to, subject, body):
    limits.add(("mail",), time.time())
    return mailer.send(to, subject, body)


def minutes():
    return int(engine.settings.get("email_code_minutes", 15))


async def start_verification(p, addr):
    """Make a code for `addr` and mail it. Returns the fields the page needs: what to tell the player."""
    if not mail_allowed(time.time()):
        return {"email_msg": "Mail is busy right now. Open Profile in a few minutes and ask for the code again."}
    ok, msg, code, to, _ = await run(engine.email_begin, p, addr)
    if ok:
        send_mail(to, f"Your Meme Street code: {code}",
                  f"Your Meme Street verification code is:\n\n    {code}\n\nIt works for {minutes()} minutes. Type it into the "
                  "game to confirm this email address.\n\nIf you did not ask for this, ignore this email: nothing will "
                  "change on any account.\n")
    return {"email_msg": msg, "email_sent": bool(ok)}


@app.post("/api/account/email")
async def account_email(b: EmailIn, request: Request, x_token: str = Header("")):
    """Add or change the account's email address: a code is mailed to it."""
    p = engine.player_for(x_token)
    if p is None:
        return JSONResponse({"error": "bad token"}, status_code=401)
    ip = client_ip(request)
    now = time.time()
    if limits.count(("email-ip", ip), 3600, now) >= 12:
        return too_many(limits.retry_after(("email-ip", ip), 3600, now))
    limits.add(("email-ip", ip), now)
    if engine.email_mode() == "off":
        return JSONResponse({"error": "Email is not used in this game"}, status_code=400)
    out = await start_verification(p, b.email)
    await run(engine.save, False)
    return {"ok": bool(out.get("email_sent")), "msg": out["email_msg"]}


@app.post("/api/account/email/resend")
async def account_email_resend(request: Request, x_token: str = Header("")):
    p = engine.player_for(x_token)
    if p is None:
        return JSONResponse({"error": "bad token"}, status_code=401)
    now = time.time()
    ip = client_ip(request)
    if limits.count(("email-ip", ip), 3600, now) >= 12:
        return too_many(limits.retry_after(("email-ip", ip), 3600, now))
    limits.add(("email-ip", ip), now)
    addr = p.email_pending or (p.email if not p.email_verified else None)
    if not addr:
        return {"ok": False, "msg": "There is no address waiting to be verified"}
    out = await start_verification(p, addr)
    return {"ok": bool(out.get("email_sent")), "msg": out["email_msg"]}


@app.post("/api/account/email/verify")
async def account_email_verify(b: CodeIn, x_token: str = Header("")):
    p = engine.player_for(x_token)
    if p is None:
        return JSONResponse({"error": "bad token"}, status_code=401)
    key = ("verify-fail", p.token)
    now = time.time()
    if limits.count(key, 900, now) >= 20:                  # (the code itself also dies after a few wrong tries)
        return too_many(limits.retry_after(key, 900, now))
    ok, msg = await run(engine.email_confirm, p, b.code)
    if not ok:
        limits.add(key, now)
    else:
        await run(engine.save, False)
    return {"ok": ok, "msg": msg}


@app.post("/api/account/forgot")
async def account_forgot(b: Forgot, request: Request):
    """A forgotten password. Always answers the same way, whether or not the name exists or has a verified address."""
    ip = client_ip(request)
    now = time.time()
    if limits.count(("forgot-ip", ip), 3600, now) >= 10:
        return too_many(limits.retry_after(("forgot-ip", ip), 3600, now))
    limits.add(("forgot-ip", ip), now)
    if mail_allowed(now):
        got = await run(engine.recovery_begin, b.name)
        if got:
            code, to = got
            send_mail(to, f"Meme Street password reset code: {code}",
                      f"Someone asked to reset the password of the Meme Street account \"{b.name.strip()}\".\n\n"
                      f"Your reset code is:\n\n    {code}\n\nIt works for {minutes()} minutes. Type it into the game "
                      "together with a new password.\n\nIf this was not you, ignore this email: your password stays "
                      "as it is.\n")
    return {"ok": True, "msg": "If that account has a verified email address, we have sent it a reset code."}


@app.post("/api/account/recover")
async def account_recover(b: Recover, request: Request):
    """Finish a password reset: the code from the email plus a new password. Logs the player in."""
    ip = client_ip(request)
    now = time.time()
    name_key, ip_key = ("recover-name", b.name.strip().lower()), ("recover-ip", ip)
    if limits.count(name_key, 900, now) >= 10:
        return too_many(limits.retry_after(name_key, 900, now))
    if limits.count(ip_key, 900, now) >= 30:
        return too_many(limits.retry_after(ip_key, 900, now))
    problem = password_problem(b.password, b.name)
    if problem:
        return JSONResponse({"error": problem}, status_code=400)
    record = await hashed(b.password)
    p, err = await run(engine.recovery_finish, b.name, b.code, record)
    if p is None:
        limits.add(name_key, now)
        limits.add(ip_key, now)
        return JSONResponse({"error": err}, status_code=400)
    token = await run(engine.new_session, p, ip)
    await run(engine.save, False)
    return {"ok": True, "token": token, "name": p.name, "msg": "Password changed. You are logged in."}


@app.post("/api/login")
async def login(j: Register, request: Request):
    ip = client_ip(request)
    now = time.time()
    name_key = ("fail-name", j.name.strip().lower())
    ip_key = ("fail-ip", ip)
    if limits.count(name_key, 900, now) >= int(engine.settings.get("login_fails_per_name", 5)):
        return too_many(limits.retry_after(name_key, 900, now))
    if limits.count(ip_key, 600, now) >= int(engine.settings.get("login_fails_per_ip", 20)):
        return too_many(limits.retry_after(ip_key, 600, now))
    token, record = await run(engine.password_record, j.name)
    ok = await verified(j.password, record)
    if not (token and ok):                       # one answer for "no such name" and "wrong password"
        limits.add(name_key, now)
        limits.add(ip_key, now)
        return JSONResponse({"error": "Wrong name or password"}, status_code=401)
    limits.clear(name_key)
    p = engine.by_token.get(token)
    session = await run(engine.new_session, p, ip)
    return {"token": session, "name": p.name}


@app.post("/api/logout")
async def logout(x_token: str = Header("")):
    await run(engine.end_session, x_token or "")
    return {"ok": True}


@app.post("/api/account/password")
async def change_password(b: PasswordChange, x_token: str = Header("")):
    """Set a password (accounts from before passwords) or change it. Every other session ends and the answer carries
    a fresh session token for this browser, because an account's old permanent token stops working once it has a
    password."""
    p = engine.player_for(x_token)
    if p is None:
        return JSONResponse({"error": "bad token"}, status_code=401)
    key = ("fail-name", p.name.lower())
    now = time.time()
    if p.pw:
        if limits.count(key, 900, now) >= int(engine.settings.get("login_fails_per_name", 5)):
            return too_many(limits.retry_after(key, 900, now))
        if not await verified(b.current, p.pw):
            limits.add(key, now)
            return JSONResponse({"error": "The current password is not right"}, status_code=401)
    problem = password_problem(b.new, p.name)
    if problem:
        return JSONResponse({"error": problem}, status_code=400)
    record = await hashed(b.new)

    def apply():
        engine.set_password(p, record)
        engine.end_all_sessions(p)
        return engine.new_session(p)
    token = await run(apply)
    await run(engine.save, False)
    return {"ok": True, "token": token, "msg": "Password saved. Other devices have been logged out."}


@app.post("/api/account/logout_all")
async def logout_everywhere(x_token: str = Header("")):
    p = engine.player_for(x_token)
    if p is None:
        return JSONResponse({"error": "bad token"}, status_code=401)
    n = await run(engine.end_all_sessions, p, x_token)
    return {"ok": True, "msg": f"Logged out of {n} other device(s)" if n else "There were no other devices logged in"}


def broadcast(text, audience=None, members_only=False):
    """Queue a message for every open connection, or only for the tokens in `audience` (a set of player keys).
    `members_only` leaves out logged-out visitors (chat is not for them)."""
    for conn in list(clients.values()):
        if not conn.remote and (audience is None or conn.token in audience) and not (members_only and conn.token == GUEST_KEY):
            conn.push(text)
    for link in list(gateways.values()):
        link.broadcast(text, audience, members_only)


def do_chat(p, text, channel, share):
    ok, msg, m = engine.post_chat(p, text, channel, share)
    return ok, msg, m, (engine.chat_audience(m) if m else None)


async def handle_message(conn, p, raw):
    """One message from a page. `conn` is where the answers go: the page's own websocket, or the stand-in the game
    keeps for a page that is connected through a gateway. The two behave alike from here on."""
    try:
        if len(raw) > 2000:
            return
        m = json.loads(raw)
        if not isinstance(m, dict):
            return
        kind = m.get("type")
        if p.guest and kind not in ("history", "company", "sync"):      # a logged-out visitor may only look
            conn.push(dumps({"type": "result", "ok": False, "msg": "Create an account or sign in to do that"}))
            return
        if kind == "trade":
            try:
                raw_amount = m.get("amount")
                amount = None if raw_amount in (None, "") else float(raw_amount)
                ok, msg = await run(engine.trade, p, str(m.get("ticker")), str(m.get("side")),
                                    float(m.get("pct") or 0), amount)
            except (ValueError, TypeError):
                ok, msg = False, "Bad trade request"
            except Exception:
                logger.exception("trade failed")
                ok, msg = False, "Trade error"
            conn.push(dumps({"type": "result", "ok": ok, "msg": msg}))
        elif kind == "order":
            now = time.time()
            if now - conn.last_query.get("order", 0.0) < 0.2:
                conn.push(dumps({"type": "result", "ok": False, "msg": "Slow down a little"}))
                return
            conn.last_query["order"] = now
            try:
                action = str(m.get("action"))
                if action == "cancel":
                    ok, msg = await run(engine.cancel_order, p, m.get("id"))
                elif action == "bracket":
                    ok, msg = await run(engine.place_bracket, p, str(m.get("ticker")),
                                        float(m.get("take_profit")), float(m.get("stop_loss")))
                elif action == "place":
                    raw_amount = m.get("amount")
                    raw_pct = m.get("pct")
                    ok, msg = await run(engine.place_order, p, str(m.get("ticker")), str(m.get("kind")),
                                        float(m.get("trigger")),
                                        None if raw_pct in (None, "") else float(raw_pct),
                                        None if raw_amount in (None, "") else float(raw_amount))
                else:
                    ok, msg = False, "Unknown order action"
            except (ValueError, TypeError):
                ok, msg = False, "Bad order request"
            except Exception:
                logger.exception("order failed")
                ok, msg = False, "Order error"
            conn.push(dumps({"type": "result", "ok": ok, "msg": msg}))
        elif kind == "contest_trade":
            now = time.time()
            if now - conn.last_query.get("contest_trade", 0.0) < 0.2:
                conn.push(dumps({"type": "result", "ok": False, "msg": "Slow down a little"}))
                return
            conn.last_query["contest_trade"] = now
            try:
                raw_amount = m.get("amount")
                ok, msg = await run(engine.contest_trade, p, str(m.get("id")), str(m.get("ticker")),
                                    str(m.get("side")), float(m.get("pct") or 0),
                                    None if raw_amount in (None, "") else float(raw_amount))
            except (ValueError, TypeError):
                ok, msg = False, "Bad trade request"
            except Exception:
                logger.exception("contest trade failed")
                ok, msg = False, "Trade error"
            conn.push(dumps({"type": "result", "ok": ok, "msg": "Contest (paper money): " + msg, "contest": True}))
        elif kind in ("history", "company"):
            now = time.time()
            if now - conn.last_query.get(kind, 0.0) < 0.2:  # lookups are heavier than trades
                return
            conn.last_query[kind] = now
            ticker = str(m.get("ticker", ""))
            if kind == "history":
                result = await run(engine.chart_for, ticker, str(m.get("period", "30s")))
            else:
                result = await run(engine.company_for, ticker)
            conn.push(dumps(result))
        elif kind == "chat":
            ok, msg, cm, audience = await run(do_chat, p, str(m.get("text", ""))[:600],
                                              str(m.get("channel", "global"))[:60], m.get("share"))
            if ok:
                broadcast(dumps({"type": "chat", "msg": cm}), audience, members_only=True)
            else:
                conn.push(dumps({"type": "chat_error", "msg": msg}))
        elif kind == "chat_history":
            conn.push(dumps({"type": "chat_history", "msgs": await run(engine.chat_history, p)}))
        elif kind == "chat_report":
            ok, msg = await run(engine.report_chat, p, int(m.get("id", 0)))
            conn.push(dumps({"type": "result", "ok": ok, "msg": msg}))
            for mid in await run(engine.take_auto_deletes):       # enough reports removed it: tell every page
                broadcast(dumps({"type": "chat_delete", "id": mid}), members_only=True)
        elif kind == "chat_appeal":
            ok, msg = await run(engine.appeal, p, str(m.get("text", ""))[:600])
            conn.push(dumps({"type": "result", "ok": ok, "msg": msg}))
        elif kind == "sync":                               # the page noticed it missed updates
            now = time.time()
            if now - conn.last_query.get(kind, 0.0) >= 2.0:
                conn.last_query[kind] = now
                conn.push(await run(lambda: dumps(engine.init_for(p))))
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug("ignored malformed websocket message: %r", e)
    except Exception:
        logger.exception("websocket message failed")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str = ""):
    await ws.accept()
    p = engine.player_for(token) or engine.guest_for(token)
    if not p:
        await ws.send_text(dumps({"type": "error", "msg": "bad token"}))
        await ws.close()
        return
    conn = Conn(ws, p.token, clients)           # (the account's own key, never the session token)
    conn.push(await run(lambda: dumps(engine.init_for(p))))
    clients[ws] = conn
    conn.task = asyncio.create_task(conn.writer())
    try:
        while conn.alive:
            await handle_message(conn, p, await ws.receive_text())
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        conn.close()
        if conn.task:
            conn.task.cancel()


# ---- gateways: other processes that hold the websockets (see gateway.py)
class RemoteConn:
    """What the game keeps for a page that is connected to a gateway: the page's messages arrive over the gateway's
    link and are handled one at a time, in order, exactly as for a local websocket; answers go back over the link."""
    remote = True

    def __init__(self, link, cid, p):
        self.link, self.cid, self.p, self.token = link, cid, p, p.token
        self.inbox = deque()
        self.wake = asyncio.Event()
        self.last_query = {}
        self.alive = True
        self.counted = False                        # has it been added to its gateway's list of open pages yet?
        self.task = None

    @property
    def key(self):
        return (self.link.id, self.cid)

    def push(self, text):
        if self.alive:
            self.link.conn.push(dumps({"t": "to", "c": self.cid, "x": text}))

    def push_tick(self, text):
        pass

    def close(self, hang_up=False):
        if not self.alive:
            return
        self.alive = False
        self.wake.set()
        self.link.forget(self)
        if hang_up and self.link.alive:
            self.link.conn.push(dumps({"t": "hangup", "c": self.cid}))

    async def run(self):
        """First the page's `init`, then its messages in order, until it goes away."""
        try:
            init = await run(lambda: dumps(engine.init_for(self.p)))
            if not self.alive:
                return
            self.push(init)
            self.link.players[self.token] = self.link.players.get(self.token, 0) + 1
            self.counted = True
            self.link.conn.push(dumps({"t": "opened", "c": self.cid, "pk": self.token}))      # (after the init, and ticks only follow it)
            while self.alive:
                while self.inbox:
                    await handle_message(self, self.p, self.inbox.popleft())
                    if not self.alive:
                        return
                self.wake.clear()
                if not self.inbox:
                    await self.wake.wait()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("gateway client failed")
            self.close(hang_up=True)


class GatewayLink:
    """One gateway process, connected over a websocket of its own."""
    _ids = 0

    def __init__(self, ws):
        GatewayLink._ids += 1
        self.id = GatewayLink._ids
        self.ws = ws
        self.conn = Conn(ws, "gateway")            # the writer: ordered messages, plus one slot for the latest tick
        self.conn.limit = 50000                    # (one link carries every page of a gateway, so its queue is deep)
        self.conns = {}                            # connection id -> RemoteConn
        self.players = {}                          # player key -> how many of its pages are open on this gateway
        self.alive = True

    def forget(self, rc):
        self.conns.pop(rc.cid, None)
        clients.pop(rc.key, None)
        if rc.counted:
            rc.counted = False
            n = self.players.get(rc.token, 0) - 1
            if n > 0:
                self.players[rc.token] = n
            else:
                self.players.pop(rc.token, None)

    def send_tick(self, base, mes, notes):
        """The shared part once, then each of this gateway's players' own part: the gateway joins them per page."""
        if not self.players:
            return
        rows = [f"{tok}\t{mes[tok]}" for tok in self.players if tok in mes]
        self.conn.push_tick("T\n" + base + "\n" + "\n".join(rows))
        for tok in self.players:
            if tok in notes:
                self.broadcast(dumps({"type": "notice", "msgs": notes[tok]}), {tok})

    def broadcast(self, text, audience, members_only=False):
        if audience is not None:
            audience = [tok for tok in audience if tok in self.players]
            if not audience:
                return
        self.conn.push(dumps({"t": "bc", "x": text, "aud": audience, "mo": members_only}))

    def open(self, cid, token):
        p = engine.player_for(token) or engine.guest_for(token)
        if p is None:
            self.conn.push(dumps({"t": "to", "c": cid, "x": dumps({"type": "error", "msg": "bad token"})}))
            self.conn.push(dumps({"t": "hangup", "c": cid}))
            return
        rc = RemoteConn(self, cid, p)
        self.conns[cid] = rc
        clients[rc.key] = rc
        rc.task = asyncio.create_task(rc.run())

    def message(self, cid, raw):
        rc = self.conns.get(cid)
        if rc is not None and isinstance(raw, str):
            rc.inbox.append(raw)
            rc.wake.set()

    def drop(self, cid):
        rc = self.conns.get(cid)
        if rc is not None:
            rc.close()
            if rc.task:
                rc.task.cancel()

    def lost(self):
        """The gateway went away: its pages go with it (they reconnect, through it or another gateway)."""
        self.alive = False
        for rc in list(self.conns.values()):
            self.drop(rc.cid)
        gateways.pop(self.id, None)
        self.conn.close()


async def http_for_gateway(msg):
    """Answer a page's ordinary request (sign-in, portfolio, admin...) for a gateway: the request is run through this
    server's own app, as if it had arrived directly."""
    path = str(msg.get("path", "/"))
    headers = [(str(k).lower().encode("latin-1"), str(v).encode("latin-1")) for k, v in dict(msg.get("headers", {})).items()]
    body = str(msg.get("body", "")).encode("utf-8")
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": str(msg.get("method", "GET")),
             "scheme": "http", "path": path, "raw_path": path.encode("utf-8"), "root_path": "",
             "query_string": str(msg.get("qs", "")).encode("latin-1"), "headers": headers,
             "client": ("127.0.0.1", 0), "server": ("127.0.0.1", 0)}
    sent, got = [], []
    state = {"body": body}

    async def receive():
        if state["body"] is not None:
            b, state["body"] = state["body"], None
            return {"type": "http.request", "body": b, "more_body": False}
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            sent.append((message["status"], [(k.decode("latin-1"), v.decode("latin-1")) for k, v in message.get("headers", [])]))
        elif message["type"] == "http.response.body":
            got.append(message.get("body", b""))

    try:
        await app(scope, receive, send)
    except Exception:
        logger.exception("gateway request failed")
        return {"t": "http_res", "id": msg.get("id"), "status": 500, "headers": [["content-type", "application/json"]],
                "body": '{"error":"server error"}'}
    status, hdrs = sent[0] if sent else (500, [])
    keep = [[k, v] for k, v in hdrs if k.lower() not in ("content-length", "server", "date", "connection")]
    return {"t": "http_res", "id": msg.get("id"), "status": status, "headers": keep,
            "body": b"".join(got).decode("utf-8", "replace")}


@app.websocket("/internal/gateway")
async def gateway_endpoint(ws: WebSocket, key: str = ""):
    """A gateway process connects here. Needs the shared CORE_KEY; with none set this door is shut."""
    await ws.accept()
    if not CORE_KEY or not secrets.compare_digest(key.encode("utf-8"), CORE_KEY.encode("utf-8")):
        await ws.close(code=1008)
        return
    link = GatewayLink(ws)
    gateways[link.id] = link
    link.conn.task = asyncio.create_task(link.conn.writer())
    logger.info("gateway %d connected", link.id)
    tasks = set()

    async def answer(m):
        link.conn.push(dumps(await http_for_gateway(m)))
    try:
        while link.alive:
            m = json.loads(await ws.receive_text())
            kind = m.get("t")
            if kind == "open":
                link.open(m["c"], str(m.get("token", "")))
            elif kind == "msg":
                link.message(m["c"], m.get("raw"))
            elif kind == "close":
                link.drop(m["c"])
            elif kind == "http":
                task = asyncio.create_task(answer(m))
                tasks.add(task)
                task.add_done_callback(tasks.discard)
    except (WebSocketDisconnect, RuntimeError, ValueError, KeyError):
        pass
    finally:
        logger.info("gateway %d gone", link.id)
        link.lost()
        for task in tasks:
            task.cancel()


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
    return await run(engine.house_stats)


@app.post("/api/admin/credit")
async def admin_credit(t: Transfer, x_admin_key: str = Header("")):
    """Stand-in for a confirmed memebuck purchase until the crypto payment flow exists."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)

    def work():
        p = find_player(t.name)
        if not p:
            return None
        ok, msg = engine.credit(p, t.amount)
        return ok, msg, p.cash, p.name
    got = await run(work)
    if got is None:
        return JSONResponse({"error": "unknown player"}, status_code=404)
    ok, msg, cash, name = got
    logger.info("admin credit %s %.2f: %s", name, t.amount, msg)
    return {"ok": ok, "msg": msg, "cash": cash}


@app.post("/api/admin/withdraw")
async def admin_withdraw(t: Transfer, x_admin_key: str = Header("")):
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)

    def work():
        p = find_player(t.name)
        if not p:
            return None
        ok, msg = engine.debit(p, t.amount)
        return ok, msg, p.cash, p.name
    got = await run(work)
    if got is None:
        return JSONResponse({"error": "unknown player"}, status_code=404)
    ok, msg, cash, name = got
    logger.info("admin withdraw %s %.2f: %s", name, t.amount, msg)
    return {"ok": ok, "msg": msg, "cash": cash}


# ------------------------------------------------------------------------------------------ players' own data
_last_call = {}


def rate_ok(token, key, interval):
    """Lookups cost the server something; a page that asks faster than this gets a 429 instead."""
    now = time.monotonic()
    if len(_last_call) > 5000:
        _last_call.clear()
    k = (token, key)
    if now - _last_call.get(k, 0.0) < interval:
        return False
    _last_call[k] = now
    return True


async def with_player(x_token, key, fn, *args, interval=0.25):
    """Check the token, apply the rate limit, run `fn(player, *args)` under the engine lock."""
    p = engine.player_for(x_token or "")
    if not p:
        return JSONResponse({"error": "bad token"}, status_code=401)
    if not rate_ok(x_token, key, interval):
        return JSONResponse({"error": "slow down"}, status_code=429)
    return await run(fn, p, *args)


def acted(result):
    ok, msg = result
    return {"ok": ok, "msg": msg}


class Named(BaseModel):
    name: str


class Ident(BaseModel):
    id: str


class Flag(BaseModel):
    public: bool


class MsgId(BaseModel):
    id: int


class Mute(BaseModel):
    name: str
    seconds: float


@app.get("/api/portfolio")
async def portfolio(x_token: str = Header("")):
    """The player's equity curve, positions, realised and unrealised profit, fees, dividends and best/worst trades."""
    return await with_player(x_token, "portfolio", engine.portfolio_for)


@app.get("/api/history")
async def history(x_token: str = Header(""), limit: int = 100, before: int = 0, kind: str = ""):
    """The player's ledger entries, newest first. Page with `before` (the `seq` of the last entry received)."""
    kinds = [k for k in kind.split(",") if k] or None
    return await with_player(x_token, "history", engine.history_for, limit, before or None, kinds)


@app.get("/api/history.csv")
async def history_csv(x_token: str = Header("")):
    p = engine.player_for(x_token or "")
    if not p:
        return JSONResponse({"error": "bad token"}, status_code=401)
    if not rate_ok(x_token, "csv", 2.0):
        return JSONResponse({"error": "slow down"}, status_code=429)
    text = await run(engine.history_csv, p)
    return Response(text, media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="meme-street-{p.name}.csv"'})


@app.get("/api/me")
async def me(x_token: str = Header("")):
    """Achievements, daily quests, tournaments, who you follow, and your ranks."""
    return await with_player(x_token, "me", engine.me_for)


@app.get("/api/boards")
async def boards(x_token: str = Header("")):
    """The season, risk-adjusted and all-time leaderboards."""
    return await with_player(x_token, "boards", engine.boards_for)


@app.post("/api/tournament/join")
async def tournament_join(b: Ident, x_token: str = Header("")):
    res = await with_player(x_token, "tjoin", engine.tournament_join, b.id, interval=0.5)
    return res if isinstance(res, JSONResponse) else acted(res)


@app.get("/api/profile/{name}")
async def profile(name: str, x_token: str = Header("")):
    """Another player's profile. Their results and (delayed) holdings are only included if they made them public."""
    res = await with_player(x_token, "profile", lambda p, n: engine.public_profile(n, p), name)
    if res is None:
        return JSONResponse({"error": "no such player"}, status_code=404)
    return res


@app.get("/api/following")
async def following(x_token: str = Header("")):
    return await with_player(x_token, "following", engine.following_for)


@app.post("/api/follow")
async def follow(b: Named, x_token: str = Header("")):
    res = await with_player(x_token, "follow", engine.follow, b.name, interval=0.3)
    return res if isinstance(res, JSONResponse) else acted(res)


@app.post("/api/unfollow")
async def unfollow(b: Named, x_token: str = Header("")):
    res = await with_player(x_token, "follow", engine.unfollow, b.name, interval=0.3)
    return res if isinstance(res, JSONResponse) else acted(res)


@app.post("/api/public")
async def set_public(b: Flag, x_token: str = Header("")):
    res = await with_player(x_token, "public", engine.set_public, b.public, interval=0.5)
    return res if isinstance(res, JSONResponse) else acted(res)


# ------------------------------------------------------------------------------------------ admin
@app.get("/api/admin/overview")
async def admin_overview(x_admin_key: str = Header("")):
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    guests = sum(1 for c in clients.values() if c.token == GUEST_KEY)      # logged-out visitors watching the market
    data = await run(engine.admin_overview, online=len(clients) - guests, guests=guests)
    data["perf"] = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in perf.items() if k != "recent"}
    data["perf"]["gateways"] = len(gateways)
    return data


@app.get("/api/admin/player/{name}")
async def admin_player(name: str, x_admin_key: str = Header("")):
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    data = await run(engine.admin_player, name)
    if data is None:
        return JSONResponse({"error": "unknown player"}, status_code=404)
    return data


@app.get("/api/admin/chat")
async def admin_chat(x_admin_key: str = Header("")):
    """Recent chat, reports, who is muted and running tournaments, for moderation."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return await run(engine.admin_social)


@app.post("/api/admin/chat/delete")
async def admin_chat_delete(b: MsgId, x_admin_key: str = Header("")):
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    n = await run(engine.delete_chat, b.id, "admin")
    if n:
        broadcast(dumps({"type": "chat_delete", "id": b.id}), members_only=True)
    return {"ok": n > 0, "deleted": n}


@app.post("/api/admin/mute")
async def admin_mute(b: Mute, x_admin_key: str = Header("")):
    """Mute a player's chat for `seconds` (0 lifts the mute)."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    ok, msg = await run(engine.mute, b.name, b.seconds, "admin")
    return {"ok": ok, "msg": msg}


class AppealDecision(BaseModel):
    id: int
    decision: str


class ResetGame(BaseModel):
    confirm: str


def do_reset():
    """Back everything up, then start the game over. Runs under the engine lock."""
    return engine.reset_with_backup(os.path.join(BASE, "backups", time.strftime("reset-%Y%m%d-%H%M%S")))


@app.post("/api/admin/reset")
async def admin_reset(b: ResetGame, x_admin_key: str = Header("")):
    """Start the game over at Day 1 with everyone on the starting balance. Needs the word RESET as confirmation; the
    old save and ledger are copied into backups/ first."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if b.confirm != "RESET":
        return JSONResponse({"ok": False, "msg": "Type RESET to confirm"}, status_code=400)
    folder = await run(do_reset)
    for conn in list(clients.values()):              # every page reconnects and gets the fresh game
        conn.close(hang_up=True)
    return {"ok": True, "msg": "The game is back at Day 1. The old game was saved to " + os.path.relpath(folder, BASE)}


@app.get("/api/admin/accounts")
async def admin_accounts(x_admin_key: str = Header("")):
    """How many accounts have passwords and verified email, and which accounts share an address (possible
    multi-accounting)."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    data = await run(engine.account_stats)
    data["mail"] = mailer.status()
    return data


@app.get("/api/admin/mail")
async def admin_mail(x_admin_key: str = Header("")):
    """The mail the game sent recently. In console mode (no SMTP server set) the messages, codes included, are kept
    here so the admin can pass a code on by hand."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return {"status": mailer.status(), "recent": mailer.recent()}


@app.post("/api/admin/email")
async def admin_email(b: AdminEmail, x_admin_key: str = Header("")):
    """Support actions on one account's email: mark it verified (you checked by other means) or remove it."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)

    def work():
        p = find_player(b.name)
        if p is None:
            return None
        if b.action == "verify":
            ok, msg = engine.email_force_verified(p)
        elif b.action == "clear":
            engine.email_clear(p)
            ok, msg = True, "The email address was removed"
        else:
            return False, "Unknown action"
        engine._log_mod("admin", "email_" + b.action, p.name)
        return ok, msg
    got = await run(work)
    if got is None:
        return JSONResponse({"ok": False, "msg": "Unknown player"}, status_code=404)
    await run(engine.save, False)
    return {"ok": got[0], "msg": got[1]}


@app.post("/api/admin/reset_password")
async def admin_reset_password(b: ResetPassword, x_admin_key: str = Header("")):
    """Give a player who forgot their password a temporary one (shown once) and end all their sessions."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    temp = secrets.token_urlsafe(9)
    record = await hashed(temp)
    p = await run(engine.reset_password, b.name, record)
    if p is None:
        return JSONResponse({"ok": False, "msg": "Unknown player"}, status_code=404)
    await run(engine.save, False)
    return {"ok": True, "msg": f"New temporary password for {p.name}: tell them to change it after logging in",
            "password": temp}


@app.post("/api/admin/appeal")
async def admin_appeal(b: AppealDecision, x_admin_key: str = Header("")):
    """Lift or keep the mute of a player who appealed."""
    if not admin_ok(x_admin_key):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    ok, msg = await run(engine.resolve_appeal, b.id, b.decision)
    return {"ok": ok, "msg": msg}


# ------------------------------------------------------------------------------------------ pages
add_pages(app, BASE)
