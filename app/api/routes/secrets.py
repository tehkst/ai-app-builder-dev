from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.secret_vault import vault_configured
from app.models.user import User
from app.services.secret_vault_service import (
    create_or_replace_secret,
    delete_secret,
    list_secrets,
    organization_id_for_user,
)


router = APIRouter()


class SecretUpsertRequest(BaseModel):
    key_name: str
    value: str


async def _require_organization_id(user: User, db: AsyncSession) -> str:
    organization_id = await organization_id_for_user(db, user.id)
    if not organization_id:
        raise HTTPException(status_code=403, detail="No organization found for this account.")
    return organization_id


@router.get("")
async def get_secrets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    organization_id = await _require_organization_id(current_user, db)
    return {
        "configured": vault_configured(),
        "secrets": await list_secrets(db, organization_id),
    }


@router.post("")
async def upsert_secret(
    request: SecretUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    organization_id = await _require_organization_id(current_user, db)
    try:
        await create_or_replace_secret(
            db, organization_id, current_user.id, request.key_name, request.value
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error))
    return {"status": "ok", "message": "Secret saved."}


@router.delete("/{key_name}")
async def remove_secret(
    key_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    organization_id = await _require_organization_id(current_user, db)
    deleted = await delete_secret(db, organization_id, key_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Secret not found.")
    return {"status": "ok", "message": "Secret deleted."}
