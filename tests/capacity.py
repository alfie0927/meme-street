"""Capacity test: how many players can one server process carry?

Usage:  python tests/capacity.py [clients=100] [seconds=30] [gateways=0]      (CAPACITY_STATE=<a copy of state.json> starts from a real save)

With gateways (see gateway.py) the players connect to that many gateway processes, round-robin, and the report adds up the CPU of the game server and every gateway and also shows the game server alone,
which is what limits how far the set-up can grow.

Unlike stress.py (which hammers the server with garbage), this imitates ordinary players: each one connects, reads the
once-a-second updates, makes a trade about every 15 seconds, looks at a chart about every 20 seconds and opens a
company page about every 30 seconds. The clients only count bytes (they do not parse the updates), so the machine is
spent on the server and not on the load generator.

It reports what matters for capacity: how long the server's once-a-second tick takes (the engine and the per-player
updates), how long sending takes, how many ticks came late, how many bytes each player receives per second, and the
server process's CPU and memory. The game stays healthy while the tick (plus sending) stays well under one second.
"""
import asyncio
import json
import os
import random
import sys
import time
import urllib.request

import websockets

from _helpers import IsolatedServer
from stress import post

TICKERS = ["NVXA", "CLDR", "GOLD", "MSI", "OILX", "BOND"]


def _children(pid):
    """Process ids under `pid` (on Windows the `python` launcher starts the real interpreter as a child)."""
    import subprocess
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={pid}').ProcessId"],
                             capture_output=True, text=True, timeout=20).stdout.split()
        return [int(x) for x in out]
    except Exception:
        return []


def cpu_and_memory(pid):
    """(CPU seconds used so far, resident memory in MB) of the server and whatever it started, or (None, None)."""
    pids = [pid] + (_children(pid) if sys.platform == "win32" else [])
    results = [_one_process(x) for x in pids]
    results = [r for r in results if r[0] is not None]
    if not results:
        return None, None
    return sum(r[0] for r in results), sum(r[1] for r in results)


def _one_process(pid):
    try:
        import psutil
        p = psutil.Process(pid)
        return sum(p.cpu_times()[:2]), p.memory_info().rss / 1e6
    except ImportError:
        pass
    except Exception:
        return None, None
    if sys.platform == "win32":                          # no psutil: ask Windows directly
        try:
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t), ("a", ctypes.c_size_t), ("b", ctypes.c_size_t),
                            ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]
            kernel = ctypes.windll.kernel32
            kernel.OpenProcess.restype = wintypes.HANDLE
            handle = kernel.OpenProcess(0x1000 | 0x0400, False, pid)
            ft = [wintypes.FILETIME() for _ in range(4)]
            kernel.GetProcessTimes(handle, *[ctypes.byref(x) for x in ft])
            cpu = sum(((x.dwHighDateTime << 32) | x.dwLowDateTime) * 1e-7 for x in ft[2:])
            counters = Counters()
            counters.cb = ctypes.sizeof(Counters)
            ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
            kernel.CloseHandle(handle)
            return cpu, counters.WorkingSetSize / 1e6
        except Exception:
            return None, None
    return None, None


async def player(srv, i, seconds, stats):
    _, body = await asyncio.get_running_loop().run_in_executor(None, post, srv.url, "/api/join", {"name": f"cap{i}_{random.randint(0, 99999)}"})
    try:
        port = srv.gateway_ports[i % len(srv.gateway_ports)] if srv.gateway_ports else srv.port
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws?token={body['token']}", max_size=None,
                                      ping_interval=None) as ws:
            async def reader():
                async for raw in ws:
                    stats["bytes"] += len(raw)
                    stats["msgs"] += 1
            task = asyncio.create_task(reader())
            end = time.time() + seconds
            nxt_trade, nxt_chart, nxt_company = (time.time() + random.uniform(1, 15), time.time() + random.uniform(1, 20),
                                                 time.time() + random.uniform(1, 30))
            while time.time() < end:
                now = time.time()
                if now >= nxt_trade:
                    await ws.send(json.dumps({"type": "trade", "ticker": random.choice(TICKERS),
                                              "side": random.choice(["buy", "sell"]), "pct": random.choice([0.1, 0.25, 0.5])}))
                    nxt_trade = now + random.uniform(8, 22)
                if now >= nxt_chart:
                    await ws.send(json.dumps({"type": "history", "ticker": random.choice(TICKERS),
                                              "period": random.choice(["5m", "1h", "1d"])}))
                    nxt_chart = now + random.uniform(10, 30)
                if now >= nxt_company:
                    await ws.send(json.dumps({"type": "company", "ticker": random.choice(TICKERS)}))
                    nxt_company = now + random.uniform(15, 45)
                await asyncio.sleep(0.5)
            task.cancel()
    except Exception as e:
        stats["errors"] += 1
        stats["last_error"] = repr(e)[:120]


def total_cpu_and_memory(procs):
    got = [cpu_and_memory(p.pid) for p in procs]
    got = [g for g in got if g[0] is not None]
    return (sum(g[0] for g in got), sum(g[1] for g in got)) if got else (None, None)


def run(clients=100, seconds=30, verbose=True, gateways=0):
    from collections import Counter
    stats = Counter()
    state = os.environ.get("CAPACITY_STATE") or None      # e.g. a copy of the real state.json: a full-size world
    with IsolatedServer(state_file=state, gateways=gateways) as srv:
        cpu0, _ = total_cpu_and_memory(srv.procs)
        core0, _ = cpu_and_memory(srv.proc.pid)
        t0 = time.time()

        async def main():
            await asyncio.gather(*[player(srv, i, seconds, stats) for i in range(clients)])
        asyncio.run(main())
        wall = time.time() - t0
        cpu1, mem = total_cpu_and_memory(srv.procs)
        core1, _ = cpu_and_memory(srv.proc.pid)
        req = urllib.request.Request(srv.url + "/api/admin/overview", headers={"X-Admin-Key": "testkey"})
        with urllib.request.urlopen(req, timeout=20) as r:
            perf = json.loads(r.read())["perf"]
        req = urllib.request.Request(srv.url + "/api/admin/stats", headers={"X-Admin-Key": "testkey"})
        with urllib.request.urlopen(req, timeout=20) as r:
            admin = json.loads(r.read())
    summary = {"clients": clients, "seconds": seconds, "errors": stats["errors"],
               "bytes_per_player_per_second": int(stats["bytes"] / max(1, clients) / max(1.0, wall)),
               "server_tick_ms": round(perf["tick_ms"], 1), "server_tick_max_ms": round(perf["tick_max_ms"], 1),
               "server_send_ms": round(perf["send_ms"], 1), "late_ticks": perf["late_ticks"], "ticks": perf["ticks"],
               "save_ms": round(perf.get("last_save_ms", 0.0), 1), "drift": admin["invariant_drift"]}
    if cpu0 is not None:
        summary["server_cpu_percent_of_one_core"] = round(100 * (cpu1 - cpu0) / max(1.0, wall), 1)
        summary["server_memory_mb"] = round(mem)
        if gateways:
            summary["gateways"] = gateways
            summary["game_server_alone_percent_of_one_core"] = round(100 * (core1 - core0) / max(1.0, wall), 1)
    if "last_error" in stats:
        summary["last_error"] = stats["last_error"]
    if verbose:
        print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    secs = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    gw = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    run(n, secs, gateways=gw)
