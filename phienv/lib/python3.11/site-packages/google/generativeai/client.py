from __future__ import annotations

import os
import contextlib
import inspect
import dataclasses
import pathlib
from typing import Any, cast
from collections.abc import Sequence
import httplib2
from io import IOBase

import google.ai.generativelanguage as glm
import google.generativeai.protos as protos

from google.auth import credentials as ga_credentials
from google.auth import exceptions as ga_exceptions
from google import auth
from google.api_core import client_options as client_options_lib
from google.api_core import gapic_v1
from google.api_core import operations_v1

import googleapiclient.http
import googleapiclient.discovery

try:
    from google.generativeai import version

    __version__ = version.__version__
except ImportError:
    __version__ = "0.0.0"

USER_AGENT = "genai-py"

#### Caution! ####
#  - It would make sense for the discovery URL to respect the client_options.endpoint setting.
#    - That would make testing Files on the staging server possible.
#  - We tried fixing this once, but broke colab in the process because their endpoint didn't forward the discovery
#    requests. https://github.com/google-gemini/generative-ai-python/pull/333
#  - Kaggle would have a similar problem  (b/362278209).
#    - I think their proxy would forward the discovery traffic.
#    - But they don't need to intercept the files-service at all, and uploads of large files could overload them.
#      - Do the scotty uploads go to the same domain?
#    - If you do route the discovery call to kaggle, be sure to attach the default_metadata (they need it).
#  - One solution to all this would be if configure could take overrides per service.
#    - set client_options.endpoint, but use a different endpoint for file service? It's not clear how best to do that
#      through the file service.
##################
GENAI_API_DISCOVERY_URL = "https://generativelanguage.googleapis.com/$discovery/rest"


@contextlib.contextmanager
def patch_colab_gce_credentials():
    get_gce = auth._default._get_gce_credentials
    if "COLAB_RELEASE_TAG" in os.environ:
        auth._default._get_gce_credentials = lambda *args, **kwargs: (None, None)

    try:
        yield
    finally:
        auth._default._get_gce_credentials = get_gce


