from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, List, Union, Any, cast

from pydantic import AnyUrl, ValidationError

from phidata.app.db import DbApp
from phidata.app import PhidataApp, PhidataAppArgs
from phidata.exceptions.app import AppInvalidException
from phidata.constants import (
    SCRIPTS_DIR_ENV_VAR,
    STORAGE_DIR_ENV_VAR,
    META_DIR_ENV_VAR,
    PRODUCTS_DIR_ENV_VAR,
    NOTEBOOKS_DIR_ENV_VAR,
    WORKSPACE_CONFIG_DIR_ENV_VAR,
    PHIDATA_RUNTIME_ENV_VAR,
)
from phidata.infra.docker.resource.network import DockerNetwork
from phidata.infra.docker.resource.container import DockerContainer
from phidata.infra.docker.resource.group import (
    DockerResourceGroup,
    DockerBuildContext,
)
from phidata.infra.k8s.create.apps.v1.deployment import CreateDeployment
from phidata.infra.k8s.create.core.v1.secret import CreateSecret
from phidata.infra.k8s.create.core.v1.config_map import CreateConfigMap
from phidata.infra.k8s.create.core.v1.container import CreateContainer
from phidata.infra.k8s.create.core.v1.volume import (
    CreateVolume,
    VolumeType,
)
from phidata.infra.k8s.create.common.port import CreatePort
from phidata.infra.k8s.create.group import CreateK8sResourceGroup
from phidata.infra.k8s.enums.image_pull_policy import ImagePullPolicy
from phidata.infra.k8s.enums.restart_policy import RestartPolicy
from phidata.infra.k8s.resource.group import (
    K8sResourceGroup,
    K8sBuildContext,
)
from phidata.utils.common import (
    get_image_str,
    get_default_container_name,
    get_default_configmap_name,
    get_default_secret_name,
    get_default_deploy_name,
    get_default_pod_name,
)
from phidata.utils.cli_console import print_error
from phidata.utils.log import logger


class K8sUrlArgs(PhidataAppArgs):
    name: str = "k8s_url"
    version: str = "1"
    enabled: bool = True

    url: str
    file_name: Optional[str] = None
    cache_manifests: bool = True
    manifest_dir: Union[str, Path] = "k8s"


