import json
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

COMPOSE_EXAMPLE = Path("docker-compose.example.yml")


def load_compose_example() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(COMPOSE_EXAMPLE.read_text(encoding="utf-8")))


def test_compose_stack_is_tracked_as_an_example_template() -> None:
    assert COMPOSE_EXAMPLE.exists()
    assert "docker-compose.yml" in Path(".gitignore").read_text(encoding="utf-8").splitlines()


def test_backend_healthcheck_targets_live_health_endpoint() -> None:
    compose = load_compose_example()

    healthcheck = compose["services"]["backend"]["healthcheck"]["test"]

    assert healthcheck[-1] == (
        "from os import environ; "
        "from urllib.request import urlopen; "
        "urlopen(f\"http://127.0.0.1:{environ.get('ADG_BACKEND_PORT', '8000')}/health\")"
    )


def test_backend_compose_allows_configurable_internal_port() -> None:
    compose = load_compose_example()

    backend = compose["services"]["backend"]

    assert backend["environment"]["ADG_BACKEND_PORT"] == "${ADG_BACKEND_PORT:-8000}"
    assert backend["expose"] == ["${ADG_BACKEND_PORT:-8000}"]
    assert "--port ${ADG_BACKEND_PORT:-8000}" in backend["command"]


def test_backend_compose_passes_runtime_datasource_pool_settings() -> None:
    compose = load_compose_example()

    environment = compose["services"]["backend"]["environment"]

    assert environment["ADG_RUNTIME_DATASOURCE_POOL_CACHE_SIZE"] == (
        "${ADG_RUNTIME_DATASOURCE_POOL_CACHE_SIZE:-32}"
    )
    assert environment["ADG_RUNTIME_DATASOURCE_POOL_IDLE_TTL_SECONDS"] == (
        "${ADG_RUNTIME_DATASOURCE_POOL_IDLE_TTL_SECONDS:-300}"
    )
    assert environment["ADG_RUNTIME_DATASOURCE_POOL_SIZE"] == (
        "${ADG_RUNTIME_DATASOURCE_POOL_SIZE:-5}"
    )
    assert environment["ADG_RUNTIME_DATASOURCE_POOL_MAX_OVERFLOW"] == (
        "${ADG_RUNTIME_DATASOURCE_POOL_MAX_OVERFLOW:-0}"
    )


def test_backend_dockerfile_supports_configurable_runtime_port() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "ENV ADG_BACKEND_PORT=8000" in dockerfile
    assert "--port ${ADG_BACKEND_PORT:-8000}" in dockerfile


def test_backend_compose_requires_both_production_secrets() -> None:
    compose = load_compose_example()

    environment = compose["services"]["backend"]["environment"]

    assert "ADG_SECRET_KEY" in environment
    assert "ADG_CREDENTIAL_ENCRYPTION_KEY" in environment


def test_backend_compose_passes_optional_pypi_index_build_arg() -> None:
    compose = load_compose_example()

    build = compose["services"]["backend"]["build"]

    assert build["args"]["PYPI_INDEX_URL"] == "${PYPI_INDEX_URL:-https://pypi.org/simple}"


def test_backend_compose_publishes_configurable_host_port_for_mcp_clients() -> None:
    compose = load_compose_example()

    backend = compose["services"]["backend"]

    assert backend["ports"] == ["${ADG_BACKEND_HOST_PORT:-8000}:${ADG_BACKEND_PORT:-8000}"]
    assert backend["environment"]["ADG_BACKEND_HOST_PORT"] == "${ADG_BACKEND_HOST_PORT:-8000}"


def test_backend_dockerfile_runs_as_non_root_user() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "USER adg" in dockerfile


def test_backend_dockerfile_uses_uv_lock_for_frozen_installs() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "COPY pyproject.toml uv.lock" in dockerfile
    assert "uv sync --frozen --no-dev --extra all" in dockerfile


def test_backend_dockerfile_supports_configurable_pypi_index() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "ARG PYPI_INDEX_URL=https://pypi.org/simple" in dockerfile
    assert 'pip install --no-cache-dir --index-url "${PYPI_INDEX_URL}" uv' in dockerfile
    assert 'uv sync --frozen --no-dev --extra all --default-index "${PYPI_INDEX_URL}"' in dockerfile


def test_env_example_documents_optional_pypi_index() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "PYPI_INDEX_URL=https://pypi.org/simple" in env_example


def test_env_example_documents_backend_port_override() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "ADG_BACKEND_PORT=8000" in env_example


def test_env_example_documents_backend_host_port_override() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "ADG_BACKEND_HOST_PORT=8000" in env_example


def test_web_compose_passes_optional_npm_registry_build_arg() -> None:
    compose = load_compose_example()

    build = compose["services"]["web"]["build"]

    assert build["args"]["NPM_REGISTRY_URL"] == "${NPM_REGISTRY_URL:-https://registry.npmjs.org/}"


def test_web_compose_allows_configurable_host_port() -> None:
    compose = load_compose_example()

    web = compose["services"]["web"]

    assert web["ports"] == ["${ADG_WEB_PORT:-8080}:80"]


def test_web_compose_passes_backend_port_to_nginx() -> None:
    compose = load_compose_example()

    web = compose["services"]["web"]

    assert web["environment"]["ADG_BACKEND_PORT"] == "${ADG_BACKEND_PORT:-8000}"


def test_web_dockerfile_uses_npm_ci() -> None:
    dockerfile = Path("web/Dockerfile").read_text(encoding="utf-8")

    assert "RUN npm ci" in dockerfile
    assert "RUN npm install" not in dockerfile


def test_web_dockerfile_supports_configurable_npm_registry() -> None:
    dockerfile = Path("web/Dockerfile").read_text(encoding="utf-8")

    assert "ARG NPM_REGISTRY_URL=https://registry.npmjs.org/" in dockerfile
    assert 'npm ci --registry "${NPM_REGISTRY_URL}"' in dockerfile


def test_web_dockerfile_renders_nginx_config_from_template() -> None:
    dockerfile = Path("web/Dockerfile").read_text(encoding="utf-8")

    assert "COPY web/nginx.conf /etc/nginx/templates/default.conf.template" in dockerfile
    assert "COPY web/nginx.conf /etc/nginx/conf.d/default.conf" not in dockerfile


def test_web_nginx_proxy_uses_configurable_backend_port() -> None:
    nginx_conf = Path("web/nginx.conf").read_text(encoding="utf-8")

    assert "backend:${ADG_BACKEND_PORT}" in nginx_conf
    assert "backend:8000" not in nginx_conf


def test_env_example_documents_optional_npm_registry() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "NPM_REGISTRY_URL=https://registry.npmjs.org/" in env_example


def test_env_example_documents_web_port_override() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "ADG_WEB_PORT=8080" in env_example


def test_web_package_declares_auditable_dependency_scripts() -> None:
    package_json = json.loads(Path("web/package.json").read_text(encoding="utf-8"))

    scripts = package_json["scripts"]
    assert scripts["audit"] == "npm audit --registry=https://registry.npmjs.org"
    assert scripts["audit:prod"] == "npm audit --omit=dev --registry=https://registry.npmjs.org"
    dependencies = package_json["dependencies"]
    dev_dependencies = package_json["devDependencies"]
    assert "xlsx" not in dependencies
    assert "read-excel-file" in dependencies
    assert "@vitejs/plugin-react" not in dependencies
    assert "typescript" not in dependencies
    assert "vite" not in dependencies
    assert "@vitejs/plugin-react" in dev_dependencies
    assert "typescript" in dev_dependencies
    assert "vite" in dev_dependencies
