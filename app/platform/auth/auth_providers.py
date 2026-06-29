from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol

from app.platform.security.security_context import SecurityContext


@dataclass(frozen=True)
class AuthCredential:
    kind: str
    value: str
    metadata: Dict[str, str]


@dataclass(frozen=True)
class ProviderResult:
    success: bool
    provider: str
    context: Optional[SecurityContext] = None
    reason: str = ""


class AuthProvider(Protocol):
    provider_name: str

    def authenticate(self, credential: AuthCredential) -> ProviderResult:
        ...


class StaticTokenProvider:
    provider_name = "static_token"

    def __init__(self, tokens: Dict[str, SecurityContext]) -> None:
        self._tokens = dict(tokens)

    def authenticate(self, credential: AuthCredential) -> ProviderResult:
        if credential.kind != "token":
            return ProviderResult(False, self.provider_name, reason="unsupported credential")
        context = self._tokens.get(credential.value)
        if context is None:
            return ProviderResult(False, self.provider_name, reason="invalid token")
        return ProviderResult(True, self.provider_name, context=context)


class StaticApiKeyProvider:
    provider_name = "static_api_key"

    def __init__(self, keys: Dict[str, SecurityContext]) -> None:
        self._keys = dict(keys)

    def authenticate(self, credential: AuthCredential) -> ProviderResult:
        if credential.kind != "api_key":
            return ProviderResult(False, self.provider_name, reason="unsupported credential")
        context = self._keys.get(credential.value)
        if context is None:
            return ProviderResult(False, self.provider_name, reason="invalid api key")
        return ProviderResult(True, self.provider_name, context=context)


class ProviderChain:
    def __init__(self, providers: List[AuthProvider]) -> None:
        self._providers = list(providers)

    def authenticate(self, credential: AuthCredential) -> ProviderResult:
        last_result = ProviderResult(False, "provider_chain", reason="no providers")
        for provider in self._providers:
            result = provider.authenticate(credential)
            if result.success:
                return result
            last_result = result
        return ProviderResult(False, "provider_chain", reason=last_result.reason)
