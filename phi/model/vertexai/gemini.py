import json
from dataclasses import dataclass, field
from typing import Optional, List, Iterator, Dict, Any, Union, Callable

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import Function, FunctionCall
from phi.tools import Tool, Toolkit
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from vertexai.generative_models import (
        GenerativeModel,
        GenerationResponse,
        FunctionDeclaration,
        Tool as GeminiTool,
        Candidate as GenerationResponseCandidate,
        Content as GenerationResponseContent,
        Part as GenerationResponsePart,
    )
except ImportError:
    logger.error("`google-cloud-aiplatform` not installed")
    raise

class Gemini(Model):
    name: str = "Gemini"
    model: str = "gemini-1.5-flash-002"
    provider: str = "VertexAI"

    generation_config: Optional[Any] = None
    safety_settings: Optional[Any] = None
    function_declarations: Optional[List[FunctionDeclaration]] = None
    generative_model_request_params: Optional[Dict[str, Any]] = None
    generative_model: Optional[GenerativeModel] = None

    def get_client(self) -> GenerativeModel:
        if self.generative_model is None:
            self.generative_model = GenerativeModel(model_name=self.model, **self.request_kwargs)
        return self.generative_model

    @property
    def request_kwargs(self) -> Dict[str, Any]:
        _request_params: Dict[str, Any] = {}
        if self.generation_config:
            _request_params["generation_config"] = self.generation_config
        if self.safety_settings:
            _request_params["safety_settings"] = self.safety_settings
        if self.generative_model_request_params:
            _request_params.update(self.generative_model__request_params)
        if self.function_declarations:
            _request_params["tools"] = [GeminiTool(function_declarations=self.function_declarations)]
        return _request_params

    def convert_messages_to_contents(self, messages: List[Message]) -> List[Any]:
        _contents: List[Any] = []
        for m in messages:
            if isinstance(m.content, str):
                _contents.append(m.content)
            elif isinstance(m.content, list):
                _contents.extend(m.content)
        return _contents

    def invoke(self, messages: List[Message]) -> GenerationResponse:
        return self.get_client().generate_content(contents=self.convert_messages_to_contents(messages))

    def invoke_stream(self, messages: List[Message]) -> Iterator[GenerationResponse]:
        yield from self.client.generate_content(
            contents=self.convert_messages_to_contents(messages),
            stream=True,
        )

    def response(self, messages: List[Message]) -> str:
        logger.debug("---------- VertexAI Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: GenerationResponse = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")
        # logger.debug(f"VertexAI response type: {type(response)}")
        # logger.debug(f"VertexAI response: {response}")

        # -*- Parse response
        response_candidates: List[GenerationResponseCandidate] = response.candidates
        response_content: GenerationResponseContent = response_candidates[0].content
        response_role = response_content.role
        response_parts: List[GenerationResponsePart] = response_content.parts
        response_text: Optional[str] = None
        response_function_calls: Optional[List[Dict[str, Any]]] = None

        if len(response_parts) > 1:
            logger.warning("Multiple content parts are not yet supported.")
            return "More than one response part found."

        _part_dict = response_parts[0].to_dict()
        if "text" in _part_dict:
            response_text = _part_dict.get("text")
        if "function_call" in _part_dict:
            if response_function_calls is None:
                response_function_calls = []
            response_function_calls.append(
                {
                    "type": "function",
                    "function": {
                        "name": _part_dict.get("function_call").get("name"),
                        "arguments": json.dumps(_part_dict.get("function_call").get("args")),
                    },
                }
            )

        # -*- Create assistant message
        assistant_message = Message(
            role=response_role or "assistant",
            content=response_text,
        )
        # -*- Add tool calls to assistant message
        if response_function_calls is not None:
            assistant_message.tool_calls = response_function_calls

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)
        # TODO: Add token usage to metrics

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function calls
        if assistant_message.tool_calls is not None:
            final_response = ""
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in assistant_message.tool_calls:
                _tool_call_id = tool_call.get("id")
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(role="tool", tool_call_id=_tool_call_id, content="Could not find function to call.")
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="tool", tool_call_id=_tool_call_id, content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    final_response += f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    final_response += "\nRunning:"
                    for _f in function_calls_to_run:
                        final_response += f"\n - {_f.get_call_str()}"
                    final_response += "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run)
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            # -*- Get new response using result of tool call
            final_response += self.response(messages=messages)
            return final_response
        logger.debug("---------- VertexAI Response End ----------")
        return assistant_message.get_content_string()

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- VertexAI Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_role: Optional[str] = None
        response_function_calls: Optional[List[Dict[str, Any]]] = None
        assistant_message_content = ""
        response_timer = Timer()
        response_timer.start()
        for response in self.invoke_stream(messages=messages):
            # logger.debug(f"VertexAI response type: {type(response)}")
            # logger.debug(f"VertexAI response: {response}")

            # -*- Parse response
            response_candidates: List[GenerationResponseCandidate] = response.candidates
            response_content: GenerationResponseContent = response_candidates[0].content
            if response_role is None:
                response_role = response_content.role
            response_parts: List[GenerationResponsePart] = response_content.parts
            _part_dict = response_parts[0].to_dict()

            # -*- Return text if present, otherwise get function call
            if "text" in _part_dict:
                response_text = _part_dict.get("text")
                yield response_text
                assistant_message_content += response_text

            # -*- Parse function calls
            if "function_call" in _part_dict:
                if response_function_calls is None:
                    response_function_calls = []
                response_function_calls.append(
                    {
                        "type": "function",
                        "function": {
                            "name": _part_dict.get("function_call").get("name"),
                            "arguments": json.dumps(_part_dict.get("function_call").get("args")),
                        },
                    }
                )

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(role=response_role or "assistant")
        # -*- Add content to assistant message
        if assistant_message_content != "":
            assistant_message.content = assistant_message_content
        # -*- Add tool calls to assistant message
        if response_function_calls is not None:
            assistant_message.tool_calls = response_function_calls

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function calls
        if assistant_message.tool_calls is not None:
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in assistant_message.tool_calls:
                _tool_call_id = tool_call.get("id")
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(
                        Message(role="tool", tool_call_id=_tool_call_id, content="Could not find function to call.")
                    )
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="tool", tool_call_id=_tool_call_id, content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    yield f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "\nRunning:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run)
            if len(function_call_results) > 0:
                messages.extend(function_call_results)
            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages)
        logger.debug("---------- VertexAI Response End ----------")