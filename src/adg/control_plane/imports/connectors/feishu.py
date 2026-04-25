from collections.abc import Mapping
from typing import Any, cast

from adg.control_plane.imports.connectors.base import (
    DirectoryImportBatch,
    PullOnlyDirectoryImporter,
    normalized_path,
    normalized_roles,
    required_text,
)
from adg.control_plane.imports.models import ImportedUserRow


class FeishuImporter(PullOnlyDirectoryImporter):
    """Normalize Feishu/Lark user payloads into the shared directory import batch."""

    platform = "feishu"

    def normalize(self, payload: Mapping[str, Any]) -> DirectoryImportBatch:
        users = payload.get("users")
        if not isinstance(users, list):
            raise ValueError("Feishu payload must include a users list")
        return DirectoryImportBatch(
            users=[
                ImportedUserRow(
                    user_name=required_text(user.get("name"), field_name="name"),
                    org_path=normalized_path(user.get("department_path"), delimiter=self.delimiter),
                    external_ref=required_text(user.get("user_id"), field_name="user_id"),
                    roles=normalized_roles(user.get("roles")),
                )
                for user in cast(list[Mapping[str, Any]], users)
            ],
            delimiter=self.delimiter,
        )
