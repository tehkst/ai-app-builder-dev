Here's a production-ready FastAPI backend code based on your requirements and architecture:

### Directory Structure
```
backend/
│
├── src/
│   ├── controllers/
│   │   ├── customer_controller.py
│   │   ├── analytics_controller.py
│   │   ├── admin_controller.py
│   │   └── auth_controller.py
│   │
│   ├── models/
│   │   ├── customer.py
│   │   ├── user.py
│   │   ├── subscription.py
│   │   └── analytics.py
│   │
│   ├── routes/
│   │   ├── customer_routes.py
│   │   ├── analytics_routes.py
│   │   ├── admin_routes.py
│   │   └── auth_routes.py
│   │
│   ├── middleware/
│   │   ├── auth_middleware.py
│   │   └── error_middleware.py
│   │
│   ├── config/
│   │   ├── db.py
│   │   └── server.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── customer_service.py
│   │   └── analytics_service.py
│   │
│   └── app.py
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
```

#### `src/config/db.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

#### `src/models/customer.py`
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .db import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    address = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

#### `src/models/user.py`
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    email = Column(String, unique=True, index=True)
    role = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

#### `src/routes/customer_routes.py`
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..models.customer import Customer
from ..config.db import SessionLocal
from ..services.customer_service import create_customer, get_customers, get_customer, update_customer, delete_customer

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/customers")
async def read_customers(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return await get_customers(db=db, skip=skip, limit=limit)

@router.post("/customers")
async def add_customer(customer: Customer, db: Session = Depends(get_db)):
    return await create_customer(db=db, customer=customer)

@router.get("/customers/{customer_id}")
async def read_customer(customer_id: int, db: Session = Depends(get_db)):
    return await get_customer(db=db, customer_id=customer_id)

@router.put("/customers/{customer_id}")
async def modify_customer(customer_id: int, customer: Customer, db: Session = Depends(get_db)):
    return await update_customer(db=db, customer_id=customer_id, customer=customer)

@router.delete("/customers/{customer_id}")
async def remove_customer(customer_id: int, db: Session = Depends(get_db)):
    return await delete_customer(db=db, customer_id=customer_id)
```

#### `src/services/customer_service.py`
```python
from sqlalchemy.orm import Session
from ..models.customer import Customer

async def get_customers(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Customer).offset(skip).limit(limit).all()

async def create_customer(db: Session, customer: Customer):
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

async def get_customer(db: Session, customer_id: int):
    return db.query(Customer).filter(Customer.id == customer_id).first()

async def update_customer(db: Session, customer_id: int, customer: Customer):
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if db_customer:
        for key, value in customer.dict().items():
            setattr(db_customer, key, value)
        db.commit()
        db.refresh(db_customer)
        return db_customer
    return None

async def delete_customer(db: Session, customer_id: int):
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if db_customer:
        db.delete(db_customer)
        db.commit()
        return db_customer
    return None
```

#### `src/app.py`
```python
from fastapi import FastAPI
from .config.db import engine, Base
from .routes import customer_routes

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(customer_routes.router, prefix="/api")
```

### Running the Application
To run the FastAPI application, use the following command:
```bash
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
```

### Note
- Ensure to replace the `DATABASE_URL` in `db.py` with your actual PostgreSQL connection string.
- Implement similar models, routes, and services for `User`, `Subscription`, and `Analytics` as per your architecture.
- Add JWT authentication and error handling middleware as needed.
- This code is structured for clarity and modularity, following best practices for FastAPI applications.