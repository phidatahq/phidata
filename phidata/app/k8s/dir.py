from pathlib import Path
from typing import Optional, Union

from phidata.app.k8s.app import K8sApp, K8sAppArgs
from phidata.exceptions.app import AppInvalidException
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.log import logger


class K8sDirArgs(K8sAppArgs):
    dir: Union[str, Path]


class K8sDir(K8sApp):
    def __init__(
        self,
        dir: Union[str, Path],
        name: Optional[str] = None,
        version: str = "1",
        enabled: bool = True,
        cache_manifests: bool = True,
    ):
        super().__init__()

        try:
            self.args: K8sDirArgs = K8sDirArgs(
                dir=dir,
                name=name,
                version=version,
                enabled=enabled,
                cache_manifests=cache_manifests,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    def get_k8s_rg(
        self, k8s_build_context: K8sBuildContext
    ) -> Optional[K8sResourceGroup]:

        # Validate URL
        manifest_dir = self.args.dir
        if manifest_dir is None:
            raise AppInvalidException("Invalid dir")

        if isinstance(manifest_dir, str):
            workspace_config_dir = self.workspace_config_dir
            if workspace_config_dir:
                self.args.manifest_dir = (
                    Path(workspace_config_dir).joinpath(manifest_dir).resolve()
                )
        elif isinstance(manifest_dir, Path):
            self.args.manifest_dir = manifest_dir

        if self.args.name is None:
            self.args.name = self.args.manifest_dir.stem

        return super().get_k8s_rg(k8s_build_context=k8s_build_context)
