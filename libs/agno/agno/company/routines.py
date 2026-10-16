"""Company schedule payloads and bundled Skills; the scheduler owns execution."""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from agno.company.declarations import Routine
from agno.company.execution import _ExecutorAuthorization, _validate_executor_tools
from agno.db.schemas.scheduler import RUN_ENDPOINT_RE
from agno.guardrails.base import BaseGuardrail
from agno.skills import LocalSkills, Skills


def load_routine_skills() -> Skills:
    """Load the editable, packaged Routine templates through the standard loader."""
    return Skills(loaders=[LocalSkills(str(Path(__file__).parent / "skills"))])


async def aload_routine_skills() -> Skills:
    """Load templates without blocking the event loop."""
    return await asyncio.to_thread(load_routine_skills)


def _routine_message(product_id: str, instructions: str) -> str:
    # Run metadata is not automatically visible in the model's messages.
    import json

    return "Operate only on Product " + json.dumps(product_id) + ".\n\n" + instructions


def _routine_failure(output: Any) -> Optional[str]:
    """Read structured execution results, never infer success from model prose."""
    if hasattr(output, "to_dict"):
        output = output.to_dict()
    if isinstance(output, list):
        for child in output:
            error = _routine_failure(child)
            if error:
                return error
    elif isinstance(output, dict):
        for tool in output.get("tools") or []:
            if tool.get("tool_call_error") and tool.get("tool_name") in {
                "add_company_source",
                "read_company_source",
                "intake_company_source",
                "propose_company_task",
                "summarize_company_product",
                "refresh_company_product",
            }:
                return str(tool["tool_name"]) + " failed: " + str(tool.get("result") or "Company operation failed")
        if output.get("success") is False:
            return str(output.get("error") or "Routine step failed")
        for key in ("member_responses", "step_results", "steps"):
            error = _routine_failure(output.get(key))
            if error:
                return error
    return None


class _RoutineResultGuardrail(BaseGuardrail):
    """Use the runtime's blocking output-check path for failed Company operations."""

    def check(self, run_input: Any = None, run_output: Any = None) -> None:
        from agno.exceptions import OutputCheckError
        from agno.run.authorization import current_authorization

        if isinstance(current_authorization(), _RoutineAuthorization):
            error = _routine_failure(run_output)
            if error:
                run_output.content = error
                raise OutputCheckError(error)

    async def async_check(self, run_input: Any = None, run_output: Any = None) -> None:
        self.check(run_input, run_output)


def _failed_routines(db: Any, products: Any) -> int:
    from agno.scheduler import ScheduleManager

    schedules = ScheduleManager(db)
    failed = 0
    for product in products:
        for routine_id in (product.get("metadata") or {}).get("routine_ids", []):
            schedule = schedules.get(routine_id)
            if schedule is None or schedule.managed_by != "company":
                continue
            runs = schedules.get_runs(routine_id, limit=1)
            failed += bool(runs and runs[0].status == "failed")
    return failed


async def _afailed_routines(db: Any, products: Any) -> int:
    from agno.scheduler import ScheduleManager

    schedules = ScheduleManager(db)
    failed = 0
    for product in products:
        for routine_id in (product.get("metadata") or {}).get("routine_ids", []):
            schedule = await schedules.aget(routine_id)
            if schedule is None or schedule.managed_by != "company":
                continue
            runs = await schedules.aget_runs(routine_id, limit=1)
            failed += bool(runs and runs[0].status == "failed")
    return failed


def _routine_executor_endpoint(executor_type: str, executor_id: str, registry: Any) -> str:
    component = getattr(registry, "get_" + executor_type)(executor_id) if registry else None
    if component is None:
        raise ValueError("Routine executor is missing from the registry")
    _validate_executor_tools(component)
    endpoint = f"/{executor_type}s/{executor_id}/runs"
    if RUN_ENDPOINT_RE.fullmatch(endpoint) is None:
        raise ValueError("Invalid Routine executor id")
    return endpoint


def _schedule_fields(product_id: str, routine: Routine, registry: Any) -> Dict[str, Any]:
    endpoint = _routine_executor_endpoint(routine.executor_type, routine.executor_id, registry)
    instructions = routine.instructions
    if instructions is None and routine.template is not None:
        skill = load_routine_skills().get_skill(routine.template)
        if skill is None:
            raise ValueError("Routine template is unavailable")
        instructions = skill.instructions
    if not instructions or not instructions.strip():
        raise ValueError("Routine instructions are required")
    fields = dict(
        name=product_id + "." + routine.name,
        cron_expr=routine.cron_expr,
        endpoint=endpoint,
        timezone=routine.timezone,
        payload={
            "message": _routine_message(product_id, instructions),
            "metadata": {"product_id": product_id, "template": routine.template, "auto_accept": False},
        },
    )

    # Reuse scheduler validation for the composed identity on every creation path.
    from agno.os.routers.schedules.schema import ScheduleCreate

    ScheduleCreate.model_validate(fields)
    return fields


class _RoutineAuthorization(_ExecutorAuthorization):
    """Routine authority permits proposals, never acceptance or schedule edits."""

    def __init__(self, original: Any, routine_id: Optional[str] = None, product_id: Optional[str] = None):
        super().__init__(original)
        self.routine_id = routine_id
        self.product_id = product_id

    def snapshot(self) -> Dict[str, Any]:
        return {
            **super().snapshot(),
            "company_routine": True,
            "company_routine_unscoped": self.original is None,
            "company_routine_id": self.routine_id,
            "company_product_id": self.product_id,
        }


def _require_routine_product(product_id: Optional[str], authority: Any = None) -> None:
    from agno.run.authorization import current_authorization

    authority = authority or current_authorization()
    if (
        isinstance(authority, _RoutineAuthorization)
        and authority.product_id is not None
        and authority.product_id != product_id
    ):
        raise PermissionError("Routine authority is restricted to its configured Product")


async def _require_active_routine_product(db: Any, product_id: Optional[str]) -> None:
    from agno.company.execution import _call

    if db is None or not product_id or await _call(db, "get_product", product_id) is None:
        raise ValueError("Routine Product is missing or archived")
