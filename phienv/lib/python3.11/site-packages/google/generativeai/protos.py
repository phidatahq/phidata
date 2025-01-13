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
"""
This module provides low level access to the ProtoBuffer "Message" classes used by the API.

**For typical usage of this SDK you do not need to use any of these classes.**

ProtoBufers are Google API's serilization format. They are strongly typed and efficient.

The `genai` SDK tries to be permissive about what objects it will accept from a user, but in the end
the SDK always converts input to an appropriate Proto Message object to send as the request. Each API request
has a `*Request` and `*Response` Message defined here.

If you have any uncertainty about what the API may accept or return, these classes provide the
complete/unambiguous answer. They come from the `google-ai-generativelanguage` package which is
generated from a snapshot of the API definition.

>>> from google.generativeai import protos
>>> import inspect
>>> print(inspect.getsource(protos.Part))

Proto classes can have "oneof" fields. Use `in` to check which `oneof` field is set.

>>> p = protos.Part(text='hello')
>>> 'text' in p
True
>>> p.inline_data = {'mime_type':'image/png', 'data': b'PNG'}
>>> type(p.inline_data) is protos.Blob
True
>>> 'inline_data' in p
True
>>> 'text' in p
False

Instances of all Message classes can be converted into JSON compatible dictionaries with the following construct
(Bytes are base64 encoded):

>>> p_dict = type(p).to_dict(p)
>>> p_dict
{'inline_data': {'mime_type': 'image/png', 'data': 'UE5H'}}

A compatible dict can be converted to an instance of a Message class by passing it as the first argument to the
constructor:

>>> p = protos.Part(p_dict)
inline_data {
  mime_type: "image/png"
  data: "PNG"
}

Note when converting that `to_dict` accepts additional arguments:

- `use_integers_for_enums:bool = True`, Set it to `False` to replace enum int values with their string
   names in the output
- ` including_default_value_fields:bool = True`, Set it to `False` to reduce the verbosity of the output.

Additional arguments are described in the docstring:

>>> help(proto.Part.to_dict)
"""

from google.ai.generativelanguage_v1beta.types import *
from google.ai.generativelanguage_v1beta.types import __all__
