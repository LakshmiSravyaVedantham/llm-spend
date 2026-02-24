"""
Pricing tables for LLM providers (per million tokens).
"""

from __future__ import annotations

PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    # Google
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}

# Pre-sorted list of known model names from longest to shortest for greedy matching.
_SORTED_MODELS = sorted(PRICING.keys(), key=len, reverse=True)


def get_model_pricing(model: str) -> dict[str, float]:
    """Get pricing for a model, with fuzzy matching for partial names.

    Matching priority (most-specific first):
    1. Exact match
    2. Known model name is a substring of the given model string (longest match first)
    3. Given model string is a substring of a known model name (longest match first)
    """
    if model in PRICING:
        return PRICING[model]

    # Longest known model that is contained within the given name wins.
    for known_model in _SORTED_MODELS:
        if known_model in model:
            return PRICING[known_model]

    # Reverse: given model is contained within a known model name.
    for known_model in _SORTED_MODELS:
        if model in known_model:
            return PRICING[known_model]

    return {}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given model and token counts."""
    pricing = get_model_pricing(model)
    if not pricing:
        return 0.0
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost


def detect_provider(model: str) -> str:
    """Detect provider from model name."""
    model_lower = model.lower()
    if model_lower.startswith("claude"):
        return "anthropic"
    if model_lower.startswith(("gpt-", "o1", "o3")):
        return "openai"
    if model_lower.startswith("gemini"):
        return "google"
    return "unknown"
