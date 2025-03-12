from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import os

from app.utils.logger import logger


def find_dotenv_file(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the .env file by searching in the current directory and parent directories.
    
    Args:
        start_path: The path to start searching from. Defaults to the directory of this file.
        
    Returns:
        Path to the .env file if found, None otherwise.
    """
    if start_path is None:
        start_path = Path(__file__).resolve().parent.parent.parent
    
    # Check if .env exists in the start path
    env_path = start_path / '.env'
    if env_path.exists():
        return env_path
    
    # Check if we're at the root directory
    if start_path.parent == start_path:
        return None
    
    # Recursively check parent directories
    return find_dotenv_file(start_path.parent)


def load_environment(env_path: Optional[Path] = None) -> bool:
    """
    Load environment variables from .env file.
    
    Args:
        env_path: Path to the .env file. If None, will search for it.
        
    Returns:
        True if environment variables were loaded successfully, False otherwise.
    """
    if env_path is None:
        env_path = find_dotenv_file()
    
    if env_path is None or not env_path.exists():
        logger.warning("No .env file found. Using existing environment variables.")
        return False
    
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Environment loaded from: {env_path}")
    return True 