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
from google.ai.generativelanguage import gapic_version as package_version

__version__ = package_version.__version__


from google.ai.generativelanguage_v1beta.services.cache_service.async_client import (
    CacheServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.cache_service.client import (
    CacheServiceClient,
)
from google.ai.generativelanguage_v1beta.services.discuss_service.async_client import (
    DiscussServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.discuss_service.client import (
    DiscussServiceClient,
)
from google.ai.generativelanguage_v1beta.services.file_service.async_client import (
    FileServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.file_service.client import (
    FileServiceClient,
)
from google.ai.generativelanguage_v1beta.services.generative_service.async_client import (
    GenerativeServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.generative_service.client import (
    GenerativeServiceClient,
)
from google.ai.generativelanguage_v1beta.services.model_service.async_client import (
    ModelServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.model_service.client import (
    ModelServiceClient,
)
from google.ai.generativelanguage_v1beta.services.permission_service.async_client import (
    PermissionServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.permission_service.client import (
    PermissionServiceClient,
)
from google.ai.generativelanguage_v1beta.services.prediction_service.async_client import (
    PredictionServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.prediction_service.client import (
    PredictionServiceClient,
)
from google.ai.generativelanguage_v1beta.services.retriever_service.async_client import (
    RetrieverServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.retriever_service.client import (
    RetrieverServiceClient,
)
from google.ai.generativelanguage_v1beta.services.text_service.async_client import (
    TextServiceAsyncClient,
)
from google.ai.generativelanguage_v1beta.services.text_service.client import (
    TextServiceClient,
)
from google.ai.generativelanguage_v1beta.types.cache_service import (
    CreateCachedContentRequest,
    DeleteCachedContentRequest,
    GetCachedContentRequest,
    ListCachedContentsRequest,
    ListCachedContentsResponse,
    UpdateCachedContentRequest,
)
from google.ai.generativelanguage_v1beta.types.cached_content import CachedContent
from google.ai.generativelanguage_v1beta.types.citation import (
    CitationMetadata,
    CitationSource,
)
from google.ai.generativelanguage_v1beta.types.content import (
    Blob,
    CodeExecution,
    CodeExecutionResult,
    Content,
    DynamicRetrievalConfig,
    ExecutableCode,
    FileData,
    FunctionCall,
    FunctionCallingConfig,
    FunctionDeclaration,
    FunctionResponse,
    GoogleSearchRetrieval,
    GroundingPassage,
    GroundingPassages,
    Part,
    Schema,
    Tool,
    ToolConfig,
    Type,
)
from google.ai.generativelanguage_v1beta.types.discuss_service import (
    CountMessageTokensRequest,
    CountMessageTokensResponse,
    Example,
    GenerateMessageRequest,
    GenerateMessageResponse,
    Message,
    MessagePrompt,
)
from google.ai.generativelanguage_v1beta.types.file import File, VideoMetadata
from google.ai.generativelanguage_v1beta.types.file_service import (
    CreateFileRequest,
    CreateFileResponse,
    DeleteFileRequest,
    GetFileRequest,
    ListFilesRequest,
    ListFilesResponse,
)
from google.ai.generativelanguage_v1beta.types.generative_service import (
    AttributionSourceId,
    BatchEmbedContentsRequest,
    BatchEmbedContentsResponse,
    Candidate,
    ContentEmbedding,
    CountTokensRequest,
    CountTokensResponse,
    EmbedContentRequest,
    EmbedContentResponse,
    GenerateAnswerRequest,
    GenerateAnswerResponse,
    GenerateContentRequest,
    GenerateContentResponse,
    GenerationConfig,
    GroundingAttribution,
    GroundingChunk,
    GroundingMetadata,
    GroundingSupport,
    LogprobsResult,
    RetrievalMetadata,
    SearchEntryPoint,
    Segment,
    SemanticRetrieverConfig,
    TaskType,
)
from google.ai.generativelanguage_v1beta.types.model import Model
from google.ai.generativelanguage_v1beta.types.model_service import (
    CreateTunedModelMetadata,
    CreateTunedModelRequest,
    DeleteTunedModelRequest,
    GetModelRequest,
    GetTunedModelRequest,
    ListModelsRequest,
    ListModelsResponse,
    ListTunedModelsRequest,
    ListTunedModelsResponse,
    UpdateTunedModelRequest,
)
from google.ai.generativelanguage_v1beta.types.permission import Permission
from google.ai.generativelanguage_v1beta.types.permission_service import (
    CreatePermissionRequest,
    DeletePermissionRequest,
    GetPermissionRequest,
    ListPermissionsRequest,
    ListPermissionsResponse,
    TransferOwnershipRequest,
    TransferOwnershipResponse,
    UpdatePermissionRequest,
)
from google.ai.generativelanguage_v1beta.types.prediction_service import (
    PredictRequest,
    PredictResponse,
)
from google.ai.generativelanguage_v1beta.types.retriever import (
    Chunk,
    ChunkData,
    Condition,
    Corpus,
    CustomMetadata,
    Document,
    MetadataFilter,
    StringList,
)
from google.ai.generativelanguage_v1beta.types.retriever_service import (
    BatchCreateChunksRequest,
    BatchCreateChunksResponse,
    BatchDeleteChunksRequest,
    BatchUpdateChunksRequest,
    BatchUpdateChunksResponse,
    CreateChunkRequest,
    CreateCorpusRequest,
    CreateDocumentRequest,
    DeleteChunkRequest,
    DeleteCorpusRequest,
    DeleteDocumentRequest,
    GetChunkRequest,
    GetCorpusRequest,
    GetDocumentRequest,
    ListChunksRequest,
    ListChunksResponse,
    ListCorporaRequest,
    ListCorporaResponse,
    ListDocumentsRequest,
    ListDocumentsResponse,
    QueryCorpusRequest,
    QueryCorpusResponse,
    QueryDocumentRequest,
    QueryDocumentResponse,
    RelevantChunk,
    UpdateChunkRequest,
    UpdateCorpusRequest,
    UpdateDocumentRequest,
)
from google.ai.generativelanguage_v1beta.types.safety import (
    ContentFilter,
    HarmCategory,
    SafetyFeedback,
    SafetyRating,
    SafetySetting,
)
from google.ai.generativelanguage_v1beta.types.text_service import (
    BatchEmbedTextRequest,
    BatchEmbedTextResponse,
    CountTextTokensRequest,
    CountTextTokensResponse,
    Embedding,
    EmbedTextRequest,
    EmbedTextResponse,
    GenerateTextRequest,
    GenerateTextResponse,
    TextCompletion,
    TextPrompt,
)
from google.ai.generativelanguage_v1beta.types.tuned_model import (
    Dataset,
    Hyperparameters,
    TunedModel,
    TunedModelSource,
    TuningExample,
    TuningExamples,
    TuningSnapshot,
    TuningTask,
)

__all__ = (
    "CacheServiceClient",
    "CacheServiceAsyncClient",
    "DiscussServiceClient",
    "DiscussServiceAsyncClient",
    "FileServiceClient",
    "FileServiceAsyncClient",
    "GenerativeServiceClient",
    "GenerativeServiceAsyncClient",
    "ModelServiceClient",
    "ModelServiceAsyncClient",
    "PermissionServiceClient",
    "PermissionServiceAsyncClient",
    "PredictionServiceClient",
    "PredictionServiceAsyncClient",
    "RetrieverServiceClient",
    "RetrieverServiceAsyncClient",
    "TextServiceClient",
    "TextServiceAsyncClient",
    "CreateCachedContentRequest",
    "DeleteCachedContentRequest",
    "GetCachedContentRequest",
    "ListCachedContentsRequest",
    "ListCachedContentsResponse",
    "UpdateCachedContentRequest",
    "CachedContent",
    "CitationMetadata",
    "CitationSource",
    "Blob",
    "CodeExecution",
    "CodeExecutionResult",
    "Content",
    "DynamicRetrievalConfig",
    "ExecutableCode",
    "FileData",
    "FunctionCall",
    "FunctionCallingConfig",
    "FunctionDeclaration",
    "FunctionResponse",
    "GoogleSearchRetrieval",
    "GroundingPassage",
    "GroundingPassages",
    "Part",
    "Schema",
    "Tool",
    "ToolConfig",
    "Type",
    "CountMessageTokensRequest",
    "CountMessageTokensResponse",
    "Example",
    "GenerateMessageRequest",
    "GenerateMessageResponse",
    "Message",
    "MessagePrompt",
    "File",
    "VideoMetadata",
    "CreateFileRequest",
    "CreateFileResponse",
    "DeleteFileRequest",
    "GetFileRequest",
    "ListFilesRequest",
    "ListFilesResponse",
    "AttributionSourceId",
    "BatchEmbedContentsRequest",
    "BatchEmbedContentsResponse",
    "Candidate",
    "ContentEmbedding",
    "CountTokensRequest",
    "CountTokensResponse",
    "EmbedContentRequest",
    "EmbedContentResponse",
    "GenerateAnswerRequest",
    "GenerateAnswerResponse",
    "GenerateContentRequest",
    "GenerateContentResponse",
    "GenerationConfig",
    "GroundingAttribution",
    "GroundingChunk",
    "GroundingMetadata",
    "GroundingSupport",
    "LogprobsResult",
    "RetrievalMetadata",
    "SearchEntryPoint",
    "Segment",
    "SemanticRetrieverConfig",
    "TaskType",
    "Model",
    "CreateTunedModelMetadata",
    "CreateTunedModelRequest",
    "DeleteTunedModelRequest",
    "GetModelRequest",
    "GetTunedModelRequest",
    "ListModelsRequest",
    "ListModelsResponse",
    "ListTunedModelsRequest",
    "ListTunedModelsResponse",
    "UpdateTunedModelRequest",
    "Permission",
    "CreatePermissionRequest",
    "DeletePermissionRequest",
    "GetPermissionRequest",
    "ListPermissionsRequest",
    "ListPermissionsResponse",
    "TransferOwnershipRequest",
    "TransferOwnershipResponse",
    "UpdatePermissionRequest",
    "PredictRequest",
    "PredictResponse",
    "Chunk",
    "ChunkData",
    "Condition",
    "Corpus",
    "CustomMetadata",
    "Document",
    "MetadataFilter",
    "StringList",
    "BatchCreateChunksRequest",
    "BatchCreateChunksResponse",
    "BatchDeleteChunksRequest",
    "BatchUpdateChunksRequest",
    "BatchUpdateChunksResponse",
    "CreateChunkRequest",
    "CreateCorpusRequest",
    "CreateDocumentRequest",
    "DeleteChunkRequest",
    "DeleteCorpusRequest",
    "DeleteDocumentRequest",
    "GetChunkRequest",
    "GetCorpusRequest",
    "GetDocumentRequest",
    "ListChunksRequest",
    "ListChunksResponse",
    "ListCorporaRequest",
    "ListCorporaResponse",
    "ListDocumentsRequest",
    "ListDocumentsResponse",
    "QueryCorpusRequest",
    "QueryCorpusResponse",
    "QueryDocumentRequest",
    "QueryDocumentResponse",
    "RelevantChunk",
    "UpdateChunkRequest",
    "UpdateCorpusRequest",
    "UpdateDocumentRequest",
    "ContentFilter",
    "SafetyFeedback",
    "SafetyRating",
    "SafetySetting",
    "HarmCategory",
    "BatchEmbedTextRequest",
    "BatchEmbedTextResponse",
    "CountTextTokensRequest",
    "CountTextTokensResponse",
    "Embedding",
    "EmbedTextRequest",
    "EmbedTextResponse",
    "GenerateTextRequest",
    "GenerateTextResponse",
    "TextCompletion",
    "TextPrompt",
    "Dataset",
    "Hyperparameters",
    "TunedModel",
    "TunedModelSource",
    "TuningExample",
    "TuningExamples",
    "TuningSnapshot",
    "TuningTask",
)
