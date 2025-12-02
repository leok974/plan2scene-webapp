from pydantic import BaseModel
from typing import Optional, List


class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    scene_url: Optional[str] = None
    video_url: Optional[str] = None
    current_stage: Optional[str] = None


class RoomPreview(BaseModel):
    id: str
    type: Optional[str] = None
    polygon: List[List[float]]  # [[x, y], ...]
    height: float


class ScenePreviewResponse(BaseModel):
    job_id: str
    rooms: List[RoomPreview]
    bbox: List[float]  # [min_x, min_y, max_x, max_y]
