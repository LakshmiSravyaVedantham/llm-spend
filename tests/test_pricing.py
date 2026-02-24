"""Tests for llm_spend.pricing."""

import pytest

from llm_spend.pricing import PRICING, calculate_cost, detect_provider, get_model_pricing


class TestCalculateCost:
    def test_known_model_gpt4o(self):
        # 1 million input + 1 million output for gpt-4o
        # input: $2.50/M, output: $10.00/M => total $12.50
        cost = calculate_cost("gpt-4o", 1_000_000, 1_000_000)
        assert cost == pytest.approx(12.50, rel=1e-6)

    def test_known_model_claude_sonnet(self):
        # 500k input + 250k output for claude-sonnet-4
        # input: $3.00/M, output: $15.00/M
        # => 0.5*3 + 0.25*15 = 1.50 + 3.75 = 5.25
        cost = calculate_cost("claude-sonnet-4", 500_000, 250_000)
        assert cost == pytest.approx(5.25, rel=1e-6)

    def test_known_model_gpt4o_mini(self):
        # 100k input + 100k output
        # input: $0.15/M, output: $0.60/M
        # => 0.1*0.15 + 0.1*0.60 = 0.015 + 0.060 = 0.075
        cost = calculate_cost("gpt-4o-mini", 100_000, 100_000)
        assert cost == pytest.approx(0.075, rel=1e-6)

    def test_zero_tokens(self):
        cost = calculate_cost("gpt-4o", 0, 0)
        assert cost == 0.0

    def test_unknown_model_returns_zero(self):
        cost = calculate_cost("totally-unknown-model-xyz", 100_000, 100_000)
        assert cost == 0.0


class TestFuzzyModelMatching:
    def test_exact_match(self):
        pricing = get_model_pricing("gpt-4o-mini")
        assert pricing["input"] == pytest.approx(0.15)
        assert pricing["output"] == pytest.approx(0.60)

    def test_versioned_suffix_matches_gpt4o_mini(self):
        # "gpt-4o-mini-2024-07-18" should match "gpt-4o-mini"
        pricing = get_model_pricing("gpt-4o-mini-2024-07-18")
        assert pricing != {}
        assert pricing["input"] == pytest.approx(0.15)

    def test_versioned_suffix_matches_claude(self):
        # A versioned claude model name
        pricing = get_model_pricing("claude-3-5-sonnet-20241022-v1")
        assert pricing != {}

    def test_unknown_model_returns_empty(self):
        pricing = get_model_pricing("no-such-model-xyz-9999")
        assert pricing == {}

    def test_all_pricing_keys_resolve(self):
        """Every model in PRICING should resolve to itself."""
        for model in PRICING:
            pricing = get_model_pricing(model)
            assert pricing != {}, f"Model {model!r} did not resolve"


class TestDetectProvider:
    def test_claude_is_anthropic(self):
        assert detect_provider("claude-3-5-sonnet-20241022") == "anthropic"

    def test_gpt_is_openai(self):
        assert detect_provider("gpt-4o") == "openai"
        assert detect_provider("gpt-4o-mini") == "openai"

    def test_o1_is_openai(self):
        assert detect_provider("o1") == "openai"
        assert detect_provider("o1-mini") == "openai"

    def test_gemini_is_google(self):
        assert detect_provider("gemini-1.5-pro") == "google"

    def test_unknown_returns_unknown(self):
        assert detect_provider("some-random-model") == "unknown"
