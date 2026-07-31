from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User


security = HTTPBearer()


async def _user_from_token(token: str, db: AsyncSession) -> User:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    return await _user_from_token(credentials.credentials, db)


async def get_current_user_from_query_or_header(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Same identity check as get_current_user, but also accepts the bearer token as
    a ?token= query parameter.

    Scoped to endpoints an <iframe src="..."> needs to load directly (e.g. the
    generated-app preview) - a plain iframe navigation can't attach a custom
    Authorization header, so the SPA passes its existing token this way instead.
    Still a real signed credential, verified identically to the header path.
    """

    token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing credentials")
    return await _user_from_token(token, db)
