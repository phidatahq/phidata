import uuid
from typing import Optional

from phi.tools import Toolkit
from phi.utils.log import logger


class PhiTools(Toolkit):
    def __init__(self):
        super().__init__(name="phi_tools")

        self.register(self.create_new_app)
        self.register(self.start_user_workspace)
        self.register(self.validate_phi_is_ready)

    def validate_phi_is_ready(self) -> bool:
        """Validates that Phi is ready to run commands.

        :return: True if Phi is ready, False otherwise.
        """
        # Check if docker is running
        return True

    def create_new_app(self, template: str, workspace_name: str) -> str:
        """Creates a new phidata workspace for a given application template.
        Use this function when the user wants to create a new "llm-app", "api-app", "django-app", or "streamlit-app".
        Remember to provide a name for the new workspace.
        You can use the format: "template-name" + name of an interesting person (lowercase, no spaces).

        :param template: (required) The template to use for the new application.
            One of: llm-app, api-app, django-app, streamlit-app
        :param workspace_name: (required) The name of the workspace to create for the new application.
        :return: Status of the function or next steps.
        """
        from phi.workspace.operator import create_workspace, TEMPLATE_TO_NAME_MAP, WorkspaceStarterTemplate

        ws_template: Optional[WorkspaceStarterTemplate] = None
        if template.lower() in WorkspaceStarterTemplate.__members__.values():
            ws_template = WorkspaceStarterTemplate(template)

        if ws_template is None:
            return f"Error: Invalid template: {template}, must be one of: llm-app, api-app, django-app, streamlit-app"

        ws_dir_name: Optional[str] = workspace_name
        if ws_dir_name is None:
            # Get default_ws_name from template
            default_ws_name: Optional[str] = TEMPLATE_TO_NAME_MAP.get(ws_template)
            # Add a 2 digit random suffix to the default_ws_name
            random_suffix = str(uuid.uuid4())[:2]
            default_ws_name = f"{default_ws_name}-{random_suffix}"

            return (
                f"Ask the user for a name for the app directory with the default value: {default_ws_name}."
                f"Ask the user to input YES or NO to use the default value."
            )
            # # Ask user for workspace name if not provided
            # ws_dir_name = Prompt.ask("Please provide a name for the app", default=default_ws_name, console=console)

        logger.info(f"Creating: {template} at {ws_dir_name}")
        try:
            create_successful = create_workspace(name=ws_dir_name, template=ws_template.value)
            if create_successful:
                return (
                    f"Successfully created a {ws_template.value} at {ws_dir_name}. "
                    f"Ask the user if they want to start the app now."
                )
            else:
                return f"Error: Failed to create {template}"
        except Exception as e:
            return f"Error: {e}"

    def start_user_workspace(self, workspace_name: Optional[str] = None) -> str:
        """Starts the workspace for a user. Use this function when the user wants to start a given workspace.
        If the workspace name is not provided, the function will start the active workspace.
        Otherwise, it will start the workspace with the given name.

        :param workspace_name: The name of the workspace to start
        :return: Status of the function or next steps.
        """
        from phi.cli.config import PhiCliConfig
        from phi.infra.type import InfraType
        from phi.workspace.config import WorkspaceConfig
        from phi.workspace.operator import start_workspace

        phi_config: Optional[PhiCliConfig] = PhiCliConfig.from_saved_config()
        if not phi_config:
            return "Error: Phi not initialized. Please run `phi ai` again"

        workspace_config_to_start: Optional[WorkspaceConfig] = None
        active_ws_config: Optional[WorkspaceConfig] = phi_config.get_active_ws_config()

        if workspace_name is None:
            if active_ws_config is None:
                return "Error: No active workspace found. Please create a workspace first."
            workspace_config_to_start = active_ws_config
        else:
            workspace_config_by_name: Optional[WorkspaceConfig] = phi_config.get_ws_config_by_dir_name(workspace_name)
            if workspace_config_by_name is None:
                return f"Error: Could not find a workspace with name: {workspace_name}"
            workspace_config_to_start = workspace_config_by_name

            # Set the active workspace to the workspace to start
            if active_ws_config is not None and active_ws_config.ws_root_path != workspace_config_by_name.ws_root_path:
                phi_config.set_active_ws_dir(workspace_config_by_name.ws_root_path)
                active_ws_config = workspace_config_by_name

        try:
            start_workspace(
                phi_config=phi_config,
                ws_config=workspace_config_to_start,
                target_env="dev",
                target_infra=InfraType.docker,
                auto_confirm=True,
            )
            return f"Successfully started workspace: {workspace_config_to_start.ws_root_path.stem}"
        except Exception as e:
            return f"Error: {e}"
