from ..data import (
    MaxRowsError,
    curry,
    default_data_transformer,
    limit_rows,
    pipe,
    sample,
    to_csv,
    to_json,
    to_values,
    DataTransformerRegistry,
)

from ...utils._vegafusion_data import vegafusion_data_transformer

from typing import Final


# ==============================================================================
# VegaLite 5 data transformers
# ==============================================================================


ENTRY_POINT_GROUP: Final = "altair.vegalite.v5.data_transformer"


data_transformers = DataTransformerRegistry(entry_point_group=ENTRY_POINT_GROUP)
data_transformers.register("default", default_data_transformer)
data_transformers.register("json", to_json)
data_transformers.register("csv", to_csv)
data_transformers.register("vegafusion", vegafusion_data_transformer)
data_transformers.enable("default")


__all__ = (
    "MaxRowsError",
    "curry",
    "default_data_transformer",
    "limit_rows",
    "pipe",
    "sample",
    "to_csv",
    "to_json",
    "to_values",
    "data_transformers",
    "vegafusion_data_transformer",
)
