from phi.api.schemas.ai import ConversationType
from phi.cli.config import PhiCliConfig


def phi_ai_conversation(
    phi_config: PhiCliConfig,
    start_new_conversation: bool = False,
    autonomous_conversation: bool = True,
    print_conversation_history: bool = False,
    stream: bool = False,
) -> None:
    """Start a conversation with Phi AI."""
    from phi.ai.phi_ai import PhiAI

    conversation_type = ConversationType.AUTO if autonomous_conversation else ConversationType.RAG
    ai = PhiAI(new_conversation=start_new_conversation, conversation_type=conversation_type, phi_config=phi_config)
    if print_conversation_history:
        ai.print_conversation_history()

    ai.start_conversation(stream=stream)
