import pytest
from tests._stub_provider import StubProvider


def test_stub_returns_canned_response():
    p = StubProvider()
    p.respond_with("Hello, world!")
    result = p.chat([{"role": "user", "content": "hi"}])
    assert "Hello, world!" in result["text"]


def test_stub_raises_if_no_response_queued():
    p = StubProvider()
    with pytest.raises(RuntimeError, match="no canned response"):
        p.chat([{"role": "user", "content": "hi"}])


def test_stub_records_calls():
    p = StubProvider()
    p.respond_with("ok")
    p.chat([{"role": "user", "content": "first"}])
    assert len(p.calls) == 1
    assert p.calls[0]["messages"][0]["content"] == "first"
