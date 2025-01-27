from os import getenv
import time
import json
from pathlib import Path
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
    import google.generativeai as genai
    from google.ai.generativelanguage_v1beta.types import (
        Part,
        FunctionCall as GeminiFunctionCall,
        FunctionResponse as GeminiFunctionResponse,
    )
    from google.generativeai import GenerativeModel
    from google.generativeai.types.generation_types import GenerateContentResponse
    from google.generativeai.types.content_types import FunctionDeclaration, Tool as GeminiTool
    from google.generativeai.types import file_types
    from google.ai.generativelanguage_v1beta.types.generative_service import (
        GenerateContentResponse as ResultGenerateContentResponse,
    )
    from google.protobuf.struct_pb2 import Struct
except (ModuleNotFoundError, ImportError):
    raise ImportError("`google-generativeai` not installed. Please install it using `pip install google-generativeai`")


@dataclass
class MessageData:
    response_content: str = ""
    response_block: Optional[GenerateContentResponse] = None
    response_role: Optional[str] = None
    response_parts: Optional[List] = None
    valid_response_parts: Optional[List] = None
    response_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    response_usage: Optional[ResultGenerateContentResponse] = None


@dataclass
class Metrics:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    time_to_first_token: Optional[float] = None
    response_timer: Timer = field(default_factory=Timer)

    def log(self):
        logger.debug("**************** METRICS START ****************")
        if self.time_to_first_token is not None:
            logger.debug(f"* Time to first token:         {self.time_to_first_token:.4f}s")
        logger.debug(f"* Time to generate response:   {self.response_timer.elapsed:.4f}s")
        logger.debug(f"* Tokens per second:           {self.output_tokens / self.response_timer.elapsed:.4f} tokens/s")
        logger.debug(f"* Input tokens:                {self.input_tokens}")
        logger.debug(f"* Output tokens:               {self.output_tokens}")
        logger.debug(f"* Total tokens:                {self.total_tokens}")
        logger.debug("**************** METRICS END ******************")


