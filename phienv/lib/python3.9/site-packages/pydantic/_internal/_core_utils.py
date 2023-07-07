from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Hashable, Iterable, TypeVar, Union, cast

from pydantic_core import CoreSchema, core_schema
from typing_extensions import TypeAliasType, TypeGuard, get_args

from . import _repr

AnyFunctionSchema = Union[
    core_schema.AfterValidatorFunctionSchema,
    core_schema.BeforeValidatorFunctionSchema,
    core_schema.WrapValidatorFunctionSchema,
    core_schema.PlainValidatorFunctionSchema,
]


FunctionSchemaWithInnerSchema = Union[
    core_schema.AfterValidatorFunctionSchema,
    core_schema.BeforeValidatorFunctionSchema,
    core_schema.WrapValidatorFunctionSchema,
]

CoreSchemaField = Union[
    core_schema.ModelField, core_schema.DataclassField, core_schema.TypedDictField, core_schema.ComputedField
]
CoreSchemaOrField = Union[core_schema.CoreSchema, CoreSchemaField]

_CORE_SCHEMA_FIELD_TYPES = {'typed-dict-field', 'dataclass-field', 'model-field', 'computed-field'}
_FUNCTION_WITH_INNER_SCHEMA_TYPES = {'function-before', 'function-after', 'function-wrap'}
_LIST_LIKE_SCHEMA_WITH_ITEMS_TYPES = {'list', 'tuple-variable', 'set', 'frozenset'}


def is_definition_ref_schema(s: core_schema.CoreSchema) -> TypeGuard[core_schema.DefinitionReferenceSchema]:
    return s['type'] == 'definition-ref'


def is_definitions_schema(s: core_schema.CoreSchema) -> TypeGuard[core_schema.DefinitionsSchema]:
    return s['type'] == 'definitions'


def is_core_schema(
    schema: CoreSchemaOrField,
) -> TypeGuard[CoreSchema]:
    return schema['type'] not in _CORE_SCHEMA_FIELD_TYPES


def is_core_schema_field(
    schema: CoreSchemaOrField,
) -> TypeGuard[CoreSchemaField]:
    return schema['type'] in _CORE_SCHEMA_FIELD_TYPES


def is_function_with_inner_schema(
    schema: CoreSchemaOrField,
) -> TypeGuard[FunctionSchemaWithInnerSchema]:
    return schema['type'] in _FUNCTION_WITH_INNER_SCHEMA_TYPES


def is_list_like_schema_with_items_schema(
    schema: CoreSchema,
) -> TypeGuard[
    core_schema.ListSchema | core_schema.TupleVariableSchema | core_schema.SetSchema | core_schema.FrozenSetSchema
]:
    return schema['type'] in _LIST_LIKE_SCHEMA_WITH_ITEMS_TYPES


def get_type_ref(type_: type[Any], args_override: tuple[type[Any], ...] | None = None) -> str:
    """Produces the ref to be used for this type by pydantic_core's core schemas.

    This `args_override` argument was added for the purpose of creating valid recursive references
    when creating generic models without needing to create a concrete class.
    """
    origin = type_
    args = args_override or ()
    generic_metadata = getattr(type_, '__pydantic_generic_metadata__', None)
    if generic_metadata:
        origin = generic_metadata['origin'] or origin
        args = generic_metadata['args'] or args

    module_name = getattr(origin, '__module__', '<No __module__>')
    if isinstance(origin, TypeAliasType):
        type_ref = f'{module_name}.{origin.__name__}'
    else:
        try:
            qualname = getattr(origin, '__qualname__', f'<No __qualname__: {origin}>')
        except Exception:
            qualname = getattr(origin, '__qualname__', '<No __qualname__>')
        type_ref = f'{module_name}.{qualname}:{id(origin)}'

    arg_refs: list[str] = []
    for arg in args:
        if isinstance(arg, str):
            # Handle string literals as a special case; we may be able to remove this special handling if we
            # wrap them in a ForwardRef at some point.
            arg_ref = f'{arg}:str-{id(arg)}'
        else:
            arg_ref = f'{_repr.display_as_type(arg)}:{id(arg)}'
        arg_refs.append(arg_ref)
    if arg_refs:
        type_ref = f'{type_ref}[{",".join(arg_refs)}]'
    return type_ref


def get_ref(s: core_schema.CoreSchema) -> None | str:
    """Get the ref from the schema if it has one.
    This exists just for type checking to work correctly.
    """
    return s.get('ref', None)  # type: ignore


