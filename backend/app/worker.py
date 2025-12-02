import asyncio
from .services.plan2scene import run_plan2scene
from .jobs import update_job
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def process_job(job_id: str, upload_path: Path, output_dir: Path, r2v_path: Optional[Path] = None):
    """
    Background task to process the job.
    
    Args:
        job_id: Unique job identifier
        upload_path: Path to uploaded floorplan image
        output_dir: Directory for job outputs
        r2v_path: Optional path to R2V annotation file
    """
    try:
        update_job(job_id, status="processing")
        await run_plan2scene(job_id, upload_path, output_dir, r2v_path)
        
        # Assume output files are named standardly
        scene_url = f"/static/jobs/{job_id}/scene.glb"
        video_url = f"/static/jobs/{job_id}/walkthrough.mp4"
        
        update_job(job_id, status="done", scene_url=scene_url, video_url=video_url)
        logger.info(f"Job {job_id} completed successfully.")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        update_job(job_id, status="failed")
