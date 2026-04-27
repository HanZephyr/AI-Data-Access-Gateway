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


class FeishuImporter(PullOnlyDirectoryImporter):
    """Pull Feishu organization and user data with app credentials."""

    platform = "feishu"
    _base_url = "https://open.feishu.cn/open-apis"

    def fetch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        payload = config.get("payload")
        if isinstance(payload, Mapping):
            return self.normalize(cast(Mapping[str, Any], payload))

        self.delimiter = str(config.get("delimiter") or "/").strip() or "/"
        required_text(config.get("app_id"), field_name="app_id")
        required_text(config.get("app_secret"), field_name="app_secret")
        return self._fetch_directory_batch(config)

    def normalize(self, payload: Mapping[str, Any]) -> DirectoryImportBatch:
        users = payload.get("users")
        if not isinstance(users, list):
            raise ValueError("Feishu payload must include a users list")
        return DirectoryImportBatch(
            users=[
                ImportedUserRow(
                    user_name=required_text(user.get("name"), field_name="name"),
                    org_path=normalized_path(user.get("department_path"), delimiter=self.delimiter),
                    external_ref=required_text(
                        user.get("user_id") or user.get("open_id"),
                        field_name="user_id",
                    ),
                    roles=normalized_roles(user.get("roles")),
                )
                for user in cast(list[Mapping[str, Any]], users)
            ],
            delimiter=self.delimiter,
        )

    def _fetch_directory_batch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        token = self._fetch_app_access_token(
            required_text(config.get("app_id"), field_name="app_id"),
            required_text(config.get("app_secret"), field_name="app_secret"),
        )
        root_department_id = str(config.get("root_department_id") or "0").strip() or "0"
        departments = self._fetch_departments(token, root_department_id)
        department_paths = self._build_department_path_map({"items": departments})
        department_ids = [
            root_department_id,
            *[record["open_department_id"] for record in departments],
        ]
        users = self._fetch_users(token, list(dict.fromkeys(department_ids)))

        return DirectoryImportBatch(
            users=[
                ImportedUserRow(
                    user_name=required_text(user.get("name"), field_name="name"),
                    org_path=self._resolve_org_path(user, department_paths),
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

    def _fetch_app_access_token(self, app_id: str, app_secret: str) -> str:
        body = self._request_json(
            f"{self._base_url}/auth/v3/app_access_token/internal",
            method="POST",
            payload={"app_id": app_id, "app_secret": app_secret},
        )
        token = body.get("app_access_token")
        if not isinstance(token, str) or not token.strip():
            raise ValueError("Feishu access token response did not include app_access_token")
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
            for item in self._paginate(
                f"{self._base_url}/contact/v3/departments/{department_id}/children",
                token,
                query={
                    "department_id_type": self._department_id_type(department_id),
                    "page_size": "50",
                },
            ):
                open_department_id = str(item.get("open_department_id") or "").strip()
                if not open_department_id or open_department_id in departments:
                    continue
                record = dict(item)
                record.setdefault("parent_department_id", department_id)
                departments[open_department_id] = record
                queue.append(open_department_id)

        return list(departments.values())

    def _fetch_users(self, token: str, department_ids: Sequence[str]) -> list[Mapping[str, Any]]:
        users: dict[str, Mapping[str, Any]] = {}
        for department_id in department_ids:
            for item in self._paginate(
                f"{self._base_url}/contact/v3/users/find_by_department",
                token,
                query={
                    "department_id": department_id,
                    "department_id_type": self._department_id_type(department_id),
                    "page_size": "50",
                },
            ):
                user_id = str(item.get("user_id") or item.get("open_id") or "").strip()
                if not user_id:
                    continue
                candidate_ids = item.get("department_ids")
                normalized_department_ids = [department_id]
                if isinstance(candidate_ids, Sequence) and not isinstance(
                    candidate_ids,
                    (str, bytes, bytearray),
                ):
                    normalized_department_ids = list(
                        dict.fromkeys(
                            [
                                str(candidate).strip()
                                for candidate in candidate_ids
                                if str(candidate).strip()
                            ]
                            + [department_id]
                        )
                    )
                row = dict(item)
                row["department_ids"] = normalized_department_ids
                if user_id not in users:
                    users[user_id] = row
                    continue
                merged = dict(users[user_id])
                existing = list(merged.get("department_ids") or [])
                merged["department_ids"] = list(dict.fromkeys(existing + normalized_department_ids))
                users[user_id] = merged
        return list(users.values())

    def _paginate(
        self,
        url: str,
        token: str,
        *,
        query: Mapping[str, str],
    ) -> list[Mapping[str, Any]]:
        page_token = ""
        items: list[Mapping[str, Any]] = []
        while True:
            params = dict(query)
            if page_token:
                params["page_token"] = page_token
            body = self._request_json(url, token=token, query=params)
            data = body.get("data")
            payload = data if isinstance(data, Mapping) else body
            batch = payload.get("items")
            if batch is None and set(payload.keys()).issubset({"has_more", "page_token"}):
                batch = []
            if not isinstance(batch, list):
                response_keys = sorted(str(key) for key in body.keys())
                payload_keys = (
                    sorted(str(key) for key in payload.keys())
                    if isinstance(payload, Mapping)
                    else []
                )
                detail = (
                    "Feishu directory response did not include an items list "
                    f"(response_keys={response_keys}, payload_keys={payload_keys}"
                )
                request_id = str(body.get("request_id") or "").strip()
                if request_id:
                    detail = f"{detail}, request_id={request_id}"
                detail = f"{detail})"
                raise ValueError(detail)
            items.extend(cast(list[Mapping[str, Any]], batch))
            if not payload.get("has_more"):
                return items
            next_token = payload.get("page_token")
            if not isinstance(next_token, str) or not next_token:
                return items
            page_token = next_token

    def _request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        token: str | None = None,
        query: Mapping[str, str] | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        full_url = url
        if query:
            full_url = f"{url}?{parse.urlencode(query)}"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(full_url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=20) as response:
                body = cast(Mapping[str, Any], json.loads(response.read().decode("utf-8")))
                self._raise_for_api_error(body)
                return body
        except error.HTTPError as exc:  # pragma: no cover - exercised by integration only
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"Feishu API request failed: {detail or exc.reason}") from exc

    def _raise_for_api_error(self, body: Mapping[str, Any]) -> None:
        code = body.get("code")
        if code in (None, 0, "0"):
            return
        message = str(body.get("msg") or body.get("message") or "unknown error").strip()
        detail = f"Feishu API error {code}: {message}"
        request_id = str(body.get("request_id") or "").strip()
        if request_id:
            detail = f"{detail} (request_id={request_id})"
        raise ValueError(detail)

    def _department_id_type(self, department_id: str) -> str:
        if department_id.strip() == "0":
            return "department_id"
        return "open_department_id"

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
        names: dict[str, str] = {}
        parents: dict[str, str] = {}
        for record in records:
            primary_id = str(
                record.get("department_id") or record.get("open_department_id") or ""
            ).strip()
            alternate_id = str(
                record.get("open_department_id") or record.get("department_id") or ""
            ).strip()
            if not primary_id and not alternate_id:
                continue
            name = required_text(record.get("name"), field_name="department.name")
            parent_id = str(
                record.get("parent_department_id") or record.get("parent_id") or ""
            ).strip()
            for department_id in {primary_id, alternate_id} - {""}:
                names[department_id] = name
                parents[department_id] = parent_id

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
