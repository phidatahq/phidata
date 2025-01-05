from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class Memory:
    """Model for Agent Memories"""

    memory: str
    id: Optional[str] = None
    topic: Optional[str] = None
    input: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
