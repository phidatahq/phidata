import json
from typing import Optional, List, Iterator, Dict, Any

from phi.aws.api_client import AwsApiClient
from phi.llm.base import LLM
from phi.llm.message import Message
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import (
    get_function_call_for_tool_call,
)

try:
    from boto3 import session  # noqa: F401
except ImportError:
    logger.error("`boto3` not installed")
    raise


class AwsBedrock(LLM):
    """
    AWS Bedrock model.

    Args:
        model (str): The model to use.
        aws_region (Optional[str]): The AWS region to use.
        aws_profile (Optional[str]): The AWS profile to use.
        aws_client (Optional[AwsApiClient]): The AWS client to use.
        request_params (Optional[Dict[str, Any]]): The request parameters to use.
        _bedrock_client (Optional[Any]): The Bedrock client to use.
        _bedrock_runtime_client (Optional[Any]): The Bedrock runtime client to use.
    """

    name: str = "AwsBedrock"
    model: str

    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_client: Optional[AwsApiClient] = None
    # -*- Request parameters
    request_params: Optional[Dict[str, Any]] = None

    _bedrock_client: Optional[Any] = None
    _bedrock_runtime_client: Optional[Any] = None

    def get_aws_region(self) -> Optional[str]:
        # Priority 1: Use aws_region from model
        if self.aws_region is not None:
            return self.aws_region

        # Priority 2: Get aws_region from env
        from os import getenv
        from phi.constants import AWS_REGION_ENV_VAR

        aws_region_env = getenv(AWS_REGION_ENV_VAR)
        if aws_region_env is not None:
            self.aws_region = aws_region_env
        return self.aws_region

    def get_aws_profile(self) -> Optional[str]:
        # Priority 1: Use aws_region from resource
        if self.aws_profile is not None:
            return self.aws_profile

        # Priority 2: Get aws_profile from env
        from os import getenv
        from phi.constants import AWS_PROFILE_ENV_VAR

        aws_profile_env = getenv(AWS_PROFILE_ENV_VAR)
        if aws_profile_env is not None:
            self.aws_profile = aws_profile_env
        return self.aws_profile

    def get_aws_client(self) -> AwsApiClient:
        if self.aws_client is not None:
            return self.aws_client

        self.aws_client = AwsApiClient(aws_region=self.get_aws_region(), aws_profile=self.get_aws_profile())
        return self.aws_client

    @property
    def bedrock_runtime_client(self):
        if self._bedrock_runtime_client is not None:
            return self._bedrock_runtime_client

        boto3_session: session = self.get_aws_client().boto3_session
        self._bedrock_runtime_client = boto3_session.client(service_name="bedrock-runtime")
        return self._bedrock_runtime_client

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        return {}

    def invoke(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the Bedrock API.

        Args:
            body (Dict[str, Any]): The request body.

        Returns:
            Dict[str, Any]: The response from the Bedrock API.
        """
        return self.bedrock_runtime_client.converse(**body)

    def invoke_stream(self, body: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """
        Invoke the Bedrock API with streaming.

        Args:
            body (Dict[str, Any]): The request body.

        Returns:
            Iterator[Dict[str, Any]]: The streamed response.
        """
        response = self.bedrock_runtime_client.converse_stream(**body)
        stream = response.get("stream")
        if stream:
            for event in stream:
                yield event

    def create_assistant_message(self, request_body: Dict[str, Any]) -> Message:
        raise NotImplementedError("Please use a subclass of AwsBedrock")

    def get_request_body(self, messages: List[Message]) -> Dict[str, Any]:
        raise NotImplementedError("Please use a subclass of AwsBedrock")

    def parse_response_message(self, response: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Please use a subclass of AwsBedrock")

    def parse_response_delta(self, response: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError("Please use a subclass of AwsBedrock")

    def response(self, messages: List[Message]) -> str:
        """
        Generate a response from the Bedrock API.

        Args:
            messages (List[Message]): The messages to include in the request.

        Returns:
            str: The response from the Bedrock API.
        """
        logger.debug("---------- Bedrock Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        body = self.get_request_body(messages)
        logger.debug(f"Invoking: {body}")
        response: Dict[str, Any] = self.invoke(body=body)
        response_timer.stop()

        # -*- Parse response
        parsed_response = self.parse_response_message(response)
        stop_reason = parsed_response["stop_reason"]

        # -*- Create assistant message
        assistant_message = self.create_assistant_message(parsed_response)

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        prompt_tokens = 0
        if prompt_tokens is not None:
            assistant_message.metrics["prompt_tokens"] = prompt_tokens
            if "prompt_tokens" not in self.metrics:
                self.metrics["prompt_tokens"] = prompt_tokens
            else:
                self.metrics["prompt_tokens"] += prompt_tokens
        completion_tokens = 0
        if completion_tokens is not None:
            assistant_message.metrics["completion_tokens"] = completion_tokens
            if "completion_tokens" not in self.metrics:
                self.metrics["completion_tokens"] = completion_tokens
            else:
                self.metrics["completion_tokens"] += completion_tokens
        total_tokens = prompt_tokens + completion_tokens
        if total_tokens is not None:
            assistant_message.metrics["total_tokens"] = total_tokens
            if "total_tokens" not in self.metrics:
                self.metrics["total_tokens"] = total_tokens
            else:
                self.metrics["total_tokens"] += total_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # -*- Create tool calls if needed
        if stop_reason == "tool_use":
            tool_requests = parsed_response["tool_requests"]
            if tool_requests is not None:
                tool_calls: List[Dict[str, Any]] = []
                tool_ids: List[str] = []
                tool_response = tool_requests[0]["text"]
                for tool in tool_requests:
                    if "toolUse" in tool.keys():
                        tool_id = tool["toolUse"]["toolUseId"]
                        tool_name = tool["toolUse"]["name"]
                        tool_args = tool["toolUse"]["input"]

                        tool_ids.append(tool_id)
                        tool_calls.append(
                            {
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": json.dumps(tool_args),
                                },
                            }
                        )

            assistant_message.content = tool_response
            if len(tool_calls) > 0:
                assistant_message.tool_calls = tool_calls

        # -*- Parse and run function call
        if assistant_message.tool_calls is not None and self.run_tools:
            # Remove the tool call from the response content
            final_response = str(assistant_message.content)
            final_response += "\n\n"
            function_calls_to_run = []
            for tool_call in assistant_message.tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    messages.append(Message(role="user", content="Could not find function to call."))
                    continue
                if _function_call.error is not None:
                    messages.append(Message(role="user", content=_function_call.error))
                    continue
                function_calls_to_run.append(_function_call)

            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    final_response += f" - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    final_response += "Running:"
                    for _f in function_calls_to_run:
                        final_response += f"\n - {_f.get_call_str()}"
                    final_response += "\n\n"

            function_call_results = self.run_function_calls(function_calls_to_run)
            if len(function_call_results) > 0:
                fc_responses: List = []

                for _fc_message_index, _fc_message in enumerate(function_call_results):
                    tool_result = {
                        "toolUseId": tool_ids[_fc_message_index],
                        "content": [{"json": json.dumps(_fc_message.content)}],
                    }
                    tool_result_message = {"role": "user", "content": json.dumps([{"toolResult": tool_result}])}
                    fc_responses.append(tool_result_message)

                logger.debug(f"Tool call responses: {fc_responses}")
                messages.append(Message(role="user", content=json.dumps(fc_responses)))

            # -*- Yield new response using results of tool calls
            final_response += self.response(messages=messages)
            return final_response

        logger.debug("---------- Bedrock Response End ----------")
        # -*- Return content if no function calls are present
        if assistant_message.content is not None:
            return assistant_message.get_content_string()
        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        """
        Stream the response from the Bedrock API.

        Args:
            messages (List[Message]): The messages to include in the request.

        Returns:
            Iterator[str]: The streamed response.
        """
        logger.debug("---------- Bedrock Response Start ----------")

        assistant_message_content = ""
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        request_body = self.get_request_body(messages)
        logger.debug(f"Invoking: {request_body}")

        # Initialize variables
        message = {}
        tool_use = {}
        content: List[Dict[str, Any]] = []
        text = ""
        tool_ids = []
        tool_calls = []
        function_calls_to_run = []
        stop_reason = None

        response = self.invoke_stream(body=request_body)

        # Process the streaming response
        for chunk in response:
            if "messageStart" in chunk:
                message["role"] = chunk["messageStart"]["role"]
                logger.debug(f"Role: {message['role']}")

            elif "contentBlockStart" in chunk:
                tool = chunk["contentBlockStart"]["start"].get("toolUse")
                if tool:
                    tool_use["toolUseId"] = tool["toolUseId"]
                    tool_use["name"] = tool["name"]

            elif "contentBlockDelta" in chunk:
                delta = chunk["contentBlockDelta"]["delta"]
                if "toolUse" in delta:
                    if "input" not in tool_use:
                        tool_use["input"] = ""
                    tool_use["input"] += delta["toolUse"]["input"]
                elif "text" in delta:
                    text += delta["text"]
                    assistant_message_content += delta["text"]
                    yield delta["text"]  # Yield text content as it's received

            elif "contentBlockStop" in chunk:
                if "input" in tool_use:
                    # Finish collecting tool use input
                    try:
                        tool_use["input"] = json.loads(tool_use["input"])
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse tool input as JSON: {e}")
                        tool_use["input"] = {}
                    content.append({"toolUse": tool_use})
                    tool_ids.append(tool_use["toolUseId"])
                    # Prepare the tool call
                    tool_call = {
                        "type": "function",
                        "function": {
                            "name": tool_use["name"],
                            "arguments": json.dumps(tool_use["input"]),
                        },
                    }
                    tool_calls.append(tool_call)
                    tool_use = {}
                else:
                    # Finish collecting text content
                    content.append({"text": text})
                    text = ""

            elif "messageStop" in chunk:
                stop_reason = chunk["messageStop"]["stopReason"]
                logger.debug(f"Stop reason: {stop_reason}")

            elif "metadata" in chunk:
                metadata = chunk["metadata"]
                if "usage" in metadata:
                    completion_tokens = metadata["usage"]["outputTokens"]
                    logger.debug(f"Completion tokens: {completion_tokens}")

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # Create assistant message
        assistant_message = Message(role="assistant")
        assistant_message.content = assistant_message_content

        # Update usage metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        prompt_tokens = 0  # Update as per your application logic
        assistant_message.metrics["prompt_tokens"] = prompt_tokens
        self.metrics["prompt_tokens"] = self.metrics.get("prompt_tokens", 0) + prompt_tokens

        assistant_message.metrics["completion_tokens"] = completion_tokens
        self.metrics["completion_tokens"] = self.metrics.get("completion_tokens", 0) + completion_tokens

        total_tokens = prompt_tokens + completion_tokens
        assistant_message.metrics["total_tokens"] = total_tokens
        self.metrics["total_tokens"] = self.metrics.get("total_tokens", 0) + total_tokens

        # Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # Handle tool calls if any
        if tool_calls and self.run_tools:
            logger.debug("Processing tool calls from streamed content.")

            for tool_call in tool_calls:
                _function_call = get_function_call_for_tool_call(tool_call, self.functions)
                if _function_call is None:
                    error_message = "Could not find function to call."
                    messages.append(Message(role="user", content=error_message))
                    logger.error(error_message)
                    continue
                if _function_call.error:
                    messages.append(Message(role="user", content=_function_call.error))
                    logger.error(_function_call.error)
                    continue
                function_calls_to_run.append(_function_call)

            # Optionally display the tool calls
            if self.show_tool_calls:
                if len(function_calls_to_run) == 1:
                    yield f"\n - Running: {function_calls_to_run[0].get_call_str()}\n\n"
                elif len(function_calls_to_run) > 1:
                    yield "\nRunning:"
                    for _f in function_calls_to_run:
                        yield f"\n - {_f.get_call_str()}"
                    yield "\n\n"

            # Execute the function calls
            function_call_results = self.run_function_calls(function_calls_to_run)
            if function_call_results:
                fc_responses = []
                for _fc_message_index, _fc_message in enumerate(function_call_results):
                    tool_result = {
                        "toolUseId": tool_ids[_fc_message_index],
                        "content": [{"json": json.dumps(_fc_message.content)}],
                    }
                    tool_result_message = {"role": "user", "content": json.dumps([{"toolResult": tool_result}])}
                    fc_responses.append(tool_result_message)

                logger.debug(f"Tool call responses: {fc_responses}")
                # Append the tool results to the messages
                messages.extend([Message(role="user", content=json.dumps(fc_responses))])

            yield from self.response(messages=messages)

        logger.debug("---------- Bedrock Response End ----------")
