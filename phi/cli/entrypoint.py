"""Phi Cli

This is the entrypoint for the `phi` cli application.
"""
from typing import Optional

import typer

from phi.cli.ws.ws_cli import ws_cli
from phi.cli.k.k_cli import k_cli
from phi.utils.log import set_log_level_to_debug

phi_cli = typer.Typer(
    help="""\b
Phidata is an AI toolkit for engineers.
\b
Usage:
1. Run `phi ws create` to create a new workspace
2. Run `phi ws up` to start the workspace
3. Run `phi ws down` to stop the workspace
""",
    no_args_is_help=True,
    add_completion=False,
    invoke_without_command=True,
    options_metavar="\b",
    subcommand_metavar="[COMMAND] [OPTIONS]",
    pretty_exceptions_show_locals=False,
)


@phi_cli.command(short_help="Initialize phidata, use -r to reset")
def init(
    reset: bool = typer.Option(False, "--reset", "-r", help="Reset phidata", show_default=True),
    print_debug_log: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Print debug logs.",
    ),
    login: bool = typer.Option(False, "--login", "-l", help="Login with phidata.com", show_default=True),
):
    """
    \b
    Initialize phidata, use -r to reset

    \b
    Examples:
    * `phi init`    -> Initializing phidata
    * `phi init -r` -> Reset and initializing phidata
    """
    if print_debug_log:
        set_log_level_to_debug()

    from phi.cli.operator import initialize_phi

    initialize_phi(reset=reset, login=login)


@phi_cli.command(short_help="Reset phi installation")
def reset(
    print_debug_log: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Print debug logs.",
    ),
):
    """
    \b
    Reset the existing phidata installation
    After resetting please run `phi init` to initialize again.
    """
    if print_debug_log:
        set_log_level_to_debug()

    from phi.cli.operator import initialize_phi

    initialize_phi(reset=True)


@phi_cli.command(short_help="Authenticate with phidata.com")
def auth(
    print_debug_log: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Print debug logs.",
    ),
):
    """
    \b
    Authenticate your account with phidata.
    """
    if print_debug_log:
        set_log_level_to_debug()

    from phi.cli.operator import authenticate_user

    authenticate_user()


@phi_cli.command(short_help="Log in from the cli", hidden=True)
def login(
    print_debug_log: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Print debug logs.",
    ),
):
    """
    \b
    Log in from the cli

    \b
    Examples:
    * `phi login`
    """
    if print_debug_log:
        set_log_level_to_debug()

    from phi.cli.operator import sign_in_using_cli

    sign_in_using_cli()


@phi_cli.command(short_help="Ping phidata servers")
def ping(
    print_debug_log: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Print debug logs.",
    ),
):
    """Ping the phidata servers and check if you are authenticated"""
    if print_debug_log:
        set_log_level_to_debug()

    from phi.api.user import user_ping
    from phi.cli.console import print_info

    ping_success = user_ping()
    if ping_success:
        print_info("Ping successful")
    else:
        print_info("Could not ping phidata servers")


@phi_cli.command(short_help="Print phi config")
def config(
    print_debug_log: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Print debug logs.",
    ),
    show_all: bool = typer.Option(
        False,
        "-a",
        "--all",
        help="Show all workspaces",
    ),
):
    """Print your current phidata config"""
    if print_debug_log:
        set_log_level_to_debug()

    from phi.cli.config import PhiCliConfig
    from phi.cli.console import print_info

    conf: Optional[PhiCliConfig] = PhiCliConfig.from_saved_config()
    if conf is not None:
        conf.print_to_cli(show_all=show_all)
    else:
        print_info("Phi not initialized, run `phi init` to get started")


@phi_cli.command(short_help="Set current directory as active workspace")
def set(
    ws_name: str = typer.Option(None, "-ws", help="Active workspace name"),
    print_debug_log: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Print debug logs.",
    ),
):
    """
    \b
    Set the current directory as the active workspace.
    This command can be run from within the workspace directory
        OR with a -ws flag to set another workspace as primary.

    Set a workspace as active

    \b
    Examples:
    $ `phi ws set`           -> Set the current directory as the active phidata workspace
    $ `phi ws set -ws idata` -> Set the workspace named idata as the active phidata workspace
    """
    from phi.workspace.operator import set_workspace_as_active

    if print_debug_log:
        set_log_level_to_debug()

    set_workspace_as_active(ws_dir_name=ws_name)


