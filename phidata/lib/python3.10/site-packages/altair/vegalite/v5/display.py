import os
from typing import Dict

from ...utils.mimebundle import spec_to_mimebundle
from ..display import (
    Displayable,
    default_renderer_base,
    json_renderer_base,
    RendererRegistry,
    HTMLRenderer,
    DefaultRendererReturnType,
)

from .schema import SCHEMA_VERSION

from typing import Final

VEGALITE_VERSION: Final = SCHEMA_VERSION.lstrip("v")
VEGA_VERSION: Final = "5"
VEGAEMBED_VERSION: Final = "6"


# ==============================================================================
# VegaLite v5 renderer logic
# ==============================================================================


# The MIME type for Vega-Lite 5.x releases.
VEGALITE_MIME_TYPE: Final = "application/vnd.vegalite.v5+json"

# The MIME type for Vega 5.x releases.
VEGA_MIME_TYPE: Final = "application/vnd.vega.v5+json"

# The entry point group that can be used by other packages to declare other
# renderers that will be auto-detected. Explicit registration is also
# allowed by the PluginRegistery API.
ENTRY_POINT_GROUP: Final = "altair.vegalite.v5.renderer"

# The display message when rendering fails
DEFAULT_DISPLAY: Final = f"""\
<VegaLite {VEGALITE_VERSION.split('.')[0]} object>

If you see this message, it means the renderer has not been properly enabled
for the frontend that you are using. For more information, see
https://altair-viz.github.io/user_guide/display_frontends.html#troubleshooting
"""

renderers = RendererRegistry(entry_point_group=ENTRY_POINT_GROUP)

here = os.path.dirname(os.path.realpath(__file__))


def mimetype_renderer(spec: dict, **metadata) -> DefaultRendererReturnType:
    return default_renderer_base(spec, VEGALITE_MIME_TYPE, DEFAULT_DISPLAY, **metadata)


def json_renderer(spec: dict, **metadata) -> DefaultRendererReturnType:
    return json_renderer_base(spec, DEFAULT_DISPLAY, **metadata)


def png_renderer(spec: dict, **metadata) -> Dict[str, bytes]:
    # To get proper return value type, would need to write complex
    # overload signatures for spec_to_mimebundle based on `format`
    return spec_to_mimebundle(  # type: ignore[return-value]
        spec,
        format="png",
        mode="vega-lite",
        vega_version=VEGA_VERSION,
        vegaembed_version=VEGAEMBED_VERSION,
        vegalite_version=VEGALITE_VERSION,
        **metadata,
    )


def svg_renderer(spec: dict, **metadata) -> Dict[str, str]:
    # To get proper return value type, would need to write complex
    # overload signatures for spec_to_mimebundle based on `format`
    return spec_to_mimebundle(  # type: ignore[return-value]
        spec,
        format="svg",
        mode="vega-lite",
        vega_version=VEGA_VERSION,
        vegaembed_version=VEGAEMBED_VERSION,
        vegalite_version=VEGALITE_VERSION,
        **metadata,
    )


def jupyter_renderer(spec: dict, **metadata):
    """Render chart using the JupyterChart Jupyter Widget"""
    from altair import Chart, JupyterChart

    # Configure offline mode
    offline = metadata.get("offline", False)

    # mypy doesn't see the enable_offline class method for some reason
    JupyterChart.enable_offline(offline=offline)  # type: ignore[attr-defined]

    # propagate embed options
    embed_options = metadata.get("embed_options", None)

    # Need to ignore attr-defined mypy rule because mypy doesn't see _repr_mimebundle_
    # conditionally defined in AnyWidget
    return JupyterChart(
        chart=Chart.from_dict(spec), embed_options=embed_options
    )._repr_mimebundle_()  # type: ignore[attr-defined]


def browser_renderer(
    spec: dict, offline=False, using=None, port=0, **metadata
) -> Dict[str, str]:
    from altair.utils._show import open_html_in_browser

    if offline:
        metadata["template"] = "inline"
    mimebundle = spec_to_mimebundle(
        spec,
        format="html",
        mode="vega-lite",
        vega_version=VEGA_VERSION,
        vegaembed_version=VEGAEMBED_VERSION,
        vegalite_version=VEGALITE_VERSION,
        **metadata,
    )

    if isinstance(mimebundle, tuple):
        mimebundle = mimebundle[0]

    html = mimebundle["text/html"]
    open_html_in_browser(html, using=using, port=port)
    return {}


html_renderer = HTMLRenderer(
    mode="vega-lite",
    template="universal",
    vega_version=VEGA_VERSION,
    vegaembed_version=VEGAEMBED_VERSION,
    vegalite_version=VEGALITE_VERSION,
)

renderers.register("default", html_renderer)
renderers.register("html", html_renderer)
renderers.register("colab", html_renderer)
renderers.register("kaggle", html_renderer)
renderers.register("zeppelin", html_renderer)
renderers.register("mimetype", mimetype_renderer)
renderers.register("jupyterlab", mimetype_renderer)
renderers.register("nteract", mimetype_renderer)
renderers.register("json", json_renderer)
renderers.register("png", png_renderer)
renderers.register("svg", svg_renderer)
renderers.register("jupyter", jupyter_renderer)
renderers.register("browser", browser_renderer)
renderers.enable("default")


class VegaLite(Displayable):
    """An IPython/Jupyter display class for rendering VegaLite 5."""

    renderers = renderers
    schema_path = (__name__, "schema/vega-lite-schema.json")


def vegalite(spec: dict, validate: bool = True) -> None:
    """Render and optionally validate a VegaLite 5 spec.

    This will use the currently enabled renderer to render the spec.

    Parameters
    ==========
    spec: dict
        A fully compliant VegaLite 5 spec, with the data portion fully processed.
    validate: bool
        Should the spec be validated against the VegaLite 5 schema?
    """
    from IPython.display import display

    display(VegaLite(spec, validate=validate))
