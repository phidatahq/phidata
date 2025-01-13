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
from typing import Dict, Type

from .base import CacheServiceTransport
from .grpc import CacheServiceGrpcTransport
from .grpc_asyncio import CacheServiceGrpcAsyncIOTransport
from .rest import CacheServiceRestInterceptor, CacheServiceRestTransport

# Compile a registry of transports.
_transport_registry = OrderedDict()  # type: Dict[str, Type[CacheServiceTransport]]
_transport_registry["grpc"] = CacheServiceGrpcTransport
_transport_registry["grpc_asyncio"] = CacheServiceGrpcAsyncIOTransport
_transport_registry["rest"] = CacheServiceRestTransport

__all__ = (
    "CacheServiceTransport",
    "CacheServiceGrpcTransport",
    "CacheServiceGrpcAsyncIOTransport",
    "CacheServiceRestTransport",
    "CacheServiceRestInterceptor",
)
