from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.platform.compatibility.scanner import scan_file


def main() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)

        supported = root / "supported.py"
        supported.write_text(
            "from __future__ import annotations\n"
            "def load(value: dict[str, str] | None = None) -> list[str]:\n"
            "    return list((value or {}).values())\n",
            encoding="utf-8",
        )
        assert scan_file(supported) == []

        builtins = root / "builtins.py"
        builtins.write_text(
            "def load(value: dict[str, str]) -> list[str]:\n"
            "    return list(value.values())\n",
            encoding="utf-8",
        )
        assert scan_file(builtins) == []

        unsupported = root / "unsupported.py"
        unsupported.write_text(
            "def load(value: str | None = None):\n"
            "    return value\n",
            encoding="utf-8",
        )
        issues = scan_file(unsupported)
        assert len(issues) == 1
        assert issues[0]["pattern"] == "pep604_union_without_future_annotations"

    print("PYTHON 3.9 COMPATIBILITY SCANNER CHECK PASSED")


if __name__ == "__main__":
    main()
