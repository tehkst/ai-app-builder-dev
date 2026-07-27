from __future__ import annotations

import argparse
from pathlib import Path


def validate_contract() -> None:
    root = Path(__file__).parent
    required = ["main.py", "models.py", "security.py", "api.py", "schemas.py",
                "index.html", "assets/app.js", "assets/app.css", "Dockerfile", "requirements.txt"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise SystemExit("Missing reference application files: %s" % ", ".join(missing))
    html = (root / "index.html").read_text(encoding="utf-8")
    script = (root / "assets/app.js").read_text(encoding="utf-8")
    for marker in (
        "bookingForm", "registerForm", "loginForm", "serviceForm", "bookingList",
        "forgotPasswordForm", "resetPasswordForm",
        "customerRegisterForm", "customerLoginForm", "customerForgotForm", "customerBookingList",
    ):
        if marker not in html and marker not in script:
            raise SystemExit("Missing acceptance marker: %s" % marker)
    print("REFERENCE APPLICATION CONTRACT PASSED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-contract", action="store_true")
    parser.parse_args()
    validate_contract()
