import json
from typing import Optional, List, Dict, Any, Iterator, Tuple

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from cohere import Client as CohereClient
    from cohere.types.tool import Tool as CohereTool
    from cohere.types.non_streamed_chat_response import NonStreamedChatResponse
    from cohere.types.streamed_chat_response import (
        StreamedChatResponse,
        StreamStartStreamedChatResponse,
        TextGenerationStreamedChatResponse,
        ToolCallsChunkStreamedChatResponse,
        ToolCallsGenerationStreamedChatResponse,
        StreamEndStreamedChatResponse,
    )
    from cohere.types.tool_result import ToolResult
    from cohere.types.tool_parameter_definitions_value import (
        ToolParameterDefinitionsValue,
    )
    from cohere.types.api_meta_tokens import ApiMetaTokens
    from cohere.types.api_meta import ApiMeta
except ImportError:
    logger.error("`cohere` not installed")
    raise


class CohereChat(Model):
    """
    A class representing a chat model using the Cohere API.

    This class extends the base Model class and provides functionality to interact
    with Cohere's chat API, including handling requests, responses, and various
    configuration options.

    Attributes:
        name (str): The name of the model, set to "cohere".
        model (str): The specific Cohere model to use, default is "command-r-plus".
        temperature (Optional[float]): Controls randomness in output generation.
        max_tokens (Optional[int]): Maximum number of tokens to generate.
        top_k (Optional[int]): Number of top tokens to consider for sampling.
        top_p (Optional[float]): Cumulative probability threshold for token sampling.
        frequency_penalty (Optional[float]): Penalizes frequent token usage.
        presence_penalty (Optional[float]): Penalizes repeated token usage.
        request_params (Optional[Dict[str, Any]]): Additional request parameters.
        add_chat_history (bool): Whether to add chat history to Cohere messages.
        api_key (Optional[str]): Cohere API key for authentication.
        client_params (Optional[Dict[str, Any]]): Additional client parameters.
        cohere_client (Optional[CohereClient]): Pre-configured Cohere client instance.
    """

    name: str = "cohere"
    model: str = "command-r-plus"
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    request_params: Optional[Dict[str, Any]] = None
    add_chat_history: bool = False
    api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None
    cohere_client: Optional[CohereClient] = None

    @property
    def client(self) -> CohereClient:
        """
        Lazy-loaded Cohere client property.

        This property ensures that a Cohere client is created only when needed,
        and reuses an existing client if available.

        Returns:
            CohereClient: An instance of the Cohere client.
        """
        # If a client is already set, return it
        if self.cohere_client:
            return self.cohere_client

        # Initialize client parameters
        _client_params: Dict[str, Any] = {}

        # Add API key to client parameters if provided
        if self.api_key:
            _client_params["api_key"] = self.api_key

        # Create and store a new Cohere client
        self.cohere_client = CohereClient(**_client_params)

        return self.cohere_client

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        """
        Constructs API request parameters based on instance attributes.

        This property compiles various configuration options into a dictionary
        that can be used as keyword arguments for API requests.

        Returns:
            Dict[str, Any]: A dictionary of API request parameters.
        """
        # Initialize request parameters dictionary
        _request_params: Dict[str, Any] = {}

        # Add conversation_id if session_id is set and chat history is not added
        if self.session_id is not None and not self.add_chat_history:
            _request_params["conversation_id"] = self.session_id

        # Add other parameters if they are set
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.top_k:
            _request_params["top_k"] = self.top_k
        if self.top_p:
            _request_params["top_p"] = self.top_p
        if self.frequency_penalty:
            _request_params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty:
            _request_params["presence_penalty"] = self.presence_penalty

        # Update with any additional request parameters
        if self.request_params:
            _request_params.update(self.request_params)

        return _request_params

    def _update_metrics(self, agent_message: Message, response_timer: Timer, meta: Optional[ApiMeta]) -> None:
        """
        Updates metrics for the agent message based on the API response.

        This method updates various metrics including response time and token usage.

        Args:
            agent_message (Message): The message object to update with metrics.
            response_timer (Timer): Timer object containing the elapsed time.
            meta (Optional[ApiMeta]): Metadata from the API response.
        """
        # Update response time metrics
        agent_message.metrics["time"] = response_timer.elapsed
        self.metrics.setdefault("response_times", []).append(response_timer.elapsed)

        # Extract token information from metadata
        tokens: Optional[ApiMetaTokens] = meta.tokens if meta else None

        # Update token metrics if available
        if tokens:
            self._update_token_metrics(agent_message, tokens)

    def _update_token_metrics(self, agent_message: Message, tokens: ApiMetaTokens) -> None:
        """
        Updates token-specific metrics for the agent message.

        This method calculates and updates various token-related metrics including
        input tokens, output tokens, and total tokens used.

        Args:
            agent_message (Message): The message object to update with token metrics.
            tokens (ApiMetaTokens): Token information from the API response.
        """
        # Update input token metrics
        if tokens.input_tokens is not None:
            agent_message.metrics["input_tokens"] = tokens.input_tokens
            self.metrics["input_tokens"] = self.metrics.get("input_tokens", 0) + tokens.input_tokens

        # Update output token metrics
        if tokens.output_tokens is not None:
            agent_message.metrics["output_tokens"] = tokens.output_tokens
            self.metrics["output_tokens"] = self.metrics.get("output_tokens", 0) + tokens.output_tokens

        # Calculate and update total token metrics
        if tokens.input_tokens is not None and tokens.output_tokens is not None:
            total_tokens = tokens.input_tokens + tokens.output_tokens
            agent_message.metrics["total_tokens"] = total_tokens
            self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + total_tokens

    def _prepare_function_calls(self, agent_message: Message) -> Tuple[List[FunctionCall], List[Message]]:
        """
        Prepares function calls based on tool calls in the agent message.

        This method processes tool calls, matches them with available functions,
        and prepares them for execution. It also handles errors if functions
        are not found or if there are issues with the function calls.

        Args:
            agent_message (Message): The message containing tool calls to process.

        Returns:
            Tuple[List[FunctionCall], List[Message]]: A tuple containing a list of
            prepared function calls and a list of error messages.
        """
        function_calls_to_run: List[FunctionCall] = []
        error_messages: List[Message] = []

        # Check if tool_calls is None or empty
        if not agent_message.tool_calls:
            return function_calls_to_run, error_messages

        # Process each tool call in the agent message
        for tool_call in agent_message.tool_calls:
            # Attempt to get a function call for the tool call
            _function_call = get_function_call_for_tool_call(tool_call, self.functions)

            # Handle cases where function call cannot be created
            if _function_call is None:
                error_messages.append(Message(role="user", content="Could not find function to call."))
                continue

            # Handle cases where function call has an error
            if _function_call.error is not None:
                error_messages.append(Message(role="user", content=_function_call.error))
                continue

            # Add valid function calls to the list
            function_calls_to_run.append(_function_call)

        return function_calls_to_run, error_messages

    def _format_tool_calls_display(self, function_calls: List[FunctionCall]) -> str:
        """
        Formats the display string for tool calls.

        This method creates a human-readable string representation of the
        function calls to be executed.

        Args:
            function_calls (List[FunctionCall]): List of function calls to format.

        Returns:
            str: A formatted string displaying the function calls.
        """
        # Handle case with a single function call
        if len(function_calls) == 1:
            return f"- Running: {function_calls[0].get_call_str()}\n\n"

        # Handle case with multiple function calls
        elif len(function_calls) > 1:
            return "Running:" + "".join(f"\n - {_f.get_call_str()}" for _f in function_calls) + "\n\n"

        # Return empty string if no function calls
        return ""

    def get_tools(self) -> Optional[List[CohereTool]]:
        """
        Converts functions to Cohere API compatible tools.

        This method transforms the internal function definitions into a format
        that is compatible with the Cohere API. It creates CohereTool objects
        for each function, including their names, descriptions, and parameter
        definitions.

        Returns:
            Optional[List[CohereTool]]: A list of Cohere tools or None if no
            functions are defined.
        """
        # Return None if no functions are defined
        if not self.functions:
            return None

        # List comprehension to create CohereTool objects for each function
        return [
            CohereTool(
                name=f_name,
                description=function.description or "",
                parameter_definitions={
                    param_name: ToolParameterDefinitionsValue(
                        # Determine the parameter type
                        type=(param_info["type"] if isinstance(param_info["type"], str) else param_info["type"][0]),
                        # Determine if the parameter is required
                        required="null" not in param_info["type"],
                    )
                    for param_name, param_info in function.parameters.get("properties", {}).items()
                },
            )
            for f_name, function in self.functions.items()
        ]

    def _prepare_api_request(self, messages: List[Message]) -> Tuple[str, Dict[str, Any]]:
        """
        Prepares the API request by formatting messages and setting parameters.

        This method processes the list of messages to create the appropriate
        request format for the Cohere API. It handles both scenarios where
        chat history is added to the request and where it isn't.

        Args:
            messages (List[Message]): A list of Message objects representing
                the conversation history.

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the chat message
            (string) and the API keyword arguments (dictionary).
        """
        # Copy the existing API kwargs to avoid modifying the original
        api_kwargs = self.api_kwargs.copy()
        chat_message = ""

        if self.add_chat_history:
            logger.debug("Providing chat_history to cohere")
            chat_history: List[Dict[str, str]] = []

            # Process each message in the conversation
            for m in messages:
                if m.role == "system" and "preamble" not in api_kwargs:
                    # Set system message as preamble
                    api_kwargs["preamble"] = m.content
                elif m.role == "user":
                    # Set the latest user message as chat_message
                    chat_message = m.get_content_string()
                    chat_history.append({"role": "USER", "message": chat_message})
                else:
                    # Add assistant messages to chat history
                    chat_history.append({"role": "CHATBOT", "message": m.get_content_string() or ""})

            # Remove the last user message if it's at the end of chat history
            if chat_history and chat_history[-1].get("role") == "USER":
                chat_history.pop()

            api_kwargs["chat_history"] = chat_history
        else:
            # If not adding chat history, find the system message and latest user message
            for m in messages:
                if m.role == "system" and "preamble" not in api_kwargs:
                    api_kwargs["preamble"] = m.get_content_string()
                    break

            for m in reversed(messages):
                if m.role == "user":
                    chat_message = m.get_content_string()
                    break

        return chat_message or "", api_kwargs

    def invoke(
        self, messages: List[Message], tool_results: Optional[List[ToolResult]] = None
    ) -> NonStreamedChatResponse:
        """
        Invokes the Cohere chat API with the given messages and tool results.

        This method prepares the API request, including any tools and tool results,
        and sends a non-streaming request to the Cohere chat API.

        Args:
            messages (List[Message]): A list of Message objects representing the conversation history.
            tool_results (Optional[List[ToolResult]]): A list of ToolResult objects from previous tool calls, if any.

        Returns:
            NonStreamedChatResponse: The complete response from the Cohere chat API.
        """
        # Prepare the API request parameters
        chat_message, api_kwargs = self._prepare_api_request(messages)

        # Add tools to the request if they are defined
        if self.tools:
            api_kwargs["tools"] = self.get_tools()

        # Add tool results to the request if provided
        if tool_results:
            api_kwargs["tool_results"] = tool_results

        # Send the request to the Cohere chat API and return the response
        return self.client.chat(message=chat_message, model=self.model, **api_kwargs)

    def invoke_stream(
        self, messages: List[Message], tool_results: Optional[List[ToolResult]] = None
    ) -> Iterator[StreamedChatResponse]:
        """
        Invokes the Cohere chat API in streaming mode with the given messages and tool results.

        This method prepares the API request, including any tools and tool results,
        and sends a streaming request to the Cohere chat API. It returns an iterator
        that yields streamed responses.

        Args:
            messages (List[Message]): A list of Message objects representing the conversation history.
            tool_results (Optional[List[ToolResult]]): A list of ToolResult objects from previous tool calls, if any.

        Returns:
            Iterator[StreamedChatResponse]: An iterator yielding streamed responses from the Cohere chat API.
        """
        # Prepare the API request parameters
        chat_message, api_kwargs = self._prepare_api_request(messages)

        # Add tools to the request if they are defined
        if self.tools:
            api_kwargs["tools"] = self.get_tools()

        # Add tool results to the request if provided
        if tool_results:
            api_kwargs["tool_results"] = tool_results

        # Send the streaming request to the Cohere chat API and return the iterator
        return self.client.chat_stream(message=chat_message, model=self.model, **api_kwargs)

    def response(self, messages: List[Message], tool_results: Optional[List[ToolResult]] = None) -> ModelResponse:
        """
        Generates a response using the Cohere chat API and processes any tool calls.

        This method handles the complete flow of generating a response, including
        invoking the API, processing tool calls, and recursively handling follow-up
        responses after tool execution.

        Args:
            messages (List[Message]): A list of Message objects representing the conversation history.
            tool_results (Optional[List[ToolResult]]): Results from previous tool executions, if any.

        Returns:
            ModelResponse: The final response, including any tool call results.
        """
        logger.debug("---------- Cohere Response Start ----------")
        # Log all input messages
        for m in messages:
            m.log()

        model_response = ModelResponse()
        response_timer = Timer()
        response_timer.start()

        # Invoke the Cohere API
        response = self.invoke(messages=messages, tool_results=tool_results)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        response_content = response.text
        response_tool_calls = response.tool_calls

        # Create an agent message from the response
        agent_message = Message(role="assistant", content=response_content)

        # Process tool calls if present
        if response_tool_calls:
            tool_calls = [
                {
                    "type": "function",
                    "function": {
                        "name": tools.name,
                        "arguments": json.dumps(tools.parameters),
                    },
                }
                for tools in response_tool_calls
            ]
            agent_message.tool_calls = tool_calls

        # Update metrics and append the agent message
        self._update_metrics(agent_message, response_timer, response.meta)
        messages.append(agent_message)
        agent_message.log()

        # Handle tool calls if present and tool running is enabled
        if agent_message.tool_calls and self.run_tools:
            model_response.content = agent_message.get_content_string() + "\n\n"
            function_calls_to_run, error_messages = self._prepare_function_calls(agent_message)

            if error_messages:
                messages.extend(error_messages)

            if self.show_tool_calls:
                model_response.content += self._format_tool_calls_display(function_calls_to_run)

            # Execute function calls
            function_call_results = self.run_function_calls(function_calls_to_run)
            if function_call_results:
                messages.extend(function_call_results)

            # Prepare tool results for the next API call
            if response_tool_calls and len(function_call_results) == len(response_tool_calls):
                tool_results = [
                    ToolResult(
                        call=tool_call,
                        outputs=[tool_call.parameters, {"result": fn_result.content}],
                    )
                    for tool_call, fn_result in zip(response_tool_calls, function_call_results)
                ]
            else:
                tool_results = None

            # Make a recursive call with tool results if available
            if tool_results:
                messages.append(Message(role="user", content=""))
            response_after_tool_calls = self.response(messages=messages, tool_results=tool_results)
            if response_after_tool_calls.content:
                model_response.content += response_after_tool_calls.content
            return model_response

        # If no tool calls, return the agent message content
        if agent_message.content:
            model_response.content = agent_message.get_content_string()

        logger.debug("---------- Cohere Response End ----------")
        return model_response

    def response_stream(
        self, messages: List[Message], tool_results: Optional[List[ToolResult]] = None
    ) -> Iterator[ModelResponse]:
        """
        Generates a streaming response using the Cohere chat API and processes any tool calls.

        This method handles the complete flow of generating a streaming response, including
        invoking the API, processing tool calls, and recursively handling follow-up
        responses after tool execution.

        Args:
            messages (List[Message]): A list of Message objects representing the conversation history.
            tool_results (Optional[List[ToolResult]]): Results from previous tool executions, if any.

        Yields:
            ModelResponse: Chunks of the response, including any tool call results.
        """
        logger.debug("---------- Cohere Response Start ----------")
        # Log all input messages
        for m in messages:
            m.log()

        agent_message_content = ""
        tool_calls = []
        response_tool_calls = []
        response_timer = Timer()
        response_timer.start()
        last_meta = None

        # Process the streaming response
        for response in self.invoke_stream(messages=messages, tool_results=tool_results):
            if isinstance(response, StreamStartStreamedChatResponse):
                # Stream start, no action needed
                pass
            elif isinstance(response, TextGenerationStreamedChatResponse):
                if response.text is not None:
                    agent_message_content += response.text
                    yield ModelResponse(content=response.text)
            elif isinstance(response, ToolCallsChunkStreamedChatResponse):
                if response.tool_call_delta is None:
                    yield ModelResponse(content=response.text)
            elif isinstance(response, ToolCallsGenerationStreamedChatResponse):
                for tc in response.tool_calls:
                    response_tool_calls.append(tc)
                    tool_calls.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.parameters),
                            },
                        }
                    )
            elif isinstance(response, StreamEndStreamedChatResponse):
                last_meta = response.response.meta

        yield ModelResponse(content="\n\n")
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # Create an agent message from the accumulated content
        agent_message = Message(role="assistant", content=agent_message_content)
        if tool_calls:
            agent_message.tool_calls = tool_calls

        # Update metrics and append the agent message
        self._update_metrics(agent_message, response_timer, last_meta)
        messages.append(agent_message)
        agent_message.log()

        # Handle tool calls if present and tool running is enabled
        if agent_message.tool_calls and self.run_tools:
            function_calls_to_run, error_messages = self._prepare_function_calls(agent_message)

            if error_messages:
                messages.extend(error_messages)

            if self.show_tool_calls:
                yield ModelResponse(content=self._format_tool_calls_display(function_calls_to_run))

            # Execute function calls
            function_call_results = self.run_function_calls(function_calls_to_run)
            if function_call_results:
                messages.extend(function_call_results)

            # Prepare tool results for the next API call
            if response_tool_calls and len(function_call_results) == len(response_tool_calls):
                tool_results = [
                    ToolResult(
                        call=tool_call,
                        outputs=[tool_call.parameters, {"result": fn_result.content}],
                    )
                    for tool_call, fn_result in zip(response_tool_calls, function_call_results)
                ]
            else:
                tool_results = None

            # Make a recursive call with tool results if available
            if tool_results:
                messages.append(Message(role="user", content=""))
            yield from self.response_stream(messages=messages, tool_results=tool_results)
        logger.debug("---------- Cohere Response End ----------")
