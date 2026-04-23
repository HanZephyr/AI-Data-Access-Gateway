import json
from typing import Any

from sqlalchemy.orm import Session

from adg.audit.models import AuditEvent


class AuditService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_event(
        self,
        *,
        tenant_id: str,
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
        event = AuditEvent(
            tenant_id=tenant_id,
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
