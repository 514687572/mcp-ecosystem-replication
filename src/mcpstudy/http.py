"""Polite, cached HTTP access.

All external calls in this project go through CachedSession so that:
  * responses are cached on disk (re-running a step costs nothing),
  * per-host request pacing keeps us inside rate limits,
  * 429/403/5xx responses back off instead of failing the run,
  * every payload we analyse is traceable to a stored response.
"""
import hashlib
import json
import os
import time
import urllib.parse

import requests

from . import config


class RateLimiter:
    """Enforces a minimum interval between calls to the same host."""

    def __init__(self, intervals):
        self.intervals = dict(intervals or {})
        self.default = float(self.intervals.get("default", 0.0))
        self.last_call = {}

    def wait(self, host):
        interval = float(self.intervals.get(host, self.default))
        previous = self.last_call.get(host)
        if previous is not None:
            elapsed = time.time() - previous
            if elapsed < interval:
                time.sleep(interval - elapsed)
        self.last_call[host] = time.time()


class CachedSession:
    def __init__(self, cfg=None, cache_dir=None):
        self.cfg = cfg or config.load()
        http_cfg = self.cfg.get("http", {})
        self.timeout = int(http_cfg.get("timeout_seconds", 60))
        self.max_retries = int(http_cfg.get("max_retries", 5))
        # Cap on the sleep between retries of a *connection* failure. Without a
        # cap, a flaky local proxy costs 1+2+4+8+16 = 31s per call, which
        # dominates the runtime of any large fetch.
        self.retry_backoff_cap = float(
            http_cfg.get("retry_backoff_cap_seconds", 3)
        )
        self.user_agent = http_cfg.get("user_agent", "mcp-ecosystem-study")
        self.limiter = RateLimiter(http_cfg.get("min_interval_seconds"))
        self.cache_dir = cache_dir or config.CACHE_DIR
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.session = requests.Session()
        self._apply_proxy_policy(http_cfg)
        self.stats = {"fresh": 0, "cached": 0, "errors": 0}

    def _apply_proxy_policy(self, http_cfg):
        """Honour the configured proxy policy for this session.

        On Windows, requests picks the proxy up from the Internet Settings
        registry even when no *_PROXY environment variable is set. When that
        local proxy is not running, every request fails with ProxyError, so the
        policy has to be switchable from config rather than code.
        """
        mode = str(http_cfg.get("proxy_mode", "auto")).lower()
        url = http_cfg.get("proxy_url") or ""
        if mode == "none":
            self.session.trust_env = False
            self.session.proxies = {"http": None, "https": None}
        elif mode in ("url", "fixed") and url:
            self.session.trust_env = False
            self.session.proxies = {"http": url, "https": url}
        # mode == "auto": leave requests to discover the proxy itself

    # -- cache -----------------------------------------------------------------

    def _cache_path(self, url, params):
        key = url + "?" + urllib.parse.urlencode(sorted((params or {}).items()))
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return os.path.join(self.cache_dir, digest + ".json")

    def _read_cache(self, path):
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (ValueError, OSError):
            return None

    def _write_cache(self, path, payload):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(tmp, path)

    # -- requests --------------------------------------------------------------

    def get_json(self, url, params=None, headers=None, use_cache=True,
                 allow_status=(200,)):
        """GET a JSON document, using the on-disk cache when available."""
        cache_path = self._cache_path(url, params)
        if use_cache:
            cached = self._read_cache(cache_path)
            if cached is not None:
                self.stats["cached"] += 1
                return cached

        host = urllib.parse.urlparse(url).netloc
        merged = {"User-Agent": self.user_agent, "Accept": "application/json"}
        merged.update(headers or {})

        last_error = None
        for attempt in range(self.max_retries):
            self.limiter.wait(host)
            try:
                response = self.session.get(
                    url, params=params, headers=merged, timeout=self.timeout
                )
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(2 ** attempt, self.retry_backoff_cap))
                continue

            if response.status_code in allow_status:
                payload = response.json()
                if use_cache:
                    self._write_cache(cache_path, payload)
                self.stats["fresh"] += 1
                return payload

            # Rate limiting / transient failures: back off and retry.
            if response.status_code in (403, 429) or response.status_code >= 500:
                last_error = requests.HTTPError(
                    "HTTP %s for %s" % (response.status_code, url)
                )
                time.sleep(_backoff_seconds(response, attempt))
                continue

            # Anything else (404, 400) is a real answer; record and stop.
            self.stats["errors"] += 1
            try:
                detail = response.json()
            except ValueError:
                detail = response.text[:400]
            return {"__http_error__": response.status_code, "detail": detail,
                    "url": url}

        self.stats["errors"] += 1
        raise requests.RequestException(
            "giving up on %s after %d attempts: %s"
            % (url, self.max_retries, last_error)
        )

    def get_bytes(self, url, headers=None, use_cache=True):
        """GET raw bytes (used for package archives)."""
        cache_path = self._cache_path(url, None) + ".bin"
        if use_cache and os.path.isfile(cache_path):
            self.stats["cached"] += 1
            with open(cache_path, "rb") as fh:
                return fh.read()

        host = urllib.parse.urlparse(url).netloc
        merged = {"User-Agent": self.user_agent}
        merged.update(headers or {})
        for attempt in range(self.max_retries):
            self.limiter.wait(host)
            try:
                response = self.session.get(url, headers=merged, timeout=self.timeout)
            except requests.RequestException:
                time.sleep(min(2 ** attempt, self.retry_backoff_cap))
                continue
            if response.status_code == 200:
                if use_cache:
                    with open(cache_path, "wb") as fh:
                        fh.write(response.content)
                self.stats["fresh"] += 1
                return response.content
            if response.status_code in (403, 429) or response.status_code >= 500:
                time.sleep(_backoff_seconds(response, attempt))
                continue
            raise requests.HTTPError("HTTP %s for %s" % (response.status_code, url))
        raise requests.RequestException("giving up on %s" % url)

    def summary(self):
        return dict(self.stats)


def _backoff_seconds(response, attempt):
    """Honour Retry-After / X-RateLimit-Reset when the server sends them."""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 120.0)
        except ValueError:
            pass
    reset = response.headers.get("X-RateLimit-Reset")
    if reset:
        try:
            delta = float(reset) - time.time()
            if 0 < delta <= 180:
                return delta + 1.0
        except ValueError:
            pass
    return min(2 ** (attempt + 1), 60)
