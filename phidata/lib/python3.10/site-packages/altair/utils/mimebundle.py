from typing import Literal, Optional, Union, cast, Tuple

from .deprecation import AltairDeprecationWarning
from .html import spec_to_html
from ._importers import import_vl_convert, vl_version_for_vl_convert
import struct
import warnings


def spec_to_mimebundle(
    spec: dict,
    format: Literal["html", "json", "png", "svg", "pdf", "vega", "vega-lite"],
    mode: Optional[Literal["vega-lite"]] = None,
    vega_version: Optional[str] = None,
    vegaembed_version: Optional[str] = None,
    vegalite_version: Optional[str] = None,
    embed_options: Optional[dict] = None,
    engine: Optional[Literal["vl-convert", "altair_saver"]] = None,
    **kwargs,
) -> Union[dict, Tuple[dict, dict]]:
    """Convert a vega-lite specification to a mimebundle

    The mimebundle type is controlled by the ``format`` argument, which can be
    one of the following ['html', 'json', 'png', 'svg', 'pdf', 'vega', 'vega-lite']

    Parameters
    ----------
    spec : dict
        a dictionary representing a vega-lite plot spec
    format : string {'html', 'json', 'png', 'svg', 'pdf', 'vega', 'vega-lite'}
        the file format to be saved.
    mode : string {'vega-lite'}
        The rendering mode.
    vega_version : string
        The version of vega.js to use
    vegaembed_version : string
        The version of vegaembed.js to use
    vegalite_version : string
        The version of vegalite.js to use. Only required if mode=='vega-lite'
    embed_options : dict (optional)
        The vegaEmbed options dictionary. Defaults to the embed options set with
        alt.renderers.set_embed_options().
        (See https://github.com/vega/vega-embed for details)
    engine: string {'vl-convert', 'altair_saver'}
        the conversion engine to use for 'png', 'svg', 'pdf', and 'vega' formats
    **kwargs :
        Additional arguments will be passed to the generating function

    Returns
    -------
    output : dict
        a mime-bundle representing the image

    Note
    ----
    The png, svg, pdf, and vega outputs require the altair_saver package
    """
    # Local import to avoid circular ImportError
    from altair.utils.display import (
        compile_with_vegafusion,
        using_vegafusion,
    )
    from altair import renderers

    if mode != "vega-lite":
        raise ValueError("mode must be 'vega-lite'")

    internal_mode: Literal["vega-lite", "vega"] = mode
    if using_vegafusion():
        spec = compile_with_vegafusion(spec)
        internal_mode = "vega"

    # Default to the embed options set by alt.renderers.set_embed_options
    if embed_options is None:
        final_embed_options = renderers.options.get("embed_options", {})
    else:
        final_embed_options = embed_options

    embed_options = preprocess_embed_options(final_embed_options)

    if format in ["png", "svg", "pdf", "vega"]:
        format = cast(Literal["png", "svg", "pdf", "vega"], format)
        return _spec_to_mimebundle_with_engine(
            spec,
            format,
            internal_mode,
            engine=engine,
            format_locale=embed_options.get("formatLocale", None),
            time_format_locale=embed_options.get("timeFormatLocale", None),
            **kwargs,
        )
    if format == "html":
        html = spec_to_html(
            spec,
            mode=internal_mode,
            vega_version=vega_version,
            vegaembed_version=vegaembed_version,
            vegalite_version=vegalite_version,
            embed_options=embed_options,
            **kwargs,
        )
        return {"text/html": html}
    if format == "vega-lite":
        if vegalite_version is None:
            raise ValueError("Must specify vegalite_version")
        return {"application/vnd.vegalite.v{}+json".format(vegalite_version[0]): spec}
    if format == "json":
        return {"application/json": spec}
    raise ValueError(
        "format must be one of "
        "['html', 'json', 'png', 'svg', 'pdf', 'vega', 'vega-lite']"
    )


