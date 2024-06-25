from types import ModuleType
from packaging.version import Version
from importlib.metadata import version as importlib_version


def import_vegafusion() -> ModuleType:
    min_version = "1.5.0"
    try:
        version = importlib_version("vegafusion")
        embed_version = importlib_version("vegafusion-python-embed")
        if version != embed_version or Version(version) < Version(min_version):
            raise RuntimeError(
                "The versions of the vegafusion and vegafusion-python-embed packages must match\n"
                f"and must be version {min_version} or greater.\n"
                f"Found:\n"
                f" - vegafusion=={version}\n"
                f" - vegafusion-python-embed=={embed_version}\n"
            )
        import vegafusion as vf  # type: ignore

        return vf
    except ImportError as err:
        raise ImportError(
            'The "vegafusion" data transformer and chart.transformed_data feature requires\n'
            f"version {min_version} or greater of the 'vegafusion-python-embed' and 'vegafusion' packages.\n"
            "These can be installed with pip using:\n"
            f'    pip install "vegafusion[embed]>={min_version}"\n'
            "Or with conda using:\n"
            f'    conda install -c conda-forge "vegafusion-python-embed>={min_version}" '
            f'"vegafusion>={min_version}"\n\n'
            f"ImportError: {err.args[0]}"
        ) from err


def import_vl_convert() -> ModuleType:
    min_version = "1.3.0"
    try:
        version = importlib_version("vl-convert-python")
        if Version(version) < Version(min_version):
            raise RuntimeError(
                f"The vl-convert-python package must be version {min_version} or greater. "
                f"Found version {version}"
            )
        import vl_convert as vlc

        return vlc
    except ImportError as err:
        raise ImportError(
            f"The vl-convert Vega-Lite compiler and file export feature requires\n"
            f"version {min_version} or greater of the 'vl-convert-python' package. \n"
            f"This can be installed with pip using:\n"
            f'   pip install "vl-convert-python>={min_version}"\n'
            "or conda:\n"
            f'   conda install -c conda-forge "vl-convert-python>={min_version}"\n\n'
            f"ImportError: {err.args[0]}"
        ) from err


def vl_version_for_vl_convert() -> str:
    from ..vegalite import SCHEMA_VERSION

    # Compute VlConvert's vl_version string (of the form 'v5_2')
    # from SCHEMA_VERSION (of the form 'v5.2.0')
    return "_".join(SCHEMA_VERSION.split(".")[:2])


def import_pyarrow_interchange() -> ModuleType:
    min_version = "11.0.0"
    try:
        version = importlib_version("pyarrow")

        if Version(version) < Version(min_version):
            raise RuntimeError(
                f"The pyarrow package must be version {min_version} or greater. "
                f"Found version {version}"
            )
        import pyarrow.interchange as pi

        return pi
    except ImportError as err:
        raise ImportError(
            f"Usage of the DataFrame Interchange Protocol requires\n"
            f"version {min_version} or greater of the pyarrow package. \n"
            f"This can be installed with pip using:\n"
            f'   pip install "pyarrow>={min_version}"\n'
            "or conda:\n"
            f'   conda install -c conda-forge "pyarrow>={min_version}"\n\n'
            f"ImportError: {err.args[0]}"
        ) from err


def pyarrow_available() -> bool:
    try:
        import_pyarrow_interchange()
        return True
    except (ImportError, RuntimeError):
        return False
