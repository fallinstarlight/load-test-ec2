import errno
import re
import threading
import time
from datetime import datetime, timezone
from html.parser import HTMLParser

import requests
from urllib3.exceptions import ReadTimeoutError

from config import validate_url
from models import Result


class MessageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks = []

    def handle_data(self, data):
        self.chunks.append(data)


def identify(body):
    parser = MessageParser()
    parser.feed(body)
    parser.close()
    matches = re.findall(r"\bConectado a Server ([123])\b", " ".join(parser.chunks))
    return int(matches[0]) if len(matches) == 1 else None


def network_error(exc):
    pending, seen = [exc], set()
    while pending:
        item = pending.pop()
        if not isinstance(item, BaseException) or id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, (requests.Timeout, ReadTimeoutError, TimeoutError)):
            return "timeout"
        if isinstance(item, OSError) and item.errno in (errno.ECONNREFUSED, 10061):
            return "connection_refused"
        pending.extend((*item.args, item.__context__, item.__cause__, getattr(item, "reason", None)))
    return "connection"


class Client:
    def __init__(self, url, timeout):
        self.url = validate_url(url)
        self.timeout = timeout
        self.local = threading.local()

    def get(self, identifier, scenario, repetition):
        if not hasattr(self.local, "session"):
            session = requests.Session()
            session.trust_env = False
            session.mount("http://", requests.adapters.HTTPAdapter(max_retries=0))
            self.local.session = session
        stamp = datetime.now(timezone.utc).isoformat()
        start = time.perf_counter()
        status, server, body, error = None, None, "", ""
        try:
            with self.local.session.get(self.url, timeout=self.timeout, allow_redirects=False) as response:
                status, body = response.status_code, response.text
                if status != 200:
                    outcome, error = "http_status", f"HTTP {status}"
                else:
                    server = identify(body)
                    outcome = "success" if server else "unidentified"
                    if not server:
                        error = "Expected exactly one recognized server greeting."
        except (requests.Timeout, requests.ConnectionError) as exc:
            outcome, error = network_error(exc), str(exc)
        except Exception as exc:
            outcome, error = "other", repr(exc)
        return start, Result(identifier, scenario, repetition, stamp, (time.perf_counter()-start)*1000,
                             status, outcome, error, body, server)
