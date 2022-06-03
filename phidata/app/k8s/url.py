from collections import OrderedDict
from pathlib import Path
from typing import Optional, Dict, List, Union, Any, cast

from pydantic import AnyUrl, ValidationError

from phidata.app.db import DbApp
from phidata.app.k8s.app import K8sApp, K8sAppArgs
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


class K8sUrlArgs(K8sAppArgs):
    url: str
    file_name: Optional[str] = None
    cache_dir: Union[str, Path] = "k8s"


class K8sUrl(K8sApp):
    def __init__(
        self,
        url: str,
        name: str,
        file_name: Optional[str] = None,
        cache_dir: Union[str, Path] = "k8s",
        version: str = "1",
        enabled: bool = True,
        cache_manifests: bool = True,
    ):
        super().__init__()

        try:
            self.args: K8sUrlArgs = K8sUrlArgs(
                url=url,
                name=name,
                file_name=file_name,
                cache_dir=cache_dir,
                version=version,
                enabled=enabled,
                cache_manifests=cache_manifests,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

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

    def get_download_file_path(self) -> Optional[Path]:
        """
        Returns the file path to download the URL to
        """

        file_dir: Optional[Path] = None
        if isinstance(self.args.cache_dir, str):
            workspace_config_dir = self.workspace_config_dir
            if workspace_config_dir:
                file_dir = (
                    Path(workspace_config_dir)
                    .joinpath(self.args.cache_dir)
                    .joinpath(self.args.name)
                    .resolve()
                )
        elif isinstance(self.args.cache_dir, Path):
            file_dir = self.args.cache_dir

        if file_dir is not None:
            file_name: str = self.best_guess_file_name()
            return file_dir.joinpath(file_name)

        return None

    def prepare_manifest_file(self) -> Path:
        """
        Downloads the URL if needed and returns a Path object
        pointing to the downloaded file

        Raises Exception if file cannot be prepared
        """

        # Validate URL
        url = self.args.url
        if url is None:
            raise AppInvalidException("Invalid URL")

        # Validate file_path is available
        download_file_path = self.get_download_file_path()
        if download_file_path is None:
            raise AppInvalidException("Download FilePath invalid")

        if (
            self.args.cache_manifests
            and download_file_path.exists()
            and download_file_path.is_file()
        ):
            logger.debug("File exists")
            return download_file_path

        # Download URL contents
        logger.debug("Downloading")
        logger.debug(f"  Url: {url}")
        logger.debug(f"  To : {download_file_path}")

        # Create the parent directory if it does not exist
        file_dir = download_file_path.parent
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
                download_file_path.write_text(response_text)
                logger.info(f"Url downloaded to {str(download_file_path)}")
                return download_file_path

            # Download file as bytes
            response_bytes: bytes = response.content
            if response_bytes is not None and response_bytes != b"":
                download_file_path.write_bytes(response_bytes)
                logger.info(f"Url downloaded to {str(download_file_path)}")
                return download_file_path
        except Exception as e:
            logger.error(f"Could not download url: {url}")
            logger.exception(e)
        raise AppInvalidException("Could not create manifest file")

    def get_k8s_rg(
        self, k8s_build_context: K8sBuildContext
    ) -> Optional[K8sResourceGroup]:

        # Prepare manifest file and set the args
        self.args.manifest_file = self.prepare_manifest_file()
        return super().get_k8s_rg(k8s_build_context=k8s_build_context)
