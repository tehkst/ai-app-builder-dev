"""
Dependency analyzer — builds module dependency graphs and symbol call chains
from Python source files in the workspace.

Used by the enhanced FailureAnalyzer to provide richer context for repair.
Python 3.9 compatible — uses ast module for static analysis.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Module dependency graph
# ---------------------------------------------------------------------------

def build_dependency_graph(
    workspace_path: str,
    affected_paths: List[str],
    *,
    max_files: int = 100,
) -> List[Dict[str, Any]]:
    """
    Build a directed graph of module imports for the affected and related files.

    Returns list of edges: {"source": "module_a", "target": "module_b", "relation": "imports"}
    """
    root = Path(workspace_path).resolve()
    edges: List[Dict[str, Any]] = []

    # Collect all Python files in scope
    all_py_files = _collect_python_files(root, affected_paths, max_files)

    # Build module name -> file path mapping
    module_map = _build_module_map(root, all_py_files)

    # Parse imports for each affected file
    for py_file in all_py_files:
        resolved = root / py_file
        try:
            source = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        imports = _extract_imports(source)
        source_module = _file_to_module(py_file)

        for imp in imports:
            target_module = _resolve_import(imp, module_map)
            if target_module:
                edges.append({
                    "source": source_module,
                    "target": target_module,
                    "relation": "imports",
                })

    return edges


# ---------------------------------------------------------------------------
# Changed symbol detection
# ---------------------------------------------------------------------------

def detect_changed_symbols(
    workspace_path: str,
    affected_paths: List[str],
) -> List[Dict[str, str]]:
    """
    Identify which functions/classes/methods exist in the changed files.
    This is a static snapshot — differential analysis (before/after) requires
    workspace git state tracking.

    Returns: [{"name": "SymbolName", "type": "function|class|method", "file": "path"}]
    """
    root = Path(workspace_path).resolve()
    symbols: List[Dict[str, str]] = []

    for rel_path in affected_paths:
        if not rel_path.endswith(".py"):
            continue
        resolved = root / rel_path
        try:
            source = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.append({
                    "name": node.name,
                    "type": "function",
                    "file": rel_path,
                })
            elif isinstance(node, ast.AsyncFunctionDef):
                symbols.append({
                    "name": node.name,
                    "type": "function",
                    "file": rel_path,
                })
            elif isinstance(node, ast.ClassDef):
                symbols.append({
                    "name": node.name,
                    "type": "class",
                    "file": rel_path,
                })
                # Also find methods inside the class
                for child in ast.walk(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not node:
                        symbols.append({
                            "name": "%s.%s" % (node.name, child.name),
                            "type": "method",
                            "file": rel_path,
                        })

    return symbols


# ---------------------------------------------------------------------------
# Caller chain
# ---------------------------------------------------------------------------

def build_caller_chain(
    workspace_path: str,
    changed_symbols: List[Dict[str, str]],
    *,
    max_files: int = 100,
) -> List[Dict[str, Any]]:
    """
    Find all callers of the changed symbols across the codebase.

    Returns: [{"caller": "func_name", "callee": "symbol_name", "file": "path", "line": 42}]
    """
    root = Path(workspace_path).resolve()
    caller_chain: List[Dict[str, Any]] = []

    # Collect all Python files
    all_py_files = _collect_python_files(root, [], max_files)

    # Build set of changed symbol names for fast lookup
    changed_names: Set[str] = {s["name"] for s in changed_symbols}

    for py_file in all_py_files:
        resolved = root / py_file
        try:
            source = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        class CallVisitor(ast.NodeVisitor):
            def __init__(self):
                self.callers: List[Dict[str, Any]] = []
                self.current_func: Optional[str] = None

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                prev = self.current_func
                self.current_func = node.name
                self.generic_visit(node)
                self.current_func = prev

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                prev = self.current_func
                self.current_func = node.name
                self.generic_visit(node)
                self.current_func = prev

            def visit_Call(self, node: ast.Call) -> None:
                called = _call_name(node)
                if called and called in changed_names:
                    self.callers.append({
                        "caller": self.current_func or "<module>",
                        "callee": called,
                        "file": str(py_file),
                        "line": node.lineno,
                    })
                self.generic_visit(node)

        visitor = CallVisitor()
        visitor.visit(tree)
        caller_chain.extend(visitor.callers)

    return caller_chain


# ---------------------------------------------------------------------------
# Impacted modules
# ---------------------------------------------------------------------------

def assess_impacted_modules(
    dependency_graph: List[Dict[str, Any]],
    affected_paths: List[str],
) -> List[Dict[str, str]]:
    """
    From the dependency graph, find modules that depend on the affected paths.

    Returns: [{"module": "app.x", "file": "path/x.py", "reason": "imports app.affected"}]
    """
    affected_modules: Set[str] = set()
    for path in affected_paths:
        mod = _file_to_module(path)
        affected_modules.add(mod)

    impacted: List[Dict[str, str]] = []
    seen: Set[str] = set()

    for edge in dependency_graph:
        if edge["target"] in affected_modules:
            if edge["source"] not in seen:
                seen.add(edge["source"])
                impacted.append({
                    "module": edge["source"],
                    "file": _module_to_file(edge["source"]),
                    "reason": "imports changed module %s" % edge["target"],
                })

    return impacted


# ---------------------------------------------------------------------------
# Regression probability
# ---------------------------------------------------------------------------

def assess_regression_probability(
    changed_symbols: List[Dict[str, str]],
    caller_chain: List[Dict[str, Any]],
    impacted_modules: List[Dict[str, str]],
    affected_paths: List[str],
) -> Tuple[str, str]:
    """
    Assess the likelihood of regression based on the scope of changes.

    Returns: (probability: str, reason: str)
    """
    num_symbols = len(changed_symbols)
    num_callers = len(caller_chain)
    num_impacted = len(impacted_modules)
    num_files = len(affected_paths)

    # Heuristic scoring
    score = 0

    if num_files > 5:
        score += 3
    elif num_files > 2:
        score += 1

    if num_symbols > 10:
        score += 3
    elif num_symbols > 3:
        score += 1

    if num_callers > 20:
        score += 3
    elif num_callers > 5:
        score += 2
    elif num_callers > 0:
        score += 1

    if num_impacted > 10:
        score += 3
    elif num_impacted > 3:
        score += 2
    elif num_impacted > 0:
        score += 1

    if score >= 8:
        probability = "critical"
        reason = "Large blast radius: %d files changed, %d callers, %d impacted modules" % (
            num_files, num_callers, num_impacted,
        )
    elif score >= 5:
        probability = "high"
        reason = "Moderate blast radius: %d callers, %d impacted modules" % (
            num_callers, num_impacted,
        )
    elif score >= 2:
        probability = "medium"
        reason = "Limited blast radius: %d changed files, %d callers" % (
            num_files, num_callers,
        )
    else:
        probability = "low"
        reason = "Narrow change scope: %d files, %d symbols, no external callers" % (
            num_files, num_symbols,
        )

    return probability, reason


# ---------------------------------------------------------------------------
# Architecture violation check
# ---------------------------------------------------------------------------

def check_architecture_violations(
    affected_paths: List[str],
    architecture_constraints: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """
    Check if any affected paths violate known architecture constraints.

    Constraints are simple rules like:
    - "No new files in app/platform/core/"
    - "Do not modify app/platform/constitution/"
    - "Do not create modules outside app/platform/"

    Returns: (violation_detected: bool, detail: str)
    """
    if not architecture_constraints:
        return False, ""

    violations: List[str] = []

    for path in affected_paths:
        for constraint in architecture_constraints:
            constraint_lower = constraint.lower()

            # Pattern: "no new files in X"
            if "no new" in constraint_lower or "do not create" in constraint_lower:
                # Extract the restricted path
                for word in constraint_lower.split():
                    if "/" in word or "\\" in word:
                        restricted = word.strip("'\"/.")
                        if restricted in path.lower():
                            violations.append(
                                "File %s violates constraint: %s" % (path, constraint)
                            )

            # Pattern: "do not modify X"
            if "do not modify" in constraint_lower or "do not change" in constraint_lower:
                for word in constraint_lower.split():
                    if "/" in word or "\\" in word:
                        restricted = word.strip("'\"/.")
                        if restricted in path.lower():
                            violations.append(
                                "File %s violates constraint: %s" % (path, constraint)
                            )

    if violations:
        return True, "; ".join(violations)
    return False, ""


# ---------------------------------------------------------------------------
# Diagnosis confidence
# ---------------------------------------------------------------------------

def assess_diagnosis_confidence(
    stack_frames: List[Dict[str, str]],
    affected_paths: List[str],
    category: str,
) -> str:
    """
    Assess how confident we are in the failure diagnosis.

    Returns: "low" | "medium" | "high"
    """
    score = 0

    # Stack frames give us exact locations
    if stack_frames:
        score += 3

    # Affected paths from traceback
    if affected_paths:
        score += 1

    # Specific categories have higher diagnostic precision
    precise_categories = {"syntax-error", "import-error", "type-error", "assertion-failure"}
    vague_categories = {"general-failure", "timeout", "build-failure"}

    if category in precise_categories:
        score += 2
    elif category in vague_categories:
        score -= 1

    if score >= 4:
        return "high"
    elif score >= 2:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_python_files(
    root: Path,
    priority_paths: List[str],
    max_files: int,
) -> List[str]:
    """Collect Python files from workspace, prioritizing the given paths."""
    result: List[str] = []

    # Add priority paths first
    for path in priority_paths:
        if path.endswith(".py") and (root / path).is_file():
            result.append(path)

    # Walk the workspace for additional Python files
    for dirpath, dirnames, filenames in os.walk(str(root)):
        rel = Path(dirpath).relative_to(root)
        # Skip excluded directories
        if any(p in {"", ".", ".."} for p in rel.parts):
            continue
        if str(rel).startswith(".git") or "__pycache__" in str(rel):
            continue

        for fname in filenames:
            if fname.endswith(".py"):
                rel_path = str(rel / fname) if str(rel) != "." else fname
                if rel_path not in result:
                    result.append(rel_path)

        if len(result) >= max_files:
            break

    return result[:max_files]


def _build_module_map(root: Path, py_files: List[str]) -> Dict[str, str]:
    """Build a mapping of module name -> file path."""
    module_map: Dict[str, str] = {}
    for py_file in py_files:
        mod = _file_to_module(py_file)
        if mod not in module_map:
            module_map[mod] = py_file
    return module_map


def _file_to_module(file_path: str) -> str:
    """Convert a file path to a Python module name."""
    path = file_path.replace(os.sep, "/")
    if path.endswith(".py"):
        path = path[:-3]
    if path.endswith("/__init__"):
        path = path[:-9]
    return path.replace("/", ".")


def _module_to_file(module_name: str) -> str:
    """Convert a Python module name to a file path."""
    return module_name.replace(".", "/") + ".py"


def _extract_imports(source: str) -> List[str]:
    """Extract import targets from Python source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base = node.module
                for alias in node.names:
                    if alias.name == "*":
                        imports.append(base)
                    else:
                        imports.append("%s.%s" % (base, alias.name))
            elif node.level and node.level > 0:
                # Relative import — skip for now
                pass

    return imports


def _resolve_import(
    import_name: str,
    module_map: Dict[str, str],
) -> Optional[str]:
    """Resolve an import to a known module name in the workspace."""
    # Direct match
    if import_name in module_map:
        return import_name

    # Try parent modules
    parts = import_name.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in module_map:
            # ImportFrom names commonly include a symbol suffix. The graph
            # target must be the longest module that actually exists.
            return candidate

    return None


def _call_name(node: ast.Call) -> Optional[str]:
    """Extract the name of a function being called."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return _attribute_chain(node.func)
    return None


def _attribute_chain(node: ast.Attribute) -> str:
    """Build a dotted name from an attribute chain."""
    parts: List[str] = []
    current: Any = node
    while isinstance(current, ast.Attribute):
        parts.insert(0, current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.insert(0, current.id)
    return ".".join(parts)
