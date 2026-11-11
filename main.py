import json
import time
from client import Client
from config import ROOT, configuration
from export import Report, csv_file
from metrics import NA, compare, summarize
from scheduler import Scheduler
from visualization import plot


def cpu_observation():
    while True:
        text = input("Peak EC2 CPU observed during this run (0–100, Enter if unavailable): ").strip()
        if not text:
            return NA
        try:
            value = float(text)
            if 0 <= value <= 100:
                return value
        except ValueError:
            pass
        print("Enter a percentage from 0 to 100 or leave blank.")


def main():
    args, scenarios = configuration()
    art = (ROOT / "art.txt").read_bytes().replace(b"\r\n", b"\n").rstrip(b"\n")
    if not art:
        raise ValueError("Empty art reference")
    print(f"GET {args.url} | timeout {args.timeout}s | pause {args.pause}s | output {args.output}")
    for s in scenarios:
        print(f"{s.name}: {s.requests} requests, up to {s.threads} concurrent, {s.repetitions} run(s)")
    if input("Start these runs? [y/N] ").strip().lower() != "y":
        return
    report = Report(args.output)
    print(f"Results: {report.folder}")
    scheduler = Scheduler(Client(args.url, args.timeout, art))
    for s, rep in ((s, r) for s in scenarios for r in range(1, s.repetitions+1)):
        if report.summaries:
            time.sleep(args.pause)
        rows, elapsed, reason = scheduler.run(s, rep)
        summary = summarize(s, rep, rows, elapsed, reason, NA)
        try:
            summary["ec2_max_cpu_pct"] = cpu_observation()
        except (EOFError, KeyboardInterrupt):
            reason = reason or "Operator ended session after run"
            summary["stop_reason"] = reason
        report.save(rows, summary)
        print(json.dumps(summary, indent=2))
        if reason:
            break
    table = compare(report.summaries)
    csv_file(report.folder / "comparison.csv", table)
    print("Scenario   Runs  Threads  Requests/run  Avg successes  Avg failures")
    for row in table:
        print(f"{row['scenario']:10} {row['runs']:4} {row['threads']:8} {row['requests_per_run']:12}"
              f" {row['avg_successes']:13.1f} {row['avg_failures']:12.1f}")
    plot(report.folder, table)


if __name__ == "__main__":
    main()

