from __future__ import annotations

from app.platform.auth.auth_providers import AuthCredential, ProviderChain, StaticApiKeyProvider, StaticTokenProvider
from app.platform.security.security_context import SecurityContext


def main() -> None:
    context = SecurityContext(
        tenant_id="tenant1",
        organization_id="org1",
        actor_id="user1",
        actor_type="user",
        roles=["platform_owner"],
    )
    token_provider = StaticTokenProvider({"token1": context})
    api_key_provider = StaticApiKeyProvider({"key1": context})
    chain = ProviderChain([token_provider, api_key_provider])

    token_result = chain.authenticate(AuthCredential(kind="token", value="token1", metadata={}))
    assert token_result.success is True
    assert token_result.context == context

    key_result = chain.authenticate(AuthCredential(kind="api_key", value="key1", metadata={}))
    assert key_result.success is True
    assert key_result.context == context

    failed = chain.authenticate(AuthCredential(kind="api_key", value="missing", metadata={}))
    assert failed.success is False
    assert failed.reason

    unsupported = chain.authenticate(AuthCredential(kind="oauth", value="token", metadata={}))
    assert unsupported.success is False

    print("D5.2 AUTH PROVIDER CHECK PASSED")


if __name__ == "__main__":
    main()
