.. _bytes-ops:

Native bytes operations
========================

These ``bytes`` operations have fast, optimized implementations. Other
bytes operations use generic implementations that are often slower.

Construction
------------

* Bytes literal
* ``bytes(x: list)``

Operators
---------

* Concatenation (``b1 + b2``)
* Indexing (``b[n]``)
* Slicing (``b[n:m]``, ``b[n:]``, ``b[:m]``)
* Comparisons (``==``, ``!=``)

.. _bytes-methods:

Methods
-------

* ``b.decode()``
* ``b.decode(encoding: str)``
* ``b.decode(encoding: str, errors: str)``
* ``b.join(x: Iterable)``

.. note::

    :ref:`str.encode() <str-methods>` is also optimized.

Formatting
----------

A subset of % formatting operations are optimized (``b"..." % (...)``).

Functions
---------

* ``len(b: bytes)``
* ``ord(b: bytes)``