class FileServiceClient(glm.FileServiceClient):
    def __init__(self, *args, **kwargs):
        self._discovery_api = None
        super().__init__(*args, **kwargs)

    def _setup_discovery_api(self, metadata: dict | Sequence[tuple[str, str]] = ()):
        api_key = self._client_options.api_key
        if api_key is None:
            raise ValueError(
                "Invalid operation: Uploading to the File API requires an API key. Please provide a valid API key."
            )

        request = googleapiclient.http.HttpRequest(
            http=httplib2.Http(),
            postproc=lambda resp, content: (resp, content),
            uri=f"{GENAI_API_DISCOVERY_URL}?version=v1beta&key={api_key}",
            headers=dict(metadata),
        )
        response, content = request.execute()
        request.http.close()

        discovery_doc = content.decode("utf-8")
        self._discovery_api = googleapiclient.discovery.build_from_document(
            discovery_doc, developerKey=api_key
        )

    def create_file(
        self,
        path: str | pathlib.Path | os.PathLike | IOBase,
        *,
        mime_type: str | None = None,
        name: str | None = None,
        display_name: str | None = None,
        resumable: bool = True,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> protos.File:
        if self._discovery_api is None:
            self._setup_discovery_api(metadata)

        file = {}
        if name is not None:
            file["name"] = name
        if display_name is not None:
            file["displayName"] = display_name

        if isinstance(path, IOBase):
            media = googleapiclient.http.MediaIoBaseUpload(
                fd=path, mimetype=mime_type, resumable=resumable
            )
        else:
            media = googleapiclient.http.MediaFileUpload(
                filename=path, mimetype=mime_type, resumable=resumable
            )

        request = self._discovery_api.media().upload(body={"file": file}, media_body=media)
        for key, value in metadata:
            request.headers[key] = value
        result = request.execute()

        return self.get_file({"name": result["file"]["name"]})


class FileServiceAsyncClient(glm.FileServiceAsyncClient):
    async def create_file(self, *args, **kwargs):
        raise NotImplementedError(
            "The `create_file` method is currently not supported for the asynchronous client."
        )


@dataclasses.dataclass
class _ClientManager:
    client_config: dict[str, Any] = dataclasses.field(default_factory=dict)
    default_metadata: Sequence[tuple[str, str]] = ()
    clients: dict[str, Any] = dataclasses.field(default_factory=dict)

    def configure(
        self,
        *,
        api_key: str | None = None,
        credentials: ga_credentials.Credentials | dict | None = None,
        # The user can pass a string to choose `rest` or `grpc` or 'grpc_asyncio'.
        # See _transport_registry in the google.ai.generativelanguage package.
        # Since the transport classes align with the client classes it wouldn't make
        # sense to accept a `Transport` object here even though the client classes can.
        # We could accept a dict since all the `Transport` classes take the same args,
        # but that seems rare. Users that need it can just switch to the low level API.
        transport: str | None = None,
        client_options: client_options_lib.ClientOptions | dict[str, Any] | None = None,
        client_info: gapic_v1.client_info.ClientInfo | None = None,
        default_metadata: Sequence[tuple[str, str]] = (),
    ) -> None:
        """Initializes default client configurations using specified parameters or environment variables.

        If no API key has been provided (either directly, or on `client_options`) and the
        `GEMINI_API_KEY` environment variable is set, it will be used as the API key. If not,
        if the `GOOGLE_API_KEY` environement variable is set, it will be used as the API key.

        Note: Not all arguments are detailed below. Refer to the `*ServiceClient` classes in
        `google.ai.generativelanguage` for details on the other arguments.

        Args:
            transport: A string, one of: [`rest`, `grpc`, `grpc_asyncio`].
            api_key: The API-Key to use when creating the default clients (each service uses
                a separate client). This is a shortcut for `client_options={"api_key": api_key}`.
                If omitted, and the `GEMINI_API_KEY` or the `GOOGLE_API_KEY` environment variable
                are set, they will be used in this order of priority.
            default_metadata: Default (key, value) metadata pairs to send with every request.
                when using `transport="rest"` these are sent as HTTP headers.
        """
        if isinstance(client_options, dict):
            client_options = client_options_lib.from_dict(client_options)
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        client_options = cast(client_options_lib.ClientOptions, client_options)
        had_api_key_value = getattr(client_options, "api_key", None)

        if had_api_key_value:
            if api_key is not None:
                raise ValueError(
                    "Invalid configuration: Please set either `api_key` or `client_options['api_key']`, but not both."
                )
        else:
            if api_key is None:
                # If no key is provided explicitly, attempt to load one from the
                # environment.
                api_key = os.getenv("GEMINI_API_KEY")

            if api_key is None:
                # If the GEMINI_API_KEY doesn't exist, attempt to load the
                # GOOGLE_API_KEY from the environment.
                api_key = os.getenv("GOOGLE_API_KEY")

            client_options.api_key = api_key

        user_agent = f"{USER_AGENT}/{__version__}"
        if client_info:
            # Be respectful of any existing agent setting.
            if client_info.user_agent:
                client_info.user_agent += f" {user_agent}"
            else:
                client_info.user_agent = user_agent
        else:
            client_info = gapic_v1.client_info.ClientInfo(user_agent=user_agent)

        client_config = {
            "credentials": credentials,
            "transport": transport,
            "client_options": client_options,
            "client_info": client_info,
        }

        client_config = {key: value for key, value in client_config.items() if value is not None}

        self.client_config = client_config
        self.default_metadata = default_metadata

        self.clients = {}

    def make_client(self, name):
        if name == "file":
            cls = FileServiceClient
        elif name == "file_async":
            cls = FileServiceAsyncClient
        elif name.endswith("_async"):
            name = name.split("_")[0]
            cls = getattr(glm, name.title() + "ServiceAsyncClient")
        else:
            cls = getattr(glm, name.title() + "ServiceClient")

        # Attempt to configure using defaults.
        if not self.client_config:
            configure()

        try:
            with patch_colab_gce_credentials():
                client = cls(**self.client_config)
        except ga_exceptions.DefaultCredentialsError as e:
            e.args = (
                "\n  No API_KEY or ADC found. Please either:\n"
                "    - Set the `GOOGLE_API_KEY` environment variable.\n"
                "    - Manually pass the key with `genai.configure(api_key=my_api_key)`.\n"
                "    - Or set up Application Default Credentials, see https://ai.google.dev/gemini-api/docs/oauth for more information.",
            )
            raise e

        if not self.default_metadata:
            return client

        def keep(name, f):
            if name.startswith("_"):
                return False

            if not callable(f):
                return False

            if "metadata" not in inspect.signature(f).parameters.keys():
                return False

            return True

        def add_default_metadata_wrapper(f):
            def call(*args, metadata=(), **kwargs):
                metadata = list(metadata) + list(self.default_metadata)
                return f(*args, **kwargs, metadata=metadata)

            return call

        for name, value in inspect.getmembers(cls):
            if not keep(name, value):
                continue
            f = getattr(client, name)
            f = add_default_metadata_wrapper(f)
            setattr(client, name, f)

        return client

    def get_default_client(self, name):
        name = name.lower()
        if name == "operations":
            return self.get_default_operations_client()

        client = self.clients.get(name)
        if client is None:
            client = self.make_client(name)
            self.clients[name] = client
        return client

    def get_default_operations_client(self) -> operations_v1.OperationsClient:
        client = self.clients.get("operations", None)
        if client is None:
            model_client = self.get_default_client("Model")
            client = model_client._transport.operations_client
            self.clients["operations"] = client
        return client


def configure(
    *,
    api_key: str | None = None,
    credentials: ga_credentials.Credentials | dict | None = None,
    # The user can pass a string to choose `rest` or `grpc` or 'grpc_asyncio'.
    # Since the transport classes align with the client classes it wouldn't make
    # sense to accept a `Transport` object here even though the client classes can.
    # We could accept a dict since all the `Transport` classes take the same args,
    # but that seems rare. Users that need it can just switch to the low level API.
    transport: str | None = None,
    client_options: client_options_lib.ClientOptions | dict | None = None,
    client_info: gapic_v1.client_info.ClientInfo | None = None,
    default_metadata: Sequence[tuple[str, str]] = (),
):
    """Captures default client configuration.

    If no API key has been provided (either directly, or on `client_options`) and the
    `GOOGLE_API_KEY` environment variable is set, it will be used as the API key.

    Note: Not all arguments are detailed below. Refer to the `*ServiceClient` classes in
    `google.ai.generativelanguage` for details on the other arguments.

    Args:
        transport: A string, one of: [`rest`, `grpc`, `grpc_asyncio`].
        api_key: The API-Key to use when creating the default clients (each service uses
            a separate client). This is a shortcut for `client_options={"api_key": api_key}`.
            If omitted, and the `GOOGLE_API_KEY` environment variable is set, it will be
            used.
        default_metadata: Default (key, value) metadata pairs to send with every request.
            when using `transport="rest"` these are sent as HTTP headers.
    """
    return _client_manager.configure(
        api_key=api_key,
        credentials=credentials,
        transport=transport,
        client_options=client_options,
        client_info=client_info,
        default_metadata=default_metadata,
    )


_client_manager = _ClientManager()
_client_manager.configure()


def get_default_cache_client() -> glm.CacheServiceClient:
    return _client_manager.get_default_client("cache")


def get_default_file_client() -> glm.FilesServiceClient:
    return _client_manager.get_default_client("file")


def get_default_file_async_client() -> glm.FilesServiceAsyncClient:
    return _client_manager.get_default_client("file_async")


def get_default_generative_client() -> glm.GenerativeServiceClient:
    return _client_manager.get_default_client("generative")


def get_default_generative_async_client() -> glm.GenerativeServiceAsyncClient:
    return _client_manager.get_default_client("generative_async")


def get_default_operations_client() -> operations_v1.OperationsClient:
    return _client_manager.get_default_client("operations")


def get_default_model_client() -> glm.ModelServiceAsyncClient:
    return _client_manager.get_default_client("model")


def get_default_retriever_client() -> glm.RetrieverClient:
    return _client_manager.get_default_client("retriever")


def get_default_retriever_async_client() -> glm.RetrieverAsyncClient:
    return _client_manager.get_default_client("retriever_async")


def get_default_permission_client() -> glm.PermissionServiceClient:
    return _client_manager.get_default_client("permission")


def get_default_permission_async_client() -> glm.PermissionServiceAsyncClient:
    return _client_manager.get_default_client("permission_async")
