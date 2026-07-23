FACTORY_COMPATIBILITY_POLICY = {
    "factory_python_major_minor": "3.9",
    "generated_backend_python_major_minor": "3.11",
    "generated_frontend_node_major": "20",
    "generated_postgres_image": "postgres:16-alpine",
}


FACTORY_RUNTIME_SCAN_PATHS = [
    "app",
    "test_graph.py",
]


FACTORY_RUNTIME_EXCLUDED_PATHS = [
    "generated_apps",
    "app/ai/nodes/template_enforcer.py",
    "app/platform/compatibility/policy.py",
]


PYTHON_39_FORBIDDEN_PATTERNS = [
    {
        "pattern": "pep604_union_without_future_annotations",
        "issue": (
            "PEP 604 union annotations require Python 3.10 unless the module "
            "enables postponed annotation evaluation."
        ),
    },
]
