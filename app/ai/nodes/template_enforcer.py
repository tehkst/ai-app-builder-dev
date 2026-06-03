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
from app.models.audit_log import AuditLog
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
from app.services.audit_service import create_audit_log


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
            await create_audit_log(
                db=db,
                event_type="rbac_denied",
                status="blocked",
                actor_user_id=user_id,
                detail="Insufficient role",
            )
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

    "backend/app/models/audit_log.py": """from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)
    actor_user_id = Column(Integer, index=True, nullable=True)
    route = Column(String, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
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
from app.services.audit_service import create_audit_log
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
        await create_audit_log(
            db=db,
            event_type="user_register_failed",
            status="failed",
            route="/api/auth/register",
            detail=str(error),
        )
        raise HTTPException(status_code=400, detail=str(error))

    await create_audit_log(
        db=db,
        event_type="user_registered",
        status="success",
        actor_user_id=user.id,
        route="/api/auth/register",
    )

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
        await create_audit_log(
            db=db,
            event_type="login_failed",
            status="failed",
            route="/api/auth/login",
            detail="Invalid credentials",
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await create_audit_log(
        db=db,
        event_type="login_success",
        status="success",
        actor_user_id=user.id,
        route="/api/auth/login",
    )

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
from app.services.audit_service import create_audit_log
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
    customer = await create_customer(db=db, payload=payload)

    await create_audit_log(
        db=db,
        event_type="customer_created",
        status="success",
        actor_user_id=int(current_user_id),
        route="/api/customers/",
        detail=f"customer_id={customer.id}",
    )

    return customer
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

    "backend/app/services/audit_service.py": """from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def create_audit_log(
    db: AsyncSession,
    event_type: str,
    status: str,
    actor_user_id: Optional[int] = None,
    route: Optional[str] = None,
    detail: Optional[str] = None,
) -> AuditLog:
    audit_log = AuditLog(
        event_type=event_type,
        status=status,
        actor_user_id=actor_user_id,
        route=route,
        detail=detail,
    )

    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)

    return audit_log
""",

    "backend/app/services/auth_service.py": """from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.membership import Membership
