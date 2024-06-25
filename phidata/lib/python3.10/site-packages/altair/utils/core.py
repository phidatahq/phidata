"""
Utility routines
"""

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
import json
import itertools
import re
import sys
import traceback
import warnings
from typing import (
    Callable,
    TypeVar,
    Any,
    Union,
    Dict,
    Optional,
    Tuple,
    Sequence,
    Type,
    cast,
)
from types import ModuleType

import jsonschema
import pandas as pd
import numpy as np
from pandas.api.types import infer_dtype

from altair.utils.schemapi import SchemaBase
from altair.utils._dfi_types import Column, DtypeKind, DataFrame as DfiDataFrame

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from typing import Literal, Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from pandas.core.interchange.dataframe_protocol import Column as PandasColumn

V = TypeVar("V")
P = ParamSpec("P")


@runtime_checkable
class DataFrameLike(Protocol):
    def __dataframe__(
        self, nan_as_null: bool = False, allow_copy: bool = True
    ) -> DfiDataFrame: ...


TYPECODE_MAP = {
    "ordinal": "O",
    "nominal": "N",
    "quantitative": "Q",
    "temporal": "T",
    "geojson": "G",
}

INV_TYPECODE_MAP = {v: k for k, v in TYPECODE_MAP.items()}


# aggregates from vega-lite version 4.6.0
AGGREGATES = [
    "argmax",
    "argmin",
    "average",
    "count",
    "distinct",
    "max",
    "mean",
    "median",
    "min",
    "missing",
    "product",
    "q1",
    "q3",
    "ci0",
    "ci1",
    "stderr",
    "stdev",
    "stdevp",
    "sum",
    "valid",
    "values",
    "variance",
    "variancep",
    "exponential",
    "exponentialb",
]

# window aggregates from vega-lite version 4.6.0
WINDOW_AGGREGATES = [
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
    "first_value",
    "last_value",
    "nth_value",
]

# timeUnits from vega-lite version 4.17.0
TIMEUNITS = [
    "year",
    "quarter",
    "month",
    "week",
    "day",
    "dayofyear",
    "date",
    "hours",
    "minutes",
    "seconds",
    "milliseconds",
    "yearquarter",
    "yearquartermonth",
    "yearmonth",
    "yearmonthdate",
    "yearmonthdatehours",
    "yearmonthdatehoursminutes",
    "yearmonthdatehoursminutesseconds",
    "yearweek",
    "yearweekday",
    "yearweekdayhours",
    "yearweekdayhoursminutes",
    "yearweekdayhoursminutesseconds",
    "yeardayofyear",
    "quartermonth",
    "monthdate",
    "monthdatehours",
    "monthdatehoursminutes",
    "monthdatehoursminutesseconds",
    "weekday",
    "weeksdayhours",
    "weekdayhours",
    "weekdayhoursminutes",
    "weekdayhoursminutesseconds",
    "dayhours",
    "dayhoursminutes",
    "dayhoursminutesseconds",
    "hoursminutes",
    "hoursminutesseconds",
    "minutesseconds",
    "secondsmilliseconds",
    "utcyear",
    "utcquarter",
    "utcmonth",
    "utcweek",
    "utcday",
    "utcdayofyear",
    "utcdate",
    "utchours",
    "utcminutes",
    "utcseconds",
    "utcmilliseconds",
    "utcyearquarter",
    "utcyearquartermonth",
    "utcyearmonth",
    "utcyearmonthdate",
    "utcyearmonthdatehours",
    "utcyearmonthdatehoursminutes",
    "utcyearmonthdatehoursminutesseconds",
    "utcyearweek",
    "utcyearweekday",
    "utcyearweekdayhours",
    "utcyearweekdayhoursminutes",
    "utcyearweekdayhoursminutesseconds",
    "utcyeardayofyear",
    "utcquartermonth",
    "utcmonthdate",
    "utcmonthdatehours",
    "utcmonthdatehoursminutes",
    "utcmonthdatehoursminutesseconds",
    "utcweekday",
    "utcweeksdayhours",
    "utcweekdayhoursminutes",
    "utcweekdayhoursminutesseconds",
    "utcdayhours",
    "utcdayhoursminutes",
    "utcdayhoursminutesseconds",
    "utchoursminutes",
    "utchoursminutesseconds",
    "utcminutesseconds",
    "utcsecondsmilliseconds",
]


