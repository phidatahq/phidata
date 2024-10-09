from phi.docker.app.jupyter import Jupyter
from phi.docker.resource.image import DockerImage

from workspace.settings import ws_settings

#
# -*- Jupyter Docker resources
#

# -*- Jupyter image
jupyter_image = DockerImage(
    name=f"{ws_settings.image_repo}/jupyter-{ws_settings.image_name}",
    tag=ws_settings.dev_env,
    enabled=(ws_settings.build_images and ws_settings.dev_jupyter_enabled),
    path=str(ws_settings.ws_root),
    dockerfile="workspace/jupyter/Dockerfile",
    pull=ws_settings.force_pull_images,
    skip_docker_cache=ws_settings.skip_image_cache,
)

# -*- Jupyter running on port 8888:8888
dev_jupyter_app = Jupyter(
    name=f"jupyter-{ws_settings.ws_name}",
    enabled=ws_settings.dev_jupyter_enabled,
    image=jupyter_image,
    mount_workspace=True,
    use_cache=ws_settings.use_cache,
    # Read secrets from secrets/dev_jupyter_secrets.yml
    secrets_file=ws_settings.ws_root.joinpath("workspace/secrets/dev_jupyter_secrets.yml"),
)
