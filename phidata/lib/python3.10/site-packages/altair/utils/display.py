import json
import pkgutil
import textwrap
from typing import Callable, Dict, Optional, Tuple, Any, Union
import uuid

from ._vegafusion_data import compile_with_vegafusion, using_vegafusion
from .plugin_registry import PluginRegistry, PluginEnabler
from .mimebundle import spec_to_mimebundle
from .schemapi import validate_jsonschema


# ==============================================================================
# Renderer registry
# ==============================================================================
# MimeBundleType needs to be the same as what are acceptable return values
# for _repr_mimebundle_,
# see https://ipython.readthedocs.io/en/stable/config/integrating.html#MyObject._repr_mimebundle_
MimeBundleDataType = Dict[str, Any]
MimeBundleMetaDataType = Dict[str, Any]
MimeBundleType = Union[
    MimeBundleDataType, Tuple[MimeBundleDataType, MimeBundleMetaDataType]
]
RendererType = Callable[..., MimeBundleType]
# Subtype of MimeBundleType as more specific in the values of the dictionaries
DefaultRendererReturnType = Tuple[
    Dict[str, Union[str, dict]], Dict[str, Dict[str, Any]]
]


class RendererRegistry(PluginRegistry[RendererType]):
    entrypoint_err_messages = {
        "notebook": textwrap.dedent(
            """
            To use the 'notebook' renderer, you must install the vega package
            and the associated Jupyter extension.
            See https://altair-viz.github.io/getting_started/installation.html
            for more information.
            """
        ),
        "altair_viewer": textwrap.dedent(
            """
            To use the 'altair_viewer' renderer, you must install the altair_viewer
            package; see http://github.com/altair-viz/altair_viewer/
            for more information.
            """
        ),
    }

    def set_embed_options(
        self,
        defaultStyle: Optional[Union[bool, str]] = None,
        renderer: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        padding: Optional[int] = None,
        scaleFactor: Optional[float] = None,
        actions: Optional[Union[bool, Dict[str, bool]]] = None,
        format_locale: Optional[Union[str, dict]] = None,
        time_format_locale: Optional[Union[str, dict]] = None,
        **kwargs,
    ) -> PluginEnabler:
        """Set options for embeddings of Vega & Vega-Lite charts.

        Options are fully documented at https://github.com/vega/vega-embed.
        Similar to the `enable()` method, this can be used as either
        a persistent global switch, or as a temporary local setting using
        a context manager (i.e. a `with` statement).

        Parameters
        ----------
        defaultStyle : bool or string
            Specify a default stylesheet for embed actions.
        renderer : string
            The renderer to use for the view. One of "canvas" (default) or "svg"
        width : integer
            The view width in pixels
        height : integer
            The view height in pixels
        padding : integer
            The view padding in pixels
        scaleFactor : number
            The number by which to multiply the width and height (default 1)
            of an exported PNG or SVG image.
        actions : bool or dict
            Determines if action links ("Export as PNG/SVG", "View Source",
            "View Vega" (only for Vega-Lite), "Open in Vega Editor") are
            included with the embedded view. If the value is true, all action
            links will be shown and none if the value is false. This property
            can take a key-value mapping object that maps keys (export, source,
            compiled, editor) to boolean values for determining if
            each action link should be shown.
        format_locale : str or dict
            d3-format locale name or dictionary. Defaults to "en-US" for United States English.
            See https://github.com/d3/d3-format/tree/main/locale for available names and example
            definitions.
        time_format_locale : str or dict
            d3-time-format locale name or dictionary. Defaults to "en-US" for United States English.
            See https://github.com/d3/d3-time-format/tree/main/locale for available names and example
            definitions.
        **kwargs :
            Additional options are passed directly to embed options.
        """
        options: Dict[str, Optional[Union[bool, str, float, Dict[str, bool]]]] = {
            "defaultStyle": defaultStyle,
            "renderer": renderer,
            "width": width,
            "height": height,
            "padding": padding,
            "scaleFactor": scaleFactor,
            "actions": actions,
            "formatLocale": format_locale,
            "timeFormatLocale": time_format_locale,
        }
        kwargs.update({key: val for key, val in options.items() if val is not None})
        return self.enable(None, embed_options=kwargs)


