"""
llm-spend: Track your AI API costs per file, function, and feature.
"""

from llm_spend.store import SpendStore
from llm_spend.tracker import SpendContext, _set_store, spending, track

# Convenience alias: ``LLMSpend`` is the store class
LLMSpend = SpendStore

__all__ = [
    "track",
    "spending",
    "SpendContext",
    "SpendStore",
    "LLMSpend",
    "_set_store",
]

__version__ = "0.1.0"
