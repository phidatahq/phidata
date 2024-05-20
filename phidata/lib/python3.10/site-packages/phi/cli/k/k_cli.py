"""Phidata Kubectl Cli

This is the entrypoint for the `phi k` commands.
"""

from pathlib import Path
from typing import Optional

import typer

from phi.cli.console import (
    print_info,
    log_config_not_available_msg,
    log_active_workspace_not_available,
    print_available_workspaces,
)
from phi.utils.log import logger, set_log_level_to_debug

k_cli = typer.Typer(
    name="k",
    short_help="Manage kubernetes resources",
    help="""\b
Use `phi k [COMMAND]` to save, get, update kubernetes resources.
Run `phi k [COMMAND] --help` for more info.
""",
    no_args_is_help=True,
    add_completion=False,
    invoke_without_command=True,
    options_metavar="",
    subcommand_metavar="[COMMAND] [OPTIONS]",
)


@k_cli.command(short_help="Save your K8s Resources")
def save(
    resource_filter: Optional[str] = typer.Argument(
        None,
        help="Resource filter. Format - ENV:GROUP:NAME:TYPE",
    ),
    env_filter: Optional[str] = typer.Option(None, "-e", "--env", metavar="", help="Filter the environment to deploy."),
    group_filter: Optional[str] = typer.Option(
        None, "-g", "--group", metavar="", help="Filter resources using group name."
    ),
    name_filter: Optional[str] = typer.Option(None, "-n", "--name", metavar="", help="Filter resource using name."),
    type_filter: Optional[str] = typer.Option(
        None,
        "-t",
        "--type",
        metavar="",
        help="Filter resource using type",
    ),
    print_debug_log: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Print debug logs.",
    ),
):
    """
    Saves your k8s resources. Used to validate what is being deployed

    \b
    Examples:
    > `phi k save`      -> Save resources for the active workspace
    """
    if print_debug_log:
        set_log_level_to_debug()

    from phi.cli.config import PhiCliConfig
    from phi.workspace.config import WorkspaceConfig
    from phi.k8s.operator import save_resources
    from phi.utils.resource_filter import parse_k8s_resource_filter

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
            active_ws_dir_name = active_ws_config.ws_root_path.stem
            ws_at_current_path_dir_name = ws_at_current_path.ws_root_path.stem

            print_info(
                f"Workspace at the current directory ({ws_at_current_path_dir_name}) "
                + f"is not the Active Workspace ({active_ws_dir_name})"
            )
            update_active_workspace = typer.confirm(
                f"Update active workspace to {ws_at_current_path_dir_name}", default=True
            )
            if update_active_workspace:
                phi_config.set_active_ws_dir(ws_at_current_path.ws_root_path)
                active_ws_config = ws_at_current_path

    target_env: Optional[str] = None
    target_group: Optional[str] = None
    target_name: Optional[str] = None
    target_type: Optional[str] = None

    # derive env:infra:name:type:group from ws_filter
    if resource_filter is not None:
        if not isinstance(resource_filter, str):
            raise TypeError(f"Invalid resource_filter. Expected: str, Received: {type(resource_filter)}")
        (
            target_env,
            target_group,
            target_name,
            target_type,
        ) = parse_k8s_resource_filter(resource_filter)

    # derive env:infra:name:type:group from command options
    if target_env is None and env_filter is not None and isinstance(env_filter, str):
        target_env = env_filter
    if target_group is None and group_filter is not None and isinstance(group_filter, str):
        target_group = group_filter
    if target_name is None and name_filter is not None and isinstance(name_filter, str):
        target_name = name_filter
    if target_type is None and type_filter is not None and isinstance(type_filter, str):
        target_type = type_filter

    logger.debug("Processing workspace")
    logger.debug(f"\ttarget_env   : {target_env}")
    logger.debug(f"\ttarget_group : {target_group}")
    logger.debug(f"\ttarget_name  : {target_name}")
    logger.debug(f"\ttarget_type  : {target_type}")
    save_resources(
        phi_config=phi_config,
        ws_config=active_ws_config,
        target_env=target_env,
        target_group=target_group,
        target_name=target_name,
        target_type=target_type,
    )


