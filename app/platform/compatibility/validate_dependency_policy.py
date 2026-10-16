import json

from app.platform.compatibility.dependency_policy import (
    APPROVED_PLATFORM_DEPENDENCIES,
    CANDIDATE_PLATFORM_DEPENDENCIES,
    DEPENDENCY_POLICY_RULES,
)


REQUIRED_APPROVED_DEPENDENCIES = [
    "fastapi",
    "sqlalchemy",
    "python-dotenv",
    "openai",
    "pyyaml",
    "slowapi",
]


REQUIRED_SECURITY_CANDIDATES = []


REQUIRED_FIELDS = [
    "purpose",
    "risk_level",
    "notes",
]


def validate_dependency_policy():
    issues = []

    for dependency_name in REQUIRED_APPROVED_DEPENDENCIES:
        dependency = APPROVED_PLATFORM_DEPENDENCIES.get(dependency_name)

        if dependency is None:
            issues.append(
                {
                    "dependency": dependency_name,
                    "issue": "Required approved dependency is missing from policy.",
                }
            )
            continue

        for field in REQUIRED_FIELDS:
            if not dependency.get(field):
                issues.append(
                    {
                        "dependency": dependency_name,
                        "field": field,
                        "issue": "Approved dependency is missing a required policy field.",
                    }
                )

    for dependency_name in REQUIRED_SECURITY_CANDIDATES:
        dependency = CANDIDATE_PLATFORM_DEPENDENCIES.get(dependency_name)

        if dependency is None:
            issues.append(
                {
                    "dependency": dependency_name,
                    "issue": "Required security candidate dependency is missing from policy.",
                }
            )
            continue

        for field in REQUIRED_FIELDS:
            if not dependency.get(field):
                issues.append(
                    {
                        "dependency": dependency_name,
                        "field": field,
                        "issue": "Candidate dependency is missing a required policy field.",
                    }
                )

    if not DEPENDENCY_POLICY_RULES:
        issues.append(
            {
                "issue": "Dependency policy rules must not be empty.",
            }
        )

    return {
        "passed": len(issues) == 0,
        "approved_dependency_count": len(APPROVED_PLATFORM_DEPENDENCIES),
        "candidate_dependency_count": len(CANDIDATE_PLATFORM_DEPENDENCIES),
        "rule_count": len(DEPENDENCY_POLICY_RULES),
        "issues": issues,
    }


def main():
    report = validate_dependency_policy()
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
