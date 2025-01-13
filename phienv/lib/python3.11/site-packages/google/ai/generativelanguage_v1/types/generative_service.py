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

import proto  # type: ignore

from google.ai.generativelanguage_v1.types import citation
from google.ai.generativelanguage_v1.types import content as gag_content
from google.ai.generativelanguage_v1.types import safety

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1",
    manifest={
        "TaskType",
        "GenerateContentRequest",
        "GenerationConfig",
        "GenerateContentResponse",
        "Candidate",
        "LogprobsResult",
        "EmbedContentRequest",
        "ContentEmbedding",
        "EmbedContentResponse",
        "BatchEmbedContentsRequest",
        "BatchEmbedContentsResponse",
        "CountTokensRequest",
        "CountTokensResponse",
    },
)


class TaskType(proto.Enum):
    r"""Type of task for which the embedding will be used.

    Values:
        TASK_TYPE_UNSPECIFIED (0):
            Unset value, which will default to one of the
            other enum values.
        RETRIEVAL_QUERY (1):
            Specifies the given text is a query in a
            search/retrieval setting.
        RETRIEVAL_DOCUMENT (2):
            Specifies the given text is a document from
            the corpus being searched.
        SEMANTIC_SIMILARITY (3):
            Specifies the given text will be used for
            STS.
        CLASSIFICATION (4):
            Specifies that the given text will be
            classified.
        CLUSTERING (5):
            Specifies that the embeddings will be used
            for clustering.
        QUESTION_ANSWERING (6):
            Specifies that the given text will be used
            for question answering.
        FACT_VERIFICATION (7):
            Specifies that the given text will be used
            for fact verification.
    """
    TASK_TYPE_UNSPECIFIED = 0
    RETRIEVAL_QUERY = 1
    RETRIEVAL_DOCUMENT = 2
    SEMANTIC_SIMILARITY = 3
    CLASSIFICATION = 4
    CLUSTERING = 5
    QUESTION_ANSWERING = 6
    FACT_VERIFICATION = 7


