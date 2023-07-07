import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from phiterm.conf.constants import PHI_AUTH_TOKEN_PATH
from phiterm.utils.log import logger


class CliAuthRequestHandler(BaseHTTPRequestHandler):
    """Request Handler to accept the CLI auth token after the web based auth flow.
    Reference: https://medium.com/@hasinthaindrajee/browser-sso-for-cli-applications-b0be743fa656
    Source: https://gist.github.com/mdonkers/63e115cc0c79b4f6b8b3a6b797e485c7
    TODO:
        * Fix the header and limit to only localhost or phidata.com
    """

    def _set_response(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST")
        self.end_headers()

    # def do_GET(self):
    #     logger.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
    #     self._set_response()
    #     self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_OPTIONS(self):
        # logger.info(
        #     "OPTIONS request,\nPath: %s\nHeaders:\n%s\n",
        #     str(self.path),
        #     str(self.headers),
        # )
        self._set_response()
        # self.wfile.write("OPTIONS request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])  # <--- Gets the size of data
        post_data = self.rfile.read(content_length)  # <--- Gets the data itself
        # logger.info(
        #     "POST request,\nPath: {}\nHeaders:\n{}\n\nBody:\n{}\n".format(
        #         str(self.path), str(self.headers), post_data.decode("utf-8")
        #     )
        # )
        # logger.info("Data: {}".format(post_data))
        # logger.info("type: {}".format(type(post_data)))
        PHI_AUTH_TOKEN_PATH.touch(exist_ok=True)
        PHI_AUTH_TOKEN_PATH.write_text(post_data.decode("utf-8"))
        # TODO: Add checks before shutting down the server
        self.server.running = False  # type: ignore
        self._set_response()

    def log_message(self, format, *args):
        pass


class CliAuthServer:
    """
    Source: https://stackoverflow.com/a/38196725/10953921
    """

    def __init__(self, port=9190):
        self._server = HTTPServer(("", port), CliAuthRequestHandler)
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._server.running = False  # type: ignore

    def run(self):
        self._server.running = True  # type: ignore
        while self._server.running:  # type: ignore
            self._server.handle_request()

    def start(self):
        self._thread.start()

    def shut_down(self):
        self._thread.close()  # type: ignore


def get_port_for_auth_server():
    # TODO: Check if port is available
    return 9190


def get_auth_token_from_web_flow(port) -> Optional[str]:
    """
    GET request: curl http://localhost:9190
    POST request: curl -d "foo=bar&bin=baz" http://localhost:9190
    """

    server = CliAuthServer(port)
    server.run()

    if PHI_AUTH_TOKEN_PATH.exists() and PHI_AUTH_TOKEN_PATH.is_file():
        auth_token_str = PHI_AUTH_TOKEN_PATH.read_text()
        auth_token_json = json.loads(auth_token_str)
        PHI_AUTH_TOKEN_PATH.unlink()
        return auth_token_json.get("AuthToken", None)
    return None
