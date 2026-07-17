from __future__ import annotations

from typing import Any, Optional

from app.platform.company_brain.company_brain import CompanyBrain
from app.platform.digital_twin.twin_runtime import DigitalTwin
from app.platform.executive_ai.ceo import CEO
from app.platform.executive_ai.cfo import CFO
from app.platform.executive_ai.coo import COO
from app.platform.executive_ai.cto import CTO
from app.platform.simulation.simulation_engine import SimulationEngine


class ExecutiveCouncil:
    def __init__(
        self, company_brain: Optional[CompanyBrain] = None,
        digital_twin: Optional[DigitalTwin] = None,
        simulation_engine: Optional[SimulationEngine] = None,
    ) -> None:
        brain = company_brain or CompanyBrain()
        twin = digital_twin or DigitalTwin()
        simulation = simulation_engine or SimulationEngine(brain, twin)
        self.company_brain = brain
        self.digital_twin = twin
        self.simulation_engine = simulation
        self.members = [CEO(brain, twin, simulation), CTO(brain, twin, simulation), COO(brain, twin, simulation), CFO(brain, twin, simulation)]

    def consult(self, request: str) -> dict[str, Any]:
        return {"status": "interfaces_ready", "autonomous_reasoning": False, "advice": [member.advise(request) for member in self.members]}
