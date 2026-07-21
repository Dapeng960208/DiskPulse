# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from dependencies import CurrentUserDep, get_db, require_super_admin
from schemas.vendorEventDefinitionSchema import (
    AssociationType,
    ReviewStatus,
    StorageType,
    VendorEventDefinitionCreate,
    VendorEventDefinitionOut,
    VendorEventDefinitionPage,
    VendorEventDefinitionPatch,
    VendorEventDiscoveryOut,
)
from services import audit_service, vendorEventDefinitionService


router = APIRouter(
    prefix="/admin/vendor-event-definitions",
    tags=["vendor-event-definitions"],
    dependencies=[Depends(require_super_admin)],
)

DBDep = Annotated[Session, Depends(get_db)]
DefinitionId = Annotated[int, Path(ge=1)]
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Keyword = Annotated[str | None, Query(max_length=100)]


@router.get("", response_model=VendorEventDefinitionPage)
def list_definitions(
    _current_user: CurrentUserDep,
    db: DBDep,
    page: PageNumber = 1,
    size: PageSize = 20,
    storage_type: StorageType | None = None,
    association_type: AssociationType | None = None,
    keyword: Keyword = None,
    review_status: ReviewStatus | None = None,
) -> dict:
    return vendorEventDefinitionService.list_definition_page(
        db,
        page=page,
        size=size,
        storage_type=storage_type,
        association_type=association_type,
        keyword=keyword,
        review_status=review_status,
    )


@router.post(
    "",
    response_model=VendorEventDefinitionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_definition(
    payload: VendorEventDefinitionCreate,
    request: Request,
    response: Response,
    current_user: CurrentUserDep,
    db: DBDep,
) -> dict:
    result = vendorEventDefinitionService.create_definition(
        db,
        payload,
        audit_context=audit_service.audit_context_for_request(
            request,
            actor_user_id=current_user.id,
        ),
    )
    response.headers["Location"] = (
        f"/storage-pulse/api/admin/vendor-event-definitions/{result['id']}"
    )
    return result


@router.post("/discover", response_model=VendorEventDiscoveryOut)
def discover_definitions(
    request: Request,
    current_user: CurrentUserDep,
    db: DBDep,
) -> dict:
    return vendorEventDefinitionService.discover(
        db,
        audit_context=audit_service.audit_context_for_request(
            request,
            actor_user_id=current_user.id,
        ),
    )


@router.get("/{definition_id}", response_model=VendorEventDefinitionOut)
def get_definition(
    definition_id: DefinitionId,
    _current_user: CurrentUserDep,
    db: DBDep,
) -> dict:
    return vendorEventDefinitionService.get_definition_detail(db, definition_id)


@router.patch("/{definition_id}", response_model=VendorEventDefinitionOut)
def update_definition(
    definition_id: DefinitionId,
    payload: VendorEventDefinitionPatch,
    request: Request,
    current_user: CurrentUserDep,
    db: DBDep,
) -> dict:
    return vendorEventDefinitionService.update_definition(
        db,
        definition_id,
        payload,
        audit_context=audit_service.audit_context_for_request(
            request,
            actor_user_id=current_user.id,
        ),
    )


@router.delete(
    "/{definition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_definition(
    definition_id: DefinitionId,
    request: Request,
    current_user: CurrentUserDep,
    db: DBDep,
) -> Response:
    vendorEventDefinitionService.delete_definition(
        db,
        definition_id,
        audit_context=audit_service.audit_context_for_request(
            request,
            actor_user_id=current_user.id,
        ),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
