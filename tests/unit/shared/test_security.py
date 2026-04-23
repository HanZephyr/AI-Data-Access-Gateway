from adg.shared.security import generate_api_key, hash_api_key, verify_api_key


def test_generate_api_key_uses_adg_prefix() -> None:
    raw_key = generate_api_key()

    assert raw_key.startswith("adg_")
    assert len(raw_key) > 32


def test_hash_and_verify_api_key() -> None:
    raw_key = "adg_test_secret"
    hashed = hash_api_key(raw_key)

    assert hashed != raw_key
    assert verify_api_key(raw_key, hashed)
    assert not verify_api_key("adg_wrong_secret", hashed)
