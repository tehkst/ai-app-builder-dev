"""Load the AI workforce from company/workforce/ (manifest + role files)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.platform.nautilus.permissions import PERMISSION_MODES

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WORKFORCE_DIR = REPO_ROOT / "company" / "workforce"
AUTONOMY_TIERS = (0, 1, 2, 3)


class WorkforceError(ValueError):
    pass


@dataclass(frozen=True)
class Employee:
    employee_id: str
    name: str
    department: str
    role_prompt: str
    permission_mode: str
    autonomy_tier: int
    responsibilities: List[str] = field(default_factory=list)
    adapted_from: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Workforce:
    employees: Dict[str, Employee]

    def get(self, employee_id: str) -> Employee:
        if employee_id not in self.employees:
            raise WorkforceError(f"No employee '{employee_id}' in the workforce manifest.")
        return self.employees[employee_id]

    def for_responsibility(self, responsibility: str) -> Employee:
        for employee in self.employees.values():
            if responsibility in employee.responsibilities:
                return employee
        raise WorkforceError(f"No employee is responsible for '{responsibility}'.")


def _employee(entry: Dict[str, Any], base: Path) -> Employee:
    employee_id = str(entry.get("id") or "").strip()
    if not employee_id:
        raise WorkforceError("Every employee needs an 'id'.")
    mode = str(entry.get("permission_mode") or "approve")
    if mode not in PERMISSION_MODES:
        raise WorkforceError(f"{employee_id}: permission_mode must be one of {PERMISSION_MODES}.")
    tier = entry.get("autonomy_tier")
    if tier not in AUTONOMY_TIERS:
        raise WorkforceError(f"{employee_id}: autonomy_tier must be one of {AUTONOMY_TIERS}.")
    role_path = (base / str(entry.get("role_file") or "")).resolve()
    if base.resolve() not in role_path.parents or not role_path.is_file():
        raise WorkforceError(f"{employee_id}: role_file must be an existing file inside {base}.")
    role_prompt = role_path.read_text(encoding="utf-8").strip()
    if not role_prompt:
        raise WorkforceError(f"{employee_id}: role file is empty.")
    return Employee(
        employee_id=employee_id, name=str(entry.get("name") or employee_id),
        department=str(entry.get("department") or ""), role_prompt=role_prompt,
        permission_mode=mode, autonomy_tier=int(tier),
        responsibilities=[str(r) for r in entry.get("responsibilities") or []],
        adapted_from=[str(a) for a in entry.get("adapted_from") or []],
    )


def load_workforce(directory: Optional[Path] = None) -> Workforce:
    import yaml  # PyYAML ships with the langchain dependency set

    base = Path(directory or DEFAULT_WORKFORCE_DIR)
    manifest = yaml.safe_load((base / "manifest.yaml").read_text(encoding="utf-8")) or {}
    employees: Dict[str, Employee] = {}
    for entry in manifest.get("employees") or []:
        employee = _employee(entry, base)
        if employee.employee_id in employees:
            raise WorkforceError(f"Duplicate employee id '{employee.employee_id}'.")
        employees[employee.employee_id] = employee
    if not employees:
        raise WorkforceError("The workforce manifest lists no employees.")
    return Workforce(employees)
