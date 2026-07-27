from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from crypto_vault import decrypt_secret, encrypt_secret, vault_configured
from mailer import send_email
from models import Booking, Customer, Owner, OwnerEmailSetting, PasswordResetToken, Service, SessionLocal
from schemas import (
    BookingInput,
    BookingStatusInput,
    Credentials,
    EmailSettingsInput,
    ForgotPasswordInput,
    ProfileInput,
    ResetPasswordInput,
    ServiceInput,
)
from security import (
    current_customer_id,
    current_owner_id,
    hash_password,
    hash_token,
    issue_customer_token,
    issue_owner_token,
    optional_customer_id,
    verify_password,
)

router = APIRouter(prefix="/api")

RESET_TOKEN_TTL_MINUTES = 30


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/auth/register")
def register(data: Credentials, response: Response, db: Session = Depends(db_session)):
    if db.query(Owner).filter(Owner.email == data.email.lower()).first():
        raise HTTPException(409, "Account already exists")
    owner = Owner(email=data.email.lower(), password_hash=hash_password(data.password))
    db.add(owner)
    db.commit()
    db.refresh(owner)
    _cookie(response, "owner_session", issue_owner_token(owner.id))
    return {"owner_id": owner.id, "email": owner.email}


@router.post("/auth/login")
def login(data: Credentials, response: Response, db: Session = Depends(db_session)):
    owner = db.query(Owner).filter(Owner.email == data.email.lower()).first()
    if not owner or not verify_password(data.password, owner.password_hash):
        raise HTTPException(401, "Invalid email or password")
    _cookie(response, "owner_session", issue_owner_token(owner.id))
    return {"owner_id": owner.id, "email": owner.email}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("owner_session")
    return {"logged_out": True}


@router.post("/auth/forgot-password")
def forgot_password(data: ForgotPasswordInput, request: Request, db: Session = Depends(db_session)):
    owner = db.query(Owner).filter(Owner.email == data.email.lower()).first()
    if owner:
        _issue_reset_token(db, "owner", owner.id, owner.email, request)
    return {"status": "ok", "message": "If an account exists for that email, a reset link has been sent."}


@router.post("/auth/reset-password")
def reset_password_route(data: ResetPasswordInput, db: Session = Depends(db_session)):
    owner_id = _consume_reset_token(db, "owner", data.token)
    if owner_id is None:
        raise HTTPException(400, "This reset link is invalid or has expired.")
    owner = db.get(Owner, owner_id)
    owner.password_hash = hash_password(data.new_password)
    db.commit()
    return {"status": "ok", "message": "Password updated. You can now sign in."}


@router.get("/owner/dashboard")
def dashboard(owner_id: int = Depends(current_owner_id), db: Session = Depends(db_session)):
    owner = db.get(Owner, owner_id)
    services = db.query(Service).filter(Service.owner_id == owner_id).order_by(Service.id).all()
    bookings = db.query(Booking).join(Service).filter(Service.owner_id == owner_id).order_by(Booking.id.desc()).all()
    return {
        "profile": {"email": owner.email, "business_name": owner.business_name},
        "services": [_service(item) for item in services],
        "bookings": [_booking(item) for item in bookings],
    }


@router.put("/owner/profile")
def profile(data: ProfileInput, owner_id: int = Depends(current_owner_id), db: Session = Depends(db_session)):
    owner = db.get(Owner, owner_id)
    owner.business_name = data.business_name
    db.commit()
    return {"business_name": owner.business_name}


