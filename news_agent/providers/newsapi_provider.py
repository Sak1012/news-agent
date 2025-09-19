from __future__ import annotations

from datetime import datetime
from typing import Iterable, Mapping, Optional

import requests

from ..models import RawArticle
from .base import BaseProvider


class NewsAPIProvider(BaseProvider):
    """Fetches articles from newsapi.org."""

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("NewsAPIProvider requires an API key")
        self._api_key = api_key

    def fetch(self, query: str, limit: int = 10, **kwargs: Mapping[str, object]) -> Iterable[RawArticle]:
        params = {
            "q": query,
            "pageSize": limit,
            "language": kwargs.get("language", "en"),
            "sortBy": kwargs.get("sort_by", "publishedAt"),
        }
        response = requests.get(
            self.BASE_URL,
            params=params,
            headers={"Authorization": self._api_key},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        for article in payload.get("articles", []):
            yield RawArticle(
                title=article.get("title") or "Untitled",
                url=article.get("url") or "",
                source=(article.get("source") or {}).get("name") or "Unknown",
                published_at=_parse_date(article.get("publishedAt")),
                content=article.get("content"),
                description=article.get("description"),
            )


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