InferredVegaLiteType = Literal["ordinal", "nominal", "quantitative", "temporal"]


def infer_vegalite_type(
    data: object,
) -> Union[InferredVegaLiteType, Tuple[InferredVegaLiteType, list]]:
    """
    From an array-like input, infer the correct vega typecode
    ('ordinal', 'nominal', 'quantitative', or 'temporal')

    Parameters
    ----------
    data: object
    """
    typ = infer_dtype(data, skipna=False)

    if typ in [
        "floating",
        "mixed-integer-float",
        "integer",
        "mixed-integer",
        "complex",
    ]:
        return "quantitative"
    elif typ == "categorical" and hasattr(data, "cat") and data.cat.ordered:
        return ("ordinal", data.cat.categories.tolist())
    elif typ in ["string", "bytes", "categorical", "boolean", "mixed", "unicode"]:
        return "nominal"
    elif typ in [
        "datetime",
        "datetime64",
        "timedelta",
        "timedelta64",
        "date",
        "time",
        "period",
    ]:
        return "temporal"
    else:
        warnings.warn(
            "I don't know how to infer vegalite type from '{}'.  "
            "Defaulting to nominal.".format(typ),
            stacklevel=1,
        )
        return "nominal"


def merge_props_geom(feat: dict) -> dict:
    """
    Merge properties with geometry
    * Overwrites 'type' and 'geometry' entries if existing
    """

    geom = {k: feat[k] for k in ("type", "geometry")}
    try:
        feat["properties"].update(geom)
        props_geom = feat["properties"]
    except (AttributeError, KeyError):
        # AttributeError when 'properties' equals None
        # KeyError when 'properties' is non-existing
        props_geom = geom

    return props_geom


def sanitize_geo_interface(geo: MutableMapping) -> dict:
    """Santize a geo_interface to prepare it for serialization.

    * Make a copy
    * Convert type array or _Array to list
    * Convert tuples to lists (using json.loads/dumps)
    * Merge properties with geometry
    """

    geo = deepcopy(geo)

    # convert type _Array or array to list
    for key in geo.keys():
        if str(type(geo[key]).__name__).startswith(("_Array", "array")):
            geo[key] = geo[key].tolist()

    # convert (nested) tuples to lists
    geo_dct: dict = json.loads(json.dumps(geo))

    # sanitize features
    if geo_dct["type"] == "FeatureCollection":
        geo_dct = geo_dct["features"]
        if len(geo_dct) > 0:
            for idx, feat in enumerate(geo_dct):
                geo_dct[idx] = merge_props_geom(feat)
    elif geo_dct["type"] == "Feature":
        geo_dct = merge_props_geom(geo_dct)
    else:
        geo_dct = {"type": "Feature", "geometry": geo_dct}

    return geo_dct


