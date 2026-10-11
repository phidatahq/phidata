"""Build only public package sources into a runtime image; never send the working tree."""

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="agno-sandbox:local")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    with tempfile.TemporaryDirectory(prefix="agno-runtime-build-") as directory:
        context = Path(directory)
        shutil.copytree(
            root / "libs/agno/agno",
            context / "agno",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        for filename in ("pyproject.toml", "LICENSE"):
            shutil.copyfile(root / "libs/agno" / filename, context / filename)
        shutil.copyfile(root / "README.md", context / "README.md")
        shutil.copyfile(Path(__file__).with_name("Dockerfile"), context / "Dockerfile")
        subprocess.run(
            ["docker", "build", "--progress=plain", "--tag", args.tag, str(context)],
            check=True,
        )


if __name__ == "__main__":
    main()
