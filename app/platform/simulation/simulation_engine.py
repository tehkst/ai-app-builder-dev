from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from app.platform.company_brain.company_brain import CompanyBrain
from app.platform.company_brain.event_models import DomainEvent
from app.platform.digital_twin.twin_runtime import DigitalTwin
from app.platform.simulation.scenario_runner import ScenarioRunner
from app.platform.simulation.simulation_session import Scenario, SimulationSession


@dataclass(frozen=True)
class Prediction:
    status: str = "not_implemented"


@dataclass(frozen=True)
class RiskAssessment:
    status: str = "not_implemented"


@dataclass(frozen=True)
class ImpactAssessment:
    status: str = "not_implemented"


@dataclass(frozen=True)
class ExecutionSimulation:
    status: str = "not_implemented"


class SimulationEngine:
    def __init__(self, company_brain: Optional[CompanyBrain] = None, digital_twin: Optional[DigitalTwin] = None) -> None:
        self.company_brain = company_brain or CompanyBrain()
        self.digital_twin = digital_twin or DigitalTwin()
        self.runner = ScenarioRunner()

    def create_session(self, name: str, assumptions: Optional[dict[str, Any]] = None) -> SimulationSession:
        return SimulationSession(Scenario(name=name, assumptions=assumptions or {}))

    def replay(self, events: Iterable[DomainEvent]) -> dict[str, object]:
        return self.digital_twin.replay(events).snapshot()

    def run(self, session: SimulationSession) -> dict[str, Any]:
        return self.runner.run(session, self.digital_twin.snapshot())

    def predict(self) -> Prediction:
        return Prediction()

    def assess_risk(self) -> RiskAssessment:
        return RiskAssessment()

    def assess_impact(self) -> ImpactAssessment:
        return ImpactAssessment()

    def simulate_execution(self) -> ExecutionSimulation:
        return ExecutionSimulation()
