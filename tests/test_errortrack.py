"""The error tracker (errortrack.py, ROADMAP E13): errors the server logs are grouped by where they were raised and what
they were, counted and kept with their last traceback, and the admin page reads them from /api/admin/errors."""
import json
import logging
import unittest

from _helpers import IsolatedServer
import errortrack
from test_server import http


class TrackerTests(unittest.TestCase):
    def test_errors_are_grouped_and_counted(self):
        t = errortrack.ErrorTracker()
        log = logging.getLogger("test-errortrack")
        log.addHandler(t)
        log.propagate = False
        try:
            for _ in range(3):
                try:
                    {}["missing"]
                except KeyError:
                    log.exception("could not read it")
            log.error("plain error, no traceback")
            log.warning("a warning is not an error")
        finally:
            log.removeHandler(t)
        snap = t.snapshot()
        self.assertEqual(snap["total"], 4)
        kinds = {k["what"]: k for k in snap["kinds"]}
        self.assertEqual(kinds["KeyError"]["count"], 3)
        self.assertIn("test_errortrack.py", kinds["KeyError"]["where"])
        self.assertIn("KeyError", kinds["KeyError"]["trace"])
        self.assertEqual(kinds["error"]["count"], 1)

    def test_it_keeps_a_bounded_number_of_kinds_and_never_raises(self):
        t = errortrack.ErrorTracker()
        for i in range(errortrack.MAX_KINDS + 20):
            t.emit(logging.LogRecord("x", logging.ERROR, f"file{i}.py", i, "boom %s", (i,), None))
        self.assertEqual(len(t.kinds), errortrack.MAX_KINDS)
        t.emit(object())                                       # (garbage in: ignored, not raised)


class AdminTests(unittest.TestCase):
    def test_the_admin_page_reads_the_errors(self):
        with IsolatedServer() as srv:
            self.assertEqual(http(srv, "/api/admin/errors")[0], 403)
            status, text, _ = http(srv, "/api/admin/errors", headers={"X-Admin-Key": "testkey"})
            self.assertEqual(status, 200)
            d = json.loads(text)
            self.assertIn("kinds", d)
            self.assertGreater(d["started"], 0)


if __name__ == "__main__":
    unittest.main()
