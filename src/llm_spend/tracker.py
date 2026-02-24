"""
Decorator and context manager for tracking LLM API call costs.
"""

from __future__ import annotations

import functools
import inspect
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from llm_spend.pricing import calculate_cost, detect_provider
from llm_spend.store import SpendStore

# Module-level default store (lazily created)
_store: Optional[SpendStore] = None


def _get_store() -> SpendStore:
    global _store
    if _store is None:
        _store = SpendStore()
    return _store


def _set_store(store: SpendStore) -> None:
    """Replace the module-level store (useful for testing)."""
    global _store
    _store = store


# ------------------------------------------------------------------
# Response object helpers
# ------------------------------------------------------------------


def _extract_tokens(response: Any) -> tuple[int, int]:
    """Extract (input_tokens, output_tokens) from common response objects."""
    if response is None:
        return 0, 0

    usage = getattr(response, "usage", None)
    if usage is not None:
        # OpenAI style: prompt_tokens / completion_tokens
        prompt = getattr(usage, "prompt_tokens", None)
        completion = getattr(usage, "completion_tokens", None)
        if prompt is not None and completion is not None:
            return int(prompt), int(completion)

        # Anthropic style: input_tokens / output_tokens
        inp = getattr(usage, "input_tokens", None)
        out = getattr(usage, "output_tokens", None)
        if inp is not None and out is not None:
            return int(inp), int(out)

        # Generic fallback
        inp = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", 0)
        out = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", 0)
        return int(inp), int(out)

    # Dict-style usage
    if isinstance(response, dict):
        usage_dict = response.get("usage", {})
        if isinstance(usage_dict, dict):
            inp = usage_dict.get("input_tokens") or usage_dict.get("prompt_tokens", 0)
            out = usage_dict.get("output_tokens") or usage_dict.get("completion_tokens", 0)
            return int(inp), int(out)

    return 0, 0


def _extract_model(response: Any) -> Optional[str]:
    """Extract model name from a response object."""
    if response is None:
        return None
    model = getattr(response, "model", None)
    if model:
        return str(model)
    if isinstance(response, dict):
        return response.get("model")
    return None


# ------------------------------------------------------------------
# Decorator
# ------------------------------------------------------------------


def track(
    model: str,
    label: Optional[str] = None,
    provider: Optional[str] = None,
):
    """
    Decorator to track LLM API call costs.

    Usage::

        @track(model="gpt-4o", label="summarize")
        def summarize(text):
            response = openai_client.chat.completions.create(...)
            return response
    """

    def decorator(func: Any) -> Any:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Capture caller info one level above wrapper
            frame = inspect.stack()[1]
            caller_file: str = frame.filename
            caller_function: str = frame.function

            start = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000.0

            input_tokens, output_tokens = _extract_tokens(result)
            detected_model = _extract_model(result) or model
            detected_provider = provider or detect_provider(detected_model)
            cost = calculate_cost(detected_model, input_tokens, output_tokens)

            _get_store().log_call(
                provider=detected_provider,
                model=detected_model,
                label=label or func.__name__,
                file=caller_file,
                function=caller_function,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                duration_ms=duration_ms,
            )
            return result

        return wrapper

    return decorator


# ------------------------------------------------------------------
# Context manager
# ------------------------------------------------------------------


class SpendContext:
    """Holds mutable token counts for the ``spending`` context manager."""

    def __init__(self) -> None:
        self.input_tokens: int = 0
        self.output_tokens: int = 0


@contextmanager
def spending(
    model: str,
    label: Optional[str] = None,
    provider: Optional[str] = None,
) -> Iterator[SpendContext]:
    """
    Context manager for manual tracking::

        with spending("claude-sonnet-4", label="classify") as s:
            response = client.messages.create(...)
            s.input_tokens = response.usage.input_tokens
            s.output_tokens = response.usage.output_tokens
    """
    ctx = SpendContext()

    # Capture caller info
    frame = inspect.stack()[1]
    caller_file: str = frame.filename
    caller_function: str = frame.function

    start = time.time()
    try:
        yield ctx
    finally:
        duration_ms = (time.time() - start) * 1000.0
        detected_provider = provider or detect_provider(model)
        cost = calculate_cost(model, ctx.input_tokens, ctx.output_tokens)

        _get_store().log_call(
            provider=detected_provider,
            model=model,
            label=label,
            file=caller_file,
            function=caller_function,
            input_tokens=ctx.input_tokens,
            output_tokens=ctx.output_tokens,
            cost_usd=cost,
            duration_ms=duration_ms,
        )
