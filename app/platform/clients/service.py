"""Clients area (Mission Control -> Clients): agency clients, their code, Health Checks and jobs.

Founder-only POST endpoints (`/mission-control/clients/*`, token in the body like the rest of
Mission Control). Fetching code and running a Health Check happen in background threads; the screen
polls `detail`. Health Checks are read-only (nothing from a client's code runs); see
`codebase_health` and `clients/fetch.py`. Fix, feature, upgrade and care-plan jobs can be handed to
the AI team (`start-work`, step 4a): Orca on a copy of the code, commands in the sandbox (`work.py`).
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.platform.auth.service import require_founder
from app.platform.clients import delivery, work
from app.platform.clients.fetch import FetchError, classify_source, clone, workspaces_root
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformClient, PlatformClientCodebase, PlatformClientDelivery, PlatformClientJob, PlatformClientWork

CONTRACT = "clients-v1"
CLIENT_STATUSES = ("lead", "active", "past")
JOB_KINDS = ("health_check", "audit", "fix", "feature", "upgrade", "care_plan")
JOB_STATUSES = ("lead", "quoted", "in_progress", "delivered", "paid", "closed")
HEALTH_CHECK_ONLINE = True  # endoflife.date + OSV.dev lookups; checks switch this off (no network in CI)
_LOCK = threading.Lock()
_START_WORK_LOCK = threading.Lock()
_DELIVER_LOCK = threading.Lock()
DELIVERABLE = ("complete", "complete_unverified")
_RUNNING: Dict[str, threading.Thread] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


def _guard(payload: Dict[str, Any], action: Callable[[Any, Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    founder = require_founder(payload or {})
    if not founder.get("authorized"):
        return {"contract": CONTRACT, "status": "unauthorized", "authenticated": False}
    create_platform_tables()
    with PlatformSessionLocal() as db:
        try:
            return {"contract": CONTRACT, **action(db, payload or {})}
        except (ValueError, FetchError) as exc:  # includes work.WorkError and delivery.DeliveryError
            return {"contract": CONTRACT, "status": "invalid-request", "error": str(exc)}


def _text(payload: Dict[str, Any], key: str, limit: int, required: bool = False) -> str:
    value = str(payload.get(key) or "").strip()[:limit]
    if required and not value:
        raise ValueError(f"{key} is required.")
    return value


def _client_view(client: PlatformClient, codebases, jobs, work_items=(), deliveries=()) -> Dict[str, Any]:
    by_job: Dict[str, Any] = {}
    for item in work_items:  # newest first: the job shows its latest hand-off
        by_job.setdefault(item.job_id, item)
    sources = {c.codebase_id: c.source for c in codebases}
    by_work: Dict[str, List[Dict[str, Any]]] = {}
    for d in deliveries:
        by_work.setdefault(d.work_id, []).append(_delivery_view(d))
    return {"client_id": client.client_id, "name": client.name, "contact": client.contact, "notes": client.notes,
            "status": client.status, "created_at": _iso(client.created_at), "updated_at": _iso(client.updated_at),
            "codebases": [_codebase_view(c) for c in codebases],
            "jobs": [_job_view(j, by_job.get(j.job_id), sources, by_work) for j in jobs]}


def _delivery_view(d: PlatformClientDelivery) -> Dict[str, Any]:
    return {"kind": d.kind, "target": d.target, "branch": d.branch, "url": d.url, "files_changed": d.files_changed,
            "at": _iso(d.created_at)}


def _codebase_view(c: PlatformClientCodebase) -> Dict[str, Any]:
    summary = json.loads(c.last_check_json) if c.last_check_json else None
    return {"codebase_id": c.codebase_id, "label": c.label, "source_kind": c.source_kind, "source": c.source,
            "status": c.status, "error": c.error, "last_check": summary, "has_report": bool(c.last_report_path),
            "last_checked_at": _iso(c.last_checked_at), "running": _running(c.codebase_id)}


def _job_view(j: PlatformClientJob, item: Optional[PlatformClientWork] = None, sources: Optional[Dict[str, str]] = None,
              deliveries: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> Dict[str, Any]:
    view = {"job_id": j.job_id, "title": j.title, "kind": j.kind, "status": j.status, "price": j.price,
            "notes": j.notes, "updated_at": _iso(j.updated_at), "can_start_work": j.kind in work.WORK_KINDS, "work": None}
    if item is not None:
        view["work"] = {"work_id": item.work_id, "codebase_id": item.codebase_id, "ai_provider": item.ai_provider,
                        "started_at": _iso(item.created_at), "mission": work.mission_view(item.mission_id),
                        "pr_target": "/".join(delivery.github_repo((sources or {}).get(item.codebase_id, "")) or ()) or None,
                        "deliveries": (deliveries or {}).get(item.work_id, [])}
    return view


def _running(key: str) -> bool:
    with _LOCK:
        thread = _RUNNING.get(key)
        return bool(thread and thread.is_alive())


def _start(key: str, work: Callable[[], None]) -> bool:
    with _LOCK:
        if key in _RUNNING and _RUNNING[key].is_alive():
            return False
        thread = threading.Thread(target=work, name=f"client-{key}", daemon=True)
        _RUNNING[key] = thread
        thread.start()
        return True


TRANSIENT = {"fetching": "Fetching was interrupted (the server restarted). Run it again.",
             "checking": "The Health Check was interrupted (the server restarted). Run it again."}


def _reconcile(db, codebase: PlatformClientCodebase) -> None:
    """A fetch/check whose worker thread is gone (e.g. after a restart) is marked interrupted, not busy forever."""
    if codebase.status in TRANSIENT and not _running(codebase.codebase_id):
        codebase.status, codebase.error, codebase.updated_at = "failed", TRANSIENT[codebase.status], _now()
        db.commit()


def _client(db, client_id: str) -> PlatformClient:
    client = db.query(PlatformClient).filter_by(client_id=client_id).first()
    if not client:
        raise ValueError("No such client.")
    return client


# ---- endpoints ------------------------------------------------------------------------------

def list_clients(payload: Dict[str, Any]) -> Dict[str, Any]:
    def action(db, _):
        clients = db.query(PlatformClient).order_by(PlatformClient.updated_at.desc()).all()
        out = []
        for c in clients:
            codebases = db.query(PlatformClientCodebase).filter_by(client_id=c.client_id).all()
            for codebase in codebases:
                _reconcile(db, codebase)
            jobs = db.query(PlatformClientJob).filter_by(client_id=c.client_id).all()
            out.append(_client_view(c, codebases, jobs))
        return {"status": "ready", "clients": out}
    return _guard(payload, action)


def client_detail(payload: Dict[str, Any]) -> Dict[str, Any]:
    def action(db, p):
        client = _client(db, _text(p, "client_id", 64, True))
        codebases = db.query(PlatformClientCodebase).filter_by(client_id=client.client_id).order_by(PlatformClientCodebase.created_at).all()
        for codebase in codebases:
            _reconcile(db, codebase)
        jobs = db.query(PlatformClientJob).filter_by(client_id=client.client_id).order_by(PlatformClientJob.created_at.desc()).all()
        items = db.query(PlatformClientWork).filter_by(client_id=client.client_id).order_by(PlatformClientWork.id.desc()).all()
        sent = db.query(PlatformClientDelivery).filter(PlatformClientDelivery.work_id.in_([i.work_id for i in items])).all() if items else []
        return {"status": "ready", "client": _client_view(client, codebases, jobs, items, sent), "ai_provider": work.provider_label()}
    return _guard(payload, action)


def create_client(payload: Dict[str, Any]) -> Dict[str, Any]:
    def action(db, p):
        client = PlatformClient(client_id=f"CL-{uuid.uuid4().hex[:10]}", name=_text(p, "name", 120, True),
                                contact=_text(p, "contact", 200) or None, notes=_text(p, "notes", 4000), status="lead")
        db.add(client)
        db.commit()
        return {"status": "created", "client": _client_view(client, [], [])}
    return _guard(payload, action)


def update_client(payload: Dict[str, Any]) -> Dict[str, Any]:
    def action(db, p):
        client = _client(db, _text(p, "client_id", 64, True))
        if "status" in p:
            if p["status"] not in CLIENT_STATUSES:
                raise ValueError(f"status must be one of {CLIENT_STATUSES}.")
            client.status = p["status"]
        for key, limit in (("name", 120), ("contact", 200), ("notes", 4000)):
            if key in p:
                setattr(client, key, _text(p, key, limit, key == "name") or (None if key == "contact" else ""))
        client.updated_at = _now()
        db.commit()
        return {"status": "updated"}
    return _guard(payload, action)


def add_codebase(payload: Dict[str, Any]) -> Dict[str, Any]:
    def action(db, p):
        client = _client(db, _text(p, "client_id", 64, True))
        kind, source = classify_source(_text(p, "source", 500, True))
        codebase = PlatformClientCodebase(
            codebase_id=f"CB-{uuid.uuid4().hex[:10]}", client_id=client.client_id,
            label=_text(p, "label", 120) or Path(source.rstrip("/")).name.removesuffix(".git") or "codebase",
            source_kind=kind, source=source, status="added")
        if kind == "local_folder":
            codebase.local_path, codebase.status = source, "ready"
        db.add(codebase)
        client.updated_at = _now()
        db.commit()
        if kind == "git_url":
            _start(codebase.codebase_id, lambda: _fetch(codebase.codebase_id))
        return {"status": "added", "codebase": _codebase_view(codebase)}
    return _guard(payload, action)


def run_check(payload: Dict[str, Any]) -> Dict[str, Any]:
    def action(db, p):
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=_text(p, "codebase_id", 64, True)).first()
        if not codebase:
            raise ValueError("No such codebase.")
        _reconcile(db, codebase)
        if _running(codebase.codebase_id):
            return {"status": "already-running"}
        if not codebase.local_path:  # a git fetch never finished: fetch again (the check follows)
            started = _start(codebase.codebase_id, lambda: _fetch(codebase.codebase_id))
            return {"status": "started" if started else "already-running"}
        started = _start(codebase.codebase_id, lambda: _check(codebase.codebase_id))
        return {"status": "started" if started else "already-running"}
    return _guard(payload, action)


def add_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    def action(db, p):
        client = _client(db, _text(p, "client_id", 64, True))
        kind = _text(p, "kind", 32) or "fix"
        if kind not in JOB_KINDS:
            raise ValueError(f"kind must be one of {JOB_KINDS}.")
        job = PlatformClientJob(job_id=f"JB-{uuid.uuid4().hex[:10]}", client_id=client.client_id,
                                title=_text(p, "title", 200, True), kind=kind, status="lead",
                                price=_text(p, "price", 60) or None, notes=_text(p, "notes", 4000))
        db.add(job)
        client.updated_at = _now()
        db.commit()
        return {"status": "created", "job": _job_view(job)}
    return _guard(payload, action)


def update_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    def action(db, p):
        job = db.query(PlatformClientJob).filter_by(job_id=_text(p, "job_id", 64, True)).first()
        if not job:
            raise ValueError("No such job.")
        if "status" in p:
            if p["status"] not in JOB_STATUSES:
                raise ValueError(f"status must be one of {JOB_STATUSES}.")
            job.status = p["status"]
        for key, limit in (("price", 60), ("notes", 4000), ("title", 200)):
            if key in p:
                setattr(job, key, _text(p, key, limit, key == "title") or (None if key == "price" else ""))
        job.updated_at = _now()
        db.commit()
        return {"status": "updated", "job": _job_view(job)}
    return _guard(payload, action)


def start_work(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Hand a job to the AI team. The founder must confirm the client agreed to their code being
    sent to the AI provider named in the confirmation (`client_consent: true` + that provider)."""
    def action(db, p):
        job = db.query(PlatformClientJob).filter_by(job_id=_text(p, "job_id", 64, True)).first()
        if not job:
            raise ValueError("No such job.")
        if job.kind not in work.WORK_KINDS:
            raise ValueError("Only fix, feature, upgrade and care-plan jobs go to the AI team.")
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=_text(p, "codebase_id", 64, True),
                                                             client_id=job.client_id).first()
        if not codebase:
            raise ValueError("Choose one of this client's codebases.")
        _reconcile(db, codebase)
        if codebase.status not in ("ready", "failed") or not codebase.local_path or _running(codebase.codebase_id):
            raise ValueError("Wait until the code is fetched and checked.")
        ai = work.current_ai()
        provider = work.provider_label(ai)
        if ai is None:
            raise ValueError("Choose an AI provider in Settings first.")
        if p.get("client_consent") is not True or p.get("ai_provider") != provider:
            raise ValueError(f"Confirm the client agreed to their code being sent to {provider}.")
        with _START_WORK_LOCK:  # two tabs or a retried request must not start two missions for one job
            return _start_work_locked(db, p, job, codebase, ai, provider)
    return _guard(payload, action)


