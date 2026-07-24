from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from app.ai.templates.trusted import TRUSTED_TEMPLATES
from app.platform.artifacts.qualification_target import (
    GENERATED_APP_PATH_ENV,
    configured_generated_app_path,
    generated_app_path,
)


VALIDATORS = (
    "app.platform.frontend.validate_frontend_contract",
    "app.platform.frontend.validate_frontend_build",
    "app.platform.security_report",
    "app.platform.artifacts.registry_report",
)


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "artifact-reference"
        for relative_path, content in TRUSTED_TEMPLATES.items():
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        assert generated_app_path(str(root)) == root.resolve()
        environment = dict(os.environ)
        environment[GENERATED_APP_PATH_ENV] = str(root)
        previous = os.environ.get(GENERATED_APP_PATH_ENV)
        os.environ[GENERATED_APP_PATH_ENV] = str(root)
        try:
            assert configured_generated_app_path() == root.resolve()
            from app.ai.nodes.file_writer import file_writer_node

            written = file_writer_node(
                {
                    "project_id": "different-project-id",
                    "file_manifest": {
                        "files": [
                            {
                                "file_path": "qualification-marker.txt",
                                "content": "canonical-target\n",
                            }
                        ]
                    },
                }
            )
            assert (
                Path(
                    written["generated_files"]["qualification-marker.txt"]
                ).resolve()
                == (root / "qualification-marker.txt").resolve()
            )
        finally:
            if previous is None:
                os.environ.pop(GENERATED_APP_PATH_ENV, None)
            else:
                os.environ[GENERATED_APP_PATH_ENV] = previous
        for module in VALIDATORS:
            result = subprocess.run(
                [sys.executable, "-m", module],
                cwd=Path(__file__).resolve().parents[3],
                env=environment,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (module, result.stdout, result.stderr)

        for module in (
            "app.platform.artifacts.refresh_manifest",
            "app.platform.artifacts.detect_drift",
        ):
            result = subprocess.run(
                [sys.executable, "-m", module],
                cwd=Path(__file__).resolve().parents[3],
                env=environment,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (module, result.stdout, result.stderr)

        profile = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.platform.validate_all",
                "--profile",
                "artifact",
                "--artifact-path",
                str(root),
            ],
            cwd=Path(__file__).resolve().parents[3],
            capture_output=True,
            text=True,
        )
        assert profile.returncode == 0, (profile.stdout, profile.stderr)

    print("AFOS-013 ARTIFACT QUALIFICATION TARGET CHECK PASSED")


if __name__ == "__main__":
    run()
