from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL", "sqlite:///./booking.db")
    return value.replace("postgresql+asyncpg://", "postgresql://").replace("sqlite+aiosqlite://", "sqlite://")


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


class Owner(Base):
    __tablename__ = "app_8a475555f614_owners"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    business_name = Column(String(160), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    services = relationship("Service", back_populates="owner", cascade="all, delete-orphan")


class Customer(Base):
    __tablename__ = "app_8a475555f614_customers"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(160), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings = relationship("Booking", back_populates="customer")


class Service(Base):
    __tablename__ = "app_8a475555f614_services"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("app_8a475555f614_owners.id"), nullable=False)
    name = Column(String(160), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    owner = relationship("Owner", back_populates="services")
    bookings = relationship("Booking", back_populates="service")


class Booking(Base):
    __tablename__ = "app_8a475555f614_bookings"
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("app_8a475555f614_services.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("app_8a475555f614_customers.id"), nullable=True)
    customer_name = Column(String(160), nullable=False)
    customer_email = Column(String(255), nullable=False)
    appointment_at = Column(DateTime, nullable=False)
    status = Column(String(40), default="confirmed", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    service = relationship("Service", back_populates="bookings")
    customer = relationship("Customer", back_populates="bookings")


class PasswordResetToken(Base):
    __tablename__ = "app_8a475555f614_password_reset_tokens"
    id = Column(Integer, primary_key=True)
    subject_type = Column(String(20), nullable=False)
    subject_id = Column(Integer, nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OwnerEmailSetting(Base):
    __tablename__ = "app_8a475555f614_owner_email_settings"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("app_8a475555f614_owners.id"), unique=True, nullable=False)
    provider = Column(String(20), default="platform", nullable=False)
    gmail_address = Column(String(255), nullable=True)
    gmail_app_password_ciphertext = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def initialize() -> None:
    Base.metadata.create_all(engine)
