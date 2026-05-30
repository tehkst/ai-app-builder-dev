from pathlib import Path

from app.ai.state import ProjectState


GENERATED_APPS_DIR = Path("generated_apps")


def safe_write_file(base_dir: Path, file_path: str, content: str) -> str:
    target_path = base_dir / file_path
    resolved_target = target_path.resolve()
    resolved_base = base_dir.resolve()

    if not str(resolved_target).startswith(str(resolved_base)):
        raise ValueError(f"Unsafe file path blocked: {file_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")

    return str(target_path)


def file_writer_node(state: ProjectState) -> ProjectState:
    project_id = state["project_id"]
    project_dir = GENERATED_APPS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    written_files = {}

    manifest = state.get("file_manifest", {})
    files = manifest.get("files", [])

    for file in files:
        written_path = safe_write_file(
            base_dir=project_dir,
            file_path=file["file_path"],
            content=file["content"],
        )

        written_files[file["file_path"]] = written_path

    return {
        **state,
        "generated_files": written_files,
        "current_step": "files_written",
    }
