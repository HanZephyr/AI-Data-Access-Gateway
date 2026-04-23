from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.audit.models import AuditEvent
from adg.audit.service import AuditService


def test_audit_service_records_event(db_session: Session) -> None:
    service = AuditService(db_session)

    event = service.record_event(
        tenant_id="default",
        user_id="u_123",
        api_key_id="key_123",
        event_type="metadata",
        decision="allow",
        datasource_id="ds_123",
        resource_ids=["res_1"],
        query_id=None,
        sql_text=None,
        reason=None,
        metadata={"tool": "list_datasources"},
    )
    db_session.commit()

    stored = db_session.execute(select(AuditEvent)).scalar_one()
    assert stored.id == event.id
    assert stored.tenant_id == "default"
    assert stored.event_type == "metadata"
    assert stored.resource_ids_json == "[\"res_1\"]"
    assert stored.metadata_json == "{\"tool\":\"list_datasources\"}"
