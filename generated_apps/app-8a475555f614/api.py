from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from models import Booking, Owner, Service, SessionLocal
from schemas import BookingInput, BookingStatusInput, Credentials, ProfileInput, ServiceInput
from security import current_owner_id, hash_password, issue_owner_token, verify_password

router = APIRouter(prefix="/api")


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
    _cookie(response, issue_owner_token(owner.id))
    return {"owner_id": owner.id, "email": owner.email}


@router.post("/auth/login")
def login(data: Credentials, response: Response, db: Session = Depends(db_session)):
    owner = db.query(Owner).filter(Owner.email == data.email.lower()).first()
    if not owner or not verify_password(data.password, owner.password_hash):
        raise HTTPException(401, "Invalid email or password")
    _cookie(response, issue_owner_token(owner.id))
    return {"owner_id": owner.id, "email": owner.email}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("owner_session")
    return {"logged_out": True}


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


@router.get("/public/services")
def public_services(db: Session = Depends(db_session)):
    return [_service(item) for item in db.query(Service).order_by(Service.id).all()]


@router.post("/public/bookings")
def create_booking(data: BookingInput, db: Session = Depends(db_session)):
    if not db.get(Service, data.service_id):
        raise HTTPException(404, "Service not found")
    item = Booking(**data.dict())
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


def _cookie(response: Response, token: str) -> None:
    response.set_cookie("owner_session", token, httponly=True, secure=True, samesite="lax", max_age=43200)


def _service(item: Service) -> dict:
    return {"id": item.id, "name": item.name, "duration_minutes": item.duration_minutes, "price": item.price}


def _booking(item: Booking) -> dict:
    return {"id": item.id, "service_id": item.service_id, "service_name": item.service.name,
            "customer_name": item.customer_name, "customer_email": item.customer_email,
            "appointment_at": item.appointment_at.isoformat(), "status": item.status}
