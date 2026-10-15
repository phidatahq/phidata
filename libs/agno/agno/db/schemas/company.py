"""Company errors shared by storage and services."""


class CompanyNotFound(LookupError):
    """The record does not exist or is outside the caller's membership."""


class CompanyForbidden(PermissionError):
    """A visible record requires an owner action."""


class CompanyConflict(ValueError):
    """A stale version or operation would violate a Company invariant."""
