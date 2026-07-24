from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[3]


def project_architecture_decisions() -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    for path in _adr_paths():
        content = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(REPO_ROOT))
        title = _title(content, path.stem)
        decision_id = _decision_id(title, path.stem)
        node_id = "artifact:%s" % decision_id.lower()
        references = _references(content)
        nodes.append({
            "id": node_id,
            "type": "Artifact",
            "name": title,
            "authority": "Canonical",
            "lifecycle": "Active",
            "purpose": _first_paragraph(content),
            "technology": {},
            "quality": {"validation": "Repository-backed"},
            "ownership": {"repository": "tehkst/ai-app-builder-dev"},
            "operational": {},
            "evidence": [{"source": relative, "kind": "architecture-decision"}],
            "decision": {
                "why_introduced": _section(content, ("Context", "Why", "Purpose")),
                "decision": _section(content, ("Decision",)),
                "supersedes": _section(content, ("Supersedes", "Replaced")),
            },
        })
        for reference in references:
            edges.append({
                "source": node_id,
                "target": "module:%s" % reference[:-3].replace("/", "."),
                "type": "references",
                "evidence": relative,
            })
    return {"nodes": nodes, "edges": edges}


def _adr_paths() -> List[Path]:
    roots = [REPO_ROOT / "company" / "architecture" / "adr", REPO_ROOT / "docs" / "architecture"]
    paths = []
    for root in roots:
        if root.exists():
            paths.extend(path for path in root.rglob("*.md") if "adr" in path.name.lower() or "decision" in path.name.lower())
    return sorted(set(paths))


def _title(content: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else fallback.replace("-", " ").title()


def _decision_id(title: str, fallback: str) -> str:
    match = re.search(r"\bADR[-_ ]?\d+\b", title, re.IGNORECASE)
    return match.group(0).replace(" ", "-").replace("_", "-") if match else fallback


def _references(content: str) -> List[str]:
    return sorted(set(re.findall(r"\bapp/[A-Za-z0-9_./-]+\.py\b", content)))


def _section(content: str, headings: tuple) -> str:
    names = "|".join(re.escape(name) for name in headings)
    match = re.search(r"^##\s+(?:%s)\s*$\n(.*?)(?=^##\s+|\Z)" % names, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return match.group(1).strip()[:1000] if match else "Not explicitly recorded."


def _first_paragraph(content: str) -> str:
    body = re.sub(r"^#.*$", "", content, count=1, flags=re.MULTILINE).strip()
    return body.split("\n\n", 1)[0].strip()[:500]
