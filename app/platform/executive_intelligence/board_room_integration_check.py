from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep

from app.platform.executive_intelligence.board_room_integration import inspect_board_room_integration


CONTEXT = """from app.platform.executive_intelligence.service import build_executive_intelligence_briefing\n\nclass ContextRetriever:\n    def retrieve(self):\n        sources = {\"executive_intelligence\": self._safe(build_executive_intelligence_briefing)}\n        return sources\n"""
CONSOLE = """from app.platform.board_room.executive_reasoning_engine import ExecutiveReasoningEngine\n\ndef board_room_chat(payload):\n    return ExecutiveReasoningEngine().reason(payload[\"message\"])\n"""
ENGINE = """from app.platform.board_room.context_retriever import ContextRetriever\n\nclass ExecutiveReasoningEngine:\n    def __init__(self):\n        self.context_retriever = ContextRetriever()\n    def reason(self, message):\n        return self.context_retriever.retrieve(message)\n"""
INTELLIGENCE = """def build_executive_intelligence_briefing():\n    return {\"state_contract_version\": \"executive-state-v1\"}\n"""


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        _write(root, "app/platform/board_room/context_retriever.py", CONTEXT)
        _write(root, "app/platform/board_room/executive_reasoning_engine.py", ENGINE)
        _write(root, "app/platform/operating_console/service.py", CONSOLE)
        _write(root, "app/platform/executive_intelligence/service.py", INTELLIGENCE)

        valid = inspect_board_room_integration(root)
        assert valid["status"] == "consuming_executive_intelligence"
        assert valid["confidence"] == "high" and valid["unknown_reason"] is None

        _write(
            root,
            "app/platform/operating_console/service.py",
            "from app.platform.company_intelligence.service import build_company_intelligence_snapshot\n" + CONSOLE,
        )
        legacy = inspect_board_room_integration(root)
        assert legacy["status"] == "unknown"
        assert "authoritative legacy company intelligence absent" in legacy["unknown_reason"]

        first_checked_at = legacy["checked_at"]
        sleep(1.1)
        _write(root, "app/platform/operating_console/service.py", CONSOLE)
        refreshed = inspect_board_room_integration(root)
        assert refreshed["status"] == "consuming_executive_intelligence"
        assert refreshed["checked_at"] != first_checked_at

        _write(root, "app/platform/board_room/context_retriever.py", "class ContextRetriever: pass\n")
        missing = inspect_board_room_integration(root)
        assert missing["status"] == "unknown"
        assert "board room calls executive intelligence" in missing["unknown_reason"]
    print("Board Room Executive Intelligence integration evidence checks passed")


if __name__ == "__main__":
    main()
