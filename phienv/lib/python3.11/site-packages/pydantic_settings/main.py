from __future__ import annotations as _annotations

from typing import Any, ClassVar

from pydantic import ConfigDict
from pydantic._internal._config import config_keys
from pydantic._internal._utils import deep_update
from pydantic.main import BaseModel

from .sources import (
    ENV_FILE_SENTINEL,
    CliSettingsSource,
    DefaultSettingsSource,
    DotEnvSettingsSource,
    DotenvType,
    EnvSettingsSource,
    InitSettingsSource,
    PathType,
    PydanticBaseSettingsSource,
    SecretsSettingsSource,
)


class SettingsConfigDict(ConfigDict, total=False):
    case_sensitive: bool
    nested_model_default_partial_update: bool | None
    env_prefix: str
    env_file: DotenvType | None
    env_file_encoding: str | None
    env_ignore_empty: bool
    env_nested_delimiter: str | None
    env_parse_none_str: str | None
    env_parse_enums: bool | None
    cli_prog_name: str | None
    cli_parse_args: bool | list[str] | tuple[str, ...] | None
    cli_settings_source: CliSettingsSource[Any] | None
    cli_parse_none_str: str | None
    cli_hide_none_type: bool
    cli_avoid_json: bool
    cli_enforce_required: bool
    cli_use_class_docs_for_groups: bool
    cli_exit_on_error: bool
    cli_prefix: str
    cli_implicit_flags: bool | None
    secrets_dir: PathType | None
    json_file: PathType | None
    json_file_encoding: str | None
    yaml_file: PathType | None
    yaml_file_encoding: str | None
    pyproject_toml_depth: int
    """
    Number of levels **up** from the current working directory to attempt to find a pyproject.toml
    file.

    This is only used when a pyproject.toml file is not found in the current working directory.
    """

    pyproject_toml_table_header: tuple[str, ...]
    """
    Header of the TOML table within a pyproject.toml file to use when filling variables.
    This is supplied as a `tuple[str, ...]` instead of a `str` to accommodate for headers
    containing a `.`.

    For example, `toml_table_header = ("tool", "my.tool", "foo")` can be used to fill variable
    values from a table with header `[tool."my.tool".foo]`.

    To use the root table, exclude this config setting or provide an empty tuple.
    """

    toml_file: PathType | None


# Extend `config_keys` by pydantic settings config keys to
# support setting config through class kwargs.
# Pydantic uses `config_keys` in `pydantic._internal._config.ConfigWrapper.for_model`
# to extract config keys from model kwargs, So, by adding pydantic settings keys to
# `config_keys`, they will be considered as valid config keys and will be collected
# by Pydantic.
config_keys |= set(SettingsConfigDict.__annotations__.keys())


