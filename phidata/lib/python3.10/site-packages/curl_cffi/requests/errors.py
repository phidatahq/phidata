from .. import CurlError


class RequestsError(CurlError):
    """Base exception for curl_cffi.requests package"""

    def __init__(self, msg, code=0, response=None, *args, **kwargs):
        super().__init__(msg, code, *args, **kwargs)
        self.response = response


class CookieConflict(RequestsError):
    pass


class SessionClosed(RequestsError):
    pass
