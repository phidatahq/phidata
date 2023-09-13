from typing import Optional

from phi.api.schemas.user import UserSchema
from phi.cli.config import PhiCliConfig
from phi.workspace.config import WorkspaceConfig
from phi.utils.log import logger


def start_conversation(phi_config: PhiCliConfig, ws_config: WorkspaceConfig) -> bool:
    """Start a conversation with Phi AI."""

    from rich.prompt import Prompt
    from phi.api.ai import create_conversation

    logger.debug("*** Chatting with Phi AI ***")

    user: Optional[UserSchema] = phi_config.user
    if user is None:
        logger.error("Please authenticate using `phi auth`")
        return False

    message = Prompt.ask(":boom: Message")
    logger.debug(f"Message: {message}")

    new_conversation = create_conversation(message=message, user=user)
    logger.debug(f"New Conversation: {new_conversation}")

    return True
