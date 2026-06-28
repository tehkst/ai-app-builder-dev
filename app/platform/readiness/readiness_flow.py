from __future__ import annotations

from app.platform.readiness.readiness_models import (
    DependencyCheck,
    EnvironmentCheck,
    PerformanceMetric,
    ReadinessContext,
    ReadinessItem,
)


def run_demo_readiness() -> ReadinessContext:
    items = [
        ReadinessItem("ready_security", "security", "Security baseline", "passed", True),
        ReadinessItem("ready_billing", "billing", "Billing workflow", "passed", True),
        ReadinessItem("ready_docs", "docs", "User documentation", "pending", False),
        ReadinessItem("ready_monitoring", "operations", "Monitoring baseline", "passed", True),
    ]
    environments = [
        EnvironmentCheck("env_staging", "staging", "Staging environment", "ready"),
        EnvironmentCheck("env_prod", "production", "Production environment", "ready"),
        EnvironmentCheck("env_dev", "development", "Development environment", "ready"),
    ]
    dependencies = [
        DependencyCheck("dep_python", "python", "3.9", "ready"),
        DependencyCheck("dep_fastapi", "fastapi", "pinned", "ready"),
        DependencyCheck("dep_openai", "openai", "configured", "ready"),
    ]
    performance = [
        PerformanceMetric("perf_latency", "latency_p95", 380, 500, "ms"),
        PerformanceMetric("perf_error", "error_rate", 0.01, 0.05, "ratio"),
        PerformanceMetric("perf_queue", "queue_wait", 20, 60, "seconds"),
    ]
    return ReadinessContext(
        items=items,
        environments=environments,
        dependencies=dependencies,
        performance=performance,
        metadata={"flow": "readiness_pack"},
    )
