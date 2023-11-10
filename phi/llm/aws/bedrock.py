import json
from typing import Optional, List, Iterator, Dict, Any

from phi.aws.api_client import AwsApiClient
from phi.llm.base import LLM
from phi.llm.message import Message
from phi.utils.log import logger
from phi.utils.timer import Timer

try:
    from boto3 import session  # noqa: F401
except ImportError:
    logger.error("`boto3` not installed")
    raise


class AwsBedrock(LLM):
    name: str = "AwsBedrock"
    model: str = "anthropic.claude-v2"

    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_client: Optional[AwsApiClient] = None

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

    def invoke_model(self, prompt: str) -> Dict[str, Any]:
        body = {"prompt": prompt}
        body.update(self.api_kwargs)
        body_json = json.dumps(body)

        response = self.bedrock_runtime_client.invoke_model(
            body=body_json,
            modelId="anthropic.claude-v2",
            accept="application/json",
            contentType="application/json",
        )

        response_body = response.get("body")
        if response_body is None:
            return {}

        return json.loads(response_body.read())

    def invoke_model_stream(self, prompt: str) -> Iterator[Dict[str, Any]]:
        body = {"prompt": prompt}
        body.update(self.api_kwargs)
        body_json = json.dumps(body)

        response = self.bedrock_runtime_client.invoke_model_with_response_stream(
            body=body_json,
            modelId="anthropic.claude-v2",
        )

        for event in response.get("body"):
            chunk = event.get("chunk")
            if chunk:
                yield json.loads(chunk.get("bytes").decode())

    def build_prompt(self, messages: List[Message]) -> str:
        """Build prompt from messages"""

        prompt = ""
        for m in messages:
            if m.role == "user":
                if m.content is not None:
                    prompt += m.get_content_string()

        # -*- Log prompt for debugging
        logger.debug(f"PROMPT: {prompt}")
        return prompt

    def parsed_response(self, messages: List[Message]) -> str:
        logger.debug("---------- Aws Response Start ----------")

        response_timer = Timer()
        response_timer.start()
        response: Dict[str, Any] = self.invoke_model(prompt=self.build_prompt(messages))
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Parse response
        response_completion = response.get("completion")

        # -*- Create assistant message
        assistant_message = Message(
            role="assistant",
            content=response_completion,
        )

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

        logger.debug("---------- Aws Response End ----------")
        # -*- Return content
        return assistant_message.get_content_string()

    def response_message(self, messages: List[Message]) -> Dict:
        logger.debug("---------- Aws Response Start ----------")

        response_timer = Timer()
        response_timer.start()
        response: Dict[str, Any] = self.invoke_model(prompt=self.build_prompt(messages))
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Parse response
        response_completion = response.get("completion")

        # -*- Create assistant message
        assistant_message = Message(
            role="assistant",
            content=response_completion,
        )

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

        logger.debug("---------- Aws Response End ----------")
        # -*- Return content
        return response

    def parsed_response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Aws Response Start ----------")

        assistant_message_content = ""
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for delta in self.invoke_model_stream(prompt=self.build_prompt(messages)):
            completion_tokens += 1
            # -*- Parse response
            delta_completion = delta.get("completion")
            # -*- Yield completion
            if delta_completion is not None:
                assistant_message_content += delta_completion
                yield delta_completion

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
        logger.debug("---------- Aws Response End ----------")

    def response_delta(self, messages: List[Message]) -> Iterator[Dict]:
        logger.debug("---------- OpenAI Response Start ----------")

        assistant_message_content = ""
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for delta in self.invoke_model_stream(prompt=self.build_prompt(messages)):
            completion_tokens += 1
            # -*- Parse response
            delta_completion = delta.get("completion")
            # -*- Yield completion
            if delta_completion is not None:
                assistant_message_content += delta_completion
                yield delta

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
        logger.debug("---------- Aws Response End ----------")
