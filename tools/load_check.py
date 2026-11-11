"""A load check before a launch day: many visitors opening the Daily Chart at once (docs/REACH_PLAN.md P5, roadmap B13).

  python tools/load_check.py                                   200 visitors over 20 s at http://127.0.0.1:8100
  python tools/load_check.py --visitors 500 --ramp 30 --watch 30
  python tools/load_check.py demo                              the self-check: a tiny server on this computer

Only a staging or local copy: an address that is not on this computer is refused, so this can never be pointed at the
live site. The staging copy listens on the server's own port 8100; run this there, or through the tunnel that
deploy/upload.ps1 -Staging opens. Each visitor does what a logged-out browser does: the page, its two scripts, today's
chart, a start, then the game's state once a second for --watch seconds.

Every request of the run comes from one address, and a copy lets one address start only a few visitor games a day
(the setting daily_visits_per_ip). For the run, give the copy a file content/zz_load_check.json holding
{"settings": {"daily_visits_per_ip": 100000}}, restart it, and delete the file afterwards. Without it the run still
measures the page and the chart, and says how many starts were refused.
"""
import argparse
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlsplit

LOCAL = {"127.0.0.1", "localhost", "::1"}
SLOW = 1.0                                              # (seconds: a 95th percentile above this fails the check)


def get(base, path, vid, post=False):
    """(seconds, status, body) of one request; status 0 is a connection that failed or timed out."""
    req = urllib.request.Request(base + path, data=b"" if post else None, headers={"X-Visitor": vid},
                                 method="POST" if post else "GET")
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, body = e.code, b""
    except OSError:
        status, body = 0, b""
    return time.perf_counter() - t, status, body


def visitor(base, watch, delay, rows, started):
    time.sleep(delay)
    vid = uuid.uuid4().hex

    def go(path, name=None, post=False):
        s, status, body = get(base, path, vid, post)
        rows.append((name or path, s, status))           # (list.append is safe across threads)
        return status, body
    for path in ("/daily", "/js/chart.js", "/js/daily.js", "/api/daily"):
        go(path)
    status, body = go("/api/daily/start", post=True)
    if status != 200 or b'"error"' in body:
        return                                           # (refused: a real browser stops here too)
    started.append(1)
    for i in range(watch):
        time.sleep(1)
        go(f"/api/daily/state?since={i}", "/api/daily/state")


def run(base, visitors, ramp, watch):
    """Returns (lines to print, passed)."""
    if urlsplit(base).hostname not in LOCAL:
        raise SystemExit(f"{base} is not on this computer: the load check is for a staging or local copy only")
    rows, started = [], []
    threads = [threading.Thread(target=visitor, args=(base, watch, ramp * i / visitors, rows, started)) for i in range(visitors)]
    t = time.time()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    out, ok = [f"{visitors} visitors over {ramp} s, each watching {watch} s: {len(rows)} requests in {time.time() - t:.0f} s",
               f"{'request':18}{'count':>7}{'failed':>8}{'median ms':>11}{'95% ms':>9}{'max ms':>9}"], True
    for name in dict.fromkeys(r[0] for r in rows):
        secs = sorted(r[1] for r in rows if r[0] == name)
        bad = sum(1 for r in rows if r[0] == name and r[2] != 200)
        p95 = secs[int(len(secs) * .95) - 1] if len(secs) > 1 else secs[0]
        ok = ok and not bad and p95 <= SLOW
        out.append(f"{name:18}{len(secs):>7}{bad:>8}{statistics.median(secs) * 1000:>11.0f}{p95 * 1000:>9.0f}{secs[-1] * 1000:>9.0f}")
    out.append(f"games started: {len(started)} of {visitors}" + ("" if len(started) == visitors else
               " (the rest were refused: see daily_visits_per_ip at the top of this file)"))
    out.append("PASS" if ok else f"FAIL: a request failed, or a 95th percentile is over {SLOW * 1000:.0f} ms")
    return out, ok


def demo():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(503 if self.path == "/js/chart.js" else 200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")
        do_POST = do_GET
        log_message = lambda *a: None
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    out, ok = run(f"http://127.0.0.1:{srv.server_port}", 4, 0, 2)
    srv.shutdown()
    assert not ok and out[-1].startswith("FAIL") and "games started: 4 of 4" in out[-2], out      # the 503 fails the check
    assert [x.split()[:3] for x in out[2:8]] == [["/daily", "4", "0"], ["/js/chart.js", "4", "4"], ["/js/daily.js", "4", "0"],
                                                 ["/api/daily", "4", "0"], ["/api/daily/start", "4", "0"], ["/api/daily/state", "8", "0"]], out
    try:
        run("https://memestreet.net", 1, 0, 0)
    except SystemExit:
        return print("ok")
    raise AssertionError("an address that is not on this computer must be refused")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
    else:
        a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
        a.add_argument("base", nargs="?", default="http://127.0.0.1:8100")
        a.add_argument("--visitors", type=int, default=200)
        a.add_argument("--ramp", type=float, default=20, help="seconds over which the visitors arrive")
        a.add_argument("--watch", type=int, default=20, help="seconds each visitor follows the game")
        o = a.parse_args()
        lines, passed = run(o.base.rstrip("/"), o.visitors, o.ramp, o.watch)
        print("\n".join(lines))
        sys.exit(0 if passed else 1)
