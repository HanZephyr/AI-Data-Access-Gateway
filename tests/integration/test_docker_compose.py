from pathlib import Path

import yaml  # type: ignore[import-untyped]


def test_backend_healthcheck_targets_live_health_endpoint() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))

    healthcheck = compose["services"]["backend"]["healthcheck"]["test"]

    assert healthcheck[-1] == "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health')"


def test_backend_compose_requires_both_production_secrets() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))

    environment = compose["services"]["backend"]["environment"]

    assert "ADG_SECRET_KEY" in environment
    assert "ADG_CREDENTIAL_ENCRYPTION_KEY" in environment
