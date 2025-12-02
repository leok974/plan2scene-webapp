"""
Plan2Scene Pipeline Engine

Provides orchestration for different execution modes:
- Demo: Simulated pipeline with pre-rendered assets
- GPU (Preprocessed): Assumes preprocessed Rent3D++ data, runs texture propagation + rendering
- GPU (Full): Complete pipeline from R2V vectors through to final outputs
"""

import asyncio
import shutil
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from app.config import settings
from app.services.plan2scene_commands import run_plan2scene_command, Plan2SceneCommandError
from app.jobs import update_job

logger = logging.getLogger(__name__)


class PipelineMode(Enum):
    """Available pipeline execution modes."""
    DEMO = "demo"
    GPU_PREPROCESSED = "preprocessed"
    GPU_FULL = "full"


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    success: bool
    video_path: Optional[Path] = None
    model_path: Optional[Path] = None
    error_message: Optional[str] = None
    error_stage: Optional[str] = None


class Plan2SceneEngine:
    """
    Orchestrates Plan2Scene pipeline execution in different modes.
    """
    
    def __init__(self):
        self.mode = settings.MODE
        self.pipeline_mode = settings.PIPELINE_MODE
    
    async def run_pipeline(
        self,
        job_id: str,
        upload_path: Path,
        output_dir: Path,
        r2v_annotation: Optional[Path] = None
    ) -> PipelineResult:
        """
        Main entry point for pipeline execution.
        
        Routes to appropriate pipeline based on MODE and PIPELINE_MODE settings.
        
        Args:
            job_id: Unique job identifier
            upload_path: Path to uploaded floorplan image
            output_dir: Directory for pipeline outputs
            r2v_annotation: Optional R2V annotation file (for GPU_FULL mode)
        
        Returns:
            PipelineResult with execution details
        """
        logger.info(f"Starting pipeline for job {job_id} in mode={self.mode}, pipeline_mode={self.pipeline_mode}")
        
        try:
            if self.mode == "demo":
                return await self.run_demo_pipeline(output_dir)
            elif self.mode == "gpu":
                if self.pipeline_mode == "preprocessed":
                    return await self.run_gpu_pipeline_preprocessed(upload_path, output_dir)
                elif self.pipeline_mode == "full":
                    return await self.run_gpu_pipeline_full(job_id, upload_path, output_dir, r2v_annotation)
                else:
                    error_msg = f"Unknown pipeline mode: {self.pipeline_mode}"
                    logger.error(error_msg)
                    return PipelineResult(success=False, error_message=error_msg)
            else:
                error_msg = f"Unknown execution mode: {self.mode}"
                logger.error(error_msg)
                return PipelineResult(success=False, error_message=error_msg)
        
        except Plan2SceneCommandError as e:
            logger.error(f"Pipeline failed: {e}")
            return PipelineResult(
                success=False,
                error_message=str(e),
                error_stage=e.command[1] if len(e.command) > 1 else "unknown"
            )
        except Exception as e:
            logger.error(f"Unexpected pipeline error: {e}", exc_info=True)
            return PipelineResult(success=False, error_message=str(e))
    
    async def run_demo_pipeline(self, output_dir: Path) -> PipelineResult:
        """
        Run simulated pipeline using pre-rendered demo assets.
        
        Args:
            output_dir: Directory to copy demo assets into
        
        Returns:
            PipelineResult with paths to demo assets
        """
        logger.info("Running DEMO mode pipeline")
        await asyncio.sleep(4)  # Simulate processing time
        
        # Source paths (from Docker volume mount)
        demo_video = Path("/app/demo_assets/walkthrough.mp4")
        demo_model = Path("/app/demo_assets/scene.glb")
        
        video_dest = output_dir / "walkthrough.mp4"
        model_dest = output_dir / "scene.glb"
        
        try:
            if demo_video.exists():
                shutil.copy(demo_video, video_dest)
                logger.info(f"✓ Copied demo video to {video_dest}")
            else:
                logger.error(f"❌ Demo video not found at {demo_video}")
                video_dest.write_bytes(b"error")
            
            if demo_model.exists():
                shutil.copy(demo_model, model_dest)
                logger.info(f"✓ Copied demo model to {model_dest}")
            else:
                logger.error(f"❌ Demo model not found at {demo_model}")
                model_dest.write_bytes(b"error")
            
            return PipelineResult(
                success=True,
                video_path=video_dest if video_dest.exists() else None,
                model_path=model_dest if model_dest.exists() else None
            )
        
        except Exception as e:
            logger.error(f"❌ Error in demo pipeline: {e}")
            return PipelineResult(
                success=False,
                error_message=f"Demo pipeline failed: {e}"
            )
    
    async def run_gpu_pipeline_preprocessed(
        self,
        upload_path: Path,
        output_dir: Path
    ) -> PipelineResult:
        """
        Run GPU pipeline assuming preprocessed Rent3D++ data already exists.
        
        This is the existing behavior: runs texture propagation + rendering only.
        
        Args:
            upload_path: Path to uploaded floorplan (not used in preprocessed mode)
            output_dir: Directory for outputs
        
        Returns:
            PipelineResult with paths to generated assets
        """
        logger.info("Running GPU mode pipeline (preprocessed data)")
        
        # Validate Plan2Scene repository exists
        if not settings.PLAN2SCENE_ROOT.exists():
            error_msg = f"Plan2Scene repository not found at {settings.PLAN2SCENE_ROOT}"
            logger.error(error_msg)
            return PipelineResult(success=False, error_message=error_msg)
        
        try:
            # Step 1: Texture Propagation (GNN)
            await self._run_texture_propagation_preprocessed(upload_path, output_dir)
            
            # Step 2: Rendering
            await self._run_rendering_preprocessed(output_dir)
            
            # Verify outputs
            video_path = output_dir / "walkthrough.mp4"
            model_path = output_dir / "scene.glb"
            
            if not video_path.exists():
                logger.warning("walkthrough.mp4 not found after rendering, creating placeholder")
                video_path.write_text("GPU MODE: Rendering completed but video not found")
            
            if not model_path.exists():
                logger.warning("scene.glb not found after rendering, creating placeholder")
                model_path.write_text("GPU MODE: Rendering completed but GLB not found")
            
            return PipelineResult(
                success=True,
                video_path=video_path if video_path.exists() else None,
                model_path=model_path if model_path.exists() else None
            )
        
        except Plan2SceneCommandError as e:
            logger.error(f"GPU pipeline (preprocessed) failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in GPU pipeline (preprocessed): {e}", exc_info=True)
            return PipelineResult(success=False, error_message=str(e))
    
    async def _run_texture_propagation_preprocessed(
        self,
        upload_path: Path,
        output_dir: Path
    ):
        """Run texture propagation step (existing preprocessed behavior)."""
        texture_script = settings.PLAN2SCENE_ROOT / "code/scripts/plan2scene/texture_prop/gnn_texture_prop.py"
        
        if not texture_script.exists():
            raise FileNotFoundError(f"Texture propagation script not found at {texture_script}")
        
        args = [
            "python",
            str(texture_script),
            str(upload_path.parent),
            str(output_dir),
            "test",
            "--keep-existing-predictions"
        ]
        
        logger.info("Running texture propagation...")
        result = await asyncio.to_thread(run_plan2scene_command, args)
        logger.info(f"✓ Texture propagation completed")
    
    async def _run_rendering_preprocessed(self, output_dir: Path):
        """Run rendering step (existing preprocessed behavior)."""
        render_script = settings.PLAN2SCENE_ROOT / "code/scripts/plan2scene/render_house_jsons.py"
        
        if not render_script.exists():
            raise FileNotFoundError(f"Render script not found at {render_script}")
        
        args = [
            "python",
            str(render_script),
            str(output_dir / "archs"),
            "--scene-json"
        ]
        
        logger.info("Running rendering...")
        result = await asyncio.to_thread(run_plan2scene_command, args)
        logger.info(f"✓ Rendering completed")
    
    async def run_gpu_pipeline_full(
        self,
        job_id: str,
        upload_path: Path,
        output_dir: Path,
        r2v_annotation: Optional[Path] = None
    ) -> PipelineResult:
        """
        Run complete GPU pipeline from R2V vectors through to final outputs.
        
        Pipeline stages:
        1. Convert R2V output to scene.json (using r2v-to-plan2scene)
        2. Run full Plan2Scene preprocessing (embeddings, crops, textures, rendering)
        3. Copy final outputs to job output directory
        
        Args:
            job_id: Unique job identifier (for progress tracking)
            upload_path: Path to uploaded floorplan image
            output_dir: Directory for final outputs
            r2v_annotation: Optional R2V annotation file (required for full pipeline)
        
        Returns:
            PipelineResult with paths to generated assets
        """
        logger.info("Running GPU Full pipeline (R2V + complete Plan2Scene preprocessing)")
        
        # Validate required inputs
        if r2v_annotation is None:
            error_msg = (
                "GPU Full pipeline requires an R2V annotation file. "
                "Please provide the R2V output alongside the floorplan image."
            )
            logger.error(error_msg)
            return PipelineResult(success=False, error_message=error_msg)
        
        if not r2v_annotation.exists():
            error_msg = f"R2V annotation file not found: {r2v_annotation}"
            logger.error(error_msg)
            return PipelineResult(success=False, error_message=error_msg)
        
        # Validate Plan2Scene and R2V repositories
        if not settings.PLAN2SCENE_ROOT.exists():
            error_msg = f"Plan2Scene repository not found at {settings.PLAN2SCENE_ROOT}"
            logger.error(error_msg)
            return PipelineResult(success=False, error_message=error_msg)
        
        if not settings.R2V_TO_PLAN2SCENE_ROOT.exists():
            error_msg = f"R2V-to-Plan2Scene repository not found at {settings.R2V_TO_PLAN2SCENE_ROOT}"
            logger.error(error_msg)
            return PipelineResult(success=False, error_message=error_msg)
        
        try:
            # Import full pipeline modules
            from app.services.r2v_converter import (
                convert_r2v_to_scene_json,
                extract_house_id_from_scene_json
            )
            from app.services.preprocessing_pipeline import Plan2ScenePreprocessor
            
            # Stage 1: Convert R2V to scene.json
            logger.info("Stage 1: Converting R2V output to scene.json...")
            update_job(job_id, current_stage="convert_r2v")
            r2v_output_dir = output_dir / "r2v_conversion"
            r2v_output_dir.mkdir(parents=True, exist_ok=True)
            
            scene_json_path = await asyncio.to_thread(
                convert_r2v_to_scene_json,
                r2v_annotation,
                r2v_output_dir,
                scale_factor=0.08,
                r2v_annot=True
            )
            
            house_id = extract_house_id_from_scene_json(scene_json_path)
            logger.info(f"✓ Scene.json generated for house: {house_id}")
            
            # Stage 2: Run full Plan2Scene preprocessing
            logger.info("Stage 2: Running full Plan2Scene preprocessing pipeline...")
            update_job(job_id, current_stage="preprocessing")
            
            # Create a job-specific working directory for Plan2Scene processing
            # This avoids writing to the read-only mounted plan2scene repo
            job_data_dir = output_dir / "plan2scene_data"
            job_data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using job-specific data directory: {job_data_dir}")
            
            preprocessor = Plan2ScenePreprocessor(data_root=job_data_dir)
            
            pipeline_result = await asyncio.to_thread(
                preprocessor.run_full_pipeline,
                scene_json_path,
                house_id,
                split="test",
                drop=0.0
            )
            
            if not pipeline_result.success:
                error_msg = (
                    f"Preprocessing pipeline failed at stage: {pipeline_result.failed_stage}. "
                    f"Error: {pipeline_result.error_message}"
                )
                logger.error(error_msg)
                return PipelineResult(
                    success=False,
                    error_message=error_msg,
                    error_stage=pipeline_result.failed_stage
                )
            
            logger.info(f"✓ Full preprocessing pipeline completed successfully")
            
            # Stage 3: Copy final outputs to job output directory
            logger.info("Stage 3: Copying final outputs to job directory...")
            update_job(job_id, current_stage="finalizing")
            
            video_dest = output_dir / "walkthrough.mp4"
            model_dest = output_dir / "scene.glb"
            
            # Copy video if available
            if pipeline_result.rendered_video and pipeline_result.rendered_video.exists():
                shutil.copy(pipeline_result.rendered_video, video_dest)
                logger.info(f"✓ Copied video to {video_dest}")
            else:
                logger.warning("No rendered video found, creating placeholder")
                video_dest.write_text("GPU Full: Video rendering not yet implemented")
            
            # Copy or convert model
            if pipeline_result.final_scene_json and pipeline_result.final_scene_json.exists():
                # TODO: Convert scene.json to GLB format
                # For now, copy the scene.json as a placeholder
                shutil.copy(pipeline_result.final_scene_json, model_dest.with_suffix(".scene.json"))
                logger.info(f"✓ Copied scene.json to {model_dest.with_suffix('.scene.json')}")
                
                # Create placeholder GLB
                model_dest.write_text("GPU Full: GLB conversion not yet implemented. See .scene.json")
            else:
                logger.warning("No final scene.json found, creating placeholder")
                model_dest.write_text("GPU Full: Scene.json generation failed")
            
            return PipelineResult(
                success=True,
                video_path=video_dest if video_dest.exists() else None,
                model_path=model_dest if model_dest.exists() else None
            )
        
        except Plan2SceneCommandError as e:
            logger.error(f"GPU Full pipeline failed: {e}")
            return PipelineResult(
                success=False,
                error_message=str(e),
                error_stage=e.command[1] if len(e.command) > 1 else "unknown"
            )
        except Exception as e:
            logger.error(f"Unexpected error in GPU Full pipeline: {e}", exc_info=True)
            return PipelineResult(success=False, error_message=str(e))



# Legacy function for backward compatibility
async def run_plan2scene(
    job_id: str, 
    upload_path: Path, 
    output_dir: Path,
    r2v_path: Optional[Path] = None
):
    """
    Legacy entry point for Plan2Scene pipeline.
    
    Maintained for backward compatibility with existing worker.py.
    
    Args:
        job_id: Unique job identifier
        upload_path: Path to uploaded floorplan image
        output_dir: Directory for job outputs
        r2v_path: Optional path to R2V annotation file
    """
    engine = Plan2SceneEngine()
    result = await engine.run_pipeline(job_id, upload_path, output_dir, r2v_path)
    
    if not result.success:
        raise Exception(result.error_message or "Pipeline failed")

