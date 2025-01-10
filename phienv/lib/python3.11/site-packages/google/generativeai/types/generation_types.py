# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
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
from __future__ import annotations

import collections
import contextlib
from collections.abc import Iterable, AsyncIterable, Mapping
import dataclasses
import itertools
import json
import sys
import textwrap
from typing import Union, Any
from typing_extensions import TypedDict
import types

import google.protobuf.json_format
import google.api_core.exceptions

from google.generativeai import protos
from google.generativeai import string_utils
from google.generativeai.types import content_types
from google.generativeai.responder import _rename_schema_fields

__all__ = [
    "AsyncGenerateContentResponse",
    "BlockedPromptException",
    "StopCandidateException",
    "IncompleteIterationError",
    "BrokenResponseError",
    "GenerationConfigDict",
    "GenerationConfigType",
    "GenerationConfig",
    "GenerateContentResponse",
]

if sys.version_info < (3, 10):

    def aiter(obj):
        return obj.__aiter__()

    async def anext(obj, default=None):
        try:
            return await obj.__anext__()
        except StopAsyncIteration:
            if default is not None:
                return default
            else:
                raise


class BlockedPromptException(Exception):
    pass


class StopCandidateException(Exception):
    pass


class IncompleteIterationError(Exception):
    pass


class BrokenResponseError(Exception):
    pass


class GenerationConfigDict(TypedDict, total=False):
    # TODO(markdaoust): Python 3.11+ use `NotRequired`, ref: https://peps.python.org/pep-0655/
    candidate_count: int
    stop_sequences: Iterable[str]
    max_output_tokens: int
    temperature: float
    response_mime_type: str
    response_schema: protos.Schema | Mapping[str, Any]  # fmt: off


@dataclasses.dataclass
class GenerationConfig:
    """A simple dataclass used to configure the generation parameters of `GenerativeModel.generate_content`.

    Attributes:
        candidate_count:
            Number of generated responses to return.
        stop_sequences:
            The set of character sequences (up
            to 5) that will stop output generation. If
            specified, the API will stop at the first
            appearance of a stop sequence. The stop sequence
            will not be included as part of the response.
        max_output_tokens:
            The maximum number of tokens to include in a
            candidate.

            If unset, this will default to output_token_limit specified
            in the model's specification.
        temperature:
            Controls the randomness of the output. Note: The
            default value varies by model, see the `Model.temperature`
            attribute of the `Model` returned the `genai.get_model`
            function.

            Values can range from [0.0,1.0], inclusive. A value closer
            to 1.0 will produce responses that are more varied and
            creative, while a value closer to 0.0 will typically result
            in more straightforward responses from the model.
        top_p:
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Tokens are sorted based on their assigned probabilities so
            that only the most likely tokens are considered. Top-k
            sampling directly limits the maximum number of tokens to
            consider, while Nucleus sampling limits number of tokens
            based on the cumulative probability.

            Note: The default value varies by model, see the
            `Model.top_p` attribute of the `Model` returned the
            `genai.get_model` function.

        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            The model uses combined Top-k and nucleus sampling.

            Top-k sampling considers the set of `top_k` most probable
            tokens. Defaults to 40.

            Note: The default value varies by model, see the
            `Model.top_k` attribute of the `Model` returned the
            `genai.get_model` function.
        seed:
            Optional.  Seed used in decoding. If not set, the request uses a randomly generated seed.
        response_mime_type:
            Optional. Output response mimetype of the generated candidate text.

            Supported mimetype:
                `text/plain`: (default) Text output.
                `text/x-enum`: for use with a string-enum in `response_schema`
                `application/json`: JSON response in the candidates.

        response_schema:
            Optional. Specifies the format of the JSON requested if response_mime_type is
            `application/json`.
        presence_penalty:
            Optional.
        frequency_penalty:
            Optional.
        response_logprobs:
            Optional. If true, export the `logprobs` results in response.
        logprobs:
            Optional. Number of candidates of log probabilities to return at each step of decoding.
    """

    candidate_count: int | None = None
    stop_sequences: Iterable[str] | None = None
    max_output_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    seed: int | None = None
    response_mime_type: str | None = None
    response_schema: protos.Schema | Mapping[str, Any] | type | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    response_logprobs: bool | None = None
    logprobs: int | None = None


