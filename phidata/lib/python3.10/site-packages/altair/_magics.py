"""
Magic functions for rendering vega-lite specifications
"""

__all__ = ["vegalite"]

import json
import warnings

import IPython
from IPython.core import magic_arguments
import pandas as pd
from toolz import curried

from altair.vegalite import v5 as vegalite_v5

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


RENDERERS = {
    "vega-lite": {
        "5": vegalite_v5.VegaLite,
    },
}


TRANSFORMERS = {
    "vega-lite": {
        "5": vegalite_v5.data_transformers,
    },
}


def _prepare_data(data, data_transformers):
    """Convert input data to data for use within schema"""
    if data is None or isinstance(data, dict):
        return data
    elif isinstance(data, pd.DataFrame):
        return curried.pipe(data, data_transformers.get())
    elif isinstance(data, str):
        return {"url": data}
    else:
        warnings.warn("data of type {} not recognized".format(type(data)), stacklevel=1)
        return data


def _get_variable(name):
    """Get a variable from the notebook namespace."""
    ip = IPython.get_ipython()
    if ip is None:
        raise ValueError(
            "Magic command must be run within an IPython "
            "environment, in which get_ipython() is defined."
        )
    if name not in ip.user_ns:
        raise NameError(
            "argument '{}' does not match the name of any defined variable".format(name)
        )
    return ip.user_ns[name]


@magic_arguments.magic_arguments()
@magic_arguments.argument(
    "data",
    nargs="?",
    help="local variablename of a pandas DataFrame to be used as the dataset",
)
@magic_arguments.argument("-v", "--version", dest="version", default="v5")
@magic_arguments.argument("-j", "--json", dest="json", action="store_true")
def vegalite(line, cell):
    """Cell magic for displaying vega-lite visualizations in CoLab.

    %%vegalite [dataframe] [--json] [--version='v5']

    Visualize the contents of the cell using Vega-Lite, optionally
    specifying a pandas DataFrame object to be used as the dataset.

    if --json is passed, then input is parsed as json rather than yaml.
    """
    args = magic_arguments.parse_argstring(vegalite, line)
    existing_versions = {"v5": "5"}
    version = existing_versions[args.version]
    assert version in RENDERERS["vega-lite"]
    VegaLite = RENDERERS["vega-lite"][version]
    data_transformers = TRANSFORMERS["vega-lite"][version]

    if args.json:
        spec = json.loads(cell)
    elif not YAML_AVAILABLE:
        try:
            spec = json.loads(cell)
        except json.JSONDecodeError as err:
            raise ValueError(
                "%%vegalite: spec is not valid JSON. "
                "Install pyyaml to parse spec as yaml"
            ) from err
    else:
        spec = yaml.load(cell, Loader=yaml.SafeLoader)

    if args.data is not None:
        data = _get_variable(args.data)
        spec["data"] = _prepare_data(data, data_transformers)

    return VegaLite(spec)
