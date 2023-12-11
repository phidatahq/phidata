import json
from typing import Optional, Dict, List, Any, Iterator

from rich import box
from rich.prompt import Prompt
from rich.live import Live
from rich.table import Table
from rich.markdown import Markdown

from phi.api.ai import conversation_chat
from phi.api.schemas.user import UserSchema
from phi.api.schemas.ai import ConversationType
from phi.cli.config import PhiCliConfig
from phi.cli.console import console
from phi.cli.settings import phi_cli_settings
from phi.llm.message import Message
from phi.tools.function import Function, FunctionCall
from phi.tools.shell import ShellTools
from phi.tools.phi import PhiTools
from phi.workspace.config import WorkspaceConfig
from phi.utils.log import logger
from phi.utils.functions import get_function_call
from phi.utils.timer import Timer
from phi.utils.json_io import write_json_file, read_json_file


class PhiAI:
    def __init__(
        self,
        new_conversation: bool = False,
        conversation_type: ConversationType = ConversationType.RAG,
        phi_config: Optional[PhiCliConfig] = None,
    ):
        logger.debug("--**-- Starting Phi AI --**--")

        _phi_config = phi_config or PhiCliConfig.from_saved_config()
        if _phi_config is None:
            raise ValueError("Phi config not found. Please run `phi init`")
        _user = _phi_config.user
        if _user is None:
            raise ValueError("User not found. Please run `phi auth`")
        _active_workspace = _phi_config.get_active_ws_config()

        self.conversation_db: Optional[List[Dict[str, Any]]] = None
        self.functions: Dict[str, Function] = {**ShellTools().functions, **PhiTools().functions}

        _conversation_id = None
        _conversation_history = None
        if not new_conversation:
            latest_conversation = self.get_latest_conversation()
            if latest_conversation is not None:
                # Check if the latest conversation is of the same type and user
                if latest_conversation.get("conversation_type") == conversation_type and latest_conversation.get(
                    "user"
                ) == _user.model_dump(include={"id_user", "email"}):
                    logger.debug("Found conversation for the same user and type")
                    # Check if the latest conversation is for the same workspace
                    if _active_workspace is not None and latest_conversation.get(
                        "workspace"
                    ) == _active_workspace.model_dump(include={"ws_dir_name"}):
                        logger.debug("Found conversation for the same workspace")
                        # Check if the latest conversation has the same functions
                        if latest_conversation.get("functions") == list(self.functions.keys()):
                            logger.debug("Found conversation with the same functions")
                            _conversation_id = latest_conversation.get("conversation_id")
                            _conversation_history = latest_conversation.get("conversation_history")

        if _conversation_id is None:
            from phi.api.ai import conversation_create, ConversationCreateResponse

            _conversation: Optional[ConversationCreateResponse] = conversation_create(
                user=_user, conversation_type=conversation_type, functions=self.functions
            )
            if _conversation is None:
                logger.error("Could not create conversation, please authenticate using `phi auth`")
                exit(0)

            _conversation_id = _conversation.id
            _conversation_history = _conversation.chat_history

        self.phi_config: PhiCliConfig = _phi_config
        self.user: UserSchema = _user
        self.active_workspace: Optional[WorkspaceConfig] = _active_workspace
        self.conversation_id: str = _conversation_id
        self.conversation_history: List[Dict[str, Any]] = _conversation_history or []
        self.conversation_type: ConversationType = conversation_type

        self.save_conversation()
        logger.debug(f"--**-- Conversation: {self.conversation_id} --**--")

    def start_conversation(self, stream: bool = False):
        conversation_active = True
        while conversation_active:
            username = self.user.username or "You"
            console.rule()
            user_message_str = None
            user_message_str_valid = False
            while not user_message_str_valid:
                user_message_str = Prompt.ask(f"[bold] :sunglasses: {username} [/bold]", console=console)
                if user_message_str is None or user_message_str == "":
                    console.print("Please enter a valid message")
                    continue
                user_message_str_valid = True
            if user_message_str is None:
                raise ValueError("Message invalid")
            self.conversation_history.append({"role": "user", "content": user_message_str})

            # -*- Quit conversation
            if user_message_str in ("exit", "quit", "bye"):
                conversation_active = False
                break

            # -*- Send message to Phi AI
            api_response: Optional[Iterator[str]] = conversation_chat(
                user=self.user,
                conversation_id=self.conversation_id,
                message=Message(role="user", content=user_message_str),
                conversation_type=self.conversation_type,
                functions=self.functions,
                stream=stream,
            )
            if api_response is None:
                logger.error("Could not reach Phi AI")
                conversation_active = False
            else:
                with Live(console=console) as live:
                    response_content = ""
                    if stream:
                        for _response in api_response:
                            if _response is None or _response == "" or _response == "{}":
                                continue
                            response_dict = json.loads(_response)
                            if "content" in response_dict and response_dict.get("content") is not None:
                                response_content += response_dict.get("content")
                                table = Table(show_header=False, box=box.ROUNDED)
                                table.add_row(Markdown(response_content))
                                live.update(table)
                            elif "function_call" in response_dict:
                                for function_response in self.run_function_stream(response_dict.get("function_call")):
                                    response_content += function_response
                                    table = Table(show_header=False, box=box.ROUNDED)
                                    table.add_row(Markdown(response_content))
                                    live.update(table)
                    else:
                        _response = next(api_response)
                        if _response is None or _response == "" or _response == "{}":
                            response_content = "Something went wrong, please try again."
                        else:
                            response_dict = json.loads(_response)
                            if "content" in response_dict and response_dict.get("content") is not None:
                                response_content = response_dict.get("content")
                            elif "function_call" in response_dict:
                                response_content = self.run_function(response_dict.get("function_call"))
                        table = Table(show_header=False, box=box.ROUNDED)
                        table.add_row(Markdown(response_content))
                        console.print(table)
                    self.conversation_history.append({"role": "assistant", "content": response_content})
            self.save_conversation()

    def run_function_stream(self, function_call: Dict[str, Any]) -> Iterator[str]:
        _function_name = function_call.get("name")
        _function_arguments_str = function_call.get("arguments")
        if _function_name is not None:
            function_call_obj: Optional[FunctionCall] = get_function_call(
                name=_function_name, arguments=_function_arguments_str, functions=self.functions
            )
            if function_call_obj is None:
                return "Something went wrong, please try again."

            # -*- Run function call
            yield f"Running: {function_call_obj.get_call_str()}\n\n"
            function_call_timer = Timer()
            function_call_timer.start()
            function_call_obj.execute()
            function_call_timer.stop()
            function_call_message = Message(
                role="function",
                name=function_call_obj.function.name,
                content=function_call_obj.result,
                metrics={"time": function_call_timer.elapsed},
            )
            # -*- Send message to Phi AI
            api_response: Optional[Iterator[str]] = conversation_chat(
                user=self.user,
                conversation_id=self.conversation_id,
                message=function_call_message,
                conversation_type=self.conversation_type,
                functions=self.functions,
                stream=True,
            )
            if api_response is not None:
                for _response in api_response:
                    if _response is None or _response == "" or _response == "{}":
                        continue
                    response_dict = json.loads(_response)
                    if "content" in response_dict and response_dict.get("content") is not None:
                        yield response_dict.get("content")
                    elif "function_call" in response_dict:
                        yield from self.run_function_stream(response_dict.get("function_call"))
        else:
            yield "Could not run function, please try again."

    def run_function(self, function_call: Dict[str, Any]) -> str:
        _function_name = function_call.get("name")
        _function_arguments_str = function_call.get("arguments")
        if _function_name is not None:
            function_call_obj: Optional[FunctionCall] = get_function_call(
                name=_function_name, arguments=_function_arguments_str, functions=self.functions
            )
            if function_call_obj is None:
                return "Something went wrong, please try again."

            # -*- Run function call
            function_run_response = f"Running: {function_call_obj.get_call_str()}\n\n"
            function_call_timer = Timer()
            function_call_timer.start()
            function_call_obj.execute()
            function_call_timer.stop()
            function_call_message = Message(
                role="function",
                name=function_call_obj.function.name,
                content=function_call_obj.result,
                metrics={"time": function_call_timer.elapsed},
            )
            # -*- Send message to Phi AI
            api_response: Optional[Iterator[str]] = conversation_chat(
                user=self.user,
                conversation_id=self.conversation_id,
                message=function_call_message,
                conversation_type=self.conversation_type,
                functions=self.functions,
                stream=False,
            )
            if api_response is not None:
                _response = next(api_response)
                if _response is None or _response == "" or _response == "{}":
                    function_run_response += "Something went wrong, please try again."
                else:
                    response_dict = json.loads(_response)
                    if "content" in response_dict and response_dict.get("content") is not None:
                        function_run_response += response_dict.get("content")
                    elif "function_call" in response_dict:
                        function_run_response += self.run_function(response_dict.get("function_call"))
            return function_run_response
        return "Something went wrong, please try again."

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "conversation_history": self.conversation_history,
            "conversation_type": self.conversation_type,
            "user": self.user.model_dump(include={"id_user", "email"}),
            "workspace": self.active_workspace.model_dump(include={"ws_root_path"})
            if self.active_workspace is not None
            else None,
            "functions": list(self.functions.keys()),
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

    # async def conversation(self, stream: bool = False):
    #     from rich import box
    #     from rich.prompt import Prompt
    #     from rich.live import Live
    #     from rich.table import Table
    #     from rich.markdown import Markdown
    #     from phi.api.ai import ai_ws_connect
    #
    #     logger.info("Starting conversation with Phi AI")
    #
    #     conversation_active = True
    #     username = self.user.username or "You"
    #     async with ai_ws_connect(
    #         user=self.user,
    #         conversation_id=self.conversation_id,
    #         conversation_type=self.conversation_type,
    #         stream=stream,
    #     ) as ai_ws:
    #         while conversation_active:
    #             console.rule()
    #             user_message = Prompt.ask(f"[bold] :sunglasses: {username} [/bold]", console=console)
    #             self.conversation_history.append({"role": "user", "content": user_message})
    #
    #             # -*- Quit conversation
    #             if user_message in ("exit", "quit", "bye"):
    #                 conversation_active = False
    #
    #             # -*- Send message to Phi AI
    #             await ai_ws.send(user_message)
    #             with Live(console=console) as live:
    #                 if stream:
    #                     chat_response = ""
    #                     ai_response_chunk = await ai_ws.recv()
    #                     while ai_response_chunk is not None and ai_response_chunk != "AI_RESPONSE_STOP_STREAM":
    #                         chat_response += ai_response_chunk
    #                         table = Table(show_header=False, box=box.ROUNDED)
    #                         table.add_row(Markdown(chat_response))
    #                         live.update(table)
    #                         ai_response_chunk = await ai_ws.recv()
    #                         if ai_response_chunk is None or ai_response_chunk == "AI_RESPONSE_STOP_STREAM":
    #                             break
    #                         if ai_response_chunk.startswith("{"):
    #                             await ai_ws.send("function_result:one")
    #                     self.conversation_history.append({"role": "assistant", "content": chat_response})
    #                 else:
    #                     ai_response = await ai_ws.recv()
    #                     logger.info(f"ai_response: {type(ai_response)} | {ai_response}")
    #
    #                     if ai_response is None:
    #                         logger.error("Could not reach Phi AI")
    #                         conversation_active = False
    #                     chat_response = ai_response
    #                     table = Table(show_header=False, box=box.ROUNDED)
    #                     table.add_row(Markdown(chat_response))
    #                     console.print(table)
    #                     self.conversation_history.append({"role": "assistant", "content": chat_response})
    #             self.save_conversation()
