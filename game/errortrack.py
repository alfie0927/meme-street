"""A small error tracker (ROADMAP E13): every error the server logs (a failed tick, an exception in a request, a failed
save or email) is grouped by where it happened and what it was, counted, and kept with the last message and traceback,
so the admin page can show what is going wrong without anyone logging in to the server.

It is a logging handler on the root logger, so it sees what `logger.exception(...)` and uvicorn's own error log write.
At most `MAX_KINDS` kinds are kept (the oldest is dropped); nothing is written to disk (the server's log has it all).
"""
import logging
import threading
import time
import traceback

MAX_KINDS = 100


class ErrorTracker(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.kinds = {}                   # (where, what) -> {"count", "first", "last", "message", "trace", "logger"}
        self.total = 0
        self.lock_ = threading.Lock()

    def emit(self, record):
        try:
            what = record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else "error"
            where = f"{record.pathname.replace(chr(92), '/').split('/')[-1]}:{record.lineno}"
            if record.exc_info and record.exc_info[2]:
                tb = traceback.extract_tb(record.exc_info[2])
                if tb:                                        # where it was raised, not where it was logged
                    where = f"{tb[-1].filename.replace(chr(92), '/').split('/')[-1]}:{tb[-1].lineno}"
            message = record.getMessage()
            if record.exc_info and record.exc_info[1] is not None:
                message += f": {record.exc_info[1]}"
            trace = "".join(traceback.format_exception(*record.exc_info))[-4000:] if record.exc_info else ""
            now = time.time()
            with self.lock_:
                self.total += 1
                key = (where, what)
                k = self.kinds.get(key)
                if k is None:
                    if len(self.kinds) >= MAX_KINDS:
                        del self.kinds[min(self.kinds, key=lambda x: self.kinds[x]["last"])]
                    k = self.kinds[key] = {"count": 0, "first": now, "where": where, "what": what}
                k.update(count=k["count"] + 1, last=now, message=message[:500], trace=trace, logger=record.name)
        except Exception:                                     # (an error tracker must never raise)
            pass

    def snapshot(self, since=None):
        """Every kind of error, the most recent first; `since` (a time) counts only those seen after it."""
        with self.lock_:
            rows = [dict(v) for v in self.kinds.values() if since is None or v["last"] >= since]
        rows.sort(key=lambda r: -r["last"])
        return {"total": self.total, "kinds": rows}


tracker = ErrorTracker()


def install():
    """Attach the tracker to the root logger (once)."""
    root = logging.getLogger()
    if tracker not in root.handlers:
        root.addHandler(tracker)
    return tracker
