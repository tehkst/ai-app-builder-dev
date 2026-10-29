"""Check for step 4b, delivering client work: the typed repository confirmation, one pull request per
piece of work, a new branch only (default branch untouched, no force), 3-way apply over unrelated
client commits, a clean refusal when the client's code changed underneath, and patch downloads.
A local bare repository stands in for GitHub's git server and a fake for its API (no network)."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest import mock

from fastapi.testclient import TestClient

from app.platform.auth.service import _sign_claims
from app.platform.clients import delivery, service, work
from app.platform.clients.work_check import HANDOVER, FakeSandbox, PLAN
from app.platform.orca import MissionStore, Orca, api_service, runner, sandbox_commands
from app.platform.orca.orca_check import PASS, Pod, finish, write
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformClientCodebase
from app.platform.server import app

REAL_PROTOCOLS = list(delivery.PROTOCOLS)  # main() relaxes them for the stand-in GitHub
GIT = ["git", "-c", "user.name=Client", "-c", "user.email=client@example.com", "-c", "init.defaultBranch=main",
       "-c", "core.hooksPath=/dev/null"]


def git(cwd: Path, *args: str) -> str:
    return subprocess.run([*GIT, *args], cwd=str(cwd), capture_output=True, text=True, check=True).stdout.strip()


def client_repo(base: Path, name: str) -> Dict[str, Path]:
    """A bare 'GitHub' repo with one commit, and the fetched copy the platform would hold."""
    seed, bare, fetched = base / f"{name}-seed", base / f"{name}.git", base / f"{name}-fetched"
    seed.mkdir()
    (seed / "package.json").write_text(json.dumps({"name": name, "scripts": {"test": "node test.js"}}))
    (seed / "greet.js").write_text("module.exports = () => 'hi';\n")
    (seed / "README.md").write_text("# Shop\n")
    git(seed, "init", "--quiet")
    git(seed, "add", "--all")
    git(seed, "commit", "--quiet", "-m", "initial")
    git(base, "clone", "--quiet", "--bare", str(seed), str(bare))
    git(base, "clone", "--quiet", str(bare), str(fetched))
    return {"seed": seed, "bare": bare, "fetched": fetched}


def upstream_commit(base: Path, bare: Path, path: str, content: str) -> None:
    """The client pushes a commit of their own after we fetched."""
    other = Path(tempfile.mkdtemp(dir=base))
    git(base, "clone", "--quiet", str(bare), str(other / "c"))
    (other / "c" / path).write_text(content)
    git(other / "c", "commit", "--quiet", "-am", "client change")
    git(other / "c", "push", "--quiet", "origin", "main")


class FakeGitHub:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.open: Dict[str, str] = {}  # "owner:branch" -> PR url
        self.fail_next_post = False

    def __call__(self, method, path, token, body=None):
        self.calls.append({"method": method, "path": path, "token": token, "body": body})
        owner_repo = path.split("/repos/", 1)[1].split("/pulls", 1)[0]
        if method == "GET":
            head = path.split("head=", 1)[1]
            return [{"html_url": self.open[head]}] if head in self.open else []
        if self.fail_next_post:
            self.fail_next_post = False
            raise delivery.DeliveryError("GitHub could not be reached: timed out")
        url = f"https://github.com/{owner_repo}/pull/{len(self.open) + 1}"
        self.open[f"{owner_repo.split('/')[0]}:{body['head']}"] = url
        return {"html_url": url}


def check_helpers() -> None:
    assert delivery.github_repo("https://github.com/kopi/shop") == ("kopi", "shop")
    assert delivery.github_repo("https://github.com/kopi/shop.git") == ("kopi", "shop")
    for bad in ("https://gitlab.com/kopi/shop", "https://github.com/kopi", "https://github.com/a/b/c", "/Users/x/shop",
                "http://github.com/kopi/shop", "https://github.com/../shop"):
        assert delivery.github_repo(bad) is None, bad
    assert delivery.branch_name("Fix: member discount (checkout)!", "WK-0123456789") == "ai-factory/fix-member-discount-checkout-456789"
    assert delivery.branch_name("???", "WK-abcdefabcd") == "ai-factory/change-efabcd"


def check_direct(base: Path, hub: FakeGitHub) -> None:
    """3-way apply over an unrelated client commit works; a conflicting one is refused, nothing pushed."""
    mission = SimpleNamespace(plan_summary="s", status="complete", tasks=[SimpleNamespace(
        title="Return hello", status="passed", acceptance_checks=["npm test"])])
    for name, client_edit, expect_ok in (("unrelated", ("README.md", "# Shop\nNow with cake.\n"), True),
                                         ("conflict", ("greet.js", "module.exports = () => 'hey';\n"), False)):
        repo = client_repo(base, name)
        copy = work.prepare_copy(str(repo["fetched"]), f"CL-{name}")
        Path(copy["workspace"], "greet.js").write_text("module.exports = () => 'hello';\n")
        upstream_commit(base, repo["bare"], *client_edit)
        with mock.patch.object(delivery, "remote_url", lambda o, r, b=repo["bare"]: str(b)):
            try:
                result = delivery.open_pull_request(source=f"https://github.com/kopi/{name}", workspace=copy["workspace"],
                                                    git_dir=copy["git_dir"], work_id=copy["work_id"], job_title="Say hello",
                                                    mission=mission, token="test-token")
            except delivery.DeliveryError as exc:
                assert not expect_ok, exc
                assert "no longer apply" in str(exc), exc
                assert git(repo["bare"], "branch", "--list", "ai-factory/*") == "", "nothing pushed after a refusal"
                continue
        assert expect_ok
        branch = result["branch"]
        assert git(repo["bare"], "show", f"{branch}:greet.js") == "module.exports = () => 'hello';"
        assert "Now with cake." in git(repo["bare"], "show", f"{branch}:README.md"), "client's own commit kept"
        assert git(repo["bare"], "show", "main:greet.js") == "module.exports = () => 'hi';", "default branch untouched"
        assert result["base"] == "main" and result["files_changed"] == 1

    # Someone else's branch with the same name is never reused or overwritten.
    repo = client_repo(base, "taken")
    copy = work.prepare_copy(str(repo["fetched"]), "CL-taken")
    Path(copy["workspace"], "greet.js").write_text("module.exports = () => 'hello';\n")
    branch = delivery.branch_name("Say hello", copy["work_id"])
    other = base / "taken-other"
    git(base, "clone", "--quiet", str(repo["bare"]), str(other))
    git(other, "checkout", "--quiet", "-b", branch)
    (other / "x.txt").write_text("theirs\n")
    git(other, "add", "x.txt")
    git(other, "commit", "--quiet", "-m", "their work")
    git(other, "push", "--quiet", "origin", branch)
    with mock.patch.object(delivery, "remote_url", lambda o, r: str(repo["bare"])):
        try:
            delivery.open_pull_request(source="https://github.com/kopi/taken", workspace=copy["workspace"],
                                       git_dir=copy["git_dir"], work_id=copy["work_id"], job_title="Say hello",
                                       mission=mission, token="test-token")
            raise AssertionError("an unrelated branch was reused")
        except delivery.DeliveryError as exc:
            assert "wasn't made for this work" in str(exc), exc
    assert git(repo["bare"], "log", "-1", "--format=%s", branch) == "their work", "their branch untouched"


def check_local_branch(base: Path) -> None:
    """Code added from a git folder on this Mac gets a new branch in that repository: the checked-out
    branch, uncommitted files and hooks are left alone, a retry reuses the branch, and someone else's
    branch with the same name is never overwritten."""
    repo = base / "own-app"
    repo.mkdir()
    (repo / "greet.js").write_text("module.exports = () => 'hi';\n")
    git(repo, "init", "--quiet")
    git(repo, "add", "--all")
    git(repo, "commit", "--quiet", "-m", "initial")
    hook = repo / ".git" / "hooks" / "reference-transaction"
    hook.write_text(f"#!/bin/sh\ntouch {base / 'hook-ran'}\n")
    hook.chmod(0o755)
    assert delivery.local_repo(str(repo)) == repo.resolve() and delivery.local_repo("https://github.com/a/b") is None
    assert delivery.local_repo(str(base)) is None and delivery.local_repo("own-app") is None, "a git folder, by full path"
    copy = work.prepare_copy(str(repo), "CL-own")
    Path(copy["workspace"], "greet.js").write_text("module.exports = () => 'hello';\n")
    (repo / "notes.txt").write_text("uncommitted work in progress\n")  # the owner is mid-change
    mission = SimpleNamespace(plan_summary="s", status="complete_unverified", handover=None,
                              integration={"passed": True, "not_run": [{"command": "npm test", "needs": "a database"}]},
                              tasks=[SimpleNamespace(title="Return hello", status="passed", acceptance_checks=["npm run lint", "npm test"])])
    args = dict(source=str(repo), workspace=copy["workspace"], git_dir=copy["git_dir"], work_id=copy["work_id"],
                job_title="Say hello", mission=mission)
    with mock.patch.object(delivery, "PROTOCOLS", REAL_PROTOCOLS):  # works under the production settings
        result = delivery.create_local_branch(**args)
    branch = result["branch"]
    assert result["base"] == "main" and result["target"] == str(repo.resolve()) and result["files_changed"] == 1, result
    assert git(repo, "show", f"{branch}:greet.js") == "module.exports = () => 'hello';"
    message = git(repo, "log", "-1", "--format=%B", branch)
    assert delivery.work_marker(copy["work_id"]) in message and "- `npm run lint`" in message, message
    assert "> - `npm test` (needs a database)" in message, "unchecked checks are named, not hidden"
    assert git(repo, "symbolic-ref", "--short", "HEAD") == "main", "checked-out branch unchanged"
    assert (repo / "greet.js").read_text() == "module.exports = () => 'hi';\n", "working files unchanged"
    assert (repo / "notes.txt").exists() and not (base / "hook-ran").exists(), "uncommitted file kept, no hooks run"
    assert delivery.create_local_branch(**args)["branch"] == branch, "a retry reuses its own branch"

    git(repo, "branch", "-f", branch, "main")  # now someone else's branch has that name
    try:
        delivery.create_local_branch(**args)
        raise AssertionError("someone else's branch was reused")
    except delivery.DeliveryError as exc:
        assert "wasn't made for this work" in str(exc), exc
    assert git(repo, "log", "-1", "--format=%s", branch) == "initial", "their branch untouched"


def check_api_flow(base: Path, hub: FakeGitHub) -> None:
    os.environ["ASF_CLIENT_WORKSPACES"] = str(base / "workspaces")
    service.HEALTH_CHECK_ONLINE = False
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    token = _sign_claims({"sub": "founder@example.com", "role": "founder", "exp": expires})
    http = TestClient(app)

    def post(path: str, **body):
        return http.post(f"/mission-control/{path}", json={"token": token, **body}).json()

    repo = client_repo(base, "shop")
    client_id = post("clients/create", name="Kopi Shop")["client"]["client_id"]
    create_platform_tables()
    github_cb = f"CB-{uuid.uuid4().hex[:10]}"
    with PlatformSessionLocal() as db:  # as if fetched from GitHub (no network in checks)
        db.add(PlatformClientCodebase(codebase_id=github_cb, client_id=client_id, label="shop", source_kind="git_url",
                                      source="https://github.com/kopi/shop", local_path=str(repo["fetched"]), status="ready"))
        db.commit()
    local = base / "local-shop"
    local.mkdir()
    (local / "a.txt").write_text("a\n")
    local_cb = post("clients/add-codebase", client_id=client_id, source=str(local))["codebase"]["codebase_id"]
    job = post("clients/add-job", client_id=client_id, title="Say hello", kind="fix")["job"]
    detail = post("clients/detail", client_id=client_id)
    provider, terms = detail["ai_provider"], detail["ai_terms"]["version"]

    store, fake = MissionStore(base / "missions"), FakeSandbox()
    pod = Pod({"Software Architect": [*finish("p1", PLAN)],
               "Builder": [*write("b1", "greet.js", "module.exports = () => 'hello';\n", "returns hello")],
               "QA Lead": [*finish("q1", PASS)], "Security Reviewer": [*finish("s1", PASS)],
               "Technical Writer": [*finish("w1", HANDOVER)]})
    with mock.patch.object(api_service, "_orca_factory", lambda: Orca(chat=pod, store=store)), \
            mock.patch.object(sandbox_commands, "run_in_sandbox", fake), \
            mock.patch.object(delivery, "remote_url", lambda o, r: str(repo["bare"])), \
            mock.patch("app.platform.credential_vault.service.resolve_credential",
                       lambda key: "test-token" if key == delivery.TOKEN_KEY else None):
        started = post("clients/start-work", job_id=job["job_id"], codebase_id=github_cb, client_consent=True,
                       ai_provider=provider, terms_version=terms)
        mission_id = started["mission_id"]
        runner.wait_for(mission_id, 60)
        work_id = started["work_id"]
        early = post("clients/deliver", work_id=work_id, confirm_repository="kopi/shop")
        assert early["status"] == "invalid-request" and "finished" in early["error"], early
        post("orca/decide-execution", mission_id=mission_id, approved=True)
        runner.wait_for(mission_id, 60)
        assert store.load(mission_id).status == "complete"

        for wrong in ("", "kopi/other", "KOPI/SHOP"):
            refused = post("clients/deliver", work_id=work_id, confirm_repository=wrong)
            assert refused["status"] == "invalid-request" and "Type kopi/shop" in refused["error"], refused
        assert all(c["path"] != "/repos/kopi/shop/pulls" for c in hub.calls)
        hub.fail_next_post = True  # the branch gets pushed, then GitHub's API times out
        failed = post("clients/deliver", work_id=work_id, confirm_repository="kopi/shop")
        assert failed["status"] == "invalid-request" and "timed out" in failed["error"], failed
        assert git(repo["bare"], "branch", "--list", "ai-factory/*"), "the branch was pushed before the failure"
        sent = post("clients/deliver", work_id=work_id, confirm_repository="kopi/shop")  # retry finishes the job
        assert sent["status"] == "delivered", sent
        pr = sent["delivery"]
        assert pr["url"].startswith("https://github.com/kopi/shop/pull/") and pr["branch"].startswith("ai-factory/say-hello-")
        call = [c for c in hub.calls if c["path"] == "/repos/kopi/shop/pulls"][-1]
        assert call["method"] == "POST" and call["token"] == "test-token"
        assert call["body"]["head"] == pr["branch"] and call["body"]["base"] == "main"
        assert "`npm test`" in call["body"]["body"] and "Nothing is merged" in call["body"]["body"]
        assert HANDOVER["summary"] in call["body"]["body"] and "How to check it" in call["body"]["body"], "handover in the PR"
        assert git(repo["bare"], "show", f"{pr['branch']}:greet.js") == "module.exports = () => 'hello';"
        assert git(repo["bare"], "show", "main:greet.js") == "module.exports = () => 'hi';"
        assert "node_modules" not in git(repo["bare"], "show", "--stat", pr["branch"]), "installed packages never delivered"
        again = post("clients/deliver", work_id=work_id, confirm_repository="kopi/shop")
        assert again["status"] == "already-delivered" and again["delivery"]["url"] == pr["url"]
        shop_posts = [c for c in hub.calls if c["method"] == "POST" and c["path"] == "/repos/kopi/shop/pulls"]
        assert hub.open[f"kopi:{pr['branch']}"] == pr["url"] and len(shop_posts) == 2  # failed, then retried once

        detail = post("clients/detail", client_id=client_id)["client"]
        delivered = {j["job_id"]: j for j in detail["jobs"]}[job["job_id"]]
        assert delivered["status"] == "delivered" and delivered["work"]["pr_target"] == "kopi/shop"
        assert delivered["work"]["deliveries"][0]["url"] == pr["url"]

        assert http.post("/mission-control/clients/patch", json={"work_id": work_id}).status_code == 404
        download = http.post("/mission-control/clients/patch", json={"token": token, "work_id": work_id})
        assert download.status_code == 200 and b"+module.exports = () => 'hello';" in download.content
        assert 'filename="say-hello-' in download.headers["content-disposition"]
        post("clients/update-job", job_id=job["job_id"], status="in_progress")
        assert http.post("/mission-control/clients/patch", json={"token": token, "work_id": work_id}).status_code == 200
        assert {j["job_id"]: j for j in post("clients/detail", client_id=client_id)["client"]["jobs"]}[job["job_id"]]["status"] == "delivered"

        # Code from a folder on this Mac: patch only.
        job2 = post("clients/add-job", client_id=client_id, title="Tidy", kind="fix")["job"]
        pod.scripts.update({"Software Architect": [*finish("p2", PLAN)]})
        local_work = post("clients/start-work", job_id=job2["job_id"], codebase_id=local_cb, client_consent=True,
                          ai_provider=provider, terms_version=terms)
        runner.wait_for(local_work["mission_id"], 60)
        local_send = post("clients/deliver", work_id=local_work["work_id"], confirm_repository="kopi/shop")
        assert local_send["status"] == "invalid-request" and "patch" in local_send["error"], local_send


def main() -> None:
    hub = FakeGitHub()
    with tempfile.TemporaryDirectory() as tmp, \
            mock.patch.object(delivery, "PROTOCOLS", ["-c", "protocol.allow=always"]), \
            mock.patch.object(delivery, "github_request", hub):  # local stand-ins for GitHub: never the network
        base = Path(tmp).resolve()
        check_helpers()
        check_local_branch(base)
        check_direct(base, hub)
        check_api_flow(base, hub)
    print("CLIENT DELIVERY CHECK PASSED")


if __name__ == "__main__":
    main()
