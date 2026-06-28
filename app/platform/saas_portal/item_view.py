from __future__ import annotations

from app.platform.catalog.catalog_models import CatalogContext
from app.platform.catalog.catalog_store import activations_for_tenant, summarize_catalog
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_item_view(context: CatalogContext, tenant_id: str) -> PortalView:
    scoped = activations_for_tenant(context.activations, tenant_id)
    summary = summarize_catalog(context.items, scoped, [])
    return PortalView(
        view_id="portal_items",
        title="Items",
        cards=[
            PortalCard("active", "Active Items", str(summary.activation_count), "healthy", {}),
            PortalCard("templates", "Templates", str(summary.template_count), "healthy", {}),
            PortalCard("extensions", "Extensions", str(summary.extension_count), "healthy", {}),
        ],
    )
