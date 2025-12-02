"""
Plan2Scene command execution utilities.

Provides reusable helpers for running Plan2Scene and R2V-related commands
with proper error handling, logging, and environment setup.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


class Plan2SceneCommandError(Exception):
    """Custom exception for Plan2Scene command failures."""
    
    def __init__(self, message: str, command: List[str], stderr: str, returncode: int):
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(message)
    
    def __str__(self):
        return (
            f"{self.args[0]}\n"
            f"Command: {' '.join(self.command)}\n"
            f"Return code: {self.returncode}\n"
            f"Stderr: {self.stderr}"
        )


@dataclass
class CommandResult:
    """Result of a command execution."""
    returncode: int
    stdout: str
    stderr: str
    command: List[str]


def run_plan2scene_command(
    args: List[str],
    cwd: Optional[Path] = None,
    env_overrides: Optional[Dict[str, str]] = None,
    check: bool = True,
    capture_output: bool = True,
    use_gpu: Optional[bool] = None
) -> CommandResult:
    """
    Execute a Plan2Scene-related command with proper environment setup.
    
    Args:
        args: Command arguments (e.g., ["python", "script.py", "arg1"])
        cwd: Working directory for command execution (defaults to PLAN2SCENE_ROOT)
        env_overrides: Additional environment variables to set
        check: Raise Plan2SceneCommandError on non-zero exit code
        capture_output: Capture stdout/stderr for logging
        use_gpu: Whether to use GPU (defaults to settings.plan2scene_gpu_enabled)
    
    Returns:
        CommandResult with execution details
    
    Raises:
        Plan2SceneCommandError: If command fails and check=True
    """
    # Default to Plan2Scene root if no cwd specified
    if cwd is None:
        cwd = settings.PLAN2SCENE_ROOT
    
    # Default use_gpu from config if not specified
    if use_gpu is None:
        use_gpu = settings.plan2scene_gpu_enabled
    
    # 🔑 CRITICAL: Inherit environment from parent process (including PYTHONPATH set in Dockerfile)
    import os
    env = os.environ.copy()
    
    # CPU fallback: Hide GPUs from PyTorch if GPU is disabled
    if not use_gpu:
        env["CUDA_VISIBLE_DEVICES"] = ""
        env["FORCE_CPU"] = "1"
        logger.info("CPU fallback mode enabled: hiding GPUs from PyTorch")
    
    # Apply any user-provided environment overrides
    if env_overrides:
        env.update(env_overrides)
    
    # Log the command
    logger.info(f"Executing Plan2Scene command: {' '.join(args)}")
    logger.info(f"Working directory: {cwd}")
    logger.info(f"PYTHONPATH: {env.get('PYTHONPATH', 'not set')}")
    
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            env=env,
            capture_output=capture_output,
            text=True,
            check=False  # We'll handle the check ourselves for better errors
        )
        
        # Log output
        if result.stdout:
            logger.debug(f"Command stdout:\n{result.stdout}")
        if result.stderr:
            logger.debug(f"Command stderr:\n{result.stderr}")
        
        # Check for errors if requested
        if check and result.returncode != 0:
            error_msg = f"Plan2Scene command failed with return code {result.returncode}"
            raise Plan2SceneCommandError(
                message=error_msg,
                command=args,
                stderr=result.stderr,
                returncode=result.returncode
            )
        
        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=args
        )
    
    except FileNotFoundError as e:
        error_msg = f"Command not found: {args[0]}"
        logger.error(error_msg)
        raise Plan2SceneCommandError(
            message=error_msg,
            command=args,
            stderr=str(e),
            returncode=-1
        )


def run_r2v_command(
    args: List[str],
    cwd: Optional[Path] = None,
    env_overrides: Optional[Dict[str, str]] = None,
    check: bool = True,
    use_gpu: Optional[bool] = None
) -> CommandResult:
    """
    Execute an R2V-to-Plan2Scene command with proper environment setup.
    
    Similar to run_plan2scene_command but uses R2V_TO_PLAN2SCENE_ROOT.
    
    Args:
        args: Command arguments
        cwd: Working directory (defaults to R2V_TO_PLAN2SCENE_ROOT)
        env_overrides: Additional environment variables
        check: Raise error on non-zero exit
        use_gpu: Whether to use GPU (defaults to settings.plan2scene_gpu_enabled)
    
    Returns:
        CommandResult with execution details
    """
    if cwd is None:
        cwd = settings.R2V_TO_PLAN2SCENE_ROOT
    
    # Default use_gpu from config if not specified
    if use_gpu is None:
        use_gpu = settings.plan2scene_gpu_enabled
    
    # Build environment with R2V code path
    import os
    env = os.environ.copy()
    
    # CPU fallback: Hide GPUs from PyTorch if GPU is disabled
    if not use_gpu:
        env["CUDA_VISIBLE_DEVICES"] = ""
        env["FORCE_CPU"] = "1"
        logger.info("CPU fallback mode enabled (R2V): hiding GPUs from PyTorch")
    
    # Add R2V code/src to PYTHONPATH
    r2v_code_path = settings.R2V_TO_PLAN2SCENE_ROOT / "code" / "src"
    if r2v_code_path.exists():
        pythonpath_entries = [str(r2v_code_path)]
        if "PYTHONPATH" in env:
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    
    if env_overrides:
        env.update(env_overrides)
    
    logger.info(f"Executing R2V command: {' '.join(args)}")
    logger.info(f"Working directory: {cwd}")
    
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stdout:
            logger.debug(f"R2V stdout:\n{result.stdout}")
        if result.stderr:
            logger.debug(f"R2V stderr:\n{result.stderr}")
        
        if check and result.returncode != 0:
            error_msg = f"R2V command failed with return code {result.returncode}"
            raise Plan2SceneCommandError(
                message=error_msg,
                command=args,
                stderr=result.stderr,
                returncode=result.returncode
            )
        
        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=args
        )
    
    except FileNotFoundError as e:
        error_msg = f"R2V command not found: {args[0]}"
        logger.error(error_msg)
        raise Plan2SceneCommandError(
            message=error_msg,
            command=args,
            stderr=str(e),
            returncode=-1
        )
