from collections.abc import Mapping, Sequence
from typing import Any, cast

from adg.control_plane.imports.connectors.base import (
    DirectoryImportBatch,
    PullOnlyDirectoryImporter,
    normalized_roles,
    required_text,
)
from adg.control_plane.imports.models import ImportedUserRow


class WeComImporter(PullOnlyDirectoryImporter):
    """Normalize WeCom users plus department ids into the shared import batch."""

    platform = "wecom"

    def normalize(self, payload: Mapping[str, Any]) -> DirectoryImportBatch:
        department_names = payload.get("department_names")
        users = payload.get("users")
        if not isinstance(department_names, Mapping):
            raise ValueError("WeCom payload must include department_names")
        if not isinstance(users, list):
            raise ValueError("WeCom payload must include a users list")

        normalized_users: list[ImportedUserRow] = []
        for user in cast(list[Mapping[str, Any]], users):
            department_ids = user.get("department")
            if department_ids is None:
                org_path = None
            elif isinstance(department_ids, Sequence) and not isinstance(
                department_ids, (str, bytes, bytearray)
            ):
                segments = [
                    required_text(
                        department_names.get(str(department_id)),
                        field_name=f"department_names[{department_id}]",
                    )
                    for department_id in department_ids
                ]
                org_path = self.delimiter.join(segments) or None
            else:
                raise ValueError("WeCom user department must be a sequence")

            extattr = user.get("extattr")
            if extattr is None:
                extattr = {}
            if not isinstance(extattr, Mapping):
                raise ValueError("WeCom user extattr must be a mapping")

            normalized_users.append(
                ImportedUserRow(
                    user_name=required_text(user.get("name"), field_name="name"),
                    org_path=org_path,
                    external_ref=required_text(user.get("userid"), field_name="userid"),
                    roles=normalized_roles(extattr.get("roles")),
                )
            )

        return DirectoryImportBatch(users=normalized_users, delimiter=self.delimiter)
