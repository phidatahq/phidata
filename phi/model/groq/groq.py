import httpx
from typing import Optional, List, Iterator, Dict, Any, Union, Tuple

from phi.model.base import Model
from phi.model.message import Message
from phi.model.response import ModelResponse
from phi.tools.function import FunctionCall
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import get_function_call_for_tool_call

try:
    from groq import Groq as GroqClient
except ImportError:
    logger.error("`groq` not installed")
    raise


class Groq(Model):
    """
    A class to interact with the Groq language model via its API.
    """

    name: str = "Groq"
    model: str = "llama3-70b-8192"

    # -*- Request parameters
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Any] = None
    logprobs: Optional[bool] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    response_format: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    temperature: Optional[float] = None
    top_logprobs: Optional[int] = None
    top_p: Optional[float] = None
    user: Optional[str] = None
    extra_headers: Optional[Any] = None
    extra_query: Optional[Any] = None
    request_params: Optional[Dict[str, Any]] = None

    # -*- Client parameters
    api_key: Optional[str] = None
    base_url: Optional[Union[str, httpx.URL]] = None
    timeout: Optional[int] = None
    max_retries: Optional[int] = None
    default_headers: Optional[Any] = None
    default_query: Optional[Any] = None
    client_params: Optional[Dict[str, Any]] = None

    # -*- Provide the Groq client manually
    groq_client: Optional[GroqClient] = None

    @property
    def client(self) -> GroqClient:
        """
        Initializes and returns a GroqClient instance using the provided client parameters.

        Returns:
            GroqClient: An instance of the Groq client.
        """
        if self.groq_client:
            return self.groq_client

        _client_params: Dict[str, Any] = {}
        if self.api_key:
            _client_params["api_key"] = self.api_key
        if self.base_url:
            _client_params["base_url"] = self.base_url
        if self.timeout:
            _client_params["timeout"] = self.timeout
        if self.max_retries:
            _client_params["max_retries"] = self.max_retries
        if self.default_headers:
            _client_params["default_headers"] = self.default_headers
        if self.default_query:
            _client_params["default_query"] = self.default_query
        if self.client_params:
            _client_params.update(self.client_params)
        return GroqClient(**_client_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        """
        Constructs the API keyword arguments based on the provided request parameters.

        Returns:
            Dict[str, Any]: A dictionary of API keyword arguments.
        """
        _request_params: Dict[str, Any] = {}
        if self.frequency_penalty is not None:
            _request_params["frequency_penalty"] = self.frequency_penalty
        if self.logit_bias is not None:
            _request_params["logit_bias"] = self.logit_bias
        if self.logprobs is not None:
            _request_params["logprobs"] = self.logprobs
        if self.max_tokens is not None:
            _request_params["max_tokens"] = self.max_tokens
        if self.presence_penalty is not None:
            _request_params["presence_penalty"] = self.presence_penalty
        if self.response_format is not None:
            _request_params["response_format"] = self.response_format
        if self.seed is not None:
            _request_params["seed"] = self.seed
        if self.stop is not None:
            _request_params["stop"] = self.stop
        if self.temperature is not None:
            _request_params["temperature"] = self.temperature
        if self.top_logprobs is not None:
            _request_params["top_logprobs"] = self.top_logprobs
        if self.top_p is not None:
            _request_params["top_p"] = self.top_p
        if self.user is not None:
            _request_params["user"] = self.user
        if self.extra_headers is not None:
            _request_params["extra_headers"] = self.extra_headers
        if self.extra_query is not None:
            _request_params["extra_query"] = self.extra_query
        if self.tools:
            _request_params["tools"] = self.get_tools_for_api()
            if self.tool_choice is None:
                _request_params["tool_choice"] = "auto"
            else:
                _request_params["tool_choice"] = self.tool_choice
        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the Groq model configuration to a dictionary.

        Returns:
            Dict[str, Any]: A dictionary representation of the model configuration.
        """
        _dict = super().to_dict()
        if self.frequency_penalty is not None:
            _dict["frequency_penalty"] = self.frequency_penalty
        if self.logit_bias is not None:
            _dict["logit_bias"] = self.logit_bias
        if self.logprobs is not None:
            _dict["logprobs"] = self.logprobs
        if self.max_tokens is not None:
            _dict["max_tokens"] = self.max_tokens
        if self.presence_penalty is not None:
            _dict["presence_penalty"] = self.presence_penalty
        if self.response_format is not None:
            _dict["response_format"] = self.response_format
        if self.seed is not None:
            _dict["seed"] = self.seed
        if self.stop is not None:
            _dict["stop"] = self.stop
        if self.temperature is not None:
            _dict["temperature"] = self.temperature
        if self.top_logprobs is not None:
            _dict["top_logprobs"] = self.top_logprobs
        if self.top_p is not None:
            _dict["top_p"] = self.top_p
        if self.user is not None:
            _dict["user"] = self.user
        if self.extra_headers is not None:
            _dict["extra_headers"] = self.extra_headers
        if self.extra_query is not None:
            _dict["extra_query"] = self.extra_query
        if self.tools:
            _dict["tools"] = self.get_tools_for_api()
            if self.tool_choice is None:
                _dict["tool_choice"] = "auto"
            else:
                _dict["tool_choice"] = self.tool_choice
        return _dict

    def invoke(self, messages: List[Message]) -> Any:
        """
        Sends a request to the Groq API with the given messages.

        Args:
            messages (List[Message]): A list of messages representing the conversation history.

        Returns:
            Any: The response from the Groq API.
        """
        if self.tools and self.response_format:
            logger.warn(
                f"Response format is not supported for Groq when specifying tools. Ignoring response_format: {self.response_format}"
            )
            self.response_format = {"type": "text"}

        # Format messages for the API
        formatted_messages = [m.to_dict() for m in messages]
        for msg in formatted_messages:
            msg.pop("created_at")

        return self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,  # type: ignore
            **self.api_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Iterator[Any]:
        """
        Sends a streaming request to the Groq API with the given messages.

        Args:
            messages (List[Message]): A list of messages representing the conversation history.

        Yields:
            Iterator[Any]: An iterator over the streaming response from the Groq API.
        """
        # Format messages for the API
        formatted_messages = [m.to_dict() for m in messages]
        for msg in formatted_messages:
            msg.pop("created_at")

        yield from self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,  # type: ignore
            stream=True,
            **self.api_kwargs,
        )

    def response(self, messages: List[Message]) -> ModelResponse:
        """
        Generates a response from the Groq model based on the provided messages.

        Args:
            messages (List[Message]): A list of Message objects representing the conversation history.

        Returns:
            ModelResponse: The model's response.
        """
        logger.debug("---------- Groq Response Start ----------")
        # Log messages for debugging
        for m in messages:
            m.log()

        # Create a ModelResponse object to return
        model_response = ModelResponse()

        # Invoke the model and get response with timing
        response, elapsed_time = self._get_response_with_timing(messages)

        # Parse the response into an agent message
        agent_message = self._parse_response(response)

        # Update usage metrics
        self._update_usage_metrics(agent_message, elapsed_time, response)

        # Add agent message to messages
        messages.append(agent_message)
        agent_message.log()

        # Handle tool calls if any
        if agent_message.tool_calls:
            return self._handle_tool_calls(agent_message, messages, model_response)

        # Return content if no function calls are present
        if agent_message.content is not None:
            model_response.content = agent_message.get_content_string()

        logger.debug("---------- Groq Response End ----------")
        return model_response

    def response_stream(self, messages: List[Message]) -> Iterator[ModelResponse]:
        """
        Generates a streaming response from the Groq model based on the provided messages.

        Args:
            messages (List[Message]): A list of Message objects representing the conversation history.

        Yields:
            Iterator[ModelResponse]: An iterator over the model's response chunks.
        """
        logger.debug("---------- Groq Response Start ----------")
        # Log messages for debugging
        for m in messages:
            m.log()

        # Initialize variables to store response data
        agent_message_role: Optional[str] = None
        agent_message_content = ""
        agent_message_tool_calls: Optional[List[Any]] = None
        response_timer = Timer()
        response_timer.start()

        # Stream the response from the model
        for response in self.invoke_stream(messages=messages):
            # Parse response delta
            response_delta = response.choices[0].delta
            if agent_message_role is None and response_delta.role is not None:
                agent_message_role = response_delta.role
            response_content: Optional[str] = response_delta.content
            response_tool_calls: Optional[List[Any]] = response_delta.tool_calls

            # Yield content if present
            if response_content is not None:
                agent_message_content += response_content
                yield ModelResponse(content=response_content)

            # Collect tool calls
            if response_tool_calls is not None and len(response_tool_calls) > 0:
                if agent_message_tool_calls is None:
                    agent_message_tool_calls = []
                agent_message_tool_calls.extend(response_tool_calls)

        response_timer.stop()
        elapsed_time = response_timer.elapsed
        logger.debug(f"Time to generate response: {elapsed_time:.4f}s")

        # Create agent message
        agent_message = Message(role=(agent_message_role or "agent"))
        if agent_message_content != "":
            agent_message.content = agent_message_content
        if agent_message_tool_calls is not None:
            agent_message.tool_calls = [t.model_dump() for t in agent_message_tool_calls]

        # Update usage metrics
        self._update_usage_metrics(agent_message, elapsed_time, response=None)

        # Add agent message to messages
        messages.append(agent_message)
        agent_message.log()

        # Handle tool calls if any
        if agent_message.tool_calls:
            yield from self._handle_tool_calls_stream(agent_message, messages)
        logger.debug("---------- Groq Response End ----------")

    def _get_response_with_timing(self, messages: List[Message]) -> Tuple[Any, float]:
        """
        Invokes the Groq model with the given messages and returns the response and time taken.

        Args:
            messages (List[Message]): A list of Message objects representing the conversation history.

        Returns:
            Tuple[Any, float]: The response from the model and the time taken to get the response.
        """
        response_timer = Timer()
        response_timer.start()
        response = self.invoke(messages=messages)
        response_timer.stop()
        elapsed_time = response_timer.elapsed
        logger.debug(f"Time to generate response: {elapsed_time:.4f}s")
        return response, elapsed_time

    def _parse_response(self, response: Any) -> Message:
        """
        Parses the response from the Groq model and returns a Message object.

        Args:
            response (Any): The response from the Groq model.

        Returns:
            Message: A Message object containing the parsed response.
        """
        response_message = response.choices[0].message
        agent_message = Message(
            role=response_message.role or "agent",
            content=response_message.content,
        )
        if response_message.tool_calls is not None and len(response_message.tool_calls) > 0:
            agent_message.tool_calls = [t.model_dump() for t in response_message.tool_calls]
        return agent_message

    def _update_usage_metrics(
        self, agent_message: Message, elapsed_time: float, response: Optional[Any]
    ) -> None:
        """
        Updates the usage metrics based on the agent message and response.

        Args:
            agent_message (Message): The agent's message.
            elapsed_time (float): The time taken to get the response.
            response (Optional[Any]): The response from the Groq model.
        """
        # Add response time to metrics
        agent_message.metrics["time"] = elapsed_time
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(elapsed_time)

        # Add token usage to metrics if available
        if response and response.usage is not None:
            self.metrics.update(response.usage.model_dump())

    def _handle_tool_calls(
        self, agent_message: Message, messages: List[Message], model_response: ModelResponse
    ) -> ModelResponse:
        """
        Parses and runs tool calls from the agent message, updates messages, and returns the updated model response.

        Args:
            agent_message (Message): The agent's message containing tool calls.
            messages (List[Message]): The conversation history.
            model_response (ModelResponse): The current model response.

        Returns:
            ModelResponse: The updated model response after handling tool calls.
        """
        model_response.content = ""
        function_calls_to_run: List[FunctionCall] = []

        # Process each tool call
        for tool_call in agent_message.tool_calls:
            _tool_call_id = tool_call.get("id")
            _function_call = get_function_call_for_tool_call(tool_call, self.functions)
            if _function_call is None:
                messages.append(
                    Message(role="tool", tool_call_id=_tool_call_id, content="Could not find function to call.")
                )
                continue
            if _function_call.error is not None:
                messages.append(
                    Message(role="tool", tool_call_id=_tool_call_id, content=_function_call.error)
                )
                continue
            function_calls_to_run.append(_function_call)

        # Show tool calls if enabled
        if self.show_tool_calls:
            if len(function_calls_to_run) == 1:
                model_response.content += f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
            elif len(function_calls_to_run) > 1:
                model_response.content += "\nRunning:"
                for _f in function_calls_to_run:
                    model_response.content += f"\n - {_f.get_call_str()}"
                model_response.content += "\n\n"

        # Run function calls
        function_call_results = self.run_function_calls(function_calls_to_run)
        if len(function_call_results) > 0:
            messages.extend(function_call_results)

        # Get new response using results of tool calls
        response_after_tool_calls = self.response(messages=messages)
        if response_after_tool_calls.content is not None:
            model_response.content += response_after_tool_calls.content
        return model_response

    def _handle_tool_calls_stream(
        self, agent_message: Message, messages: List[Message]
    ) -> Iterator[ModelResponse]:
        """
        Parses and runs tool calls from the agent message in a streaming manner.

        Args:
            agent_message (Message): The agent's message containing tool calls.
            messages (List[Message]): The conversation history.

        Yields:
            Iterator[ModelResponse]: An iterator over the updated model responses after handling tool calls.
        """
        function_calls_to_run: List[FunctionCall] = []

        # Process each tool call
        for tool_call in agent_message.tool_calls:
            _tool_call_id = tool_call.get("id")
            _function_call = get_function_call_for_tool_call(tool_call, self.functions)
            if _function_call is None:
                messages.append(
                    Message(role="tool", tool_call_id=_tool_call_id, content="Could not find function to call.")
                )
                continue
            if _function_call.error is not None:
                messages.append(
                    Message(role="tool", tool_call_id=_tool_call_id, content=_function_call.error)
                )
                continue
            function_calls_to_run.append(_function_call)

        # Show tool calls if enabled
        if self.show_tool_calls:
            if len(function_calls_to_run) == 1:
                yield ModelResponse(content=f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n")
            elif len(function_calls_to_run) > 1:
                yield ModelResponse(content="\nRunning:")
                for _f in function_calls_to_run:
                    yield ModelResponse(content=f"\n - {_f.get_call_str()}")
                yield ModelResponse(content="\n\n")

        # Run function calls
        function_call_results = self.run_function_calls(function_calls_to_run)
        if len(function_call_results) > 0:
            messages.extend(function_call_results)

        # Yield new response using results of tool calls
        yield from self.response_stream(messages=messages)
