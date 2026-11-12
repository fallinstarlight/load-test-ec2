import csv
import math
from collections import Counter, defaultdict
from statistics import mean

NA = "Not available"
SERVERS = (1, 2, 3)
CPU = [f"server{i}_max_cpu_pct" for i in SERVERS]
BASE = ["threads", "requested", "executed", "successes", "failures", "cancelled", "failure_pct",
        "elapsed_s", "mean_ms", "min_ms", "max_ms", "p95_ms", "successful_req_s"]
DISTRIBUTION = [f"n{i}{suffix}" for i in SERVERS for suffix in ("", "_pct")]


def summarize(scenario, rep, rows, elapsed, reason):
    latencies = sorted(r.duration_ms for r in rows if r.result == "success")
    counts = Counter(r.server for r in rows if r.result == "success")
    ok, n = len(latencies), len(rows)
    data = dict(scenario=scenario.name, repetition=rep, threads=scenario.threads,
                requested=scenario.requests, executed=n, cancelled=scenario.requests-n,
                successes=ok, failures=n-ok, failure_pct=(n-ok)*100/n if n else NA,
                elapsed_s=elapsed, mean_ms=mean(latencies) if ok else NA,
                min_ms=latencies[0] if ok else NA, max_ms=latencies[-1] if ok else NA,
                p95_ms=latencies[math.ceil(.95*ok)-1] if ok else NA,
                successful_req_s=ok/elapsed if elapsed else NA, stop_reason=reason,
                unidentified=sum(r.result == "unidentified" for r in rows))
    for i in SERVERS:
        data[f"n{i}"] = counts[i]
        data[f"n{i}_pct"] = 100*counts[i]/ok if ok else NA
    return data


def load_previous(paths):
    runs = []
    for path in dict.fromkeys(p.resolve() for p in paths):
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"scenario", *BASE, "ec2_max_cpu_pct"}
            if not required.issubset(reader.fieldnames or ()):
                raise ValueError(f"{path}: expected a Lab 4.1 runs.csv")
            for raw in reader:
                row = dict(scenario=raw["scenario"])
                for key in required-{"scenario"}:
                    value = raw[key]
                    row[key] = float(value) if value not in ("", NA) else NA
                    if row[key] != NA and not math.isfinite(row[key]):
                        raise ValueError(f"{path}: invalid {key}")
                runs.append(row)
    return runs


def compare(summaries, lab):
    groups = defaultdict(list)
    for row in summaries:
        groups[(row["scenario"], row["threads"], row["requested"])].append(row)
    table = []
    for (name, threads, requests), runs in groups.items():
        entry = dict(lab=lab, scenario=name, threads=threads, requests_per_run=requests, runs=len(runs))
        for field in BASE + CPU + DISTRIBUTION + ["ec2_max_cpu_pct"]:
            values = [r[field] for r in runs if r.get(field, NA) != NA]
            entry["avg_"+field] = mean(values) if values else NA
            # A server share has no inherent adverse direction. Report both extremes.
            entry["min_"+field] = min(values) if values else NA
            entry["max_"+field] = max(values) if values else NA
            entry["observations_"+field] = len(values)
            if field not in DISTRIBUTION:
                worst = min if field in ("successes", "executed", "successful_req_s") else max
                entry["worst_"+field] = worst(values) if values else NA
        table.append(entry)
    return table
