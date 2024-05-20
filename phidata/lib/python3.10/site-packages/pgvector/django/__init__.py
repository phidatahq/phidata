from django.contrib.postgres.operations import CreateExtension
from django.contrib.postgres.indexes import PostgresIndex
from django.db.models import Field, FloatField, Func, Value
import numpy as np
from .forms import VectorFormField
from ..utils import from_db, to_db

__all__ = ['VectorExtension', 'VectorField', 'IvfflatIndex', 'HnswIndex', 'L2Distance', 'MaxInnerProduct', 'CosineDistance']


class VectorExtension(CreateExtension):
    def __init__(self):
        self.name = 'vector'


# https://docs.djangoproject.com/en/4.2/howto/custom-model-fields/
class VectorField(Field):
    description = 'Vector'
    empty_strings_allowed = False

    def __init__(self, *args, dimensions=None, **kwargs):
        self.dimensions = dimensions
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.dimensions is not None:
            kwargs['dimensions'] = self.dimensions
        return name, path, args, kwargs

    def db_type(self, connection):
        if self.dimensions is None:
            return 'vector'
        return 'vector(%d)' % self.dimensions

    def from_db_value(self, value, expression, connection):
        return from_db(value)

    def to_python(self, value):
        if isinstance(value, list):
            return np.array(value, dtype=np.float32)
        return from_db(value)

    def get_prep_value(self, value):
        return to_db(value)

    def value_to_string(self, obj):
        return self.get_prep_value(self.value_from_object(obj))

    def validate(self, value, model_instance):
        if isinstance(value, np.ndarray):
            value = value.tolist()
        super().validate(value, model_instance)

    def run_validators(self, value):
        if isinstance(value, np.ndarray):
            value = value.tolist()
        super().run_validators(value)

    def formfield(self, **kwargs):
        return super().formfield(form_class=VectorFormField, **kwargs)


class IvfflatIndex(PostgresIndex):
    suffix = 'ivfflat'

    def __init__(self, *expressions, lists=None, **kwargs):
        self.lists = lists
        super().__init__(*expressions, **kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.lists is not None:
            kwargs['lists'] = self.lists
        return path, args, kwargs

    def get_with_params(self):
        with_params = []
        if self.lists is not None:
            with_params.append('lists = %d' % self.lists)
        return with_params


class HnswIndex(PostgresIndex):
    suffix = 'hnsw'

    def __init__(self, *expressions, m=None, ef_construction=None, **kwargs):
        self.m = m
        self.ef_construction = ef_construction
        super().__init__(*expressions, **kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.m is not None:
            kwargs['m'] = self.m
        if self.ef_construction is not None:
            kwargs['ef_construction'] = self.ef_construction
        return path, args, kwargs

    def get_with_params(self):
        with_params = []
        if self.m is not None:
            with_params.append('m = %d' % self.m)
        if self.ef_construction is not None:
            with_params.append('ef_construction = %d' % self.ef_construction)
        return with_params


class DistanceBase(Func):
    output_field = FloatField()

    def __init__(self, expression, vector, **extra):
        if not hasattr(vector, 'resolve_expression'):
            vector = Value(to_db(vector))
        super().__init__(expression, vector, **extra)


class L2Distance(DistanceBase):
    function = ''
    arg_joiner = ' <-> '


class MaxInnerProduct(DistanceBase):
    function = ''
    arg_joiner = ' <#> '


class CosineDistance(DistanceBase):
    function = ''
    arg_joiner = ' <=> '
