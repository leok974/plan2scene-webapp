"""
Test script to verify backend imports and configuration work correctly.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_imports():
    """Test that all backend modules can be imported."""
    print("Testing backend module imports...")
    
    try:
        print("  ✓ Importing config...")
        from app.config import settings
        
        print("  ✓ Importing plan2scene_commands...")
        from app.services.plan2scene_commands import run_plan2scene_command, Plan2SceneCommandError
        
        print("  ✓ Importing r2v_converter...")
        from app.services.r2v_converter import convert_r2v_to_scene_json
        
        print("  ✓ Importing preprocessing_pipeline...")
        from app.services.preprocessing_pipeline import Plan2ScenePreprocessor
        
        print("  ✓ Importing plan2scene engine...")
        from app.services.plan2scene import Plan2SceneEngine, PipelineMode
        
        print("\n✅ All imports successful!")
        return True
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration settings."""
    print("\nTesting configuration...")
    
    try:
        from app.config import settings
        
        print(f"  MODE: {settings.MODE}")
        print(f"  PIPELINE_MODE: {settings.PIPELINE_MODE}")
        print(f"  PLAN2SCENE_ROOT: {settings.PLAN2SCENE_ROOT}")
        print(f"  plan2scene_data_root: {settings.plan2scene_data_root}")
        print(f"  plan2scene_code_root: {settings.plan2scene_code_root}")
        print(f"  R2V_TO_PLAN2SCENE_ROOT: {settings.R2V_TO_PLAN2SCENE_ROOT}")
        
        # Check paths exist
        if settings.PLAN2SCENE_ROOT.exists():
            print(f"  ✓ Plan2Scene repo found")
        else:
            print(f"  ❌ Plan2Scene repo NOT found at {settings.PLAN2SCENE_ROOT}")
        
        if settings.R2V_TO_PLAN2SCENE_ROOT.exists():
            print(f"  ✓ R2V repo found")
        else:
            print(f"  ❌ R2V repo NOT found at {settings.R2V_TO_PLAN2SCENE_ROOT}")
        
        print("\n✅ Configuration OK!")
        return True
    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_script_paths():
    """Test that Plan2Scene scripts can be found."""
    print("\nTesting Plan2Scene script paths...")
    
    try:
        from app.config import settings
        
        scripts_root = settings.PLAN2SCENE_ROOT / "code" / "scripts" / "plan2scene"
        
        scripts_to_check = [
            ("preprocessing/fill_room_embeddings.py", "Room Embeddings"),
            ("crop_select/vgg_crop_selector.py", "VGG Crop Selector"),
            ("texture_prop/gnn_texture_prop.py", "GNN Texture Propagation"),
            ("postprocessing/seam_correct_textures.py", "Seam Correction"),
            ("postprocessing/embed_textures.py", "Texture Embedding"),
            ("render_house_jsons.py", "Rendering"),
        ]
        
        all_found = True
        for script_path, name in scripts_to_check:
            full_path = scripts_root / script_path
            if full_path.exists():
                print(f"  ✓ {name}: {script_path}")
            else:
                print(f"  ❌ {name}: NOT FOUND at {script_path}")
                all_found = False
        
        if all_found:
            print("\n✅ All scripts found!")
        else:
            print("\n⚠️  Some scripts missing - pipeline may not work")
        
        return all_found
    except Exception as e:
        print(f"\n❌ Script path test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Backend Verification Test")
    print("=" * 60)
    print()
    
    success = True
    success &= test_imports()
    success &= test_configuration()
    success &= test_script_paths()
    
    print()
    print("=" * 60)
    if success:
        print("✅ All tests passed! Backend is ready.")
    else:
        print("⚠️  Some tests failed. Review output above.")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
