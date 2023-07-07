# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import logging
import threading
from io import BytesIO

import awscrt.http
import botocore.awsrequest
import botocore.session
from awscrt.auth import AwsCredentials, AwsCredentialsProvider
from awscrt.io import (
    ClientBootstrap,
    ClientTlsContext,
    DefaultHostResolver,
    EventLoopGroup,
    TlsContextOptions,
)
from awscrt.s3 import S3Client, S3RequestTlsMode, S3RequestType
from botocore import UNSIGNED
from botocore.compat import urlsplit
from botocore.config import Config
from botocore.exceptions import NoCredentialsError

from s3transfer.constants import GB, MB
from s3transfer.exceptions import TransferNotDoneError
from s3transfer.futures import BaseTransferFuture, BaseTransferMeta
from s3transfer.utils import CallArgs, OSUtils, get_callbacks

logger = logging.getLogger(__name__)


class CRTCredentialProviderAdapter:
    def __init__(self, botocore_credential_provider):
        self._botocore_credential_provider = botocore_credential_provider
        self._loaded_credentials = None
        self._lock = threading.Lock()

    def __call__(self):
        credentials = self._get_credentials().get_frozen_credentials()
        return AwsCredentials(
            credentials.access_key, credentials.secret_key, credentials.token
        )

    def _get_credentials(self):
        with self._lock:
            if self._loaded_credentials is None:
                loaded_creds = (
                    self._botocore_credential_provider.load_credentials()
                )
                if loaded_creds is None:
                    raise NoCredentialsError()
                self._loaded_credentials = loaded_creds
            return self._loaded_credentials


def create_s3_crt_client(
    region,
    botocore_credential_provider=None,
    num_threads=None,
    target_throughput=5 * GB / 8,
    part_size=8 * MB,
    use_ssl=True,
    verify=None,
):
    """
    :type region: str
    :param region: The region used for signing

    :type botocore_credential_provider:
        Optional[botocore.credentials.CredentialResolver]
    :param botocore_credential_provider: Provide credentials for CRT
        to sign the request if not set, the request will not be signed

    :type num_threads: Optional[int]
    :param num_threads: Number of worker threads generated. Default
        is the number of processors in the machine.

    :type target_throughput: Optional[int]
    :param target_throughput: Throughput target in Bytes.
        Default is 0.625 GB/s (which translates to 5 Gb/s).

    :type part_size: Optional[int]
    :param part_size: Size, in Bytes, of parts that files will be downloaded
        or uploaded in.

    :type use_ssl: boolean
    :param use_ssl: Whether or not to use SSL.  By default, SSL is used.
        Note that not all services support non-ssl connections.

    :type verify: Optional[boolean/string]
    :param verify: Whether or not to verify SSL certificates.
        By default SSL certificates are verified.  You can provide the
        following values:

        * False - do not validate SSL certificates.  SSL will still be
            used (unless use_ssl is False), but SSL certificates
            will not be verified.
        * path/to/cert/bundle.pem - A filename of the CA cert bundle to
            use. Specify this argument if you want to use a custom CA cert
            bundle instead of the default one on your system.
    """

    event_loop_group = EventLoopGroup(num_threads)
    host_resolver = DefaultHostResolver(event_loop_group)
    bootstrap = ClientBootstrap(event_loop_group, host_resolver)
    provider = None
    tls_connection_options = None

    tls_mode = (
        S3RequestTlsMode.ENABLED if use_ssl else S3RequestTlsMode.DISABLED
    )
    if verify is not None:
        tls_ctx_options = TlsContextOptions()
        if verify:
            tls_ctx_options.override_default_trust_store_from_path(
                ca_filepath=verify
            )
        else:
            tls_ctx_options.verify_peer = False
        client_tls_option = ClientTlsContext(tls_ctx_options)
        tls_connection_options = client_tls_option.new_connection_options()
    if botocore_credential_provider:
        credentails_provider_adapter = CRTCredentialProviderAdapter(
            botocore_credential_provider
        )
        provider = AwsCredentialsProvider.new_delegate(
            credentails_provider_adapter
        )

    target_gbps = target_throughput * 8 / GB
    return S3Client(
        bootstrap=bootstrap,
        region=region,
        credential_provider=provider,
        part_size=part_size,
        tls_mode=tls_mode,
        tls_connection_options=tls_connection_options,
        throughput_target_gbps=target_gbps,
    )


