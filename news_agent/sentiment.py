from __future__ import annotations

from typing import Optional

_POSITIVE = {
    "growth",
    "improve",
    "improving",
    "surge",
    "strong",
    "beat",
    "record",
    "gain",
    "positive",
    "optimistic",
    "upbeat",
    "increase",
    "exceed",
    "sustainable",
    "sustainability",
    "expansion",
}

_NEGATIVE = {
    "loss",
    "decline",
    "drop",
    "warning",
    "weak",
    "downturn",
    "concern",
    "miss",
    "lawsuit",
    "negative",
    "risk",
    "regulatory",
    "penalty",
    "fraud",
    "downgrade",
}


def score_sentiment(text: Optional[str]) -> tuple[str, float]:
    if not text:
        return "neutral", 0.0
    lowered = text.lower()
    pos_hits = sum(lowered.count(token) for token in _POSITIVE)
    neg_hits = sum(lowered.count(token) for token in _NEGATIVE)
    total = pos_hits + neg_hits
    if total == 0:
        return "neutral", 0.0
    score = (pos_hits - neg_hits) / max(total, 1)
    if score > 0.2:
        return "positive", score
    if score < -0.2:
        return "negative", score
    return "neutral", score