# ==============================================================================
# VegaLite v1/v2 renderer logic
# ==============================================================================


class Displayable:
    """A base display class for VegaLite v1/v2.

    This class takes a VegaLite v1/v2 spec and does the following:

    1. Optionally validates the spec against a schema.
    2. Uses the RendererPlugin to grab a renderer and call it when the
       IPython/Jupyter display method (_repr_mimebundle_) is called.

    The spec passed to this class must be fully schema compliant and already
    have the data portion of the spec fully processed and ready to serialize.
    In practice, this means, the data portion of the spec should have been passed
    through appropriate data model transformers.
    """

    renderers: Optional[RendererRegistry] = None
    schema_path = ("altair", "")

    def __init__(self, spec: dict, validate: bool = False) -> None:
        self.spec = spec
        self.validate = validate
        self._validate()

    def _validate(self) -> None:
        """Validate the spec against the schema."""
        data = pkgutil.get_data(*self.schema_path)
        assert data is not None
        schema_dict: dict = json.loads(data.decode("utf-8"))
        validate_jsonschema(
            self.spec,
            schema_dict,
        )

    def _repr_mimebundle_(
        self, include: Any = None, exclude: Any = None
    ) -> MimeBundleType:
        """Return a MIME bundle for display in Jupyter frontends."""
        if self.renderers is not None:
            renderer_func = self.renderers.get()
            assert renderer_func is not None
            return renderer_func(self.spec)
        else:
            return {}


def default_renderer_base(
    spec: dict, mime_type: str, str_repr: str, **options
) -> DefaultRendererReturnType:
    """A default renderer for Vega or VegaLite that works for modern frontends.

    This renderer works with modern frontends (JupyterLab, nteract) that know
    how to render the custom VegaLite MIME type listed above.
    """
    # Local import to avoid circular ImportError
    from altair.vegalite.v5.display import VEGA_MIME_TYPE, VEGALITE_MIME_TYPE

    assert isinstance(spec, dict)
    bundle: Dict[str, Union[str, dict]] = {}
    metadata: Dict[str, Dict[str, Any]] = {}

    if using_vegafusion():
        spec = compile_with_vegafusion(spec)

        # Swap mimetype from Vega-Lite to Vega.
        # If mimetype was JSON, leave it alone
        if mime_type == VEGALITE_MIME_TYPE:
            mime_type = VEGA_MIME_TYPE

    bundle[mime_type] = spec
    bundle["text/plain"] = str_repr
    if options:
        metadata[mime_type] = options
    return bundle, metadata


def json_renderer_base(
    spec: dict, str_repr: str, **options
) -> DefaultRendererReturnType:
    """A renderer that returns a MIME type of application/json.

    In JupyterLab/nteract this is rendered as a nice JSON tree.
    """
    return default_renderer_base(
        spec, mime_type="application/json", str_repr=str_repr, **options
    )


class HTMLRenderer:
    """Object to render charts as HTML, with a unique output div each time"""

    def __init__(self, output_div: str = "altair-viz-{}", **kwargs) -> None:
        self._output_div = output_div
        self.kwargs = kwargs

    @property
    def output_div(self) -> str:
        return self._output_div.format(uuid.uuid4().hex)

    def __call__(self, spec: dict, **metadata) -> Dict[str, str]:
        kwargs = self.kwargs.copy()
        kwargs.update(metadata)
        # To get proper return value type, would need to write complex
        # overload signatures for spec_to_mimebundle based on `format`
        return spec_to_mimebundle(  # type: ignore[return-value]
            spec, format="html", output_div=self.output_div, **kwargs
        )
