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
from typing import Optional, List
from dataclasses import dataclass

from app.config import settings
from app.services.plan2scene_commands import run_plan2scene_command, Plan2SceneCommandError

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
            "house_lists": self.data_root / "input" / "house_lists",
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
        house_list_file = dirs["house_lists"] / f"{split}.txt"
        if not house_list_file.exists() or house_id not in house_list_file.read_text():
            with open(house_list_file, "a") as f:
                f.write(f"{house_id}\n")
            logger.info(f"Added {house_id} to {house_list_file}")
        
        return dirs
    
    def run_full_pipeline(
        self,
        scene_json_path: Path,
        house_id: str,
        split: str = "test",
        drop: float = 0.0
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
            
            # Copy input scene.json to input directory
            input_scene_json = dirs["input"] / scene_json_path.name
            if not input_scene_json.exists():
                import shutil
                shutil.copy(scene_json_path, input_scene_json)
                logger.info(f"Copied scene.json to {input_scene_json}")
            
            # Stage 1: Fill room embeddings
            stage_result = self._run_fill_room_embeddings(split, drop)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Stage 2: VGG crop selection
            stage_result = self._run_vgg_crop_selector(split, drop)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Stage 3: GNN texture propagation
            stage_result = self._run_gnn_texture_prop(split, drop)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Stage 4: Seam correction
            stage_result = self._run_seam_correct_textures(split, drop)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Stage 5: Embed textures
            stage_result = self._run_embed_textures(split, drop)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
            # Find the final scene.json with embedded textures
            embedded_scene_json = dirs["embed_textures"] / f"{house_id}.scene.json"
            if embedded_scene_json.exists():
                result.final_scene_json = embedded_scene_json
            
            # Stage 6: Rendering
            stage_result = self._run_rendering(split, drop)
            result.stage_results.append(stage_result)
            if not stage_result.success:
                result.failed_stage = stage_result.stage_name
                result.error_message = stage_result.error_message
                return result
            
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
    
    def _run_fill_room_embeddings(self, split: str, drop: float) -> PipelineStageResult:
        """Stage 1: Generate texture embeddings for rooms."""
        script = self.scripts_root / "preprocessing" / "fill_room_embeddings.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="fill_room_embeddings",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        args = [
            "python", str(script),
            str(self.data_root),
            split,
            "--drop", str(drop)
        ]
        
        logger.info("Stage 1/6: Filling room embeddings...")
        try:
            run_plan2scene_command(args)
            logger.info("✓ Room embeddings completed")
            return PipelineStageResult(
                stage_name="fill_room_embeddings",
                success=True,
                output_dir=self.data_root / "processed" / "texture_gen" / split / f"drop_{drop:.1f}"
            )
        except Plan2SceneCommandError as e:
            logger.error(f"Room embeddings failed: {e}")
            return PipelineStageResult(
                stage_name="fill_room_embeddings",
                success=False,
                error_message=str(e)
            )
    
    def _run_vgg_crop_selector(self, split: str, drop: float) -> PipelineStageResult:
        """Stage 2: Select optimal texture crops using VGG."""
        script = self.scripts_root / "crop_select" / "vgg_crop_selector.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="vgg_crop_selector",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        args = [
            "python", str(script),
            str(self.data_root),
            split,
            "--drop", str(drop)
        ]
        
        logger.info("Stage 2/6: Running VGG crop selection...")
        try:
            run_plan2scene_command(args)
            logger.info("✓ VGG crop selection completed")
            return PipelineStageResult(
                stage_name="vgg_crop_selector",
                success=True,
                output_dir=self.data_root / "processed" / "vgg_crop_select" / split / f"drop_{drop:.1f}"
            )
        except Plan2SceneCommandError as e:
            logger.error(f"VGG crop selection failed: {e}")
            return PipelineStageResult(
                stage_name="vgg_crop_selector",
                success=False,
                error_message=str(e)
            )
    
    def _run_gnn_texture_prop(self, split: str, drop: float) -> PipelineStageResult:
        """Stage 3: Propagate textures using GNN."""
        script = self.scripts_root / "texture_prop" / "gnn_texture_prop.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="gnn_texture_prop",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        args = [
            "python", str(script),
            str(self.data_root),
            split,
            "--drop", str(drop)
        ]
        
        logger.info("Stage 3/6: Running GNN texture propagation...")
        try:
            run_plan2scene_command(args)
            logger.info("✓ GNN texture propagation completed")
            return PipelineStageResult(
                stage_name="gnn_texture_prop",
                success=True,
                output_dir=self.data_root / "processed" / "gnn_prop" / split / f"drop_{drop:.1f}"
            )
        except Plan2SceneCommandError as e:
            logger.error(f"GNN texture propagation failed: {e}")
            return PipelineStageResult(
                stage_name="gnn_texture_prop",
                success=False,
                error_message=str(e)
            )
    
    def _run_seam_correct_textures(self, split: str, drop: float) -> PipelineStageResult:
        """Stage 4: Make textures tileable (seam correction)."""
        script = self.scripts_root / "postprocessing" / "seam_correct_textures.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="seam_correct_textures",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        args = [
            "python", str(script),
            str(self.data_root),
            split,
            "--drop", str(drop)
        ]
        
        logger.info("Stage 4/6: Running seam correction...")
        try:
            run_plan2scene_command(args)
            logger.info("✓ Seam correction completed")
            return PipelineStageResult(
                stage_name="seam_correct_textures",
                success=True,
                output_dir=self.data_root / "processed" / "seam_correct" / split / f"drop_{drop:.1f}"
            )
        except Plan2SceneCommandError as e:
            logger.error(f"Seam correction failed: {e}")
            return PipelineStageResult(
                stage_name="seam_correct_textures",
                success=False,
                error_message=str(e)
            )
    
    def _run_embed_textures(self, split: str, drop: float) -> PipelineStageResult:
        """Stage 5: Embed textures into scene.json."""
        script = self.scripts_root / "postprocessing" / "embed_textures.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="embed_textures",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        args = [
            "python", str(script),
            str(self.data_root),
            split,
            "--drop", str(drop)
        ]
        
        logger.info("Stage 5/6: Embedding textures into scene.json...")
        try:
            run_plan2scene_command(args)
            logger.info("✓ Texture embedding completed")
            return PipelineStageResult(
                stage_name="embed_textures",
                success=True,
                output_dir=self.data_root / "processed" / "embed_textures" / split / f"drop_{drop:.1f}"
            )
        except Plan2SceneCommandError as e:
            logger.error(f"Texture embedding failed: {e}")
            return PipelineStageResult(
                stage_name="embed_textures",
                success=False,
                error_message=str(e)
            )
    
    def _run_rendering(self, split: str, drop: float) -> PipelineStageResult:
        """Stage 6: Render PNG previews and optionally video."""
        script = self.scripts_root / "render_house_jsons.py"
        
        if not script.exists():
            return PipelineStageResult(
                stage_name="render_house_jsons",
                success=False,
                error_message=f"Script not found: {script}"
            )
        
        # Input is the embedded scene.json directory
        input_dir = self.data_root / "processed" / "embed_textures" / split / f"drop_{drop:.1f}"
        output_dir = self.data_root / "processed" / "renders" / split / f"drop_{drop:.1f}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        args = [
            "python", str(script),
            str(input_dir),
            "--output-dir", str(output_dir),
            "--scene-json"
        ]
        
        logger.info("Stage 6/6: Rendering previews...")
        try:
            run_plan2scene_command(args)
            logger.info("✓ Rendering completed")
            return PipelineStageResult(
                stage_name="render_house_jsons",
                success=True,
                output_dir=output_dir
            )
        except Plan2SceneCommandError as e:
            logger.error(f"Rendering failed: {e}")
            return PipelineStageResult(
                stage_name="render_house_jsons",
                success=False,
                error_message=str(e)
            )
