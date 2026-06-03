from app.ai.state import ProjectState


TRUSTED_TEMPLATES = {
    "backend/app/api/__init__.py": """""",

    "backend/app/api/routes/__init__.py": """from app.api.routes import auth, customers, dashboard

__all__ = [
    "auth",
    "customers",
    "dashboard",
]
""",

    "backend/main.py": """from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.routes import auth, customers, dashboard
from app.core.config import settings
from app.core.database import Base, engine
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.models.customer import Customer
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


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

    "backend/app/core/config.py": """from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Generated Enterprise App"
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = str(ENV_FILE)


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
""",

    "backend/app/core/database.py": """from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)


AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

__all__ = [
    "Base",
    "engine",
    "AsyncSessionLocal",
    "get_db",
]
""",

    "backend/app/core/rate_limit.py": """from slowapi import Limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.util import get_remote_address


AUTH_RATE_LIMIT = "10/minute"


limiter = Limiter(
    key_func=get_remote_address,
)


async def rate_limit_exceeded_handler(request, exc):
    return _rate_limit_exceeded_handler(request, exc)
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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.membership import Membership


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


async def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
):
    return {
        "id": current_user_id,
    }


def require_role(allowed_roles: list[str]):
    async def role_checker(
        current_user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
    ):
        try:
            user_id = int(current_user_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid token subject")

        result = await db.execute(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.role.in_(allowed_roles),
            )
        )
        membership = result.scalar_one_or_none()

        if membership is None:
            raise HTTPException(status_code=403, detail="Insufficient role")

        return True

    return role_checker
""",

    "backend/app/schemas/auth.py": """from pydantic import BaseModel, EmailStr


class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    access_token: str
    token_type: str
""",

    "backend/app/schemas/customer.py": """from typing import Optional

from pydantic import BaseModel, EmailStr


class CustomerCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None

    class Config:
        from_attributes = True
""",

    "backend/app/models/user.py": """from sqlalchemy import Boolean, Column, Integer, String

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
""",

    "backend/app/models/customer.py": """from sqlalchemy import Column, Integer, String

from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
""",

    "backend/app/models/organization.py": """from sqlalchemy import Column, Integer, String

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
""",

    "backend/app/models/membership.py": """from sqlalchemy import Column, Integer, String

from app.core.database import Base


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    organization_id = Column(Integer, index=True, nullable=False)
    role = Column(String, default="member", nullable=False)
""",

    "backend/app/api/routes/auth.py": """from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.core.database import get_db
from app.core.rate_limit import AUTH_RATE_LIMIT, limiter
from app.core.security import create_access_token
from app.schemas.auth import UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import authenticate_user, create_user


router = APIRouter()


@router.post("/register", response_model=UserResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def register(
    request: Request,
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await create_user(db=db, payload=payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    access_token = create_access_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/login", response_model=UserResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request,
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(
        db=db,
        username=payload.username,
        password=payload.password,
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(subject=str(user.id))

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me")
async def me(
    current_user_id: str = Depends(get_current_user_id),
):
    return {
        "user_id": current_user_id,
    }
""",

    "backend/app/api/routes/customers.py": """from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.core.database import get_db
from app.schemas.customer import CustomerCreate, CustomerResponse
from app.services.customer_service import create_customer, get_customers


router = APIRouter()


@router.get("/", response_model=list[CustomerResponse])
async def list_customers(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await get_customers(db=db)


@router.post("/", response_model=CustomerResponse)
async def add_customer(
    payload: CustomerCreate,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await create_customer(db=db, payload=payload)
""",

    "backend/app/api/routes/dashboard.py": """from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.core.database import get_db
from app.models.customer import Customer


router = APIRouter()


@router.get("/summary")
async def dashboard_summary(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count(Customer.id))
    )

    customer_count = result.scalar_one()

    return {
        "customer_count": customer_count,
        "current_user_id": current_user_id,
    }
""",

    "backend/app/services/auth_service.py": """from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserRegisterRequest


async def get_user_by_email(
    db: AsyncSession,
    email: str,
):
    result = await db.execute(
        select(User).where(User.email == email)
    )

    return result.scalar_one_or_none()


async def get_user_by_username(
    db: AsyncSession,
    username: str,
):
    result = await db.execute(
        select(User).where(User.username == username)
    )

    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    payload: UserRegisterRequest,
):
    existing_user = await get_user_by_email(
        db=db,
        email=payload.email,
    )

    if existing_user:
        raise ValueError("User already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
):
    user = await get_user_by_username(
        db=db,
        username=username,
    )

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
""",

    "backend/app/services/customer_service.py": """from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate


async def get_customers(
    db: AsyncSession,
):
    result = await db.execute(
        select(Customer)
    )

    return result.scalars().all()


async def create_customer(
    db: AsyncSession,
    payload: CustomerCreate,
):
    customer = Customer(**payload.model_dump())

    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    return customer
""",

    "backend/.env.example": """APP_NAME=Generated Enterprise App
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/generated_app
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
greenlet
python-jose[cryptography]
bcrypt
python-dotenv
email-validator
slowapi
slowapi
""",

    "backend/Dockerfile": """FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",

    "backend/docker-compose.yml": """services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: generated_app
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5433:5432"
    volumes:
      - generated_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d generated_app"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build: .
    env_file:
      - .env
    ports:
      - "8001:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  generated_postgres_data:
""",

    "backend/.dockerignore": """.venv
__pycache__
*.pyc
.env
.git
.gitignore
.pytest_cache
.mypy_cache
.DS_Store
""",

    "frontend/.env.example": """NEXT_PUBLIC_API_URL=http://localhost:8001
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
