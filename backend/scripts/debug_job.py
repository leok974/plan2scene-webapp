#!/usr/bin/env python3
"""
Debug utility for inspecting Plan2Scene job artifacts.

Usage:
    python scripts/debug_job.py <job_id>
    
Example:
    docker compose exec backend python scripts/debug_job.py a294d0d8c8e04ee1bbe2539af9133cd4
"""

import sys
import json
from pathlib import Path
from typing import Optional


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def check_file(path: Path, name: str) -> None:
    """Check if file exists and print info."""
    if path.exists():
        size = path.stat().st_size
        print(f"  ✓ {name}: {format_size(size)}")
    else:
        print(f"  ✗ {name}: MISSING")


def main(job_id: str) -> None:
    """Debug a Plan2Scene job."""
    base = Path("/app/static/jobs") / job_id
    
    if not base.exists():
        print(f"ERROR: Job directory not found: {base}")
        return
    
    print("=" * 70)
    print(f"Job ID: {job_id}")
    print("=" * 70)
    
    # Root level files
    print("\n📁 Root Contents:")
    for p in sorted(base.iterdir()):
        if p.is_file():
            print(f"  - {p.name} ({format_size(p.stat().st_size)})")
        else:
            print(f"  - {p.name}/ (directory)")
    
    # Check key output files
    print("\n📦 Key Output Files:")
    check_file(base / "scene.glb", "scene.glb")
    check_file(base / "walkthrough.mp4", "walkthrough.mp4")
    
    # R2V conversion
    print("\n🔄 R2V Conversion:")
    r2v_dir = base / "r2v_conversion"
    if r2v_dir.exists():
        scene_json = r2v_dir / "uploads.scene.json"
        check_file(scene_json, "uploads.scene.json")
        if scene_json.exists():
            try:
                data = json.loads(scene_json.read_text())
                rooms = data.get("scene", {}).get("arch", {}).get("rooms", [])
                print(f"    Rooms: {len(rooms)}")
            except Exception as e:
                print(f"    Error reading: {e}")
    else:
        print("  ✗ r2v_conversion directory not found")
    
    # Plan2Scene data
    print("\n🏗️  Plan2Scene Processing:")
    p2s_base = base / "plan2scene_data"
    
    if not p2s_base.exists():
        print("  ✗ plan2scene_data directory not found")
        return
    
    # Check processed stages
    processed = p2s_base / "processed"
    if processed.exists():
        stages = {
            "texture_gen": "Room Embeddings",
            "vgg_crop_select": "VGG Crop Selection",
            "gnn_prop": "GNN Texture Propagation",
        }
        
        for stage_dir, stage_name in stages.items():
            stage_path = processed / stage_dir / "test" / "drop_0.0"
            if stage_path.exists():
                # Count files
                all_files = list(stage_path.rglob("*"))
                file_count = len([f for f in all_files if f.is_file()])
                total_size = sum(f.stat().st_size for f in all_files if f.is_file())
                print(f"  ✓ {stage_name}: {file_count} files ({format_size(total_size)})")
            else:
                print(f"  ✗ {stage_name}: Not found")
    
    # Final embedded scene
    print("\n✨ Final Output:")
    final_scenes = [
        processed / "vgg_crop_select" / "test" / "drop_0.0" / "archs" / "uploads.scene.json",
        processed / "full_archs" / "test" / "uploads.scene.json",
    ]
    
    found_final = False
    for scene_path in final_scenes:
        if scene_path.exists():
            size = scene_path.stat().st_size
            print(f"  ✓ Embedded scene: {scene_path.relative_to(p2s_base)} ({format_size(size)})")
            found_final = True
            
            # Parse room count
            try:
                data = json.loads(scene_path.read_text())
                rooms = data.get("scene", {}).get("arch", {}).get("rooms", [])
                print(f"    Rooms with textures: {len(rooms)}")
            except Exception:
                pass
            break
    
    if not found_final:
        print("  ✗ No final embedded scene.json found")
    
    # Texture crops
    print("\n🎨 Generated Textures:")
    texture_crops = processed / "gnn_prop" / "test" / "drop_0.0" / "texture_crops"
    if texture_crops.exists():
        png_files = list(texture_crops.rglob("*.png"))
        print(f"  ✓ Texture PNGs: {len(png_files)} files")
        if png_files:
            total_size = sum(f.stat().st_size for f in png_files)
            print(f"    Total size: {format_size(total_size)}")
    else:
        print("  ✗ No texture crops found")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/debug_job.py <job_id>")
        print("\nExample:")
        print("  docker compose exec backend python scripts/debug_job.py a294d0d8c8e04ee1bbe2539af9133cd4")
        sys.exit(1)
    
    main(sys.argv[1])
