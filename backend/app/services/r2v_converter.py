"""
R2V to Plan2Scene conversion utilities.

Handles conversion from R2V (Raster-to-Vector) outputs to Plan2Scene scene.json format.
"""

import logging
from pathlib import Path
from typing import Optional
import json

from app.config import settings
from app.services.plan2scene_commands import run_r2v_command, Plan2SceneCommandError

logger = logging.getLogger(__name__)


def convert_r2v_to_scene_json(
    r2v_output_path: Path,
    out_dir: Path,
    scale_factor: float = 0.08,
    r2v_annot: bool = False
) -> Path:
    """
    Convert R2V output to Plan2Scene scene.json format.
    
    Wraps the r2v-to-plan2scene convert.py script:
    PYTHONPATH=./code/src python convert.py [out_dir] [r2v_output_path] --scale-factor [scale_factor] [--r2v-annot]
    
    Args:
        r2v_output_path: Path to R2V output file (annotation or vector file)
        out_dir: Output directory for generated scene.json
        scale_factor: Scale factor for coordinate conversion (default: 0.08 per Plan2Scene docs)
        r2v_annot: Whether the input is an R2V annotation file (vs direct vector)
    
    Returns:
        Path to the generated *.scene.json file
    
    Raises:
        Plan2SceneCommandError: If conversion fails
        FileNotFoundError: If r2v-to-plan2scene repo or convert.py not found
    """
    # Validate R2V-to-Plan2Scene repository
    if not settings.R2V_TO_PLAN2SCENE_ROOT.exists():
        raise FileNotFoundError(
            f"R2V-to-Plan2Scene repository not found at {settings.R2V_TO_PLAN2SCENE_ROOT}. "
            f"Please clone it from https://github.com/3dlg-hcvc/r2v-to-plan2scene"
        )
    
    convert_script = settings.R2V_TO_PLAN2SCENE_ROOT / "convert.py"
    if not convert_script.exists():
        raise FileNotFoundError(
            f"convert.py not found at {convert_script}. "
            f"Please ensure r2v-to-plan2scene is properly cloned."
        )
    
    # Validate input file
    if not r2v_output_path.exists():
        raise FileNotFoundError(f"R2V output file not found: {r2v_output_path}")
    
    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Build command arguments
    args = [
        "python",
        str(convert_script),
        str(out_dir),
        str(r2v_output_path),
        "--scale-factor",
        str(scale_factor)
    ]
    
    if r2v_annot:
        args.append("--r2v-annot")
    
    logger.info(f"Converting R2V output to scene.json")
    logger.info(f"  Input: {r2v_output_path}")
    logger.info(f"  Output dir: {out_dir}")
    logger.info(f"  Scale factor: {scale_factor}")
    logger.info(f"  R2V annotation format: {r2v_annot}")
    
    try:
        result = run_r2v_command(args)
        logger.info(f"✓ R2V conversion completed successfully")
        
        # Find the generated scene.json file
        # The convert.py script typically creates <house_id>.scene.json
        scene_json_files = list(out_dir.glob("*.scene.json"))
        
        if not scene_json_files:
            raise FileNotFoundError(
                f"No *.scene.json file found in {out_dir} after conversion. "
                f"Conversion may have failed silently."
            )
        
        if len(scene_json_files) > 1:
            logger.warning(f"Multiple scene.json files found, using first: {scene_json_files[0]}")
        
        scene_json_path = scene_json_files[0]
        logger.info(f"Generated scene.json: {scene_json_path}")
        
        # Validate it's valid JSON
        try:
            with open(scene_json_path) as f:
                scene_data = json.load(f)
            logger.info(f"✓ Validated scene.json structure (has {len(scene_data.get('rooms', []))} rooms)")
        except json.JSONDecodeError as e:
            logger.error(f"Generated scene.json is not valid JSON: {e}")
            raise
        
        return scene_json_path
    
    except Plan2SceneCommandError as e:
        logger.error(f"R2V conversion failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during R2V conversion: {e}", exc_info=True)
        raise


def extract_house_id_from_scene_json(scene_json_path: Path) -> str:
    """
    Extract house ID from scene.json filename.
    
    Args:
        scene_json_path: Path to *.scene.json file
    
    Returns:
        House ID (filename without .scene.json extension)
    """
    if not scene_json_path.name.endswith(".scene.json"):
        raise ValueError(f"Expected *.scene.json file, got: {scene_json_path.name}")
    
    house_id = scene_json_path.stem.replace(".scene", "")
    return house_id
