from __future__ import annotations

import importlib
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.platform.deployment.approved_cloud_run import _deploy_command
from app.platform.saas_builder.deployment import bounded_source_directory, deployment_options
from app.platform.saas_builder.lifecycle import project_lifecycle
from app.platform.saas_builder.service import create_build, get_build
from app.platform.saas_builder.specification import bounded_specification
from app.platform.saas_builder.template import reference_file_changes
from app.platform.saas_builder.ui import render_builder


def _materialize(root: Path) -> Path:
    spec = bounded_specification(
        "Build an appointment-booking SaaS for a dog-grooming business. "
        "The owner can register, create services and manage bookings. Customers book publicly.",
        "Pawfect Appointments",
    )
    files = reference_file_changes("APP-CHECK", spec)
    assert spec["acceptance_criteria"] and spec["excluded_functionality"]
    for item in files:
        relative = Path(item["path"]).relative_to("generated_apps/app-check")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["content"], encoding="utf-8")
    return root


def _load_app(root: Path):
    os.environ["DATABASE_URL"] = "sqlite:///%s" % (root / "booking.db")
    os.environ["APP_SESSION_SECRET"] = "acceptance-secret-with-sufficient-length"
    sys.path.insert(0, str(root))
    try:
        return importlib.import_module("main").app
    finally:
        sys.path.pop(0)


def run_check() -> None:
    assert bounded_source_directory("generated_apps/app-check") == "generated_apps/app-check"
    assert bounded_source_directory("../outside") == "."
    options = deployment_options({
        "source_directory": "generated_apps/app-check",
        "service_name": "afos-app-check",
        "project_id": "ai-software-factory-500910",
        "region": "asia-southeast1",
    })
    assert "ai-software-factory-deploy@ai-software-factory-500910.iam.gserviceaccount.com" in deployment_options({
        "source_directory": "generated_apps/app-check",
        "service_name": "afos-app-check",
        "project_id": "ai-software-factory-500910",
        "region": "asia-southeast1",
    })
    assert "ai-software-factory-500910:asia-southeast1:ai-factory-db" in options
    assert "--set-secrets" in options
    command = _deploy_command({
        "source_directory": "generated_apps/app-check",
        "service_name": "afos-app-check",
        "project_id": "ai-software-factory-500910",
        "region": "asia-southeast1",
    })
    assert "--no-invoker-iam-check" in command and "--allow-unauthenticated" not in command
    ui = render_builder()
    assert "Founder" not in ui and "localStorage" not in ui and "What would you like to build?" in ui
    assert project_lifecycle({"context": {}, "current_stage": "accepted"})["status"] == "scope_confirmed"
    user = SimpleNamespace(id="saas-builder-check-user", email="builder-check@example.com")
    other = SimpleNamespace(id="different-workspace-user", email="other@example.com")
    request = {
        "application_name": "Pawfect Appointments",
        "description": "Build an appointment booking SaaS with owner login, services, and public bookings.",
    }
    first = create_build(request, user)
    repeated = create_build(request, user)
    run_id = first["build"]["workflow_run_id"]
    assert repeated["build"]["workflow_run_id"] == run_id
    assert get_build(run_id, other)["status"] == "forbidden"
    for _ in range(30):
        durable = get_build(run_id, user)
        if durable.get("build", {}).get("status") == "ready_for_repository":
            break
        time.sleep(0.05)
    assert durable["build"]["status"] == "ready_for_repository"
    with tempfile.TemporaryDirectory() as directory:
        root = _materialize(Path(directory))
        with TestClient(_load_app(root), base_url="https://testserver") as client:
            credentials = {"email": "owner@example.com", "password": "strong-pass-123"}
            assert client.get("/api/owner/dashboard").status_code == 401
            assert client.post("/api/auth/register", json=credentials).status_code == 200
            assert client.put("/api/owner/profile", json={"business_name": "Pawfect Grooming"}).status_code == 200
            service = client.post("/api/owner/services", json={"name": "Full Groom", "duration_minutes": 60, "price": 85}).json()
            assert client.post("/api/auth/logout").status_code == 200
            booking = client.post("/api/public/bookings", json={
                "service_id": service["id"], "appointment_at": "2026-08-01T10:00:00",
                "customer_name": "Alex Customer", "customer_email": "alex@example.com",
            }).json()
            assert client.get("/api/owner/dashboard").status_code == 401
            assert client.post("/api/auth/login", json=credentials).status_code == 200
            dashboard = client.get("/api/owner/dashboard").json()
            assert dashboard["bookings"][0]["id"] == booking["id"]
            assert client.patch("/api/owner/bookings/%s" % booking["id"], json={"status": "completed"}).status_code == 200
            assert client.get("/api/owner/dashboard").json()["bookings"][0]["status"] == "completed"
    print("AFOS-016 SAAS BUILDER CHECK PASSED")


if __name__ == "__main__":
    run_check()
