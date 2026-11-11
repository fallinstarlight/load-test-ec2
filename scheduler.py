from collections import deque
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from time import perf_counter
from uuid import uuid4


class Scheduler:
    def __init__(self, client):
        self.client = client

    def run(self, scenario, rep):
        rows, pending = [], set()
        window = deque(maxlen=20)
        submitted = failures = streak = 0
        reason = ""
        first = None
        clock = last = perf_counter()
        batch = uuid4().hex

        def progress():
            done = len(rows)
            print(f"{scenario.name} #{rep} | {scenario.threads} threads | {done}/{scenario.requests} "
                  f"({100*done/scenario.requests:.1f}%) | OK {done-failures} | failed {failures} | "
                  f"{perf_counter()-clock:.1f}s", flush=True)

        with ThreadPoolExecutor(max_workers=scenario.threads) as pool:
            while pending or (not reason and submitted < scenario.requests):
                while not reason and len(pending) < scenario.threads and submitted < scenario.requests:
                    submitted += 1
                    pending.add(pool.submit(self.client.get, f"{batch}-{submitted}", scenario.name, rep))
                try:
                    ready, pending = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                except KeyboardInterrupt:
                    reason = "Operator interrupted the run"
                    continue
                for future in sorted(ready, key=lambda f: f.result()[0] + f.result()[1].duration_ms/1000):
                    started, row = future.result()
                    first = started if first is None else min(first, started)
                    rows.append(row)
                    failed = row.result != "success"
                    failures += failed
                    streak = streak + 1 if failed else 0
                    window.append(failed)
                    if not reason and (streak >= 5 or (len(window) == 20 and sum(window) >= 10)):
                        reason = "Persistent failures: 5 consecutive or at least 10 of the latest 20"
                if perf_counter() - last >= 1:
                    progress()
                    last = perf_counter()
        elapsed = perf_counter() - first
        progress()
        return rows, elapsed, reason
