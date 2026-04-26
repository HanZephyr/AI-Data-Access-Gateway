import json
from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any, cast
from urllib import error, parse, request

from adg.control_plane.imports.connectors.base import (
    DirectoryImportBatch,
    PullOnlyDirectoryImporter,
    normalized_path,
    normalized_roles,
    required_text,
)
from adg.control_plane.imports.models import ImportedUserRow


class DingTalkImporter(PullOnlyDirectoryImporter):
    """Pull DingTalk departments and users with app credentials."""

    platform = "dingtalk"
    _base_url = "https://oapi.dingtalk.com"

    def fetch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        payload = config.get("payload")
        if isinstance(payload, Mapping):
            return self.normalize(cast(Mapping[str, Any], payload))

        self.delimiter = str(config.get("delimiter") or "/").strip() or "/"
        required_text(config.get("app_key"), field_name="app_key")
        required_text(config.get("app_secret"), field_name="app_secret")
        return self._fetch_directory_batch(config)

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

    def _fetch_directory_batch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        token = self._fetch_access_token(
            required_text(config.get("app_key"), field_name="app_key"),
            required_text(config.get("app_secret"), field_name="app_secret"),
        )
        root_department_id = str(config.get("root_department_id") or "1").strip() or "1"
        departments = self._fetch_departments(token, root_department_id)
        department_paths = self._extract_department_paths({"result": departments})
        users = self._fetch_users(token, [record["dept_id"] for record in departments])
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

    def _fetch_access_token(self, app_key: str, app_secret: str) -> str:
        body = self._request_json(
            f"{self._base_url}/gettoken",
            method="GET",
            query={"appkey": app_key, "appsecret": app_secret},
        )
        token = body.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise ValueError("DingTalk token response did not include access_token")
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
                method="GET",
                query={
                    "access_token": token,
                    "id": department_id,
                    "fetch_child": "false",
                },
            )
            rows = body.get("department")
            if not isinstance(rows, list):
                raise ValueError("DingTalk department response did not include department list")
            for row in cast(list[Mapping[str, Any]], rows):
                current_id = str(row.get("id") or row.get("dept_id") or "").strip()
                if not current_id or current_id in departments:
                    continue
                record = {
                    "dept_id": current_id,
                    "name": row.get("name"),
                    "parent_id": row.get("parentid") or row.get("parent_id") or department_id,
                }
                departments[current_id] = record
                if current_id != department_id:
                    queue.append(current_id)

        return list(departments.values())

    def _fetch_users(self, token: str, department_ids: Sequence[str]) -> list[Mapping[str, Any]]:
        users: dict[str, Mapping[str, Any]] = {}
        for department_id in department_ids:
            offset = 0
            while True:
                body = self._request_json(
                    f"{self._base_url}/user/listbypage",
                    method="GET",
                    query={
                        "access_token": token,
                        "department_id": str(department_id),
                        "offset": str(offset),
                        "size": "100",
                    },
                )
                rows = body.get("userlist")
                if not isinstance(rows, list):
                    raise ValueError("DingTalk user response did not include userlist")
                for row in cast(list[Mapping[str, Any]], rows):
                    user_id = str(row.get("userid") or "").strip()
                    if not user_id:
                        continue
                    if user_id not in users:
                        users[user_id] = row
                        continue
                    merged = dict(users[user_id])
                    existing = list(merged.get("dept_id_list") or merged.get("department") or [])
                    current = row.get("department") or row.get("dept_id_list")
                    if isinstance(current, Sequence) and not isinstance(
                        current,
                        (str, bytes, bytearray),
                    ):
                        merged["dept_id_list"] = list({*existing, *current})
                    users[user_id] = merged
                if not body.get("hasMore"):
                    break
                offset += len(rows)
        return list(users.values())

    def _request_json(
        self,
        url: str,
        *,
        method: str,
        query: Mapping[str, str],
    ) -> Mapping[str, Any]:
        full_url = f"{url}?{parse.urlencode(query)}"
        req = request.Request(full_url, method=method)
        try:
            with request.urlopen(req, timeout=20) as response:
                return cast(Mapping[str, Any], json.loads(response.read().decode("utf-8")))
        except error.HTTPError as exc:  # pragma: no cover - exercised by integration only
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"DingTalk API request failed: {detail or exc.reason}") from exc

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
