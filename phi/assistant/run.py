from typing import Any, Optional, Dict, List

from pydantic import BaseModel, ConfigDict

from phi.assistant.tool import Tool
from phi.assistant.exceptions import ThreadIdNotSet, AssistantIdNotSet, RunIdNotSet
from phi.utils.log import logger

try:
    from openai import OpenAI
    from openai.types.beta.threads.run import Run as OpenAIRun
except ImportError:
    logger.error("`openai` not installed")
    raise


class Run(BaseModel):
    # -*- Run settings
    # Run id which can be referenced in API endpoints.
    id: Optional[str] = None
    # The object type, populated by the API. Always assistant.run.
    object: Optional[str] = None

    # The ID of the thread that was executed on as a part of this run.
    thread_id: Optional[str] = None
    # The ID of the assistant used for execution of this run.
    assistant_id: Optional[str] = None

    # The status of the run, which can be either
    # queued, in_progress, requires_action, cancelling, cancelled, failed, completed, or expired.
    status: Optional[str] = None

    # Details on the action required to continue the run. Will be null if no action is required.
    required_action: Optional[Dict[str, Any]] = None

    # The last error associated with this run. Will be null if there are no errors.
    last_error: Optional[Dict[str, Any]] = None

    # True if this run is active
    is_active: bool = True
    # The Unix timestamp (in seconds) for when the run was created.
    created_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run will expire.
    expires_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run was started.
    started_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run was cancelled.
    cancelled_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run failed.
    failed_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run was completed.
    completed_at: Optional[int] = None
    # The list of File IDs the assistant used for this run.
    file_ids: Optional[List[Any]] = None

    # The ID of the Model to be used to execute this run. If a value is provided here,
    # it will override the model associated with the assistant.
    # If not, the model associated with the assistant will be used.
    model: Optional[str] = None
    # Override the default system message of the assistant.
    # This is useful for modifying the behavior on a per-run basis.
    instructions: Optional[str] = None
    # Override the tools the assistant can use for this run.
    # This is useful for modifying the behavior on a per-run basis.
    tools: Optional[List[Tool | Dict]] = None

    # Set of 16 key-value pairs that can be attached to an object.
    # This can be useful for storing additional information about the object in a structured format.
    # Keys can be a maximum of 64 characters long and values can be a maxium of 512 characters long.
    metadata: Optional[Dict[str, Any]] = None

    # If True, show debug logs
    debug_mode: bool = False
    # Enable monitoring on phidata.com
    monitoring: bool = False

    openai: Optional[OpenAI] = None
    openai_run: Optional[OpenAIRun] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def client(self) -> OpenAI:
        return self.openai or OpenAI()

    def load_from_openai(self, openai_run: OpenAIRun):
        self.id = openai_run.id
        self.object = openai_run.object
        self.created_at = openai_run.created_at

    def create(self) -> OpenAIRun:
        if self.thread_id is None:
            raise ThreadIdNotSet("Thread.id not set")

        if self.assistant_id is None:
            raise AssistantIdNotSet("Assistant.id not set")

        request_body: Dict[str, Any] = {}
        if self.model:
            request_body["model"] = self.model
        if self.instructions:
            request_body["instructions"] = self.instructions
        if self.tools:
            _tools = []
            for _tool in self.tools:
                if isinstance(_tool, Tool):
                    _tools.append(_tool.to_dict())
                else:
                    _tools.append(_tool)
            request_body["tools"] = _tools
        if self.metadata:
            request_body["metadata"] = self.metadata

        self.openai_run = self.client.beta.threads.runs.create(
            thread_id=self.thread_id, assistant_id=self.assistant_id, **request_body
        )
        self.load_from_openai(self.openai_run)
        return self.openai_run

    def get(self, use_cache: bool = True) -> OpenAIRun:
        if self.openai_run is not None and use_cache:
            return self.openai_run

        if self.thread_id is None:
            raise ThreadIdNotSet("Thread.id not set")

        _run_id = self.id or self.openai_run.id if self.openai_run else None
        if _run_id is not None:
            self.openai_run = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread_id,
                run_id=_run_id,
            )
            self.load_from_openai(self.openai_run)
            return self.openai_run
        raise RunIdNotSet("Message.id not set")

    def get_or_create(self, use_cache: bool = True) -> OpenAIRun:
        try:
            return self.get(use_cache=use_cache)
        except RunIdNotSet:
            return self.create()

    def update(self) -> OpenAIRun:
        try:
            run_to_update = self.get()
            if run_to_update is not None:
                request_body: Dict[str, Any] = {}
                if self.metadata:
                    request_body["metadata"] = self.metadata

                self.openai_run = self.client.beta.threads.runs.update(
                    thread_id=run_to_update.thread_id,
                    run_id=run_to_update.id,
                    **request_body,
                )
                self.load_from_openai(self.openai_run)
                return self.openai_run
        except (ThreadIdNotSet, RunIdNotSet):
            logger.warning("Message not available")
            raise
