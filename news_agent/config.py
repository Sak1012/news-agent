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
    max_per_source: Optional[int] = 1
    sec_user_agent: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        import os

        return cls(
            newsapi_key=os.getenv("NEWSAPI_KEY"),
            default_limit=int(os.getenv("NEWS_AGENT_DEFAULT_LIMIT", "10")),
            allowed_domains=_split_csv(os.getenv("NEWS_AGENT_ALLOWED_DOMAINS")),
            max_per_source=_parse_source_limit(os.getenv("NEWS_AGENT_MAX_PER_SOURCE"), default=1),
            sec_user_agent=os.getenv("NEWS_AGENT_SEC_USER_AGENT"),
        )


def _parse_source_limit(value: Optional[str], default: Optional[int] = None) -> Optional[int]:
    if value is None or value.strip() == "":
        return default
    try:
        parsed = int(value)
    except ValueError:
        raise ValueError("NEWS_AGENT_MAX_PER_SOURCE must be an integer if set") from None
    if parsed <= 0:
        return None
    return parsed