# @app.command(short_help="Print your K8s Resources")
# def print(
#     refresh: bool = typer.Option(
#         False,
#         "-r",
#         "--refresh",
#         help="Refresh the workspace config, use this if you've just changed your phi-config.yaml",
#         show_default=True,
#     ),
#     type_filters: List[str] = typer.Option(
#         None, "-k", "--kind", help="Filter the K8s resources by kind"
#     ),
#     name_filters: List[str] = typer.Option(
#         None, "-n", "--name", help="Filter the K8s resources by name"
#     ),
# ):
#     """
#     Print your k8s resources so you know exactly what is being deploying
#
#     \b
#     Examples:
#     * `phi k print`      -> Print resources for the primary workspace
#     * `phi k print data` -> Print resources for the workspace named data
#     """
#
#     from phi import schemas
#     from phiterm.k8s import k8s_operator
#     from phiterm.conf.phi_conf import PhiConf
#
#     config: Optional[PhiConf] = PhiConf.get_saved_conf()
#     if not config:
#         conf_not_available_msg()
#         raise typer.Exit(1)
#
#     primary_ws: Optional[schemas.WorkspaceSchema] = config.primary_ws
#     if primary_ws is None:
#         primary_ws_not_available_msg()
#         raise typer.Exit(1)
#
#     k8s_operator.print_k8s_resources_as_yaml(
#         primary_ws, config, refresh, type_filters, name_filters
#     )
#
#
# @app.command(short_help="Apply your K8s Resources")
# def apply(
#     refresh: bool = typer.Option(
#         False,
#         "-r",
#         "--refresh",
#         help="Refresh the workspace config, use this if you've just changed your phi-config.yaml",
#         show_default=True,
#     ),
#     service_filters: List[str] = typer.Option(
#         None, "-s", "--svc", help="Filter the Services"
#     ),
#     type_filters: List[str] = typer.Option(
#         None, "-k", "--kind", help="Filter the K8s resources by kind"
#     ),
#     name_filters: List[str] = typer.Option(
#         None, "-n", "--name", help="Filter the K8s resources by name"
#     ),
# ):
#     """
#     Apply your k8s resources. You can filter the resources by services, kind or name
#
#     \b
#     Examples:
#     * `phi k apply`      -> Apply resources for the primary workspace
#     """
#
#     from phi import schemas
#     from phiterm.k8s import k8s_operator
#     from phiterm.conf.phi_conf import PhiConf
#
#     config: Optional[PhiConf] = PhiConf.get_saved_conf()
#     if not config:
#         conf_not_available_msg()
#         raise typer.Exit(1)
#
#     primary_ws: Optional[schemas.WorkspaceSchema] = config.primary_ws
#     if primary_ws is None:
#         primary_ws_not_available_msg()
#         raise typer.Exit(1)
#
#     k8s_operator.apply_k8s_resources(
#         primary_ws, config, refresh, service_filters, type_filters, name_filters
#     )
#
#
# @app.command(short_help="Get active K8s Objects")
# def get(
#     service_filters: List[str] = typer.Option(
#         None, "-s", "--svc", help="Filter the Services"
#     ),
#     type_filters: List[str] = typer.Option(
#         None, "-k", "--kind", help="Filter the K8s resources by kind"
#     ),
#     name_filters: List[str] = typer.Option(
#         None, "-n", "--name", help="Filter the K8s resources by name"
#     ),
# ):
#     """
#     Get active k8s resources.
#
#     \b
#     Examples:
#     * `phi k apply`      -> Get active resources for the primary workspace
#     """
#
#     from phi import schemas
#     from phiterm.k8s import k8s_operator
#     from phiterm.conf.phi_conf import PhiConf
#
#     config: Optional[PhiConf] = PhiConf.get_saved_conf()
#     if not config:
#         conf_not_available_msg()
#         raise typer.Exit(1)
#
#     primary_ws: Optional[schemas.WorkspaceSchema] = config.primary_ws
#     if primary_ws is None:
#         primary_ws_not_available_msg()
#         raise typer.Exit(1)
#
#     k8s_operator.print_active_k8s_resources(
#         primary_ws, config, service_filters, type_filters, name_filters
#     )
#
#
# if __name__ == "__main__":
#     app()
