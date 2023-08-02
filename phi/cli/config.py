from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

from phi.cli.console import print_heading, print_info
from phi.cli.settings import phi_cli_settings
from phi.api.schemas.user import UserSchema
from phi.api.schemas.workspace import WorkspaceSchema, WorkspaceDelete
from phi.utils.log import logger
from phi.utils.pickle import pickle_object_to_file, unpickle_object_from_file
from phi.workspace.config import WorkspaceConfig


class PhiCliConfig:
    """The PhiCliConfig class manages user data for the phi cli"""

    def __init__(self, user_schema: Optional[UserSchema] = None) -> None:
        # Current user, populated after authenticating with the api
        # To add a user, use the user setter
        self._user: Optional[UserSchema] = user_schema

        # Active ws dir - used as the default for `phi` commands
        # To add an active workspace, use the active_ws_dir setter
        self._active_ws_dir: Optional[str] = None

        # Mapping from ws_dir_name to ws_config
        self.ws_config_map: Dict[str, WorkspaceConfig] = OrderedDict()

        # Quick access from ws_root -> ws_config
        self.path_to_ws_config_map: Dict[Path, WorkspaceConfig] = OrderedDict()

        # Save the config to disk once initialized
        self.save_config()

    ######################################################
    ## User functions
    ######################################################

    @property
    def user(self) -> Optional[UserSchema]:
        return self._user

    async def set_user(self, user: Optional[UserSchema]) -> None:
        """Sets the user"""
        if user is not None:
            if self._user is not None:
                if self._user.email == "anon":
                    from phi.api.workspace import claim_anonymous_workspaces

                    logger.debug("Current user is anon -- claiming workspaces")
                    # If the current user is anon, claim all workspaces
                    workspaces_claimed = await claim_anonymous_workspaces(
                        anon_user=self._user,
                        authenticated_user=user,
                        workspaces=[ws.ws_schema for ws in self.available_ws if ws.ws_schema is not None],
                    )
                    if not workspaces_claimed:
                        logger.warning("Could not claim existing workspaces, please authenticate again")
                self._user = user
            else:
                logger.debug("Setting user")
                self._user = user
            self.save_config()

    ######################################################
    ## Workspace functions
    ######################################################

    @property
    def active_ws_dir(self) -> Optional[str]:
        return self._active_ws_dir

    @active_ws_dir.setter
    def active_ws_dir(self, ws_dir_name: Optional[str]) -> None:
        if ws_dir_name is not None:
            self._active_ws_dir = ws_dir_name
            self.save_config()

    @property
    def available_ws(self) -> List[WorkspaceConfig]:
        return list(self.ws_config_map.values())

    def _add_or_update_ws_config(
        self,
        ws_dir_name: str,
        ws_root_path: Optional[Path] = None,
        ws_schema: Optional[WorkspaceSchema] = None,
    ) -> Optional[WorkspaceConfig]:
        """The main function to create, update or refresh the WorkspaceConfig.

        Notes:
        1. ws_name is the only required argument.
        2. This function does not call self.save_config().
            Remember to save_config() after calling this function.
        """

        # Validate ws_name is not None
        if ws_dir_name is None or not isinstance(ws_dir_name, str):
            return None

        ######################################################
        # Create new ws_config for ws_name if one does not exist
        ######################################################
        if ws_dir_name not in self.ws_config_map:
            logger.debug(f"Creating workspace for directory: {ws_dir_name}")
            new_workspace_config = WorkspaceConfig(
                ws_dir_name=ws_dir_name,
                ws_schema=ws_schema,
                ws_root_path=ws_root_path,
            )
            self.ws_config_map[ws_dir_name] = new_workspace_config
            if ws_root_path is not None:
                self.path_to_ws_config_map[ws_root_path] = new_workspace_config
                logger.debug(f"Workspace dir: {ws_root_path}")
            logger.debug(f"Workspace created for directory: {ws_dir_name}")

            # Return the new_workspace_config
            return new_workspace_config

        ######################################################
        # Update ws_config
        ######################################################
        logger.debug(f"Updating workspace at directory: {ws_dir_name}")
        # By this point there should be a WorkspaceConfig object for this ws_name
        existing_ws_config: Optional[WorkspaceConfig] = self.ws_config_map.get(ws_dir_name, None)
        if existing_ws_config is None:
            logger.error("Something went wrong. Please try again.")
            return None

        # Make a new WorkspaceConfig using new fields where provided and fields from the existing_ws_config where not
        updated_ws_config: WorkspaceConfig = WorkspaceConfig(
            ws_dir_name=(ws_dir_name or existing_ws_config.ws_dir_name),
            ws_schema=(ws_schema or existing_ws_config.ws_schema),
            ws_root_path=(ws_root_path or existing_ws_config.ws_root_path),
            create_ts=existing_ws_config.create_ts,
        )

        # Point the ws_config in ws_config_map and path_to_ws_config_map to updated_ws_config
        # 1. Pop the existing object from the self.ws_config_map
        if ws_dir_name in self.ws_config_map:
            self.ws_config_map.pop(ws_dir_name)
            logger.debug(f"Removed {ws_dir_name} from ws_config_map")
        self.ws_config_map[ws_dir_name] = updated_ws_config

        # 2. Pop the existing object from the self.path_to_ws_config_map
        if updated_ws_config.ws_root_path is not None:
            if updated_ws_config.ws_root_path in self.path_to_ws_config_map:
                self.path_to_ws_config_map.pop(updated_ws_config.ws_root_path)
                logger.debug(f"Removed {updated_ws_config.ws_root_path} from path_to_ws_config_map")
            self.path_to_ws_config_map[updated_ws_config.ws_root_path] = self.ws_config_map[ws_dir_name]
        logger.debug(f"Workspace updated: {ws_dir_name}")

        # Return the updated_ws_config
        return updated_ws_config

    ######################################################
    # END
    ######################################################

    def add_new_ws_to_config(
        self,
        ws_dir_name: str,
        ws_root_path: Path,
    ) -> Optional[WorkspaceConfig]:
        """Adds a newly created workspace to the PhiCliConfig"""
        ws_config = self._add_or_update_ws_config(
            ws_dir_name=ws_dir_name,
            ws_root_path=ws_root_path,
        )
        self.save_config()
        return ws_config

    def update_ws_config(
        self,
        ws_dir_name: str,
        ws_schema: Optional[WorkspaceSchema] = None,
        ws_root_path: Optional[Path] = None,
        set_as_active: bool = False,
    ) -> Optional[WorkspaceConfig]:
        """Updates WorkspaceConfig and returns True if successful"""
        ws_config = self._add_or_update_ws_config(
            ws_dir_name=ws_dir_name,
            ws_schema=ws_schema,
            ws_root_path=ws_root_path,
        )
        if set_as_active:
            self.active_ws_dir = ws_dir_name
        self.save_config()
        return ws_config

    async def delete_ws(self, ws_dir_name: str) -> None:
        """Handles Deleting a workspace from the PhiCliConfig and api"""

        print_heading(f"Deleting record for directory: {ws_dir_name}")
        print_info("-*- Note: this does not delete any files on disk, please delete them manually")

        ws_config: Optional[WorkspaceConfig] = self.ws_config_map.pop(ws_dir_name, None)
        if ws_config is None:
            logger.warning(f"No record of workspace at {ws_dir_name}")
            return

        if ws_config.ws_root_path is not None:
            self.path_to_ws_config_map.pop(ws_config.ws_root_path, None)

        # Check if we're deleting the active workspace, if yes, unset the active ws
        if (
            self._active_ws_dir is not None
            and ws_config.ws_dir_name is not None
            and self._active_ws_dir == ws_config.ws_dir_name
        ):
            print_info(f"Removing {ws_config.ws_dir_name} as the active workspace")
            self._active_ws_dir = None

        if self.user is not None and ws_config.ws_schema is not None:
            print_info(f"Deleting workspace {ws_config.ws_dir_name} from the server")

            from phi.api.workspace import delete_workspace_for_user

            await delete_workspace_for_user(
                user=self.user,
                workspace=WorkspaceDelete(
                    id_workspace=ws_config.ws_schema.id_workspace, ws_name=ws_config.ws_schema.ws_name
                ),
            )

        self.save_config()

    ######################################################
    ## Get Workspace Data
    ######################################################

    def get_ws_config_by_dir_name(self, ws_dir_name: str) -> Optional[WorkspaceConfig]:
        return self.ws_config_map[ws_dir_name] if ws_dir_name in self.ws_config_map else None

    def get_ws_config_by_path(self, ws_root_path: Path) -> Optional[WorkspaceConfig]:
        return self.path_to_ws_config_map[ws_root_path] if ws_root_path in self.path_to_ws_config_map else None

    def get_ws_dir_name_by_path(self, ws_root_path: Path) -> Optional[str]:
        if ws_root_path in self.path_to_ws_config_map:
            return self.path_to_ws_config_map[ws_root_path].ws_dir_name
        return None

    def get_ws_schema_by_dir_name(self, ws_dir_name: str) -> Optional[WorkspaceSchema]:
        if ws_dir_name in self.ws_config_map:
            return self.ws_config_map[ws_dir_name].ws_schema
        return None

    def get_ws_schema_by_path(self, ws_root_path: Path) -> Optional[WorkspaceSchema]:
        if ws_root_path in self.path_to_ws_config_map:
            return self.path_to_ws_config_map[ws_root_path].ws_schema
        return None

    def get_ws_root_path_by_dir_name(self, ws_dir_name: str) -> Optional[Path]:
        if ws_dir_name in self.ws_config_map:
            return self.ws_config_map[ws_dir_name].ws_root_path
        return None

    def get_active_ws_config(self, load: bool = True) -> Optional[WorkspaceConfig]:
        if self.active_ws_dir is not None and self.active_ws_dir in self.ws_config_map:
            active_ws_config: WorkspaceConfig = self.ws_config_map[self.active_ws_dir]
            if load:
                active_ws_config.load()
            return active_ws_config
        return None

    ######################################################
    ## Save PhiCliConfig
    ######################################################

    def save_config(self):
        logger.debug(f"Saving config to {str(phi_cli_settings.config_file_path)}")
        pickle_object_to_file(self, phi_cli_settings.config_file_path)

    @classmethod
    def from_saved_config(cls):
        logger.debug(f"Reading PhiCliConfig from {phi_cli_settings.config_file_path}")
        try:
            return unpickle_object_from_file(file_path=phi_cli_settings.config_file_path, verify_class=cls)
        except Exception as e:
            logger.warning(e)
            logger.warning("If error persists, setup the workspace again using `phi ws setup`")

    ######################################################
    ## Print PhiCliConfig
    ######################################################

    def print_to_cli(self, show_all: bool = False):
        if self.user:
            print_heading(f"User: {self.user.email}\n")
        if self.active_ws_dir:
            print_heading(f"Active workspace directory: {self.active_ws_dir}\n")
        else:
            print_info("* No active workspace, run `phi ws create` or `phi ws set`")

        if show_all and len(self.ws_config_map) > 0:
            print_heading("Available workspaces:\n")
            c = 1
            for k, v in self.ws_config_map.items():
                print_info(f"  {c}. Directory: {v.ws_dir_name}")
                print_info(f"     Path: {v.ws_root_path}")
                if v.docker_resource_groups:
                    print_info("     Docker Envs: {}".format([drg.env for drg in v.docker_resource_groups]))
                if v.k8s_resource_groups:
                    print_info("     K8s Envs: {}".format([krg.env for krg in v.k8s_resource_groups]))
                if v.aws_resource_groups:
                    print_info("     AWS Envs: {}".format([awsg.env for awsg in v.aws_resource_groups]))
                if v.ws_schema and v.ws_schema.ws_name:
                    print_info(f"     Name: {v.ws_schema.ws_name}")
                c += 1
