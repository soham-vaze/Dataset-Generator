from pydantic import BaseModel


class DatasetResponse(BaseModel):
    message: str
    dataset_id: str


class MessageResponse(BaseModel):
    message: str
