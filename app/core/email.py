from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any, Dict

from app.platform.runtime.smtp_provider_router import active_smtp_config


def email_configured() -> bool:
    config = active_smtp_config()
    return bool(config["host"] and config["username"] and config["password"])


def send_email(to_address: str, subject: str, body: str) -> Dict[str, Any]:
    config = active_smtp_config()
    if not (config["host"] and config["username"] and config["password"]):
        return {
            "sent": False,
            "reason": f"SMTP is not configured for the {config['provider']} provider. "
                      f"Set the required credentials in Secret Manager.",
        }

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["sender"]
    message["To"] = to_address
    message.set_content(body)

    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
            server.starttls()
            server.login(config["username"], config["password"])
            server.send_message(message)
        return {"sent": True, "reason": None}
    except Exception as exc:
        return {"sent": False, "reason": f"{type(exc).__name__}: {exc}"}
