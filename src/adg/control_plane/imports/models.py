from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ImportedUserRow:
    """Normalized directory import row derived from an Excel-like template."""

    user_name: str
    org_path: str | None
    external_ref: str
    roles: list[str]


@dataclass(frozen=True, slots=True)
class ExcelImportPreview:
    """Preview of what an import would create or update."""

    users: list[dict[str, Any]]
    org_nodes_to_create: list[str]
    roles_to_create: list[str]
    root_org_node_required: bool
    summary: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "users": self.users,
            "org_nodes_to_create": self.org_nodes_to_create,
            "roles_to_create": self.roles_to_create,
            "root_org_node_required": self.root_org_node_required,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class ExcelImportExecution:
    """Concrete results after applying an import batch."""

    users: list[dict[str, Any]]
    org_nodes_created: list[str]
    roles_created: list[str]
    root_org_node_created: bool
    summary: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "users": self.users,
            "org_nodes_created": self.org_nodes_created,
            "roles_created": self.roles_created,
            "root_org_node_created": self.root_org_node_created,
            "summary": self.summary,
        }
