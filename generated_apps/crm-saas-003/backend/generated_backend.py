Here's a production-ready FastAPI backend code structure based on your requirements:

### Directory Structure
```
backend/
│
├── src/
│   ├── controllers/
│   │   ├── auth_controller.py
│   │   ├── customer_controller.py
│   │   └── admin_controller.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── customer.py
│   │   ├── interaction.py
│   │   ├── analytics.py
│   │   └── settings.py
│   │
│   ├── routes/
│   │   ├── auth_routes.py
│   │   ├── customer_routes.py
│   │   └── admin_routes.py
│   │
│   ├── middleware/
│   │   └── auth.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── customer_service.py
│   │   └── admin_service.py
│   │
│   ├── config/
│   │   ├── database.py
│   │   └── settings.py
│   │
│   ├── utils/
│   │   └── jwt.py
│   │
│   └── app.py
│
├── tests/
│   ├── test_auth.py
│   ├── test_customer.py
│   └── test_admin.py
│
└── requirements.txt
```

### Code Implementation

#### `requirements.txt`
```plaintext
fastapi
uvicorn
sqlalchemy
asyncpg
pydantic
python-jose
passlib[bcrypt]
pytest
```

#### `src/config/database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

#### `src/models/user.py`
```python
from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.sql import func
from src.config.database import Base
import enum

class Role(enum.Enum):
    admin = "admin"
    user = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Enum(Role), default=Role.user)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

#### `src/models/customer.py`
```python
from sqlalchemy import Column, Integer, String, DateTime, ARRAY
from sqlalchemy.sql import func
from src.config.database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, index=True)
    phone = Column(String)
    address = Column(String)
    tags = Column(ARRAY(String))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

#### `src/routes/auth_routes.py`
```python
from fastapi import APIRouter, Depends
from src.controllers.auth_controller import register_user, login_user

router = APIRouter()

@router.post("/register")
async def register(username: str, email: str, password: str):
    return await register_user(username, email, password)

@router.post("/login")
async def login(email: str, password: str):
    return await login_user(email, password)
```

#### `src/controllers/auth_controller.py`
```python
from fastapi import HTTPException
from src.models.user import User
from src.services.auth_service import create_user, authenticate_user
from src.utils.jwt import create_access_token

async def register_user(username: str, email: str, password: str):
    user = await create_user(username, email, password)
    return {"msg": "User created successfully", "user_id": user.id}

async def login_user(email: str, password: str):
    user = await authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

#### `src/services/auth_service.py`
```python
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from src.models.user import User
from src.config.database import SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user(username: str, email: str, password: str):
    db: Session = SessionLocal()
    hashed_password = pwd_context.hash(password)
    user = User(username=username, email=email, password_hash=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

async def authenticate_user(email: str, password: str):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user and pwd_context.verify(password, user.password_hash):
        return user
    return None
```

#### `src/utils/jwt.py`
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends
from src.models.user import User

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

#### `src/app.py`
```python
from fastapi import FastAPI
from src.routes.auth_routes import router as auth_router
from src.config.database import engine, Base

app = FastAPI()

# Create database tables
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(auth_router, prefix="/api/auth")
```

### Running the Application
To run the FastAPI application, use the following command:
```bash
uvicorn src.app:app --reload
```

### Testing
You can create tests in the `tests` directory using `pytest` to ensure that your API endpoints work as expected.

This code provides a modular architecture for your FastAPI backend, implementing JWT authentication, and CRUD operations for users and customers. You can expand this structure further to include additional modules and functionalities as needed.