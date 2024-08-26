from pathlib import Path
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, ConfigDict
from sklearn.ensemble import RandomForestClassifier
import joblib
import numpy as np

from phi.workspace.settings import WorkspaceSettings


class PhiBase(BaseModel):
    name: Optional[str] = None
    group: Optional[str] = None
    version: Optional[str] = None
    env: Optional[str] = None
    enabled: bool = True

    #  -*- Resource Control
    skip_create: bool = False
    skip_read: bool = False
    skip_update: bool = False
    skip_delete: bool = False
    recreate_on_update: bool = False
    use_cache: bool = True
    force: Optional[bool] = None

    # -*- Debug Mode
    debug_mode: bool = False

    # -*- Resource Environment
    env_vars: Optional[Dict[str, Any]] = None
    env_file: Optional[Path] = None
    secrets_file: Optional[Path] = None
    aws_secrets: Optional[Any] = None

    # -*- Waiter Control
    wait_for_create: bool = True
    wait_for_update: bool = True
    wait_for_delete: bool = True
    waiter_delay: int = 30
    waiter_max_attempts: int = 50

    #  -*- Save to output directory
    save_output: bool = False
    input_dir: Optional[str] = None
    output_dir: Optional[str] = None

    #  -*- Dependencies
    depends_on: Optional[List[Any]] = None

    # -*- Workspace Settings
    workspace_settings: Optional[WorkspaceSettings] = None

    # -*- Cached Data
    cached_env_file_data: Optional[Dict[str, Any]] = None
    cached_secret_file_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    # Load pre-trained model for AI-driven suggestions
    ai_model: Optional[RandomForestClassifier] = joblib.load('ai_model.pkl')

    def get_group_name(self) -> Optional[str]:
        return self.group or self.name

    @property
    def workspace_root(self) -> Optional[Path]:
        return self.workspace_settings.ws_root if self.workspace_settings is not None else None

    @property
    def workspace_name(self) -> Optional[str]:
        return self.workspace_settings.ws_name if self.workspace_settings is not None else None

    @property
    def workspace_dir(self) -> Optional[Path]:
        if self.workspace_root is not None:
            workspace_dir = self.workspace_settings.workspace_dir if self.workspace_settings is not None else None
            if workspace_dir is not None:
                return self.workspace_root.joinpath(workspace_dir)
        return None

    def set_workspace_settings(self, workspace_settings: Optional[WorkspaceSettings] = None) -> None:
        if workspace_settings is not None:
            self.workspace_settings = workspace_settings

    def get_env_file_data(self) -> Optional[Dict[str, Any]]:
        if self.cached_env_file_data is None:
            from phi.utils.yaml_io import read_yaml_file

            self.cached_env_file_data = read_yaml_file(file_path=self.env_file)
        return self.cached_env_file_data

    def get_secret_file_data(self) -> Optional[Dict[str, Any]]:
        if self.cached_secret_file_data is None:
            from phi.utils.yaml_io import read_yaml_file

            self.cached_secret_file_data = read_yaml_file(file_path=self.secrets_file)
        return self.cached_secret_file_data

    def get_secret_from_file(self, secret_name: str) -> Optional[str]:
        secret_file_data = self.get_secret_file_data()
        if secret_file_data is not None:
            return secret_file_data.get(secret_name)
        return None

    def set_aws_env_vars(self, env_dict: Dict[str, str], aws_region: Optional[str] = None) -> None:
        from phi.constants import (
            AWS_REGION_ENV_VAR,
            AWS_DEFAULT_REGION_ENV_VAR,
        )

        if aws_region is not None:
            env_dict[AWS_REGION_ENV_VAR] = aws_region
            env_dict[AWS_DEFAULT_REGION_ENV_VAR] = aws_region
        elif self.workspace_settings is not None and self.workspace_settings.aws_region is not None:
            env_dict[AWS_REGION_ENV_VAR] = self.workspace_settings.aws_region
            env_dict[AWS_DEFAULT_REGION_ENV_VAR] = self.workspace_settings.aws_region

    def validate_configuration(self) -> bool:
        """
        Validate the configuration using AI model predictions.
        """
        features = [
            int(self.enabled),
            int(self.skip_create),
            int(self.skip_read),
            int(self.skip_update),
            int(self.skip_delete),
            int(self.recreate_on_update),
            int(self.use_cache),
            int(self.force is not None),
            int(self.debug_mode),
            int(self.env_vars is not None),
            int(self.env_file is not None),
            int(self.secrets_file is not None),
            int(self.aws_secrets is not None),
            int(self.wait_for_create),
            int(self.wait_for_update),
            int(self.wait_for_delete),
            self.waiter_delay,
            self.waiter_max_attempts,
            int(self.save_output),
            int(self.input_dir is not None),
            int(self.output_dir is not None),
            int(self.depends_on is not None),
        ]
        prediction = self.ai_model.predict([features])
        return prediction[0] == 1  # Assume 1 means valid

    def suggest_parameters(self) -> Dict[str, Any]:
        """
        Suggest optimal parameters based on AI model.
        """
        features = [
            int(self.enabled),
            int(self.skip_create),
            int(self.skip_read),
            int(self.skip_update),
            int(self.skip_delete),
            int(self.recreate_on_update),
            int(self.use_cache),
            int(self.force is not None),
            int(self.debug_mode),
            int(self.env_vars is not None),
            int(self.env_file is not None),
            int(self.secrets_file is not None),
            int(self.aws_secrets is not None),
            int(self.wait_for_create),
            int(self.wait_for_update),
            int(self.wait_for_delete),
            self.waiter_delay,
            self.waiter_max_attempts,
            int(self.save_output),
            int(self.input_dir is not None),
            int(self.output_dir is not None),
            int(self.depends_on is not None),
        ]
        suggested_values = self.ai_model.predict_proba([features])[0]
        # Map suggested values to parameters
        return {
            "waiter_delay": int(np.argmax(suggested_values[16:17])),
            "waiter_max_attempts": int(np.argmax(suggested_values[17:18])),
            # Add more mappings as needed
        }
