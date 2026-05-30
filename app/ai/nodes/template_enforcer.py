from app.ai.state import ProjectState


TRUSTED_TEMPLATES = {
    "backend/app/api/routes/__init__.py": """from app.api.routes import auth, customers, dashboard

__all__ = [
    "auth",
    "customers",
    "dashboard",
]
""",
    
    "backend/main.py": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, customers, dashboard
from app.core.config import settings


app = FastAPI(title=settings.APP_NAME)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(customers.router, prefix="/api/customers", tags=["Customers"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])


@app.get("/health")
async def health_check():
    return {"ok": True}
""",

    "backend/app/core/config.py": """import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Generated Enterprise App"
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
""",

    "backend/app/core/security.py": """from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        raise ValueError("Password cannot exceed 72 bytes")

    return bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": subject,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
""",

    "backend/app/api/dependencies.py": """from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import decode_access_token


security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        return user_id

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(allowed_roles: list[str]):
    async def role_checker():
        return True

    return role_checker
""",

    "backend/.env.example": """APP_NAME=Generated Enterprise App
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/generated_app
JWT_SECRET_KEY=replace-with-secure-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALLOWED_ORIGINS=["http://localhost:3000"]
""",

    "backend/requirements.txt": """fastapi
uvicorn[standard]
pydantic
pydantic-settings
sqlalchemy
asyncpg
python-jose[cryptography]
bcrypt
python-dotenv
""",
}


def template_enforcer_node(state: ProjectState) -> ProjectState:
    manifest = state.get("file_manifest", {})
    files = manifest.get("files", [])

    updated_files = []
    existing_paths = set()

    for file in files:
        file_path = file.get("file_path")
        existing_paths.add(file_path)

        if file_path in TRUSTED_TEMPLATES:
            file = {
                **file,
                "content": TRUSTED_TEMPLATES[file_path],
                "purpose": "Trusted enterprise template",
            }

        updated_files.append(file)

    for file_path, content in TRUSTED_TEMPLATES.items():
        if file_path not in existing_paths:
            updated_files.append(
                {
                    "file_path": file_path,
                    "file_type": "template",
                    "purpose": "Trusted enterprise template",
                    "content": content,
                }
            )

    return {
        **state,
        "file_manifest": {
            "files": updated_files,
        },
        "current_step": "templates_enforced",
    }
