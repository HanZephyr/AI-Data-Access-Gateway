from typing import Any, cast

import pytest

from adg.shared.errors import ValidationError
from adg.shared.secret_config import SecretConfigService


def test_secret_config_encrypts_reveals_and_redacts_password() -> None:
    service = SecretConfigService(
        credential_encryption_key="credential-key-for-tests-123",
        kdf_iterations=1_200,
    )

    protected = service.protect_persisted_config(
        {
            "host": "db",
            "database": "warehouse",
            "username": "alice",
            "password": "secret",
        }
    )

    password = cast(dict[str, Any], protected["password"])

    assert password["ciphertext"] != "secret"
    assert isinstance(password, dict)
    assert password["kind"] == "encrypted_secret"
    assert password["version"] == 2
    assert isinstance(password["salt"], str)
    assert password["kdf"] == "pbkdf2-hmac-sha256"
    assert password["iterations"] == 1_200
    assert isinstance(password["ciphertext"], str)
    assert service.reveal_runtime_config(protected)["password"] == "secret"
    assert service.redact_admin_config(protected)["password"] == {
        "kind": "secret_placeholder",
        "configured": True,
    }


def test_secret_config_preserves_previous_secret_when_password_missing_or_blank() -> None:
    service = SecretConfigService(
        credential_encryption_key="credential-key-for-tests-123",
        kdf_iterations=1_200,
    )
    previous = service.protect_persisted_config(
        {
            "host": "db",
            "database": "warehouse",
            "username": "alice",
            "password": "secret",
        }
    )

    omitted = service.protect_persisted_config(
        {
            "host": "db-replica",
            "database": "warehouse",
            "username": "alice",
        },
        previous=previous,
    )
    blank = service.protect_persisted_config(
        {
            "host": "db-replica",
            "database": "warehouse",
            "username": "alice",
            "password": "   ",
        },
        previous=previous,
    )

    assert omitted["password"] == previous["password"]
    assert blank["password"] == previous["password"]


def test_secret_config_can_read_legacy_sha256_envelope_and_rotates_on_reprotect() -> None:
    service = SecretConfigService(
        credential_encryption_key="credential-key-for-tests-123",
        kdf_iterations=1_200,
    )
    legacy = service._encrypt_secret_legacy_for_tests("legacy-secret")

    assert legacy["kind"] == "encrypted_secret"
    assert "version" not in legacy
    assert service.reveal_runtime_config({"password": legacy})["password"] == "legacy-secret"

    rotated = service.protect_persisted_config(
        {"password": service.reveal_runtime_config({"password": legacy})["password"]}
    )

    rotated_password = cast(dict[str, Any], rotated["password"])
    assert rotated_password["version"] == 2
    assert service.reveal_runtime_config(rotated)["password"] == "legacy-secret"


def test_secret_config_uses_random_salt_for_new_envelopes() -> None:
    service = SecretConfigService(
        credential_encryption_key="credential-key-for-tests-123",
        kdf_iterations=1_200,
    )

    first = cast(
        dict[str, Any], service.protect_persisted_config({"password": "same-secret"})["password"]
    )
    second = cast(
        dict[str, Any], service.protect_persisted_config({"password": "same-secret"})["password"]
    )

    assert first["version"] == 2
    assert second["version"] == 2
    assert first["salt"] != second["salt"]
    assert first["ciphertext"] != second["ciphertext"]


def test_secret_config_rejects_client_supplied_encrypted_envelope() -> None:
    service = SecretConfigService(
        credential_encryption_key="credential-key-for-tests-123",
        kdf_iterations=1_200,
    )
    protected = service.protect_persisted_config({"password": "secret"})

    with pytest.raises(ValidationError, match="Encrypted datasource secrets cannot be supplied"):
        service.protect_persisted_config({"password": protected["password"]})
