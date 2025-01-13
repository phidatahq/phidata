# Copyright 2015 Ian Cordasco
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import hashlib
import io
import json
import logging
import os
import re
import subprocess
import sys
import warnings
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

import packaging.version
import pkginfo
from rich import print

from twine import exceptions
from twine import wheel
from twine import wininst

DIST_TYPES = {
    "bdist_wheel": wheel.Wheel,
    "bdist_wininst": wininst.WinInst,
    "bdist_egg": pkginfo.BDist,
    "sdist": pkginfo.SDist,
}

DIST_EXTENSIONS = {
    ".whl": "bdist_wheel",
    ".exe": "bdist_wininst",
    ".egg": "bdist_egg",
    ".tar.bz2": "sdist",
    ".tar.gz": "sdist",
    ".zip": "sdist",
}

MetadataValue = Union[Optional[str], Sequence[str], Tuple[str, bytes]]

logger = logging.getLogger(__name__)


def _safe_name(name: str) -> str:
    """Convert an arbitrary string to a standard distribution name.

    Any runs of non-alphanumeric/. characters are replaced with a single '-'.

    Copied from pkg_resources.safe_name for compatibility with warehouse.
    See https://github.com/pypa/twine/issues/743.
    """
    return re.sub("[^A-Za-z0-9.]+", "-", name)


class CheckedDistribution(pkginfo.Distribution):
    """A Distribution whose name and version are confirmed to be defined."""

    name: str
    version: str


class PackageFile:
    def __init__(
        self,
        filename: str,
        comment: Optional[str],
        metadata: CheckedDistribution,
        python_version: Optional[str],
        filetype: Optional[str],
    ) -> None:
        self.filename = filename
        self.basefilename = os.path.basename(filename)
        self.comment = comment
        self.metadata = metadata
        self.python_version = python_version
        self.filetype = filetype
        self.safe_name = _safe_name(metadata.name)
        self.signed_filename = self.filename + ".asc"
        self.signed_basefilename = self.basefilename + ".asc"
        self.gpg_signature: Optional[Tuple[str, bytes]] = None
        self.attestations: Optional[List[Dict[Any, str]]] = None

        hasher = HashManager(filename)
        hasher.hash()
        hexdigest = hasher.hexdigest()

        self.md5_digest = hexdigest.md5
        self.sha2_digest = hexdigest.sha2
        self.blake2_256_digest = hexdigest.blake2

    @classmethod
    def from_filename(cls, filename: str, comment: Optional[str]) -> "PackageFile":
        # Extract the metadata from the package
        for ext, dtype in DIST_EXTENSIONS.items():
            if filename.endswith(ext):
                try:
                    with warnings.catch_warnings(record=True) as captured:
                        meta = DIST_TYPES[dtype](filename)
                except EOFError:
                    raise exceptions.InvalidDistribution(
                        "Invalid distribution file: '%s'" % os.path.basename(filename)
                    )
                else:
                    break
        else:
            raise exceptions.InvalidDistribution(
                "Unknown distribution format: '%s'" % os.path.basename(filename)
            )

        supported_metadata = list(pkginfo.distribution.HEADER_ATTRS)
        if cls._is_unknown_metadata_version(captured):
            raise exceptions.InvalidDistribution(
                "Make sure the distribution is using a supported Metadata-Version: "
                f"{', '.join(supported_metadata)}."
            )
        # If pkginfo <1.11 encounters a metadata version it doesn't support, it may give
        # back empty metadata. At the very least, we should have a name and version,
        # which could also be empty if, for example, a MANIFEST.in doesn't include
        # setup.cfg.
        missing_fields = [
            f.capitalize() for f in ["name", "version"] if not getattr(meta, f)
        ]
        if missing_fields:
            msg = f"Metadata is missing required fields: {', '.join(missing_fields)}."
            if cls._pkginfo_before_1_11():
                msg += (
                    "\n"
                    "Make sure the distribution includes the files where those fields "
                    "are specified, and is using a supported Metadata-Version: "
                    f"{', '.join(supported_metadata)}."
                )
            raise exceptions.InvalidDistribution(msg)

        py_version: Optional[str]
        if dtype == "bdist_egg":
            (dist,) = importlib_metadata.Distribution.discover(path=[filename])
            py_version = dist.metadata["Version"]
        elif dtype == "bdist_wheel":
            py_version = cast(wheel.Wheel, meta).py_version
        elif dtype == "bdist_wininst":
            py_version = cast(wininst.WinInst, meta).py_version
        else:
            py_version = None

        return cls(
            filename, comment, cast(CheckedDistribution, meta), py_version, dtype
        )

    @staticmethod
    def _is_unknown_metadata_version(
        captured: Iterable[warnings.WarningMessage],
    ) -> bool:
        NMV = getattr(pkginfo.distribution, "NewMetadataVersion", None)
        return any(warning.category is NMV for warning in captured)

    @staticmethod
    def _pkginfo_before_1_11() -> bool:
        ver = packaging.version.Version(importlib_metadata.version("pkginfo"))
        return ver < packaging.version.Version("1.11")

    def metadata_dictionary(self) -> Dict[str, MetadataValue]:
        """Merge multiple sources of metadata into a single dictionary.

        Includes values from filename, PKG-INFO, hashers, and signature.
        """
        meta = self.metadata
        data: Dict[str, MetadataValue] = {
            # identify release
            "name": self.safe_name,
            "version": meta.version,
            # file content
            "filetype": self.filetype,
            "pyversion": self.python_version,
            # additional meta-data
            "metadata_version": meta.metadata_version,
            "summary": meta.summary,
            "home_page": meta.home_page,
            "author": meta.author,
            "author_email": meta.author_email,
            "maintainer": meta.maintainer,
            "maintainer_email": meta.maintainer_email,
            "license": meta.license,
            "description": meta.description,
            "keywords": meta.keywords,
            "platform": meta.platforms,
            "classifiers": meta.classifiers,
            "download_url": meta.download_url,
            "supported_platform": meta.supported_platforms,
            "comment": self.comment,
            "sha256_digest": self.sha2_digest,
            # PEP 314
            "provides": meta.provides,
            "requires": meta.requires,
            "obsoletes": meta.obsoletes,
            # Metadata 1.2
            "project_urls": meta.project_urls,
            "provides_dist": meta.provides_dist,
            "obsoletes_dist": meta.obsoletes_dist,
            "requires_dist": meta.requires_dist,
            "requires_external": meta.requires_external,
            "requires_python": meta.requires_python,
            # Metadata 2.1
            "provides_extra": meta.provides_extras,
            "description_content_type": meta.description_content_type,
            # Metadata 2.2
            "dynamic": meta.dynamic,
        }

        if self.gpg_signature is not None:
            data["gpg_signature"] = self.gpg_signature

        if self.attestations is not None:
            data["attestations"] = json.dumps(self.attestations)

        # FIPS disables MD5 and Blake2, making the digest values None. Some package
        # repositories don't allow null values, so this only sends non-null values.
        # See also: https://github.com/pypa/twine/issues/775
        if self.md5_digest:
            data["md5_digest"] = self.md5_digest

        if self.blake2_256_digest:
            data["blake2_256_digest"] = self.blake2_256_digest

        return data

    def add_attestations(self, attestations: List[str]) -> None:
        loaded_attestations = []
        for attestation in attestations:
            with open(attestation, "rb") as att:
                try:
                    loaded_attestations.append(json.load(att))
                except json.JSONDecodeError:
                    raise exceptions.InvalidDistribution(
                        f"invalid JSON in attestation: {attestation}"
                    )

        self.attestations = loaded_attestations

    def add_gpg_signature(
        self, signature_filepath: str, signature_filename: str
    ) -> None:
        if self.gpg_signature is not None:
            raise exceptions.InvalidDistribution("GPG Signature can only be added once")

        with open(signature_filepath, "rb") as gpg:
            self.gpg_signature = (signature_filename, gpg.read())

    def sign(self, sign_with: str, identity: Optional[str]) -> None:
        print(f"Signing {self.basefilename}")
        gpg_args: Tuple[str, ...] = (sign_with, "--detach-sign")
        if identity:
            gpg_args += ("--local-user", identity)
        gpg_args += ("-a", self.filename)
        self.run_gpg(gpg_args)

        self.add_gpg_signature(self.signed_filename, self.signed_basefilename)

    @classmethod
    def run_gpg(cls, gpg_args: Tuple[str, ...]) -> None:
        try:
            subprocess.check_call(gpg_args)
            return
        except FileNotFoundError:
            if gpg_args[0] != "gpg":
                raise exceptions.InvalidSigningExecutable(
                    f"{gpg_args[0]} executable not available."
                )

        logger.warning("gpg executable not available. Attempting fallback to gpg2.")
        try:
            subprocess.check_call(("gpg2",) + gpg_args[1:])
        except FileNotFoundError:
            raise exceptions.InvalidSigningExecutable(
                "'gpg' or 'gpg2' executables not available.\n"
                "Try installing one of these or specifying an executable "
                "with the --sign-with flag."
            )


