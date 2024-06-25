import asyncio
import math
import queue
import threading
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from enum import Enum
from functools import partialmethod
from io import BytesIO
from json import dumps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypedDict,
    Union,
    cast,
)
from urllib.parse import ParseResult, parse_qsl, unquote, urlencode, urljoin, urlparse

from .. import AsyncCurl, Curl, CurlError, CurlHttpVersion, CurlInfo, CurlOpt
from ..curl import CURL_WRITEFUNC_ERROR, CurlMime
from .cookies import Cookies, CookieTypes, CurlMorsel
from .errors import RequestsError, SessionClosed
from .headers import Headers, HeaderTypes
from .models import Request, Response
from .websockets import WebSocket

try:
    import gevent
except ImportError:
    pass

try:
    import eventlet.tpool
except ImportError:
    pass

if TYPE_CHECKING:

    class ProxySpec(TypedDict, total=False):
        all: str
        http: str
        https: str
        ws: str
        wss: str

else:
    ProxySpec = Dict[str, str]

ThreadType = Literal["eventlet", "gevent"]


class BrowserType(str, Enum):
    edge99 = "edge99"
    edge101 = "edge101"
    chrome99 = "chrome99"
    chrome100 = "chrome100"
    chrome101 = "chrome101"
    chrome104 = "chrome104"
    chrome107 = "chrome107"
    chrome110 = "chrome110"
    chrome116 = "chrome116"
    chrome119 = "chrome119"
    chrome120 = "chrome120"
    chrome99_android = "chrome99_android"
    safari15_3 = "safari15_3"
    safari15_5 = "safari15_5"
    safari17_0 = "safari17_0"
    safari17_2_ios = "safari17_2_ios"

    chrome = "chrome120"
    safari = "safari17_0"
    safari_ios = "safari17_2_ios"

    @classmethod
    def has(cls, item):
        return item in cls.__members__

    @classmethod
    def normalize(cls, item):
        if item == "chrome":
            return cls.chrome
        elif item == "safari":
            return cls.safari
        elif item == "safari_ios":
            return cls.safari_ios
        else:
            return item


class BrowserSpec:
    """A more structured way of selecting browsers"""

    # TODO


def _is_absolute_url(url: str) -> bool:
    """Check if the provided url is an absolute url"""
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme and parsed_url.hostname)


def _update_url_params(url: str, params: Union[Dict, List, Tuple]) -> str:
    """Add GET params to provided URL being aware of existing.

    Parameters:
        url: string of target URL
        params: dict containing requested params to be added

    Returns:
        string with updated URL

    >> url = 'http://stackoverflow.com/test?answers=true'
    >> new_params = {'answers': False, 'data': ['some','values']}
    >> _update_url_params(url, new_params)
    'http://stackoverflow.com/test?data=some&data=values&answers=false'
    """
    # Unquoting URL first so we don't loose existing args
    url = unquote(url)

    # Extracting url info
    parsed_url = urlparse(url)

    # Extracting URL arguments from parsed URL
    get_args = parsed_url.query

    # Do NOT converting URL arguments to dict
    parsed_get_args = parse_qsl(get_args)

    # Merging URL arguments dict with new params
    old_args_counter = Counter((x[0] for x in parsed_get_args))
    if isinstance(params, dict):
        params = list(params.items())
    new_args_counter = Counter((x[0] for x in params))

    for key, value in params:
        # Bool and Dict values should be converted to json-friendly values
        # you may throw this part away if you don't like it :)
        if isinstance(value, (bool, dict)):
            value = dumps(value)

        # 1 to 1 mapping, we have to search and update it.
        if old_args_counter.get(key) == 1 and new_args_counter.get(key) == 1:
            parsed_get_args = [(x if x[0] != key else (key, value)) for x in parsed_get_args]
        else:
            parsed_get_args.append((key, value))

    # Converting URL argument to proper query string
    encoded_get_args = urlencode(parsed_get_args, doseq=True)

    # Creating new parsed result object based on provided with new
    # URL arguments. Same thing happens inside of urlparse.
    new_url = ParseResult(
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        encoded_get_args,
        parsed_url.fragment,
    ).geturl()

    return new_url


def _update_header_line(header_lines: List[str], key: str, value: str):
    """Update header line list by key value pair."""
    for idx, line in enumerate(header_lines):
        if line.lower().startswith(key.lower() + ":"):
            header_lines[idx] = f"{key}: {value}"
            break
    else:  # if not break
        header_lines.append(f"{key}: {value}")


