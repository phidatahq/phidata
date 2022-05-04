from typing import List, Optional, Dict

from pydantic import BaseModel

from phidata.infra.k8s.create.common.port import CreatePort
from phidata.infra.k8s.create.core.v1.volume import CreateVolume
from phidata.infra.k8s.enums.image_pull_policy import ImagePullPolicy
from phidata.utils.common import get_image_str
from phidata.infra.k8s.resource.core.v1.container import (
    Container,
    ContainerPort,
    EnvFromSource,
    VolumeMount,
    ConfigMapEnvSource,
    SecretEnvSource,
    EnvVar,
    EnvVarSource,
    ConfigMapKeySelector,
    SecretKeySelector,
)
from phidata.utils.log import logger


class CreateEnvVarFromConfigMap(BaseModel):
    env_var_name: str
    configmap_name: str
    configmap_key: Optional[str] = None


class CreateEnvVarFromSecret(BaseModel):
    env_var_name: str
    secret_name: str
    secret_key: Optional[str] = None


class CreateContainer(BaseModel):
    container_name: str
    app_name: str
    image_name: str
    image_tag: str
    args: Optional[List[str]] = None
    command: Optional[List[str]] = None
    image_pull_policy: Optional[ImagePullPolicy] = ImagePullPolicy.IF_NOT_PRESENT
    env: Optional[Dict[str, str]] = None
    envs_from_configmap: Optional[List[str]] = None
    envs_from_secret: Optional[List[str]] = None
    env_vars_from_secret: Optional[List[CreateEnvVarFromSecret]] = None
    env_vars_from_configmap: Optional[List[CreateEnvVarFromConfigMap]] = None
    ports: Optional[List[CreatePort]] = None
    volumes: Optional[List[CreateVolume]] = None
    labels: Optional[Dict[str, str]] = None

    def create(self) -> Optional[Container]:
        """Creates the Container resource"""

        container_name = self.container_name
        logger.debug(f"Init Container resource: {container_name}")

        container_ports: Optional[List[ContainerPort]] = None
        if self.ports:
            container_ports = []
            for _port in self.ports:
                container_ports.append(
                    ContainerPort(
                        name=_port.name,
                        container_port=_port.container_port,
                        protocol=_port.protocol,
                    )
                )

        env_from: Optional[List[EnvFromSource]] = None
        if self.envs_from_configmap:
            if env_from is None:
                env_from = []
            for _cm_name_for_env in self.envs_from_configmap:
                env_from.append(
                    EnvFromSource(
                        config_map_ref=ConfigMapEnvSource(name=_cm_name_for_env)
                    )
                )
        if self.envs_from_secret:
            if env_from is None:
                env_from = []
            for _secretenvs in self.envs_from_secret:
                env_from.append(
                    EnvFromSource(secret_ref=SecretEnvSource(name=_secretenvs))
                )

        env: Optional[List[EnvVar]] = None
        if self.env is not None and isinstance(self.env, dict):
            if env is None:
                env = []
            for key, value in self.env.items():
                env.append(
                    EnvVar(
                        name=key,
                        value=value,
                    )
                )

        if self.env_vars_from_configmap:
            if env is None:
                env = []
            for _cmenv_var in self.env_vars_from_configmap:
                env.append(
                    EnvVar(
                        name=_cmenv_var.env_var_name,
                        value_from=EnvVarSource(
                            config_map_key_ref=ConfigMapKeySelector(
                                key=_cmenv_var.configmap_key
                                if _cmenv_var.configmap_key
                                else _cmenv_var.env_var_name,
                                name=_cmenv_var.configmap_name,
                            )
                        ),
                    )
                )
        if self.env_vars_from_secret:
            if env is None:
                env = []
            for _secretenv_var in self.env_vars_from_secret:
                env.append(
                    EnvVar(
                        name=_secretenv_var.env_var_name,
                        value_from=EnvVarSource(
                            secret_key_ref=SecretKeySelector(
                                key=_secretenv_var.secret_key
                                if _secretenv_var.secret_key
                                else _secretenv_var.env_var_name,
                                name=_secretenv_var.secret_name,
                            )
                        ),
                    )
                )

        volume_mounts: Optional[List[VolumeMount]] = None
        if self.volumes:
            volume_mounts = []
            for _volume in self.volumes:
                volume_mounts.append(
                    VolumeMount(
                        name=_volume.volume_name,
                        mount_path=_volume.mount_path,
                    )
                )

        container_resource = Container(
            name=container_name,
            image=get_image_str(self.image_name, self.image_tag),
            image_pull_policy=self.image_pull_policy,
            args=self.args,
            command=self.command,
            ports=container_ports,
            env_from=env_from,
            env=env,
            volume_mounts=volume_mounts,
        )
        return container_resource
