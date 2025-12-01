"""
Quick verification script to check if Plan2Scene setup is ready for full pipeline mode.
"""

from pathlib import Path
import sys

def check_repo(name, path):
    """Check if a repository exists."""
    if path.exists():
        print(f"✅ {name}: {path}")
        return True
    else:
        print(f"❌ {name}: NOT FOUND at {path}")
        return False

def check_script(name, path):
    """Check if a script exists."""
    if path.exists():
        print(f"  ✅ {name}")
        return True
    else:
        print(f"  ❌ {name}: NOT FOUND")
        return False

def main():
    print("=" * 60)
    print("Plan2Scene Full Pipeline Setup Verification")
    print("=" * 60)
    print()
    
    all_good = True
    
    # Check repositories
    print("📁 Required Repositories:")
    plan2scene_root = Path("../plan2scene").resolve()
    r2v_root = Path("../r2v-to-plan2scene").resolve()
    
    all_good &= check_repo("Plan2Scene", plan2scene_root)
    all_good &= check_repo("R2V-to-Plan2Scene", r2v_root)
    print()
    
    # Check Plan2Scene scripts
    print("📜 Plan2Scene Scripts:")
    scripts_root = plan2scene_root / "code" / "scripts" / "plan2scene"
    
    critical_scripts = [
        ("texture_gen/fill_room_embeddings.py", "Room Embeddings"),
        ("texture_gen/vgg_crop_selector.py", "VGG Crop Selector"),
        ("texture_prop/gnn_texture_prop.py", "GNN Texture Propagation"),
        ("texture_gen/seam_correct_textures.py", "Seam Correction"),
        ("texture_gen/embed_textures.py", "Texture Embedding"),
        ("render_house_jsons.py", "Rendering"),
    ]
    
    for script_path, name in critical_scripts:
        full_path = scripts_root / script_path
        all_good &= check_script(name, full_path)
    print()
    
    # Check R2V converter
    print("🔄 R2V Converter:")
    convert_script = r2v_root / "convert.py"
    all_good &= check_script("convert.py", convert_script)
    print()
    
    # Check Plan2Scene data directory
    print("💾 Plan2Scene Data Directory:")
    data_root = plan2scene_root / "data"
    if data_root.exists():
        print(f"  ✅ Data directory exists: {data_root}")
        
        # Check for weights/checkpoints
        weights_dirs = [
            data_root / "model_best",
            data_root / "checkpoints",
            data_root / "pretrained",
        ]
        
        weights_found = False
        for weights_dir in weights_dirs:
            if weights_dir.exists():
                weights_found = True
                print(f"  ✅ Found weights directory: {weights_dir}")
        
        if not weights_found:
            print("  ⚠️  No pretrained weights found. Download them from:")
            print("     https://github.com/3dlg-hcvc/plan2scene#download-trained-models")
    else:
        print(f"  ℹ️  Data directory will be created: {data_root}")
    print()
    
    # Check environment configuration
    print("⚙️  Environment Configuration:")
    env_file = Path(".env")
    if env_file.exists():
        print(f"  ✅ .env file exists")
        content = env_file.read_text()
        if "MODE=gpu" in content:
            print("  ✅ MODE=gpu configured")
        if "PIPELINE_MODE=full" in content:
            print("  ✅ PIPELINE_MODE=full configured")
    else:
        print(f"  ⚠️  No .env file found. Copy from .env.example")
    print()
    
    # Summary
    print("=" * 60)
    if all_good:
        print("✅ Setup verification PASSED!")
        print("   Ready to run full pipeline mode.")
        print()
        print("Next steps:")
        print("  1. Download Plan2Scene weights if not already done")
        print("  2. Start the app: docker compose up --build")
        print("  3. Upload floorplan image + R2V annotation file")
    else:
        print("❌ Setup verification FAILED!")
        print("   Please fix the issues above before running full pipeline.")
    print("=" * 60)
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