def _start_work_locked(db, p, job, codebase, ai, provider) -> Dict[str, Any]:
    """Runs under _START_WORK_LOCK: check for active work, then copy, start and record."""
    db.expire_all()  # see work another request committed while we waited for the lock
    latest = db.query(PlatformClientWork).filter_by(job_id=job.job_id).order_by(PlatformClientWork.id.desc()).first()
    if latest:
        current = work.mission_view(latest.mission_id)
        if current and not current["finished"]:
            raise ValueError("The AI team is already working on this job.")
    client = _client(db, job.client_id)
    goal = job.title + (f"\n\n{job.notes}" if job.notes else "") + (
        f"\n\n{_text(p, 'instructions', 4000)}" if p.get("instructions") else "")
    copy = work.prepare_copy(codebase.local_path, client.client_id)
    mission = work.start_mission(goal=goal, workspace=copy["workspace"], client={
        "client_id": client.client_id, "client_name": client.name, "job_id": job.job_id,
        "codebase_id": codebase.codebase_id, "work_id": copy["work_id"]}, ai=ai)
    founder = require_founder(p).get("email") or "founder"
    item = PlatformClientWork(work_id=copy["work_id"], job_id=job.job_id, client_id=client.client_id,
                              codebase_id=codebase.codebase_id, mission_id=mission.mission_id,
                              workspace=copy["workspace"], git_dir=copy["git_dir"], ai_provider=provider,
                              consent_by=founder)
    db.add(item)
    if job.status in ("lead", "quoted"):
        job.status = "in_progress"
    job.updated_at = client.updated_at = _now()
    db.commit()
    return {"status": "started", "work_id": item.work_id, "mission_id": mission.mission_id}