GenerationConfigType = Union[protos.GenerationConfig, GenerationConfigDict, GenerationConfig]


def _normalize_schema(generation_config):
    # Convert response_schema to protos.Schema for request
    response_schema = generation_config.get("response_schema", None)
    if response_schema is None:
        return

    if isinstance(response_schema, protos.Schema):
        return

    if isinstance(response_schema, type):
        response_schema = content_types._schema_for_class(response_schema)
    elif isinstance(response_schema, types.GenericAlias):
        if not str(response_schema).startswith("list["):
            raise ValueError(
                f"Invalid input: Could not understand the type of '{response_schema}'. "
                "Expected one of the following types: `int`, `float`, `str`, `bool`, `enum`, "
                "`typing_extensions.TypedDict`, `dataclass` or `list[...]`."
            )
        response_schema = content_types._schema_for_class(response_schema)

    response_schema = _rename_schema_fields(response_schema)
    generation_config["response_schema"] = protos.Schema(response_schema)


def to_generation_config_dict(generation_config: GenerationConfigType):
    if generation_config is None:
        return {}
    elif isinstance(generation_config, protos.GenerationConfig):
        schema = generation_config.response_schema
        generation_config = type(generation_config).to_dict(
            generation_config
        )  # pytype: disable=attribute-error
        generation_config["response_schema"] = schema
        return generation_config
    elif isinstance(generation_config, GenerationConfig):
        generation_config = dataclasses.asdict(generation_config)
        _normalize_schema(generation_config)
        return {key: value for key, value in generation_config.items() if value is not None}
    elif hasattr(generation_config, "keys"):
        generation_config = dict(generation_config)
        _normalize_schema(generation_config)
        return generation_config
    else:
        raise TypeError(
            "Invalid input type. Expected a `dict` or `GenerationConfig` for `generation_config`.\n"
            f"However, received an object of type: {type(generation_config)}.\n"
            f"Object Value: {generation_config}"
        )


def _join_citation_metadatas(
    citation_metadatas: Iterable[protos.CitationMetadata],
):
    citation_metadatas = list(citation_metadatas)
    return citation_metadatas[-1]


def _join_safety_ratings_lists(
    safety_ratings_lists: Iterable[list[protos.SafetyRating]],
):
    ratings = {}
    blocked = collections.defaultdict(list)

    for safety_ratings_list in safety_ratings_lists:
        for rating in safety_ratings_list:
            ratings[rating.category] = rating.probability
            blocked[rating.category].append(rating.blocked)

    blocked = {category: any(blocked) for category, blocked in blocked.items()}

    safety_list = []
    for (category, probability), blocked in zip(ratings.items(), blocked.values()):
        safety_list.append(
            protos.SafetyRating(category=category, probability=probability, blocked=blocked)
        )

    return safety_list


def _join_contents(contents: Iterable[protos.Content]):
    contents = tuple(contents)
    roles = [c.role for c in contents if c.role]
    if roles:
        role = roles[0]
    else:
        role = ""

    parts = []
    for content in contents:
        parts.extend(content.parts)

    merged_parts = []
    last = parts[0]
    for part in parts[1:]:
        if "text" in last and "text" in part:
            last = protos.Part(text=last.text + part.text)
            continue

        # Can we merge the new thing into last?
        # If not, put last in list of parts, and new thing becomes last
        if "executable_code" in last and "executable_code" in part:
            last = protos.Part(
                executable_code=_join_executable_code(last.executable_code, part.executable_code)
            )
            continue

        if "code_execution_result" in last and "code_execution_result" in part:
            last = protos.Part(
                code_execution_result=_join_code_execution_result(
                    last.code_execution_result, part.code_execution_result
                )
            )
            continue

        merged_parts.append(last)
        last = part

    merged_parts.append(last)

    return protos.Content(
        role=role,
        parts=merged_parts,
    )


def _join_executable_code(code_1, code_2):
    return protos.ExecutableCode(language=code_1.language, code=code_1.code + code_2.code)


def _join_code_execution_result(result_1, result_2):
    return protos.CodeExecutionResult(
        outcome=result_2.outcome, output=result_1.output + result_2.output
    )


