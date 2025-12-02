from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from uuid import uuid4
import logging
import json

from . import schemas
from .jobs import create_job, get_job
from .worker import process_job
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Plan2Scene Web Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / settings.UPLOAD_DIR
STATIC_DIR = BASE_DIR / "static"
JOBS_STATIC_DIR = BASE_DIR / settings.JOBS_DIR

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
JOBS_STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "mode": settings.MODE}


@app.get("/api/config")
def get_config():
    """Return current pipeline configuration for frontend."""
    return {
        "mode": settings.MODE,
        "pipeline_mode": settings.PIPELINE_MODE,
        "gpu_enabled": settings.plan2scene_gpu_enabled
    }


@app.post("/api/convert", response_model=schemas.JobCreateResponse)
async def create_conversion_job(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    r2v_annotation: UploadFile = File(None)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported.")

    job_id = uuid4().hex
    upload_path = UPLOAD_DIR / f"{job_id}_{file.filename}"

    # Save floorplan image file
    contents = await file.read()
    upload_path.write_bytes(contents)

    # Save R2V annotation file if provided
    r2v_path = None
    if r2v_annotation and r2v_annotation.filename:
        r2v_path = UPLOAD_DIR / f"{job_id}_r2v_annotation.txt"
        r2v_contents = await r2v_annotation.read()
        r2v_path.write_bytes(r2v_contents)
        logger.info(f"R2V annotation file saved: {r2v_path}")

    # Create job entry
    create_job(job_id)

    # Dispatch background task
    job_output_dir = JOBS_STATIC_DIR / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)
    
    background_tasks.add_task(process_job, job_id, upload_path, job_output_dir, r2v_path)

    return schemas.JobCreateResponse(job_id=job_id, status="processing")


@app.get("/api/jobs/{job_id}", response_model=schemas.JobStatusResponse)
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return schemas.JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        scene_url=job.scene_url,
        video_url=job.video_url,
        current_stage=job.current_stage,
    )


@app.get("/api/jobs/{job_id}/download/walkthrough")
async def download_walkthrough(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    video_path = JOBS_STATIC_DIR / job_id / "walkthrough.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename="plan2scene-walkthrough.mp4",
        headers={"Content-Disposition": "attachment; filename=plan2scene-walkthrough.mp4"}
    )


@app.get("/api/jobs/{job_id}/download/scene")
async def download_scene(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    model_path = JOBS_STATIC_DIR / job_id / "scene.glb"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model not found")
    
    return FileResponse(
        path=str(model_path),
        media_type="model/gltf-binary",
        filename="plan2scene-model.glb",
        headers={"Content-Disposition": "attachment; filename=plan2scene-model.glb"}
    )


@app.get("/api/jobs/{job_id}/scene", response_model=schemas.ScenePreviewResponse)
def get_job_scene_preview(job_id: str) -> schemas.ScenePreviewResponse:
    """
    Return a simplified, frontend-friendly representation of the Plan2Scene output
    for a given job. This does NOT expose textures, just room polygons + heights.
    """
    job_dir = JOBS_STATIC_DIR / job_id
    
    scene_path = (
        job_dir
        / "plan2scene_data"
        / "processed"
        / "vgg_crop_select"
        / "test"
        / "drop_0.0"
        / "archs"
        / "uploads.scene.json"
    )
    
    if not scene_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Scene JSON not found for job {job_id}",
        )
    
    data = json.loads(scene_path.read_text())
    arch = data.get("scene", {}).get("arch", {})
    rooms_raw = arch.get("rooms", [])
    elements = arch.get("elements", [])
    
    # Build a mapping of roomId -> floor points
    room_floors = {}
    for elem in elements:
        if elem.get("type") == "Floor" and "roomId" in elem and "points" in elem:
            room_id = elem["roomId"]
            # Points is a list containing a single polygon
            points = elem["points"]
            if isinstance(points, list) and len(points) > 0:
                room_floors[room_id] = points[0] if isinstance(points[0], list) and isinstance(points[0][0], (list, float, int)) else points
    
    rooms: list[schemas.RoomPreview] = []
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    
    for room in rooms_raw:
        room_id = room.get("id")
        if not room_id or room_id not in room_floors:
            continue
        
        # type
        room_type = None
        if isinstance(room.get("types"), list) and room["types"]:
            room_type = str(room["types"][0])
        
        raw_poly = room_floors[room_id]
        poly: list[list[float]] = []
        
        for pt in raw_poly:
            # Points are [x, y, z] where y is vertical (0), we want x and z for 2D
            if isinstance(pt, (list, tuple)) and len(pt) >= 3:
                x, z = float(pt[0]), float(pt[2])
                poly.append([x, z])
                min_x = min(min_x, x)
                min_y = min(min_y, z)
                max_x = max(max_x, x)
                max_y = max(max_y, z)
            elif isinstance(pt, dict) and "x" in pt and "z" in pt:
                x, z = float(pt["x"]), float(pt["z"])
                poly.append([x, z])
                min_x = min(min_x, x)
                min_y = min(min_y, z)
                max_x = max(max_x, x)
                max_y = max(max_y, z)
        
        if not poly:
            continue
        
        height = float(arch.get("defaults", {}).get("Wall", {}).get("height") or 2.8)
        
        rooms.append(
            schemas.RoomPreview(
                id=str(room_id),
                type=room_type,
                polygon=poly,
                height=height,
            )
        )
    
    if not rooms:
        raise HTTPException(
            status_code=400,
            detail=f"No rooms with polygons found for job {job_id}",
        )
    
    if min_x == float("inf"):
        min_x = min_y = 0.0
        max_x = max_y = 1.0
    
    bbox = [min_x, min_y, max_x, max_y]
    
    return schemas.ScenePreviewResponse(job_id=job_id, rooms=rooms, bbox=bbox)
