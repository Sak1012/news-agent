from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class RawArticle:
    """Raw article data collected from a provider."""

    title: str
    url: str
    source: str
    published_at: Optional[datetime]
    content: Optional[str]
    description: Optional[str]


@dataclass(slots=True)
class NewsItem:
    """Structured representation of a processed article."""

    title: str
    url: str
    source: str
    published_at: Optional[datetime]
    summary: Optional[str]
    sentiment: str
    sentiment_score: float
    excerpt: Optional[str] = None
