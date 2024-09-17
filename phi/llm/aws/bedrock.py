import json
from typing import Optional, List, Iterator, Dict, Any

from phi.aws.api_client import AwsApiClient
from phi.llm.base import LLM
from phi.llm.message import Message
from phi.utils.retry import exponential_backoff
from phi.utils.log import logger
from phi.utils.timer import Timer
from phi.utils.tools import (
    get_function_call_for_tool_call,
)

try:
    from boto3 import session  # noqa: F401
    from botocore.exceptions import ClientError
except ImportError:
    logger.error("`boto3` not installed")
    raise


class AwsBedrock(LLM):
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
    def bedrock_client(self):
        if self._bedrock_client is not None:
            return self._bedrock_client

        boto3_session: session = self.get_aws_client().boto3_session
        self._bedrock_client = boto3_session.client(service_name="bedrock")
        return self._bedrock_client

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

    def get_model_summaries(self) -> List[Dict[str, Any]]:
        list_response: dict = self.bedrock_client.list_foundation_models()
        if list_response is None or "modelSummaries" not in list_response:
            return []

        return list_response["modelSummaries"]

    def get_model_ids(self) -> List[str]:
        model_summaries: List[Dict[str, Any]] = self.get_model_summaries()
        if len(model_summaries) == 0:
            return []

        return [model_summary["modelId"] for model_summary in model_summaries]

    def get_model_details(self) -> Dict[str, Any]:
        model_details: dict = self.bedrock_client.get_foundation_model(modelIdentifier=self.model)

        if model_details is None or "modelDetails" not in model_details:
            return {}

        return model_details["modelDetails"]

    @exponential_backoff(
        exceptions=(ClientError,),
        max_retries=5,
        base_delay=1,
        max_delay=60,
        factor=2,
        jitter=True
    )
    def _make_bedrock_request(self, modelId, messages, toolConfig=None, system=None):
        request_params = {
            "modelId": modelId,
            "messages": messages
        }

        if toolConfig is not None:
            request_params["toolConfig"] = toolConfig

        if system is not None:
            request_params["system"] = system

        return self.bedrock_runtime_client.converse(**request_params)

    def invoke_stream(self, body: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        response = self.bedrock_runtime_client.invoke_model_with_response_stream(
            body=json.dumps(body),
            modelId=self.model,
        )
        for event in response.get("body"):
            chunk = event.get("chunk")
            if chunk:
                yield json.loads(chunk.get("bytes").decode())

    def get_request_body(self, messages: List[Message]) -> Dict[str, Any]:
        raise NotImplementedError("Please use a subclass of AwsBedrock")

    def parse_response_message(self, response: Dict[str, Any]) -> Message:
        raise NotImplementedError("Please use a subclass of AwsBedrock")

    def parse_response_delta(self, response: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError("Please use a subclass of AwsBedrock")

    def response(self, messages: List[Message]) -> str:
        logger.debug("---------- Bedrock Response Start ----------")
        # Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        request_body = self.get_request_body(messages)
        tools = request_body.get("tools")
        sys_prompt = [{"text": request_body.get("system")}]
        
        try:
            response: Dict[str, Any] = self._make_bedrock_request(
                modelId=self.model,
                messages=request_body.get("messages", []),
                toolConfig={"tools": tools} if tools else None,
                system=sys_prompt if sys_prompt else None
            )
        except Exception as e:
            logger.error(f"Error making Bedrock request: {str(e)}")
            return "An error occurred while processing your request. Please try again later."


        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")
        logger.debug(f"Response: {response}")

        # Parse response
        response_content = response["output"]["message"]["content"][0]["text"]
        response_role = response["output"]["message"]["role"]
        logger.debug(f"Response content: {response_content}")

        # Create assistant message
        assistant_message = Message(
            role=response_role,
            content=response_content,
        )

        # Check if the response contains a tool call
        if response.get("stopReason") == "tool_use":
            tool_calls: List[Dict[str, Any]] = []
            tool_ids: List[str] = []
            for tool_use in response["output"]["message"]["content"]:
                if "toolUse" in tool_use:
                    tool = tool_use["toolUse"]
                    tool_name = tool["name"]
                    tool_input = tool["input"]
                    tool_use_id = tool["toolUseId"]
                    tool_ids.append(tool_use_id)

                    logger.info(f"Tool request: {tool_name}. Input: {tool_input}")
                    logger.info(f"Tool use ID: {tool_use_id}")

                    function_def = {"name": tool_name}
                    if tool_input:
                        function_def["arguments"] = json.dumps(tool_input)
                    tool_calls.append(
                        {
                            "type": "function",
                            "function": function_def,
                        }
                    )

            # Convert response_content to string
            assistant_message.content = response_content
            logger.info(f"Assistant content: {assistant_message.content}")

            if len(tool_calls) > 0:
                assistant_message.tool_calls = tool_calls
            logger.info(f"Assistant message: {assistant_message}")

        # Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        prompt_tokens = 0  # You may need to get this from the response if available
        completion_tokens = 0  # You may need to get this from the response if available
        if prompt_tokens is not None:
            assistant_message.metrics["prompt_tokens"] = prompt_tokens
            if "prompt_tokens" not in self.metrics:
                self.metrics["prompt_tokens"] = prompt_tokens
            else:
                self.metrics["prompt_tokens"] += prompt_tokens
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

        # Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        # Parse and run function call
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
                fc_responses: List[Dict[str, Any]] = []

                for _fc_message_index, _fc_message in enumerate(function_call_results):
                    fc_responses.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_ids[_fc_message_index],
                            "content": _fc_message.content,
                        }
                    )

                # Convert fc_responses to string
                try:
                    messages.append(Message(role="user", content=json.dumps(fc_responses)))
                except json.JSONDecodeError as e:
                    logger.error(f"Error serializing fc_responses: {e}")
                    messages.append(
                        Message(role="user", content=str(fc_responses))
                    )  # Fallback to string representation

            # Yield new response using results of tool calls
            final_response += self.response(messages=messages)
            return final_response
        logger.debug("---------- Bedrock Response End ----------")
        # Return content
        if assistant_message.content is not None:
            return assistant_message.get_content_string()
        return "Something went wrong, please try again."

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Bedrock Response Start ----------")

        assistant_message_content = ""
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for delta in self.invoke_stream(body=self.get_request_body(messages)):
            completion_tokens += 1
            # -*- Parse response
            content = self.parse_response_delta(delta)
            # -*- Yield completion
            if content is not None:
                assistant_message_content += content
                yield content

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(role="assistant")
        # -*- Add content to assistant message
        if assistant_message_content != "":
            assistant_message.content = assistant_message_content

        # -*- Update usage metrics
        # Add response time to metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # Add token usage to metrics
        prompt_tokens = 0
        assistant_message.metrics["prompt_tokens"] = prompt_tokens
        if "prompt_tokens" not in self.metrics:
            self.metrics["prompt_tokens"] = prompt_tokens
        else:
            self.metrics["prompt_tokens"] += prompt_tokens
        logger.debug(f"Estimated completion tokens: {completion_tokens}")
        assistant_message.metrics["completion_tokens"] = completion_tokens
        if "completion_tokens" not in self.metrics:
            self.metrics["completion_tokens"] = completion_tokens
        else:
            self.metrics["completion_tokens"] += completion_tokens
        total_tokens = prompt_tokens + completion_tokens
        assistant_message.metrics["total_tokens"] = total_tokens
        if "total_tokens" not in self.metrics:
            self.metrics["total_tokens"] = total_tokens
        else:
            self.metrics["total_tokens"] += total_tokens

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()
        logger.debug("---------- Bedrock Response End ----------")
