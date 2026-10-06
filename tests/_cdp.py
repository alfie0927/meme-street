"""A tiny Chrome DevTools Protocol driver for browser smoke tests (Edge or Chrome, headless).

No extra packages: it uses the `websockets` package that uvicorn already installs.
"""
import asyncio
import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request

import websockets

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/microsoft-edge",
]


def find_browser():
    for path in CANDIDATES:
        if os.path.exists(path):
            return path
    for name in ("msedge", "chrome", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    return None


class Page:
    def __init__(self, ws):
        self.ws, self.n, self.errors, self.waiters = ws, 0, [], {}

    async def pump(self):
        try:
            async for raw in self.ws:
                m = json.loads(raw)
                if "id" in m and m["id"] in self.waiters:
                    self.waiters.pop(m["id"]).set_result(m)
                elif m.get("method") == "Runtime.exceptionThrown":
                    d = m["params"]["exceptionDetails"]
                    self.errors.append(d.get("exception", {}).get("description") or d.get("text"))
                elif m.get("method") == "Runtime.consoleAPICalled" and m["params"]["type"] == "error":
                    self.errors.append("console.error: " + " ".join(
                        str(a.get("value", a.get("description"))) for a in m["params"]["args"]))
        except Exception:
            pass

    async def cmd(self, method, **params):
        self.n += 1
        fut = asyncio.get_event_loop().create_future()
        self.waiters[self.n] = fut
        await self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        try:
            return (await asyncio.wait_for(fut, 10)).get("result", {})
        except asyncio.TimeoutError:
            return {"timeout": True}

    async def js(self, expr):
        r = await self.cmd("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in r:
            return "JS-EXC: " + str(r["exceptionDetails"].get("exception", {}).get("description"))
        return r.get("result", {}).get("value")

    async def shot(self, path):
        r = await self.cmd("Page.captureScreenshot", format="png")
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(r["data"]))

    async def goto(self, url, wait=1.5):
        await self.cmd("Page.navigate", url=url)
        await asyncio.sleep(wait)


class _Browser(subprocess.Popen):
    """The headless browser process. Terminating it also kills its child processes (Edge and Chrome start several,
    and they keep the profile folder open) and deletes the temporary profile folder, which is over 100 MB: the tests
    used to leave one behind for every browser they started and filled the disk."""
    profile = None

    def terminate(self):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(self.pid), "/T", "/F"], capture_output=True)
        else:
            super().terminate()
        try:
            self.wait(10)
        except Exception:
            self.kill()
        for _ in range(20):                      # the browser may need a moment to let go of its files
            shutil.rmtree(self.profile, ignore_errors=True)
            if not os.path.exists(self.profile):
                break
            time.sleep(0.5)


async def open_page(width=1400, height=1000, debug_port=9333, mobile=False, scale=1):
    browser = find_browser()
    if not browser:
        raise RuntimeError("no Edge/Chrome found")
    profile = tempfile.mkdtemp(prefix="meme_street_browser_")
    proc = _Browser([browser, "--headless=new", "--disable-gpu", f"--remote-debugging-port={debug_port}",
                     f"--window-size={width},{height}", "--user-data-dir=" + profile, "about:blank"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc.profile = profile
    tab = None
    for _ in range(60):
        try:
            tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{debug_port}/json"))
            tab = next(t for t in tabs if t["type"] == "page")
            break
        except Exception:
            await asyncio.sleep(0.5)
    if tab is None:
        proc.terminate()
        raise RuntimeError("browser did not start")
    ws = await websockets.connect(tab["webSocketDebuggerUrl"], max_size=None)
    page = Page(ws)
    asyncio.create_task(page.pump())
    for domain in ("Runtime", "Page"):
        await page.cmd(domain + ".enable")
    await page.cmd("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=scale, mobile=mobile)
    if mobile:
        await page.cmd("Emulation.setTouchEmulationEnabled", enabled=True)
    return proc, page, profile
