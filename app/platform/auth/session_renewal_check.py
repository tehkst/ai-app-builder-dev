"""Check for founder session renewal (found in the pilot: an open Mission Control signed the founder
out every 12 hours, twice during one job). A valid session gets a fresh token that keeps the
original sign-in time; renewals never go past 7 days after the password was entered; an expired,
tampered or non-founder token is refused."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.platform.auth import service
from app.platform.auth.service import _sign_claims, _verify_token, login_founder, refresh_session


def iso(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat()


def main() -> None:
    env = dict(os.environ, FOUNDER_EMAIL="founder@example.com", FOUNDER_PASSWORD="local-test-password",
               MISSION_CONTROL_SESSION_SECRET="session-renewal-check-secret")
    with patch.dict(os.environ, env, clear=True), patch.object(service, "_persisted_password_hash", lambda: None):
        login = login_founder({"email": "founder@example.com", "password": "local-test-password"})
        assert login["authenticated"], login
        first = _verify_token(login["session"]["token"])
        assert first["auth_time"] and first["exp"] > first["auth_time"], first

        renewed = refresh_session({"token": login["session"]["token"]})
        claims = _verify_token(renewed["session"]["token"])
        assert renewed["authenticated"] and claims["auth_time"] == first["auth_time"], "keeps the sign-in time"
        assert claims["sub"] == "founder@example.com" and claims["role"] == "founder"

        now = datetime.now(timezone.utc)
        late = _sign_claims({"sub": "founder@example.com", "role": "founder", "iat": iso(now),
                             "auth_time": iso(now - timedelta(days=6, hours=20)), "exp": iso(now + timedelta(hours=1))})
        capped = _verify_token(refresh_session({"token": late})["session"]["token"])
        assert datetime.fromisoformat(capped["exp"]) <= now + timedelta(hours=4, minutes=1), "never past 7 days"

        stale = _sign_claims({"sub": "founder@example.com", "role": "founder", "iat": iso(now),
                              "auth_time": iso(now - timedelta(days=7, minutes=1)), "exp": iso(now + timedelta(hours=1))})
        assert refresh_session({"token": stale})["authenticated"] is False, "the password is asked again after 7 days"

        legacy = _sign_claims({"sub": "founder@example.com", "role": "founder", "iat": iso(now - timedelta(hours=2)),
                               "exp": iso(now + timedelta(hours=10))})  # issued before auth_time existed
        assert _verify_token(refresh_session({"token": legacy})["session"]["token"])["auth_time"] == iso(now - timedelta(hours=2))

        expired = _sign_claims({"sub": "founder@example.com", "role": "founder", "iat": iso(now - timedelta(hours=13)),
                                "auth_time": iso(now - timedelta(hours=13)), "exp": iso(now - timedelta(hours=1))})
        system = _sign_claims({"sub": "system", "role": "system", "iat": iso(now), "exp": iso(now + timedelta(minutes=2))})
        for bad in (expired, system, login["session"]["token"][:-2] + "00", "", "nonsense"):
            assert refresh_session({"token": bad})["authenticated"] is False, bad[:20]
    print("SESSION RENEWAL CHECK PASSED")


if __name__ == "__main__":
    main()
