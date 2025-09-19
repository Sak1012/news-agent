from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class AgentConfig:
    """Runtime configuration for the news agent."""

    newsapi_key: Optional[str] = None
    default_limit: int = 10
    allowed_domains: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "AgentConfig":
        import os

        return cls(
            newsapi_key=os.getenv("NEWSAPI_KEY"),
            default_limit=int(os.getenv("NEWS_AGENT_DEFAULT_LIMIT", "10")),
            allowed_domains=_split_csv(os.getenv("NEWS_AGENT_ALLOWED_DOMAINS")),
        )
