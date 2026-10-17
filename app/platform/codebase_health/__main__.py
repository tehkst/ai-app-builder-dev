"""CLI: python -m app.platform.codebase_health PATH [--out DIR] [--pdf] [--json]

Runs the read-only Health Check on a local folder (clone the client's repository first, read-only)
and writes <project>-health-check.md (and .pdf / .json when asked) to --out (default: current folder).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.platform.codebase_health.report import render_markdown, render_pdf
from app.platform.codebase_health.service import run_health_check


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Codebase Health Check.")
    parser.add_argument("path", help="Folder of the codebase to check")
    parser.add_argument("--out", default=".", help="Where to write the report")
    parser.add_argument("--pdf", action="store_true", help="Also write a client-ready PDF")
    parser.add_argument("--json", action="store_true", help="Also write the raw results as JSON")
    parser.add_argument("--offline", action="store_true", help="Skip endoflife.date and OSV.dev lookups")
    args = parser.parse_args()
    result = run_health_check(args.path, online_lookups=not args.offline)
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"{result['project']}-health-check"
    stem.with_suffix(".md").write_text(render_markdown(result), encoding="utf-8")
    written = [stem.with_suffix(".md")]
    if args.pdf:
        written.append(Path(render_pdf(result, str(stem.with_suffix(".pdf")))))
    if args.json:
        stem.with_suffix(".json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        written.append(stem.with_suffix(".json"))
    print(f"{result['project']}: {result['overall']['grade']} ({result['overall']['score']}/100)")
    for path in written:
        print(f"  wrote {path}")


if __name__ == "__main__":
    main()