def collect_definitions(schema: core_schema.CoreSchema) -> dict[str, core_schema.CoreSchema]:
    defs: dict[str, CoreSchema] = {}

    def _record_valid_refs(s: core_schema.CoreSchema, recurse: Recurse) -> core_schema.CoreSchema:
        ref = get_ref(s)
        if ref:
            defs[ref] = s
        return recurse(s, _record_valid_refs)

    walk_core_schema(schema, _record_valid_refs)

    return defs


def define_expected_missing_refs(
    schema: core_schema.CoreSchema, allowed_missing_refs: set[str]
) -> core_schema.CoreSchema:
    if not allowed_missing_refs:
        # in this case, there are no missing refs to potentially substitute, so there's no need to walk the schema
        # this is a common case (will be hit for all non-generic models), so it's worth optimizing for
        return schema
    refs = set()

    def _record_refs(s: core_schema.CoreSchema, recurse: Recurse) -> core_schema.CoreSchema:
        ref: str | None = s.get('ref')  # type: ignore[assignment]
        if ref:
            refs.add(ref)
        return recurse(s, _record_refs)

    walk_core_schema(schema, _record_refs)

    expected_missing_refs = allowed_missing_refs.difference(refs)
    if expected_missing_refs:
        definitions: list[core_schema.CoreSchema] = [
            # TODO: Replace this with a (new) CoreSchema that, if present at any level, makes validation fail
            #   Issue: https://github.com/pydantic/pydantic-core/issues/619
            core_schema.none_schema(ref=ref, metadata={'pydantic_debug_missing_ref': True, 'invalid': True})
            for ref in expected_missing_refs
        ]
        return core_schema.definitions_schema(schema, definitions)
    return schema


def collect_invalid_schemas(schema: core_schema.CoreSchema) -> list[core_schema.CoreSchema]:
    invalid_schemas: list[core_schema.CoreSchema] = []

    def _is_schema_valid(s: core_schema.CoreSchema, recurse: Recurse) -> core_schema.CoreSchema:
        if s.get('metadata', {}).get('invalid'):
            invalid_schemas.append(s)
        return recurse(s, _is_schema_valid)

    walk_core_schema(schema, _is_schema_valid)
    return invalid_schemas


T = TypeVar('T')


Recurse = Callable[[core_schema.CoreSchema, 'Walk'], core_schema.CoreSchema]
Walk = Callable[[core_schema.CoreSchema, Recurse], core_schema.CoreSchema]

# TODO: Should we move _WalkCoreSchema into pydantic_core proper?
#   Issue: https://github.com/pydantic/pydantic-core/issues/615


