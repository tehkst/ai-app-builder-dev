from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import requests

from app.platform.auth.service import require_founder

DEFAULT_PROJECT_ID = "ai-software-factory-500910"
DEFAULT_REGION = "asia-southeast1"
DEFAULT_SERVICE_NAME = "ai-software-factory-production"
DEFAULT_SERVICE_URL = "https://ai-software-factory-production-85787156520.asia-southeast1.run.app"


def build_production_verification_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Automated Production Verification",
        "status": "ready",
        "service_url": DEFAULT_SERVICE_URL,
        "service_name": DEFAULT_SERVICE_NAME,
        "region": DEFAULT_REGION,
        "project_id": DEFAULT_PROJECT_ID,
        "governance": {
            "read_only": True,
            "deployment": False,
            "traffic_shift": False,
            "rollback": False,
            "github_mutation": False,
            "pr_merge": False,
            "secrets_exposed": False,
        },
        "endpoints": {
            "summary": "GET /mission-control/verification",
            "run": "POST /mission-control/verification/run",
        },
    }


def run_production_verification(payload: dict[str, Any]) -> dict[str, Any]:
    request = _verification_request(payload)
    checks: list[dict[str, Any]] = []
    auth = require_founder(payload)
    checks.append(_manual_check("founder_token_validation", bool(auth.get("authorized")), None, "Founder token is valid." if auth.get("authorized") else "Founder token is invalid or missing."))
    if not auth.get("authorized"):
        return _result(request, checks)

    root = _http_check("service_url_reachable", request["service_url"])
    checks.append(root)
    checks.append(_manual_check(
        "dashboard_html_contains_brand",
        bool(root.get("body_contains_brand")),
        root.get("status_code"),
        "Dashboard HTML contains Mission Control or AI Software Factory." if root.get("body_contains_brand") else "Dashboard HTML did not include Mission Control or AI Software Factory.",
        root.get("response_time_ms"),
    ))
    checks.append(_http_check("runtime_endpoint_reachable_if_available", _join(request["service_url"], "/mission-control/runtime"), optional=True))
    checks.append(_http_check("github_execution_endpoint_reachable_if_available", _join(request["service_url"], "/mission-control/github-execution"), optional=True))
    checks.append(_http_check("deployment_endpoint_reachable_if_available", _join(request["service_url"], "/mission-control/deployment"), optional=True))
    return _result(request, checks)


def _verification_request(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "service_url": _clean_url(payload.get("service_url") or DEFAULT_SERVICE_URL),
        "service_name": str(payload.get("service_name") or DEFAULT_SERVICE_NAME).strip() or DEFAULT_SERVICE_NAME,
        "region": str(payload.get("region") or DEFAULT_REGION).strip() or DEFAULT_REGION,
        "project_id": str(payload.get("project_id") or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID,
    }


def _clean_url(value: Any) -> str:
    text = str(value or DEFAULT_SERVICE_URL).strip()
    return text.rstrip("/") if text.startswith(("https://", "http://")) else DEFAULT_SERVICE_URL


def _join(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _http_check(name: str, url: str, optional: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = requests.get(url, timeout=12)
        elapsed = int((time.perf_counter() - started) * 1000)
        text = response.text[:200000] if response.text else ""
        ok = 200 <= response.status_code < 400
        if optional and response.status_code in {401, 403, 404, 405}:
            return _manual_check(name, True, response.status_code, f"Optional endpoint unavailable or protected with HTTP {response.status_code}.", elapsed)
        check = _manual_check(name, ok, response.status_code, f"HTTP {response.status_code}", elapsed)
        check["body_contains_brand"] = "Mission Control" in text or "AI Software Factory" in text
        return check
    except requests.RequestException as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return _manual_check(name, bool(optional), None, ("Optional endpoint not reachable: " if optional else "Endpoint not reachable: ") + _safe_detail(str(exc)), elapsed)


def _manual_check(name: str, passed: bool, status_code: int | None, detail: str, response_time_ms: int | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "detail": _safe_detail(detail),
    }


def _result(request: dict[str, str], checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(check["passed"] for check in checks)
    return {
        "status": "verification-complete",
        "service_url": request["service_url"],
        "service_name": request["service_name"],
        "region": request["region"],
        "project_id": request["project_id"],
        "overall_result": "pass" if passed else "fail",
        "checks": checks,
        "recommended_action": "Production verification passed. Continue with founder review for any next step." if passed else "Review failed checks before any deployment, traffic, rollback, merge, or release action.",
        "founder_approval_required_for_next_step": True,
        "deployment": False,
        "traffic_shift": False,
        "rollback": False,
        "github_mutation": False,
        "pr_merge": False,
        "secrets_visible": False,
    }


def _safe_detail(value: str) -> str:
    lowered = value.replace("\n", " ").strip()
    return lowered[:500]
