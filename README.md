# Apache ASCII art load test

Use Python 3.11+ in Windows PowerShell. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest -v
```

Set authorized.json to a JSON array containing your instance's current public IPv4 as a string. The initial empty array prevents accidental requests. Replace EC2_IP below with that same IP.

```powershell
.\.venv\Scripts\python.exe main.py --url http://EC2_IP/ --requests 20 --threads 1
.\.venv\Scripts\python.exe main.py --url http://EC2_IP/ --mode suite --pause 15
```

Single mode also accepts --timeout, --repetitions, --pause, --output and --allowlist. Suite mode runs 20×1 once, then 100×10, 1000×50 and 5000×100 three times each, in sequence. A thread limit controls concurrency. Every run requires the session's initial interactive confirmation. No redirects, automatic retries or environment proxies. Only HTTP GET / on an explicitly allowed IPv4 and port 80 is supported. The requests timeout applies to connect/read inactivity.

A successful response has status 200 and contains the entire multiline art in art.txt after CRLF normalization. Request timings include receiving the body. Each worker reuses its own HTTP session. One scheduler collects results. It stops issuing work on five consecutive failures or ten in the latest twenty completions, drains outstanding work, reports unissued requests as cancelled and ends the suite. The bounded set of outstanding requests can finish after the stop decision.

Run duration starts at the first GET and ends once workers finish. Failure percentage uses executed requests. Successful throughput is successes divided by elapsed seconds. P95 uses nearest rank: sort successful latencies and select position ceil(0.95 × successes), counting from 1. Empty latency samples are recorded as Not available.

Observe the instance in a second SSH window with top (aggregate CPU busy percentage = 100 minus %id). Enter the highest observed value after each run or press Enter. Short runs may end between samples. Client CPU is never substituted.

Each session writes a uniquely named directory under results/ or --output, containing per-request CSVs, individual run JSON files, runs.csv, errors.log, comparison.csv and comparison.png. The comparison uses arithmetic means and maxima over available run measurements. Its runs column includes completed or halted runs with a report. Mean run P95 is an average of per-run percentiles.
