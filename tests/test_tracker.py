"""Tests for llm_spend.tracker."""

from pathlib import Path
from types import SimpleNamespace

import pytest

import llm_spend.tracker as tracker_module
from llm_spend.store import SpendStore
from llm_spend.tracker import _extract_model, _extract_tokens, spending, track

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_store(tmp_path: Path):
    """Swap the module-level store for an in-memory one."""
    real_store = SpendStore(db_path=tmp_path / "test.db")
    tracker_module._set_store(real_store)
    yield real_store
    # Tear down: reset to None so next test gets a fresh default
    tracker_module._store = None


def _openai_response(prompt_tokens=100, completion_tokens=50, model="gpt-4o"):
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    return SimpleNamespace(usage=usage, model=model)


def _anthropic_response(input_tokens=200, output_tokens=75, model="claude-sonnet-4"):
    usage = SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    return SimpleNamespace(usage=usage, model=model)


# ---------------------------------------------------------------------------
# _extract_tokens
# ---------------------------------------------------------------------------


class TestExtractTokens:
    def test_openai_response(self):
        resp = _openai_response(prompt_tokens=300, completion_tokens=150)
        inp, out = _extract_tokens(resp)
        assert inp == 300
        assert out == 150

    def test_anthropic_response(self):
        resp = _anthropic_response(input_tokens=400, output_tokens=200)
        inp, out = _extract_tokens(resp)
        assert inp == 400
        assert out == 200

    def test_none_response(self):
        assert _extract_tokens(None) == (0, 0)

    def test_no_usage_attribute(self):
        assert _extract_tokens(SimpleNamespace()) == (0, 0)

    def test_dict_openai_style(self):
        resp = {"usage": {"prompt_tokens": 50, "completion_tokens": 25}}
        inp, out = _extract_tokens(resp)
        assert inp == 50
        assert out == 25

    def test_dict_anthropic_style(self):
        resp = {"usage": {"input_tokens": 60, "output_tokens": 30}}
        inp, out = _extract_tokens(resp)
        assert inp == 60
        assert out == 30


class TestExtractModel:
    def test_extracts_model_attribute(self):
        resp = SimpleNamespace(model="gpt-4o-mini")
        assert _extract_model(resp) == "gpt-4o-mini"

    def test_none_response(self):
        assert _extract_model(None) is None

    def test_no_model_attribute(self):
        assert _extract_model(SimpleNamespace()) is None

    def test_dict_style(self):
        assert _extract_model({"model": "gemini-1.5-pro"}) == "gemini-1.5-pro"


# ---------------------------------------------------------------------------
# _detect_provider (via tracker)
# ---------------------------------------------------------------------------


class TestDetectProvider:
    def test_claude_is_anthropic(self):
        from llm_spend.pricing import detect_provider

        assert detect_provider("claude-3-5-sonnet-20241022") == "anthropic"

    def test_gpt_is_openai(self):
        from llm_spend.pricing import detect_provider

        assert detect_provider("gpt-4o") == "openai"

    def test_gemini_is_google(self):
        from llm_spend.pricing import detect_provider

        assert detect_provider("gemini-2.0-flash") == "google"


# ---------------------------------------------------------------------------
# @track decorator
# ---------------------------------------------------------------------------


class TestTrackDecorator:
    def test_track_decorator_logs_call(self, mock_store: SpendStore):
        @track(model="gpt-4o", label="test-summary")
        def my_api_call():
            return _openai_response(prompt_tokens=1000, completion_tokens=500)

        my_api_call()

        total = mock_store.get_total(days=1)
        assert total["total_calls"] == 1
        assert total["total_input"] == 1000
        assert total["total_output"] == 500

    def test_track_decorator_returns_result(self, mock_store: SpendStore):
        @track(model="gpt-4o")
        def my_api_call():
            return {"result": "hello"}

        result = my_api_call()
        assert result == {"result": "hello"}

    def test_track_decorator_uses_response_model(self, mock_store: SpendStore):
        @track(model="gpt-4o")
        def my_api_call():
            return _openai_response(model="gpt-4o-mini")

        my_api_call()

        calls = mock_store.get_all_calls(days=1)
        assert calls[0]["model"] == "gpt-4o-mini"

    def test_track_decorator_calculates_cost(self, mock_store: SpendStore):
        @track(model="gpt-4o")
        def my_api_call():
            # 1M input + 1M output for gpt-4o => $2.50 + $10.00 = $12.50
            return _openai_response(prompt_tokens=1_000_000, completion_tokens=1_000_000)

        my_api_call()

        total = mock_store.get_total(days=1)
        assert total["total_cost"] == pytest.approx(12.50, rel=1e-6)


# ---------------------------------------------------------------------------
# spending context manager
# ---------------------------------------------------------------------------


class TestSpendingContextManager:
    def test_spending_logs_call(self, mock_store: SpendStore):
        with spending("claude-sonnet-4", label="classify") as s:
            s.input_tokens = 500
            s.output_tokens = 100

        total = mock_store.get_total(days=1)
        assert total["total_calls"] == 1
        assert total["total_input"] == 500
        assert total["total_output"] == 100

    def test_spending_calculates_cost(self, mock_store: SpendStore):
        # claude-sonnet-4: $3.00/M input, $15.00/M output
        # 1M + 1M => $18.00
        with spending("claude-sonnet-4") as s:
            s.input_tokens = 1_000_000
            s.output_tokens = 1_000_000

        total = mock_store.get_total(days=1)
        assert total["total_cost"] == pytest.approx(18.00, rel=1e-6)

    def test_spending_logs_even_on_exception(self, mock_store: SpendStore):
        with pytest.raises(ValueError):
            with spending("gpt-4o", label="err") as s:
                s.input_tokens = 200
                s.output_tokens = 50
                raise ValueError("something went wrong")

        total = mock_store.get_total(days=1)
        assert total["total_calls"] == 1
