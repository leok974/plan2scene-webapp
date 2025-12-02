#!/usr/bin/env python3
"""
Smoke test for full GPU pipeline (MODE=gpu, PIPELINE_MODE=full).

This script exercises the complete Plan2Scene pipeline through the backend API
without requiring the UI. It creates a job, polls for completion, and verifies
that output files are generated.

Usage:
    # From host:
    docker compose exec backend python scripts/smoke_full_gpu_pipeline.py

    # Override defaults with env vars:
    docker compose exec -e SMOKE_API_BASE=http://localhost:8000 \
                        -e SMOKE_TIMEOUT=900 \
                        backend python scripts/smoke_full_gpu_pipeline.py

Environment variables:
    SMOKE_API_BASE: API base URL (default: http://localhost:8000)
    SMOKE_FLOORPLAN: Path to floorplan image (default: tests/fixtures/smoke_floorplan.png)
    SMOKE_R2V: Path to R2V annotation file (default: tests/fixtures/smoke_r2v.txt)
    SMOKE_TIMEOUT: Timeout in seconds (default: 600)
    SMOKE_POLL_INTERVAL: Polling interval in seconds (default: 5)
"""

import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("[SMOKE] ERROR: requests module not installed", file=sys.stderr)
    print("[SMOKE] Run: pip install requests", file=sys.stderr)
    sys.exit(1)


# Configuration
API_BASE = os.getenv("SMOKE_API_BASE", "http://localhost:8000")
TIMEOUT = int(os.getenv("SMOKE_TIMEOUT", "3600"))  # 60 minutes for full pipeline
POLL_INTERVAL = int(os.getenv("SMOKE_POLL_INTERVAL", "5"))

# Fixture paths (relative to backend directory)
BACKEND_DIR = Path(__file__).parent.parent
FLOORPLAN_PATH = Path(os.getenv("SMOKE_FLOORPLAN", BACKEND_DIR / "tests/fixtures/smoke_floorplan.png"))
R2V_PATH = Path(os.getenv("SMOKE_R2V", BACKEND_DIR / "tests/fixtures/smoke_r2v.txt"))

# Static files root (matches main.py StaticFiles mount)
STATIC_ROOT = BACKEND_DIR / "static"


def resolve_static_path(url: str) -> Path:
    """
    Convert a /static/jobs/... URL into a filesystem path.
    
    Args:
        url: URL like "/static/jobs/{job_id}/scene.glb"
    
    Returns:
        Path object pointing to the actual file on disk
    """
    parsed = urlparse(url)
    path = parsed.path
    
    # Remove leading '/static/' prefix
    if path.startswith("/static/"):
        path = path[len("/static/"):]
    
    return STATIC_ROOT / path


def print_header(msg: str):
    """Print a formatted header message."""
    print(f"\n{'=' * 70}")
    print(f"[SMOKE] {msg}")
    print('=' * 70)


def print_step(msg: str):
    """Print a step message."""
    print(f"[SMOKE] {msg}")


def print_error(msg: str):
    """Print an error message to stderr."""
    print(f"[SMOKE] ERROR: {msg}", file=sys.stderr)


