from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CompanyBrainArtifact:
    path: str
    title: str
    artifact_type: str
    content: str


class CompanyBrainRepository(Protocol):
    def get_artifact(self, path: str) -> CompanyBrainArtifact:
        ...

    def list_artifacts(self, prefix: str) -> list[CompanyBrainArtifact]:
        ...


class FileCompanyBrainRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path("company")

    def get_artifact(self, path: str) -> CompanyBrainArtifact:
        target = self.root / path
        content = target.read_text(encoding="utf-8")
        return CompanyBrainArtifact(
            path=str(target),
            title=_title_from_content(content, target.name),
            artifact_type=_artifact_type(target),
            content=content,
        )

    def list_artifacts(self, prefix: str = "") -> list[CompanyBrainArtifact]:
        root = self.root / prefix
        files = sorted(path for path in root.rglob("*.md") if path.is_file())
        artifacts: list[CompanyBrainArtifact] = []
        for file_path in files:
            content = file_path.read_text(encoding="utf-8")
            artifacts.append(
                CompanyBrainArtifact(
                    path=str(file_path),
                    title=_title_from_content(content, file_path.name),
                    artifact_type=_artifact_type(file_path),
                    content=content,
                )
            )
        return artifacts


def _title_from_content(content: str, fallback: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return fallback


def _artifact_type(path: Path) -> str:
    parts = set(path.parts)
    if "adr" in parts:
        return "adr"
    if "board" in parts:
        return "board"
    if "strategy" in parts:
        return "strategy"
    if "constitution" in parts:
        return "constitution"
    if "missions" in parts:
        return "mission"
    if "product" in parts:
        return "product"
    if "executives" in parts:
        return "executive"
    if "knowledge" in parts:
        return "knowledge"
    return "company"
