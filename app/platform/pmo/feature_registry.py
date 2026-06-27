from __future__ import annotations

from typing import Dict, Optional

from app.platform.pmo.planning_models import FeatureItem


FEATURES: Dict[str, FeatureItem] = {
    "constitution_registry": FeatureItem(
        feature_id="constitution_registry",
        epic_id="platform_constitution",
        title="Constitution Registry",
        status="planned",
        priority=1,
    ),
    "delegation_policy_engine": FeatureItem(
        feature_id="delegation_policy_engine",
        epic_id="dynamic_delegation",
        title="Delegation Policy Engine",
        status="planned",
        priority=2,
    ),
    "sandbox_executor": FeatureItem(
        feature_id="sandbox_executor",
        epic_id="runtime_sandbox",
        title="Sandbox Executor",
        status="planned",
        priority=3,
    ),
}


def all_features() -> Dict[str, FeatureItem]:
    return dict(FEATURES)


def get_feature(feature_id: str) -> Optional[FeatureItem]:
    return FEATURES.get(feature_id)
