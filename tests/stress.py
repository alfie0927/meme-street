"""Stress test: many clients hammering one server with valid and invalid messages at once.

Usage:  python tests/stress.py [clients=40] [seconds=30]

Starts its own isolated server (your state.json is never touched). Every client joins, then for the whole
run sends a random mix of: trades (valid and invalid sides, sizes, amounts, tickers), history and company
lookups, chat messages, reports, sync requests, the social HTTP endpoints, garbage that is
not JSON, JSON that is not an object, and oversized messages, and it keeps disconnecting and reconnecting. One extra client never reads its socket (a slow client), and a monitor
checks that the game keeps ticking about once a second and measures how much data each tick costs.

Prints a summary and exits with code 1 if anything failed: a connection error, a tick gap over 4 s, ticks
that were late more than a few times, a traceback through engine.py or server.py, or the token invariant drifting.
"""
import asyncio
import json
import random
import sys
import time
import urllib.error
import urllib.request

import websockets

from _helpers import IsolatedServer

TICKERS = ["NVXA", "CLDR", "GOLD", "MSI", "BOND", "DOGO", "CRUDE", "MOON", "NOPE", ""]
PERIODS = ["30s", "1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1mo", "1y", "day", "bogus", None, 5]
PCTS = [.1, .25, .5, 1, 0, -1, 2, "x", None]
AMOUNTS = [None, None, None, 5, 50, 1e6, -3, "abc", "", 0, 1e308, [1], {}]
CHATS = ["gm", "buy the dip", "<b>bold</b>", "https://spam.example/x", "x" * 400, "", "   ", "shit", "‮ rtl", 5, None]
CHANNELS = ["global", "global", "club:nothing", "weird", None, 7]
HTTP_GETS = ["/api/me", "/api/boards", "/api/portfolio", "/api/history?limit=20", "/api/history.csv",
             "/api/following", "/api/profile/monitor", "/api/profile/nobody"]
HTTP_POSTS = [("/api/follow", {"name": "monitor"}), ("/api/unfollow", {"name": "monitor"}),
              ("/api/public", {"public": True}), ("/api/public", {"public": False}),
              ("/api/tournament/join", {"id": "marathon-0"}), ("/api/follow", {"nope": 1})]


