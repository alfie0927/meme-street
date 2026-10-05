"""Let other people open your game from the internet while it runs on your own computer.

    python share.py             open a free Cloudflare "quick tunnel" to the game and print the link to send people
    python share.py --install   first time only: download Cloudflare's small tunnel program (cloudflared) into ./tools
    python share.py --port 8000 the port your game listens on (default 8000)
    python share.py --lan       only show the addresses for people on the same Wi-Fi / network (no tunnel)

This does NOT start the game (start it yourself, as usual) and it never touches your save. It only connects the game
that is already running on this computer to a public address. How it works: cloudflared makes an outgoing connection
to Cloudflare, and Cloudflare gives you an https://something.trycloudflare.com address that forwards to your computer.
Nothing needs to be opened on your router, your home address is not revealed, and the link works from phones and
other countries. The link is new every time you run this (a permanent one needs a free Cloudflare account and a
domain name). It works for as long as this window stays open, your computer is awake and the game is running.

Things to know before you share the link
  * Anyone with the link can create an account and play. The admin page is on the same address, so run the game with
    a long, secret ADMIN_KEY (or none: no key means the admin page is switched off).
  * Your computer does the work, so a few dozen friends is fine; hundreds need a real server.
  * Cloudflare quick tunnels are free and meant for testing, with no uptime promise."""
import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "tools")
SHARE_FILE = os.path.join(HERE, "share_url.txt")
URL_RE = re.compile(r"https://[a-z0-9][a-z0-9-]*\.trycloudflare\.com")
DOWNLOAD = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"


def extract_url(line):
    """The public address in a line of cloudflared's output, or None."""
    m = URL_RE.search(line)
    return m.group(0) if m else None


def game_is_running(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except OSError:
        return False


def find_cloudflared():
    local = os.path.join(TOOLS, "cloudflared.exe" if os.name == "nt" else "cloudflared")
    if os.path.exists(local):
        return local
    return shutil.which("cloudflared")


def install():
    """Download cloudflared (Windows) from Cloudflare's own release page on GitHub into ./tools."""
    if os.name != "nt":
        print("On this system install it with your package manager (for example `brew install cloudflared`),")
        print("or see https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        return 1
    os.makedirs(TOOLS, exist_ok=True)
    target = os.path.join(TOOLS, "cloudflared.exe")
    print("Downloading cloudflared from", DOWNLOAD)
    try:
        with urllib.request.urlopen(DOWNLOAD, timeout=60) as r, open(target + ".part", "wb") as out:
            shutil.copyfileobj(r, out)
    except Exception as e:
        print("The download failed:", e)
        print("You can also install it yourself:  winget install --id Cloudflare.cloudflared")
        return 1
    if os.path.getsize(target + ".part") < 5_000_000:
        os.remove(target + ".part")
        print("The downloaded file is too small to be the program; try again or use winget (see above).")
        return 1
    os.replace(target + ".part", target)
    print("Saved to", target)
    return 0


def lan_addresses():
    found = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                found.add(ip)
    except OSError:
        pass
    try:                                                    # the address used to reach the outside world
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("203.0.113.1", 9))
            found.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(found)


def show_lan(port):
    ips = lan_addresses()
    print("People on the same Wi-Fi or network can open:")
    for ip in ips:
        print(f"    http://{ip}:{port}")
    print("This only works if the game listens to the network, not just this computer. Start it with")
    print("    python launch.py --host 0.0.0.0     (or: python -m uvicorn server:app --host 0.0.0.0 --port 8000)")
    print("and allow Python through the Windows firewall when it asks.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Share the running game with people outside your home")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--install", action="store_true", help="download cloudflared into ./tools")
    ap.add_argument("--lan", action="store_true", help="show the addresses for people on the same network and stop")
    args = ap.parse_args(argv)
    if args.install:
        return install()
    if args.lan:
        show_lan(args.port)
        return 0
    if not game_is_running(args.port):
        print(f"The game is not running on port {args.port}. Start it first (for example `python launch.py`), then run this again.")
        return 1
    exe = find_cloudflared()
    if not exe:
        print("The tunnel program (cloudflared) is not installed yet. Either:")
        print("    python share.py --install            (downloads it from Cloudflare into ./tools)")
        print("    winget install --id Cloudflare.cloudflared   (the Windows package manager)")
        print("then run `python share.py` again.")
        return 1
    print("Opening the tunnel...")
    proc = subprocess.Popen([exe, "tunnel", "--url", f"http://127.0.0.1:{args.port}", "--no-autoupdate"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    found = threading.Event()
    tail = []

    def watch():
        for line in proc.stdout:
            tail.append(line.rstrip())
            del tail[:-15]
            url = extract_url(line)
            if url and not found.is_set():
                found.set()
                with open(SHARE_FILE, "w", encoding="utf-8") as fh:
                    fh.write(url + "\n")
                bar = "=" * (len(url) + 6)
                print(f"\n{bar}\n   {url}\n{bar}")
                print("Send this link to your testers. It works while this window stays open, your computer is awake and")
                print("the game is running. (Saved to share_url.txt. Press Ctrl+C to stop sharing.)\n")
    threading.Thread(target=watch, daemon=True).start()
    try:
        started = time.time()
        while proc.poll() is None:
            time.sleep(0.5)
            if not found.is_set() and time.time() - started > 60:
                print("No link after a minute. What cloudflared said:")
                print("\n".join(tail))
                break
        if proc.poll() is not None and not found.is_set():
            print("cloudflared stopped before giving a link. What it said:")
            print("\n".join(tail))
    except KeyboardInterrupt:
        pass
    finally:
        if proc.poll() is None:
            proc.terminate()
        print("Sharing stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