def _spec_to_mimebundle_with_engine(
    spec: dict,
    format: Literal["png", "svg", "pdf", "vega"],
    mode: Literal["vega-lite", "vega"],
    format_locale: Optional[Union[str, dict]] = None,
    time_format_locale: Optional[Union[str, dict]] = None,
    **kwargs,
) -> Union[dict, Tuple[dict, dict]]:
    """Helper for Vega-Lite to mimebundle conversions that require an engine

    Parameters
    ----------
    spec : dict
        a dictionary representing a vega-lite plot spec
    format : string {'png', 'svg', 'pdf', 'vega'}
        the format of the mimebundle to be returned
    mode : string {'vega-lite', 'vega'}
        The rendering mode.
    engine: string {'vl-convert', 'altair_saver'}
        the conversion engine to use
    format_locale : str or dict
        d3-format locale name or dictionary. Defaults to "en-US" for United States English.
        See https://github.com/d3/d3-format/tree/main/locale for available names and example
        definitions.
    time_format_locale : str or dict
        d3-time-format locale name or dictionary. Defaults to "en-US" for United States English.
        See https://github.com/d3/d3-time-format/tree/main/locale for available names and example
        definitions.
    **kwargs :
        Additional arguments will be passed to the conversion function
    """
    # Normalize the engine string (if any) by lower casing
    # and removing underscores and hyphens
    engine = kwargs.pop("engine", None)
    normalized_engine = _validate_normalize_engine(engine, format)

    if normalized_engine == "vlconvert":
        vlc = import_vl_convert()
        vl_version = vl_version_for_vl_convert()
        if format == "vega":
            if mode == "vega":
                vg = spec
            else:
                vg = vlc.vegalite_to_vega(spec, vl_version=vl_version)
            return {"application/vnd.vega.v5+json": vg}
        elif format == "svg":
            if mode == "vega":
                svg = vlc.vega_to_svg(
                    spec,
                    format_locale=format_locale,
                    time_format_locale=time_format_locale,
                )
            else:
                svg = vlc.vegalite_to_svg(
                    spec,
                    vl_version=vl_version,
                    format_locale=format_locale,
                    time_format_locale=time_format_locale,
                )
            return {"image/svg+xml": svg}
        elif format == "png":
            scale = kwargs.get("scale_factor", 1)
            # The default ppi for a PNG file is 72
            default_ppi = 72
            ppi = kwargs.get("ppi", default_ppi)
            if mode == "vega":
                png = vlc.vega_to_png(
                    spec,
                    scale=scale,
                    ppi=ppi,
                    format_locale=format_locale,
                    time_format_locale=time_format_locale,
                )
            else:
                png = vlc.vegalite_to_png(
                    spec,
                    vl_version=vl_version,
                    scale=scale,
                    ppi=ppi,
                    format_locale=format_locale,
                    time_format_locale=time_format_locale,
                )
            factor = ppi / default_ppi
            w, h = _pngxy(png)
            return {"image/png": png}, {
                "image/png": {"width": w / factor, "height": h / factor}
            }
        elif format == "pdf":
            scale = kwargs.get("scale_factor", 1)
            if mode == "vega":
                pdf = vlc.vega_to_pdf(
                    spec,
                    scale=scale,
                    format_locale=format_locale,
                    time_format_locale=time_format_locale,
                )
            else:
                pdf = vlc.vegalite_to_pdf(
                    spec,
                    vl_version=vl_version,
                    scale=scale,
                    format_locale=format_locale,
                    time_format_locale=time_format_locale,
                )
            return {"application/pdf": pdf}
        else:
            # This should be validated above
            # but raise exception for the sake of future development
            raise ValueError("Unexpected format {fmt!r}".format(fmt=format))
    elif normalized_engine == "altairsaver":
        warnings.warn(
            "The altair_saver export engine is deprecated and will be removed in a future version.\n"
            "Please migrate to the vl-convert engine",
            AltairDeprecationWarning,
            stacklevel=1,
        )
        import altair_saver

        return altair_saver.render(spec, format, mode=mode, **kwargs)
    else:
        # This should be validated above
        # but raise exception for the sake of future development
        raise ValueError(
            "Unexpected normalized_engine {eng!r}".format(eng=normalized_engine)
        )


def _validate_normalize_engine(
    engine: Optional[Literal["vl-convert", "altair_saver"]],
    format: Literal["png", "svg", "pdf", "vega"],
) -> str:
    """Helper to validate and normalize the user-provided engine

    engine : {None, 'vl-convert', 'altair_saver'}
        the user-provided engine string
    format : string {'png', 'svg', 'pdf', 'vega'}
        the format of the mimebundle to be returned
    """
    # Try to import vl_convert
    try:
        vlc = import_vl_convert()
    except ImportError:
        vlc = None

    # Try to import altair_saver
    try:
        import altair_saver
    except ImportError:
        altair_saver = None

    # Normalize engine string by lower casing and removing underscores and hyphens
    normalized_engine = (
        None if engine is None else engine.lower().replace("-", "").replace("_", "")
    )

    # Validate or infer default value of normalized_engine
    if normalized_engine == "vlconvert":
        if vlc is None:
            raise ValueError(
                "The 'vl-convert' conversion engine requires the vl-convert-python package"
            )
    elif normalized_engine == "altairsaver":
        if altair_saver is None:
            raise ValueError(
                "The 'altair_saver' conversion engine requires the altair_saver package"
            )
    elif normalized_engine is None:
        if vlc is not None:
            normalized_engine = "vlconvert"
        elif altair_saver is not None:
            normalized_engine = "altairsaver"
        else:
            raise ValueError(
                "Saving charts in {fmt!r} format requires the vl-convert-python or altair_saver package: "
                "see http://github.com/altair-viz/altair_saver/".format(fmt=format)
            )
    else:
        raise ValueError(
            "Invalid conversion engine {engine!r}. Expected one of {valid!r}".format(
                engine=engine, valid=("vl-convert", "altair_saver")
            )
        )
    return normalized_engine


def _pngxy(data):
    """read the (width, height) from a PNG header

    Taken from IPython.display
    """
    ihdr = data.index(b"IHDR")
    # next 8 bytes are width/height
    return struct.unpack(">ii", data[ihdr + 4 : ihdr + 12])


def preprocess_embed_options(embed_options: dict) -> dict:
    """Preprocess embed options to a form compatible with Vega Embed

    Parameters
    ----------
    embed_options : dict
        The embed options dictionary to preprocess.

    Returns
    -------
    embed_opts : dict
        The preprocessed embed options dictionary.
    """
    embed_options = (embed_options or {}).copy()

    # Convert locale strings to objects compatible with Vega Embed using vl-convert
    format_locale = embed_options.get("formatLocale", None)
    if isinstance(format_locale, str):
        vlc = import_vl_convert()
        embed_options["formatLocale"] = vlc.get_format_locale(format_locale)

    time_format_locale = embed_options.get("timeFormatLocale", None)
    if isinstance(time_format_locale, str):
        vlc = import_vl_convert()
        embed_options["timeFormatLocale"] = vlc.get_time_format_locale(
            time_format_locale
        )

    return embed_options
