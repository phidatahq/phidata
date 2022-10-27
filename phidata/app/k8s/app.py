import yaml
from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, List, Any

from phidata.app.phidata_app import PhidataApp, PhidataAppArgs
from phidata.infra.docker.resource.group import DockerBuildContext
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.log import logger


class K8sAppArgs(PhidataAppArgs):
    name: str = "K8sApp"
    version: str = "1"
    enabled: bool = True

    manifest_dir: Optional[Path] = None
    manifest_file: Optional[Path] = None
    cache_manifests: bool = True


class K8sApp(PhidataApp):
    def __init__(
        self,
        name: str = "K8sApp",
        version: str = "1",
        enabled: bool = True,
        manifest_dir: Optional[Path] = None,
        manifest_file: Optional[Path] = None,
        cache_manifests: bool = True,
    ):
        super().__init__()
        try:
            self.args: K8sAppArgs = K8sAppArgs(
                name=name,
                version=version,
                enabled=enabled,
                manifest_dir=manifest_dir,
                manifest_file=manifest_file,
                cache_manifests=cache_manifests,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    def init_docker_resource_groups(
        self, docker_build_context: DockerBuildContext
    ) -> None:
        logger.error(f"{self.args.name} not available for Docker")

    ######################################################
    ## K8s Resources
    ######################################################

    def get_k8s_rg(
        self, k8s_build_context: K8sBuildContext
    ) -> Optional[K8sResourceGroup]:
        app_name = self.name
        logger.debug(f"Building {app_name} K8sResourceGroup")

        # K8sResourceGroup to return
        k8s_resource_group: K8sResourceGroup = K8sResourceGroup(
            name=app_name,
            enabled=self.enabled,
        )

        manifest_dir: Optional[Path] = self.args.manifest_dir
        manifest_file: Optional[Path] = self.args.manifest_file
        manifests_to_parse: List[Dict[str, Any]] = []

        # Read manifests from file
        if manifest_file is not None:
            logger.debug(f"Reading manifests from {manifest_file}")
            suffix = manifest_file.suffix
            if suffix == ".yaml":
                for manifest in yaml.safe_load_all(manifest_file.read_text()):
                    if isinstance(manifest, dict):
                        manifests_to_parse.append(manifest)
            else:
                logger.error(f"{suffix} files not yet supported")

            if len(manifests_to_parse) == 0:
                logger.warning(f"No manifests found in {str(manifest_file)}")
                return None

        # Read manifests from dir
        elif manifest_dir is not None:
            if manifest_dir.exists() and manifest_dir.is_dir():
                for _file in manifest_dir.glob("*.yaml"):
                    logger.debug(f"Reading manifests from {_file}")
                    for manifest in yaml.safe_load_all(_file.read_text()):
                        if isinstance(manifest, dict):
                            manifests_to_parse.append(manifest)

            if len(manifests_to_parse) == 0:
                logger.warning(f"No manifests found in {str(manifest_dir)}")
                return None

        for manifest in manifests_to_parse:
            k8s_resource_group.add_manifest_to_group(manifest)

        return k8s_resource_group

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:
        k8s_rg = self.get_k8s_rg(k8s_build_context)
        if k8s_rg is not None:
            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg
