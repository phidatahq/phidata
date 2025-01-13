# -*- coding: utf-8 -*-
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from collections import OrderedDict
import re
from typing import (
    Callable,
    Dict,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry_async as retries
from google.api_core.client_options import ClientOptions
from google.auth import credentials as ga_credentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import duration_pb2  # type: ignore
from google.protobuf import field_mask_pb2  # type: ignore
from google.protobuf import timestamp_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.services.cache_service import pagers
from google.ai.generativelanguage_v1beta.types import (
    cached_content as gag_cached_content,
)
from google.ai.generativelanguage_v1beta.types import cache_service
from google.ai.generativelanguage_v1beta.types import cached_content
from google.ai.generativelanguage_v1beta.types import content

from .client import CacheServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, CacheServiceTransport
from .transports.grpc_asyncio import CacheServiceGrpcAsyncIOTransport


class CacheServiceAsyncClient:
    """API for managing cache of content (CachedContent resources)
    that can be used in GenerativeService requests. This way
    generate content requests can benefit from preprocessing work
    being done earlier, possibly lowering their computational cost.
    It is intended to be used with large contexts.
    """

    _client: CacheServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = CacheServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = CacheServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = CacheServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = CacheServiceClient._DEFAULT_UNIVERSE

    cached_content_path = staticmethod(CacheServiceClient.cached_content_path)
    parse_cached_content_path = staticmethod(
        CacheServiceClient.parse_cached_content_path
    )
    model_path = staticmethod(CacheServiceClient.model_path)
    parse_model_path = staticmethod(CacheServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        CacheServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        CacheServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(CacheServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(CacheServiceClient.parse_common_folder_path)
    common_organization_path = staticmethod(CacheServiceClient.common_organization_path)
    parse_common_organization_path = staticmethod(
        CacheServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(CacheServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        CacheServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(CacheServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        CacheServiceClient.parse_common_location_path
    )

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            CacheServiceAsyncClient: The constructed client.
        """
        return CacheServiceClient.from_service_account_info.__func__(CacheServiceAsyncClient, info, *args, **kwargs)  # type: ignore

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            file.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            CacheServiceAsyncClient: The constructed client.
        """
        return CacheServiceClient.from_service_account_file.__func__(CacheServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

    from_service_account_json = from_service_account_file

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[ClientOptions] = None
    ):
        """Return the API endpoint and client cert source for mutual TLS.

        The client cert source is determined in the following order:
        (1) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is not "true", the
        client cert source is None.
        (2) if `client_options.client_cert_source` is provided, use the provided one; if the
        default client cert source exists, use the default one; otherwise the client cert
        source is None.

        The API endpoint is determined in the following order:
        (1) if `client_options.api_endpoint` if provided, use the provided one.
        (2) if `GOOGLE_API_USE_CLIENT_CERTIFICATE` environment variable is "always", use the
        default mTLS endpoint; if the environment variable is "never", use the default API
        endpoint; otherwise if client cert source exists, use the default mTLS endpoint, otherwise
        use the default API endpoint.

        More details can be found at https://google.aip.dev/auth/4114.

        Args:
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. Only the `api_endpoint` and `client_cert_source` properties may be used
                in this method.

        Returns:
            Tuple[str, Callable[[], Tuple[bytes, bytes]]]: returns the API endpoint and the
                client cert source to use.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If any errors happen.
        """
        return CacheServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> CacheServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            CacheServiceTransport: The transport used by the client instance.
        """
        return self._client.transport

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._client._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used
                by the client instance.
        """
        return self._client._universe_domain

    get_transport_class = CacheServiceClient.get_transport_class

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, CacheServiceTransport, Callable[..., CacheServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the cache service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,CacheServiceTransport,Callable[..., CacheServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the CacheServiceTransport constructor.
                If set to None, a transport is chosen automatically.
            client_options (Optional[Union[google.api_core.client_options.ClientOptions, dict]]):
                Custom options for the client.

                1. The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client when ``transport`` is
                not explicitly provided. Only if this property is not set and
                ``transport`` was not explicitly provided, the endpoint is
                determined by the GOOGLE_API_USE_MTLS_ENDPOINT environment
                variable, which have one of the following values:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto-switch to the
                default mTLS endpoint if client certificate is present; this is
                the default value).

                2. If the GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide a client certificate for mTLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.

                3. The ``universe_domain`` property can be used to override the
                default "googleapis.com" universe. Note that ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client = CacheServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def list_cached_contents(
        self,
        request: Optional[Union[cache_service.ListCachedContentsRequest, dict]] = None,
        *,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> pagers.ListCachedContentsAsyncPager:
        r"""Lists CachedContents.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_list_cached_contents():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.ListCachedContentsRequest(
                )

                # Make the request
                page_result = client.list_cached_contents(request=request)

                # Handle the response
                async for response in page_result:
                    print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.ListCachedContentsRequest, dict]]):
                The request object. Request to list CachedContents.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.services.cache_service.pagers.ListCachedContentsAsyncPager:
                Response with CachedContents list.

                Iterating over this object will yield
                results and resolve additional pages
                automatically.

        """
        # Create or coerce a protobuf request object.
        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, cache_service.ListCachedContentsRequest):
            request = cache_service.ListCachedContentsRequest(request)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.list_cached_contents
        ]

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # This method is paged; wrap the response in a pager, which provides
        # an `__aiter__` convenience method.
        response = pagers.ListCachedContentsAsyncPager(
            method=rpc,
            request=request,
            response=response,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def create_cached_content(
        self,
        request: Optional[Union[cache_service.CreateCachedContentRequest, dict]] = None,
        *,
        cached_content: Optional[gag_cached_content.CachedContent] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_cached_content.CachedContent:
        r"""Creates CachedContent resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_create_cached_content():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.CreateCachedContentRequest(
                )

                # Make the request
                response = await client.create_cached_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.CreateCachedContentRequest, dict]]):
                The request object. Request to create CachedContent.
            cached_content (:class:`google.ai.generativelanguage_v1beta.types.CachedContent`):
                Required. The cached content to
                create.

                This corresponds to the ``cached_content`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CachedContent:
                Content that has been preprocessed
                and can be used in subsequent request to
                GenerativeService.

                Cached content can be only used with
                model it was created for.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([cached_content])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, cache_service.CreateCachedContentRequest):
            request = cache_service.CreateCachedContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if cached_content is not None:
            request.cached_content = cached_content

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.create_cached_content
        ]

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def get_cached_content(
        self,
        request: Optional[Union[cache_service.GetCachedContentRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> cached_content.CachedContent:
        r"""Reads CachedContent resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_get_cached_content():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.GetCachedContentRequest(
                    name="name_value",
                )

                # Make the request
                response = await client.get_cached_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.GetCachedContentRequest, dict]]):
                The request object. Request to read CachedContent.
            name (:class:`str`):
                Required. The resource name referring to the content
                cache entry. Format: ``cachedContents/{id}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CachedContent:
                Content that has been preprocessed
                and can be used in subsequent request to
                GenerativeService.

                Cached content can be only used with
                model it was created for.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, cache_service.GetCachedContentRequest):
            request = cache_service.GetCachedContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.get_cached_content
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def update_cached_content(
        self,
        request: Optional[Union[cache_service.UpdateCachedContentRequest, dict]] = None,
        *,
        cached_content: Optional[gag_cached_content.CachedContent] = None,
        update_mask: Optional[field_mask_pb2.FieldMask] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> gag_cached_content.CachedContent:
        r"""Updates CachedContent resource (only expiration is
        updatable).

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_update_cached_content():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.UpdateCachedContentRequest(
                )

                # Make the request
                response = await client.update_cached_content(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.UpdateCachedContentRequest, dict]]):
                The request object. Request to update CachedContent.
            cached_content (:class:`google.ai.generativelanguage_v1beta.types.CachedContent`):
                Required. The content cache entry to
                update

                This corresponds to the ``cached_content`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            update_mask (:class:`google.protobuf.field_mask_pb2.FieldMask`):
                The list of fields to update.
                This corresponds to the ``update_mask`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta.types.CachedContent:
                Content that has been preprocessed
                and can be used in subsequent request to
                GenerativeService.

                Cached content can be only used with
                model it was created for.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([cached_content, update_mask])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, cache_service.UpdateCachedContentRequest):
            request = cache_service.UpdateCachedContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if cached_content is not None:
            request.cached_content = cached_content
        if update_mask is not None:
            request.update_mask = update_mask

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.update_cached_content
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata(
                (("cached_content.name", request.cached_content.name),)
            ),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def delete_cached_content(
        self,
        request: Optional[Union[cache_service.DeleteCachedContentRequest, dict]] = None,
        *,
        name: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> None:
        r"""Deletes CachedContent resource.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta

            async def sample_delete_cached_content():
                # Create a client
                client = generativelanguage_v1beta.CacheServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta.DeleteCachedContentRequest(
                    name="name_value",
                )

                # Make the request
                await client.delete_cached_content(request=request)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta.types.DeleteCachedContentRequest, dict]]):
                The request object. Request to delete CachedContent.
            name (:class:`str`):
                Required. The resource name referring to the content
                cache entry Format: ``cachedContents/{id}``

                This corresponds to the ``name`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([name])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, cache_service.DeleteCachedContentRequest):
            request = cache_service.DeleteCachedContentRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if name is not None:
            request.name = name

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.delete_cached_content
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("name", request.name),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    async def __aenter__(self) -> "CacheServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("CacheServiceAsyncClient",)
