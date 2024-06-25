import asyncio
from concurrent.futures import Future
from threading import Thread
from types import TracebackType
from typing import Any, Awaitable, Dict, Optional, Type, Union

from .duckduckgo_search_async import AsyncDDGS


class DDGS(AsyncDDGS):
    _loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
    Thread(target=_loop.run_forever, daemon=True).start()  # Start the event loop run in a separate thread.

    def __init__(
        self,
        headers: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        proxies: Union[Dict[str, str], str, None] = None,  # deprecated
        timeout: Optional[int] = 10,
    ) -> None:
        """Initialize the DDGS object.

        Args:
            headers (dict, optional): Dictionary of headers for the HTTP client. Defaults to None.
            proxy (str, optional): proxy for the HTTP client, supports http/https/socks5 protocols.
                example: "http://user:pass@example.com:3128". Defaults to None.
            timeout (int, optional): Timeout value for the HTTP client. Defaults to 10.
        """
        super().__init__(headers=headers, proxy=proxy, proxies=proxies, timeout=timeout)

    def __enter__(self) -> "DDGS":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self._close_session()

    def __del__(self) -> None:
        self._close_session()

    def _close_session(self) -> None:
        """Close the curl-cffi async session."""
        if hasattr(self, "_asession") and self._asession._closed is False:
            self._run_async_in_thread(self._asession.close())

    def _run_async_in_thread(self, coro: Awaitable[Any]) -> Any:
        """Runs an async coroutine in a separate thread."""
        future: Future[Any] = asyncio.run_coroutine_threadsafe(coro, self._loop)
        result = future.result()
        return result

    def text(self, *args: Any, **kwargs: Any) -> Any:
        return self._run_async_in_thread(super().text(*args, **kwargs))

    def images(self, *args: Any, **kwargs: Any) -> Any:
        return self._run_async_in_thread(super().images(*args, **kwargs))

    def videos(self, *args: Any, **kwargs: Any) -> Any:
        return self._run_async_in_thread(super().videos(*args, **kwargs))

    def news(self, *args: Any, **kwargs: Any) -> Any:
        return self._run_async_in_thread(super().news(*args, **kwargs))

    def answers(self, *args: Any, **kwargs: Any) -> Any:
        return self._run_async_in_thread(super().answers(*args, **kwargs))

    def suggestions(self, *args: Any, **kwargs: Any) -> Any:
        return self._run_async_in_thread(super().suggestions(*args, **kwargs))

    def maps(self, *args: Any, **kwargs: Any) -> Any:
        return self._run_async_in_thread(super().maps(*args, **kwargs))

    def translate(self, *args: Any, **kwargs: Any) -> Any:
        return self._run_async_in_thread(super().translate(*args, **kwargs))
