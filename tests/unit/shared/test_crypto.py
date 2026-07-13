import base64

import pytest
from cryptography.fernet import InvalidToken
from pytest import MonkeyPatch

from adg.shared import crypto
from adg.shared.crypto import decrypt_fernet_envelope, encrypt_fernet_envelope


def valid_envelope() -> dict[str, object]:
    return encrypt_fernet_envelope(
        b"secret",
        secret="credential-key-for-tests-123",
        iterations=1_200,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("iterations", True),
        ("iterations", 999),
        ("iterations", 2_000_001),
        ("salt", "not-base64!"),
        ("salt", base64.urlsafe_b64encode(b"short-salt").decode()),
        ("version", 3),
    ],
)
def test_decrypt_fernet_envelope_rejects_untrusted_kdf_parameters(
    field: str,
    value: object,
) -> None:
    envelope = valid_envelope()
    envelope[field] = value

    with pytest.raises(InvalidToken):
        decrypt_fernet_envelope(
            envelope,
            secret="credential-key-for-tests-123",
        )


def test_decrypt_fernet_envelope_rejects_iterations_before_deriving_key(
    monkeypatch: MonkeyPatch,
) -> None:
    envelope = valid_envelope()
    envelope["iterations"] = 2_000_001

    def fail_if_derived(**kwargs: object) -> bytes:
        raise AssertionError("KDF must not run for an invalid envelope")

    monkeypatch.setattr(crypto, "derive_pbkdf2_fernet_key", fail_if_derived)

    with pytest.raises(InvalidToken):
        decrypt_fernet_envelope(
            envelope,
            secret="credential-key-for-tests-123",
        )
