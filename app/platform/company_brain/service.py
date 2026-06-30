from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.platform.company_brain.repository import FileCompanyBrainRepository


def build_company_brain_repository_summary() -> dict[str, Any]:
    repository = FileCompanyBrainRepository()
    artifacts = repository.list_artifacts()
    return {
        "company": "AI Software Factory",
        "product": "Company Brain Repository",
        "storage": "repository-filesystem",
        "total_artifacts": len(artifacts),
        "artifacts": [
            {
                "path": artifact.path,
                "title": artifact.title,
                "artifact_type": artifact.artifact_type,
            }
            for artifact in artifacts
        ],
    }


def get_company_brain_artifact(path: str) -> dict[str, Any]:
    repository = FileCompanyBrainRepository()
    artifact = repository.get_artifact(path)
    return asdict(artifact)
