import numpy as np
from struct import pack, unpack


def from_db(value):
    # could be ndarray if already cast by lower-level driver
    if value is None or isinstance(value, np.ndarray):
        return value

    return np.array(value[1:-1].split(','), dtype=np.float32)


def from_db_binary(value):
    if value is None:
        return value

    (dim, unused) = unpack('>HH', value[:4])
    return np.frombuffer(value, dtype='>f', count=dim, offset=4).astype(dtype=np.float32)


def to_db(value, dim=None):
    if value is None:
        return value

    if isinstance(value, np.ndarray):
        if value.ndim != 1:
            raise ValueError('expected ndim to be 1')

        if not np.issubdtype(value.dtype, np.integer) and not np.issubdtype(value.dtype, np.floating):
            raise ValueError('dtype must be numeric')

        value = value.tolist()

    if dim is not None and len(value) != dim:
        raise ValueError('expected %d dimensions, not %d' % (dim, len(value)))

    return '[' + ','.join([str(float(v)) for v in value]) + ']'


def to_db_binary(value):
    if value is None:
        return value

    value = np.asarray(value, dtype='>f')

    if value.ndim != 1:
        raise ValueError('expected ndim to be 1')

    return pack('>HH', value.shape[0], 0) + value.tobytes()