def work_changes(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The AI team's changes so far, compared with the client's code as received."""
    def action(db, p):
        item = db.query(PlatformClientWork).filter_by(work_id=_text(p, "work_id", 64, True)).first()
        if not item:
            raise ValueError("No such work.")
        return {"status": "ready", **work.changes(item.workspace, item.git_dir)}
    return _guard(payload, action)


def _finished_mission(item: PlatformClientWork, accept_unverified: bool):
    from app.platform.orca import api_service, runner

    mission = api_service._orca_factory().store.load(item.mission_id)
    if mission is None:
        raise ValueError("The AI team's mission record is missing.")
    if runner.is_running(mission.mission_id) or mission.status not in DELIVERABLE:
        raise ValueError("Only finished work can be delivered: wait until the AI team is done and checked.")
    if mission.status == "complete_unverified" and not accept_unverified:
        raise ValueError("The project's tests were not run for this work. Confirm you want to send it anyway.")
    return mission


def deliver(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Open a pull request on the client's GitHub repo with the AI team's changes. The founder types
    the repository name to confirm (`confirm_repository`); one pull request per piece of work."""
    def action(db, p):
        item = db.query(PlatformClientWork).filter_by(work_id=_text(p, "work_id", 64, True)).first()
        if not item:
            raise ValueError("No such work.")
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=item.codebase_id).first()
        repo = delivery.github_repo(codebase.source if codebase else "")
        if repo is None:
            raise ValueError("This code didn't come from GitHub; download the patch instead.")
        target = "/".join(repo)
        if _text(p, "confirm_repository", 200) != target:
            raise ValueError(f"Type {target} to confirm where the pull request goes.")
        mission = _finished_mission(item, p.get("accept_unverified") is True)
        job = db.query(PlatformClientJob).filter_by(job_id=item.job_id).first()
        with _DELIVER_LOCK:
            db.expire_all()
            sent = db.query(PlatformClientDelivery).filter_by(work_id=item.work_id, kind="pull_request").first()
            if sent:
                return {"status": "already-delivered", "delivery": _delivery_view(sent)}
            from app.platform.credential_vault.service import resolve_credential

            result = delivery.open_pull_request(source=codebase.source, workspace=item.workspace, git_dir=item.git_dir,
                                                work_id=item.work_id, job_title=job.title, mission=mission,
                                                token=resolve_credential(delivery.TOKEN_KEY) or "")
            record = PlatformClientDelivery(delivery_id=f"DL-{uuid.uuid4().hex[:10]}", work_id=item.work_id,
                                            job_id=item.job_id, kind="pull_request", target=result["target"],
                                            branch=result["branch"], url=result["url"], files_changed=result["files_changed"],
                                            delivered_by=require_founder(p).get("email") or "founder")
            db.add(record)
            job.status, job.updated_at = "delivered", _now()
            db.commit()
            return {"status": "delivered", "delivery": _delivery_view(record)}
    return _guard(payload, action)


