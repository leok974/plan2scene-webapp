"""
R2V to Plan2Scene conversion utilities.

Handles conversion from R2V (Raster-to-Vector) outputs to Plan2Scene scene.json format.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import json

from app.config import settings
from app.services.plan2scene_commands import run_r2v_command, Plan2SceneCommandError

logger = logging.getLogger(__name__)


# Mapping from R2V room types to Plan2Scene's 12 standard room types
# This ensures compatibility with pretrained GNN checkpoints
R2V_TO_PLAN2SCENE_ROOM_TYPE_MAP = {
    # Direct mappings
    "bedroom": "Bedroom",
    "Bedroom": "Bedroom",
    "bathroom": "Bathroom",
    "Bathroom": "Bathroom",
    "restroom": "Bathroom",
    "washing_room": "Bathroom",
    "kitchen": "Kitchen",
    "Kitchen": "Kitchen",
    "cooking_counter": "Kitchen",
    "entrance": "Entrance",
    "Entrance": "Entrance",
    "corridor": "Corridor",
    "Corridor": "Corridor",
    "closet": "Closet",
    "Closet": "Closet",
    "living_room": "Reception",  # Living room → Reception
    "Reception": "Reception",
    "Outdoor": "Outdoor",
    "Terrace": "Terrace",
    "Balcony": "Balcony",
    "Staircase": "Staircase",
    
    # Special R2V types that need mapping
    "PS": "Unknown",  # PS (unclear meaning) → Unknown
    "washing_basin": "Bathroom",  # Fixture → Bathroom
    "toilet": "Bathroom",  # Fixture → Bathroom
    "bathtub": "Bathroom",  # Fixture → Bathroom
    "special": "Unknown",
    "wall": "Unknown",  # Wall annotation → Unknown
    "door": "Unknown",  # Door annotation → Unknown
}


def normalize_room_type(room_type: str) -> str:
    """
    Normalize R2V room type to one of Plan2Scene's 12 standard types.
    
    This ensures compatibility with pretrained GNN texture propagation models,
    which expect the specific 12 room types they were trained on.
    
    Args:
        room_type: R2V room type (can be lowercase, fixtures, special types, etc.)
    
    Returns:
        One of the 12 standard Plan2Scene room types, or "Unknown" if unmappable
    """
    normalized = R2V_TO_PLAN2SCENE_ROOM_TYPE_MAP.get(room_type, "Unknown")
    if normalized == "Unknown" and room_type not in R2V_TO_PLAN2SCENE_ROOM_TYPE_MAP:
        logger.warning(f"Unknown room type '{room_type}' mapped to 'Unknown'")
    return normalized


def normalize_scene_json(scene_path: Path) -> Tuple[int, int, str, str]:
    """
    Normalize an r2v-to-plan2scene scene.json in-place:
    - Rooms live at data['scene']['arch']['rooms']
    - Room types live in room['types'][0]
    - arch.id may be a full path (e.g. '/app/uploads') and must be normalized to 'uploads'
    
    This is critical for Plan2Scene preprocessing compatibility:
    - GNN checkpoints expect exactly 12 room types
    - House keys must match between scene.json ID and data_lists
    
    Args:
        scene_path: Path to the scene.json file to normalize
    
    Returns:
        Tuple of (room_count, normalized_room_count, original_id, normalized_id)
    """
    data = json.loads(scene_path.read_text(encoding="utf-8"))
    
    scene = data.get("scene", {})
    arch = scene.get("arch", {})
    rooms = arch.get("rooms", [])
    
    room_count = len(rooms)
    normalized_room_count = 0
    
    # Normalize room types to Plan2Scene's 12 standard types
    for room in rooms:
        types = room.get("types") or []
        if not types:
            continue
        original_type = types[0]
        normalized_type = normalize_room_type(original_type)
        if normalized_type != original_type:
            room["types"] = [normalized_type]
            normalized_room_count += 1
    
    # Normalize arch.id → house_key (e.g. '/app/uploads.png' → 'uploads')
    original_id = arch.get("id", "")
    normalized_id = original_id
    if original_id:
        # Strip directories
        leaf = Path(original_id).name
        # Strip extension(s)
        normalized_id = Path(leaf).stem
        # Extra safety: if still has a dot, split on first
        if "." in normalized_id:
            normalized_id = normalized_id.split(".")[0]
        arch["id"] = normalized_id
    
    # Write back
    scene.setdefault("arch", arch)
    data["scene"] = scene
    scene_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    logger.info(
        "Normalized scene.json at %s: rooms=%d, normalized=%d, id=%r → %r",
        scene_path,
        room_count,
        normalized_room_count,
        original_id,
        normalized_id,
    )
    return room_count, normalized_room_count, original_id, normalized_id


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
        str(scale_factor),
        "--no-previews"  # Skip preview generation to avoid font dependency issues
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
        
        # The R2V converter saves files based on the input filename, not the output directory
        # It creates /path/to/input/<input_name>.scene.json (without UUID suffix)
        # We need to find and move it to the expected output directory
        
        # Check the output directory first
        scene_json_files = list(out_dir.glob("*.scene.json"))
        
        if not scene_json_files:
            # R2V saves files based on the input path, stripping UUID suffixes
            # Input: /app/uploads/UUID_r2v_annotation.txt -> Output: /app/uploads.scene.json
            # So we need to look in the parent directory of the input directory
            input_dir = r2v_output_path.parent  # /app/uploads/
            parent_dir = input_dir.parent  # /app/
            input_base = r2v_output_path.stem.split('_')[0] if '_' in r2v_output_path.stem else r2v_output_path.stem
            
            # Look for generated files in both directories
            potential_files = list(input_dir.glob("*.scene.json")) + list(parent_dir.glob(f"{input_dir.name}.scene.json"))
            logger.info(f"Found {len(potential_files)} scene.json files in {input_dir} and {parent_dir}")
            
            if potential_files:
                # Move the first scene.json to the output directory
                source_file = potential_files[0]
                dest_file = out_dir / source_file.name
                import shutil
                shutil.move(str(source_file), str(dest_file))
                logger.info(f"Moved {source_file} to {dest_file}")
                
                # Also move objectaabb.json if it exists
                objectaabb_file = source_file.with_suffix('.objectaabb.json')
                if objectaabb_file.exists():
                    dest_objectaabb = out_dir / objectaabb_file.name
                    shutil.move(str(objectaabb_file), str(dest_objectaabb))
                    logger.info(f"Moved {objectaabb_file} to {dest_objectaabb}")
                
                scene_json_files = [dest_file]
            else:
                raise FileNotFoundError(
                    f"No *.scene.json file found in {out_dir} or {input_dir} after conversion. "
                    f"Conversion may have failed silently."
                )
        
        if len(scene_json_files) > 1:
            logger.warning(f"Multiple scene.json files found, using first: {scene_json_files[0]}")
        
        scene_json_path = scene_json_files[0]
        logger.info(f"Generated scene.json: {scene_json_path}")
        
        # Normalize the scene.json structure for Plan2Scene compatibility
        try:
            room_count, normalized_count, original_id, normalized_id = normalize_scene_json(scene_json_path)
            logger.info(
                f"✓ Validated scene.json structure: rooms={room_count} (normalized={normalized_count}), id={original_id!r} → {normalized_id!r}"
            )
        except json.JSONDecodeError as e:
            logger.error(f"Generated scene.json is not valid JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to normalize scene.json: {e}", exc_info=True)
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
