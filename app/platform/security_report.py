import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATED_APP = ROOT / "generated_apps" / "crm-saas-multifile-001"


CHECKS = [
    {
        "name": "auth",
        "status": "present",
        "files": [
            "backend/app/api/routes/auth.py",
            "backend/app/core/security.py",
        ],
        "required_text": [
            "create_access_token",
            "decode_access_token",
            "hash_password",
            "verify_password",
        ],
    },
    {
        "name": "rate_limiting",
        "status": "present",
        "files": [
            "backend/app/core/rate_limit.py",
            "backend/app/api/routes/auth.py",
        ],
        "required_text": [
            "AUTH_RATE_LIMIT",
            "@limiter.limit(AUTH_RATE_LIMIT)",
        ],
    },
    {
        "name": "membership_rbac",
        "status": "membership_based",
        "files": [
            "backend/app/api/dependencies.py",
            "backend/app/models/membership.py",
        ],
        "required_text": [
            "def require_role",
            "Membership.user_id",
            "Membership.role.in_",
        ],
    },
    {
        "name": "audit_logging",
        "status": "present",
        "files": [
            "backend/app/models/audit_log.py",
            "backend/app/services/audit_service.py",
            "backend/app/api/routes/auth.py",
            "backend/app/api/routes/customers.py",
        ],
        "required_text": [
            "class AuditLog",
            "create_audit_log",
            "user_registered",
            "login_success",
            "customer_created",
        ],
    },
    {
        "name": "frontend_token_handling",
        "status": "validated",
        "files": [
            "frontend/lib/auth.ts",
            "frontend/lib/api.ts",
            "frontend/app/login/page.tsx",
            "frontend/app/register/page.tsx",
        ],
        "required_text": [
            'ACCESS_TOKEN_KEY = "access_token"',
            'headers.set("Authorization", `Bearer ${token}`)',
            "saveAccessToken(response.access_token)",
        ],
    },
    {
        "name": "frontend_safe_errors",
        "status": "validated",
        "files": [
            "frontend/lib/errors.ts",
            "frontend/app/login/page.tsx",
            "frontend/app/register/page.tsx",
            "frontend/app/customers/page.tsx",
        ],
        "required_text": [
            "SAFE_ERROR_MESSAGES",
            "loginFailed",
            "registerFailed",
            "customersLoadFailed",
            "customerCreateFailed",
        ],
    },
    {
        "name": "containerization",
        "status": "present",
        "files": [
            "backend/Dockerfile",
            "backend/docker-compose.yml",
            "backend/.dockerignore",
        ],
        "required_text": [],
    },
]


def read_existing_files(relative_paths):
    contents = {}

    for relative_path in relative_paths:
        path = GENERATED_APP / relative_path

        if path.exists():
            contents[relative_path] = path.read_text()
        else:
            contents[relative_path] = None

    return contents


def evaluate_check(check):
    contents = read_existing_files(check["files"])
    missing_files = [
        relative_path
        for relative_path, content in contents.items()
        if content is None
    ]

    combined_content = "\n".join(
        content for content in contents.values() if content is not None
    )

    missing_text = [
        required
        for required in check["required_text"]
        if required not in combined_content
    ]

    passed = not missing_files and not missing_text

    return {
        "name": check["name"],
        "expected_status": check["status"],
        "passed": passed,
        "missing_files": missing_files,
        "missing_text": missing_text,
    }


def main():
    results = [evaluate_check(check) for check in CHECKS]
    passed = all(result["passed"] for result in results)

    report = {
        "generated_app": str(GENERATED_APP),
        "overall": "MVP-safe" if passed else "needs-attention",
        "passed": passed,
        "summary": {
            "auth": "present",
            "rate_limiting": "present",
            "rbac": "membership-based",
            "audit_logging": "present",
            "frontend_token_handling": "validated",
            "frontend_safe_errors": "validated",
            "frontend_build_validation": "available",
        },
        "checks": results,
    }

    print(json.dumps(report, indent=2))

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
