from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

from phi.cli.console import print_heading, print_info
from phi.cli.settings import phi_cli_settings
from phi.api.schemas.user import UserSchema
from phi.api.schemas.workspace import WorkspaceSchema
from phi.utils.log import logger
from phi.utils.pickle import pickle_object_to_file, unpickle_object_from_file
from phi.workspace.config import WorkspaceConfig


class PhiCliConfig:
    """The PhiCliConfig class manages user data for the phi cli"""

    def __init__(self, user_schema: Optional[UserSchema] = None) -> None:
        # Current user, populated after authenticating with the api
        # To add a user, use the user setter
        self._user: Optional[UserSchema] = user_schema

        # Active ws - used as the default for `phi` commands
        # To add an active workspace, use the active_ws_name setter
        self._active_ws_name: Optional[str] = None

        # Mapping from ws_name to ws_config
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

    @user.setter
    def user(self, user: Optional[UserSchema]) -> None:
        """Sets the user"""
        if user is not None:
            self._user = user
            self.save_config()

    ######################################################
    ## Workspace functions
    ######################################################

    @property
    def active_ws_name(self) -> Optional[str]:
        return self._active_ws_name

    @active_ws_name.setter
    def active_ws_name(self, ws_name: Optional[str]) -> None:
        if ws_name is not None:
            self._active_ws_name = ws_name
            self.save_config()

    @property
    def available_ws(self) -> List[WorkspaceSchema]:
        available_ws = []
        if self.ws_config_map:
            for ws_config in self.ws_config_map.values():
                if ws_config.ws_schema is not None:
                    available_ws.append(ws_config.ws_schema)
        return available_ws

    @available_ws.setter
    def available_ws(self, avl_ws: Optional[List[WorkspaceSchema]]) -> None:
        if avl_ws:
            for ws_schema in avl_ws:
                if ws_schema.ws_name is not None:
                    self._add_or_update_ws_config(ws_name=ws_schema.ws_name, ws_schema=ws_schema)
            self.save_config()

    def _add_or_update_ws_config(
        self,
        ws_name: str,
        ws_schema: Optional[WorkspaceSchema] = None,
        ws_root_path: Optional[Path] = None,
    ) -> None:
        """The main function to create, update or refresh the WorkspaceConfig.

        Notes:
        1. ws_name is the only required argument.
        2. This function does not call self.save_config().
            Remember to save_config() after calling this function.
        """

        # Validate ws_name is not None
        if ws_name is None or not isinstance(ws_name, str):
            return

        ######################################################
        # Create new ws_config for ws_name if one does not exist
        ######################################################
        if ws_name not in self.ws_config_map:
            logger.debug(f"Creating workspace: {ws_name}")
            new_workspace_config = WorkspaceConfig(
                ws_name=ws_name,
                ws_schema=ws_schema,
                ws_root_path=ws_root_path,
            )
            # Load the new workspace
            new_workspace_config.load()
            self.ws_config_map[ws_name] = new_workspace_config
            if ws_root_path is not None:
                self.path_to_ws_config_map[ws_root_path] = new_workspace_config
                logger.debug(f"Workspace dir: {ws_root_path}")
            logger.debug(f"Workspace created: {ws_name}")
            return

        ######################################################
        # Update ws_config
        ######################################################
        logger.debug(f"Updating workspace: {ws_name}")
        # By this point there should be a WorkspaceConfig object for this ws_name
        existing_ws_config: Optional[WorkspaceConfig] = self.ws_config_map.get(ws_name, None)
        if existing_ws_config is None:
            logger.error("Something went wrong. Please try again.")
            return

        # Make a new WorkspaceConfig using new fields or fields from the existing_ws_config
        updated_ws_config: WorkspaceConfig = WorkspaceConfig(
            ws_name=(ws_name or existing_ws_config.ws_name),
            ws_schema=(ws_schema or existing_ws_config.ws_schema),
            ws_root_path=(ws_root_path or existing_ws_config.ws_root_path),
            create_ts=existing_ws_config.create_ts,
        )
        # Load the updated workspace
        updated_ws_config.load()

        # Point the ws_config in ws_config_map and path_to_ws_config_map to updated_ws_config
        # 1. Pop the existing object from the self.ws_config_map
        if ws_name in self.ws_config_map:
            self.ws_config_map.pop(ws_name)
            logger.debug(f"Removed {ws_name} from ws_config_map")
        self.ws_config_map[ws_name] = updated_ws_config

        # 2. Pop the existing object from the self.path_to_ws_config_map
        if updated_ws_config.ws_root_path is not None:
            if updated_ws_config.ws_root_path in self.path_to_ws_config_map:
                self.path_to_ws_config_map.pop(updated_ws_config.ws_root_path)
                logger.debug(f"Removed {updated_ws_config.ws_root_path} from path_to_ws_config_map")
            self.path_to_ws_config_map[updated_ws_config.ws_root_path] = self.ws_config_map[ws_name]
        logger.debug(f"Workspace updated: {ws_name}")

    ######################################################
    # END
    ######################################################

    def add_new_ws_to_config(
        self,
        ws_name: str,
        ws_root_path: Path,
    ) -> None:
        """Adds a newly created workspace to the PhiCliConfig"""
        self._add_or_update_ws_config(
            ws_name=ws_name,
            ws_root_path=ws_root_path,
        )
        self.save_config()

    def update_ws_config(
        self,
        ws_name: str,
        ws_schema: Optional[WorkspaceSchema] = None,
        ws_root_path: Optional[Path] = None,
        set_as_active: bool = False,
    ) -> None:
        """Updates WorkspaceConfig and returns True if successful"""
        self._add_or_update_ws_config(
            ws_name=ws_name,
            ws_schema=ws_schema,
            ws_root_path=ws_root_path,
        )
        if set_as_active:
            self.active_ws_name = ws_name
        self.save_config()

    async def delete_ws(self, ws_name: str) -> None:
        """Handles Deleting a workspace from the PhiCliConfig and api"""

        print_heading(f"Deleting record for: {ws_name}")
        print_info("-*- Note: this does not delete any files on disk, please delete them manually")

        ws_config: Optional[WorkspaceConfig] = self.ws_config_map.pop(ws_name, None)
        if ws_config is None:
            logger.warning(f"No record of workspace {ws_name}")
            return

        if ws_config.ws_root_path is not None:
            self.path_to_ws_config_map.pop(ws_config.ws_root_path, None)

        # Check if we're deleting the active workspace, if yes, unset the active ws
        if (
            self._active_ws_name is not None
            and ws_config.ws_name is not None
            and self._active_ws_name == ws_config.ws_name
        ):
            print_info(f"Removing {ws_config.ws_name} as the active workspace")
            self._active_ws_name = None

        if self.user is not None and ws_config.ws_schema is not None:
            print_info(f"Deleting workspace {ws_config.ws_name} from the server")

            from phi.api.workspace import delete_workspace_for_user

            await delete_workspace_for_user(user=self.user, workspace=ws_config.ws_schema)

        self.save_config()

    ######################################################
    ## Get Workspace Data
    ######################################################

    def get_ws_config_by_name(self, ws_name: str) -> Optional[WorkspaceConfig]:
        return self.ws_config_map[ws_name] if ws_name in self.ws_config_map else None

    def get_ws_config_by_path(self, ws_root_path: Path) -> Optional[WorkspaceConfig]:
        return self.path_to_ws_config_map[ws_root_path] if ws_root_path in self.path_to_ws_config_map else None

    def get_ws_name_by_path(self, ws_root_path: Path) -> Optional[str]:
        if ws_root_path in self.path_to_ws_config_map:
            return self.path_to_ws_config_map[ws_root_path].ws_name
        return None

    def get_ws_schema_by_name(self, ws_name: str) -> Optional[WorkspaceSchema]:
        if ws_name in self.ws_config_map:
            return self.ws_config_map[ws_name].ws_schema
        return None

    def get_ws_schema_by_path(self, ws_root_path: Path) -> Optional[WorkspaceSchema]:
        if ws_root_path in self.path_to_ws_config_map:
            return self.path_to_ws_config_map[ws_root_path].ws_schema
        return None

    def get_ws_root_path_by_name(self, ws_name: str) -> Optional[Path]:
        if ws_name in self.ws_config_map:
            return self.ws_config_map[ws_name].ws_root_path
        return None

    def get_active_ws_config(self, refresh: bool = False) -> Optional[WorkspaceConfig]:
        if self.active_ws_name is not None and self.active_ws_name in self.ws_config_map:
            if refresh:
                self.refresh_ws_config(self.active_ws_name)
            return self.ws_config_map[self.active_ws_name]
        return None

    def refresh_ws_config(self, ws_name: str) -> None:
        """Refresh the workspace config for a given workspace name"""
        self._add_or_update_ws_config(ws_name=ws_name)
        logger.debug(f"++**++ Config refreshed: {ws_name}")
        self.save_config()

    ######################################################
    ## Sync Workspace Data from api
    ######################################################

    async def sync_workspaces_from_api(self) -> None:
        from phi.api.workspace import get_primary_workspace, get_available_workspaces

        if self.user is None:
            logger.error("User not available for workspace sync")
            return

        # Call api to get the available workspaces
        available_workspaces: Optional[List[WorkspaceSchema]] = await get_available_workspaces(self.user)
        if available_workspaces is not None:
            logger.debug(f"Received {len(available_workspaces)} available workspaces")
            self.available_ws = available_workspaces

        # Call api to get the primary_ws
        primary_ws: Optional[WorkspaceSchema] = await get_primary_workspace(self.user)
        if primary_ws is None:
            logger.debug("No primary workspace available")
        else:
            logger.debug(f"Received primary ws: {primary_ws.model_dump_json(indent=2)}")
            self.active_ws_name = primary_ws.ws_name

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
        if self.active_ws_name:
            print_heading(f"Active workspace: {self.active_ws_name}\n")
        else:
            print_info("* No active workspace, run `phi ws create` or `phi ws set`")

        if show_all and len(self.ws_config_map) > 0:
            print_heading("Available workspaces:\n")
            c = 1
            for k, v in self.ws_config_map.items():
                print_info(f"  {c}. Name: {v.ws_name}")
                print_info(f"     Dir: {v.ws_root_path}")
                if v.ws_schema:
                    logger.debug(f"     Schema: {v.ws_schema.model_dump_json(exclude_none=True, indent=2)}")
                print_info("  -*-\n")
                c += 1
