from __future__ import annotations

from app.platform.auth.auth_check import main as auth_check
from app.platform.auth.auth_provider_check import main as provider_check
from app.platform.auth.d54_marker import main as marker_check
from app.platform.auth.journal_check import main as journal_check
from app.platform.auth.policy_check import main as policy_check
from app.platform.security.security_context_check import main as context_check


def main() -> None:
    context_check()
    provider_check()
    policy_check()
    marker_check()
    journal_check()
    auth_check()
    print("D5 READINESS CHECK PASSED")


if __name__ == "__main__":
    main()
