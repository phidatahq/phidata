from typing import Optional

from typer import launch as typer_launch

from phi.cli.settings import phi_cli_settings, PHI_CLI_DIR
from phi.cli.config import PhiCliConfig
from phi.cli.console import print_info, print_heading
from phi.utils.log import logger


def delete_phidata_conf() -> None:
    from phi.utils.filesystem import delete_from_fs

    logger.debug("Removing existing Phidata configuration")
    delete_from_fs(PHI_CLI_DIR)


def authenticate_user() -> None:
    """Authenticate the user using credentials from phidata.com
    Steps:
    1. Authenticate the user by opening the phidata sign-in url
        and the web-app will post an auth token to a mini http server
        running on the auth_server_port.
    2. Using the auth_token, authenticate the CLI with api and
        save the auth_token. This step is handled by authenticate_and_get_user()
    3. After the user is authenticated update the PhiCliConfig.
    """
    from phi.api.user import authenticate_and_get_user
    from phi.api.schemas.user import UserSchema
    from phi.cli.auth_server import (
        get_port_for_auth_server,
        get_auth_token_from_web_flow,
    )

    print_heading("Authenticating with phidata.com ...")

    auth_server_port = get_port_for_auth_server()
    redirect_uri = "http%3A%2F%2Flocalhost%3A{}%2F".format(auth_server_port)
    auth_url = "{}?source=cli&action=signin&redirecturi={}".format(phi_cli_settings.signin_url, redirect_uri)
    print_info("\nYour browser will be opened to visit:\n{}".format(auth_url))
    typer_launch(auth_url)
    print_info("\nWaiting for a response from browser...\n")

    tmp_auth_token = get_auth_token_from_web_flow(auth_server_port)
    if tmp_auth_token is None:
        logger.error("Could not authenticate, please try again")
        return

    phi_config: Optional[PhiCliConfig] = PhiCliConfig.from_saved_config()
    existing_user: Optional[UserSchema] = phi_config.user if phi_config is not None else None
    try:
        user: Optional[UserSchema] = authenticate_and_get_user(
            tmp_auth_token=tmp_auth_token, existing_user=existing_user
        )
    except Exception as e:
        logger.exception(e)
        logger.error("Could not authenticate, please try again")
        return

    if user is None:
        logger.error("Could not authenticate, please try again")
        return

    if phi_config is None:
        phi_config = PhiCliConfig(user)
    else:
        phi_config.user = user

    print_info("Welcome {}".format(user.email))


def initialize_phi(reset: bool = False, login: bool = False) -> bool:
    """Initialize phi on the users machine.

    Steps:
    1. Check if PHI_CLI_DIR exists, if not, create it. If reset == True, recreate PHI_CLI_DIR.
    2. Authenticates the user if login == True.
    3. If PhiCliConfig exists and auth is valid, return True.
    """
    from phi.utils.filesystem import delete_from_fs
    from phi.api.user import create_anon_user

    print_heading("Welcome to phidata!")
    if reset:
        delete_phidata_conf()

    logger.debug("Initializing phidata")

    # Check if ~/.phi exists, if it is not a dir - delete it and create the dir
    if PHI_CLI_DIR.exists():
        logger.debug(f"{PHI_CLI_DIR} exists")
        if not PHI_CLI_DIR.is_dir():
            try:
                delete_from_fs(PHI_CLI_DIR)
            except Exception as e:
                logger.exception(e)
                raise Exception(f"Something went wrong, please delete {PHI_CLI_DIR} and run again")
            PHI_CLI_DIR.mkdir(parents=True, exist_ok=True)
    else:
        PHI_CLI_DIR.mkdir(parents=True)
        logger.debug(f"Created {PHI_CLI_DIR}")

    # Confirm PHI_CLI_DIR exists otherwise we should return
    if PHI_CLI_DIR.exists():
        logger.debug(f"Phidata config location: {PHI_CLI_DIR}")
    else:
        raise Exception("Something went wrong, please try again")

    phi_config: Optional[PhiCliConfig] = PhiCliConfig.from_saved_config()
    if phi_config is None:
        logger.debug("Creating new PhiCliConfig")
        phi_config = PhiCliConfig()

    # Authenticate user
    if login:
        authenticate_user()
    else:
        anon_user = create_anon_user()
        if anon_user is not None and phi_config is not None:
            phi_config.user = anon_user

    if phi_config is not None:
        logger.debug("Phidata initialized")
        return True
    else:
        logger.error("Something went wrong, please try again")
        return False


