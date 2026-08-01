from __future__ import annotations

import json
import subprocess
import time
from typing import Any, Dict, List, Optional

from app.platform.gcp.environment_topology import ENVIRONMENTS, GCP_PROJECT_ID, GCP_REGION

# Infrastructure drift isn't tied to a git commit the way the rest of build_graph()'s
# projections are, so this keeps its own cache on its own clock rather than sharing
# projection.py's git-revision-keyed 60s cache.
_GCLOUD_TIMEOUT_SECONDS = 20
_CACHE_TTL_SECONDS = 300
_CACHE: Dict[str, Any] = {}


def project_infrastructure(refresh: bool = False) -> Dict[str, Any]:
    if not refresh and _fresh():
        return _CACHE["result"]
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    drift: Dict[str, Any] = {}
    for env_name, declared in ENVIRONMENTS.items():
        observed = _observe(declared)
        drift[env_name] = _compare(declared, observed)
        nodes.extend(_nodes(env_name, declared, observed))
        edges.extend(_edges(env_name))
    result = {"nodes": nodes, "edges": edges, "drift": drift}
    _CACHE.update({"result": result, "created": time.monotonic()})
    return result


def _fresh() -> bool:
    return "result" in _CACHE and time.monotonic() - _CACHE.get("created", 0.0) < _CACHE_TTL_SECONDS


def _observe(declared: Dict[str, str]) -> Optional[Dict[str, Any]]:
    # No gcloud, no credentials, no network - this must never crash build_graph(), the
    # same reasoning authority_projection.py and lineage_projection.py already document.
    try:
        service = _describe_service(declared["cloud_run_service"])
        if service is None:
            return None
        service["secret_accessible"] = _secret_accessible(declared["database_secret"], service.get("service_account"))
        return service
    except Exception:
        return None


def _describe_service(service_name: str) -> Optional[Dict[str, Any]]:
    command = [
        "gcloud", "run", "services", "describe", service_name,
        "--region=%s" % GCP_REGION, "--project=%s" % GCP_PROJECT_ID,
        "--format=json(spec.template.spec.serviceAccountName,spec.template.metadata.annotations,"
        "spec.template.spec.containers)",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=_GCLOUD_TIMEOUT_SECONDS)
    if completed.returncode != 0:
        return None
    payload = json.loads(completed.stdout)
    template = ((payload.get("spec") or {}).get("template") or {})
    annotations = (template.get("metadata") or {}).get("annotations") or {}
    cloudsql_raw = annotations.get("run.googleapis.com/cloudsql-instances", "")
    database_secret_name = None
    for container in (template.get("spec") or {}).get("containers") or []:
        for env_var in container.get("env") or []:
            if env_var.get("name") == "DATABASE_URL":
                database_secret_name = ((env_var.get("valueFrom") or {}).get("secretKeyRef") or {}).get("name")
    return {
        "cloudsql_instances": [item for item in cloudsql_raw.split(",") if item],
        "database_secret_name": database_secret_name,
        "service_account": (template.get("spec") or {}).get("serviceAccountName"),
    }


def _secret_accessible(secret_name: str, service_account: Optional[str]) -> Optional[bool]:
    if not service_account:
        return None
    command = ["gcloud", "secrets", "get-iam-policy", secret_name, "--project=%s" % GCP_PROJECT_ID, "--format=json"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=_GCLOUD_TIMEOUT_SECONDS)
    if completed.returncode != 0:
        return None
    policy = json.loads(completed.stdout)
    for binding in policy.get("bindings") or []:
        if binding.get("role") == "roles/secretmanager.secretAccessor":
            if any(service_account in member for member in binding.get("members") or []):
                return True
    return False


def _compare(declared: Dict[str, str], observed: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if observed is None:
        return {"status": "unavailable", "issues": []}
    issues: List[str] = []
    if declared["cloud_sql_connection_name"] not in (observed.get("cloudsql_instances") or []):
        issues.append(
            "declared cloud_sql_connection_name %s is not attached (observed: %s)"
            % (declared["cloud_sql_connection_name"], observed.get("cloudsql_instances"))
        )
    if observed.get("database_secret_name") != declared["database_secret"]:
        issues.append(
            "declared database_secret %s does not match observed %s"
            % (declared["database_secret"], observed.get("database_secret_name"))
        )
    if observed.get("secret_accessible") is False:
        issues.append("runtime service account cannot read declared secret %s" % declared["database_secret"])
    return {"status": "drift" if issues else "match", "issues": issues}


def _nodes(env_name: str, declared: Dict[str, str], observed: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    availability = "unavailable" if observed is None else "observed"
    deployment_id = "deployment:%s" % env_name
    database_id = "database:%s" % declared["cloud_sql_database"]
    secret_id = "secret:%s" % declared["database_secret"]
    return [
        _node(deployment_id, "Deployment", declared["cloud_run_service"], availability, {
            "environment": env_name, "cloud_run_service": declared["cloud_run_service"],
        }),
        _node(database_id, "Database", declared["cloud_sql_database"], availability, {
            "cloud_sql_connection_name": declared["cloud_sql_connection_name"],
        }),
        _node(secret_id, "Secret", declared["database_secret"], availability, {}),
    ]


def _edges(env_name: str) -> List[Dict[str, str]]:
    declared = ENVIRONMENTS[env_name]
    deployment_id = "deployment:%s" % env_name
    database_id = "database:%s" % declared["cloud_sql_database"]
    secret_id = "secret:%s" % declared["database_secret"]
    return [
        {"source": deployment_id, "target": database_id, "type": "connects_to", "evidence": "environment-topology"},
        {"source": deployment_id, "target": secret_id, "type": "reads_secret", "evidence": "environment-topology"},
    ]


def _node(node_id: str, node_type: str, name: str, availability: str, technology: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": node_id, "type": node_type, "name": name, "authority": "Canonical",
        "lifecycle": "Active", "technology": technology, "quality": {"observation": availability},
        "ownership": {"repository": "tehkst/ai-app-builder-dev"}, "operational": {}, "evidence": [],
    }
