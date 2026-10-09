"""Shared helpers for the test suite. Importing this module makes `engine` importable from the project root
and runs from there (the engine reads its content packs from the working directory)."""
import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import engine  # noqa: E402

# The market has pre-market, regular and after-hours sessions on the real clock, which change how big the noise is.
# Tests that are not about sessions want the plain, flat market, so (in this process only) the engine reads
# `premarket_seconds` and `aftermarket_seconds` as 0 unless a test sets them itself (a test of sessions does:
# `e.settings["premarket_seconds"] = 300`). The engine's clock is also shifted to start 100 seconds into a game day
# and then runs normally. Real server tests are protected in the same way: IsolatedServer turns sessions off
# unless a test asks for them.
import types  # noqa: E402

_OFFSET = (int(time.time() // engine.MARKET_DAY_SECONDS) * engine.MARKET_DAY_SECONDS + 100) - time.time()
engine.time = types.SimpleNamespace(time=lambda: time.time() + _OFFSET)

_real_read = engine.Engine._read


def _flat_read(self):
    sectors, companies, templates, settings, profiles, derived = _real_read(self)
    quiet_world = {"premarket_seconds": 0, "aftermarket_seconds": 0,           # no sessions...
                   "moonshot_initial": 0, "moonshot_mean_seconds": 1e12,       # ...no moonshots...
                   "catalyst_mean_seconds": 1e12,                              # ...no catalysts...
                   "sector_shock_mean_seconds": 1e12,                          # ...and no industry shocks...
                   "chat_min_trades": 0,                                       # ...anyone may chat without trading first...
                   "require_password": False,                                  # ...may join with just a name...
                   "signup_bonus": 1000}                                        # ...and start with 1,000 MB (the game itself: 10,000)
    forced = {"signup_bonus": 1000}                                          # the tests' money is 1,000 MB a head
    return sectors, companies, templates, {**quiet_world, **settings, **forced}, profiles, derived


engine.Engine._read = _flat_read


def make_engine(seed=1, **settings):
    """A fresh engine with no save file, on a fake clock the tests control through `e.now`."""
    random.seed(seed)
    e = engine.Engine(state_file=None)
    e.settings.update(settings)
    e.tick(now=e.now)
    return e


def fixed_engine(seed=1, **settings):
    """An engine built as if at one fixed moment (a quarter of the way into a game day), so that two builds in one test
    are identical however long each takes. Tests that compare two runs of the same world need it: an engine starts its
    clock from the real time, and a second's difference moves where the day boundaries fall."""
    random.seed(seed)
    clock = engine.time
    engine.time = types.SimpleNamespace(time=lambda: 40 * engine.MARKET_DAY_SECONDS + 100.0)
    try:
        e = engine.Engine(state_file=None)
    finally:
        engine.time = clock
    e.settings.update(settings)
    return e


def join(e, name, extra_cash=0.0):
    p, err = e.join(name)
    assert p, err
    if extra_cash:
        e.credit(p, extra_cash)
    return p


def advance(e, seconds):
    """Run whole ticks of one second each."""
    for _ in range(int(seconds)):
        e.tick(now=e.now + 1)


def quiet(e):
    """Skip building the public state and leaderboard: they aren't needed by most tests and are slow."""
    e._public = lambda: None
    e._board = lambda: None


def drift(e):
    return e.total_tokens() - e.minted


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class IsolatedServer:
    """Runs the real FastAPI app in a subprocess from a temporary copy of the project, so tests never read or
    overwrite the real state.json. Usage:  with IsolatedServer() as srv: srv.url, srv.port"""

    FILES = ["engine.py", "newsgen.py", "memestreet_logo_peaks.png", "relations.py", "contest.py", "accounts.py", "mailer.py", "netutil.py", "wsconn.py", "pages.py", "gateway.py", "ledger.py", "social.py", "server.py", "index.html", "about.html", "admin.html", "pack_growth.json", "pack_fiction.json", "base.json", "expansion.json", "events_pack.json",
             "market_profiles.json"]

    def __init__(self, admin_key="testkey", settings=None, state_file=None, gateways=None):
        # With `gateways` (or the environment variable MS_TEST_GATEWAYS) the game runs the way a big deployment does: one
        # game server process and that many gateway processes holding the websockets (see gateway.py). `url` and `port`
        # are then those of the first gateway, so a test cannot tell the difference, and running the whole suite with
        # MS_TEST_GATEWAYS=2 proves that.
        self.gateways = int(os.environ.get("MS_TEST_GATEWAYS", 0)) if gateways is None else int(gateways)
        self.state_file = state_file                  # a saved game to start from (copied in; the original is not touched)
        self.admin_key = admin_key
        self.settings = {"premarket_seconds": 0, "aftermarket_seconds": 0, "chat_min_trades": 0, "contest_join_seconds": 86400, "require_password": False, "signup_bonus": 1000, **(settings or {})}   # flat market unless asked
        self.proc = None

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="meme_street_test_")
        for f in self.FILES:
            for folder in (ROOT, os.path.join(ROOT, "brand")):           # (the logo lives in brand/)
                if os.path.exists(os.path.join(folder, f)):
                    shutil.copy(os.path.join(folder, f), self.dir)
                    break
        if self.state_file:
            shutil.copy(self.state_file, os.path.join(self.dir, "state.json"))
        if self.settings:  # e.g. faster earnings: written as an extra content pack that overrides settings
            import json
            with open(os.path.join(self.dir, "zz_test_settings.json"), "w", encoding="utf-8") as fh:
                json.dump({"settings": self.settings}, fh)
        self.core_port = free_port()
        self.core_url = f"http://127.0.0.1:{self.core_port}"
        self.procs = []
        self.log_files = []
        env = dict(os.environ, ADMIN_KEY=self.admin_key)
        self.key = "test-core-key"
        if self.gateways:
            env["CORE_KEY"] = self.key
        self.log_path = os.path.join(self.dir, "server.log")
        self.proc = self._start("server:app", self.core_port, env, self.log_path)    # (the game itself)
        gate_ports = []
        for i in range(self.gateways):
            port = free_port()
            gate_ports.append(port)
            genv = dict(os.environ, CORE_KEY=self.key, CORE_URL=f"ws://127.0.0.1:{self.core_port}/internal/gateway")
            self._start("gateway:app", port, genv, os.path.join(self.dir, f"gateway{i}.log"))
        self.gateway_ports = gate_ports
        self.port = gate_ports[0] if gate_ports else self.core_port
        self.url = f"http://127.0.0.1:{self.port}"
        deadline = time.time() + 40
        failure = "server did not start"
        while time.time() < deadline:
            dead = [p for p in self.procs if p.poll() is not None]
            if dead:
                failure = "server exited: " + self.log()
                break
            try:
                urllib.request.urlopen(self.core_url + "/", timeout=1).read(10)
                for port in gate_ports:                  # every gateway must have found the game before the test starts
                    body = urllib.request.urlopen(f"http://127.0.0.1:{port}/gateway/health", timeout=1).read()
                    if b'"ok":true' not in body:
                        raise OSError("gateway not linked yet")
                return self
            except Exception:
                time.sleep(0.3)
        self.__exit__(None, None, None)            # a server that never came up must not leave its folder behind
        raise RuntimeError(failure)

    def _start(self, app, port, env, log_path):
        log_file = open(log_path, "wb")   # a file, not a pipe, so a chatty server can never block
        self.log_files.append(log_file)
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port),
                                 "--log-level", "warning"], cwd=self.dir, env=env, stdout=log_file, stderr=subprocess.STDOUT)
        self.procs.append(proc)
        return proc

    def __exit__(self, *exc):
        self.final_log = self.log()
        for proc in reversed(self.procs):          # (gateways first, then the game)
            proc.terminate()
            try:
                proc.wait(10)
            except Exception:
                proc.kill()
        for fh in self.log_files:
            try:
                fh.close()
            except Exception:
                pass
        for _ in range(20):                      # on Windows the server may need a moment to release its files
            shutil.rmtree(self.dir, ignore_errors=True)
            if not os.path.exists(self.dir):
                break
            time.sleep(0.5)

    def log(self):
        """Everything the server (and any gateway) printed so far (warnings and tracebacks)."""
        out = []
        try:
            for fh in self.log_files:
                fh.flush()
                with open(fh.name, "rb") as rd:
                    out.append(rd.read().decode("utf-8", "replace"))
        except Exception:
            pass
        return "\n".join(out)
