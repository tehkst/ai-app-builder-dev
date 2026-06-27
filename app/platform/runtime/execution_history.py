from __future__ import annotations

from typing import Dict, List


def append_history(history: List[Dict[str, str]], event: Dict[str, str]) -> List[Dict[str, str]]:
    return history + [dict(event)]


def last_state(history: List[Dict[str, str]]) -> str:
    if not history:
        return ""
    return history[-1].get("next_state", "")
