from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL", "sqlite:///./booking.db")
    return value.replace("postgresql+asyncpg://", "postgresql://").replace("sqlite+aiosqlite://", "sqlite://")


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


class Owner(Base):
    __tablename__ = "__APPLICATION_DB_PREFIX___owners"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    business_name = Column(String(160), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    services = relationship("Service", back_populates="owner", cascade="all, delete-orphan")


class Customer(Base):
    __tablename__ = "__APPLICATION_DB_PREFIX___customers"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(160), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings = relationship("Booking", back_populates="customer")


class Service(Base):
    __tablename__ = "__APPLICATION_DB_PREFIX___services"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("__APPLICATION_DB_PREFIX___owners.id"), nullable=False)
    name = Column(String(160), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    owner = relationship("Owner", back_populates="services")
    bookings = relationship("Booking", back_populates="service")


class Booking(Base):
    __tablename__ = "__APPLICATION_DB_PREFIX___bookings"
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("__APPLICATION_DB_PREFIX___services.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("__APPLICATION_DB_PREFIX___customers.id"), nullable=True)
    customer_name = Column(String(160), nullable=False)
    customer_email = Column(String(255), nullable=False)
    appointment_at = Column(DateTime, nullable=False)
    status = Column(String(40), default="confirmed", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    service = relationship("Service", back_populates="bookings")
    customer = relationship("Customer", back_populates="bookings")


class PasswordResetToken(Base):
    __tablename__ = "__APPLICATION_DB_PREFIX___password_reset_tokens"
    id = Column(Integer, primary_key=True)
    subject_type = Column(String(20), nullable=False)
    subject_id = Column(Integer, nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def initialize() -> None:
    Base.metadata.create_all(engine)
