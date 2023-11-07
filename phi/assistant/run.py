from typing import Any, Optional, Dict

from pydantic import BaseModel, ConfigDict


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

    # If True, show debug logs
    debug_mode: bool = False
    # Enable monitoring on phidata.com
    monitoring: bool = False

    # Set of 16 key-value pairs that can be attached to an object.
    # This can be useful for storing additional information about the object in a structured format.
    # Keys can be a maximum of 64 characters long and values can be a maxium of 512 characters long.
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