class _WalkCoreSchema:
    def __init__(self):
        self._schema_type_to_method = self._build_schema_type_to_method()

    def _build_schema_type_to_method(self) -> dict[core_schema.CoreSchemaType, Recurse]:
        mapping: dict[core_schema.CoreSchemaType, Recurse] = {}
        key: core_schema.CoreSchemaType
        for key in get_args(core_schema.CoreSchemaType):
            method_name = f"handle_{key.replace('-', '_')}_schema"
            mapping[key] = getattr(self, method_name, self._handle_other_schemas)
        return mapping

    def walk(self, schema: core_schema.CoreSchema, f: Walk) -> core_schema.CoreSchema:
        return f(schema.copy(), self._walk)

    def _walk(self, schema: core_schema.CoreSchema, f: Walk) -> core_schema.CoreSchema:
        schema = self._schema_type_to_method[schema['type']](schema, f)
        ser_schema: core_schema.SerSchema | None = schema.get('serialization', None)  # type: ignore
        if ser_schema:
            schema['serialization'] = self._handle_ser_schemas(ser_schema.copy(), f)
        return schema

    def _handle_other_schemas(self, schema: core_schema.CoreSchema, f: Walk) -> core_schema.CoreSchema:
        if 'schema' in schema:
            schema['schema'] = self.walk(schema['schema'], f)  # type: ignore
        return schema

    def _handle_ser_schemas(self, ser_schema: core_schema.SerSchema, f: Walk) -> core_schema.SerSchema:
        schema: core_schema.CoreSchema | None = ser_schema.get('schema', None)
        if schema is not None:
            ser_schema['schema'] = self.walk(schema, f)  # type: ignore
        return ser_schema

    def handle_definitions_schema(self, schema: core_schema.DefinitionsSchema, f: Walk) -> core_schema.CoreSchema:
        new_definitions: list[core_schema.CoreSchema] = []
        for definition in schema['definitions']:
            updated_definition = self.walk(definition, f)
            if 'ref' in updated_definition:
                # If the updated definition schema doesn't have a 'ref', it shouldn't go in the definitions
                # This is most likely to happen due to replacing something with a definition reference, in
                # which case it should certainly not go in the definitions list
                new_definitions.append(updated_definition)
        new_inner_schema = self.walk(schema['schema'], f)

        if not new_definitions and len(schema) == 3:
            # This means we'd be returning a "trivial" definitions schema that just wrapped the inner schema
            return new_inner_schema

        new_schema = schema.copy()
        new_schema['schema'] = new_inner_schema
        new_schema['definitions'] = new_definitions
        return new_schema

    def handle_list_schema(self, schema: core_schema.ListSchema, f: Walk) -> core_schema.CoreSchema:
        if 'items_schema' in schema:
            schema['items_schema'] = self.walk(schema['items_schema'], f)
        return schema

    def handle_set_schema(self, schema: core_schema.SetSchema, f: Walk) -> core_schema.CoreSchema:
        if 'items_schema' in schema:
            schema['items_schema'] = self.walk(schema['items_schema'], f)
        return schema

    def handle_frozenset_schema(self, schema: core_schema.FrozenSetSchema, f: Walk) -> core_schema.CoreSchema:
        if 'items_schema' in schema:
            schema['items_schema'] = self.walk(schema['items_schema'], f)
        return schema

    def handle_generator_schema(self, schema: core_schema.GeneratorSchema, f: Walk) -> core_schema.CoreSchema:
        if 'items_schema' in schema:
            schema['items_schema'] = self.walk(schema['items_schema'], f)
        return schema

    def handle_tuple_variable_schema(
        self, schema: core_schema.TupleVariableSchema | core_schema.TuplePositionalSchema, f: Walk
    ) -> core_schema.CoreSchema:
        schema = cast(core_schema.TupleVariableSchema, schema)
        if 'items_schema' in schema:
            schema['items_schema'] = self.walk(schema['items_schema'], f)
        return schema

    def handle_tuple_positional_schema(
        self, schema: core_schema.TupleVariableSchema | core_schema.TuplePositionalSchema, f: Walk
    ) -> core_schema.CoreSchema:
        schema = cast(core_schema.TuplePositionalSchema, schema)
        schema['items_schema'] = [self.walk(v, f) for v in schema['items_schema']]
        if 'extra_schema' in schema:
            schema['extra_schema'] = self.walk(schema['extra_schema'], f)
        return schema

    def handle_dict_schema(self, schema: core_schema.DictSchema, f: Walk) -> core_schema.CoreSchema:
        if 'keys_schema' in schema:
            schema['keys_schema'] = self.walk(schema['keys_schema'], f)
        if 'values_schema' in schema:
            schema['values_schema'] = self.walk(schema['values_schema'], f)
        return schema

    def handle_function_schema(self, schema: AnyFunctionSchema, f: Walk) -> core_schema.CoreSchema:
        if not is_function_with_inner_schema(schema):
            return schema
        schema['schema'] = self.walk(schema['schema'], f)
        return schema

    def handle_union_schema(self, schema: core_schema.UnionSchema, f: Walk) -> core_schema.CoreSchema:
        schema['choices'] = [self.walk(v, f) for v in schema['choices']]
        return schema

    def handle_tagged_union_schema(self, schema: core_schema.TaggedUnionSchema, f: Walk) -> core_schema.CoreSchema:
        new_choices: dict[Hashable, core_schema.CoreSchema] = {}
        for k, v in schema['choices'].items():
            new_choices[k] = v if isinstance(v, (str, int)) else self.walk(v, f)
        schema['choices'] = new_choices
        return schema

    def handle_chain_schema(self, schema: core_schema.ChainSchema, f: Walk) -> core_schema.CoreSchema:
        schema['steps'] = [self.walk(v, f) for v in schema['steps']]
        return schema

    def handle_lax_or_strict_schema(self, schema: core_schema.LaxOrStrictSchema, f: Walk) -> core_schema.CoreSchema:
        schema['lax_schema'] = self.walk(schema['lax_schema'], f)
        schema['strict_schema'] = self.walk(schema['strict_schema'], f)
        return schema

    def handle_json_or_python_schema(self, schema: core_schema.JsonOrPythonSchema, f: Walk) -> core_schema.CoreSchema:
        schema['json_schema'] = self.walk(schema['json_schema'], f)
        schema['python_schema'] = self.walk(schema['python_schema'], f)
        return schema

    def handle_model_fields_schema(self, schema: core_schema.ModelFieldsSchema, f: Walk) -> core_schema.CoreSchema:
        if 'extra_validator' in schema:
            schema['extra_validator'] = self.walk(schema['extra_validator'], f)
        replaced_fields: dict[str, core_schema.ModelField] = {}
        replaced_computed_fields: list[core_schema.ComputedField] = []
        for computed_field in schema.get('computed_fields', None) or ():
            replaced_field = computed_field.copy()
            replaced_field['return_schema'] = self.walk(computed_field['return_schema'], f)
            replaced_computed_fields.append(replaced_field)
        if replaced_computed_fields:
            schema['computed_fields'] = replaced_computed_fields
        for k, v in schema['fields'].items():
            replaced_field = v.copy()
            replaced_field['schema'] = self.walk(v['schema'], f)
            replaced_fields[k] = replaced_field
        schema['fields'] = replaced_fields
        return schema

    def handle_typed_dict_schema(self, schema: core_schema.TypedDictSchema, f: Walk) -> core_schema.CoreSchema:
        if 'extra_validator' in schema:
            schema['extra_validator'] = self.walk(schema['extra_validator'], f)
        replaced_computed_fields: list[core_schema.ComputedField] = []
        for computed_field in schema.get('computed_fields', None) or ():
            replaced_field = computed_field.copy()
            replaced_field['return_schema'] = self.walk(computed_field['return_schema'], f)
            replaced_computed_fields.append(replaced_field)
        if replaced_computed_fields:
            schema['computed_fields'] = replaced_computed_fields
        replaced_fields: dict[str, core_schema.TypedDictField] = {}
        for k, v in schema['fields'].items():
            replaced_field = v.copy()
            replaced_field['schema'] = self.walk(v['schema'], f)
            replaced_fields[k] = replaced_field
        schema['fields'] = replaced_fields
        return schema

    def handle_dataclass_args_schema(self, schema: core_schema.DataclassArgsSchema, f: Walk) -> core_schema.CoreSchema:
        replaced_fields: list[core_schema.DataclassField] = []
        replaced_computed_fields: list[core_schema.ComputedField] = []
        for computed_field in schema.get('computed_fields', None) or ():
            replaced_field = computed_field.copy()
            replaced_field['return_schema'] = self.walk(computed_field['return_schema'], f)
            replaced_computed_fields.append(replaced_field)
        if replaced_computed_fields:
            schema['computed_fields'] = replaced_computed_fields
        for field in schema['fields']:
            replaced_field = field.copy()
            replaced_field['schema'] = self.walk(field['schema'], f)
            replaced_fields.append(replaced_field)
        schema['fields'] = replaced_fields
        return schema

    def handle_arguments_schema(self, schema: core_schema.ArgumentsSchema, f: Walk) -> core_schema.CoreSchema:
        replaced_arguments_schema: list[core_schema.ArgumentsParameter] = []
        for param in schema['arguments_schema']:
            replaced_param = param.copy()
            replaced_param['schema'] = self.walk(param['schema'], f)
            replaced_arguments_schema.append(replaced_param)
        schema['arguments_schema'] = replaced_arguments_schema
        if 'var_args_schema' in schema:
            schema['var_args_schema'] = self.walk(schema['var_args_schema'], f)
        if 'var_kwargs_schema' in schema:
            schema['var_kwargs_schema'] = self.walk(schema['var_kwargs_schema'], f)
        return schema

    def handle_call_schema(self, schema: core_schema.CallSchema, f: Walk) -> core_schema.CoreSchema:
        schema['arguments_schema'] = self.walk(schema['arguments_schema'], f)
        if 'return_schema' in schema:
            schema['return_schema'] = self.walk(schema['return_schema'], f)
        return schema


