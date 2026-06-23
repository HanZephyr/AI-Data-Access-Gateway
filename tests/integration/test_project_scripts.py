import tomllib
from pathlib import Path


def test_project_exposes_init_admin_script() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    scripts = data["project"]["scripts"]

    assert scripts["init-admin"] == "adg.control_plane.bootstrap:main"
    assert "adg-init-admin" not in scripts


def test_security_workflow_audits_frontend_dev_dependencies() -> None:
    workflow = (
        Path(__file__).resolve().parents[2]
        / ".github"
        / "workflows"
        / "security-audit.yml"
    ).read_text(encoding="utf-8")

    assert "npm audit --registry=https://registry.npmjs.org" in workflow


def test_release_docs_distinguish_fastmcp_and_supplemental_http_api() -> None:
    root = Path(__file__).resolve().parents[2]

    english_readme = (root / "README.md").read_text(encoding="utf-8")
    chinese_readme = (root / "docs" / "zh-CN" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "primary AI-agent integration is the FastMCP Streamable HTTP `/mcp`" in (
        english_readme
    )
    assert (
        "`POST /api/tools/{tool_name}` is a supplemental plain HTTP tool API"
        in english_readme
    )
    assert "面向 AI Agent 的主入口是 FastMCP Streamable HTTP `/mcp`" in chinese_readme
    assert (
        "`POST /api/tools/{tool_name}` 是面向传统服务集成的补充普通 HTTP 工具接口"
        in chinese_readme
    )


def test_historical_mcp_runtime_docs_mark_old_route_superseded() -> None:
    root = Path(__file__).resolve().parents[2]
    historical_docs = [
        root
        / "docs"
        / "superpowers"
        / "specs"
        / "2026-04-24-milestone-3-mcp-runtime-design.md",
        root
        / "docs"
        / "superpowers"
        / "acceptance"
        / "2026-04-24-milestone-3-mcp-runtime.md",
    ]

    for path in historical_docs:
        content = path.read_text(encoding="utf-8")
        assert "已被当前实现和 2026-04-26 身份改造覆盖" in content
        assert "不支持 `POST /mcp/tools/{tool_name}` 作为兼容别名" in content
