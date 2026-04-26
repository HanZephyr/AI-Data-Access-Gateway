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


class DingTalkImporter(PullOnlyDirectoryImporter):
    """Normalize DingTalk user payloads into the shared directory import batch."""

    platform = "dingtalk"

    def fetch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        payload = config.get("payload")
        if isinstance(payload, Mapping):
            return self.normalize(cast(Mapping[str, Any], payload))

        self.delimiter = str(config.get("delimiter") or "/").strip() or "/"
        users_payload = config.get("users_payload")
        if not isinstance(users_payload, Mapping):
            raise ValueError("DingTalk config must include users_payload")

        users = self._extract_users(users_payload)
        department_paths = self._extract_department_paths(config.get("departments_payload"))
        return DirectoryImportBatch(
            users=[
                ImportedUserRow(
                    user_name=required_text(user.get("name"), field_name="name"),
                    org_path=self._resolve_org_path(user, department_paths),
                    external_ref=required_text(user.get("userid"), field_name="userid"),
                    roles=normalized_roles(user.get("role_list") or user.get("roles")),
                )
                for user in users
            ],
            delimiter=self.delimiter,
        )

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

    def _extract_users(self, payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        result = payload.get("result")
        if isinstance(result, list):
            return cast(list[Mapping[str, Any]], result)
        if isinstance(result, Mapping):
            for key in ("users", "list"):
                candidate = result.get(key)
                if isinstance(candidate, list):
                    return cast(list[Mapping[str, Any]], candidate)
        for key in ("users", "userlist", "list"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return cast(list[Mapping[str, Any]], candidate)
        raise ValueError("DingTalk users payload must include a result.users/result.list list")

    def _extract_department_paths(self, payload: Any) -> dict[str, str]:
        if not isinstance(payload, Mapping):
            return {}

        departments = payload.get("departments")
        if not isinstance(departments, list):
            result = payload.get("result")
            if isinstance(result, list):
                departments = result
            elif isinstance(result, Mapping):
                departments = result.get("departments") or result.get("list")
        if not isinstance(departments, list):
            return {}

        records = cast(list[Mapping[str, Any]], departments)
        names = {
            str(
                record.get("dept_id") or record.get("dept_id_str") or record.get("id")
            ): required_text(record.get("name"), field_name="department.name")
            for record in records
            if record.get("dept_id") is not None or record.get("id") is not None
        }
        parents = {
            str(record.get("dept_id") or record.get("dept_id_str") or record.get("id")): str(
                record.get("parent_id") or record.get("parentid") or 0
            )
            for record in records
            if record.get("dept_id") is not None or record.get("id") is not None
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
        department_paths: Mapping[str, str],
    ) -> str | None:
        if user.get("dept_path") is not None:
            return normalized_path(user.get("dept_path"), delimiter=self.delimiter)

        department_ids = (
            user.get("dept_id_list")
            or user.get("dept_ids")
            or user.get("department")
        )
        if not isinstance(department_ids, Sequence) or isinstance(
            department_ids, (str, bytes, bytearray)
        ):
            return None

        candidate_paths = [
            department_paths.get(str(department_id), "")
            for department_id in department_ids
            if str(department_id).strip()
        ]
        path = max(candidate_paths, key=len, default="")
        return path or None