def _peek_queue(q: queue.Queue, default=None):
    try:
        return q.queue[0]
    except IndexError:
        return default


def _peek_aio_queue(q: asyncio.Queue, default=None):
    try:
        return q._queue[0]  # type: ignore
    except IndexError:
        return default


not_set = object()


class BaseSession:
    """Provide common methods for setting curl options and reading info in sessions."""

    def __init__(
        self,
        *,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        auth: Optional[Tuple[str, str]] = None,
        proxies: Optional[ProxySpec] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[Tuple[str, str]] = None,
        base_url: Optional[str] = None,
        params: Optional[dict] = None,
        verify: bool = True,
        timeout: Union[float, Tuple[float, float]] = 30,
        trust_env: bool = True,
        allow_redirects: bool = True,
        max_redirects: int = -1,
        impersonate: Optional[Union[str, BrowserType]] = None,
        default_headers: bool = True,
        default_encoding: Union[str, Callable[[bytes], str]] = "utf-8",
        curl_options: Optional[dict] = None,
        curl_infos: Optional[list] = None,
        http_version: Optional[CurlHttpVersion] = None,
        debug: bool = False,
        interface: Optional[str] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
    ):
        self.headers = Headers(headers)
        self.cookies = Cookies(cookies)
        self.auth = auth
        self.base_url = base_url
        self.params = params
        self.verify = verify
        self.timeout = timeout
        self.trust_env = trust_env
        self.allow_redirects = allow_redirects
        self.max_redirects = max_redirects
        self.impersonate = impersonate
        self.default_headers = default_headers
        self.default_encoding = default_encoding
        self.curl_options = curl_options or {}
        self.curl_infos = curl_infos or []
        self.http_version = http_version
        self.debug = debug
        self.interface = interface
        self.cert = cert

        if proxy and proxies:
            raise TypeError("Cannot specify both 'proxy' and 'proxies'")
        if proxy:
            proxies = {"all": proxy}
        self.proxies: ProxySpec = proxies or {}
        self.proxy_auth = proxy_auth

        if self.base_url and not _is_absolute_url(self.base_url):
            raise ValueError("You need to provide an absolute url for 'base_url'")

        self._closed = False

    def _set_curl_options(
        self,
        curl,
        method: str,
        url: str,
        params: Optional[Union[Dict, List, Tuple]] = None,
        data: Optional[Union[Dict[str, str], List[Tuple], str, BytesIO, bytes]] = None,
        json: Optional[dict] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        files: Optional[Dict] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Optional[Union[float, Tuple[float, float], object]] = not_set,
        allow_redirects: Optional[bool] = None,
        max_redirects: Optional[int] = None,
        proxies: Optional[ProxySpec] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[Tuple[str, str]] = None,
        verify: Optional[Union[bool, str]] = None,
        referer: Optional[str] = None,
        accept_encoding: Optional[str] = "gzip, deflate, br",
        content_callback: Optional[Callable] = None,
        impersonate: Optional[Union[str, BrowserType]] = None,
        default_headers: Optional[bool] = None,
        http_version: Optional[CurlHttpVersion] = None,
        interface: Optional[str] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        stream: bool = False,
        max_recv_speed: int = 0,
        multipart: Optional[CurlMime] = None,
        queue_class: Any = None,
        event_class: Any = None,
    ):
        c = curl

        # method
        if method == "POST":
            c.setopt(CurlOpt.POST, 1)
        elif method != "GET":
            c.setopt(CurlOpt.CUSTOMREQUEST, method.encode())

        # url
        if self.params:
            url = _update_url_params(url, self.params)
        if params:
            url = _update_url_params(url, params)
        if self.base_url:
            url = urljoin(self.base_url, url)
        c.setopt(CurlOpt.URL, url.encode())

        # data/body/json
        if isinstance(data, (dict, list, tuple)):
            body = urlencode(data).encode()
        elif isinstance(data, str):
            body = data.encode()
        elif isinstance(data, BytesIO):
            body = data.read()
        elif isinstance(data, bytes):
            body = data
        elif data is None:
            body = b""
        else:
            raise TypeError("data must be dict, str, BytesIO or bytes")
        if json is not None:
            body = dumps(json, separators=(",", ":")).encode()

        # Tell libcurl to be aware of bodies and related headers when,
        # 1. POST/PUT/PATCH, even if the body is empty, it's up to curl to decide what to do;
        # 2. GET/DELETE with body, although it's against the RFC, some applications. e.g. Elasticsearch, use this.
        if body or method in ("POST", "PUT", "PATCH"):
            c.setopt(CurlOpt.POSTFIELDS, body)
            # necessary if body contains '\0'
            c.setopt(CurlOpt.POSTFIELDSIZE, len(body))

        # headers
        h = Headers(self.headers)
        h.update(headers)

        # remove Host header if it's unnecessary, otherwise curl maybe confused.
        # Host header will be automatically added by curl if it's not present.
        # https://github.com/yifeikong/curl_cffi/issues/119
        host_header = h.get("Host")
        if host_header is not None:
            u = urlparse(url)
            if host_header == u.netloc or host_header == u.hostname:
                try:
                    del h["Host"]
                except KeyError:
                    pass

        header_lines = []
        for k, v in h.multi_items():
            header_lines.append(f"{k}: {v}")
        if json is not None:
            _update_header_line(header_lines, "Content-Type", "application/json")
        if isinstance(data, dict) and method != "POST":
            _update_header_line(header_lines, "Content-Type", "application/x-www-form-urlencoded")
        # print("header lines", header_lines)
        c.setopt(CurlOpt.HTTPHEADER, [h.encode() for h in header_lines])

        req = Request(url, h, method)

        # cookies
        c.setopt(CurlOpt.COOKIEFILE, b"")  # always enable the curl cookie engine first
        c.setopt(CurlOpt.COOKIELIST, "ALL")  # remove all the old cookies first.

        for morsel in self.cookies.get_cookies_for_curl(req):
            # print("Setting", morsel.to_curl_format())
            curl.setopt(CurlOpt.COOKIELIST, morsel.to_curl_format())
        if cookies:
            temp_cookies = Cookies(cookies)
            for morsel in temp_cookies.get_cookies_for_curl(req):
                curl.setopt(CurlOpt.COOKIELIST, morsel.to_curl_format())

        # files
        if files:
            raise NotImplementedError("files is not supported, use `multipart`.")

        # multipart
        if multipart:
            # multipart will overrides postfields
            for k, v in cast(dict, data or {}).items():
                multipart.addpart(name=k, data=v.encode() if isinstance(v, str) else v)
            c.setopt(CurlOpt.MIMEPOST, multipart._form)

        # auth
        if self.auth or auth:
            if self.auth:
                username, password = self.auth
            if auth:
                username, password = auth
            c.setopt(CurlOpt.USERNAME, username.encode())  # pyright: ignore [reportPossiblyUnboundVariable=none]
            c.setopt(CurlOpt.PASSWORD, password.encode())  # pyright: ignore [reportPossiblyUnboundVariable=none]

        # timeout
        if timeout is not_set:
            timeout = self.timeout
        if timeout is None:
            timeout = 0  # indefinitely

        if isinstance(timeout, tuple):
            connect_timeout, read_timeout = timeout
            all_timeout = connect_timeout + read_timeout
            c.setopt(CurlOpt.CONNECTTIMEOUT_MS, int(connect_timeout * 1000))
            if not stream:
                c.setopt(CurlOpt.TIMEOUT_MS, int(all_timeout * 1000))
            else:
                # trick from: https://github.com/yifeikong/curl_cffi/issues/156
                c.setopt(CurlOpt.LOW_SPEED_LIMIT, 1)
                c.setopt(CurlOpt.LOW_SPEED_TIME, math.ceil(all_timeout))

        elif isinstance(timeout, (int, float)):
            if not stream:
                c.setopt(CurlOpt.TIMEOUT_MS, int(timeout * 1000))
            else:
                c.setopt(CurlOpt.CONNECTTIMEOUT_MS, int(timeout * 1000))
                c.setopt(CurlOpt.LOW_SPEED_LIMIT, 1)
                c.setopt(CurlOpt.LOW_SPEED_TIME, math.ceil(timeout))

        # allow_redirects
        c.setopt(
            CurlOpt.FOLLOWLOCATION,
            int(self.allow_redirects if allow_redirects is None else allow_redirects),
        )

        # max_redirects
        c.setopt(
            CurlOpt.MAXREDIRS,
            self.max_redirects if max_redirects is None else max_redirects,
        )

        # proxies
        if proxy and proxies:
            raise TypeError("Cannot specify both 'proxy' and 'proxies'")
        if proxy:
            proxies = {"all": proxy}
        if proxies is None:
            proxies = self.proxies

        if proxies:
            parts = urlparse(url)
            proxy = cast(Optional[str], proxies.get(parts.scheme, proxies.get("all")))
            if parts.hostname:
                proxy = (
                    cast(
                        Optional[str],
                        proxies.get(
                            f"{parts.scheme}://{parts.hostname}",
                            proxies.get(f"all://{parts.hostname}"),
                        ),
                    )
                    or proxy
                )

            if proxy is not None:
                if parts.scheme == "https" and proxy.startswith("https://"):
                    warnings.warn(
                        "You may be using http proxy WRONG, the prefix should be 'http://' not 'https://',"
                        "see: https://github.com/yifeikong/curl_cffi/issues/6",
                        RuntimeWarning,
                        stacklevel=2,
                    )

                c.setopt(CurlOpt.PROXY, proxy)
                # for http proxy, need to tell curl to enable tunneling
                if not proxy.startswith("socks"):
                    c.setopt(CurlOpt.HTTPPROXYTUNNEL, 1)

                # proxy_auth
                proxy_auth = proxy_auth or self.proxy_auth
                if proxy_auth:
                    username, password = proxy_auth
                    c.setopt(CurlOpt.PROXYUSERNAME, username.encode())
                    c.setopt(CurlOpt.PROXYPASSWORD, password.encode())

        # verify
        if verify is False or not self.verify and verify is None:
            c.setopt(CurlOpt.SSL_VERIFYPEER, 0)
            c.setopt(CurlOpt.SSL_VERIFYHOST, 0)

        # cert for this single request
        if isinstance(verify, str):
            c.setopt(CurlOpt.CAINFO, verify)

        # cert for the session
        if verify in (None, True) and isinstance(self.verify, str):
            c.setopt(CurlOpt.CAINFO, self.verify)

        # referer
        if referer:
            c.setopt(CurlOpt.REFERER, referer.encode())

        # accept_encoding
        if accept_encoding is not None:
            c.setopt(CurlOpt.ACCEPT_ENCODING, accept_encoding.encode())

        # cert
        cert = cert or self.cert
        if cert:
            if isinstance(cert, str):
                c.setopt(CurlOpt.SSLCERT, cert)
            else:
                cert, key = cert
                c.setopt(CurlOpt.SSLCERT, cert)
                c.setopt(CurlOpt.SSLKEY, key)

        # impersonate
        impersonate = impersonate or self.impersonate
        default_headers = self.default_headers if default_headers is None else default_headers
        if impersonate:
            impersonate = BrowserType.normalize(impersonate)
            ret = c.impersonate(impersonate, default_headers=default_headers)
            if ret != 0:
                raise RequestsError(f"Impersonating {impersonate} is not supported")

        # http_version, after impersonate, which will change this to http2
        http_version = http_version or self.http_version
        if http_version:
            c.setopt(CurlOpt.HTTP_VERSION, http_version)

        # set extra curl options, must come after impersonate, because it will alter some options
        for k, v in self.curl_options.items():
            c.setopt(k, v)

        buffer = None
        q = None
        header_recved = None
        quit_now = None
        if stream:
            q = queue_class()
            header_recved = event_class()
            quit_now = event_class()

            def qput(chunk):
                if not header_recved.is_set():
                    header_recved.set()
                if quit_now.is_set():
                    return CURL_WRITEFUNC_ERROR
                q.put_nowait(chunk)
                return len(chunk)

            c.setopt(CurlOpt.WRITEFUNCTION, qput)
        elif content_callback is not None:
            c.setopt(CurlOpt.WRITEFUNCTION, content_callback)
        else:
            buffer = BytesIO()
            c.setopt(CurlOpt.WRITEDATA, buffer)
        header_buffer = BytesIO()
        c.setopt(CurlOpt.HEADERDATA, header_buffer)

        if method == "HEAD":
            c.setopt(CurlOpt.NOBODY, 1)

        # interface
        interface = interface or self.interface
        if interface:
            c.setopt(CurlOpt.INTERFACE, interface.encode())

        # max_recv_speed
        # do not check, since 0 is a valid value to disable it
        c.setopt(CurlOpt.MAX_RECV_SPEED_LARGE, max_recv_speed)

        return req, buffer, header_buffer, q, header_recved, quit_now

    def _parse_response(self, curl, buffer, header_buffer, default_encoding):
        c = curl
        rsp = Response(c)
        rsp.url = cast(bytes, c.getinfo(CurlInfo.EFFECTIVE_URL)).decode()
        if buffer:
            rsp.content = buffer.getvalue()
        rsp.http_version = cast(int, c.getinfo(CurlInfo.HTTP_VERSION))
        rsp.status_code = cast(int, c.getinfo(CurlInfo.RESPONSE_CODE))
        rsp.ok = 200 <= rsp.status_code < 400
        header_lines = header_buffer.getvalue().splitlines()

        # TODO history urls
        header_list = []
        for header_line in header_lines:
            if not header_line.strip():
                continue
            if header_line.startswith(b"HTTP/"):
                # read header from last response
                rsp.reason = c.get_reason_phrase(header_line).decode()
                # empty header list for new redirected response
                header_list = []
                continue
            if header_line.startswith(b" ") or header_line.startswith(b"\t"):
                header_list[-1] += header_line
                continue
            header_list.append(header_line)
        rsp.headers = Headers(header_list)
        # print("Set-cookie", rsp.headers["set-cookie"])
        morsels = [CurlMorsel.from_curl_format(c) for c in c.getinfo(CurlInfo.COOKIELIST)]
        # for l in c.getinfo(CurlInfo.COOKIELIST):
        #     print("Curl Cookies", l.decode())

        self.cookies.update_cookies_from_curl(morsels)
        rsp.cookies = self.cookies
        # print("Cookies after extraction", self.cookies)

        rsp.default_encoding = default_encoding
        rsp.elapsed = cast(float, c.getinfo(CurlInfo.TOTAL_TIME))
        rsp.redirect_count = cast(int, c.getinfo(CurlInfo.REDIRECT_COUNT))
        rsp.redirect_url = cast(bytes, c.getinfo(CurlInfo.REDIRECT_URL)).decode()

        for info in self.curl_infos:
            rsp.infos[info] = c.getinfo(info)

        return rsp

    def _check_session_closed(self):
        if self._closed:
            raise SessionClosed("Session is closed, cannot send request.")