class K8sUrl(PhidataApp):
    def __init__(
        self,
        url: str,
        name: str = "k8s_url",
        version: str = "1",
        enabled: bool = True,
        file_name: Optional[str] = None,
        cache_manifests: bool = True,
        manifest_dir: Union[str, Path] = "k8s",
    ):
        super().__init__()
        try:
            self.args: K8sUrlArgs = K8sUrlArgs(
                url=url,
                name=name,
                version=version,
                enabled=enabled,
                file_name=file_name,
                cache_manifests=cache_manifests,
                manifest_dir=manifest_dir,
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

    def best_guess_file_name(self) -> str:

        from phidata.utils.dttm import get_today_utc_date_str

        fn: Optional[str] = self.args.file_name
        if fn is None:
            _url_path: str = str(self.args.url)
            if "/" in _url_path:
                fn = _url_path.split("/")[-1]
        if fn is None:
            fn = get_today_utc_date_str()
        logger.debug(f"Best guess file name: {fn}")
        return fn

    def get_file_path(self) -> Optional[Path]:
        """
        Returns the file path to download the URL to
        """

        file_name: str = self.best_guess_file_name()
        file_dir: Optional[Path] = None

        if isinstance(self.args.manifest_dir, str):
            workspace_config_dir = self.workspace_config_dir
            if workspace_config_dir:
                file_dir = (
                    Path(workspace_config_dir)
                    .joinpath(self.args.manifest_dir)
                    .joinpath(self.args.name)
                    .resolve()
                )
        elif isinstance(self.args.manifest_dir, Path):
            file_dir = self.args.manifest_dir

        if file_dir is not None:
            return file_dir.joinpath(file_name)
        return None

    def prepare_manifest_file(self) -> Path:
        """
        Downloads the URL if needed and returns
        a Path object pointing to the downloaded file

        Raises Exception if file cannot be prepared
        """

        # Validate URL
        url = self.args.url
        if url is None:
            raise AppInvalidException("Invalid URL")

        # Validate file_path is available
        file_path = self.get_file_path()
        if file_path is None:
            raise AppInvalidException("FilePath invalid")

        if self.args.cache_manifests and file_path.exists() and file_path.is_file():
            logger.debug("File exists")
            return file_path

        # Download URL contents
        logger.debug("Downloading")
        logger.debug(f"  Url: {url}")
        logger.debug(f"  To : {file_path}")

        # Create the parent directory if it does not exist
        file_dir = file_path.parent
        if not file_dir.exists():
            file_dir.mkdir(parents=True, exist_ok=True)

        # Download URL to file
        try:
            import httpx

            response: httpx.Response = httpx.get(url=url)
            # logger.debug("response: {}".format(type(response)))
            # logger.debug("response: {}".format(str(response)))

            if response.is_error:
                logger.error("Could not read URL")
                logger.error(response.reason_phrase)
                response.raise_for_status()

            # Download file as text
            response_text: str = response.text
            if response_text is not None and response_text != "":
                file_path.write_text(response_text)
                logger.info(f"Url downloaded to {str(file_path)}")
                return file_path

            # Download file as bytes
            response_bytes: bytes = response.content
            if response_bytes is not None and response_bytes != b"":
                file_path.write_bytes(response_bytes)
                logger.info(f"Url downloaded to {str(file_path)}")
                return file_path
        except Exception as e:
            logger.error(f"Could not download url: {url}")
            logger.exception(e)
        raise AppInvalidException("Could not create manifest file")

    def get_k8s_rg(
        self, k8s_build_context: K8sBuildContext
    ) -> Optional[K8sResourceGroup]:
        app_name = self.name
        logger.debug(f"Building {app_name} K8sResourceGroup")

        # Prepare manifest file
        file_path: Path = self.prepare_manifest_file()

        # Read manifests from file
        manifests_from_file: List[Dict[str, Any]] = []
        suffix = file_path.suffix
        if suffix == ".yaml":
            import yaml

            for manifest in yaml.safe_load_all(file_path.read_text()):
                # logger.info(f"manifest: {manifest}")
                if isinstance(manifest, dict):
                    manifests_from_file.append(manifest)
        else:
            logger.error(f"{suffix} files not yet supported")
        # logger.info(f"manifests_from_file: {manifests_from_file}")

        if len(manifests_from_file) == 0:
            logger.warning(f"No manifests found in {str(file_path)}")
            return None

        # Create K8sResourceGroup
        k8s_resource_group: K8sResourceGroup = K8sResourceGroup(
            name=self.name,
            enabled=self.enabled,
        )
        for manifest in manifests_from_file:
            logger.debug(f"Reading: {manifest}")

            kind = manifest.get("kind", None)
            if kind is None:
                logger.warning(f"Could not parse manifest: {manifest}")

            try:

                ######################################################
                ## Parse Namespace
                ######################################################
                if kind == "Namespace":
                    from phidata.infra.k8s.resource.core.v1.namespace import Namespace

                    _ns_resource = Namespace(**manifest)
                    if _ns_resource is not None:
                        _ns_resource.name = self.args.name
                        k8s_resource_group.ns = _ns_resource
                        logger.debug(
                            f"Read: {_ns_resource.get_resource_type()}: {_ns_resource.get_resource_name()}"
                        )
                ######################################################
                ## Parse ServiceAccount
                ######################################################
                elif kind == "'ServiceAccount',":
                    from phidata.infra.k8s.resource.core.v1.service_account import (
                        ServiceAccount,
                    )

                    _sa_resource = ServiceAccount(**manifest)
                    if _sa_resource is not None:
                        _sa_resource.name = self.args.name
                        k8s_resource_group.sa = _sa_resource
                        logger.debug(
                            f"Read: {_sa_resource.get_resource_type()}: {_sa_resource.get_resource_name()}"
                        )
                ######################################################
                ## Parse ClusterRole
                ######################################################
                elif kind == "ClusterRole":
                    from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluster_role import (
                        ClusterRole,
                    )

                    _cr_resource = ClusterRole(**manifest)
                    if _cr_resource is not None:
                        _cr_resource.name = self.args.name
                        k8s_resource_group.cr = _cr_resource
                        logger.debug(
                            f"Read: {_cr_resource.get_resource_type()}: {_cr_resource.get_resource_name()}"
                        )
                ######################################################
                ## Parse ClusterRoleBinding
                ######################################################
                elif kind == "ClusterRoleBinding":
                    from phidata.infra.k8s.resource.rbac_authorization_k8s_io.v1.cluste_role_binding import (
                        ClusterRoleBinding,
                    )

                    _crb_resource = ClusterRoleBinding(**manifest)
                    if _crb_resource is not None:
                        _crb_resource.name = self.args.name
                        k8s_resource_group.crb = _crb_resource
                        logger.debug(
                            f"Read: {_crb_resource.get_resource_type()}: {_crb_resource.get_resource_name()}"
                        )
                ######################################################
                ## Parse Secrets
                ######################################################
                elif kind == "Secret":
                    from phidata.infra.k8s.resource.core.v1.secret import Secret

                    _secret_resource = Secret(**manifest)
                    _secret_resource.name = self.args.name
                    if k8s_resource_group.secrets is None:
                        k8s_resource_group.secrets = []
                    k8s_resource_group.secrets.append(_secret_resource)
                    logger.debug(
                        f"Read: {_secret_resource.get_resource_type()}: {_secret_resource.get_resource_name()}"
                    )
                ######################################################
                ## Parse ConfigMaps
                ######################################################
                elif kind == "ConfigMap":
                    from phidata.infra.k8s.resource.core.v1.config_map import ConfigMap

                    _cm_resource = ConfigMap(**manifest)
                    _cm_resource.name = self.args.name
                    if k8s_resource_group.config_maps is None:
                        k8s_resource_group.config_maps = []
                    k8s_resource_group.config_maps.append(_cm_resource)
                    logger.debug(
                        f"Read: {_cm_resource.get_resource_type()}: {_cm_resource.get_resource_name()}"
                    )
                ######################################################
                ## Parse StorageClasses
                ######################################################
                elif kind == "StorageClass":
                    from phidata.infra.k8s.resource.storage_k8s_io.v1.storage_class import (
                        StorageClass,
                    )

                    _sc_resource = StorageClass(**manifest)
                    _sc_resource.name = self.args.name
                    if k8s_resource_group.storage_classes is None:
                        k8s_resource_group.storage_classes = []
                    k8s_resource_group.storage_classes.append(_sc_resource)
                    logger.debug(
                        f"Read: {_sc_resource.get_resource_type()}: {_sc_resource.get_resource_name()}"
                    )
                ######################################################
                ## Parse Services
                ######################################################
                elif kind == "Service":
                    from phidata.infra.k8s.resource.core.v1.service import Service

                    _svc_resource = Service(**manifest)
                    _svc_resource.name = self.args.name
                    if k8s_resource_group.services is None:
                        k8s_resource_group.services = []
                    k8s_resource_group.services.append(_svc_resource)
                    logger.debug(
                        f"Read: {_svc_resource.get_resource_type()}: {_svc_resource.get_resource_name()}"
                    )
                ######################################################
                ## Parse Deployments
                ######################################################
                elif kind == "Deployment":
                    from phidata.infra.k8s.resource.apps.v1.deployment import Deployment

                    _deploy_resource = Deployment(**manifest)
                    _deploy_resource.name = self.args.name
                    if k8s_resource_group.deployments is None:
                        k8s_resource_group.deployments = []
                    k8s_resource_group.deployments.append(_deploy_resource)
                    logger.debug(
                        f"Read: {_deploy_resource.get_resource_type()}: {_deploy_resource.get_resource_name()}"
                    )
                ######################################################
                ## Parse CustomResourceDefinitions
                ######################################################
                if kind == "CustomResourceDefinition":
                    from phidata.infra.k8s.resource.apiextensions_k8s_io.v1.custom_resource_definition import (
                        CustomResourceDefinition,
                    )

                    _crd_resource = CustomResourceDefinition(**manifest)
                    _crd_resource.name = self.args.name
                    if k8s_resource_group.crds is None:
                        k8s_resource_group.crds = []
                    k8s_resource_group.crds.append(_crd_resource)
                    logger.debug(
                        f"Read: {_crd_resource.get_resource_type()}: {_crd_resource.get_resource_name()}"
                    )
                ######################################################
                ## TODO: Parse CustomObjects
                ######################################################

            except ValidationError as validation_error:
                logger.warning(
                    f"Could not parse manifest, run with -d flag to view the malformed manifest"
                )
                logger.exception(validation_error)
                continue
        return k8s_resource_group

    def init_k8s_resource_groups(self, k8s_build_context: K8sBuildContext) -> None:
        k8s_rg = self.get_k8s_rg(k8s_build_context)
        if k8s_rg is not None:
            if self.k8s_resource_groups is None:
                self.k8s_resource_groups = OrderedDict()
            self.k8s_resource_groups[k8s_rg.name] = k8s_rg

        # logger.info(f"self.k8s_resource_groups: {self.k8s_resource_groups}")
