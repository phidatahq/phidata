from __future__ import annotations

from typing import Iterator, cast

from agno.agent.respond import Respond
from agno.agent.step import AgentStep
from agno.models.message import Message
from agno.run.messages import RunMessages
from agno.run.response import RunEvent, RunResponse


class Task(AgentStep):
    def __init__(self, instructions: str):
        self.instructions = instructions

    def run(
        self,
        agent: "Agent",  # type: ignore  # noqa: F821
        run_messages: RunMessages,
    ) -> Iterator[RunResponse]:
        from phi.agent import Agent

        agent = cast(Agent, agent)

        # Yield a step started event
        if agent.stream_intermediate_steps:
            yield agent.create_run_response(content="Task started", event=RunEvent.step_started)

        # If instructions are provided, add them to the messages
        if self.instructions:
            run_messages.messages.append(
                Message(
                    role=agent.user_message_role,
                    content=f"Task: {self.instructions}",
                    add_to_agent_memory=False,
                )
            )

        # Run the Respond step
        yield from Respond().run(agent, run_messages)
