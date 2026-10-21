"""The Audit (sold after the Health Check): the Code Auditor reviews a client's codebase and writes a
prioritised fix plan, which the platform checks before it reaches the client.

1. A fresh Health Check and impact map (read-only, nothing run) give the auditor its starting facts.
2. The Code Auditor (read-only; any command it runs goes to the container sandbox) reads a redacted
   copy of the code (secret files withheld, secret values removed: `redaction.py`) and
   returns an owner summary, a map of the app's parts, findings and the first three steps. The
   client's code is read by the AI provider the founder confirmed the client agreed to; the audit is
   pinned to that provider and model.
3. The platform then checks the work: every finding's evidence file must exist in the codebase
   (otherwise it is marked "not verified"), each fix gets the impact map's answer to "what breaks if
   we change this?", and each size gets a suggested price.
"""
from __future__ import annotations

import posixpath
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from app.platform.clients.redaction import redact_all, redacted_copy
from app.platform.nautilus.messages import ChatFn

SEVERITIES = ("critical", "high", "medium", "low")
SIZES = ("S", "M", "L")
# Suggested fixed prices for the fix plan (the founder quotes the final price).
PRICE_BY_SIZE = {"S": "$90", "M": "$250", "L": "$600"}
HOURS_BY_SIZE = {"S": "1-2 hours", "M": "3-6 hours", "L": "1-3 days"}
MAX_TURNS = 60

_STR = {"type": "string"}
AUDIT_SCHEMA: Dict[str, Any] = {
    "type": "object", "required": ["summary", "map", "findings", "first_steps"],
    "properties": {
        "summary": _STR,
        "map": {"type": "array", "items": {"type": "object", "required": ["part", "purpose"], "properties": {
            "part": _STR, "purpose": _STR, "files": {"type": "array", "items": _STR},
            "connects_to": {"type": "array", "items": _STR}}}},
        "findings": {"type": "array", "items": {"type": "object",
                                                "required": ["title", "severity", "evidence", "impact", "fix", "size"],
                                                "properties": {
            "title": _STR, "severity": {"type": "string", "enum": list(SEVERITIES)},
            "evidence": {"type": "array", "items": {"type": "object", "required": ["file"], "properties": {
                "file": _STR, "line": {"type": "integer"}, "note": _STR}}},
            "impact": _STR, "fix": _STR, "size": {"type": "string", "enum": list(SIZES)},
            "change_target": _STR, "inference": {"type": "boolean"}}}},
        "first_steps": {"type": "array", "items": _STR},
        "appendix": _STR,
    },
}

# Replaceable for checks (scripted auditor); production builds the pinned provider's chat.
chat_factory: Callable[[str, str], ChatFn] = lambda provider, model: _provider_chat(provider, model)


def _provider_chat(provider: str, model: str) -> ChatFn:
    from app.platform.nautilus.chat_providers import build_chat_fn

    return build_chat_fn(provider, model)


def assignment(project: str, health: Dict[str, Any]) -> str:
    risks = "\n".join(f"- [{r['severity']}] {r['title']}: {r['detail']}" for r in health.get("all_risks", [])[:25]) or "- none"
    areas = "\n".join(f"- {a['title']}: {a['grade']} ({a['score']}/100)" for a in health.get("areas", []))
    impact = health.get("impact") or {}
    hot = "\n".join(f"- {h['path']}: used directly by {h['used_directly_by']}, affects {h['affects']} files"
                    for h in impact.get("hotspots", [])[:10]) or "- (no links found)"
    vuln = "\n".join(f"- {p['package']}: used in {', '.join(p['files'][:5])}" for p in impact.get("vulnerable_packages", [])) or "- none"
    stack = ", ".join(f"{k}: {', '.join(v)}" for k, v in (health.get("stack") or {}).items() if v) or "unknown"
    return (f"## Codebase\n{project} ({stack}; {health['size']['lines']:,} lines in {health['size']['files']} files)\n\n"
            f"## Health Check (automated, grade {health['overall']['grade']})\n{areas}\n\nRisks found:\n{risks}\n\n"
            f"## Impact map (files whose changes ripple furthest)\n{hot}\n\nPackages with known vulnerabilities and "
            f"where they are used:\n{vuln}\n\n"
            "## Deliverable\nRead the code (list_files, read_file; start with the entry points and the files above), "
            "confirm or correct the Health Check, and add what automation can't see. Then call final_output with:\n"
            "- summary: three plain sentences for the business owner;\n"
            "- map: the main parts (part, purpose, key files, what each connects to);\n"
            "- findings: most important first; each with title, severity (critical/high/medium/low), evidence (the "
            "files and lines you read that show it), impact (why it matters to the business, plainly), fix, size "
            "(S, M or L), change_target (the file, class or function the fix would change) and inference=true when "
            "you couldn't confirm it in the code;\n"
            "- first_steps: the three things to do first, in order;\n"
            "- appendix: technical notes for the next developer.\n"
            "Never repeat a secret's value: refer to secrets by file, line and kind.")


