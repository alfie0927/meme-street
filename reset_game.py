"""Start the game over at Day 1, from the command line.

    python reset_game.py            asks you to type RESET, then does it
    python reset_game.py --yes      does it without asking

It does what the admin page's "Reset the game to Day 1" button does (see HOW_IT_WORKS.md, section 10): every player
goes back to the starting balance (`signup_bonus`), positions are closed at the market price, orders cancelled, and
the trade history, medals and achievements cleared. Prices, charts, accounts and passwords stay. The old save, chart file
and ledger are copied into backups/reset-<date> first.

STOP THE SERVER FIRST. A running server would write its own copy of the game over this one a few seconds later. The script
refuses to run while something answers on port 8000 (set PORT=... if you use another port; --force skips the check).
"""
import os
import socket
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)


def server_running(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def main(argv):
    port = int(os.environ.get("PORT", "8000"))
    if "--force" not in argv and server_running(port):
        print(f"Something is listening on port {port}: that looks like the game server. Stop it (Ctrl+C in its window) "
              "and run this again, or use --force if you know it is not the game.")
        return 1
    if not os.path.exists("state.json"):
        print("There is no state.json here, so there is no game to reset (a new server starts a fresh one).")
        return 1
    if "--yes" not in argv:
        print("This puts every player back to Day 1 with the starting balance and clears trade history, medals and "
              "achievements. The old game is backed up first.")
        if input("Type RESET to continue: ").strip() != "RESET":
            print("Not reset.")
            return 1
    from engine import Engine                                   # (importing it loads the game, like the server does)
    engine = Engine(ledger_path=os.path.join(BASE, "ledger.db"))
    folder = engine.reset_with_backup(os.path.join(BASE, "backups", time.strftime("reset-%Y%m%d-%H%M%S")))
    print(f"Done. It is Day {engine.season_no} again; {len(engine.players)} player(s) "
          f"are on {engine.settings.get('signup_bonus', 0):,.0f} MB. The old game is in {os.path.relpath(folder, BASE)}.")
    if engine.ledger is not None:
        engine.ledger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