class CRTTransferManager:
    def __init__(self, crt_s3_client, crt_request_serializer, osutil=None):
        """A transfer manager interface for Amazon S3 on CRT s3 client.

        :type crt_s3_client: awscrt.s3.S3Client
        :param crt_s3_client: The CRT s3 client, handling all the
            HTTP requests and functions under then hood

        :type crt_request_serializer: s3transfer.crt.BaseCRTRequestSerializer
        :param crt_request_serializer: Serializer, generates unsigned crt HTTP
            request.

        :type osutil: s3transfer.utils.OSUtils
        :param osutil: OSUtils object to use for os-related behavior when
            using with transfer manager.
        """
        if osutil is None:
            self._osutil = OSUtils()
        self._crt_s3_client = crt_s3_client
        self._s3_args_creator = S3ClientArgsCreator(
            crt_request_serializer, self._osutil
        )
        self._future_coordinators = []
        self._semaphore = threading.Semaphore(128)  # not configurable
        # A counter to create unique id's for each transfer submitted.
        self._id_counter = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, *args):
        cancel = False
        if exc_type:
            cancel = True
        self._shutdown(cancel)

    def download(
        self, bucket, key, fileobj, extra_args=None, subscribers=None
    ):
        if extra_args is None:
            extra_args = {}
        if subscribers is None:
            subscribers = {}
        callargs = CallArgs(
            bucket=bucket,
            key=key,
            fileobj=fileobj,
            extra_args=extra_args,
            subscribers=subscribers,
        )
        return self._submit_transfer("get_object", callargs)

    def upload(self, fileobj, bucket, key, extra_args=None, subscribers=None):
        if extra_args is None:
            extra_args = {}
        if subscribers is None:
            subscribers = {}
        callargs = CallArgs(
            bucket=bucket,
            key=key,
            fileobj=fileobj,
            extra_args=extra_args,
            subscribers=subscribers,
        )
        return self._submit_transfer("put_object", callargs)

    def delete(self, bucket, key, extra_args=None, subscribers=None):
        if extra_args is None:
            extra_args = {}
        if subscribers is None:
            subscribers = {}
        callargs = CallArgs(
            bucket=bucket,
            key=key,
            extra_args=extra_args,
            subscribers=subscribers,
        )
        return self._submit_transfer("delete_object", callargs)

    def shutdown(self, cancel=False):
        self._shutdown(cancel)

    def _cancel_transfers(self):
        for coordinator in self._future_coordinators:
            if not coordinator.done():
                coordinator.cancel()

    def _finish_transfers(self):
        for coordinator in self._future_coordinators:
            coordinator.result()

    def _wait_transfers_done(self):
        for coordinator in self._future_coordinators:
            coordinator.wait_until_on_done_callbacks_complete()

    def _shutdown(self, cancel=False):
        if cancel:
            self._cancel_transfers()
        try:
            self._finish_transfers()

        except KeyboardInterrupt:
            self._cancel_transfers()
        except Exception:
            pass
        finally:
            self._wait_transfers_done()

    def _release_semaphore(self, **kwargs):
        self._semaphore.release()

    def _submit_transfer(self, request_type, call_args):
        on_done_after_calls = [self._release_semaphore]
        coordinator = CRTTransferCoordinator(transfer_id=self._id_counter)
        components = {
            'meta': CRTTransferMeta(self._id_counter, call_args),
            'coordinator': coordinator,
        }
        future = CRTTransferFuture(**components)
        afterdone = AfterDoneHandler(coordinator)
        on_done_after_calls.append(afterdone)

        try:
            self._semaphore.acquire()
            on_queued = self._s3_args_creator.get_crt_callback(
                future, 'queued'
            )
            on_queued()
            crt_callargs = self._s3_args_creator.get_make_request_args(
                request_type,
                call_args,
                coordinator,
                future,
                on_done_after_calls,
            )
            crt_s3_request = self._crt_s3_client.make_request(**crt_callargs)
        except Exception as e:
            coordinator.set_exception(e, True)
            on_done = self._s3_args_creator.get_crt_callback(
                future, 'done', after_subscribers=on_done_after_calls
            )
            on_done(error=e)
        else:
            coordinator.set_s3_request(crt_s3_request)
        self._future_coordinators.append(coordinator)

        self._id_counter += 1
        return future


class CRTTransferMeta(BaseTransferMeta):
    """Holds metadata about the CRTTransferFuture"""

    def __init__(self, transfer_id=None, call_args=None):
        self._transfer_id = transfer_id
        self._call_args = call_args
        self._user_context = {}

    @property
    def call_args(self):
        return self._call_args

    @property
    def transfer_id(self):
        return self._transfer_id

    @property
    def user_context(self):
        return self._user_context


