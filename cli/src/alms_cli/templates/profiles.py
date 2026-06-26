"""Profile, capability, and dependency metadata for generated ALMS projects."""

ALL_CAPABILITIES = {
    "runtime_auth",
    "scalar_docs",
    "llm",
    "langgraph",
    "database",
    "redis",
    "observability",
    "tests",
    "docker",
    "ci",
}

PROFILE_CAPABILITIES: dict[str, set[str]] = {
    "core-api": {"runtime_auth", "tests"},
    "llm-agent": {"runtime_auth", "tests", "llm", "scalar_docs"},
    "workflow-agent": {"runtime_auth", "tests", "llm", "langgraph", "scalar_docs"},
    "db-agent": {"runtime_auth", "tests", "database"},
    "observable": {"runtime_auth", "tests", "observability"},
    "full": {
        "runtime_auth",
        "tests",
        "llm",
        "langgraph",
        "database",
        "redis",
        "observability",
        "scalar_docs",
        "docker",
        "ci",
    },
}

FEATURE_LABEL_TO_CAPABILITY: dict[str, str] = {
    "database": "database",
    "redis cache": "redis",
    "ai agents": "llm",
    "observability": "observability",
    "docker support": "docker",
    "ci/cd": "ci",
}

CAPABILITY_TO_EXTRA: dict[str, str | None] = {
    "llm": "ai",
    "langgraph": "workflow",
    "database": "db",
    "redis": "cache",
    "observability": "observability",
    "scalar_docs": "docs",
}

NO_EXTRA_CAPABILITIES = frozenset({"runtime_auth", "tests", "docker", "ci"})

EXTRA_DEPS: dict[str, list[str]] = {
    "ai": [
        "langchain>=1.2.15",
        "langchain-community>=0.4.1",
        "langchain-mcp-adapters>=0.1.14",
        "langchain-openai>=1.1.0",
        "openai>=2.33.0",
    ],
    "workflow": ["langgraph>=1.1.9"],
    "db": [
        "sqlalchemy>=2.0.49",
        "asyncpg>=0.31.0",
        "alembic>=1.17.2",
    ],
    "cache": ["redis>=7.4.0"],
    "observability": [
        "opentelemetry-api>=1.25.0",
        "opentelemetry-sdk>=1.25.0",
        "opentelemetry-instrumentation-fastapi>=0.46b0",
        "opentelemetry-instrumentation-sqlalchemy>=0.46b0",
        "opentelemetry-instrumentation-redis>=0.46b0",
        "opentelemetry-exporter-otlp>=1.25.0",
        "prometheus-client>=0.20.0",
    ],
    "docs": ["scalar-fastapi>=1.6.0"],
}


def resolve_capabilities(
    profile: str | None = None,
    features: list[str] | None = None,
) -> set[str]:
    """Return the resolved capability set from a profile name and/or feature list."""
    caps: set[str] = set()

    if profile and profile in PROFILE_CAPABILITIES:
        caps = PROFILE_CAPABILITIES[profile].copy()

    if features:
        for feature in features:
            key = feature.strip().lower()
            for label, capability in FEATURE_LABEL_TO_CAPABILITY.items():
                if label in key:
                    caps.add(capability)
                    break

    caps.add("runtime_auth")
    caps.add("tests")
    return caps


def resolve_extras(capabilities: set[str]) -> list[str]:
    """Return the ordered list of pip extras needed for a capability set."""
    extras: list[str] = []
    for capability in sorted(capabilities):
        extra = CAPABILITY_TO_EXTRA.get(capability)
        if extra and extra not in extras:
            extras.append(extra)
    return extras


def resolve_profile(capabilities: set[str]) -> str:
    """Return the matching profile name, or custom when capabilities are ad hoc."""
    for name, profile_capabilities in PROFILE_CAPABILITIES.items():
        if profile_capabilities == capabilities:
            return name
    return "custom"