@router.post("/owner/services")
def create_service(data: ServiceInput, owner_id: int = Depends(current_owner_id), db: Session = Depends(db_session)):
    item = Service(owner_id=owner_id, **data.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _service(item)


@router.get("/owner/email-settings")
def get_email_settings(owner_id: int = Depends(current_owner_id), db: Session = Depends(db_session)):
    setting = db.query(OwnerEmailSetting).filter(OwnerEmailSetting.owner_id == owner_id).first()
    return {
        "provider": setting.provider if setting else "platform",
        "gmail_address": setting.gmail_address if setting else None,
        "gmail_app_password_configured": bool(setting and setting.gmail_app_password_ciphertext),
        "vault_configured": vault_configured(),
    }


@router.put("/owner/email-settings")
def update_email_settings(data: EmailSettingsInput, owner_id: int = Depends(current_owner_id), db: Session = Depends(db_session)):
    if data.provider == "gmail" and data.gmail_app_password and not vault_configured():
        raise HTTPException(503, "Email credential vault is not configured.")
    setting = db.query(OwnerEmailSetting).filter(OwnerEmailSetting.owner_id == owner_id).first()
    if not setting:
        setting = OwnerEmailSetting(owner_id=owner_id)
        db.add(setting)
    setting.provider = data.provider
    if data.gmail_address is not None:
        setting.gmail_address = data.gmail_address
    if data.gmail_app_password:
        setting.gmail_app_password_ciphertext = encrypt_secret(data.gmail_app_password)
    db.commit()
    return {
        "provider": setting.provider,
        "gmail_address": setting.gmail_address,
        "gmail_app_password_configured": bool(setting.gmail_app_password_ciphertext),
        "vault_configured": vault_configured(),
    }


@router.post("/owner/email-settings/reveal")
def reveal_email_settings(owner_id: int = Depends(current_owner_id), db: Session = Depends(db_session)):
    setting = db.query(OwnerEmailSetting).filter(OwnerEmailSetting.owner_id == owner_id).first()
    if not setting or not setting.gmail_app_password_ciphertext:
        raise HTTPException(404, "No Gmail credential is saved yet.")
    try:
        password = decrypt_secret(setting.gmail_app_password_ciphertext)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    return {"gmail_app_password": password}


@router.get("/public/services")
def public_services(db: Session = Depends(db_session)):
    return [_service(item) for item in db.query(Service).order_by(Service.id).all()]


@router.post("/public/bookings")
def create_booking(
    data: BookingInput,
    customer_id: Optional[int] = Depends(optional_customer_id),
    db: Session = Depends(db_session),
):
    if not db.get(Service, data.service_id):
        raise HTTPException(404, "Service not found")
    item = Booking(customer_id=customer_id, **data.dict())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _booking(item)


@router.patch("/owner/bookings/{booking_id}")
def update_booking(booking_id: int, data: BookingStatusInput, owner_id: int = Depends(current_owner_id), db: Session = Depends(db_session)):
    item = db.query(Booking).join(Service).filter(Booking.id == booking_id, Service.owner_id == owner_id).first()
    if not item:
        raise HTTPException(404, "Booking not found")
    item.status = data.status
    db.commit()
    return _booking(item)


@router.post("/customer/auth/register")
def customer_register(data: Credentials, response: Response, db: Session = Depends(db_session)):
    if db.query(Customer).filter(Customer.email == data.email.lower()).first():
        raise HTTPException(409, "Account already exists")
    customer = Customer(email=data.email.lower(), password_hash=hash_password(data.password))
    db.add(customer)
    db.commit()
    db.refresh(customer)
    _cookie(response, "customer_session", issue_customer_token(customer.id))
    return {"customer_id": customer.id, "email": customer.email}


@router.post("/customer/auth/login")
def customer_login(data: Credentials, response: Response, db: Session = Depends(db_session)):
    customer = db.query(Customer).filter(Customer.email == data.email.lower()).first()
    if not customer or not verify_password(data.password, customer.password_hash):
        raise HTTPException(401, "Invalid email or password")
    _cookie(response, "customer_session", issue_customer_token(customer.id))
    return {"customer_id": customer.id, "email": customer.email}


@router.post("/customer/auth/logout")
def customer_logout(response: Response):
    response.delete_cookie("customer_session")
    return {"logged_out": True}


@router.post("/customer/auth/forgot-password")
def customer_forgot_password(data: ForgotPasswordInput, request: Request, db: Session = Depends(db_session)):
    customer = db.query(Customer).filter(Customer.email == data.email.lower()).first()
    if customer:
        _issue_reset_token(db, "customer", customer.id, customer.email, request)
    return {"status": "ok", "message": "If an account exists for that email, a reset link has been sent."}


@router.post("/customer/auth/reset-password")
def customer_reset_password(data: ResetPasswordInput, db: Session = Depends(db_session)):
    customer_id = _consume_reset_token(db, "customer", data.token)
    if customer_id is None:
        raise HTTPException(400, "This reset link is invalid or has expired.")
    customer = db.get(Customer, customer_id)
    customer.password_hash = hash_password(data.new_password)
    db.commit()
    return {"status": "ok", "message": "Password updated. You can now sign in."}


@router.get("/customer/bookings")
def customer_bookings(customer_id: int = Depends(current_customer_id), db: Session = Depends(db_session)):
    bookings = db.query(Booking).filter(Booking.customer_id == customer_id).order_by(Booking.id.desc()).all()
    return [_booking(item) for item in bookings]


def _issue_reset_token(db: Session, subject_type: str, subject_id: int, email: str, request: Request) -> None:
    token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        subject_type=subject_type,
        subject_id=subject_id,
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    ))
    db.commit()
    link = "%s/?type=%s&token=%s" % (str(request.base_url).rstrip("/"), subject_type, token)
    send_email(
        email,
        "Reset your Pawfect Appointments password",
        "Someone requested a password reset for your account.\n\n"
        "Reset your password (expires in %s minutes):\n%s\n\n"
        "If you did not request this, you can ignore this email." % (RESET_TOKEN_TTL_MINUTES, link),
        **_resolve_smtp_overrides(db),
    )


def _resolve_smtp_overrides(db: Session) -> dict:
    setting = db.query(OwnerEmailSetting).filter(OwnerEmailSetting.provider == "gmail").first()
    if not setting or not setting.gmail_address or not setting.gmail_app_password_ciphertext:
        return {}
    try:
        password = decrypt_secret(setting.gmail_app_password_ciphertext)
    except RuntimeError:
        return {}
    return {
        "host": "smtp.gmail.com",
        "port": 587,
        "username": setting.gmail_address,
        "password": password,
        "sender": setting.gmail_address,
    }


def _consume_reset_token(db: Session, subject_type: str, token: str) -> Optional[int]:
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == hash_token(token)).first()
    if (
        not reset_token
        or reset_token.subject_type != subject_type
        or reset_token.used_at is not None
        or reset_token.expires_at < datetime.utcnow()
    ):
        return None
    reset_token.used_at = datetime.utcnow()
    db.commit()
    return reset_token.subject_id


def _cookie(response: Response, name: str, token: str) -> None:
    response.set_cookie(name, token, httponly=True, secure=True, samesite="lax", max_age=43200)


def _service(item: Service) -> dict:
    return {"id": item.id, "name": item.name, "duration_minutes": item.duration_minutes, "price": item.price}


def _booking(item: Booking) -> dict:
    return {"id": item.id, "service_id": item.service_id, "service_name": item.service.name,
            "customer_name": item.customer_name, "customer_email": item.customer_email,
            "appointment_at": item.appointment_at.isoformat(), "status": item.status}
