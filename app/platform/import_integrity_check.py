"""Fails when any file under app/ imports an app.* module that doesn't exist.

Added in clean-up batch 4 after deletions left checks importing the retired app.main and a service
importing a removed module: module-level imports of missing modules only break when that file is
run, so CI must look for them explicitly.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    files = [p for p in (ROOT / "app").rglob("*.py") if "__pycache__" not in p.parts]
    modules = set()
    for path in files:
        parts = list(path.relative_to(ROOT).with_suffix("").parts)
        modules.add(".".join(parts[:-1] if parts[-1] == "__init__" else parts))
    broken = []
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module.startswith("app."):
                if node.module not in modules:
                    broken.append(f"{path.relative_to(ROOT)}: from {node.module} import ...")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name.startswith("app.") and name not in modules and name.rsplit(".", 1)[0] not in modules:
                        broken.append(f"{path.relative_to(ROOT)}: import {name}")
    assert not broken, "Imports of modules that don't exist:\n" + "\n".join(broken)
    print(f"IMPORT INTEGRITY CHECK PASSED ({len(files)} files)")


if __name__ == "__main__":
    main()
