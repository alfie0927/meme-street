"""Start the game.

    python launch.py                       the game in one process on http://127.0.0.1:8000 (what `uvicorn server:app` does)
    python launch.py --gateways 4          the game server plus four gateway processes that hold the players' connections

One process is plenty for a few hundred players. With `--gateways N` the work of sending every player their once-a-second
update is spread over N more processes (gateway.py explains how), which is what a larger crowd needs. Players always
connect to the same address either way (--port, default 8000); the game server itself then listens only on this
computer (--core-port, default 8001).

    --host 127.0.0.1    who may connect: only this computer (default), or 0.0.0.0 for everyone who can reach it
    --port 8000         the address players use
    --core-port 8001    where the game server listens in gateway mode (only this computer can reach it)

Set ADMIN_KEY first if you want the admin page (it is switched off without a key).
To let people outside your home reach it, run `python share.py` as well (see HOW_IT_WORKS.md, "Sharing it")."""
import argparse
import os
import secrets
import signal
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def wait_for(url, seconds, procs):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if any(p.poll() is not None for p in procs):
            return False
        try:
            urllib.request.urlopen(url, timeout=1).read(10)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="Start Meme Street")
    ap.add_argument("--gateways", type=int, default=0, help="number of gateway processes (0 = everything in one process)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--core-port", type=int, default=8001)
    args = ap.parse_args(argv)
    os.chdir(HERE)
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))      # a stop request shuts the children down too (the `finally` below)
    py = sys.executable
    if args.gateways <= 0:
        return subprocess.call([py, "-m", "uvicorn", "server:app", "--host", args.host, "--port", str(args.port)])

    key = os.environ.get("CORE_KEY") or secrets.token_urlsafe(24)
    core_url = f"ws://127.0.0.1:{args.core_port}/internal/gateway"
    core = subprocess.Popen([py, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(args.core_port),
                             "--log-level", "warning"], env=dict(os.environ, CORE_KEY=key))
    gate = None
    try:
        if not wait_for(f"http://127.0.0.1:{args.core_port}/api/auth_mode", 90, [core]):
            print("The game server did not start (see the messages above).")
            return 1
        gate = subprocess.Popen([py, "-m", "uvicorn", "gateway:app", "--host", args.host, "--port", str(args.port),
                                 "--workers", str(args.gateways), "--log-level", "warning"],
                                env=dict(os.environ, CORE_KEY=key, CORE_URL=core_url))
        if not wait_for(f"http://127.0.0.1:{args.port}/gateway/health", 60, [core, gate]):
            print("The gateways did not start (see the messages above).")
            return 1
        print(f"Meme Street is running: {args.gateways} gateway process(es) on port {args.port}, the game on port {args.core_port}.")
        print("Press Ctrl+C to stop.")
        while core.poll() is None and gate.poll() is None:
            time.sleep(1)
        print("A part of the game stopped; shutting everything down.")
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for proc in (gate, core):                        # gateways first, then the game (which saves on the way out)
            if proc is not None and proc.poll() is None:
                proc.terminate()
        for proc in (gate, core):
            if proc is not None:
                try:
                    proc.wait(30)
                except Exception:
                    proc.kill()


if __name__ == "__main__":
    sys.exit(main())
