import warnings

import hashlib
import io
import json
import jsonschema
import pandas as pd
from toolz.curried import pipe as _pipe
import itertools
import sys
from typing import cast, List, Optional, Any, Iterable, Union, Literal, IO

# Have to rename it here as else it overlaps with schema.core.Type and schema.core.Dict
from typing import Type as TypingType
from typing import Dict as TypingDict

from .schema import core, channels, mixins, Undefined, UndefinedType, SCHEMA_URL

from .data import data_transformers
from ... import utils, expr
from ...expr import core as _expr_core
from .display import renderers, VEGALITE_VERSION, VEGAEMBED_VERSION, VEGA_VERSION
from .theme import themes
from .compiler import vegalite_compilers
from ...utils._vegafusion_data import (
    using_vegafusion as _using_vegafusion,
    compile_with_vegafusion as _compile_with_vegafusion,
)
from ...utils.core import DataFrameLike
from ...utils.data import DataType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

ChartDataType = Union[DataType, core.Data, str, core.Generator, UndefinedType]


# ------------------------------------------------------------------------
# Data Utilities
def _dataset_name(values: Union[dict, list, core.InlineDataset]) -> str:
    """Generate a unique hash of the data

    Parameters
    ----------
    values : list, dict, core.InlineDataset
        A representation of data values.

    Returns
    -------
    name : string
        A unique name generated from the hash of the values.
    """
    if isinstance(values, core.InlineDataset):
        values = values.to_dict()
    if values == [{}]:
        return "empty"
    values_json = json.dumps(values, sort_keys=True, default=str)
    hsh = hashlib.sha256(values_json.encode()).hexdigest()[:32]
    return "data-" + hsh


def _consolidate_data(data, context):
    """If data is specified inline, then move it to context['datasets']

    This function will modify context in-place, and return a new version of data
    """
    values = Undefined
    kwds = {}

    if isinstance(data, core.InlineData):
        if data.name is Undefined and data.values is not Undefined:
            if isinstance(data.values, core.InlineDataset):
                values = data.to_dict()["values"]
            else:
                values = data.values
            kwds = {"format": data.format}

    elif isinstance(data, dict):
        if "name" not in data and "values" in data:
            values = data["values"]
            kwds = {k: v for k, v in data.items() if k != "values"}

    if values is not Undefined:
        name = _dataset_name(values)
        data = core.NamedData(name=name, **kwds)
        context.setdefault("datasets", {})[name] = values

    return data


def _prepare_data(data, context=None):
    """Convert input data to data for use within schema

    Parameters
    ----------
    data :
        The input dataset in the form of a DataFrame, dictionary, altair data
        object, or other type that is recognized by the data transformers.
    context : dict (optional)
        The to_dict context in which the data is being prepared. This is used
        to keep track of information that needs to be passed up and down the
        recursive serialization routine, such as global named datasets.
    """
    if data is Undefined:
        return data

    # convert dataframes  or objects with __geo_interface__ to dict
    elif isinstance(data, pd.DataFrame) or hasattr(data, "__geo_interface__"):
        data = _pipe(data, data_transformers.get())

    # convert string input to a URLData
    elif isinstance(data, str):
        data = core.UrlData(data)

    elif isinstance(data, DataFrameLike):
        data = _pipe(data, data_transformers.get())

    # consolidate inline data to top-level datasets
    if context is not None and data_transformers.consolidate_datasets:
        data = _consolidate_data(data, context)

    # if data is still not a recognized type, then return
    if not isinstance(data, (dict, core.Data)):
        warnings.warn("data of type {} not recognized".format(type(data)), stacklevel=1)

    return data


# ------------------------------------------------------------------------
# Aliases & specializations
Bin = core.BinParams
Impute = core.ImputeParams
Title = core.TitleParams


class LookupData(core.LookupData):
    @utils.use_signature(core.LookupData)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_dict(self, *args, **kwargs) -> dict:
        """Convert the chart to a dictionary suitable for JSON export."""
        copy = self.copy(deep=False)
        copy.data = _prepare_data(copy.data, kwargs.get("context"))
        return super(LookupData, copy).to_dict(*args, **kwargs)


class FacetMapping(core.FacetMapping):
    _class_is_valid_at_instantiation = False

    @utils.use_signature(core.FacetMapping)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_dict(self, *args, **kwargs) -> dict:
        copy = self.copy(deep=False)
        context = kwargs.get("context", {})
        data = context.get("data", None)
        if isinstance(self.row, str):
            copy.row = core.FacetFieldDef(**utils.parse_shorthand(self.row, data))
        if isinstance(self.column, str):
            copy.column = core.FacetFieldDef(**utils.parse_shorthand(self.column, data))
        return super(FacetMapping, copy).to_dict(*args, **kwargs)


# ------------------------------------------------------------------------
# Encoding will contain channel objects that aren't valid at instantiation
core.FacetedEncoding._class_is_valid_at_instantiation = False

# ------------------------------------------------------------------------
# These are parameters that are valid at the top level, but are not valid
# for specs that are within a composite chart
# (layer, hconcat, vconcat, facet, repeat)
TOPLEVEL_ONLY_KEYS = {"background", "config", "autosize", "padding", "$schema"}


def _get_channels_mapping() -> TypingDict[TypingType[core.SchemaBase], str]:
    mapping: TypingDict[TypingType[core.SchemaBase], str] = {}
    for attr in dir(channels):
        cls = getattr(channels, attr)
        if isinstance(cls, type) and issubclass(cls, core.SchemaBase):
            mapping[cls] = attr.replace("Value", "").lower()
    return mapping


# -------------------------------------------------------------------------
# Tools for working with parameters
class Parameter(_expr_core.OperatorMixin):
    """A Parameter object"""

    # NOTE: If you change this class, make sure that the protocol in
    # altair/vegalite/v5/schema/core.py is updated accordingly if needed.

    _counter: int = 0

    @classmethod
    def _get_name(cls) -> str:
        cls._counter += 1
        return f"param_{cls._counter}"

    def __init__(
        self,
        name: Optional[str] = None,
        empty: Union[bool, UndefinedType] = Undefined,
        param: Union[
            core.VariableParameter,
            core.TopLevelSelectionParameter,
            core.SelectionParameter,
            UndefinedType,
        ] = Undefined,
        param_type: Union[Literal["variable", "selection"], UndefinedType] = Undefined,
    ) -> None:
        if name is None:
            name = self._get_name()
        self.name = name
        self.empty = empty
        self.param = param
        self.param_type = param_type

    @utils.deprecation.deprecated(
        message="'ref' is deprecated. No need to call '.ref()' anymore."
    )
    def ref(self) -> dict:
        "'ref' is deprecated. No need to call '.ref()' anymore."
        return self.to_dict()

    def to_dict(self) -> TypingDict[str, Union[str, dict]]:
        if self.param_type == "variable":
            return {"expr": self.name}
        elif self.param_type == "selection":
            return {
                "param": self.name.to_dict()
                if hasattr(self.name, "to_dict")
                else self.name
            }
        else:
            raise ValueError(f"Unrecognized parameter type: {self.param_type}")

    def __invert__(self):
        if self.param_type == "selection":
            return SelectionPredicateComposition({"not": {"param": self.name}})
        else:
            return _expr_core.OperatorMixin.__invert__(self)

    def __and__(self, other):
        if self.param_type == "selection":
            if isinstance(other, Parameter):
                other = {"param": other.name}
            return SelectionPredicateComposition({"and": [{"param": self.name}, other]})
        else:
            return _expr_core.OperatorMixin.__and__(self, other)

    def __or__(self, other):
        if self.param_type == "selection":
            if isinstance(other, Parameter):
                other = {"param": other.name}
            return SelectionPredicateComposition({"or": [{"param": self.name}, other]})
        else:
            return _expr_core.OperatorMixin.__or__(self, other)

    def __repr__(self) -> str:
        return "Parameter({0!r}, {1})".format(self.name, self.param)

    def _to_expr(self) -> str:
        return self.name

    def _from_expr(self, expr) -> "ParameterExpression":
        return ParameterExpression(expr=expr)

    def __getattr__(
        self, field_name: str
    ) -> Union[_expr_core.GetAttrExpression, "SelectionExpression"]:
        if field_name.startswith("__") and field_name.endswith("__"):
            raise AttributeError(field_name)
        _attrexpr = _expr_core.GetAttrExpression(self.name, field_name)
        # If self is a SelectionParameter and field_name is in its
        # fields or encodings list, then we want to return an expression.
        if check_fields_and_encodings(self, field_name):
            return SelectionExpression(_attrexpr)
        return _expr_core.GetAttrExpression(self.name, field_name)

    # TODO: Are there any special cases to consider for __getitem__?
    # This was copied from v4.
    def __getitem__(self, field_name: str) -> _expr_core.GetItemExpression:
        return _expr_core.GetItemExpression(self.name, field_name)


# Enables use of ~, &, | with compositions of selection objects.
class SelectionPredicateComposition(core.PredicateComposition):
    def __invert__(self):
        return SelectionPredicateComposition({"not": self.to_dict()})

    def __and__(self, other):
        return SelectionPredicateComposition({"and": [self.to_dict(), other.to_dict()]})

    def __or__(self, other):
        return SelectionPredicateComposition({"or": [self.to_dict(), other.to_dict()]})


class ParameterExpression(_expr_core.OperatorMixin, object):
    def __init__(self, expr) -> None:
        self.expr = expr

    def to_dict(self) -> TypingDict[str, str]:
        return {"expr": repr(self.expr)}

    def _to_expr(self) -> str:
        return repr(self.expr)

    def _from_expr(self, expr) -> "ParameterExpression":
        return ParameterExpression(expr=expr)


class SelectionExpression(_expr_core.OperatorMixin, object):
    def __init__(self, expr) -> None:
        self.expr = expr

    def to_dict(self) -> TypingDict[str, str]:
        return {"expr": repr(self.expr)}

    def _to_expr(self) -> str:
        return repr(self.expr)

    def _from_expr(self, expr) -> "SelectionExpression":
        return SelectionExpression(expr=expr)


def check_fields_and_encodings(parameter: Parameter, field_name: str) -> bool:
    for prop in ["fields", "encodings"]:
        try:
            if field_name in getattr(parameter.param.select, prop):  # type: ignore[union-attr]
                return True
        except (AttributeError, TypeError):
            pass

    return False


# ------------------------------------------------------------------------
# Top-Level Functions


def value(value, **kwargs) -> dict:
    """Specify a value for use in an encoding"""
    return dict(value=value, **kwargs)


def param(
    name: Optional[str] = None,
    value: Union[Any, UndefinedType] = Undefined,
    bind: Union[core.Binding, UndefinedType] = Undefined,
    empty: Union[bool, UndefinedType] = Undefined,
    expr: Union[str, core.Expr, _expr_core.Expression, UndefinedType] = Undefined,
    **kwds,
) -> Parameter:
    """Create a named parameter.
    See https://altair-viz.github.io/user_guide/interactions.html for examples.
    Although both variable parameters and selection parameters can be created using
    this 'param' function, to create a selection parameter, it is recommended to use
    either 'selection_point' or 'selection_interval' instead.

    Parameters
    ----------
    name : string (optional)
        The name of the parameter. If not specified, a unique name will be
        created.
    value : any (optional)
        The default value of the parameter. If not specified, the parameter
        will be created without a default value.
    bind : :class:`Binding` (optional)
        Binds the parameter to an external input element such as a slider,
        selection list or radio button group.
    empty : boolean (optional)
        For selection parameters, the predicate of empty selections returns
        True by default. Override this behavior, by setting this property
        'empty=False'.
    expr : str, Expression (optional)
        An expression for the value of the parameter. This expression may
        include other parameters, in which case the parameter will
        automatically update in response to upstream parameter changes.
    **kwds :
        additional keywords will be used to construct a parameter.  If 'select'
        is among the keywords, then a selection parameter will be created.
        Otherwise, a variable parameter will be created.

    Returns
    -------
    parameter: Parameter
        The parameter object that can be used in chart creation.
    """
    parameter = Parameter(name)

    if empty is not Undefined:
        parameter.empty = empty
        if parameter.empty == "none":
            warnings.warn(
                """The value of 'empty' should be True or False.""",
                utils.AltairDeprecationWarning,
                stacklevel=1,
            )
            parameter.empty = False
        elif parameter.empty == "all":
            warnings.warn(
                """The value of 'empty' should be True or False.""",
                utils.AltairDeprecationWarning,
                stacklevel=1,
            )
            parameter.empty = True
        elif (parameter.empty is False) or (parameter.empty is True):
            pass
        else:
            raise ValueError("The value of 'empty' should be True or False.")

    if "init" in kwds:
        warnings.warn(
            """Use 'value' instead of 'init'.""",
            utils.AltairDeprecationWarning,
            stacklevel=1,
        )
        if value is Undefined:
            kwds["value"] = kwds.pop("init")
        else:
            # If both 'value' and 'init' are set, we ignore 'init'.
            kwds.pop("init")

    # ignore[arg-type] comment is needed because we can also pass _expr_core.Expression
    if "select" not in kwds:
        parameter.param = core.VariableParameter(
            name=parameter.name,
            bind=bind,
            value=value,
            expr=expr,
            **kwds,
        )
        parameter.param_type = "variable"
    elif "views" in kwds:
        parameter.param = core.TopLevelSelectionParameter(
            name=parameter.name, bind=bind, value=value, expr=expr, **kwds
        )
        parameter.param_type = "selection"
    else:
        parameter.param = core.SelectionParameter(
            name=parameter.name, bind=bind, value=value, expr=expr, **kwds
        )
        parameter.param_type = "selection"

    return parameter


def _selection(
    type: Union[Literal["interval", "point"], UndefinedType] = Undefined, **kwds
) -> Parameter:
    # We separate out the parameter keywords from the selection keywords
    param_kwds = {}

    for kwd in {"name", "bind", "value", "empty", "init", "views"}:
        if kwd in kwds:
            param_kwds[kwd] = kwds.pop(kwd)

    select: Union[core.IntervalSelectionConfig, core.PointSelectionConfig]
    if type == "interval":
        select = core.IntervalSelectionConfig(type=type, **kwds)
    elif type == "point":
        select = core.PointSelectionConfig(type=type, **kwds)
    elif type in ["single", "multi"]:
        select = core.PointSelectionConfig(type="point", **kwds)
        warnings.warn(
            """The types 'single' and 'multi' are now
        combined and should be specified using "selection_point()".""",
            utils.AltairDeprecationWarning,
            stacklevel=1,
        )
    else:
        raise ValueError("""'type' must be 'point' or 'interval'""")

    return param(select=select, **param_kwds)


@utils.deprecation.deprecated(
    message="""'selection' is deprecated.
   Use 'selection_point()' or 'selection_interval()' instead; these functions also include more helpful docstrings."""
)
def selection(
    type: Union[Literal["interval", "point"], UndefinedType] = Undefined, **kwds
) -> Parameter:
    """
    Users are recommended to use either 'selection_point' or 'selection_interval' instead, depending on the type of parameter they want to create.

    Create a selection parameter.

    Parameters
    ----------
    type : enum('point', 'interval') (required)
        Determines the default event processing and data query for the
        selection. Vega-Lite currently supports two selection types:
        * "point" - to select multiple discrete data values; the first
        value is selected on click and additional values toggled on
        shift-click.
        * "interval" - to select a continuous range of data values on
        drag.
    **kwds :
        additional keywords to control the selection.
    """

    return _selection(type=type, **kwds)


