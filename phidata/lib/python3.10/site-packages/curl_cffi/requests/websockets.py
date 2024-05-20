import asyncio
import struct
from enum import IntEnum
from typing import Callable, Optional, Tuple

from curl_cffi.const import CurlECode, CurlWsFlag
from curl_cffi.curl import CurlError

ON_MESSAGE_T = Callable[["WebSocket", bytes], None]
ON_ERROR_T = Callable[["WebSocket", CurlError], None]
ON_OPEN_T = Callable[["WebSocket"], None]
ON_CLOSE_T = Callable[["WebSocket", int, str], None]


class WsCloseCode(IntEnum):
    OK = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    UNKNOWN = 1005
    ABNORMAL_CLOSURE = 1006
    INVALID_DATA = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MANDATORY_EXTENSION = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    BAD_GATEWAY = 1014


class WebSocketError(CurlError):
    pass


class WebSocket:
    def __init__(
        self,
        session,
        curl,
        on_message: Optional[ON_MESSAGE_T] = None,
        on_error: Optional[ON_ERROR_T] = None,
        on_open: Optional[ON_OPEN_T] = None,
        on_close: Optional[ON_CLOSE_T] = None,
    ):
        self.session = session
        self.curl = curl
        self.on_message = on_message
        self.on_error = on_error
        self.on_open = on_open
        self.on_close = on_close
        self.keep_running = True
        self._loop = None

    def recv_fragment(self):
        return self.curl.ws_recv()

    def recv(self) -> Tuple[bytes, int]:
        """
        Receive a frame as bytes.

        libcurl split frames into fragments, so we have to collect all the chunks for
        a frame.
        """
        chunks = []
        flags = 0
        # TODO use select here
        while True:
            try:
                chunk, frame = self.curl.ws_recv()
                flags = frame.flags
                chunks.append(chunk)
                if frame.bytesleft == 0 and flags & CurlWsFlag.CONT == 0:
                    break
            except CurlError as e:
                if e.code == CurlECode.AGAIN:
                    pass
                else:
                    raise

        return b"".join(chunks), flags

    def send(self, payload: bytes, flags: CurlWsFlag = CurlWsFlag.BINARY):
        """Send a data frame"""
        return self.curl.ws_send(payload, flags)

    def run_forever(self):
        """
        libcurl automatically handles pings and pongs.

        ref: https://curl.se/libcurl/c/libcurl-ws.html
        """
        if self.on_open:
            self.on_open(self)

        # Keep reading the messages and invoke callbacks
        while self.keep_running:
            try:
                msg, flags = self.recv()
                if self.on_message:
                    self.on_message(self, msg)
                if flags & CurlWsFlag.CLOSE:
                    self.keep_running = False
                    # Unpack close code and reason
                    if len(msg) < 2:
                        code = WsCloseCode.UNKNOWN
                        reason = ""
                    else:
                        try:
                            code = struct.unpack_from("!H", msg)[0]
                            reason = msg[2:].decode()
                        except UnicodeDecodeError:
                            raise WebSocketError("Invalid close message", WsCloseCode.INVALID_DATA)
                        except Exception:
                            raise WebSocketError("Invalid close frame", WsCloseCode.PROTOCOL_ERROR)
                        else:
                            if code < 3000 and (code not in WsCloseCode or code == 1005):
                                raise WebSocketError(
                                    "Invalid close code", WsCloseCode.PROTOCOL_ERROR
                                )
                    if self.on_close:
                        self.on_close(self, code, reason)
            except WebSocketError as e:
                # Follow the spec to close the connection
                # TODO: Consider adding setting to autoclose connection on error-free close
                self.close(e.code)
                if self.on_error:
                    self.on_error(self, e)
            except CurlError as e:
                if self.on_error:
                    self.on_error(self, e)

    def close(self, code: int = WsCloseCode.OK, message: bytes = b""):
        msg = struct.pack("!H", code) + message
        # FIXME how to reset, or can a curl handle connect to two websockets?
        self.send(msg, CurlWsFlag.CLOSE)
        self.keep_running = False
        self.curl.close()

    @property
    def loop(self):
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        return self._loop

    async def arecv(self) -> Tuple[bytes, int]:
        return await self.loop.run_in_executor(None, self.recv)

    async def asend(self, payload: bytes, flags: CurlWsFlag = CurlWsFlag.BINARY):
        return await self.loop.run_in_executor(None, self.send, payload, flags)

    async def aclose(self, code: int = WsCloseCode.OK, message: bytes = b""):
        await self.loop.run_in_executor(None, self.close, code, message)
        self.curl.reset()
        self.session.push_curl(self.curl)
