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


class DingTalkImporter(PullOnlyDirectoryImporter):
    """Normalize DingTalk user payloads into the shared directory import batch."""

    platform = "dingtalk"

    def normalize(self, payload: Mapping[str, Any]) -> DirectoryImportBatch:
        result = payload.get("result")
        if not isinstance(result, Mapping):
            raise ValueError("DingTalk payload must include a result mapping")
        users = result.get("users")
        if not isinstance(users, list):
            raise ValueError("DingTalk payload must include a users list")

        return DirectoryImportBatch(
            users=[
                ImportedUserRow(
                    user_name=required_text(user.get("name"), field_name="name"),
                    org_path=normalized_path(user.get("dept_path"), delimiter=self.delimiter),
                    external_ref=required_text(user.get("userid"), field_name="userid"),
                    roles=normalized_roles(user.get("role_list")),
                )
                for user in cast(list[Mapping[str, Any]], users)
            ],
            delimiter=self.delimiter,
        )
