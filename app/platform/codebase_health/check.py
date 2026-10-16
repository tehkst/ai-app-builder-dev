"""Check for the Codebase Health Check: a throwaway fixture project with known problems."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from app.platform.codebase_health.report import render_markdown
from app.platform.codebase_health.service import grade, run_health_check

FAKE_KEY = "AKIA" + "Q" * 16  # built at runtime so the repository itself holds no key-shaped string


def build_fixture(root: Path, outside: Path) -> None:
    (root / "src" / "generated").mkdir(parents=True)
    (root / "package.json").write_text(json.dumps({"dependencies": {"next": "15.0.0", "react": "*"}}))
    (root / "src" / "page.tsx").write_text("export default function Page() { return null }\n" * 30)
    (root / "src" / "big.ts").write_text("export const x = 1;\n" * 900)
    (root / "src" / "generated" / "client.ts").write_text("// @generated\n" + "export const y = 2;\n" * 5000)
    (root / "src" / "config.ts").write_text(f'const key = "{FAKE_KEY}";\n')
    (root / ".env").write_text("SECRET=1\n")
    fallback = "sk-" + "A1b2C3d4" * 5
    (root / "src" / "client.ts").write_text(f'const apiKey = process.env.OPENAI_KEY || "{fallback}";\n')
    (root / "deploy").mkdir()
    (root / "deploy" / "id_rsa").write_text("-----BEGIN " + "RSA PRIVATE KEY-----\nabc\n")
    (root / "pyproject.toml").write_text('[project]\nname = "shop"\ndependencies = ["fastapi>=0.100", "requests==2.31.0"]\n')
    (root / "setup.py").write_text(f"open({str(outside / 'ran.txt')!r}, 'w').write('executed')\n")
    (outside / "elsewhere.ts").write_text("export const z = 3;\n" * 2000)
    os.symlink(outside, root / "linked")  # must not be followed


def main() -> None:
    with tempfile.TemporaryDirectory() as base:
        root, outside = Path(base, "shop"), Path(base, "outside")
        root.mkdir(), outside.mkdir()
        build_fixture(root, outside)
        result = run_health_check(str(root))
        areas = {a["key"]: a for a in result["areas"]}
        assert result["contract"] == "codebase-health-v1" and result["project"] == "shop"
        assert "Next.js" in result["stack"]["frameworks"] and "npm (no lockfile)" in result["stack"]["package_managers"]
        kinds = {h["kind"] for h in areas["security"]["data"]["locations"]}
        assert {"AWS access key", "Committed .env file", "OpenAI-style API key", "Private key"} <= kinds, kinds
        files = {h["file"] for h in areas["security"]["data"]["locations"]}
        assert {"src/client.ts", "deploy/id_rsa"} <= files, files
        deps = areas["dependencies"]["data"]
        assert deps["ecosystems"].get("pip") == 2 and "pip:fastapi" in deps["unpinned"], deps
        assert areas["licence"]["findings"] and areas["licence"]["findings"][0]["title"] == "No licence file"
        markdown = render_markdown(result)
        for value in (FAKE_KEY, "A1b2C3d4" * 5, "abc"):
            assert value not in markdown and value not in json.dumps(result), "secret values must never be reported"
        maintain = areas["maintainability"]["data"]
        assert maintain["generated_files"] == 1 and "src/generated/client.ts" not in str(maintain["largest"])
        assert maintain["largest"][0]["path"] == "src/big.ts"
        assert "elsewhere.ts" not in json.dumps(result), "symlinks out of the codebase must not be followed"
        assert not (outside / "ran.txt").exists(), "nothing from the codebase may be executed"
        titles = [r["title"] for r in result["all_risks"]]
        assert "No automated tests" in titles and "No dependency lockfile" in titles, titles
        assert areas["security"]["score"] == 50 and result["top_risks"][0]["severity"] == "high"
        assert [grade(s) for s in (95, 80, 65, 45, 10)] == ["A", "B", "C", "D", "F"]
        assert result["next_steps"] and "Health Check is the first step of a full Audit" in markdown
    print("CODEBASE HEALTH CHECK PASSED")


if __name__ == "__main__":
    main()
