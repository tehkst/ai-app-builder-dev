"""
Edit executor — applies concrete edit operations to real workspace files.

Validates every edit before applying: path containment, operation support,
syntax checks, fingerprint recording. Never bypasses workspace boundaries.

Strategy priority (prefer minimal changes for git history preservation):
  1. ast_replace  — replace a specific function/class/method by AST name
  2. apply_patch  — apply a unified diff to the existing file
  3. replace_file — full-file replacement (fallback only)

When no strategy is specified or a higher-priority strategy fails,
the executor falls back through the chain automatically.
"""
from __future__ import annotations

import ast
import hashlib
import re
from difflib import unified_diff
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.platform.coding_agent.models import EditContract, EditOperation
from app.platform.coding_agent.policy import (
    EXCLUDED_PATH_PREFIXES,
    MAX_CHANGED_FILES_HARD_LIMIT,
    MAX_FILE_SIZE_BYTES,
)


# Strategy priority order (index 0 = most preferred)
STRATEGY_PRIORITY: List[str] = ["ast_replace", "apply_patch", "replace_file"]

# Allowed strategies
ALLOWED_STRATEGIES: set = {"ast_replace", "apply_patch", "replace_file"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_edits(
    contract: EditContract,
    workspace_path: str,
    *,
    changed_files: Optional[List[str]] = None,
    file_fingerprints: Optional[Dict[str, Dict[str, str]]] = None,
) -> Tuple[List[str], Dict[str, Dict[str, str]], List[Dict[str, Any]]]:
    """
    Apply all edits from the contract to the workspace.

    For each edit, tries strategies in priority order (ast_replace → apply_patch
    → replace_file), falling back when a higher-priority strategy fails.

    Returns:
        (changed_paths, updated_fingerprints, validation_warnings)
        Each warning includes 'strategy_used' indicating which strategy was applied.
    """
    root = Path(workspace_path).resolve()
    applied: List[str] = []
    fingerprints: Dict[str, Dict[str, str]] = dict(file_fingerprints or {})
    warnings: List[Dict[str, Any]] = []

    if not contract.edits:
        warnings.append({"severity": "warn", "message": "Edit contract contains no edits."})
        return applied, fingerprints, warnings

    if len(contract.edits) > MAX_CHANGED_FILES_HARD_LIMIT:
        warnings.append({
            "severity": "block",
            "message": "Edit contract exceeds hard file limit (%d > %d)." % (
                len(contract.edits), MAX_CHANGED_FILES_HARD_LIMIT,
            ),
        })
        return applied, fingerprints, warnings

    for edit in contract.edits:
        result = _apply_single_edit(edit, root, fingerprints, changed_files or [])
        if result is None:
            warnings.append({
                "severity": "fail",
                "path": edit.path,
                "message": "Edit application blocked by safety check (all strategies failed).",
            })
            continue
        path, before_fp, after_fp, strategy_used = result
        applied.append(path)
        fingerprints[path] = {
            "before": before_fp,
            "after": after_fp,
            "strategy": strategy_used,
        }

    return applied, fingerprints, warnings


def record_pre_edit_fingerprint(path: str, workspace_path: str) -> str:
    """Record SHA-256 fingerprint of a file before editing."""
    resolved = _resolve_path(path, Path(workspace_path).resolve())
    if resolved is None or not resolved.is_file():
        return ""
    content = resolved.read_text(encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def record_post_edit_fingerprint(path: str, workspace_path: str) -> str:
    """Record SHA-256 fingerprint of a file after editing."""
    return record_pre_edit_fingerprint(path, workspace_path)


# ---------------------------------------------------------------------------
# Core: strategy-ordered edit application
# ---------------------------------------------------------------------------

def _apply_single_edit(
    edit: EditOperation,
    root: Path,
    fingerprints: Dict[str, Dict[str, str]],
    changed_files: List[str],
) -> Optional[Tuple[str, str, str, str]]:
    """
    Apply one edit, trying strategies in priority order.
    Returns (path, before_fp, after_fp, strategy_used) or None.
    """
    # --- Phase 0: Universal safety checks ---
    resolved = _resolve_path(edit.path, root)
    if resolved is None:
        return None

    if edit.operation not in {"create", "update", "delete"}:
        return None

    if not edit.source_evidence:
        return None

    if edit.path in changed_files:
        return None

    if len(edit.content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        return None

    # --- Phase 1: Determine effective strategy order ---
    strategies = _effective_strategies(edit)

    # --- Phase 2: Try each strategy ---
    for strategy in strategies:
        result = _try_strategy(edit, resolved, strategy)
        if result is not None:
            before_fp, after_fp = result
            return (edit.path, before_fp, after_fp, strategy)

    return None  # All strategies failed


def _effective_strategies(edit: EditOperation) -> List[str]:
    """
    Determine which strategies to try and in what order.

    If the model explicitly requested a strategy, try that first, then fall back.
    If no strategy specified, try ast_replace if target_symbol is present,
    then apply_patch, then replace_file.
    """
    specified = edit.strategy.strip()

    # Validate the specified strategy
    if specified in ALLOWED_STRATEGIES:
        # Try specified first, then fall back through the rest
        ordered = [specified]
        for s in STRATEGY_PRIORITY:
            if s not in ordered:
                ordered.append(s)
        return ordered

    # No valid strategy specified — use auto-detection priority
    ordered: List[str] = []

    # If target_symbol is provided, ast_replace is likely intended
    if edit.target_symbol:
        ordered.append("ast_replace")

    # Add remaining strategies in priority order
    for s in STRATEGY_PRIORITY:
        if s not in ordered:
            ordered.append(s)

    return ordered


def _try_strategy(
    edit: EditOperation,
    resolved: Path,
    strategy: str,
) -> Optional[Tuple[str, str]]:
    """
    Try applying the edit with a specific strategy.
    Returns (before_fingerprint, after_fingerprint) or None.
    """
    if strategy == "ast_replace":
        return _apply_ast_replace(edit, resolved)
    elif strategy == "apply_patch":
        return _apply_unified_diff(edit, resolved)
    elif strategy == "replace_file":
        return _apply_file_replace(edit, resolved)
    return None


# ---------------------------------------------------------------------------
# Strategy 1: AST-based replacement (highest priority)
# ---------------------------------------------------------------------------

def _apply_ast_replace(
    edit: EditOperation,
    resolved: Path,
) -> Optional[Tuple[str, str]]:
    """
    Replace a specific function/class/method by name using AST.

    Requires:
    - edit.target_symbol: name of the function/class/method to replace
    - edit.target_type: "function" | "class" | "method"
    - edit.content: complete source code for the replacement symbol
    - File must exist and be valid Python
    """
    if not edit.target_symbol:
        return None  # ast_replace requires a target_symbol

    if edit.operation == "create":
        return None  # AST replace only works for updates

    if edit.operation == "delete":
        return _apply_ast_delete(edit, resolved)

    # Read original file
    try:
        original = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None

    # Validate replacement content syntax
    if not _validate_python_syntax(edit.content):
        return None

    # Parse and transform
    try:
        tree = ast.parse(original)
    except SyntaxError:
        return None  # Can't AST-replace a file with invalid syntax

    # Find and replace the target symbol
    transformer = _AstSymbolReplacer(edit.target_symbol, edit.target_type, edit.content)
    try:
        new_tree = transformer.visit(tree)
    except _AstReplaceError:
        return None

    if not transformer.found:
        return None  # Target symbol not found in file

    # Unparse the modified AST back to source
    try:
        new_source = ast.unparse(new_tree)
    except Exception:
        return None

    # Reconstruct with original formatting (unparse loses comments/whitespace)
    # For now, use the unparsed result directly — it's syntactically correct
    new_source = _reconstruct_with_formatting(new_source, original)

    # Validate the result
    if not _validate_python_syntax(new_source):
        return None

    if _is_placeholder(new_source):
        return None

    # Reject unchanged
    if new_source == original:
        return None

    before_fp = hashlib.sha256(original.encode("utf-8")).hexdigest()

    # Write back
    try:
        resolved.write_text(new_source, encoding="utf-8")
    except (OSError, PermissionError):
        return None

    after_fp = hashlib.sha256(new_source.encode("utf-8")).hexdigest()
    return (before_fp, after_fp)


def _apply_ast_delete(
    edit: EditOperation,
    resolved: Path,
) -> Optional[Tuple[str, str]]:
    """Delete a specific symbol by name using AST."""
    if not edit.target_symbol:
        return None

    try:
        original = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None

    try:
        tree = ast.parse(original)
    except SyntaxError:
        return None

    deleter = _AstSymbolDeleter(edit.target_symbol, edit.target_type)
    try:
        new_tree = deleter.visit(tree)
    except _AstReplaceError:
        return None

    if not deleter.found:
        return None

    try:
        new_source = ast.unparse(new_tree)
    except Exception:
        return None

    new_source = _reconstruct_with_formatting(new_source, original)
    before_fp = hashlib.sha256(original.encode("utf-8")).hexdigest()

    try:
        resolved.write_text(new_source, encoding="utf-8")
    except (OSError, PermissionError):
        return None

    after_fp = hashlib.sha256(new_source.encode("utf-8")).hexdigest()
    return (before_fp, after_fp)


class _AstReplaceError(Exception):
    """Internal signal that AST replacement failed for this file."""
    pass


class _AstSymbolReplacer(ast.NodeTransformer):
    """AST transformer that replaces a named function/class with new source."""

    def __init__(self, target_name: str, target_type: str, replacement_source: str) -> None:
        self.target_name = target_name
        self.target_type = target_type
        self.replacement_source = replacement_source
        self.found = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        if node.name == self.target_name and self.target_type in ("function", "method"):
            return self._replace(node)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        if node.name == self.target_name and self.target_type in ("function", "method"):
            return self._replace(node)
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        if node.name == self.target_name and self.target_type == "class":
            return self._replace(node)
        return self.generic_visit(node)

    def _replace(self, node: ast.AST) -> ast.AST:
        try:
            replacement_tree = ast.parse(self.replacement_source)
        except SyntaxError:
            raise _AstReplaceError("Replacement source has invalid syntax.")

        # Extract the body of the replacement (first node)
        if isinstance(replacement_tree, ast.Module) and replacement_tree.body:
            replacement_node = replacement_tree.body[0]
            # Preserve decorators from the original if it has them
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if hasattr(node, "decorator_list"):
                    replacement_node.decorator_list = node.decorator_list  # type: ignore[attr-defined]
            self.found = True
            return replacement_node

        raise _AstReplaceError("Could not parse replacement into a valid symbol.")


class _AstSymbolDeleter(ast.NodeTransformer):
    """AST transformer that removes a named function/class."""

    def __init__(self, target_name: str, target_type: str) -> None:
        self.target_name = target_name
        self.target_type = target_type
        self.found = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if node.name == self.target_name and self.target_type in ("function", "method"):
            self.found = True
            return None  # Remove this node
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        if node.name == self.target_name and self.target_type in ("function", "method"):
            self.found = True
            return None
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        if node.name == self.target_name and self.target_type == "class":
            self.found = True
            return None
        return self.generic_visit(node)


def _reconstruct_with_formatting(new_source: str, original: str) -> str:
    """
    Best-effort reconstruction to preserve original formatting.
    ast.unparse() loses comments, blank lines, and some whitespace.
    This is a minimal pass — full formatting preservation is a future enhancement.
    """
    # Preserve shebang and encoding lines from original
    original_lines = original.split("\n")
    new_lines = new_source.split("\n")

    # If original starts with shebang or encoding, keep those lines
    prefix_lines: List[str] = []
    for line in original_lines:
        stripped = line.strip()
        if stripped.startswith("#!") or stripped.startswith("# -*-") or stripped.startswith("# coding"):
            prefix_lines.append(line)
        elif stripped == "" and not prefix_lines:
            prefix_lines.append(line)
        else:
            break

    if prefix_lines:
        result = "\n".join(prefix_lines) + "\n" + "\n".join(
            l for l in new_lines if l.strip() not in {p.strip() for p in prefix_lines}
        )
        return result

    return new_source


# ---------------------------------------------------------------------------
# Strategy 2: Unified diff (apply_patch)
# ---------------------------------------------------------------------------

def _apply_unified_diff(
    edit: EditOperation,
    resolved: Path,
) -> Optional[Tuple[str, str]]:
    """
    Apply a unified diff to the existing file.

    Supports:
    - update: apply diff to existing file
    - create: diff content is the new file (treated as full content)
    - delete: not applicable via diff

    Falls back gracefully if the diff does not apply cleanly.
    """
    if edit.operation == "delete":
        return None  # Diffs don't make sense for deletions

    if edit.operation == "create":
        # For creates, treat diff content as the full new file
        return _apply_file_replace(edit, resolved)

    # update: apply patch to existing file
    try:
        original = resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None

    before_fp = hashlib.sha256(original.encode("utf-8")).hexdigest()

    # Validate the content looks like a diff
    if not _looks_like_diff(edit.content):
        return None  # Not a diff — fall back to replace_file

    # Try to apply the patch
    try:
        patched = _apply_patch_to_text(original, edit.content)
    except _PatchError:
        return None  # Patch failed — fall back

    if not patched or patched == original:
        return None

    if _is_placeholder(patched):
        return None

    # Validate Python syntax for .py files
    if edit.path.endswith(".py") and not _validate_python_syntax(patched):
        return None

    if len(patched.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
        return None

    try:
        resolved.write_text(patched, encoding="utf-8")
    except (OSError, PermissionError):
        return None

    after_fp = hashlib.sha256(patched.encode("utf-8")).hexdigest()
    return (before_fp, after_fp)


def _looks_like_diff(content: str) -> bool:
    """Heuristic: does this content look like a unified diff?"""
    stripped = content.strip()
    # Unified diffs have lines starting with ---, +++, @@
    has_header = (
        re.search(r'^---\s', stripped, re.MULTILINE) is not None
        or re.search(r'^\+\+\+\s', stripped, re.MULTILINE) is not None
    )
    has_hunk = re.search(r'^@@\s', stripped, re.MULTILINE) is not None
    return has_header and has_hunk


class _PatchError(Exception):
    """Patch could not be applied."""
    pass


def _apply_patch_to_text(original: str, patch_text: str) -> str:
    """
    Apply a unified diff patch to original text.

    Implements a simplified but safe patch algorithm:
    - Parse hunks from the diff
    - Locate each hunk in the original text by context lines
    - Replace old lines with new lines
    - Validate that the resulting text is consistent
    """
    original_lines = original.splitlines(keepends=True)
    hunks = _parse_hunks(patch_text)
    if not hunks:
        raise _PatchError("No hunks found in patch.")

    result_lines = list(original_lines)
    offset = 0  # Tracks line-number shifts from applied hunks

    for hunk in hunks:
        applied = _apply_hunk(result_lines, hunk, offset)
        if applied is False:
            raise _PatchError("Hunk failed to apply at context.")
        offset = applied

    result = "".join(result_lines)

    # Sanity check: result should not be wildly larger or smaller
    if abs(len(result) - len(original)) > max(100000, len(original) * 2):
        raise _PatchError("Patch result is suspiciously large or small.")

    return result


def _parse_hunks(patch_text: str) -> List[Dict[str, Any]]:
    """Parse unified diff into structured hunks."""
    hunks: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    context_lines: List[str] = []
    new_lines: List[str] = []
    in_hunk = False

    for line in patch_text.splitlines(keepends=False):
        line_with_newline = line + "\n"

        if line.startswith("@@") and not in_hunk:
            # Start of a new hunk
            if current is not None and context_lines:
                current["context"] = context_lines
                current["new_lines"] = new_lines
                hunks.append(current)

            current = {"header": line, "context": [], "new_lines": []}
            context_lines = []
            new_lines = []
            in_hunk = True
            continue

        if line.startswith("@@") and in_hunk:
            # Next hunk starting — save current
            if current is not None and context_lines:
                current["context"] = context_lines
                current["new_lines"] = new_lines
                hunks.append(current)
            current = {"header": line, "context": [], "new_lines": []}
            context_lines = []
            new_lines = []
            continue

        if not in_hunk:
            continue

        if line.startswith(" "):
            # Context line (present in both old and new)
            context_lines.append(line[1:])
            new_lines.append(line[1:])
        elif line.startswith("-"):
            # Removed line (in old, not in new)
            context_lines.append(line[1:])
        elif line.startswith("+"):
            # Added line (in new, not in old)
            new_lines.append(line[1:])
        # Skip other lines (comments, empty)

    # Save final hunk
    if current is not None and context_lines:
        current["context"] = context_lines
        current["new_lines"] = new_lines
        hunks.append(current)

    return hunks


def _apply_hunk(result_lines: List[str], hunk: Dict[str, Any], offset: int) -> Any:
    """
    Try to apply a hunk to result_lines, searching from the given offset.
    Returns new offset on success, or False on failure.
    """
    context = hunk.get("context", [])
    new_lines_list = hunk.get("new_lines", [])

    if not context:
        return False

    # Find the context in the current result
    context_len = len(context)
    for i in range(max(0, offset - 3), len(result_lines) - context_len + 1):
        # Try matching from position i
        match = True
        for j in range(context_len):
            expected = context[j]
            actual = result_lines[i + j].rstrip("\n")
            if expected != actual and not (
                # Allow whitespace-only differences
                expected.strip() == actual.strip()
                and (expected.lstrip() != actual.lstrip())
            ):
                match = False
                break
        if match:
            # Found the context — replace old context with new lines
            del result_lines[i:i + context_len]
            for idx, new_line in enumerate(new_lines_list):
                result_lines.insert(i + idx, new_line + "\n")
            return i + len(new_lines_list)  # New offset

    return False  # Context not found


# ---------------------------------------------------------------------------
# Strategy 3: Full-file replacement (fallback)
# ---------------------------------------------------------------------------

def _apply_file_replace(
    edit: EditOperation,
    resolved: Path,
) -> Optional[Tuple[str, str]]:
    """
    Full-file replacement — the lowest-priority strategy.
    Used when AST replacement and patch application both fail.
    """
    before_fp = ""

    if edit.operation == "update":
        if not resolved.is_file():
            return None
        try:
            original = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None
        before_fp = hashlib.sha256(original.encode("utf-8")).hexdigest()

        if edit.content == original:
            return None
        if _is_placeholder(edit.content):
            return None

    elif edit.operation == "create":
        if resolved.is_file():
            return None
        if not edit.content.strip():
            return None
        if _is_placeholder(edit.content):
            return None

    elif edit.operation == "delete":
        if not resolved.is_file():
            return None
        try:
            original = resolved.read_text(encoding="utf-8")
            before_fp = hashlib.sha256(original.encode("utf-8")).hexdigest()
        except (OSError, UnicodeError):
            return None

    # Python syntax validation for .py files
    if edit.operation in {"create", "update"} and edit.path.endswith(".py"):
        if not _validate_python_syntax(edit.content):
            return None

    # Encoding validation
    try:
        edit.content.encode("utf-8")
    except UnicodeError:
        return None

    # Apply
    try:
        if edit.operation == "create":
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(edit.content, encoding="utf-8")
        elif edit.operation == "update":
            resolved.write_text(edit.content, encoding="utf-8")
        elif edit.operation == "delete":
            resolved.unlink()
    except (OSError, PermissionError):
        return None

    after_fp = ""
    if edit.operation != "delete":
        try:
            new_content = resolved.read_text(encoding="utf-8")
            after_fp = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
        except (OSError, UnicodeError):
            return None
    else:
        after_fp = "deleted"

    return (before_fp, after_fp)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _resolve_path(relative_path: str, root: Path) -> Optional[Path]:
    """Validate and resolve a relative path within the workspace root."""
    path = relative_path.strip()

    if not path or path.startswith("/") or "\\" in path:
        return None

    candidate = Path(path)
    if any(part in {"", ".", ".."} for part in candidate.parts):
        return None

    if any(str(candidate).startswith(prefix) for prefix in EXCLUDED_PATH_PREFIXES):
        return None

    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None

    return resolved


def _is_placeholder(content: str) -> bool:
    """Detect common placeholder patterns that indicate non-executable content."""
    stripped = content.strip().lower()
    placeholders = [
        "# todo", "# implement", "# add logic",
        "pass  # todo", "# your code here",
        "# modify this function", "# update as needed",
        "raise notimplementederror",
    ]
    return any(ph in stripped for ph in placeholders)


def _validate_python_syntax(source: str) -> bool:
    """Validate Python source using compile() for 3.9 compatibility."""
    try:
        compile(source, "<edit>", "exec")
        return True
    except SyntaxError:
        return False
