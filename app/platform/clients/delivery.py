"""Hand the AI team's work to the client (step 4b): a pull request on their GitHub repo, or a patch.

Nothing leaves this machine until the founder has looked at the changes and confirmed, by typing the
repository name, that a pull request should be opened there. Delivery never merges, never
force-pushes and never touches the default branch: it pushes one new branch and opens a pull
request against the default branch for the client to review.

How the branch is built:
1. The patch is the diff of the mission copy against its baseline (`work.patch`), so it contains
   exactly what the AI team changed; installed packages and caches are excluded.
2. A fresh clone of the client's repo (https only, hooks off, token via GIT_ASKPASS) gets a new
   branch; the patch is applied with `git apply --3way --index`, so it still lands if the client
   pushed unrelated commits since the code was fetched. If it doesn't apply, nothing is pushed.
3. One commit, pushed without force to `refs/heads/<new branch>` (an existing branch makes the push
   fail), then the GitHub API opens the pull request. The clone is deleted afterwards.

The token is the "GitHub Token (client pull requests)" credential the founder saves in Settings
(contents + pull requests write on the client's repo). It is never logged or stored with the work.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from app.platform.clients.fetch import git_auth_env
from app.platform.clients.work import SAFE_GIT, WorkError, patch

TOKEN_KEY = "GITHUB_CLIENT_DELIVERY_TOKEN"
GIT_TIMEOUT = 600
GITHUB_API = "https://api.github.com"
BRANCH_PREFIX = "ai-factory/"
NAME = re.compile(r"^(?!\.{1,2}$)[A-Za-z0-9_.-]{1,100}$")  # never "." or ".."
# Only https remotes (checks swap in a local file:// remote).
PROTOCOLS = ["-c", "protocol.allow=never", "-c", "protocol.https.allow=always"]


class DeliveryError(ValueError):
    pass


def github_repo(source: str) -> Optional[Tuple[str, str]]:
    """(owner, repo) for an https://github.com/owner/repo source, else None."""
    parsed = urlparse(source or "")
    parts = [p for p in parsed.path.split("/") if p]
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com" or len(parts) != 2:
        return None
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return (owner, repo) if NAME.match(owner) and NAME.match(repo) else None


def remote_url(owner: str, repo: str) -> str:
    return f"https://github.com/{owner}/{repo}.git"


def branch_name(title: str, work_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-") or "change"
    return f"{BRANCH_PREFIX}{slug}-{work_id[-6:].lower()}"


def github_request(method: str, path: str, token: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    request = urllib.request.Request(GITHUB_API + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
                                              "X-GitHub-Api-Version": "2022-11-28",
                                              "User-Agent": "ai-software-factory-delivery"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read() or b"{}").get("message") or ""
        except ValueError:
            detail = ""
        raise DeliveryError(f"GitHub refused the pull request ({exc.code}{': ' + detail if detail else ''}).") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise DeliveryError(f"GitHub could not be reached: {exc}") from exc


def _git(cwd: Path, env: Dict[str, str], *args: str, secret: str = "") -> str:
    done = subprocess.run(["git", *PROTOCOLS, *SAFE_GIT, "-c", "credential.helper=", *args], cwd=str(cwd), env=env,
                          capture_output=True, text=True, timeout=GIT_TIMEOUT)
    if done.returncode != 0:
        message = ((done.stderr or done.stdout).strip().splitlines() or [f"git {args[0]} failed"])[-1]
        raise DeliveryError(f"git {args[0]}: {message.replace(secret or chr(0), '***')[:300]}")
    return done.stdout.strip()


def pr_body(job_title: str, mission: Any) -> str:
    lines = [f"## {job_title}", "", mission.plan_summary or "", "", "### What was done"]
    for task in mission.tasks:
        lines.append(f"- {'✅' if task.status == 'passed' else '⚠️'} {task.title}")
    checks = [c for t in mission.tasks for c in t.acceptance_checks]
    if mission.status == "complete":
        lines += ["", "### Checks", "These passed in an isolated container:"] + [f"- `{c}`" for c in checks]
    else:
        lines += ["", "> The project's tests were not run for this change. Please test before merging."]
    lines += ["", "Prepared by AI Software Factory and reviewed before sending. Nothing is merged until you merge it."]
    return "\n".join(lines)


def open_pull_request(*, source: str, workspace: str, git_dir: str, work_id: str, job_title: str, mission: Any,
                      token: str) -> Dict[str, Any]:
    repo = github_repo(source)
    if repo is None:
        raise DeliveryError("Pull requests go to GitHub repositories; download the patch instead.")
    if not token:
        raise DeliveryError("Add the GitHub Token (client pull requests) in Settings -> Credentials first.")
    owner, name = repo
    diff = patch(workspace, git_dir)
    if not diff["patch"].strip():  # bytes
        raise DeliveryError("There are no changes to deliver.")
    branch = branch_name(job_title, work_id)
    scratch = Path(tempfile.mkdtemp(prefix="asf-delivery-"))
    url = remote_url(owner, name)
    try:
        clone, patch_file = scratch / "repo", scratch / "changes.patch"
        patch_file.write_bytes(diff["patch"])
        with git_auth_env(url, token) as env:
            _git(scratch, env, "clone", "--single-branch", "--no-recurse-submodules", "--quiet", url, str(clone), secret=token)
            base = _git(clone, env, "symbolic-ref", "--short", "HEAD")
            _git(clone, env, "checkout", "--quiet", "-b", branch)
            try:
                _git(clone, env, "apply", "--3way", "--index", "--whitespace=nowarn", str(patch_file))
            except DeliveryError as exc:
                raise DeliveryError("The changes no longer apply to the client's repository (it changed since the code "
                                    f"was fetched). Fetch the code again and restart the job. ({exc})") from exc
            _git(clone, env, "commit", "--quiet", "--no-verify", "-m", job_title, "-m",
                 "Prepared by AI Software Factory.")
            _git(clone, env, "push", "--quiet", "origin", f"HEAD:refs/heads/{branch}", secret=token)
        created = github_request("POST", f"/repos/{owner}/{name}/pulls", token,
                                 {"title": job_title, "head": branch, "base": base, "body": pr_body(job_title, mission)})
        pr_url = str(created.get("html_url") or "")
        if not pr_url.startswith(f"https://github.com/{owner}/{name}/pull/"):
            raise DeliveryError("GitHub did not return a pull request link.")
        return {"target": f"{owner}/{name}", "branch": branch, "base": base, "url": pr_url,
                "files_changed": diff["files_changed"]}
    except subprocess.TimeoutExpired as exc:
        raise DeliveryError("Talking to GitHub took too long and was stopped.") from exc
    except WorkError as exc:
        raise DeliveryError(str(exc)) from exc
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
