import numpy as np
import psycopg2
from psycopg2.extensions import adapt, new_type, register_adapter, register_type
from ..utils import from_db, to_db

__all__ = ['register_vector']


class VectorAdapter(object):
    def __init__(self, vector):
        self._vector = vector

    def getquoted(self):
        return adapt(to_db(self._vector)).getquoted()


def cast_vector(value, cur):
    return from_db(value)


def register_vector(conn_or_curs=None):
    cur = conn_or_curs.cursor() if hasattr(conn_or_curs, 'cursor') else conn_or_curs

    try:
        cur.execute('SELECT NULL::vector')
        oid = cur.description[0][1]
    except psycopg2.errors.UndefinedObject:
        raise psycopg2.ProgrammingError('vector type not found in the database')

    vector = new_type((oid,), 'VECTOR', cast_vector)
    register_type(vector)
    register_adapter(np.ndarray, VectorAdapter)
