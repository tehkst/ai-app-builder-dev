from pathlib import Path
from typing import List, Dict


BASE_DIR = Path(__file__).resolve().parent.parent.parent
GENERATED_APPS_DIR = BASE_DIR / "generated_apps"


def safe_write_generated_files(
    project_id: str,
    generated_files: List[Dict[str, str]],
) -> List[str]:
    project_dir = GENERATED_APPS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    written_files = []

    for file in generated_files:
        relative_path = file.get("file_path")
        content = file.get("content", "")

        if not relative_path:
            continue

        target_path = project_dir / relative_path
        resolved_target = target_path.resolve()

        if not str(resolved_target).startswith(str(project_dir.resolve())):
            raise ValueError(f"Unsafe file path blocked: {relative_path}")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")

        written_files.append(str(target_path))

    return written_files
