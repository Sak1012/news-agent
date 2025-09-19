from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from ..models import RawArticle
from .base import BaseProvider


class MockProvider(BaseProvider):
    """Returns hard-coded articles for offline development."""

    def fetch(self, query: str, limit: int = 10, **kwargs) -> Iterable[RawArticle]:
        now = datetime.utcnow()
        sample = [
            RawArticle(
                title=f"{query.title()} expands sustainability efforts",
                url="https://example.com/sustainability",
                source="Example News",
                published_at=now - timedelta(hours=2),
                content=(
                    f"{query} announced new sustainability targets aimed at reducing emissions by 30% "
                    "over the next five years. The initiative includes investments in renewable energy "
                    "and supply chain transparency."
                ),
                description="Company targets lower emissions and greener supply chains.",
            ),
            RawArticle(
                title=f"Analysts debate {query} quarterly earnings",
                url="https://example.com/earnings",
                source="Market Watchers",
                published_at=now - timedelta(days=1),
                content=(
                    f"Market analysts offered mixed reactions to {query}'s latest earnings report, citing "
                    "flat revenue growth but improving operating margins. Investor sentiment appears "
                    "cautious heading into the next quarter."
                ),
                description="Mixed analyst sentiment following the latest results.",
            ),
        ]
        return sample[:limit]
