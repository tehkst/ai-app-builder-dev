"""Keep clients' secrets away from the AI provider.

- `is_secret_file(path)`: files that exist to hold secrets (.env files, private keys, keystores,
  credential JSON, .npmrc/.pypirc/auth.json/.htpasswd). Example/template versions are not secret.
- `redact(text)`: removes secret values from text, using the Health Check's own patterns, and whole
  PEM private-key blocks (header, body and footer), not just the header line.
- `redacted_copy(source, dest)`: the copy the Code Auditor reads. Only the files the Health Check would
  read (git-tracked, or walked without vendored/generated folders), secret files replaced by a one-line
  note that they exist, every text file redacted. Nothing secret enters the model conversation, so
  nothing can leak through a tool result before the final report is scrubbed.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from app.platform.codebase_health.inventory import build_inventory
from app.platform.codebase_health.scanners import KEY_FILE_NAMES, KEY_FILE_SUFFIXES, SECRET_PATTERNS

REMOVED = "[secret removed]"
SECRET_SUFFIXES = KEY_FILE_SUFFIXES | {".p12", ".pfx", ".jks", ".keystore", ".ppk", ".asc", ".gpg"}
SECRET_NAMES = KEY_FILE_NAMES | {".npmrc", ".pypirc", "auth.json", ".htpasswd", ".netrc", ".git-credentials",
                                 ".dockercfg", "credentials", "secrets.yml", "secrets.yaml", "secrets.json"}
TEMPLATE_HINT = re.compile(r"(?i)\.(example|sample|dist|template|tmpl)$|example|sample")
SECRET_NAME_PATTERN = re.compile(r"(?i)^\.env(\..+)?$|^.*\.env$|credentials.*\.json$|service[-_]?account.*\.json$|"
                                 r"^id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$")
PEM_BLOCK = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----.*?(?:-----END [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----|\Z)", re.S)
MAX_TEXT_BYTES = 2_000_000


def is_secret_file(path: str) -> bool:
    name = Path(path).name
    if TEMPLATE_HINT.search(name):
        return False
    return (name.lower() in SECRET_NAMES or Path(name).suffix.lower() in SECRET_SUFFIXES
            or bool(SECRET_NAME_PATTERN.match(name)))


def redact(text: str) -> str:
    text = PEM_BLOCK.sub(REMOVED, text)
    for _, pattern in SECRET_PATTERNS:
        text = pattern.sub(REMOVED, text)
    return text


def redact_all(value: Any) -> Any:
    """Redact every string inside a JSON-like value (for the stored audit and the report)."""
    if isinstance(value, dict):
        return {key: redact_all(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_all(item) for item in value]
    return redact(value) if isinstance(value, str) else value


def redacted_copy(source: str, dest: str) -> int:
    """Write the auditor's copy of `source` into `dest`; returns how many secret files were withheld."""
    src, out = Path(source).resolve(), Path(dest)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    withheld = 0
    for rel in build_inventory(src).all_paths:
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if is_secret_file(rel):
            target.write_text("(This file exists in the client's code but was withheld: it holds secrets.)\n")
            withheld += 1
            continue
        path = src / rel
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_TEXT_BYTES:
                continue
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue  # binary (images, archives): nothing the auditor needs to read
        target.write_text(redact(raw.decode("utf-8", errors="replace")), encoding="utf-8")
    return withheld
