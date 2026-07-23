from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutivePerspective:
    primary: str
    supporting: tuple[str, ...] = ()

    @property
    def prompt_instruction(self) -> str:
        if not self.supporting:
            return f"Use the judgment and priorities of an experienced {self.primary}."
        support = ", ".join(self.supporting)
        return f"Lead as an experienced {self.primary}, while synthesizing the relevant judgment of {support}."


class ExecutivePerspectiveSelector:
    """Selects advisory perspective only; it grants no execution authority."""

    _SIGNALS = {
        "CEO Advisor": r"\b(strategy|market|fundrais|investor|positioning|company|revenue|business model|competitive)\b",
        "CTO": r"\b(architecture|platform|system design|technology|technical strategy|infrastructure|security|scalability)\b",
        "Chief Product Officer": r"\b(product|customer|user|founder experience|onboarding|roadmap|prioriti[sz]|design|agents?)\b",
        "VP Engineering": r"\b(delivery|execution plan|engineering team|capacity|quality|release|sprint|timeline|process)\b",
        "Principal Engineer": r"\b(debug|bug|code|implementation|refactor|test failure|root cause|repository|performance)\b",
    }

    @classmethod
    def select(cls, message: str) -> ExecutivePerspective:
        normalized = " ".join(message.lower().split())
        matches = [name for name, pattern in cls._SIGNALS.items() if re.search(pattern, normalized)]
        if not matches:
            return ExecutivePerspective("CEO Advisor")
        return ExecutivePerspective(matches[0], tuple(matches[1:3]))
