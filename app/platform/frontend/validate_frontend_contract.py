from app.platform.artifacts.qualification_target import generated_app_path


GENERATED_APP = generated_app_path()


REQUIRED_CHECKS = [
    (
        "frontend/lib/auth.ts",
        'ACCESS_TOKEN_KEY = "access_token"',
        "frontend auth helper must use the approved access_token storage key",
    ),
    (
        "frontend/lib/api.ts",
        'headers.set("Authorization", `Bearer ${token}`)',
        "frontend API helper must attach Bearer token authorization header",
    ),
    (
        "frontend/app/login/page.tsx",
        "saveAccessToken(response.access_token)",
        "login page must save the access token through the trusted auth helper",
    ),
    (
        "frontend/app/register/page.tsx",
        "saveAccessToken(response.access_token)",
        "register page must save the access token through the trusted auth helper",
    ),
    (
        "frontend/app/login/page.tsx",
        "SAFE_ERROR_MESSAGES.loginFailed",
        "login page must use safe error messages",
    ),
    (
        "frontend/app/register/page.tsx",
        "SAFE_ERROR_MESSAGES.registerFailed",
        "register page must use safe error messages",
    ),
    (
        "frontend/app/customers/page.tsx",
        "SAFE_ERROR_MESSAGES.customersLoadFailed",
        "customers page must use safe load failure message",
    ),
    (
        "frontend/app/customers/page.tsx",
        "SAFE_ERROR_MESSAGES.customerCreateFailed",
        "customers page must use safe create failure message",
    ),
]


FORBIDDEN_CHECKS = [
    (
        "frontend/lib/auth.ts",
        'localStorage.getItem("token")',
        "frontend must not use old token storage key",
    ),
    (
        "frontend/lib/auth.ts",
        'localStorage.setItem("token"',
        "frontend must not save old token storage key",
    ),
    (
        "frontend/lib/api.ts",
        'localStorage.getItem("token")',
        "frontend API helper must use trusted auth helper instead of direct old token key",
    ),
]


def read_file(relative_path: str) -> str:
    path = GENERATED_APP / relative_path

    if not path.exists():
        raise AssertionError(f"Missing required frontend file: {relative_path}")

    return path.read_text()


def main() -> None:
    issues = []

    for relative_path, expected_text, message in REQUIRED_CHECKS:
        content = read_file(relative_path)

        if expected_text not in content:
            issues.append(
                {
                    "file": relative_path,
                    "issue": message,
                    "missing": expected_text,
                }
            )

    for relative_path, forbidden_text, message in FORBIDDEN_CHECKS:
        content = read_file(relative_path)

        if forbidden_text in content:
            issues.append(
                {
                    "file": relative_path,
                    "issue": message,
                    "forbidden": forbidden_text,
                }
            )

    passed = not issues

    print(
        {
            "passed": passed,
            "checked_app": str(GENERATED_APP),
            "required_check_count": len(REQUIRED_CHECKS),
            "forbidden_check_count": len(FORBIDDEN_CHECKS),
            "issues": issues,
        }
    )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
