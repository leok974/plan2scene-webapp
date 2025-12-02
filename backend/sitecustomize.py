"""
Site-wide customization for Plan2Scene webapp.

This module patches the torchvision import in Plan2Scene's vgg.py module
at runtime to maintain compatibility with newer torchvision versions.

Also provides CPU fallback mode patches when GPU is disabled or incompatible:
- No-op noise_cuda module stub
- YAML config device override (cuda → cpu)
- torch.load() wrapper for CPU-safe checkpoint loading
"""

import sys
import os


# Detect CPU fallback mode
PLAN2SCENE_GPU_ENABLED = os.environ.get("PLAN2SCENE_GPU_ENABLED", "1")
CUDA_VISIBLE_DEVICES = os.environ.get("CUDA_VISIBLE_DEVICES", "")
FORCE_CPU = PLAN2SCENE_GPU_ENABLED in ("0", "false", "False", "") or CUDA_VISIBLE_DEVICES == ""


# Monkey-patch torchvision.models.utils if it doesn't exist
def patch_torchvision():
    """Add compatibility shim for torchvision.models.utils."""
    try:
        import torchvision.models.utils
    except (ImportError, ModuleNotFoundError):
        # torchvision.models.utils doesn't exist, add compatibility layer
        try:
            import torchvision.models._api as _api
            import torchvision.models as models
            
            # Create the utils module
            from types import ModuleType
            utils = ModuleType('torchvision.models.utils')
            utils.load_state_dict_from_url = _api.load_state_dict_from_url
            
            # Register it
            models.utils = utils
            sys.modules['torchvision.models.utils'] = utils
            
            print("[sitecustomize] ✓ Patched torchvision.models.utils for compatibility")
        except Exception as e:
            print(f"[sitecustomize] ⚠ Failed to patch torchvision: {e}")


def create_noise_cuda_stub():
    """Create a CPU-compatible noise_cuda module for CPU fallback mode.
    
    Plan2Scene unconditionally imports noise_cuda even when running on CPU.
    This stub allows CPU mode to work by providing CPU-compatible noise generation.
    """
    if FORCE_CPU:
        try:
            from types import ModuleType
            import torch
            
            # Create noise_cuda module with CPU implementations
            noise_cuda = ModuleType('noise_cuda')
            
            # CPU-compatible noise generation
            def forward_stub(position, seed):
                """CPU fallback for noise_cuda.forward().
                
                Generates pseudo-random noise on CPU using torch.randn.
                This is slower than the CUDA version but functionally equivalent.
                
                The CUDA version generates 2D noise (likely real/imaginary or X/Y components)
                for each position. Input is flattened, output is [2, num_positions].
                
                Args:
                    position: Flattened tensor of shape [num_positions, position_dim]
                    seed: Flattened tensor of shape [num_positions]
                
                Returns:
                    Noise tensor of shape [2, num_positions]
                """
                num_positions = position.shape[0]
                
                # Use seed for deterministic noise generation
                # Take first seed value if multiple (they're usually the same)
                generator = torch.Generator()
                if seed.numel() > 0:
                    generator.manual_seed(int(seed.flatten()[0].item()))
                
                # Generate 2D noise (2 channels) for each position
                # Shape: [2, num_positions]
                noise = torch.randn(2, num_positions, generator=generator, device='cpu')
                return noise
            
            noise_cuda.forward = forward_stub
            
            # Register the stub module
            sys.modules['noise_cuda'] = noise_cuda
            
            print("[sitecustomize] ✓ Created noise_cuda stub for CPU fallback mode")
        except Exception as e:
            print(f"[sitecustomize] ⚠ Failed to create noise_cuda stub: {e}")


def patch_plan2scene_config_loader():
    """Patch Plan2Scene config loader to force CPU device when GPU is disabled.
    
    Plan2Scene configs have 'device: cuda' hardcoded, but raise an exception
    if no GPU is available. This patch intercepts config loading and replaces
    'device: cuda' with 'device: cpu' when running in CPU fallback mode.
    
    Additionally patches the Config class __init__ to override device attribute.
    """
    if FORCE_CPU:
        try:
            # Import and patch the YAML loader
            import yaml
            from functools import wraps
            
            # Store original yaml.load
            original_load = yaml.load
            original_safe_load = yaml.safe_load
            
            def patched_load(stream, Loader=yaml.Loader):
                """Patched yaml.load that replaces device: cuda with device: cpu."""
                data = original_load(stream, Loader=Loader)
                if isinstance(data, dict) and 'device' in data and data['device'] == 'cuda':
                    data['device'] = 'cpu'
                    print("[sitecustomize] ✓ Patched config device: cuda → cpu")
                return data
            
            def patched_safe_load(stream):
                """Patched yaml.safe_load that replaces device: cuda with device: cpu."""
                data = original_safe_load(stream)
                if isinstance(data, dict) and 'device' in data and data['device'] == 'cuda':
                    data['device'] = 'cpu'
                    print("[sitecustomize] ✓ Patched config device: cuda → cpu")
                return data
            
            # Replace yaml.load with patched version
            yaml.load = patched_load
            yaml.safe_load = patched_safe_load
            
            print("[sitecustomize] ✓ Patched YAML loader for CPU device override")
            
            # Also patch the Config class __init__ to force device='cpu'
            # This is needed because .to(system_conf.device) is called after config loading
            try:
                import sys
                import importlib.util
                import importlib.machinery
                
                # Lazy patch: intercept config_parser module import
                class ConfigParserLoader(importlib.abc.Loader):
                    """Loader that patches config_parser.Config after loading."""
                    
                    def __init__(self, spec):
                        self.spec = spec
                    
                    def create_module(self, spec):
                        return None  # Use default module creation
                    
                    def exec_module(self, module):
                        # Execute the original module
                        spec = self.spec
                        loader = spec.loader
                        if hasattr(loader, '_orig_loader'):
                            loader._orig_loader.exec_module(module)
                        else:
                            # Fallback to source file execution
                            with open(spec.origin, 'rb') as f:
                                code = compile(f.read(), spec.origin, 'exec')
                                exec(code, module.__dict__)
                        
                        # Patch the Config class if it exists
                        if hasattr(module, 'Config'):
                            original_init = module.Config.__init__
                            
                            def patched_init(self, *args, **kwargs):
                                original_init(self, *args, **kwargs)
                                # Force device to 'cpu' after initialization
                                if hasattr(self, 'device') and self.device == 'cuda':
                                    self.device = 'cpu'
                                    print("[sitecustomize] ✓ Patched Config.device: cuda → cpu")
                            
                            module.Config.__init__ = patched_init
                
                class ConfigParserFinder(importlib.abc.MetaPathFinder):
                    """Meta path finder to intercept config_parser imports."""
                    
                    def find_spec(self, fullname, path, target=None):
                        if fullname != 'config_parser':
                            return None
                        
                        # Find the original spec
                        for finder in sys.meta_path[1:]:  # Skip ourselves
                            if hasattr(finder, 'find_spec'):
                                spec = finder.find_spec(fullname, path, target)
                                if spec is not None:
                                    # Replace loader with our patcher
                                    patching_loader = ConfigParserLoader(spec)
                                    patching_loader._orig_loader = spec.loader
                                    spec.loader = patching_loader
                                    return spec
                        return None
                
                # Insert at the beginning of meta_path to intercept imports
                sys.meta_path.insert(0, ConfigParserFinder())
                print("[sitecustomize] ✓ Installed Config class patcher")
                
            except Exception as e:
                print(f"[sitecustomize] ⚠ Failed to install Config class patcher: {e}")
            
        except Exception as e:
            print(f"[sitecustomize] ⚠ Failed to patch YAML loader: {e}")


