from phi.agent import Agent
from phi.tools import Function

try:
    from composio_phidata import Action, ComposioToolSet  # type: ignore
except (ModuleNotFoundError, ImportError):
    logger.error("`composio_phidata` not installed. Install it with `pip install composio-phidata`.")
    raise

toolset = ComposioToolSet()
composio_tools = toolset.get_tools(actions=[Action.GITHUB_STAR_A_REPOSITORY_FOR_THE_AUTHENTICATED_USER])

functions = []
functions.append(Function(
    name=composio_tools[0].name,
    entrypoint=composio_tools[0].entrypoint,
    sanitize_arguments=True
))
agent = Agent(tools=composio_tools, show_tool_calls=True)
agent.print_response("Can you star phidatahq/phidata repo?")
