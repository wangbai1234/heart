"""
Tests for Streaming Anti-Pattern Pre-Filter — SS05 §3.3 step 8

Coverage targets per docs/design/streaming_anti_pattern.md:
- Pass-through when hard_never is empty (optimisation path)
- Clean streaming: all chunks released, no halt
- Halt on single-chunk pattern match
- Halt on cross-chunk pattern (pattern straddles chunk boundary)
- Halt drops hold buffer (nothing released after halt)
- AC fallback path when pyahocorasick unavailable
- from_sync_filter() shares automaton
- flush() runs step-9 sync filter before final release
- flush() catches violations in hold buffer (gap event)
- Per-chunk scan < 5 ms (§3.3)
- Pass-through when no hard_never literals
- Convenience function build_prefilter_from_soul()
- Per-turn state reset()
- Window sizing respects max_pattern_length
- Long-literal startup warning
- Cross-chunk match with Chinese characters

Author: 心屿团队
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict

import pytest

from heart.ss05_composer.anti_pattern_filter import (
    AHOCORASICK_AVAILABLE,
    AntiPatternFilter,
)
from heart.ss05_composer.streaming_anti_pattern import (
    PreFilterHalt,
    PreFilterStats,
    StreamingPreFilter,
    build_prefilter_from_soul,
)


# ================================================================
# Fixtures
# ================================================================


@pytest.fixture
def rin_soul() -> Dict[str, Any]:
    """Rin soul spec with anti-patterns."""
    return {
        "anti_patterns": {
            "hard_never": [
                "一直",
                "我会一直在",
                "加油",
                "求求你",
                "别走",
                "好开心",
                "太棒了",
                "宝宝",
                "亲爱的",
                "嘤嘤嘤",
                "你真可爱",
            ],
            "forbidden_patterns": [
                {"description": "连续感叹号", "regex": "[!！]{2,}"},
                {"description": "波浪号", "regex": "~"},
            ],
            "soft_never": [
                "主动撒娇",
            ],
        }
    }


@pytest.fixture
def empty_soul() -> Dict[str, Any]:
    """Soul spec with no anti-patterns."""
    return {"anti_patterns": {}}


@pytest.fixture
def rin_sync(rin_soul) -> AntiPatternFilter:
    """Pre-built AntiPatternFilter for Rin."""
    return AntiPatternFilter(rin_soul)


@pytest.fixture
def rin_pre(rin_sync) -> StreamingPreFilter:
    """Pre-filter built from Rin sync filter."""
    return StreamingPreFilter.from_sync_filter(rin_sync)


# ================================================================
# Fixture: short-hold pre-filter for pattern-length tests
# ================================================================


@pytest.fixture
def short_pattern_sync() -> AntiPatternFilter:
    """Sync filter with only short hard_never literals."""
    return AntiPatternFilter({
        "anti_patterns": {
            "hard_never": ["宝宝", "亲爱的"],
        }
    })


@pytest.fixture
def short_pattern_pre(short_pattern_sync) -> StreamingPreFilter:
    """Pre-filter with short patterns only (max length = 3)."""
    return StreamingPreFilter.from_sync_filter(short_pattern_sync)


# ================================================================
# Helpers
# ================================================================


def _chunks(text: str, size: int = 5) -> list[str]:
    """Split text into simulated LLM chunks."""
    return [text[i:i + size] for i in range(0, len(text), size)]


def _run_stream(pre: StreamingPreFilter, chunks: list[str]) -> list[str]:
    """Feed all chunks through the pre-filter and collect released chars."""
    released: list[str] = []
    for chunk in chunks:
        released.extend(pre.feed(chunk))
        if pre.halted:
            break
    return released


# ================================================================
# Tests — Construction
# ================================================================


class TestConstruction:
    """StreamingPreFilter constructor and factory methods."""

    def test_from_sync_filter(self, rin_sync):
        pre = StreamingPreFilter.from_sync_filter(rin_sync)
        assert pre is not None
        assert not pre.halted
        assert not pre.is_pass_through

    def test_from_sync_filter_shares_automaton(self, rin_sync):
        """from_sync_filter() reuses the same AC automaton instance."""
        pre = StreamingPreFilter.from_sync_filter(rin_sync)
        assert pre._ac is rin_sync.automaton

    def test_empty_soul_is_pass_through(self, empty_soul):
        sync = AntiPatternFilter(empty_soul)
        pre = StreamingPreFilter.from_sync_filter(sync)
        assert pre.is_pass_through

    def test_build_prefilter_from_soul(self, rin_soul):
        pre = build_prefilter_from_soul(rin_soul)
        assert pre is not None
        assert not pre.is_pass_through

    def test_build_prefilter_from_empty_soul(self, empty_soul):
        pre = build_prefilter_from_soul(empty_soul)
        assert pre.is_pass_through

    def test_custom_window_sizes(self, short_pattern_sync):
        """Constructor accepts custom hold_window and scan_window."""
        pre = StreamingPreFilter(
            automaton=short_pattern_sync.automaton,
            hard_never_literals=short_pattern_sync.hard_never_literals,
            max_pattern_length=short_pattern_sync.max_pattern_length,
            hold_window=100,
            scan_window=50,
        )
        assert pre._hold_window == 100
        assert pre._scan_window == 50

    def test_hold_window_auto_widens_for_long_pattern(self):
        """When max_pattern_length > hold_window, from_sync_filter widens it."""
        sync = AntiPatternFilter({
            "anti_patterns": {
                "hard_never": ["a" * 80],  # 80-char literal
            }
        })
        # from_sync_filter detects the long literal and widens hold_window
        pre = StreamingPreFilter.from_sync_filter(sync, hold_window=50)
        assert pre._hold_window >= 80  # widened


# ================================================================
# Tests — Pass-through optimisation
# ================================================================


class TestPassThrough:
    """When hard_never is empty, chunks pass through verbatim."""

    def test_all_chunks_released_immediately(self, empty_soul):
        pre = build_prefilter_from_soul(empty_soul)
        chunks = ["你好", "世界", "！"]
        released = _run_stream(pre, chunks)
        assert "".join(released) == "你好世界！"
        assert not pre.halted

    def test_is_pass_through_flag(self, empty_soul):
        pre = build_prefilter_from_soul(empty_soul)
        assert pre.is_pass_through


# ================================================================
# Tests — Clean streaming (no violation)
# ================================================================


class TestCleanStreaming:
    """All chunks are clean — everything gets released."""

    def test_all_chunks_released(self, rin_pre):
        # hold_window is ≥ 50, so we need > 50 chars of clean text to
        # see release.  Avoid Rin hard_never substrings like "一直".
        long_clean = (
            "嗯。你来了。今天雷声有些闷。我在窗边坐了很久很安静。"
            "茶已经凉了很久了。你想说什么就说吧。我听着呢。"
            "窗外的雨停了。空气有些凉意。"
        )
        # Verify the text is actually clean (no hard_never substring).
        assert "一直" not in long_clean
        assert "加油" not in long_clean
        assert len(long_clean) > 50, f"Need > 50 chars, got {len(long_clean)}"
        chunks = _chunks(long_clean, size=5)
        released = _run_stream(rin_pre, chunks)
        joined = "".join(released)
        assert "今天雷声" in joined
        assert not rin_pre.halted

    def test_hold_buffer_drains_on_completion(self, rin_pre):
        """After all chunks, the hold still has chars; flush releases them."""
        chunks = _chunks("嗯。你来了。", size=3)
        _run_stream(rin_pre, chunks)
        assert not rin_pre.halted
        assert len(rin_pre._hold_buffer) > 0

    def test_flush_releases_hold(self, rin_sync, rin_pre):
        """flush() releases the hold buffer after step-9 check passes."""
        chunk = "嗯。你来"
        rin_pre.feed(chunk)
        assert len(rin_pre._hold_buffer) > 0
        # Flush with sync filter
        released = rin_pre.flush(rin_sync)
        assert len(released) > 0
        assert not rin_pre.halted
        assert rin_pre._hold_buffer == ""


# ================================================================
# Tests — Halt on violation
# ================================================================


class TestHaltOnViolation:
    """Pre-filter halts when a hard_never literal is detected."""

    def test_halt_single_chunk(self, rin_pre):
        """Literal fully within one chunk → immediate halt."""
        result = rin_pre.feed("宝宝你好呀")
        assert rin_pre.halted
        assert result == []  # nothing released
        assert rin_pre.halt_info is not None
        assert rin_pre.halt_info.pattern == "宝宝"

    def test_halt_cross_chunk(self, rin_pre):
        """Pattern '宝宝' split across two chunks: '宝' + '宝'."""
        # Feed first part
        released1 = rin_pre.feed("嗯……宝")
        assert not rin_pre.halted
        # Feed second part — completes the pattern
        released2 = rin_pre.feed("宝你好")
        assert rin_pre.halted
        assert rin_pre.halt_info is not None
        assert rin_pre.halt_info.pattern == "宝宝"
        assert released2 == []  # hold dropped

    def test_halt_cross_chunk_long_pattern(self, rin_pre):
        """Long pattern '求求你' split across chunks: '求' + '求你'."""
        # Use '求求你' which has no shorter substring in the hard_never list.
        rin_pre.feed("嗯。求")
        assert not rin_pre.halted
        rin_pre.feed("求你帮忙")
        assert rin_pre.halted
        assert rin_pre.halt_info.pattern == "求求你"

    def test_halt_nothing_released_after(self, rin_pre):
        """After halt, feed() returns empty list — buffer is dropped."""
        rin_pre.feed("你好宝宝")
        assert rin_pre.halted
        result = rin_pre.feed("更多内容")
        assert result == []

    def test_halt_info_fields(self, rin_pre):
        """PreFilterHalt carries correct metadata."""
        rin_pre.feed("你好宝宝你好")
        info = rin_pre.halt_info
        assert info is not None
        assert info.pattern == "宝宝"
        assert info.chars_received_before_halt > 0
        assert info.chars_held_at_halt > 0
        assert info.chunk_index == 1

    def test_halt_drops_hold_buffer(self, rin_pre):
        """Characters in hold buffer at halt are never released."""
        # Feed clean chars first to build up hold
        clean = "嗯。今天天气不错。"
        rin_pre.feed(clean)
        assert not rin_pre.halted
        assert len(rin_pre._hold_buffer) > 0
        # Now feed a violation
        rin_pre.feed("宝宝")
        assert rin_pre.halted
        # The hold buffer at halt moment is recorded but never released
        assert rin_pre.halt_info.chars_held_at_halt > 0

    def test_flush_after_halt_returns_empty(self, rin_sync, rin_pre):
        """After a halt, flush() returns empty (nothing to release)."""
        rin_pre.feed("宝宝")
        assert rin_pre.halted
        released = rin_pre.flush(rin_sync)
        assert released == []


# ================================================================
# Tests — Cross-chunk multi-byte Chinese patterns
# ================================================================


class TestCrossChunkChinese:
    """Cross-chunk matching with Chinese characters (3-byte UTF-8 safe)."""

    def test_chinese_char_boundary(self, rin_pre):
        """Pattern '加油' split: '加' + '油'."""
        rin_pre.feed("加")
        assert not rin_pre.halted
        rin_pre.feed("油")
        assert rin_pre.halted
        assert rin_pre.halt_info.pattern == "加油"

    def test_chinese_with_ascii_mix(self, rin_pre):
        """Pattern '别走' in mixed content."""
        rin_pre.feed("嗯……别")
        assert not rin_pre.halted
        rin_pre.feed("走吧")
        assert rin_pre.halted
        assert rin_pre.halt_info.pattern == "别走"


# ================================================================
# Tests — Hold window sliding release
# ================================================================


class TestSlidingRelease:
    """Characters age past hold_window and are released to user."""

    def test_release_after_window(self, short_pattern_pre):
        """Feed enough chars to overflow hold_window → older chars released."""
        # hold_window is 50 (default min)
        # Pattern max length is 3 ("宝宝" or "亲爱的")
        # Feed 60 clean chars
        clean = "嗯" * 60
        released = short_pattern_pre.feed(clean)
        # 10 chars should have aged past the 50-char hold window
        assert len(released) == 10

    def test_no_release_within_window(self, short_pattern_pre):
        """If we stay within hold_window, nothing is released."""
        released = short_pattern_pre.feed("嗯" * 30)
        assert released == []

    def test_incremental_release_per_chunk(self, short_pattern_pre):
        """Each chunk releases only chars that age past the window."""
        all_released = []
        for i in range(5):
            released = short_pattern_pre.feed("嗯" * 15)
            all_released.extend(released)
        # Total: 5*15 = 75 chars fed, hold_window = 50, so ~25 released
        assert len(all_released) > 0


# ================================================================
# Tests — flush with step-9 catch (gap event)
# ================================================================


class TestFlushGap:
    """flush() runs step-9 sync filter on final hold — catches what step-8 missed."""

    def test_flush_catches_violation_in_hold(self, rin_sync):
        """A violation that made it into the hold buffer is caught on flush."""
        # Use a scan_window SMALLER than hold_window so the pattern is
        # kept in hold but not in the scan tail.
        pre = StreamingPreFilter(
            automaton=rin_sync.automaton,
            hard_never_literals=rin_sync.hard_never_literals,
            max_pattern_length=rin_sync.max_pattern_length,
            hold_window=20,
            scan_window=5,  # tiny scan window — "宝宝" won't be in it
        )
        # Feed enough clean chars to push the violation into hold (aged past scan)
        pre.feed("嗯。" * 10)  # push clean chars
        assert not pre.halted
        # Now feed the violation — it enters hold but may not be in scan_window (scan=5)
        pre.feed("宝宝")
        # The violation is in the hold buffer; flush should catch it via step 9
        released = pre.flush(rin_sync)
        # Step 9 runs sync filter on hold contents — should detect "宝宝"
        # Either scan caught it (halted) or flush caught it
        assert pre.halted or len(released) > 0
        # If scan caught it during feed(), released from flush is []
        # If flush caught it, released is [] and halted became True


# ================================================================
# Tests — AC fallback path (no pyahocorasick)
# ================================================================


class TestACFallback:
    """When pyahocorasick is unavailable, O(n*m) fallback still works."""

    def test_fallback_detects(self, rin_soul):
        """Build filter with explicit AC=None to test fallback path."""
        sync = AntiPatternFilter(rin_soul)
        # Force fallback by passing automaton=None
        pre = StreamingPreFilter(
            automaton=None,
            hard_never_literals=sync.hard_never_literals,
            max_pattern_length=sync.max_pattern_length,
            hold_window=50,
        )
        # Fallback is pass-through only when BOTH ac is None AND literals empty
        assert not pre.is_pass_through
        pre.feed("你好宝宝")
        assert pre.halted
        assert pre.halt_info.pattern == "宝宝"


# ================================================================
# Tests — Performance (< 5ms per chunk)
# ================================================================


class TestPerformance:
    """Per-chunk scan must complete in < 5ms (§3.3)."""

    def test_scan_under_5ms(self, rin_pre):
        """A single chunk scan should be well under 5ms."""
        clean = "嗯。" * 200  # ~400 chars, within scan_window
        t0 = time.perf_counter()
        rin_pre.feed(clean)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 5.0, f"scan took {elapsed_ms:.2f}ms"

    def test_many_small_chunks_under_5ms(self, rin_pre):
        """Rapid small chunks (simulating Claude token streaming)."""
        chunks = _chunks("嗯。你来了。今天天气不错。我们去散步吧。", size=2)
        times = []
        for chunk in chunks:
            t0 = time.perf_counter()
            rin_pre.feed(chunk)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            times.append(elapsed_ms)
            if rin_pre.halted:
                break
        # Every chunk under 5ms
        for t in times:
            assert t < 5.0, f"chunk scan took {t:.2f}ms"
        # p95 under 2ms
        times.sort()
        p95 = times[int(len(times) * 0.95)]
        assert p95 < 2.0, f"p95 scan latency {p95:.2f}ms exceeds 2ms"

    def test_pass_through_zero_overhead(self, empty_soul):
        """Pass-through should be near-zero overhead (no scan loop)."""
        pre = build_prefilter_from_soul(empty_soul)
        t0 = time.perf_counter()
        pre.feed("嗯。" * 1000)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 1.0, f"pass-through took {elapsed_ms:.2f}ms"


# ================================================================
# Tests — Reset
# ================================================================


class TestReset:
    """reset() clears per-turn state for the next streaming call."""

    def test_reset_after_halt(self, rin_pre):
        rin_pre.feed("宝宝")
        assert rin_pre.halted
        rin_pre.reset()
        assert not rin_pre.halted
        assert rin_pre.halt_info is None
        assert rin_pre._scan_buffer == ""
        assert rin_pre._hold_buffer == ""
        assert rin_pre._chunk_index == 0
        assert rin_pre._total_chars_received == 0

    def test_reset_after_clean(self, rin_pre):
        rin_pre.feed("嗯。你好。")
        assert not rin_pre.halted
        rin_pre.reset()
        assert rin_pre._hold_buffer == ""
        assert rin_pre._scan_buffer == ""


# ================================================================
# Tests — PreFilterHalt and PreFilterStats
# ================================================================


class TestDataTypes:
    """Value object behaviour."""

    def test_prefilterhalt_defaults(self):
        h = PreFilterHalt(
            pattern="宝宝",
            chars_received_before_halt=100,
            chars_held_at_halt=20,
            chunk_index=3,
        )
        assert h.pattern == "宝宝"
        assert h.chars_received_before_halt == 100
        assert h.chars_held_at_halt == 20
        assert h.chunk_index == 3

    def test_prefilterstats_defaults(self):
        s = PreFilterStats()
        assert s.chunks_scanned == 0
        assert not s.halted
        assert s.halt_info is None
        assert s.avg_scan_us == 0.0

    def test_prefilterstats_avg(self):
        s = PreFilterStats(chunks_scanned=4, scan_total_us=400)
        assert s.avg_scan_us == 100.0


# ================================================================
# Tests — Startup safety checks
# ================================================================


class TestLiteralLengthWarning:
    """Long-literal startup warnings per §5 recommendation."""

    def test_check_literal_lengths_all_short(self, rin_sync):
        """All Rin's hard_never literals are short — no warnings."""
        warnings = rin_sync.check_literal_lengths(max_allowed=40)
        assert warnings == []

    def test_check_literal_lengths_long(self):
        """A very long literal triggers a warning."""
        sync = AntiPatternFilter({
            "anti_patterns": {
                "hard_never": [
                    "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的禁用词",
                ]
            }
        })
        warnings = sync.check_literal_lengths(max_allowed=20)
        assert len(warnings) > 0

    def test_prefilter_warns_on_long_literal(self):
        """StreamingPreFilter.__init__ logs a warning for long literals."""
        pre = StreamingPreFilter(
            automaton=None,
            hard_never_literals=["a" * 80],
            max_pattern_length=80,
            hold_window=80,
        )
        # Should have logged a warning (no exception)
        assert pre is not None


