from __future__ import annotations

from app.platform.data.tenants.tenant_models import Tenant
from app.platform.data.tenants.tenant_store import TenantStore


def main() -> None:
    store = TenantStore()
    tenant = Tenant(tenant_id="tenant1", name="Acme")
    store.add(tenant)
    assert tenant.enabled(), tenant
    assert store.get("tenant1") == tenant
    assert len(store.list_all()) == 1
    assert len(store.enabled_items()) == 1
    print("TENANT CHECK PASSED")


if __name__ == "__main__":
    main()
