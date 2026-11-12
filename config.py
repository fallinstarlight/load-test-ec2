import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
ALB = "ldb-42-759300108.us-east-1.elb.amazonaws.com"
HOSTS = (ALB, "localhost", "127.0.0.1")


@dataclass(frozen=True)
class Scenario:
    name: str
    requests: int
    threads: int
    repetitions: int


SUITE = (Scenario("baseline", 20, 1, 1), Scenario("scenario1", 100, 10, 3),
         Scenario("scenario2", 1000, 50, 3), Scenario("scenario3", 5000, 100, 3))


def validate_url(url):
    parts = urlsplit(url)
    host = parts.hostname
    if host not in HOSTS or url.lower() not in {
        f"http://{host}{port}{path}" for port in ("", ":80") for path in ("", "/")
    }:
        raise ValueError("Use the authorized ALB or a loopback HTTP root URL on port 80.")
    return f"http://{host}/"


def configuration():
    p = argparse.ArgumentParser(description="Lab 4.2 ALB benchmark")
    p.add_argument("--url", default=f"http://{ALB}/")
    p.add_argument("--mode", choices=("single", "suite", "fault"), default="single")
    for key in ("requests", "threads", "repetitions"):
        p.add_argument("--"+key, type=int)
    p.add_argument("--healthy", nargs="+", type=int, choices=(1, 2, 3))
    p.add_argument("--timeout", type=float, default=5)
    p.add_argument("--pause", type=float, default=10)
    p.add_argument("--output", type=Path, default=ROOT / "results")
    p.add_argument("--lab41", action="append", type=Path, default=[], help="Lab 4.1 runs.csv (repeatable)")
    a = p.parse_args()
    try:
        a.url = validate_url(a.url)
        allowed = json.loads((ROOT / "authorized.json").read_text(encoding="utf-8-sig"))
        if not isinstance(allowed, list) or urlsplit(a.url).hostname not in allowed:
            raise ValueError("Destination missing from authorized.json")
        a.output.mkdir(exist_ok=True, parents=True)
    except (ValueError, OSError) as exc:
        p.error(str(exc))
    if not math.isfinite(a.timeout) or a.timeout <= 0 or not math.isfinite(a.pause) or a.pause < 0:
        p.error("Use a finite positive timeout and a finite nonnegative pause.")
    if bool(a.healthy) != (a.mode == "fault"):
        p.error("Provide --healthy with the expected server numbers in fault mode only.")
    sizes = (a.requests, a.threads, a.repetitions)
    if a.mode != "single" and any(x is not None for x in sizes):
        p.error("Suite and fault parameters are fixed.")
    if a.mode == "suite":
        return a, SUITE
    n, t, r = (v if v is not None else d for v, d in zip(sizes, (20, 1, 1)))
    if not (1 <= n <= 5000 and 1 <= t <= 100 and r >= 1):
        p.error("Use 1–5000 requests, 1–100 threads and at least one repetition.")
    return a, [Scenario(a.mode, n, t, r)]

