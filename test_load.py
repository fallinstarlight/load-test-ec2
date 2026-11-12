import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from client import Client, identify
from config import ALB, SUITE, Scenario, validate_url
from export import Report, csv_file
from metrics import CPU, NA, compare, load_previous, summarize
from models import Result
from scheduler import Scheduler
from visualization import plot


class Tests(unittest.TestCase):
    def test_destination(self):
        for url in ("https://localhost", "http://localhost:8000", "http://example.org",
                    "http://localhost@evil.org", "http://localhost/?x", "http://127.0.0.2",
                    "http://localhost/path", "http:// localhost/"):
            with self.assertRaises(ValueError):
                validate_url(url)
        for host in ("127.0.0.1", "localhost", ALB.upper()):
            self.assertEqual(validate_url(f"http://{host}:80/"), f"http://{host.lower()}/")
        self.assertEqual(sum(s.repetitions for s in SUITE), 10)

    @patch("client.requests.Session")
    def test_response(self, session):
        get = session.return_value.get
        reply = get.return_value.__enter__.return_value
        client = Client("http://localhost/", 2)
        for code, body, expected, server in (
                (200, "<p>Conectado a Server 1</p><pre>/^\\</pre>", "success", 1),
                (200, "Conectado a Server 2", "success", 2), (200, "Conectado a Server 3", "success", 3),
                (200, "Conectado a Server 12", "unidentified", None),
                (200, "Conectado a Server 1 Conectado a Server 2", "unidentified", None),
                (500, "Conectado a Server 2", "http_status", None), (302, "", "http_status", None)):
            reply.status_code, reply.text = code, body
            row = client.get("id", "test", 1)[1]
            self.assertEqual((row.result, row.server, row.status, row.body), (expected, server, code, body))
        for exc, expected in ((requests.Timeout(), "timeout"),
                              (requests.ConnectionError(ConnectionRefusedError(10061, "refused")), "connection_refused"),
                              (requests.ConnectionError("network"), "connection")):
            get.side_effect = exc
            self.assertEqual(client.get("id", "test", 1)[1].result, expected)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertEqual(session.return_value.mount.call_args.args[1].max_retries.total, 0)

    def test_metrics_exports_and_plots(self):
        scenario = Scenario("baseline", 22, 1, 1)
        rows = [Result(str(i), scenario.name, 1, "", i, 200, "success", "", "", 1+i%2)
                for i in range(1, 21)]
        rows.append(Result("21", scenario.name, 1, "", 99, 200, "unidentified", "", "?", None))
        data = summarize(scenario, 1, rows, 2, "interrupted")
        self.assertEqual((data["executed"], data["failures"], data["cancelled"], data["unidentified"]),
                         (21, 1, 1, 1))
        self.assertEqual((data["p95_ms"], data["successful_req_s"], data["n2_pct"], data["n3_pct"]),
                         (19, 10, 50, 0))
        self.assertEqual(summarize(scenario, 1, [], 1, "interrupt")["n1_pct"], NA)
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            report = Report(folder)
            report.save(rows, data)
            report.save([], summarize(scenario, 2, [], 1, "interrupt"))
            self.assertEqual(json.loads((report.folder/"baseline-1.json").read_text()), data)
            with (report.folder/"baseline-1-requests.csv").open(newline="") as file:
                self.assertEqual(len(list(csv.DictReader(file))), 21)
            self.assertIn("unidentified", (report.folder/"errors.log").read_text())
            legacy = folder/"legacy.csv"
            csv_file(legacy, [dict(data, ec2_max_cpu_pct=NA)])
            table = compare(load_previous([legacy]), "4.1") + compare([data], "4.2")
            plot(folder, table)
            for name in ("distribution", "p95", "throughput"):
                self.assertTrue((folder/f"{name}.png").read_bytes().startswith(b"\x89PNG"))
            self.assertFalse((folder/"cpu.png").exists())
            data.update(dict.fromkeys(CPU, 10))
            plot(folder, compare([data], "4.2"))
            self.assertTrue((folder/"cpu.png").is_file())

    @patch("client.requests.Session")
    def test_scheduler(self, session):
        reply = session.return_value.get.return_value.__enter__.return_value
        reply.status_code, reply.text = 200, "Conectado a Server 2"
        scheduler = Scheduler(Client("http://localhost/", 1))
        rows, elapsed, stop = scheduler.run(Scenario("test", 20, 5, 1), 1)
        self.assertEqual(len({r.id for r in rows}), 20)
        self.assertFalse(stop)
        reply.status_code = 500
        rows, elapsed, stop = scheduler.run(Scenario("test", 20, 1, 1), 1)
        self.assertEqual(len(rows), 5)
        self.assertTrue(stop)

