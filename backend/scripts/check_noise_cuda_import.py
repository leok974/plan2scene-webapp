#!/usr/bin/env python3
"""
Sanity check for noise_cuda CUDA extension import.

This verifies that the noise_cuda extension was built and can be imported
successfully by the Python interpreter.
"""

import sys


def main():
    """Check if noise_cuda can be imported."""
    print("=" * 70)
    print("noise_cuda Import Check")
    print("=" * 70)
    
    try:
        import noise_cuda  # type: ignore
        
        print("✓ SUCCESS: noise_cuda imported successfully")
        print(f"  Module: {noise_cuda}")
        print(f"  Location: {noise_cuda.__file__}")
        
        # Try to access some attributes if available
        if hasattr(noise_cuda, '__version__'):
            print(f"  Version: {noise_cuda.__version__}")
        
        print("=" * 70)
        return 0
        
    except ImportError as e:
        print(f"✗ IMPORT FAILED: {e}")
        print("\nThe noise_cuda extension has not been built or installed.")
        print("Run: docker compose exec backend python scripts/build_noise_cuda.py")
        print("=" * 70)
        return 1
        
    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