def run_auditor(local_path: str, project: str, health: Dict[str, Any], ai: Tuple[str, str]) -> Dict[str, Any]:
    """The Code Auditor's raw review. Raises AuditError when no usable review comes back."""
    from app.platform.orca.employee_runner import run_employee
    from app.platform.orca.workforce import load_workforce

    auditor = load_workforce().for_responsibility("audit_codebase")
    result = run_employee(auditor, assignment=assignment(project, health), workspace_root=local_path,
                          chat=chat_factory(*ai), output_schema=AUDIT_SCHEMA, allow_writes=False,
                          allow_execution=False, max_turns=MAX_TURNS, sandboxed=True)
    if result.run.status == "provider_error":
        raise AuditError(f"The AI provider failed ({result.run.error or 'no detail'}); run the Audit again.")
    if not result.output:
        raise AuditError(f"The Code Auditor finished without a review ({result.run.status}); run the Audit again.")
    return result.output


class AuditError(RuntimeError):
    pass


def _file_exists(root: Path, rel: str) -> Optional[str]:
    """The evidence file as a codebase-relative path if it really exists there, else None."""
    clean = posixpath.normpath(str(rel or "").replace("\\", "/").lstrip("/"))
    if not clean or clean.startswith(".."):
        return None
    path = (root / clean).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return clean if path.is_file() else None




def finish(raw: Dict[str, Any], local_path: str, health: Dict[str, Any]) -> Dict[str, Any]:
    """Check the auditor's work against the codebase and add impact, size and price to each finding."""
    from app.platform.impact_map import build_map, impact

    root = Path(local_path)
    imap = build_map(local_path)
    order = {s: i for i, s in enumerate(SEVERITIES)}
    findings = []
    for item in raw.get("findings") or []:
        evidence, verified = [], False
        for ev in item.get("evidence") or []:
            real = _file_exists(root, ev.get("file", ""))
            verified = verified or bool(real)
            given = str(ev.get("file", ""))[:300]
            outside = posixpath.normpath(given.replace("\\", "/").lstrip("/")).startswith("..")
            evidence.append({"file": real or ("(outside this codebase)" if outside else given), "line": ev.get("line"),
                             "note": str(ev.get("note") or "")[:500], "exists": bool(real)})
        target = str(item.get("change_target") or "") or next((e["file"] for e in evidence if e["exists"]), "")
        reach = impact(imap, target) if target else {"found": False}
        size = item.get("size") if item.get("size") in SIZES else "M"
        findings.append({
            "title": str(item.get("title", ""))[:200], "severity": item.get("severity", "medium"),
            "impact": str(item.get("impact", ""))[:1500], "fix": str(item.get("fix", ""))[:1500],
            "size": size, "hours": HOURS_BY_SIZE[size], "price": PRICE_BY_SIZE[size], "evidence": evidence[:10],
            "verified": verified and not item.get("inference"),
            "change_impact": {k: reach.get(k) for k in ("found", "name", "kind", "level", "affected_count",
                                                        "entry_points", "tests", "untested", "advice")},
        })
    findings.sort(key=lambda f: (order.get(f["severity"], 9), not f["verified"]))
    audit = {
        "summary": str(raw.get("summary", ""))[:2000],
        "map": [{"part": str(m.get("part", ""))[:120], "purpose": str(m.get("purpose", ""))[:400],
                 "files": [str(x)[:200] for x in (m.get("files") or [])[:8]],
                 "connects_to": [str(x)[:120] for x in (m.get("connects_to") or [])[:8]]} for m in (raw.get("map") or [])[:15]],
        "findings": findings[:40],
        "first_steps": [str(s)[:400] for s in (raw.get("first_steps") or [])[:3]],
        "appendix": str(raw.get("appendix", ""))[:6000],
        "health": {"overall": health["overall"], "areas": [{"title": a["title"], "score": a["score"], "grade": a["grade"]}
                                                           for a in health["areas"]], "stack": health.get("stack"),
                   "size": health["size"], "checked_at": health["checked_at"]},
        "impact": {k: (health.get("impact") or {}).get(k) for k in ("files", "linked_files", "links", "hotspots", "vulnerable_packages")},
        "unverified": sum(1 for f in findings if not f["verified"]),
    }
    return redact_all(audit)  # in case the auditor repeated a key despite its instructions


def run_audit(local_path: str, project: str, ai: Tuple[str, str], online_lookups: bool) -> Dict[str, Any]:
    from app.platform.codebase_health.service import run_health_check

    health = run_health_check(local_path, online_lookups=online_lookups)
    scratch = Path(tempfile.mkdtemp(prefix="asf-audit-"))
    try:
        copy = scratch / project_dir_name(project)
        redacted_copy(local_path, str(copy))  # what the AI provider may see
        raw = run_auditor(str(copy), project, health, ai)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return finish(raw, local_path, health)  # evidence and impact are checked against the real code, locally


def project_dir_name(project: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", project).strip("-.") or "code"


def counts(audit: Dict[str, Any]) -> Dict[str, int]:
    return {s: sum(1 for f in audit["findings"] if f["severity"] == s) for s in SEVERITIES}

