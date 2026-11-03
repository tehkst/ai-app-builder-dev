"""Check the Codebase Map: the scanner (endpoints, requests, mounts, matching, hosts, secrets), globs
and assignment, the architecture checks and the Cartographer's fix round, descriptions and their
carry-over on updates, redaction (no secret reaches the AI or the map), the founder-only API with the
consent gate, the viewer and the export for the client. A scripted Cartographer; no network."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

from app.platform.codebase_map import build, cartographer
from app.platform.codebase_map.sample import FILES, write_sample
from app.platform.codebase_map.sample_architecture import ARCHITECTURE
from app.platform.codebase_map.scan import build_scan
from app.platform.nautilus.loop_check import call, turn

SECRET = "sk_live_" + "4" * 24


class Cartographer:
    """A scripted Codebase Cartographer: answers the architecture briefing with `arch` (after one
    file read), any fix request with `fixed`, and each worksheet with a name for every file and
    endpoint in it. Records everything sent to it."""

    def __init__(self, arch: Dict[str, Any], fixed: Dict[str, Any] = None) -> None:
        self.arch, self.fixed = arch, fixed or arch
        self.seen: List[str] = []
        self.worksheets: List[List[str]] = []
        self.lock = threading.Lock()

    def __call__(self, messages, tools):
        with self.lock:
            self.seen += [str(m.get("content", "")) for m in messages]
        last = messages[-1]
        if last.get("role") == "tool" and "final_output" in str(messages[-2].get("tool_calls", "")):
            return turn("Done.")
        brief = messages[1]["content"]
        if last.get("role") == "user" and "found these problems" in str(last.get("content")):
            return turn("", [call("fix", "final_output", **self.fixed)])
        if "## Scan summary" in brief:
            if last.get("role") == "user":
                return turn("", [call("r1", "read_file", path="api/app/settings.py")])
            return turn("", [call("a1", "final_output", **self.arch)])
        paths = re.findall(r"^### (\S+)", brief, re.M)
        keys = re.findall(r"^- ((?:GET|POST|PUT|PATCH|DELETE|ANY|AJAX) \S+)", brief, re.M)
        with self.lock:
            self.worksheets.append(paths)
        return turn("", [call("d1", "final_output",
                              files=[{"path": p, "name": "Name of " + p.split("/")[-1], "description": f"Does {p}."} for p in paths],
                              routes=[{"key": k, "name": "Endpoint " + k, "description": "Answers " + k} for k in keys])])


def check_scan(root: Path) -> None:
    scan = build_scan(str(root))
    keys = {(r.key, r.file) for r in scan.routes}
    for expected in (("GET /api/orders", "api/app/routes/orders.py"),  # blueprint mounted with url_prefix elsewhere
                     ("POST /api/orders", "api/app/routes/orders.py"),
                     ("GET /api/orders/<int:order_id>", "api/app/routes/orders.py"),
                     ("GET /v2/users/:id", "server/routes/users.js"),  # router mounted with app.use, middleware in front
                     ("POST /v2/users", "server/routes/users.js"),
                     ("GET /api/items", "web/src/app/api/items/route.ts"),  # Next.js route file
                     ("GET /wp-json/bakery/v1/cakes/*", "plugin/bakery.php"),  # WordPress REST, READABLE
                     ("AJAX /admin-ajax/bakery_save", "plugin/bakery.php")):
        assert expected in keys, (expected, sorted(keys))
    matched = {(q.method, q.url, r.key) for q, r, _ in scan.http}
    assert ("GET", "*/api/orders", "GET /api/orders") in matched, "an unknown base URL is dropped; the method stays GET"
    assert ("POST", "/api/orders", "POST /api/orders") in matched, "fetch options give the method"
    assert ("GET", "/api/orders/*", "GET /api/orders/<int:order_id>") in matched
    assert ("GET", "/v2/users/*", "GET /v2/users/:id") in matched
    assert ("AJAX", "/admin-ajax/bakery_save", "AJAX /admin-ajax/bakery_save") in matched
    assert set(scan.hosts) == {"api.stripe.com", "api.sendgrid.com"}, scan.hosts
    assert [(s["file"], s["kind"]) for s in scan.secrets] == [("api/app/settings.py", "Stripe live key")], scan.secrets
    assert "web/src/app/[shop]/page.tsx" in scan.entrypoints()
    assert scan.files["api/app/routes/orders.py"].doc == "Order endpoints."
    assert scan.files["api/app/routes/orders.py"].defines[0] == "orders: List or create orders."


def check_globs() -> None:
    G = build.Glob
    assert G("web").matches("web/src/a.ts") and G("web/").matches("web/a.ts") and not G("web").matches("webapp/a.ts")
    assert G("web/src/app/**/page.tsx").matches("web/src/app/page.tsx")
    assert G("web/src/app/**/page.tsx").matches("web/src/app/a/b/page.tsx")
    assert G("app/orders/[id]/**").matches("app/orders/[id]/page.tsx") and not G("app/orders/[id]/**").matches("app/orders/i/x")
    assert G("src/*.{ts,tsx}").matches("src/a.tsx") and not G("src/*.{ts,tsx}").matches("src/x/a.ts")
    assert G("**/*.test.ts").matches("a/b/c.test.ts") and G("**/*.test.ts").matches("c.test.ts")
    assert G("lib/file?.py").matches("lib/file1.py") and G("[ab].py").matches("a.py")


def check_architecture(root: Path) -> None:
    scan = build_scan(str(root))
    arch = build.clean_architecture(ARCHITECTURE)
    assert build.check_architecture(scan, arch) == []
    owner = build.assign(scan, arch)
    assert owner["web/src/app/orders/page.tsx"] == "web.pages" and owner["web/src/lib/api.ts"] == "web.client", "deepest wins"
    assert owner["web/src/components/Unused.tsx"] == "web", "files no child claims stay on the parent"
    excluded = {**ARCHITECTURE, "nodes": [{**n, "exclude": ["**/Unused.tsx"]} if n["id"] == "web" else n for n in ARCHITECTURE["nodes"]]}
    assert build.assign(scan, build.clean_architecture(excluded))["web/src/components/Unused.tsx"] == build.UNASSIGNED
    broken = build.clean_architecture({**ARCHITECTURE, "nodes": [
        *[n for n in ARCHITECTURE["nodes"] if n["id"] not in ("api", "accounts")],
        {"id": "x", "label": "X", "kind": "gadget", "parent": "nowhere", "summary": "", "paths": ["nothing-here"]}],
        "flows": [{"title": "F", "steps": [{"node": "web"}, {"node": "ghost.ts"}]}]})
    problems = "\n".join(build.check_architecture(scan, broken))
    for text in ("kind 'gadget'", "parent 'nowhere'", "'x' needs a summary", "'ghost.ts' is not a node id",
                 "belong to no node", "api/app (2)", "server/routes (1)", "'x' claims no files"):
        assert text in problems, (text, problems)
    implied = build.clean_architecture({**ARCHITECTURE, "nodes": [{k: v for k, v in n.items() if k != "parent"}
                                                                for n in ARCHITECTURE["nodes"]]})
    assert {n["id"]: n["parent"] for n in implied["nodes"]}["web.pages"] == "web", "a dotted id implies its parent"
    kept = build.drop_invalid(scan, broken)
    assert {n["id"]: n["kind"] for n in kept["nodes"]}["x"] == "feature" and not kept["flows"], kept["flows"]


def check_make_map(root: Path) -> None:
    # The first architecture has a problem; the fix round corrects it.
    wrong = {**ARCHITECTURE, "nodes": [{**n, "parent": "website"} if n["id"] == "web.pages" else n for n in ARCHITECTURE["nodes"]]}
    bot = Cartographer(wrong, fixed=ARCHITECTURE)
    pinned = []
    with mock.patch.object(cartographer, "chat_factory", lambda p, m: pinned.append((p, m)) or bot):
        result = cartographer.make_map(str(root), "bakery", ("openai", "gpt-test"))
    assert set(pinned) == {("openai", "gpt-test")}, pinned
    assert result["problems"] == [] and any("parent 'website'" in s for s in bot.seen), "the fix round ran"
    assert len(bot.worksheets) == 1, "small parts share one description batch (each batch costs a full briefing)"
    graph = result["graph"]
    by_path = {f["path"]: f for f in graph["files"]}
    code = len(build_scan(str(root)).files)  # README and package.json aren't code
    assert by_path["web/src/lib/api.ts"]["name"] == "Name of api.ts" and result["described"] == code == 12
    assert {r["key"]: r["name"] for r in graph["routes"]}["POST /v2/users"] == "Endpoint POST /v2/users"
    assert graph["stats"]["described"] == graph["stats"]["files"] and graph["stats"]["unassigned"] == 0
    assert ["web/src/lib/api.ts", "api/app/routes/orders.py", "http", "GET /api/orders"] in graph["links"]
    assert ["api/app/routes/orders.py", "stripe", "package", ""] in graph["links"]
    assert ["plugin/bakery.php", "sendgrid", "http", ""] in graph["links"]
    assert graph["flows"][0]["steps"][0]["ref"] == "web/src/app/orders/page.tsx" and len(graph["tour"]) == 2
    health = {h["id"]: h for h in graph["health"]}
    assert health["secrets"]["refs"] == [{"ref": "api/app/settings.py", "note": "Stripe live key (line 1)"}]
    assert [r["ref"] for r in health["unused"]["refs"]] == ["web/src/components/Unused.tsx"], \
        "packages, settings and scripts a page loads (no package.json) aren't 'unused'"
    sent, saved = "\n".join(bot.seen), json.dumps(result)
    assert "settings.py" in sent and SECRET not in sent and SECRET not in saved, "no secret reaches the AI or the map"
    assert "Scan summary" in sent and "ENDPOINTS (" in sent and "Write for the app's owner" in sent

    # An update: unchanged files keep their descriptions (also when moved); only new and changed ones are described.
    previous = {"graph": graph, "architecture": result["architecture"]}
    (root / "web/src/lib/api.ts").write_text(FILES["web/src/lib/api.ts"] + "export async function refund() {}\n")
    (root / "server/routes/people.js").write_text(FILES["server/routes/users.js"])
    (root / "server/routes/users.js").unlink()
    (root / "api/app/notes.py").write_text('"""Notes."""\n')
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    again = Cartographer(ARCHITECTURE)
    with mock.patch.object(cartographer, "chat_factory", lambda p, m: again):
        updated = cartographer.make_map(str(root), "bakery", ("openai", "gpt-test"), previous=previous)
    described = sorted(p for sheet in again.worksheets for p in sheet)
    assert described == ["api/app/notes.py", "web/src/lib/api.ts"], described
    assert not any("## Scan summary" in s for s in again.seen), "the architecture is reused"
    moved = {f["path"]: f for f in updated["graph"]["files"]}["server/routes/people.js"]
    assert moved["name"] == "Name of users.js" and updated["carried"] == code - 1, updated["carried"]


def check_api(root: Path, base: Path) -> None:
    from fastapi.testclient import TestClient

    from app.platform.auth.service import _sign_claims
    from app.platform.clients import maps, service, work
    from app.platform.persistence.database import PlatformSessionLocal
    from app.platform.persistence.models import PlatformClientMap
    from app.platform.server import app

    os.environ["ASF_CLIENT_WORKSPACES"] = str(base / "workspaces")
    service.HEALTH_CHECK_ONLINE = False
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    http = TestClient(app)

    def post(path: str, **body):
        return http.post(f"/mission-control/clients/{path}", json={"token": token, **body}).json()

    client_id = post("create", name="Bakery")["client"]["client_id"]
    codebase_id = post("add-codebase", client_id=client_id, source=str(root))["codebase"]["codebase_id"]
    if codebase_id in service._RUNNING:
        service._RUNNING[codebase_id].join(timeout=120)
    detail = post("detail", client_id=client_id)
    start = dict(codebase_id=codebase_id, client_consent=True, ai_provider=detail["ai_provider"],
                 terms_version=detail["ai_terms"]["version"])
    assert http.post("/mission-control/clients/run-map", json=start).json()["status"] == "unauthorized"
    for missing in ({"client_consent": False}, {"ai_provider": "elsewhere"}):
        refused = post("run-map", **{**start, **missing})
        assert refused["status"] == "invalid-request" and "agreed" in refused["error"], refused
    refused = post("run-map", **{**start, "terms_version": "old"})
    assert refused["status"] == "invalid-request" and "out of date" in refused["error"], refused

    named = {**ARCHITECTURE, "nodes": [{**n, "label": "</script><script>alert(1)</script>"} if n["id"] == "api" else n
                                       for n in ARCHITECTURE["nodes"]]}
    bot, pinned = Cartographer(named), []
    with mock.patch.object(cartographer, "chat_factory", lambda p, m: pinned.append((p, m)) or bot):
        started = post("run-map", **start)
        assert started["status"] == "started", started
        service._RUNNING[started["map_id"]].join(timeout=120)
    assert set(pinned) == {work.current_ai()}, "the map uses the agreed provider"
    shown = post("detail", client_id=client_id)["client"]["codebases"][0]["map"]
    assert shown["status"] == "ready" and shown["stats"]["files"] >= 10 and shown["consent_terms"] == start["terms_version"], shown
    assert shown["health"][0]["title"] == "Passwords or keys written into the code"
    data = post("map-data", map_id=started["map_id"])
    assert data["graph"]["project"]["name"] == "Bakery" and data["meta"]["client"] == "Bakery"
    assert http.post("/mission-control/clients/map-data", json={"map_id": started["map_id"]}).json()["status"] == "unauthorized"

    page = http.get("/mission-control/clients/map")
    assert page.status_code == 200 and "map-data" in page.text and "FP_START" in page.text and "Bakery" not in page.text
    exported = http.post("/mission-control/clients/map-export", json={"token": token, "map_id": started["map_id"]})
    html = exported.text
    assert exported.status_code == 200 and 'filename="' in exported.headers["Content-Disposition"]
    assert "</script><script>alert" not in html and "\\u003c/script\\u003e" in html, "AI-written text can't break out"
    assert str(root) not in html and str(base) not in html and "map-data" not in html.split("window.FP_START(")[1]
    assert '"health": []' in html, "Health stays out of the client's copy unless asked for"
    with_health = http.post("/mission-control/clients/map-export",
                            json={"token": token, "map_id": started["map_id"], "include_health": True}).text
    assert "Passwords or keys written into the code" in with_health and SECRET not in with_health
    assert http.post("/mission-control/clients/map-export", json={"map_id": started["map_id"]}).status_code == 404

    check_jarvis(http, token, started["map_id"])

    with PlatformSessionLocal() as db:  # a run whose worker died with the server
        db.query(PlatformClientMap).filter_by(map_id=started["map_id"]).update({"status": "running"})
        db.commit()
    stale = post("detail", client_id=client_id)["client"]["codebases"][0]["map"]
    assert stale["status"] == "failed" and "interrupted" in stale["error"], stale


def check_jarvis(http, token: str, map_id: str) -> None:
    from app.platform.codebase_map import jarvis

    for text in ("create the system map of my app", "Make a codebase map for Bakery", "can you map my app?",
                 "draw a floorplan of the shop", "visualize the bakery codebase", "map of the whole platform"):
        assert jarvis.is_map_request(text), text
    for text in ("show the architecture map insight", "map the customer field to the CRM", "add a map page to the app",
                 "what's on the roadmap"):
        assert not jarvis.is_map_request(text), text

    def chat(message: str, **extra):
        return http.post("/mission-control/operating-console/chat",
                         json={"message": message, "conversation_id": "c", **extra}).json()

    answer = chat("create the system map of my app", token=token)
    buttons = {b["label"]: b for b in answer["action_metadata"]["action_buttons"]}
    assert "Codebase Map" in answer["board_room_response"], answer
    assert buttons["Open the map of Bakery: bakery"]["payload"] == {"map_id": map_id}, buttons
    assert buttons["Update the map of Bakery: bakery"]["target"] == "startCodebaseMap"
    assert buttons["Map AI Software Factory itself"]["target"] == "startPlatformMap", "'my app' offers the platform"
    named = chat("make a codebase map of Bakery", token=token)["action_metadata"]["action_buttons"]
    assert [b["label"] for b in named] == ["Open the map of Bakery: bakery", "Update the map of Bakery: bakery"], named
    assert "action_metadata" not in chat("create the system map of my app") or \
        chat("create the system map of my app").get("action_metadata", {}).get("intent_type") != "codebase_map", \
        "without a founder session Jarvis doesn't list clients' code"

    first = http.post("/mission-control/clients/map-platform", json={"token": token}).json()
    again = http.post("/mission-control/clients/map-platform", json={"token": token}).json()
    assert first["status"] == "ready" and first["codebase_id"] == again["codebase_id"], "the platform is filed once"
    assert http.post("/mission-control/clients/map-platform", json={}).json()["status"] == "unauthorized"
    own = chat("map my app", token=token)["action_metadata"]["action_buttons"]
    assert [b["label"] for b in own] == ["Make a map of AI Software Factory"] and own[0]["payload"]["own"] is True, own


def check_viewer_javascript() -> None:
    import shutil

    from app.platform.ui.mc2.map_viewer import BOOT, SCRIPT

    node = shutil.which("node")
    if node is None:
        print("  (node not installed: viewer syntax check skipped)")
        return
    for name, source in (("viewer", SCRIPT), ("boot", BOOT)):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
            handle.write(source)
        result = subprocess.run([node, "--check", handle.name], capture_output=True, text=True)
        Path(handle.name).unlink()
        assert result.returncode == 0, f"map {name} script has a syntax error:\n{result.stderr}"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        root = write_sample(base / "bakery")
        check_scan(root)
        check_globs()
        check_viewer_javascript()
        check_architecture(root)
        check_make_map(write_sample(base / "bakery-2"))
        check_api(root, base)
    print("CODEBASE MAP CHECK PASSED")


if __name__ == "__main__":
    main()
