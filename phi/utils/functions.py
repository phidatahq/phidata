import json
from typing import Optional, Dict, Any

from phi.llm.schemas import Function, FunctionCall
from phi.utils.log import logger


def get_function_call(
    name: str, arguments: Optional[str] = None, functions: Optional[Dict[str, Function]] = None
) -> Optional[FunctionCall]:
    logger.debug(f"Getting function {name}. Args: {arguments}")
    if functions is None:
        return None

    function_to_call: Optional[Function] = None
    if name in functions:
        function_to_call = functions[name]
    if function_to_call is None:
        logger.error(f"Function {name} not found")
        return None

    function_call = FunctionCall(function=function_to_call)
    if arguments is not None and arguments != "":
        try:
            if "None" in arguments:
                arguments = arguments.replace("None", "null")
            if "True" in arguments:
                arguments = arguments.replace("True", "true")
            if "False" in arguments:
                arguments = arguments.replace("False", "false")
            _arguments = json.loads(arguments)
        except Exception as e:
            logger.error(f"Unable to decode function arguments {arguments}: {e}")
            return None

        if not isinstance(_arguments, dict):
            logger.error(f"Function arguments {arguments} is not a valid JSON object")
            return None

        try:
            clean_arguments: Dict[str, Any] = {}
            for k, v in _arguments.items():
                if isinstance(v, str):
                    _v = v.strip().lower()
                    if _v in ("none", "null"):
                        clean_arguments[k] = None
                    elif _v == "true":
                        clean_arguments[k] = True
                    elif _v == "false":
                        clean_arguments[k] = False
                    else:
                        clean_arguments[k] = v.strip()
                else:
                    clean_arguments[k] = v

            function_call.arguments = clean_arguments
        except Exception as e:
            logger.error(f"Unable to parse function arguments {arguments}: {e}")
            return None
    return function_call


# def run_function(func, *args, **kwargs):
#     if asyncio.iscoroutinefunction(func):
#         logger.debug("Running asynchronous function")
#         try:
#             loop = asyncio.get_running_loop()
#         except RuntimeError as e:  # No running event loop
#             logger.debug(f"Could not get running event loop: {e}")
#             logger.debug("Running with a new event loop")
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)
#             result = loop.run_until_complete(func(*args, **kwargs))
#             loop.close()
#             logger.debug("Done running with a new event loop")
#             return result
#         else:  # There is a running event loop
#             logger.debug("Running in existing event loop")
#             result = loop.run_until_complete(func(*args, **kwargs))
#             logger.debug("Done running in existing event loop")
#             return result
#     else:  # The function is a synchronous function
#         logger.debug("Running synchronous function")
#         return func(*args, **kwargs)