_dispatch = _WalkCoreSchema().walk


def walk_core_schema(schema: core_schema.CoreSchema, f: Walk) -> core_schema.CoreSchema:
    """Recursively traverse a CoreSchema.

    Args:
        schema (core_schema.CoreSchema): The CoreSchema to process, it will not be modified.
        f (Walk): A function to apply. This function takes two arguments:
          1. The current CoreSchema that is being processed
             (not the same one you passed into this function, one level down).
          2. The "next" `f` to call. This lets you for example use `f=functools.partial(some_method, some_context)`
             to pass data down the recursive calls without using globals or other mutable state.

    Returns:
        core_schema.CoreSchema: A processed CoreSchema.
    """
    return f(schema.copy(), _dispatch)


def _simplify_schema_references(schema: core_schema.CoreSchema, inline: bool) -> core_schema.CoreSchema:  # noqa: C901
    valid_defs: dict[str, core_schema.CoreSchema] = {}
    invalid_defs: dict[str, core_schema.CoreSchema] = {}

    def make_result(schema: core_schema.CoreSchema, defs: Iterable[core_schema.CoreSchema]) -> core_schema.CoreSchema:
        definitions = list(defs)
        if definitions:
            return core_schema.definitions_schema(schema=schema, definitions=definitions)
        return schema

    def collect_refs(s: core_schema.CoreSchema, recurse: Recurse) -> core_schema.CoreSchema:
        if s['type'] == 'definitions':
            for definition in s['definitions']:
                ref = get_ref(definition)
                assert ref is not None
                def_schema = recurse(definition, collect_refs).copy()
                if 'invalid' in def_schema.get('metadata', {}):
                    invalid_defs[ref] = def_schema
                else:
                    valid_defs[ref] = def_schema
            return recurse(s['schema'], collect_refs)
        ref = get_ref(s)
        if ref is not None:
            if 'invalid' in s.get('metadata', {}):
                invalid_defs[ref] = s
            else:
                valid_defs[ref] = s
        return recurse(s, collect_refs)

    schema = walk_core_schema(schema, collect_refs)

    all_defs = {**invalid_defs, **valid_defs}

    def flatten_refs(s: core_schema.CoreSchema, recurse: Recurse) -> core_schema.CoreSchema:
        if is_definitions_schema(s):
            new: dict[str, Any] = dict(s)
            # iterate ourselves, we don't want to flatten the actual defs!
            definitions: list[CoreSchema] = new.pop('definitions')
            schema = cast(CoreSchema, new.pop('schema'))
            # remaining keys are optional like 'serialization'
            schema = cast(CoreSchema, {**schema, **new})
            s['schema'] = recurse(schema, flatten_refs)
            for definition in definitions:
                recurse(definition, flatten_refs)  # don't re-assign here!
            return schema
        s = recurse(s, flatten_refs)
        ref = get_ref(s)
        if ref and ref in all_defs:
            all_defs[ref] = s
            return core_schema.definition_reference_schema(schema_ref=ref)
        return s

    schema = walk_core_schema(schema, flatten_refs)

    for def_schema in all_defs.values():
        walk_core_schema(def_schema, flatten_refs)

    if not inline:
        return make_result(schema, all_defs.values())

    ref_counts: dict[str, int] = defaultdict(int)
    involved_in_recursion: dict[str, bool] = {}
    current_recursion_ref_count: dict[str, int] = defaultdict(int)

    def count_refs(s: core_schema.CoreSchema, recurse: Recurse) -> core_schema.CoreSchema:
        if not is_definition_ref_schema(s):
            return recurse(s, count_refs)
        ref = s['schema_ref']
        ref_counts[ref] += 1
        if current_recursion_ref_count[ref] != 0:
            involved_in_recursion[ref] = True
            return s

        current_recursion_ref_count[ref] += 1
        recurse(all_defs[ref], count_refs)
        current_recursion_ref_count[ref] -= 1
        return s

    schema = walk_core_schema(schema, count_refs)

    assert all(c == 0 for c in current_recursion_ref_count.values()), 'this is a bug! please report it'

    def inline_refs(s: core_schema.CoreSchema, recurse: Recurse) -> core_schema.CoreSchema:
        if s['type'] == 'definition-ref':
            ref = s['schema_ref']
            # Check if the reference is only used once and not involved in recursion
            if ref_counts[ref] <= 1 and not involved_in_recursion.get(ref, False):
                # Inline the reference by replacing the reference with the actual schema
                new = all_defs.pop(ref)
                ref_counts[ref] -= 1  # because we just replaced it!
                new.pop('ref')  # type: ignore
                # put all other keys that were on the def-ref schema into the inlined version
                # in particular this is needed for `serialization`
                if 'serialization' in s:
                    new['serialization'] = s['serialization']
                s = recurse(new, inline_refs)
                return s
            else:
                return recurse(s, inline_refs)
        else:
            return recurse(s, inline_refs)

    schema = walk_core_schema(schema, inline_refs)

    definitions = [d for d in all_defs.values() if ref_counts[d['ref']] > 0]  # type: ignore
    return make_result(schema, definitions)


def flatten_schema_defs(schema: core_schema.CoreSchema) -> core_schema.CoreSchema:
    """Simplify schema references by:
    1. Grouping all definitions into a single top-level `definitions` schema, similar to a JSON schema's `#/$defs`.
    """
    return _simplify_schema_references(schema, inline=False)


def inline_schema_defs(schema: core_schema.CoreSchema) -> core_schema.CoreSchema:
    """Simplify schema references by:
    1. Inlining any definitions that are only referenced in one place and are not involved in a cycle.
    2. Removing any unused `ref` references from schemas.
    """
    return _simplify_schema_references(schema, inline=True)