def numpy_is_subtype(dtype: Any, subtype: Any) -> bool:
    try:
        return np.issubdtype(dtype, subtype)
    except (NotImplementedError, TypeError):
        return False


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:  # noqa: C901
    """Sanitize a DataFrame to prepare it for serialization.

    * Make a copy
    * Convert RangeIndex columns to strings
    * Raise ValueError if column names are not strings
    * Raise ValueError if it has a hierarchical index.
    * Convert categoricals to strings.
    * Convert np.bool_ dtypes to Python bool objects
    * Convert np.int dtypes to Python int objects
    * Convert floats to objects and replace NaNs/infs with None.
    * Convert DateTime dtypes into appropriate string representations
    * Convert Nullable integers to objects and replace NaN with None
    * Convert Nullable boolean to objects and replace NaN with None
    * convert dedicated string column to objects and replace NaN with None
    * Raise a ValueError for TimeDelta dtypes
    """
    df = df.copy()

    if isinstance(df.columns, pd.RangeIndex):
        df.columns = df.columns.astype(str)

    for col_name in df.columns:
        if not isinstance(col_name, str):
            raise ValueError(
                "Dataframe contains invalid column name: {0!r}. "
                "Column names must be strings".format(col_name)
            )

    if isinstance(df.index, pd.MultiIndex):
        raise ValueError("Hierarchical indices not supported")
    if isinstance(df.columns, pd.MultiIndex):
        raise ValueError("Hierarchical indices not supported")

    def to_list_if_array(val):
        if isinstance(val, np.ndarray):
            return val.tolist()
        else:
            return val

    for dtype_item in df.dtypes.items():
        # We know that the column names are strings from the isinstance check
        # further above but mypy thinks it is of type Hashable and therefore does not
        # let us assign it to the col_name variable which is already of type str.
        col_name = cast(str, dtype_item[0])
        dtype = dtype_item[1]
        dtype_name = str(dtype)
        if dtype_name == "category":
            # Work around bug in to_json for categorical types in older versions
            # of pandas as they do not properly convert NaN values to null in to_json.
            # We can probably remove this part once we require pandas >= 1.0
            col = df[col_name].astype(object)
            df[col_name] = col.where(col.notnull(), None)
        elif dtype_name == "string":
            # dedicated string datatype (since 1.0)
            # https://pandas.pydata.org/pandas-docs/version/1.0.0/whatsnew/v1.0.0.html#dedicated-string-data-type
            col = df[col_name].astype(object)
            df[col_name] = col.where(col.notnull(), None)
        elif dtype_name == "bool":
            # convert numpy bools to objects; np.bool is not JSON serializable
            df[col_name] = df[col_name].astype(object)
        elif dtype_name == "boolean":
            # dedicated boolean datatype (since 1.0)
            # https://pandas.io/docs/user_guide/boolean.html
            col = df[col_name].astype(object)
            df[col_name] = col.where(col.notnull(), None)
        elif dtype_name.startswith("datetime") or dtype_name.startswith("timestamp"):
            # Convert datetimes to strings. This needs to be a full ISO string
            # with time, which is why we cannot use ``col.astype(str)``.
            # This is because Javascript parses date-only times in UTC, but
            # parses full ISO-8601 dates as local time, and dates in Vega and
            # Vega-Lite are displayed in local time by default.
            # (see https://github.com/altair-viz/altair/issues/1027)
            df[col_name] = (
                df[col_name].apply(lambda x: x.isoformat()).replace("NaT", "")
            )
        elif dtype_name.startswith("timedelta"):
            raise ValueError(
                'Field "{col_name}" has type "{dtype}" which is '
                "not supported by Altair. Please convert to "
                "either a timestamp or a numerical value."
                "".format(col_name=col_name, dtype=dtype)
            )
        elif dtype_name.startswith("geometry"):
            # geopandas >=0.6.1 uses the dtype geometry. Continue here
            # otherwise it will give an error on np.issubdtype(dtype, np.integer)
            continue
        elif (
            dtype_name
            in {
                "Int8",
                "Int16",
                "Int32",
                "Int64",
                "UInt8",
                "UInt16",
                "UInt32",
                "UInt64",
                "Float32",
                "Float64",
            }
        ):  # nullable integer datatypes (since 24.0) and nullable float datatypes (since 1.2.0)
            # https://pandas.pydata.org/pandas-docs/version/0.25/whatsnew/v0.24.0.html#optional-integer-na-support
            col = df[col_name].astype(object)
            df[col_name] = col.where(col.notnull(), None)
        elif numpy_is_subtype(dtype, np.integer):
            # convert integers to objects; np.int is not JSON serializable
            df[col_name] = df[col_name].astype(object)
        elif numpy_is_subtype(dtype, np.floating):
            # For floats, convert to Python float: np.float is not JSON serializable
            # Also convert NaN/inf values to null, as they are not JSON serializable
            col = df[col_name]
            bad_values = col.isnull() | np.isinf(col)
            df[col_name] = col.astype(object).where(~bad_values, None)
        elif dtype == object:
            # Convert numpy arrays saved as objects to lists
            # Arrays are not JSON serializable
            col = df[col_name].astype(object).apply(to_list_if_array)
            df[col_name] = col.where(col.notnull(), None)
    return df


