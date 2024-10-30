"""
Common configurations for agents
"""

from pathlib import Path
from typing import Dict, Any

# Base paths
BASE_DIR = Path(__file__).parent
TMP_DIR = BASE_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)

# Database configurations
DB_CONFIG = {
    "sqlite": {
        "db_file": str(TMP_DIR / "agents.db")
    },
    "lancedb": {
        "uri": str(TMP_DIR / "lancedb")
    }
}

# Agent common configurations
AGENT_COMMON_CONFIG: Dict[str, Any] = {
    "markdown": True,
    "show_tool_calls": True,
}

# Model configurations
MODEL_CONFIG = {
    "default_model": "gpt-4o"
}

# Knowledge base configurations
KNOWLEDGE_BASE_CONFIG = {
    "pdf_urls": [
        "https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"
    ]
}