def patch_file(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The AI team's changes as a patch download ({"name", "content"}), or None if not allowed."""
    if not require_founder(payload or {}).get("authorized"):
        return None
    create_platform_tables()
    with PlatformSessionLocal() as db:
        item = db.query(PlatformClientWork).filter_by(work_id=str(payload.get("work_id") or "")).first()
        if not item:
            return None
        try:
            _finished_mission(item, payload.get("accept_unverified") is True)
            result = work.patch(item.workspace, item.git_dir)
        except ValueError:
            return None
        if not result["patch"].strip():
            return None
        job = db.query(PlatformClientJob).filter_by(job_id=item.job_id).first()
        db.add(PlatformClientDelivery(delivery_id=f"DL-{uuid.uuid4().hex[:10]}", work_id=item.work_id, job_id=item.job_id,
                                      kind="patch", files_changed=result["files_changed"],
                                      delivered_by=require_founder(payload).get("email") or "founder"))
        db.commit()
        slug = delivery.branch_name(job.title if job else "changes", item.work_id).removeprefix(delivery.BRANCH_PREFIX)
        return {"name": f"{slug}.patch", "content": result["patch"]}


def report_pdf(payload: Dict[str, Any]) -> Optional[bytes]:
    """PDF bytes of the latest Health Check, or None (unauthorised / no report)."""
    if not require_founder(payload or {}).get("authorized"):
        return None
    create_platform_tables()
    with PlatformSessionLocal() as db:
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=str(payload.get("codebase_id") or "")).first()
        path = Path(codebase.last_report_path) if codebase and codebase.last_report_path else None
    return path.read_bytes() if path and path.is_file() else None


