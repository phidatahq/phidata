import json
import pathlib
import warnings
from typing import IO, Union, Optional, Literal

from .mimebundle import spec_to_mimebundle
from ..vegalite.v5.data import data_transformers
from altair.utils._vegafusion_data import using_vegafusion


def write_file_or_filename(
    fp: Union[str, pathlib.PurePath, IO],
    content: Union[str, bytes],
    mode: str = "w",
    encoding: Optional[str] = None,
) -> None:
    """Write content to fp, whether fp is a string, a pathlib Path or a
    file-like object"""
    if isinstance(fp, str) or isinstance(fp, pathlib.PurePath):
        with open(file=fp, mode=mode, encoding=encoding) as f:
            f.write(content)
    else:
        fp.write(content)


def set_inspect_format_argument(
    format: Optional[str], fp: Union[str, pathlib.PurePath, IO], inline: bool
) -> str:
    """Inspect the format argument in the save function"""
    if format is None:
        if isinstance(fp, str):
            format = fp.split(".")[-1]
        elif isinstance(fp, pathlib.PurePath):
            format = fp.suffix.lstrip(".")
        else:
            raise ValueError(
                "must specify file format: "
                "['png', 'svg', 'pdf', 'html', 'json', 'vega']"
            )

    if format != "html" and inline:
        warnings.warn("inline argument ignored for non HTML formats.", stacklevel=1)

    return format


def set_inspect_mode_argument(
    mode: Optional[Literal["vega-lite"]],
    embed_options: dict,
    spec: dict,
    vegalite_version: Optional[str],
) -> Literal["vega-lite"]:
    """Inspect the mode argument in the save function"""
    if mode is None:
        if "mode" in embed_options:
            mode = embed_options["mode"]
        elif "$schema" in spec:
            mode = spec["$schema"].split("/")[-2]
        else:
            mode = "vega-lite"

    if mode != "vega-lite":
        raise ValueError("mode must be 'vega-lite', " "not '{}'".format(mode))

    if mode == "vega-lite" and vegalite_version is None:
        raise ValueError("must specify vega-lite version")

    return mode


def save(
    chart,
    fp: Union[str, pathlib.PurePath, IO],
    vega_version: Optional[str],
    vegaembed_version: Optional[str],
    format: Optional[Literal["json", "html", "png", "svg", "pdf"]] = None,
    mode: Optional[Literal["vega-lite"]] = None,
    vegalite_version: Optional[str] = None,
    embed_options: Optional[dict] = None,
    json_kwds: Optional[dict] = None,
    webdriver: Optional[Literal["chrome", "firefox"]] = None,
    scale_factor: float = 1,
    engine: Optional[Literal["vl-convert", "altair_saver"]] = None,
    inline: bool = False,
    **kwargs,
) -> None:
    """Save a chart to file in a variety of formats

    Supported formats are [json, html, png, svg, pdf]

    Parameters
    ----------
    chart : alt.Chart
        the chart instance to save
    fp : string filename, pathlib.Path or file-like object
        file to which to write the chart.
    format : string (optional)
        the format to write: one of ['json', 'html', 'png', 'svg', 'pdf'].
        If not specified, the format will be determined from the filename.
    mode : string (optional)
        Must be 'vega-lite'. If not specified, then infer the mode from
        the '$schema' property of the spec, or the ``opt`` dictionary.
        If it's not specified in either of those places, then use 'vega-lite'.
    vega_version : string (optional)
        For html output, the version of vega.js to use
    vegalite_version : string (optional)
        For html output, the version of vegalite.js to use
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
    scale_factor : float (optional)
        scale_factor to use to change size/resolution of png or svg output
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
    if json_kwds is None:
        json_kwds = {}

    format = set_inspect_format_argument(format, fp, inline)  # type: ignore[assignment]

    def perform_save():
        spec = chart.to_dict(context={"pre_transform": False})

        inner_mode = set_inspect_mode_argument(
            mode, embed_options or {}, spec, vegalite_version
        )

        if format == "json":
            json_spec = json.dumps(spec, **json_kwds)
            write_file_or_filename(
                fp, json_spec, mode="w", encoding=kwargs.get("encoding", "utf-8")
            )
        elif format == "html":
            if inline:
                kwargs["template"] = "inline"
            mimebundle = spec_to_mimebundle(
                spec=spec,
                format=format,
                mode=inner_mode,
                vega_version=vega_version,
                vegalite_version=vegalite_version,
                vegaembed_version=vegaembed_version,
                embed_options=embed_options,
                json_kwds=json_kwds,
                **kwargs,
            )
            write_file_or_filename(
                fp,
                mimebundle["text/html"],
                mode="w",
                encoding=kwargs.get("encoding", "utf-8"),
            )
        elif format in ["png", "svg", "pdf", "vega"]:
            mimebundle = spec_to_mimebundle(
                spec=spec,
                format=format,
                mode=inner_mode,
                vega_version=vega_version,
                vegalite_version=vegalite_version,
                vegaembed_version=vegaembed_version,
                embed_options=embed_options,
                webdriver=webdriver,
                scale_factor=scale_factor,
                engine=engine,
                **kwargs,
            )
            if format == "png":
                write_file_or_filename(fp, mimebundle[0]["image/png"], mode="wb")
            elif format == "pdf":
                write_file_or_filename(fp, mimebundle["application/pdf"], mode="wb")
            else:
                encoding = kwargs.get("encoding", "utf-8")
                write_file_or_filename(
                    fp, mimebundle["image/svg+xml"], mode="w", encoding=encoding
                )
        else:
            raise ValueError("Unsupported format: '{}'".format(format))

    if using_vegafusion():
        # When the vegafusion data transformer is enabled, transforms will be
        # evaluated during save and the resulting data will be included in the
        # vega specification that is saved.
        with data_transformers.disable_max_rows():
            perform_save()
    else:
        # Temporarily turn off any data transformers so that all data is inlined
        # when calling chart.to_dict. This is relevant for vl-convert which cannot access
        # local json files which could be created by a json data transformer. Furthermore,
        # we don't exit the with statement until this function completed due to the issue
        # described at https://github.com/vega/vl-convert/issues/31
        with data_transformers.enable("default"), data_transformers.disable_max_rows():
            perform_save()
