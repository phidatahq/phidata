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


from typing import AsyncIterable, Iterable, Optional

import google.ai.generativelanguage as glm
from google.generativeai import protos

from google.generativeai.client import get_default_retriever_client
from google.generativeai.client import get_default_retriever_async_client
from google.generativeai.types import helper_types
from google.generativeai.types.model_types import idecode_time
from google.generativeai.types import retriever_types


def create_corpus(
    name: str | None = None,
    display_name: str | None = None,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> retriever_types.Corpus:
    """Calls the API to create a new `Corpus` by specifying either a corpus resource name as an ID or a display name, and returns the created `Corpus`.

    Args:
        name: The corpus resource name (ID). The name must be alphanumeric and fewer
            than 40 characters.
        display_name: The human readable display name. The display name must be fewer
            than 128 characters. All characters, including alphanumeric, spaces, and
            dashes are supported.
        request_options: Options for the request.

    Return:
        `retriever_types.Corpus` object with specified name or display name.

    Raises:
        ValueError: When the name is not specified or formatted incorrectly.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_client()

    if name is None:
        corpus = protos.Corpus(display_name=display_name)
    elif retriever_types.valid_name(name):
        corpus = protos.Corpus(name=f"corpora/{name}", display_name=display_name)
    else:
        raise ValueError(retriever_types.NAME_ERROR_MSG.format(length=len(name), name=name))

    request = protos.CreateCorpusRequest(corpus=corpus)
    response = client.create_corpus(request, **request_options)
    response = type(response).to_dict(response)
    idecode_time(response, "create_time")
    idecode_time(response, "update_time")
    response = retriever_types.Corpus(**response)
    return response


async def create_corpus_async(
    name: str | None = None,
    display_name: str | None = None,
    client: glm.RetrieverServiceAsyncClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> retriever_types.Corpus:
    """This is the async version of `retriever.create_corpus`."""
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_async_client()

    if name is None:
        corpus = protos.Corpus(display_name=display_name)
    elif retriever_types.valid_name(name):
        corpus = protos.Corpus(name=f"corpora/{name}", display_name=display_name)
    else:
        raise ValueError(retriever_types.NAME_ERROR_MSG.format(length=len(name), name=name))

    request = protos.CreateCorpusRequest(corpus=corpus)
    response = await client.create_corpus(request, **request_options)
    response = type(response).to_dict(response)
    idecode_time(response, "create_time")
    idecode_time(response, "update_time")
    response = retriever_types.Corpus(**response)
    return response


def get_corpus(
    name: str,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> retriever_types.Corpus:  # fmt: skip
    """Calls the API to fetch a `Corpus` by name and returns the `Corpus`.

    Args:
        name: The `Corpus` name.
        request_options: Options for the request.

    Return:
        a `retriever_types.Corpus` of interest.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_client()

    if "/" not in name:
        name = "corpora/" + name

    request = protos.GetCorpusRequest(name=name)
    response = client.get_corpus(request, **request_options)
    response = type(response).to_dict(response)
    idecode_time(response, "create_time")
    idecode_time(response, "update_time")
    response = retriever_types.Corpus(**response)
    return response


async def get_corpus_async(
    name: str,
    client: glm.RetrieverServiceAsyncClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> retriever_types.Corpus:  # fmt: skip
    """This is the async version of `retriever.get_corpus`."""

    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_async_client()

    if "/" not in name:
        name = "corpora/" + name

    request = protos.GetCorpusRequest(name=name)
    response = await client.get_corpus(request, **request_options)
    response = type(response).to_dict(response)
    idecode_time(response, "create_time")
    idecode_time(response, "update_time")
    response = retriever_types.Corpus(**response)
    return response


def delete_corpus(
    name: str,
    force: bool = False,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
):  # fmt: skip
    """Calls the API to remove a `Corpus` from the service, optionally deleting associated `Document`s and objects if the `force` parameter is set to true.

    Args:
        name: The `Corpus` name.
        force: If set to true, any `Document`s and objects related to this `Corpus` will also be deleted.
        request_options: Options for the request.

    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_client()

    if "/" not in name:
        name = "corpora/" + name

    request = protos.DeleteCorpusRequest(name=name, force=force)
    client.delete_corpus(request, **request_options)


async def delete_corpus_async(
    name: str,
    force: bool = False,
    client: glm.RetrieverServiceAsyncClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
):  # fmt: skip
    """This is the async version of `retriever.delete_corpus`."""
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_async_client()

    if "/" not in name:
        name = "corpora/" + name

    request = protos.DeleteCorpusRequest(name=name, force=force)
    await client.delete_corpus(request, **request_options)


def list_corpora(
    *,
    page_size: Optional[int] = None,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> Iterable[retriever_types.Corpus]:
    """Calls the API to list all `Corpora` in the service and returns a list of paginated `Corpora`.

    Args:
        page_size: Maximum number of `Corpora` to request.
        page_token: A page token, received from a previous ListCorpora call.
        request_options: Options for the request.

    Return:
        Paginated list of `Corpora`.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_client()

    request = protos.ListCorporaRequest(page_size=page_size)
    for corpus in client.list_corpora(request, **request_options):
        corpus = type(corpus).to_dict(corpus)
        idecode_time(corpus, "create_time")
        idecode_time(corpus, "update_time")
        yield retriever_types.Corpus(**corpus)


async def list_corpora_async(
    *,
    page_size: Optional[int] = None,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> AsyncIterable[retriever_types.Corpus]:
    """This is the async version of `retriever.list_corpora`."""
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_async_client()

    request = protos.ListCorporaRequest(page_size=page_size)
    async for corpus in await client.list_corpora(request, **request_options):
        corpus = type(corpus).to_dict(corpus)
        idecode_time(corpus, "create_time")
        idecode_time(corpus, "update_time")
        yield retriever_types.Corpus(**corpus)
