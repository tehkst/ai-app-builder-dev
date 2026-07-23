from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = PROJECT_ROOT / "app"


def module_name_from_path(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT).with_suffix("")
    if relative.name == "__init__":
        relative = relative.parent
    return ".".join(relative.parts)


def iter_python_files(root: Path = APP_ROOT) -> List[Path]:
    ignored_parts = {
        "__pycache__",
        ".venv",
        "venv",
        ".git",
        "node_modules",
    }

    files: List[Path] = []
    for path in root.rglob("*.py"):
        if any(part in ignored_parts for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def _assigned_names(target: ast.AST) -> Set[str]:
    names: Set[str] = set()

    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for item in target.elts:
            names.update(_assigned_names(item))

    return names


def get_defined_symbols(path: Path) -> Set[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return set()

    symbols: Set[str] = set()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                symbols.update(_assigned_names(target))

        elif isinstance(node, ast.AnnAssign):
            symbols.update(_assigned_names(node.target))

        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols.add(alias.asname or alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    symbols.add(alias.asname or alias.name)

    return symbols


def build_function_registry(root: Path = APP_ROOT) -> Dict[str, List[str]]:
    registry: Dict[str, List[str]] = {}

    for path in iter_python_files(root):
        module_name = module_name_from_path(path)
        symbols = get_defined_symbols(path)
        if path.name == "__init__.py" and "_PART_NAMES" in symbols:
            for child in path.parent.glob("part_*.py"):
                symbols.update(get_defined_symbols(child))
        existing = set(registry.get(module_name, []))
        registry[module_name] = sorted(existing | symbols)

    return registry


def get_from_imports(path: Path) -> List[Tuple[str, str, int]]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []

    imports: List[Tuple[str, str, int]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        if not node.module:
            continue

        if node.level != 0:
            continue

        if not node.module.startswith("app."):
            continue

        for alias in node.names:
            if alias.name == "*":
                continue
            imports.append((node.module, alias.name, node.lineno))

    return imports


def _submodule_exists(imported_module: str, imported_name: str, registry: Dict[str, List[str]]) -> bool:
    return f"{imported_module}.{imported_name}" in registry


def validate_internal_imports(root: Path = APP_ROOT) -> Dict[str, object]:
    registry = build_function_registry(root)
    missing: List[Dict[str, object]] = []

    for path in iter_python_files(root):
        importing_module = module_name_from_path(path)

        for imported_module, imported_name, line in get_from_imports(path):
            known_symbols = registry.get(imported_module)

            if known_symbols is None:
                if _submodule_exists(imported_module, imported_name, registry):
                    continue

                missing.append(
                    {
                        "file": str(path.relative_to(PROJECT_ROOT)),
                        "module": importing_module,
                        "line": line,
                        "imported_from": imported_module,
                        "missing_name": imported_name,
                        "reason": "Imported module not found in symbol registry",
                    }
                )
                continue

            if imported_name not in known_symbols and not _submodule_exists(
                imported_module, imported_name, registry
            ):
                missing.append(
                    {
                        "file": str(path.relative_to(PROJECT_ROOT)),
                        "module": importing_module,
                        "line": line,
                        "imported_from": imported_module,
                        "missing_name": imported_name,
                        "available_names": known_symbols,
                        "reason": "Imported name not defined in target module",
                    }
                )

    return {
        "success": len(missing) == 0,
        "checked_files": len(iter_python_files(root)),
        "registered_modules": len(registry),
        "missing_imports": missing,
    }


def main() -> None:
    result = validate_internal_imports()

    print(result)

    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