from app.models.organization import Organization
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
    await db.flush()

    organization = Organization(
        name=f"{payload.username}'s Organization",
    )
    db.add(organization)
    await db.flush()

    membership = Membership(
        user_id=user.id,
        organization_id=organization.id,
        role="owner",
    )
    db.add(membership)

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

    "frontend/components/Navbar.tsx": """"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { clearAccessToken, isAuthenticated } from "../lib/auth";

export default function Navbar() {
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(isAuthenticated());
  }, []);

  function handleLogout() {
    clearAccessToken();
    setLoggedIn(false);
    window.location.href = "/login";
  }

  return (
    <nav className="flex items-center justify-between border-b px-6 py-4">
      <Link href="/" className="font-semibold">
        Generated Enterprise App
      </Link>

      <div className="flex gap-4">
        <Link href="/dashboard">Dashboard</Link>
        <Link href="/customers">Customers</Link>

        {loggedIn ? (
          <button onClick={handleLogout} type="button">
            Logout
          </button>
        ) : (
          <Link href="/login">Login</Link>
        )}
      </div>
    </nav>
  );
}
""",

    "frontend/app/login/page.tsx": """"use client";

import { FormEvent, useState } from "react";
import { login } from "../../lib/api";
import { saveAccessToken } from "../../lib/auth";
import { SAFE_ERROR_MESSAGES } from "../../lib/errors";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");

    try {
      const response = await login(username, password);
      saveAccessToken(response.access_token);
      window.location.href = "/dashboard";
    } catch {
      setErrorMessage(SAFE_ERROR_MESSAGES.loginFailed);
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Login</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          className="w-full rounded border px-3 py-2"
          placeholder="Username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />

        <input
          className="w-full rounded border px-3 py-2"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {errorMessage ? (
          <p className="text-sm text-red-600">{errorMessage}</p>
        ) : null}

        <button className="w-full rounded bg-black px-4 py-2 text-white" type="submit">
          Login
        </button>
      </form>
    </main>
  );
}
""",

    "frontend/app/register/page.tsx": """"use client";

import { FormEvent, useState } from "react";
import { register } from "../../lib/api";
import { saveAccessToken } from "../../lib/auth";
import { SAFE_ERROR_MESSAGES } from "../../lib/errors";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");

    try {
      const response = await register(username, email, password);
      saveAccessToken(response.access_token);
      window.location.href = "/dashboard";
    } catch {
      setErrorMessage(SAFE_ERROR_MESSAGES.registerFailed);
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Create account</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          className="w-full rounded border px-3 py-2"
          placeholder="Username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />

        <input
          className="w-full rounded border px-3 py-2"
          placeholder="Email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <input
          className="w-full rounded border px-3 py-2"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {errorMessage ? (
          <p className="text-sm text-red-600">{errorMessage}</p>
        ) : null}

        <button className="w-full rounded bg-black px-4 py-2 text-white" type="submit">
          Register
        </button>
      </form>
    </main>
  );
}
""",

    "frontend/app/customers/page.tsx": """"use client";

import { FormEvent, useEffect, useState } from "react";
import { createCustomer, getCustomers } from "../../lib/api";
import { SAFE_ERROR_MESSAGES } from "../../lib/errors";

type Customer = {
  id: number;
  name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
};

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  async function loadCustomers() {
    setErrorMessage("");

    try {
      const data = await getCustomers();
      setCustomers(data as Customer[]);
    } catch {
      setErrorMessage(SAFE_ERROR_MESSAGES.customersLoadFailed);
    }
  }

  useEffect(() => {
    loadCustomers();
  }, []);

  async function handleCreateCustomer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");

    try {
      await createCustomer({
        name,
        email: email || undefined,
        company: company || undefined,
      });

      setName("");
      setEmail("");
      setCompany("");
      await loadCustomers();
    } catch {
      setErrorMessage(SAFE_ERROR_MESSAGES.customerCreateFailed);
    }
  }

  return (
    <main className="px-6 py-8">
      <h1 className="mb-6 text-2xl font-semibold">Customers</h1>

      <form onSubmit={handleCreateCustomer} className="mb-8 grid gap-3 md:grid-cols-4">
        <input
          className="rounded border px-3 py-2"
          placeholder="Name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />

        <input
          className="rounded border px-3 py-2"
          placeholder="Email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <input
          className="rounded border px-3 py-2"
          placeholder="Company"
          value={company}
          onChange={(event) => setCompany(event.target.value)}
        />

        <button className="rounded bg-black px-4 py-2 text-white" type="submit">
          Add Customer
        </button>
      </form>

      {errorMessage ? (
        <p className="mb-4 text-sm text-red-600">{errorMessage}</p>
      ) : null}

      <div className="overflow-x-auto rounded border">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b">
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Company</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((customer) => (
              <tr className="border-b" key={customer.id}>
                <td className="px-3 py-2">{customer.name}</td>
                <td className="px-3 py-2">{customer.email || "-"}</td>
                <td className="px-3 py-2">{customer.company || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
""",

    "frontend/lib/api.ts": """import { getAccessToken } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

type RequestOptions = RequestInit & {
  authenticated?: boolean;
};

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  if (options.authenticated !== false) {
    const token = getAccessToken();

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error("Request failed");
  }

  return response.json() as Promise<T>;
}

export async function login(username: string, password: string) {
  return request<{ access_token: string; token_type: string }>(
    "/api/auth/login",
    {
      method: "POST",
      authenticated: false,
      body: JSON.stringify({ username, password }),
    },
  );
}

export async function register(
  username: string,
  email: string,
  password: string,
) {
  return request<{ access_token: string; token_type: string }>(
    "/api/auth/register",
    {
      method: "POST",
      authenticated: false,
      body: JSON.stringify({ username, email, password }),
    },
  );
}

export async function getCurrentUser() {
  return request<{ user_id: string }>("/api/auth/me");
}

export async function getCustomers() {
  return request("/api/customers/");
}

export async function createCustomer(payload: {
  name: string;
  email?: string;
  phone?: string;
  company?: string;
}) {
  return request("/api/customers/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
""",

    "frontend/lib/auth.ts": """export const ACCESS_TOKEN_KEY = "access_token";

export function saveAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function clearAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getAccessToken());
}
""",

    "frontend/lib/errors.ts": """export function getSafeErrorMessage(
  fallbackMessage: string,
): string {
  return fallbackMessage;
}

export const SAFE_ERROR_MESSAGES = {
  loginFailed: "Login failed. Please check your credentials.",
  registerFailed: "Registration failed. Please try again.",
  customersLoadFailed: "Unable to load customers. Please try again later.",
  customerCreateFailed: "Unable to create customer. Please try again later.",
  unauthorized: "Your session has expired. Please log in again.",
};
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
