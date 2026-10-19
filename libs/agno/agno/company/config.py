"""Opt-in Company configuration."""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from agno.company.declarations import Product
from agno.db.base import AsyncBaseDb, BaseDb
from agno.models.base import Model


@dataclass
class CompanyConfig:
    """Company resources. An omitted database inherits AgentOS.db at assembly."""

    db: Optional[Union[BaseDb, AsyncBaseDb]] = None
    model: Optional[Model] = None
    products: List["Product"] = field(default_factory=list)
    acceptance_checks: Dict[str, Callable[[Dict[str, Any], Any], Any]] = field(default_factory=dict)
    automation_history_retention_days: int = 30
    namespace: str = "company"
    task_input_max_bytes: int = 256 * 1024

    def __post_init__(self) -> None:
        from agno.fs._paths import normalize_namespace

        if not isinstance(self.namespace, str) or not self.namespace.strip():
            raise ValueError("namespace must be a non-empty path prefix")
        normalize_namespace(self.namespace)
        if (
            isinstance(self.task_input_max_bytes, bool)
            or not isinstance(self.task_input_max_bytes, int)
            or self.task_input_max_bytes < 1
        ):
            raise ValueError("task_input_max_bytes must be a positive integer")
        if (
            isinstance(self.automation_history_retention_days, bool)
            or not isinstance(self.automation_history_retention_days, int)
            or self.automation_history_retention_days < 1
        ):
            raise ValueError("automation_history_retention_days must be a positive integer")


# Bound only from framework-injected tool context; model arguments never set identities.
_namespace_values: ContextVar[Dict[str, Any]] = ContextVar("company_namespace_values", default={})


def _namespace_bindings() -> Dict[str, Any]:
    from agno.run.authorization import current_authorization

    values = dict(_namespace_values.get())
    authority = current_authorization()
    if authority is not None:
        values["user_id"] = authority.context.principal_id
    return values


def _resolved_namespace(namespace: str) -> str:
    from agno.fs._paths import normalize_namespace, normalize_template_value, parse_namespace_template

    name = normalize_namespace(namespace)
    values = _namespace_bindings()
    for placeholder in parse_namespace_template(name):
        name = name.replace("{" + placeholder + "}", normalize_template_value(placeholder, values.get(placeholder)))
    return name


def _namespace_scope(fn):
    import inspect
    from functools import wraps

    signature = inspect.signature(fn)
    parameters = list(signature.parameters.values())
    for name in ("_agno_agent", "_agno_team"):
        if name not in signature.parameters:
            index = next((i for i, p in enumerate(parameters) if p.kind == p.VAR_KEYWORD), len(parameters))
            parameters.insert(
                index, inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=None, annotation=Any)
            )

    def bind(args, kwargs):
        agent, team = kwargs.get("_agno_agent"), kwargs.get("_agno_team")
        for name in ("_agno_agent", "_agno_team"):
            if name not in signature.parameters:
                kwargs.pop(name, None)
        bound = signature.bind(*args, **kwargs).arguments
        extra = bound.get("kwargs", {})
        context = bound.get("_agno_run_context", bound.get("run_context", extra.get("run_context")))
        values = {key: getattr(context, key, None) or extra.get(key) for key in ("user_id", "agent_id", "team_id")}
        values["agent_id"] = getattr(agent, "id", None) or values["agent_id"]
        values["team_id"] = getattr(team, "id", None) or getattr(agent, "team_id", None) or values["team_id"]
        return _namespace_values.set(values)

    if inspect.iscoroutinefunction(fn):

        @wraps(fn)
        async def wrapped(*args, **kwargs):
            token = bind(args, kwargs)
            try:
                return await fn(*args, **kwargs)
            finally:
                _namespace_values.reset(token)
    else:

        @wraps(fn)
        def wrapped(*args, **kwargs):
            token = bind(args, kwargs)
            try:
                return fn(*args, **kwargs)
            finally:
                _namespace_values.reset(token)

    setattr(wrapped, "__signature__", signature.replace(parameters=parameters))
    wrapped.__annotations__ = {**fn.__annotations__, "_agno_agent": Any, "_agno_team": Any}
    return wrapped
