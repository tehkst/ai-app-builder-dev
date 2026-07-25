from __future__ import annotations

from typing import Any


REFERENCE_KIND = "appointment_booking"


def bounded_specification(description: str, application_name: str = "") -> dict[str, Any]:
    request = " ".join(str(description or "").split()).strip()
    if not request:
        raise ValueError("Describe the application you want to build.")
    lowered = request.lower()
    if not any(term in lowered for term in ("appointment", "booking", "bookable", "schedule")):
        raise ValueError("The current golden path supports a bounded appointment-booking application.")
    name = " ".join(str(application_name or "").split()).strip() or "Bookable"
    return {
        "contract": "generated-application-spec-v1",
        "reference_kind": REFERENCE_KIND,
        "product_name": name[:80],
        "founder_request": request,
        "target_users": ["business owner", "customer"],
        "primary_journeys": [
            "Owner registers, signs in, creates a business profile and service, and manages bookings.",
            "Customer views the public page, selects a service and time, and confirms a booking.",
        ],
        "functional_requirements": [
            "Owner registration, login, logout, and protected management pages",
            "Business profile and service creation",
            "Public service and availability selection",
            "Booking creation, confirmation, listing, and status updates",
        ],
        "non_functional_requirements": [
            "Responsive interface", "Persistent PostgreSQL data", "Input validation",
            "Empty, error, and success states", "Health and readiness endpoints",
        ],
        "data_entities": ["Owner", "Business", "Service", "Booking"],
        "permissions": {"owner": "manage own business data", "customer": "create public bookings"},
        "pages": ["Home", "Register", "Login", "Owner dashboard", "Public booking", "Confirmation"],
        "apis": ["/api/auth/*", "/api/owner/*", "/api/public/*", "/health", "/ready"],
        "acceptance_criteria": [
            "Owner registration and protected login work.",
            "A service and customer booking persist after refresh.",
            "The owner can view and update the booking.",
            "Health, readiness, and live browser acceptance pass.",
        ],
        "deployment_requirements": ["Cloud Run", "PostgreSQL DATABASE_URL", "APP_SESSION_SECRET"],
        "excluded_functionality": [
            "Payments", "calendar synchronization", "marketplace discovery",
            "native mobile applications", "complex roles", "application billing",
        ],
    }