class Gemini(Model):
    """
    Gemini model class for Google's Generative AI models.

    Based on https://ai.google.dev/gemini-api/docs/function-calling

    Attributes:
        id (str): Model ID. Default is `gemini-2.0-flash-exp`.
        name (str): The name of this chat model instance. Default is `Gemini`.
        provider (str): Model provider. Default is `Google`.
        function_declarations (List[FunctionDeclaration]): List of function declarations.
        generation_config (Any): Generation configuration.
        safety_settings (Any): Safety settings.
        generative_model_kwargs (Dict[str, Any]): Generative model keyword arguments.
        api_key (str): API key.
        client (GenerativeModel): Generative model client.
    """

    id: str = "gemini-2.0-flash-exp"
    name: str = "Gemini"
    provider: str = "Google"

    # Request parameters
    function_declarations: Optional[List[FunctionDeclaration]] = None
    generation_config: Optional[Any] = None
    safety_settings: Optional[Any] = None
    generative_model_kwargs: Optional[Dict[str, Any]] = None

    # Client parameters
    api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None

    # Gemini client
    client: Optional[GenerativeModel] = None

    def get_client(self) -> GenerativeModel:
        """
        Returns an instance of the GenerativeModel client.

        Returns:
            GenerativeModel: The GenerativeModel client.
        """
        if self.client:
            return self.client

        client_params: Dict[str, Any] = {}

        self.api_key = self.api_key or getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.error("GOOGLE_API_KEY not set. Please set the GOOGLE_API_KEY environment variable.")
        client_params["api_key"] = self.api_key

        if self.client_params:
            client_params.update(self.client_params)
        genai.configure(**client_params)
        return genai.GenerativeModel(model_name=self.id, **self.request_kwargs)

    @property
    def request_kwargs(self) -> Dict[str, Any]:
        """
        Returns the request keyword arguments for the GenerativeModel client.

        Returns:
            Dict[str, Any]: The request keyword arguments.
        """
        request_params: Dict[str, Any] = {}
        if self.generation_config:
            request_params["generation_config"] = self.generation_config
        if self.safety_settings:
            request_params["safety_settings"] = self.safety_settings
        if self.generative_model_kwargs:
            request_params.update(self.generative_model_kwargs)
        if self.function_declarations:
            request_params["tools"] = [GeminiTool(function_declarations=self.function_declarations)]
        return request_params

    def format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Converts a list of Message objects to the Gemini-compatible format.

        Args:
            messages (List[Message]): The list of messages to convert.

        Returns:
            List[Dict[str, Any]]: The formatted_messages list of messages.
        """
        formatted_messages: List = []
        for message in messages:
            message_for_model: Dict[str, Any] = {}

            # Add role to the message for the model
            role = (
                "model"
                if message.role in ["system", "developer"]
                else "user"
                if message.role == "tool"
                else message.role
            )
            message_for_model["role"] = role

            # Add content to the message for the model
            content = message.content
            # Initialize message_parts to be used for Gemini
            message_parts: List[Any] = []

            # Function calls
            if (not content or message.role == "model") and message.tool_calls:
                for tool_call in message.tool_calls:
                    message_parts.append(
                        Part(
                            function_call=GeminiFunctionCall(
                                name=tool_call["function"]["name"],
                                args=json.loads(tool_call["function"]["arguments"]),
                            )
                        )
                    )
            # Function results
            elif message.role == "tool" and hasattr(message, "combined_function_result"):
                s = Struct()
                for combined_result in message.combined_function_result:
                    function_name = combined_result[0]
                    function_response = combined_result[1]
                    s.update({"result": [function_response]})
                    message_parts.append(Part(function_response=GeminiFunctionResponse(name=function_name, response=s)))
            # Normal content
            else:
                if isinstance(content, str):
                    message_parts = [Part(text=content)]
                elif isinstance(content, list):
                    message_parts = [Part(text=part) for part in content if isinstance(part, str)]
                else:
                    message_parts = []

            # Add images to the message for the model
            if message.images is not None and message.role == "user":
                for image in message.images:
                    # Case 1: Image is a file_types.File object (Recommended)
                    # Add it as a File object
                    if isinstance(image, file_types.File):
                        # Google recommends that if using a single image, place the text prompt after the image.
                        message_parts.insert(0, image)
                    # Case 2: If image is a string, it is a URL or a local path
                    elif isinstance(image, str) or isinstance(image, Path):
                        # Case 2.1: Image is a URL
                        # Download the image from the URL and add it as base64 encoded data
                        if isinstance(image, str) and (image.startswith("http://") or image.startswith("https://")):
                            try:
                                import httpx
                                import base64

                                image_content = httpx.get(image).content
                                image_data = {
                                    "mime_type": "image/jpeg",
                                    "data": base64.b64encode(image_content).decode("utf-8"),
                                }
                                message_parts.append(image_data)  # type: ignore
                            except Exception as e:
                                logger.warning(f"Failed to download image from {image}: {e}")
                                continue
                        # Case 2.2: Image is a local path
                        # Open the image file and add it as base64 encoded data
                        else:
                            try:
                                import PIL.Image
                            except ImportError:
                                logger.error("`PIL.Image not installed. Please install it using 'pip install pillow'`")
                                raise

                            try:
                                image_path = image if isinstance(image, Path) else Path(image)
                                if image_path.exists() and image_path.is_file():
                                    image_data = PIL.Image.open(image_path)  # type: ignore
                                else:
                                    logger.error(f"Image file {image_path} does not exist.")
                                    raise
                                message_parts.append(image_data)  # type: ignore
                            except Exception as e:
                                logger.warning(f"Failed to load image from {image_path}: {e}")
                                continue
                    # Case 3: Image is a bytes object
                    # Add it as base64 encoded data
                    elif isinstance(image, bytes):
                        image_data = {"mime_type": "image/jpeg", "data": base64.b64encode(image).decode("utf-8")}
                        message_parts.append(image_data)
                    else:
                        logger.warning(f"Unknown image type: {type(image)}")
                        continue

            if message.videos is not None and message.role == "user":
                try:
                    for video in message.videos:
                        # Case 1: Video is a file_types.File object (Recommended)
                        # Add it as a File object
                        if isinstance(video, file_types.File):
                            # Google recommends that if using a single video, place the text prompt after the video.
                            message_parts.insert(0, video)
                        # Case 2: If video is a string, it is a local path
                        elif isinstance(video, str) or isinstance(video, Path):
                            # Upload the video file to the Gemini API
                            video_file = None
                            video_path = video if isinstance(video, Path) else Path(video)
                            # Check if video is already uploaded
                            video_file_name = video_path.name
                            video_file_exists = genai.get_file(video_file_name)
                            if video_file_exists:
                                video_file = video_file_exists
                            else:
                                if video_path.exists() and video_path.is_file():
                                    video_file = genai.upload_file(path=video_path)
                                else:
                                    logger.error(f"Video file {video_path} does not exist.")
                                    raise

                            # Check whether the file is ready to be used.
                            while video_file.state.name == "PROCESSING":
                                time.sleep(2)
                                video_file = genai.get_file(video_file.name)

                            if video_file.state.name == "FAILED":
                                raise ValueError(video_file.state.name)

                            # Google recommends that if using a single video, place the text prompt after the video.
                            if video_file is not None:
                                message_parts.insert(0, video_file)  # type: ignore
                except Exception as e:
                    logger.warning(f"Failed to load video from {message.videos}: {e}")
                    continue

            if message.audio is not None and message.role == "user":
                try:
                    # Case 1: Audio is a file_types.File object (Recommended)
                    # Add it as a File object
                    if isinstance(message.audio, file_types.File):
                        # Google recommends that if using a single audio, place the text prompt after the audio.
                        message_parts.insert(0, message.audio)  # type: ignore
                    # Case 2: If audio is a string, it is a local path
                    elif isinstance(message.audio, str) or isinstance(message.audio, Path):
                        audio_path = message.audio if isinstance(message.audio, Path) else Path(message.audio)
                        if audio_path.exists() and audio_path.is_file():
                            import mimetypes

                            # Get mime type from file extension
                            mime_type = mimetypes.guess_type(audio_path)[0] or "audio/mp3"
                            audio_file = {"mime_type": mime_type, "data": audio_path.read_bytes()}
                            message_parts.insert(0, audio_file)  # type: ignore
                        else:
                            logger.error(f"Audio file {audio_path} does not exist.")
                            raise
                    # Case 3: Audio is a bytes object
                    # Add it as base64 encoded data
                    elif isinstance(message.audio, bytes):
                        audio_file = {"mime_type": "audio/mp3", "data": message.audio}
                        message_parts.insert(0, audio_file)  # type: ignore
                except Exception as e:
                    logger.warning(f"Failed to load audio from {message.audio}: {e}")
                    continue

            message_for_model["parts"] = message_parts
            formatted_messages.append(message_for_model)

        return formatted_messages

    def format_functions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts function parameters to a Gemini-compatible format.

        Args:
            params (Dict[str, Any]): The original parameters dictionary.

        Returns:
            Dict[str, Any]: The converted parameters dictionary compatible with Gemini.
        """
        formatted_params = {}

        for key, value in params.items():
            if key == "properties" and isinstance(value, dict):
                converted_properties = {}
                for prop_key, prop_value in value.items():
                    property_type = prop_value.get("type")
                    if property_type == "array":
                        converted_properties[prop_key] = prop_value
                        continue
                    if isinstance(property_type, list):
                        # Create a copy to avoid modifying the original list
                        non_null_types = [t for t in property_type if t != "null"]
                        if non_null_types:
                            # Use the first non-null type
                            converted_type = non_null_types[0]
                            if converted_type == "array":
                                prop_value["type"] = converted_type
                                converted_properties[prop_key] = prop_value
                                continue
                        else:
                            # Default type if all types are 'null'
                            converted_type = "string"
                    else:
                        converted_type = property_type

                    converted_properties[prop_key] = {"type": converted_type}
                formatted_params[key] = converted_properties
            else:
                formatted_params[key] = value

        return formatted_params

    def _build_function_declaration(self, func: Function) -> FunctionDeclaration:
        """
        Builds the function declaration for Gemini tool calling.

        Args:
            func: An instance of the function.

        Returns:
            FunctionDeclaration: The formatted function declaration.
        """
        formatted_params = self.format_functions(func.parameters)
        if "properties" in formatted_params and formatted_params["properties"]:
            # We have parameters to add
            return FunctionDeclaration(
                name=func.name,
                description=func.description,
                parameters=formatted_params,
            )
        else:
            return FunctionDeclaration(
                name=func.name,
                description=func.description,
            )

    def add_tool(
        self,
        tool: Union["Tool", "Toolkit", Callable, dict, "Function"],
        strict: bool = False,
        agent: Optional[Any] = None,
    ) -> None:
        """
        Adds tools to the model.

        Args:
            tool: The tool to add. Can be a Tool, Toolkit, Callable, dict, or Function.
        """
        if self.function_declarations is None:
            self.function_declarations = []

        # If the tool is a Tool or Dict, log a warning.
        if isinstance(tool, Tool) or isinstance(tool, Dict):
            logger.warning("Tool of type 'Tool' or 'dict' is not yet supported by Gemini.")

        # If the tool is a Callable or Toolkit, add its functions to the Model
        elif callable(tool) or isinstance(tool, Toolkit) or isinstance(tool, Function):
            if self.functions is None:
                self.functions = {}

            if isinstance(tool, Toolkit):
                # For each function in the toolkit, process entrypoint and add to self.tools
                for name, func in tool.functions.items():
                    # If the function does not exist in self.functions, add to self.tools
                    if name not in self.functions:
                        func._agent = agent
                        func.process_entrypoint()
                        self.functions[name] = func
                        function_declaration = self._build_function_declaration(func)
                        self.function_declarations.append(function_declaration)
                        logger.debug(f"Function {name} from {tool.name} added to model.")

            elif isinstance(tool, Function):
                if tool.name not in self.functions:
                    tool._agent = agent
                    tool.process_entrypoint()
                    self.functions[tool.name] = tool

                    function_declaration = self._build_function_declaration(tool)
                    self.function_declarations.append(function_declaration)
                    logger.debug(f"Function {tool.name} added to model.")

            elif callable(tool):
                try:
                    function_name = tool.__name__
                    if function_name not in self.functions:
                        func = Function.from_callable(tool)
                        self.functions[func.name] = func
                        function_declaration = self._build_function_declaration(func)
                        self.function_declarations.append(function_declaration)
                        logger.debug(f"Function '{func.name}' added to model.")
                except Exception as e:
                    logger.warning(f"Could not add function {tool}: {e}")

    def invoke(self, messages: List[Message]):
        """
        Invokes the model with a list of messages and returns the response.

        Args:
            messages (List[Message]): The list of messages to send to the model.

        Returns:
            GenerateContentResponse: The response from the model.
        """
        return self.get_client().generate_content(contents=self.format_messages(messages))

    def invoke_stream(self, messages: List[Message]):
        """
        Invokes the model with a list of messages and returns the response as a stream.

        Args:
            messages (List[Message]): The list of messages to send to the model.

        Returns:
            Iterator[GenerateContentResponse]: The response from the model as a stream.
        """
        yield from self.get_client().generate_content(
            contents=self.format_messages(messages),
            stream=True,
        )

    def update_usage_metrics(
        self,
        assistant_message: Message,
        usage: Optional[ResultGenerateContentResponse] = None,
        metrics: Metrics = Metrics(),
    ) -> None:
        """
        Update the usage metrics.

        Args:
            assistant_message (Message): The assistant message.
            usage (ResultGenerateContentResponse): The usage metrics.
            stream_usage (Optional[StreamUsageData]): The stream usage metrics.
        """
        assistant_message.metrics["time"] = metrics.response_timer.elapsed
        self.metrics.setdefault("response_times", []).append(metrics.response_timer.elapsed)
        if usage:
            metrics.input_tokens = usage.prompt_token_count or 0
            metrics.output_tokens = usage.candidates_token_count or 0
            metrics.total_tokens = usage.total_token_count or 0

            if metrics.input_tokens is not None:
                assistant_message.metrics["input_tokens"] = metrics.input_tokens
                self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + metrics.input_tokens
            if metrics.output_tokens is not None:
                assistant_message.metrics["output_tokens"] = metrics.output_tokens
                self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + metrics.output_tokens
            if metrics.total_tokens is not None:
                assistant_message.metrics["total_tokens"] = metrics.total_tokens
                self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + metrics.total_tokens
            if metrics.time_to_first_token is not None:
                assistant_message.metrics["time_to_first_token"] = metrics.time_to_first_token
                self.metrics["time_to_first_token"] = metrics.time_to_first_token

    def create_assistant_message(self, response: GenerateContentResponse, metrics: Metrics) -> Message:
        """
        Create an assistant message from the response.

        Args:
            response (GenerateContentResponse): The model response.
            response_timer (Timer): The response timer.

        Returns:
            Message: The assistant message.
        """
        message_data = MessageData()

        message_data.response_block = response.candidates[0].content
        message_data.response_role = message_data.response_block.role
        message_data.response_parts = message_data.response_block.parts
        message_data.response_usage = response.usage_metadata

        if message_data.response_parts is not None:
            for part in message_data.response_parts:
                part_dict = type(part).to_dict(part)

                # Extract text if present
                if "text" in part_dict:
                    message_data.response_content = part_dict.get("text")

                # Parse function calls
                if "function_call" in part_dict:
                    message_data.response_tool_calls.append(
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
            role=message_data.response_role or "model",
            content=message_data.response_content,
        )

        # -*- Update assistant message if tool calls are present
        if len(message_data.response_tool_calls) > 0:
            assistant_message.tool_calls = message_data.response_tool_calls

        # -*- Update usage metrics
        self.update_usage_metrics(assistant_message, message_data.response_usage, metrics)
        return assistant_message

    def get_function_calls_to_run(
        self,
        assistant_message: Message,
        messages: List[Message],
    ) -> List[FunctionCall]:
        """
        Extracts and validates function calls from the assistant message.

        Args:
            assistant_message (Message): The assistant message containing tool calls.
            messages (List[Message]): The list of conversation messages.

        Returns:
            List[FunctionCall]: A list of valid function calls to run.
        """
        function_calls_to_run: List[FunctionCall] = []
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="tool", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="tool", content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)
        return function_calls_to_run

    def format_function_call_results(
        self,
        function_call_results: List[Message],
        messages: List[Message],
    ):
        """
        Processes the results of function calls and appends them to messages.

        Args:
            function_call_results (List[Message]): The results from running function calls.
            messages (List[Message]): The list of conversation messages.
        """
        if function_call_results:
            combined_content: List = []
            combined_function_result: List = []

            for result in function_call_results:
                combined_content.append(result.content)
                combined_function_result.append((result.tool_name, result.content))

            messages.append(
                Message(role="tool", content=combined_content, combined_function_details=combined_function_result)
            )

    def handle_tool_calls(self, assistant_message: Message, messages: List[Message], model_response: ModelResponse):
        """
        Handle tool calls in the assistant message.

        Args:
            assistant_message (Message): The assistant message.
            messages (List[Message]): A list of messages.
            model_response (ModelResponse): The model response.

        Returns:
            Optional[ModelResponse]: The updated model response.
        """
        if assistant_message.tool_calls and self.run_tools:
            model_response.content = assistant_message.get_content_string() or ""
            function_calls_to_run = self.get_function_calls_to_run(assistant_message, messages)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    model_response.content += f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    model_response.content += "\nRunning:"
                    for _f in function_calls_to_run:
                        model_response.content += f"\n - {_f.get_call_str()}"
                    model_response.content += "\n\n"

            function_call_results: List[Message] = []
            for _ in self.run_function_calls(
                function_calls=function_calls_to_run,
                function_call_results=function_call_results,
            ):
                pass

            self.format_function_call_results(function_call_results, messages)

            return model_response
        return None

    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Send a generate cone content request to the model and return the response.

        Args:
            messages (List[Message]): The list of messages to send to the model.

        Returns:
            ModelResponse: The model response.
        """
        logger.debug("---------- Gemini Response Start ----------")
        self._log_messages(messages)
        model_response = ModelResponse()
        metrics = Metrics()

        # -*- Generate response
        metrics.response_timer.start()
        response: GenerateContentResponse = self.invoke(messages=messages)
        metrics.response_timer.stop()

        # -*- Create assistant message
        assistant_message = self.create_assistant_message(response=response, metrics=metrics)

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        # -*- Update model response with assistant message content
        if assistant_message.content is not None:
            model_response.content = assistant_message.get_content_string()

        # -*- Handle tool calls
        if self.handle_tool_calls(assistant_message, messages, model_response) is not None:
            response_after_tool_calls = self.response(messages=messages)
            if response_after_tool_calls.content is not None:
                if model_response.content is None:
                    model_response.content = ""
                model_response.content += response_after_tool_calls.content

            return model_response

        logger.debug("---------- Gemini Response End ----------")
        return model_response

    def handle_stream_tool_calls(self, assistant_message: Message, messages: List[Message]):
        """
        Parse and run function calls and append the results to messages.

        Args:
            assistant_message (Message): The assistant message containing tool calls.
            messages (List[Message]): The list of conversation messages.

        Yields:
            Iterator[ModelResponse]: Yields model responses during function execution.
        """
        if assistant_message.tool_calls and self.run_tools:
            function_calls_to_run = self.get_function_calls_to_run(assistant_message, messages)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    yield ModelResponse(content=f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n")
                elif len(function_calls_to_run) > 1:
                    yield ModelResponse(content="\nRunning:")
                    for _f in function_calls_to_run:
                        yield ModelResponse(content=f"\n - {_f.get_call_str()}")
                    yield ModelResponse(content="\n\n")

            function_call_results: List[Message] = []
            for intermediate_model_response in self.run_function_calls(
                function_calls=function_calls_to_run, function_call_results=function_call_results
            ):
                yield intermediate_model_response

            self.format_function_call_results(function_call_results, messages)

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        """
        Send a generate content request to the model and return the response as a stream.

        Args:
            messages (List[Message]): The list of messages to send to the model.

        Yields:
            Iterator[ModelResponse]: The model responses
        """
        logger.debug("---------- Gemini Response Start ----------")
        self._log_messages(messages)
        message_data = MessageData()
        metrics = Metrics()

        metrics.response_timer.start()
        for response in self.invoke_stream(messages=messages):
            message_data.response_block = response.candidates[0].content
            message_data.response_role = message_data.response_block.role
            message_data.response_parts = message_data.response_block.parts

            if message_data.response_parts is not None:
                for part in message_data.response_parts:
                    part_dict = type(part).to_dict(part)

                    # -*- Yield text if present
                    if "text" in part_dict:
                        text = part_dict.get("text")
                        yield ModelResponse(content=text)
                        message_data.response_content += text
                        metrics.output_tokens += 1
                        if metrics.output_tokens == 1:
                            metrics.time_to_first_token = metrics.response_timer.elapsed
                    else:
                        message_data.valid_response_parts = message_data.response_parts

                    # -*- Skip function calls if there are no parts
                    if not message_data.response_block.parts and message_data.response_parts:
                        continue
                    # -*- Parse function calls
                    if "function_call" in part_dict:
                        message_data.response_tool_calls.append(
                            {
                                "type": "function",
                                "function": {
                                    "name": part_dict.get("function_call").get("name"),
                                    "arguments": json.dumps(part_dict.get("function_call").get("args")),
                                },
                            }
                        )
            message_data.response_usage = response.usage_metadata
        metrics.response_timer.stop()

        # -*- Create assistant message
        assistant_message = Message(
            role=message_data.response_role or "model",
            content=message_data.response_content,
        )

        # -*- Update assistant message if tool calls are present
        if len(message_data.response_tool_calls) > 0:
            assistant_message.tool_calls = message_data.response_tool_calls

        # -*- Update usage metrics
        self.update_usage_metrics(assistant_message, message_data.response_usage, metrics)

        # -*- Add assistant message to messages
        messages.append(assistant_message)

        # -*- Log response and metrics
        assistant_message.log()
        metrics.log()

        if assistant_message.tool_calls is not None and len(assistant_message.tool_calls) > 0 and self.run_tools:
            yield from self.handle_stream_tool_calls(assistant_message, messages)
            yield from self.response_stream(messages=messages)

        logger.debug("---------- Gemini Response End ----------")
