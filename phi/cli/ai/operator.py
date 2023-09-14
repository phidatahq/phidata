from typing import Optional

from phi.api.schemas.user import UserSchema
from phi.cli.config import PhiCliConfig
from phi.workspace.config import WorkspaceConfig
from phi.utils.log import logger


def start_conversation(
    phi_config: PhiCliConfig,
    ws_config: WorkspaceConfig,
    start_new_conversation: bool = False,
    show_all_messages: bool = False,
) -> bool:
    """Start a conversation with Phi AI."""

    from rich.prompt import Prompt
    from phi.api.ai import conversation_create, conversation_chat, ConversationCreateResponse, ConversationChatResponse
    from phi.cli.console import console

    logger.debug("*** Chatting with Phi AI ***")

    user: Optional[UserSchema] = phi_config.user
    if user is None:
        logger.error("Please authenticate using `phi auth`")
        return False

    conversation: Optional[ConversationCreateResponse] = conversation_create(user=user)
    if conversation is None:
        logger.error("Could not create conversation")
        return False

    conversation_id = conversation.id
    chat_history = conversation.chat_history
    logger.debug(f"Conversation: {conversation_id}")

    role_column_width = 12
    if show_all_messages:
        for message in chat_history:
            if message["role"] == "system":
                continue
            elif message["role"] == "assistant":
                padding = " " * (role_column_width - len("Phi"))
                console.print(f":sunglasses: Phi{padding}: {message['content']}")
            elif message["role"] == "user":
                username = user.username or "You"
                padding = " " * (role_column_width - len(username))
                console.print(f":sunglasses: {username}{padding}: {message['content']}")
            else:
                padding = " " * (role_column_width - len(message["role"]))
                console.print(f":sunglasses: {message['role']}:{padding}: {message['content']}")

    conversation_active = True
    while conversation_active:
        username = user.username or "You"
        username_padding = " " * (role_column_width - len(username))
        user_message = Prompt.ask(f":sunglasses: {username}{username_padding}")
        chat_history.append({"role": "user", "content": user_message})

        # -*- Quit conversation
        if user_message in ("exit", "quit", "bye"):
            conversation_active = False

        # -*- Send message to Phi AI
        chat_response: Optional[ConversationChatResponse] = conversation_chat(
            user=user,
            conversation_id=conversation_id,
            message=user_message,
        )
        if chat_response is None:
            logger.error("Could not chat with Phi AI")
            return False

        phi_padding = " " * (role_column_width - len("Phi"))
        console.print(f":sunglasses: Phi{phi_padding}: {chat_response.response}")
        chat_history.append({"role": "assistant", "content": chat_response.response})

    return True
