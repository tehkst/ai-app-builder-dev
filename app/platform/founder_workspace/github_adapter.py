from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class GitHubRequestWriteError(RuntimeError):
    """Raised when a GitHub request artifact cannot be written."""


@dataclass(frozen=True)
class GitHubRequestWriteConfig:
    repository: str
    token: str
    base_branch: str = "main"
    write_branch_prefix: str = "founder-requests"
    create_pull_request: bool = False
    api_url: str = "https://api.github.com"

    @classmethod
    def from_environment(cls) -> "GitHubRequestWriteConfig | None":
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        repository = (
            os.getenv("AI_FACTORY_REQUEST_REPOSITORY")
            or os.getenv("GITHUB_REPOSITORY")
            or ""
        ).strip()
        if not token or not repository:
            return None

        return cls(
            repository=repository,
            token=token,
            base_branch=os.getenv("AI_FACTORY_REQUEST_BASE_BRANCH", "main").strip() or "main",
            write_branch_prefix=(
                os.getenv("AI_FACTORY_REQUEST_BRANCH_PREFIX", "founder-requests").strip()
                or "founder-requests"
            ),
            create_pull_request=os.getenv(
                "AI_FACTORY_REQUEST_CREATE_PR",
                "false",
            ).strip().lower()
            in {"1", "true", "yes", "on"},
            api_url=os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/"),
        )


@dataclass(frozen=True)
class GitHubRequestWriteResult:
    repository: str
    branch: str
    path: str
    commit_sha: str | None
    pull_request_url: str | None
    mode: str


class GitHubRequestWriteAdapter:
    """GitHub-backed write adapter for Founder Workspace requests.

    The adapter writes request artifacts through GitHub's REST API using only
    Python standard-library modules so the platform does not gain a new runtime
    dependency. It supports safe idempotent writes by checking whether the
    target artifact already exists before creating or updating it.
    """

    def __init__(self, config: GitHubRequestWriteConfig):
        self.config = config

    def write_request_artifact(
        self,
        *,
        request_id: str,
        artifact_path: str,
        content: str,
        title: str,
    ) -> GitHubRequestWriteResult:
        branch = self._write_branch(request_id)
        base_sha = self._get_branch_head_sha(self.config.base_branch)

        if branch != self.config.base_branch:
            self._ensure_branch(branch, base_sha)

        existing = self._get_file_metadata(artifact_path, branch)
        if existing and existing.get("content"):
            decoded = base64.b64decode(existing["content"]).decode("utf-8")
            if decoded == content:
                return GitHubRequestWriteResult(
                    repository=self.config.repository,
                    branch=branch,
                    path=artifact_path,
                    commit_sha=None,
                    pull_request_url=None,
                    mode="duplicate-existing-artifact",
                )

        commit_sha = self._put_file(
            path=artifact_path,
            content=content,
            branch=branch,
            message=f"GCP-02 capture founder request {request_id}: {title}",
            sha=existing.get("sha") if existing else None,
        )

        pull_request_url = None
        if self.config.create_pull_request and branch != self.config.base_branch:
            pull_request_url = self._create_pull_request(
                branch=branch,
                request_id=request_id,
                title=title,
            )

        return GitHubRequestWriteResult(
            repository=self.config.repository,
            branch=branch,
            path=artifact_path,
            commit_sha=commit_sha,
            pull_request_url=pull_request_url,
            mode="github",
        )

    def _write_branch(self, request_id: str) -> str:
        if not self.config.create_pull_request:
            return self.config.base_branch
        safe_request_id = request_id.lower().replace("_", "-")
        return f"{self.config.write_branch_prefix}/{safe_request_id}"

    def _get_branch_head_sha(self, branch: str) -> str:
        response = self._request("GET", f"/repos/{self.config.repository}/git/ref/heads/{branch}")
        try:
            return str(response["object"]["sha"])
        except KeyError as exc:
            raise GitHubRequestWriteError(f"Unable to resolve branch head for {branch}") from exc

    def _ensure_branch(self, branch: str, base_sha: str) -> None:
        try:
            self._request("GET", f"/repos/{self.config.repository}/git/ref/heads/{branch}")
            return
        except GitHubRequestWriteError as exc:
            if "404" not in str(exc):
                raise

        self._request(
            "POST",
            f"/repos/{self.config.repository}/git/refs",
            {
                "ref": f"refs/heads/{branch}",
                "sha": base_sha,
            },
        )

    def _get_file_metadata(self, path: str, branch: str) -> dict[str, Any] | None:
        encoded_path = urllib.parse.quote(path)
        try:
            return self._request(
                "GET",
                f"/repos/{self.config.repository}/contents/{encoded_path}?ref={branch}",
            )
        except GitHubRequestWriteError as exc:
            if "404" in str(exc):
                return None
            raise

    def _put_file(
        self,
        *,
        path: str,
        content: str,
        branch: str,
        message: str,
        sha: str | None,
    ) -> str:
        encoded_path = urllib.parse.quote(path)
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        response = self._request(
            "PUT",
            f"/repos/{self.config.repository}/contents/{encoded_path}",
            payload,
        )
        try:
            return str(response["commit"]["sha"])
        except KeyError as exc:
            raise GitHubRequestWriteError("GitHub response did not include a commit SHA") from exc

    def _create_pull_request(self, *, branch: str, request_id: str, title: str) -> str | None:
        try:
            response = self._request(
                "POST",
                f"/repos/{self.config.repository}/pulls",
                {
                    "title": f"GCP-02 Founder Request {request_id}: {title}",
                    "head": branch,
                    "base": self.config.base_branch,
                    "body": (
                        "GitHub-backed Founder Workspace request artifact.\n\n"
                        f"- Request ID: `{request_id}`\n"
                        "- Source: `/mission-control/requests`\n"
                        "- Milestone: GCP-02"
                    ),
                },
            )
        except GitHubRequestWriteError as exc:
            if "Validation Failed" in str(exc) or "already exists" in str(exc):
                return None
            raise

        return response.get("html_url")

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.config.token}",
            "User-Agent": "ai-software-factory-gcp-02",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{self.config.api_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise GitHubRequestWriteError(
                f"GitHub API {method} {path} failed with {exc.code}: {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise GitHubRequestWriteError(f"GitHub API {method} {path} failed: {exc}") from exc

        if not raw:
            return {}
        return json.loads(raw)
