from __future__ import annotations

import contextlib
import logging
import sys
from typing import Any, Iterator

import click

# Initialise the builtin logging module for other component using it.
# Ex: pip
logging.basicConfig()


class LogContext:
    stream = sys.stderr

    def __init__(self, verbosity: int = 0, indent_width: int = 2):
        self.verbosity = self._initial_verbosity = verbosity
        self.current_indent = self._initial_indent = 0
        self._indent_width = self._initial_indent_width = indent_width

    def log(self, message: str, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("err", True)
        prefix = " " * self.current_indent
        click.secho(prefix + message, *args, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        if self.verbosity >= 1:
            self.log(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        if self.verbosity >= 0:
            self.log(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("fg", "yellow")
        self.log(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("fg", "red")
        self.log(message, *args, **kwargs)

    def _indent(self) -> None:
        self.current_indent += self._indent_width

    def _dedent(self) -> None:
        self.current_indent -= self._indent_width

    @contextlib.contextmanager
    def indentation(self) -> Iterator[None]:
        """
        Increase indentation.
        """
        self._indent()
        try:
            yield
        finally:
            self._dedent()

    def reset(self) -> None:
        """Reset logger to initial state."""
        self.verbosity = self._initial_verbosity
        self.current_indent = self._initial_indent
        self._indent_width = self._initial_indent_width


log = LogContext()
