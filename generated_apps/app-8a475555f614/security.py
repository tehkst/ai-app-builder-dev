from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Cookie, HTTPException
from jose import JWTError, jwt


SECRET = os.environ.get("APP_SESSION_SECRET", "")
ALGORITHM = "HS256"


def ensure_secret() -> None:
    if os.environ.get("ENVIRONMENT") == "production" and len(SECRET) < 32:
        raise RuntimeError("APP_SESSION_SECRET must be configured in production")


def hash_password(value: str) -> str:
    return bcrypt.hashpw(value.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(value: str, hashed: str) -> bool:
    return bcrypt.checkpw(value.encode("utf-8"), hashed.encode("utf-8"))


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def issue_owner_token(owner_id: int) -> str:
    payload = {"sub": str(owner_id), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def current_owner_id(owner_session: str = Cookie(default="")) -> int:
    try:
        value = jwt.decode(owner_session, SECRET, algorithms=[ALGORITHM]).get("sub")
        return int(value)
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Owner login required")


def issue_customer_token(customer_id: int) -> str:
    payload = {"sub": str(customer_id), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def current_customer_id(customer_session: str = Cookie(default="")) -> int:
    try:
        value = jwt.decode(customer_session, SECRET, algorithms=[ALGORITHM]).get("sub")
        return int(value)
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Customer login required")


def optional_customer_id(customer_session: str = Cookie(default="")) -> Optional[int]:
    try:
        value = jwt.decode(customer_session, SECRET, algorithms=[ALGORITHM]).get("sub")
        return int(value)
    except (JWTError, TypeError, ValueError):
        return None
