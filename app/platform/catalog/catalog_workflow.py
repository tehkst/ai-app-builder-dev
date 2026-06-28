from __future__ import annotations

from app.platform.catalog.catalog_models import CatalogContext
from app.platform.catalog.catalog_store import activate_item, add_catalog_rule, catalog_items, publish_release


def run_demo_catalog() -> CatalogContext:
    items = catalog_items()
    releases = [
        publish_release("release_template", "template_crm", "1.0.0", "Initial template"),
        publish_release("release_extension", "plugin_quality", "1.0.0", "Initial extension"),
    ]
    activations = [
        activate_item("activation_template", "tenant_platform", "template_crm", "1.0.0"),
        activate_item("activation_connector", "tenant_platform", "connector_tasks", "1.0.0"),
    ]
    rules = [
        add_catalog_rule("rule_review", "plugin_quality", "requires_review", "medium"),
        add_catalog_rule("rule_tenant", "connector_tasks", "tenant_scoped", "high"),
    ]
    return CatalogContext(
        items=items,
        releases=releases,
        activations=activations,
        rules=rules,
        metadata={"workflow": "catalog"},
    )
