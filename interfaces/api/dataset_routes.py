import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from uuid import UUID

from app.use_cases.manage_dataset import (
    delete_dataset,
    get_dataset,
    list_datasets,
)
from domain.entities.user import UserEntity
from domain.interfaces.dataset_repository import DatasetRepositoryInterface
from interfaces.api.dependencies import get_current_user, get_dataset_repo, storage_service
from interfaces.schemas.dataset import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["datasets"])


@router.get("/datasets")
def list_datasets_route(
    dataset_type: str = Query(...),
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    datasets = list_datasets(dataset_type, current_user.id, dataset_repo)

    return {
        "datasets": [
            {
                "id": str(d.id),
                "name": d.name,
                "format": d.format,
                "created_at": d.created_at,
            }
            for d in datasets
        ]
    }


@router.get("/datasets/{dataset_id}")
def get_dataset_route(
    dataset_id: UUID,
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> FileResponse:
    entity = get_dataset(dataset_id, current_user.id, dataset_repo)

    if not entity:
        raise HTTPException(status_code=404, detail="Dataset not found")

    file_path = storage_service.get_storage_path(entity.storage_key)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing")

    return FileResponse(path=file_path, media_type="text/csv", filename=f"{entity.name}.csv")


@router.delete("/datasets/{dataset_id}", response_model=MessageResponse)
def delete_dataset_route(
    dataset_id: UUID,
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
) -> dict:
    deleted = delete_dataset(dataset_id, current_user.id, dataset_repo, storage_service)

    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {"message": "Dataset deleted successfully"}


@router.get("/datasets/{dataset_id}/status")
def get_dataset_status(
    dataset_id: UUID,
    dataset_repo: DatasetRepositoryInterface = Depends(get_dataset_repo),
    current_user: UserEntity = Depends(get_current_user),
)-> dict:
    entity = dataset_repo.find_by_id_and_user(dataset_id, current_user.id)
    if not entity:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return {"dataset_id": dataset_id, "status": entity.status}
