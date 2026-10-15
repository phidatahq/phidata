"""Shared visibility checks for trusted application configuration and framework IDs.

Internal components remain usable through direct Python calls and native team delegation.
"""

from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Set, TypeVar

from agno.registry._reserved import MANAGER_TEAM_ID, RESERVED_MANAGER_IDS

if TYPE_CHECKING:
    from agno.registry import Registry

T = TypeVar("T")


def _is_public(kind: str, component_id: Optional[str], registry: Optional["Registry"] = None) -> bool:
    # Framework identities cannot be promoted by application policy or catalog data.
    if component_id in RESERVED_MANAGER_IDS and (kind != "team" or component_id != MANAGER_TEAM_ID):
        return False
    return registry is None or (kind, component_id) not in getattr(registry, "internal_components", ())


def _catalog_allowed(kind: str, component_id: Optional[str], registry: Optional["Registry"] = None) -> bool:
    # A stored row can never substitute for a framework-owned runtime object.
    return component_id not in RESERVED_MANAGER_IDS and _is_public(kind, component_id, registry)


def _catalog_exclusions(kind: str, registry: Optional["Registry"] = None) -> Set[str]:
    excluded = set(RESERVED_MANAGER_IDS)
    if registry is not None:
        excluded.update(
            cid for component_type, cid in getattr(registry, "internal_components", ()) if component_type == kind
        )
    return excluded


def _public_components(kind: str, components: Optional[Iterable[T]], registry: Optional["Registry"] = None) -> List[T]:
    return [c for c in components or [] if _is_public(kind, getattr(c, "id", None), registry)]


def _component_kind(component: Any) -> str:
    # Includes factories, remote proxies and external agent adapters without
    # importing the component classes (which themselves depend on Registry).
    if hasattr(component, "members") or type(component).__name__ in ("TeamFactory", "RemoteTeam"):
        return "team"
    if hasattr(component, "steps") or type(component).__name__ in ("WorkflowFactory", "RemoteWorkflow"):
        return "workflow"
    return "agent"


def _public_manifest(manifest: Any, registry: Optional["Registry"] = None) -> Any:
    if manifest is None:
        return None
    hidden = set(RESERVED_MANAGER_IDS) - {MANAGER_TEAM_ID}
    if registry is not None:
        hidden.update(cid for _, cid in getattr(registry, "internal_components", ()))
    return {key: value for key, value in manifest.items() if key not in hidden}


def _public_os_components(os: Any, kind: str) -> List[Any]:
    """Public roster for both AgentOS and lightweight router hosts."""
    return _public_components(kind, getattr(os, kind + "s", None), getattr(os, "registry", None))