@phi_cli.command(short_help="Chat with Phi AI", options_metavar="")
def ai(
    batch: bool = typer.Option(
        False,
        "-b",
        "--batch",
        help="Return the response as a batch i.e do not stream the response.",
    ),
    start_new_conversation: bool = typer.Option(
        False,
        "-n",
        "--new",
        help="Start a new conversation.",
    ),
    show_previous_messages: bool = typer.Option(
        False,
        "-a",
        "--all",
        help="Show all previous messages.",
    ),
    print_debug_log: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Print debug logs.",
    ),
):
    """
    Chat with Phi AI

    \b
    Examples:
    $ `phi ai`      -> Start a conversation with Phi AI
    """

    if print_debug_log:
        set_log_level_to_debug()

    from pathlib import Path
    from phi.cli.config import PhiCliConfig
    from phi.cli.console import (
        print_info,
        log_config_not_available_msg,
        log_active_workspace_not_available,
        print_available_workspaces,
    )
    from phi.workspace.config import WorkspaceConfig
    from phi.ai.operator import phi_ai_conversation

    phi_config: Optional[PhiCliConfig] = PhiCliConfig.from_saved_config()
    if not phi_config:
        log_config_not_available_msg()
        return

    active_ws_config: Optional[WorkspaceConfig] = phi_config.get_active_ws_config()
    if active_ws_config is None:
        log_active_workspace_not_available()
        avl_ws = phi_config.available_ws
        if avl_ws:
            print_available_workspaces(avl_ws)
        return

    current_path: Path = Path(".").resolve()
    if active_ws_config.ws_root_path != current_path:
        ws_at_current_path = phi_config.get_ws_config_by_path(current_path)
        if ws_at_current_path is not None:
            print_info(
                f"Workspace at the current directory ({ws_at_current_path.ws_dir_name}) "
                + f"is not the Active Workspace ({active_ws_config.ws_dir_name})"
            )
            update_active_workspace = typer.confirm(
                f"Update active workspace to {ws_at_current_path.ws_dir_name}", default=True
            )
            if update_active_workspace:
                phi_config.active_ws_dir = ws_at_current_path.ws_dir_name
                active_ws_config = ws_at_current_path

    phi_ai_conversation(
        phi_config=phi_config,
        ws_config=active_ws_config,
        start_new_conversation=start_new_conversation,
        show_previous_messages=show_previous_messages,
        stream=(not batch),
    )


