from __future__ import annotations

from typing import Iterable, List

from app.platform.catalog.catalog_models import CatalogActivation, CatalogItem, CatalogRelease, CatalogRule, CatalogSummary


PUBLISHED_STATUS = "published"
ACTIVE_STATUS = "active"


def catalog_items() -> List[CatalogItem]:
    return [
        CatalogItem(
            "template_crm",
            "template",
            "AI CRM Starter",
            "platform",
            "1.0.0",
            PUBLISHED_STATUS,
            ["sales", "customer"],
            ["project_seed", "generation_prompt"],
        ),
        CatalogItem(
            "plugin_quality",
            "extension",
            "Quality Review Extension",
            "platform",
            "1.0.0",
            PUBLISHED_STATUS,
            ["quality", "review"],
            ["review_check", "scorecard"],
        ),
        CatalogItem(
            "connector_tasks",
            "connector",
            "Task Workspace Connector",
            "platform",
            "1.0.0",
            PUBLISHED_STATUS,
            ["workflow", "workspace"],
            ["task_sync", "comment_sync"],
        ),
    ]


def find_item(item_id: str) -> CatalogItem:
    for item in catalog_items():
        if item.item_id == item_id:
            return item
    raise ValueError(f"Unknown catalog item: {item_id}")


def publish_release(release_id: str, item_id: str, version: str, notes: str) -> CatalogRelease:
    find_item(item_id)
    return CatalogRelease(release_id, item_id, version, PUBLISHED_STATUS, notes)


def activate_item(activation_id: str, tenant_id: str, item_id: str, version: str) -> CatalogActivation:
    find_item(item_id)
    return CatalogActivation(activation_id, tenant_id, item_id, version, ACTIVE_STATUS)


def add_catalog_rule(rule_id: str, item_id: str, rule: str, severity: str) -> CatalogRule:
    find_item(item_id)
    return CatalogRule(rule_id, item_id, rule, severity)


def activations_for_tenant(activations: Iterable[CatalogActivation], tenant_id: str) -> List[CatalogActivation]:
    return [activation for activation in activations if activation.tenant_id == tenant_id]


def summarize_catalog(items: Iterable[CatalogItem], activations: Iterable[CatalogActivation], rules: Iterable[CatalogRule]) -> CatalogSummary:
    item_list = list(items)
    activation_list = list(activations)
    rule_list = list(rules)
    return CatalogSummary(
        item_count=len(item_list),
        published_count=len([item for item in item_list if item.status == PUBLISHED_STATUS]),
        activation_count=len(activation_list),
        rule_count=len(rule_list),
        template_count=len([item for item in item_list if item.item_type == "template"]),
        extension_count=len([item for item in item_list if item.item_type == "extension"]),
        connector_count=len([item for item in item_list if item.item_type == "connector"]),
    )
