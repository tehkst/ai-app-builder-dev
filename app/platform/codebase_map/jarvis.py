"""Jarvis -> Codebase Map: "create the system map of my app" gets buttons, not a written answer.

`is_map_request` spots the request (system/codebase map, map of my app/code, floorplan). `reply`
answers without the AI: it lists the codebases the founder has (those named in the message, or
all of them) with **Open the map** for a finished map and **Make a map** otherwise, and offers to
map this platform itself. The buttons run in the Jarvis panel (ui/mc2/jarvis_panel.py), which
asks for the same confirmation as the Clients screen before any code is sent to an AI provider.

`map_platform` is the endpoint behind "Map AI Software Factory itself": it files the platform's
own repository as a codebase of an internal client, once, so its maps are kept like any other.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

from app.platform.auth.service import require_founder

MAP_REQUEST = re.compile(
    r"\b(system|codebase|code|app|repo(sitory)?)\s+map\b|\bfloor\s?plan\b|"
    r"\bmap\s+(of\s+)?(my|the|our|this|that)\s+(\w+\s+)?(app|application|code|codebase|system|platform|repo|repository|project)\b|"
    r"\b(visuali[sz]e|diagram)\s+(my|the|our|this)\s+(\w+\s+)?(app|application|code|codebase|system|repo)\b", re.I)
PLATFORM_WORDS = re.compile(r"\b(my|this|our)\s+(app|platform|system)\b|\bmission control\b|\bai software factory\b|\bplatform\b", re.I)
INTERNAL_CLIENT = "AI Software Factory (internal)"
PLATFORM_ROOT = Path(__file__).resolve().parents[3]  # the repository this platform runs from
MAX_LISTED = 6


def is_map_request(text: str) -> bool:
    return bool(MAP_REQUEST.search(text or ""))


def _named(text: str, *names: str) -> bool:
    return any(n and re.search(r"(?<!\w)" + re.escape(n.lower()) + r"(?!\w)", text) for n in names)


def reply(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.platform.clients.maps import latest_maps
    from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
    from app.platform.persistence.models import PlatformClient, PlatformClientCodebase

    text = str(payload.get("message") or payload.get("prompt") or "").lower()
    create_platform_tables()
    rows: List[Dict[str, Any]] = []
    with PlatformSessionLocal() as db:
        clients = {c.client_id: c.name for c in db.query(PlatformClient).all()}
        for client_id in clients:
            maps = latest_maps(db, client_id)
            for cb in db.query(PlatformClientCodebase).filter_by(client_id=client_id).all():
                m = maps.get(cb.codebase_id)
                rows.append({"client_id": client_id, "client": clients[client_id], "codebase_id": cb.codebase_id,
                             "label": cb.label, "ready": cb.status == "ready" and bool(cb.local_path),
                             "platform": cb.local_path == str(PLATFORM_ROOT),
                             "map": {"map_id": m.map_id, "status": m.status} if m else None})
    rows.sort(key=lambda r: (not r["map"], not r["ready"], r["client"].lower()))  # mapped code first: it's what's asked for most
    named = [r for r in rows if _named(text, r["client"], r["label"])]
    wants_platform = bool(PLATFORM_WORDS.search(text)) and not named
    own = [r for r in rows if r["platform"]]
    # "my app": this platform once it's filed; until then every codebase, plus the offer to map the platform
    shown = (named or (own if wants_platform and own else rows))[:MAX_LISTED]
    buttons: List[Dict[str, Any]] = []
    lines: List[str] = []
    for r in shown:
        name = r["label"] if r["platform"] else f"{r['client']}: {r['label']}"
        m = r["map"]
        if m and m["status"] == "ready":
            buttons.append({"label": f"Open the map of {name}", "action_type": "function", "target": "openCodebaseMap",
                            "payload": {"map_id": m["map_id"]}})
        if m and m["status"] == "running":
            lines.append(f"- {name}: the map is being drawn now; it shows up in Clients when it's done.")
        elif r["ready"]:
            buttons.append({"label": f"{'Update the map' if m and m['status'] == 'ready' else 'Make a map'} of {name}",
                            "action_type": "function", "target": "startCodebaseMap",
                            "payload": {"client_id": r["client_id"], "codebase_id": r["codebase_id"], "name": name,
                                        "own": r["platform"]}})
        else:
            lines.append(f"- {name}: its code isn't fetched yet (see Clients).")
    if not any(r["platform"] for r in shown) and (wants_platform or not shown):
        buttons.append({"label": "Map AI Software Factory itself", "action_type": "function", "target": "startPlatformMap",
                        "payload": {}})
    intro = ("I'll draw a Codebase Map: an interactive map of the app's parts, the outside services it uses and how "
             "they connect, with a plain name for every file. It opens in its own tab.")
    if not buttons and not lines:
        intro += " There's no code to map yet: add a codebase to a client in Clients first."
    else:
        intro += " Pick one below. Before anything is sent to the AI provider you'll be asked to confirm."
    response = "\n".join([intro, *lines])
    return {"status": "ready", "board_room_response": response, "message": response,
            "action_metadata": {"intent_type": "codebase_map", "action_buttons": buttons}}


def map_platform(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The platform's own repository as a codebase of the internal client (made on first use)."""
    if not require_founder(payload or {}).get("authorized"):
        return {"status": "unauthorized"}
    from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
    from app.platform.persistence.models import PlatformClient, PlatformClientCodebase

    create_platform_tables()
    with PlatformSessionLocal() as db:
        cb = db.query(PlatformClientCodebase).filter_by(local_path=str(PLATFORM_ROOT)).first()
        if cb is None:
            client = db.query(PlatformClient).filter_by(name=INTERNAL_CLIENT).first()
            if client is None:
                client = PlatformClient(client_id=f"CL-{uuid.uuid4().hex[:10]}", name=INTERNAL_CLIENT, status="active",
                                        notes="This platform's own code, for Codebase Maps.")
                db.add(client)
                db.flush()
            cb = PlatformClientCodebase(codebase_id=f"CB-{uuid.uuid4().hex[:10]}", client_id=client.client_id,
                                        label="AI Software Factory", source_kind="local_folder", source=str(PLATFORM_ROOT),
                                        local_path=str(PLATFORM_ROOT), status="ready")
            db.add(cb)
            db.commit()
        return {"status": "ready", "client_id": cb.client_id, "codebase_id": cb.codebase_id, "name": cb.label}