def _join_candidates(candidates: Iterable[protos.Candidate]):
    """Joins stream chunks of a single candidate."""
    candidates = tuple(candidates)

    index = candidates[0].index  # These should all be the same.

    return protos.Candidate(
        index=index,
        content=_join_contents([c.content for c in candidates]),
        finish_reason=candidates[-1].finish_reason,
        safety_ratings=_join_safety_ratings_lists([c.safety_ratings for c in candidates]),
        citation_metadata=_join_citation_metadatas([c.citation_metadata for c in candidates]),
        token_count=candidates[-1].token_count,
    )


def _join_candidate_lists(candidate_lists: Iterable[list[protos.Candidate]]):
    """Joins stream chunks where each chunk is a list of candidate chunks."""
    # Assuming that is a candidate ends, it is no longer returned in the list of
    # candidates and that's why candidates have an index
    candidates = collections.defaultdict(list)
    for candidate_list in candidate_lists:
        for candidate in candidate_list:
            candidates[candidate.index].append(candidate)

    new_candidates = []
    for index, candidate_parts in sorted(candidates.items()):
        new_candidates.append(_join_candidates(candidate_parts))

    return new_candidates


def _join_prompt_feedbacks(
    prompt_feedbacks: Iterable[protos.GenerateContentResponse.PromptFeedback],
):
    # Always return the first prompt feedback.
    return next(iter(prompt_feedbacks))


def _join_chunks(chunks: Iterable[protos.GenerateContentResponse]):
    chunks = tuple(chunks)
    if "usage_metadata" in chunks[-1]:
        usage_metadata = chunks[-1].usage_metadata
    else:
        usage_metadata = None

    return protos.GenerateContentResponse(
        candidates=_join_candidate_lists(c.candidates for c in chunks),
        prompt_feedback=_join_prompt_feedbacks(c.prompt_feedback for c in chunks),
        usage_metadata=usage_metadata,
    )


_INCOMPLETE_ITERATION_MESSAGE = """\
Please let the response complete iteration before accessing the final accumulated
attributes (or call `response.resolve()`)"""