# @phi_cli.command(short_help="Start resources defined in a resources.py file")
# def start(
#     resources_file: str = typer.Argument(
#         "resources.py",
#         help="Path to workspace file.",
#         show_default=False,
#     ),
#     env_filter: Optional[str] = typer.Option(
#         None, "-e", "--env", metavar="", help="Filter the environment to deploy"
#     ),
#     config_filter: Optional[str] = typer.Option(
#         None, "-c", "--config", metavar="", help="Filter the config to deploy"
#     ),
#     name_filter: Optional[str] = typer.Option(
#         None, "-n", "--name", metavar="", help="Filter using resource name"
#     ),
#     type_filter: Optional[str] = typer.Option(
#         None,
#         "-t",
#         "--type",
#         metavar="",
#         help="Filter using resource type",
#     ),
#     group_filter: Optional[str] = typer.Option(
#         None, "-g", "--group", metavar="", help="Filter using group name"
#     ),
#     dry_run: bool = typer.Option(
#         False,
#         "-dr",
#         "--dry-run",
#         help="Print which resources will be deployed and exit.",
#     ),
#     auto_confirm: bool = typer.Option(
#         False,
#         "-y",
#         "--yes",
#         help="Skip the confirmation before deploying resources.",
#     ),
#     print_debug_log: bool = typer.Option(
#         False,
#         "-d",
#         "--debug",
#         help="Print debug logs.",
#     ),
#     force: bool = typer.Option(
#         False,
#         "-f",
#         "--force",
#         help="Force",
#     ),
# ):
#     """\b
#     Start resources defined in a resources.py file
#     \b
#     Examples:
#     > `phi ws start`                -> Start resources defined in a resources.py file
#     > `phi ws start workspace.py`   -> Start resources defined in a workspace.py file
#     """
#     from pathlib import Path
#     from phi.conf.phi_conf import PhiConf
#     from phi.cli.operator import start_resources
#     from phi.utils.load_env import load_env
#     from phi.utils.cli_console import print_error, print_conf_not_available_msg
#     from phi.workspace.ws_enums import WorkspaceConfigType
#
#     if print_debug_log:
#         set_log_level_to_debug()
#
#     phi_conf: Optional[PhiConf] = PhiConf.get_saved_conf()
#     if not phi_conf:
#         print_conf_not_available_msg()
#         return
#
#     # Load environment from .env
#     load_env(
#         env={
#             "PHI_WS_FORCE": str(force),
#         },
#         dotenv_dir=Path(".").resolve(),
#     )
#
#     target_env: Optional[str] = None
#     target_config_str: Optional[str] = None
#     target_config: Optional[WorkspaceConfigType] = None
#     target_name: Optional[str] = None
#     target_type: Optional[str] = None
#     target_group: Optional[str] = None
#
#     if env_filter is not None and isinstance(env_filter, str):
#         target_env = env_filter
#     if config_filter is not None and isinstance(config_filter, str):
#         target_config_str = config_filter
#     if name_filter is not None and isinstance(name_filter, str):
#         target_name = name_filter
#     if type_filter is not None and isinstance(type_filter, str):
#         target_type = type_filter
#     if group_filter is not None and isinstance(group_filter, str):
#         target_group = group_filter
#
#     if target_config_str is not None:
#         if target_config_str.lower() not in WorkspaceConfigType.values_list():
#             print_error(
#                 f"{target_config_str} not supported",
#                 f"please choose from: {WorkspaceConfigType.values_list()}"
#             )
#             return
#         target_config = WorkspaceConfigType.from_str(target_config_str)
#
#     resources_file_path: Path = Path(".").resolve().joinpath(resources_file)
#     start_resources(
#         resources_file_path=resources_file_path,
#         target_env=target_env,
#         target_config=target_config,
#         target_name=target_name,
#         target_type=target_type,
#         target_group=target_group,
#         dry_run=dry_run,
#         auto_confirm=auto_confirm,
#     )
#
#
# @phi_cli.command(short_help="Stop resources defined in a resources.py file")
# def stop(
#     resources_file: str = typer.Argument(
#         "resources.py",
#         help="Path to workspace file.",
#         show_default=False,
#     ),
#     env_filter: Optional[str] = typer.Option(
#         None, "-e", "--env", metavar="", help="Filter the environment to deploy"
#     ),
#     config_filter: Optional[str] = typer.Option(
#         None, "-c", "--config", metavar="", help="Filter the config to deploy"
#     ),
#     name_filter: Optional[str] = typer.Option(
#         None, "-n", "--name", metavar="", help="Filter using resource name"
#     ),
#     type_filter: Optional[str] = typer.Option(
#         None,
#         "-t",
#         "--type",
#         metavar="",
#         help="Filter using resource type",
#     ),
#     group_filter: Optional[str] = typer.Option(
#         None, "-g", "--group", metavar="", help="Filter using group name"
#     ),
#     dry_run: bool = typer.Option(
#         False,
#         "-dr",
#         "--dry-run",
#         help="Print which resources will be deployed and exit.",
#     ),
#     auto_confirm: bool = typer.Option(
#         False,
#         "-y",
#         "--yes",
#         help="Skip the confirmation before deploying resources.",
#     ),
#     print_debug_log: bool = typer.Option(
#         False,
#         "-d",
#         "--debug",
#         help="Print debug logs.",
#     ),
#     force: bool = typer.Option(
#         False,
#         "-f",
#         "--force",
#         help="Force",
#     ),
# ):
#     """\b
#     Start resources defined in a resources.py file
#     \b
#     Examples:
#     > `phi ws start`                -> Start resources defined in a resources.py file
#     > `phi ws start workspace.py`   -> Start resources defined in a workspace.py file
#     """
#     from pathlib import Path
#     from phi.conf.phi_conf import PhiConf
#
#     from phi.cli.operator import stop_resources
#     from phi.utils.load_env import load_env
#     from phi.utils.cli_console import print_error, print_conf_not_available_msg
#     from phi.workspace.ws_enums import WorkspaceConfigType
#
#     if print_debug_log:
#         set_log_level_to_debug()
#
#     phi_conf: Optional[PhiConf] = PhiConf.get_saved_conf()
#     if not phi_conf:
#         print_conf_not_available_msg()
#         return
#
#     # Load environment from .env
#     load_env(
#         env={
#             "PHI_WS_FORCE": str(force),
#         },
#         dotenv_dir=Path(".").resolve(),
#     )
#
#     target_env: Optional[str] = None
#     target_config_str: Optional[str] = None
#     target_config: Optional[WorkspaceConfigType] = None
#     target_name: Optional[str] = None
#     target_type: Optional[str] = None
#     target_group: Optional[str] = None
#
#     if env_filter is not None and isinstance(env_filter, str):
#         target_env = env_filter
#     if config_filter is not None and isinstance(config_filter, str):
#         target_config_str = config_filter
#     if name_filter is not None and isinstance(name_filter, str):
#         target_name = name_filter
#     if type_filter is not None and isinstance(type_filter, str):
#         target_type = type_filter
#     if group_filter is not None and isinstance(group_filter, str):
#         target_group = group_filter
#
#     if target_config_str is not None:
#         if target_config_str.lower() not in WorkspaceConfigType.values_list():
#             print_error(
#                 f"{target_config_str} not supported",
#                 f"please choose from: {WorkspaceConfigType.values_list()}"
#             )
#             return
#         target_config = WorkspaceConfigType.from_str(target_config_str)
#
#     resources_file_path: Path = Path(".").resolve().joinpath(resources_file)
#     stop_resources(
#         resources_file_path=resources_file_path,
#         target_env=target_env,
#         target_config=target_config,
#         target_name=target_name,
#         target_type=target_type,
#         target_group=target_group,
#         dry_run=dry_run,
#         auto_confirm=auto_confirm,
#     )
#
#
# @phi_cli.command(short_help="Update resources defined in a resources.py file")
# def patch(
#     resources_file: str = typer.Argument(
#         "resources.py",
#         help="Path to workspace file.",
#         show_default=False,
#     ),
#     env_filter: Optional[str] = typer.Option(
#         None, "-e", "--env", metavar="", help="Filter the environment to deploy"
#     ),
#     config_filter: Optional[str] = typer.Option(
#         None, "-c", "--config", metavar="", help="Filter the config to deploy"
#     ),
#     name_filter: Optional[str] = typer.Option(
#         None, "-n", "--name", metavar="", help="Filter using resource name"
#     ),
#     type_filter: Optional[str] = typer.Option(
#         None,
#         "-t",
#         "--type",
#         metavar="",
#         help="Filter using resource type",
#     ),
#     group_filter: Optional[str] = typer.Option(
#         None, "-g", "--group", metavar="", help="Filter using group name"
#     ),
#     dry_run: bool = typer.Option(
#         False,
#         "-dr",
#         "--dry-run",
#         help="Print which resources will be deployed and exit.",
#     ),
#     auto_confirm: bool = typer.Option(
#         False,
#         "-y",
#         "--yes",
#         help="Skip the confirmation before deploying resources.",
#     ),
#     print_debug_log: bool = typer.Option(
#         False,
#         "-d",
#         "--debug",
#         help="Print debug logs.",
#     ),
#     force: bool = typer.Option(
#         False,
#         "-f",
#         "--force",
#         help="Force",
#     ),
# ):
#     """\b
#     Start resources defined in a resources.py file
#     \b
#     Examples:
#     > `phi ws start`                -> Start resources defined in a resources.py file
#     > `phi ws start workspace.py`   -> Start resources defined in a workspace.py file
#     """
#     from pathlib import Path
#     from phi.conf.phi_conf import PhiConf
#
#     from phi.cli.operator import patch_resources
#     from phi.utils.load_env import load_env
#     from phi.utils.cli_console import print_error, print_conf_not_available_msg
#     from phi.workspace.ws_enums import WorkspaceConfigType
#
#     if print_debug_log:
#         set_log_level_to_debug()
#
#     phi_conf: Optional[PhiConf] = PhiConf.get_saved_conf()
#     if not phi_conf:
#         print_conf_not_available_msg()
#         return
#
#     # Load environment from .env
#     load_env(
#         env={
#             "PHI_WS_FORCE": str(force),
#         },
#         dotenv_dir=Path(".").resolve(),
#     )
#
#     target_env: Optional[str] = None
#     target_config_str: Optional[str] = None
#     target_config: Optional[WorkspaceConfigType] = None
#     target_name: Optional[str] = None
#     target_type: Optional[str] = None
#     target_group: Optional[str] = None
#
#     if env_filter is not None and isinstance(env_filter, str):
#         target_env = env_filter
#     if config_filter is not None and isinstance(config_filter, str):
#         target_config_str = config_filter
#     if name_filter is not None and isinstance(name_filter, str):
#         target_name = name_filter
#     if type_filter is not None and isinstance(type_filter, str):
#         target_type = type_filter
#     if group_filter is not None and isinstance(group_filter, str):
#         target_group = group_filter
#
#     if target_config_str is not None:
#         if target_config_str.lower() not in WorkspaceConfigType.values_list():
#             print_error(
#                 f"{target_config_str} not supported",
#                 f"please choose from: {WorkspaceConfigType.values_list()}"
#             )
#             return
#         target_config = WorkspaceConfigType.from_str(target_config_str)
#
#     resources_file_path: Path = Path(".").resolve().joinpath(resources_file)
#     patch_resources(
#         resources_file_path=resources_file_path,
#         target_env=target_env,
#         target_config=target_config,
#         target_name=target_name,
#         target_type=target_type,
#         target_group=target_group,
#         dry_run=dry_run,
#         auto_confirm=auto_confirm,
#     )
#
#
# @phi_cli.command(short_help="Restart resources defined in a resources.py file")
# def restart(
#     resources_file: str = typer.Argument(
#         "resources.py",
#         help="Path to workspace file.",
#         show_default=False,
#     ),
#     env_filter: Optional[str] = typer.Option(
#         None, "-e", "--env", metavar="", help="Filter the environment to deploy"
#     ),
#     config_filter: Optional[str] = typer.Option(
#         None, "-c", "--config", metavar="", help="Filter the config to deploy"
#     ),
#     name_filter: Optional[str] = typer.Option(
#         None, "-n", "--name", metavar="", help="Filter using resource name"
#     ),
#     type_filter: Optional[str] = typer.Option(
#         None,
#         "-t",
#         "--type",
#         metavar="",
#         help="Filter using resource type",
#     ),
#     group_filter: Optional[str] = typer.Option(
#         None, "-g", "--group", metavar="", help="Filter using group name"
#     ),
#     dry_run: bool = typer.Option(
#         False,
#         "-dr",
#         "--dry-run",
#         help="Print which resources will be deployed and exit.",
#     ),
#     auto_confirm: bool = typer.Option(
#         False,
#         "-y",
#         "--yes",
#         help="Skip the confirmation before deploying resources.",
#     ),
#     print_debug_log: bool = typer.Option(
#         False,
#         "-d",
#         "--debug",
#         help="Print debug logs.",
#     ),
#     force: bool = typer.Option(
#         False,
#         "-f",
#         "--force",
#         help="Force",
#     ),
# ):
#     """\b
#     Restart resources defined in a resources.py file
#     \b
#     Examples:
#     > `phi ws restart`                -> Start resources defined in a resources.py file
#     > `phi ws restart workspace.py`   -> Start resources defined in a workspace.py file
#     """
#     from time import sleep
#     from phi.utils.cli_console import print_info
#
#     stop(
#         resources_file=resources_file,
#         env_filter=env_filter,
#         config_filter=config_filter,
#         name_filter=name_filter,
#         type_filter=type_filter,
#         group_filter=group_filter,
#         dry_run=dry_run,
#         auto_confirm=auto_confirm,
#         print_debug_log=print_debug_log,
#         force=force,
#     )
#     print_info("Sleeping for 2 seconds..")
#     sleep(2)
#     start(
#         resources_file=resources_file,
#         env_filter=env_filter,
#         config_filter=config_filter,
#         name_filter=name_filter,
#         type_filter=type_filter,
#         group_filter=group_filter,
#         dry_run=dry_run,
#         auto_confirm=auto_confirm,
#         print_debug_log=print_debug_log,
#         force=force,
#     )


phi_cli.add_typer(ws_cli)
phi_cli.add_typer(k_cli)