class GenerateContentRequest(proto.Message):
    r"""Request to generate a completion from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The name of the ``Model`` to use for generating
            the completion.

            Format: ``name=models/{model}``.
        contents (MutableSequence[google.ai.generativelanguage_v1.types.Content]):
            Required. The content of the current conversation with the
            model.

            For single-turn queries, this is a single instance. For
            multi-turn queries like
            `chat <https://ai.google.dev/gemini-api/docs/text-generation#chat>`__,
            this is a repeated field that contains the conversation
            history and the latest request.
        safety_settings (MutableSequence[google.ai.generativelanguage_v1.types.SafetySetting]):
            Optional. A list of unique ``SafetySetting`` instances for
            blocking unsafe content.

            This will be enforced on the
            ``GenerateContentRequest.contents`` and
            ``GenerateContentResponse.candidates``. There should not be
            more than one setting for each ``SafetyCategory`` type. The
            API will block any contents and responses that fail to meet
            the thresholds set by these settings. This list overrides
            the default settings for each ``SafetyCategory`` specified
            in the safety_settings. If there is no ``SafetySetting`` for
            a given ``SafetyCategory`` provided in the list, the API
            will use the default safety setting for that category. Harm
            categories HARM_CATEGORY_HATE_SPEECH,
            HARM_CATEGORY_SEXUALLY_EXPLICIT,
            HARM_CATEGORY_DANGEROUS_CONTENT, HARM_CATEGORY_HARASSMENT
            are supported. Refer to the
            `guide <https://ai.google.dev/gemini-api/docs/safety-settings>`__
            for detailed information on available safety settings. Also
            refer to the `Safety
            guidance <https://ai.google.dev/gemini-api/docs/safety-guidance>`__
            to learn how to incorporate safety considerations in your AI
            applications.
        generation_config (google.ai.generativelanguage_v1.types.GenerationConfig):
            Optional. Configuration options for model
            generation and outputs.

            This field is a member of `oneof`_ ``_generation_config``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    contents: MutableSequence[gag_content.Content] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    safety_settings: MutableSequence[safety.SafetySetting] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.SafetySetting,
    )
    generation_config: "GenerationConfig" = proto.Field(
        proto.MESSAGE,
        number=4,
        optional=True,
        message="GenerationConfig",
    )


class GenerationConfig(proto.Message):
    r"""Configuration options for model generation and outputs. Not
    all parameters are configurable for every model.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        candidate_count (int):
            Optional. Number of generated responses to
            return.
            Currently, this value can only be set to 1. If
            unset, this will default to 1.

            This field is a member of `oneof`_ ``_candidate_count``.
        stop_sequences (MutableSequence[str]):
            Optional. The set of character sequences (up to 5) that will
            stop output generation. If specified, the API will stop at
            the first appearance of a ``stop_sequence``. The stop
            sequence will not be included as part of the response.
        max_output_tokens (int):
            Optional. The maximum number of tokens to include in a
            response candidate.

            Note: The default value varies by model, see the
            ``Model.output_token_limit`` attribute of the ``Model``
            returned from the ``getModel`` function.

            This field is a member of `oneof`_ ``_max_output_tokens``.
        temperature (float):
            Optional. Controls the randomness of the output.

            Note: The default value varies by model, see the
            ``Model.temperature`` attribute of the ``Model`` returned
            from the ``getModel`` function.

            Values can range from [0.0, 2.0].

            This field is a member of `oneof`_ ``_temperature``.
        top_p (float):
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and Top-p (nucleus) sampling.

            Tokens are sorted based on their assigned probabilities so
            that only the most likely tokens are considered. Top-k
            sampling directly limits the maximum number of tokens to
            consider, while Nucleus sampling limits the number of tokens
            based on the cumulative probability.

            Note: The default value varies by ``Model`` and is specified
            by the\ ``Model.top_p`` attribute returned from the
            ``getModel`` function. An empty ``top_k`` attribute
            indicates that the model doesn't apply top-k sampling and
            doesn't allow setting ``top_k`` on requests.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            Gemini models use Top-p (nucleus) sampling or a combination
            of Top-k and nucleus sampling. Top-k sampling considers the
            set of ``top_k`` most probable tokens. Models running with
            nucleus sampling don't allow top_k setting.

            Note: The default value varies by ``Model`` and is specified
            by the\ ``Model.top_p`` attribute returned from the
            ``getModel`` function. An empty ``top_k`` attribute
            indicates that the model doesn't apply top-k sampling and
            doesn't allow setting ``top_k`` on requests.

            This field is a member of `oneof`_ ``_top_k``.
        presence_penalty (float):
            Optional. Presence penalty applied to the next token's
            logprobs if the token has already been seen in the response.

            This penalty is binary on/off and not dependant on the
            number of times the token is used (after the first). Use
            [frequency_penalty][google.ai.generativelanguage.v1.GenerationConfig.frequency_penalty]
            for a penalty that increases with each use.

            A positive penalty will discourage the use of tokens that
            have already been used in the response, increasing the
            vocabulary.

            A negative penalty will encourage the use of tokens that
            have already been used in the response, decreasing the
            vocabulary.

            This field is a member of `oneof`_ ``_presence_penalty``.
        frequency_penalty (float):
            Optional. Frequency penalty applied to the next token's
            logprobs, multiplied by the number of times each token has
            been seen in the respponse so far.

            A positive penalty will discourage the use of tokens that
            have already been used, proportional to the number of times
            the token has been used: The more a token is used, the more
            dificult it is for the model to use that token again
            increasing the vocabulary of responses.

            Caution: A *negative* penalty will encourage the model to
            reuse tokens proportional to the number of times the token
            has been used. Small negative values will reduce the
            vocabulary of a response. Larger negative values will cause
            the model to start repeating a common token until it hits
            the
            [max_output_tokens][google.ai.generativelanguage.v1.GenerationConfig.max_output_tokens]
            limit: "...the the the the the...".

            This field is a member of `oneof`_ ``_frequency_penalty``.
        response_logprobs (bool):
            Optional. If true, export the logprobs
            results in response.

            This field is a member of `oneof`_ ``_response_logprobs``.
        logprobs (int):
            Optional. Only valid if
            [response_logprobs=True][google.ai.generativelanguage.v1.GenerationConfig.response_logprobs].
            This sets the number of top logprobs to return at each
            decoding step in the
            [Candidate.logprobs_result][google.ai.generativelanguage.v1.Candidate.logprobs_result].

            This field is a member of `oneof`_ ``_logprobs``.
    """

    candidate_count: int = proto.Field(
        proto.INT32,
        number=1,
        optional=True,
    )
    stop_sequences: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=2,
    )
    max_output_tokens: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=5,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=6,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=7,
        optional=True,
    )
    presence_penalty: float = proto.Field(
        proto.FLOAT,
        number=15,
        optional=True,
    )
    frequency_penalty: float = proto.Field(
        proto.FLOAT,
        number=16,
        optional=True,
    )
    response_logprobs: bool = proto.Field(
        proto.BOOL,
        number=17,
        optional=True,
    )
    logprobs: int = proto.Field(
        proto.INT32,
        number=18,
        optional=True,
    )


class GenerateContentResponse(proto.Message):
    r"""Response from the model supporting multiple candidate responses.

    Safety ratings and content filtering are reported for both prompt in
    ``GenerateContentResponse.prompt_feedback`` and for each candidate
    in ``finish_reason`` and in ``safety_ratings``. The API:

    -  Returns either all requested candidates or none of them
    -  Returns no candidates at all only if there was something wrong
       with the prompt (check ``prompt_feedback``)
    -  Reports feedback on each candidate in ``finish_reason`` and
       ``safety_ratings``.

    Attributes:
        candidates (MutableSequence[google.ai.generativelanguage_v1.types.Candidate]):
            Candidate responses from the model.
        prompt_feedback (google.ai.generativelanguage_v1.types.GenerateContentResponse.PromptFeedback):
            Returns the prompt's feedback related to the
            content filters.
        usage_metadata (google.ai.generativelanguage_v1.types.GenerateContentResponse.UsageMetadata):
            Output only. Metadata on the generation
            requests' token usage.
    """

    class PromptFeedback(proto.Message):
        r"""A set of the feedback metadata the prompt specified in
        ``GenerateContentRequest.content``.

        Attributes:
            block_reason (google.ai.generativelanguage_v1.types.GenerateContentResponse.PromptFeedback.BlockReason):
                Optional. If set, the prompt was blocked and
                no candidates are returned. Rephrase the prompt.
            safety_ratings (MutableSequence[google.ai.generativelanguage_v1.types.SafetyRating]):
                Ratings for safety of the prompt.
                There is at most one rating per category.
        """

        class BlockReason(proto.Enum):
            r"""Specifies the reason why the prompt was blocked.

            Values:
                BLOCK_REASON_UNSPECIFIED (0):
                    Default value. This value is unused.
                SAFETY (1):
                    Prompt was blocked due to safety reasons. Inspect
                    ``safety_ratings`` to understand which safety category
                    blocked it.
                OTHER (2):
                    Prompt was blocked due to unknown reasons.
                BLOCKLIST (3):
                    Prompt was blocked due to the terms which are
                    included from the terminology blocklist.
                PROHIBITED_CONTENT (4):
                    Prompt was blocked due to prohibited content.
            """
            BLOCK_REASON_UNSPECIFIED = 0
            SAFETY = 1
            OTHER = 2
            BLOCKLIST = 3
            PROHIBITED_CONTENT = 4

        block_reason: "GenerateContentResponse.PromptFeedback.BlockReason" = (
            proto.Field(
                proto.ENUM,
                number=1,
                enum="GenerateContentResponse.PromptFeedback.BlockReason",
            )
        )
        safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
            proto.MESSAGE,
            number=2,
            message=safety.SafetyRating,
        )

    class UsageMetadata(proto.Message):
        r"""Metadata on the generation request's token usage.

        Attributes:
            prompt_token_count (int):
                Number of tokens in the prompt. When ``cached_content`` is
                set, this is still the total effective prompt size meaning
                this includes the number of tokens in the cached content.
            candidates_token_count (int):
                Total number of tokens across all the
                generated response candidates.
            total_token_count (int):
                Total token count for the generation request
                (prompt + response candidates).
        """

        prompt_token_count: int = proto.Field(
            proto.INT32,
            number=1,
        )
        candidates_token_count: int = proto.Field(
            proto.INT32,
            number=2,
        )
        total_token_count: int = proto.Field(
            proto.INT32,
            number=3,
        )

    candidates: MutableSequence["Candidate"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="Candidate",
    )
    prompt_feedback: PromptFeedback = proto.Field(
        proto.MESSAGE,
        number=2,
        message=PromptFeedback,
    )
    usage_metadata: UsageMetadata = proto.Field(
        proto.MESSAGE,
        number=3,
        message=UsageMetadata,
    )


class Candidate(proto.Message):
    r"""A response candidate generated from the model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        index (int):
            Output only. Index of the candidate in the
            list of response candidates.

            This field is a member of `oneof`_ ``_index``.
        content (google.ai.generativelanguage_v1.types.Content):
            Output only. Generated content returned from
            the model.
        finish_reason (google.ai.generativelanguage_v1.types.Candidate.FinishReason):
            Optional. Output only. The reason why the
            model stopped generating tokens.
            If empty, the model has not stopped generating
            tokens.
        safety_ratings (MutableSequence[google.ai.generativelanguage_v1.types.SafetyRating]):
            List of ratings for the safety of a response
            candidate.
            There is at most one rating per category.
        citation_metadata (google.ai.generativelanguage_v1.types.CitationMetadata):
            Output only. Citation information for model-generated
            candidate.

            This field may be populated with recitation information for
            any text included in the ``content``. These are passages
            that are "recited" from copyrighted material in the
            foundational LLM's training data.
        token_count (int):
            Output only. Token count for this candidate.
        avg_logprobs (float):
            Output only.
        logprobs_result (google.ai.generativelanguage_v1.types.LogprobsResult):
            Output only. Log-likelihood scores for the
            response tokens and top tokens
    """

    class FinishReason(proto.Enum):
        r"""Defines the reason why the model stopped generating tokens.

        Values:
            FINISH_REASON_UNSPECIFIED (0):
                Default value. This value is unused.
            STOP (1):
                Natural stop point of the model or provided
                stop sequence.
            MAX_TOKENS (2):
                The maximum number of tokens as specified in
                the request was reached.
            SAFETY (3):
                The response candidate content was flagged
                for safety reasons.
            RECITATION (4):
                The response candidate content was flagged
                for recitation reasons.
            LANGUAGE (6):
                The response candidate content was flagged
                for using an unsupported language.
            OTHER (5):
                Unknown reason.
            BLOCKLIST (7):
                Token generation stopped because the content
                contains forbidden terms.
            PROHIBITED_CONTENT (8):
                Token generation stopped for potentially
                containing prohibited content.
            SPII (9):
                Token generation stopped because the content
                potentially contains Sensitive Personally
                Identifiable Information (SPII).
            MALFORMED_FUNCTION_CALL (10):
                The function call generated by the model is
                invalid.
        """
        FINISH_REASON_UNSPECIFIED = 0
        STOP = 1
        MAX_TOKENS = 2
        SAFETY = 3
        RECITATION = 4
        LANGUAGE = 6
        OTHER = 5
        BLOCKLIST = 7
        PROHIBITED_CONTENT = 8
        SPII = 9
        MALFORMED_FUNCTION_CALL = 10

    index: int = proto.Field(
        proto.INT32,
        number=3,
        optional=True,
    )
    content: gag_content.Content = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_content.Content,
    )
    finish_reason: FinishReason = proto.Field(
        proto.ENUM,
        number=2,
        enum=FinishReason,
    )
    safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
        proto.MESSAGE,
        number=5,
        message=safety.SafetyRating,
    )
    citation_metadata: citation.CitationMetadata = proto.Field(
        proto.MESSAGE,
        number=6,
        message=citation.CitationMetadata,
    )
    token_count: int = proto.Field(
        proto.INT32,
        number=7,
    )
    avg_logprobs: float = proto.Field(
        proto.DOUBLE,
        number=10,
    )
    logprobs_result: "LogprobsResult" = proto.Field(
        proto.MESSAGE,
        number=11,
        message="LogprobsResult",
    )


class LogprobsResult(proto.Message):
    r"""Logprobs Result

    Attributes:
        top_candidates (MutableSequence[google.ai.generativelanguage_v1.types.LogprobsResult.TopCandidates]):
            Length = total number of decoding steps.
        chosen_candidates (MutableSequence[google.ai.generativelanguage_v1.types.LogprobsResult.Candidate]):
            Length = total number of decoding steps. The chosen
            candidates may or may not be in top_candidates.
    """

    class Candidate(proto.Message):
        r"""Candidate for the logprobs token and score.

        .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

        Attributes:
            token (str):
                The candidate’s token string value.

                This field is a member of `oneof`_ ``_token``.
            token_id (int):
                The candidate’s token id value.

                This field is a member of `oneof`_ ``_token_id``.
            log_probability (float):
                The candidate's log probability.

                This field is a member of `oneof`_ ``_log_probability``.
        """

        token: str = proto.Field(
            proto.STRING,
            number=1,
            optional=True,
        )
        token_id: int = proto.Field(
            proto.INT32,
            number=3,
            optional=True,
        )
        log_probability: float = proto.Field(
            proto.FLOAT,
            number=2,
            optional=True,
        )

    class TopCandidates(proto.Message):
        r"""Candidates with top log probabilities at each decoding step.

        Attributes:
            candidates (MutableSequence[google.ai.generativelanguage_v1.types.LogprobsResult.Candidate]):
                Sorted by log probability in descending
                order.
        """

        candidates: MutableSequence["LogprobsResult.Candidate"] = proto.RepeatedField(
            proto.MESSAGE,
            number=1,
            message="LogprobsResult.Candidate",
        )

    top_candidates: MutableSequence[TopCandidates] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message=TopCandidates,
    )
    chosen_candidates: MutableSequence[Candidate] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=Candidate,
    )


class EmbedContentRequest(proto.Message):
    r"""Request containing the ``Content`` for the model to embed.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        content (google.ai.generativelanguage_v1.types.Content):
            Required. The content to embed. Only the ``parts.text``
            fields will be counted.
        task_type (google.ai.generativelanguage_v1.types.TaskType):
            Optional. Optional task type for which the embeddings will
            be used. Can only be set for ``models/embedding-001``.

            This field is a member of `oneof`_ ``_task_type``.
        title (str):
            Optional. An optional title for the text. Only applicable
            when TaskType is ``RETRIEVAL_DOCUMENT``.

            Note: Specifying a ``title`` for ``RETRIEVAL_DOCUMENT``
            provides better quality embeddings for retrieval.

            This field is a member of `oneof`_ ``_title``.
        output_dimensionality (int):
            Optional. Optional reduced dimension for the output
            embedding. If set, excessive values in the output embedding
            are truncated from the end. Supported by newer models since
            2024 only. You cannot set this value if using the earlier
            model (``models/embedding-001``).

            This field is a member of `oneof`_ ``_output_dimensionality``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    content: gag_content.Content = proto.Field(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    task_type: "TaskType" = proto.Field(
        proto.ENUM,
        number=3,
        optional=True,
        enum="TaskType",
    )
    title: str = proto.Field(
        proto.STRING,
        number=4,
        optional=True,
    )
    output_dimensionality: int = proto.Field(
        proto.INT32,
        number=5,
        optional=True,
    )


class ContentEmbedding(proto.Message):
    r"""A list of floats representing an embedding.

    Attributes:
        values (MutableSequence[float]):
            The embedding values.
    """

    values: MutableSequence[float] = proto.RepeatedField(
        proto.FLOAT,
        number=1,
    )


class EmbedContentResponse(proto.Message):
    r"""The response to an ``EmbedContentRequest``.

    Attributes:
        embedding (google.ai.generativelanguage_v1.types.ContentEmbedding):
            Output only. The embedding generated from the
            input content.
    """

    embedding: "ContentEmbedding" = proto.Field(
        proto.MESSAGE,
        number=1,
        message="ContentEmbedding",
    )


class BatchEmbedContentsRequest(proto.Message):
    r"""Batch request to get embeddings from the model for a list of
    prompts.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        requests (MutableSequence[google.ai.generativelanguage_v1.types.EmbedContentRequest]):
            Required. Embed requests for the batch. The model in each of
            these requests must match the model specified
            ``BatchEmbedContentsRequest.model``.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    requests: MutableSequence["EmbedContentRequest"] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message="EmbedContentRequest",
    )


class BatchEmbedContentsResponse(proto.Message):
    r"""The response to a ``BatchEmbedContentsRequest``.

    Attributes:
        embeddings (MutableSequence[google.ai.generativelanguage_v1.types.ContentEmbedding]):
            Output only. The embeddings for each request,
            in the same order as provided in the batch
            request.
    """

    embeddings: MutableSequence["ContentEmbedding"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="ContentEmbedding",
    )


class CountTokensRequest(proto.Message):
    r"""Counts the number of tokens in the ``prompt`` sent to a model.

    Models may tokenize text differently, so each model may return a
    different ``token_count``.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        contents (MutableSequence[google.ai.generativelanguage_v1.types.Content]):
            Optional. The input given to the model as a prompt. This
            field is ignored when ``generate_content_request`` is set.
        generate_content_request (google.ai.generativelanguage_v1.types.GenerateContentRequest):
            Optional. The overall input given to the ``Model``. This
            includes the prompt as well as other model steering
            information like `system
            instructions <https://ai.google.dev/gemini-api/docs/system-instructions>`__,
            and/or function declarations for `function
            calling <https://ai.google.dev/gemini-api/docs/function-calling>`__.
            ``Model``\ s/\ ``Content``\ s and
            ``generate_content_request``\ s are mutually exclusive. You
            can either send ``Model`` + ``Content``\ s or a
            ``generate_content_request``, but never both.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    contents: MutableSequence[gag_content.Content] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=gag_content.Content,
    )
    generate_content_request: "GenerateContentRequest" = proto.Field(
        proto.MESSAGE,
        number=3,
        message="GenerateContentRequest",
    )


class CountTokensResponse(proto.Message):
    r"""A response from ``CountTokens``.

    It returns the model's ``token_count`` for the ``prompt``.

    Attributes:
        total_tokens (int):
            The number of tokens that the ``Model`` tokenizes the
            ``prompt`` into. Always non-negative.
    """

    total_tokens: int = proto.Field(
        proto.INT32,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))
