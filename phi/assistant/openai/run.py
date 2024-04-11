from typing import Any, Optional, Dict, List, Union, Callable, cast
from typing_extensions import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from phi.assistant.openai.assistant import OpenAIAssistant
from phi.assistant.openai.exceptions import ThreadIdNotSet, AssistantIdNotSet, RunIdNotSet
from phi.tools import Tool, Toolkit
from phi.tools.function import Function
from phi.utils.functions import get_function_call
from phi.utils.log import logger

try:
    from openai import OpenAI
    from openai.types.beta.threads.run import (
        Run as OpenAIRun,
        RequiredAction,
        LastError,
    )
    from openai.types.beta.threads.required_action_function_tool_call import RequiredActionFunctionToolCall
    from openai.types.beta.threads.run_submit_tool_outputs_params import ToolOutput
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
    # OpenAIAssistant used for this run
    assistant: Optional[OpenAIAssistant] = None
    # The ID of the assistant used for execution of this run.
    assistant_id: Optional[str] = None

    # The status of the run, which can be either
    # queued, in_progress, requires_action, cancelling, cancelled, failed, completed, or expired.
    status: Optional[
        Literal["queued", "in_progress", "requires_action", "cancelling", "cancelled", "failed", "completed", "expired"]
    ] = None

    # Details on the action required to continue the run. Will be null if no action is required.
    required_action: Optional[RequiredAction] = None

    # The Unix timestamp (in seconds) for when the run was created.
    created_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run was started.
    started_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run will expire.
    expires_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run was cancelled.
    cancelled_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run failed.
    failed_at: Optional[int] = None
    # The Unix timestamp (in seconds) for when the run was completed.
    completed_at: Optional[int] = None

    # The list of File IDs the assistant used for this run.
    file_ids: Optional[List[str]] = None

    # The ID of the Model to be used to execute this run. If a value is provided here,
    # it will override the model associated with the assistant.
    # If not, the model associated with the assistant will be used.
    model: Optional[str] = None
    # Override the default system message of the assistant.
    # This is useful for modifying the behavior on a per-run basis.
    instructions: Optional[str] = None
    # Override the tools the assistant can use for this run.
    # This is useful for modifying the behavior on a per-run basis.
    tools: Optional[List[Union[Tool, Toolkit, Callable, Dict, Function]]] = None
    # Functions extracted from the tools which can be executed locally by the assistant.
    functions: Optional[Dict[str, Function]] = None

    # The last error associated with this run. Will be null if there are no errors.
    last_error: Optional[LastError] = None

    # Set of 16 key-value pairs that can be attached to an object.
    # This can be useful for storing additional information about the object in a structured format.
    # Keys can be a maximum of 64 characters long and values can be a maximum of 512 characters long.
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

    @model_validator(mode="after")
    def extract_functions_from_tools(self) -> "Run":
        if self.tools is not None:
            for tool in self.tools:
                if self.functions is None:
                    self.functions = {}
                if isinstance(tool, Toolkit):
                    self.functions.update(tool.functions)
                    logger.debug(f"Functions from {tool.name} added to OpenAIAssistant.")
                elif isinstance(tool, Function):
                    self.functions[tool.name] = tool
                    logger.debug(f"Function {tool.name} added to OpenAIAssistant.")
                elif callable(tool):
                    f = Function.from_callable(tool)
                    self.functions[f.name] = f
                    logger.debug(f"Function {f.name} added to OpenAIAssistant")
        return self

    def load_from_openai(self, openai_run: OpenAIRun):
        self.id = openai_run.id
        self.object = openai_run.object
        self.status = openai_run.status
        self.required_action = openai_run.required_action
        self.last_error = openai_run.last_error
        self.created_at = openai_run.created_at
        self.started_at = openai_run.started_at
        self.expires_at = openai_run.expires_at
        self.cancelled_at = openai_run.cancelled_at
        self.failed_at = openai_run.failed_at
        self.completed_at = openai_run.completed_at
        self.file_ids = openai_run.file_ids
        self.openai_run = openai_run

    def get_tools_for_api(self) -> Optional[List[Dict[str, Any]]]:
        if self.tools is None:
            return None

        tools_for_api = []
        for tool in self.tools:
            if isinstance(tool, Tool):
                tools_for_api.append(tool.to_dict())
            elif isinstance(tool, dict):
                tools_for_api.append(tool)
            elif callable(tool):
                func = Function.from_callable(tool)
                tools_for_api.append({"type": "function", "function": func.to_dict()})
            elif isinstance(tool, Toolkit):
                for _f in tool.functions.values():
                    tools_for_api.append({"type": "function", "function": _f.to_dict()})
            elif isinstance(tool, Function):
                tools_for_api.append({"type": "function", "function": tool.to_dict()})
        return tools_for_api

    def create(
        self,
        thread_id: Optional[str] = None,
        assistant: Optional[OpenAIAssistant] = None,
        assistant_id: Optional[str] = None,
    ) -> "Run":
        _thread_id = thread_id or self.thread_id
        if _thread_id is None:
            raise ThreadIdNotSet("Thread.id not set")

        _assistant_id = assistant.get_id() if assistant is not None else assistant_id
        if _assistant_id is None:
            _assistant_id = self.assistant.get_id() if self.assistant is not None else self.assistant_id
        if _assistant_id is None:
            raise AssistantIdNotSet("OpenAIAssistant.id not set")

        request_body: Dict[str, Any] = {}
        if self.model is not None:
            request_body["model"] = self.model
        if self.instructions is not None:
            request_body["instructions"] = self.instructions
        if self.tools is not None:
            request_body["tools"] = self.get_tools_for_api()
        if self.metadata is not None:
            request_body["metadata"] = self.metadata

        self.openai_run = self.client.beta.threads.runs.create(
            thread_id=_thread_id, assistant_id=_assistant_id, **request_body
        )
        self.load_from_openai(self.openai_run)  # type: ignore
        logger.debug(f"Run created: {self.id}")
        return self

    def get_id(self) -> Optional[str]:
        return self.id or self.openai_run.id if self.openai_run else None

    def get_from_openai(self, thread_id: Optional[str] = None) -> OpenAIRun:
        _thread_id = thread_id or self.thread_id
        if _thread_id is None:
            raise ThreadIdNotSet("Thread.id not set")

        _run_id = self.get_id()
        if _run_id is None:
            raise RunIdNotSet("Run.id not set")

        self.openai_run = self.client.beta.threads.runs.retrieve(
            thread_id=_thread_id,
            run_id=_run_id,
        )
        self.load_from_openai(self.openai_run)
        return self.openai_run

    def get(self, use_cache: bool = True, thread_id: Optional[str] = None) -> "Run":
        if self.openai_run is not None and use_cache:
            return self

        self.get_from_openai(thread_id=thread_id)
        return self

    def get_or_create(
        self,
        use_cache: bool = True,
        thread_id: Optional[str] = None,
        assistant: Optional[OpenAIAssistant] = None,
        assistant_id: Optional[str] = None,
    ) -> "Run":
        try:
            return self.get(use_cache=use_cache)
        except RunIdNotSet:
            return self.create(thread_id=thread_id, assistant=assistant, assistant_id=assistant_id)

    def update(self, thread_id: Optional[str] = None) -> "Run":
        try:
            run_to_update = self.get_from_openai(thread_id=thread_id)
            if run_to_update is not None:
                request_body: Dict[str, Any] = {}
                if self.metadata is not None:
                    request_body["metadata"] = self.metadata

                self.openai_run = self.client.beta.threads.runs.update(
                    thread_id=run_to_update.thread_id,
                    run_id=run_to_update.id,
                    **request_body,
                )
                self.load_from_openai(self.openai_run)
                logger.debug(f"Run updated: {self.id}")
                return self
            raise ValueError("Run not available")
        except (ThreadIdNotSet, RunIdNotSet):
            logger.warning("Message not available")
            raise

    def wait(
        self,
        interval: int = 1,
        timeout: Optional[int] = None,
        thread_id: Optional[str] = None,
        status: Optional[List[str]] = None,
        callback: Optional[Callable[[OpenAIRun], None]] = None,
    ) -> bool:
        import time

        status_to_wait = status or ["requires_action", "cancelling", "cancelled", "failed", "completed", "expired"]
        start_time = time.time()
        while True:
            logger.debug(f"Waiting for run {self.id} to complete")
            run = self.get_from_openai(thread_id=thread_id)
            logger.debug(f"Run {run.id} {run.status}")
            if callback is not None:
                callback(run)
            if run.status in status_to_wait:
                return True
            if timeout is not None and time.time() - start_time > timeout:
                logger.error(f"Run {run.id} did not complete within {timeout} seconds")
                return False
                # raise TimeoutError(f"Run {run.id} did not complete within {timeout} seconds")
            time.sleep(interval)

    def run(
        self,
        thread_id: Optional[str] = None,
        assistant: Optional[OpenAIAssistant] = None,
        assistant_id: Optional[str] = None,
        wait: bool = True,
        callback: Optional[Callable[[OpenAIRun], None]] = None,
    ) -> "Run":
        # Update Run with new values
        self.thread_id = thread_id or self.thread_id
        self.assistant = assistant or self.assistant
        self.assistant_id = assistant_id or self.assistant_id

        # Create Run
        self.create()

        run_completed = not wait
        while not run_completed:
            self.wait(callback=callback)

            # -*- Check if run requires action
            if self.status == "requires_action":
                if self.assistant is None:
                    logger.warning("OpenAIAssistant not available to complete required_action")
                    return self
                if self.required_action is not None:
                    if self.required_action.type == "submit_tool_outputs":
                        tool_calls: List[RequiredActionFunctionToolCall] = (
                            self.required_action.submit_tool_outputs.tool_calls
                        )

                        tool_outputs = []
                        for tool_call in tool_calls:
                            if tool_call.type == "function":
                                run_functions = self.assistant.functions
                                if self.functions is not None:
                                    if run_functions is not None:
                                        run_functions.update(self.functions)
                                    else:
                                        run_functions = self.functions
                                function_call = get_function_call(
                                    name=tool_call.function.name,
                                    arguments=tool_call.function.arguments,
                                    functions=run_functions,
                                )
                                if function_call is None:
                                    logger.error(f"Function {tool_call.function.name} not found")
                                    continue

                                # -*- Run function call
                                success = function_call.execute()
                                if not success:
                                    logger.error(f"Function {tool_call.function.name} failed")
                                    continue

                                output = str(function_call.result) if function_call.result is not None else ""
                                tool_outputs.append(ToolOutput(tool_call_id=tool_call.id, output=output))

                        # -*- Submit tool outputs
                        _oai_run = cast(OpenAIRun, self.openai_run)
                        self.openai_run = self.client.beta.threads.runs.submit_tool_outputs(
                            thread_id=_oai_run.thread_id,
                            run_id=_oai_run.id,
                            tool_outputs=tool_outputs,
                        )

                        self.load_from_openai(self.openai_run)
            else:
                run_completed = True
        return self

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(
            exclude_none=True,
            include={
                "id",
                "object",
                "thread_id",
                "assistant_id",
                "status",
                "required_action",
                "last_error",
                "model",
                "instructions",
                "tools",
                "metadata",
            },
        )

    def pprint(self):
        """Pretty print using rich"""
        from rich.pretty import pprint

        pprint(self.to_dict())

    def __str__(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=4)
