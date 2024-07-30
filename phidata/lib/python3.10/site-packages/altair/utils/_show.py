import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Union, Iterable, Optional


def open_html_in_browser(
    html: Union[str, bytes],
    using: Union[str, Iterable[str], None] = None,
    port: Optional[int] = None,
):
    """
    Display an html document in a web browser without creating a temp file.

    Instantiates a simple http server and uses the webbrowser module to
    open the server's URL

    Parameters
    ----------
    html: str
        HTML string to display
    using: str or iterable of str
        Name of the web browser to open (e.g. "chrome", "firefox", etc.).
        If an iterable, choose the first browser available on the system.
        If none, choose the system default browser.
    port: int
        Port to use. Defaults to a random port
    """
    # Encode html to bytes
    if isinstance(html, str):
        html_bytes = html.encode("utf8")
    else:
        html_bytes = html

    browser = None

    if using is None:
        browser = webbrowser.get(None)
    else:
        # normalize using to an iterable
        if isinstance(using, str):
            using = [using]

        for browser_key in using:
            try:
                browser = webbrowser.get(browser_key)
                if browser is not None:
                    break
            except webbrowser.Error:
                pass

        if browser is None:
            raise ValueError("Failed to locate a browser with name in " + str(using))

    class OneShotRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            bufferSize = 1024 * 1024
            for i in range(0, len(html_bytes), bufferSize):
                self.wfile.write(html_bytes[i : i + bufferSize])

        def log_message(self, format, *args):
            # Silence stderr logging
            pass

    # Use specified port if provided, otherwise choose a random port (port value of 0)
    server = HTTPServer(
        ("127.0.0.1", port if port is not None else 0), OneShotRequestHandler
    )
    browser.open("http://127.0.0.1:%s" % server.server_port)
    server.handle_request()
