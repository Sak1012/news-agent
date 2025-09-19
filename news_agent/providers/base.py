from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Mapping

from ..models import RawArticle


class BaseProvider(ABC):
    """Abstract base class for content providers."""

    @abstractmethod
    def fetch(self, query: str, limit: int = 10, **kwargs: Mapping[str, object]) -> Iterable[RawArticle]:
        """Yield ``RawArticle`` objects for the given query."""


ProviderList = List[BaseProvider]
