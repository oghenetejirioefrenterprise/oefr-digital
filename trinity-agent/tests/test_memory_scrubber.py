"""Tests for the memory fence scrubber."""
from __future__ import annotations

import pytest

from trinity.memory.scrubber import MemoryFenceScrubber, scrub


def test_no_fence_passes_through():
    assert scrub("hello world") == "hello world"


def test_simple_fence_removed():
    assert scrub("hi <active_memory>secret</active_memory> bye") == "hi  bye"


def test_fence_with_attributes_removed():
    assert (
        scrub('a <active_memory source="store">x</active_memory> b')
        == "a  b"
    )


def test_unclosed_fence_drops_remainder():
    assert scrub("safe <active_memory>tail never closed") == "safe "


def test_streaming_split_across_open_tag():
    s = MemoryFenceScrubber()
    out = s.scrub_chunk("hello <active_") + s.scrub_chunk("memory>secret") + s.scrub_chunk("</active_memory> bye") + s.flush()
    assert out == "hello  bye"


def test_streaming_split_across_close_tag():
    s = MemoryFenceScrubber()
    out = (
        s.scrub_chunk("a <active_memory>se")
        + s.scrub_chunk("cret</active_")
        + s.scrub_chunk("memory> b")
        + s.flush()
    )
    assert out == "a  b"


def test_streaming_partial_lt_no_tag():
    """Stray '<' that never becomes a tag must eventually flush."""
    s = MemoryFenceScrubber()
    out = s.scrub_chunk("a < b") + s.flush()
    assert out == "a < b"


def test_two_fences_in_one_string():
    text = "x <active_memory>1</active_memory> y <active_memory>2</active_memory> z"
    assert scrub(text) == "x  y  z"


def test_chunked_one_char_at_a_time():
    text = "ok <active_memory>hidden</active_memory>!"
    s = MemoryFenceScrubber()
    out = "".join(s.scrub_chunk(c) for c in text) + s.flush()
    assert out == "ok !"


def test_case_insensitive():
    assert scrub("a <Active_Memory>x</ACTIVE_MEMORY> b") == "a  b"


def test_empty_chunk_is_safe():
    s = MemoryFenceScrubber()
    assert s.scrub_chunk("") == ""
    assert s.flush() == ""


def test_streaming_unclosed_fence_then_more_text_drops_all():
    """Once a fence is open and never closed before flush, everything inside dies."""
    s = MemoryFenceScrubber()
    out = (
        s.scrub_chunk("safe ")
        + s.scrub_chunk("<active_memory>part1 ")
        + s.scrub_chunk("part2 part3")
        + s.flush()
    )
    assert out == "safe "
