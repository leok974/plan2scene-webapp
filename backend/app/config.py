import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Execution mode
    MODE: str = os.getenv("MODE", "demo")  # demo or gpu
    
    # Pipeline mode for GPU execution
    PIPELINE_MODE: str = os.getenv("PIPELINE_MODE", "preprocessed")  # preprocessed or full
    
    # Local storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    JOBS_DIR: str = os.getenv("JOBS_DIR", "static/jobs")
    
    # Plan2Scene repository paths
    PLAN2SCENE_ROOT: Path = Path(os.getenv("PLAN2SCENE_ROOT", "../plan2scene"))
    PLAN2SCENE_DATA_ROOT: Path = Path(os.getenv("PLAN2SCENE_DATA_ROOT", ""))  # Auto-computed if empty
    
    # R2V-to-Plan2Scene repository path
    R2V_TO_PLAN2SCENE_ROOT: Path = Path(os.getenv("R2V_TO_PLAN2SCENE_ROOT", "../r2v-to-plan2scene"))
    
    # Raster-to-Vector repository path (optional, for future phase)
    RASTER_TO_VECTOR_ROOT: Path = Path(os.getenv("RASTER_TO_VECTOR_ROOT", "../raster-to-vector"))
    
    # GPU availability flag - set to False to force CPU fallback
    plan2scene_gpu_enabled: bool = Field(True, env="PLAN2SCENE_GPU_ENABLED")

    class Config:
        env_file = ".env"
    
    @property
    def plan2scene_data_root(self) -> Path:
        """Compute Plan2Scene data root, defaulting to PLAN2SCENE_ROOT/data if not explicitly set."""
        if self.PLAN2SCENE_DATA_ROOT and self.PLAN2SCENE_DATA_ROOT != Path(""):
            return self.PLAN2SCENE_DATA_ROOT
        return self.PLAN2SCENE_ROOT / "data"
    
    @property
    def plan2scene_code_root(self) -> Path:
        """Return the code/src directory of Plan2Scene for PYTHONPATH."""
        return self.PLAN2SCENE_ROOT / "code" / "src"

settings = Settings()