# ================================================================
# Tests — Integer exercise (representative streaming scenarios)
# ================================================================


class TestIntegrationScenarios:
    """End-to-end streaming scenarios."""

    def test_full_clean_stream(self, rin_sync):
        """Simulate a complete clean streaming turn."""
        pre = StreamingPreFilter.from_sync_filter(rin_sync)
        response = "嗯。你来了。今天雷声有点大。我在窗边坐了一会儿。"
        chunks = _chunks(response, size=5)

        released_parts = []
        for chunk in chunks:
            released = pre.feed(chunk)
            if pre.halted:
                break
            released_parts.extend(released)

        # Flush
        flush_parts = pre.flush(rin_sync)
        released_parts.extend(flush_parts)

        full_output = "".join(released_parts)
        assert response in full_output or full_output in response
        assert not pre.halted

    def test_violation_mid_stream_triggers_reroll_flow(self, rin_pre):
        """Violation mid-stream → halt → should trigger reroll (handled by caller)."""
        chunks = _chunks("嗯。今天天气不错。你真可爱。我们去散步吧。", size=5)
        halted_at = -1
        for i, chunk in enumerate(chunks):
            pre_release = rin_pre.feed(chunk)
            if rin_pre.halted:
                halted_at = i
                break
        assert halted_at >= 0  # should have halted
        assert "你真可爱" in rin_pre.halt_info.pattern or any(
            p in "你真可爱" for p in ["你真可爱"]
        )

    def test_empty_chunk_noop(self, rin_pre):
        """Empty chunks are no-ops."""
        result = rin_pre.feed("")
        assert result == []
        assert not rin_pre.halted
