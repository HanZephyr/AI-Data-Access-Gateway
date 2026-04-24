from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from adg.masking.service import MaskingService
from adg.shared.errors import ValidationError

SECRET = "unit-test-secret-value"


def test_fixed_masking_uses_configured_replacement(db_session: Session) -> None:
    masked = MaskingService(db_session, secret_key=SECRET).mask_plain_value(
        "alice@example.com",
        strategy="fixed",
        config={"replacement": "REDACTED"},
    )

    assert masked == "REDACTED"


def test_partial_masking_preserves_prefix_and_suffix(db_session: Session) -> None:
    masked = MaskingService(db_session, secret_key=SECRET).mask_plain_value(
        "alice@example.com",
        strategy="partial",
        config={"prefix": 2, "suffix": 2, "fill": "#"},
    )

    assert masked is not None
    assert masked.startswith("al")
    assert masked.endswith("om")
    assert set(masked[2:-2]) == {"#"}


def test_hash_masking_is_deterministic_and_not_plaintext(db_session: Session) -> None:
    service = MaskingService(db_session, secret_key=SECRET)

    first = service.mask_plain_value("alice@example.com", strategy="hash", config={})
    second = service.mask_plain_value("alice@example.com", strategy="hash", config={})

    assert first is not None
    assert first == second
    assert first != "alice@example.com"
    assert len(first) == 64


def test_reversible_masking_creates_marker_and_decrypts(db_session: Session) -> None:
    service = MaskingService(db_session, secret_key=SECRET)

    marker = service.mask_reversible_value(
        user_id="user-1",
        datasource_id="ds_1",
        query_id="qry_1",
        field_name="email",
        value="alice@example.com",
    )
    plaintext = service.decrypt_values(
        user_id="user-1",
        values=[marker],
    )

    assert marker.startswith("$adg_rev$")
    assert plaintext == ["alice@example.com"]


def test_decrypt_rejects_expired_contexts(db_session: Session) -> None:
    service = MaskingService(db_session, secret_key=SECRET)
    marker = service.mask_reversible_value(
        user_id="user-1",
        datasource_id="ds_1",
        query_id="qry_1",
        field_name="email",
        value="alice@example.com",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    with pytest.raises(ValidationError, match="Decrypt context expired"):
        service.decrypt_values(user_id="user-1", values=[marker])
