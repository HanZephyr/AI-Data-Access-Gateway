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

    def fetch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        payload = config.get("payload")
        if isinstance(payload, Mapping):
            return self.normalize(cast(Mapping[str, Any], payload))

        self.delimiter = str(config.get("delimiter") or "/").strip() or "/"
        departments_payload = config.get("departments_payload")
        users_payload = config.get("users_payload")
        if not isinstance(users_payload, Mapping):
            raise ValueError("WeCom config must include users_payload")

        department_names = self._extract_department_names(departments_payload)
        users = self._extract_users(users_payload)
        return self.normalize(
            {
                "department_names": department_names,
                "users": users,
            }
        )

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

    def _extract_users(self, payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        candidates = (
            payload.get("users"),
            payload.get("userlist"),
            payload.get("data"),
        )
        for candidate in candidates:
            if isinstance(candidate, list):
                return cast(list[Mapping[str, Any]], candidate)
            if isinstance(candidate, Mapping):
                userlist = candidate.get("userlist")
                if isinstance(userlist, list):
                    return cast(list[Mapping[str, Any]], userlist)
        raise ValueError("WeCom users payload must include a users/userlist list")

    def _extract_department_names(self, payload: Any) -> dict[str, str]:
        if isinstance(payload, Mapping):
            raw_map = payload.get("department_names")
            if isinstance(raw_map, Mapping):
                return {
                    str(key): required_text(value, field_name=f"department_names[{key}]")
                    for key, value in raw_map.items()
                }

            departments = payload.get("department")
            if not isinstance(departments, list):
                data = payload.get("data")
                if isinstance(data, Mapping):
                    departments = data.get("department")
            if isinstance(departments, list):
                return {
                    str(department.get("id")): required_text(
                        department.get("name"),
                        field_name="department.name",
                    )
                    for department in cast(list[Mapping[str, Any]], departments)
                    if department.get("id") is not None
                }

        raise ValueError("WeCom departments payload must include department_names or department")
