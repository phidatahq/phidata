from __future__ import annotations

from typing import Iterable

from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.req import InstallRequirement
from pip._internal.utils.misc import redact_auth_from_url


class PipToolsError(Exception):
    pass


class NoCandidateFound(PipToolsError):
    def __init__(
        self,
        ireq: InstallRequirement,
        candidates_tried: Iterable[InstallationCandidate],
        finder: PackageFinder,
    ) -> None:
        self.ireq = ireq
        self.candidates_tried = candidates_tried
        self.finder = finder

    def __str__(self) -> str:
        versions = []
        pre_versions = []

        for candidate in sorted(self.candidates_tried):
            version = str(candidate.version)
            if candidate.version.is_prerelease:
                pre_versions.append(version)
            else:
                versions.append(version)

        lines = [f"Could not find a version that matches {self.ireq}"]

        if versions:
            lines.append(f"Tried: {', '.join(versions)}")

        if pre_versions:
            if self.finder.allow_all_prereleases:
                line = "Tried"
            else:
                line = "Skipped"

            line += f" pre-versions: {', '.join(pre_versions)}"
            lines.append(line)

        if versions or pre_versions:
            lines.append(
                "There are incompatible versions in the resolved dependencies:"
            )
            source_ireqs = getattr(self.ireq, "_source_ireqs", [])
            lines.extend(f"  {ireq}" for ireq in source_ireqs)
        else:
            redacted_urls = tuple(
                redact_auth_from_url(url) for url in self.finder.index_urls
            )
            lines.append("No versions found")
            lines.append(
                "{} {} reachable?".format(
                    "Were" if len(redacted_urls) > 1 else "Was",
                    " or ".join(redacted_urls),
                )
            )
        return "\n".join(lines)


class IncompatibleRequirements(PipToolsError):
    def __init__(self, ireq_a: InstallRequirement, ireq_b: InstallRequirement) -> None:
        self.ireq_a = ireq_a
        self.ireq_b = ireq_b

    def __str__(self) -> str:
        message = "Incompatible requirements found: {} and {}"
        return message.format(self.ireq_a, self.ireq_b)
