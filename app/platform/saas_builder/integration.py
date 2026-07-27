from __future__ import annotations

from typing import Any


def install_saas_builder(app: Any) -> None:
    from app.api.routes.auth import router as customer_auth_router
    from app.api.routes.secrets import router as customer_secrets_router
    from app.platform.saas_builder.routes import router as saas_builder_router

    app.include_router(customer_auth_router, prefix="/api/auth")
    app.include_router(customer_secrets_router, prefix="/api/secrets")
    app.include_router(saas_builder_router)

    @app.on_event("startup")
    async def initialize_customer_identity() -> None:
        from app.platform.saas_builder.identity import initialize_identity_tables

        await initialize_identity_tables()


def is_credential_free_preparation(state: dict[str, Any], stage: object) -> bool:
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    return context.get("request_channel") == "saas_builder" and stage == "prepare"


def prepare_if_saas_builder(state: dict[str, Any]) -> dict[str, Any] | None:
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    if context.get("request_channel") != "saas_builder":
        return None
    from app.platform.saas_builder.preparation import prepare_reference_application

    return prepare_reference_application(state)


def repository_package(state: dict[str, Any]) -> dict[str, Any] | None:
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    change_set = state.get("change_set")
    files = change_set.get("files") if isinstance(change_set, dict) else None
    if context.get("request_channel") != "saas_builder" or not isinstance(files, list) or not files:
        return None
    return {
        "repository": context.get("repository"),
        "base_ref": "main",
        "branch_name": "afos-016-%s" % str(context.get("application_id") or "app").lower(),
        "commit_message": "feat: deliver %s" % context.get("application_name"),
        "pr_title": "AFOS-016: Deliver %s" % context.get("application_name"),
        "pr_body": "Generated from canonical mission %s." % state.get("mission_id"),
        "file_changes": files,
        "source_directory": context.get("source_directory"),
        "service_name": context.get("service_name"),
    }
