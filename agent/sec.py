"""SEC client for Tesla companyfacts and the filing index.

Tests inject a transport, so they never call the live SEC site. A normal call
sends ``User-Agent`` from ``SEC_USER_AGENT`` and caches the body under
``data/cache/``. The client fails closed when that variable is empty. It does
not hardcode an email address.
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

from agent.settings import Settings

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json"
FILING_INDEX_URL = "https://data.sec.gov/submissions/CIK0001318605.json"
SUBMISSIONS_BASE_URL = "https://data.sec.gov/submissions/"
# Older filings overflow into pages the index names under filings.files.
_PAGE_NAME = re.compile(r"CIK0001318605-submissions-\d{3}\.json")

MAX_REQUESTS_PER_SECOND = 10
_MIN_INTERVAL_NS = 1_000_000_000 // MAX_REQUESTS_PER_SECOND

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"

Transport = Callable[[str, str], bytes]
NowNs = Callable[[], int]
SleepNs = Callable[[int], None]


class SecClientError(Exception):
    """The SEC client refused to send a request."""


class MissingUserAgentError(SecClientError):
    """``SEC_USER_AGENT`` is empty, so no request is sent."""


def default_transport(url: str, user_agent: str, timeout: float = 30) -> bytes:
    """GET ``url`` with the given User-Agent. Callers pass the env value in."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


class SecClient:
    """Cached, rate-limited reader for the two Tesla SEC JSON documents."""

    def __init__(
        self,
        user_agent: str,
        *,
        cache_dir: Path | None = None,
        transport: Transport | None = None,
        now_ns: NowNs | None = None,
        sleep_ns: SleepNs | None = None,
    ) -> None:
        cleaned = user_agent.strip()
        if cleaned == "":
            raise MissingUserAgentError("SEC_USER_AGENT is empty")
        self._user_agent = cleaned
        self._cache_dir = DEFAULT_CACHE_DIR if cache_dir is None else cache_dir
        self._transport = default_transport if transport is None else transport
        self._now_ns = time.monotonic_ns if now_ns is None else now_ns
        self._sleep_ns = _sleep_seconds if sleep_ns is None else sleep_ns
        self._last_request_ns: int | None = None
        self._lock = threading.Lock()

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        cache_dir: Path | None = None,
        transport: Transport | None = None,
    ) -> SecClient:
        """Build a client from ``SEC_USER_AGENT``. Empty values fail closed."""
        return cls(
            settings.sec_user_agent.get_secret_value(),
            cache_dir=cache_dir,
            transport=transport,
        )

    def companyfacts(self) -> bytes:
        """Download Tesla's companyfacts JSON, using the cache when it exists."""
        return self.get(COMPANYFACTS_URL)

    def filing_index(self) -> bytes:
        """Download Tesla's submissions filing index, using the cache when it exists."""
        return self.get(FILING_INDEX_URL)

    def filing_index_page(self, name: str) -> bytes:
        """Download one overflow page of the filing index, by the name it lists."""
        if _PAGE_NAME.fullmatch(name) is None:
            raise ValueError(f"unexpected filing index page name: {name!r}")
        return self.get(SUBMISSIONS_BASE_URL + name)

    def get(self, url: str) -> bytes:
        """Return the body for ``url``. A cache hit does not call the network."""
        path = self._cache_path(url)
        cached = _read_cache(path)
        if cached is not None:
            return cached
        with self._lock:
            cached = _read_cache(path)
            if cached is not None:
                return cached
            self._pace()
            body = self._transport(url, self._user_agent)
            _write_cache(path, body)
            return body

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self._cache_dir / digest

    def _pace(self) -> None:
        """Wait so network calls stay at or below 10 per second. Caller holds the lock."""
        now = self._now_ns()
        if self._last_request_ns is not None:
            elapsed = now - self._last_request_ns
            if elapsed < _MIN_INTERVAL_NS:
                self._sleep_ns(_MIN_INTERVAL_NS - elapsed)
                now = self._now_ns()
        self._last_request_ns = now


def _sleep_seconds(nanoseconds: int) -> None:
    time.sleep(nanoseconds / 1_000_000_000)


def _read_cache(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    return path.read_bytes()


def _write_cache(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes(body)
    temporary.replace(path)
