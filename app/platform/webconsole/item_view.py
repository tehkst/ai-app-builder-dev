from __future__ import annotations

from app.platform.catalog.catalog_models import CatalogContext
from app.platform.catalog.catalog_store import summarize_catalog
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_item_view(context: CatalogContext) -> ConsoleView:
    summary = summarize_catalog(context.items, context.activations, context.rules)
    return ConsoleView(
        view_id="admin_items",
        title="Items",
        cards=[
            ConsoleCard("items", "Items", str(summary.item_count), "healthy", {}),
            ConsoleCard("active", "Active", str(summary.published_count), "healthy", {}),
            ConsoleCard("uses", "Uses", str(summary.activation_count), "healthy", {}),
            ConsoleCard("templates", "Templates", str(summary.template_count), "healthy", {}),
            ConsoleCard("extensions", "Extensions", str(summary.extension_count), "healthy", {}),
            ConsoleCard("connectors", "Connectors", str(summary.connector_count), "healthy", {}),
        ],
    )
