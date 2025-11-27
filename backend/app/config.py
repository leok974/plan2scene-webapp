import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MODE: str = os.getenv("MODE", "demo")  # demo or gpu
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    JOBS_DIR: str = os.getenv("JOBS_DIR", "static/jobs")
    PLAN2SCENE_REPO: str = os.getenv("PLAN2SCENE_REPO", "../plan2scene")

    class Config:
        env_file = ".env"

settings = Settings()
