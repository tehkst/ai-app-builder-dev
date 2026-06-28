from __future__ import annotations

from app.platform.catalog.catalog_workflow import run_demo_catalog


def main() -> None:
    data = run_demo_catalog()
    assert len(data.items) == 3, data
    assert len(data.releases) == 2, data
    assert len(data.activations) == 2, data
    assert len(data.rules) == 2, data
    print("V124 CHECK PASSED")


if __name__ == "__main__":
    main()
