from __future__ import annotations

from typing import Dict, List


PROVIDERS: Dict[str, List[str]] = {
    "platform_core": ["runtime", "events", "self_healing"],
    "github": ["repository", "pull_request", "issue"],
    "llm_provider": ["chat", "embedding"],
    "workflow_provider": ["workflow_execution"],
    "observability_provider": ["trace", "metrics"],
}


def provider_registry() -> Dict[str, List[str]]:
    return {provider: list(capabilities) for provider, capabilities in PROVIDERS.items()}


def capabilities_for_provider(provider: str) -> List[str]:
    return list(PROVIDERS.get(provider, []))