def sanitize_arrow_table(pa_table):
    """Sanitize arrow table for JSON serialization"""
    import pyarrow as pa
    import pyarrow.compute as pc

    arrays = []
    schema = pa_table.schema
    for name in schema.names:
        array = pa_table[name]
        dtype_name = str(schema.field(name).type)
        if dtype_name.startswith("timestamp") or dtype_name.startswith("date"):
            arrays.append(pc.strftime(array))
        elif dtype_name.startswith("duration"):
            raise ValueError(
                'Field "{col_name}" has type "{dtype}" which is '
                "not supported by Altair. Please convert to "
                "either a timestamp or a numerical value."
                "".format(col_name=name, dtype=dtype_name)
            )
        else:
            arrays.append(array)

    return pa.Table.from_arrays(arrays, names=schema.names)


def parse_shorthand(
    shorthand: Union[Dict[str, Any], str],
    data: Optional[Union[pd.DataFrame, DataFrameLike]] = None,
    parse_aggregates: bool = True,
    parse_window_ops: bool = False,
    parse_timeunits: bool = True,
    parse_types: bool = True,
) -> Dict[str, Any]:
    """General tool to parse shorthand values

    These are of the form:

    - "col_name"
    - "col_name:O"
    - "average(col_name)"
    - "average(col_name):O"

    Optionally, a dataframe may be supplied, from which the type
    will be inferred if not specified in the shorthand.

    Parameters
    ----------
    shorthand : dict or string
        The shorthand representation to be parsed
    data : DataFrame, optional
        If specified and of type DataFrame, then use these values to infer the
        column type if not provided by the shorthand.
    parse_aggregates : boolean
        If True (default), then parse aggregate functions within the shorthand.
    parse_window_ops : boolean
        If True then parse window operations within the shorthand (default:False)
    parse_timeunits : boolean
        If True (default), then parse timeUnits from within the shorthand
    parse_types : boolean
        If True (default), then parse typecodes within the shorthand

    Returns
    -------
    attrs : dict
        a dictionary of attributes extracted from the shorthand

    Examples
    --------
    >>> data = pd.DataFrame({'foo': ['A', 'B', 'A', 'B'],
    ...                      'bar': [1, 2, 3, 4]})

    >>> parse_shorthand('name') == {'field': 'name'}
    True

    >>> parse_shorthand('name:Q') == {'field': 'name', 'type': 'quantitative'}
    True

    >>> parse_shorthand('average(col)') == {'aggregate': 'average', 'field': 'col'}
    True

    >>> parse_shorthand('foo:O') == {'field': 'foo', 'type': 'ordinal'}
    True

    >>> parse_shorthand('min(foo):Q') == {'aggregate': 'min', 'field': 'foo', 'type': 'quantitative'}
    True

    >>> parse_shorthand('month(col)') == {'field': 'col', 'timeUnit': 'month', 'type': 'temporal'}
    True

    >>> parse_shorthand('year(col):O') == {'field': 'col', 'timeUnit': 'year', 'type': 'ordinal'}
    True

    >>> parse_shorthand('foo', data) == {'field': 'foo', 'type': 'nominal'}
    True

    >>> parse_shorthand('bar', data) == {'field': 'bar', 'type': 'quantitative'}
    True

    >>> parse_shorthand('bar:O', data) == {'field': 'bar', 'type': 'ordinal'}
    True

    >>> parse_shorthand('sum(bar)', data) == {'aggregate': 'sum', 'field': 'bar', 'type': 'quantitative'}
    True

    >>> parse_shorthand('count()', data) == {'aggregate': 'count', 'type': 'quantitative'}
    True
    """
    from altair.utils._importers import pyarrow_available

    if not shorthand:
        return {}

    valid_typecodes = list(TYPECODE_MAP) + list(INV_TYPECODE_MAP)

    units = {
        "field": "(?P<field>.*)",
        "type": "(?P<type>{})".format("|".join(valid_typecodes)),
        "agg_count": "(?P<aggregate>count)",
        "op_count": "(?P<op>count)",
        "aggregate": "(?P<aggregate>{})".format("|".join(AGGREGATES)),
        "window_op": "(?P<op>{})".format("|".join(AGGREGATES + WINDOW_AGGREGATES)),
        "timeUnit": "(?P<timeUnit>{})".format("|".join(TIMEUNITS)),
    }

    patterns = []

    if parse_aggregates:
        patterns.extend([r"{agg_count}\(\)"])
        patterns.extend([r"{aggregate}\({field}\)"])
    if parse_window_ops:
        patterns.extend([r"{op_count}\(\)"])
        patterns.extend([r"{window_op}\({field}\)"])
    if parse_timeunits:
        patterns.extend([r"{timeUnit}\({field}\)"])

    patterns.extend([r"{field}"])

    if parse_types:
        patterns = list(itertools.chain(*((p + ":{type}", p) for p in patterns)))

    regexps = (
        re.compile(r"\A" + p.format(**units) + r"\Z", re.DOTALL) for p in patterns
    )

    # find matches depending on valid fields passed
    if isinstance(shorthand, dict):
        attrs = shorthand
    else:
        attrs = next(
            exp.match(shorthand).groupdict()  # type: ignore[union-attr]
            for exp in regexps
            if exp.match(shorthand) is not None
        )

    # Handle short form of the type expression
    if "type" in attrs:
        attrs["type"] = INV_TYPECODE_MAP.get(attrs["type"], attrs["type"])

    # counts are quantitative by default
    if attrs == {"aggregate": "count"}:
        attrs["type"] = "quantitative"

    # times are temporal by default
    if "timeUnit" in attrs and "type" not in attrs:
        attrs["type"] = "temporal"

    # if data is specified and type is not, infer type from data
    if "type" not in attrs:
        if pyarrow_available() and data is not None and isinstance(data, DataFrameLike):
            dfi = data.__dataframe__()
            if "field" in attrs:
                unescaped_field = attrs["field"].replace("\\", "")
                if unescaped_field in dfi.column_names():
                    column = dfi.get_column_by_name(unescaped_field)
                    try:
                        attrs["type"] = infer_vegalite_type_for_dfi_column(column)
                    except (NotImplementedError, AttributeError, ValueError):
                        # Fall back to pandas-based inference.
                        # Note: The AttributeError catch is a workaround for
                        # https://github.com/pandas-dev/pandas/issues/55332
                        if isinstance(data, pd.DataFrame):
                            attrs["type"] = infer_vegalite_type(data[unescaped_field])
                        else:
                            raise

                    if isinstance(attrs["type"], tuple):
                        attrs["sort"] = attrs["type"][1]
                        attrs["type"] = attrs["type"][0]
        elif isinstance(data, pd.DataFrame):
            # Fallback if pyarrow is not installed or if pandas is older than 1.5
            #
            # Remove escape sequences so that types can be inferred for columns with special characters
            if "field" in attrs and attrs["field"].replace("\\", "") in data.columns:
                attrs["type"] = infer_vegalite_type(
                    data[attrs["field"].replace("\\", "")]
                )
                # ordered categorical dataframe columns return the type and sort order as a tuple
                if isinstance(attrs["type"], tuple):
                    attrs["sort"] = attrs["type"][1]
                    attrs["type"] = attrs["type"][0]

    # If an unescaped colon is still present, it's often due to an incorrect data type specification
    # but could also be due to using a column name with ":" in it.
    if (
        "field" in attrs
        and ":" in attrs["field"]
        and attrs["field"][attrs["field"].rfind(":") - 1] != "\\"
    ):
        raise ValueError(
            '"{}" '.format(attrs["field"].split(":")[-1])
            + "is not one of the valid encoding data types: {}.".format(
                ", ".join(TYPECODE_MAP.values())
            )
            + "\nFor more details, see https://altair-viz.github.io/user_guide/encodings/index.html#encoding-data-types. "
            + "If you are trying to use a column name that contains a colon, "
            + 'prefix it with a backslash; for example "column\\:name" instead of "column:name".'
        )
    return attrs


