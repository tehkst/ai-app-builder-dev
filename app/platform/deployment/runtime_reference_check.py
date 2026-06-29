from __future__ import annotations

from pathlib import Path


def assert_contains(path: str, text: str) -> None:
    content = Path(path).read_text()
    assert text in content, "{} missing {}".format(path, text)


def main() -> None:
    path = "infra/gcp/runtime-references.example"
    assert Path(path).exists(), path
    assert_contains(path, "APP_REF=")
    assert_contains(path, "DATA_REF=")
    assert_contains(path, "MODEL_A_REF=")
    assert_contains(path, "PAYMENT_REF=")
    assert_contains(path, "MAIL_REF=")
    print("RUNTIME REFERENCE CHECK PASSED")


if __name__ == "__main__":
    main()
