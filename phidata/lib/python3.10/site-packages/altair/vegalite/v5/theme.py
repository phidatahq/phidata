"""Tools for enabling and registering chart themes"""

from typing import Dict, Union, Final

from ...utils.theme import ThemeRegistry

VEGA_THEMES = [
    "ggplot2",
    "quartz",
    "vox",
    "fivethirtyeight",
    "dark",
    "latimes",
    "urbaninstitute",
    "excel",
    "googlecharts",
    "powerbi",
]


class VegaTheme:
    """Implementation of a builtin vega theme."""

    def __init__(self, theme: str) -> None:
        self.theme = theme

    def __call__(self) -> Dict[str, Dict[str, Dict[str, Union[str, int]]]]:
        return {
            "usermeta": {"embedOptions": {"theme": self.theme}},
            "config": {"view": {"continuousWidth": 300, "continuousHeight": 300}},
        }

    def __repr__(self) -> str:
        return "VegaTheme({!r})".format(self.theme)


# The entry point group that can be used by other packages to declare other
# themes that will be auto-detected. Explicit registration is also
# allowed by the PluginRegistery API.
ENTRY_POINT_GROUP: Final = "altair.vegalite.v5.theme"
themes = ThemeRegistry(entry_point_group=ENTRY_POINT_GROUP)

themes.register(
    "default",
    lambda: {"config": {"view": {"continuousWidth": 300, "continuousHeight": 300}}},
)
themes.register(
    "opaque",
    lambda: {
        "config": {
            "background": "white",
            "view": {"continuousWidth": 300, "continuousHeight": 300},
        }
    },
)
themes.register("none", lambda: {})

for theme in VEGA_THEMES:
    themes.register(theme, VegaTheme(theme))

themes.enable("default")