# ---- background work ------------------------------------------------------------------------

def _update(codebase_id: str, **fields) -> None:
    with PlatformSessionLocal() as db:
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=codebase_id).first()
        for key, value in fields.items():
            setattr(codebase, key, value)
        codebase.updated_at = _now()
        db.commit()


def _fetch(codebase_id: str) -> None:
    with PlatformSessionLocal() as db:
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=codebase_id).first()
        client_id, source = codebase.client_id, codebase.source
    dest = workspaces_root() / client_id / codebase_id
    _update(codebase_id, status="fetching", error=None)
    try:
        from app.platform.credential_vault.service import resolve_credential

        clone(source, dest, token=resolve_credential("GITHUB_IMPORT_TOKEN"))
        _update(codebase_id, status="ready", local_path=str(dest))
    except Exception as exc:  # report any failure on screen instead of losing it in a thread
        _update(codebase_id, status="failed", error=str(exc)[:500])
        return
    _check(codebase_id)  # the code is here: run the Health Check straight away, in the same worker


def _check(codebase_id: str) -> None:
    from app.platform.codebase_health.report import render_pdf
    from app.platform.codebase_health.service import run_health_check

    with PlatformSessionLocal() as db:
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=codebase_id).first()
        client_id, local_path, label = codebase.client_id, codebase.local_path, codebase.label
    _update(codebase_id, status="checking", error=None)
    try:
        result = run_health_check(local_path, online_lookups=HEALTH_CHECK_ONLINE)
        result["project"] = label
        reports = workspaces_root() / client_id / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        pdf = render_pdf(result, str(reports / f"{codebase_id}-health-check.pdf"))
        summary = {"overall": result["overall"], "stack": result["stack"], "size": result["size"],
                   "areas": [{"title": a["title"], "score": a["score"], "grade": a["grade"]} for a in result["areas"]],
                   "top_risks": result["top_risks"], "next_steps": result["next_steps"], "checked_at": result["checked_at"]}
        _update(codebase_id, status="ready", last_check_json=json.dumps(summary), last_report_path=pdf, last_checked_at=_now())
    except Exception as exc:
        _update(codebase_id, status="failed", error=f"Health Check failed: {str(exc)[:400]}")
