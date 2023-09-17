from phi.cli.config import PhiCliConfig
from phi.workspace.config import WorkspaceConfig


def phi_ai_conversation(
    phi_config: PhiCliConfig,
    ws_config: WorkspaceConfig,
    start_new_conversation: bool = False,
    show_previous_messages: bool = False,
    stream: bool = False,
) -> None:
    """Start a conversation with Phi AI."""

    from phi.ai.phi_ai import PhiAI

    ai = PhiAI(new_conversation=start_new_conversation, phi_config=phi_config, ws_config=ws_config)
    if show_previous_messages:
        ai.print_conversation_history()

    ai.start_conversation(stream=stream)
