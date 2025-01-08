from __future__ import annotations

from typing import Any, Iterator

from agno.run.messages import RunMessages
from agno.run.response import RunResponse


class AgentStep:
    def __init__(self):
        """Initialize the AgentStep"""
        pass

    def run(
        self,
        agent: "Agent",  # type: ignore  # noqa: F821
        run_messages: RunMessages,
    ) -> Iterator[RunResponse]:
        """
        Runs the AgentStep for the given agent and the provided messages.

        Args:
            agent (Agent): The agent for which the step is being run.
            run_messages (RunMessages): The messages to process during the step.

        Returns:
            Iterator[RunResponse]: An iterator of RunResponse objects.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("run method not implemented")

    async def arun(
        self,
        agent: "Agent",  # type: ignore  # noqa: F821
        run_messages: RunMessages,
    ) -> Any:
        """
        Runs the AgentStep for the given agent and the provided messages asynchronously.

        Args:
            agent (Agent): The agent for which the step is being run.
            run_messages (RunMessages): The messages to process during the step.

        Returns:
            AsyncIterator[RunResponse]: An async iterator of RunResponse objects.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("arun method not implemented")
