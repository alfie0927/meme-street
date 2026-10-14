"""Shared helpers for the test suite. Importing this module makes the game's modules (game/) importable and runs from
the project folder. The engine finds its content packs (content/) and its save folder (data/) through game/paths.py."""
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
GAME = os.path.join(ROOT, "game")
sys.path.insert(0, GAME)
sys.path.insert(1, os.path.join(ROOT, "tools"))        # (launch.py and share.py are tested too)
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

_raw_read = engine.Engine._read


# base.json turns these down for the new price model (market_model 2); the engine tests run the old market with its news
NEW_MARKET_NEWS = ("event_mean_seconds", "issue_mean_seconds", "cross_mean_seconds", "catalyst_mean_seconds",
                   "sector_shock_mean_seconds", "moonshot_mean_seconds", "moonshot_initial", "offering_mean_seconds",
                   "rumor_prob", "rumor_delay_seconds")


def _real_read(self):
    """The content packs as they are, but with the old market's news and price model (market_model 1): what the tests
    that want "the real default settings" (test_wild's moonshots and catalysts) were written for."""
    sectors, companies, templates, settings, profiles, derived = _raw_read(self)
    settings = {k: v for k, v in settings.items() if k not in NEW_MARKET_NEWS}
    settings.setdefault("event_mean_seconds", 120)
    settings["market_model"] = 1
    settings["quest_ladder"] = False                 # quest rewards would land in the exact-cash checks (test_ladder turns it on)
    return sectors, companies, templates, settings, profiles, derived


def _flat_read(self):
    sectors, companies, templates, settings, profiles, derived = _real_read(self)
    quiet_world = {"premarket_seconds": 0, "aftermarket_seconds": 0,           # no sessions...
                   "moonshot_initial": 0, "moonshot_mean_seconds": 1e12,       # ...no moonshots...
                   "catalyst_mean_seconds": 1e12,                              # ...no catalysts...
                   "sector_shock_mean_seconds": 1e12,                          # ...and no industry shocks...
                   "chat_min_trades": 0,                                       # ...anyone may chat without trading first...
                   "require_password": False,                                  # ...may join with just a name...
                   "signup_bonus": 1000}                                        # ...and start with 1,000 MB (the game itself: 10,000)
    forced = {"signup_bonus": 1000,                                          # the tests' money is 1,000 MB a head,
              "quest_ladder": False,                                         # no quest rewards landing in exact-cash tests,
              "market_model": 1}                                         # on the old zero-drift market (a test of the new
    #                                                                          one sets e.settings["market_model"] = 2)
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


PROJECT_FOLDERS = ("game", "web", "content", "tools")      # what a copy of the game needs (plus the logo from brand/)


def copy_project(dest, settings=None):
    """Copy the game into `dest` with the same folders (game/, web/, content/, tools/, the logo in brand/), so that it
    runs there exactly as it does here but with its own empty data/. `settings` are written as one more content pack
    (content/zz_test_settings.json) that overrides the shipped settings."""
    skip = shutil.ignore_patterns("__pycache__", "*.pyc", "cloudflared*")
    for folder in PROJECT_FOLDERS:
        shutil.copytree(os.path.join(ROOT, folder), os.path.join(dest, folder), ignore=skip, dirs_exist_ok=True)
    os.makedirs(os.path.join(dest, "brand"), exist_ok=True)
    for logo in ("memestreet_logo_peaks.png", "memestreet_header_peaks.png"):
        shutil.copy(os.path.join(ROOT, "brand", logo), os.path.join(dest, "brand"))
    os.makedirs(os.path.join(dest, "data"), exist_ok=True)
    if settings:
        import json
        with open(os.path.join(dest, "content", "zz_test_settings.json"), "w", encoding="utf-8") as fh:
            json.dump({"settings": settings}, fh)
    return dest


class IsolatedServer:
    """Runs the real FastAPI app in a subprocess from a temporary copy of the project, so tests never read or
    overwrite the real save (data/state.json). Usage:  with IsolatedServer() as srv: srv.url, srv.port
    `srv.dir` is the copy, `srv.code` its game/ folder (where the server is started) and `srv.data` its data/ folder."""

    def __init__(self, admin_key="testkey", settings=None, state_file=None, gateways=None, env=None):
        # With `gateways` (or the environment variable MS_TEST_GATEWAYS) the game runs the way a big deployment does: one
        # game server process and that many gateway processes holding the websockets (see gateway.py). `url` and `port`
        # are then those of the first gateway, so a test cannot tell the difference, and running the whole suite with
        # MS_TEST_GATEWAYS=2 proves that.
        self.gateways = int(os.environ.get("MS_TEST_GATEWAYS", 0)) if gateways is None else int(gateways)
        self.state_file = state_file                  # a saved game to start from (copied in; the original is not touched)
        self.admin_key = admin_key
        self.settings = {"premarket_seconds": 0, "aftermarket_seconds": 0, "chat_min_trades": 0, "contest_join_seconds": 86400, "require_password": False, "signup_bonus": 1000, **(settings or {})}   # flat market unless asked
        self.proc = None
        self.extra_env = dict(env or {})               # e.g. {"PAYMENTS": "test"} for the shop tests

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="meme_street_test_")
        copy_project(self.dir, self.settings)      # (settings, e.g. faster earnings, become an extra content pack)
        self.code = os.path.join(self.dir, "game")
        self.data = os.path.join(self.dir, "data")
        if self.state_file:
            shutil.copy(self.state_file, os.path.join(self.data, "state.json"))
        self.core_port = free_port()
        self.core_url = f"http://127.0.0.1:{self.core_port}"
        self.procs = []
        self.log_files = []
        env = dict(os.environ, ADMIN_KEY=self.admin_key, **self.extra_env)
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
                                 "--log-level", "warning"], cwd=self.code, env=env, stdout=log_file, stderr=subprocess.STDOUT)
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
