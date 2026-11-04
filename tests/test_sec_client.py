"""SEC client contract: fixtures, User-Agent, cache, and the 10 request/second cap.

Nothing in this module calls the live SEC site. ``urlopen`` is either replaced
or never reached.
"""

import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from agent.sec import (
    COMPANYFACTS_URL,
    DEFAULT_CACHE_DIR,
    FILING_INDEX_URL,
    MAX_REQUESTS_PER_SECOND,
    MissingUserAgentError,
    SecClient,
    default_transport,
)
from agent.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "sec"
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
USER_AGENT = "ExampleAgent/1.0"


class FakeClock:
    """Integer nanosecond clock. ``sleep`` moves it forward and does not wait."""

    def __init__(self) -> None:
        self.ns = 0

    def now(self) -> int:
        return self.ns

    def sleep(self, nanoseconds: int) -> None:
        self.ns += nanoseconds


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("PUBLISH_FORWARD_FORECAST", raising=False)


def _forbid_network(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("the SEC client test tried to use the network")


def test_companyfacts_url_is_the_tesla_endpoint() -> None:
    assert COMPANYFACTS_URL == "https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json"
    assert FILING_INDEX_URL == "https://data.sec.gov/submissions/CIK0001318605.json"
    assert MAX_REQUESTS_PER_SECOND == 10


def test_source_has_no_email_address() -> None:
    text = (REPO_ROOT / "agent" / "sec.py").read_text(encoding="utf-8")
    assert EMAIL.search(text) is None


def test_default_cache_dir_is_gitignored() -> None:
    assert DEFAULT_CACHE_DIR == REPO_ROOT / "data" / "cache"
    result = subprocess.run(
        ["git", "check-ignore", "-q", "data/cache/companyfacts.json"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_empty_user_agent_fails_closed_without_a_request(tmp_path: Path) -> None:
    calls: list[str] = []

    def transport(url: str, user_agent: str) -> bytes:
        calls.append(url)
        return b""

    for value in ("", "   "):
        with pytest.raises(MissingUserAgentError, match="SEC_USER_AGENT is empty"):
            SecClient(value, cache_dir=tmp_path, transport=transport)
    assert calls == []


def test_settings_with_an_empty_user_agent_fail_closed(clean_env: None, tmp_path: Path) -> None:
    settings = Settings(_env_file=None)
    with pytest.raises(MissingUserAgentError):
        SecClient.from_settings(settings, cache_dir=tmp_path)


def test_companyfacts_and_filing_index_use_fixtures_not_the_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _forbid_network)
    companyfacts = (FIXTURES / "companyfacts.json").read_bytes()
    submissions = (FIXTURES / "submissions.json").read_bytes()
    seen: list[tuple[str, str]] = []

    def transport(url: str, user_agent: str) -> bytes:
        seen.append((url, user_agent))
        if url == COMPANYFACTS_URL:
            return companyfacts
        if url == FILING_INDEX_URL:
            return submissions
        raise AssertionError(f"unexpected URL {url}")

    client = SecClient(USER_AGENT, cache_dir=tmp_path, transport=transport)
    assert client.companyfacts() == companyfacts
    assert client.filing_index() == submissions
    assert client.companyfacts() == companyfacts
    assert client.filing_index() == submissions
    assert seen == [
        (COMPANYFACTS_URL, USER_AGENT),
        (FILING_INDEX_URL, USER_AGENT),
    ]


def test_a_failed_request_is_not_cached(tmp_path: Path) -> None:
    calls = {"n": 0}

    def transport(url: str, user_agent: str) -> bytes:
        calls["n"] += 1
        raise urllib.error.URLError("down")

    client = SecClient(USER_AGENT, cache_dir=tmp_path, transport=transport)
    with pytest.raises(urllib.error.URLError):
        client.get(COMPANYFACTS_URL)
    with pytest.raises(urllib.error.URLError):
        client.get(COMPANYFACTS_URL)
    assert calls["n"] == 2
    assert list(tmp_path.iterdir()) == []


def test_network_requests_stay_at_or_below_ten_per_second(tmp_path: Path) -> None:
    clock = FakeClock()
    stamps: list[int] = []

    def transport(url: str, user_agent: str) -> bytes:
        stamps.append(clock.now())
        return b"{}"

    client = SecClient(
        USER_AGENT,
        cache_dir=tmp_path,
        transport=transport,
        now_ns=clock.now,
        sleep_ns=clock.sleep,
    )
    for index in range(11):
        client.get(f"https://data.sec.gov/example/{index}")

    assert stamps[0] == 0
    for earlier, later in zip(stamps, stamps[1:], strict=False):
        assert later - earlier >= 1_000_000_000 // MAX_REQUESTS_PER_SECOND
    for start in stamps:
        in_window = [stamp for stamp in stamps if start <= stamp < start + 1_000_000_000]
        assert len(in_window) <= MAX_REQUESTS_PER_SECOND

    before = clock.now()
    client.get("https://data.sec.gov/example/0")
    assert clock.now() == before
    assert len(stamps) == 11


def test_default_transport_sends_the_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        def read(self) -> bytes:
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    def urlopen(request: urllib.request.Request, timeout: float = 30) -> Response:
        captured["header"] = request.get_header("User-agent")
        captured["url"] = request.full_url
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert default_transport(COMPANYFACTS_URL, USER_AGENT) == b"{}"
    assert captured == {"header": USER_AGENT, "url": COMPANYFACTS_URL}
