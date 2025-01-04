from typing import Any, List, Iterator, Optional, AsyncIterator

from agno.model.message import Message
from agno.run.response import RunResponse


class AgentStep:
    def __init__(self):
        """Initialize the AgentStep"""
        pass

    def run(
        self,
        agent: Any,
        messages: List[Message],
        user_messages: List[Message],
        system_message: Optional[Message] = None,
    ) -> Iterator[RunResponse]:
        """
        Runs the AgentStep for the given agent and the provided messages.
        Args:
            agent (Agent): The agent for which the step is being run.
            messages (List[Message]): The list of all messages to process during the step.
            user_messages (List[Message]): The list of user messages to process during the step.
            system_message (Optional[Message]): The system message to process during the step.
        Returns:
            Iterator[RunResponse]: An iterator over RunResponse objects.
        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("run_step method not implemented")

    async def areun(
        self,
        agent: Any,
        messages: List[Message],
        user_messages: List[Message],
        system_message: Optional[Message] = None,
    ) -> AsyncIterator[RunResponse]:
        """
        Runs the AgentStep for the given agent and the provided messages asynchronously.
        """
        raise NotImplementedError("areun method not implemented")
