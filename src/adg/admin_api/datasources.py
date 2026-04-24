import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from adg.app.dependencies import AuthenticatedApiKey, require_admin_api_key
from adg.connectors.errors import ConnectorDependencyError, ConnectorOperationError
from adg.connectors.registry import get_connector_registry
from adg.control_plane.db import get_session
from adg.control_plane.models.datasource import Datasource
from adg.control_plane.services.datasource_service import DatasourceService
from adg.control_plane.services.metadata_scan_service import MetadataScanService
from adg.shared.errors import NotFoundError

router = APIRouter(prefix="/admin/datasources", tags=["admin"])


class DatasourceCreateRequest(BaseModel):
    name: str
    type: str
    config: dict[str, object]
    status: str = "active"


class DatasourceUpdateRequest(BaseModel):
    name: str | None = None
    config: dict[str, object] | None = None
    status: str | None = None


def _serialize_datasource(datasource: Datasource) -> dict[str, Any]:
    return {
        "id": datasource.id,
        "name": datasource.name,
        "type": datasource.type,
        "datasource_kind": datasource.datasource_kind,
        "config": json.loads(datasource.config_json),
        "status": datasource.status,
        "created_at": datasource.created_at.isoformat(),
        "updated_at": datasource.updated_at.isoformat(),
    }


@router.get("")
def list_datasources(
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> list[dict[str, Any]]:
    service = DatasourceService(session)
    return [_serialize_datasource(item) for item in service.list_datasources()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_datasource(
    payload: DatasourceCreateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    service = DatasourceService(session)
    datasource = service.create_datasource(
        name=payload.name,
        connector_type=payload.type,
        config=payload.config,
        status=payload.status,
    )
    session.commit()
    session.refresh(datasource)
    return _serialize_datasource(datasource)


@router.get("/{datasource_id}")
def get_datasource(
    datasource_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    service = DatasourceService(session)
    try:
        datasource = service.get_datasource(datasource_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return _serialize_datasource(datasource)


@router.patch("/{datasource_id}")
def update_datasource(
    datasource_id: str,
    payload: DatasourceUpdateRequest,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    service = DatasourceService(session)
    try:
        datasource = service.update_datasource(
            datasource_id=datasource_id,
            name=payload.name,
            status=payload.status,
            config=payload.config,
        )
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    session.commit()
    session.refresh(datasource)
    return _serialize_datasource(datasource)


@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_datasource(
    datasource_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    service = DatasourceService(session)
    try:
        service.delete_datasource(datasource_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{datasource_id}/test")
def test_datasource(
    datasource_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    service = DatasourceService(session)
    try:
        datasource = service.get_datasource(datasource_id)
        connector = get_connector_registry().create(datasource.type)
        connector.test_connection(datasource.config())
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (ConnectorDependencyError, ConnectorOperationError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return {"status": "ok"}


@router.post("/{datasource_id}/scan")
def scan_datasource(
    datasource_id: str,
    _: Annotated[AuthenticatedApiKey, Depends(require_admin_api_key)],
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, int | str]:
    datasource_service = DatasourceService(session)
    scan_service = MetadataScanService(session)
    try:
        datasource = datasource_service.get_datasource(datasource_id)
        connector = get_connector_registry().create(datasource.type)
        snapshot = connector.scan_metadata(datasource.config())
        counts = scan_service.replace_snapshot(datasource=datasource, snapshot=snapshot)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (ConnectorDependencyError, ConnectorOperationError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    session.commit()
    return {"status": "ok", **counts}
