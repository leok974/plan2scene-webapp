from pydantic import BaseModel
from typing import Optional


class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    scene_url: Optional[str] = None
    video_url: Optional[str] = None