def post(url, path, body, headers=None):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def social_call(srv, token, stats):
    """One random call to the social and portfolio HTTP endpoints; any answer except a server error is fine."""
    try:
        if random.random() < 0.6:
            req = urllib.request.Request(srv.url + random.choice(HTTP_GETS), headers={"X-Token": token})
        else:
            path, body = random.choice(HTTP_POSTS)
            req = urllib.request.Request(srv.url + path, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json", "X-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                r.read()
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        stats["http_%dxx" % (code // 100)] += 1
    except Exception:
        stats["http_errors"] += 1


async def client(srv, i, seconds, stats):
    status, body = post(srv.url, "/api/join", {"name": f"stress{i}_{random.randint(0, 99999)}"})
    token = body["token"]
    end = time.time() + seconds
    while time.time() < end:
        try:
            async with websockets.connect(f"ws://127.0.0.1:{srv.port}/ws?token={token}", max_size=None) as ws:
                async def reader():
                    async for raw in ws:
                        t = json.loads(raw).get("type")
                        stats[t if t in ("init", "tick", "result", "history", "company", "chat", "notice", "chat_error")
                              else "other"] += 1
                reading = asyncio.create_task(reader())
                life = time.time() + random.uniform(2, 8)
                while time.time() < min(end, life):
                    r = random.random()
                    if r < 0.45:
                        msg = {"type": "trade", "ticker": random.choice(TICKERS), "side": random.choice(["buy", "sell", "hold", None]),
                               "pct": random.choice(PCTS), "amount": random.choice(AMOUNTS)}
                    elif r < 0.65:
                        msg = {"type": "history", "ticker": random.choice(TICKERS), "period": random.choice(PERIODS)}
                    elif r < 0.75:
                        msg = {"type": "company", "ticker": random.choice(TICKERS)}
                    elif r < 0.79:
                        msg = {"type": "chat", "text": random.choice(CHATS), "channel": random.choice(CHANNELS),
                               "share": random.choice([None, None, 1.5, "x", 0])}
                    elif r < 0.80:
                        msg = random.choice([{"type": "sync"}, {"type": "chat_history"},
                                             {"type": "chat_report", "id": random.choice([0, 1, 2, "x", None])}])
                    elif r < 0.84:
                        await asyncio.get_running_loop().run_in_executor(None, social_call, srv, token, stats)
                        msg = {"type": "history", "ticker": "GOLD", "period": "1m"}
                    elif r < 0.87:
                        msg = random.choice([[1, 2, 3], "str", 42, None, {"type": None}, {"type": ["a"]}, {}])
                    else:
                        msg = None
                    try:
                        if msg is None:
                            await ws.send(random.choice(["not json{{{", "", "x" * 5000, "\x00\xff", "null"]))
                        else:
                            await ws.send(json.dumps(msg))
                    except (ValueError, TypeError):
                        await ws.send("nan")
                    await asyncio.sleep(random.uniform(0, 0.05))
                reading.cancel()
                stats["reconnects"] += 1
        except Exception:
            stats["errors"] += 1


async def slow_client(srv, seconds):
    """Never reads its socket: the server must not let it hold up the game loop."""
    _, body = post(srv.url, "/api/join", {"name": f"slowpoke{random.randint(0, 99999)}"})
    async with websockets.connect(f"ws://127.0.0.1:{srv.port}/ws?token={body['token']}"):
        await asyncio.sleep(seconds)


async def monitor(srv, seconds, out):
    _, body = post(srv.url, "/api/join", {"name": f"monitor{random.randint(0, 99999)}"})
    ticks, sizes = [], []
    async with websockets.connect(f"ws://127.0.0.1:{srv.port}/ws?token={body['token']}", max_size=None) as ws:
        end = time.time() + seconds
        while time.time() < end:
            raw = await asyncio.wait_for(ws.recv(), 15)
            m = json.loads(raw)
            if m["type"] == "tick":
                ticks.append(time.time())
                sizes.append(len(raw))
    out["ticks_seen"] = len(ticks)
    out["max_gap"] = max((b - a for a, b in zip(ticks, ticks[1:])), default=99.0)
    out["avg_tick_bytes"] = int(sum(sizes) / len(sizes)) if sizes else 0


def run(clients=40, seconds=30, verbose=True):
    """Returns (ok, summary dict). Used by the command line and by test_stress.py."""
    from collections import Counter
    stats, mon = Counter(), {}
    with IsolatedServer() as srv:
        for bad in ["", "a", "x" * 50, "<script>"]:
            post(srv.url, "/api/join", {"name": bad})
        async def main():
            await asyncio.gather(monitor(srv, seconds, mon), slow_client(srv, seconds),
                                 *[client(srv, i, seconds, stats) for i in range(clients)])
        asyncio.run(main())
        req = urllib.request.Request(srv.url + "/api/admin/stats", headers={"X-Admin-Key": "testkey"})
        with urllib.request.urlopen(req, timeout=10) as r:
            admin = json.loads(r.read())
        req = urllib.request.Request(srv.url + "/api/admin/overview", headers={"X-Admin-Key": "testkey"})
        with urllib.request.urlopen(req, timeout=10) as r:
            perf = json.loads(r.read())["perf"]
        log = srv.log()
    bad_traces = [b for b in log.split("Traceback (most recent call last):")[1:]
                  if "engine.py" in b.split("\n\n")[0] or "server.py" in b.split("\n\n")[0]]
    summary = {"clients": clients, "seconds": seconds, **dict(stats), **mon, "drift": admin["invariant_drift"],
               "server_tick_ms": perf["tick_ms"], "server_tick_max_ms": perf["tick_max_ms"],
               "server_send_ms": perf["send_ms"], "late_ticks": perf["late_ticks"], "tracebacks_in_our_code": len(bad_traces)}
    ok = (stats["errors"] == 0 and stats["http_errors"] == 0 and stats["http_5xx"] == 0 and mon.get("max_gap", 99) < 4.0
          and perf["late_ticks"] <= max(2, seconds // 10) and not bad_traces and abs(admin["invariant_drift"]) < 1e-6)
    if verbose:
        print(json.dumps(summary, indent=2))
        print("PASS" if ok else "FAIL")
        if bad_traces:
            print(bad_traces[0][:1500])
    return ok, summary


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    secs = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    sys.exit(0 if run(n, secs)[0] else 1)
