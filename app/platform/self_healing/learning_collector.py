from __future__ import annotations

from typing import Dict, List


def collect_learning(records: List[Dict[str, object]], diagnosis: str, plan: str, result: str) -> List[Dict[str, object]]:
    return records + [
        {
            "diagnosis": diagnosis,
            "plan": plan,
            "result": result,
        }
    ]