class CRTTransferFuture(BaseTransferFuture):
    def __init__(self, meta=None, coordinator=None):
        """The future associated to a submitted transfer request via CRT S3 client

        :type meta: s3transfer.crt.CRTTransferMeta
        :param meta: The metadata associated to the transfer future.

        :type coordinator: s3transfer.crt.CRTTransferCoordinator
        :param coordinator: The coordinator associated to the transfer future.
        """
        self._meta = meta
        if meta is None:
            self._meta = CRTTransferMeta()
        self._coordinator = coordinator

    @property
    def meta(self):
        return self._meta

    def done(self):
        return self._coordinator.done()

    def result(self, timeout=None):
        self._coordinator.result(timeout)

    def cancel(self):
        self._coordinator.cancel()

    def set_exception(self, exception):
        """Sets the exception on the future."""
        if not self.done():
            raise TransferNotDoneError(
                'set_exception can only be called once the transfer is '
                'complete.'
            )
        self._coordinator.set_exception(exception, override=True)


class BaseCRTRequestSerializer:
    def serialize_http_request(self, transfer_type, future):
        """Serialize CRT HTTP requests.

        :type transfer_type: string
        :param transfer_type: the type of transfer made,
            e.g 'put_object', 'get_object', 'delete_object'

        :type future: s3transfer.crt.CRTTransferFuture

        :rtype: awscrt.http.HttpRequest
        :returns: An unsigned HTTP request to be used for the CRT S3 client
        """
        raise NotImplementedError('serialize_http_request()')


class BotocoreCRTRequestSerializer(BaseCRTRequestSerializer):
    def __init__(self, session, client_kwargs=None):
        """Serialize CRT HTTP request using botocore logic
        It also takes into account configuration from both the session
        and any keyword arguments that could be passed to
        `Session.create_client()` when serializing the request.

        :type session: botocore.session.Session

        :type client_kwargs: Optional[Dict[str, str]])
        :param client_kwargs: The kwargs for the botocore
            s3 client initialization.
        """
        self._session = session
        if client_kwargs is None:
            client_kwargs = {}
        self._resolve_client_config(session, client_kwargs)
        self._client = session.create_client(**client_kwargs)
        self._client.meta.events.register(
            'request-created.s3.*', self._capture_http_request
        )
        self._client.meta.events.register(
            'after-call.s3.*', self._change_response_to_serialized_http_request
        )
        self._client.meta.events.register(
            'before-send.s3.*', self._make_fake_http_response
        )

    def _resolve_client_config(self, session, client_kwargs):
        user_provided_config = None
        if session.get_default_client_config():
            user_provided_config = session.get_default_client_config()
        if 'config' in client_kwargs:
            user_provided_config = client_kwargs['config']

        client_config = Config(signature_version=UNSIGNED)
        if user_provided_config:
            client_config = user_provided_config.merge(client_config)
        client_kwargs['config'] = client_config
        client_kwargs["service_name"] = "s3"

    def _crt_request_from_aws_request(self, aws_request):
        url_parts = urlsplit(aws_request.url)
        crt_path = url_parts.path
        if url_parts.query:
            crt_path = f'{crt_path}?{url_parts.query}'
        headers_list = []
        for name, value in aws_request.headers.items():
            if isinstance(value, str):
                headers_list.append((name, value))
            else:
                headers_list.append((name, str(value, 'utf-8')))

        crt_headers = awscrt.http.HttpHeaders(headers_list)
        # CRT requires body (if it exists) to be an I/O stream.
        crt_body_stream = None
        if aws_request.body:
            if hasattr(aws_request.body, 'seek'):
                crt_body_stream = aws_request.body
            else:
                crt_body_stream = BytesIO(aws_request.body)

        crt_request = awscrt.http.HttpRequest(
            method=aws_request.method,
            path=crt_path,
            headers=crt_headers,
            body_stream=crt_body_stream,
        )
        return crt_request

    def _convert_to_crt_http_request(self, botocore_http_request):
        # Logic that does CRTUtils.crt_request_from_aws_request
        crt_request = self._crt_request_from_aws_request(botocore_http_request)
        if crt_request.headers.get("host") is None:
            # If host is not set, set it for the request before using CRT s3
            url_parts = urlsplit(botocore_http_request.url)
            crt_request.headers.set("host", url_parts.netloc)
        if crt_request.headers.get('Content-MD5') is not None:
            crt_request.headers.remove("Content-MD5")
        return crt_request

    def _capture_http_request(self, request, **kwargs):
        request.context['http_request'] = request

    def _change_response_to_serialized_http_request(
        self, context, parsed, **kwargs
    ):
        request = context['http_request']
        parsed['HTTPRequest'] = request.prepare()

    def _make_fake_http_response(self, request, **kwargs):
        return botocore.awsrequest.AWSResponse(
            None,
            200,
            {},
            FakeRawResponse(b""),
        )

    def _get_botocore_http_request(self, client_method, call_args):
        return getattr(self._client, client_method)(
            Bucket=call_args.bucket, Key=call_args.key, **call_args.extra_args
        )['HTTPRequest']

    def serialize_http_request(self, transfer_type, future):
        botocore_http_request = self._get_botocore_http_request(
            transfer_type, future.meta.call_args
        )
        crt_request = self._convert_to_crt_http_request(botocore_http_request)
        return crt_request


