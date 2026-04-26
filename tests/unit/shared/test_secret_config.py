from adg.shared.secret_config import SecretConfigService


def test_secret_config_encrypts_reveals_and_redacts_password() -> None:
    service = SecretConfigService(credential_encryption_key="credential-key-for-tests-123")

    protected = service.protect_persisted_config(
        {
            "host": "db",
            "database": "warehouse",
            "username": "alice",
            "password": "secret",
        }
    )

    password = protected["password"]

    assert password != "secret"
    assert isinstance(password, dict)
    assert password == {
        "kind": "encrypted_secret",
        "ciphertext": password["ciphertext"],
    }
    assert service.reveal_runtime_config(protected)["password"] == "secret"
    assert service.redact_admin_config(protected)["password"] == {
        "kind": "secret_placeholder",
        "configured": True,
    }


def test_secret_config_preserves_previous_secret_when_password_missing_or_blank() -> None:
    service = SecretConfigService(credential_encryption_key="credential-key-for-tests-123")
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
