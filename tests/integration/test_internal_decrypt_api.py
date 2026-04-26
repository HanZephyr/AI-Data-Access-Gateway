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
from adg.control_plane.models.directory import Role, User, UserRole
from adg.control_plane.models.governance import ResourcePolicy
from adg.control_plane.models.resource import Resource
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
                id="key_runtime",
                name="runtime",
                key_hash=hash_api_key("adg_runtime"),
                user_id="user-1",
                status="active",
                scopes='["runtime"]',
            )
        )
        session.add(User(id="user-1", name="Alice", external_ref="u001", status="active"))
        session.add(Role(id="role_analyst", name="Analyst", status="active"))
        session.add(UserRole(user_id="user-1", role_id="role_analyst"))
        session.add(
            Resource(
                id="res_customers",
                datasource_id="ds_1",
                parent_id=None,
                kind="relational_table",
                name="customers",
                path="warehouse.public.customers",
                display_name="customers",
                query_language="sql",
                status="active",
                metadata_json="{}",
            )
        )
        session.add(
            ResourcePolicy(
                subject_type="user",
                subject_id="user-1",
                effect="allow",
                action="read",
                resource_id="res_customers",
                allow_decrypt=True,
                status="active",
            )
        )
        service = MaskingService(session, secret_key=get_settings().secret_key)
        marker = service.mask_reversible_value(
            user_id="user-1",
            datasource_id="ds_1",
            resource_ids=["res_customers"],
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


def test_runtime_decrypt_returns_plaintext_and_audits_resource_scope() -> None:
    client, marker, session_factory = build_internal_app()

    response = client.post(
        "/runtime/decrypt",
        json={"values": [marker]},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 200
    assert response.json() == {"values": ["alice@example.com"]}
    with session_factory() as session:
        event = session.execute(select(AuditEvent)).scalar_one()
    assert event.event_type == "decryption"
    assert event.decision == "allowed"
    assert event.datasource_id == "ds_1"
    assert event.resource_ids == ["res_customers"]


def test_runtime_decrypt_rejects_expired_context() -> None:
    client, marker, _ = build_internal_app(expired=True)

    response = client.post(
        "/runtime/decrypt",
        json={"values": [marker]},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Decrypt context expired"


def test_runtime_decrypt_rejects_when_user_lacks_decrypt_permission() -> None:
    client, marker, session_factory = build_internal_app()

    with session_factory() as session:
        policy = (
            session.query(ResourcePolicy)
            .filter(ResourcePolicy.resource_id == "res_customers")
            .one()
        )
        policy.allow_decrypt = False
        session.commit()

    response = client.post(
        "/runtime/decrypt",
        json={"values": [marker]},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Decrypt not allowed for this resource"


def test_runtime_decrypt_rejects_when_context_resource_no_longer_exists() -> None:
    client, marker, session_factory = build_internal_app()

    with session_factory() as session:
        resource = session.get(Resource, "res_customers")
        assert resource is not None
        session.delete(resource)
        session.commit()

    response = client.post(
        "/runtime/decrypt",
        json={"values": [marker]},
        headers={"X-ADG-API-Key": "adg_runtime"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Decrypt context references unavailable resource"
    with session_factory() as session:
        events = session.execute(select(AuditEvent).order_by(AuditEvent.created_at)).scalars().all()
    assert events[-1].event_type == "decryption"
    assert events[-1].decision == "denied"
    assert events[-1].resource_ids == ["res_customers"]
