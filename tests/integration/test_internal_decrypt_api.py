from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from adg.app.main import create_app
from adg.app.settings import get_settings
from adg.audit.models import AuditEvent
from adg.control_plane.db import create_engine_from_url, create_session_factory, get_session
from adg.control_plane.models import Base
from adg.control_plane.models.api_key import ApiKey
from adg.masking.service import MaskingService
from adg.shared.security import hash_api_key


def build_internal_app(
    *,
    expired: bool = False,
) -> tuple[TestClient, str, sessionmaker[Session]]:
    engine = create_engine_from_url("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            ApiKey(
                id="key_internal",
                name="internal",
                key_hash=hash_api_key("adg_internal"),
                status="active",
                scopes='["internal"]',
            )
        )
        service = MaskingService(session, secret_key=get_settings().secret_key)
        marker = service.mask_reversible_value(
            user_id="user-1",
            datasource_id="ds_1",
            query_id="qry_1",
            field_name="email",
            value="alice@example.com",
            expires_at=(
                datetime.now(UTC) - timedelta(seconds=1)
                if expired
                else datetime.now(UTC) + timedelta(minutes=5)
            ),
        )
        session.commit()

    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), marker, session_factory


def test_internal_decrypt_returns_plaintext_and_audits() -> None:
    client, marker, session_factory = build_internal_app()

    response = client.post(
        "/internal/decrypt",
        json={"user_id": "user-1", "values": [marker]},
        headers={"X-ADG-API-Key": "adg_internal"},
    )

    assert response.status_code == 200
    assert response.json() == {"values": ["alice@example.com"]}
    with session_factory() as session:
        event = session.execute(select(AuditEvent)).scalar_one()
    assert event.event_type == "decryption"
    assert event.decision == "allowed"


def test_internal_decrypt_rejects_expired_context() -> None:
    client, marker, _ = build_internal_app(expired=True)

    response = client.post(
        "/internal/decrypt",
        json={"user_id": "user-1", "values": [marker]},
        headers={"X-ADG-API-Key": "adg_internal"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Decrypt context expired"
