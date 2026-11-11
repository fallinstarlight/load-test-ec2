import csv
import json
import logging
from dataclasses import asdict
from uuid import uuid4


def csv_file(path, records):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


class Report:
    def __init__(self, output):
        self.folder = output / uuid4().hex
        self.folder.mkdir(parents=True)
        self.log = logging.getLogger(self.folder.name)
        self.log.setLevel(logging.INFO)
        self.error_path = self.folder / "errors.log"
        self.summaries = []

    def save(self, rows, summary):
        stem = f"{summary['scenario']}-{summary['repetition']}"
        csv_file(self.folder / f"{stem}-requests.csv", [asdict(r) for r in rows])
        handler = logging.FileHandler(self.error_path, encoding="utf-8")
        self.log.addHandler(handler)
        try:
            self.log_errors(rows, summary, stem)
        finally:
            self.log.removeHandler(handler)
            handler.close()
        self.save_summary(summary, rows, stem)

    def log_errors(self, rows, summary, stem):
        for r in rows:
            if r.result != "success":
                self.log.error("%s %s %s %s", r.timestamp, r.id, r.result, r.error)
        if summary["stop_reason"]:
            self.log.warning("%s: %s; %s unissued", stem, summary["stop_reason"], summary["cancelled"])

    def save_summary(self, summary, rows, stem):
        assert summary["successes"] + summary["failures"] == len(rows)
        self.summaries.append(summary)
        (self.folder / f"{stem}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        csv_file(self.folder / "runs.csv", self.summaries)

