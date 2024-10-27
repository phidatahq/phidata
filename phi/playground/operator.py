from typing import List, Optional

from phi.agent.agent import Agent, Tool, Toolkit, Function, AgentRun
from phi.agent.session import AgentSession
from phi.utils.log import logger


def format_tools(agent_tools):
    formatted_tools = []
    if agent_tools is not None:
        for tool in agent_tools:
            if isinstance(tool, dict):
                formatted_tools.append(tool)
            elif isinstance(tool, Tool):
                formatted_tools.append(tool.to_dict())
            elif isinstance(tool, Toolkit):
                for f_name, f in tool.functions.items():
                    formatted_tools.append(f.to_dict())
            elif isinstance(tool, Function):
                formatted_tools.append(tool.to_dict())
            elif callable(tool):
                func = Function.from_callable(tool)
                formatted_tools.append(func.to_dict())
            else:
                logger.warning(f"Unknown tool type: {type(tool)}")
    return formatted_tools


def get_agent_by_id(agents: List[Agent], agent_id: str) -> Optional[Agent]:
    for agent in agents:
        if agent.agent_id == agent_id:
            return agent
    return None


def get_session_title(session: AgentSession) -> str:
    if session is None:
        return "Unnamed session"
    session_name = session.session_data.get("session_name") if session.session_data is not None else None
    if session_name is not None:
        return session_name
    memory = session.memory
    if memory is not None:
        runs = memory.get("runs") or memory.get("chats")
        if isinstance(runs, list):
            for _run in runs:
                try:
                    run_parsed = AgentRun.model_validate(_run)
                    if run_parsed.message is not None and run_parsed.message.role == "user":
                        content = run_parsed.message.get_content_string()
                        if content:
                            return content
                        else:
                            return "No title"
                except Exception as e:
                    logger.error(f"Error parsing chat: {e}")
    return "Unnamed session"
