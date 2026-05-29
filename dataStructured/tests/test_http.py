import pytest
import requests

from scripts.lib.http import get_with_retry, HttpRetryError


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class _FakeSession:
    """Returns queued responses (or raises queued exceptions) per call."""

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = 0

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls += 1
        out = self._outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return _Resp(out)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr("scripts.lib.http.time.sleep", lambda *_: None)


def test_returns_on_first_success():
    s = _FakeSession([200])
    resp = get_with_retry("http://x", session=s)
    assert resp.status_code == 200
    assert s.calls == 1


def test_retries_then_succeeds_on_5xx():
    s = _FakeSession([503, 200])
    resp = get_with_retry("http://x", session=s, retries=3)
    assert resp.status_code == 200
    assert s.calls == 2


def test_retries_on_connection_error_then_succeeds():
    s = _FakeSession([requests.ConnectionError("boom"), 200])
    resp = get_with_retry("http://x", session=s, retries=3)
    assert resp.status_code == 200
    assert s.calls == 2


def test_raises_after_exhausting_retries_on_5xx():
    s = _FakeSession([500, 500, 500])
    with pytest.raises(HttpRetryError):
        get_with_retry("http://x", session=s, retries=3)
    assert s.calls == 3


def test_does_not_retry_on_404():
    s = _FakeSession([404])
    with pytest.raises(requests.HTTPError):
        get_with_retry("http://x", session=s, retries=3)
    assert s.calls == 1
