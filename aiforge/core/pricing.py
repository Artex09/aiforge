"""Token pricing and cost estimation for per-run accounting.

Prices are USD per 1M tokens. The table is intentionally small and overridable;
the point is built-in, honest cost accounting off the token counts every run
already produces — not a comprehensive price database.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

# model -> (input_per_1m, output_per_1m) in USD
PRICES: Dict[str, Tuple[float, float]] = {
    "aiforge-mock-1": (0.0, 0.0),
    "aiforge-embed-1": (0.0, 0.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "claude-fable-5": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (0.80, 4.00),
}


def price_for(model: str) -> Tuple[float, float]:
    if model in PRICES:
        return PRICES[model]
    # prefix match so versioned ids ("gpt-4o-2024-..") still resolve
    for key, price in PRICES.items():
        if model.startswith(key):
            return price
    return (0.0, 0.0)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    inp, out = price_for(model)
    return round((prompt_tokens / 1_000_000) * inp + (completion_tokens / 1_000_000) * out, 6)


def cost_from_usage(model: str, usage: Any) -> float:
    """Accepts a Usage object or a dict with prompt/completion token counts."""
    if isinstance(usage, dict):
        return estimate_cost(model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
    return estimate_cost(model, getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0))