def infer_vegalite_type_for_dfi_column(
    column: Union[Column, "PandasColumn"],
) -> Union[InferredVegaLiteType, Tuple[InferredVegaLiteType, list]]:
    from pyarrow.interchange.from_dataframe import column_to_array

    try:
        kind = column.dtype[0]
    except NotImplementedError as e:
        # Edge case hack:
        # dtype access fails for pandas column with datetime64[ns, UTC] type,
        # but all we need to know is that its temporal, so check the
        # error message for the presence of datetime64.
        #
        # See https://github.com/pandas-dev/pandas/issues/54239
        if "datetime64" in e.args[0] or "timestamp" in e.args[0]:
            return "temporal"
        raise e

    if (
        kind == DtypeKind.CATEGORICAL
        and column.describe_categorical["is_ordered"]
        and column.describe_categorical["categories"] is not None
    ):
        # Treat ordered categorical column as Vega-Lite ordinal
        categories_column = column.describe_categorical["categories"]
        categories_array = column_to_array(categories_column)
        return "ordinal", categories_array.to_pylist()
    if kind in (DtypeKind.STRING, DtypeKind.CATEGORICAL, DtypeKind.BOOL):
        return "nominal"
    elif kind in (DtypeKind.INT, DtypeKind.UINT, DtypeKind.FLOAT):
        return "quantitative"
    elif kind == DtypeKind.DATETIME:
        return "temporal"
    else:
        raise ValueError(f"Unexpected DtypeKind: {kind}")