def selection_interval(
    name: Optional[str] = None,
    value: Union[Any, UndefinedType] = Undefined,
    bind: Union[core.Binding, str, UndefinedType] = Undefined,
    empty: Union[bool, UndefinedType] = Undefined,
    expr: Union[str, core.Expr, _expr_core.Expression, UndefinedType] = Undefined,
    encodings: Union[List[str], UndefinedType] = Undefined,
    on: Union[str, UndefinedType] = Undefined,
    clear: Union[str, bool, UndefinedType] = Undefined,
    resolve: Union[Literal["global", "union", "intersect"], UndefinedType] = Undefined,
    mark: Union[core.Mark, UndefinedType] = Undefined,
    translate: Union[str, bool, UndefinedType] = Undefined,
    zoom: Union[str, bool, UndefinedType] = Undefined,
    **kwds,
) -> Parameter:
    """Create an interval selection parameter. Selection parameters define data queries that are driven by direct manipulation from user input (e.g., mouse clicks or drags). Interval selection parameters are used to select a continuous range of data values on drag, whereas point selection parameters (`selection_point`) are used to select multiple discrete data values.)

    Parameters
    ----------
    name : string (optional)
        The name of the parameter. If not specified, a unique name will be
        created.
    value : any (optional)
        The default value of the parameter. If not specified, the parameter
        will be created without a default value.
    bind : :class:`Binding`, str (optional)
        Binds the parameter to an external input element such as a slider,
        selection list or radio button group.
    empty : boolean (optional)
        For selection parameters, the predicate of empty selections returns
        True by default. Override this behavior, by setting this property
        'empty=False'.
    expr : :class:`Expr` (optional)
        An expression for the value of the parameter. This expression may
        include other parameters, in which case the parameter will
        automatically update in response to upstream parameter changes.
    encodings : List[str] (optional)
        A list of encoding channels. The corresponding data field values
        must match for a data tuple to fall within the selection.
    on : string (optional)
        A Vega event stream (object or selector) that triggers the selection.
        For interval selections, the event stream must specify a start and end.
    clear : string or boolean (optional)
        Clears the selection, emptying it of all values. This property can
        be an Event Stream or False to disable clear.  Default is 'dblclick'.
    resolve : enum('global', 'union', 'intersect') (optional)
        With layered and multi-view displays, a strategy that determines
        how selections' data queries are resolved when applied in a filter
        transform, conditional encoding rule, or scale domain.
        One of:

        * 'global': only one brush exists for the entire SPLOM. When the
          user begins to drag, any previous brushes are cleared, and a
          new one is constructed.
        * 'union': each cell contains its own brush, and points are
          highlighted if they lie within any of these individual brushes.
        * 'intersect': each cell contains its own brush, and points are
          highlighted only if they fall within all of these individual
          brushes.

        The default is 'global'.
    mark : :class:`Mark` (optional)
        An interval selection also adds a rectangle mark to depict the
        extents of the interval. The mark property can be used to
        customize the appearance of the mark.
    translate : string or boolean (optional)
        When truthy, allows a user to interactively move an interval
        selection back-and-forth. Can be True, False (to disable panning),
        or a Vega event stream definition which must include a start and
        end event to trigger continuous panning. Discrete panning (e.g.,
        pressing the left/right arrow keys) will be supported in future
        versions.
        The default value is True, which corresponds to
        [pointerdown, window:pointerup] > window:pointermove!
        This default allows users to click and drag within an interval
        selection to reposition it.
    zoom : string or boolean (optional)
        When truthy, allows a user to interactively resize an interval
        selection. Can be True, False (to disable zooming), or a Vega
        event stream definition. Currently, only wheel events are supported,
        but custom event streams can still be used to specify filters,
        debouncing, and throttling. Future versions will expand the set of
        events that can trigger this transformation.
        The default value is True, which corresponds to wheel!. This
        default allows users to use the mouse wheel to resize an interval
        selection.
    **kwds :
        Additional keywords to control the selection.

    Returns
    -------
    parameter: Parameter
        The parameter object that can be used in chart creation.
    """
    return _selection(
        type="interval",
        name=name,
        value=value,
        bind=bind,
        empty=empty,
        expr=expr,
        encodings=encodings,
        on=on,
        clear=clear,
        resolve=resolve,
        mark=mark,
        translate=translate,
        zoom=zoom,
        **kwds,
    )


def selection_point(
    name: Optional[str] = None,
    value: Union[Any, UndefinedType] = Undefined,
    bind: Union[core.Binding, str, UndefinedType] = Undefined,
    empty: Union[bool, UndefinedType] = Undefined,
    expr: Union[core.Expr, UndefinedType] = Undefined,
    encodings: Union[List[str], UndefinedType] = Undefined,
    fields: Union[List[str], UndefinedType] = Undefined,
    on: Union[str, UndefinedType] = Undefined,
    clear: Union[str, bool, UndefinedType] = Undefined,
    resolve: Union[Literal["global", "union", "intersect"], UndefinedType] = Undefined,
    toggle: Union[str, bool, UndefinedType] = Undefined,
    nearest: Union[bool, UndefinedType] = Undefined,
    **kwds,
) -> Parameter:
    """Create a point selection parameter. Selection parameters define data queries that are driven by direct manipulation from user input (e.g., mouse clicks or drags). Point selection parameters are used to select multiple discrete data values; the first value is selected on click and additional values toggled on shift-click. To select a continuous range of data values on drag interval selection parameters (`selection_interval`) can be used instead.

    Parameters
    ----------
    name : string (optional)
        The name of the parameter. If not specified, a unique name will be
        created.
    value : any (optional)
        The default value of the parameter. If not specified, the parameter
        will be created without a default value.
    bind : :class:`Binding`, str (optional)
        Binds the parameter to an external input element such as a slider,
        selection list or radio button group.
    empty : boolean (optional)
        For selection parameters, the predicate of empty selections returns
        True by default. Override this behavior, by setting this property
        'empty=False'.
    expr : :class:`Expr` (optional)
        An expression for the value of the parameter. This expression may
        include other parameters, in which case the parameter will
        automatically update in response to upstream parameter changes.
    encodings : List[str] (optional)
        A list of encoding channels. The corresponding data field values
        must match for a data tuple to fall within the selection.
    fields : List[str] (optional)
        A list of field names whose values must match for a data tuple to
        fall within the selection.
    on : string (optional)
        A Vega event stream (object or selector) that triggers the selection.
        For interval selections, the event stream must specify a start and end.
    clear : string or boolean (optional)
        Clears the selection, emptying it of all values. This property can
        be an Event Stream or False to disable clear.  Default is 'dblclick'.
    resolve : enum('global', 'union', 'intersect') (optional)
        With layered and multi-view displays, a strategy that determines
        how selections' data queries are resolved when applied in a filter
        transform, conditional encoding rule, or scale domain.
        One of:

        * 'global': only one brush exists for the entire SPLOM. When the
          user begins to drag, any previous brushes are cleared, and a
          new one is constructed.
        * 'union': each cell contains its own brush, and points are
          highlighted if they lie within any of these individual brushes.
        * 'intersect': each cell contains its own brush, and points are
          highlighted only if they fall within all of these individual
          brushes.

        The default is 'global'.
    toggle : string or boolean (optional)
        Controls whether data values should be toggled (inserted or
        removed from a point selection) or only ever inserted into
        point selections.
        One of:

        * True (default): the toggle behavior, which corresponds to
          "event.shiftKey". As a result, data values are toggled
          when the user interacts with the shift-key pressed.
        * False: disables toggling behaviour; the selection will
          only ever contain a single data value corresponding
          to the most recent interaction.
        * A Vega expression which is re-evaluated as the user interacts.
          If the expression evaluates to True, the data value is
          toggled into or out of the point selection. If the expression
          evaluates to False, the point selection is first cleared, and
          the data value is then inserted. For example, setting the
          value to the Vega expression True will toggle data values
          without the user pressing the shift-key.

    nearest : boolean (optional)
        When true, an invisible voronoi diagram is computed to accelerate
        discrete selection. The data value nearest the mouse cursor is
        added to the selection.  The default is False, which means that
        data values must be interacted with directly (e.g., clicked on)
        to be added to the selection.
    **kwds :
        Additional keywords to control the selection.

    Returns
    -------
    parameter: Parameter
        The parameter object that can be used in chart creation.
    """
    return _selection(
        type="point",
        name=name,
        value=value,
        bind=bind,
        empty=empty,
        expr=expr,
        encodings=encodings,
        fields=fields,
        on=on,
        clear=clear,
        resolve=resolve,
        toggle=toggle,
        nearest=nearest,
        **kwds,
    )


@utils.deprecation.deprecated(
    message="'selection_multi' is deprecated.  Use 'selection_point'"
)
@utils.use_signature(core.PointSelectionConfig)
def selection_multi(**kwargs):
    """'selection_multi' is deprecated.  Use 'selection_point'"""
    return _selection(type="point", **kwargs)


@utils.deprecation.deprecated(
    message="'selection_single' is deprecated.  Use 'selection_point'"
)
@utils.use_signature(core.PointSelectionConfig)
def selection_single(**kwargs):
    """'selection_single' is deprecated.  Use 'selection_point'"""
    return _selection(type="point", **kwargs)


@utils.use_signature(core.Binding)
def binding(input, **kwargs):
    """A generic binding"""
    return core.Binding(input=input, **kwargs)


@utils.use_signature(core.BindCheckbox)
def binding_checkbox(**kwargs):
    """A checkbox binding"""
    return core.BindCheckbox(input="checkbox", **kwargs)


@utils.use_signature(core.BindRadioSelect)
def binding_radio(**kwargs):
    """A radio button binding"""
    return core.BindRadioSelect(input="radio", **kwargs)


@utils.use_signature(core.BindRadioSelect)
def binding_select(**kwargs):
    """A select binding"""
    return core.BindRadioSelect(input="select", **kwargs)


@utils.use_signature(core.BindRange)
def binding_range(**kwargs):
    """A range binding"""
    return core.BindRange(input="range", **kwargs)


# TODO: update the docstring
def condition(
    predicate: Union[
        Parameter, str, expr.Expression, core.Expr, core.PredicateComposition, dict
    ],
    # Types of these depends on where the condition is used so we probably
    # can't be more specific here.
    if_true: Any,
    if_false: Any,
    **kwargs,
) -> Union[dict, core.SchemaBase]:
    """A conditional attribute or encoding

    Parameters
    ----------
    predicate: Parameter, PredicateComposition, expr.Expression, dict, or string
        the selection predicate or test predicate for the condition.
        if a string is passed, it will be treated as a test operand.
    if_true:
        the spec or object to use if the selection predicate is true
    if_false:
        the spec or object to use if the selection predicate is false
    **kwargs:
        additional keyword args are added to the resulting dict

    Returns
    -------
    spec: dict or VegaLiteSchema
        the spec that describes the condition
    """
    test_predicates = (str, expr.Expression, core.PredicateComposition)

    condition: TypingDict[
        str,
        Union[
            bool, str, _expr_core.Expression, core.PredicateComposition, UndefinedType
        ],
    ]
    if isinstance(predicate, Parameter):
        if (
            predicate.param_type == "selection"
            or getattr(predicate.param, "expr", Undefined) is Undefined
        ):
            condition = {"param": predicate.name}
            if "empty" in kwargs:
                condition["empty"] = kwargs.pop("empty")
            elif isinstance(predicate.empty, bool):
                condition["empty"] = predicate.empty
        else:
            condition = {"test": getattr(predicate.param, "expr", Undefined)}
    elif isinstance(predicate, test_predicates):
        condition = {"test": predicate}
    elif isinstance(predicate, dict):
        condition = predicate
    else:
        raise NotImplementedError(
            "condition predicate of type {}" "".format(type(predicate))
        )

    if isinstance(if_true, core.SchemaBase):
        # convert to dict for now; the from_dict call below will wrap this
        # dict in the appropriate schema
        if_true = if_true.to_dict()
    elif isinstance(if_true, str):
        if isinstance(if_false, str):
            raise ValueError(
                "A field cannot be used for both the `if_true` and `if_false` values of a condition. One of them has to specify a `value` or `datum` definition."
            )
        else:
            if_true = utils.parse_shorthand(if_true)
            if_true.update(kwargs)
    condition.update(if_true)

    selection: Union[dict, core.SchemaBase]
    if isinstance(if_false, core.SchemaBase):
        # For the selection, the channel definitions all allow selections
        # already. So use this SchemaBase wrapper if possible.
        selection = if_false.copy()
        selection.condition = condition
    elif isinstance(if_false, str):
        selection = {"condition": condition, "shorthand": if_false}
        selection.update(kwargs)
    else:
        selection = dict(condition=condition, **if_false)

    return selection


# --------------------------------------------------------------------
# Top-level objects


