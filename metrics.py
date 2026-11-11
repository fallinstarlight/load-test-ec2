import math
from statistics import mean

NA = "Not available"


def summarize(scenario, rep, rows, elapsed, reason, cpu):
    latencies = sorted(r.duration_ms for r in rows if r.result == "success")
    ok = len(latencies)
    n = len(rows)
    return dict(scenario=scenario.name, repetition=rep, threads=scenario.threads,
                requested=scenario.requests, executed=n, cancelled=scenario.requests-n,
                successes=ok, failures=n-ok, failure_pct=(n-ok)*100/n if n else NA,
                elapsed_s=elapsed, mean_ms=mean(latencies) if ok else NA,
                min_ms=latencies[0] if ok else NA, max_ms=latencies[-1] if ok else NA,
                p95_ms=latencies[math.ceil(.95*ok)-1] if ok else NA,
                successful_req_s=ok/elapsed if elapsed else NA, ec2_max_cpu_pct=cpu,
                stop_reason=reason)


def compare(summaries):
    groups = {}
    for row in summaries:
        groups.setdefault(row["scenario"], []).append(row)
    table = []
    for name, runs in groups.items():
        entry = dict(scenario=name, runs=len(runs), threads=runs[0]["threads"],
                     requests_per_run=runs[0]["requested"])
        for field in ("executed", "successes", "failures", "cancelled", "failure_pct", "elapsed_s",
                      "mean_ms", "min_ms", "max_ms", "p95_ms", "successful_req_s", "ec2_max_cpu_pct"):
            values = [r[field] for r in runs if r[field] != NA]
            entry["avg_"+field] = mean(values) if values else NA
            entry["max_"+field] = max(values) if values else NA
        table.append(entry)
    return table