class BaseGenerateContentResponse:
    def __init__(
        self,
        done: bool,
        iterator: (
            None
            | Iterable[protos.GenerateContentResponse]
            | AsyncIterable[protos.GenerateContentResponse]
        ),
        result: protos.GenerateContentResponse,
        chunks: Iterable[protos.GenerateContentResponse] | None = None,
    ):
        self._done = done
        self._iterator = iterator
        self._result = result
        if chunks is None:
            self._chunks = [result]
        else:
            self._chunks = list(chunks)
        if result.prompt_feedback.block_reason:
            self._error = BlockedPromptException(result)
        else:
            self._error = None

    def to_dict(self):
        """Returns the result as a JSON-compatible dict.

        Note: This doesn't capture the iterator state when streaming, it only captures the accumulated
        `GenerateContentResponse` fields.

        >>> import json
        >>> response = model.generate_content('Hello?')
        >>> json.dumps(response.to_dict())
        """
        return type(self._result).to_dict(self._result)

    @property
    def candidates(self):
        """The list of candidate responses.

        Raises:
            IncompleteIterationError: With `stream=True` if iteration over the stream was not completed.
        """
        if not self._done:
            raise IncompleteIterationError(_INCOMPLETE_ITERATION_MESSAGE)
        return self._result.candidates

    @property
    def parts(self):
        """A quick accessor equivalent to `self.candidates[0].content.parts`

        Raises:
            ValueError: If the candidate list does not contain exactly one candidate.
        """
        candidates = self.candidates
        if not candidates:
            msg = (
                "Invalid operation: The `response.parts` quick accessor requires a single candidate, "
                "but but `response.candidates` is empty."
            )
            if self.prompt_feedback:
                raise ValueError(
                    msg + "\nThis appears to be caused by a blocked prompt, "
                    f"see `response.prompt_feedback`: {self.prompt_feedback}"
                )
            else:
                raise ValueError(msg)

        if len(candidates) > 1:
            raise ValueError(
                "Invalid operation: The `response.parts` quick accessor retrieves the parts for a single candidate. "
                "This response contains multiple candidates, please use `result.candidates[index].text`."
            )
        parts = candidates[0].content.parts
        return parts

    @property
    def text(self):
        """A quick accessor equivalent to `self.candidates[0].content.parts[0].text`

        Raises:
            ValueError: If the candidate list or parts list does not contain exactly one entry.
        """
        parts = self.parts
        if not parts:
            candidate = self.candidates[0]

            fr = candidate.finish_reason
            FinishReason = protos.Candidate.FinishReason

            msg = (
                "Invalid operation: The `response.text` quick accessor requires the response to contain a valid "
                "`Part`, but none were returned. The candidate's "
                f"[finish_reason](https://ai.google.dev/api/generate-content#finishreason) is {fr}."
            )

            if fr is FinishReason.FINISH_REASON_UNSPECIFIED:
                raise ValueError(msg)
            elif fr is FinishReason.STOP:
                raise ValueError(msg)
            elif fr is FinishReason.MAX_TOKENS:
                raise ValueError(msg)
            elif fr is FinishReason.SAFETY:
                raise ValueError(
                    msg + f" The candidate's safety_ratings are: {candidate.safety_ratings}.",
                    candidate.safety_ratings,
                )
            elif fr is FinishReason.RECITATION:
                raise ValueError(
                    msg + " Meaning that the model was reciting from copyrighted material."
                )
            elif fr is FinishReason.LANGUAGE:
                raise ValueError(msg + " Meaning the response was using an unsupported language.")
            elif fr is FinishReason.OTHER:
                raise ValueError(msg)
            elif fr is FinishReason.BLOCKLIST:
                raise ValueError(msg)
            elif fr is FinishReason.PROHIBITED_CONTENT:
                raise ValueError(msg)
            elif fr is FinishReason.SPII:
                raise ValueError(msg + " SPII - Sensitive Personally Identifiable Information.")
            elif fr is FinishReason.MALFORMED_FUNCTION_CALL:
                raise ValueError(
                    msg + " Meaning that model generated a `FunctionCall` that was invalid. "
                    "Setting the "
                    "[Function calling mode](https://ai.google.dev/gemini-api/docs/function-calling#function_calling_mode) "
                    "to `ANY` can fix this because it enables constrained decoding."
                )
            else:
                raise ValueError(msg)

        texts = []
        for part in parts:
            if "text" in part:
                texts.append(part.text)
                continue
            if "executable_code" in part:
                language = part.executable_code.language.name.lower()
                if language == "language_unspecified":
                    language = ""
                else:
                    language = f" {language}"
                texts.extend([f"```{language}", part.executable_code.code.lstrip("\n"), "```"])
                continue
            if "code_execution_result" in part:
                outcome_result = part.code_execution_result.outcome.name.lower().replace(
                    "outcome_", ""
                )
                if outcome_result == "ok" or outcome_result == "unspecified":
                    outcome_result = ""
                else:
                    outcome_result = f" {outcome_result}"
                texts.extend([f"```{outcome_result}", part.code_execution_result.output, "```"])
                continue

            part_type = protos.Part.pb(part).whichOneof("data")
            raise ValueError(f"Could not convert `part.{part_type}` to text.")

        return "\n".join(texts)

    @property
    def prompt_feedback(self):
        return self._result.prompt_feedback

    @property
    def usage_metadata(self):
        return self._result.usage_metadata

    def __str__(self) -> str:
        if self._done:
            _iterator = "None"
        else:
            _iterator = f"<{self._iterator.__class__.__name__}>"

        as_dict = type(self._result).to_dict(
            self._result, use_integers_for_enums=False, including_default_value_fields=False
        )
        json_str = json.dumps(as_dict, indent=2)

        _result = f"protos.GenerateContentResponse({json_str})"
        _result = _result.replace("\n", "\n                    ")

        if self._error:

            _error = f",\nerror={repr(self._error)}"
        else:
            _error = ""

        return (
            textwrap.dedent(
                f"""\
                response:
                {type(self).__name__}(
                    done={self._done},
                    iterator={_iterator},
                    result={_result},
                )"""
            )
            + _error
        )

    __repr__ = __str__


@contextlib.contextmanager
def rewrite_stream_error():
    try:
        yield
    except (google.protobuf.json_format.ParseError, AttributeError) as e:
        raise google.api_core.exceptions.BadRequest(
            "Unknown error trying to retrieve streaming response. "
            "Please retry with `stream=False` for more details."
        )


