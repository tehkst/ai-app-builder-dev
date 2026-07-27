from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


GENERATED_ROOT = Path("generated_apps")


def bounded_source_directory(value: Any) -> str:
    text = str(value or ".").strip()
    if text == ".":
        return text
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        return "."
    if len(path.parts) != 2 or path.parts[0] != GENERATED_ROOT.name:
        return "."
    if not re.fullmatch(r"app-[a-z0-9-]{3,80}", path.parts[1]):
        return "."
    return path.as_posix()


def deployment_options(request: dict[str, str]) -> list[str]:
    if request["source_directory"] == ".":
        return []
    if not request["service_name"].startswith("afos-app-"):
        raise ValueError("Generated application deployments require an afos-app service.")
    options = [
        "--service-account",
        "ai-software-factory-deploy@%s.iam.gserviceaccount.com" % request["project_id"],
        "--add-cloudsql-instances",
        "%s:%s:ai-factory-db" % (request["project_id"], request["region"]),
        "--set-secrets",
        "APP_SESSION_SECRET=MISSION_CONTROL_SESSION_SECRET:latest,"
        "DATABASE_URL=ai-software-factory-production-database-url:latest,"
        "SMTP_PASSWORD=smtp-password:latest",
    ]
    smtp_env_vars = {
        name: os.environ.get(name, "")
        for name in ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "EMAIL_FROM")
        if os.environ.get(name)
    }
    if smtp_env_vars:
        options += [
            "--set-env-vars",
            ",".join("%s=%s" % (name, value) for name, value in smtp_env_vars.items()),
        ]
    return options
