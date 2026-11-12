import json
import time
from datetime import datetime, timezone
from uuid import uuid4

from client import Client
from config import configuration
from export import Report, csv_file
from metrics import CPU, NA, SERVERS, compare, load_previous, summarize
from scheduler import Scheduler
from visualization import plot


def cpu_observation(server):
    while True:
        text = input(f"Server {server} peak CPU during this run (0–100%, Enter if unavailable): ").strip()
        if not text:
            return NA
        try:
            value = float(text)
            if 0 <= value <= 100:
                return value
        except ValueError:
            pass
        print("Enter a percentage from 0 to 100 or leave blank.")


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    args, scenarios = configuration()
    try:
        historical = load_previous(args.lab41)
    except (ValueError, OSError, TypeError) as exc:
        raise SystemExit(f"Cannot read Lab 4.1 input: {exc}") from exc
    scheduler = Scheduler(Client(args.url, args.timeout))
    report = None
    for s, rep in ((s, r) for s in scenarios for r in range(1, s.repetitions+1)):
        try:
            if report:
                time.sleep(args.pause)
            print(f"GET {args.url} | {s.name} run {rep}/{s.repetitions} | {s.requests} requests | "
                  f"{s.threads} threads | timeout {args.timeout}s | pause {args.pause}s | {args.output}")
            if input("Start this run? [y/N] ").strip().lower() != "y":
                break
        except (EOFError, KeyboardInterrupt):
            break
        if report is None:
            report = Report(args.output)
            print(f"Results: {report.folder}")
        run_id, start = uuid4().hex, now()
        rows, elapsed, reason = scheduler.run(s, rep, run_id)
        summary = summarize(s, rep, rows, elapsed, reason)
        summary.update(run_id=run_id, url=args.url, started_utc=start, ended_utc=now(),
                       timeout_s=args.timeout, pause_s=args.pause, repetitions=s.repetitions)
        if args.healthy:
            seen = {r.server for r in rows if r.result == "success"}
            summary.update(expected_healthy=sorted(set(args.healthy)), observed_servers=sorted(seen),
                           only_healthy_verified=(len(rows) == 20 and summary["successes"] == 20
                                                  and seen.issubset(args.healthy)))
        summary.update(dict.fromkeys(CPU, NA))
        try:
            for i, field in zip(SERVERS, CPU):
                summary[field] = cpu_observation(i)
        except (EOFError, KeyboardInterrupt):
            reason = reason or "Operator ended session after run"
            summary["stop_reason"] = reason
        report.save(rows, summary)
        print(json.dumps(summary, indent=2))
        if reason:
            break
    if report:
        table = compare(historical, "4.1") + compare(report.summaries, "4.2")
        csv_file(report.folder / "comparison.csv", table)
        plot(report.folder, table)
        print("Differences across labs are observational and do not establish causality.")


if __name__ == "__main__":
    main()
