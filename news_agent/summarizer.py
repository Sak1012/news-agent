from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Optional

_WORD_RE = re.compile(r"[A-Za-z']+")


def summarize(text: Optional[str], max_sentences: int = 2) -> Optional[str]:
    if not text:
        return None
    sentences = _split_sentences(text)
    if not sentences:
        return None
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    scores = _score_sentences(sentences)
    ranked = sorted(enumerate(sentences), key=lambda item: scores.get(item[0], 0.0), reverse=True)
    top_indices = sorted(idx for idx, _ in ranked[:max_sentences])
    return " ".join(sentences[idx] for idx in top_indices)


def _split_sentences(text: str) -> List[str]:
    split = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in split if sentence.strip()]


def _score_sentences(sentences: Iterable[str]) -> dict[int, float]:
    words = [word.lower() for sentence in sentences for word in _WORD_RE.findall(sentence)]
    if not words:
        return {}
    freq = Counter(words)
    max_freq = max(freq.values())
    normalized = {word: count / max_freq for word, count in freq.items()}
    scores: dict[int, float] = {}
    for idx, sentence in enumerate(sentences):
        tokens = _WORD_RE.findall(sentence)
        if not tokens:
            continue
        scores[idx] = sum(normalized.get(word.lower(), 0.0) for word in tokens) / len(tokens)
    return scores
