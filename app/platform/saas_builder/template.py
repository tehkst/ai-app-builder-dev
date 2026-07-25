from __future__ import annotations

from pathlib import Path
from typing import Any


TEMPLATE_ROOT = Path(__file__).with_name("reference_app")


def reference_file_changes(application_id: str, spec: dict[str, Any]) -> list[dict[str, str]]:
    prefix = "generated_apps/%s" % application_id.lower()
    replacements = {
        "__APPLICATION_NAME__": str(spec["product_name"]),
        "__APPLICATION_ID__": application_id,
        "__APPLICATION_DB_PREFIX__": application_id.lower().replace("-", "_"),
    }
    changes = []
    for source in sorted(
        path for path in TEMPLATE_ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    ):
        content = source.read_text(encoding="utf-8")
        for old, new in replacements.items():
            content = content.replace(old, new)
        changes.append({
            "path": "%s/%s" % (prefix, source.relative_to(TEMPLATE_ROOT).as_posix()),
            "operation": "write",
            "content": content,
        })
    return changes


def validation_plan(application_id: str) -> list[str]:
    root = "generated_apps/%s" % application_id.lower()
    return [
        "python3 -m compileall %s" % root,
        "python3 %s/reference_acceptance.py --local-contract" % root,
        "docker build %s" % root,
    ]