GENERATE_CONTENT_RESPONSE_DOC = """Instances of this class manage the response of the `generate_content` method.

    These are returned by `GenerativeModel.generate_content` and `ChatSession.send_message`.
    This object is based on the low level `protos.GenerateContentResponse` class which just has `prompt_feedback`
    and `candidates` attributes. This class adds several quick accessors for common use cases.

    The same object type is returned for both `stream=True/False`.

    ### Streaming

    When you pass `stream=True` to `GenerativeModel.generate_content` or `ChatSession.send_message`,
    iterate over this object to receive chunks of the response:

    ```
    response = model.generate_content(..., stream=True):
    for chunk in response:
      print(chunk.text)
    ```

    `GenerateContentResponse.prompt_feedback` is available immediately but
    `GenerateContentResponse.candidates`, and all the attributes derived from them (`.text`, `.parts`),
    are only available after the iteration is complete.
    """

ASYNC_GENERATE_CONTENT_RESPONSE_DOC = (
    """This is the async version of `genai.GenerateContentResponse`."""
)


@string_utils.set_doc(GENERATE_CONTENT_RESPONSE_DOC)
class GenerateContentResponse(BaseGenerateContentResponse):
    @classmethod
    def from_iterator(cls, iterator: Iterable[protos.GenerateContentResponse]):
        iterator = iter(iterator)
        with rewrite_stream_error():
            response = next(iterator)

        return cls(
            done=False,
            iterator=iterator,
            result=response,
        )

    @classmethod
    def from_response(cls, response: protos.GenerateContentResponse):
        return cls(
            done=True,
            iterator=None,
            result=response,
        )

    def __iter__(self):
        # This is not thread safe.
        if self._done:
            for chunk in self._chunks:
                yield GenerateContentResponse.from_response(chunk)
            return

        # Always have the next chunk available.
        if len(self._chunks) == 0:
            self._chunks.append(next(self._iterator))

        for n in itertools.count():
            if self._error:
                raise self._error

            if n >= len(self._chunks) - 1:
                # Look ahead for a new item, so that you know the stream is done
                # when you yield the last item.
                if self._done:
                    return

                try:
                    item = next(self._iterator)
                except StopIteration:
                    self._done = True
                except Exception as e:
                    self._error = e
                    self._done = True
                else:
                    self._chunks.append(item)
                    self._result = _join_chunks([self._result, item])

            item = self._chunks[n]

            item = GenerateContentResponse.from_response(item)
            yield item

    def resolve(self):
        if self._done:
            return

        for _ in self:
            pass


@string_utils.set_doc(ASYNC_GENERATE_CONTENT_RESPONSE_DOC)
class AsyncGenerateContentResponse(BaseGenerateContentResponse):
    @classmethod
    async def from_aiterator(cls, iterator: AsyncIterable[protos.GenerateContentResponse]):
        iterator = aiter(iterator)  # type: ignore
        with rewrite_stream_error():
            response = await anext(iterator)  # type: ignore

        return cls(
            done=False,
            iterator=iterator,
            result=response,
        )

    @classmethod
    def from_response(cls, response: protos.GenerateContentResponse):
        return cls(
            done=True,
            iterator=None,
            result=response,
        )

    async def __aiter__(self):
        # This is not thread safe.
        if self._done:
            for chunk in self._chunks:
                yield GenerateContentResponse.from_response(chunk)
            return

        # Always have the next chunk available.
        if len(self._chunks) == 0:
            self._chunks.append(await anext(self._iterator))  # type: ignore

        for n in itertools.count():
            if self._error:
                raise self._error

            if n >= len(self._chunks) - 1:
                # Look ahead for a new item, so that you know the stream is done
                # when you yield the last item.
                if self._done:
                    return

                try:
                    item = await anext(self._iterator)  # type: ignore
                except StopAsyncIteration:
                    self._done = True
                except Exception as e:
                    self._error = e
                    self._done = True
                else:
                    self._chunks.append(item)
                    self._result = _join_chunks([self._result, item])

            item = self._chunks[n]

            item = GenerateContentResponse.from_response(item)
            yield item

    async def resolve(self):
        if self._done:
            return

        async for _ in self:
            pass
