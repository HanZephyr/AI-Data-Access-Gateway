from collections.abc import Mapping, Sequence
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

    def fetch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        payload = config.get("payload")
        if isinstance(payload, Mapping):
            return self.normalize(cast(Mapping[str, Any], payload))

        users_payload = config.get("users_payload")
        if not isinstance(users_payload, Mapping):
            raise ValueError("Feishu config must include users_payload")

        self.delimiter = str(config.get("delimiter") or "/").strip() or "/"
        departments = self._build_department_path_map(config.get("departments_payload"))
        users = self._extract_users(users_payload)

        return DirectoryImportBatch(
            users=[
                ImportedUserRow(
                    user_name=required_text(user.get("name"), field_name="name"),
                    org_path=self._resolve_org_path(user, departments),
                    external_ref=required_text(
                        user.get("user_id") or user.get("open_id"),
                        field_name="user_id",
                    ),
                    roles=normalized_roles(user.get("roles")),
                )
                for user in users
            ],
            delimiter=self.delimiter,
        )

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

    def _extract_users(self, payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        candidates = (
            payload.get("users"),
            payload.get("items"),
            payload.get("data"),
        )
        for candidate in candidates:
            if isinstance(candidate, list):
                return cast(list[Mapping[str, Any]], candidate)
            if isinstance(candidate, Mapping):
                items = candidate.get("items")
                if isinstance(items, list):
                    return cast(list[Mapping[str, Any]], items)
        raise ValueError("Feishu users payload must include a users/items list")

    def _build_department_path_map(self, payload: Any) -> dict[str, str]:
        if not isinstance(payload, Mapping):
            return {}

        departments = payload.get("items")
        if not isinstance(departments, list):
            data = payload.get("data")
            if isinstance(data, Mapping):
                departments = data.get("items")
        if not isinstance(departments, list):
            return {}

        records = cast(list[Mapping[str, Any]], departments)
        names = {
            str(record.get("open_department_id") or record.get("department_id")): required_text(
                record.get("name"),
                field_name="department.name",
            )
            for record in records
            if record.get("open_department_id") or record.get("department_id")
        }
        parents = {
            str(record.get("open_department_id") or record.get("department_id")): str(
                record.get("parent_department_id") or record.get("parent_id") or ""
            )
            for record in records
            if record.get("open_department_id") or record.get("department_id")
        }

        cache: dict[str, str] = {}

        def build_path(department_id: str) -> str:
            cached = cache.get(department_id)
            if cached is not None:
                return cached

            name = names.get(department_id)
            if name is None:
                return ""
            parent_id = parents.get(department_id) or ""
            if not parent_id or parent_id in {"0", department_id} or parent_id not in names:
                cache[department_id] = name
                return name
            parent_path = build_path(parent_id)
            path = self.delimiter.join([segment for segment in [parent_path, name] if segment])
            cache[department_id] = path
            return path

        return {department_id: build_path(department_id) for department_id in names}

    def _resolve_org_path(
        self,
        user: Mapping[str, Any],
        departments: Mapping[str, str],
    ) -> str | None:
        if user.get("department_path") is not None:
            return normalized_path(user.get("department_path"), delimiter=self.delimiter)

        department_ids = user.get("department_ids") or user.get("department_id_list")
        if not isinstance(department_ids, Sequence) or isinstance(
            department_ids, (str, bytes, bytearray)
        ):
            return None

        candidate_paths = [
            departments.get(str(department_id), "")
            for department_id in department_ids
            if str(department_id).strip()
        ]
        path = max(candidate_paths, key=len, default="")
        return path or None
