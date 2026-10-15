"""Trusted deployment policy for component discovery, dispatch and composition.

Policies are supplied by application code, never reconstructed from component
configs or metadata. They do not grant permissions. Direct Python execution and
native delegation within an already constructed team remain application-owned.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, List, Literal, Optional, Set, TypeVar

from agno.registry._reserved import MANAGER_TEAM_ID, RESERVED_MANAGER_IDS

if TYPE_CHECKING:
    from agno.registry import Registry

ComponentKind = Literal["agent", "team", "workflow"]
T = TypeVar("T")


@dataclass(frozen=True)
class ComponentPolicy:
    """Deployment rules for one typed component identity.

    ``public=False`` makes the component internal: it cannot be discovered,
    addressed by a runner/API/schedule, or loaded into another component from
    the catalog. Its owning code-defined team can still delegate to it.
    ``composable=False`` keeps a public component runnable while excluding it
    from the build palette. Defaults preserve ordinary application behavior.
    """

    component_type: ComponentKind
    component_id: str
    public: bool = True
    composable: bool = True

    def __post_init__(self) -> None:
        if self.component_type not in ("agent", "team", "workflow") or not self.component_id:
            raise ValueError("ComponentPolicy requires a component type and a non-empty id")


def _policy(kind: str, component_id: Optional[str], registry: Optional["Registry"] = None) -> Optional[ComponentPolicy]:
    if registry is not None:
        return next(
            (
                p
                for p in getattr(registry, "component_policies", ())
                if p.component_type == kind and p.component_id == component_id
            ),
            None,
        )
    return None


def _is_public(kind: str, component_id: Optional[str], registry: Optional["Registry"] = None) -> bool:
    # Framework identities cannot be promoted by application policy or catalog data.
    if component_id in RESERVED_MANAGER_IDS and (kind != "team" or component_id != MANAGER_TEAM_ID):
        return False
    policy = _policy(kind, component_id, registry)
    return policy.public if policy is not None else True


def _is_composable(kind: str, component_id: Optional[str], registry: Optional["Registry"] = None) -> bool:
    if component_id in RESERVED_MANAGER_IDS or not _is_public(kind, component_id, registry):
        return False
    policy = _policy(kind, component_id, registry)
    return policy.composable if policy is not None else True


def _catalog_allowed(kind: str, component_id: Optional[str], registry: Optional["Registry"] = None) -> bool:
    # A stored row can never substitute for a framework-owned runtime object.
    return component_id not in RESERVED_MANAGER_IDS and _is_public(kind, component_id, registry)


def _catalog_exclusions(kind: str, registry: Optional["Registry"] = None) -> Set[str]:
    excluded = set(RESERVED_MANAGER_IDS)
    if registry is not None:
        excluded.update(
            p.component_id
            for p in getattr(registry, "component_policies", ())
            if p.component_type == kind and not p.public
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
        hidden.update(p.component_id for p in getattr(registry, "component_policies", ()) if not p.public)
    return {key: value for key, value in manifest.items() if key not in hidden}


def _public_os_components(os: Any, kind: str) -> List[Any]:
    """Public roster for both AgentOS and lightweight router hosts."""
    return _public_components(kind, getattr(os, kind + "s", None), getattr(os, "registry", None))
