"""Stack-agnostic scanners for the Codebase Health Check. Read-only; nothing from the codebase runs.

Each scanner returns plain data plus findings: (severity, title, detail) where severity is
"high", "medium" or "low". Secrets are never copied into results: only the file, line and kind.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.platform.codebase_health.inventory import Inventory

Finding = Tuple[str, str, str]

SECRET_PATTERNS = (
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Stripe live key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}\b")),
    ("OpenAI-style API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{32,}\b")),
    ("Hard-coded password", re.compile(r"(?i)\b(?:password|passwd|db_pass(?:word)?)\s*[:=]\s*['\"][^'\"\s]{6,}['\"]")),
)
SECRET_SCAN_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".rb", ".go", ".java", ".kt", ".cs", ".dart",
                        ".json", ".yml", ".yaml", ".env", ".ini", ".cfg", ".conf", ".xml", ".properties", ".sh", ".toml"}
KEY_FILE_SUFFIXES = {".pem", ".key"}
KEY_FILE_NAMES = {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
PLACEHOLDER = re.compile(r"(?i)example|changeme|placeholder|your[_-]|xxx|dummy|<.+>|\$\{|process\.env|getenv|os\.environ")
CI_FILES = (".github/workflows/", ".gitlab-ci.yml", "bitbucket-pipelines.yml", "Jenkinsfile", ".circleci/", "azure-pipelines.yml")
TEST_HINTS = re.compile(r"(^|/)(tests?|__tests__|spec|specs)/|(_test|\.test|\.spec|Test)\.[a-z]+$|(^|/)test_[^/]+\.py$")


def scan_dependencies(inv: Inventory) -> Tuple[Dict[str, Any], List[Finding]]:
    deps: Dict[str, Dict[str, str]] = {}
    findings: List[Finding] = []
    pkg = _json(inv.read("package.json"))
    if pkg:
        deps["npm"] = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    composer = _json(inv.read("composer.json"))
    if composer:
        deps["composer"] = {k: v for k, v in {**composer.get("require", {}), **composer.get("require-dev", {})}.items() if "/" in k}
    py_manifest = _python_manifest_deps(inv)
    req = inv.read("requirements.txt")
    if py_manifest and not req:
        deps["pip"] = py_manifest
    if req:
        py = {}
        for line in req.splitlines():
            line = line.split("#")[0].strip()
            if line and not line.startswith(("-", "git+", "http")):
                name = re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0]
                py[name] = line[len(name):].strip() or "*"
        deps["pip"] = py
    total = sum(len(v) for v in deps.values())
    unpinned = sorted(f"{eco}:{n}" for eco, items in deps.items() for n, v in items.items()
                      if v in {"*", "latest", "", "x"} or (eco == "pip" and not re.search(r"==|~=", v)))
    npm_lock = inv.has("pnpm-lock.yaml", "yarn.lock", "package-lock.json", "bun.lockb")
    py_lock = inv.has("poetry.lock", "Pipfile.lock", "uv.lock", "pdm.lock")
    if py_lock:  # ranges in pyproject/Pipfile are fine when a lockfile pins the real versions
        unpinned = [u for u in unpinned if not u.startswith("pip:")]
    missing_lock = ("npm" in deps and not npm_lock) or ("composer" in deps and not inv.has("composer.lock"))
    has_lock = not missing_lock and bool(deps)
    if missing_lock:
        findings.append(("medium", "No dependency lockfile",
                         "Installs can pull different versions over time, so the app may break without any code change."))
    if unpinned:
        findings.append(("medium" if len(unpinned) > 5 else "low", f"{len(unpinned)} dependencies without a fixed version",
                         "Versions float on every install; upgrades happen by accident instead of on purpose."))
    if total > 150:
        findings.append(("low", f"{total} direct dependencies", "A large dependency surface means more updates and more security advisories to track."))
    return {"ecosystems": {k: len(v) for k, v in deps.items()}, "total": total, "lockfile": has_lock,
            "unpinned": unpinned[:20], "names": {k: sorted(v)[:200] for k, v in deps.items()}}, findings


def scan_secrets(inv: Inventory) -> Tuple[Dict[str, Any], List[Finding]]:
    hits: List[Dict[str, Any]] = []
    for rel in inv.all_paths:
        name = Path(rel).name
        if name.startswith(".env") and not name.endswith((".example", ".sample", ".template")):
            hits.append({"file": rel, "line": None, "kind": "Committed .env file"})
            continue
        key_file = Path(rel).suffix.lower() in KEY_FILE_SUFFIXES or name in KEY_FILE_NAMES
        if not key_file and (Path(rel).suffix.lower() not in SECRET_SCAN_SUFFIXES or "lock" in name):
            continue
        text = inv.read(rel)
        if not text:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for kind, pattern in SECRET_PATTERNS:
                match = pattern.search(line)
                # judge the matched value only: `process.env.KEY || "sk-..."` still commits a real key
                if match and not PLACEHOLDER.search(match.group(0)):
                    hits.append({"file": rel, "line": number, "kind": kind})  # never the value itself
                    break
    findings: List[Finding] = []
    if hits:
        findings.append(("high", f"{len(hits)} possible secret(s) in the code",
                         "Keys or passwords stored in the code can be copied by anyone with access to it; they should be "
                         "rotated and moved to environment variables or a secrets manager."))
    return {"count": len(hits), "locations": hits[:50]}, findings


def scan_tests_and_ci(inv: Inventory) -> Tuple[Dict[str, Any], List[Finding]]:
    test_files = [p for p in inv.all_paths if TEST_HINTS.search(p) and Path(p).suffix in {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".php", ".rb", ".go", ".java", ".kt", ".dart", ".cs"}]
    ci = sorted({hint.rstrip("/") for hint in CI_FILES for p in inv.all_paths if p.startswith(hint) or p == hint})
    code_lines = sum(f.lines for f in inv.files if f.language not in {"HTML", "CSS"})
    test_lines = sum(f.lines for f in inv.files if f.path in set(test_files))
    findings: List[Finding] = []
    if not test_files:
        findings.append(("high", "No automated tests", "Every change has to be checked by hand, so updates and upgrades are risky and slow."))
    elif code_lines and test_lines / code_lines < 0.05:
        findings.append(("medium", "Very few tests", f"Tests are about {round(100 * test_lines / code_lines)}% of the code; most changes are untested."))
    if not ci:
        findings.append(("medium", "No continuous integration", "Nothing checks changes automatically before they reach the live app."))
    return {"test_files": len(test_files), "test_lines": test_lines, "code_lines": code_lines, "ci": ci}, findings


def scan_docs(inv: Inventory) -> Tuple[Dict[str, Any], List[Finding]]:
    readme = next((p for p in inv.all_paths if "/" not in p and p.lower().startswith("readme")), None)
    readme_text = inv.read(readme) if readme else ""
    setup = bool(re.search(r"(?i)install|setup|getting started|npm (run|install)|pip install|composer install|docker", readme_text or ""))
    env_example = inv.has(".env.example", ".env.sample", ".env.template")
    findings: List[Finding] = []
    if not readme or len(readme_text or "") < 300:
        findings.append(("medium", "Little or no documentation", "A new developer can't learn how to run or change the app without the original author."))
    elif not setup:
        findings.append(("low", "README has no setup steps", "Setting the app up again (new server, new developer) depends on memory."))
    if not env_example and any(Path(p).name.startswith(".env") for p in inv.all_paths):
        findings.append(("low", "No .env example", "The settings the app needs aren't documented."))
    return {"readme": readme, "readme_chars": len(readme_text or ""), "setup_steps": setup, "env_example": env_example}, findings


def scan_git(root: Path) -> Tuple[Dict[str, Any], List[Finding]]:
    if not (root / ".git").exists():
        return {"available": False}, [("low", "No git history provided", "Without history we can't see how actively the code was maintained.")]

    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    commits = int(git("rev-list", "--count", "HEAD") or 0)
    last = git("log", "-1", "--format=%cI")
    roots = git("rev-list", "--max-parents=0", "HEAD").splitlines()
    first = git("log", "-1", "--format=%cI", roots[-1]) if roots else ""
    authors = len(set(filter(None, git("log", "--format=%ae").splitlines())))
    days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).days if last else None
    findings: List[Finding] = []
    if days_since is not None and days_since > 365:
        findings.append(("medium", f"No changes for {days_since // 30} months",
                         "Code that hasn't been touched for a long time usually has outdated, unpatched dependencies."))
    if authors == 1 and commits > 20:
        findings.append(("low", "One person ever worked on it", "All knowledge sits with one developer; handover risk is high."))
    return {"available": True, "commits": commits, "last_commit": last, "first_commit": first, "authors": authors,
            "days_since_last_commit": days_since}, findings


def scan_size(inv: Inventory) -> Tuple[Dict[str, Any], List[Finding]]:
    big = inv.large_files()
    findings: List[Finding] = []
    if len(big) >= 5:
        findings.append(("medium", f"{len(big)}+ very large files", "Files over 500 lines are harder to change safely; they're where bugs concentrate."))
    elif big:
        findings.append(("low", f"{len(big)} very large file(s)", "Worth splitting when they next need changes."))
    return {"files": len(inv.files), "lines": sum(f.lines for f in inv.files), "by_language": inv.lines_by_language,
            "generated_files": len(inv.generated), "generated_lines": sum(f.lines for f in inv.generated), "source": inv.source,
            "largest": [{"path": f.path, "lines": f.lines} for f in big]}, findings


def scan_license(inv: Inventory) -> Tuple[Dict[str, Any], List[Finding]]:
    lic = next((p for p in inv.all_paths if "/" not in p and p.upper().startswith(("LICENSE", "LICENCE", "COPYING"))), None)
    kind = None
    if lic:
        text = (inv.read(lic) or "")[:2000]
        for label, needle in (("MIT", "MIT License"), ("Apache-2.0", "Apache License"), ("GPL", "GNU GENERAL PUBLIC"),
                              ("BSD", "BSD"), ("Proprietary", "All rights reserved")):
            if needle.lower() in text.lower():
                kind = label
                break
    findings: List[Finding] = []
    if not lic:
        findings.append(("low", "No licence file", "Who owns the code isn't stated; worth confirming in the client contract."))
    return {"file": lic, "kind": kind}, findings


def _python_manifest_deps(inv: Inventory) -> Dict[str, str]:
    """Dependencies from pyproject.toml ([project] or Poetry) and Pipfile; TOML parsed, never executed."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover - older interpreters: skip rather than guess
        return {}
    found: Dict[str, str] = {}
    for rel in ("pyproject.toml", "Pipfile"):
        text = inv.read(rel)
        if not text:
            continue
        try:
            data = tomllib.loads(text)
        except (tomllib.TOMLDecodeError, ValueError):
            continue
        project = data.get("project", {})
        for spec in list(project.get("dependencies", [])) + [d for group in project.get("optional-dependencies", {}).values() for d in group]:
            name = re.split(r"[<>=!~\[; ]", spec.strip(), maxsplit=1)[0]
            if name:
                found[name] = spec[len(name):].strip() or "*"
        poetry = data.get("tool", {}).get("poetry", {})
        sections = [poetry.get("dependencies", {}), poetry.get("dev-dependencies", {})]
        sections += [g.get("dependencies", {}) for g in poetry.get("group", {}).values()]
        sections += [data.get("packages", {}), data.get("dev-packages", {})]  # Pipfile
        for section in sections:
            for name, value in section.items():
                if name.lower() == "python":
                    continue
                version = value if isinstance(value, str) else (value.get("version", "*") if isinstance(value, dict) else "*")
                found[name] = version if version.startswith(("=", "<", ">", "~", "!", "^")) or version == "*" else f"=={version}"
    return found


def _json(text):
    try:
        return json.loads(text) if text else {}
    except ValueError:
        return {}
