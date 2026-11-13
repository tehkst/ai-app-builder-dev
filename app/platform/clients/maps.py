"""Codebase Maps of client code (Mission Control -> Clients -> a codebase -> Map).

Founder-only, like the rest of the Clients area. Making a map sends a redacted copy of the client's
code to the AI provider named in the confirmation, so it has the same consent gate as jobs and the
Audit, and is pinned to that provider. A new map of the same code reuses the last one's parts and
descriptions where the code is unchanged, so updates cost little; `redraw` starts over.

The map is a JSON file under the client's folder. The viewer (`/mission-control/clients/map`) loads
it through `map_data`; `map_export` gives a single HTML file to send to the client, without this
machine's folder paths.

The map is a living record: after each delivered job (`after_delivery`, called by `deliver` and the
patch download) it is updated from the delivered code, with the job shown as Recent work. Each map
records what made it (`trigger_json`), so the Maps screen lists its history.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.platform.auth.service import require_founder
from app.platform.clients import provider_terms, work
from app.platform.clients.fetch import workspaces_root
from app.platform.clients.service import _START_WORK_LOCK, _guard, _now, _iso, _running, _start, _text
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformClient, PlatformClientCodebase, PlatformClientMap

HISTORY = 8  # map versions listed per codebase on the Maps screen


def map_view(m: PlatformClientMap) -> Dict[str, Any]:
    view = {"map_id": m.map_id, "status": m.status, "error": m.error, "ai_provider": m.ai_provider,
            "consent_terms": m.consent_terms, "audience": m.audience, "started_at": _iso(m.created_at),
            "finished_at": _iso(m.finished_at)}
    summary = json.loads(m.summary_json) if m.summary_json else {}
    if summary:
        from app.platform.ai_costs import summarize

        view["cost"] = summarize(summary.get("ai_usage") or [])  # failed maps keep their AI cost too
        view.update({k: summary[k] for k in ("stats", "problems", "carried", "described", "health", "recent") if k in summary})
    trigger = json.loads(m.trigger_json) if m.trigger_json else {}
    view["trigger"] = {k: trigger.get(k) for k in ("kind", "job_title", "job_id", "delivery_kind")} if trigger else {"kind": "manual"}
    return view


def reconcile(db, m: PlatformClientMap) -> None:
    if m.status == "running" and not _running(m.map_id):
        m.status, m.error, m.finished_at = "failed", "Making the map was interrupted (the server restarted). Make it again.", _now()
        db.commit()


def latest_maps(db, client_id: str) -> Dict[str, PlatformClientMap]:
    """codebase -> its newest map (any status)."""
    out: Dict[str, PlatformClientMap] = {}
    for m in db.query(PlatformClientMap).filter_by(client_id=client_id).order_by(PlatformClientMap.id.desc()).all():
        reconcile(db, m)
        out.setdefault(m.codebase_id, m)
    return out


def list_maps(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Every codebase with its newest map, for the Maps screen (newest map first, unmapped code last)."""
    def action(db, _):
        rows = []
        clients = {c.client_id: c.name for c in db.query(PlatformClient).all()}
        for client_id, client_name in clients.items():
            maps = latest_maps(db, client_id)
            for cb in db.query(PlatformClientCodebase).filter_by(client_id=client_id).all():
                m = maps.get(cb.codebase_id)
                history = db.query(PlatformClientMap).filter_by(codebase_id=cb.codebase_id) \
                    .order_by(PlatformClientMap.id.desc()).limit(HISTORY).all()
                rows.append({"client_id": client_id, "client": client_name, "codebase_id": cb.codebase_id,
                             "label": cb.label, "source": cb.source, "codebase_status": cb.status,
                             "can_map": cb.status in ("ready", "checking") and bool(cb.local_path),
                             "map": map_view(m) if m else None,
                             "history": [{k: v for k, v in map_view(h).items()
                                          if k in ("map_id", "status", "finished_at", "trigger", "cost", "error")}
                                         for h in history]})
        rows.sort(key=lambda r: ((r["map"] or {}).get("started_at") or "", r["client"].lower()), reverse=True)
        return {"status": "ready", "codebases": rows, "ai_provider": work.provider_label(),
                "ai_terms": provider_terms.terms_for(work.current_ai())}
    return _guard(payload, action)