def use_signature(Obj: Callable[P, Any]):
    """Apply call signature and documentation of Obj to the decorated method"""

    def decorate(f: Callable[..., V]) -> Callable[P, V]:
        # call-signature of f is exposed via __wrapped__.
        # we want it to mimic Obj.__init__
        f.__wrapped__ = Obj.__init__  # type: ignore
        f._uses_signature = Obj  # type: ignore

        # Supplement the docstring of f with information from Obj
        if Obj.__doc__:
            # Patch in a reference to the class this docstring is copied from,
            # to generate a hyperlink.
            doclines = Obj.__doc__.splitlines()
            doclines[0] = f"Refer to :class:`{Obj.__name__}`"

            if f.__doc__:
                doc = f.__doc__ + "\n".join(doclines[1:])
            else:
                doc = "\n".join(doclines)
            try:
                f.__doc__ = doc
            except AttributeError:
                # __doc__ is not modifiable for classes in Python < 3.3
                pass

        return f

    return decorate


def update_nested(
    original: MutableMapping, update: Mapping, copy: bool = False
) -> MutableMapping:
    """Update nested dictionaries

    Parameters
    ----------
    original : MutableMapping
        the original (nested) dictionary, which will be updated in-place
    update : Mapping
        the nested dictionary of updates
    copy : bool, default False
        if True, then copy the original dictionary rather than modifying it

    Returns
    -------
    original : MutableMapping
        a reference to the (modified) original dict

    Examples
    --------
    >>> original = {'x': {'b': 2, 'c': 4}}
    >>> update = {'x': {'b': 5, 'd': 6}, 'y': 40}
    >>> update_nested(original, update)  # doctest: +SKIP
    {'x': {'b': 5, 'c': 4, 'd': 6}, 'y': 40}
    >>> original  # doctest: +SKIP
    {'x': {'b': 5, 'c': 4, 'd': 6}, 'y': 40}
    """
    if copy:
        original = deepcopy(original)
    for key, val in update.items():
        if isinstance(val, Mapping):
            orig_val = original.get(key, {})
            if isinstance(orig_val, MutableMapping):
                original[key] = update_nested(orig_val, val)
            else:
                original[key] = val
        else:
            original[key] = val
    return original


