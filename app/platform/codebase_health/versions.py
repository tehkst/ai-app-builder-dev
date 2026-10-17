"""Runtime/framework versions and exact locked package versions of a client codebase (read-only).

Feeds the end-of-life lookup (endoflife.date) and the vulnerability lookup (OSV.dev). Everything is
parsed from files (manifests, lockfiles, Dockerfiles, version files); nothing is executed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from app.platform.codebase_health.inventory import Inventory

# endoflife.date product -> (label, how many version parts make a release cycle)
PRODUCTS = {
    "nodejs": ("Node.js", 1), "php": ("PHP", 2), "python": ("Python", 2), "laravel": ("Laravel", 1),
    "django": ("Django", 2), "wordpress": ("WordPress", 2), "nextjs": ("Next.js", 1), "react": ("React", 1),
}
LOCK_LIMIT = 1000


def _version(text: str) -> Optional[str]:
    """First concrete version in a constraint or tag: '^8.1|^8.2' -> '8.1', 'v18.17.0' -> '18.17.0'."""
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", text or "")
    return ".".join(g for g in match.groups() if g is not None) if match else None


def _cycle(product: str, version: str) -> str:
    parts = version.split(".")
    return ".".join(parts[: PRODUCTS[product][1]]) if len(parts) >= PRODUCTS[product][1] else parts[0]


def _add(found: Dict[str, Dict[str, str]], product: str, raw: Optional[str], source: str) -> None:
    version = _version(raw or "")
    if version and product not in found:
        found[product] = {"product": product, "label": PRODUCTS[product][0], "version": version,
                          "cycle": _cycle(product, version), "source": source}


def _json(inv: Inventory, rel: str) -> dict:
    try:
        return json.loads(inv.read(rel) or "{}")
    except ValueError:
        return {}


def detect_versions(inv: Inventory) -> List[Dict[str, str]]:
    found: Dict[str, Dict[str, str]] = {}
    locked = {(p["ecosystem"], p["name"].lower()): p["version"] for p in locked_packages(inv)}

    # Exact locked versions first (most precise), then declared constraints and runtime files.
    for product, eco, name in (("laravel", "Packagist", "laravel/framework"), ("django", "PyPI", "django"),
                               ("nextjs", "npm", "next"), ("react", "npm", "react")):
        if (eco, name) in locked:
            _add(found, product, locked[(eco, name)], "lockfile")
    pkg = _json(inv, "package.json")
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    _add(found, "nextjs", deps.get("next"), "package.json")
    _add(found, "react", deps.get("react"), "package.json")
    _add(found, "nodejs", (pkg.get("engines") or {}).get("node"), "package.json engines")
    for rel in (".nvmrc", ".node-version"):
        _add(found, "nodejs", inv.read(rel), rel)
    composer = _json(inv, "composer.json")
    require = composer.get("require", {})
    _add(found, "php", require.get("php"), "composer.json")
    _add(found, "laravel", require.get("laravel/framework"), "composer.json")
    wp = inv.read("wp-includes/version.php") or ""
    match = re.search(r"\$wp_version\s*=\s*['\"]([^'\"]+)['\"]", wp)
    _add(found, "wordpress", match.group(1) if match else None, "wp-includes/version.php")
    for rel in (".python-version", "runtime.txt"):
        _add(found, "python", inv.read(rel), rel)
    pyproject = inv.read("pyproject.toml") or ""
    match = re.search(r"requires-python\s*=\s*['\"]([^'\"]+)['\"]", pyproject) or re.search(r"(?m)^python\s*=\s*['\"]([^'\"]+)['\"]", pyproject)
    _add(found, "python", match.group(1) if match else None, "pyproject.toml")
    req = inv.read("requirements.txt") or ""
    match = re.search(r"(?im)^django\s*==\s*([\d.]+)", req)
    _add(found, "django", match.group(1) if match else None, "requirements.txt")
    for rel in inv.all_paths:
        if Path(rel).name.lower().startswith("dockerfile"):
            for image, tag in re.findall(r"(?im)^\s*FROM\s+(?:[\w.-]+/)?(node|php|python):([\w.-]+)", inv.read(rel) or ""):
                _add(found, {"node": "nodejs"}.get(image.lower(), image.lower()), tag, rel)
    return list(found.values())


def locked_packages(inv: Inventory) -> List[Dict[str, str]]:
    """Exact versions from lockfiles: npm (package-lock, pnpm), Packagist (composer.lock), PyPI."""
    out: List[Dict[str, str]] = []
    seen = set()

    def add(eco: str, name: str, version: str) -> None:
        version = (version or "").lstrip("v=").strip()
        key = (eco, name, version)
        if name and re.match(r"\d", version) and key not in seen and len(out) < LOCK_LIMIT:
            seen.add(key)
            out.append({"ecosystem": eco, "name": name, "version": version})

    npm_lock = _json(inv, "package-lock.json")
    for path, meta in (npm_lock.get("packages") or {}).items():
        if path.startswith("node_modules/") or "/node_modules/" in path:
            add("npm", path.split("node_modules/")[-1], meta.get("version", ""))
    for name, meta in (npm_lock.get("dependencies") or {}).items():  # lockfile v1
        add("npm", name, (meta or {}).get("version", ""))
    pnpm = inv.read("pnpm-lock.yaml")
    if pnpm:
        try:
            import yaml

            data = yaml.safe_load(pnpm) or {}
        except Exception:
            data = {}
        for key in (data.get("packages") or {}):
            spec = str(key).lstrip("/").split("(")[0]
            name, _, version = spec.rpartition("@")
            add("npm", name, version)
    composer_lock = _json(inv, "composer.lock")
    for section in ("packages", "packages-dev"):
        for item in composer_lock.get(section) or []:
            add("Packagist", item.get("name", ""), item.get("version", ""))
    poetry = inv.read("poetry.lock")
    if poetry:
        for name, version in re.findall(r'\[\[package\]\]\s*name\s*=\s*"([^"]+)"\s*version\s*=\s*"([^"]+)"', poetry):
            add("PyPI", name, version)
    pipfile_lock = _json(inv, "Pipfile.lock")
    for section in ("default", "develop"):
        for name, meta in (pipfile_lock.get(section) or {}).items():
            add("PyPI", name, (meta or {}).get("version", ""))
    for line in (inv.read("requirements.txt") or "").splitlines():
        match = re.match(r"\s*([A-Za-z0-9_.\-]+)\s*==\s*([\w.]+)", line)
        if match:
            add("PyPI", match.group(1), match.group(2))
    return out
