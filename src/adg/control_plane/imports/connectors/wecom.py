import json
from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any, cast
from urllib import error, parse, request

from adg.control_plane.imports.connectors.base import (
    DirectoryImportBatch,
    PullOnlyDirectoryImporter,
    normalized_roles,
    required_text,
)
from adg.control_plane.imports.models import ImportedUserRow


class WeComImporter(PullOnlyDirectoryImporter):
    """Pull WeCom departments and members with corp credentials."""

    platform = "wecom"
    _base_url = "https://qyapi.weixin.qq.com/cgi-bin"

    def fetch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        payload = config.get("payload")
        if isinstance(payload, Mapping):
            return self.normalize(cast(Mapping[str, Any], payload))

        self.delimiter = str(config.get("delimiter") or "/").strip() or "/"
        required_text(config.get("corp_id"), field_name="corp_id")
        required_text(config.get("corp_secret"), field_name="corp_secret")
        return self._fetch_directory_batch(config)

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

            extattr = user.get("extattr") or {}
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

    def _fetch_directory_batch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        token = self._fetch_access_token(
            required_text(config.get("corp_id"), field_name="corp_id"),
            required_text(config.get("corp_secret"), field_name="corp_secret"),
        )
        root_department_id = str(config.get("root_department_id") or "1").strip() or "1"
        departments = self._fetch_departments(token, root_department_id)
        department_names = self._build_department_name_map(departments, root_department_id)
        users = self._fetch_users(token, [department["id"] for department in departments])
        return self.normalize({"department_names": department_names, "users": users})

    def _fetch_access_token(self, corp_id: str, corp_secret: str) -> str:
        body = self._request_json(
            f"{self._base_url}/gettoken",
            query={"corpid": corp_id, "corpsecret": corp_secret},
        )
        token = body.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise ValueError("WeCom token response did not include access_token")
        return token

    def _fetch_departments(self, token: str, root_department_id: str) -> list[dict[str, Any]]:
        queue: deque[str] = deque([root_department_id])
        visited: set[str] = set()
        departments: dict[str, dict[str, Any]] = {}

        while queue:
            department_id = queue.popleft()
            if department_id in visited:
                continue
            visited.add(department_id)
            body = self._request_json(
                f"{self._base_url}/department/list",
                query={"access_token": token, "id": department_id},
            )
            rows = body.get("department")
            if not isinstance(rows, list):
                raise ValueError("WeCom department response did not include department list")
            for row in cast(list[Mapping[str, Any]], rows):
                current_id = str(row.get("id") or "").strip()
                if not current_id or current_id in departments:
                    continue
                record = dict(row)
                departments[current_id] = record
                if current_id != department_id:
                    queue.append(current_id)

        return list(departments.values())

    def _fetch_users(self, token: str, department_ids: Sequence[str]) -> list[Mapping[str, Any]]:
        users: dict[str, Mapping[str, Any]] = {}
        for department_id in department_ids:
            body = self._request_json(
                f"{self._base_url}/user/list",
                query={
                    "access_token": token,
                    "department_id": str(department_id),
                    "fetch_child": "0",
                },
            )
            rows = body.get("userlist")
            if not isinstance(rows, list):
                raise ValueError("WeCom user response did not include userlist")
            for row in cast(list[Mapping[str, Any]], rows):
                user_id = str(row.get("userid") or "").strip()
                if not user_id:
                    continue
                if user_id not in users:
                    users[user_id] = row
                    continue
                merged = dict(users[user_id])
                existing_departments = list(merged.get("department") or [])
                current_departments = row.get("department")
                if isinstance(current_departments, Sequence) and not isinstance(
                    current_departments,
                    (str, bytes, bytearray),
                ):
                    merged["department"] = list({*existing_departments, *current_departments})
                users[user_id] = merged
        return list(users.values())

    def _request_json(
        self,
        url: str,
        *,
        query: Mapping[str, str],
    ) -> Mapping[str, Any]:
        full_url = f"{url}?{parse.urlencode(query)}"
        req = request.Request(full_url, method="GET")
        try:
            with request.urlopen(req, timeout=20) as response:
                return cast(Mapping[str, Any], json.loads(response.read().decode("utf-8")))
        except error.HTTPError as exc:  # pragma: no cover - exercised by integration only
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"WeCom API request failed: {detail or exc.reason}") from exc

    def _build_department_name_map(
        self,
        departments: Sequence[Mapping[str, Any]],
        root_department_id: str,
    ) -> dict[str, str]:
        name_by_id = {
            str(department.get("id")): required_text(
                department.get("name"),
                field_name="department.name",
            )
            for department in departments
            if department.get("id") is not None
        }
        parent_by_id = {
            str(department.get("id")): str(department.get("parentid") or 0)
            for department in departments
            if department.get("id") is not None
        }
        cache: dict[str, str] = {}

        def build_path(department_id: str) -> str:
            cached = cache.get(department_id)
            if cached is not None:
                return cached
            name = name_by_id.get(department_id)
            if name is None:
                return ""
            parent_id = parent_by_id.get(department_id) or ""
            if (
                not parent_id
                or parent_id in {"0", department_id}
                or department_id == root_department_id
                or parent_id not in name_by_id
            ):
                cache[department_id] = name
                return name
            parent_path = build_path(parent_id)
            path = self.delimiter.join([segment for segment in [parent_path, name] if segment])
            cache[department_id] = path
            return path

        return {department_id: build_path(department_id) for department_id in name_by_id}
