import json
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from adg.control_plane.models.datasource import Datasource
from adg.control_plane.models.resource import Resource, ResourceField
from adg.shared.errors import NotFoundError


class DatasourceService:
    """Owns datasource persistence and cleanup of datasource-owned snapshots."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_datasources(self) -> list[Datasource]:
        """Return datasources in creation order for stable admin-console tables."""

        return list(
            self._session.execute(select(Datasource).order_by(Datasource.created_at)).scalars()
        )

    def create_datasource(
        self,
        *,
        name: str,
        connector_type: str,
        config: dict[str, object],
        status: str = "active",
    ) -> Datasource:
        """Create a relational datasource record with compact JSON configuration."""

        datasource = Datasource(
            name=name,
            type=connector_type,
            datasource_kind="relational",
            config_json=json.dumps(config, separators=(",", ":")),
            status=status,
        )
        self._session.add(datasource)
        return datasource

    def get_datasource(self, datasource_id: str) -> Datasource:
        """Load a datasource or raise the domain-level not-found error."""

        datasource = self._session.get(Datasource, datasource_id)
        if datasource is None:
            raise NotFoundError("Datasource not found")
        return datasource

    def update_datasource(
        self,
        *,
        datasource_id: str,
        name: str | None,
        status: str | None,
        config: dict[str, object] | None,
    ) -> Datasource:
        """Apply partial datasource updates while preserving omitted fields."""

        datasource = self.get_datasource(datasource_id)
        if name is not None:
            datasource.name = name
        if status is not None:
            datasource.status = status
        if config is not None:
            datasource.config_json = json.dumps(config, separators=(",", ":"))
        datasource.updated_at = datetime.now(UTC)
        return datasource

    def delete_datasource(self, datasource_id: str) -> None:
        """Delete a datasource and all scanned metadata snapshots that depend on it."""

        datasource = self.get_datasource(datasource_id)
        self._session.execute(
            delete(ResourceField).where(ResourceField.datasource_id == datasource.id)
        )
        self._session.execute(delete(Resource).where(Resource.datasource_id == datasource.id))
        self._session.delete(datasource)
