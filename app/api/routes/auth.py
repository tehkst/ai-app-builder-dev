import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.services.auth_service import (
    create_user_with_organization,
    authenticate_user,
    request_password_reset,
    reset_password,
)


router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    organization_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user, organization, membership = await create_user_with_organization(
            db=db,
            email=request.email,
            full_name=request.full_name,
            password=request.password,
            organization_name=request.organization_name,
        )

        access_token = create_access_token(subject=user.id)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
            },
            "organization": {
                "id": organization.id,
                "name": organization.name,
            },
            "role": membership.role,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.post("/login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(
        db=db,
        email=request.email,
        password=request.password,
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = create_access_token(subject=user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
        },
    }

from app.api.dependencies import get_current_user
from app.models.user import User


@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
    }


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    base_url = os.getenv("PUBLIC_BASE_URL", "")
    await request_password_reset(db, request.email, base_url)
    return {
        "status": "ok",
        "message": "If an account exists for that email, a reset link has been sent.",
    }


@router.post("/reset-password")
async def reset_password_route(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    ok = await reset_password(db, request.token, request.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    return {"status": "ok", "message": "Password updated. You can now sign in."}
