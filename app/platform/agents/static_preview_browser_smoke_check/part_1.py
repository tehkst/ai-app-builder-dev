# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List
from app.platform.agents.approval_gated_static_preview_materialization_check import (
    run_check as run_v90_materialization_check,
)
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.materialization_approval_record_service import (
    create_materialization_approval_record,
)
from app.platform.services.materialization_execution_gate_service import (
    attempt_materialization_execution,
)

def _extract_static_asset_paths(html: str) -> List[str]:
    assets: List[str] = []

    for match in re.finditer(r"<link[^>]+href=[\"']([^\"']+)[\"']", html, re.IGNORECASE):
        assets.append(match.group(1))

    for match in re.finditer(r"<script[^>]+src=[\"']([^\"']+)[\"']", html, re.IGNORECASE):
        assets.append(match.group(1))

    return [
        asset
        for asset in assets
        if asset
        and not asset.startswith(("http://", "https://", "//", "data:", "#"))
    ]

def _safe_asset_path(workspace_root: Path, asset_path: str) -> Path:
    target = (workspace_root / asset_path).resolve()
    if not str(target).startswith(str(workspace_root.resolve())):
        raise ValueError(f"Asset path escapes workspace root: {asset_path}")
    return target
