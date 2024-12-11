import json
from typing import Optional, List, Iterator, Dict, Any, Union, Callable

from phi.llm.base import LLM
from phi.llm.message import Message
from phi.tools.function import Function, FunctionCall
from phi.tools import Tool, Toolkit
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    import google.generativeai as genai
    from google.generativeai import GenerativeModel
    from google.generativeai.types.generation_types import GenerateContentResponse
    from google.generativeai.types.content_types import FunctionDeclaration, Tool as GeminiTool
    from google.ai.generativelanguage_v1beta.types.generative_service import (
        GenerateContentResponse as ResultGenerateContentResponse,
    )
    from google.protobuf.struct_pb2 import Struct
except ImportError:
    logger.error("`google-generativeai` not installed. Please install it using `pip install google-generativeai`")
    raise


class Gemini(LLM):
    name: str = "Gemini"
    model: str = "gemini-1.5-flash"
    function_declarations: Optional[List[FunctionDeclaration]] = None
    generation_config: Optional[Any] = None
    safety_settings: Optional[Any] = None
    generative_model_kwargs: Optional[Dict[str, Any]] = None
    api_key: Optional[str] = None
    gemini_client: Optional[GenerativeModel] = None

    def conform_messages_to_gemini(self, messages: List[Message]) -> List[Dict[str, Any]]:
        converted = []
        for msg in messages:
            content = msg.content
            if content is None or content == "" or msg.role == "tool":
                role = "model" if msg.role == "system" else "user" if msg.role == "tool" else msg.role
                converted.append({"role": role, "parts": msg.parts})  # type: ignore
            else:
                if isinstance(content, str):
                    parts = [content]
                elif isinstance(content, list):
                    parts = content  # type: ignore
                else:
                    parts = [" "]
                role = "model" if msg.role == "system" else "user" if msg.role == "tool" else msg.role
                converted.append({"role": role, "parts": parts})
        return converted

    def conform_function_to_gemini(self, params: Dict[str, Any]) -> Dict[str, Any]:
        fixed_parameters = {}
        for k, v in params.items():
            if k == "properties":
                fixed_properties = {}
                for prop_k, prop_v in v.items():
                    fixed_property_type = prop_v.get("type")
                    if isinstance(fixed_property_type, list):
                        if "null" in fixed_property_type:
                            fixed_property_type.remove("null")
                        fixed_properties[prop_k] = {"type": fixed_property_type[0]}
                    else:
                        fixed_properties[prop_k] = {"type": fixed_property_type}
                fixed_parameters[k] = fixed_properties
            else:
                fixed_parameters[k] = v
        return fixed_parameters

    def add_tool(self, tool: Union[Tool, Toolkit, Callable, Dict, Function]) -> None:
        if self.function_declarations is None:
            self.function_declarations = []

        # If the tool is a Tool or Dict, add it directly to the LLM
        if isinstance(tool, Tool) or isinstance(tool, Dict):
            logger.warning(f"Tool of type: {type(tool)} is not yet supported by Gemini.")
        # If the tool is a Callable or Toolkit, add its functions to the LLM
        elif callable(tool) or isinstance(tool, Toolkit) or isinstance(tool, Function):
            if self.functions is None:
                self.functions = {}

            if isinstance(tool, Toolkit):
                self.functions.update(tool.functions)
                for func in tool.functions.values():
                    fd = FunctionDeclaration(
                        name=func.name,
                        description=func.description,
                        parameters=self.conform_function_to_gemini(func.parameters),
                    )
                    self.function_declarations.append(fd)
                logger.debug(f"Functions from {tool.name} added to LLM.")
            elif isinstance(tool, Function):
                self.functions[tool.name] = tool
                fd = FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=self.conform_function_to_gemini(tool.parameters),
                )
                self.function_declarations.append(fd)
                logger.debug(f"Function {tool.name} added to LLM.")
            elif callable(tool):
                func = Function.from_callable(tool)
                self.functions[func.name] = func
                fd = FunctionDeclaration(
                    name=func.name,
                    description=func.description,
                    parameters=self.conform_function_to_gemini(func.parameters),
                )
                self.function_declarations.append(fd)
                logger.debug(f"Function {func.name} added to LLM.")

    @property
    def client(self):
        if self.gemini_client is None:
            genai.configure(api_key=self.api_key)
            self.gemini_client = genai.GenerativeModel(model_name=self.model, **self.api_kwargs)
        return self.gemini_client

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if self.generation_config:
            kwargs["generation_config"] = self.generation_config
        if self.safety_settings:
            kwargs["safety_settings"] = self.safety_settings
        if self.generative_model_kwargs:
            kwargs.update(self.generative_model_kwargs)
        if self.function_declarations:
            kwargs["tools"] = [GeminiTool(function_declarations=self.function_declarations)]
        return kwargs

    def invoke(self, messages: List[Message]):
        return self.client.generate_content(contents=self.conform_messages_to_gemini(messages))

    def invoke_stream(self, messages: List[Message]):
        yield from self.client.generate_content(
            contents=self.conform_messages_to_gemini(messages),
            stream=True,
        )

    def response(self, messages: List[Message]) -> str:
        logger.debug("---------- Gemini Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response: GenerateContentResponse = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")
        # logger.debug(f"Gemini response type: {type(response)}")
        # logger.debug(f"Gemini response: {response}")

        # -*- Parse response
        response_content = response.candidates[0].content
        response_role = response_content.role
        response_parts = response_content.parts
        response_metrics: ResultGenerateContentResponse = response.usage_metadata
        response_function_calls: List[Dict[str, Any]] = []
        response_text: Optional[str] = None

        for part in response_parts:
            part_dict = type(part).to_dict(part)

            # -*- Extract text if present
            if "text" in part_dict:
                response_text = part_dict.get("text")

            # -*- Parse function calls
            if "function_call" in part_dict:
                response_function_calls.append(
                    {
                        "type": "function",
                        "function": {
                            "name": part_dict.get("function_call").get("name"),
                            "arguments": json.dumps(part_dict.get("function_call").get("args")),
                        },
                    }
                )

        # -*- Create assistant message
        assistant_message = Message(
            role=response_role or "model",
            content=response_text,
            parts=response_parts,
        )

        if len(response_function_calls) > 0:
            assistant_message.tool_calls = response_function_calls

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        if response_metrics:
            input_tokens = response_metrics.prompt_token_count
            output_tokens = response_metrics.candidates_token_count
            total_tokens = response_metrics.total_token_count

            if input_tokens is not None:
                assistant_message.metrics["input_tokens"] = input_tokens
                self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + input_tokens

            if output_tokens is not None:
                assistant_message.metrics["output_tokens"] = output_tokens
                self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + output_tokens

            if total_tokens is not None:
                assistant_message.metrics["total_tokens"] = total_tokens
                self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + total_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function calls
        if assistant_message.tool_calls is not None:
            final_response = assistant_message.get_content_string() or ""
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="tool", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="tool", content=_function_call.error))
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
                for result in function_call_results:
                    s = Struct()
                    s.update({"result": [result.content]})
                    function_response = genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(name=result.tool_call_name, response=s)
                    )
                    messages.append(Message(role="tool", content=result.content, parts=[function_response]))

            # -*- Get new response using result of tool call
            final_response += self.response(messages=messages)
            return final_response
        logger.debug("---------- Gemini Response End ----------")
        return assistant_message.get_content_string()

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Gemini Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_function_calls: List[Dict[str, Any]] = []
        assistant_message_content: str = ""
        response_metrics: Optional[ResultGenerateContentResponse.UsageMetadata] = None
        response_timer = Timer()
        response_timer.start()
        for response in self.invoke_stream(messages=messages):
            # logger.debug(f"Gemini response type: {type(response)}")
            # logger.debug(f"Gemini response: {response}")

            # -*- Parse response
            response_content = response.candidates[0].content
            response_role = response_content.role
            response_parts = response_content.parts

            for part in response_parts:
                part_dict = type(part).to_dict(part)

                # -*- Yield text if present
                if "text" in part_dict:
                    response_text = part_dict.get("text")
                    yield response_text
                    assistant_message_content += response_text

                # -*- Parse function calls
                if "function_call" in part_dict:
                    response_function_calls.append(
                        {
                            "type": "function",
                            "function": {
                                "name": part_dict.get("function_call").get("name"),
                                "arguments": json.dumps(part_dict.get("function_call").get("args")),
                            },
                        }
                    )
            response_metrics = response.usage_metadata

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(role=response_role or "model", parts=response_parts)
        # -*- Add content to assistant message
        if assistant_message_content != "":
            assistant_message.content = assistant_message_content
        # -*- Add tool calls to assistant message
        if response_function_calls != []:
            assistant_message.tool_calls = response_function_calls

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        if response_metrics:
            input_tokens = response_metrics.prompt_token_count
            output_tokens = response_metrics.candidates_token_count
            total_tokens = response_metrics.total_token_count

            if input_tokens is not None:
                assistant_message.metrics["input_tokens"] = input_tokens
                self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + input_tokens

            if output_tokens is not None:
                assistant_message.metrics["output_tokens"] = output_tokens
                self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + output_tokens

            if total_tokens is not None:
                self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + total_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Parse and run function calls
        if assistant_message.tool_calls is not None:
            function_calls_to_run: List[FunctionCall] = []
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="tool", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="tool", content=_function_call.error))
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
                for result in function_call_results:
                    s = Struct()
                    s.update({"result": [result.content]})
                    function_response = genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(name=result.tool_call_name, response=s)
                    )
                    messages.append(Message(role="tool", content=result.content, parts=[function_response]))

            # -*- Yield new response using results of tool calls
            yield from self.response_stream(messages=messages)
        logger.debug("---------- Gemini Response End ----------")