class FakeRawResponse(BytesIO):
    def stream(self, amt=1024, decode_content=None):
        while True:
            chunk = self.read(amt)
            if not chunk:
                break
            yield chunk


class CRTTransferCoordinator:
    """A helper class for managing CRTTransferFuture"""

    def __init__(self, transfer_id=None, s3_request=None):
        self.transfer_id = transfer_id
        self._s3_request = s3_request
        self._lock = threading.Lock()
        self._exception = None
        self._crt_future = None
        self._done_event = threading.Event()

    @property
    def s3_request(self):
        return self._s3_request

    def set_done_callbacks_complete(self):
        self._done_event.set()

    def wait_until_on_done_callbacks_complete(self, timeout=None):
        self._done_event.wait(timeout)

    def set_exception(self, exception, override=False):
        with self._lock:
            if not self.done() or override:
                self._exception = exception

    def cancel(self):
        if self._s3_request:
            self._s3_request.cancel()

    def result(self, timeout=None):
        if self._exception:
            raise self._exception
        try:
            self._crt_future.result(timeout)
        except KeyboardInterrupt:
            self.cancel()
            raise
        finally:
            if self._s3_request:
                self._s3_request = None
            self._crt_future.result(timeout)

    def done(self):
        if self._crt_future is None:
            return False
        return self._crt_future.done()

    def set_s3_request(self, s3_request):
        self._s3_request = s3_request
        self._crt_future = self._s3_request.finished_future


class S3ClientArgsCreator:
    def __init__(self, crt_request_serializer, os_utils):
        self._request_serializer = crt_request_serializer
        self._os_utils = os_utils

    def get_make_request_args(
        self, request_type, call_args, coordinator, future, on_done_after_calls
    ):
        recv_filepath = None
        send_filepath = None
        s3_meta_request_type = getattr(
            S3RequestType, request_type.upper(), S3RequestType.DEFAULT
        )
        on_done_before_calls = []
        if s3_meta_request_type == S3RequestType.GET_OBJECT:
            final_filepath = call_args.fileobj
            recv_filepath = self._os_utils.get_temp_filename(final_filepath)
            file_ondone_call = RenameTempFileHandler(
                coordinator, final_filepath, recv_filepath, self._os_utils
            )
            on_done_before_calls.append(file_ondone_call)
        elif s3_meta_request_type == S3RequestType.PUT_OBJECT:
            send_filepath = call_args.fileobj
            data_len = self._os_utils.get_file_size(send_filepath)
            call_args.extra_args["ContentLength"] = data_len

        crt_request = self._request_serializer.serialize_http_request(
            request_type, future
        )

        return {
            'request': crt_request,
            'type': s3_meta_request_type,
            'recv_filepath': recv_filepath,
            'send_filepath': send_filepath,
            'on_done': self.get_crt_callback(
                future, 'done', on_done_before_calls, on_done_after_calls
            ),
            'on_progress': self.get_crt_callback(future, 'progress'),
        }

    def get_crt_callback(
        self,
        future,
        callback_type,
        before_subscribers=None,
        after_subscribers=None,
    ):
        def invoke_all_callbacks(*args, **kwargs):
            callbacks_list = []
            if before_subscribers is not None:
                callbacks_list += before_subscribers
            callbacks_list += get_callbacks(future, callback_type)
            if after_subscribers is not None:
                callbacks_list += after_subscribers
            for callback in callbacks_list:
                # The get_callbacks helper will set the first augment
                # by keyword, the other augments need to be set by keyword
                # as well
                if callback_type == "progress":
                    callback(bytes_transferred=args[0])
                else:
                    callback(*args, **kwargs)

        return invoke_all_callbacks


class RenameTempFileHandler:
    def __init__(self, coordinator, final_filename, temp_filename, osutil):
        self._coordinator = coordinator
        self._final_filename = final_filename
        self._temp_filename = temp_filename
        self._osutil = osutil

    def __call__(self, **kwargs):
        error = kwargs['error']
        if error:
            self._osutil.remove_file(self._temp_filename)
        else:
            try:
                self._osutil.rename_file(
                    self._temp_filename, self._final_filename
                )
            except Exception as e:
                self._osutil.remove_file(self._temp_filename)
                # the CRT future has done already at this point
                self._coordinator.set_exception(e)


class AfterDoneHandler:
    def __init__(self, coordinator):
        self._coordinator = coordinator

    def __call__(self, **kwargs):
        self._coordinator.set_done_callbacks_complete()