class TopLevelMixin(mixins.ConfigMethodMixin):
    """Mixin for top-level chart objects such as Chart, LayeredChart, etc."""

    _class_is_valid_at_instantiation: bool = False

    def to_dict(
        self,
        validate: bool = True,
        *,
        format: str = "vega-lite",
        ignore: Optional[List[str]] = None,
        context: Optional[TypingDict[str, Any]] = None,
    ) -> dict:
        """Convert the chart to a dictionary suitable for JSON export

        Parameters
        ----------
        validate : bool, optional
            If True (default), then validate the output dictionary
            against the schema.
        format : str, optional
            Chart specification format, one of "vega-lite" (default) or "vega"
        ignore : list[str], optional
            A list of keys to ignore. It is usually not needed
            to specify this argument as a user.
        context : dict[str, Any], optional
            A context dictionary. It is usually not needed
            to specify this argument as a user.

        Notes
        -----
        Technical: The ignore parameter will *not* be passed to child to_dict
        function calls.

        Returns
        -------
        dict
            The dictionary representation of this chart

        Raises
        ------
        SchemaValidationError
            if validate=True and the dict does not conform to the schema
        """

        # Validate format
        if format not in ("vega-lite", "vega"):
            raise ValueError(
                f'The format argument must be either "vega-lite" or "vega". Received {repr(format)}'
            )

        # We make use of three context markers:
        # - 'data' points to the data that should be referenced for column type
        #   inference.
        # - 'top_level' is a boolean flag that is assumed to be true; if it's
        #   true then a "$schema" arg is added to the dict.
        # - 'datasets' is a dict of named datasets that should be inserted
        #   in the top-level object
        # - 'pre_transform' whether data transformations should be pre-evaluated
        #   if the current data transformer supports it (currently only used when
        #   the "vegafusion" transformer is enabled)

        # note: not a deep copy because we want datasets and data arguments to
        # be passed by reference
        context = context.copy() if context else {}
        context.setdefault("datasets", {})
        is_top_level = context.get("top_level", True)

        # TopLevelMixin instance does not necessarily have copy defined but due to how
        # Altair is set up this should hold. Too complex to type hint right now
        copy = self.copy(deep=False)  # type: ignore[attr-defined]
        original_data = getattr(copy, "data", Undefined)
        copy.data = _prepare_data(original_data, context)

        if original_data is not Undefined:
            context["data"] = original_data

        # remaining to_dict calls are not at top level
        context["top_level"] = False

        # TopLevelMixin instance does not necessarily have to_dict defined
        # but due to how Altair is set up this should hold.
        # Too complex to type hint right now
        vegalite_spec = super(TopLevelMixin, copy).to_dict(  # type: ignore[misc]
            validate=validate, ignore=ignore, context=dict(context, pre_transform=False)
        )

        # TODO: following entries are added after validation. Should they be validated?
        if is_top_level:
            # since this is top-level we add $schema if it's missing
            if "$schema" not in vegalite_spec:
                vegalite_spec["$schema"] = SCHEMA_URL

            # apply theme from theme registry
            the_theme = themes.get()
            # Use assert to tell type checkers that it is not None. Holds true
            # as there is always a default theme set when importing Altair
            assert the_theme is not None
            vegalite_spec = utils.update_nested(the_theme(), vegalite_spec, copy=True)

            # update datasets
            if context["datasets"]:
                vegalite_spec.setdefault("datasets", {}).update(context["datasets"])

        if context.get("pre_transform", True) and _using_vegafusion():
            if format == "vega-lite":
                raise ValueError(
                    'When the "vegafusion" data transformer is enabled, the \n'
                    "to_dict() and to_json() chart methods must be called with "
                    'format="vega". \n'
                    "For example: \n"
                    '    >>> chart.to_dict(format="vega")\n'
                    '    >>> chart.to_json(format="vega")'
                )
            else:
                return _compile_with_vegafusion(vegalite_spec)
        else:
            if format == "vega":
                plugin = vegalite_compilers.get()
                if plugin is None:
                    raise ValueError("No active vega-lite compiler plugin found")
                return plugin(vegalite_spec)
            else:
                return vegalite_spec

    def to_json(
        self,
        validate: bool = True,
        indent: Optional[Union[int, str]] = 2,
        sort_keys: bool = True,
        *,
        format: str = "vega-lite",
        ignore: Optional[List[str]] = None,
        context: Optional[TypingDict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """Convert a chart to a JSON string

        Parameters
        ----------
        validate : bool, optional
            If True (default), then validate the output dictionary
            against the schema.
        indent : int, optional
            The number of spaces of indentation to use. The default is 2.
        sort_keys : bool, optional
            If True (default), sort keys in the output.
        format : str, optional
            The chart specification format. One of "vega-lite" (default) or "vega".
            The "vega" format relies on the active Vega-Lite compiler plugin, which
            by default requires the vl-convert-python package.
        ignore : list[str], optional
            A list of keys to ignore. It is usually not needed
            to specify this argument as a user.
        context : dict[str, Any], optional
            A context dictionary. It is usually not needed
            to specify this argument as a user.
        **kwargs
            Additional keyword arguments are passed to ``json.dumps()``
        """
        if ignore is None:
            ignore = []
        if context is None:
            context = {}
        spec = self.to_dict(
            validate=validate, format=format, ignore=ignore, context=context
        )
        return json.dumps(spec, indent=indent, sort_keys=sort_keys, **kwargs)

    def to_html(
        self,
        base_url: str = "https://cdn.jsdelivr.net/npm",
        output_div: str = "vis",
        embed_options: Optional[dict] = None,
        json_kwds: Optional[dict] = None,
        fullhtml: bool = True,
        requirejs: bool = False,
        inline: bool = False,
        **kwargs,
    ) -> str:
        """Embed a Vega/Vega-Lite spec into an HTML page

        Parameters
        ----------
        base_url : string (optional)
            The base url from which to load the javascript libraries.
        output_div : string (optional)
            The id of the div element where the plot will be shown.
        embed_options : dict (optional)
            Dictionary of options to pass to the vega-embed script. Default
            entry is {'mode': mode}.
        json_kwds : dict (optional)
            Dictionary of keywords to pass to json.dumps().
        fullhtml : boolean (optional)
            If True (default) then return a full html page. If False, then return
            an HTML snippet that can be embedded into an HTML page.
        requirejs : boolean (optional)
            If False (default) then load libraries from base_url using <script>
            tags. If True, then load libraries using requirejs
        inline: bool (optional)
            If False (default), the required JavaScript libraries are loaded
            from a CDN location in the resulting html file.
            If True, the required JavaScript libraries are inlined into the resulting
            html file so that it will work without an internet connection.
            The vl-convert-python package is required if True.
        **kwargs :
            additional kwargs passed to spec_to_html.
        Returns
        -------
        output : string
            an HTML string for rendering the chart.
        """
        if inline:
            kwargs["template"] = "inline"
        return utils.spec_to_html(
            self.to_dict(),
            mode="vega-lite",
            vegalite_version=VEGALITE_VERSION,
            vegaembed_version=VEGAEMBED_VERSION,
            vega_version=VEGA_VERSION,
            base_url=base_url,
            output_div=output_div,
            embed_options=embed_options,
            json_kwds=json_kwds,
            fullhtml=fullhtml,
            requirejs=requirejs,
            **kwargs,
        )

    def to_url(self, *, fullscreen: bool = False) -> str:
        """Convert a chart to a URL that opens the chart specification in the Vega chart editor
        The chart specification (including any inline data) is encoded in the URL.

        This method requires that the vl-convert-python package is installed.

        Parameters
        ----------
        fullscreen : bool
            If True, editor will open chart in fullscreen mode. Default False
        """
        from ...utils._importers import import_vl_convert

        vlc = import_vl_convert()
        if _using_vegafusion():
            return vlc.vega_to_url(self.to_dict(format="vega"), fullscreen=fullscreen)
        else:
            return vlc.vegalite_to_url(self.to_dict(), fullscreen=fullscreen)

    def open_editor(self, *, fullscreen: bool = False) -> None:
        """Opens the chart specification in the Vega chart editor using the default browser.

        Parameters
        ----------
        fullscreen : bool
            If True, editor will open chart in fullscreen mode. Default False
        """
        import webbrowser

        webbrowser.open(self.to_url(fullscreen=fullscreen))

    def save(
        self,
        fp: Union[str, IO],
        format: Optional[Literal["json", "html", "png", "svg", "pdf"]] = None,
        override_data_transformer: bool = True,
        scale_factor: float = 1.0,
        mode: Optional[str] = None,
        vegalite_version: str = VEGALITE_VERSION,
        vega_version: str = VEGA_VERSION,
        vegaembed_version: str = VEGAEMBED_VERSION,
        embed_options: Optional[dict] = None,
        json_kwds: Optional[dict] = None,
        webdriver: Optional[str] = None,
        engine: Optional[str] = None,
        inline=False,
        **kwargs,
    ) -> None:
        """Save a chart to file in a variety of formats

        Supported formats are json, html, png, svg, pdf; the last three require
        the altair_saver package to be installed.

        Parameters
        ----------
        fp : string filename or file-like object
            file in which to write the chart.
        format : string (optional)
            the format to write: one of ['json', 'html', 'png', 'svg', 'pdf'].
            If not specified, the format will be determined from the filename.
        override_data_transformer : `boolean` (optional)
            If True (default), then the save action will be done with
            the MaxRowsError disabled. If False, then do not change the data
            transformer.
        scale_factor : float (optional)
            scale_factor to use to change size/resolution of png or svg output
        mode : string (optional)
            Must be 'vega-lite'. If not specified, then infer the mode from
            the '$schema' property of the spec, or the ``opt`` dictionary.
            If it's not specified in either of those places, then use 'vega-lite'.
        vegalite_version : string (optional)
            For html output, the version of vegalite.js to use
        vega_version : string (optional)
            For html output, the version of vega.js to use
        vegaembed_version : string (optional)
            For html output, the version of vegaembed.js to use
        embed_options : dict (optional)
            The vegaEmbed options dictionary. Default is {}
            (See https://github.com/vega/vega-embed for details)
        json_kwds : dict (optional)
            Additional keyword arguments are passed to the output method
            associated with the specified format.
        webdriver : string {'chrome' | 'firefox'} (optional)
            Webdriver to use for png, svg, or pdf output when using altair_saver engine
        engine: string {'vl-convert', 'altair_saver'}
            the conversion engine to use for 'png', 'svg', and 'pdf' formats
        inline: bool (optional)
            If False (default), the required JavaScript libraries are loaded
            from a CDN location in the resulting html file.
            If True, the required JavaScript libraries are inlined into the resulting
            html file so that it will work without an internet connection.
            The vl-convert-python package is required if True.
        **kwargs :
            additional kwargs passed to spec_to_mimebundle.
        """
        from ...utils.save import save

        kwds = dict(
            chart=self,
            fp=fp,
            format=format,
            scale_factor=scale_factor,
            mode=mode,
            vegalite_version=vegalite_version,
            vega_version=vega_version,
            vegaembed_version=vegaembed_version,
            embed_options=embed_options,
            json_kwds=json_kwds,
            webdriver=webdriver,
            engine=engine,
            inline=inline,
            **kwargs,
        )

        # By default we override the data transformer. This makes it so
        # that save() will succeed even for large datasets that would
        # normally trigger a MaxRowsError
        if override_data_transformer:
            with data_transformers.disable_max_rows():
                save(**kwds)
        else:
            save(**kwds)
        return

    # Fallback for when rendering fails; the full repr is too long to be
    # useful in nearly all cases.
    def __repr__(self) -> str:
        return "alt.{}(...)".format(self.__class__.__name__)

    # Layering and stacking
    def __add__(self, other) -> "LayerChart":
        if not isinstance(other, TopLevelMixin):
            raise ValueError("Only Chart objects can be layered.")
        return layer(self, other)

    def __and__(self, other) -> "VConcatChart":
        if not isinstance(other, TopLevelMixin):
            raise ValueError("Only Chart objects can be concatenated.")
        # Too difficult to type check this
        return vconcat(self, other)

    def __or__(self, other) -> "HConcatChart":
        if not isinstance(other, TopLevelMixin):
            raise ValueError("Only Chart objects can be concatenated.")
        return hconcat(self, other)

    def repeat(
        self,
        repeat: Union[List[str], UndefinedType] = Undefined,
        row: Union[List[str], UndefinedType] = Undefined,
        column: Union[List[str], UndefinedType] = Undefined,
        layer: Union[List[str], UndefinedType] = Undefined,
        columns: Union[int, UndefinedType] = Undefined,
        **kwargs,
    ) -> "RepeatChart":
        """Return a RepeatChart built from the chart

        Fields within the chart can be set to correspond to the row or
        column using `alt.repeat('row')` and `alt.repeat('column')`.

        Parameters
        ----------
        repeat : list
            a list of data column names to be repeated. This cannot be
            used along with the ``row``, ``column`` or ``layer`` argument.
        row : list
            a list of data column names to be mapped to the row facet
        column : list
            a list of data column names to be mapped to the column facet
        layer : list
            a list of data column names to be layered. This cannot be
            used along with the ``row``, ``column`` or ``repeat`` argument.
        columns : int
            the maximum number of columns before wrapping. Only referenced
            if ``repeat`` is specified.
        **kwargs :
            additional keywords passed to RepeatChart.

        Returns
        -------
        chart : RepeatChart
            a repeated chart.
        """
        repeat_specified = repeat is not Undefined
        rowcol_specified = row is not Undefined or column is not Undefined
        layer_specified = layer is not Undefined

        if repeat_specified and rowcol_specified:
            raise ValueError(
                "repeat argument cannot be combined with row/column argument."
            )
        elif repeat_specified and layer_specified:
            raise ValueError("repeat argument cannot be combined with layer argument.")

        repeat_arg: Union[List[str], core.LayerRepeatMapping, core.RepeatMapping]
        if repeat_specified:
            assert not isinstance(repeat, UndefinedType)  # For mypy
            repeat_arg = repeat
        elif layer_specified:
            repeat_arg = core.LayerRepeatMapping(layer=layer, row=row, column=column)
        else:
            repeat_arg = core.RepeatMapping(row=row, column=column)

        return RepeatChart(spec=self, repeat=repeat_arg, columns=columns, **kwargs)

    def properties(self, **kwargs) -> Self:
        """Set top-level properties of the Chart.

        Argument names and types are the same as class initialization.
        """
        # ignore type as copy comes from another class for subclasses of TopLevelMixin
        copy = self.copy(deep=False)  # type: ignore[attr-defined]
        for key, val in kwargs.items():
            if key == "selection" and isinstance(val, Parameter):
                # TODO: Can this be removed
                # For backward compatibility with old selection interface.
                setattr(copy, key, {val.name: val.selection})
            else:
                # Don't validate data, because it hasn't been processed.
                if key != "data":
                    # ignore type as validate_property comes from SchemaBase,
                    # not from TopLevelMixin
                    self.validate_property(key, val)  # type: ignore[attr-defined]
                setattr(copy, key, val)
        return copy

    def project(
        self,
        type: Union[
            str, core.ProjectionType, core.ExprRef, Parameter, UndefinedType
        ] = Undefined,
        center: Union[
            List[float], core.Vector2number, core.ExprRef, Parameter, UndefinedType
        ] = Undefined,
        clipAngle: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        clipExtent: Union[
            List[List[float]],
            core.Vector2Vector2number,
            core.ExprRef,
            Parameter,
            UndefinedType,
        ] = Undefined,
        coefficient: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        distance: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        fraction: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        lobes: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        parallel: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        precision: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        radius: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        ratio: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        reflectX: Union[bool, core.ExprRef, Parameter, UndefinedType] = Undefined,
        reflectY: Union[bool, core.ExprRef, Parameter, UndefinedType] = Undefined,
        rotate: Union[
            List[float],
            core.Vector2number,
            core.Vector3number,
            core.ExprRef,
            Parameter,
            UndefinedType,
        ] = Undefined,
        scale: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        spacing: Union[
            float, core.Vector2number, core.ExprRef, Parameter, UndefinedType
        ] = Undefined,
        tilt: Union[float, core.ExprRef, Parameter, UndefinedType] = Undefined,
        translate: Union[
            List[float], core.Vector2number, core.ExprRef, Parameter, UndefinedType
        ] = Undefined,
        **kwds,
    ) -> Self:
        """Add a geographic projection to the chart.

        This is generally used either with ``mark_geoshape`` or with the
        ``latitude``/``longitude`` encodings.

        Available projection types are
        ['albers', 'albersUsa', 'azimuthalEqualArea', 'azimuthalEquidistant',
        'conicConformal', 'conicEqualArea', 'conicEquidistant', 'equalEarth', 'equirectangular',
        'gnomonic', 'identity', 'mercator', 'orthographic', 'stereographic', 'transverseMercator']

        Parameters
        ----------
        type : str
            The cartographic projection to use. This value is case-insensitive, for example
            `"albers"` and `"Albers"` indicate the same projection type. You can find all valid
            projection types [in the
            documentation](https://vega.github.io/vega-lite/docs/projection.html#projection-types).

            **Default value:** `equalEarth`
        center : List(float)
            Sets the projection’s center to the specified center, a two-element array of
            longitude and latitude in degrees.

            **Default value:** `[0, 0]`
        clipAngle : float
            Sets the projection’s clipping circle radius to the specified angle in degrees. If
            `null`, switches to [antimeridian](http://bl.ocks.org/mbostock/3788999) cutting
            rather than small-circle clipping.
        clipExtent : List(List(float))
            Sets the projection’s viewport clip extent to the specified bounds in pixels. The
            extent bounds are specified as an array `[[x0, y0], [x1, y1]]`, where `x0` is the
            left-side of the viewport, `y0` is the top, `x1` is the right and `y1` is the
            bottom. If `null`, no viewport clipping is performed.
        coefficient : float
            The coefficient parameter for the ``hammer`` projection.

            **Default value:** ``2``
        distance : float
            For the ``satellite`` projection, the distance from the center of the sphere to the
            point of view, as a proportion of the sphere’s radius. The recommended maximum clip
            angle for a given ``distance`` is acos(1 / distance) converted to degrees. If tilt
            is also applied, then more conservative clipping may be necessary.

            **Default value:** ``2.0``
        fraction : float
            The fraction parameter for the ``bottomley`` projection.

            **Default value:** ``0.5``, corresponding to a sin(ψ) where ψ = π/6.
        lobes : float
            The number of lobes in projections that support multi-lobe views: ``berghaus``,
            ``gingery``, or ``healpix``. The default value varies based on the projection type.
        parallel : float
            For conic projections, the `two standard parallels
            <https://en.wikipedia.org/wiki/Map_projection#Conic>`__ that define the map layout.
            The default depends on the specific conic projection used.
        precision : float
            Sets the threshold for the projection’s [adaptive
            resampling](http://bl.ocks.org/mbostock/3795544) to the specified value in pixels.
            This value corresponds to the [Douglas–Peucker
            distance](http://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm).
             If precision is not specified, returns the projection’s current resampling
            precision which defaults to `√0.5 ≅ 0.70710…`.
        radius : float
            The radius parameter for the ``airy`` or ``gingery`` projection. The default value
            varies based on the projection type.
        ratio : float
            The ratio parameter for the ``hill``, ``hufnagel``, or ``wagner`` projections. The
            default value varies based on the projection type.
        reflectX : boolean
            Sets whether or not the x-dimension is reflected (negated) in the output.
        reflectY : boolean
            Sets whether or not the y-dimension is reflected (negated) in the output.
        rotate : List(float)
            Sets the projection’s three-axis rotation to the specified angles, which must be a
            two- or three-element array of numbers [`lambda`, `phi`, `gamma`] specifying the
            rotation angles in degrees about each spherical axis. (These correspond to yaw,
            pitch and roll.)

            **Default value:** `[0, 0, 0]`
        scale : float
            The projection’s scale (zoom) factor, overriding automatic fitting. The default
            scale is projection-specific. The scale factor corresponds linearly to the distance
            between projected points; however, scale factor values are not equivalent across
            projections.
        spacing : float
            The spacing parameter for the ``lagrange`` projection.

            **Default value:** ``0.5``
        tilt : float
            The tilt angle (in degrees) for the ``satellite`` projection.

            **Default value:** ``0``.
        translate : List(float)
            The projection’s translation offset as a two-element array ``[tx, ty]``,
            overriding automatic fitting.

        """
        projection = core.Projection(
            center=center,
            clipAngle=clipAngle,
            clipExtent=clipExtent,
            coefficient=coefficient,
            distance=distance,
            fraction=fraction,
            lobes=lobes,
            parallel=parallel,
            precision=precision,
            radius=radius,
            ratio=ratio,
            reflectX=reflectX,
            reflectY=reflectY,
            rotate=rotate,
            scale=scale,
            spacing=spacing,
            tilt=tilt,
            translate=translate,
            # Ignore as we type here `type` as a str but in core.Projection
            # it's a Literal with all options
            type=type,  # type: ignore[arg-type]
            **kwds,
        )
        return self.properties(projection=projection)

    def _add_transform(self, *transforms: core.Transform) -> Self:
        """Copy the chart and add specified transforms to chart.transform"""
        copy = self.copy(deep=["transform"])  # type: ignore[attr-defined]
        if copy.transform is Undefined:
            copy.transform = []
        copy.transform.extend(transforms)
        return copy

    def transform_aggregate(
        self,
        aggregate: Union[List[core.AggregatedFieldDef], UndefinedType] = Undefined,
        groupby: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        **kwds: Union[TypingDict[str, Any], str],
    ) -> Self:
        """
        Add an :class:`AggregateTransform` to the schema.

        Parameters
        ----------
        aggregate : List(:class:`AggregatedFieldDef`)
            Array of objects that define fields to aggregate.
        groupby : List(string)
            The data fields to group by. If not specified, a single group containing all data
            objects will be used.
        **kwds : Union[TypingDict[str, Any], str]
            additional keywords are converted to aggregates using standard
            shorthand parsing.

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        Examples
        --------
        The aggregate transform allows you to specify transforms directly using
        the same shorthand syntax as used in encodings:

        >>> import altair as alt
        >>> chart1 = alt.Chart().transform_aggregate(
        ...     mean_acc='mean(Acceleration)',
        ...     groupby=['Origin']
        ... )
        >>> print(chart1.transform[0].to_json())  # doctest: +NORMALIZE_WHITESPACE
        {
          "aggregate": [
            {
              "as": "mean_acc",
              "field": "Acceleration",
              "op": "mean"
            }
          ],
          "groupby": [
            "Origin"
          ]
        }

        It also supports including AggregatedFieldDef instances or dicts directly,
        so you can create the above transform like this:

        >>> chart2 = alt.Chart().transform_aggregate(
        ...     [alt.AggregatedFieldDef(field='Acceleration', op='mean',
        ...                             **{'as': 'mean_acc'})],
        ...     groupby=['Origin']
        ... )
        >>> chart2.transform == chart1.transform
        True

        See Also
        --------
        alt.AggregateTransform : underlying transform object

        """
        if aggregate is Undefined:
            aggregate = []
        for key, val in kwds.items():
            parsed = utils.parse_shorthand(val)
            dct = {
                "as": key,
                "field": parsed.get("field", Undefined),
                "op": parsed.get("aggregate", Undefined),
            }
            assert not isinstance(aggregate, UndefinedType)  # For mypy
            aggregate.append(core.AggregatedFieldDef(**dct))
        return self._add_transform(
            core.AggregateTransform(aggregate=aggregate, groupby=groupby)
        )

    def transform_bin(
        self,
        as_: Union[
            str, core.FieldName, List[Union[str, core.FieldName]], UndefinedType
        ] = Undefined,
        field: Union[str, core.FieldName, UndefinedType] = Undefined,
        bin: Union[Literal[True], core.BinParams] = True,
        **kwargs,
    ) -> Self:
        """
        Add a :class:`BinTransform` to the schema.

        Parameters
        ----------
        as_ : anyOf(string, List(string))
            The output fields at which to write the start and end bin values.
        bin : anyOf(boolean, :class:`BinParams`)
            An object indicating bin properties, or simply ``true`` for using default bin
            parameters.
        field : string
            The data field to bin.

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        Examples
        --------
        >>> import altair as alt
        >>> chart = alt.Chart().transform_bin("x_binned", "x")
        >>> chart.transform[0]
        BinTransform({
          as: 'x_binned',
          bin: True,
          field: 'x'
        })

        >>> chart = alt.Chart().transform_bin("x_binned", "x",
        ...                                   bin=alt.Bin(maxbins=10))
        >>> chart.transform[0]
        BinTransform({
          as: 'x_binned',
          bin: BinParams({
            maxbins: 10
          }),
          field: 'x'
        })

        See Also
        --------
        alt.BinTransform : underlying transform object

        """
        if as_ is not Undefined:
            if "as" in kwargs:
                raise ValueError(
                    "transform_bin: both 'as_' and 'as' passed as arguments."
                )
            kwargs["as"] = as_
        kwargs["bin"] = bin
        kwargs["field"] = field
        return self._add_transform(core.BinTransform(**kwargs))

    def transform_calculate(
        self,
        as_: Union[str, core.FieldName, UndefinedType] = Undefined,
        calculate: Union[
            str, core.Expr, _expr_core.Expression, UndefinedType
        ] = Undefined,
        **kwargs: Union[str, core.Expr, _expr_core.Expression],
    ) -> Self:
        """
        Add a :class:`CalculateTransform` to the schema.

        Parameters
        ----------
        as_ : string
            The field for storing the computed formula value.
        calculate : string or alt.expr.Expression
            An `expression <https://vega.github.io/vega-lite/docs/types.html#expression>`__
            string. Use the variable ``datum`` to refer to the current data object.
        **kwargs
            transforms can also be passed by keyword argument; see Examples

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        Examples
        --------
        >>> import altair as alt
        >>> from altair import datum, expr

        >>> chart = alt.Chart().transform_calculate(y = 2 * expr.sin(datum.x))
        >>> chart.transform[0]
        CalculateTransform({
          as: 'y',
          calculate: (2 * sin(datum.x))
        })

        It's also possible to pass the ``CalculateTransform`` arguments directly:

        >>> kwds = {'as_': 'y', 'calculate': '2 * sin(datum.x)'}
        >>> chart = alt.Chart().transform_calculate(**kwds)
        >>> chart.transform[0]
        CalculateTransform({
          as: 'y',
          calculate: '2 * sin(datum.x)'
        })

        As the first form is easier to write and understand, that is the
        recommended method.

        See Also
        --------
        alt.CalculateTransform : underlying transform object
        """
        if as_ is Undefined:
            # Ignoring assignment error as passing 'as' as a keyword argument is
            # an edge case and it's not worth changing the type annotation
            # in this function to account for it as it could be confusing to
            # users.
            as_ = kwargs.pop("as", Undefined)  # type: ignore[assignment]
        elif "as" in kwargs:
            raise ValueError(
                "transform_calculate: both 'as_' and 'as' passed as arguments."
            )
        if as_ is not Undefined or calculate is not Undefined:
            dct = {"as": as_, "calculate": calculate}
            self = self._add_transform(core.CalculateTransform(**dct))  # type: ignore[arg-type]
        for as_, calculate in kwargs.items():
            dct = {"as": as_, "calculate": calculate}
            self = self._add_transform(core.CalculateTransform(**dct))  # type: ignore[arg-type]
        return self

    def transform_density(
        self,
        density: Union[str, core.FieldName],
        as_: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        bandwidth: Union[float, UndefinedType] = Undefined,
        counts: Union[bool, UndefinedType] = Undefined,
        cumulative: Union[bool, UndefinedType] = Undefined,
        extent: Union[List[float], UndefinedType] = Undefined,
        groupby: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        maxsteps: Union[int, UndefinedType] = Undefined,
        minsteps: Union[int, UndefinedType] = Undefined,
        steps: Union[int, UndefinedType] = Undefined,
    ) -> Self:
        """Add a :class:`DensityTransform` to the spec.

        Parameters
        ----------
        density : str
            The data field for which to perform density estimation.
        as_ : [str, str]
            The output fields for the sample value and corresponding density estimate.
            **Default value:** ``["value", "density"]``
        bandwidth : float
            The bandwidth (standard deviation) of the Gaussian kernel. If unspecified or set to
            zero, the bandwidth value is automatically estimated from the input data using
            Scott’s rule.
        counts : boolean
            A boolean flag indicating if the output values should be probability estimates
            (false) or smoothed counts (true).
            **Default value:** ``false``
        cumulative : boolean
            A boolean flag indicating whether to produce density estimates (false) or cumulative
            density estimates (true).
            **Default value:** ``false``
        extent : List([float, float])
            A [min, max] domain from which to sample the distribution. If unspecified, the
            extent will be determined by the observed minimum and maximum values of the density
            value field.
        groupby : List(str)
            The data fields to group by. If not specified, a single group containing all data
            objects will be used.
        maxsteps : int
            The maximum number of samples to take along the extent domain for plotting the
            density. **Default value:** ``200``
        minsteps : int
            The minimum number of samples to take along the extent domain for plotting the
            density. **Default value:** ``25``
        steps : int
            The exact number of samples to take along the extent domain for plotting the
            density. If specified, overrides both minsteps and maxsteps to set an exact number
            of uniform samples. Potentially useful in conjunction with a fixed extent to ensure
            consistent sample points for stacked densities.
        """
        return self._add_transform(
            core.DensityTransform(
                density=density,
                bandwidth=bandwidth,
                counts=counts,
                cumulative=cumulative,
                extent=extent,
                groupby=groupby,
                maxsteps=maxsteps,
                minsteps=minsteps,
                steps=steps,
                **{"as": as_},
            )
        )

    def transform_impute(
        self,
        impute: Union[str, core.FieldName],
        key: Union[str, core.FieldName],
        frame: Union[List[Optional[int]], UndefinedType] = Undefined,
        groupby: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        keyvals: Union[List[Any], core.ImputeSequence, UndefinedType] = Undefined,
        method: Union[
            Literal["value", "mean", "median", "max", "min"],
            core.ImputeMethod,
            UndefinedType,
        ] = Undefined,
        value=Undefined,
    ) -> Self:
        """
        Add an :class:`ImputeTransform` to the schema.

        Parameters
        ----------
        impute : string
            The data field for which the missing values should be imputed.
        key : string
            A key field that uniquely identifies data objects within a group.
            Missing key values (those occurring in the data but not in the current group) will
            be imputed.
        frame : List(anyOf(None, int))
            A frame specification as a two-element array used to control the window over which
            the specified method is applied. The array entries should either be a number
            indicating the offset from the current data object, or null to indicate unbounded
            rows preceding or following the current data object.  For example, the value ``[-5,
            5]`` indicates that the window should include five objects preceding and five
            objects following the current object.
            **Default value:** :  ``[null, null]`` indicating that the window includes all
            objects.
        groupby : List(string)
            An optional array of fields by which to group the values.
            Imputation will then be performed on a per-group basis.
        keyvals : anyOf(List(Mapping(required=[])), :class:`ImputeSequence`)
            Defines the key values that should be considered for imputation.
            An array of key values or an object defining a `number sequence
            <https://vega.github.io/vega-lite/docs/impute.html#sequence-def>`__.
            If provided, this will be used in addition to the key values observed within the
            input data.  If not provided, the values will be derived from all unique values of
            the ``key`` field. For ``impute`` in ``encoding``, the key field is the x-field if
            the y-field is imputed, or vice versa.
            If there is no impute grouping, this property *must* be specified.
        method : :class:`ImputeMethod`
            The imputation method to use for the field value of imputed data objects.
            One of ``value``, ``mean``, ``median``, ``max`` or ``min``.
            **Default value:**  ``"value"``
        value : Mapping(required=[])
            The field value to use when the imputation ``method`` is ``"value"``.

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        alt.ImputeTransform : underlying transform object
        """
        return self._add_transform(
            core.ImputeTransform(
                impute=impute,
                key=key,
                frame=frame,
                groupby=groupby,
                keyvals=keyvals,
                method=method,
                value=value,
            )
        )

    def transform_joinaggregate(
        self,
        joinaggregate: Union[
            List[core.JoinAggregateFieldDef], UndefinedType
        ] = Undefined,
        groupby: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        **kwargs: str,
    ) -> Self:
        """
        Add a :class:`JoinAggregateTransform` to the schema.

        Parameters
        ----------
        joinaggregate : List(:class:`JoinAggregateFieldDef`)
            The definition of the fields in the join aggregate, and what calculations to use.
        groupby : List(string)
            The data fields for partitioning the data objects into separate groups. If
            unspecified, all data points will be in a single group.
        **kwargs
            joinaggregates can also be passed by keyword argument; see Examples.

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        Examples
        --------
        >>> import altair as alt
        >>> chart = alt.Chart().transform_joinaggregate(x='sum(y)')
        >>> chart.transform[0]
        JoinAggregateTransform({
          joinaggregate: [JoinAggregateFieldDef({
            as: 'x',
            field: 'y',
            op: 'sum'
          })]
        })

        See Also
        --------
        alt.JoinAggregateTransform : underlying transform object
        """
        if joinaggregate is Undefined:
            joinaggregate = []
        for key, val in kwargs.items():
            parsed = utils.parse_shorthand(val)
            dct = {
                "as": key,
                "field": parsed.get("field", Undefined),
                "op": parsed.get("aggregate", Undefined),
            }
            assert not isinstance(joinaggregate, UndefinedType)  # For mypy
            joinaggregate.append(core.JoinAggregateFieldDef(**dct))
        return self._add_transform(
            core.JoinAggregateTransform(joinaggregate=joinaggregate, groupby=groupby)
        )

    def transform_extent(
        self, extent: Union[str, core.FieldName], param: Union[str, core.ParameterName]
    ) -> Self:
        """Add a :class:`ExtentTransform` to the spec.

        Parameters
        ----------
        extent : str
            The field of which to get the extent.
        param : str
            The name of the output parameter which will be created by
            the extent transform.

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining
        """
        return self._add_transform(core.ExtentTransform(extent=extent, param=param))

    # TODO: Update docstring
    def transform_filter(
        self,
        filter: Union[
            str,
            core.Expr,
            _expr_core.Expression,
            core.Predicate,
            Parameter,
            core.PredicateComposition,
            # E.g. {'not': alt.FieldRangePredicate(field='year', range=[1950, 1960])}
            TypingDict[str, Union[core.Predicate, str, list, bool]],
        ],
        **kwargs,
    ) -> Self:
        """
        Add a :class:`FilterTransform` to the schema.

        Parameters
        ----------
        filter : a filter expression or :class:`PredicateComposition`
            The `filter` property must be one of the predicate definitions:
            (1) a string or alt.expr expression
            (2) a range predicate
            (3) a selection predicate
            (4) a logical operand combining (1)-(3)
            (5) a Selection object

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining
        """
        if isinstance(filter, Parameter):
            new_filter: TypingDict[str, Union[bool, str]] = {"param": filter.name}
            if "empty" in kwargs:
                new_filter["empty"] = kwargs.pop("empty")
            elif isinstance(filter.empty, bool):
                new_filter["empty"] = filter.empty
            filter = new_filter  # type: ignore[assignment]
        return self._add_transform(core.FilterTransform(filter=filter, **kwargs))  # type: ignore[arg-type]

    def transform_flatten(
        self,
        flatten: List[Union[str, core.FieldName]],
        as_: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
    ) -> Self:
        """Add a :class:`FlattenTransform` to the schema.

        Parameters
        ----------
        flatten : List(string)
            An array of one or more data fields containing arrays to flatten.
            If multiple fields are specified, their array values should have a parallel
            structure, ideally with the same length.
            If the lengths of parallel arrays do not match,
            the longest array will be used with ``null`` values added for missing entries.
        as : List(string)
            The output field names for extracted array values.
            **Default value:** The field name of the corresponding array field

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        alt.FlattenTransform : underlying transform object
        """
        return self._add_transform(
            core.FlattenTransform(flatten=flatten, **{"as": as_})
        )

    def transform_fold(
        self,
        fold: List[Union[str, core.FieldName]],
        as_: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
    ) -> Self:
        """Add a :class:`FoldTransform` to the spec.

        Parameters
        ----------
        fold : List(string)
            An array of data fields indicating the properties to fold.
        as : [string, string]
            The output field names for the key and value properties produced by the fold
            transform. Default: ``["key", "value"]``

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        Chart.transform_pivot : pivot transform - opposite of fold.
        alt.FoldTransform : underlying transform object
        """
        return self._add_transform(core.FoldTransform(fold=fold, **{"as": as_}))

    def transform_loess(
        self,
        on: Union[str, core.FieldName],
        loess: Union[str, core.FieldName],
        as_: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        bandwidth: Union[float, UndefinedType] = Undefined,
        groupby: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
    ) -> Self:
        """Add a :class:`LoessTransform` to the spec.

        Parameters
        ----------
        on : str
            The data field of the independent variable to use a predictor.
        loess : str
            The data field of the dependent variable to smooth.
        as_ : [str, str]
            The output field names for the smoothed points generated by the loess transform.
            **Default value:** The field names of the input x and y values.
        bandwidth : float
            A bandwidth parameter in the range ``[0, 1]`` that determines the amount of
            smoothing. **Default value:** ``0.3``
        groupby : List(str)
            The data fields to group by. If not specified, a single group containing all data
            objects will be used.

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        Chart.transform_regression: regression transform
        alt.LoessTransform : underlying transform object
        """
        return self._add_transform(
            core.LoessTransform(
                loess=loess, on=on, bandwidth=bandwidth, groupby=groupby, **{"as": as_}
            )
        )

    def transform_lookup(
        self,
        lookup: Union[str, UndefinedType] = Undefined,
        from_: Union[core.LookupData, core.LookupSelection, UndefinedType] = Undefined,
        as_: Union[
            Union[str, core.FieldName], List[Union[str, core.FieldName]], UndefinedType
        ] = Undefined,
        default: Union[str, UndefinedType] = Undefined,
        **kwargs,
    ) -> Self:
        """Add a :class:`DataLookupTransform` or :class:`SelectionLookupTransform` to the chart

        Parameters
        ----------
        lookup : string
            Key in primary data source.
        from_ : anyOf(:class:`LookupData`, :class:`LookupSelection`)
            Secondary data reference.
        as_ : anyOf(string, List(string))
            The output fields on which to store the looked up data values.

            For data lookups, this property may be left blank if ``from_.fields``
            has been specified (those field names will be used); if ``from_.fields``
            has not been specified, ``as_`` must be a string.

            For selection lookups, this property is optional: if unspecified,
            looked up values will be stored under a property named for the selection;
            and if specified, it must correspond to ``from_.fields``.
        default : string
            The default value to use if lookup fails. **Default value:** ``null``

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        alt.DataLookupTransform : underlying transform object
        alt.SelectionLookupTransform : underlying transform object
        """
        if as_ is not Undefined:
            if "as" in kwargs:
                raise ValueError(
                    "transform_lookup: both 'as_' and 'as' passed as arguments."
                )
            kwargs["as"] = as_
        if from_ is not Undefined:
            if "from" in kwargs:
                raise ValueError(
                    "transform_lookup: both 'from_' and 'from' passed as arguments."
                )
            kwargs["from"] = from_
        kwargs["lookup"] = lookup
        kwargs["default"] = default
        return self._add_transform(core.LookupTransform(**kwargs))

    def transform_pivot(
        self,
        pivot: Union[str, core.FieldName],
        value: Union[str, core.FieldName],
        groupby: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        limit: Union[int, UndefinedType] = Undefined,
        op: Union[str, core.AggregateOp, UndefinedType] = Undefined,
    ) -> Self:
        """Add a :class:`PivotTransform` to the chart.

        Parameters
        ----------
        pivot : str
            The data field to pivot on. The unique values of this field become new field names
            in the output stream.
        value : str
            The data field to populate pivoted fields. The aggregate values of this field become
            the values of the new pivoted fields.
        groupby : List(str)
            The optional data fields to group by. If not specified, a single group containing
            all data objects will be used.
        limit : int
            An optional parameter indicating the maximum number of pivoted fields to generate.
            The default ( ``0`` ) applies no limit. The pivoted ``pivot`` names are sorted in
            ascending order prior to enforcing the limit.
            **Default value:** ``0``
        op : string
            The aggregation operation to apply to grouped ``value`` field values.
            **Default value:** ``sum``

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        Chart.transform_fold : fold transform - opposite of pivot.
        alt.PivotTransform : underlying transform object
        """
        return self._add_transform(
            core.PivotTransform(
                # Ignore as we type here `op` as a str but in core.PivotTransform
                # it's a Literal with all options
                pivot=pivot,
                value=value,
                groupby=groupby,
                limit=limit,
                op=op,  # type: ignore[arg-type]
            )
        )

    def transform_quantile(
        self,
        quantile: Union[str, core.FieldName],
        as_: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        groupby: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        probs: Union[List[float], UndefinedType] = Undefined,
        step: Union[float, UndefinedType] = Undefined,
    ) -> Self:
        """Add a :class:`QuantileTransform` to the chart

        Parameters
        ----------
        quantile : str
            The data field for which to perform quantile estimation.
        as : [str, str]
            The output field names for the probability and quantile values.
        groupby : List(str)
            The data fields to group by. If not specified, a single group containing all data
            objects will be used.
        probs : List(float)
            An array of probabilities in the range (0, 1) for which to compute quantile values.
            If not specified, the *step* parameter will be used.
        step : float
            A probability step size (default 0.01) for sampling quantile values. All values from
            one-half the step size up to 1 (exclusive) will be sampled. This parameter is only
            used if the *probs* parameter is not provided. **Default value:** ``["prob", "value"]``

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        alt.QuantileTransform : underlying transform object
        """
        return self._add_transform(
            core.QuantileTransform(
                quantile=quantile,
                groupby=groupby,
                probs=probs,
                step=step,
                **{"as": as_},
            )
        )

    def transform_regression(
        self,
        on: Union[str, core.FieldName],
        regression: Union[str, core.FieldName],
        as_: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        extent: Union[List[float], UndefinedType] = Undefined,
        groupby: Union[List[Union[str, core.FieldName]], UndefinedType] = Undefined,
        method: Union[
            Literal["linear", "log", "exp", "pow", "quad", "poly"], UndefinedType
        ] = Undefined,
        order: Union[int, UndefinedType] = Undefined,
        params: Union[bool, UndefinedType] = Undefined,
    ) -> Self:
        """Add a :class:`RegressionTransform` to the chart.

        Parameters
        ----------
        on : str
            The data field of the independent variable to use a predictor.
        regression : str
            The data field of the dependent variable to predict.
        as_ : [str, str]
            The output field names for the smoothed points generated by the regression
            transform. **Default value:** The field names of the input x and y values.
        extent : [float, float]
            A [min, max] domain over the independent (x) field for the starting and ending
            points of the generated trend line.
        groupby : List(str)
            The data fields to group by. If not specified, a single group containing all data
            objects will be used.
        method : enum('linear', 'log', 'exp', 'pow', 'quad', 'poly')
            The functional form of the regression model. One of ``"linear"``, ``"log"``,
            ``"exp"``, ``"pow"``, ``"quad"``, or ``"poly"``.  **Default value:** ``"linear"``
        order : int
            The polynomial order (number of coefficients) for the 'poly' method.
            **Default value:** ``3``
        params : boolean
            A boolean flag indicating if the transform should return the regression model
            parameters (one object per group), rather than trend line points.
            The resulting objects include a ``coef`` array of fitted coefficient values
            (starting with the intercept term and then including terms of increasing order)
            and an ``rSquared`` value (indicating the total variance explained by the model).
            **Default value:** ``false``

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        Chart.transform_loess : LOESS transform
        alt.RegressionTransform : underlying transform object
        """
        return self._add_transform(
            core.RegressionTransform(
                regression=regression,
                on=on,
                extent=extent,
                groupby=groupby,
                method=method,
                order=order,
                params=params,
                **{"as": as_},
            )
        )

    def transform_sample(self, sample: int = 1000) -> Self:
        """
        Add a :class:`SampleTransform` to the schema.

        Parameters
        ----------
        sample : int
            The maximum number of data objects to include in the sample. Default: 1000.

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        alt.SampleTransform : underlying transform object
        """
        return self._add_transform(core.SampleTransform(sample))

    def transform_stack(
        self,
        as_: Union[str, core.FieldName, List[str]],
        stack: Union[str, core.FieldName],
        groupby: List[Union[str, core.FieldName]],
        offset: Union[
            Literal["zero", "center", "normalize"], UndefinedType
        ] = Undefined,
        sort: Union[List[core.SortField], UndefinedType] = Undefined,
    ) -> Self:
        """
        Add a :class:`StackTransform` to the schema.

        Parameters
        ----------
        as_ : anyOf(string, List(string))
            Output field names. This can be either a string or an array of strings with
            two elements denoting the name for the fields for stack start and stack end
            respectively.
            If a single string(eg."val") is provided, the end field will be "val_end".
        stack : string
            The field which is stacked.
        groupby : List(string)
            The data fields to group by.
        offset : enum('zero', 'center', 'normalize')
            Mode for stacking marks. Default: 'zero'.
        sort : List(:class:`SortField`)
            Field that determines the order of leaves in the stacked charts.

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        See Also
        --------
        alt.StackTransform : underlying transform object
        """
        return self._add_transform(
            core.StackTransform(
                stack=stack, groupby=groupby, offset=offset, sort=sort, **{"as": as_}
            )
        )

    def transform_timeunit(
        self,
        as_: Union[str, core.FieldName, UndefinedType] = Undefined,
        field: Union[str, core.FieldName, UndefinedType] = Undefined,
        timeUnit: Union[str, core.TimeUnit, UndefinedType] = Undefined,
        **kwargs: str,
    ) -> Self:
        """
        Add a :class:`TimeUnitTransform` to the schema.

        Parameters
        ----------
        as_ : string
            The output field to write the timeUnit value.
        field : string
            The data field to apply time unit.
        timeUnit : str or :class:`TimeUnit`
            The timeUnit.
        **kwargs
            transforms can also be passed by keyword argument; see Examples

        Returns
        -------
        self : Chart object
            returns chart to allow for chaining

        Examples
        --------
        >>> import altair as alt
        >>> from altair import datum, expr

        >>> chart = alt.Chart().transform_timeunit(month='month(date)')
        >>> chart.transform[0]
        TimeUnitTransform({
          as: 'month',
          field: 'date',
          timeUnit: 'month'
        })

        It's also possible to pass the ``TimeUnitTransform`` arguments directly;
        this is most useful in cases where the desired field name is not a
        valid python identifier:

        >>> kwds = {'as': 'month', 'timeUnit': 'month', 'field': 'The Month'}
        >>> chart = alt.Chart().transform_timeunit(**kwds)
        >>> chart.transform[0]
        TimeUnitTransform({
          as: 'month',
          field: 'The Month',
          timeUnit: 'month'
        })

        As the first form is easier to write and understand, that is the
        recommended method.

        See Also
        --------
        alt.TimeUnitTransform : underlying transform object

        """
        if as_ is Undefined:
            as_ = kwargs.pop("as", Undefined)
        else:
            if "as" in kwargs:
                raise ValueError(
                    "transform_timeunit: both 'as_' and 'as' passed as arguments."
                )
        if as_ is not Undefined:
            dct = {"as": as_, "timeUnit": timeUnit, "field": field}
            self = self._add_transform(core.TimeUnitTransform(**dct))  # type: ignore[arg-type]
        for as_, shorthand in kwargs.items():
            dct = utils.parse_shorthand(
                shorthand,
                parse_timeunits=True,
                parse_aggregates=False,
                parse_types=False,
            )
            dct.pop("type", None)
            dct["as"] = as_
            if "timeUnit" not in dct:
                raise ValueError("'{}' must include a valid timeUnit".format(shorthand))
            self = self._add_transform(core.TimeUnitTransform(**dct))  # type: ignore[arg-type]
        return self

    def transform_window(
        self,
        window: Union[List[core.WindowFieldDef], UndefinedType] = Undefined,
        frame: Union[List[Optional[int]], UndefinedType] = Undefined,
        groupby: Union[List[str], UndefinedType] = Undefined,
        ignorePeers: Union[bool, UndefinedType] = Undefined,
        sort: Union[
            List[Union[core.SortField, TypingDict[str, str]]], UndefinedType
        ] = Undefined,
        **kwargs: str,
    ) -> Self:
        """Add a :class:`WindowTransform` to the schema

        Parameters
        ----------
        window : List(:class:`WindowFieldDef`)
            The definition of the fields in the window, and what calculations to use.
        frame : List(anyOf(None, int))
            A frame specification as a two-element array indicating how the sliding window
            should proceed. The array entries should either be a number indicating the offset
            from the current data object, or null to indicate unbounded rows preceding or
            following the current data object. The default value is ``[null, 0]``, indicating
            that the sliding window includes the current object and all preceding objects. The
            value ``[-5, 5]`` indicates that the window should include five objects preceding
            and five objects following the current object. Finally, ``[null, null]`` indicates
            that the window frame should always include all data objects. The only operators
            affected are the aggregation operations and the ``first_value``, ``last_value``, and
            ``nth_value`` window operations. The other window operations are not affected by
            this.

            **Default value:** :  ``[null, 0]`` (includes the current object and all preceding
            objects)
        groupby : List(string)
            The data fields for partitioning the data objects into separate windows. If
            unspecified, all data points will be in a single group.
        ignorePeers : boolean
            Indicates if the sliding window frame should ignore peer values. (Peer values are
            those considered identical by the sort criteria). The default is false, causing the
            window frame to expand to include all peer values. If set to true, the window frame
            will be defined by offset values only. This setting only affects those operations
            that depend on the window frame, namely aggregation operations and the first_value,
            last_value, and nth_value window operations.

            **Default value:** ``false``
        sort : List(:class:`SortField`)
            A sort field definition for sorting data objects within a window. If two data
            objects are considered equal by the comparator, they are considered “peer” values of
            equal rank. If sort is not specified, the order is undefined: data objects are
            processed in the order they are observed and none are considered peers (the
            ignorePeers parameter is ignored and treated as if set to ``true`` ).
        **kwargs
            transforms can also be passed by keyword argument; see Examples

        Examples
        --------
        A cumulative line chart

        >>> import altair as alt
        >>> import numpy as np
        >>> import pandas as pd
        >>> data = pd.DataFrame({'x': np.arange(100),
        ...                      'y': np.random.randn(100)})
        >>> chart = alt.Chart(data).mark_line().encode(
        ...     x='x:Q',
        ...     y='ycuml:Q'
        ... ).transform_window(
        ...     ycuml='sum(y)'
        ... )
        >>> chart.transform[0]
        WindowTransform({
          window: [WindowFieldDef({
            as: 'ycuml',
            field: 'y',
            op: 'sum'
          })]
        })

        """
        if kwargs:
            if window is Undefined:
                window = []
            for as_, shorthand in kwargs.items():
                kwds = {"as": as_}
                kwds.update(
                    utils.parse_shorthand(
                        shorthand,
                        parse_aggregates=False,
                        parse_window_ops=True,
                        parse_timeunits=False,
                        parse_types=False,
                    )
                )
                assert not isinstance(window, UndefinedType)  # For mypy
                # Ignore as core.WindowFieldDef has a Literal type hint with all options
                window.append(core.WindowFieldDef(**kwds))  # type: ignore[arg-type]

        return self._add_transform(
            core.WindowTransform(
                window=window,
                frame=frame,
                groupby=groupby,
                ignorePeers=ignorePeers,
                sort=sort,
            )
        )

    # Display-related methods

    def _repr_mimebundle_(self, include=None, exclude=None):
        """Return a MIME bundle for display in Jupyter frontends."""
        # Catch errors explicitly to get around issues in Jupyter frontend
        # see https://github.com/ipython/ipython/issues/11038
        try:
            dct = self.to_dict(context={"pre_transform": False})
        except Exception:
            utils.display_traceback(in_ipython=True)
            return {}
        else:
            return renderers.get()(dct)

    def display(
        self,
        renderer: Union[Literal["canvas", "svg"], UndefinedType] = Undefined,
        theme: Union[str, UndefinedType] = Undefined,
        actions: Union[bool, dict, UndefinedType] = Undefined,
        **kwargs,
    ) -> None:
        """Display chart in Jupyter notebook or JupyterLab

        Parameters are passed as options to vega-embed within supported frontends.
        See https://github.com/vega/vega-embed#options for details.

        Parameters
        ----------
        renderer : string ('canvas' or 'svg')
            The renderer to use
        theme : string
            The Vega theme name to use; see https://github.com/vega/vega-themes
        actions : bool or dict
            Specify whether action links ("Open In Vega Editor", etc.) are
            included in the view.
        **kwargs :
            Additional parameters are also passed to vega-embed as options.

        """
        from IPython.display import display

        if renderer is not Undefined:
            kwargs["renderer"] = renderer
        if theme is not Undefined:
            kwargs["theme"] = theme
        if actions is not Undefined:
            kwargs["actions"] = actions

        if kwargs:
            options = renderers.options.copy()
            options["embed_options"] = options.get("embed_options", {}).copy()
            options["embed_options"].update(kwargs)
            with renderers.enable(**options):
                display(self)
        else:
            display(self)

    @utils.deprecation.deprecated(message="'serve' is deprecated. Use 'show' instead.")
    def serve(
        self,
        ip="127.0.0.1",
        port=8888,
        n_retries=50,
        files=None,
        jupyter_warning=True,
        open_browser=True,
        http_server=None,
        **kwargs,
    ):
        """
        'serve' is deprecated. Use 'show' instead.

        Open a browser window and display a rendering of the chart

        Parameters
        ----------
        html : string
            HTML to serve
        ip : string (default = '127.0.0.1')
            ip address at which the HTML will be served.
        port : int (default = 8888)
            the port at which to serve the HTML
        n_retries : int (default = 50)
            the number of nearby ports to search if the specified port
            is already in use.
        files : dictionary (optional)
            dictionary of extra content to serve
        jupyter_warning : bool (optional)
            if True (default), then print a warning if this is used
            within the Jupyter notebook
        open_browser : bool (optional)
            if True (default), then open a web browser to the given HTML
        http_server : class (optional)
            optionally specify an HTTPServer class to use for showing the
            figure. The default is Python's basic HTTPServer.
        **kwargs :
            additional keyword arguments passed to the save() method

        """
        from ...utils.server import serve

        html = io.StringIO()
        self.save(html, format="html", **kwargs)
        html.seek(0)

        serve(
            html.read(),
            ip=ip,
            port=port,
            n_retries=n_retries,
            files=files,
            jupyter_warning=jupyter_warning,
            open_browser=open_browser,
            http_server=http_server,
        )

    def show(self) -> None:
        """Display the chart using the active renderer"""
        if renderers.active == "browser":
            # Opens browser window as side-effect.
            # We use a special case here so that IPython is not required
            self._repr_mimebundle_()
        else:
            # Mime-bundle based renderer, requires running in an IPython session
            from IPython.display import display

            display(self)

    @utils.use_signature(core.Resolve)
    def _set_resolve(self, **kwargs):
        """Copy the chart and update the resolve property with kwargs"""
        if not hasattr(self, "resolve"):
            raise ValueError(
                "{} object has no attribute " "'resolve'".format(self.__class__)
            )
        copy = self.copy(deep=["resolve"])
        if copy.resolve is Undefined:
            copy.resolve = core.Resolve()
        for key, val in kwargs.items():
            copy.resolve[key] = val
        return copy

    @utils.use_signature(core.AxisResolveMap)
    def resolve_axis(self, *args, **kwargs) -> Self:
        return self._set_resolve(axis=core.AxisResolveMap(*args, **kwargs))

    @utils.use_signature(core.LegendResolveMap)
    def resolve_legend(self, *args, **kwargs) -> Self:
        return self._set_resolve(legend=core.LegendResolveMap(*args, **kwargs))

    @utils.use_signature(core.ScaleResolveMap)
    def resolve_scale(self, *args, **kwargs) -> Self:
        return self._set_resolve(scale=core.ScaleResolveMap(*args, **kwargs))


class _EncodingMixin:
    @utils.use_signature(channels._encode_signature)
    def encode(self, *args, **kwargs) -> Self:
        # Convert args to kwargs based on their types.
        kwargs = utils.infer_encoding_types(args, kwargs, channels)

        # get a copy of the dict representation of the previous encoding
        # ignore type as copy method comes from SchemaBase
        copy = self.copy(deep=["encoding"])  # type: ignore[attr-defined]
        encoding = copy._get("encoding", {})
        if isinstance(encoding, core.VegaLiteSchema):
            encoding = {k: v for k, v in encoding._kwds.items() if v is not Undefined}

        # update with the new encodings, and apply them to the copy
        encoding.update(kwargs)
        copy.encoding = core.FacetedEncoding(**encoding)
        return copy

    def facet(
        self,
        facet: Union[str, channels.Facet, UndefinedType] = Undefined,
        row: Union[str, core.FacetFieldDef, channels.Row, UndefinedType] = Undefined,
        column: Union[
            str, core.FacetFieldDef, channels.Column, UndefinedType
        ] = Undefined,
        data: Union[ChartDataType, UndefinedType] = Undefined,
        columns: Union[int, UndefinedType] = Undefined,
        **kwargs,
    ) -> "FacetChart":
        """Create a facet chart from the current chart.

        Faceted charts require data to be specified at the top level; if data
        is not specified, the data from the current chart will be used at the
        top level.

        Parameters
        ----------
        facet : string, Facet (optional)
            The data column to use as an encoding for a wrapped facet.
            If specified, then neither row nor column may be specified.
        column : string, Column, FacetFieldDef (optional)
            The data column to use as an encoding for a column facet.
            May be combined with row argument, but not with facet argument.
        row : string or Row, FacetFieldDef (optional)
            The data column to use as an encoding for a row facet.
            May be combined with column argument, but not with facet argument.
        data : string or dataframe (optional)
            The dataset to use for faceting. If not supplied, then data must
            be specified in the top-level chart that calls this method.
        columns : integer
            the maximum number of columns for a wrapped facet.

        Returns
        -------
        self :
            for chaining
        """
        facet_specified = facet is not Undefined
        rowcol_specified = row is not Undefined or column is not Undefined

        if facet_specified and rowcol_specified:
            raise ValueError(
                "facet argument cannot be combined with row/column argument."
            )

        if data is Undefined:
            if self.data is Undefined:  # type: ignore[has-type]
                raise ValueError(
                    "Facet charts require data to be specified at the top level. "
                    "If you are trying to facet layered or concatenated charts, "
                    "ensure that the same data variable is passed to each chart "
                    "or specify the data inside the facet method instead."
                )
            # ignore type as copy comes from another class
            self = self.copy(deep=False)  # type: ignore[attr-defined]
            data, self.data = self.data, Undefined  # type: ignore[has-type]

        if facet_specified:
            if isinstance(facet, str):
                facet = channels.Facet(facet)
        else:
            facet = FacetMapping(row=row, column=column)

        return FacetChart(spec=self, facet=facet, data=data, columns=columns, **kwargs)


class Chart(
    TopLevelMixin, _EncodingMixin, mixins.MarkMethodMixin, core.TopLevelUnitSpec
):
    """Create a basic Altair/Vega-Lite chart.

    Although it is possible to set all Chart properties as constructor attributes,
    it is more idiomatic to use methods such as ``mark_point()``, ``encode()``,
    ``transform_filter()``, ``properties()``, etc. See Altair's documentation
    for details and examples: http://altair-viz.github.io/.

    Parameters
    ----------
    data : Data
        An object describing the data source
    mark : AnyMark
        A `MarkDef` or `CompositeMarkDef` object, or a string describing the mark type
        (one of `"arc"`, `"area"`, `"bar"`, `"circle"`, `"geoshape"`, `"image"`,
        `"line"`, `"point"`, `"rule"`, `"rect"`, `"square"`, `"text"`, `"tick"`,
        `"trail"`, `"boxplot"`, `"errorband"`, and `"errorbar"`).
    encoding : FacetedEncoding
        A key-value mapping between encoding channels and definition of fields.
    autosize : anyOf(AutosizeType, AutoSizeParams)
        Sets how the visualization size should be determined. If a string, should be one of
        `"pad"`, `"fit"` or `"none"`. Object values can additionally specify parameters for
        content sizing and automatic resizing. `"fit"` is only supported for single and
        layered views that don't use `rangeStep`.  Default value: `pad`
    background : string
        CSS color property to use as the background of visualization.

        **Default value:** none (transparent)
    config : Config
        Vega-Lite configuration object.  This property can only be defined at the top-level
        of a specification.
    description : string
        Description of this mark for commenting purpose.
    height : float
        The height of a visualization.
    name : string
        Name of the visualization for later reference.
    padding : Padding
        The default visualization padding, in pixels, from the edge of the visualization
        canvas to the data rectangle.  If a number, specifies padding for all sides. If an
        object, the value should have the format `{"left": 5, "top": 5, "right": 5,
        "bottom": 5}` to specify padding for each side of the visualization.  Default
        value: `5`
    projection : Projection
        An object defining properties of geographic projection.  Works with `"geoshape"`
        marks and `"point"` or `"line"` marks that have a channel (one or more of `"X"`,
        `"X2"`, `"Y"`, `"Y2"`) with type `"latitude"`, or `"longitude"`.
    selection : Mapping(required=[])
        A key-value mapping between selection names and definitions.
    title : anyOf(string, TitleParams)
        Title for the plot.
    transform : List(Transform)
        An array of data transformations such as filter and new field calculation.
    width : float
        The width of a visualization.
    """

    def __init__(
        self,
        data: Union[ChartDataType, UndefinedType] = Undefined,
        encoding: Union[core.FacetedEncoding, UndefinedType] = Undefined,
        mark: Union[str, core.AnyMark, UndefinedType] = Undefined,
        width: Union[int, str, dict, core.Step, UndefinedType] = Undefined,
        height: Union[int, str, dict, core.Step, UndefinedType] = Undefined,
        **kwargs,
    ) -> None:
        super(Chart, self).__init__(
            # Data type hints won't match with what TopLevelUnitSpec expects
            # as there is some data processing happening when converting to
            # a VL spec
            data=data,  # type: ignore[arg-type]
            encoding=encoding,
            mark=mark,
            width=width,
            height=height,
            **kwargs,
        )

    _counter: int = 0

    @classmethod
    def _get_name(cls) -> str:
        cls._counter += 1
        return f"view_{cls._counter}"

    @classmethod
    def from_dict(cls, dct: dict, validate: bool = True) -> core.SchemaBase:  # type: ignore[override]  # Not the same signature as SchemaBase.from_dict. Would ideally be aligned in the future
        """Construct class from a dictionary representation

        Parameters
        ----------
        dct : dictionary
            The dict from which to construct the class
        validate : boolean
            If True (default), then validate the input against the schema.

        Returns
        -------
        obj : Chart object
            The wrapped schema

        Raises
        ------
        jsonschema.ValidationError :
            if validate=True and dct does not conform to the schema
        """
        for class_ in TopLevelMixin.__subclasses__():
            if class_ is Chart:
                class_ = cast(TypingType[TopLevelMixin], super(Chart, cls))
            try:
                # TopLevelMixin classes don't necessarily have from_dict defined
                # but all classes which are used here have due to how Altair is
                # designed. Too complex to type check right now.
                return class_.from_dict(dct, validate=validate)  # type: ignore[attr-defined]
            except jsonschema.ValidationError:
                pass

        # As a last resort, try using the Root vegalite object
        return core.Root.from_dict(dct, validate)

    def to_dict(
        self,
        validate: bool = True,
        *,
        format: str = "vega-lite",
        ignore: Optional[List[str]] = None,
        context: Optional[TypingDict[str, Any]] = None,
    ) -> dict:
        """Convert the chart to a dictionary suitable for JSON export

        Parameters
        ----------
        validate : bool, optional
            If True (default), then validate the output dictionary
            against the schema.
        format : str, optional
            Chart specification format, one of "vega-lite" (default) or "vega"
        ignore : list[str], optional
            A list of keys to ignore. It is usually not needed
            to specify this argument as a user.
        context : dict[str, Any], optional
            A context dictionary. It is usually not needed
            to specify this argument as a user.

        Notes
        -----
        Technical: The ignore parameter will *not* be passed to child to_dict
        function calls.

        Returns
        -------
        dict
            The dictionary representation of this chart

        Raises
        ------
        SchemaValidationError
            if validate=True and the dict does not conform to the schema
        """
        context = context or {}
        if self.data is Undefined and "data" not in context:
            # No data specified here or in parent: inject empty data
            # for easier specification of datum encodings.
            copy = self.copy(deep=False)
            copy.data = core.InlineData(values=[{}])  # type: ignore[assignment]
            return super(Chart, copy).to_dict(
                validate=validate, format=format, ignore=ignore, context=context
            )
        return super().to_dict(
            validate=validate, format=format, ignore=ignore, context=context
        )

    def transformed_data(
        self,
        row_limit: Optional[int] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> Optional[DataFrameLike]:
        """Evaluate a Chart's transforms

        Evaluate the data transforms associated with a Chart and return the
        transformed data a DataFrame

        Parameters
        ----------
        row_limit : int (optional)
            Maximum number of rows to return for each DataFrame. None (default) for unlimited
        exclude : iterable of str
            Set of the names of charts to exclude

        Returns
        -------
        DataFrame
            Transformed data as a DataFrame
        """
        from altair.utils._transformed_data import transformed_data

        return transformed_data(self, row_limit=row_limit, exclude=exclude)

    def add_params(self, *params: Parameter) -> Self:
        """Add one or more parameters to the chart."""
        if not params:
            return self
        copy = self.copy(deep=["params"])
        if copy.params is Undefined:
            copy.params = []

        for s in params:
            copy.params.append(s.param)
        return copy

    @utils.deprecation.deprecated(
        message="'add_selection' is deprecated. Use 'add_params' instead."
    )
    def add_selection(self, *params) -> Self:
        """'add_selection' is deprecated. Use 'add_params' instead."""
        return self.add_params(*params)

    def interactive(
        self, name: Optional[str] = None, bind_x: bool = True, bind_y: bool = True
    ) -> Self:
        """Make chart axes scales interactive

        Parameters
        ----------
        name : string
            The parameter name to use for the axes scales. This name should be
            unique among all parameters within the chart.
        bind_x : boolean, default True
            If true, then bind the interactive scales to the x-axis
        bind_y : boolean, default True
            If true, then bind the interactive scales to the y-axis

        Returns
        -------
        chart :
            copy of self, with interactive axes added

        """
        encodings = []
        if bind_x:
            encodings.append("x")
        if bind_y:
            encodings.append("y")
        return self.add_params(selection_interval(bind="scales", encodings=encodings))


def _check_if_valid_subspec(spec: Union[dict, core.SchemaBase], classname: str) -> None:
    """Check if the spec is a valid sub-spec.

    If it is not, then raise a ValueError
    """
    err = (
        'Objects with "{0}" attribute cannot be used within {1}. '
        "Consider defining the {0} attribute in the {1} object instead."
    )

    if not isinstance(spec, (core.SchemaBase, dict)):
        raise ValueError("Only chart objects can be used in {0}.".format(classname))
    for attr in TOPLEVEL_ONLY_KEYS:
        if isinstance(spec, core.SchemaBase):
            val = getattr(spec, attr, Undefined)
        else:
            val = spec.get(attr, Undefined)
        if val is not Undefined:
            raise ValueError(err.format(attr, classname))


def _check_if_can_be_layered(spec: Union[dict, core.SchemaBase]) -> None:
    """Check if the spec can be layered."""

    def _get(spec, attr):
        if isinstance(spec, core.SchemaBase):
            return spec._get(attr)
        else:
            return spec.get(attr, Undefined)

    encoding = _get(spec, "encoding")
    if encoding is not Undefined:
        for channel in ["row", "column", "facet"]:
            if _get(encoding, channel) is not Undefined:
                raise ValueError(
                    "Faceted charts cannot be layered. Instead, layer the charts before faceting."
                )
    if isinstance(spec, (Chart, LayerChart)):
        return

    if not isinstance(spec, (core.SchemaBase, dict)):
        raise ValueError("Only chart objects can be layered.")
    if _get(spec, "facet") is not Undefined:
        raise ValueError(
            "Faceted charts cannot be layered. Instead, layer the charts before faceting."
        )
    if isinstance(spec, FacetChart) or _get(spec, "facet") is not Undefined:
        raise ValueError(
            "Faceted charts cannot be layered. Instead, layer the charts before faceting."
        )
    if isinstance(spec, RepeatChart) or _get(spec, "repeat") is not Undefined:
        raise ValueError(
            "Repeat charts cannot be layered. Instead, layer the charts before repeating."
        )
    if isinstance(spec, ConcatChart) or _get(spec, "concat") is not Undefined:
        raise ValueError(
            "Concatenated charts cannot be layered. Instead, layer the charts before concatenating."
        )
    if isinstance(spec, HConcatChart) or _get(spec, "hconcat") is not Undefined:
        raise ValueError(
            "Concatenated charts cannot be layered. Instead, layer the charts before concatenating."
        )
    if isinstance(spec, VConcatChart) or _get(spec, "vconcat") is not Undefined:
        raise ValueError(
            "Concatenated charts cannot be layered. Instead, layer the charts before concatenating."
        )


class RepeatChart(TopLevelMixin, core.TopLevelRepeatSpec):
    """A chart repeated across rows and columns with small changes"""

    # Because TopLevelRepeatSpec is defined as a union as of Vega-Lite schema 4.9,
    # we set the arguments explicitly here.
    # TODO: Should we instead use tools/schemapi/codegen.get_args?
    @utils.use_signature(core.TopLevelRepeatSpec)
    def __init__(
        self,
        repeat=Undefined,
        spec=Undefined,
        align=Undefined,
        autosize=Undefined,
        background=Undefined,
        bounds=Undefined,
        center=Undefined,
        columns=Undefined,
        config=Undefined,
        data=Undefined,
        datasets=Undefined,
        description=Undefined,
        name=Undefined,
        padding=Undefined,
        params=Undefined,
        resolve=Undefined,
        spacing=Undefined,
        title=Undefined,
        transform=Undefined,
        usermeta=Undefined,
        **kwds,
    ):
        _check_if_valid_subspec(spec, "RepeatChart")
        _spec_as_list = [spec]
        params, _spec_as_list = _combine_subchart_params(params, _spec_as_list)
        spec = _spec_as_list[0]
        if isinstance(spec, (Chart, LayerChart)):
            params = _repeat_names(params, repeat, spec)
        super(RepeatChart, self).__init__(
            repeat=repeat,
            spec=spec,
            align=align,
            autosize=autosize,
            background=background,
            bounds=bounds,
            center=center,
            columns=columns,
            config=config,
            data=data,
            datasets=datasets,
            description=description,
            name=name,
            padding=padding,
            params=params,
            resolve=resolve,
            spacing=spacing,
            title=title,
            transform=transform,
            usermeta=usermeta,
            **kwds,
        )

    def transformed_data(
        self,
        row_limit: Optional[int] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> Optional[DataFrameLike]:
        """Evaluate a RepeatChart's transforms

        Evaluate the data transforms associated with a RepeatChart and return the
        transformed data a DataFrame

        Parameters
        ----------
        row_limit : int (optional)
            Maximum number of rows to return for each DataFrame. None (default) for unlimited
        exclude : iterable of str
            Set of the names of charts to exclude

        Raises
        ------
        NotImplementedError
            RepeatChart does not yet support transformed_data
        """
        raise NotImplementedError(
            "transformed_data is not yet implemented for RepeatChart"
        )

    def interactive(
        self, name: Optional[str] = None, bind_x: bool = True, bind_y: bool = True
    ) -> Self:
        """Make chart axes scales interactive

        Parameters
        ----------
        name : string
            The parameter name to use for the axes scales. This name should be
            unique among all parameters within the chart.
        bind_x : boolean, default True
            If true, then bind the interactive scales to the x-axis
        bind_y : boolean, default True
            If true, then bind the interactive scales to the y-axis

        Returns
        -------
        chart :
            copy of self, with interactive axes added

        """
        copy = self.copy(deep=False)
        copy.spec = copy.spec.interactive(name=name, bind_x=bind_x, bind_y=bind_y)
        return copy

    def add_params(self, *params: Parameter) -> Self:
        """Add one or more parameters to the chart."""
        if not params or self.spec is Undefined:
            return self
        copy = self.copy()
        copy.spec = copy.spec.add_params(*params)
        return copy.copy()

    @utils.deprecation.deprecated(
        message="'add_selection' is deprecated. Use 'add_params' instead."
    )
    def add_selection(self, *selections) -> Self:
        """'add_selection' is deprecated. Use 'add_params' instead."""
        return self.add_params(*selections)


def repeat(
    repeater: Literal["row", "column", "repeat", "layer"] = "repeat",
) -> core.RepeatRef:
    """Tie a channel to the row or column within a repeated chart

    The output of this should be passed to the ``field`` attribute of
    a channel.

    Parameters
    ----------
    repeater : {'row'|'column'|'repeat'|'layer'}
        The repeater to tie the field to. Default is 'repeat'.

    Returns
    -------
    repeat : RepeatRef object
    """
    if repeater not in ["row", "column", "repeat", "layer"]:
        raise ValueError("repeater must be one of ['row', 'column', 'repeat', 'layer']")
    return core.RepeatRef(repeat=repeater)


class ConcatChart(TopLevelMixin, core.TopLevelConcatSpec):
    """A chart with horizontally-concatenated facets"""

    @utils.use_signature(core.TopLevelConcatSpec)
    def __init__(self, data=Undefined, concat=(), columns=Undefined, **kwargs):
        # TODO: move common data to top level?
        for spec in concat:
            _check_if_valid_subspec(spec, "ConcatChart")
        super(ConcatChart, self).__init__(
            data=data, concat=list(concat), columns=columns, **kwargs
        )
        self.data, self.concat = _combine_subchart_data(self.data, self.concat)
        self.params, self.concat = _combine_subchart_params(self.params, self.concat)

    # Too difficult to fix override error
    def __ior__(self, other: core.NonNormalizedSpec) -> Self:  # type: ignore[override]
        _check_if_valid_subspec(other, "ConcatChart")
        self.concat.append(other)
        self.data, self.concat = _combine_subchart_data(self.data, self.concat)
        self.params, self.concat = _combine_subchart_params(self.params, self.concat)
        return self

    # Too difficult to fix override error
    def __or__(self, other: core.NonNormalizedSpec) -> Self:  # type: ignore[override]
        copy = self.copy(deep=["concat"])
        copy |= other
        return copy

    def transformed_data(
        self,
        row_limit: Optional[int] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> List[DataFrameLike]:
        """Evaluate a ConcatChart's transforms

        Evaluate the data transforms associated with a ConcatChart and return the
        transformed data for each subplot as a list of DataFrames

        Parameters
        ----------
        row_limit : int (optional)
            Maximum number of rows to return for each DataFrame. None (default) for unlimited
        exclude : iterable of str
            Set of the names of charts to exclude

        Returns
        -------
        list of DataFrame
            Transformed data for each subplot as a list of DataFrames
        """
        from altair.utils._transformed_data import transformed_data

        return transformed_data(self, row_limit=row_limit, exclude=exclude)

    def interactive(
        self, name: Optional[str] = None, bind_x: bool = True, bind_y: bool = True
    ) -> Self:
        """Make chart axes scales interactive

        Parameters
        ----------
        name : string
            The parameter name to use for the axes scales. This name should be
            unique among all parameters within the chart.
        bind_x : boolean, default True
            If true, then bind the interactive scales to the x-axis
        bind_y : boolean, default True
            If true, then bind the interactive scales to the y-axis

        Returns
        -------
        chart :
            copy of self, with interactive axes added

        """
        encodings = []
        if bind_x:
            encodings.append("x")
        if bind_y:
            encodings.append("y")
        return self.add_params(selection_interval(bind="scales", encodings=encodings))

    def add_params(self, *params: Parameter) -> Self:
        """Add one or more parameters to the chart."""
        if not params or not self.concat:
            return self
        copy = self.copy()
        copy.concat = [chart.add_params(*params) for chart in copy.concat]
        return copy

    @utils.deprecation.deprecated(
        message="'add_selection' is deprecated. Use 'add_params' instead."
    )
    def add_selection(self, *selections) -> Self:
        """'add_selection' is deprecated. Use 'add_params' instead."""
        return self.add_params(*selections)


def concat(*charts, **kwargs) -> ConcatChart:
    """Concatenate charts horizontally"""
    return ConcatChart(concat=charts, **kwargs)


class HConcatChart(TopLevelMixin, core.TopLevelHConcatSpec):
    """A chart with horizontally-concatenated facets"""

    @utils.use_signature(core.TopLevelHConcatSpec)
    def __init__(self, data=Undefined, hconcat=(), **kwargs):
        # TODO: move common data to top level?
        for spec in hconcat:
            _check_if_valid_subspec(spec, "HConcatChart")
        super(HConcatChart, self).__init__(data=data, hconcat=list(hconcat), **kwargs)
        self.data, self.hconcat = _combine_subchart_data(self.data, self.hconcat)
        self.params, self.hconcat = _combine_subchart_params(self.params, self.hconcat)

    def __ior__(self, other: core.NonNormalizedSpec) -> Self:
        _check_if_valid_subspec(other, "HConcatChart")
        self.hconcat.append(other)
        self.data, self.hconcat = _combine_subchart_data(self.data, self.hconcat)
        self.params, self.hconcat = _combine_subchart_params(self.params, self.hconcat)
        return self

    def __or__(self, other: core.NonNormalizedSpec) -> Self:
        copy = self.copy(deep=["hconcat"])
        copy |= other
        return copy

    def transformed_data(
        self,
        row_limit: Optional[int] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> List[DataFrameLike]:
        """Evaluate a HConcatChart's transforms

        Evaluate the data transforms associated with a HConcatChart and return the
        transformed data for each subplot as a list of DataFrames

        Parameters
        ----------
        row_limit : int (optional)
            Maximum number of rows to return for each DataFrame. None (default) for unlimited
        exclude : iterable of str
            Set of the names of charts to exclude

        Returns
        -------
        list of DataFrame
            Transformed data for each subplot as a list of DataFrames
        """
        from altair.utils._transformed_data import transformed_data

        return transformed_data(self, row_limit=row_limit, exclude=exclude)

    def interactive(
        self, name: Optional[str] = None, bind_x: bool = True, bind_y: bool = True
    ) -> Self:
        """Make chart axes scales interactive

        Parameters
        ----------
        name : string
            The parameter name to use for the axes scales. This name should be
            unique among all parameters within the chart.
        bind_x : boolean, default True
            If true, then bind the interactive scales to the x-axis
        bind_y : boolean, default True
            If true, then bind the interactive scales to the y-axis

        Returns
        -------
        chart :
            copy of self, with interactive axes added

        """
        encodings = []
        if bind_x:
            encodings.append("x")
        if bind_y:
            encodings.append("y")
        return self.add_params(selection_interval(bind="scales", encodings=encodings))

    def add_params(self, *params: Parameter) -> Self:
        """Add one or more parameters to the chart."""
        if not params or not self.hconcat:
            return self
        copy = self.copy()
        copy.hconcat = [chart.add_params(*params) for chart in copy.hconcat]
        return copy

    @utils.deprecation.deprecated(
        message="'add_selection' is deprecated. Use 'add_params' instead."
    )
    def add_selection(self, *selections) -> Self:
        """'add_selection' is deprecated. Use 'add_params' instead."""
        return self.add_params(*selections)


def hconcat(*charts, **kwargs) -> HConcatChart:
    """Concatenate charts horizontally"""
    return HConcatChart(hconcat=charts, **kwargs)


class VConcatChart(TopLevelMixin, core.TopLevelVConcatSpec):
    """A chart with vertically-concatenated facets"""

    @utils.use_signature(core.TopLevelVConcatSpec)
    def __init__(self, data=Undefined, vconcat=(), **kwargs):
        # TODO: move common data to top level?
        for spec in vconcat:
            _check_if_valid_subspec(spec, "VConcatChart")
        super(VConcatChart, self).__init__(data=data, vconcat=list(vconcat), **kwargs)
        self.data, self.vconcat = _combine_subchart_data(self.data, self.vconcat)
        self.params, self.vconcat = _combine_subchart_params(self.params, self.vconcat)

    def __iand__(self, other: core.NonNormalizedSpec) -> Self:
        _check_if_valid_subspec(other, "VConcatChart")
        self.vconcat.append(other)
        self.data, self.vconcat = _combine_subchart_data(self.data, self.vconcat)
        self.params, self.vconcat = _combine_subchart_params(self.params, self.vconcat)
        return self

    def __and__(self, other: core.NonNormalizedSpec) -> Self:
        copy = self.copy(deep=["vconcat"])
        copy &= other
        return copy

    def transformed_data(
        self,
        row_limit: Optional[int] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> List[DataFrameLike]:
        """Evaluate a VConcatChart's transforms

        Evaluate the data transforms associated with a VConcatChart and return the
        transformed data for each subplot as a list of DataFrames

        Parameters
        ----------
        row_limit : int (optional)
            Maximum number of rows to return for each DataFrame. None (default) for unlimited
        exclude : iterable of str
            Set of the names of charts to exclude

        Returns
        -------
        list of DataFrame
            Transformed data for each subplot as a list of DataFrames
        """
        from altair.utils._transformed_data import transformed_data

        return transformed_data(self, row_limit=row_limit, exclude=exclude)

    def interactive(
        self, name: Optional[str] = None, bind_x: bool = True, bind_y: bool = True
    ) -> Self:
        """Make chart axes scales interactive

        Parameters
        ----------
        name : string
            The parameter name to use for the axes scales. This name should be
            unique among all parameters within the chart.
        bind_x : boolean, default True
            If true, then bind the interactive scales to the x-axis
        bind_y : boolean, default True
            If true, then bind the interactive scales to the y-axis

        Returns
        -------
        chart :
            copy of self, with interactive axes added

        """
        encodings = []
        if bind_x:
            encodings.append("x")
        if bind_y:
            encodings.append("y")
        return self.add_params(selection_interval(bind="scales", encodings=encodings))

    def add_params(self, *params: Parameter) -> Self:
        """Add one or more parameters to the chart."""
        if not params or not self.vconcat:
            return self
        copy = self.copy()
        copy.vconcat = [chart.add_params(*params) for chart in copy.vconcat]
        return copy

    @utils.deprecation.deprecated(
        message="'add_selection' is deprecated. Use 'add_params' instead."
    )
    def add_selection(self, *selections) -> Self:
        """'add_selection' is deprecated. Use 'add_params' instead."""
        return self.add_params(*selections)


def vconcat(*charts, **kwargs) -> VConcatChart:
    """Concatenate charts vertically"""
    return VConcatChart(vconcat=charts, **kwargs)


class LayerChart(TopLevelMixin, _EncodingMixin, core.TopLevelLayerSpec):
    """A Chart with layers within a single panel"""

    @utils.use_signature(core.TopLevelLayerSpec)
    def __init__(self, data=Undefined, layer=(), **kwargs):
        # TODO: move common data to top level?
        # TODO: check for conflicting interaction
        for spec in layer:
            _check_if_valid_subspec(spec, "LayerChart")
            _check_if_can_be_layered(spec)
        super(LayerChart, self).__init__(data=data, layer=list(layer), **kwargs)
        self.data, self.layer = _combine_subchart_data(self.data, self.layer)
        # Currently (Vega-Lite 5.5) the same param can't occur on two layers
        self.layer = _remove_duplicate_params(self.layer)
        self.params, self.layer = _combine_subchart_params(self.params, self.layer)

        # Some properties are not allowed within layer; we'll move to parent.
        layer_props = ("height", "width", "view")
        combined_dict, self.layer = _remove_layer_props(self, self.layer, layer_props)

        for prop in combined_dict:
            self[prop] = combined_dict[prop]

    def transformed_data(
        self,
        row_limit: Optional[int] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> List[DataFrameLike]:
        """Evaluate a LayerChart's transforms

        Evaluate the data transforms associated with a LayerChart and return the
        transformed data for each layer as a list of DataFrames

        Parameters
        ----------
        row_limit : int (optional)
            Maximum number of rows to return for each DataFrame. None (default) for unlimited
        exclude : iterable of str
            Set of the names of charts to exclude

        Returns
        -------
        list of DataFrame
            Transformed data for each layer as a list of DataFrames
        """
        from altair.utils._transformed_data import transformed_data

        return transformed_data(self, row_limit=row_limit, exclude=exclude)

    def __iadd__(self, other: Union[core.LayerSpec, core.UnitSpec]) -> Self:
        _check_if_valid_subspec(other, "LayerChart")
        _check_if_can_be_layered(other)
        self.layer.append(other)
        self.data, self.layer = _combine_subchart_data(self.data, self.layer)
        self.params, self.layer = _combine_subchart_params(self.params, self.layer)
        return self

    def __add__(self, other: Union[core.LayerSpec, core.UnitSpec]) -> Self:
        copy = self.copy(deep=["layer"])
        copy += other
        return copy

    def add_layers(self, *layers: Union[core.LayerSpec, core.UnitSpec]) -> Self:
        copy = self.copy(deep=["layer"])
        for layer in layers:
            copy += layer
        return copy

    def interactive(
        self, name: Optional[str] = None, bind_x: bool = True, bind_y: bool = True
    ) -> Self:
        """Make chart axes scales interactive

        Parameters
        ----------
        name : string
            The parameter name to use for the axes scales. This name should be
            unique among all parameters within the chart.
        bind_x : boolean, default True
            If true, then bind the interactive scales to the x-axis
        bind_y : boolean, default True
            If true, then bind the interactive scales to the y-axis

        Returns
        -------
        chart :
            copy of self, with interactive axes added

        """
        if not self.layer:
            raise ValueError(
                "LayerChart: cannot call interactive() until a " "layer is defined"
            )
        copy = self.copy(deep=["layer"])
        copy.layer[0] = copy.layer[0].interactive(
            name=name, bind_x=bind_x, bind_y=bind_y
        )
        return copy

    def add_params(self, *params: Parameter) -> Self:
        """Add one or more parameters to the chart."""
        if not params or not self.layer:
            return self
        copy = self.copy()
        copy.layer[0] = copy.layer[0].add_params(*params)
        return copy.copy()

    @utils.deprecation.deprecated(
        message="'add_selection' is deprecated. Use 'add_params' instead."
    )
    def add_selection(self, *selections) -> Self:
        """'add_selection' is deprecated. Use 'add_params' instead."""
        return self.add_params(*selections)


def layer(*charts, **kwargs) -> LayerChart:
    """layer multiple charts"""
    return LayerChart(layer=charts, **kwargs)


class FacetChart(TopLevelMixin, core.TopLevelFacetSpec):
    """A Chart with layers within a single panel"""

    @utils.use_signature(core.TopLevelFacetSpec)
    def __init__(
        self,
        data=Undefined,
        spec=Undefined,
        facet=Undefined,
        params=Undefined,
        **kwargs,
    ):
        _check_if_valid_subspec(spec, "FacetChart")
        _spec_as_list = [spec]
        params, _spec_as_list = _combine_subchart_params(params, _spec_as_list)
        spec = _spec_as_list[0]
        super(FacetChart, self).__init__(
            data=data, spec=spec, facet=facet, params=params, **kwargs
        )

    def transformed_data(
        self,
        row_limit: Optional[int] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> Optional[DataFrameLike]:
        """Evaluate a FacetChart's transforms

        Evaluate the data transforms associated with a FacetChart and return the
        transformed data a DataFrame

        Parameters
        ----------
        row_limit : int (optional)
            Maximum number of rows to return for each DataFrame. None (default) for unlimited
        exclude : iterable of str
            Set of the names of charts to exclude

        Returns
        -------
        DataFrame
            Transformed data as a DataFrame
        """
        from altair.utils._transformed_data import transformed_data

        return transformed_data(self, row_limit=row_limit, exclude=exclude)

    def interactive(
        self, name: Optional[str] = None, bind_x: bool = True, bind_y: bool = True
    ) -> Self:
        """Make chart axes scales interactive

        Parameters
        ----------
        name : string
            The parameter name to use for the axes scales. This name should be
            unique among all parameters within the chart.
        bind_x : boolean, default True
            If true, then bind the interactive scales to the x-axis
        bind_y : boolean, default True
            If true, then bind the interactive scales to the y-axis

        Returns
        -------
        chart :
            copy of self, with interactive axes added

        """
        copy = self.copy(deep=False)
        copy.spec = copy.spec.interactive(name=name, bind_x=bind_x, bind_y=bind_y)
        return copy

    def add_params(self, *params: Parameter) -> Self:
        """Add one or more parameters to the chart."""
        if not params or self.spec is Undefined:
            return self
        copy = self.copy()
        copy.spec = copy.spec.add_params(*params)
        return copy.copy()

    @utils.deprecation.deprecated(
        message="'add_selection' is deprecated. Use 'add_params' instead."
    )
    def add_selection(self, *selections) -> Self:
        """'add_selection' is deprecated. Use 'add_params' instead."""
        return self.add_params(*selections)


def topo_feature(url: str, feature: str, **kwargs) -> core.UrlData:
    """A convenience function for extracting features from a topojson url

    Parameters
    ----------
    url : string
        An URL from which to load the data set.

    feature : string
        The name of the TopoJSON object set to convert to a GeoJSON feature collection. For
        example, in a map of the world, there may be an object set named `"countries"`.
        Using the feature property, we can extract this set and generate a GeoJSON feature
        object for each country.

    **kwargs :
        additional keywords passed to TopoDataFormat
    """
    return core.UrlData(
        url=url, format=core.TopoDataFormat(type="topojson", feature=feature, **kwargs)
    )


def _combine_subchart_data(data, subcharts):
    def remove_data(subchart):
        if subchart.data is not Undefined:
            subchart = subchart.copy()
            subchart.data = Undefined
        return subchart

    if not subcharts:
        # No subcharts = nothing to do.
        pass
    elif data is Undefined:
        # Top level has no data; all subchart data must
        # be identical to proceed.
        subdata = subcharts[0].data
        if subdata is not Undefined and all(c.data is subdata for c in subcharts):
            data = subdata
            subcharts = [remove_data(c) for c in subcharts]
    else:
        # Top level has data; subchart data must be either
        # undefined or identical to proceed.
        if all(c.data is Undefined or c.data is data for c in subcharts):
            subcharts = [remove_data(c) for c in subcharts]

    return data, subcharts


def _viewless_dict(param: Parameter) -> dict:
    d = param.to_dict()
    d.pop("views", None)
    return d


def _needs_name(subchart):
    # Only `Chart` objects need a name
    if (subchart.name is not Undefined) or (not isinstance(subchart, Chart)):
        return False

    # Variable parameters won't receive a views property.
    if all(isinstance(p, core.VariableParameter) for p in subchart.params):
        return False

    return True


# Convert SelectionParameters to TopLevelSelectionParameters with a views property.
def _prepare_to_lift(param):
    param = param.copy()

    if isinstance(param, core.VariableParameter):
        return param

    if isinstance(param, core.SelectionParameter):
        return core.TopLevelSelectionParameter(**param.to_dict(), views=[])

    if param.views is Undefined:
        param.views = []

    return param


def _remove_duplicate_params(layer):
    subcharts = [subchart.copy() for subchart in layer]
    found_params = []

    for subchart in subcharts:
        if (not hasattr(subchart, "params")) or (subchart.params is Undefined):
            continue

        params = []

        # Ensure the same selection parameter doesn't appear twice
        for param in subchart.params:
            if isinstance(param, core.VariableParameter):
                params.append(param)
                continue

            p = param.copy()
            pd = _viewless_dict(p)

            if pd not in found_params:
                params.append(p)
                found_params.append(pd)

        if len(params) == 0:
            subchart.params = Undefined
        else:
            subchart.params = params

    return subcharts


def _combine_subchart_params(params, subcharts):
    if params is Undefined:
        params = []

    # List of triples related to params, (param, dictionary minus views, views)
    param_info = []

    # Put parameters already found into `param_info` list.
    for param in params:
        p = _prepare_to_lift(param)
        param_info.append(
            (
                p,
                _viewless_dict(p),
                [] if isinstance(p, core.VariableParameter) else p.views,
            )
        )

    subcharts = [subchart.copy() for subchart in subcharts]

    for subchart in subcharts:
        if (not hasattr(subchart, "params")) or (subchart.params is Undefined):
            continue

        if _needs_name(subchart):
            subchart.name = subchart._get_name()

        for param in subchart.params:
            p = _prepare_to_lift(param)
            pd = _viewless_dict(p)

            dlist = [d for _, d, _ in param_info]
            found = pd in dlist

            if isinstance(p, core.VariableParameter) and found:
                continue

            if isinstance(p, core.VariableParameter) and not found:
                param_info.append((p, pd, []))
                continue

            # At this stage in the loop, p must be a TopLevelSelectionParameter.

            if isinstance(subchart, Chart) and (subchart.name not in p.views):
                p.views.append(subchart.name)

            if found:
                i = dlist.index(pd)
                _, _, old_views = param_info[i]
                new_views = [v for v in p.views if v not in old_views]
                old_views += new_views
            else:
                param_info.append((p, pd, p.views))

        subchart.params = Undefined

    for p, _, v in param_info:
        if len(v) > 0:
            p.views = v

    subparams = [p for p, _, _ in param_info]

    if len(subparams) == 0:
        subparams = Undefined

    return subparams, subcharts


def _get_repeat_strings(repeat):
    if isinstance(repeat, list):
        return repeat
    elif isinstance(repeat, core.LayerRepeatMapping):
        klist = ["row", "column", "layer"]
    elif isinstance(repeat, core.RepeatMapping):
        klist = ["row", "column"]
    rclist = [k for k in klist if repeat[k] is not Undefined]
    rcstrings = [[f"{k}_{v}" for v in repeat[k]] for k in rclist]
    return ["".join(s) for s in itertools.product(*rcstrings)]


def _extend_view_name(v, r, spec):
    # prevent the same extension from happening more than once
    if isinstance(spec, Chart):
        if v.endswith("child__" + r):
            return v
        else:
            return f"{v}_child__{r}"
    elif isinstance(spec, LayerChart):
        if v.startswith("child__" + r):
            return v
        else:
            return f"child__{r}_{v}"


def _repeat_names(params, repeat, spec):
    if params is Undefined:
        return params

    repeat = _get_repeat_strings(repeat)
    params_named = []

    for param in params:
        if not isinstance(param, core.TopLevelSelectionParameter):
            params_named.append(param)
            continue
        p = param.copy()
        views = []
        repeat_strings = _get_repeat_strings(repeat)
        for v in param.views:
            if isinstance(spec, Chart):
                if any(v.endswith(f"child__{r}") for r in repeat_strings):
                    views.append(v)
                else:
                    views += [_extend_view_name(v, r, spec) for r in repeat_strings]
            elif isinstance(spec, LayerChart):
                if any(v.startswith(f"child__{r}") for r in repeat_strings):
                    views.append(v)
                else:
                    views += [_extend_view_name(v, r, spec) for r in repeat_strings]

        p.views = views
        params_named.append(p)

    return params_named


def _remove_layer_props(chart, subcharts, layer_props):
    def remove_prop(subchart, prop):
        # If subchart is a UnitSpec, then subchart["height"] raises a KeyError
        try:
            if subchart[prop] is not Undefined:
                subchart = subchart.copy()
                subchart[prop] = Undefined
        except KeyError:
            pass
        return subchart

    output_dict = {}

    if not subcharts:
        # No subcharts = nothing to do.
        return output_dict, subcharts

    for prop in layer_props:
        if chart[prop] is Undefined:
            # Top level does not have this prop.
            # Check for consistent props within the subcharts.
            values = []
            for c in subcharts:
                # If c is a UnitSpec, then c["height"] raises a KeyError.
                try:
                    val = c[prop]
                    if val is not Undefined:
                        values.append(val)
                except KeyError:
                    pass
            if len(values) == 0:
                pass
            elif all(v == values[0] for v in values[1:]):
                output_dict[prop] = values[0]
            else:
                raise ValueError(f"There are inconsistent values {values} for {prop}")
        else:
            # Top level has this prop; subchart must either not have the prop
            # or it must be Undefined or identical to proceed.
            if all(
                getattr(c, prop, Undefined) is Undefined or c[prop] == chart[prop]
                for c in subcharts
            ):
                output_dict[prop] = chart[prop]
            else:
                raise ValueError(f"There are inconsistent values {values} for {prop}")
        subcharts = [remove_prop(c, prop) for c in subcharts]

    return output_dict, subcharts


@utils.use_signature(core.SequenceParams)
def sequence(start, stop=None, step=Undefined, as_=Undefined, **kwds):
    """Sequence generator."""
    if stop is None:
        start, stop = 0, start
    params = core.SequenceParams(start=start, stop=stop, step=step, **{"as": as_})
    return core.SequenceGenerator(sequence=params, **kwds)


@utils.use_signature(core.GraticuleParams)
def graticule(**kwds):
    """Graticule generator."""
    if not kwds:
        # graticule: True indicates default parameters
        graticule = True
    else:
        graticule = core.GraticuleParams(**kwds)
    return core.GraticuleGenerator(graticule=graticule)


def sphere() -> core.SphereGenerator:
    """Sphere generator."""
    return core.SphereGenerator(sphere=True)
