from dataclasses import dataclass, field
from typing import List, Optional

from agno.models.message import Message


@dataclass
class RunMessages:
    """Container for messages used in an Agent run.

    Attributes:
        messages: List of all messages to send to the model
        system_message: The system message for this run
        user_message: The user message for this run
    """

    system_message: Optional[Message] = None
    user_message: Optional[Message] = None
    messages: List[Message] = field(default_factory=list)
