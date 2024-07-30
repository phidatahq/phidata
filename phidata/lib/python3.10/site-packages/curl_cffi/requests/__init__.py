__all__ = [
    "Session",
    "AsyncSession",
    "BrowserType",
    "CurlWsFlag",
    "request",
    "head",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "options",
    "RequestsError",
    "Cookies",
    "Headers",
    "Request",
    "Response",
    "WebSocket",
    "WebSocketError",
    "WsCloseCode",
]

from functools import partial
from io import BytesIO
from typing import Callable, Dict, List, Optional, Tuple, Union

from ..const import CurlHttpVersion, CurlWsFlag
from ..curl import CurlMime
from .cookies import Cookies, CookieTypes
from .errors import RequestsError
from .headers import Headers, HeaderTypes
from .models import Request, Response
from .session import AsyncSession, BrowserType, ProxySpec, Session, ThreadType
from .websockets import WebSocket, WebSocketError, WsCloseCode


def request(
    method: str,
    url: str,
    params: Optional[Union[Dict, List, Tuple]] = None,
    data: Optional[Union[Dict[str, str], List[Tuple], str, BytesIO, bytes]] = None,
    json: Optional[dict] = None,
    headers: Optional[HeaderTypes] = None,
    cookies: Optional[CookieTypes] = None,
    files: Optional[Dict] = None,
    auth: Optional[Tuple[str, str]] = None,
    timeout: Union[float, Tuple[float, float]] = 30,
    allow_redirects: bool = True,
    max_redirects: int = -1,
    proxies: Optional[ProxySpec] = None,
    proxy: Optional[str] = None,
    proxy_auth: Optional[Tuple[str, str]] = None,
    verify: Optional[bool] = None,
    referer: Optional[str] = None,
    accept_encoding: Optional[str] = "gzip, deflate, br",
    content_callback: Optional[Callable] = None,
    impersonate: Optional[Union[str, BrowserType]] = None,
    thread: Optional[ThreadType] = None,
    default_headers: Optional[bool] = None,
    default_encoding: Union[str, Callable[[bytes], str]] = "utf-8",
    curl_options: Optional[dict] = None,
    http_version: Optional[CurlHttpVersion] = None,
    debug: bool = False,
    interface: Optional[str] = None,
    multipart: Optional[CurlMime] = None,
    cert: Optional[Union[str, Tuple[str, str]]] = None,
) -> Response:
    """Send an http request.

    Parameters:
        method: http method for the request: GET/POST/PUT/DELETE etc.
        url: url for the requests.
        params: query string for the requests.
        data: form values or binary data to use in body, ``Content-Type: application/x-www-form-urlencoded`` will be added if a dict is given.
        json: json values to use in body, `Content-Type: application/json` will be added automatically.
        headers: headers to send.
        cookies: cookies to use.
        files: not supported, use ``multipart`` instead.
        auth: HTTP basic auth, a tuple of (username, password), only basic auth is supported.
        timeout: how many seconds to wait before giving up.
        allow_redirects: whether to allow redirection.
        max_redirects: max redirect counts, default unlimited(-1).
        proxies: dict of proxies to use, format: ``{"http": proxy_url, "https": proxy_url}``.
        proxy: proxy to use, format: "http://user@pass:proxy_url". Cannot be used with the above parameter.
        proxy_auth: HTTP basic auth for proxy, a tuple of (username, password).
        verify: whether to verify https certs.
        referer: shortcut for setting referer header.
        accept_encoding: shortcut for setting accept-encoding header.
        content_callback: a callback function to receive response body. ``def callback(chunk: bytes) -> None:``
        impersonate: which browser version to impersonate.
        thread: work with other thread implementations. choices: eventlet, gevent.
        default_headers: whether to set default browser headers.
        default_encoding: encoding for decoding response content if charset is not found in headers.
                Defaults to "utf-8". Can be set to a callable for automatic detection.
        curl_options: extra curl options to use.
        http_version: limiting http version, http2 will be tries by default.
        debug: print extra curl debug info.
        interface: which interface use in request to server.
        multipart: upload files using the multipart format, see.

    Returns:
        A ``Response`` object.
    """
    with Session(thread=thread, curl_options=curl_options, debug=debug) as s:
        return s.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            proxies=proxies,
            proxy=proxy,
            proxy_auth=proxy_auth,
            verify=verify,
            referer=referer,
            accept_encoding=accept_encoding,
            content_callback=content_callback,
            impersonate=impersonate,
            default_headers=default_headers,
            default_encoding=default_encoding,
            http_version=http_version,
            interface=interface,
            multipart=multipart,
            cert=cert,
        )


head = partial(request, "HEAD")
get = partial(request, "GET")
post = partial(request, "POST")
put = partial(request, "PUT")
patch = partial(request, "PATCH")
delete = partial(request, "DELETE")
options = partial(request, "OPTIONS")
