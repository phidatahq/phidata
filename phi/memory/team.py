from typing import Dict, List, Any, Optional, Tuple

from pydantic import BaseModel

from phi.llm.message import Message
from phi.llm.references import References


class TeamMemory(BaseModel):
    # Messages between the user and the Workflow.
    # Note: the llm prompts are stored in the llm_messages
    chat_history: List[Message] = []
    # Prompts sent to the LLM and the LLM responses.
    llm_messages: List[Message] = []
    # References from the vector database.
    references: List[References] = []

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
