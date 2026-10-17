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


SECRET_MARKER = "fixture-body-must-not-leave-the-machine"


def assert_grade_cap(result: dict) -> None:
    """Two or more high-severity risks cap the grade at C; the report says so when the cap applied."""
    highs = sum(1 for r in result["all_risks"] if r["severity"] == "high")
    overall, raw = result["overall"], grade(result["overall"]["score"])
    if highs >= 2:
        assert overall["grade"] in {"C", "D", "F"}, overall
        assert bool(overall["grade_note"]) == ("ABCDF".index(raw) < "ABCDF".index("C")), overall


def check_v2_online(base: Path) -> None:
    """Versions, end-of-life, vulnerabilities, stack configuration and grade cap, with a fake network."""
    from datetime import date, timedelta

    root = base / "agency-client"
    (root / "config").mkdir(parents=True)
    (root / "package.json").write_text(json.dumps({"engines": {"node": ">=16"}, "dependencies": {"lodash": "^4.17.0"}}))
    lock_packages = {"": {}, "node_modules/lodash": {"version": "4.17.15"}, "node_modules/left-pad": {"version": "1.3.0"}}
    for i in range(12000):  # pad the lockfile past the 2 MB source-file cap: it must still be parsed
        lock_packages[f"node_modules/padding-package-with-a-long-name-{i:05d}"] = {"version": "1.0.0", "resolved": "x" * 120}
    (root / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": lock_packages}))
    assert (root / "package-lock.json").stat().st_size > 2_000_000
    (root / ".python-version").write_text("3.99\n")
    (root / "composer.json").write_text(json.dumps({"require": {"php": "^8.2", "laravel/framework": "^10.0"}}))
    (root / "composer.lock").write_text(json.dumps({"packages": [{"name": "laravel/framework", "version": "v10.1.0"}]}))
    (root / "wp-config.php").write_text("<?php // " + SECRET_MARKER + "\ndefine( 'DB_PASSWORD', 'realpass123' );\n"
                                        "define( 'WP_DEBUG', true );\n")
    (root / "config" / "settings.py").write_text("DEBUG = True\nALLOWED_HOSTS = ['*']\n")
    soon = (date.today() + timedelta(days=60)).isoformat()
    calls = []

    def fake_fetch(url, payload=None):
        calls.append((url, payload))
        assert url.startswith(("https://endoflife.date/api/", "https://api.osv.dev/v1/")), url
        if "endoflife.date" in url:
            product = url.rsplit("/", 1)[-1][:-5]
            return {"nodejs": [{"cycle": "26", "eol": "2029-04-30"}, {"cycle": "16", "eol": "2023-09-11"}],
                    "php": [{"cycle": "8.5", "eol": "2029-12-31"}, {"cycle": "8.2", "eol": soon}],
                    "laravel": [{"cycle": "13", "eol": "2028-03-17"}, {"cycle": "10", "eol": "2025-02-04"}],
                    "python": [{"cycle": "3.14", "eol": "2030-10-31"}]}.get(product, [])
        if url.endswith("querybatch"):
            many = [{"id": f"GHSA-test-{n:04d}"} for n in range(1, 31)]  # 30 advisories: only the last is high
            return {"results": [{"vulns": many} if q["package"]["name"] == "lodash" else {} for q in payload["queries"]]}
        severity = "HIGH" if url.endswith("0030") else "LOW"
        return {"id": url.rsplit("/", 1)[-1], "summary": "Prototype pollution", "database_specific": {"severity": severity}}

    result = run_health_check(str(root), fetch=fake_fetch)
    areas = {a["key"]: a for a in result["areas"]}
    statuses = {i["label"]: i["status"] for i in areas["runtimes"]["data"]["items"]}
    assert statuses == {"Node.js": "end_of_life", "PHP": "ending_soon", "Laravel": "end_of_life", "Python": "unknown"}, statuses
    assert any("Node.js 16 is no longer supported" in f["title"] for f in areas["runtimes"]["findings"])
    affected = areas["vulnerabilities"]["data"]["affected"]
    assert [(a["name"], a["worst"]) for a in affected] == [("lodash", "high")], affected
    kinds = {h["kind"] for h in areas["security"]["data"]["locations"]}
    assert "WordPress database password or salt" in kinds, kinds
    issues = {i["issue"] for i in areas["configuration"]["data"]["issues"]}
    assert {"WordPress debug mode is on", "Django DEBUG = True"} <= issues, issues
    sent = json.dumps([payload for _, payload in calls])
    assert SECRET_MARKER not in sent and "realpass123" not in sent and "DEBUG" not in sent, "only names and versions may be sent"
    assert_grade_cap(result)
    report = render_markdown(result)
    assert "Versions in use" in report and "GHSA-test-0001" in report and "realpass123" not in report
    assert areas["vulnerabilities"]["data"]["advisories"] == 30 and areas["vulnerabilities"]["data"]["unrated_advisories"] == 0

    pnpm_root = base / "pnpm5"
    pnpm_root.mkdir()
    (pnpm_root / "pnpm-lock.yaml").write_text("lockfileVersion: 5.4\npackages:\n  /lodash/4.17.15:\n    resolution: {}\n"
                                              "  /@scope/pkg/1.0.0_react@18.2.0:\n    resolution: {}\n")
    from app.platform.codebase_health.inventory import build_inventory
    from app.platform.codebase_health.versions import locked_packages
    got = {(p["name"], p["version"]) for p in locked_packages(build_inventory(pnpm_root))}
    assert got == {("lodash", "4.17.15"), ("@scope/pkg", "1.0.0")}, got

    calls.clear()
    offline = run_health_check(str(root), online_lookups=False, fetch=fake_fetch)
    offline_areas = {a["key"]: a for a in offline["areas"]}
    assert not calls, "offline runs must not touch the network"
    assert not offline_areas["vulnerabilities"]["data"]["checked"] and "Offline run" in offline["method"]
    assert {i["status"] for i in offline_areas["runtimes"]["data"]["items"]} == {"not_checked"}


def main() -> None:
    with tempfile.TemporaryDirectory() as base:
        root, outside = Path(base, "shop"), Path(base, "outside")
        root.mkdir(), outside.mkdir()
        build_fixture(root, outside)
        result = run_health_check(str(root), online_lookups=False)
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
        assert_grade_cap(result)
        check_v2_online(Path(base))
    print("CODEBASE HEALTH CHECK PASSED")


if __name__ == "__main__":
    main()
