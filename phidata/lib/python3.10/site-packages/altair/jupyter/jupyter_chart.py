import json
import anywidget
import traitlets
import pathlib
from typing import Any, Set, Optional

import altair as alt
from altair.utils._vegafusion_data import (
    using_vegafusion,
    compile_to_vegafusion_chart_state,
)
from altair import TopLevelSpec
from altair.utils.selection import IndexSelection, PointSelection, IntervalSelection

_here = pathlib.Path(__file__).parent


class Params(traitlets.HasTraits):
    """
    Traitlet class storing a JupyterChart's params
    """

    def __init__(self, trait_values):
        super().__init__()

        for key, value in trait_values.items():
            if isinstance(value, (int, float)):
                traitlet_type = traitlets.Float()
            elif isinstance(value, str):
                traitlet_type = traitlets.Unicode()
            elif isinstance(value, list):
                traitlet_type = traitlets.List()
            elif isinstance(value, dict):
                traitlet_type = traitlets.Dict()
            else:
                traitlet_type = traitlets.Any()

            # Add the new trait.
            self.add_traits(**{key: traitlet_type})

            # Set the trait's value.
            setattr(self, key, value)

    def __repr__(self):
        return f"Params({self.trait_values()})"


class Selections(traitlets.HasTraits):
    """
    Traitlet class storing a JupyterChart's selections
    """

    def __init__(self, trait_values):
        super().__init__()

        for key, value in trait_values.items():
            if isinstance(value, IndexSelection):
                traitlet_type = traitlets.Instance(IndexSelection)
            elif isinstance(value, PointSelection):
                traitlet_type = traitlets.Instance(PointSelection)
            elif isinstance(value, IntervalSelection):
                traitlet_type = traitlets.Instance(IntervalSelection)
            else:
                raise ValueError(f"Unexpected selection type: {type(value)}")

            # Add the new trait.
            self.add_traits(**{key: traitlet_type})

            # Set the trait's value.
            setattr(self, key, value)

            # Make read-only
            self.observe(self._make_read_only, names=key)

    def __repr__(self):
        return f"Selections({self.trait_values()})"

    def _make_read_only(self, change):
        """
        Work around to make traits read-only, but still allow us to change
        them internally
        """
        if change["name"] in self.traits() and change["old"] != change["new"]:
            self._set_value(change["name"], change["old"])
        raise ValueError(
            "Selections may not be set from Python.\n"
            f"Attempted to set select: {change['name']}"
        )

    def _set_value(self, key, value):
        self.unobserve(self._make_read_only, names=key)
        setattr(self, key, value)
        self.observe(self._make_read_only, names=key)


def load_js_src() -> str:
    return (_here / "js" / "index.js").read_text()


