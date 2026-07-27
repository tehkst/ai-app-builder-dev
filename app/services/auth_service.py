import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_email
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership
from app.models.password_reset_token import PasswordResetToken

RESET_TOKEN_TTL_MINUTES = 30


async def get_user_by_email(
    db: AsyncSession,
    email: str,
):
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def create_user_with_organization(
    db: AsyncSession,
    email: str,
    full_name: str,
    password: str,
    organization_name: str,
):
    existing_user = await get_user_by_email(db, email)

    if existing_user:
        raise ValueError("User already exists")

    organization = Organization(
        name=organization_name,
        plan="free",
    )

    db.add(organization)
    await db.flush()

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
    )

    db.add(user)
    await db.flush()

    membership = Membership(
        user_id=user.id,
        organization_id=organization.id,
        role="owner",
    )

    db.add(membership)

    await db.commit()
    await db.refresh(user)

    return user, organization, membership


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
):
    user = await get_user_by_email(db, email)

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def request_password_reset(
    db: AsyncSession,
    email: str,
    base_url: str,
) -> None:
    user = await get_user_by_email(db, email)
    if not user:
        return

    token = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    )
    db.add(reset_token)
    await db.commit()

    link = f"{base_url}/reset-password?token={token}&type=customer"
    send_email(
        user.email,
        "Reset your AI Software Factory password",
        f"Someone requested a password reset for your account.\n\n"
        f"Reset your password (expires in {RESET_TOKEN_TTL_MINUTES} minutes):\n{link}\n\n"
        f"If you did not request this, you can ignore this email.",
    )


async def reset_password(
    db: AsyncSession,
    token: str,
    new_password: str,
) -> bool:
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(token))
    )
    reset_token = result.scalar_one_or_none()
    if not reset_token or reset_token.used_at is not None or reset_token.expires_at < datetime.utcnow():
        return False

    user = await db.get(User, reset_token.user_id)
    if not user:
        return False

    user.password_hash = hash_password(new_password)
    reset_token.used_at = datetime.utcnow()
    await db.commit()
    return True
