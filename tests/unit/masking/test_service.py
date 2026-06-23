import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from adg.connectors.base import QueryResult
from adg.control_plane.models.masking import DecryptContext, MaskingPolicy
from adg.control_plane.models.resource import Resource
from adg.masking.service import MaskingService
from adg.policy.runtime import IdentityContext
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


def test_reversible_masking_wraps_context_key_with_masking_encryption_key(
    db_session: Session,
) -> None:
    service = MaskingService(
        db_session,
        secret_key=SECRET,
        masking_encryption_key="masking-key-for-tests",
        kdf_iterations=1_200,
    )

    marker = service.mask_reversible_value(
        user_id="user-1",
        datasource_id="ds_1",
        query_id="qry_1",
        field_name="email",
        value="alice@example.com",
    )
    context = db_session.query(DecryptContext).one()
    envelope = json.loads(context.key_ciphertext)

    assert envelope["kind"] == "encrypted_secret"
    assert envelope["version"] == 2
    assert envelope["kdf"] == "pbkdf2-hmac-sha256"
    assert envelope["iterations"] == 1_200
    assert service.decrypt_values(user_id="user-1", values=[marker]) == ["alice@example.com"]


def test_reversible_decrypt_accepts_legacy_secret_key_wrapped_context(
    db_session: Session,
) -> None:
    temporary_key = Fernet.generate_key()
    ciphertext = Fernet(temporary_key).encrypt(b"legacy@example.com").decode()
    legacy_service_key = base64.urlsafe_b64encode(hashlib.sha256(SECRET.encode()).digest())
    db_session.add(
        DecryptContext(
            id="ctx_legacy",
            query_id="qry_legacy",
            user_id="user-1",
            datasource_id="ds_1",
            resource_ids_json="[]",
            key_ciphertext=Fernet(legacy_service_key).encrypt(temporary_key).decode(),
            allowed_fields_json='["email"]',
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )
    db_session.flush()

    plaintext = MaskingService(
        db_session,
        secret_key=SECRET,
        masking_encryption_key="masking-key-for-tests",
        kdf_iterations=1_200,
    ).decrypt_values(
        user_id="user-1",
        values=[f"$adg_rev$ctx_legacy${ciphertext}"],
    )

    assert plaintext == ["legacy@example.com"]


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


def test_group_scoped_masking_policy_does_not_match_runtime_identity(
    db_session: Session,
) -> None:
    db_session.add(
        Resource(
            id="res_customers",
            datasource_id="ds_1",
            parent_id=None,
            kind="relational_table",
            name="customers",
            path="warehouse.public.customers",
            display_name="customers",
            query_language="sql",
            metadata_json="{}",
        )
    )
    db_session.add(
        MaskingPolicy(
            resource_id="res_customers",
            field_name="email",
            strategy="fixed",
            config_json='{"replacement":"REDACTED"}',
            subject_type="group",
            subject_id="finance",
            status="active",
        )
    )
    db_session.flush()

    resource = db_session.get(Resource, "res_customers")
    assert resource is not None

    masked, masked_columns = MaskingService(
        db_session,
        secret_key=SECRET,
    ).apply_to_result(
        identity=IdentityContext(
            user_id="user-1",
            roles=["analyst"],
            groups=["finance"],
        ),
        datasource_id="ds_1",
        query_id="qry_1",
        resources=[resource],
        result=QueryResult(
            columns=[{"name": "email", "data_type": "string"}],
            rows=[{"email": "alice@example.com"}],
        ),
    )

    assert masked.rows == [{"email": "alice@example.com"}]
    assert masked_columns == []
