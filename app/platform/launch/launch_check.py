from __future__ import annotations

from app.platform.launch.launch_flow import run_demo_launch
from app.platform.launch.launch_store import (
    launch_is_ready,
    published_packages,
    ready_documentation,
    ready_required_signals,
    required_signals,
    summarize_launch,
)


def main() -> None:
    data = run_demo_launch()
    assert len(data.documentation) == 3, data
    assert len(data.packages) == 2, data
    assert len(data.signals) == 5, data

    assert len(ready_documentation(data.documentation)) == 3
    assert len(published_packages(data.packages)) == 2
    assert len(required_signals(data.signals)) == 4
    assert len(ready_required_signals(data.signals)) == 4
    assert launch_is_ready(data.signals) is True

    summary = summarize_launch(data.documentation, data.packages, data.signals)
    assert summary.documentation_count == 3, summary
    assert summary.ready_documentation_count == 3, summary
    assert summary.package_count == 2, summary
    assert summary.published_package_count == 2, summary
    assert summary.required_signal_count == 4, summary
    assert summary.ready_required_signal_count == 4, summary

    print("LAUNCH PACK CHECK PASSED")


if __name__ == "__main__":
    main()