class Hexdigest(NamedTuple):
    md5: Optional[str]
    sha2: Optional[str]
    blake2: Optional[str]


class HashManager:
    """Manage our hashing objects for simplicity.

    This will also allow us to better test this logic.
    """

    def __init__(self, filename: str) -> None:
        """Initialize our manager and hasher objects."""
        self.filename = filename

        self._md5_hasher = None
        try:
            self._md5_hasher = hashlib.md5()
        except ValueError:
            # FIPs mode disables MD5
            pass

        self._sha2_hasher = hashlib.sha256()

        self._blake_hasher = None
        try:
            self._blake_hasher = hashlib.blake2b(digest_size=256 // 8)
        except (ValueError, TypeError, AttributeError):
            # FIPS mode disables blake2
            pass

    def _md5_update(self, content: bytes) -> None:
        if self._md5_hasher is not None:
            self._md5_hasher.update(content)

    def _md5_hexdigest(self) -> Optional[str]:
        if self._md5_hasher is not None:
            return self._md5_hasher.hexdigest()
        return None

    def _sha2_update(self, content: bytes) -> None:
        if self._sha2_hasher is not None:
            self._sha2_hasher.update(content)

    def _sha2_hexdigest(self) -> Optional[str]:
        if self._sha2_hasher is not None:
            return self._sha2_hasher.hexdigest()
        return None

    def _blake_update(self, content: bytes) -> None:
        if self._blake_hasher is not None:
            self._blake_hasher.update(content)

    def _blake_hexdigest(self) -> Optional[str]:
        if self._blake_hasher is not None:
            return self._blake_hasher.hexdigest()
        return None

    def hash(self) -> None:
        """Hash the file contents."""
        with open(self.filename, "rb") as fp:
            for content in iter(lambda: fp.read(io.DEFAULT_BUFFER_SIZE), b""):
                self._md5_update(content)
                self._sha2_update(content)
                self._blake_update(content)

    def hexdigest(self) -> Hexdigest:
        """Return the hexdigest for the file."""
        return Hexdigest(
            self._md5_hexdigest(),
            self._sha2_hexdigest(),
            self._blake_hexdigest(),
        )
