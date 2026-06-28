from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TenantSetting:
    setting_id: str
    tenant_id: str
    key: str
    value: str
    scope: str


@dataclass(frozen=True)
class ApiKey:
    key_id: str
    tenant_id: str
    name: str
    status: str
    scopes: List[str]


@dataclass(frozen=True)
class Integration:
    integration_id: str
    tenant_id: str
    provider: str
    status: str
    capabilities: List[str]


@dataclass(frozen=True)
class WebhookEndpoint:
    webhook_id: str
    tenant_id: str
    name: str
    url: str
    status: str
    event_types: List[str]


@dataclass(frozen=True)
class FeatureFlag:
    flag_id: str
    tenant_id: str
    name: str
    enabled: bool
    rollout: int


@dataclass(frozen=True)
class AdminOpsSummary:
    setting_count: int
    active_key_count: int
    integration_count: int
    active_webhook_count: int
    enabled_flag_count: int


@dataclass(frozen=True)
class AdminOpsContext:
    settings: List[TenantSetting]
    api_keys: List[ApiKey]
    integrations: List[Integration]
    webhooks: List[WebhookEndpoint]
    flags: List[FeatureFlag]
    metadata: Dict[str, object]
