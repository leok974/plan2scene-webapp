"""
Plan2Scene Full Pipeline - Preprocessing Stages

Implements the complete Plan2Scene preprocessing pipeline stages:
1. Room embeddings (texture_gen)
2. VGG crop selection
3. GNN texture propagation
4. Seam correction
5. Texture embedding
6. Rendering (PNG previews + video)
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from app.config import settings
from app.services.plan2scene_commands import run_plan2scene_command, Plan2SceneCommandError
from app.jobs import update_job

logger = logging.getLogger(__name__)


@dataclass
class PipelineStageResult:
    """Result of a single pipeline stage."""
    stage_name: str
    success: bool
    output_dir: Optional[Path] = None
    error_message: Optional[str] = None


@dataclass
class FullPipelineResult:
    """Result of the complete preprocessing pipeline."""
    success: bool
    house_id: str
    final_scene_json: Optional[Path] = None
    rendered_images: List[Path] = None
    rendered_video: Optional[Path] = None
    stage_results: List[PipelineStageResult] = None
    error_message: Optional[str] = None
    failed_stage: Optional[str] = None
    
    def __post_init__(self):
        if self.rendered_images is None:
            self.rendered_images = []
        if self.stage_results is None:
            self.stage_results = []


class Plan2ScenePreprocessor:
    """
    Orchestrates the full Plan2Scene preprocessing pipeline.
    
    Based on Plan2Scene README "Inference on Rent3D++ dataset" section.
    """
    
    def __init__(self, data_root: Optional[Path] = None):
        """
        Initialize preprocessor with data root directory.
        
        Args:
            data_root: Plan2Scene data directory (defaults to settings.plan2scene_data_root)
        """
        self.data_root = data_root or settings.plan2scene_data_root
        self.scripts_root = settings.PLAN2SCENE_ROOT / "code" / "scripts" / "plan2scene"
    
    def prepare_directory_structure(
        self,
        house_id: str,
        split: str = "test",
        drop: float = 0.0
    ) -> dict:
        """
        Create the required directory structure for Plan2Scene processing.
        
        Plan2Scene expects:
        - data/input/house_lists/test.txt (or train.txt, val.txt)
        - data/processed/texture_gen/test/drop_0.0/
        - data/processed/vgg_crop_select/test/drop_0.0/
        - data/processed/gnn_prop/test/drop_0.0/archs/
        - etc.
        
        Args:
            house_id: Unique house identifier
            split: Dataset split (test, train, val)
            drop: Drop rate for processing (usually 0.0 for inference)
        
        Returns:
            Dictionary of directory paths for each stage
        """
        drop_str = f"drop_{drop:.1f}"
        processed = self.data_root / "processed"
        
        dirs = {
            "input": self.data_root / "input",
            "data_lists": self.data_root / "input" / "data_lists",
            "full_archs": processed / "full_archs" / split,
            "photo_assignments": processed / "photo_assignments" / split / drop_str,
            "texture_gen": processed / "texture_gen" / split / drop_str,
            "vgg_crop_select": processed / "vgg_crop_select" / split / drop_str,
            "gnn_prop": processed / "gnn_prop" / split / drop_str,
            "gnn_prop_archs": processed / "gnn_prop" / split / drop_str / "archs",
            "seam_correct": processed / "seam_correct" / split / drop_str,
            "embed_textures": processed / "embed_textures" / split / drop_str,
            "renders": processed / "renders" / split / drop_str,
        }
        
        # Create all directories
        for name, path in dirs.items():
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {path}")
        
        # Create house list file
        house_list_file = dirs["data_lists"] / f"{split}.txt"
        if not house_list_file.exists() or house_id not in house_list_file.read_text():
            with open(house_list_file, "a") as f:
                f.write(f"{house_id}\n")
            logger.info(f"Added {house_id} to {house_list_file}")
        
        # Create empty photoroom.csv (synthetic texture generation, no real photos)
        photoroom_csv = dirs["photo_assignments"] / f"{house_id}.photoroom.csv"
        if not photoroom_csv.exists():
            # Create minimal CSV with just a header
            # Plan2Scene expects room_id,photo_path format
            with open(photoroom_csv, "w") as f:
                f.write("room_id,photo_path\n")
            logger.info(f"Created empty photoroom.csv at {photoroom_csv}")
        
        return dirs
    
    def _create_custom_data_paths_config(self) -> Path:
        """Create a custom data_paths.json that points to the job-specific directory."""
        import json
        
        config_path = self.data_root / "data_paths.json"
        
        # Use absolute paths to the job-specific directory
        data_root_abs = str(self.data_root.resolve())
        
        config = {
            "data_list_path_spec": f"{data_root_abs}/input/data_lists/{{split}}.txt",
            "arch_path_spec": f"{data_root_abs}/processed/full_archs/{{split}}/{{house_key}}.scene.json",
            "photoroom_path_spec": f"{data_root_abs}/processed/photo_assignments/{{split}}/drop_{{drop_fraction}}/{{house_key}}.photoroom.csv",
            "rectified_crops_path": f"{data_root_abs}/processed/rectified_crops",
            "train_texture_prop_val_data": f"{data_root_abs}/processed/vgg_crop_select/val/drop_0.0",
            "train_texture_prop_train_data": f"{data_root_abs}/processed/vgg_crop_select/train/drop_0.0",
            "gt_reference_crops_val": f"{data_root_abs}/processed/gt_reference/val/texture_crops"
        }
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Created custom data_paths.json at {config_path}")
        return config_path
    
    def run_full_pipeline(
        self,
        scene_json_path: Path,
        house_id: str,
        split: str = "test",
        drop: float = 0.0,
        job_id: Optional[str] = None
    ) -> FullPipelineResult:
        """
        Execute the complete Plan2Scene preprocessing pipeline.
        
        Stages:
        1. fill_room_embeddings.py - Generate texture embeddings for rooms
        2. vgg_crop_selector.py - Select optimal texture crops using VGG
        3. gnn_texture_prop.py - Propagate textures using GNN
        4. seam_correct_textures.py - Make textures tileable
        5. embed_textures.py - Embed textures into scene.json
        6. render_house_jsons.py - Render PNG previews and optionally video
        
        Args:
            scene_json_path: Path to the input scene.json file
            house_id: Unique house identifier
            split: Dataset split (test, train, val)
            drop: Drop rate (0.0 for full inference)
        
        Returns:
            FullPipelineResult with output paths and status
        """
        logger.info(f"Starting full Plan2Scene pipeline for house {house_id}")
        logger.info(f"  Scene JSON: {scene_json_path}")
        logger.info(f"  Split: {split}, Drop: {drop}")
        
        result = FullPipelineResult(
            success=False,
            house_id=house_id
        )
        
        try:
            # Prepare directory structure
            dirs = self.prepare_directory_structure(house_id, split, drop)
            
            # Create custom data_paths.json for this job
            custom_data_paths = self._create_custom_data_paths_config()
            
            # Copy input scene.json to input directory
            input_scene_json = dirs["input"] / scene_json_path.name
            if not input_scene_json.exists():
                import shutil
                shutil.copy(scene_json_path, input_scene_json)
                logger.info(f"Copied scene.json to {input_scene_json}")
            
            # Also copy scene.json to full_archs directory (expected by Plan2Scene)
            arch_scene_json = dirs["full_archs"] / f"{house_id}.scene.json"
            if not arch_scene_json.exists():
                import shutil
                shutil.copy(scene_json_path, arch_scene_json)
                logger.info(f"Copied scene.json to {arch_scene_json}")
            
            # Stage 1: Fill room embeddings
            if job_id:
                update_job(job_id, current_stage="room_embeddings")
            stage_result = self._run_fill_room_embeddings(split, drop, custom_data_paths)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Stage 2: VGG crop selection
            if job_id:
                update_job(job_id, current_stage="vgg_crop_selection")
            stage_result = self._run_vgg_crop_selector(split, drop, custom_data_paths)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Stage 3: GNN texture propagation
            if job_id:
                update_job(job_id, current_stage="texture_propagation")
            stage_result = self._run_gnn_texture_prop(split, drop, custom_data_paths)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Stage 4: Seam correction
            if job_id:
                update_job(job_id, current_stage="seam_correction")
            stage_result = self._run_seam_correct_textures(split, drop)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Stage 5: Embed textures
            if job_id:
                update_job(job_id, current_stage="texture_embedding")
            stage_result = self._run_embed_textures(split, drop, custom_data_paths)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Find the final scene.json with embedded textures
            embedded_scene_json = dirs["embed_textures"] / f"{house_id}.scene.json"
            if embedded_scene_json.exists():
                result.final_scene_json = embedded_scene_json
            
            # Stage 6: Rendering (optional - requires render.json config)
            if job_id:
                update_job(job_id, current_stage="rendering")
            stage_result = self._run_rendering(split, drop, custom_data_paths)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                # Rendering is optional - log warning but don't fail the pipeline
                logger.warning(f"Stage rendering failed (optional): {stage_result.error_message}")
                logger.warning("Continuing without PNG renders - scene.json with textures is complete")
            
            # Collect rendered outputs
            renders_dir = dirs["renders"]
            result.rendered_images = list(renders_dir.glob("*.png"))
            
            video_path = renders_dir / f"{house_id}.mp4"
            if video_path.exists():
                result.rendered_video = video_path
            
            result.success = True
            logger.info(f"✓ Full pipeline completed successfully for {house_id}")
            logger.info(f"  Final scene.json: {result.final_scene_json}")
            logger.info(f"  Rendered images: {len(result.rendered_images)}")
            logger.info(f"  Rendered video: {result.rendered_video}")
            
            return result
        
        except Plan2SceneCommandError as e:
            logger.error(f"Pipeline stage failed: {e}")
            result.error_message = str(e)
            return result
        except Exception as e:
            logger.error(f"Unexpected pipeline error: {e}", exc_info=True)
            result.error_message = str(e)
            return result
    
    def _run_fill_room_embeddings(self, split: str, drop: float, custom_data_paths: Path) -> PipelineStageResult:
        """Stage 1: Generate texture embeddings for rooms."""
        import time
        stage_name = "fill_room_embeddings"
        script = self.scripts_root / "preprocessing" / "fill_room_embeddings.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name=stage_name,
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        # Output path for texture embeddings (not data_root!)
        output_path = self.data_root / "processed" / "texture_gen" / split / f"drop_{drop:.1f}"
        
        args = [
            "python", str(script),
            str(output_path),
            split,
            "--drop", str(drop),
            "--data-paths", str(custom_data_paths)
        ]
        
        logger.info(f"Stage {stage_name}: START")
        start_time = time.time()
        try:
            run_plan2scene_command(args)
            elapsed = time.time() - start_time
            logger.info(f"Stage {stage_name}: DONE in {elapsed:.1f}s")
            return PipelineStageResult(
                stage_name=stage_name,
                success=True,
                output_dir=self.data_root / "processed" / "texture_gen" / split / f"drop_{drop:.1f}"
            )
        except Plan2SceneCommandError as e:
            elapsed = time.time() - start_time
            logger.error(f"Stage {stage_name}: FAILED after {elapsed:.1f}s - {e}")
            return PipelineStageResult(
                stage_name=stage_name,
                success=False,
                error_message=str(e)
            )
    
    def _run_vgg_crop_selector(self, split: str, drop: float, custom_data_paths: Path) -> PipelineStageResult:
        """Stage 2: Select optimal texture crops using VGG."""
        import time
        stage_name = "vgg_crop_selector"
        script = self.scripts_root / "crop_select" / "vgg_crop_selector.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name=stage_name,
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        # VGG crop selector takes: output_path texture_gen_path split
        output_path = self.data_root / "processed" / "vgg_crop_select" / split / f"drop_{drop:.1f}"
        texture_gen_path = self.data_root / "processed" / "texture_gen" / split / f"drop_{drop:.1f}"
        
        args = [
            "python", str(script),
            str(output_path),
            str(texture_gen_path),
            split,
            "--drop", str(drop),
            "--data-paths", str(custom_data_paths)
        ]
        
        logger.info(f"Stage {stage_name}: START")
        start_time = time.time()
        try:
            run_plan2scene_command(args)
            elapsed = time.time() - start_time
            logger.info(f"Stage {stage_name}: DONE in {elapsed:.1f}s")
            return PipelineStageResult(
                stage_name=stage_name,
                success=True,
                output_dir=self.data_root / "processed" / "vgg_crop_select" / split / f"drop_{drop:.1f}"
            )
        except Plan2SceneCommandError as e:
            elapsed = time.time() - start_time
            logger.error(f"Stage {stage_name}: FAILED after {elapsed:.1f}s - {e}")
            return PipelineStageResult(
                stage_name=stage_name,
                success=False,
                error_message=str(e)
            )
    
    def _run_gnn_texture_prop(self, split: str, drop: float, custom_data_paths: Path) -> PipelineStageResult:
        """Stage 3: Propagate textures using GNN."""
        script = self.scripts_root / "texture_prop" / "gnn_texture_prop.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="gnn_texture_prop",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        # Paths to GNN model config and checkpoint
        gnn_conf_path = settings.PLAN2SCENE_ROOT / "conf" / "plan2scene" / "texture_prop_conf" / "default.json"
        gnn_checkpoint_path = settings.PLAN2SCENE_ROOT / "data" / "checkpoints" / "texture-prop-synth-v2-epoch250.ckpt"
        
        # Path to custom room types that includes all R2V room types
        labels_path = Path("/app/static/plan2scene_labels")
        
        # Verify checkpoint exists
        if not gnn_checkpoint_path.exists():
            return PipelineStageResult(
                stage_name="gnn_texture_prop",
                success=False,
                error_message=f"GNN checkpoint not found: {gnn_checkpoint_path}. Please download pretrained weights."
            )
        
        output_dir = self.data_root / "processed" / "gnn_prop" / split / f"drop_{drop:.1f}"
        input_dir = self.data_root / "processed" / "vgg_crop_select" / split / f"drop_{drop:.1f}"
        
        args = [
            "python", str(script),
            str(output_dir),
            str(input_dir),
            split,
            str(gnn_conf_path),
            str(gnn_checkpoint_path),
            "--keep-existing-predictions",
            "--drop", str(drop),
            "--data-paths", str(custom_data_paths),
            "--labels-path", str(labels_path)
        ]
        
        import time
        stage_name = "gnn_texture_prop"
        logger.info(f"Stage {stage_name}: START")
        logger.info(f"  Config: {gnn_conf_path}")
        logger.info(f"  Checkpoint: {gnn_checkpoint_path}")
        start_time = time.time()
        try:
            run_plan2scene_command(args)
            elapsed = time.time() - start_time
            logger.info(f"Stage {stage_name}: DONE in {elapsed:.1f}s")
            return PipelineStageResult(
                stage_name=stage_name,
                success=True,
                output_dir=output_dir
            )
        except Plan2SceneCommandError as e:
            elapsed = time.time() - start_time
            logger.error(f"Stage {stage_name}: FAILED after {elapsed:.1f}s - {e}")
            return PipelineStageResult(
                stage_name=stage_name,
                success=False,
                error_message=str(e)
            )
    
    def _run_seam_correct_textures(self, split: str, drop: float) -> PipelineStageResult:
        """Stage 4: Make textures tileable (seam correction).
        
        Plan2Scene CLI signature:
        python seam_correct_textures.py <input_dir> <output_dir> <split> --drop <float>
        
        Where:
        - input_dir: gnn_prop/<split>/drop_<drop>/tileable_texture_crops
        - output_dir: gnn_prop/<split>/drop_<drop>/texture_crops
        
        NOTE: This stage requires Embark Studios' texture-synthesis tool.
        If seam_correct.json config is missing, we skip this stage and copy
        tileable_texture_crops -> texture_crops as-is.
        """
        script = self.scripts_root / "postprocessing" / "seam_correct_textures.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="seam_correct_textures",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        # Build paths according to Plan2Scene directory structure
        base_dir = self.data_root / "processed" / "gnn_prop" / split / f"drop_{drop}"
        input_dir = base_dir / "tileable_texture_crops"
        output_dir = base_dir / "texture_crops"
        
        # Check if seam_correct config exists
        seam_config = Path("/plan2scene/conf/plan2scene/seam_correct.json")
        
        if not seam_config.exists():
            # Skip seam correction - just copy tileable crops to texture crops
            import time
            start_time = time.time()
            logger.warning(
                "Stage seam_correct_textures: SKIPPED (seam_correct.json not found - "
                "requires Embark Studios texture-synthesis tool). "
                "Copying tileable textures without seam correction."
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all files from tileable_texture_crops to texture_crops
            import shutil
            if input_dir.exists():
                for item in input_dir.iterdir():
                    dest = output_dir / item.name
                    if item.is_file():
                        shutil.copy2(item, dest)
                    elif item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
            
            elapsed = time.time() - start_time
            logger.info(f"Stage seam_correct_textures: SKIPPED (copied in {elapsed:.1f}s)")
            return PipelineStageResult(
                stage_name="seam_correct_textures",
                success=True,
                output_dir=output_dir
            )
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        args = [
            "python", str(script),
            str(input_dir),
            str(output_dir),
            split,
            "--drop", str(drop)
        ]
        
        import time
        stage_name = "seam_correct_textures"
        logger.info(f"Stage {stage_name}: START")
        start_time = time.time()
        try:
            run_plan2scene_command(args, use_gpu=settings.plan2scene_gpu_enabled)
            elapsed = time.time() - start_time
            logger.info(f"Stage {stage_name}: DONE in {elapsed:.1f}s")
            return PipelineStageResult(
                stage_name=stage_name,
                success=True,
                output_dir=output_dir
            )
        except Plan2SceneCommandError as e:
            elapsed = time.time() - start_time
            logger.error(f"Stage {stage_name}: FAILED after {elapsed:.1f}s - {e}")
            return PipelineStageResult(
                stage_name=stage_name,
                success=False,
                error_message=str(e)
            )
    
    def _run_embed_textures(self, split: str, drop: float, custom_data_paths: Path) -> PipelineStageResult:
        """Stage 5: Embed textures into scene.json.
        
        Plan2Scene CLI signature:
        python embed_textures.py <output_path> <texture_crops_path> <split> --drop <float>
        
        Where:
        - output_path: where to save embedded arch.json (e.g., vgg_crop_select/<split>/drop_<drop>/archs)
        - texture_crops_path: gnn_prop/<split>/drop_<drop>/texture_crops
        """
        script = self.scripts_root / "postprocessing" / "embed_textures.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="embed_textures",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        # Build paths according to Plan2Scene directory structure
        base_gnn = self.data_root / "processed" / "gnn_prop" / split / f"drop_{drop}"
        base_vgg = self.data_root / "processed" / "vgg_crop_select" / split / f"drop_{drop}"
        
        texture_crops_path = base_gnn / "texture_crops"
        output_path = base_vgg / "archs"
        
        # Ensure output directory exists
        output_path.mkdir(parents=True, exist_ok=True)
        
        args = [
            "python", str(script),
            str(output_path),
            str(texture_crops_path),
            split,
            "--drop", str(drop)
        ]
        
        # Add custom data paths if provided
        if custom_data_paths and custom_data_paths.exists():
            args.extend(["--data-paths", str(custom_data_paths)])
        
        import time
        stage_name = "embed_textures"
        logger.info(f"Stage {stage_name}: START")
        start_time = time.time()
        try:
            run_plan2scene_command(args, use_gpu=settings.plan2scene_gpu_enabled)
            elapsed = time.time() - start_time
            logger.info(f"Stage {stage_name}: DONE in {elapsed:.1f}s")
            return PipelineStageResult(
                stage_name=stage_name,
                success=True,
                output_dir=output_path
            )
        except Plan2SceneCommandError as e:
            elapsed = time.time() - start_time
            logger.error(f"Stage {stage_name}: FAILED after {elapsed:.1f}s - {e}")
            return PipelineStageResult(
                stage_name=stage_name,
                success=False,
                error_message=str(e)
            )
    
    def _run_rendering(self, split: str, drop: float, custom_data_paths: Path) -> PipelineStageResult:
        """Stage 6: Render PNG previews.
        
        Plan2Scene CLI signature:
        python render_house_jsons.py <search_path> --drop <float> [--data-paths <path>]
        
        Where:
        - search_path: Directory to search for .arch.json files
        - Renders are created alongside the .arch.json files as .arch.png
        """
        script = self.scripts_root / "render_house_jsons.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="render_house_jsons",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        # Search path is where embed_textures wrote the .arch.json files
        # (vgg_crop_select/<split>/drop_<drop>/archs)
        search_path = self.data_root / "processed" / "vgg_crop_select" / split / f"drop_{drop}" / "archs"
        
        if not search_path.exists():
            return PipelineStageResult(
                stage_name="render_house_jsons",
                success=False,
                error_message=f"No arch.json files found at {search_path}"
            )
        
        args = [
            "python", str(script),
            str(search_path),
            "--drop", str(drop),
            "--scene-json"  # Process .scene.json files instead of .arch.json
        ]
        
        # Add custom data paths if provided
        if custom_data_paths and custom_data_paths.exists():
            args.extend(["--data-paths", str(custom_data_paths)])
        
        import time
        stage_name = "render_house_jsons"
        logger.info(f"Stage {stage_name}: START")
        start_time = time.time()
        try:
            run_plan2scene_command(args, use_gpu=settings.plan2scene_gpu_enabled)
            elapsed = time.time() - start_time
            logger.info(f"Stage {stage_name}: DONE in {elapsed:.1f}s")
            # Renders are created alongside the arch.json files
            return PipelineStageResult(
                stage_name=stage_name,
                success=True,
                output_dir=search_path
            )
        except Plan2SceneCommandError as e:
            elapsed = time.time() - start_time
            logger.error(f"Stage {stage_name}: FAILED after {elapsed:.1f}s - {e}")
            return PipelineStageResult(
                stage_name=stage_name,
                success=False,
                error_message=str(e)
            )
