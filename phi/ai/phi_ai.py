from typing import Optional, Dict, List, Any, Iterator

from phi.api.schemas.user import UserSchema
from phi.cli.config import PhiCliConfig
from phi.cli.console import console
from phi.cli.settings import phi_cli_settings
from phi.workspace.config import WorkspaceConfig
from phi.utils.log import logger
from phi.utils.json_io import write_json_file, read_json_file


class PhiAI:
    def __init__(
        self,
        new_conversation: bool = False,
        phi_config: Optional[PhiCliConfig] = None,
        ws_config: Optional[WorkspaceConfig] = None,
    ):
        logger.debug("--**-- Starting Phi AI --**--")

        _phi_config = phi_config or PhiCliConfig.from_saved_config()
        if _phi_config is None:
            raise ValueError("Phi config not found. Please run `phi init`")
        _ws_config = ws_config or _phi_config.get_active_ws_config()
        if _ws_config is None:
            raise ValueError("Workspace config not found. Please run `phi ws setup`")
        _user = _phi_config.user
        if _user is None:
            raise ValueError("User not found. Please run `phi auth`")

        _conversation_id = None
        _conversation_history = None
        self.conversation_db: Optional[List[Dict[str, Any]]] = None
        if not new_conversation:
            latest_conversation = self.get_latest_conversation()
            if latest_conversation is not None:
                _conversation_id = latest_conversation.get("conversation_id")
                _conversation_history = latest_conversation.get("conversation_history")

        if _conversation_id is None:
            from phi.api.ai import conversation_create, ConversationCreateResponse

            _conversation: Optional[ConversationCreateResponse] = conversation_create(user=_user)
            if _conversation is None:
                raise Exception("Could not create conversation")

            _conversation_id = _conversation.id
            _conversation_history = _conversation.chat_history

        self.phi_config: PhiCliConfig = _phi_config
        self.ws_config: WorkspaceConfig = _ws_config
        self.user: UserSchema = _user
        self.conversation_id: int = _conversation_id
        self.conversation_history: List[Dict[str, Any]] = _conversation_history or []

        self.save_conversation()
        logger.debug(f"--**-- Conversation: {self.conversation_id} --**--")

    def start_conversation(self, stream: bool = False):
        from rich import box
        from rich.prompt import Prompt
        from rich.live import Live
        from rich.table import Table
        from rich.markdown import Markdown
        from phi.api.ai import conversation_chat

        conversation_active = True
        while conversation_active:
            username = self.user.username or "You"
            console.rule()
            user_message = Prompt.ask(f"[bold] :sunglasses: {username} [/bold]", console=console)
            self.conversation_history.append({"role": "user", "content": user_message})

            # -*- Quit conversation
            if user_message in ("exit", "quit", "bye"):
                conversation_active = False

            # -*- Send message to Phi AI
            api_response: Optional[Iterator[str]] = conversation_chat(
                user=self.user,
                conversation_id=self.conversation_id,
                message=user_message,
                stream=stream,
            )
            if api_response is None:
                logger.error("Could not reach Phi AI")
                conversation_active = False
            else:
                with Live(console=console) as live:
                    if stream:
                        chat_response = ""
                        for _response in api_response:
                            chat_response += _response
                            table = Table(show_header=False, box=box.ROUNDED)
                            table.add_row(Markdown(chat_response))
                            live.update(table)
                        self.conversation_history.append({"role": "assistant", "content": chat_response})
                    else:
                        chat_response = next(api_response)
                        table = Table(show_header=False, box=box.ROUNDED)
                        table.add_row(Markdown(chat_response))
                        console.print(table)
                        self.conversation_history.append({"role": "assistant", "content": chat_response})
            self.save_conversation()

    def print_conversation_history(self):
        from rich import box
        from rich.table import Table
        from rich.markdown import Markdown

        table = Table(show_header=False, box=box.ROUNDED, show_lines=True)
        table.add_column("Role", justify="right", style="cyan")
        table.add_column("Message", justify="left", style="magenta")

        for message in self.conversation_history:
            if message["role"] == "system":
                continue
            elif message["role"] == "assistant":
                table.add_row("phi", Markdown(message["content"]))
            elif message["role"] == "user":
                username = self.user.username or "You"
                table.add_row(username, Markdown(message["content"]))
            else:
                table.add_row(message["role"], Markdown(message["content"]))
        console.print(table)
        # for message in self.conversation_history:
        #     if message["role"] == "system":
        #         continue
        #     elif message["role"] == "assistant":
        #         padding = " " * (self.column_width - len("Phi"))
        #         print_info(f":sunglasses: Phi{padding}: {message['content']}")
        #     elif message["role"] == "user":
        #         username = self.user.username or "You"
        #         padding = " " * (self.column_width - len(username))
        #         print_info(f":sunglasses: {username}{padding}: {message['content']}")
        #     else:
        #         padding = " " * (self.column_width - len(message["role"]))
        #         print_info(f":sunglasses: {message['role']}:{padding}: {message['content']}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "conversation_history": self.conversation_history,
        }

    def save_conversation(self):
        if self.conversation_id is None:
            return

        all_conversations = self.get_all_conversations()
        # Pop the latest conversation if it exists
        if len(all_conversations) > 0:
            all_conversations.pop(0)

        # Add the latest conversation
        all_conversations.insert(0, self.to_dict())
        write_json_file(file_path=phi_cli_settings.ai_conversations_path, data=all_conversations)

    def get_all_conversations(self) -> List[Dict[str, Any]]:
        try:
            if self.conversation_db is not None:
                return self.conversation_db
            stored_conversations = read_json_file(file_path=phi_cli_settings.ai_conversations_path)
            if stored_conversations is not None and isinstance(stored_conversations, list):
                self.conversation_db = stored_conversations
                return self.conversation_db
        except Exception as e:
            logger.warning(f"Could not read conversations in {phi_cli_settings.ai_conversations_path}: {e}")
        return []

    def get_latest_conversation(self) -> Optional[Dict[str, Any]]:
        conversations = self.get_all_conversations()
        if len(conversations) == 0:
            return None
        return conversations[0]
