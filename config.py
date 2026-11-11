import argparse
import json
import math
from dataclasses import dataclass
from ipaddress import IPv4Address
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Scenario:
    name: str
    requests: int
    threads: int
    repetitions: int


def validate_url(url, addresses):
    parts = urlsplit(url)
    ip = IPv4Address(parts.hostname or "")
    if (parts.scheme != "http" or parts.netloc not in (str(ip), f"{ip}:80")
            or parts.path not in ("", "/") or parts.query or parts.fragment
            or not isinstance(addresses, list) or str(ip) not in addresses):
        raise ValueError("Use the allowlisted IPv4 address and the root URL on port 80.")
    return f"http://{ip}/"


def configuration():
    p = argparse.ArgumentParser(description="Benchmark the Apache ASCII art endpoint.")
    p.add_argument("--url", required=True)
    p.add_argument("--mode", choices=["single", "suite"], default="single")
    p.add_argument("--requests", type=int)
    p.add_argument("--threads", type=int)
    p.add_argument("--repetitions", type=int)
    p.add_argument("--timeout", type=float, default=5)
    p.add_argument("--pause", type=float, default=10)
    p.add_argument("--output", type=Path, default=ROOT / "results")
    p.add_argument("--allowlist", type=Path, default=ROOT / "authorized.json")
    a = p.parse_args()
    try:
        a.url = validate_url(a.url, json.loads(a.allowlist.read_text(encoding="utf-8-sig")))
    except (ValueError, OSError) as exc:
        p.error(str(exc))
    if not math.isfinite(a.timeout) or a.timeout <= 0:
        p.error("Timeout must be finite and positive.")
    if not math.isfinite(a.pause) or a.pause < 0:
        p.error("Pause must be finite and nonnegative.")
    if a.mode == "suite":
        if any(x is not None for x in (a.requests, a.threads, a.repetitions)):
            p.error("Suite sizes and repetitions are fixed. Use single mode to customize.")
        scenarios = [Scenario("baseline", 20, 1, 1), Scenario("scenario1", 100, 10, 3),
                     Scenario("scenario2", 1000, 50, 3), Scenario("scenario3", 5000, 100, 3)]
    else:
        n, t, r = [value if value is not None else default for value, default in
                   zip((a.requests, a.threads, a.repetitions), (20, 1, 1))]
        if not (1 <= n <= 5000 and 1 <= t <= 100 and r >= 1):
            p.error("Use 1–5000 requests, 1–100 threads, and at least one repetition.")
        scenarios = [Scenario("single", n, t, r)]
    return a, scenarios
