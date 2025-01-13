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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

from google.protobuf import struct_pb2  # type: ignore
import proto  # type: ignore

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "PredictRequest",
        "PredictResponse",
    },
)


class PredictRequest(proto.Message):
    r"""Request message for
    [PredictionService.Predict][google.ai.generativelanguage.v1beta.PredictionService.Predict].

    Attributes:
        model (str):
            Required. The name of the model for prediction. Format:
            ``name=models/{model}``.
        instances (MutableSequence[google.protobuf.struct_pb2.Value]):
            Required. The instances that are the input to
            the prediction call.
        parameters (google.protobuf.struct_pb2.Value):
            Optional. The parameters that govern the
            prediction call.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    instances: MutableSequence[struct_pb2.Value] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=struct_pb2.Value,
    )
    parameters: struct_pb2.Value = proto.Field(
        proto.MESSAGE,
        number=3,
        message=struct_pb2.Value,
    )


class PredictResponse(proto.Message):
    r"""Response message for [PredictionService.Predict].

    Attributes:
        predictions (MutableSequence[google.protobuf.struct_pb2.Value]):
            The outputs of the prediction call.
    """

    predictions: MutableSequence[struct_pb2.Value] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message=struct_pb2.Value,
    )


__all__ = tuple(sorted(__protobuf__.manifest))
