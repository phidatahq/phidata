from typing import Optional, List, Union

from phidata.app.base_app import BaseApp
from phidata.app.phidata_app import PhidataApp
from phidata.app.group import AppGroup, get_apps_from_app_groups
from phidata.aws.args import AwsArgs
from phidata.aws.manager import AwsManager
from phidata.aws.resource.group import AwsResourceGroup
from phidata.infra.config import InfraConfig
from phidata.utils.log import logger


class AwsConfig(InfraConfig):
    def __init__(
        self,
        env: Optional[str] = "prd",
        version: Optional[str] = None,
        enabled: bool = True,
        apps: Optional[List[Union[BaseApp, PhidataApp]]] = None,
        app_groups: Optional[List[AppGroup]] = None,
        # AwsResourceGroups to deploy
        resources: Optional[Union[AwsResourceGroup, List[AwsResourceGroup]]] = None,
        # Resources dir where aws manifests are stored
        resources_dir: str = "aws",
        # Aws params for this Config
        # Override the aws params from WorkspaceConfig if provided
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        aws_config_file: Optional[str] = None,
        aws_shared_credentials_file: Optional[str] = None,
    ):
        super().__init__()
        _resources: Optional[List[AwsResourceGroup]] = None
        if resources is not None:
            if isinstance(resources, list):
                for _r in resources:
                    if isinstance(_r, AwsResourceGroup):
                        if _resources is None:
                            _resources = []
                        _resources.append(_r)
                    else:
                        logger.error(f"Invalid resource group: {_r}")
            elif isinstance(resources, AwsResourceGroup):
                _resources = [resources]

        _apps = apps if apps is not None else []
        if app_groups is not None:
            _apps.extend(get_apps_from_app_groups(app_groups))

        try:
            self.args: AwsArgs = AwsArgs(
                env=env,
                version=version,
                enabled=enabled,
                apps=_apps,
                resources=_resources,
                resources_dir=resources_dir,
                aws_region=aws_region,
                aws_profile=aws_profile,
                aws_config_file=aws_config_file,
                aws_shared_credentials_file=aws_shared_credentials_file,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def resources(self) -> Optional[List[AwsResourceGroup]]:
        return self.args.resources if self.args else None

    @property
    def resources_dir(self) -> Optional[str]:
        return self.args.resources_dir if self.args else None

    @resources_dir.setter
    def resources_dir(self, resources_dir: str) -> None:
        if self.args is not None and resources_dir is not None:
            self.args.resources_dir = resources_dir

    def is_valid(self) -> bool:
        return True

    def get_aws_manager(self) -> Optional[AwsManager]:
        return AwsManager(aws_args=self.args)
