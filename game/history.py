"""Long price history (ROADMAP TA-A10): game-day candles for many game years, and one-minute candles for a few real
days, in SQLite files next to the save.

The engine keeps 500 candles per real-time timeframe in memory (30 seconds to a year) and in `state.charts.json`. That is
too short for technical work: a game year of daily candles is 365 game days. This store adds:

* **Game-day candles** (`data/history.db`): one per listing per game day, covering only the regular session (the open
  after the pre-market, the close before after-hours), like a real daily chart. Kept for `history_game_years` game years
  (10); the price model reads its daily levels (yesterday's high, low and close, the averages, the 52-week range) from
  them after a restart.
* **One-minute candles** (`data/minutes.db`): kept for `history_minute_days` real days (3), so the 1m chart reaches back
  2,000 minutes. A separate file, because it is large and changes every minute (the backups skip it).
* **Every other chart timeframe** (30 seconds to a year; since 2026-10-24), in the same file, one table each (`tf_30s`,
  `tf_5m`, ... `tf_1y`): each finished candle, kept for 2,000 of its own length, so every chart reaches back 2,000 candles
  (`engine.CHART_CANDLES`) while memory and the chart file keep only the newest 500.

Rows are [t, open, high, low, close, volume]; `t` is the candle's start in real seconds (a game day starts at
`day * 1800`). Writes are queued and flushed once per tick in one transaction, like the ledger's.
"""
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS {table} (
    tk TEXT NOT NULL,
    t INTEGER NOT NULL,
    o REAL NOT NULL, h REAL NOT NULL, l REAL NOT NULL, c REAL NOT NULL, v REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (tk, t)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS {table}_t ON {table} (t);
"""


class CandleStore:
    """One table of candles keyed by (ticker, start time), in a SQLite file that may hold other tables (one per
    timeframe). Thread-safe: the tick writes, chart requests read."""

    def __init__(self, path, table="candles"):
        self.path, self.table = path, table
        self.lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA.format(table=table))
        self.buf = []

    def add(self, tk, c):
        """Queue a finished candle [t, o, h, l, c, v]; a later candle with the same start replaces it."""
        self.buf.append((tk, int(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]),
                         float(c[5]) if len(c) > 5 else 0.0))

    def flush(self):
        with self.lock:
            if not self.buf:
                return 0
            rows, self.buf = self.buf, []
            self.db.execute("BEGIN")
            try:
                self.db.executemany(f"INSERT OR REPLACE INTO {self.table} VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
            return len(rows)

    def last(self, tk, limit, before=None):
        """The newest `limit` candles of a ticker (oldest first), optionally only those starting before `before`."""
        with self.lock:
            if before is None:
                rows = self.db.execute(f"SELECT t, o, h, l, c, v FROM {self.table} WHERE tk = ? ORDER BY t DESC LIMIT ?",
                                       (tk, int(limit))).fetchall()
            else:
                rows = self.db.execute(f"SELECT t, o, h, l, c, v FROM {self.table} WHERE tk = ? AND t < ? ORDER BY t DESC LIMIT ?",
                                       (tk, int(before), int(limit))).fetchall()
        return [list(r) for r in reversed(rows)]

    def tickers(self):
        with self.lock:
            return {r[0] for r in self.db.execute(f"SELECT DISTINCT tk FROM {self.table}")}

    def prune(self, before):
        """Drop every candle that starts before `before`."""
        with self.lock:
            return self.db.execute(f"DELETE FROM {self.table} WHERE t < ?", (int(before),)).rowcount

    def close(self):
        self.flush()
        with self.lock:
            self.db.close()


def days_from_intraday(candles, day_seconds, pre, post):
    """Game-day candles (regular session only) rebuilt from intraday candles of `day_seconds / n` length: the ones that
    start inside the regular session of their day. Used once, to give an existing game a daily history."""
    out = []
    for c in candles:
        phase = c[0] % day_seconds
        if phase < pre or phase >= day_seconds - post:
            continue
        d = int(c[0] // day_seconds) * day_seconds
        if out and out[-1][0] == d:
            o = out[-1]
            o[2], o[3], o[4] = max(o[2], c[2]), min(o[3], c[3]), c[4]
            o[5] += c[5] if len(c) > 5 else 0.0
        else:
            out.append([d, c[1], c[2], c[3], c[4], c[5] if len(c) > 5 else 0.0])
    return out
