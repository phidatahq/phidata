"""
Utility functions for agents
"""

import logging
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_directory(path: str) -> Path:
    """Ensure directory exists and return Path object"""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def check_api_keys() -> bool:
    """Check if required API keys are set"""
    import os
    required_keys = ['OPENAI_API_KEY']
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        logger.error(f"Missing required API keys: {', '.join(missing_keys)}")
        return False
    return True

def get_db_path(db_name: str, base_dir: Optional[str] = None) -> Path:
    """Get database path"""
    if base_dir is None:
        base_dir = Path(__file__).parent / "tmp"
    
    db_path = Path(base_dir) / db_name
    ensure_directory(db_path.parent)
    return db_path
