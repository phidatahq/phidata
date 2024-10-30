"""
Agents 101 package initialization.
Common imports and configurations for the agents.
"""

from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
TMP_DIR = BASE_DIR / "tmp"

# Create tmp directory if it doesn't exist
TMP_DIR.mkdir(exist_ok=True)

# Common configurations
DEFAULT_MODEL_ID = "gpt-4o"
DEFAULT_DB_PATH = str(TMP_DIR / "agents.db")