class BaseSettings(BaseModel):
    """
    Base class for settings, allowing values to be overridden by environment variables.

    This is useful in production for secrets you do not wish to save in code, it plays nicely with docker(-compose),
    Heroku and any 12 factor app design.

    All the below attributes can be set via `model_config`.

    Args:
        _case_sensitive: Whether environment variables names should be read with case-sensitivity. Defaults to `None`.
        _nested_model_default_partial_update: Whether to allow partial updates on nested model default object fields.
            Defaults to `False`.
        _env_prefix: Prefix for all environment variables. Defaults to `None`.
        _env_file: The env file(s) to load settings values from. Defaults to `Path('')`, which
            means that the value from `model_config['env_file']` should be used. You can also pass
            `None` to indicate that environment variables should not be loaded from an env file.
        _env_file_encoding: The env file encoding, e.g. `'latin-1'`. Defaults to `None`.
        _env_ignore_empty: Ignore environment variables where the value is an empty string. Default to `False`.
        _env_nested_delimiter: The nested env values delimiter. Defaults to `None`.
        _env_parse_none_str: The env string value that should be parsed (e.g. "null", "void", "None", etc.)
            into `None` type(None). Defaults to `None` type(None), which means no parsing should occur.
        _env_parse_enums: Parse enum field names to values. Defaults to `None.`, which means no parsing should occur.
        _cli_prog_name: The CLI program name to display in help text. Defaults to `None` if _cli_parse_args is `None`.
            Otherwse, defaults to sys.argv[0].
        _cli_parse_args: The list of CLI arguments to parse. Defaults to None.
            If set to `True`, defaults to sys.argv[1:].
        _cli_settings_source: Override the default CLI settings source with a user defined instance. Defaults to None.
        _cli_parse_none_str: The CLI string value that should be parsed (e.g. "null", "void", "None", etc.) into
            `None` type(None). Defaults to _env_parse_none_str value if set. Otherwise, defaults to "null" if
            _cli_avoid_json is `False`, and "None" if _cli_avoid_json is `True`.
        _cli_hide_none_type: Hide `None` values in CLI help text. Defaults to `False`.
        _cli_avoid_json: Avoid complex JSON objects in CLI help text. Defaults to `False`.
        _cli_enforce_required: Enforce required fields at the CLI. Defaults to `False`.
        _cli_use_class_docs_for_groups: Use class docstrings in CLI group help text instead of field descriptions.
            Defaults to `False`.
        _cli_exit_on_error: Determines whether or not the internal parser exits with error info when an error occurs.
            Defaults to `True`.
        _cli_prefix: The root parser command line arguments prefix. Defaults to "".
        _cli_implicit_flags: Whether `bool` fields should be implicitly converted into CLI boolean flags.
            (e.g. --flag, --no-flag). Defaults to `False`.
        _secrets_dir: The secret files directory or a sequence of directories. Defaults to `None`.
    """

    def __init__(
        __pydantic_self__,
        _case_sensitive: bool | None = None,
        _nested_model_default_partial_update: bool | None = None,
        _env_prefix: str | None = None,
        _env_file: DotenvType | None = ENV_FILE_SENTINEL,
        _env_file_encoding: str | None = None,
        _env_ignore_empty: bool | None = None,
        _env_nested_delimiter: str | None = None,
        _env_parse_none_str: str | None = None,
        _env_parse_enums: bool | None = None,
        _cli_prog_name: str | None = None,
        _cli_parse_args: bool | list[str] | tuple[str, ...] | None = None,
        _cli_settings_source: CliSettingsSource[Any] | None = None,
        _cli_parse_none_str: str | None = None,
        _cli_hide_none_type: bool | None = None,
        _cli_avoid_json: bool | None = None,
        _cli_enforce_required: bool | None = None,
        _cli_use_class_docs_for_groups: bool | None = None,
        _cli_exit_on_error: bool | None = None,
        _cli_prefix: str | None = None,
        _cli_implicit_flags: bool | None = None,
        _secrets_dir: PathType | None = None,
        **values: Any,
    ) -> None:
        # Uses something other than `self` the first arg to allow "self" as a settable attribute
        super().__init__(
            **__pydantic_self__._settings_build_values(
                values,
                _case_sensitive=_case_sensitive,
                _nested_model_default_partial_update=_nested_model_default_partial_update,
                _env_prefix=_env_prefix,
                _env_file=_env_file,
                _env_file_encoding=_env_file_encoding,
                _env_ignore_empty=_env_ignore_empty,
                _env_nested_delimiter=_env_nested_delimiter,
                _env_parse_none_str=_env_parse_none_str,
                _env_parse_enums=_env_parse_enums,
                _cli_prog_name=_cli_prog_name,
                _cli_parse_args=_cli_parse_args,
                _cli_settings_source=_cli_settings_source,
                _cli_parse_none_str=_cli_parse_none_str,
                _cli_hide_none_type=_cli_hide_none_type,
                _cli_avoid_json=_cli_avoid_json,
                _cli_enforce_required=_cli_enforce_required,
                _cli_use_class_docs_for_groups=_cli_use_class_docs_for_groups,
                _cli_exit_on_error=_cli_exit_on_error,
                _cli_prefix=_cli_prefix,
                _cli_implicit_flags=_cli_implicit_flags,
                _secrets_dir=_secrets_dir,
            )
        )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Define the sources and their order for loading the settings values.

        Args:
            settings_cls: The Settings class.
            init_settings: The `InitSettingsSource` instance.
            env_settings: The `EnvSettingsSource` instance.
            dotenv_settings: The `DotEnvSettingsSource` instance.
            file_secret_settings: The `SecretsSettingsSource` instance.

        Returns:
            A tuple containing the sources and their order for loading the settings values.
        """
        return init_settings, env_settings, dotenv_settings, file_secret_settings

    def _settings_build_values(
        self,
        init_kwargs: dict[str, Any],
        _case_sensitive: bool | None = None,
        _nested_model_default_partial_update: bool | None = None,
        _env_prefix: str | None = None,
        _env_file: DotenvType | None = None,
        _env_file_encoding: str | None = None,
        _env_ignore_empty: bool | None = None,
        _env_nested_delimiter: str | None = None,
        _env_parse_none_str: str | None = None,
        _env_parse_enums: bool | None = None,
        _cli_prog_name: str | None = None,
        _cli_parse_args: bool | list[str] | tuple[str, ...] | None = None,
        _cli_settings_source: CliSettingsSource[Any] | None = None,
        _cli_parse_none_str: str | None = None,
        _cli_hide_none_type: bool | None = None,
        _cli_avoid_json: bool | None = None,
        _cli_enforce_required: bool | None = None,
        _cli_use_class_docs_for_groups: bool | None = None,
        _cli_exit_on_error: bool | None = None,
        _cli_prefix: str | None = None,
        _cli_implicit_flags: bool | None = None,
        _secrets_dir: PathType | None = None,
    ) -> dict[str, Any]:
        # Determine settings config values
        case_sensitive = _case_sensitive if _case_sensitive is not None else self.model_config.get('case_sensitive')
        env_prefix = _env_prefix if _env_prefix is not None else self.model_config.get('env_prefix')
        nested_model_default_partial_update = (
            _nested_model_default_partial_update
            if _nested_model_default_partial_update is not None
            else self.model_config.get('nested_model_default_partial_update')
        )
        env_file = _env_file if _env_file != ENV_FILE_SENTINEL else self.model_config.get('env_file')
        env_file_encoding = (
            _env_file_encoding if _env_file_encoding is not None else self.model_config.get('env_file_encoding')
        )
        env_ignore_empty = (
            _env_ignore_empty if _env_ignore_empty is not None else self.model_config.get('env_ignore_empty')
        )
        env_nested_delimiter = (
            _env_nested_delimiter
            if _env_nested_delimiter is not None
            else self.model_config.get('env_nested_delimiter')
        )
        env_parse_none_str = (
            _env_parse_none_str if _env_parse_none_str is not None else self.model_config.get('env_parse_none_str')
        )
        env_parse_enums = _env_parse_enums if _env_parse_enums is not None else self.model_config.get('env_parse_enums')

        cli_prog_name = _cli_prog_name if _cli_prog_name is not None else self.model_config.get('cli_prog_name')
        cli_parse_args = _cli_parse_args if _cli_parse_args is not None else self.model_config.get('cli_parse_args')
        cli_settings_source = (
            _cli_settings_source if _cli_settings_source is not None else self.model_config.get('cli_settings_source')
        )
        cli_parse_none_str = (
            _cli_parse_none_str if _cli_parse_none_str is not None else self.model_config.get('cli_parse_none_str')
        )
        cli_parse_none_str = cli_parse_none_str if not env_parse_none_str else env_parse_none_str
        cli_hide_none_type = (
            _cli_hide_none_type if _cli_hide_none_type is not None else self.model_config.get('cli_hide_none_type')
        )
        cli_avoid_json = _cli_avoid_json if _cli_avoid_json is not None else self.model_config.get('cli_avoid_json')
        cli_enforce_required = (
            _cli_enforce_required
            if _cli_enforce_required is not None
            else self.model_config.get('cli_enforce_required')
        )
        cli_use_class_docs_for_groups = (
            _cli_use_class_docs_for_groups
            if _cli_use_class_docs_for_groups is not None
            else self.model_config.get('cli_use_class_docs_for_groups')
        )
        cli_exit_on_error = (
            _cli_exit_on_error if _cli_exit_on_error is not None else self.model_config.get('cli_exit_on_error')
        )
        cli_prefix = _cli_prefix if _cli_prefix is not None else self.model_config.get('cli_prefix')
        cli_implicit_flags = (
            _cli_implicit_flags if _cli_implicit_flags is not None else self.model_config.get('cli_implicit_flags')
        )

        secrets_dir = _secrets_dir if _secrets_dir is not None else self.model_config.get('secrets_dir')

        # Configure built-in sources
        default_settings = DefaultSettingsSource(
            self.__class__, nested_model_default_partial_update=nested_model_default_partial_update
        )
        init_settings = InitSettingsSource(
            self.__class__,
            init_kwargs=init_kwargs,
            nested_model_default_partial_update=nested_model_default_partial_update,
        )
        env_settings = EnvSettingsSource(
            self.__class__,
            case_sensitive=case_sensitive,
            env_prefix=env_prefix,
            env_nested_delimiter=env_nested_delimiter,
            env_ignore_empty=env_ignore_empty,
            env_parse_none_str=env_parse_none_str,
            env_parse_enums=env_parse_enums,
        )
        dotenv_settings = DotEnvSettingsSource(
            self.__class__,
            env_file=env_file,
            env_file_encoding=env_file_encoding,
            case_sensitive=case_sensitive,
            env_prefix=env_prefix,
            env_nested_delimiter=env_nested_delimiter,
            env_ignore_empty=env_ignore_empty,
            env_parse_none_str=env_parse_none_str,
            env_parse_enums=env_parse_enums,
        )

        file_secret_settings = SecretsSettingsSource(
            self.__class__, secrets_dir=secrets_dir, case_sensitive=case_sensitive, env_prefix=env_prefix
        )
        # Provide a hook to set built-in sources priority and add / remove sources
        sources = self.settings_customise_sources(
            self.__class__,
            init_settings=init_settings,
            env_settings=env_settings,
            dotenv_settings=dotenv_settings,
            file_secret_settings=file_secret_settings,
        ) + (default_settings,)
        if not any([source for source in sources if isinstance(source, CliSettingsSource)]):
            if cli_parse_args is not None or cli_settings_source is not None:
                cli_settings = (
                    CliSettingsSource(
                        self.__class__,
                        cli_prog_name=cli_prog_name,
                        cli_parse_args=cli_parse_args,
                        cli_parse_none_str=cli_parse_none_str,
                        cli_hide_none_type=cli_hide_none_type,
                        cli_avoid_json=cli_avoid_json,
                        cli_enforce_required=cli_enforce_required,
                        cli_use_class_docs_for_groups=cli_use_class_docs_for_groups,
                        cli_exit_on_error=cli_exit_on_error,
                        cli_prefix=cli_prefix,
                        cli_implicit_flags=cli_implicit_flags,
                        case_sensitive=case_sensitive,
                    )
                    if cli_settings_source is None
                    else cli_settings_source
                )
                sources = (cli_settings,) + sources
        if sources:
            state: dict[str, Any] = {}
            states: dict[str, dict[str, Any]] = {}
            for source in sources:
                if isinstance(source, PydanticBaseSettingsSource):
                    source._set_current_state(state)
                    source._set_settings_sources_data(states)

                source_name = source.__name__ if hasattr(source, '__name__') else type(source).__name__
                source_state = source()

                states[source_name] = source_state
                state = deep_update(source_state, state)
            return state
        else:
            # no one should mean to do this, but I think returning an empty dict is marginally preferable
            # to an informative error and much better than a confusing error
            return {}

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra='forbid',
        arbitrary_types_allowed=True,
        validate_default=True,
        case_sensitive=False,
        env_prefix='',
        nested_model_default_partial_update=False,
        env_file=None,
        env_file_encoding=None,
        env_ignore_empty=False,
        env_nested_delimiter=None,
        env_parse_none_str=None,
        env_parse_enums=None,
        cli_prog_name=None,
        cli_parse_args=None,
        cli_settings_source=None,
        cli_parse_none_str=None,
        cli_hide_none_type=False,
        cli_avoid_json=False,
        cli_enforce_required=False,
        cli_use_class_docs_for_groups=False,
        cli_exit_on_error=True,
        cli_prefix='',
        cli_implicit_flags=False,
        json_file=None,
        json_file_encoding=None,
        yaml_file=None,
        yaml_file_encoding=None,
        toml_file=None,
        secrets_dir=None,
        protected_namespaces=('model_', 'settings_'),
    )
