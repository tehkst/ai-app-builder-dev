from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


TEMPLATE_DIR = Path(__file__).with_name("templates")


def _template(name: str, **values: str) -> str:
    """Render small preview templates without interpreting CSS/JS braces.

    These preview assets contain normal CSS and JavaScript blocks with braces. Python
    str.format treats those braces as placeholders and can raise KeyError values such
    as '\n  margin'. Keep rendering intentionally narrow: replace only explicit tokens
    passed by the caller and leave all other braces untouched.
    """

    rendered = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "generated-app"


def _snake(value: str) -> str:
    snake = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return snake or "generated_app"


def _title(value: str) -> str:
    cleaned = " ".join(value.split()) or "Generated App"
    return cleaned[:96]


def _file(path: str, language: str, purpose: str, content: str) -> Dict[str, Any]:
    return {
        "path": path,
        "language": language,
        "purpose": purpose,
        "content": content,
        "content_preview": content[:240],
        "write_status": "preview_only",
    }


def build_preview_generated_files(goal: str) -> List[Dict[str, Any]]:
    """Build DB-preview-only generated app artifacts.

    V97 keeps the same safety boundary as V88 while moving Builder beyond a static
    browser shell. These files are candidate application artifacts persisted for review;
    they are not written to disk, executed, installed, or deployed by this function.
    """

    app_title = _title(goal)
    app_slug = _slug(goal)
    app_module = _snake(goal)
    manifest = {
        "schema_version": "v97.scaffold-preview.1",
        "app_title": app_title,
        "app_slug": app_slug,
        "app_module": app_module,
        "write_mode": "db_preview_only",
        "safety": {
            "disk_write_performed": False,
            "filesystem_write_performed": False,
            "generated_code_execution_performed": False,
            "external_deployment_performed": False,
            "materialization_performed": False,
        },
        "artifacts": [
            "generated/backend/models.py",
            "generated/backend/schemas.py",
            "generated/backend/routes.py",
            "generated/backend/service.py",
            "generated/backend/tests/test_routes.py",
            "generated/frontend/App.jsx",
            "generated/frontend/package.json",
            "generated/manifest.json",
            "index.html",
            "styles.css",
            "app.js",
            "README.md",
        ],
        "approval_gate": "required_before_materialization",
    }

    backend_models = '''from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    WON = "won"
    LOST = "lost"


class TransportLead(BaseModel):
    lead_id: str = Field(..., min_length=3)
    company_name: str = Field(..., min_length=1)
    contact_name: str = Field(..., min_length=1)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    route_requirement: str = Field(default="")
    vehicle_requirement: str = Field(default="")
    status: LeadStatus = LeadStatus.NEW
    notes: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
'''

    backend_schemas = '''from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .models import LeadStatus, TransportLead


class LeadCreateRequest(BaseModel):
    company_name: str = Field(..., min_length=1)
    contact_name: str = Field(..., min_length=1)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    route_requirement: str = ""
    vehicle_requirement: str = ""
    notes: str = ""


class LeadUpdateRequest(BaseModel):
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None
    route_requirement: Optional[str] = None
    vehicle_requirement: Optional[str] = None


class LeadListResponse(BaseModel):
    leads: List[TransportLead]
    count: int
'''

    backend_service = '''from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from .models import TransportLead
from .schemas import LeadCreateRequest, LeadUpdateRequest


class LeadService:
    def __init__(self) -> None:
        self._leads: Dict[str, TransportLead] = {}

    def list_leads(self) -> List[TransportLead]:
        return list(self._leads.values())

    def create_lead(self, request: LeadCreateRequest) -> TransportLead:
        lead = TransportLead(
            lead_id=f"lead_{uuid4().hex[:12]}",
            company_name=request.company_name,
            contact_name=request.contact_name,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            route_requirement=request.route_requirement,
            vehicle_requirement=request.vehicle_requirement,
            notes=request.notes,
        )
        self._leads[lead.lead_id] = lead
        return lead

    def update_lead(self, lead_id: str, request: LeadUpdateRequest) -> Optional[TransportLead]:
        lead = self._leads.get(lead_id)
        if not lead:
            return None
        update_data = request.model_dump(exclude_unset=True)
        updated = lead.model_copy(update={**update_data, "updated_at": datetime.now(timezone.utc)})
        self._leads[lead_id] = updated
        return updated


lead_service = LeadService()
'''

    backend_routes = '''from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .schemas import LeadCreateRequest, LeadListResponse, LeadUpdateRequest
from .service import lead_service


router = APIRouter(prefix="/generated/transport-leads", tags=["generated-transport-leads"])


@router.get("", response_model=LeadListResponse)
def list_transport_leads() -> LeadListResponse:
    leads = lead_service.list_leads()
    return LeadListResponse(leads=leads, count=len(leads))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transport_lead(request: LeadCreateRequest):
    return lead_service.create_lead(request)


@router.patch("/{lead_id}")
def update_transport_lead(lead_id: str, request: LeadUpdateRequest):
    lead = lead_service.update_lead(lead_id, request)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
'''

    backend_tests = '''from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from generated.backend.routes import router


def test_transport_lead_crud_preview_contract() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    created = client.post(
        "/generated/transport-leads",
        json={
            "company_name": "Example School",
            "contact_name": "Operations Manager",
            "route_requirement": "AM and PM school routes",
            "vehicle_requirement": "13-seater with attendant",
        },
    )
    assert created.status_code == 201
    lead_id = created.json()["lead_id"]

    listed = client.get("/generated/transport-leads")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    updated = client.patch(f"/generated/transport-leads/{lead_id}", json={"status": "qualified"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "qualified"
'''

    frontend_app = f'''import {{ useMemo, useState }} from "react";

const initialLeads = [
  {{
    lead_id: "lead_preview_001",
    company_name: "Example International School",
    contact_name: "Transport Coordinator",
    route_requirement: "Morning and afternoon routes",
    vehicle_requirement: "13-seater with attendant",
    status: "new"
  }}
];

export default function GeneratedApp() {{
  const [leads] = useState(initialLeads);
  const qualifiedCount = useMemo(() => leads.filter((lead) => lead.status === "qualified").length, [leads]);

  return (
    <main className="generated-app-shell">
      <section>
        <p>DB-preview generated app</p>
        <h1>{app_title}</h1>
        <p>This React module is persisted for review only. It has not been materialized, built, deployed, or executed.</p>
      </section>
      <section aria-label="Lead summary">
        <article><strong>{{leads.length}}</strong><span>Total leads</span></article>
        <article><strong>{{qualifiedCount}}</strong><span>Qualified leads</span></article>
      </section>
      <section aria-label="Transport leads">
        {{leads.map((lead) => (
          <article key={{lead.lead_id}}>
            <h2>{{lead.company_name}}</h2>
            <p>{{lead.contact_name}}</p>
            <p>{{lead.route_requirement}}</p>
            <p>{{lead.vehicle_requirement}}</p>
          </article>
        ))}}
      </section>
    </main>
  );
}}
'''

    package_json = json.dumps(
        {
            "name": app_slug,
            "version": "0.0.0-db-preview",
            "private": True,
            "type": "module",
            "scripts": {
                "build": "vite build",
                "test": "vitest run",
            },
            "dependencies": {
                "@vitejs/plugin-react": "latest",
                "vite": "latest",
                "react": "latest",
                "react-dom": "latest",
            },
            "devDependencies": {
                "vitest": "latest",
            },
        },
        indent=2,
        sort_keys=True,
    )

    return [
        _file("generated/manifest.json", "json", "Generated app scaffold manifest and safety boundary.", json.dumps(manifest, indent=2, sort_keys=True)),
        _file("generated/backend/models.py", "python", "Typed domain model for generated transport lead CRM preview.", backend_models),
        _file("generated/backend/schemas.py", "python", "Request/response schemas for generated transport lead CRM preview.", backend_schemas),
        _file("generated/backend/service.py", "python", "Service layer for generated transport lead CRM preview.", backend_service),
        _file("generated/backend/routes.py", "python", "FastAPI routes for generated transport lead CRM preview.", backend_routes),
        _file("generated/backend/tests/test_routes.py", "python", "Pytest contract for generated route behavior.", backend_tests),
        _file("generated/frontend/App.jsx", "javascript", "React application shell for generated CRM preview.", frontend_app),
        _file("generated/frontend/package.json", "json", "Frontend package manifest for generated app preview.", package_json),
        {
            "path": "index.html",
            "language": "html",
            "purpose": "Static browser entry point for the generated app preview.",
            "content": _template("preview_index.html", goal=goal),
            "content_preview": "Static HTML shell for the generated browser app preview.",
            "write_status": "preview_only",
        },
        {
            "path": "styles.css",
            "language": "css",
            "purpose": "Styles for the generated browser app preview.",
            "content": _template("preview_styles.css"),
            "content_preview": "CSS styles for the generated browser app preview.",
            "write_status": "preview_only",
        },
        {
            "path": "app.js",
            "language": "javascript",
            "purpose": "Small browser interaction script for the generated app preview.",
            "content": _template("preview_app.js"),
            "content_preview": "JavaScript interaction for DB-preview browser review.",
            "write_status": "preview_only",
        },
        {
            "path": "README.md",
            "language": "markdown",
            "purpose": "Operator notes for the generated DB-preview app.",
            "content": _template("preview_readme.md", goal=goal),
            "content_preview": "README notes for the generated DB-preview app.",
            "write_status": "preview_only",
        },
    ]