def main() -> int:
    """
    Main smoke test logic.
    
    Returns:
        Exit code: 0 for success, non-zero for failure
    """
    print_header("Full GPU Pipeline Smoke Test")
    print_step(f"API Base: {API_BASE}")
    print_step(f"Timeout: {TIMEOUT}s")
    print_step(f"Poll Interval: {POLL_INTERVAL}s")
    
    # Step 1: Verify fixtures exist
    print_header("Step 1: Verify Fixtures")
    
    if not FLOORPLAN_PATH.exists():
        print_error(f"Floorplan not found: {FLOORPLAN_PATH}")
        return 1
    print_step(f"✓ Floorplan found: {FLOORPLAN_PATH} ({FLOORPLAN_PATH.stat().st_size} bytes)")
    
    if not R2V_PATH.exists():
        print_error(f"R2V annotation not found: {R2V_PATH}")
        return 1
    print_step(f"✓ R2V annotation found: {R2V_PATH} ({R2V_PATH.stat().st_size} bytes)")
    
    # Step 2: Check API health
    print_header("Step 2: Check API Health")
    
    try:
        health_resp = requests.get(f"{API_BASE}/healthz", timeout=10)
        health_resp.raise_for_status()
        health_data = health_resp.json()
        print_step(f"✓ API is healthy")
        print_step(f"  Status: {health_data.get('status')}")
        print_step(f"  Mode: {health_data.get('mode')}")
    except Exception as e:
        print_error(f"API health check failed: {e}")
        return 2
    
    # Step 3: Check pipeline configuration
    print_header("Step 3: Check Pipeline Configuration")
    
    try:
        config_resp = requests.get(f"{API_BASE}/api/config", timeout=10)
        config_resp.raise_for_status()
        config_data = config_resp.json()
        mode = config_data.get('mode')
        pipeline_mode = config_data.get('pipeline_mode')
        
        print_step(f"✓ Configuration retrieved")
        print_step(f"  MODE: {mode}")
        print_step(f"  PIPELINE_MODE: {pipeline_mode}")
        
        if mode != 'gpu':
            print_error(f"Expected MODE=gpu, got MODE={mode}")
            print_error("This smoke test requires GPU mode")
            return 3
        
        if pipeline_mode != 'full':
            print_error(f"Expected PIPELINE_MODE=full, got PIPELINE_MODE={pipeline_mode}")
            print_error("This smoke test requires full pipeline mode")
            return 4
            
    except Exception as e:
        print_error(f"Configuration check failed: {e}")
        return 5
    
    # Step 4: Create job
    print_header("Step 4: Create Job")
    
    try:
        files = {
            "file": ("smoke_floorplan.png", FLOORPLAN_PATH.read_bytes(), "image/png"),
            "r2v_annotation": ("smoke_r2v.txt", R2V_PATH.read_bytes(), "text/plain")
        }
        
        create_resp = requests.post(f"{API_BASE}/api/convert", files=files, timeout=30)
        create_resp.raise_for_status()
        create_data = create_resp.json()
        
        job_id = create_data.get("job_id")
        status = create_data.get("status")
        
        if not job_id:
            print_error("Job creation response missing job_id")
            return 6
        
        print_step(f"✓ Job created: {job_id}")
        print_step(f"  Initial status: {status}")
        
    except Exception as e:
        print_error(f"Job creation failed: {e}")
        return 7
    
    # Step 5: Poll for completion
    print_header("Step 5: Poll Job Status")
    
    start_time = time.time()
    deadline = start_time + TIMEOUT
    last_status = None
    last_current_stage = None
    poll_count = 0
    last_log_time = start_time
    
    while time.time() < deadline:
        try:
            status_resp = requests.get(f"{API_BASE}/api/jobs/{job_id}", timeout=10)
            status_resp.raise_for_status()
            job_data = status_resp.json()
            
            status = job_data.get("status")
            current_stage = job_data.get("current_stage")
            scene_url = job_data.get("scene_url")
            video_url = job_data.get("video_url")
            
            poll_count += 1
            current_time = time.time()
            elapsed = int(current_time - start_time)
            
            # Print status updates when something changes or every 60 seconds
            should_log = (
                status != last_status or 
                current_stage != last_current_stage or
                (current_time - last_log_time) >= 60
            )
            
            if should_log:
                if current_stage:
                    print_step(f"t={elapsed}s status={status} stage={current_stage}")
                else:
                    print_step(f"t={elapsed}s status={status}")
                last_status = status
                last_current_stage = current_stage
                last_log_time = current_time
            
            # Check for completion
            if status == "done":
                elapsed_total = int(time.time() - start_time)
                print_header("SUCCESS")
                print_step(f"Full GPU pipeline completed in {elapsed_total} seconds")
                
                if scene_url:
                    print_step(f"scene_url={scene_url}")
                if video_url:
                    print_step(f"video_url={video_url}")
                if scene_url:
                    print_step(f"scene_url={scene_url}")
                if video_url:
                    print_step(f"video_url={video_url}")
                
                print_header("Step 6: Verify Output Files")
                
                if not scene_url:
                    print_error("Job completed but scene_url is missing")
                    return 8
                
                if not video_url:
                    print_error("Job completed but video_url is missing")
                    return 9
                
                print_step(f"✓ Scene URL: {scene_url}")
                print_step(f"✓ Video URL: {video_url}")
                
                # Verify files exist on disk
                scene_path = resolve_static_path(scene_url)
                video_path = resolve_static_path(video_url)
                
                scene_exists = scene_path.exists()
                video_exists = video_path.exists()
                
                print_step(f"  Scene file exists: {scene_exists} ({scene_path})")
                if scene_exists:
                    print_step(f"    Size: {scene_path.stat().st_size} bytes")
                
                print_step(f"  Video file exists: {video_exists} ({video_path})")
                if video_exists:
                    print_step(f"    Size: {video_path.stat().st_size} bytes")
                
                if not scene_exists:
                    print_error(f"Scene file not found: {scene_path}")
                    return 10
                
                if not video_exists:
                    print_error(f"Video file not found: {video_path}")
                    return 11
                
                # SUCCESS
                print_header("FULL GPU PIPELINE: PASS ✓")
                print_step(f"Job {job_id} completed successfully")
                print_step(f"All output files verified")
                return 0
            
            # Check for failure
            if status == "failed":
                elapsed_total = int(time.time() - start_time)
                print_header("FAIL")
                print_step(f"status=failed after {elapsed_total}s")
                if current_stage:
                    print_step(f"stage={current_stage}")
                
                # Extract error details from job data
                error_msg = job_data.get("error") or job_data.get("error_message") or "Unknown error"
                print_error(f"error={error_msg}")
                print_error(f"Full job data: {job_data}")
                return 1
            
        except requests.RequestException as e:
            print_error(f"Polling failed: {e}")
            # Continue polling unless it's a persistent error
            if time.time() + POLL_INTERVAL >= deadline:
                return 13
        
        # Wait before next poll
        time.sleep(POLL_INTERVAL)
    
    # Timeout
    elapsed_total = int(time.time() - start_time)
    print_header("TIMEOUT")
    print_step(f"Full GPU pipeline did not finish within {TIMEOUT}s")
    print_step(f"Actual elapsed: {elapsed_total}s")
    print_step(f"Last status: {last_status}")
    if last_current_stage:
        print_step(f"Last stage: {last_current_stage}")
    return 2


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_error("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(99)
