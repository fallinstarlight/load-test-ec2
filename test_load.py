import unittest
from unittest.mock import patch
from time import perf_counter
from client import Client, Result
from config import Scenario, validate_url
from scheduler import Scheduler
from metrics import NA, summarize


class Tests(unittest.TestCase):
    def test_destination(self):
        for url in ["https://127.0.0.1", "http://127.0.0.1:8000", "http://example.org",
                    "http://127.0.0.2", "http://127.0.0.1/other"]:
            with self.assertRaises(ValueError):
                validate_url(url, ["127.0.0.1"])
        self.assertEqual(validate_url("http://127.0.0.1:80/", ["127.0.0.1"]), "http://127.0.0.1/")

    @patch("client.requests.Session")
    def test_response(self, session):
        get = session.return_value.get
        reply = get.return_value.__enter__.return_value
        client = Client("http://127.0.0.1/", 2, b"a\nb")
        for code, body, expected in [(200, b"a\r\nb", "success"), (302, b"", "http_status"),
                                     (200, b"x", "content")]:
            reply.status_code, reply.content = code, body
            self.assertEqual(client.get("id", "test", 1)[1].result, expected)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])

    def test_run(self):
        for outcome, expected in [("success", 20), ("timeout", 5)]:
            class Stub:
                def get(self, uid, scenario, rep):
                    return perf_counter(), Result(uid, scenario, rep, "", int(uid.split("-")[-1]),
                                                  None, outcome, "")
            s = Scenario("test", 20, 1, 1)
            rows, elapsed, stop = Scheduler(Stub()).run(s, 1)
            self.assertEqual(len({r.id for r in rows}), expected)
            summary = summarize(s, 1, rows, elapsed, stop, NA)
            self.assertEqual(summary["p95_ms"], 19 if outcome == "success" else NA)
            self.assertEqual(summary["cancelled"], 20-expected)
            self.assertEqual(bool(stop), outcome != "success")
