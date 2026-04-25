from pathlib import Path

import yaml


def test_backend_healthcheck_targets_live_health_endpoint() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))

    healthcheck = compose["services"]["backend"]["healthcheck"]["test"]

    assert healthcheck[-1] == "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health')"
