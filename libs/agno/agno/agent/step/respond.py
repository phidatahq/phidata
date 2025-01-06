from __future__ import annotations

from typing import AsyncIterator, Iterator, cast

from agno.agent.step import AgentStep
from agno.models.base import Model
from agno.models.response import ModelResponse, ModelResponseEvent
from agno.run.messages import RunMessages
from agno.run.response import RunEvent, RunResponse


class Respond(AgentStep):
    def __init__(self):
        pass

    def run(
        self,
        agent: "Agent",  # type: ignore  # noqa: F821
        run_messages: RunMessages,
    ) -> Iterator[RunResponse]:
        from agno.agent import Agent

        agent = cast(Agent, agent)

        # Yield a step started event
        if agent.stream_intermediate_steps:
            yield agent.create_run_response(content="Response started", event=RunEvent.step_started)

        model_response: ModelResponse
        agent.model = cast(Model, agent.model)
        if agent.stream:
            model_response = ModelResponse(content="")
            for model_response_chunk in agent.model.response_stream(messages=run_messages.messages):
                # If the model response is an assistant_response, yield a RunResponse with the content
                if model_response_chunk.event == ModelResponseEvent.assistant_response.value:
                    if model_response_chunk.content is not None:
                        model_response.content += model_response_chunk.content
                        # Update the agent.run_response with the content
                        agent.run_response.content = model_response.content
                        agent.run_response.created_at = model_response_chunk.created_at
                        yield agent.create_run_response(
                            content=model_response_chunk.content, created_at=model_response_chunk.created_at
                        )
                # If the model response is a tool_call_started, add the tool call to the run_response
                elif model_response_chunk.event == ModelResponseEvent.tool_call_started.value:
                    # Add tool call to the agent.run_response
                    tool_call_dict = model_response_chunk.tool_call
                    if tool_call_dict is not None:
                        # Add tool call to the agent.run_response
                        if agent.run_response.tools is None:
                            agent.run_response.tools = []
                        agent.run_response.tools.append(tool_call_dict)
                    # If the agent is streaming intermediate steps, yield a RunResponse with the tool_call_started event
                    if agent.stream_intermediate_steps:
                        yield agent.create_run_response(
                            content=model_response_chunk.content,
                            event=RunEvent.tool_call_started,
                        )
                # If the model response is a tool_call_completed, update the existing tool call in the run_response
                elif model_response_chunk.event == ModelResponseEvent.tool_call_completed.value:
                    # Update the existing tool call in the agent.run_response
                    tool_call_dict = model_response_chunk.tool_call
                    if tool_call_dict is not None and agent.run_response.tools:
                        tool_call_id_to_update = tool_call_dict["tool_call_id"]
                        # Use a dictionary comprehension to create a mapping of tool_call_id to index
                        tool_call_index_map = {tc["tool_call_id"]: i for i, tc in enumerate(agent.run_response.tools)}
                        # Update the tool call if it exists
                        if tool_call_id_to_update in tool_call_index_map:
                            agent.run_response.tools[tool_call_index_map[tool_call_id_to_update]] = tool_call_dict
                    # If the agent is streaming intermediate steps, yield a RunResponse with the tool_call_completed event
                    if agent.stream_intermediate_steps:
                        yield agent.create_run_response(
                            content=model_response_chunk.content,
                            event=RunEvent.tool_call_completed,
                        )
        else:
            # Get the model response
            model_response = agent.model.response(messages=run_messages.messages)
            # Handle structured outputs
            if agent.response_model is not None and agent.structured_outputs and model_response.parsed is not None:
                # Update the agent.run_response content with the structured output
                agent.run_response.content = model_response.parsed
                # Update the agent.run_response content_type with the structured output class name
                agent.run_response.content_type = agent.response_model.__name__
            else:
                # Update the agent.run_response content with the model response content
                agent.run_response.content = model_response.content
            # Update the agent.run_response audio with the model response audio
            if model_response.audio is not None:
                agent.run_response.audio = model_response.audio
            # Update the agent.run_response messages with the messages
            agent.run_response.messages = run_messages.messages
            # Update the agent.run_response created_at with the model response created_at
            agent.run_response.created_at = model_response.created_at
            # Yield the agent.run_response
            yield agent.run_response

    async def arun(
        self,
        agent: "Agent",  # type: ignore  # noqa: F821
        run_messages: RunMessages,
    ) -> AsyncIterator[RunResponse]:
        from agno.agent import Agent

        agent = cast(Agent, agent)

        # Yield a step started event
        if agent.stream_intermediate_steps:
            yield agent.create_run_response(content="Response started", event=RunEvent.step_started)

        model_response: ModelResponse
        agent.model = cast(Model, agent.model)
        if agent.stream:
            model_response = ModelResponse(content="")
            model_response_stream = self.model.aresponse_stream(messages=run_messages.messages)
            async for model_response_chunk in model_response_stream:  # type: ignore
                # If the model response is an assistant_response, yield a RunResponse with the content
                if model_response_chunk.event == ModelResponseEvent.assistant_response.value:
                    if model_response_chunk.content is not None:
                        model_response.content += model_response_chunk.content
                        # Update the agent.run_response with the content
                        agent.run_response.content = model_response.content
                        agent.run_response.created_at = model_response_chunk.created_at
                        yield agent.create_run_response(
                            content=model_response_chunk.content, created_at=model_response_chunk.created_at
                        )
                # If the model response is a tool_call_started, add the tool call to the run_response
                elif model_response_chunk.event == ModelResponseEvent.tool_call_started.value:
                    # Add tool call to the agent.run_response
                    tool_call_dict = model_response_chunk.tool_call
                    if tool_call_dict is not None:
                        # Add tool call to the agent.run_response
                        if agent.run_response.tools is None:
                            agent.run_response.tools = []
                        agent.run_response.tools.append(tool_call_dict)
                    # If the agent is streaming intermediate steps, yield a RunResponse with the tool_call_started event
                    if agent.stream_intermediate_steps:
                        yield agent.create_run_response(
                            content=model_response_chunk.content,
                            event=RunEvent.tool_call_started,
                        )
                # If the model response is a tool_call_completed, update the existing tool call in the run_response
                elif model_response_chunk.event == ModelResponseEvent.tool_call_completed.value:
                    # Update the existing tool call in the agent.run_response
                    tool_call_dict = model_response_chunk.tool_call
                    if tool_call_dict is not None and agent.run_response.tools:
                        tool_call_id_to_update = tool_call_dict["tool_call_id"]
                        # Use a dictionary comprehension to create a mapping of tool_call_id to index
                        tool_call_index_map = {tc["tool_call_id"]: i for i, tc in enumerate(agent.run_response.tools)}
                        # Update the tool call if it exists
                        if tool_call_id_to_update in tool_call_index_map:
                            agent.run_response.tools[tool_call_index_map[tool_call_id_to_update]] = tool_call_dict
                    # If the agent is streaming intermediate steps, yield a RunResponse with the tool_call_completed event
                    if agent.stream_intermediate_steps:
                        yield agent.create_run_response(
                            content=model_response_chunk.content,
                            event=RunEvent.tool_call_completed,
                        )
        else:
            # Get the model response
            model_response = await agent.model.aresponse(messages=run_messages.messages)
            # Handle structured outputs
            if agent.response_model is not None and agent.structured_outputs and model_response.parsed is not None:
                # Update the agent.run_response content with the structured output
                agent.run_response.content = model_response.parsed
                # Update the agent.run_response content_type with the structured output class name
                agent.run_response.content_type = agent.response_model.__name__
            else:
                # Update the agent.run_response content with the model response content
                agent.run_response.content = model_response.content
            # Update the agent.run_response audio with the model response audio
            if model_response.audio is not None:
                agent.run_response.audio = model_response.audio
            # Update the agent.run_response messages with the messages
            agent.run_response.messages = run_messages.messages
            # Update the agent.run_response created_at with the model response created_at
            agent.run_response.created_at = model_response.created_at
            # Yield the agent.run_response
            yield agent.run_response
