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
        "pattern": "| None",
        "issue": "Python 3.10 union type syntax is not allowed in factory Python 3.9 runtime code.",
    },
    {
        "pattern": "None |",
        "issue": "Python 3.10 union type syntax is not allowed in factory Python 3.9 runtime code.",
    },
    {
        "pattern": "dict[",
        "issue": "Use typing.Dict for factory Python 3.9 runtime compatibility.",
    },
    {
        "pattern": "list[",
        "issue": "Use typing.List for factory Python 3.9 runtime compatibility.",
    },
    {
        "pattern": "tuple[",
        "issue": "Use typing.Tuple for factory Python 3.9 runtime compatibility.",
    },
]
