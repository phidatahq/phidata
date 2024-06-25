from typing import Callable
from altair.utils import PluginRegistry

# ==============================================================================
# Vega-Lite to Vega compiler registry
# ==============================================================================
VegaLiteCompilerType = Callable[[dict], dict]


class VegaLiteCompilerRegistry(PluginRegistry[VegaLiteCompilerType]):
    pass
