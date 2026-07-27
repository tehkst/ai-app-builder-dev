from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Optional

SMTP_HOST_ENV = "SMTP_HOST"
SMTP_PORT_ENV = "SMTP_PORT"
SMTP_USERNAME_ENV = "SMTP_USERNAME"
SMTP_PASSWORD_ENV = "SMTP_PASSWORD"
EMAIL_FROM_ENV = "EMAIL_FROM"


def email_configured() -> bool:
    return bool(os.getenv(SMTP_HOST_ENV) and os.getenv(SMTP_USERNAME_ENV) and os.getenv(SMTP_PASSWORD_ENV))


def send_email(
    to_address: str,
    subject: str,
    body: str,
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    sender: Optional[str] = None,
) -> Dict[str, Any]:
    host = host or os.getenv(SMTP_HOST_ENV, "")
    port = port or int(os.getenv(SMTP_PORT_ENV, "587"))
    username = username or os.getenv(SMTP_USERNAME_ENV, "")
    password = password or os.getenv(SMTP_PASSWORD_ENV, "")
    sender = sender or os.getenv(EMAIL_FROM_ENV) or username

    if not (host and username and password):
        return {
            "sent": False,
            "reason": "SMTP is not configured. Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_FROM.",
        }

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_address
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(message)
        return {"sent": True, "reason": None}
    except Exception as exc:
        return {"sent": False, "reason": f"{type(exc).__name__}: {exc}"}
