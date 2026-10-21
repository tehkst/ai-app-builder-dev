"""Read what each source file depends on, without running anything (step 4d).

Deliberately small, dependency-free scanners instead of full parsers: comments are removed with a
string-aware pass, then the forms that create dependencies are matched. They find the links that
matter for "what breaks if we change this?" in small-business code:

- PHP: include/require (also `__DIR__ .`, `dirname(__FILE__) .`, WordPress template paths),
  namespaces and `use`, class references (new, ::, extends, implements, instanceof, type hints are
  ignored), global function definitions and calls, WordPress hooks (add_action/add_filter vs
  do_action/apply_filters) and get_template_part.
- JavaScript/TypeScript (and the <script> of .vue/.svelte): import/export-from/require/dynamic import.
- Python: import and from-import (absolute and relative).

What can't be seen statically (string-built includes, dynamic class names, dependency injection)
is reported as unresolved, never guessed.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

PHP_KEYWORDS = {
    "if", "elseif", "else", "while", "for", "foreach", "switch", "case", "return", "echo", "print", "isset", "unset",
    "empty", "array", "list", "function", "fn", "new", "include", "include_once", "require", "require_once", "die",
    "exit", "eval", "match", "catch", "declare", "use", "static", "self", "parent", "and", "or", "not", "clone",
}


@dataclass
class FileFacts:
    """What one file defines and refers to (names as written; resolved in graph.py)."""
    language: str
    includes: List[str] = field(default_factory=list)  # PHP include/require literals (path-ish)
    templates: List[str] = field(default_factory=list)  # WordPress get_template_part candidates
    imports: List[str] = field(default_factory=list)  # JS/TS/Python module specifiers
    namespace: str = ""
    uses: List[Tuple[str, str]] = field(default_factory=list)  # PHP (alias, fully qualified name)
    classes: List[str] = field(default_factory=list)  # PHP classes/interfaces/traits/enums defined (FQN)
    functions: List[str] = field(default_factory=list)  # PHP global functions defined
    class_refs: Set[str] = field(default_factory=set)  # PHP class names referenced (as written)
    calls: Set[str] = field(default_factory=set)  # PHP function names called
    hooks_added: Set[str] = field(default_factory=set)  # WordPress hooks this file handles
    hooks_fired: Set[str] = field(default_factory=set)  # WordPress hooks this file fires
    unresolved: int = 0  # dependencies that can't be read statically (e.g. include $path)


def strip_comments(source: str, hash_comments: bool = False) -> str:
    """Remove // and /* */ comments (and # when hash_comments), keeping strings intact."""
    out: List[str] = []
    i, n = 0, len(source)
    quote: Optional[str] = None
    while i < n:
        ch = source[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(source[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"`":
            quote = ch
            out.append(ch)
            i += 1
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            chunk = source[i:] if end < 0 else source[i:end + 2]
            out.append("\n" * chunk.count("\n"))
            i = n if end < 0 else end + 2
        elif source.startswith("//", i) or (hash_comments and ch == "#" and not source.startswith("#[", i)):
            end = source.find("\n", i)
            i = n if end < 0 else end
        else:
            out.append(ch)
            i += 1
    return "".join(out)


# ---- PHP ------------------------------------------------------------------------------------------

_PHP_INCLUDE = re.compile(r"\b(?:include|require)(?:_once)?\b\s*\(?\s*(?P<expr>[^;]+);", re.I)
_PHP_LITERAL = re.compile(r"""['"]([^'"$]+?\.(?:php|inc|phtml))['"]""", re.I)
_PHP_NAMESPACE = re.compile(r"^\s*namespace\s+([A-Za-z_\\][\w\\]*)\s*[;{]", re.M)
_PHP_USE = re.compile(r"^\s*use\s+(?!function\b|const\b)([^;]+);", re.M)
_PHP_DEFINE = re.compile(r"\b(?:abstract\s+|final\s+|readonly\s+)*(class|interface|trait|enum)\s+([A-Za-z_]\w*)", re.I)
_PHP_FUNCTION = re.compile(r"(?<![\w>:$])(?:(public|private|protected|static|abstract|final)\s+)*function\s*&?\s*([A-Za-z_]\w*)\s*\(", re.I)
_PHP_CLASS_REF = re.compile(
    r"\b(?:new|extends|instanceof)\s+(\\?[A-Za-z_][\w\\]*)|(\\?[A-Za-z_][\w\\]*)\s*::|"
    r"\bimplements\s+([\w\\\s,]+?)\s*\{", re.I)
_PHP_CALL = re.compile(r"(?<![\w>:$\\])([A-Za-z_]\w*)\s*\(")
_WP_HOOK_ADD = re.compile(r"\badd_(?:action|filter)\s*\(\s*['\"]([^'\"]+)['\"]")
_WP_HOOK_FIRE = re.compile(r"\b(?:do_action|apply_filters)(?:_ref_array|_deprecated)?\s*\(\s*['\"]([^'\"]+)['\"]")
_WP_TEMPLATE = re.compile(r"\bget_template_part\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*['\"]([^'\"]+)['\"])?")
_PHP_STRINGS = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")


def _php_name(raw: str) -> str:
    return raw.strip().lstrip("\\")


def parse_php(source: str) -> FileFacts:
    facts = FileFacts("PHP")
    code = strip_comments(source, hash_comments=True)
    for match in _PHP_INCLUDE.finditer(code):
        literal = _PHP_LITERAL.search(match.group("expr"))
        if literal:
            facts.includes.append(literal.group(1))
        else:
            facts.unresolved += 1
    for match in _WP_TEMPLATE.finditer(code):
        slug, name = match.group(1).strip("/"), match.group(2)
        facts.templates += ([f"{slug}-{name}.php"] if name else []) + [f"{slug}.php"]
    ns = _PHP_NAMESPACE.search(code)
    facts.namespace = _php_name(ns.group(1)) if ns else ""
    for match in _PHP_USE.finditer(code):
        body = match.group(1).strip()
        group = re.match(r"([\w\\]+)\\\{(.+)\}", body, re.S)
        items = [(group.group(1) + "\\" + part.strip()) for part in group.group(2).split(",")] if group else body.split(",")
        for item in items:
            parts = re.split(r"\s+as\s+", item.strip(), flags=re.I)
            fqn = _php_name(parts[0])
            if fqn:
                facts.uses.append((parts[1].strip() if len(parts) > 1 else fqn.rsplit("\\", 1)[-1], fqn))
    prefix = facts.namespace + "\\" if facts.namespace else ""
    facts.classes = [prefix + m.group(2) for m in _PHP_DEFINE.finditer(code)]
    facts.functions = [m.group(2) for m in _PHP_FUNCTION.finditer(code) if not m.group(1) and not _inside_class(code, m.start())]
    no_strings = _PHP_STRINGS.sub("''", code)
    for match in _PHP_CLASS_REF.finditer(no_strings):
        if match.group(3):
            facts.class_refs.update(_php_name(n) for n in match.group(3).split(",") if n.strip())
        else:
            name = _php_name(match.group(1) or match.group(2))
            if name.lower() not in {"self", "static", "parent"}:
                facts.class_refs.add(name)
    defined = set(facts.functions)
    facts.calls = {m.group(1) for m in _PHP_CALL.finditer(no_strings)
                   if m.group(1).lower() not in PHP_KEYWORDS and m.group(1) not in defined}
    facts.calls -= {c.rsplit("\\", 1)[-1] for c in facts.classes}
    facts.hooks_added = set(_WP_HOOK_ADD.findall(code))
    facts.hooks_fired = set(_WP_HOOK_FIRE.findall(code))
    return facts


def _inside_class(code: str, position: int) -> bool:
    """True when `position` is inside a class/trait/interface body (so `function` is a method)."""
    depth_stack: List[bool] = []  # one entry per open brace: does it open a class body?
    pending_class = False
    for match in re.finditer(r"\b(?:class|interface|trait|enum)\s+\w+|[{}]", code[:position]):
        token = match.group(0)
        if token == "{":
            depth_stack.append(pending_class)
            pending_class = False
        elif token == "}":
            if depth_stack:
                depth_stack.pop()
        else:
            pending_class = True
    return any(depth_stack)


# ---- JavaScript / TypeScript ------------------------------------------------------------------------

_JS_IMPORT = re.compile(
    r"""\bimport\s+(?:type\s+)?(?:[\w*{}\s,$]+?\s+from\s+)?['"]([^'"]+)['"]|"""
    r"""\bexport\s+(?:type\s+)?(?:\*|\{[^}]*\})(?:\s+as\s+\w+)?\s+from\s+['"]([^'"]+)['"]|"""
    r"""\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)|\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)""")
_JS_DYNAMIC = re.compile(r"\b(?:require|import)\s*\(\s*(?!['\"])")
_SFC_SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script>", re.S | re.I)


def parse_js(source: str, language: str = "JavaScript") -> FileFacts:
    facts = FileFacts(language)
    if language in ("Vue", "Svelte"):
        source = "\n".join(_SFC_SCRIPT.findall(source))
    code = strip_comments(source)
    for match in _JS_IMPORT.finditer(code):
        facts.imports.append(next(g for g in match.groups() if g))
    facts.unresolved = len(_JS_DYNAMIC.findall(code))
    return facts


# ---- Python ---------------------------------------------------------------------------------------

_PY_IMPORT = re.compile(r"^[ \t]*import\s+([\w.]+(?:\s+as\s+\w+)?(?:\s*,\s*[\w.]+(?:\s+as\s+\w+)?)*)", re.M)
_PY_FROM = re.compile(r"^[ \t]*from\s+(\.*[\w.]*)\s+import[ \t]+(\([^)]*\)|[^\n]+)", re.M)


def parse_python(source: str) -> FileFacts:
    """Real import statements only (Python's own parser), so imports quoted in docstrings or strings
    never count; old or broken files fall back to the line scanner with strings removed."""
    facts = FileFacts("Python")
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return _parse_python_lines(source, facts)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            facts.imports += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            facts.imports.append(module)
            facts.imports += [f"{module}{'' if module.endswith('.') else '.'}{a.name}" for a in node.names if a.name != "*"]
    return facts


_PY_STRINGS = re.compile(r'(?s)""".*?"""|\'\'\'.*?\'\'\'|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'')


def _parse_python_lines(source: str, facts: FileFacts) -> FileFacts:
    code = re.sub(r"#[^\n]*", "", _PY_STRINGS.sub("''", source))
    for match in _PY_IMPORT.finditer(code):
        facts.imports += [re.split(r"\s+as\s+", part.strip())[0] for part in match.group(1).split(",")]
    for match in _PY_FROM.finditer(code):
        module = match.group(1)
        names = [re.split(r"\s+as\s+", n.strip())[0] for n in match.group(2).strip("() \\").split(",")]
        names = [n for n in names if re.fullmatch(r"\w+", n)]
        facts.imports.append(module)
        # `from pkg import module` may name submodules: offer them too (resolved only if they exist)
        facts.imports += [f"{module}{'' if module.endswith('.') else '.'}{n}" for n in names]
    return facts


def parse(source: str, language: str) -> Optional[FileFacts]:
    if language == "PHP":
        return parse_php(source)
    if language in ("JavaScript", "TypeScript", "Vue", "Svelte"):
        return parse_js(source, language)
    if language == "Python":
        return parse_python(source)
    return None
