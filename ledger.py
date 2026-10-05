"""An append-only SQLite ledger of everything that changes anyone's money.

Why it exists: the game state is saved as a snapshot every 30 seconds, so a crash used to lose up to 30 seconds
of trades. The engine now also writes every money event (joins, deposits, withdrawals, buys, sells, shorts,
covers, margin calls, dividends, borrow fees, bankruptcy payouts, splits) here, flushed once per tick. After a
crash it loads the last snapshot and replays the events recorded after it (see Engine._replay), so nothing is
lost. The ledger is also the source for each player's trade history and CSV export.

Rows are never updated or deleted. Money columns are *deltas*: what the event added to the player's cash, to
the house reserve, to fees and to the position's cost basis, which is exactly what replay needs.
"""
import json
import os
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    t REAL NOT NULL,
    kind TEXT NOT NULL,
    token TEXT,
    name TEXT,
    ticker TEXT,
    shares REAL NOT NULL DEFAULT 0,
    price REAL NOT NULL DEFAULT 0,
    cash_delta REAL NOT NULL DEFAULT 0,
    house_delta REAL NOT NULL DEFAULT 0,
    fee REAL NOT NULL DEFAULT 0,
    cost_delta REAL NOT NULL DEFAULT 0,
    notional REAL NOT NULL DEFAULT 0,
    pnl REAL,
    extra TEXT
);
CREATE INDEX IF NOT EXISTS events_token ON events (token, seq);
CREATE INDEX IF NOT EXISTS events_pnl ON events (token, pnl);
CREATE TABLE IF NOT EXISTS curve (
    token TEXT NOT NULL,
    t REAL NOT NULL,
    equity REAL NOT NULL,
    cash REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS curve_token ON curve (token, t);
"""
COLUMNS = ("t", "kind", "token", "name", "ticker", "shares", "price", "cash_delta", "house_delta", "fee",
           "cost_delta", "notional", "pnl", "extra")
TRADE_KINDS = ("buy", "sell", "short", "cover", "margin_call")


class Ledger:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        self.buf = []
        self.curve_buf = []

    # ---------------------------------------------------------------- writing
    def add(self, **event):
        """Queue an event. It is written to disk by the next flush() (once per tick)."""
        extra = event.pop("extra", None)
        row = {c: event.get(c) for c in COLUMNS if c != "extra"}
        for key in ("shares", "price", "cash_delta", "house_delta", "fee", "cost_delta", "notional"):
            row[key] = float(row[key] or 0.0)
        row["extra"] = json.dumps(extra) if extra else None
        self.buf.append(row)

    def add_curve(self, token, t, equity, cash):
        self.curve_buf.append((token, t, equity, cash))

    def flush(self):
        """Write everything queued, in one transaction. Returns the number of rows written."""
        with self.lock:
            if not self.buf and not self.curve_buf:
                return 0
            rows, curve = self.buf, self.curve_buf
            self.buf, self.curve_buf = [], []
            sql = (f"INSERT INTO events ({', '.join(COLUMNS)}) VALUES ({', '.join(':' + c for c in COLUMNS)})")
            self.db.execute("BEGIN")
            try:
                if rows:
                    self.db.executemany(sql, rows)
                if curve:
                    self.db.executemany("INSERT INTO curve (token, t, equity, cash) VALUES (?, ?, ?, ?)", curve)
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
            return len(rows)

    # ---------------------------------------------------------------- reading
    def last_seq(self):
        with self.lock:
            row = self.db.execute("SELECT MAX(seq) FROM events").fetchone()
            return int(row[0] or 0)

    @staticmethod
    def _row(cursor, row):
        d = {c[0]: v for c, v in zip(cursor.description, row)}
        d["extra"] = json.loads(d["extra"]) if d.get("extra") else {}
        return d

    def events_after(self, seq):
        """Every event with a sequence number above `seq`, oldest first (used for crash recovery)."""
        with self.lock:
            cur = self.db.execute("SELECT * FROM events WHERE seq > ? ORDER BY seq", (seq,))
            return [self._row(cur, r) for r in cur.fetchall()]

    def history(self, token, limit=100, before=None, kinds=None):
        """A player's events, newest first, for the history page. `before` is a sequence number for paging."""
        sql = "SELECT * FROM events WHERE token = ?"
        args = [token]
        if before:
            sql += " AND seq < ?"
            args.append(int(before))
        if kinds:
            sql += f" AND kind IN ({', '.join('?' * len(kinds))})"
            args += list(kinds)
        sql += " ORDER BY seq DESC LIMIT ?"
        args.append(int(limit))
        with self.lock:
            cur = self.db.execute(sql, args)
            return [self._row(cur, r) for r in cur.fetchall()]

    def all_history(self, token):
        """Every event for a player, oldest first (CSV export)."""
        with self.lock:
            cur = self.db.execute("SELECT * FROM events WHERE token = ? ORDER BY seq", (token,))
            return [self._row(cur, r) for r in cur.fetchall()]

    def best_worst(self, token, n=5):
        """The player's biggest realised gains and losses (closing trades)."""
        with self.lock:
            cols = "seq, t, kind, ticker, shares, price, notional, fee, pnl"
            best = self.db.execute(f"SELECT {cols} FROM events WHERE token = ? AND pnl IS NOT NULL ORDER BY pnl DESC LIMIT ?",
                                   (token, n)).fetchall()
            worst = self.db.execute(f"SELECT {cols} FROM events WHERE token = ? AND pnl IS NOT NULL ORDER BY pnl ASC LIMIT ?",
                                    (token, n)).fetchall()
        names = cols.split(", ")
        return [dict(zip(names, r)) for r in best], [dict(zip(names, r)) for r in worst]

    def curve(self, token, limit=1440):
        with self.lock:
            rows = self.db.execute("SELECT t, equity, cash FROM curve WHERE token = ? ORDER BY t DESC LIMIT ?",
                                   (token, int(limit))).fetchall()
        return [list(r) for r in reversed(rows)]

    def clear(self):
        """Forget every event and curve point (a game reset; the caller has backed the file up first)."""
        with self.lock:
            self.buf, self.curve_buf = [], []
            self.db.execute("DELETE FROM events")
            self.db.execute("DELETE FROM curve")
            self.db.execute("DELETE FROM sqlite_sequence")

    def backup(self, path):
        """A consistent copy of the whole ledger (safe while the game is running)."""
        self.flush()
        with self.lock:
            dest = sqlite3.connect(path)
            try:
                self.db.backup(dest)
            finally:
                dest.close()

    def count(self):
        with self.lock:
            return int(self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def close(self):
        try:
            self.flush()
        finally:
            with self.lock:
                self.db.close()
