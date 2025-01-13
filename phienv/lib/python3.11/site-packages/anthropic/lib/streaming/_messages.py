from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, cast
from typing_extensions import Self, Iterator, Awaitable, AsyncIterator, assert_never

import httpx

from ._types import (
    TextEvent,
    InputJsonEvent,
    MessageStopEvent,
    MessageStreamEvent,
    ContentBlockStopEvent,
)
from ...types import Message, ContentBlock, RawMessageStreamEvent
from ..._utils import consume_sync_iterator, consume_async_iterator
from ..._models import build, construct_type
from ..._streaming import Stream, AsyncStream

if TYPE_CHECKING:
    from ..._client import Anthropic, AsyncAnthropic


class MessageStream:
    text_stream: Iterator[str]
    """Iterator over just the text deltas in the stream.

    ```py
    for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawMessageStreamEvent],
        response: httpx.Response,
        client: Anthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: Message | None = None

        self._iterator = self.__stream__()
        self._raw_stream: Stream[RawMessageStreamEvent] = Stream(cast_to=cast_to, response=response, client=client)

    def __next__(self) -> MessageStreamEvent:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[MessageStreamEvent]:
        for item in self._iterator:
            yield item

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        self.response.close()

    def get_final_message(self) -> Message:
        """Waits until the stream has been read to completion and returns
        the accumulated `Message` object.
        """
        self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    def until_done(self) -> None:
        """Blocks until the stream has been consumed"""
        consume_sync_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> Message:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def __stream__(self) -> Iterator[MessageStreamEvent]:
        for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    def __stream_text__(self) -> Iterator[str]:
        for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class MessageStreamManager:
    """Wrapper over MessageStream that is returned by `.stream()`.

    ```py
    with client.messages.stream(...) as stream:
        for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[RawMessageStreamEvent]],
    ) -> None:
        self.__stream: MessageStream | None = None
        self.__api_request = api_request

    def __enter__(self) -> MessageStream:
        raw_stream = self.__api_request()

        self.__stream = MessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncMessageStream:
    text_stream: AsyncIterator[str]
    """Async iterator over just the text deltas in the stream.

    ```py
    async for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawMessageStreamEvent],
        response: httpx.Response,
        client: AsyncAnthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: Message | None = None

        self._iterator = self.__stream__()
        self._raw_stream: AsyncStream[RawMessageStreamEvent] = AsyncStream(
            cast_to=cast_to, response=response, client=client
        )

    async def __anext__(self) -> MessageStreamEvent:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[MessageStreamEvent]:
        async for item in self._iterator:
            yield item

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        await self.response.aclose()

    async def get_final_message(self) -> Message:
        """Waits until the stream has been read to completion and returns
        the accumulated `Message` object.
        """
        await self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = await self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    async def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        await consume_async_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> Message:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def __stream__(self) -> AsyncIterator[MessageStreamEvent]:
        async for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    async def __stream_text__(self) -> AsyncIterator[str]:
        async for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class AsyncMessageStreamManager:
    """Wrapper over AsyncMessageStream that is returned by `.stream()`
    so that an async context manager can be used without `await`ing the
    original client call.

    ```py
    async with client.messages.stream(...) as stream:
        async for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawMessageStreamEvent]],
    ) -> None:
        self.__stream: AsyncMessageStream | None = None
        self.__api_request = api_request

    async def __aenter__(self) -> AsyncMessageStream:
        raw_stream = await self.__api_request

        self.__stream = AsyncMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


def build_events(
    *,
    event: RawMessageStreamEvent,
    message_snapshot: Message,
) -> list[MessageStreamEvent]:
    events_to_fire: list[MessageStreamEvent] = []

    if event.type == "message_start":
        events_to_fire.append(event)
    elif event.type == "message_delta":
        events_to_fire.append(event)
    elif event.type == "message_stop":
        events_to_fire.append(build(MessageStopEvent, type="message_stop", message=message_snapshot))
    elif event.type == "content_block_start":
        events_to_fire.append(event)
    elif event.type == "content_block_delta":
        events_to_fire.append(event)

        content_block = message_snapshot.content[event.index]
        if event.delta.type == "text_delta" and content_block.type == "text":
            events_to_fire.append(
                build(
                    TextEvent,
                    type="text",
                    text=event.delta.text,
                    snapshot=content_block.text,
                )
            )
        elif event.delta.type == "input_json_delta" and content_block.type == "tool_use":
            events_to_fire.append(
                build(
                    InputJsonEvent,
                    type="input_json",
                    partial_json=event.delta.partial_json,
                    snapshot=content_block.input,
                )
            )
    elif event.type == "content_block_stop":
        content_block = message_snapshot.content[event.index]

        events_to_fire.append(
            build(ContentBlockStopEvent, type="content_block_stop", index=event.index, content_block=content_block),
        )
    else:
        # we only want exhaustive checking for linters, not at runtime
        if TYPE_CHECKING:  # type: ignore[unreachable]
            assert_never(event)

    return events_to_fire


JSON_BUF_PROPERTY = "__json_buf"


def accumulate_event(
    *,
    event: RawMessageStreamEvent,
    current_snapshot: Message | None,
) -> Message:
    if current_snapshot is None:
        if event.type == "message_start":
            return Message.construct(**cast(Any, event.message.to_dict()))

        raise RuntimeError(f'Unexpected event order, got {event.type} before "message_start"')

    if event.type == "content_block_start":
        # TODO: check index
        current_snapshot.content.append(
            cast(
                ContentBlock,
                construct_type(type_=ContentBlock, value=event.content_block.model_dump()),
            ),
        )
    elif event.type == "content_block_delta":
        content = current_snapshot.content[event.index]
        if content.type == "text" and event.delta.type == "text_delta":
            content.text += event.delta.text
        elif content.type == "tool_use" and event.delta.type == "input_json_delta":
            from jiter import from_json

            # we need to keep track of the raw JSON string as well so that we can
            # re-parse it for each delta, for now we just store it as an untyped
            # property on the snapshot
            json_buf = cast(bytes, getattr(content, JSON_BUF_PROPERTY, b""))
            json_buf += bytes(event.delta.partial_json, "utf-8")

            if json_buf:
                content.input = from_json(json_buf, partial_mode=True)

            setattr(content, JSON_BUF_PROPERTY, json_buf)
    elif event.type == "message_delta":
        current_snapshot.stop_reason = event.delta.stop_reason
        current_snapshot.stop_sequence = event.delta.stop_sequence
        current_snapshot.usage.output_tokens = event.usage.output_tokens

    return current_snapshot
