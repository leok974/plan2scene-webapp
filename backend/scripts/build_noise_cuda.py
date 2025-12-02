#!/usr/bin/env python3
"""
Build the noise_cuda CUDA extension for Plan2Scene.

This extension is required for the texture generation pipeline and must be
compiled against the installed CUDA toolkit and PyTorch version.
"""

import os
import subprocess
import sys
from pathlib import Path


def find_noise_cuda_setup(root: Path) -> Path:
    """
    Search for the setup.py file that builds the noise_cuda extension.
    
    Args:
        root: Plan2Scene repository root
    
    Returns:
        Path to the directory containing setup.py
    
    Raises:
        RuntimeError: If setup.py cannot be found
    """
    for setup in root.rglob("setup.py"):
        try:
            text = setup.read_text(encoding="utf-8", errors="ignore")
            if "CUDAExtension('noise_cuda'" in text or 'CUDAExtension("noise_cuda"' in text:
                return setup.parent
        except Exception as e:
            print(f"Warning: Could not read {setup}: {e}")
            continue
    
    raise RuntimeError(
        f"Could not find setup.py for noise_cuda in Plan2Scene repo at {root}\n"
        "Expected to find a setup.py with CUDAExtension('noise_cuda', ...)"
    )


def build_noise_cuda(plan2scene_root: str, cuda_arch_list: str = "8.6"):
    """
    Build and install the noise_cuda CUDA extension.
    
    Args:
        plan2scene_root: Path to Plan2Scene repository
        cuda_arch_list: CUDA architecture list (e.g., "8.6" for RTX 30xx/40xx)
    """
    import shutil
    import tempfile
    
    root = Path(plan2scene_root).resolve()
    
    if not root.exists():
        raise RuntimeError(f"Plan2Scene root not found: {root}")
    
    print(f"[build_noise_cuda] Searching for noise_cuda setup.py in {root}")
    setup_dir = find_noise_cuda_setup(root)
    print(f"[build_noise_cuda] Found setup.py at: {setup_dir}")
    
    # Create temporary build directory (since plan2scene is read-only)
    with tempfile.TemporaryDirectory(prefix="noise_cuda_build_") as temp_dir:
        build_dir = Path(temp_dir)
        print(f"[build_noise_cuda] Using temporary build directory: {build_dir}")
        
        # Copy source files to writable location
        for src_file in setup_dir.glob("*"):
            if src_file.is_file():
                shutil.copy2(src_file, build_dir / src_file.name)
                print(f"  Copied: {src_file.name}")
        
        # Prepare environment
        env = os.environ.copy()
        env.setdefault("TORCH_CUDA_ARCH_LIST", cuda_arch_list)
        
        # Show environment info
        print("\n" + "=" * 70)
        print("Build Environment:")
        print("=" * 70)
        print(f"Python: {sys.executable}")
        print(f"Working directory: {build_dir}")
        print(f"TORCH_CUDA_ARCH_LIST: {env['TORCH_CUDA_ARCH_LIST']}")
        print(f"CUDA_HOME: {env.get('CUDA_HOME', 'not set')}")
        print("=" * 70 + "\n")
        
        # Build command
        cmd = [sys.executable, "setup.py", "install"]
        
        print(f"[build_noise_cuda] Running: {' '.join(cmd)}")
        print("=" * 70)
        
        result = subprocess.run(
            cmd,
            cwd=build_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print("\n" + "=" * 70)
            print("BUILD FAILED")
            print("=" * 70)
            raise SystemExit(f"noise_cuda build failed with exit code {result.returncode}")
        
        print("\n" + "=" * 70)
        print("BUILD SUCCESS")
        print("=" * 70)
        print("[build_noise_cuda] noise_cuda extension built and installed successfully")


if __name__ == "__main__":
    # Get Plan2Scene root from environment or use default
    plan2scene_root = os.getenv("PLAN2SCENE_ROOT", "/plan2scene")
    
    # Allow overriding CUDA arch list via environment
    cuda_arch_list = os.getenv("TORCH_CUDA_ARCH_LIST", "8.6")
    
    print("=" * 70)
    print("Plan2Scene noise_cuda CUDA Extension Builder")
    print("=" * 70)
    print(f"Plan2Scene root: {plan2scene_root}")
    print(f"CUDA architecture: {cuda_arch_list}")
    print("=" * 70 + "\n")
    
    try:
        build_noise_cuda(plan2scene_root, cuda_arch_list)
    except Exception as e:
        print(f"\n[build_noise_cuda] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
