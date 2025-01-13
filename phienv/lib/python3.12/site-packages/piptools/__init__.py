from __future__ import annotations

import locale

from click import secho

# Needed for locale.getpreferredencoding(False) to work
# in pip._internal.utils.encoding.auto_decode
try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error as e:  # pragma: no cover
    # setlocale can apparently crash if locale are uninitialized
    secho(f"Ignoring error when setting locale: {e}", fg="red")
