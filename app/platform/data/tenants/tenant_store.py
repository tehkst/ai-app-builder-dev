from __future__ import annotations

from typing import Dict, List, Optional

from app.platform.data.tenants.tenant_models import Tenant


class TenantStore:
    def __init__(self) -> None:
        self._items: Dict[str, Tenant] = {}

    def add(self, tenant: Tenant) -> Tenant:
        self._items[tenant.tenant_id] = tenant
        return tenant

    def get(self, tenant_id: str) -> Optional[Tenant]:
        return self._items.get(tenant_id)

    def list_all(self) -> List[Tenant]:
        return list(self._items.values())

    def enabled_items(self) -> List[Tenant]:
        return [tenant for tenant in self._items.values() if tenant.enabled()]