def run_map(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Start making (or updating) the map of a codebase. The founder confirms the client agreed to
    their code being sent to the AI provider named in the dialog."""
    def action(db, p):
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=_text(p, "codebase_id", 64, True)).first()
        if not codebase:
            raise ValueError("No such codebase.")
        if codebase.status not in ("ready", "checking") or not codebase.local_path or not Path(codebase.local_path).is_dir():
            raise ValueError("Wait until the code has been fetched.")
        ai = work.current_ai()
        provider = work.provider_label(ai)
        if ai is None:
            raise ValueError("Choose an AI provider in Settings first.")
        if p.get("client_consent") is not True or p.get("ai_provider") != provider:
            raise ValueError(f"Confirm the client agreed to their code being sent to {provider}.")
        terms = provider_terms.check_version(ai, p.get("terms_version"))
        audience = "developers" if p.get("audience") == "developers" else "everyone"
        redraw = p.get("redraw") is True
        with _START_WORK_LOCK:
            db.expire_all()
            busy = db.query(PlatformClientMap).filter_by(codebase_id=codebase.codebase_id, status="running").first()
            if busy and _running(busy.map_id):
                raise ValueError("A map of this code is already being made.")
            record = PlatformClientMap(map_id=f"MAP-{uuid.uuid4().hex[:10]}", client_id=codebase.client_id,
                                       codebase_id=codebase.codebase_id, status="running", ai_provider=provider,
                                       consent_by=require_founder(p).get("email") or "founder", consent_terms=terms,
                                       audience=audience)
            db.add(record)
            db.commit()
            _start(record.map_id, lambda: _make(record.map_id, ai, redraw))
        return {"status": "started", "map_id": record.map_id}
    return _guard(payload, action)


def _previous(db, codebase_id: str, audience: str) -> Optional[Dict[str, Any]]:
    """The last finished map of this code in the same style, to update rather than start over."""
    for m in db.query(PlatformClientMap).filter_by(codebase_id=codebase_id, status="ready", audience=audience) \
            .order_by(PlatformClientMap.id.desc()).all():
        data = _load(m)
        if data:
            return data
    return None


def _load(m: Optional[PlatformClientMap]) -> Optional[Dict[str, Any]]:
    path = Path(m.map_path) if m and m.map_path else None
    if not path or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _make(map_id: str, ai, redraw: bool, source_path: Optional[str] = None,
          recent_task: Optional[Dict[str, Any]] = None) -> None:
    """Draw the map from `source_path` (the delivered code after a job) or the codebase's own folder.
    Recent work carries over from the last map; a delivered job adds its task on top."""
    from app.platform.codebase_map import cartographer, recent

    with PlatformSessionLocal() as db:
        record = db.query(PlatformClientMap).filter_by(map_id=map_id).first()
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=record.codebase_id).first()
        local_path, label, client_id, audience = codebase.local_path, codebase.label, codebase.client_id, record.audience
        last = _previous(db, record.codebase_id, audience)
        previous = None if redraw else last  # a redraw starts over, but recent work survives it
    fields: Dict[str, Any]
    try:
        result = cartographer.make_map(source_path or local_path, label, ai, audience=audience, previous=previous,
                                       redraw=redraw)
        result["graph"]["recent"] = recent.merge(recent_task, ((last or {}).get("graph") or {}).get("recent") or [],
                                                 [f["path"] for f in result["graph"]["files"]])
        folder = workspaces_root() / client_id / "maps"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{map_id}.json"
        path.write_text(json.dumps({"graph": result["graph"], "architecture": result["architecture"]}), encoding="utf-8")
        graph = result["graph"]
        summary = {"stats": graph["stats"], "problems": result["problems"], "carried": result["carried"],
                   "described": result["described"], "ai_usage": result["ai_usage"],
                   "health": [{"title": h["title"], "severity": h["severity"], "count": h["count"]} for h in graph["health"]],
                   "recent": [{"title": t["title"], "files": len(t["items"])} for t in graph["recent"]]}
        fields = {"status": "ready", "map_path": str(path), "summary_json": json.dumps(summary), "error": None}
    except Exception as exc:  # shown on screen; nothing half-written is kept
        fields = {"status": "failed", "error": str(exc)[:500],
                  "summary_json": json.dumps({"ai_usage": getattr(exc, "usage", None) or []})}
    with PlatformSessionLocal() as db:
        record = db.query(PlatformClientMap).filter_by(map_id=map_id).first()
        for key, value in {**fields, "finished_at": _now()}.items():
            setattr(record, key, value)
        db.commit()


def after_delivery(work_id: str, delivery: Dict[str, Any]) -> Dict[str, Any]:
    """After a job is delivered, update the codebase's map from the delivered code, with the job as
    Recent work. Only for code the founder has already mapped, and only on the AI provider and terms
    the client agreed to for this job (its consent covers sending this code there). Returns what
    happened: {"status": "started", "map_id"}, {"status": "not-mapped"} or {"status": "skipped", "reason"}."""
    from app.platform.ai_costs import summarize
    from app.platform.codebase_map import recent
    from app.platform.persistence.models import PlatformClientJob, PlatformClientWork

    with PlatformSessionLocal() as db:
        item = db.query(PlatformClientWork).filter_by(work_id=work_id).first()
        if item is None:
            return {"status": "skipped", "reason": "No such work."}
        last = db.query(PlatformClientMap).filter_by(codebase_id=item.codebase_id, status="ready") \
            .order_by(PlatformClientMap.id.desc()).first()
        if last is None:
            return {"status": "not-mapped"}  # maps are made when the founder asks; nothing to keep current
        ai = work.current_ai()
        terms = provider_terms.terms_for(ai)
        if ai is None or work.provider_label(ai) != item.ai_provider:
            return {"status": "skipped", "reason": f"The AI provider changed since the client agreed to {item.ai_provider}; "
                                                   "update the map from Maps after confirming again."}
        if not terms or terms["version"] != item.consent_terms:
            return {"status": "skipped", "reason": "The provider's terms changed since the client agreed; update the map "
                                                   "from Maps after confirming again."}
        if not Path(item.workspace).is_dir():
            return {"status": "skipped", "reason": "The delivered code is no longer on this machine."}
        job = db.query(PlatformClientJob).filter_by(job_id=item.job_id).first()
        from app.platform.orca import api_service

        mission = api_service._orca_factory().store.load(item.mission_id)
        if job is None or mission is None:
            return {"status": "skipped", "reason": "The job's records are missing."}
        previous_files = [f["path"] for f in ((_load(last) or {}).get("graph") or {}).get("files") or []]
        task = recent.task_from_job(job=job, work_item=item, mission=mission, delivery=delivery, previous_files=previous_files,
                                    changed=work.changes(item.workspace, item.git_dir)["files"],
                                    cost=summarize(getattr(mission, "usage", None) or []))
        with _START_WORK_LOCK:
            db.expire_all()
            busy = db.query(PlatformClientMap).filter_by(codebase_id=item.codebase_id, status="running").first()
            if busy and _running(busy.map_id):
                return {"status": "skipped", "reason": "A map of this code is already being made; update it from Maps afterwards."}
            record = PlatformClientMap(map_id=f"MAP-{uuid.uuid4().hex[:10]}", client_id=item.client_id,
                                       codebase_id=item.codebase_id, status="running", ai_provider=item.ai_provider,
                                       consent_by=f"{item.consent_by} (agreed for job {job.job_id})",
                                       consent_terms=item.consent_terms, audience=last.audience,
                                       trigger_json=json.dumps({"kind": "delivery", "job_id": job.job_id, "job_title": job.title,
                                                                "work_id": work_id, "delivery_kind": delivery.get("kind")}))
            db.add(record)
            db.commit()
            _start(record.map_id, lambda: _make(record.map_id, ai, False, source_path=item.workspace, recent_task=task))
        return {"status": "started", "map_id": record.map_id}


def map_context(codebase_id: str) -> Dict[str, Dict[str, Any]]:
    """For the change-risk gate (orca/change_risk.py): each file's part, and the outside services it
    talks to, from the codebase's newest finished map. Empty when the code has no map."""
    with PlatformSessionLocal() as db:
        last = db.query(PlatformClientMap).filter_by(codebase_id=codebase_id, status="ready") \
            .order_by(PlatformClientMap.id.desc()).first()
        graph = ((_load(last) or {}).get("graph")) or {}
    nodes = {n["id"]: n for n in graph.get("nodes") or []}
    services: Dict[str, List[str]] = {}
    for user, used, _kind, _label in graph.get("links") or []:
        node = nodes.get(used)
        if node and node.get("kind") == "external" and node["label"] not in services.setdefault(user, []):
            services[user].append(node["label"])
    return {f["path"]: {"part": (nodes.get(f["node"]) or {}).get("label"), "services": services.get(f["path"], [])}
            for f in graph.get("files") or []}


def map_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The map for the viewer, with the client and codebase it belongs to."""
    def action(db, p):
        record = db.query(PlatformClientMap).filter_by(map_id=_text(p, "map_id", 64, True)).first()
        data = _load(record) if record and record.status == "ready" else None
        if not data:
            raise ValueError("That map isn't ready (or its file is missing); make it again from Clients.")
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=record.codebase_id).first()
        client = db.query(PlatformClient).filter_by(client_id=record.client_id).first()
        return {"status": "ready", "graph": data["graph"],
                "meta": {"map_id": record.map_id, "client": client.name if client else "", "client_id": record.client_id,
                         "codebase": codebase.label if codebase else "", "made_at": _iso(record.finished_at),
                         "ai_provider": record.ai_provider}}
    return _guard(payload, action)


def map_export(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One self-contained HTML file of the map to send to the client: no Ask, no folder paths, no
    Health (it lists where secrets sit) unless the founder includes it."""
    if not require_founder(payload or {}).get("authorized"):
        return None
    create_platform_tables()
    from app.platform.ui.mc2.map_viewer import render_export

    with PlatformSessionLocal() as db:
        record = db.query(PlatformClientMap).filter_by(map_id=str(payload.get("map_id") or "")).first()
        data = _load(record) if record and record.status == "ready" else None
        if not data:
            return None
        codebase = db.query(PlatformClientCodebase).filter_by(codebase_id=record.codebase_id).first()
        label = codebase.label if codebase else "codebase"
    graph = dict(data["graph"])
    from app.platform.codebase_map.recent import for_client

    graph["recent"] = for_client(graph.get("recent") or [])
    if payload.get("include_health") is not True:
        graph["health"] = []
    for f in graph.get("files") or []:
        f.pop("sha", None)
        f.pop("signature", None)
    name = "".join(c if c.isalnum() or c in "-_" else "-" for c in label).strip("-") or "codebase"
    return {"name": f"{name}-map.html",
            "content": render_export(graph, {"codebase": label, "made_at": _iso(record.finished_at)})}
