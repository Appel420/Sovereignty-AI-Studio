"""Tests for the new helpers, error handler, error listener, and model selector.

Covers:
- src.utils.error_handler: SovereignError hierarchy, retry helpers, ErrorHandler
- src.utils.helpers: dict/hash/timing/collection/string helpers
- watchers.error_listener: ErrorListener subscription and aggregation
- ai_core.model_selector: ModelCategory, generate_model_map, build_judge validation
"""

from __future__ import annotations

import asyncio
import time

import pytest

# ---------------------------------------------------------------------------
# src.utils.error_handler
# ---------------------------------------------------------------------------

from src.utils.error_handler import (
    AIProviderError,
    AuthError,
    ErrorCategory,
    ErrorHandler,
    MemoryError,
    NetworkError,
    SovereignError,
    TokenError,
    ValidationError,
    retry_async,
    retry_sync,
)


class TestSovereignError:
    def test_base_category_default(self):
        err = SovereignError("oops")
        assert err.category == ErrorCategory.UNKNOWN
        assert str(err) == "oops"

    def test_as_dict_structure(self):
        err = NetworkError("timeout", context={"url": "http://example.com"})
        d = err.as_dict()
        assert d["category"] == ErrorCategory.NETWORK.value
        assert d["context"]["url"] == "http://example.com"
        assert "timestamp" in d

    def test_subclass_categories(self):
        assert AuthError("x").category == ErrorCategory.AUTH
        assert AIProviderError("x").category == ErrorCategory.AI_PROVIDER
        assert MemoryError("x").category == ErrorCategory.MEMORY
        assert TokenError("x").category == ErrorCategory.TOKEN
        assert ValidationError("x").category == ErrorCategory.VALIDATION

    def test_original_stored(self):
        cause = ValueError("root cause")
        err = NetworkError("wrap", original=cause)
        assert err.original is cause
        assert err.as_dict()["original"] == str(cause)


class TestRetryAsync:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        calls = []

        async def good():
            calls.append(1)
            return "ok"

        result = await retry_async(good, retries=3)
        assert result == "ok"
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_retries_and_succeeds(self):
        calls = []

        async def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ConnectionError("not yet")
            return "done"

        result = await retry_async(flaky, retries=4, delay=0.01)
        assert result == "done"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_raises_after_exhaustion(self):
        async def always_fail():
            raise RuntimeError("always bad")

        with pytest.raises(RuntimeError, match="always bad"):
            await retry_async(always_fail, retries=2, delay=0.01)

    @pytest.mark.asyncio
    async def test_only_catches_specified_exceptions(self):
        async def raises_value_error():
            raise ValueError("not covered")

        with pytest.raises(ValueError):
            await retry_async(
                raises_value_error,
                retries=3,
                delay=0.01,
                exceptions=(ConnectionError,),
            )