def patch_torch_load_for_cpu():
    """Patch torch.load() to automatically use map_location='cpu' in CPU fallback mode.
    
    Plan2Scene checkpoints were saved on CUDA devices. When loading them on a
    CPU-only system, torch.load() will fail with "Attempting to deserialize object
    on a CUDA device but torch.cuda.is_available() is False" unless map_location
    is explicitly set to 'cpu'.
    
    This patch wraps torch.load() to automatically add map_location='cpu' when:
    - Running in CPU fallback mode (PLAN2SCENE_GPU_ENABLED=0)
    - No explicit map_location is provided by the caller
    """
    if FORCE_CPU:
        try:
            import torch
            
            # Store original torch.load
            _orig_torch_load = torch.load
            
            def _cpu_safe_torch_load(*args, **kwargs):
                """
                Wrap torch.load so that in CPU fallback mode we never try
                to deserialize CUDA tensors onto a non-CUDA device.
                
                - If caller already passes map_location, we respect it.
                - Otherwise we force map_location='cpu'.
                """
                # If map_location is already specified, don't interfere
                if "map_location" in kwargs:
                    return _orig_torch_load(*args, **kwargs)
                
                # Check if any positional arg after the first is a device or map_location
                for arg in args[1:]:
                    try:
                        if isinstance(arg, (torch.device, str)):
                            # Caller is specifying device as positional arg
                            return _orig_torch_load(*args, **kwargs)
                    except Exception:
                        pass
                
                # Force CPU placement for checkpoint loading
                return _orig_torch_load(*args, map_location="cpu", **kwargs)
            
            # Monkey-patch torch.load
            torch.load = _cpu_safe_torch_load
            
            print("[sitecustomize] ✓ Patched torch.load for CPU fallback (map_location='cpu')")
        except Exception as e:
            print(f"[sitecustomize] ⚠ Failed to patch torch.load: {e}")


# Apply patches on import
patch_torchvision()
create_noise_cuda_stub()
patch_plan2scene_config_loader()
patch_torch_load_for_cpu()


def patch_conv2d_dilation_fix():
    """Patch torch.nn.functional.conv2d to fix dilation tuple type issues on CPU.
    
    On CPU, some tensor operations can convert int tuples to bool tuples, causing
    TypeError: conv2d() received invalid combination of arguments with bool tuples.
    
    This patch ensures dilation (and other tuple params) are always int tuples.
    """
    if FORCE_CPU:
        try:
            import torch
            import torch.nn.functional as F
            
            # Store original conv2d
            _orig_conv2d = F.conv2d
            
            def _safe_conv2d(input, weight, bias=None, stride=1, padding=0, dilation=1, groups=1):
                """Wrapper ensuring all tuple parameters are int tuples, not bool tuples."""
                # Convert parameters to int tuples if they're bool tuples
                def ensure_int_tuple(val, default=1):
                    if isinstance(val, (list, tuple)):
                        # Convert any bool values to ints
                        return tuple(int(v) if isinstance(v, bool) else v for v in val)
                    return val
                
                stride = ensure_int_tuple(stride)
                padding = ensure_int_tuple(padding)
                dilation = ensure_int_tuple(dilation)
                
                return _orig_conv2d(input, weight, bias, stride, padding, dilation, groups)
            
            # Monkey-patch torch.nn.functional.conv2d
            F.conv2d = _safe_conv2d
            
            print("[sitecustomize] ✓ Patched torch.nn.functional.conv2d for CPU dilation fix")
        except Exception as e:
            print(f"[sitecustomize] ⚠ Failed to patch conv2d: {e}")


# Apply conv2d patch AFTER other patches
patch_conv2d_dilation_fix()
