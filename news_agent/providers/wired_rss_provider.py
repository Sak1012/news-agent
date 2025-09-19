from __future__ import annotations

from datetime import datetime, timezone
import difflib
import re
from typing import Dict, Iterable, List, Mapping

import feedparser
import requests

from ..models import RawArticle
from .base import BaseProvider


class WiredRSSProvider(BaseProvider):
    """Fetches and filters articles from Wired RSS feeds."""

    DEFAULT_SECTIONS: Dict[str, str] = {
        "business": "https://www.wired.com/feed/category/business/latest/rss",
        "science": "https://www.wired.com/feed/category/science/latest/rss",
    }

    def __init__(self, sections: Mapping[str, str] | None = None) -> None:
        self._sections = dict(sections or self.DEFAULT_SECTIONS)

    def fetch(self, query: str, limit: int = 10, **kwargs: Mapping[str, object]) -> Iterable[RawArticle]:
        results: List[RawArticle] = []
        for section, url in self._sections.items():
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
            except Exception:
                continue  # Skip failed feeds but continue others
            feed = feedparser.parse(response.content)
            entries = feed.entries or []
            for entry in entries:
                if not _matches_query(query, _entry_text(entry)):
                    continue
                results.append(
                    RawArticle(
                        title=entry.get("title") or f"Wired {section.title()} Update",
                        url=entry.get("link") or "",
                        source=f"Wired {section.title()}",
                        published_at=_parse_published(entry),
                        content=_get_content(entry),
                        description=entry.get("summary"),
                    )
                )
                if len(results) >= limit:
                    return results
        return results


def _entry_text(entry: Mapping[str, object]) -> str:
    title = str(entry.get("title", ""))
    summary = str(entry.get("summary", ""))
    content = ""
    contents = entry.get("content")
    if contents:
        try:
            content = " ".join(part.get("value", "") for part in contents if isinstance(part, Mapping))
        except Exception:
            content = ""
    return f"{title} {summary} {content}".lower()


def _get_content(entry: Mapping[str, object]) -> str | None:
    contents = entry.get("content")
    if contents:
        parts: List[str] = []
        for part in contents:
            if isinstance(part, Mapping):
                value = part.get("value")
                if isinstance(value, str):
                    parts.append(value)
        if parts:
            return "\n\n".join(parts)
    summary = entry.get("summary")
    return summary if isinstance(summary, str) else None


def _parse_published(entry: Mapping[str, object]) -> datetime | None:
    published_parsed = entry.get("published_parsed")
    if published_parsed:
        try:
            return datetime(*published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    updated = entry.get("updated_parsed")
    if updated:
        try:
            return datetime(*updated[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _matches_query(query: str, entry_text: str) -> bool:
    tokens = _tokenize(query)
    if not tokens:
        return True
    entry_text = entry_text.lower()
    entry_tokens = _tokenize(entry_text)
    entry_token_set = set(entry_tokens)
    for token in tokens:
        if token in entry_text:
            return True
        if len(token) >= 3:
            for candidate in entry_token_set:
                if _similar(token, candidate):
                    return True
    return False


def _tokenize(value: str) -> List[str]:
    return [token for token in re.split(r"[^a-z0-9]+", value.lower()) if token]


def _similar(a: str, b: str, threshold: float = 0.82) -> bool:
    if a == b:
        return True
    ratio = difflib.SequenceMatcher(a=a, b=b).ratio()
    return ratio >= threshold
