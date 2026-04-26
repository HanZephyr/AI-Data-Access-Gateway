import json
from typing import Any

from sqlalchemy.orm import Session

from adg.audit.models import AuditEvent


class AuditService:
    """Writes audit events using the caller-owned SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record_event(
        self,
        *,
        user_id: str | None,
        api_key_id: str | None,
        event_type: str,
        decision: str,
        datasource_id: str | None,
        resource_ids: list[str],
        query_id: str | None,
        sql_text: str | None,
        reason: str | None,
        metadata: dict[str, Any],
    ) -> AuditEvent:
        """Create an audit event row without committing the surrounding transaction."""

        event = AuditEvent(
            user_id=user_id,
            api_key_id=api_key_id,
            event_type=event_type,
            datasource_id=datasource_id,
            resource_ids_json=json.dumps(resource_ids, separators=(",", ":")),
            query_id=query_id,
            sql_text=sql_text,
            decision=decision,
            reason=reason,
            metadata_json=json.dumps(metadata, separators=(",", ":")),
        )
        self._session.add(event)
        return event

    def record_sql_view(
        self,
        *,
        api_key_id: str | None,
        user_id: str | None,
        target_event: AuditEvent,
    ) -> AuditEvent:
        """Record that an operator opened the raw SQL detail for one audit event."""

        return self.record_event(
            user_id=user_id,
            api_key_id=api_key_id,
            event_type="audit_sql_view",
            decision="allowed",
            datasource_id=target_event.datasource_id,
            resource_ids=target_event.resource_ids,
            query_id=target_event.query_id,
            sql_text=None,
            reason=None,
            metadata={"target_event_id": target_event.id},
        )
