from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class ProfileInput(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)


class ServiceInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    duration_minutes: int = Field(ge=15, le=480)
    price: float = Field(ge=0, le=100000)


class BookingInput(BaseModel):
    service_id: int
    customer_name: str = Field(min_length=2, max_length=160)
    customer_email: EmailStr
    appointment_at: datetime


class BookingStatusInput(BaseModel):
    status: str = Field(pattern="^(confirmed|completed|cancelled)$")
