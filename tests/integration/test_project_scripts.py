import tomllib
from pathlib import Path


def test_project_exposes_init_admin_script() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    scripts = data["project"]["scripts"]

    assert scripts["init-admin"] == "adg.control_plane.bootstrap:main"
    assert "adg-init-admin" not in scripts
