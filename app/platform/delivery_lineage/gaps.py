from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def detect_gaps(source: Dict[str, Any], entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    gaps = []
    contract = source["state"].get("delivery_contract")
    contract = contract if isinstance(contract, dict) else {}
    artifacts = contract.get("artifacts") or []
    produced = {ref for item in entries for ref in item.get("artifact_refs") or []}
    for artifact in artifacts:
        if not artifact.get("authoring_authority"):
            gaps.append(_gap("missing_producer", "Artifact %s has no producer." % artifact.get("artifact_id")))
        for reference in artifact.get("source_references") or []:
            if str(reference).startswith("DELIVERY-") and reference not in produced:
                gaps.append(_gap("missing_artifact", "Source artifact %s is not present." % reference))
    _release_gaps(contract, entries, gaps)
    _provider_gaps(entries, gaps)
    _timestamp_gaps(entries, gaps)
    _duplicates(entries, gaps)
    counts = Counter(item["classification"] for item in gaps)
    completeness = "complete"
    if counts.get("inconsistent"):
        completeness = "inconsistent"
    elif gaps:
        completeness = "partial"
    elif not entries:
        completeness = "unknown"
    return {
        "classification": completeness,
        "gap_count": len(gaps),
        "counts": dict(counts),
        "items": gaps,
    }


def _release_gaps(contract: Dict[str, Any], entries: List[Dict[str, Any]], gaps: List[Dict[str, str]]) -> None:
    event_types = {item.get("event_type") for item in entries}
    refs = contract.get("release_evidence_references") or []
    if "deployment_succeeded" in event_types and not any("merge" in str(value).lower() for value in refs):
        gaps.append(_gap("missing_merge", "Deployment evidence exists without linked merge evidence."))
    if contract.get("production_verification_reference") and not (
        refs or any(item.get("deployment_refs") for item in entries)
    ):
        gaps.append(_gap("missing_deployment", "Production verification has no linked deployment revision."))
    if contract.get("founder_acceptance_reference") and not contract.get("production_verification_reference"):
        gaps.append(_gap("acceptance_without_verification", "Founder acceptance has no production verification reference.", "inconsistent"))


def _provider_gaps(entries: List[Dict[str, Any]], gaps: List[Dict[str, str]]) -> None:
    generated = [item for item in entries if item.get("event_type") == "artifact_produced"]
    if generated and any(not item.get("provider") or not item.get("model") for item in generated):
        gaps.append(_gap("missing_provider_model", "One or more generated artifacts lack provider/model provenance."))


def _timestamp_gaps(entries: List[Dict[str, Any]], gaps: List[Dict[str, str]]) -> None:
    timestamps = [item.get("occurred_at") for item in entries if item.get("occurred_at")]
    if timestamps != sorted(timestamps):
        gaps.append(_gap("inconsistent_timestamps", "Recorded lineage timestamps are contradictory.", "inconsistent"))


def _duplicates(entries: List[Dict[str, Any]], gaps: List[Dict[str, str]]) -> None:
    keys = [(item["authority"], item["source_record_id"], item["event_type"]) for item in entries]
    if len(keys) != len(set(keys)):
        gaps.append(_gap("duplicate_transition", "The same authority transition appears more than once.", "inconsistent"))


def _gap(code: str, detail: str, classification: str = "partial") -> Dict[str, str]:
    return {"code": code, "classification": classification, "detail": detail}
