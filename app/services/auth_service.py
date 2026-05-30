from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership


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
