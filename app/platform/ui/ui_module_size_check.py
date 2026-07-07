from __future__ import annotations

from pathlib import Path


MAX_LINES = 200
EXEMPT = {
    "app/platform/ui/founder_dashboard_stable.py",  # legacy monolith; split over follow-up PRs
}


def main() -> None:
    failures: list[str] = []
    for path in Path("app/platform/ui").glob("*.py"):
        rel = str(path)
        if rel in EXEMPT:
            continue
        line_count = len(path.read_text().splitlines())
        if line_count > MAX_LINES:
            failures.append(f"{rel}: {line_count} lines")

    if failures:
        raise SystemExit("UI module size limit exceeded:\n" + "\n".join(failures))

    print("ui module size ok")


if __name__ == "__main__":
    main()
