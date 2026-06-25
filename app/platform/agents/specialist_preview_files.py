from pathlib import Path
from typing import Any, Dict, List


TEMPLATE_DIR = Path(__file__).with_name("templates")


def _template(name: str, **values: str) -> str:
    """Render small preview templates without interpreting CSS/JS braces.

    These preview assets contain normal CSS and JavaScript blocks with braces. Python
    str.format treats those braces as placeholders and can raise KeyError values such
    as '\n  margin'. Keep rendering intentionally narrow: replace only explicit tokens
    passed by the caller and leave all other braces untouched.
    """

    rendered = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def build_preview_generated_files(goal: str) -> List[Dict[str, Any]]:
    return [
        {
            "path": "index.html",
            "language": "html",
            "purpose": "Static browser entry point for the generated app preview.",
            "content": _template("preview_index.html", goal=goal),
            "content_preview": "Static HTML shell for the generated browser app preview.",
            "write_status": "preview_only",
        },
        {
            "path": "styles.css",
            "language": "css",
            "purpose": "Styles for the generated browser app preview.",
            "content": _template("preview_styles.css"),
            "content_preview": "CSS styles for the generated browser app preview.",
            "write_status": "preview_only",
        },
        {
            "path": "app.js",
            "language": "javascript",
            "purpose": "Small browser interaction script for the generated app preview.",
            "content": _template("preview_app.js"),
            "content_preview": "JavaScript interaction for DB-preview browser review.",
            "write_status": "preview_only",
        },
        {
            "path": "README.md",
            "language": "markdown",
            "purpose": "Operator notes for the generated DB-preview app.",
            "content": _template("preview_readme.md", goal=goal),
            "content_preview": "README notes for the generated DB-preview app.",
            "write_status": "preview_only",
        },
    ]
