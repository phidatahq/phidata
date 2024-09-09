from typing import Optional, List, Iterator, Dict, Any
from phi.llm.base import LLM
from phi.llm.message import Message
from phi.utils.log import logger
from phi.utils.timer import Timer

try:
    from unify.clients import Unify as UnifyClient, AsyncUnify as AsyncUnifyClient
except ImportError:
    logger.error("`unify` not installed")
    raise


class UnifyChat(LLM):
    name: str = "UnifyChat"
    model: Optional[str] = None
    provider: Optional[str] = None
    endpoint: Optional[str] = None
    # -*- Request parameters
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stop: Optional[List[str]] = None
    request_params: Optional[Dict[str, Any]] = None
    # -*- Client parameters
    api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None
    # -*- Provide the Unify client manually
    unify_client: Optional[UnifyClient] = None
    async_unify_client: Optional[AsyncUnifyClient] = None

    def get_client(self) -> UnifyClient:
        if self.unify_client:
            return self.unify_client

        _client_params: Dict[str, Any] = {}
        if self.api_key:
            _client_params["api_key"] = self.api_key
        if self.endpoint:
            _client_params["endpoint"] = self.endpoint
        elif self.model and self.provider:
            _client_params["model"] = self.model
            _client_params["provider"] = self.provider
        if self.client_params:
            _client_params.update(self.client_params)
        return UnifyClient(**_client_params)

    def get_async_client(self) -> AsyncUnifyClient:
        if self.async_unify_client:
            return self.async_unify_client

        _client_params: Dict[str, Any] = {}
        if self.api_key:
            _client_params["api_key"] = self.api_key
        if self.endpoint:
            _client_params["endpoint"] = self.endpoint
        elif self.model and self.provider:
            _client_params["model"] = self.model
            _client_params["provider"] = self.provider
        if self.client_params:
            _client_params.update(self.client_params)
        return AsyncUnifyClient(**_client_params)

    @property
    def api_kwargs(self) -> Dict[str, Any]:
        _request_params: Dict[str, Any] = {}
        if self.max_tokens:
            _request_params["max_tokens"] = self.max_tokens
        if self.temperature:
            _request_params["temperature"] = self.temperature
        if self.stop:
            _request_params["stop"] = self.stop
        if self.request_params:
            _request_params.update(self.request_params)
        return _request_params

    def invoke(self, messages: List[Message]) -> Any:
        client = self.get_client()
        return client.generate(
            messages=[m.to_dict() for m in messages],
            **self.api_kwargs,
        )

    async def ainvoke(self, messages: List[Message]) -> Any:
        client = self.get_async_client()
        return await client.generate(
            messages=[m.to_dict() for m in messages],
            **self.api_kwargs,
        )

    def invoke_stream(self, messages: List[Message]) -> Iterator[Any]:
        client = self.get_client()
        return client.generate(
            messages=[m.to_dict() for m in messages],
            stream=True,
            **self.api_kwargs,
        )

    async def ainvoke_stream(self, messages: List[Message]) -> Any:
        client = self.get_async_client()
        async for chunk in await client.generate(
            messages=[m.to_dict() for m in messages],
            stream=True,
            **self.api_kwargs,
        ):
            yield chunk

    def response(self, messages: List[Message]) -> str:
        logger.debug("---------- Unify Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response = self.invoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(
            role="assistant",
            content=response,
        )

        # -*- Update usage metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        logger.debug("---------- Unify Response End ----------")
        return assistant_message.get_content_string()

    def response_stream(self, messages: List[Message]) -> Iterator[str]:
        logger.debug("---------- Unify Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        assistant_message_content = ""
        completion_tokens = 0
        response_timer = Timer()
        response_timer.start()
        for chunk in self.invoke_stream(messages=messages):
            assistant_message_content += chunk
            completion_tokens += 1
            yield chunk

        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(role="assistant", content=assistant_message_content)

        # -*- Update usage metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        logger.debug("---------- Unify Response End ----------")

    async def aresponse(self, messages: List[Message]) -> str:
        logger.debug("---------- Unify Async Response Start ----------")
        # -*- Log messages for debugging
        for m in messages:
            m.log()

        response_timer = Timer()
        response_timer.start()
        response = await self.ainvoke(messages=messages)
        response_timer.stop()
        logger.debug(f"Time to generate response: {response_timer.elapsed:.4f}s")

        # -*- Create assistant message
        assistant_message = Message(
            role="assistant",
            content=response,
        )

        # -*- Update usage metrics
        assistant_message.metrics["time"] = response_timer.elapsed
        if "response_times" not in self.metrics:
            self.metrics["response_times"] = []
        self.metrics["response_times"].append(response_timer.elapsed)

        # -*- Add assistant message to messages
        messages.append(assistant_message)
        assistant_message.log()

        logger.debug("---------- Unify Async Response End ----------")
        return assistant_message.get_content_string()

    def get_credit_balance(self) -> float:
        client = self.get_client()
        return client.get_credit_balance()