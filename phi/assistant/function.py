from typing import Any, Dict, Optional, Callable, get_type_hints
from pydantic import BaseModel, validate_call

from phi.utils.log import logger


class Tool(BaseModel):
    """Model for Assistant Tools"""

    # The type of tool
    type: str
    function: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)


class Function(BaseModel):
    """Model for Assistant functions"""

    # The name of the function to be called.
    # Must be a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum length of 64.
    name: str
    # A description of what the function does, used by the model to choose when and how to call the function.
    description: Optional[str] = None
    # The parameters the functions accepts, described as a JSON Schema object.
    # To describe a function that accepts no parameters, provide the value {"type": "object", "properties": {}}.
    parameters: Dict[str, Any] = {"type": "object", "properties": {}}
    entrypoint: Optional[Callable] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True, exclude={"entrypoint"})

    @classmethod
    def from_callable(cls, c: Callable) -> "Function":
        from inspect import getdoc
        from phi.utils.json_schema import get_json_schema

        parameters = {"type": "object", "properties": {}}
        try:
            type_hints = get_type_hints(c)
            parameters = get_json_schema(type_hints)
            # logger.debug(f"Type hints for {c.__name__}: {type_hints}")
        except Exception as e:
            logger.warning(f"Could not parse args for {c.__name__}: {e}")

        return cls(
            name=c.__name__,
            description=getdoc(c),
            parameters=parameters,
            entrypoint=validate_call(c),
        )


class FunctionCall(BaseModel):
    """Model for Assistant function calls"""

    # The function to be called.
    function: Function
    # The arguments to call the function with.
    arguments: Optional[Dict[str, Any]] = None
    # The result of the function call.
    result: Optional[Any] = None

    def get_call_str(self) -> str:
        """Returns a string representation of the function call."""
        if self.arguments is None:
            return f"{self.function.name}()"
        return f"{self.function.name}({', '.join([f'{k}={v}' for k, v in self.arguments.items()])})"

    def execute(self) -> bool:
        """Runs the function call.

        @return: True if the function call was successful, False otherwise.
        """
        if self.function.entrypoint is None:
            return False

        logger.debug(f"Running: {self.get_call_str()}")

        # Call the function with no arguments if none are provided.
        if self.arguments is None:
            try:
                self.result = self.function.entrypoint()
                return True
            except Exception as e:
                logger.warning(f"Could not run function {self.get_call_str()}")
                logger.error(e)
                return False

        try:
            self.result = self.function.entrypoint(**self.arguments)
            return True
        except Exception as e:
            logger.warning(f"Could not run function {self.get_call_str()}")
            logger.error(e)
            return False
