from __future__ import annotations

from dataclasses import asdict
import re
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from .config import AgentConfig
from .models import NewsItem, RawArticle
from .providers.base import BaseProvider, ProviderList
from .providers.wired_rss_provider import WiredRSSProvider
from .sentiment import score_sentiment
from .summarizer import summarize

try:
    from .providers.newsapi_provider import NewsAPIProvider
except Exception:  # pragma: no cover - dependency optional
    NewsAPIProvider = None  # type: ignore


class NewsAgent:
    """Aggregates, summarizes, and scores news articles."""

    def __init__(self, config: Optional[AgentConfig] = None, providers: Optional[Iterable[BaseProvider]] = None) -> None:
        self.config = config or AgentConfig.from_env()
        if providers is not None:
            self.providers: ProviderList = list(providers)
        else:
            self.providers = self._build_providers()
        if not self.providers:
            raise RuntimeError("No providers configured for NewsAgent")

    def _build_providers(self) -> ProviderList:
        providers: ProviderList = []
        if getattr(self.config, "newsapi_key", None) and NewsAPIProvider is not None:
            providers.append(NewsAPIProvider(self.config.newsapi_key))
        providers.append(WiredRSSProvider())
        return providers

    def search(self, query: str, limit: Optional[int] = None, **kwargs) -> List[NewsItem]:
        if not query or not query.strip():
            raise ValueError("Query must be provided")
        limit = limit or self.config.default_limit
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        results: List[NewsItem] = []
        for provider in self.providers:
            for raw in provider.fetch(query=query, limit=limit, **kwargs):
                if raw.url:
                    if raw.url in seen_urls:
                        continue
                    if not self._is_allowed_domain(raw.url):
                        continue
                    seen_urls.add(raw.url)
                dedupe_key = self._dedupe_key(raw)
                if dedupe_key and dedupe_key in seen_titles:
                    continue
                item = self._process(raw)
                results.append(item)
                if dedupe_key:
                    seen_titles.add(dedupe_key)
                if len(results) >= limit:
                    return results
        return results

    def _process(self, article: RawArticle) -> NewsItem:
        text = article.content or article.description
        summary = summarize(text)
        sentiment_label, sentiment_score = score_sentiment(text or "")
        excerpt = (article.description or article.content)
        if excerpt and len(excerpt) > 280:
            excerpt = excerpt[:277].rstrip() + "..."
        return NewsItem(
            title=article.title,
            url=article.url,
            source=article.source,
            published_at=article.published_at,
            summary=summary,
            sentiment=sentiment_label,
            sentiment_score=sentiment_score,
            excerpt=excerpt,
        )

    def _is_allowed_domain(self, url: str) -> bool:
        if not self.config.allowed_domains:
            return True
        parsed = urlparse(url)
        if not parsed.netloc:
            return True
        hostname = parsed.netloc.lower()
        for domain in self.config.allowed_domains:
            domain = domain.lower()
            if hostname == domain or hostname.endswith(f".{domain}"):
                return True
        return False

    def to_dict(self, item: NewsItem) -> dict:
        data = asdict(item)
        if item.published_at is not None:
            data["published_at"] = item.published_at.isoformat()
        return data

    def _dedupe_key(self, article: RawArticle) -> Optional[str]:
        title = (article.title or "").strip().lower()
        if title:
            normalized_title = re.sub(r"[^a-z0-9]+", "", title)
            if normalized_title:
                return normalized_title
        excerpt = (article.description or article.content or "").strip().lower()
        if excerpt:
            normalized_excerpt = re.sub(r"[^a-z0-9]+", "", excerpt[:120])
            if normalized_excerpt:
                return normalized_excerpt
        return None
