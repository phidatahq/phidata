import os
import re
import zipfile
from typing import Optional

from pkginfo import distribution

from twine import exceptions

wininst_file_re = re.compile(r".*py(?P<pyver>\d+\.\d+)\.exe$")


class WinInst(distribution.Distribution):
    def __init__(self, filename: str, metadata_version: Optional[str] = None) -> None:
        self.filename = filename
        self.metadata_version = metadata_version
        self.extractMetadata()

    @property
    def py_version(self) -> str:
        m = wininst_file_re.match(self.filename)
        if m is None:
            return "any"
        else:
            return m.group("pyver")

    def read(self) -> bytes:
        fqn = os.path.abspath(os.path.normpath(self.filename))
        if not os.path.exists(fqn):
            raise exceptions.InvalidDistribution("No such file: %s" % fqn)

        if fqn.endswith(".exe"):
            archive = zipfile.ZipFile(fqn)
            names = archive.namelist()

            def read_file(name: str) -> bytes:
                return archive.read(name)

        else:
            raise exceptions.InvalidDistribution(
                "Not a known archive format for file: %s" % fqn
            )

        try:
            tuples = [
                x.split("/") for x in names if x.endswith((".egg-info", "PKG-INFO"))
            ]
            schwarz = sorted((len(x), x) for x in tuples)
            for path in [x[1] for x in schwarz]:
                candidate = "/".join(path)
                data = read_file(candidate)
                if b"Metadata-Version" in data:
                    return data
        finally:
            archive.close()

        raise exceptions.InvalidDistribution(
            "No PKG-INFO/.egg-info in archive: %s" % fqn
        )