def sign_in_using_cli() -> None:
    from getpass import getpass
    from phi.api.user import sign_in_user
    from phi.api.schemas.user import UserSchema, EmailPasswordAuthSchema

    print_heading("Log in")
    email_raw = input("email: ")
    pass_raw = getpass()

    if email_raw is None or pass_raw is None:
        logger.error("Incorrect email or password")

    try:
        user: Optional[UserSchema] = sign_in_user(EmailPasswordAuthSchema(email=email_raw, password=pass_raw))
    except Exception as e:
        logger.exception(e)
        logger.error("Could not authenticate, please try again")
        return

    if user is None:
        logger.error("Could not get user, please try again")
        return

    phi_config: Optional[PhiCliConfig] = PhiCliConfig.from_saved_config()
    if phi_config is None:
        phi_config = PhiCliConfig(user)
    else:
        phi_config.user = user

    print_info("Welcome {}".format(user.email))


# def start_resources(
#     resources_file_path: Path,
#     target_env: Optional[str] = None,
#     target_config: Optional[Any] = None,
#     target_name: Optional[str] = None,
#     target_type: Optional[str] = None,
#     target_group: Optional[str] = None,
#     dry_run: Optional[bool] = False,
#     auto_confirm: Optional[bool] = False,
# ) -> None:
#     print_heading(f"Starting resources in: {resources_file_path}")
#     logger.debug(f"\ttarget_env   : {target_env}")
#     logger.debug(f"\ttarget_config: {target_config}")
#     logger.debug(f"\ttarget_name  : {target_name}")
#     logger.debug(f"\ttarget_type  : {target_type}")
#     logger.debug(f"\ttarget_group : {target_group}")
#     logger.debug(f"\tdry_run      : {dry_run}")
#     logger.debug(f"\tauto_confirm : {auto_confirm}")
#
#     from phidata.aws.config import AwsConfig
#     from phidata.docker.config import DockerConfig
#     from phidata.infra.config import InfraConfig
#     from phidata.k8s.config import K8sConfig
#     from phidata.workspace import WorkspaceConfig
#
#     from phi.utils.prep_infra_config import filter_and_prep_configs
#
#     if not resources_file_path.exists():
#         logger.error(f"File does not exist: {resources_file_path}")
#         return
#
#     ws_config: WorkspaceConfig = WorkspaceConfig.from_file(resources_file_path)
#     # Set the local environment variables before processing configs
#     ws_config.set_local_env()
#
#     configs_to_deploy: List[InfraConfig] = filter_and_prep_configs(
#         ws_config=ws_config,
#         target_env=target_env,
#         target_config=target_config,
#         order="create",
#     )
#
#     num_configs_to_deploy = len(configs_to_deploy)
#     num_configs_deployed = 0
#     for config in configs_to_deploy:
#         logger.debug(f"Deploying {config.__class__.__name__}")
#         if isinstance(config, DockerConfig):
#             from phi.docker.docker_operator import deploy_docker_config
#
#             deploy_docker_config(
#                 config=config,
#                 name_filter=target_name,
#                 type_filter=target_type,
#                 app_filter=target_group,
#                 dry_run=dry_run,
#                 auto_confirm=auto_confirm,
#             )
#             num_configs_deployed += 1
#         if isinstance(config, K8sConfig):
#             from phi.k8s.k8s_operator import deploy_k8s_config
#
#             deploy_k8s_config(
#                 config=config,
#                 name_filter=target_name,
#                 type_filter=target_type,
#                 app_filter=target_group,
#                 dry_run=dry_run,
#                 auto_confirm=auto_confirm,
#             )
#             num_configs_deployed += 1
#         if isinstance(config, AwsConfig):
#             from phi.aws.aws_operator import deploy_aws_config
#
#             deploy_aws_config(
#                 config=config,
#                 name_filter=target_name,
#                 type_filter=target_type,
#                 app_filter=target_group,
#                 dry_run=dry_run,
#                 auto_confirm=auto_confirm,
#             )
#             num_configs_deployed += 1
#         # white space between runs
#         print_info("")
#
#     print_info(f"# Configs deployed: {num_configs_deployed}/{num_configs_to_deploy}\n")
#     if num_configs_to_deploy == num_configs_deployed:
#         if not dry_run:
#             print_subheading("Workspace deploy success")
#     else:
#         logger.error("Workspace deploy failed")
#
#
# def stop_resources(
#     resources_file_path: Path,
#     target_env: Optional[str] = None,
#     target_config: Optional[Any] = None,
#     target_name: Optional[str] = None,
#     target_type: Optional[str] = None,
#     target_group: Optional[str] = None,
#     dry_run: Optional[bool] = False,
#     auto_confirm: Optional[bool] = False,
# ) -> None:
#     print_heading(f"Stopping resources in: {resources_file_path}")
#     logger.debug(f"\ttarget_env   : {target_env}")
#     logger.debug(f"\ttarget_config: {target_config}")
#     logger.debug(f"\ttarget_name  : {target_name}")
#     logger.debug(f"\ttarget_type  : {target_type}")
#     logger.debug(f"\ttarget_group : {target_group}")
#     logger.debug(f"\tdry_run      : {dry_run}")
#     logger.debug(f"\tauto_confirm : {auto_confirm}")
#
#     from phidata.aws.config import AwsConfig
#     from phidata.docker.config import DockerConfig
#     from phidata.infra.config import InfraConfig
#     from phidata.k8s.config import K8sConfig
#     from phidata.workspace import WorkspaceConfig
#
#     from phi.utils.prep_infra_config import filter_and_prep_configs
#
#     if not resources_file_path.exists():
#         logger.error(f"File does not exist: {resources_file_path}")
#         return
#
#     ws_config: WorkspaceConfig = WorkspaceConfig.from_file(resources_file_path)
#     # Set the local environment variables before processing configs
#     ws_config.set_local_env()
#
#     configs_to_shutdown: List[InfraConfig] = filter_and_prep_configs(
#         ws_config=ws_config,
#         target_env=target_env,
#         target_config=target_config,
#         order="create",
#     )
#
#     num_configs_to_shutdown = len(configs_to_shutdown)
#     num_configs_shutdown = 0
#     for config in configs_to_shutdown:
#         logger.debug(f"Deploying {config.__class__.__name__}")
#         if isinstance(config, DockerConfig):
#             from phi.docker.docker_operator import shutdown_docker_config
#
#             shutdown_docker_config(
#                 config=config,
#                 name_filter=target_name,
#                 type_filter=target_type,
#                 app_filter=target_group,
#                 dry_run=dry_run,
#                 auto_confirm=auto_confirm,
#             )
#             num_configs_shutdown += 1
#         if isinstance(config, K8sConfig):
#             from phi.k8s.k8s_operator import shutdown_k8s_config
#
#             shutdown_k8s_config(
#                 config=config,
#                 name_filter=target_name,
#                 type_filter=target_type,
#                 app_filter=target_group,
#                 dry_run=dry_run,
#                 auto_confirm=auto_confirm,
#             )
#             num_configs_shutdown += 1
#         if isinstance(config, AwsConfig):
#             from phi.aws.aws_operator import shutdown_aws_config
#
#             shutdown_aws_config(
#                 config=config,
#                 name_filter=target_name,
#                 type_filter=target_type,
#                 app_filter=target_group,
#                 dry_run=dry_run,
#                 auto_confirm=auto_confirm,
#             )
#             num_configs_shutdown += 1
#         # white space between runs
#         print_info("")
#
#     print_info(f"# Configs shutdown: {num_configs_shutdown}/{num_configs_to_shutdown}\n")
#     if num_configs_to_shutdown == num_configs_shutdown:
#         if not dry_run:
#             print_subheading("Workspace shutdown success")
#     else:
#         logger.error("Workspace shutdown failed")
#
#
# def patch_resources(
#     resources_file_path: Path,
#     target_env: Optional[str] = None,
#     target_config: Optional[Any] = None,
#     target_name: Optional[str] = None,
#     target_type: Optional[str] = None,
#     target_group: Optional[str] = None,
#     dry_run: Optional[bool] = False,
#     auto_confirm: Optional[bool] = False,
# ) -> None:
#     print_heading(f"Updating resources in: {resources_file_path}")
#     logger.debug(f"\ttarget_env   : {target_env}")
#     logger.debug(f"\ttarget_config: {target_config}")
#     logger.debug(f"\ttarget_name  : {target_name}")
#     logger.debug(f"\ttarget_type  : {target_type}")
#     logger.debug(f"\ttarget_group : {target_group}")
#     logger.debug(f"\tdry_run      : {dry_run}")
#     logger.debug(f"\tauto_confirm : {auto_confirm}")
#
#     from phidata.aws.config import AwsConfig
#     from phidata.docker.config import DockerConfig
#     from phidata.infra.config import InfraConfig
#     from phidata.k8s.config import K8sConfig
#     from phidata.workspace import WorkspaceConfig
#
#     from phi.utils.prep_infra_config import filter_and_prep_configs
#
#     if not resources_file_path.exists():
#         logger.error(f"File does not exist: {resources_file_path}")
#         return
#
#     ws_config: WorkspaceConfig = WorkspaceConfig.from_file(resources_file_path)
#     # Set the local environment variables before processing configs
#     ws_config.set_local_env()
#
#     configs_to_patch: List[InfraConfig] = filter_and_prep_configs(
#         ws_config=ws_config,
#         target_env=target_env,
#         target_config=target_config,
#         order="create",
#     )
#
#     num_configs_to_patch = len(configs_to_patch)
#     num_configs_patched = 0
#     for config in configs_to_patch:
#         logger.debug(f"Deploying {config.__class__.__name__}")
#         if isinstance(config, DockerConfig):
#             from phi.docker.docker_operator import patch_docker_config
#
#             patch_docker_config(
#                 config=config,
#                 name_filter=target_name,
#                 type_filter=target_type,
#                 app_filter=target_group,
#                 dry_run=dry_run,
#                 auto_confirm=auto_confirm,
#             )
#             num_configs_patched += 1
#         if isinstance(config, K8sConfig):
#             from phi.k8s.k8s_operator import patch_k8s_config
#
#             patch_k8s_config(
#                 config=config,
#                 name_filter=target_name,
#                 type_filter=target_type,
#                 app_filter=target_group,
#                 dry_run=dry_run,
#                 auto_confirm=auto_confirm,
#             )
#             num_configs_patched += 1
#         if isinstance(config, AwsConfig):
#             from phi.aws.aws_operator import patch_aws_config
#
#             patch_aws_config(
#                 config=config,
#                 name_filter=target_name,
#                 type_filter=target_type,
#                 app_filter=target_group,
#                 dry_run=dry_run,
#                 auto_confirm=auto_confirm,
#             )
#             num_configs_patched += 1
#         # white space between runs
#         print_info("")
#
#     print_info(f"# Configs patched: {num_configs_patched}/{num_configs_to_patch}\n")
#     if num_configs_to_patch == num_configs_patched:
#         if not dry_run:
#             print_subheading("Workspace patch success")
#     else:
#         logger.error("Workspace patch failed")
