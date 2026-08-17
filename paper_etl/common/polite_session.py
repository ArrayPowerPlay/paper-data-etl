import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading

class PoliteSession(requests.Session):
    def __init__(self, qps: float = 0.1, user_agent: str = "paper-data-etl/0.1 (Contact: test@example.com)"):
        super().__init__()
        self.qps = qps
        self.min_interval = 1.0 / qps if qps > 0 else 0
        self.last_request_time = 0.0
        self.lock = threading.Lock()
        self.headers.update({"User-Agent": user_agent})

        # Retry configuration: 3 retries, backoff factor 2 (2s, 4s, 8s)
        # Status forces: 429 (Too Many Requests), 500, 502, 503, 504
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.mount("http://", adapter)
        self.mount("https://", adapter)

    def request(self, method, url, **kwargs):
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            if time_since_last < self.min_interval:
                time.sleep(self.min_interval - time_since_last)
            self.last_request_time = time.time()

        return super().request(method, url, **kwargs)
