import asyncio
import shutil
import subprocess
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)

async def run_plan2scene(job_id: str, upload_path: Path, output_dir: Path):
    """
    Wrapper logic for Plan2Scene.
    """
    logger.info(f"Starting job {job_id} in {settings.MODE} mode.")
    
    if settings.MODE == "demo":
        await _run_demo_mode(output_dir)
    elif settings.MODE == "gpu":
        await _run_gpu_mode(upload_path, output_dir)
    else:
        logger.error(f"Unknown mode: {settings.MODE}")
        raise ValueError(f"Unknown mode: {settings.MODE}")

async def _run_demo_mode(output_dir: Path):
    """
    Simulates processing by sleeping and copying demo assets.
    """
    logger.info("Running in DEMO mode. Sleeping for 4 seconds...")
    await asyncio.sleep(4)
    
    # Source paths (from the Docker volume mount)
    demo_video = Path("/app/demo_assets/walkthrough.mp4")
    demo_model = Path("/app/demo_assets/scene.glb")
    
    # Copy to the output directory (where frontend can see them)
    try:
        if demo_video.exists():
            shutil.copy(demo_video, output_dir / "walkthrough.mp4")
            logger.info(f"✓ Copied demo video to {output_dir}")
        else:
            logger.error(f"❌ Demo video not found at {demo_video}")
            (output_dir / "walkthrough.mp4").write_bytes(b"error")
            
        if demo_model.exists():
            shutil.copy(demo_model, output_dir / "scene.glb")
            logger.info(f"✓ Copied demo model to {output_dir}")
        else:
            logger.error(f"❌ Demo model not found at {demo_model}")
            (output_dir / "scene.glb").write_bytes(b"error")
            
    except Exception as e:
        logger.error(f"❌ ERROR copying demo assets: {e}")
        # Create dummy files so frontend doesn't crash
        (output_dir / "walkthrough.mp4").write_bytes(b"error")
        (output_dir / "scene.glb").write_bytes(b"error")
    
    logger.info("Demo mode completed.")

async def _run_gpu_mode(upload_path: Path, output_dir: Path):
    """
    Constructs and runs the real Plan2Scene subprocess commands.
    """
    logger.info("Running in GPU mode.")
    
    # Use the mounted path
    repo_path = Path("/app/plan2scene_core")
    
    # Check if mount exists and is not empty (basic check)
    if not repo_path.exists() or not any(repo_path.iterdir()):
        logger.error(f"Plan2Scene repo not found or empty at {repo_path}. Did you mount it?")
        raise FileNotFoundError(f"Plan2Scene repo not found at {repo_path}")

    try:
        # 1. Texture Propagation
        # Reference: python code/scripts/plan2scene/texture_prop/gnn_texture_prop.py ./data/input ./data/output test --keep-existing-predictions
        texture_script = repo_path / "code/scripts/plan2scene/texture_prop/gnn_texture_prop.py"
        
        if not texture_script.exists():
            raise FileNotFoundError(f"Texture propagation script not found at {texture_script}")
        
        cmd_texture = [
            "python",
            str(texture_script),
            str(upload_path.parent),  # Input directory
            str(output_dir),           # Output directory
            "test",
            "--keep-existing-predictions"
        ]
        
        logger.info(f"Executing Texture Propagation: {' '.join(cmd_texture)}")
        result = subprocess.run(
            cmd_texture,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(repo_path)
        )
        logger.info(f"Texture Propagation stdout: {result.stdout}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Texture Propagation failed with return code {e.returncode}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Texture Propagation error: {str(e)}")
        raise

    try:
        # 2. Render Video/Images
        # Reference: python code/scripts/plan2scene/render_house_jsons.py ./data/output/archs --scene-json
        render_script = repo_path / "code/scripts/plan2scene/render_house_jsons.py"
        
        if not render_script.exists():
            raise FileNotFoundError(f"Render script not found at {render_script}")
        
        cmd_render = [
            "python",
            str(render_script),
            str(output_dir / "archs"),  # Output architecture directory
            "--scene-json"
        ]
        
        logger.info(f"Executing Render: {' '.join(cmd_render)}")
        result = subprocess.run(
            cmd_render,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(repo_path)
        )
        logger.info(f"Render stdout: {result.stdout}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Render failed with return code {e.returncode}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Render error: {str(e)}")
        raise
    
    # Verify outputs were created
    if not (output_dir / "scene.glb").exists():
        logger.warning("scene.glb not found after rendering, creating placeholder")
        (output_dir / "scene.glb").write_text("GPU MODE: Rendering completed but GLB not found")
    if not (output_dir / "walkthrough.mp4").exists():
        logger.warning("walkthrough.mp4 not found after rendering, creating placeholder")
        (output_dir / "walkthrough.mp4").write_text("GPU MODE: Rendering completed but video not found")
