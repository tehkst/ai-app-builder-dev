from app.ai.state import ProjectState
from app.ai.templates.trusted import TRUSTED_TEMPLATES

def template_enforcer_node(state: ProjectState) -> ProjectState:
    manifest = state.get("file_manifest", {})
    files = manifest.get("files", [])

    updated_files = []
    existing_paths = set()

    for file in files:
        file_path = file.get("file_path")
        existing_paths.add(file_path)

        if file_path in TRUSTED_TEMPLATES:
            file = {
                **file,
                "content": TRUSTED_TEMPLATES[file_path],
                "purpose": "Trusted enterprise template",
            }

        updated_files.append(file)

    for file_path, content in TRUSTED_TEMPLATES.items():
        if file_path not in existing_paths:
            updated_files.append(
                {
                    "file_path": file_path,
                    "file_type": "template",
                    "purpose": "Trusted enterprise template",
                    "content": content,
                }
            )

    return {
        **state,
        "file_manifest": {
            "files": updated_files,
        },
        "current_step": "templates_enforced",
    }
