from phidata.app.group import AppGroup
from phidata.app.jupyter import JupyterLab
from phidata.docker.resource.image import DockerImage

from workspace.settings import ws_settings

#
# -*- Jupyter Docker resources
#

# -*- Jupyter image
dev_jupyter_image = DockerImage(
    name=f"{ws_settings.image_repo}/jupyter-{ws_settings.image_suffix}",
    tag=ws_settings.dev_env,
    enabled=ws_settings.build_images,
    path=str(ws_settings.ws_root),
    dockerfile="workspace/dev/images/jupyter.Dockerfile",
    pull=ws_settings.force_pull_images,
    push_image=ws_settings.push_images,
    skip_docker_cache=ws_settings.skip_image_cache,
    use_cache=ws_settings.use_cache,
)

# JupyterLab: Run dev notebooks
dev_jupyter = JupyterLab(
    image=dev_jupyter_image,
    mount_workspace=True,
    # The jupyter_lab_config is mounted when creating the image
    jupyter_config_file="/usr/local/jupyter/jupyter_lab_config.py",
    # Read env variables from env/dev_jupyter_env.yml
    env_file=ws_settings.ws_root.joinpath("workspace/env/dev_jupyter_env.yml"),
    # Read secrets from secrets/dev_jupyter_secrets.yml
    secrets_file=ws_settings.ws_root.joinpath(
        "workspace/secrets/dev_jupyter_secrets.yml"
    ),
    use_cache=ws_settings.use_cache,
    # Run the notebook server on jupyter.dp
    container_labels={
        "traefik.enable": "true",
        "traefik.http.routers.jupyter.entrypoints": "http",
        "traefik.http.routers.jupyter.rule": "Host(`jupyter.dp`)",
        "traefik.http.services.jupyter.loadbalancer.server.port": "8888",
    },
)

dev_jupyter_apps = AppGroup(
    name="jupyter",
    enabled=ws_settings.dev_jupyter_enabled,
    apps=[dev_jupyter],
)
