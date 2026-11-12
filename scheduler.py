import signal
from collections import Counter, deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from time import perf_counter
from uuid import uuid4


class Scheduler:
    def __init__(self, client):
        self.client = client

    def run(self, scenario, rep, batch=None):
        batch = batch or uuid4().hex
        rows, pending = [], set()
        counts = Counter()
        window = deque(maxlen=20)
        submitted = streak = failures = 0
        reason = ""
        clock = last = perf_counter()
        first = None

        def interrupt(*_):
            nonlocal reason
            reason = "Operator interrupted the run"

        def progress():
            done = len(rows)
            print(f"\r{self.client.url} {scenario.name} #{rep} | {scenario.threads} threads | "
                  f"{done}/{scenario.requests} ({100*done/scenario.requests:.1f}%) | "
                  f"OK {done-failures} failed {failures} | N1/N2/N3 "
                  f"{counts[1]}/{counts[2]}/{counts[3]} | {perf_counter()-clock:.1f}s",
                  end="", flush=True)

        previous = signal.signal(signal.SIGINT, interrupt)
        try:
            with ThreadPoolExecutor(max_workers=scenario.threads) as pool:
                while pending or (not reason and submitted < scenario.requests):
                    while not reason and len(pending) < scenario.threads and submitted < scenario.requests:
                        submitted += 1
                        pending.add(pool.submit(self.client.get, f"{batch}-{submitted}", scenario.name, rep))
                    ready, pending = wait(pending, timeout=.5, return_when=FIRST_COMPLETED)
                    for started, row in sorted((f.result() for f in ready),
                                               key=lambda pair: pair[0]+pair[1].duration_ms/1000):
                        first = started if first is None else min(first, started)
                        rows.append(row)
                        failed = row.result != "success"
                        if not failed:
                            counts[row.server] += 1
                        failures += failed
                        streak = streak + 1 if failed else 0
                        window.append(failed)
                        if not reason and (streak >= 5 or (len(window) == 20 and sum(window) >= 10)):
                            reason = "Persistent failures: 5 consecutive or at least 10 of the latest 20"
                    if perf_counter()-last >= 1:
                        progress()
                        last = perf_counter()
            elapsed = perf_counter()-(clock if first is None else first)
            progress()
            print()
            return rows, elapsed, reason
        finally:
            signal.signal(signal.SIGINT, previous)

