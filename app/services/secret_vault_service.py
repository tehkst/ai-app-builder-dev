from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secret_vault import decrypt_secret, encrypt_secret
from app.models.customer_secret import CustomerSecret
from app.models.membership import Membership

KEY_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
MAX_SECRET_VALUE_LENGTH = 8192


async def organization_id_for_user(db: AsyncSession, user_id: str) -> Optional[str]:
    result = await db.execute(select(Membership).where(Membership.user_id == user_id))
    membership = result.scalars().first()
    return membership.organization_id if membership else None


async def list_secrets(db: AsyncSession, organization_id: str) -> List[dict]:
    result = await db.execute(
        select(CustomerSecret)
        .where(CustomerSecret.organization_id == organization_id)
        .order_by(CustomerSecret.key_name)
    )
    return [
        {
            "key_name": row.key_name,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        }
        for row in result.scalars().all()
    ]


def _validate_key_name(key_name: str) -> None:
    if not KEY_NAME_PATTERN.match(key_name or ""):
        raise ValueError(
            "Key name must start with a letter and contain only letters, numbers, "
            "and underscores (max 64 characters)."
        )


async def _find_secret(db: AsyncSession, organization_id: str, key_name: str) -> Optional[CustomerSecret]:
    result = await db.execute(
        select(CustomerSecret).where(
            CustomerSecret.organization_id == organization_id,
            CustomerSecret.key_name == key_name,
        )
    )
    return result.scalar_one_or_none()


async def create_or_replace_secret(
    db: AsyncSession,
    organization_id: str,
    user_id: str,
    key_name: str,
    value: str,
) -> None:
    _validate_key_name(key_name)
    if not value:
        raise ValueError("Secret value cannot be empty.")
    if len(value) > MAX_SECRET_VALUE_LENGTH:
        raise ValueError(f"Secret value cannot exceed {MAX_SECRET_VALUE_LENGTH} characters.")

    ciphertext = encrypt_secret(value)

    existing = await _find_secret(db, organization_id, key_name)
    if existing:
        existing.ciphertext = ciphertext
        existing.updated_at = datetime.utcnow()
    else:
        db.add(
            CustomerSecret(
                organization_id=organization_id,
                key_name=key_name,
                ciphertext=ciphertext,
                created_by_user_id=user_id,
            )
        )
    await db.commit()


async def delete_secret(db: AsyncSession, organization_id: str, key_name: str) -> bool:
    existing = await _find_secret(db, organization_id, key_name)
    if not existing:
        return False
    await db.delete(existing)
    await db.commit()
    return True


async def get_decrypted_secret(db: AsyncSession, organization_id: str, key_name: str) -> Optional[str]:
    """Internal use only (e.g. a build job running on the customer's behalf).

    Never expose this through an API route — only list_secrets()'s metadata is safe to return.
    """
    row = await _find_secret(db, organization_id, key_name)
    if not row:
        return None
    row.last_used_at = datetime.utcnow()
    await db.commit()
    return decrypt_secret(row.ciphertext)