class Session(BaseSession):
    """A request session, cookies and connections will be reused. This object is thread-safe,
    but it's recommended to use a seperate session for each thread."""

    def __init__(
        self,
        curl: Optional[Curl] = None,
        thread: Optional[ThreadType] = None,
        use_thread_local_curl: bool = True,
        **kwargs,
    ):
        """
        Parameters set in the init method will be override by the same parameter in request method.

        Args:
            curl: curl object to use in the session. If not provided, a new one will be
                created. Also, a fresh curl object will always be created when accessed
                from another thread.
            thread: thread engine to use for working with other thread implementations.
                choices: eventlet, gevent., possible values: eventlet, gevent.
            headers: headers to use in the session.
            cookies: cookies to add in the session.
            auth: HTTP basic auth, a tuple of (username, password), only basic auth is supported.
            proxies: dict of proxies to use, format: {"http": proxy_url, "https": proxy_url}.
            proxy: proxy to use, format: "http://proxy_url". Cannot be used with the above parameter.
            proxy_auth: HTTP basic auth for proxy, a tuple of (username, password).
            base_url: absolute url to use for relative urls.
            params: query string for the session.
            verify: whether to verify https certs.
            timeout: how many seconds to wait before giving up.
            trust_env: use http_proxy/https_proxy and other environments, default True.
            allow_redirects: whether to allow redirection.
            max_redirects: max redirect counts, default unlimited(-1).
            impersonate: which browser version to impersonate in the session.
            interface: which interface use in request to server.
            default_encoding: encoding for decoding response content if charset is not found in headers.
                Defaults to "utf-8". Can be set to a callable for automatic detection.

        Notes:
            This class can be used as a context manager.

        .. code-block:: python

            from curl_cffi.requests import Session

            with Session() as s:
                r = s.get("https://example.com")
        """
        super().__init__(**kwargs)
        self._thread = thread
        self._use_thread_local_curl = use_thread_local_curl
        self._queue = None
        self._executor = None
        if use_thread_local_curl:
            self._local = threading.local()
            if curl:
                self._is_customized_curl = True
                self._local.curl = curl
            else:
                self._is_customized_curl = False
                self._local.curl = Curl(debug=self.debug)
        else:
            self._curl = curl if curl else Curl(debug=self.debug)

    @property
    def curl(self):
        if self._use_thread_local_curl:
            if self._is_customized_curl:
                warnings.warn("Creating fresh curl handle in different thread.")
            if not getattr(self._local, "curl", None):
                self._local.curl = Curl(debug=self.debug)
            return self._local.curl
        else:
            return self._curl

    @property
    def executor(self):
        if self._executor is None:
            self._executor = ThreadPoolExecutor()
        return self._executor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Close the session."""
        self._closed = True
        self.curl.close()

    @contextmanager
    def stream(self, *args, **kwargs):
        """Equivalent to ``with request(..., stream=True) as r:``"""
        rsp = self.request(*args, **kwargs, stream=True)
        try:
            yield rsp
        finally:
            rsp.close()

    def ws_connect(
        self,
        url,
        *args,
        on_message: Optional[Callable[[WebSocket, bytes], None]] = None,
        on_error: Optional[Callable[[WebSocket, CurlError], None]] = None,
        on_open: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
        **kwargs,
    ) -> WebSocket:
        """Connects to a websocket url.

        Args:
            url: the ws url to connect.
            on_message: message callback, ``def on_message(ws, str)``
            on_error: error callback, ``def on_error(ws, error)``
            on_open: open callback, ``def on_open(ws)``
            on_cloes: close callback, ``def on_close(ws)``

        Other parameters are the same as ``.request``

        Returns:
            a ws instance to communicate with the server.
        """
        self._check_session_closed()

        self._set_curl_options(self.curl, "GET", url, *args, **kwargs)

        # https://curl.se/docs/websocket.html
        self.curl.setopt(CurlOpt.CONNECT_ONLY, 2)
        self.curl.perform()

        return WebSocket(
            self,
            self.curl,
            on_message=on_message,
            on_error=on_error,
            on_open=on_open,
            on_close=on_close,
        )

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Union[Dict, List, Tuple]] = None,
        data: Optional[Union[Dict[str, str], List[Tuple], str, BytesIO, bytes]] = None,
        json: Optional[dict] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        files: Optional[Dict] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Optional[Union[float, Tuple[float, float], object]] = not_set,
        allow_redirects: Optional[bool] = None,
        max_redirects: Optional[int] = None,
        proxies: Optional[ProxySpec] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[Tuple[str, str]] = None,
        verify: Optional[bool] = None,
        referer: Optional[str] = None,
        accept_encoding: Optional[str] = "gzip, deflate, br",
        content_callback: Optional[Callable] = None,
        impersonate: Optional[Union[str, BrowserType]] = None,
        default_headers: Optional[bool] = None,
        default_encoding: Union[str, Callable[[bytes], str]] = "utf-8",
        http_version: Optional[CurlHttpVersion] = None,
        interface: Optional[str] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        stream: bool = False,
        max_recv_speed: int = 0,
        multipart: Optional[CurlMime] = None,
    ) -> Response:
        """Send the request, see ``requests.request`` for details on parameters."""

        self._check_session_closed()

        # clone a new curl instance for streaming response
        if stream:
            c = self.curl.duphandle()
            self.curl.reset()
        else:
            c = self.curl

        req, buffer, header_buffer, q, header_recved, quit_now = self._set_curl_options(
            c,
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
            http_version=http_version,
            interface=interface,
            stream=stream,
            max_recv_speed=max_recv_speed,
            multipart=multipart,
            cert=cert,
            queue_class=queue.Queue,
            event_class=threading.Event,
        )

        if stream:
            header_parsed = threading.Event()

            def perform():
                try:
                    c.perform()
                except CurlError as e:
                    rsp = self._parse_response(c, buffer, header_buffer, default_encoding)
                    rsp.request = req
                    cast(queue.Queue, q).put_nowait(RequestsError(str(e), e.code, rsp))
                finally:
                    if not cast(threading.Event, header_recved).is_set():
                        cast(threading.Event, header_recved).set()
                    # None acts as a sentinel
                    cast(queue.Queue, q).put(None)

            def cleanup(fut):
                header_parsed.wait()
                c.reset()

            stream_task = self.executor.submit(perform)
            stream_task.add_done_callback(cleanup)

            # Wait for the first chunk
            cast(threading.Event, header_recved).wait()
            rsp = self._parse_response(c, buffer, header_buffer, default_encoding)
            header_parsed.set()

            # Raise the exception if something wrong happens when receiving the header.
            first_element = _peek_queue(cast(queue.Queue, q))
            if isinstance(first_element, RequestsError):
                c.reset()
                raise first_element

            rsp.request = req
            rsp.stream_task = stream_task
            rsp.quit_now = quit_now
            rsp.queue = q
            return rsp
        else:
            try:
                if self._thread == "eventlet":
                    # see: https://eventlet.net/doc/threading.html
                    eventlet.tpool.execute(c.perform)
                elif self._thread == "gevent":
                    # see: https://www.gevent.org/api/gevent.threadpool.html
                    gevent.get_hub().threadpool.spawn(c.perform).get()
                else:
                    c.perform()
            except CurlError as e:
                rsp = self._parse_response(c, buffer, header_buffer, default_encoding)
                rsp.request = req
                raise RequestsError(str(e), e.code, rsp) from e
            else:
                rsp = self._parse_response(c, buffer, header_buffer, default_encoding)
                rsp.request = req
                return rsp
            finally:
                c.reset()

    head = partialmethod(request, "HEAD")
    get = partialmethod(request, "GET")
    post = partialmethod(request, "POST")
    put = partialmethod(request, "PUT")
    patch = partialmethod(request, "PATCH")
    delete = partialmethod(request, "DELETE")
    options = partialmethod(request, "OPTIONS")


class AsyncSession(BaseSession):
    """An async request session, cookies and connections will be reused."""

    def __init__(
        self,
        *,
        loop=None,
        async_curl: Optional[AsyncCurl] = None,
        max_clients: int = 10,
        **kwargs,
    ):
        """
        Parameters set in the init method will be override by the same parameter in request method.

        Parameters:
            loop: loop to use, if not provided, the running loop will be used.
            async_curl: [AsyncCurl](/api/curl_cffi#curl_cffi.AsyncCurl) object to use.
            max_clients: maxmium curl handle to use in the session, this will affect the concurrency ratio.
            headers: headers to use in the session.
            cookies: cookies to add in the session.
            auth: HTTP basic auth, a tuple of (username, password), only basic auth is supported.
            proxies: dict of proxies to use, format: {"http": proxy_url, "https": proxy_url}.
            proxy: proxy to use, format: "http://proxy_url". Cannot be used with the above parameter.
            proxy_auth: HTTP basic auth for proxy, a tuple of (username, password).
            base_url: absolute url to use for relative urls.
            params: query string for the session.
            verify: whether to verify https certs.
            timeout: how many seconds to wait before giving up.
            trust_env: use http_proxy/https_proxy and other environments, default True.
            allow_redirects: whether to allow redirection.
            max_redirects: max redirect counts, default unlimited(-1).
            impersonate: which browser version to impersonate in the session.
            default_encoding: encoding for decoding response content if charset is not found in headers.
                Defaults to "utf-8". Can be set to a callable for automatic detection.

        Notes:
            This class can be used as a context manager, and it's recommended to use via
            ``async with``.
            However, unlike aiohttp, it is not required to use ``with``.

        .. code-block:: python

            from curl_cffi.requests import AsyncSession

            # recommended.
            async with AsyncSession() as s:
                r = await s.get("https://example.com")

            s = AsyncSession()  # it also works.
        """
        super().__init__(**kwargs)
        self._loop = loop
        self._acurl = async_curl
        self.max_clients = max_clients
        self.init_pool()

    @property
    def loop(self):
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        return self._loop

    @property
    def acurl(self):
        if self._acurl is None:
            self._acurl = AsyncCurl(loop=self.loop)
        return self._acurl

    def init_pool(self):
        self.pool = asyncio.LifoQueue(self.max_clients)
        while True:
            try:
                self.pool.put_nowait(None)
            except asyncio.QueueFull:
                break

    async def pop_curl(self):
        curl = await self.pool.get()
        if curl is None:
            curl = Curl(debug=self.debug)
        return curl

    def push_curl(self, curl):
        try:
            self.pool.put_nowait(curl)
        except asyncio.QueueFull:
            pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
        return None

    async def close(self):
        """Close the session."""
        await self.acurl.close()
        self._closed = True
        while True:
            try:
                curl = self.pool.get_nowait()
                if curl:
                    curl.close()
            except asyncio.QueueEmpty:
                break

    def release_curl(self, curl):
        curl.clean_after_perform()
        if not self._closed:
            self.acurl.remove_handle(curl)
            curl.reset()
            self.push_curl(curl)
        else:
            curl.close()

    @asynccontextmanager
    async def stream(self, *args, **kwargs):
        """Equivalent to ``async with request(..., stream=True) as r:``"""
        rsp = await self.request(*args, **kwargs, stream=True)
        try:
            yield rsp
        finally:
            await rsp.aclose()

    async def ws_connect(self, url, *args, **kwargs):
        self._check_session_closed()

        curl = await self.pop_curl()
        # curl.debug()
        self._set_curl_options(curl, "GET", url, *args, **kwargs)
        curl.setopt(CurlOpt.CONNECT_ONLY, 2)  # https://curl.se/docs/websocket.html
        await self.loop.run_in_executor(None, curl.perform)
        return WebSocket(self, curl)

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Union[Dict, List, Tuple]] = None,
        data: Optional[Union[Dict[str, str], List[Tuple], str, BytesIO, bytes]] = None,
        json: Optional[dict] = None,
        headers: Optional[HeaderTypes] = None,
        cookies: Optional[CookieTypes] = None,
        files: Optional[Dict] = None,
        auth: Optional[Tuple[str, str]] = None,
        timeout: Optional[Union[float, Tuple[float, float], object]] = not_set,
        allow_redirects: Optional[bool] = None,
        max_redirects: Optional[int] = None,
        proxies: Optional[ProxySpec] = None,
        proxy: Optional[str] = None,
        proxy_auth: Optional[Tuple[str, str]] = None,
        verify: Optional[bool] = None,
        referer: Optional[str] = None,
        accept_encoding: Optional[str] = "gzip, deflate, br",
        content_callback: Optional[Callable] = None,
        impersonate: Optional[Union[str, BrowserType]] = None,
        default_headers: Optional[bool] = None,
        default_encoding: Union[str, Callable[[bytes], str]] = "utf-8",
        http_version: Optional[CurlHttpVersion] = None,
        interface: Optional[str] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        stream: bool = False,
        max_recv_speed: int = 0,
        multipart: Optional[CurlMime] = None,
    ):
        """Send the request, see ``curl_cffi.requests.request`` for details on parameters."""
        self._check_session_closed()

        curl = await self.pop_curl()
        req, buffer, header_buffer, q, header_recved, quit_now = self._set_curl_options(
            curl=curl,
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
            http_version=http_version,
            interface=interface,
            stream=stream,
            max_recv_speed=max_recv_speed,
            multipart=multipart,
            cert=cert,
            queue_class=asyncio.Queue,
            event_class=asyncio.Event,
        )
        if stream:
            task = self.acurl.add_handle(curl)

            async def perform():
                try:
                    await task
                except CurlError as e:
                    rsp = self._parse_response(curl, buffer, header_buffer, default_encoding)
                    rsp.request = req
                    cast(asyncio.Queue, q).put_nowait(RequestsError(str(e), e.code, rsp))
                finally:
                    if not cast(asyncio.Event, header_recved).is_set():
                        cast(asyncio.Event, header_recved).set()
                    # None acts as a sentinel
                    await cast(asyncio.Queue, q).put(None)

            def cleanup(fut):
                self.release_curl(curl)

            stream_task = asyncio.create_task(perform())
            stream_task.add_done_callback(cleanup)

            await cast(asyncio.Event, header_recved).wait()

            # Unlike threads, coroutines does not use preemptive scheduling.
            # For asyncio, there is no need for a header_parsed event, the
            # _parse_response will execute in the foreground, no background tasks running.
            rsp = self._parse_response(curl, buffer, header_buffer, default_encoding)

            first_element = _peek_aio_queue(cast(asyncio.Queue, q))
            if isinstance(first_element, RequestsError):
                self.release_curl(curl)
                raise first_element

            rsp.request = req
            rsp.astream_task = stream_task
            rsp.quit_now = quit_now
            rsp.queue = q
            return rsp
        else:
            try:
                # curl.debug()
                task = self.acurl.add_handle(curl)
                await task
                # print(curl.getinfo(CurlInfo.CAINFO))
            except CurlError as e:
                rsp = self._parse_response(curl, buffer, header_buffer, default_encoding)
                rsp.request = req
                raise RequestsError(str(e), e.code, rsp) from e
            else:
                rsp = self._parse_response(curl, buffer, header_buffer, default_encoding)
                rsp.request = req
                return rsp
            finally:
                self.release_curl(curl)

    head = partialmethod(request, "HEAD")
    get = partialmethod(request, "GET")
    post = partialmethod(request, "POST")
    put = partialmethod(request, "PUT")
    patch = partialmethod(request, "PATCH")
    delete = partialmethod(request, "DELETE")
    options = partialmethod(request, "OPTIONS")
