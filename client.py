import threading
import time
from models import Result
from datetime import datetime, timezone

import requests


class Client:
    def __init__(self, url, timeout, art):
        self.url = url
        self.timeout = timeout
        self.art = art
        self.local = threading.local()

    def get(self, identifier, scenario, repetition):
        if not hasattr(self.local, "session"):
            self.local.session = requests.Session()
            self.local.session.trust_env = False
        stamp = datetime.now(timezone.utc).isoformat()
        start = time.perf_counter()
        status, error = None, ""
        try:
            with self.local.session.get(self.url, timeout=self.timeout, allow_redirects=False) as response:
                status = response.status_code
                if status != 200:
                    outcome, error = "http_status", f"HTTP {status}"
                elif self.art not in response.content.replace(b"\r\n", b"\n"):
                    outcome, error = "content", "Expected ASCII art missing."
                else:
                    outcome = "success"
        except requests.Timeout as exc:
            outcome, error = "timeout", str(exc)
        except requests.ConnectionError as exc:
            # Requests wraps a read timeout during body consumption in ConnectionError.
            from urllib3.exceptions import ReadTimeoutError
            outcome = "timeout" if any(isinstance(x, ReadTimeoutError) for x in exc.args) else "connection"
            error = str(exc)
        except Exception as exc:
            outcome, error = "other", repr(exc)
        end = time.perf_counter()
        return start, Result(identifier, scenario, repetition, stamp, (end-start)*1000, status, outcome, error)

