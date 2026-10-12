"""Token -> USD pricing table (Gemini, approx; update as needed)."""
from __future__ import annotations

# price per 1k tokens (input, output)
PRICING_PER_1K: dict[str, tuple[float, float]] = {
    "gemini-1.5-flash": (0.000075, 0.0003),
    "gemini-1.5-pro": (0.00125, 0.005),
    "gemini-2.0-flash": (0.0001, 0.0004),
    "default": (0.0001, 0.0004),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = PRICING_PER_1K.get(model, PRICING_PER_1K["default"])
    return round((input_tokens / 1000) * inp + (output_tokens / 1000) * out, 6)


def approx_tokens(text: str) -> int:
    # ~4 chars per token heuristic
    return max(1, len(text) // 4)
