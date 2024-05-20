r"""
Provides frozendict, a simple immutable dictionary.
"""

try:
    from ._frozendict import *
    c_ext = True
    del _frozendict
except ImportError:
    from ._frozendict_py import *
    c_ext = False

from .version import version as __version__
from . import monkeypatch
from .cool import *


def _getFrozendictJsonEncoder(BaseJsonEncoder = None):
    if BaseJsonEncoder is None:
        from json.encoder import JSONEncoder
        
        BaseJsonEncoder = JSONEncoder
    
    class FrozendictJsonEncoderInternal(BaseJsonEncoder):
        def default(self, obj):
            if isinstance(obj, frozendict):
                # TODO create a C serializer
                return dict(obj)
            
            return BaseJsonEncoder.default(self, obj)
    
    return FrozendictJsonEncoderInternal


FrozendictJsonEncoder = _getFrozendictJsonEncoder()
monkeypatch.patchOrUnpatchAll(patch = True, warn = False)


from collections.abc import Mapping
Mapping.register(frozendict)
del Mapping


if c_ext:
    __all__ = (frozendict.__name__, )
else:
    __all__ = _frozendict_py.__all__
    del _frozendict_py

# TODO deprecated, to remove in future versions
FrozenOrderedDict = frozendict

__all__ += cool.__all__
__all__ += (FrozendictJsonEncoder.__name__, "FrozenOrderedDict")

del cool