def display_traceback(in_ipython: bool = True):
    exc_info = sys.exc_info()

    if in_ipython:
        from IPython.core.getipython import get_ipython

        ip = get_ipython()
    else:
        ip = None

    if ip is not None:
        ip.showtraceback(exc_info)
    else:
        traceback.print_exception(*exc_info)


def infer_encoding_types(args: Sequence, kwargs: MutableMapping, channels: ModuleType):
    """Infer typed keyword arguments for args and kwargs

    Parameters
    ----------
    args : Sequence
        Sequence of function args
    kwargs : MutableMapping
        Dict of function kwargs
    channels : ModuleType
        The module containing all altair encoding channel classes.

    Returns
    -------
    kwargs : dict
        All args and kwargs in a single dict, with keys and types
        based on the channels mapping.
    """
    # Construct a dictionary of channel type to encoding name
    # TODO: cache this somehow?
    channel_objs = (getattr(channels, name) for name in dir(channels))
    channel_objs = (
        c for c in channel_objs if isinstance(c, type) and issubclass(c, SchemaBase)
    )
    channel_to_name: Dict[Type[SchemaBase], str] = {
        c: c._encoding_name for c in channel_objs
    }
    name_to_channel: Dict[str, Dict[str, Type[SchemaBase]]] = {}
    for chan, name in channel_to_name.items():
        chans = name_to_channel.setdefault(name, {})
        if chan.__name__.endswith("Datum"):
            key = "datum"
        elif chan.__name__.endswith("Value"):
            key = "value"
        else:
            key = "field"
        chans[key] = chan

    # First use the mapping to convert args to kwargs based on their types.
    for arg in args:
        if isinstance(arg, (list, tuple)) and len(arg) > 0:
            type_ = type(arg[0])
        else:
            type_ = type(arg)

        encoding = channel_to_name.get(type_, None)
        if encoding is None:
            raise NotImplementedError("positional of type {}" "".format(type_))
        if encoding in kwargs:
            raise ValueError("encoding {} specified twice.".format(encoding))
        kwargs[encoding] = arg

    def _wrap_in_channel_class(obj, encoding):
        if isinstance(obj, SchemaBase):
            return obj

        if isinstance(obj, str):
            obj = {"shorthand": obj}

        if isinstance(obj, (list, tuple)):
            return [_wrap_in_channel_class(subobj, encoding) for subobj in obj]

        if encoding not in name_to_channel:
            warnings.warn(
                "Unrecognized encoding channel '{}'".format(encoding), stacklevel=1
            )
            return obj

        classes = name_to_channel[encoding]
        cls = classes["value"] if "value" in obj else classes["field"]

        try:
            # Don't force validation here; some objects won't be valid until
            # they're created in the context of a chart.
            return cls.from_dict(obj, validate=False)
        except jsonschema.ValidationError:
            # our attempts at finding the correct class have failed
            return obj

    return {
        encoding: _wrap_in_channel_class(obj, encoding)
        for encoding, obj in kwargs.items()
    }