class TestRetrySync:
    def test_succeeds_immediately(self):
        result = retry_sync(lambda: "hello", retries=3, delay=0.001)
        assert result == "hello"

    def test_retries_sync(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise IOError("not ready")
            return "ready"

        result = retry_sync(flaky, retries=3, delay=0.001)
        assert result == "ready"
        assert len(calls) == 2

    def test_exhausts_and_raises(self):
        def bad():
            raise OSError("disk full")

        with pytest.raises(OSError):
            retry_sync(bad, retries=2, delay=0.001)


class TestErrorHandler:
    def test_handle_plain_exception(self):
        handler = ErrorHandler()
        d = handler.handle(RuntimeError("boom"), context={"module": "test"})
        assert d["category"] == ErrorCategory.UNKNOWN.value
        assert "boom" in d["error"]
        assert d["context"]["module"] == "test"

    def test_handle_sovereign_error(self):
        handler = ErrorHandler()
        err = ValidationError("bad input")
        d = handler.handle(err)
        assert d["category"] == ErrorCategory.VALIDATION.value

    def test_recent_errors_bounded(self):
        handler = ErrorHandler()
        for i in range(10):
            handler.handle(RuntimeError(f"err {i}"))
        recent = handler.recent_errors(limit=5)
        assert len(recent) == 5

    def test_reraise_flag(self):
        handler = ErrorHandler()
        with pytest.raises(NetworkError):
            handler.handle(NetworkError("net down"), reraise=True)

    def test_publishes_to_bus(self):
        published = []

        class FakeBus:
            def publish_sync(self, event_type, payload):
                published.append((event_type, payload))

        handler = ErrorHandler(bus=FakeBus())
        handler.handle(TokenError("quota exceeded"))
        assert len(published) == 1
        assert published[0][0] == "error"

    def test_clear_resets_history(self):
        handler = ErrorHandler()
        handler.handle(RuntimeError("x"))
        handler.clear()
        assert handler.recent_errors() == []


# ---------------------------------------------------------------------------
# src.utils.helpers
# ---------------------------------------------------------------------------

from src.utils.helpers import (
    Timer,
    chunk,
    coerce_bool,
    first,
    flatten,
    merge_dicts,
    omit,
    pick,
    sanitize_key,
    sha256_hex,
    sha3_512_hex,
    truncate,
    unique,
)


class TestDictHelpers:
    def test_pick(self):
        assert pick({"a": 1, "b": 2, "c": 3}, ["a", "c"]) == {"a": 1, "c": 3}

    def test_pick_missing_keys_ignored(self):
        assert pick({"a": 1}, ["a", "z"]) == {"a": 1}

    def test_omit(self):
        assert omit({"a": 1, "b": 2, "c": 3}, ["b"]) == {"a": 1, "c": 3}

    def test_merge_dicts_deep(self):
        a = {"x": {"y": 1, "z": 2}}
        b = {"x": {"z": 99, "w": 3}}
        result = merge_dicts(a, b)
        assert result == {"x": {"y": 1, "z": 99, "w": 3}}

    def test_merge_dicts_later_wins(self):
        result = merge_dicts({"a": 1}, {"a": 2})
        assert result["a"] == 2


class TestHashHelpers:
    def test_sha3_512_is_128_hex_chars(self):
        digest = sha3_512_hex("test")
        assert len(digest) == 128
        assert all(c in "0123456789abcdef" for c in digest)

    def test_sha256_is_64_hex_chars(self):
        digest = sha256_hex("test")
        assert len(digest) == 64

    def test_sha3_512_deterministic(self):
        assert sha3_512_hex("hello") == sha3_512_hex("hello")

    def test_sha3_512_differs_from_sha256(self):
        assert sha3_512_hex("data") != sha256_hex("data")


class TestTimer:
    def test_elapsed_ms_positive(self):
        with Timer("test") as t:
            time.sleep(0.01)
        assert t.elapsed_ms >= 5.0  # at least 5ms

    def test_name_attribute(self):
        t = Timer("my_op")
        assert t.name == "my_op"


class TestCollectionHelpers:
    def test_chunk_even(self):
        assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    def test_chunk_uneven(self):
        assert chunk([1, 2, 3], 2) == [[1, 2], [3]]

    def test_chunk_invalid_size(self):
        with pytest.raises(ValueError):
            chunk([1, 2], 0)

    def test_flatten(self):
        assert flatten([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]

    def test_first_returns_first(self):
        assert first([10, 20, 30]) == 10

    def test_first_empty_returns_default(self):
        assert first([], default="x") == "x"

    def test_unique_preserves_order(self):
        assert unique([3, 1, 2, 1, 3]) == [3, 1, 2]


class TestStringHelpers:
    def test_truncate_short(self):
        assert truncate("hello", 10) == "hello"

    def test_truncate_long(self):
        result = truncate("hello world", 8)
        assert result.endswith("…")
        assert len(result) == 8

    def test_sanitize_key(self):
        assert sanitize_key("  My-Key Name  ") == "my_key_name"

    def test_coerce_bool_true_values(self):
        for v in [True, "true", "TRUE", "1", "yes", "Yes", "on", "ON"]:
            assert coerce_bool(v) is True

    def test_coerce_bool_false_values(self):
        for v in [False, "false", "0", "no", "off", "nope", None, ""]:
            assert coerce_bool(v) is False


# ---------------------------------------------------------------------------
# watchers.error_listener
# ---------------------------------------------------------------------------

from watchers.error_listener import ErrorListener
from watchers.event_bus import EventBus


class TestErrorListener:
    def setup_method(self):
        self.bus = EventBus()
        self.listener = ErrorListener(self.bus, alert_threshold=3)

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        await self.listener.start()
        assert self.listener._running is True
        await self.listener.stop()
        assert self.listener._running is False

    @pytest.mark.asyncio
    async def test_counts_errors_by_category(self):
        await self.listener.start()
        for _ in range(2):
            await self.bus.publish("error", {"error": "net", "category": "network"})
        await self.bus.publish("error", {"error": "auth", "category": "auth"})
        assert self.listener.counts()["network"] == 2
        assert self.listener.counts()["auth"] == 1
        await self.listener.stop()

    @pytest.mark.asyncio
    async def test_recent_returns_limited_list(self):
        await self.listener.start()
        for i in range(5):
            await self.bus.publish("error", {"error": f"e{i}", "category": "internal"})
        recent = self.listener.recent(limit=3)
        assert len(recent) == 3
        await self.listener.stop()

    @pytest.mark.asyncio
    async def test_alert_callback_fires_at_threshold(self):
        alerts = []

        def on_alert(category, count, msg):
            alerts.append((category, count))

        self.listener.add_alert_callback(on_alert)
        await self.listener.start()
        for _ in range(4):
            await self.bus.publish("error", {"error": "boom", "category": "ai_provider"})
        assert any(cat == "ai_provider" and cnt >= 3 for cat, cnt in alerts)
        await self.listener.stop()

    @pytest.mark.asyncio
    async def test_remove_alert_callback(self):
        alerts = []

        def cb(cat, cnt, msg):
            alerts.append(cat)

        self.listener.add_alert_callback(cb)
        self.listener.remove_alert_callback(cb)
        await self.listener.start()
        for _ in range(5):
            await self.bus.publish("error", {"error": "x", "category": "token"})
        assert alerts == []
        await self.listener.stop()

    @pytest.mark.asyncio
    async def test_status_dict(self):
        await self.listener.start()
        status = self.listener.status()
        assert status["running"] is True
        assert "counts_by_category" in status
        assert "alert_threshold" in status
        await self.listener.stop()


# ---------------------------------------------------------------------------
# ai_core.model_selector
# ---------------------------------------------------------------------------

from ai_core.model_selector import (
    CATEGORY_MODELS,
    ModelCategory,
    generate_model_map,
    get_category_for_model,
    get_models_summary,
)


class TestModelSelector:
    def test_judge_category_exists(self):
        assert ModelCategory.JUDGE in CATEGORY_MODELS
        assert len(CATEGORY_MODELS[ModelCategory.JUDGE]) == 1

    def test_generate_model_map_flat(self):
        model_map = generate_model_map()
        assert isinstance(model_map, dict)
        assert len(model_map) > 0

    def test_legacy_alias_present(self):
        model_map = generate_model_map()
        assert "super-grok-heavy-4-2" in model_map

    def test_medical_hipaa_models_first(self):
        """HIPAA-compliant medical models must appear at the start of MEDICAL."""
        medical_names = [name for name, _ in CATEGORY_MODELS[ModelCategory.MEDICAL]]
        assert "SuperGrok-4.20-Med-HIPAA" in medical_names[:2]
        assert "Grok-Med-HIPAA" in medical_names[:2]

    def test_get_category_for_known_model(self):
        cat = get_category_for_model("gpt-4o")
        assert cat == ModelCategory.GPT4

    def test_get_category_for_unknown_model(self):
        assert get_category_for_model("nonexistent-model-xyz") is None

    def test_get_models_summary_returns_all_categories(self):
        summary = get_models_summary()
        for cat in ModelCategory:
            assert cat.value in summary

    def test_all_model_names_unique(self):
        model_map = generate_model_map()
        names = [name for models in CATEGORY_MODELS.values() for name, _ in models]
        # No duplicate display names (ignoring legacy alias)
        assert len(names) == len(set(names))

    def test_claude_current_aliases_present(self):
        model_map = generate_model_map()
        for alias in ("claude-opus", "claude-sonnet", "claude-haiku"):
            assert alias in model_map

    def test_build_judge_unknown_model_raises(self, monkeypatch):
        from ai_core.model_selector import build_judge
        monkeypatch.delenv("LOCAL_LLM", raising=False)
        with pytest.raises(ValueError, match="not found"):
            build_judge(model="totally-unknown-model-xyz")

    def test_build_judge_no_model_raises(self, monkeypatch):
        from ai_core.model_selector import build_judge
        monkeypatch.delenv("LOCAL_LLM", raising=False)
        with pytest.raises(ValueError, match="model must be specified"):
            build_judge()
