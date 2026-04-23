import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from adg.audit.models import AuditEvent


class AuditService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_event(
        self,
        *,
        tenant_id: str,
        user_id: Optional[str],
        api_key_id: Optional[str],
        event_type: str,
        decision: str,
        datasource_id: Optional[str],
        resource_ids: list[str],
        query_id: Optional[str],
        sql_text: Optional[str],
        reason: Optional[str],
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
