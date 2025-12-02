from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class Job:
    job_id: str
    status: str = "processing"
    scene_url: Optional[str] = None
    video_url: Optional[str] = None
    current_stage: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


_jobs: Dict[str, Job] = {}


def create_job(job_id: str) -> Job:
    job = Job(job_id=job_id)
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def update_job(
    job_id: str, 
    *, 
    status: Optional[str] = None, 
    scene_url: Optional[str] = None, 
    video_url: Optional[str] = None,
    current_stage: Optional[str] = None
) -> Optional[Job]:
    job = _jobs.get(job_id)
    if not job:
        return None
    if status is not None:
        job.status = status
    if scene_url is not None:
        job.scene_url = scene_url
    if video_url is not None:
        job.video_url = video_url
    if current_stage is not None:
        job.current_stage = current_stage
    return job