class JupyterChart(anywidget.AnyWidget):
    _esm = load_js_src()
    _css = r"""
    .vega-embed {
        /* Make sure action menu isn't cut off */
        overflow: visible;
    }
    """

    # Public traitlets
    chart = traitlets.Instance(TopLevelSpec, allow_none=True)
    spec = traitlets.Dict(allow_none=True).tag(sync=True)
    debounce_wait = traitlets.Float(default_value=10).tag(sync=True)
    max_wait = traitlets.Bool(default_value=True).tag(sync=True)
    local_tz = traitlets.Unicode(default_value=None, allow_none=True).tag(sync=True)
    debug = traitlets.Bool(default_value=False)
    embed_options = traitlets.Dict(default_value=None, allow_none=True).tag(sync=True)

    # Internal selection traitlets
    _selection_types = traitlets.Dict()
    _vl_selections = traitlets.Dict().tag(sync=True)

    # Internal param traitlets
    _params = traitlets.Dict().tag(sync=True)

    # Internal comm traitlets for VegaFusion support
    _chart_state = traitlets.Any(allow_none=True)
    _js_watch_plan = traitlets.Any(allow_none=True).tag(sync=True)
    _js_to_py_updates = traitlets.Any(allow_none=True).tag(sync=True)
    _py_to_js_updates = traitlets.Any(allow_none=True).tag(sync=True)

    # Track whether charts are configured for offline use
    _is_offline = False

    @classmethod
    def enable_offline(cls, offline: bool = True):
        """
        Configure JupyterChart's offline behavior

        Parameters
        ----------
        offline: bool
            If True, configure JupyterChart to operate in offline mode where JavaScript
            dependencies are loaded from vl-convert.
            If False, configure it to operate in online mode where JavaScript dependencies
            are loaded from CDN dynamically. This is the default behavior.
        """
        from altair.utils._importers import import_vl_convert, vl_version_for_vl_convert

        if offline:
            if cls._is_offline:
                # Already offline
                return

            vlc = import_vl_convert()

            src_lines = load_js_src().split("\n")

            # Remove leading lines with only whitespace, comments, or imports
            while src_lines and (
                len(src_lines[0].strip()) == 0
                or src_lines[0].startswith("import")
                or src_lines[0].startswith("//")
            ):
                src_lines.pop(0)

            src = "\n".join(src_lines)

            # vl-convert's javascript_bundle function creates a self-contained JavaScript bundle
            # for JavaScript snippets that import from a small set of dependencies that
            # vl-convert includes. To see the available imports and their imported names, run
            #       import vl_convert as vlc
            #       help(vlc.javascript_bundle)
            bundled_src = vlc.javascript_bundle(
                src, vl_version=vl_version_for_vl_convert()
            )
            cls._esm = bundled_src
            cls._is_offline = True
        else:
            cls._esm = load_js_src()
            cls._is_offline = False

    def __init__(
        self,
        chart: TopLevelSpec,
        debounce_wait: int = 10,
        max_wait: bool = True,
        debug: bool = False,
        embed_options: Optional[dict] = None,
        **kwargs: Any,
    ):
        """
        Jupyter Widget for displaying and updating Altair Charts, and
        retrieving selection and parameter values

        Parameters
        ----------
        chart: Chart
            Altair Chart instance
        debounce_wait: int
             Debouncing wait time in milliseconds. Updates will be sent from the client to the kernel
             after debounce_wait milliseconds of no chart interactions.
        max_wait: bool
             If True (default), updates will be sent from the client to the kernel every debounce_wait
             milliseconds even if there are ongoing chart interactions. If False, updates will not be
             sent until chart interactions have completed.
        debug: bool
             If True, debug messages will be printed
        embed_options: dict
             Options to pass to vega-embed.
             See https://github.com/vega/vega-embed?tab=readme-ov-file#options
        """
        self.params = Params({})
        self.selections = Selections({})
        super().__init__(
            chart=chart,
            debounce_wait=debounce_wait,
            max_wait=max_wait,
            debug=debug,
            embed_options=embed_options,
            **kwargs,
        )

    @traitlets.observe("chart")
    def _on_change_chart(self, change):
        """
        Internal callback function that updates the JupyterChart's internal
        state when the wrapped Chart instance changes
        """
        new_chart = change.new
        selection_watches = []
        selection_types = {}
        initial_params = {}
        initial_vl_selections = {}
        empty_selections = {}

        if new_chart is None:
            with self.hold_sync():
                self.spec = None
                self._selection_types = selection_types
                self._vl_selections = initial_vl_selections
                self._params = initial_params
            return

        params = getattr(new_chart, "params", [])

        if params is not alt.Undefined:
            for param in new_chart.params:
                if isinstance(param.name, alt.ParameterName):
                    clean_name = param.name.to_json().strip('"')
                else:
                    clean_name = param.name

                select = getattr(param, "select", alt.Undefined)

                if select != alt.Undefined:
                    if not isinstance(select, dict):
                        select = select.to_dict()

                    select_type = select["type"]
                    if select_type == "point":
                        if not (
                            select.get("fields", None) or select.get("encodings", None)
                        ):
                            # Point selection with no associated fields or encodings specified.
                            # This is an index-based selection
                            selection_types[clean_name] = "index"
                            empty_selections[clean_name] = IndexSelection(
                                name=clean_name, value=[], store=[]
                            )
                        else:
                            selection_types[clean_name] = "point"
                            empty_selections[clean_name] = PointSelection(
                                name=clean_name, value=[], store=[]
                            )
                    elif select_type == "interval":
                        selection_types[clean_name] = "interval"
                        empty_selections[clean_name] = IntervalSelection(
                            name=clean_name, value={}, store=[]
                        )
                    else:
                        raise ValueError(f"Unexpected selection type {select.type}")
                    selection_watches.append(clean_name)
                    initial_vl_selections[clean_name] = {"value": None, "store": []}
                else:
                    clean_value = param.value if param.value != alt.Undefined else None
                    initial_params[clean_name] = clean_value

        # Handle the params generated by transforms
        for param_name in collect_transform_params(new_chart):
            initial_params[param_name] = None

        # Setup params
        self.params = Params(initial_params)

        def on_param_traitlet_changed(param_change):
            new_params = dict(self._params)
            new_params[param_change["name"]] = param_change["new"]
            self._params = new_params

        self.params.observe(on_param_traitlet_changed)

        # Setup selections
        self.selections = Selections(empty_selections)

        # Update properties all together
        with self.hold_sync():
            if using_vegafusion():
                if self.local_tz is None:
                    self.spec = None

                    def on_local_tz_change(change):
                        self._init_with_vegafusion(change["new"])

                    self.observe(on_local_tz_change, ["local_tz"])
                else:
                    self._init_with_vegafusion(self.local_tz)
            else:
                self.spec = new_chart.to_dict()
            self._selection_types = selection_types
            self._vl_selections = initial_vl_selections
            self._params = initial_params

    def _init_with_vegafusion(self, local_tz: str):
        if self.chart is not None:
            vegalite_spec = self.chart.to_dict(context={"pre_transform": False})
            with self.hold_sync():
                self._chart_state = compile_to_vegafusion_chart_state(
                    vegalite_spec, local_tz
                )
                self._js_watch_plan = self._chart_state.get_watch_plan()[
                    "client_to_server"
                ]
                self.spec = self._chart_state.get_transformed_spec()

                # Callback to update chart state and send updates back to client
                def on_js_to_py_updates(change):
                    if self.debug:
                        updates_str = json.dumps(change["new"], indent=2)
                        print(
                            f"JavaScript to Python VegaFusion updates:\n {updates_str}"
                        )
                    updates = self._chart_state.update(change["new"])
                    if self.debug:
                        updates_str = json.dumps(updates, indent=2)
                        print(
                            f"Python to JavaScript VegaFusion updates:\n {updates_str}"
                        )
                    self._py_to_js_updates = updates

                self.observe(on_js_to_py_updates, ["_js_to_py_updates"])

    @traitlets.observe("_params")
    def _on_change_params(self, change):
        for param_name, value in change.new.items():
            setattr(self.params, param_name, value)

    @traitlets.observe("_vl_selections")
    def _on_change_selections(self, change):
        """
        Internal callback function that updates the JupyterChart's public
        selections traitlet in response to changes that the JavaScript logic
        makes to the internal _selections traitlet.
        """
        for selection_name, selection_dict in change.new.items():
            value = selection_dict["value"]
            store = selection_dict["store"]
            selection_type = self._selection_types[selection_name]
            if selection_type == "index":
                self.selections._set_value(
                    selection_name,
                    IndexSelection.from_vega(selection_name, signal=value, store=store),
                )
            elif selection_type == "point":
                self.selections._set_value(
                    selection_name,
                    PointSelection.from_vega(selection_name, signal=value, store=store),
                )
            elif selection_type == "interval":
                self.selections._set_value(
                    selection_name,
                    IntervalSelection.from_vega(
                        selection_name, signal=value, store=store
                    ),
                )


def collect_transform_params(chart: TopLevelSpec) -> Set[str]:
    """
    Collect the names of params that are defined by transforms

    Parameters
    ----------
    chart: Chart from which to extract transform params

    Returns
    -------
    set of param names
    """
    transform_params = set()

    # Handle recursive case
    for prop in ("layer", "concat", "hconcat", "vconcat"):
        for child in getattr(chart, prop, []):
            transform_params.update(collect_transform_params(child))

    # Handle chart's own transforms
    transforms = getattr(chart, "transform", [])
    transforms = transforms if transforms != alt.Undefined else []
    for tx in transforms:
        if hasattr(tx, "param"):
            transform_params.add(tx.param)

    return transform_params
