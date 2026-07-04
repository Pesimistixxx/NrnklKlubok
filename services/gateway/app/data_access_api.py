"""Admin API: матрица доступа к классификациям документов."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.data_access import (
    allowed_classifications,
    checkboxes_to_matrix,
    public_data_access_config,
    save_data_access_matrix,
)
from app.request_context import role_from_request
from app.roles import get_role
from app.schemas import DataAccessOut, DataAccessUpdate

router = APIRouter(tags=["settings"])


@router.get("/settings/data-access", response_model=DataAccessOut)
async def get_data_access_settings(request: Request) -> DataAccessOut:
    role_id = role_from_request(request)
    payload = await public_data_access_config()
    payload["current_role"] = role_id
    payload["allowed_classifications"] = await allowed_classifications(role_id)
    return DataAccessOut(**payload)


@router.put("/settings/data-access", response_model=DataAccessOut)
async def put_data_access_settings(body: DataAccessUpdate, request: Request) -> DataAccessOut:
    role_id = role_from_request(request)
    role = get_role(role_id)
    if not role or not role.get("can_admin"):
        raise HTTPException(status_code=403, detail="Только администратор может менять матрицу доступа")
    updates = checkboxes_to_matrix(body.matrix)
    await save_data_access_matrix(updates)
    payload = await public_data_access_config()
    payload["current_role"] = role_id
    payload["allowed_classifications"] = await allowed_classifications(role_id)
    return DataAccessOut(**payload)
