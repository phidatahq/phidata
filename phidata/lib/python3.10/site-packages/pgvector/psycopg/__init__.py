import psycopg
from psycopg.adapt import Loader, Dumper
from psycopg.pq import Format
from psycopg.types import TypeInfo
from ..utils import from_db, from_db_binary, to_db, to_db_binary

__all__ = ['register_vector']


class VectorDumper(Dumper):

    format = Format.TEXT

    def dump(self, obj):
        return to_db(obj).encode("utf8")


class VectorBinaryDumper(VectorDumper):

    format = Format.BINARY

    def dump(self, obj):
        return to_db_binary(obj)


class VectorLoader(Loader):

    format = Format.TEXT

    def load(self, data):
        if isinstance(data, memoryview):
            data = bytes(data)
        return from_db(data.decode("utf8"))


class VectorBinaryLoader(VectorLoader):

    format = Format.BINARY

    def load(self, data):
        if isinstance(data, memoryview):
            data = bytes(data)
        return from_db_binary(data)


def register_vector(context):
    info = TypeInfo.fetch(context, 'vector')
    register_vector_info(context, info)


async def register_vector_async(context):
    info = await TypeInfo.fetch(context, 'vector')
    register_vector_info(context, info)


def register_vector_info(context, info):
    if info is None:
        raise psycopg.ProgrammingError('vector type not found in the database')
    info.register(context)

    # add oid to anonymous class for set_types
    text_dumper = type('', (VectorDumper,), {'oid': info.oid})
    binary_dumper = type('', (VectorBinaryDumper,), {'oid': info.oid})

    adapters = context.adapters
    adapters.register_dumper('numpy.ndarray', text_dumper)
    adapters.register_dumper('numpy.ndarray', binary_dumper)
    adapters.register_loader(info.oid, VectorLoader)
    adapters.register_loader(info.oid, VectorBinaryLoader)
