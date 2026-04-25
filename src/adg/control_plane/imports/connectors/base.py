from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast

from adg.control_plane.imports.excel import normalize_org_path
from adg.control_plane.imports.models import ImportedUserRow


@dataclass(frozen=True, slots=True)
class DirectoryImportBatch:
    """Uniform batch returned by pull-only directory importer connectors."""

    users: list[ImportedUserRow]
    delimiter: str = "/"

    def to_rows(self) -> list[dict[str, object]]:
        return [
            {
                "user_name": user.user_name,
                "org_path": user.org_path,
                "external_ref": user.external_ref,
                "roles": list(user.roles),
            }
            for user in self.users
        ]


class DirectoryImporter(Protocol):
    """Pluggable pull-only importer contract for third-party directories."""

    platform: str

    def normalize(self, payload: Mapping[str, Any]) -> DirectoryImportBatch: ...

    def fetch(self, config: Mapping[str, Any]) -> DirectoryImportBatch: ...


class PullOnlyDirectoryImporter:
    """Base class that treats `config['payload']` as the fetched remote response seam."""

    platform = "unknown"
    delimiter = "/"

    def fetch(self, config: Mapping[str, Any]) -> DirectoryImportBatch:
        payload = config.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("Importer config must include a mapping payload")
        return self.normalize(cast(Mapping[str, Any], payload))


def normalized_path(value: Any, *, delimiter: str = "/") -> str | None:
    """Convert either a delimited string or a string sequence into one normalized path."""

    if value is None:
        return None
    if isinstance(value, str):
        segments = normalize_org_path(value, delimiter)
        return delimiter.join(segments) or None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        segments = [str(item).strip() for item in value if str(item).strip()]
        return delimiter.join(segments) or None
    raise ValueError("Organization path must be a string, sequence, or null")


def normalized_roles(value: Any) -> list[str]:
    """Normalize role values from strings, string lists, or `{name}` objects."""

    if value is None:
        return []
    candidates: list[str] = []
    if isinstance(value, str):
        candidates = value.split(",")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            if isinstance(item, Mapping):
                name = item.get("name")
                if name is not None:
                    candidates.append(str(name))
            else:
                candidates.append(str(item))
    else:
        raise ValueError("Roles must be a string, sequence, or null")

    roles: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized or normalized in seen:
            continue
        roles.append(normalized)
        seen.add(normalized)
    return roles


def required_text(value: Any, *, field_name: str) -> str:
    """Require a non-empty string field from a connector payload."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()
