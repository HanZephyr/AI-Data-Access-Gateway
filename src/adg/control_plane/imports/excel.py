from collections.abc import Mapping, Sequence
from typing import Any

from adg.control_plane.imports.models import ImportedUserRow

REQUIRED_COLUMNS = ("user_name", "org_path", "external_ref", "roles")


def normalize_org_path(raw: str | None, delimiter: str) -> list[str]:
    """Split an org path string into normalized segments."""

    if raw is None:
        return []
    trimmed = raw.strip()
    if not trimmed:
        return []
    return [segment.strip() for segment in trimmed.split(delimiter) if segment.strip()]


def normalize_excel_import_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    delimiter: str = "/",
) -> list[ImportedUserRow]:
    """Normalize structured row data into reusable import models."""

    normalized_rows: list[ImportedUserRow] = []
    for index, row in enumerate(rows, start=1):
        _validate_required_columns(row, row_number=index)
        user_name = _require_text(row.get("user_name"), field_name="user_name", row_number=index)
        external_ref = _require_text(
            row.get("external_ref"),
            field_name="external_ref",
            row_number=index,
        )
        path_segments = normalize_org_path(_optional_text(row.get("org_path")), delimiter)
        normalized_rows.append(
            ImportedUserRow(
                user_name=user_name,
                org_path=delimiter.join(path_segments) or None,
                external_ref=external_ref,
                roles=_normalize_roles(row.get("roles"), row_number=index),
            )
        )
    return normalized_rows


def _validate_required_columns(row: Mapping[str, Any], *, row_number: int) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in row]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Row {row_number} is missing required columns: {missing}")


def _require_text(value: Any, *, field_name: str, row_number: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Row {row_number} field {field_name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("org_path must be a string or null")
    return value


def _normalize_roles(value: Any, *, row_number: int) -> list[str]:
    if value is None:
        return []
    candidates: list[str]
    if isinstance(value, str):
        candidates = value.split(",")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        candidates = [str(item) for item in value]
    else:
        raise ValueError(f"Row {row_number} field roles must be a string, list, or null")

    roles: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized or normalized in seen:
            continue
        roles.append(normalized)
        seen.add(normalized)
    return roles
